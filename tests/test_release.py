"""Adversarial public-export tests using synthetic, temporary fixtures only."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unicodedata
import unittest
from unittest import mock

from jobkit import release


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "source"
        self.root.mkdir()
        self.output = self.base / "export"
        self.make_source({"README.md": "A synthetic public starter.\n"})

    def make_source(self, files):
        for name, data in files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(data, bytes):
                target.write_bytes(data)
            else:
                target.write_text(data, encoding="utf-8")
        self.manifest([release.MANIFEST, *files])

    def manifest(self, names):
        (self.root / release.MANIFEST).write_text(
            json.dumps({"files": names}), encoding="utf-8"
        )

    def denied_terms(self, *terms):
        target = self.base / "deny.txt"
        target.write_text("\n".join(terms) + "\n", encoding="utf-8")
        return target

    def assert_blocked(self, deny_file=None):
        with self.assertRaises(release.ReleaseError):
            release.export(self.root, self.output, deny_file)
        self.assertFalse(self.output.exists())

    def cli_check(self, deny_file=None):
        arguments = ["check"]
        if deny_file is not None:
            arguments.extend(["--deny-file", str(deny_file)])
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(release, "ROOT", self.root):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = release.main(arguments)
        return code, stdout.getvalue() + stderr.getvalue()

    def test_export_roundtrip_preserves_allowed_bytes_and_nested_hidden_config(self):
        files = {
            "README.md": "English and norsk bokmål: søknad.\n",
            "docs/nested/guide.md": "# Example\nA public guide.\n",
            ".github/workflows/check.yml": "name: checks\n",
            ".gitignore": "private/\n",
            "LICENSE": "Synthetic license fixture.\n",
        }
        self.make_source(files)
        expected = {
            name: (self.root / name).read_bytes()
            for name in [release.MANIFEST, *files]
        }
        findings, blobs = release.inspect(self.root)
        self.assertEqual(findings, [])
        self.assertEqual(blobs, expected)
        self.assertEqual(release.export(self.root, self.output), len(expected))
        actual = {
            path.relative_to(self.output).as_posix(): path.read_bytes()
            for path in self.output.rglob("*") if path.is_file()
        }
        self.assertEqual(actual, expected)
        self.assertFalse((self.output / ".git").exists())

    def test_hardlinked_public_file_is_rejected(self):
        outside = self.base / 'external.txt'
        outside.write_text('Synthetic material outside the public source.')
        (self.root / 'README.md').unlink()
        os.link(outside, self.root / 'README.md')
        self.assert_blocked()

    def test_untracked_os_metadata_is_not_exported(self):
        (self.root / '.DS_Store').write_bytes(b'\x00synthetic OS metadata')
        release.export(self.root, self.output)
        self.assertFalse((self.output / '.DS_Store').exists())

    def test_windows_drive_and_control_character_manifest_paths_rejected(self):
        for path in ('C:/outside.md', 'C:outside.md', 'docs/hidden\nname.md'):
            with self.subTest(path=repr(path)):
                with self.assertRaises(release.ReleaseError):
                    release.safe_relative(path)

    def test_export_case_alias_cannot_enter_source_tree(self):
        alias = self.root.with_name(self.root.name.swapcase())
        if not alias.exists() or not alias.samefile(self.root):
            self.skipTest('case-sensitive filesystem')
        with self.assertRaises(release.ReleaseError):
            release.export(self.root, alias / 'nested-export')
        self.assertFalse((self.root / 'nested-export').exists())

    def test_export_uses_one_manifest_snapshot_during_concurrent_save(self):
        original = release.read_regular
        captured = (self.root / release.MANIFEST).read_bytes()
        changed = False

        def read_then_change(root, name):
            nonlocal changed
            data = original(root, name)
            if name == release.MANIFEST and not changed:
                changed = True
                self.manifest([release.MANIFEST, 'README.md', 'future.md'])
            return data

        with mock.patch.object(release, 'read_regular', side_effect=read_then_change):
            release.export(self.root, self.output)
        self.assertEqual(captured, (self.output / release.MANIFEST).read_bytes())
        self.assertEqual([], release.inspect(self.output)[0])

    def test_unlisted_private_file_blocks_export_without_echoing_its_name(self):
        secret_name = "private-" + "synthetic-owner.txt"
        (self.root / secret_name).write_text("synthetic personal detail")
        findings, _ = release.inspect(self.root)
        self.assertTrue(findings)
        self.assertNotIn(secret_name, json.dumps(findings))
        self.assert_blocked()

    def test_manifest_paths_reject_traversal_absolute_and_noncanonical_forms(self):
        invalid = [
            "../outside.md", "nested/../../outside.md", "/absolute.md",
            "./README.md", "nested//guide.md", "nested/./guide.md",
            "nested/guide.md/", "nested\\guide.md", "README.md\x00",
            "", 1, None, ["README.md"], {"name": "README.md"},
        ]
        for name in invalid:
            with self.subTest(name=name):
                self.manifest([release.MANIFEST, name])
                self.assert_blocked()

    def test_manifest_rejects_duplicate_and_missing_self(self):
        for names in [
            [release.MANIFEST, "README.md", "README.md"],
            [release.MANIFEST, release.MANIFEST],
            ["README.md"], [],
        ]:
            with self.subTest(names=names):
                self.manifest(names)
                self.assert_blocked()

    def test_manifest_rejects_wrong_json_shape_and_malformed_json(self):
        for value in [[], None, {"files": "README.md"},
                      {"files": [], "extra": True}]:
            with self.subTest(value=value):
                (self.root / release.MANIFEST).write_text(json.dumps(value))
                self.assert_blocked()
        (self.root / release.MANIFEST).write_text("{broken")
        self.assert_blocked()

    def test_private_suffixes_and_path_components_are_forbidden(self):
        invalid = [
            "notes.db", "notes.SQLITE3", "cv.pdf", "cv.docx", "photo.png",
            "capture.JPG", "archive.zip", "identity.pem", "token.key",
            "events.log", "records.jsonl", "private/notes.md",
            "PRIVATE/notes.md", "applications/draft.md", "receipts/info.md",
            "portal_screenshots/index.md", "candidate_profile.md",
            "credentials.json", ".env", ".nav_token", ".git/config.md",
            ".venv/info.md", "__pycache__/info.md", "program.exe",
            "candidate.md", "docs/preferences.md", "evidence/notes.md",
            "packets/cover.md", "release-deny.txt",
        ]
        for name in invalid:
            with self.subTest(name=name):
                self.manifest([release.MANIFEST, name])
                self.assert_blocked()

    def test_binary_and_non_utf8_bytes_are_blocked_even_with_text_extension(self):
        for body in [b"public\x00hidden", b"\xff\xfeprivate"]:
            with self.subTest(body=repr(body)):
                (self.root / "README.md").write_bytes(body)
                self.assert_blocked()

    def test_oversized_public_file_is_blocked(self):
        (self.root / "README.md").write_bytes(b"a" * 1_000_001)
        self.assert_blocked()

    def test_missing_manifest_entry_and_directory_instead_of_file_block(self):
        self.manifest([release.MANIFEST, "README.md", "missing.md"])
        self.assert_blocked()
        (self.root / "missing.md").mkdir()
        self.assert_blocked()

    def test_symlink_to_public_file_is_blocked(self):
        target = self.base / "elsewhere.md"
        target.write_text("Synthetic external document.")
        (self.root / "README.md").unlink()
        (self.root / "README.md").symlink_to(target)
        self.assert_blocked()

    def test_symlink_directory_in_public_path_is_blocked(self):
        target = self.base / "elsewhere"
        target.mkdir()
        (target / "guide.md").write_text("Synthetic external guide.")
        (self.root / "docs").symlink_to(target, target_is_directory=True)
        self.manifest([release.MANIFEST, "README.md", "docs/guide.md"])
        self.assert_blocked()

    def test_unlisted_and_dangling_symlinks_block(self):
        for name, target in [("link.md", "README.md"),
                             ("broken.md", "missing.md")]:
            with self.subTest(name=name):
                link = self.root / name
                link.symlink_to(target)
                self.assert_blocked()
                link.unlink()

    def test_symlink_manifest_is_blocked(self):
        original = self.root / release.MANIFEST
        target = self.base / "manifest.json"
        target.write_bytes(original.read_bytes())
        original.unlink()
        original.symlink_to(target)
        self.assert_blocked()

    def test_deny_terms_match_content_case_insensitively_and_are_not_echoed(self):
        secret = "invented" + "-person-marker"
        deny = self.denied_terms(secret)
        (self.root / "README.md").write_text("Reference: " + secret.upper())
        self.assert_blocked(deny)
        code, output = self.cli_check(deny)
        self.assertEqual(code, 1)
        self.assertNotIn(secret.casefold(), output.casefold())
        self.assertIn("private deny term", output)

    def test_deny_terms_in_filename_are_never_echoed_with_other_findings(self):
        secret = "invented" + "-filename-marker"
        deny = self.denied_terms(secret)
        private_name = "docs/" + secret + ".md"
        self.make_source({"README.md": "Public intro.\n", private_name: secret})
        self.assert_blocked(deny)
        code, output = self.cli_check(deny)
        self.assertEqual(code, 1)
        self.assertNotIn(secret.casefold(), output.casefold())

    def test_deny_terms_in_missing_filename_are_never_echoed(self):
        secret = "invented" + "-missing-marker"
        deny = self.denied_terms(secret)
        self.manifest([release.MANIFEST, "README.md", secret + ".md"])
        code, output = self.cli_check(deny)
        self.assertEqual(code, 1)
        self.assertNotIn(secret.casefold(), output.casefold())

    def test_credential_in_filename_is_not_echoed_without_deny_file(self):
        secret = "gh" + "p_" + "z" * 36
        name = "docs/" + secret + ".md"
        self.make_source({"README.md": "Public intro.\n", name: secret})
        self.assert_blocked()
        code, output = self.cli_check()
        self.assertEqual(code, 1)
        self.assertNotIn(secret, output)

    def test_deny_file_must_be_external_and_terms_meaningful(self):
        internal = self.root / "deny.txt"
        internal.write_text("synthetic private marker")
        self.assert_blocked(internal)
        internal.unlink()
        for content in ["", " \n", "ab\n", "valid term\na\n"]:
            with self.subTest(content=content):
                deny = self.base / "deny.txt"
                deny.write_text(content)
                self.assert_blocked(deny)

    def test_credential_email_and_home_path_heuristics_block_without_echoes(self):
        secrets = [
            "gh" + "p_" + "a" * 36,
            "github" + "_pat_" + "a" * 40,
            "sk" + "-proj-" + "a" * 32,
            "sk" + "-ant-" + "a" * 32,
            "Bearer " + "a" * 30,
            "ey" + "J" + "a" * 18 + "." + "b" * 20 + "." + "c" * 20,
            "-----BEGIN " + "PRIVATE KEY-----",
            "synthetic.person" + "@" + "samplemail.dev",
            "/" + "Users/" + "synthetic-person/documents",
            "/" + "home/" + "synthetic-person/documents",
            "C:" + "\\Users\\" + "synthetic-person\\documents",
            "123456" + "12345",
            "https://notion" + ".so/" + "a" * 32,
            "collection" + "://" + "a" * 32,
            "+" + "47 " + "912 " + "34 " + "567",
            "+" + "47" + "91234567",
            "+" + "1 (555) " + "123-4567",
            "AKIA" + "Z" * 16,
            "xo" + "xb-" + "1" * 12 + "-" + "a" * 12,
            "bearer " + "a" * 30,
            "-----BEGIN " + "ENCRYPTED " + "PRIVATE KEY-----",
            "-----BEGIN " + "DSA " + "PRIVATE KEY-----",
            "https://synthetic-user" + ":" + "not-a-password" + "@example.invalid/path",
        ]
        for secret in secrets:
            with self.subTest(category=secrets.index(secret)):
                (self.root / "README.md").write_text("Synthetic fixture: " + secret)
                self.assert_blocked()
                code, output = self.cli_check()
                self.assertEqual(code, 1)
                self.assertNotIn(secret, output)

    def test_common_prose_is_not_mistaken_for_credentials(self):
        (self.root / "README.md").write_text(
            "Version 1.0.0+20260927 uses UTC+01:00. Bearer tokens and https://example.com/a:b@c are described.\n"
            "Call +47 later.\n")
        self.assertEqual([], release.inspect(self.root)[0])

    def test_deny_terms_match_bom_unicode_escapes_entities_and_line_wraps(self):
        term = "invented zq\N{LATIN SMALL LETTER A WITH RING ABOVE}v-marker"
        escaped = "invented zq" + "\\u00e5v-marker"
        variants = {
            "README.md": unicodedata.normalize("NFD", term).upper(),
            "wrapped.md": term.replace(" ", "\n  "),
            "soft.md": term.replace("zq", "z\N{SOFT HYPHEN}q"),
            "entity.md": term.replace("\N{LATIN SMALL LETTER A WITH RING ABOVE}", "&aring;"),
            "data.json": json.dumps({"note": term}),
            "tool.py": 'NOTE = "' + escaped + '"\n',
            "settings.toml": 'note = "' + escaped + '"\n',
        }
        deny = self.base / "deny.txt"
        deny.write_bytes((term + "\n").encode("utf-8-sig"))
        for name, body in variants.items():
            with self.subTest(name=name):
                self.make_source({"README.md": "Public intro.\n", name: body})
                self.assertNotIn(term, body)
                self.assert_blocked(deny)
                code, output = self.cli_check(deny)
                self.assertEqual(code, 1)
                self.assertIn("private deny term", output)
                self.assertNotIn("zq", output.casefold())
                (self.root / name).unlink()

    def test_normalized_deny_term_in_filename_is_redacted(self):
        term = "invented-zq\N{LATIN SMALL LETTER A WITH RING ABOVE}v-file"
        deny = self.denied_terms(term)
        self.make_source({"README.md": "Public intro.\n", "docs/" + unicodedata.normalize("NFD", term) + ".md": "Public."})
        code, output = self.cli_check(deny)
        self.assertEqual(code, 1)
        self.assertIn("private deny term in filename", output)
        self.assertNotIn("zq", output.casefold())

    def test_generated_build_metadata_is_ignored_and_never_exported(self):
        (self.root / "uv.lock").write_text("version = 1\n")
        (self.root / "synthetic_kit.egg-info").mkdir()
        (self.root / "synthetic_kit.egg-info" / "PKG-INFO").write_text("Name: synthetic-kit\n")
        self.assertEqual([], release.inspect(self.root)[0])
        release.export(self.root, self.output)
        self.assertEqual({"README.md", release.MANIFEST}, {path.name for path in self.output.rglob("*")})
        nested = self.root / "docs" / "nested.egg-info"
        nested.mkdir(parents=True)
        (nested / "notes.txt").write_text("Unlisted synthetic note.")
        self.assertTrue(release.inspect(self.root)[0])

    def test_unexpected_git_file_blocks(self):
        (self.root / ".git").write_text("synthetic notes, not a gitdir pointer\n")
        self.assert_blocked()

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_linked_worktree_metadata_is_accepted_but_never_exported(self):
        main = self.base / "main-repository"
        git = ["git", "-c", "user.name=Synthetic", "-c", "user.email=synthetic@example.invalid", "-c", "commit.gpgsign=false"]
        subprocess.run([*git, "init", "-q", str(main)], check=True, capture_output=True)
        subprocess.run([*git, "-C", str(main), "commit", "-q", "--allow-empty", "-m", "synthetic"], check=True, capture_output=True)
        self.root = self.base / "linked-worktree"
        subprocess.run([*git, "-C", str(main), "worktree", "add", str(self.root)], check=True, capture_output=True)
        self.assertTrue((self.root / ".git").is_file())
        self.make_source({"README.md": "A synthetic public starter.\n"})
        self.assertEqual([], release.inspect(self.root)[0])
        release.export(self.root, self.output)
        self.assertFalse((self.output / ".git").exists())

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_staged_secret_blocks_even_when_working_copy_is_clean(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True, capture_output=True)
        secret = "gh" + "p_" + "b" * 36
        (self.root / "README.md").write_text("Staged synthetic value: " + secret + "\n")
        subprocess.run(["git", "-C", str(self.root), "add", "README.md", release.MANIFEST], check=True, capture_output=True)
        (self.root / "README.md").write_text("A clean synthetic working copy.\n")
        findings, _ = release.inspect(self.root)
        self.assertIn({"file": "README.md", "line": 1, "rule": "provider token", "source": "Git index"}, findings)
        code, output = self.cli_check()
        self.assertEqual(code, 1)
        self.assertNotIn(secret, output)
        self.assert_blocked()
        subprocess.run(["git", "-C", str(self.root), "add", "README.md"], check=True, capture_output=True)
        self.assertEqual([], release.inspect(self.root)[0])
        (self.root / "README.md").write_bytes(b"\xff\xfe synthetic binary")
        subprocess.run(["git", "-C", str(self.root), "add", "README.md"], check=True, capture_output=True)
        (self.root / "README.md").write_text("A clean synthetic working copy.\n")
        self.assertEqual([{"file": "README.md", "rule": "staged content is not UTF-8 text", "source": "Git index"}],
                         release.inspect(self.root)[0])

    def test_bare_home_directory_paths_are_blocked(self):
        for number, secret in enumerate([
            "/" + "Users/" + "synthetic-person",
            "/" + "home/" + "synthetic-person",
            "C:" + "\\Users\\" + "synthetic-person",
        ]):
            with self.subTest(platform=secret[:2]):
                self.output = self.base / ("export-" + str(number))
                (self.root / "README.md").write_text("Working folder: " + secret)
                self.assert_blocked()

    def test_reserved_example_email_domains_are_allowed(self):
        for domain in ["example.com", "example.org", "example.net",
                       "example.invalid", "test.invalid"]:
            with self.subTest(domain=domain):
                (self.root / "README.md").write_text("Contact: person@" + domain)
                findings, _ = release.inspect(self.root)
                self.assertEqual(findings, [])

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_git_tracked_file_inside_excluded_directory_blocks_export(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True,
                       capture_output=True)
        cache = self.root / ".venv" / "private.txt"
        cache.parent.mkdir()
        cache.write_text("Synthetic private local content.")
        subprocess.run(["git", "-C", str(self.root), "add", "-f",
                        ".venv/private.txt"], check=True, capture_output=True)
        findings, _ = release.inspect(self.root)
        self.assertTrue(any(item["rule"] == "tracked file outside public manifest"
                            for item in findings))
        self.assert_blocked()

    def test_ignored_untracked_cache_is_not_copied(self):
        cache = self.root / "__pycache__"
        cache.mkdir()
        (cache / "module.pyc").write_bytes(b"\x00cache")
        release.export(self.root, self.output)
        self.assertFalse((self.output / "__pycache__").exists())

    def test_existing_target_is_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("keep me")
        self.assert_blocked_existing_target()
        self.assertEqual(sentinel.read_text(), "keep me")

    def assert_blocked_existing_target(self):
        with self.assertRaises(release.ReleaseError):
            release.export(self.root, self.output)

    def test_existing_file_and_dangling_symlink_targets_are_preserved(self):
        self.output.write_text("keep me")
        self.assert_blocked_existing_target()
        self.assertEqual(self.output.read_text(), "keep me")
        self.output.unlink()
        self.output.symlink_to(self.base / "missing-target")
        self.assert_blocked_existing_target()
        self.assertTrue(self.output.is_symlink())
        self.assertFalse((self.base / "missing-target").exists())

    def test_export_inside_source_is_rejected(self):
        for target in [self.root, self.root / "release",
                       self.root / "nested" / "release"]:
            with self.subTest(target=target.name):
                with self.assertRaises(release.ReleaseError):
                    release.export(self.root, target)

    def test_export_copies_validated_snapshot_if_source_changes_after_inspection(self):
        original_inspect = release.inspect
        expected = (self.root / "README.md").read_bytes()

        def inspect_then_mutate(*args, **kwargs):
            result = original_inspect(*args, **kwargs)
            (self.root / "README.md").write_text("Changed after validation.")
            return result

        with mock.patch.object(release, "inspect", side_effect=inspect_then_mutate):
            release.export(self.root, self.output)
        self.assertEqual((self.output / "README.md").read_bytes(), expected)

    def test_export_rechecks_destination_created_during_inspection(self):
        original_inspect = release.inspect

        def inspect_then_create_target(*args, **kwargs):
            result = original_inspect(*args, **kwargs)
            self.output.mkdir()
            (self.output / "keep.txt").write_text("keep me")
            return result

        with mock.patch.object(release, "inspect", side_effect=inspect_then_create_target):
            self.assert_blocked_existing_target()
        self.assertEqual((self.output / "keep.txt").read_text(), "keep me")
        self.assertEqual(list(self.base.glob(".jobkit-export-*")), [])


if __name__ == "__main__":
    unittest.main()
