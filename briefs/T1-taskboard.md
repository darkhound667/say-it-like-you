# Brief T1-taskboard: CLI to manage TASKS.md

## Goal
A dependency-free Python CLI, `python3 -m taskboard`, that reads and edits the markdown
table in `TASKS.md` so the manager can track Codex work without hand-editing the table.

## Context
`TASKS.md` has a markdown table with columns: ID | Task | Owner | Branch | Status | Notes.
Statuses: todo, running, review, done, blocked. Owners: claude, codex. Read it for the exact format.

## Files you may touch
- tools/taskboard/__init__.py
- tools/taskboard/__main__.py
- tools/taskboard/parser.py
- tools/taskboard/cli.py
- tools/taskboard/README.md
- tools/tests/test_parser.py
- tools/tests/test_cli.py
- tools/tests/fixtures/*.md

## Requirements
1. `parser.py`: parse the table into a list of dataclass rows and render it back to markdown
   byte-for-byte stable (parse → render → parse is identical; text outside the table is preserved).
   Tolerate extra whitespace, escaped pipes `\|` in cells, and a missing/empty Notes cell.
2. `cli.py` with argparse subcommands (file path via `--file`, default `TASKS.md` in cwd):
   - `list [--status S] [--owner O]` — aligned plain-text table
   - `add "<title>" --owner O [--branch B] [--notes N]` — next free ID (`T<n>`), status todo
   - `set <ID> --status S [--notes N]` — validate status; error exit code 2 on unknown ID/status
   - `next` — print the first `todo` task owned by codex, or "nothing to do"
   - `summary` — counts per status plus a one-line progress bar
   - `brief <ID>` — create `briefs/<ID>.md` from `briefs/TEMPLATE.md` if it doesn't exist yet
3. Writes are atomic (write temp file in same dir, then rename).
4. Exit codes: 0 ok, 1 file/parse error, 2 bad arguments/unknown ID or status.
5. Unit tests with the stdlib `unittest` only: round-trip, escaped pipes, each subcommand,
   error codes, atomic write leaves no temp file behind. Use temp dirs; never touch the real TASKS.md.
6. `README.md`: usage examples for every subcommand.

## Done when
- [ ] `python3 -m unittest discover -s tools/tests -v` → all tests pass
- [ ] `python3 -m taskboard --file TASKS.md list` (run with `PYTHONPATH=tools`) prints the current table without modifying the file
- [ ] `git diff --check` is clean

## Out of scope
- Any third-party packages, web UI, or changes to TASKS.md itself.
