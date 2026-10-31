"""Parse and render the task table while preserving surrounding markdown."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


HEADERS = ("ID", "Task", "Owner", "Branch", "Status", "Notes")


class ParseError(ValueError):
    """The task table is missing or malformed."""


@dataclass
class TaskRow:
    id: str
    task: str
    owner: str
    branch: str
    status: str
    notes: str = ""
    raw_line: str | None = field(default=None, repr=False, compare=False)
    original: tuple[str, ...] | None = field(default=None, repr=False, compare=False)

    def values(self) -> tuple[str, ...]:
        return (self.id, self.task, self.owner, self.branch, self.status, self.notes)


@dataclass
class TaskDocument:
    before: str
    header: str
    separator: str
    rows: list[TaskRow]
    after: str
    newline: str = "\n"


def _cells(line: str) -> list[str]:
    """Split cells and decode escaped pipes and backslashes."""
    body = line.rstrip("\r\n").strip()
    if not body.startswith("|"):
        raise ParseError("expected a markdown table row")
    parts = []
    current = []
    escaped = False
    for char in body[1:]:
        if escaped:
            if char not in ("|", "\\"):
                current.append("\\")
            current.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == "|":
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    if escaped:
        current.append("\\")
    if current or not body.endswith("|"):
        parts.append(''.join(current).strip())
    return parts


def parse(text: str) -> TaskDocument:
    lines = text.splitlines(keepends=True)
    for index in range(len(lines) - 1):
        try:
            header = _cells(lines[index])
            separator = _cells(lines[index + 1])
        except ParseError:
            continue
        if tuple(header) != HEADERS:
            continue
        if len(separator) != 6 or any(not re.fullmatch(r":?-+:?", cell) for cell in separator):
            raise ParseError("invalid task table separator")
        rows = []
        end = index + 2
        while end < len(lines) and lines[end].lstrip().startswith("|"):
            cells = _cells(lines[end])
            if len(cells) == 5:
                cells.append("")
            if len(cells) != 6:
                raise ParseError(f"invalid task row on line {end + 1}")
            rows.append(TaskRow(*cells, raw_line=lines[end], original=tuple(cells)))
            end += 1
        newline = "\r\n" if lines[index + 1].endswith("\r\n") else "\n"
        return TaskDocument(''.join(lines[:index]), lines[index], lines[index + 1], rows,
                            ''.join(lines[end:]), newline)
    raise ParseError("task table not found")


def render(document: TaskDocument) -> str:
    lines = []
    for row in document.rows:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += document.newline
        if row.raw_line is not None and row.values() == row.original:
            lines.append(row.raw_line)
        else:
            cells = [value.replace("\\", r"\\").replace("|", r"\|") for value in row.values()]
            lines.append("| " + " | ".join(cells) + " |" + document.newline)
    separator = document.separator
    if lines and not separator.endswith(("\n", "\r")):
        separator += document.newline
    return document.before + document.header + separator + ''.join(lines) + document.after
