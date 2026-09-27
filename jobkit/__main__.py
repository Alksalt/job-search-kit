"""Command-line interface. Run from the public source, store data elsewhere."""
import argparse
import json
import sqlite3
import sys

from .core import WorkflowError, Workspace, demo


def parser():
    cli = argparse.ArgumentParser(description="Local job workflow records. Never submits to a portal itself.")
    cli.add_argument("--workspace", help="Private directory outside source and all Git worktrees")
    commands = cli.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Initialize an empty private workspace")
    init.add_argument("--language", choices=("en", "nb"), default="en")
    add = commands.add_parser("add", help="Stage a vacancy")
    for name in ("id", "url", "title", "employer", "deadline"):
        add.add_argument("--" + name, required=True)
    screen = commands.add_parser("screen", help="Record evidence-based eligibility")
    screen.add_argument("id")
    screen.add_argument("--decision", choices=("pass", "park", "skip"), required=True)
    screen.add_argument("--evidence", required=True, help="Evidence summary, not a filename")
    deadline = commands.add_parser("deadline", help="Correct a deadline and require fresh screening and preparation")
    deadline.add_argument("id")
    deadline.add_argument("--value", required=True, help="YYYY-MM-DD, rolling or unknown")
    deadline.add_argument("--evidence", required=True, help="Evidence summary, not a filename")
    packet = commands.add_parser("packet", help="Copy the approved documents and answers a portal requires, invalidating previous checks")
    packet.add_argument("id")
    packet.add_argument("--cv")
    packet.add_argument("--letter")
    packet.add_argument("--answers", help="Approved text for portal form fields (.md or .txt); checked, not uploaded")
    packet.add_argument("--attachment", action="append", default=[], metavar="NAME=PATH",
                        help="Another required document, for example transcript=transcript.pdf; repeatable")
    packet.add_argument("--approved", action="store_true", required=True)
    authorize = commands.add_parser("authorize", help="Record the user's permission for this vacancy and packet")
    authorize.add_argument("id")
    authorize.add_argument("--note", required=True)
    preview = commands.add_parser("preview", help="Record the operator's actual full-portal preview check")
    preview.add_argument("id")
    preview.add_argument("--evidence", required=True, help="Saved preview file inside the workspace")
    preview.add_argument("--vacancy-open", action="store_true", help="Required for rolling deadlines: the live vacancy is open")
    attempt = commands.add_parser("attempt", help="Record an attempt immediately before one Send click")
    attempt.add_argument("id")
    receipt = commands.add_parser("receipt", help="Record confirmed portal success for the unresolved attempt")
    receipt.add_argument("id")
    receipt.add_argument("--attempt-id", required=True, help="attempt_id returned by attempt; also listed by show")
    receipt.add_argument("--reference", required=True)
    receipt.add_argument("--evidence", required=True)
    reconcile = commands.add_parser("reconcile", help="Resolve an uncertain attempt with actual evidence")
    reconcile.add_argument("id")
    reconcile.add_argument("--attempt-id", required=True, help="attempt_id returned by attempt; also listed by show")
    reconcile.add_argument("--outcome", choices=("sent", "not-sent"), required=True)
    reconcile.add_argument("--evidence", required=True)
    reconcile.add_argument("--reference")
    late = commands.add_parser("late-receipt", help="Attach a real receipt to an earlier attempt previously reconciled not-sent")
    late.add_argument("id")
    late.add_argument("--attempt-id", required=True)
    late.add_argument("--reference", required=True)
    late.add_argument("--evidence", required=True)
    commands.add_parser("list").add_argument("--json", action="store_true", help="JSON is also the default")
    commands.add_parser("show", help="Show packet paths, attempt state and evidence history").add_argument("id")
    commands.add_parser("verify", help="Check stored files, state and evidence history")
    commands.add_parser("demo", help="Exercise a synthetic temporary workspace with no external actions")
    return cli


def attachments(values):
    parsed = {}
    for value in values:
        name, separator, path = value.partition("=")
        if not separator or not path or name in parsed:
            raise WorkflowError("Use --attachment NAME=PATH once per document name")
        parsed[name] = path
    return parsed


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    try:
        if args.command == "demo":
            result = demo()
        else:
            if not args.workspace:
                cli.error("--workspace is required except for demo")
            workspace = Workspace(args.workspace)
            match args.command:
                case "init": result = workspace.init(args.language)
                case "add": result = workspace.add(args.id, args.url, args.title, args.employer, args.deadline)
                case "screen": result = workspace.screen(args.id, args.decision, args.evidence)
                case "deadline": result = workspace.deadline(args.id, args.value, args.evidence)
                case "packet": result = workspace.packet(args.id, args.cv, args.letter, answers=args.answers,
                                                         attachments=attachments(args.attachment), approved=args.approved)
                case "authorize": result = workspace.authorize(args.id, args.note)
                case "preview": result = workspace.preview(args.id, args.evidence, vacancy_open=args.vacancy_open)
                case "attempt": result = workspace.attempt(args.id)
                case "receipt": result = workspace.receipt(args.id, args.attempt_id, args.reference, args.evidence)
                case "reconcile": result = workspace.reconcile(args.id, args.attempt_id, args.outcome, args.evidence, args.reference)
                case "late-receipt": result = workspace.late_receipt(args.id, args.attempt_id, args.reference, args.evidence)
                case "list": result = workspace.list()
                case "show": result = workspace.show(args.id)
                case "verify": result = workspace.verify()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and result.get("ok") is False else 0
    except (WorkflowError, OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
