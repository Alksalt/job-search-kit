"""Small transactional workflow, using only the Python standard library.

Evidence is an operator declaration backed by saved bytes. Hashes detect changes;
they cannot establish the truth of a portal receipt or of a candidate's claims.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import tempfile
from urllib.parse import urlsplit, urlunsplit
import uuid


SOURCE_ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")
PREVIEW_MAX_AGE_SECONDS = 3600
# Screening binds to these files; any edit requires a fresh screening before sending.
PROFILE_FILES = ("candidate.md", "preferences.md")
UPLOAD_SUFFIXES = (".md", ".txt", ".pdf", ".docx", ".doc", ".odt", ".rtf", ".png", ".jpg", ".jpeg")
ANSWER_SUFFIXES = (".md", ".txt")
ATTACHMENT_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}\Z")


class WorkflowError(Exception):
    """A rejected command with no authorized state transition."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise WorkflowError(f"{label} must be non-empty text")
    return value.strip()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_url(value):
    """Normalize transport identity, never infer cross-source vacancy identity."""
    parsed = urlsplit(_text(value, "URL"))
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise WorkflowError("Vacancy URL must be HTTP(S), with no credentials")
    host = parsed.hostname.lower()
    if any(char.isspace() for char in host):
        raise WorkflowError("Vacancy URL has an invalid host")
    try:
        port = parsed.port
    except ValueError:
        raise WorkflowError("Vacancy URL has an invalid port") from None
    if ":" in host:
        host = f"[{host}]"
    if port is not None and (parsed.scheme, port) not in (("http", 80), ("https", 443)):
        host += f":{port}"
    return urlunsplit((parsed.scheme, host, parsed.path or "/", parsed.query, ""))


def valid_deadline(value):
    if value in ("rolling", "unknown"):
        return value
    try:
        if date.fromisoformat(value).isoformat() == value:
            return value
    except (TypeError, ValueError):
        pass
    raise WorkflowError("Deadline must be YYYY-MM-DD, rolling or unknown")


def _no_symlinks(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise WorkflowError("Symlink paths are not allowed")
    return path


def _private_dir(path):
    _no_symlinks(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise WorkflowError("Expected a directory")
    path.chmod(0o700)


def _write_new(path, data):
    """Exclusive files in fresh generations prevent replacing old evidence."""
    _no_symlinks(path)
    _private_dir(path.parent)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


class Workspace:
    def __init__(self, root):
        self.input_root = Path(os.path.abspath(Path(root).expanduser()))
        if self.input_root.is_symlink():
            raise WorkflowError("The workspace root must not be a symlink")
        # Platform aliases above the workspace (for example a temporary-directory
        # alias) are fine. Root and internal symlinks remain forbidden.
        self.root = self.input_root.parent.resolve() / self.input_root.name
        inside_source = any(part.exists() and part.samefile(SOURCE_ROOT) for part in (self.root, *self.root.parents))
        contains_source = self.root.exists() and any(part.samefile(self.root) for part in (SOURCE_ROOT, *SOURCE_ROOT.parents))
        if inside_source or contains_source:
            raise WorkflowError("Keep the private workspace separate from the source directory")
        for parent in (self.root, *self.root.parents):
            if (parent / ".git").exists() or (parent / ".git").is_symlink():
                raise WorkflowError("Private workspaces cannot be inside a Git repository or worktree")
        self.db = self.root / "state.sqlite3"

    def path(self, value, *, file=False):
        path = Path(value).expanduser()
        if path.is_absolute() and path.is_relative_to(self.input_root):
            path = self.root / path.relative_to(self.input_root)
        path = _no_symlinks(path if path.is_absolute() else self.root / path)
        if not path.is_relative_to(self.root) or path == self.root:
            raise WorkflowError("Input paths must be inside the private workspace")
        if file and (not path.is_file() or not stat.S_ISREG(path.stat().st_mode)):
            raise WorkflowError("Evidence and material inputs must be regular files")
        if path.exists() and path.is_file() and path.stat().st_nlink != 1:
            raise WorkflowError("Hard-linked private files are not allowed")
        return path

    def _read(self, value):
        path = self.path(value, file=True)
        data = path.read_bytes()
        if not data:
            raise WorkflowError("Evidence and material files must not be empty")
        return data, path.relative_to(self.root).as_posix()

    @contextmanager
    def connection(self, *, write=False):
        # Repeat boundary checks: a previously valid workspace may have moved or
        # become a Git repository since this object was created.
        Workspace(self.root)
        if not self.db.exists() and not self.db.is_symlink():
            raise WorkflowError("Workspace is not initialized; run jobkit --workspace PATH init --language en (or nb)")
        self.path(self.db, file=True)
        for suffix in ("-journal", "-wal", "-shm"):
            self.path(str(self.db) + suffix)
        con = sqlite3.connect(self.db, timeout=10, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA foreign_keys=ON")
            if con.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise WorkflowError("Unsupported workspace schema")
            if write:
                con.execute("BEGIN IMMEDIATE")
            yield con
            if write:
                con.commit()
        except BaseException:
            if con.in_transaction:
                con.rollback()
            raise
        finally:
            con.close()

    def init(self, language="en"):
        if language not in ("en", "nb"):
            raise WorkflowError("Language must be en or nb")
        if self.root.exists() and any(self.root.iterdir()):
            raise WorkflowError("Initialize an empty private directory")
        _private_dir(self.root)
        _write_new(self.db, b"")
        con = sqlite3.connect(self.db)
        try:
            con.executescript("""
                PRAGMA foreign_keys=ON;
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE jobs (
                    id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL, employer TEXT NOT NULL, deadline TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'staged'
                        CHECK(status IN ('staged','ready','parked','skipped','attempting','sent')),
                    decision TEXT CHECK(decision IN ('pass','park','skip')),
                    screening TEXT, packet TEXT, authorization TEXT, preview TEXT,
                    attempt TEXT, receipt TEXT
                );
                CREATE TABLE events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurred_at TEXT NOT NULL, job_id TEXT REFERENCES jobs(id),
                    action TEXT NOT NULL, payload TEXT NOT NULL
                );
                CREATE UNIQUE INDEX one_unresolved_attempt ON jobs(status) WHERE status='attempting';
                CREATE TRIGGER events_no_update BEFORE UPDATE ON events
                    BEGIN SELECT RAISE(ABORT, 'Audit events cannot be changed'); END;
                CREATE TRIGGER events_no_delete BEFORE DELETE ON events
                    BEGIN SELECT RAISE(ABORT, 'Audit events cannot be deleted'); END;
                PRAGMA user_version=1;
            """)
            con.execute("INSERT INTO metadata VALUES ('language', ?)", (language,))
            con.commit()
        finally:
            con.close()
        templates = {
            "en": ("# Candidate facts\n\nRecord only verified facts you choose to use. Leave unknown facts blank.\n\n## Contact details\n\n## Experience\n\n## Education and qualifications\n\n## Languages\n\n## Evidence and verification dates\n",
                   "# Job preferences\n\n## Target roles\n\n## Locations and work arrangements\n\n## Hard requirements\n\n## Preferred conditions\n\n## Application language\n\n## Submission scope\n\nNo submission authorization is implied by this template.\n"),
            "nb": ("# Kandidatopplysninger\n\nRegistrer bare bekreftede opplysninger du ønsker å bruke. La ukjente opplysninger stå åpne.\n\n## Kontaktopplysninger\n\n## Arbeidserfaring\n\n## Utdanning og kvalifikasjoner\n\n## Språk\n\n## Dokumentasjon og kontrolldatoer\n",
                   "# Jobbønsker\n\n## Aktuelle roller\n\n## Steder og arbeidsordninger\n\n## Ufravikelige krav\n\n## Ønskede vilkår\n\n## Søknadsspråk\n\n## Tillatelse til innsending\n\nDenne malen gir ingen tillatelse til å sende søknader.\n"),
        }
        for name, content in zip(("candidate.md", "preferences.md"), templates[language]):
            _write_new(self.root / name, content.encode())
        return {"initialized": True, "language": language, "workspace": str(self.root)}

    def _job(self, con, identifier):
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise WorkflowError("ID must contain 1–64 ASCII letters, digits, hyphens or underscores")
        row = con.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if row is None:
            raise WorkflowError("Unknown vacancy ID")
        return dict(row)

    @staticmethod
    def _editable(row):
        if row["status"] in ("attempting", "sent"):
            raise WorkflowError("Attempted or sent records are immutable; reconcile uncertain attempts")

    @staticmethod
    def _event(con, identifier, action, payload):
        con.execute("INSERT INTO events(occurred_at,job_id,action,payload) VALUES (?,?,?,?)",
                    (now(), identifier, action, _json(payload)))

    def _update(self, con, identifier, action, payload, **fields):
        names = ",".join(f"{name}=?" for name in fields)
        con.execute(f"UPDATE jobs SET {names} WHERE id=?", (*fields.values(), identifier))
        self._event(con, identifier, action, payload)
        return {"id": identifier, "action": action, "status": self._job(con, identifier)["status"]}

    def add(self, identifier, url, title, employer, deadline):
        if not IDENTIFIER.fullmatch(identifier):
            raise WorkflowError("Invalid vacancy ID")
        url = canonical_url(url)
        deadline = valid_deadline(deadline)
        record = dict(id=identifier, url=url, title=_text(title, "Title"),
                      employer=_text(employer, "Employer"), deadline=deadline)
        with self.connection(write=True) as con:
            try:
                con.execute("INSERT INTO jobs(id,url,title,employer,deadline) VALUES (:id,:url,:title,:employer,:deadline)", record)
            except sqlite3.IntegrityError:
                raise WorkflowError("Vacancy ID or URL already exists") from None
            self._event(con, identifier, "add", record)
        return {**record, "status": "staged"}

    def _profile(self):
        try:
            return {name: _digest(self._read(name)[0]) for name in PROFILE_FILES}
        except (WorkflowError, OSError):
            raise WorkflowError("candidate.md and preferences.md must be non-empty regular files in the workspace") from None

    def _require_current_profile(self, row):
        # Screenings recorded before profile binding have no hashes and fail safely.
        screening = json.loads(row["screening"]) if row["screening"] else {}
        if screening.get("profile") != self._profile():
            raise WorkflowError("candidate.md or preferences.md changed after screening, or the screening predates this check; "
                                "screen again, then record authorization and a fresh preview")

    def screen(self, identifier, decision, evidence):
        if decision not in ("pass", "park", "skip"):
            raise WorkflowError("Decision must be pass, park or skip")
        evidence = _text(evidence, "Screening evidence")
        with self.connection(write=True) as con:
            self._editable(self._job(con, identifier))
            receipt = {"decision": decision, "evidence": evidence, "at": now(), "profile": self._profile()}
            return self._update(con, identifier, "screen", receipt, decision=decision,
                                screening=_json(receipt), status={"pass": "ready", "park": "parked", "skip": "skipped"}[decision],
                                authorization=None, preview=None)

    def deadline(self, identifier, value, evidence):
        value = valid_deadline(value)
        change = {"deadline": value, "evidence": _text(evidence, "Deadline evidence"), "at": now()}
        with self.connection(write=True) as con:
            row = self._job(con, identifier)
            self._editable(row)
            change["previous"] = row["deadline"]
            return self._update(con, identifier, "deadline", change, deadline=value, status="staged", decision=None,
                                screening=None, packet=None, authorization=None, preview=None)

    def _check_files(self, records):
        for record in records:
            data, _ = self._read(record["path"])
            if _digest(data) != record["sha256"]:
                raise WorkflowError("Saved material or evidence changed; prepare and check a fresh packet")

    def _packet(self, row):
        if not row["packet"]:
            raise WorkflowError("An approved packet is required")
        packet = json.loads(row["packet"])
        self._check_files(packet["files"].values())
        return packet

    def _snapshot(self, identifier, kind, source):
        data, relative = self._read(source)
        target = self.root / "evidence" / identifier / uuid.uuid4().hex / f"{kind}.evidence"
        _write_new(target, data)
        return {"path": target.relative_to(self.root).as_posix(), "sha256": _digest(data),
                "source": {"path": relative, "sha256": _digest(data)}}

    def _paths(self, packet):
        paths = {kind: str(self.root / record["path"]) for kind, record in packet["files"].items()}
        answers = paths.pop("answers", None)
        return {"upload_paths": paths, **({"answers_path": answers} if answers else {})}

    def packet(self, identifier, cv=None, letter=None, *, answers=None, attachments=None, approved=False):
        """Register exactly the approved material a portal requires: any documents, form answers or both."""
        if not approved:
            raise WorkflowError("Use --approved only for material the user has approved")
        attachments = dict(attachments or {})
        if any(not isinstance(name, str) or not ATTACHMENT_NAME.fullmatch(name) or name in ("cv", "letter", "answers")
               for name in attachments):
            raise WorkflowError("Attachment names must be 1–32 lowercase letters, digits, hyphens or underscores, "
                                "other than cv, letter or answers")
        documents = {kind: path for kind, path in {"cv": cv, "letter": letter, "answers": answers, **attachments}.items()
                     if path is not None}
        if not documents:
            raise WorkflowError("Register at least one approved document or approved answers file")
        with self.connection(write=True) as con:
            row = self._job(con, identifier)
            self._editable(row)
            if row["decision"] != "pass":
                raise WorkflowError("Eligibility must pass before preparing a packet")
            self._require_current_profile(row)
            inputs = {kind: self._read(path) for kind, path in documents.items()}
            for kind, (_, relative) in inputs.items():
                if Path(relative).suffix.lower() not in (ANSWER_SUFFIXES if kind == "answers" else UPLOAD_SUFFIXES):
                    raise WorkflowError("Answers must be Markdown or text; documents must be " + ", ".join(UPLOAD_SUFFIXES))
            generation = uuid.uuid4().hex
            packet = {"generation": generation, "files": {}, "sources": {}}
            for kind, (data, relative) in inputs.items():
                # The original extension is retained for portal upload, without
                # exposing source names in the managed filename.
                suffix = Path(relative).suffix.lower()
                target = self.root / "packets" / identifier / generation / (kind + suffix)
                _write_new(target, data)
                packet["files"][kind] = {"path": target.relative_to(self.root).as_posix(), "sha256": _digest(data)}
                packet["sources"][kind] = {"path": relative, "sha256": _digest(data)}
            result = self._update(con, identifier, "packet", packet, packet=_json(packet), authorization=None, preview=None)
            return {**result, "files": packet["files"], **self._paths(packet)}

    def authorize(self, identifier, note):
        permission = {"note": _text(note, "Authorization note"), "at": now(), "vacancy_id": identifier}
        with self.connection(write=True) as con:
            row = self._job(con, identifier)
            self._editable(row)
            if row["decision"] != "pass":
                raise WorkflowError("Eligibility must pass before authorization")
            self._require_current_profile(row)
            packet = self._packet(row)
            permission["packet_sha256"] = _digest(_json(packet).encode())
            return self._update(con, identifier, "authorize", permission, authorization=_json(permission), preview=None)

    def preview(self, identifier, evidence, *, vacancy_open=False):
        with self.connection(write=True) as con:
            row = self._job(con, identifier)
            self._editable(row)
            packet = self._packet(row)
            if row["decision"] != "pass" or not row["authorization"]:
                raise WorkflowError("Pass and scoped authorization are required before the preview check")
            self._require_current_profile(row)
            if row["deadline"] == "rolling" and not vacancy_open:
                raise WorkflowError("Rolling vacancies require --vacancy-open after checking the live vacancy")
            preview = self._snapshot(identifier, "preview", evidence)
            preview["packet_sha256"] = _digest(_json(packet).encode())
            preview["at"] = now()
            preview["vacancy_open"] = bool(vacancy_open)
            # Echo what the complete portal preview must show: these files and answers, nothing else.
            return {**self._update(con, identifier, "preview", preview, preview=_json(preview)),
                    "packet_contents": sorted(packet["files"])}

    def attempt(self, identifier):
        with self.connection(write=True) as con:
            row = self._job(con, identifier)
            self._editable(row)
            if con.execute("SELECT 1 FROM jobs WHERE status='attempting'").fetchone():
                raise WorkflowError("Reconcile the unresolved attempt before another submission")
            deadline = valid_deadline(row["deadline"])
            if row["decision"] != "pass" or deadline == "unknown" or (deadline != "rolling" and date.fromisoformat(deadline) < date.today()):
                raise WorkflowError("A current eligibility pass and unexpired deadline are required")
            self._require_current_profile(row)
            packet = self._packet(row)
            if not row["authorization"] or not row["preview"]:
                raise WorkflowError("Scoped authorization and a fresh actual portal preview are required")
            permission, preview = json.loads(row["authorization"]), json.loads(row["preview"])
            if deadline == "rolling" and not preview.get("vacancy_open"):
                raise WorkflowError("The fresh preview must confirm that the rolling vacancy is open")
            try:
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(preview["at"])).total_seconds()
            except (ValueError, TypeError):
                raise WorkflowError("Preview time is invalid; check and record a fresh preview") from None
            if age < 0 or age > PREVIEW_MAX_AGE_SECONDS:
                raise WorkflowError("Preview is older than one hour or has a future timestamp; record a fresh preview")
            packet_hash = _digest(_json(packet).encode())
            if permission["packet_sha256"] != packet_hash or preview["packet_sha256"] != packet_hash:
                raise WorkflowError("Authorization or preview belongs to another packet")
            self._check_files((preview,))
            attempt = {"id": uuid.uuid4().hex, "at": now(), "packet": packet,
                       "preview": preview, "authorization": permission, "url": row["url"],
                       "deadline": row["deadline"], "screening": json.loads(row["screening"])}
            result = self._update(con, identifier, "attempt", attempt, status="attempting", attempt=_json(attempt))
            return {**result, "attempt_id": attempt["id"],
                    "instruction": "Click Send once; then record the real receipt or reconcile uncertainty with this --attempt-id."}

    def _attempt_integrity(self, attempt):
        problems = []
        for label, records in (("packet", attempt["packet"]["files"].values()), ("preview", (attempt["preview"],))):
            for record in records:
                try:
                    self._check_files((record,))
                except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
                    problems.append(f"{label}: {exc}")
        return problems

    @staticmethod
    def _attempts(con, identifier):
        """Per-attempt outcomes derived from the append-only event log, oldest first."""
        history = {}
        for event in con.execute("SELECT action,payload FROM events WHERE job_id=? AND action IN "
                                 "('attempt','receipt','reconcile','late-receipt') ORDER BY sequence", (identifier,)):
            payload = json.loads(event["payload"])
            if event["action"] == "attempt":
                history[payload["id"]] = {"attempt": payload, "outcome": "unresolved", "receipts": []}
                continue
            entry = history.get(payload.get("attempt_id"))
            if entry is None:
                raise WorkflowError("Event history contains a resolution without its attempt")
            if payload["outcome"] == "sent":
                entry["receipts"].append(payload)
            entry["outcome"] = "sent" if entry["receipts"] else payload["outcome"]
        return history

    def _resolution(self, identifier, attempt, outcome, evidence, reference, extra_problems=()):
        # A real outcome must be recordable after Send even when an old upload or
        # preview has been lost. Keep the original references and report drift.
        problems = [*extra_problems, *self._attempt_integrity(attempt)]
        return {"outcome": outcome, "reference": reference, "evidence": self._snapshot(identifier, "receipt", evidence),
                "attempt_id": attempt["id"], "at": now(), "integrity_problems": problems}

    def _record_resolution(self, con, identifier, attempt, outcome, evidence, reference, action, *, extra_problems=()):
        result = self._resolution(identifier, attempt, outcome, evidence, reference, extra_problems)
        problems = result["integrity_problems"]
        if outcome == "sent":
            response = self._update(con, identifier, action, result, status="sent", receipt=_json(result),
                                    decision="pass", screening=_json(attempt["screening"]), deadline=attempt["deadline"],
                                    packet=_json(attempt["packet"]), preview=_json(attempt["preview"]),
                                    authorization=_json(attempt["authorization"]), attempt=_json(attempt))
        else:
            response = self._update(con, identifier, action, result, status="ready", packet=None,
                                    authorization=None, preview=None, attempt=None, receipt=None)
        return {**response, "integrity_problems": problems}

    def _resolve(self, identifier, attempt_id, outcome, evidence, reference=None, *, action="reconcile"):
        if outcome not in ("sent", "not-sent"):
            raise WorkflowError("Outcome must be sent or not-sent")
        attempt_id = _text(attempt_id, "Attempt ID")
        if outcome == "sent":
            reference = _text(reference, "Receipt reference")
        elif reference is not None:
            raise WorkflowError("A not-sent outcome must not include a receipt reference")
        with self.connection(write=True) as con:
            row = self._job(con, identifier)
            if row["status"] != "attempting" or not row["attempt"]:
                raise WorkflowError("Only an unresolved attempt can receive a receipt or reconciliation")
            attempt = json.loads(row["attempt"])
            # Checked before any evidence is copied, so a stale or wrong ID changes nothing.
            if attempt["id"] != attempt_id:
                raise WorkflowError("Attempt ID is not this vacancy's unresolved attempt; nothing was recorded. Resolve the "
                                    "unresolved attempt with its own evidence; use late-receipt for an earlier attempt")
            problems = []
            try:
                if json.loads(row["packet"]) != attempt["packet"]:
                    problems.append("Stored packet record differs from the attempt snapshot")
            except (ValueError, TypeError):
                problems.append("Stored packet record is missing or malformed")
            return self._record_resolution(con, identifier, attempt, outcome, evidence, reference, action, extra_problems=problems)

    def receipt(self, identifier, attempt_id, reference, evidence):
        return self._resolve(identifier, attempt_id, "sent", evidence, reference, action="receipt")

    def reconcile(self, identifier, attempt_id, outcome, evidence, reference=None):
        return self._resolve(identifier, attempt_id, outcome, evidence, reference)

    def late_receipt(self, identifier, attempt_id, reference, evidence):
        """Append a real receipt for an attempt of this vacancy previously reconciled not-sent.

        Other vacancies are untouched. The vacancy becomes sent, which blocks another
        attempt; if it was already sent through a newer attempt, the receipt is added
        to history as a duplicate submission and the current sent record is kept.
        """
        reference = _text(reference, "Receipt reference")
        attempt_id = _text(attempt_id, "Attempt ID")
        with self.connection(write=True) as con:
            row = self._job(con, identifier)
            if row["status"] == "attempting":
                raise WorkflowError("Resolve this vacancy's unresolved attempt with its own evidence before a late receipt")
            history = self._attempts(con, identifier)
            entry = history.get(attempt_id)
            if entry is None or entry["outcome"] != "not-sent":
                raise WorkflowError("Late receipt must identify an attempt of this vacancy that was reconciled not-sent")
            if any(receipt["reference"].casefold() == reference.casefold()
                   for other in history.values() for receipt in other["receipts"]):
                raise WorkflowError("This receipt reference is already recorded for this vacancy; record each receipt once")
            if row["status"] != "sent":
                return self._record_resolution(con, identifier, entry["attempt"], "sent", evidence, reference, "late-receipt")
            result = self._resolution(identifier, entry["attempt"], "sent", evidence, reference)
            result["also_sent_attempt"] = json.loads(row["attempt"])["id"]
            self._event(con, identifier, "late-receipt", result)
            return {"id": identifier, "action": "late-receipt", "status": "sent", "duplicate_submission": True,
                    "integrity_problems": result["integrity_problems"]}

    def list(self):
        with self.connection() as con:
            rows = [dict(row) for row in con.execute("SELECT id,url,title,employer,deadline,status,decision FROM jobs ORDER BY deadline,id")]
        # Local calendar days; negative means overdue. Rolling and unknown deadlines have none.
        for row in rows:
            row["days_left"] = (None if row["deadline"] in ("rolling", "unknown")
                                else (date.fromisoformat(row["deadline"]) - date.today()).days)
        return rows

    def show(self, identifier):
        with self.connection() as con:
            row = self._job(con, identifier)
            for key in ("screening", "packet", "authorization", "preview", "attempt", "receipt"):
                row[key] = json.loads(row[key]) if row[key] else None
            if row["packet"]:
                row.update(self._paths(row["packet"]))
            try:
                row["attempts"] = [{"id": attempt_id, "at": entry["attempt"]["at"], "outcome": entry["outcome"],
                                    "receipt_references": [receipt["reference"] for receipt in entry["receipts"]]}
                                   for attempt_id, entry in self._attempts(con, identifier).items()]
            except (WorkflowError, ValueError, KeyError, TypeError):
                row["attempts"] = None  # Damaged history; verify reports the problem.
            row["events"] = [{**dict(event), "payload": json.loads(event["payload"])} for event in
                             con.execute("SELECT sequence,occurred_at,action,payload FROM events WHERE job_id=? ORDER BY sequence", (identifier,))]
            return row

    def verify(self):
        problems = []
        for base, dirs, files in os.walk(self.root, followlinks=False):
            if any((Path(base) / name).is_symlink() for name in dirs + files):
                problems.append("Workspace contains a symlink")
            if any(not (Path(base) / name).is_symlink()
                   and (Path(base) / name).is_file()
                   and (Path(base) / name).stat().st_nlink != 1 for name in files):
                problems.append("Workspace contains a hard-linked file")
        needs_rescreen = []
        with self.connection() as con:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                problems.append("SQLite integrity check failed")
            try:
                profile = self._profile()
            except WorkflowError as exc:
                profile = None
                problems.append(str(exc))
            rows = [dict(row) for row in con.execute("SELECT * FROM jobs")]
            if sum(row["status"] == "attempting" for row in rows) > 1:
                problems.append("Multiple unresolved attempts")
            for row in rows:
                try:
                    valid_deadline(row["deadline"])
                    expected_decision = {"staged": None, "ready": "pass", "parked": "park", "skipped": "skip",
                                         "attempting": "pass", "sent": "pass"}
                    if row["status"] not in expected_decision or row["decision"] != expected_decision[row["status"]]:
                        raise WorkflowError("Status and eligibility decision are inconsistent")
                    if row["decision"] is not None:
                        if not row["screening"] or json.loads(row["screening"])["decision"] != row["decision"]:
                            raise WorkflowError("Decision lacks matching screening evidence")
                    if row["status"] == "staged" and any(row[field] for field in ("screening", "packet", "authorization", "preview", "attempt", "receipt")):
                        raise WorkflowError("Staged vacancy contains later workflow records")
                    if row["status"] not in ("attempting", "sent") and row["attempt"]:
                        raise WorkflowError("Attempt exists outside attempted or sent state")
                    if row["status"] in ("parked", "skipped") and (row["authorization"] or row["preview"]):
                        raise WorkflowError("Blocked vacancy contains active authorization or preview")
                    if row["packet"]:
                        self._packet(row)
                    if row["authorization"]:
                        authorization = json.loads(row["authorization"])
                        if (not row["packet"] or authorization["vacancy_id"] != row["id"]
                                or authorization["packet_sha256"] != _digest(row["packet"].encode())):
                            raise WorkflowError("Authorization is not bound to the current vacancy and packet")
                    if row["preview"]:
                        if not row["authorization"] or json.loads(row["preview"])["packet_sha256"] != _digest(row["packet"].encode()):
                            raise WorkflowError("Preview is not bound to an authorized current packet")
                    for name in ("preview", "receipt"):
                        if row[name]:
                            record = json.loads(row[name])
                            self._check_files((record["evidence"] if name == "receipt" else record,))
                    if row["status"] in ("attempting", "sent"):
                        if not all(row[field] for field in ("packet", "authorization", "preview", "attempt")):
                            raise WorkflowError("Incomplete attempt records")
                        attempt = json.loads(row["attempt"])
                        if (attempt["packet"] != json.loads(row["packet"]) or attempt["preview"] != json.loads(row["preview"])
                                or attempt["authorization"] != json.loads(row["authorization"]) or attempt["url"] != row["url"]):
                            raise WorkflowError("Attempt does not match packet, preview, authorization and vacancy")
                    if row["status"] == "sent":
                        if not row["receipt"] or json.loads(row["receipt"])["attempt_id"] != json.loads(row["attempt"])["id"]:
                            raise WorkflowError("Sent state lacks matching receipt")
                        receipt = json.loads(row["receipt"])
                        if receipt["outcome"] != "sent" or not _text(receipt["reference"], "Receipt reference"):
                            raise WorkflowError("Sent state lacks a confirmed receipt reference")
                    elif row["receipt"]:
                        raise WorkflowError("Unexpected receipt outside sent state")
                    # The current row must agree with the append-only per-attempt history.
                    history = self._attempts(con, row["id"])
                    current = json.loads(row["attempt"]) if row["attempt"] else None
                    unresolved = [key for key, entry in history.items() if entry["outcome"] == "unresolved"]
                    if unresolved != ([current["id"]] if current and row["status"] == "attempting" else []):
                        raise WorkflowError("Unresolved attempt state does not match the event history")
                    if (row["status"] == "sent") != any(entry["outcome"] == "sent" for entry in history.values()):
                        raise WorkflowError("Sent state does not match the recorded receipts")
                    if current and (current["id"] not in history or history[current["id"]]["attempt"] != current or (
                            row["status"] == "sent" and json.loads(row["receipt"]) not in history[current["id"]]["receipts"])):
                        raise WorkflowError("Attempt or receipt record differs from the event history")
                    if profile and row["status"] in ("ready", "parked") and json.loads(row["screening"]).get("profile") != profile:
                        needs_rescreen.append(row["id"])
                except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
                    problems.append(f"{row['id']}: {exc}")
            # Old generations remain evidence after a not-sent reconciliation.
            for event in con.execute("SELECT action,payload FROM events"):
                try:
                    payload = json.loads(event["payload"])
                    if event["action"] == "packet":
                        self._check_files(payload["files"].values())
                    elif event["action"] in ("receipt", "reconcile", "late-receipt"):
                        self._check_files((payload["evidence"],))
                        if payload.get("integrity_problems"):
                            problems.append(f"Historical {event['action']}: recorded evidence integrity problems")
                    elif event["action"] == "preview":
                        self._check_files((payload,))
                except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
                    problems.append(f"Historical {event['action']}: {exc}")
            event_count = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        # Not corruption: vacancies screened before candidate.md or preferences.md last changed.
        return {"ok": not problems, "jobs": len(rows), "events": event_count, "problems": problems,
                "needs_rescreen": sorted(needs_rescreen)}


def demo():
    """Entirely synthetic; temporary files are removed on completion."""
    with tempfile.TemporaryDirectory(prefix="jobkit-demo-") as directory:
        workspace = Workspace(Path(directory).resolve())
        workspace.init()
        for filename, content in {"cv.txt": "Synthetic CV. No real candidate.",
                                  "letter.txt": "Synthetic application for a fictional vacancy.",
                                  "preview.txt": "Synthetic preview: fictional vacancy; two correct files.",
                                  "receipt.txt": "Synthetic receipt DEMO-ONLY; no external submission."}.items():
            _write_new(workspace.root / filename, content.encode())
        workspace.add("demo-role", "https://example.invalid/jobs/demo", "Example role", "Fictional employer", "2099-12-31")
        workspace.screen("demo-role", "pass", "Synthetic facts meet fictional requirements.")
        workspace.packet("demo-role", "cv.txt", "letter.txt", approved=True)
        workspace.authorize("demo-role", "Synthetic demo authorization only.")
        workspace.preview("demo-role", "preview.txt")
        attempt_id = workspace.attempt("demo-role")["attempt_id"]
        workspace.receipt("demo-role", attempt_id, "DEMO-ONLY", "receipt.txt")
        return {"demo": "synthetic; no network or portal actions; temporary workspace removed", "verification": workspace.verify()}
