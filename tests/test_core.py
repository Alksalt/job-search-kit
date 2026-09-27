"""Synthetic state, recovery and filesystem boundary regressions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from jobkit.__main__ import main as cli_main
from jobkit.core import SOURCE_ROOT, WorkflowError, Workspace, canonical_url, demo


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="jobkit-test-")
        self.base = Path(self.temporary.name).resolve()
        self.workspace = Workspace(self.base / "private")
        self.workspace.init()
        for name in ("cv.txt", "letter.txt", "preview.txt", "receipt.txt"):
            (self.workspace.root / name).write_text(f"Synthetic {name}; no real person or employer.\n")

    def tearDown(self):
        self.temporary.cleanup()

    def add(self, identifier="example", deadline="2099-12-31"):
        self.workspace.add(identifier, f"https://example.invalid/jobs/{identifier}",
                           "Fictional role", "Fictional employer", deadline)

    def ready(self, identifier="example", deadline="2099-12-31"):
        self.add(identifier, deadline)
        self.workspace.screen(identifier, "pass", "Synthetic matching evidence.")
        self.workspace.packet(identifier, "cv.txt", "letter.txt", approved=True)
        self.workspace.authorize(identifier, "Synthetic user permission for this vacancy.")
        self.workspace.preview(identifier, "preview.txt")

    def prepare_again(self, identifier="example"):
        self.workspace.packet(identifier, "cv.txt", "letter.txt", approved=True)
        self.workspace.authorize(identifier, "New synthetic permission")
        self.workspace.preview(identifier, "preview.txt")

    def attempt(self, identifier="example"):
        return self.workspace.attempt(identifier)["attempt_id"]

    def row(self, identifier="example"):
        with self.workspace.connection() as con:
            return dict(con.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone())

    def snapshot(self):
        """Database records plus every workspace file, to prove a rejected command changed nothing."""
        with self.workspace.connection() as con:
            state = [dict(row) for row in con.execute("SELECT * FROM jobs ORDER BY id")]
            state += [dict(row) for row in con.execute("SELECT * FROM events ORDER BY sequence")]
        files = sorted(path.relative_to(self.workspace.root).as_posix() for path in self.workspace.root.rglob("*"))
        return state, files

    def test_full_flow_and_no_receipt_before_attempt(self):
        self.ready()
        with self.assertRaises(WorkflowError):
            self.workspace.receipt("example", "0" * 32, "SYNTHETIC", "receipt.txt")
        attempt = self.attempt()
        self.workspace.receipt("example", attempt, "SYNTHETIC", "receipt.txt")
        self.assertEqual("sent", self.row()["status"])
        self.assertTrue(self.workspace.verify()["ok"])
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")

    def test_packet_rebuild_invalidates_authorization_and_preview(self):
        self.ready()
        self.workspace.packet("example", "cv.txt", "letter.txt", approved=True)
        self.assertIsNone(self.row()["authorization"])
        self.assertIsNone(self.row()["preview"])
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")

    def test_packet_returns_absolute_paths_to_managed_uploads(self):
        self.add()
        self.workspace.screen('example', 'pass', 'Synthetic matching evidence.')
        result = self.workspace.packet('example', 'cv.txt', 'letter.txt', approved=True)
        for kind, source in (('cv', 'cv.txt'), ('letter', 'letter.txt')):
            path = Path(result['upload_paths'][kind])
            self.assertTrue(path.is_absolute())
            self.assertTrue(path.is_relative_to(self.workspace.root / 'packets'))
            self.assertEqual((self.workspace.root / source).read_bytes(), path.read_bytes())

    def test_changed_managed_packet_detected(self):
        self.ready()
        manifest = json.loads(self.row()["packet"])
        managed = self.workspace.root / manifest["files"]["cv"]["path"]
        managed.write_text("Changed managed upload")
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")
        self.assertFalse(self.workspace.verify()["ok"])

    def test_sources_are_provenance_and_managed_snapshots_are_authoritative(self):
        self.ready()
        original = self.workspace.show("example")["packet"]
        for name in ("cv.txt", "letter.txt", "preview.txt"):
            (self.workspace.root / name).write_text("Reusable source filename now belongs to a different vacancy")
        self.ready("other")
        self.assertEqual(original, self.workspace.show("example")["packet"])
        self.assertTrue(self.workspace.verify()["ok"])
        self.workspace.attempt("example")

    def test_changed_managed_preview_blocks_attempt(self):
        self.ready()
        preview = self.workspace.show("example")["preview"]
        (self.workspace.root / preview["path"]).write_text("Changed saved preview")
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")

    def test_old_preview_requires_new_check_but_preserves_authorization(self):
        self.ready()
        with self.workspace.connection(write=True) as con:
            preview = json.loads(self.row()["preview"])
            preview["at"] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            con.execute("UPDATE jobs SET preview=? WHERE id='example'", (json.dumps(preview),))
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")
        self.assertIsNotNone(self.row()["authorization"])
        self.workspace.preview("example", "preview.txt")
        self.workspace.attempt("example")

    def test_packet_and_preview_snapshots_survive_source_changes_after_send(self):
        self.ready()
        attempt = self.attempt()
        for name in ("cv.txt", "letter.txt", "preview.txt"):
            (self.workspace.root / name).write_text("New source for a later vacancy")
        self.workspace.receipt("example", attempt, "SYNTHETIC", "receipt.txt")
        (self.workspace.root / "receipt.txt").unlink()
        self.assertTrue(self.workspace.verify()["ok"])

    def test_reconcile_not_sent_preserves_history_and_requires_fresh_packet(self):
        self.ready()
        first = self.attempt()
        self.workspace.reconcile("example", first, "not-sent", "receipt.txt")
        self.assertIsNone(self.row()["packet"])
        self.assertIsNone(self.row()["authorization"])
        self.assertIsNone(self.row()["preview"])
        with self.assertRaises(WorkflowError):
            self.workspace.authorize("example", "Again")
        with self.workspace.connection() as con:
            actions = [r[0] for r in con.execute("SELECT action FROM events ORDER BY sequence")]
        self.assertIn("attempt", actions)
        self.assertIn("reconcile", actions)
        self.prepare_again()
        second = self.attempt()
        self.workspace.reconcile("example", second, "sent", "receipt.txt", "RECOVERED-SYNTHETIC")
        self.assertTrue(self.workspace.verify()["ok"])

    def test_historical_reconciliation_evidence_is_verified(self):
        self.ready()
        self.workspace.reconcile("example", self.attempt(), "not-sent", "receipt.txt")
        with self.workspace.connection() as con:
            evidence = json.loads(con.execute("SELECT payload FROM events WHERE action='reconcile'").fetchone()[0])["evidence"]
        (self.workspace.root / evidence["path"]).write_text("Changed historical evidence")
        self.assertFalse(self.workspace.verify()["ok"])

    def test_missing_or_blank_evidence_cannot_resolve_uncertainty(self):
        self.ready()
        attempt = self.attempt()
        for reference, evidence in (("", "receipt.txt"), ("SYNTHETIC", "missing.txt")):
            with self.assertRaises(WorkflowError):
                self.workspace.receipt("example", attempt, reference, evidence)
        self.assertEqual("attempting", self.row()["status"])

    def test_receipt_records_real_outcome_despite_missing_old_evidence(self):
        self.ready()
        attempt = self.attempt()
        current = self.workspace.show("example")
        (self.workspace.root / current["packet"]["files"]["cv"]["path"]).unlink()
        (self.workspace.root / current["preview"]["path"]).write_text("Corrupted old preview")
        result = self.workspace.receipt("example", attempt, "ACTUAL-SYNTHETIC-RECEIPT", "receipt.txt")
        self.assertEqual("sent", result["status"])
        self.assertEqual(2, len(result["integrity_problems"]))
        saved = self.workspace.show("example")["receipt"]
        self.assertEqual("ACTUAL-SYNTHETIC-RECEIPT", saved["reference"])
        self.assertTrue((self.workspace.root / saved["evidence"]["path"]).is_file())
        self.assertFalse(self.workspace.verify()["ok"])
        self.ready("other")
        self.workspace.attempt("other")

    def test_not_sent_reconciliation_can_release_corrupted_attempt(self):
        self.ready()
        attempt = self.attempt()
        preview = self.workspace.show("example")["preview"]
        (self.workspace.root / preview["path"]).unlink()
        result = self.workspace.reconcile("example", attempt, "not-sent", "receipt.txt")
        self.assertEqual("ready", result["status"])
        self.assertTrue(result["integrity_problems"])
        self.assertFalse(self.workspace.verify()["ok"])

    def test_late_receipt_recovers_original_attempt_after_not_sent(self):
        self.ready()
        attempt = self.attempt()
        original_packet = self.workspace.show("example")["packet"]
        self.workspace.reconcile("example", attempt, "not-sent", "receipt.txt")
        self.workspace.deadline("example", "unknown", "Synthetic later uncertainty")
        self.workspace.late_receipt("example", attempt, "LATE-SYNTHETIC-RECEIPT", "receipt.txt")
        record = self.workspace.show("example")
        self.assertEqual("sent", record["status"])
        self.assertEqual(original_packet, record["packet"])
        self.assertEqual("2099-12-31", record["deadline"])
        self.assertEqual(attempt, record["attempt"]["id"])
        self.assertEqual("late-receipt", record["events"][-1]["action"])
        self.assertTrue(self.workspace.verify()["ok"])

    def test_stale_attempt_id_cannot_resolve_newer_attempt_and_changes_nothing(self):
        self.ready()
        first = self.attempt()
        self.workspace.reconcile("example", first, "not-sent", "receipt.txt")
        self.prepare_again()
        second = self.attempt()
        before = self.snapshot()
        for operation in (lambda: self.workspace.receipt("example", first, "DELAYED-FIRST", "receipt.txt"),
                          lambda: self.workspace.reconcile("example", first, "sent", "receipt.txt", "DELAYED-FIRST"),
                          lambda: self.workspace.reconcile("example", "unknown-id", "not-sent", "receipt.txt"),
                          lambda: self.workspace.late_receipt("example", first, "DELAYED-FIRST", "receipt.txt")):
            with self.assertRaises(WorkflowError):
                operation()
        self.assertEqual(before, self.snapshot())
        self.workspace.receipt("example", second, "SECOND-SYNTHETIC", "receipt.txt")
        self.assertEqual(second, self.workspace.show("example")["receipt"]["attempt_id"])
        self.assertTrue(self.workspace.verify()["ok"])

    def test_late_receipt_ignores_and_keeps_another_vacancys_unresolved_attempt(self):
        self.ready()
        first = self.attempt()
        self.workspace.reconcile("example", first, "not-sent", "receipt.txt")
        self.ready("other")
        other = self.attempt("other")
        with self.assertRaises(WorkflowError):
            self.workspace.late_receipt("example", "wrong-id", "SYNTHETIC", "receipt.txt")
        self.workspace.late_receipt("example", first, "LATE-SYNTHETIC", "receipt.txt")
        self.assertEqual("sent", self.row()["status"])
        self.assertEqual("attempting", self.row("other")["status"])
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")
        self.workspace.receipt("other", other, "OTHER-SYNTHETIC", "receipt.txt")
        self.assertTrue(self.workspace.verify()["ok"])

    def test_late_receipt_for_older_attempt_after_newer_not_sent_attempt(self):
        self.ready()
        first = self.attempt()
        self.workspace.reconcile("example", first, "not-sent", "receipt.txt")
        self.prepare_again()
        second = self.attempt()
        self.workspace.reconcile("example", second, "not-sent", "receipt.txt")
        self.workspace.late_receipt("example", first, "LATE-SYNTHETIC", "receipt.txt")
        record = self.workspace.show("example")
        self.assertEqual(("sent", first), (record["status"], record["attempt"]["id"]))
        self.assertEqual([(first, "sent"), (second, "not-sent")],
                         [(item["id"], item["outcome"]) for item in record["attempts"]])
        self.assertTrue(self.workspace.verify()["ok"])

    def test_late_receipt_after_newer_sent_attempt_records_duplicate_without_rewriting(self):
        self.ready()
        first = self.attempt()
        self.workspace.reconcile("example", first, "not-sent", "receipt.txt")
        self.prepare_again()
        second = self.attempt()
        self.workspace.receipt("example", second, "SECOND-SYNTHETIC", "receipt.txt")
        current = self.workspace.show("example")["receipt"]
        with self.assertRaises(WorkflowError):
            self.workspace.late_receipt("example", first, "second-synthetic", "receipt.txt")
        result = self.workspace.late_receipt("example", first, "FIRST-SYNTHETIC", "receipt.txt")
        self.assertTrue(result["duplicate_submission"])
        record = self.workspace.show("example")
        self.assertEqual(current, record["receipt"])
        self.assertEqual([(first, "sent"), (second, "sent")], [(item["id"], item["outcome"]) for item in record["attempts"]])
        for attempt_id in (first, second):
            with self.assertRaises(WorkflowError):
                self.workspace.late_receipt("example", attempt_id, "ANOTHER-SYNTHETIC", "receipt.txt")
        self.assertTrue(self.workspace.verify()["ok"])

    def test_verify_compares_current_record_with_attempt_history(self):
        self.ready()
        self.workspace.receipt("example", self.attempt(), "SYNTHETIC", "receipt.txt")
        with self.workspace.connection(write=True) as con:
            con.execute("UPDATE jobs SET status='ready', attempt=NULL, receipt=NULL WHERE id='example'")
        result = self.workspace.verify()
        self.assertFalse(result["ok"])
        self.assertIn("example: Sent state does not match the recorded receipts", result["problems"])

    def test_profile_change_after_screening_blocks_until_rescreened(self):
        self.ready()
        with (self.workspace.root / "candidate.md").open("a") as handle:
            handle.write("\nSynthetic qualification withdrawn.\n")
        for operation in (lambda: self.workspace.attempt("example"),
                          lambda: self.workspace.preview("example", "preview.txt"),
                          lambda: self.workspace.authorize("example", "Again"),
                          lambda: self.workspace.packet("example", "cv.txt", approved=True)):
            with self.assertRaises(WorkflowError):
                operation()
        self.assertEqual(["example"], self.workspace.verify()["needs_rescreen"])
        self.workspace.screen("example", "pass", "Re-screened against the changed synthetic facts.")
        self.assertIsNone(self.row()["authorization"])
        self.assertEqual([], self.workspace.verify()["needs_rescreen"])
        self.workspace.authorize("example", "Synthetic permission after re-screening")
        self.workspace.preview("example", "preview.txt")
        self.attempt()

    def test_screening_without_profile_binding_fails_safely(self):
        self.ready()
        screening = json.loads(self.row()["screening"])
        del screening["profile"]
        with self.workspace.connection(write=True) as con:
            con.execute("UPDATE jobs SET screening=? WHERE id='example'", (json.dumps(screening),))
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")
        self.assertEqual(["example"], self.workspace.verify()["needs_rescreen"])

    def test_profile_change_during_attempt_does_not_block_resolution(self):
        self.ready()
        attempt = self.attempt()
        (self.workspace.root / "preferences.md").write_text("Synthetic: submission scope withdrawn.\n")
        self.workspace.receipt("example", attempt, "SYNTHETIC", "receipt.txt")
        self.assertTrue(self.workspace.verify()["ok"])

    def test_packet_holds_only_required_documents_and_answers(self):
        self.add()
        self.workspace.screen("example", "pass", "Synthetic match")
        (self.workspace.root / "answers.md").write_text("Synthetic approved portal answers.\n")
        (self.workspace.root / "transcript.pdf").write_bytes(b"%PDF-1.4 synthetic transcript")
        for invalid in (dict(), dict(attachments={"cv": "transcript.pdf"}), dict(attachments={"Bad Name": "transcript.pdf"}),
                        dict(answers="transcript.pdf")):
            with self.assertRaises(WorkflowError):
                self.workspace.packet("example", approved=True, **invalid)
        result = self.workspace.packet("example", "cv.txt", answers="answers.md",
                                       attachments={"transcript": "transcript.pdf"}, approved=True)
        self.assertEqual({"cv", "transcript"}, set(result["upload_paths"]))
        self.assertEqual((self.workspace.root / "answers.md").read_bytes(), Path(result["answers_path"]).read_bytes())
        self.assertEqual(result["upload_paths"], self.workspace.show("example")["upload_paths"])
        self.workspace.packet("example", "cv.txt", approved=True)
        self.workspace.authorize("example", "Synthetic permission for a CV-only portal")
        self.assertEqual(["cv"], self.workspace.preview("example", "preview.txt")["packet_contents"])
        self.workspace.receipt("example", self.attempt(), "CV-ONLY-SYNTHETIC", "receipt.txt")
        self.assertTrue(self.workspace.verify()["ok"])

    def test_list_reports_local_days_left(self):
        self.add("dated", (date.today() + timedelta(days=3)).isoformat())
        self.add("late", (date.today() - timedelta(days=1)).isoformat())
        self.add("open", "rolling")
        self.assertEqual({"dated": 3, "late": -1, "open": None},
                         {row["id"]: row["days_left"] for row in self.workspace.list()})

    def test_cli_requires_attempt_id_and_parses_attachments(self):
        def run(*arguments):
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cli_main(["--workspace", str(self.workspace.root), *arguments])
            return code, json.loads(stdout.getvalue() or stderr.getvalue())
        self.add()
        self.workspace.screen("example", "pass", "Synthetic match")
        self.assertEqual(1, run("packet", "example", "--attachment", "missing-separator", "--approved")[0])
        code, result = run("packet", "example", "--cv", "cv.txt", "--attachment", "reference=letter.txt", "--approved")
        self.assertEqual((0, {"cv", "reference"}), (code, set(result["upload_paths"])))
        self.workspace.authorize("example", "Synthetic permission")
        self.workspace.preview("example", "preview.txt")
        attempt = self.attempt()
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli_main(["--workspace", str(self.workspace.root), "receipt", "example",
                      "--reference", "SYNTHETIC", "--evidence", "receipt.txt"])
        code, _ = run("receipt", "example", "--attempt-id", attempt, "--reference", "SYNTHETIC", "--evidence", "receipt.txt")
        self.assertEqual(0, code)

    def test_invalid_second_packet_extension_leaves_no_orphan(self):
        self.add()
        self.workspace.screen("example", "pass", "Synthetic match")
        (self.workspace.root / "letter.unsupported").write_text("Synthetic letter")
        before = sorted(path.relative_to(self.workspace.root) for path in self.workspace.root.rglob("*"))
        with self.assertRaises(WorkflowError):
            self.workspace.packet("example", "cv.txt", "letter.unsupported", approved=True)
        after = sorted(path.relative_to(self.workspace.root) for path in self.workspace.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertIsNone(self.row()["packet"])

    def test_deadline_and_eligibility_gate(self):
        self.ready(deadline=(date.today() - timedelta(days=1)).isoformat())
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")
        self.workspace.screen("example", "park", "Decisive qualification still unknown.")
        with self.assertRaises(WorkflowError):
            self.workspace.packet("example", "cv.txt", "letter.txt", approved=True)

    def test_rolling_deadline_requires_explicit_current_open_assertion(self):
        self.add(deadline="rolling")
        self.workspace.screen("example", "pass", "Synthetic eligibility evidence")
        self.workspace.packet("example", "cv.txt", "letter.txt", approved=True)
        self.workspace.authorize("example", "Synthetic permission")
        with self.assertRaises(WorkflowError):
            self.workspace.preview("example", "preview.txt")
        self.workspace.preview("example", "preview.txt", vacancy_open=True)
        self.workspace.attempt("example")

    def test_unknown_deadline_blocks_and_correction_requires_revalidation(self):
        self.ready(deadline="unknown")
        with self.assertRaises(WorkflowError):
            self.workspace.attempt("example")
        self.workspace.deadline("example", "2099-12-31", "Synthetic verified deadline")
        row = self.row()
        self.assertEqual("staged", row["status"])
        for key in ("decision", "screening", "packet", "authorization", "preview"):
            self.assertIsNone(row[key])
        self.workspace.screen("example", "pass", "Revalidated after deadline correction")
        self.workspace.packet("example", "cv.txt", "letter.txt", approved=True)
        self.workspace.authorize("example", "New explicit permission")
        self.workspace.preview("example", "preview.txt")
        self.workspace.attempt("example")
        with self.assertRaises(WorkflowError):
            self.workspace.deadline("example", "rolling", "Cannot alter an active attempt")

    def test_show_exposes_decoded_resume_state(self):
        self.ready()
        self.workspace.attempt("example")
        record = self.workspace.show("example")
        self.assertIsInstance(record["packet"], dict)
        self.assertIn("path", record["packet"]["files"]["cv"])
        self.assertEqual("attempting", record["status"])
        self.assertEqual("attempt", record["events"][-1]["action"])

    def test_duplicate_identity_rejected_without_partial_event(self):
        self.add()
        with self.assertRaises(WorkflowError):
            self.add()
        with self.assertRaises(WorkflowError):
            self.workspace.add("other", "https://example.invalid/jobs/example", "Role", "Employer", "2099-12-31")
        self.assertEqual(1, len(self.workspace.list()))
        self.assertEqual(1, self.workspace.verify()["events"])

    def test_canonical_url_dedup_preserves_path_and_query_semantics(self):
        self.workspace.add("first", "HTTPS://EXAMPLE.INVALID:443/jobs/Role?source=x#preview", "Role", "Employer", "2099-12-31")
        with self.assertRaises(WorkflowError):
            self.workspace.add("second", "https://example.invalid/jobs/Role?source=x", "Role", "Employer", "2099-12-31")
        self.assertNotEqual(canonical_url("https://example.invalid/Role?a=1"), canonical_url("https://example.invalid/role?a=1"))
        self.assertNotEqual(canonical_url("https://example.invalid/role?a=1"), canonical_url("https://example.invalid/role?a=2"))

    def test_concurrent_attempts_admit_exactly_one(self):
        self.ready("first")
        self.ready("second")
        def attempt(identifier):
            try:
                Workspace(self.workspace.root).attempt(identifier)
                return "accepted"
            except WorkflowError:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("first", "second")))
        self.assertEqual(["accepted", "rejected"], sorted(results))
        self.assertEqual(1, sum(row["status"] == "attempting" for row in self.workspace.list()))

    def test_unresolved_attempt_is_immutable_across_restart(self):
        self.ready()
        self.workspace.attempt("example")
        self.workspace = Workspace(self.workspace.root)
        for operation in (
            lambda: self.workspace.screen("example", "skip", "Changed opinion"),
            lambda: self.workspace.packet("example", "cv.txt", "letter.txt", approved=True),
            lambda: self.workspace.authorize("example", "Again"),
            lambda: self.workspace.preview("example", "preview.txt"),
            lambda: self.workspace.attempt("example"),
        ):
            with self.assertRaises(WorkflowError):
                operation()
        self.assertEqual("attempting", self.row()["status"])

    def test_source_git_and_symlink_workspaces_rejected(self):
        with self.assertRaises(WorkflowError):
            Workspace(SOURCE_ROOT / "private")
        repository = self.base / "repository"
        repository.mkdir()
        (repository / ".git").write_text("gitdir: elsewhere")
        with self.assertRaises(WorkflowError):
            Workspace(repository / "private")
        (self.base / "linked").symlink_to(self.workspace.root, target_is_directory=True)
        with self.assertRaises(WorkflowError):
            Workspace(self.base / "linked")

    def test_parent_alias_allowed_but_root_and_internal_links_stay_rejected(self):
        alias = self.base / "parent-alias"
        real_parent = self.base / "actual-parent"
        real_parent.mkdir()
        alias.symlink_to(real_parent, target_is_directory=True)
        workspace = Workspace(alias / "private")
        workspace.init()
        self.assertEqual(real_parent / "private", workspace.root)
        self.assertTrue(workspace.path(alias / "private" / "candidate.md", file=True).is_file())
        (workspace.root / "linked.txt").symlink_to(workspace.root / "candidate.md")
        with self.assertRaises(WorkflowError):
            workspace.path("linked.txt", file=True)

    def test_case_alias_of_source_is_rejected_on_case_insensitive_filesystem(self):
        alias = SOURCE_ROOT.with_name(SOURCE_ROOT.name.swapcase())
        if not alias.exists() or not alias.samefile(SOURCE_ROOT):
            self.skipTest("Case-sensitive filesystem")
        with self.assertRaises(WorkflowError):
            Workspace(alias / "private")

    def test_uninitialized_workspace_error_has_init_guidance(self):
        workspace = Workspace(self.base / "not-initialized")
        with self.assertRaisesRegex(WorkflowError, "not initialized.*init"):
            workspace.list()

    def test_existing_workspace_becoming_git_repository_is_rejected(self):
        (self.workspace.root / ".git").mkdir()
        with self.assertRaises(WorkflowError):
            self.workspace.list()

    def test_outside_input_and_internal_symlink_rejected(self):
        self.add()
        self.workspace.screen("example", "pass", "Synthetic match")
        outside = self.base / "outside.txt"
        outside.write_text("Synthetic outside file")
        (self.workspace.root / "link.txt").symlink_to(outside)
        for invalid in (outside, "../outside.txt", "link.txt"):
            with self.assertRaises(WorkflowError):
                self.workspace.packet("example", invalid, "letter.txt", approved=True)
        self.assertIsNone(self.row()["packet"])

    def test_database_and_sidecar_symlinks_rejected(self):
        outside = self.base / "outside.txt"
        outside.write_text("Synthetic untouched file")
        sidecar = Path(str(self.workspace.db) + "-journal")
        sidecar.symlink_to(outside)
        with self.assertRaises(WorkflowError):
            self.workspace.list()
        self.assertEqual("Synthetic untouched file", outside.read_text())

    def test_hardlinked_material_and_database_rejected(self):
        self.add()
        self.workspace.screen("example", "pass", "Synthetic match")
        outside = self.base / "outside.txt"
        outside.write_text("Synthetic outside file")
        os.link(outside, self.workspace.root / "hardlink.txt")
        with self.assertRaises(WorkflowError):
            self.workspace.packet("example", "hardlink.txt", "letter.txt", approved=True)
        os.link(self.workspace.db, self.base / "database-link.sqlite3")
        with self.assertRaises(WorkflowError):
            self.workspace.list()

    def test_verify_rejects_unreferenced_profile_hardlink(self):
        outside = self.base / 'profile-copy.md'
        os.link(self.workspace.root / 'candidate.md', outside)
        result = self.workspace.verify()
        self.assertFalse(result['ok'])
        self.assertIn('Workspace contains a hard-linked file', result['problems'])

    def test_verify_rejects_status_decision_and_attempt_mismatches(self):
        self.ready()
        with self.workspace.connection(write=True) as con:
            con.execute("UPDATE jobs SET status='staged' WHERE id='example'")
        self.assertFalse(self.workspace.verify()["ok"])
        with self.workspace.connection(write=True) as con:
            con.execute("UPDATE jobs SET status='ready' WHERE id='example'")
        self.workspace.attempt("example")
        with self.workspace.connection(write=True) as con:
            con.execute("UPDATE jobs SET url='https://example.invalid/jobs/other' WHERE id='example'")
        self.assertFalse(self.workspace.verify()["ok"])

    def test_audit_events_reject_update_and_delete(self):
        self.add()
        with self.workspace.connection() as con:
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE events SET action='forged'")
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("DELETE FROM events")

    def test_bokmal_init_and_init_does_not_overwrite(self):
        second = Workspace(self.base / "bokmal")
        second.init("nb")
        self.assertIn("Kandidatopplysninger", (second.root / "candidate.md").read_text())
        with self.assertRaises(WorkflowError):
            second.init("en")

    def test_demo_and_cli_work_without_external_services(self):
        self.assertTrue(demo()["verification"]["ok"])
        run = subprocess.run([sys.executable, "-m", "jobkit", "demo"], cwd=SOURCE_ROOT,
                             text=True, capture_output=True)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertTrue(json.loads(run.stdout)["verification"]["ok"])
        run = subprocess.run([sys.executable, "-m", "jobkit", "list"], cwd=SOURCE_ROOT,
                             text=True, capture_output=True)
        self.assertNotEqual(0, run.returncode)


if __name__ == "__main__":
    unittest.main()
