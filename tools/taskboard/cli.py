"""Command line interface for TASKS.md."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import tempfile

from .parser import ParseError, TaskRow, parse, render


STATUSES = ("todo", "running", "review", "done", "blocked")
OWNERS = ("claude", "codex")


def atomic_write(path: Path, content: str) -> None:
    """Replace a file only after its complete content is written nearby."""
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                         prefix=f".{path.name}.", delete=False) as temp:
            temp_name = temp.name
            temp.write(content)
        os.replace(temp_name, path)
    finally:
        if temp_name is not None and os.path.exists(temp_name):
            os.unlink(temp_name)


def _display(rows: list[TaskRow]) -> None:
    columns = ("ID", "Task", "Owner", "Branch", "Status", "Notes")
    data = [row.values() for row in rows]
    widths = [max(len(columns[i]), *(len(row[i]) for row in data)) for i in range(6)]
    for row in [columns, *data]:
        print("  ".join(value.ljust(widths[i]) for i, value in enumerate(row)).rstrip())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taskboard")
    parser.add_argument("--file", default="TASKS.md", help="task file (default: TASKS.md)")
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("list")
    listing.add_argument("--status", choices=STATUSES)
    listing.add_argument("--owner", choices=OWNERS)
    adding = commands.add_parser("add")
    adding.add_argument("title")
    adding.add_argument("--owner", choices=OWNERS, required=True)
    adding.add_argument("--branch", default="")
    adding.add_argument("--notes", default="")
    setting = commands.add_parser("set")
    setting.add_argument("id")
    setting.add_argument("--status", choices=STATUSES, required=True)
    setting.add_argument("--notes")
    commands.add_parser("next")
    commands.add_parser("summary")
    briefing = commands.add_parser("brief")
    briefing.add_argument("id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    path = Path(args.file)
    try:
        with path.open("r", encoding="utf-8", newline="") as source:
            document = parse(source.read())
        if args.command == "list":
            rows = [row for row in document.rows if
                    (args.status is None or row.status == args.status) and
                    (args.owner is None or row.owner == args.owner)]
            _display(rows)
        elif args.command == "add":
            used = {row.id for row in document.rows}
            number = 0
            while f"T{number}" in used:
                number += 1
            row = TaskRow(f"T{number}", args.title, args.owner, args.branch, "todo", args.notes)
            document.rows.append(row)
            atomic_write(path, render(document))
            print(row.id)
        elif args.command == "set":
            row = next((row for row in document.rows if row.id == args.id), None)
            if row is None:
                print(f"unknown ID: {args.id}", file=sys.stderr)
                return 2
            row.status = args.status
            if args.notes is not None:
                row.notes = args.notes
            atomic_write(path, render(document))
        elif args.command == "next":
            row = next((row for row in document.rows if row.status == "todo" and row.owner == "codex"), None)
            if row is None:
                print("nothing to do")
            else:
                _display([row])
        elif args.command == "summary":
            counts = {status: sum(row.status == status for row in document.rows) for status in STATUSES}
            for status, count in counts.items():
                print(f"{status}: {count}")
            total = len(document.rows)
            done = counts["done"]
            filled = round(20 * done / total) if total else 0
            print(f"progress: [{'#' * filled}{'.' * (20 - filled)}] {done}/{total} done")
        elif args.command == "brief":
            row = next((row for row in document.rows if row.id == args.id), None)
            if row is None:
                print(f"unknown ID: {args.id}", file=sys.stderr)
                return 2
            brief_dir = path.parent / "briefs"
            brief_path = brief_dir / f"{row.id}.md"
            if not brief_path.exists():
                template = (brief_dir / "TEMPLATE.md").read_text(encoding="utf-8")
                title = re.sub(r"[\r\n]+", " ", row.task)
                content = template.replace("<ID>", row.id).replace("<short title>", title)
                atomic_write(brief_path, content)
            print(brief_path)
    except (OSError, UnicodeError, ParseError) as error:
        print(f"taskboard: {error}", file=sys.stderr)
        return 1
    return 0
