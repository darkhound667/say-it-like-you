import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taskboard.parser import ParseError, TaskRow, parse, render


FIXTURE = Path(__file__).parent / "fixtures" / "tasks.md"


class ParserTests(unittest.TestCase):
    def test_round_trip_preserves_text(self):
        source = FIXTURE.read_text(encoding="utf-8")
        self.assertEqual(render(parse(source)), source)
        self.assertEqual(parse(render(parse(source))).rows, parse(source).rows)

    def test_escaped_pipe_and_missing_notes(self):
        source = ("intro\r\n| ID | Task | Owner | Branch | Status | Notes |\r\n"
                  "|---|---|---|---|---|---|\r\n"
                  r"| T1 | A \| B | codex | x | todo |" + "\r\n"
                  "outro\r\n")
        doc = parse(source)
        self.assertEqual(doc.rows[0].task, "A | B")
        self.assertEqual(doc.rows[0].notes, "")
        self.assertEqual(render(doc), source)
        doc.rows.append(TaskRow("T2", "C | D", "codex", "", "todo"))
        result = render(doc)
        self.assertIn(r"C \| D", result)
        self.assertEqual(parse(result).rows[1].task, "C | D")
        self.assertTrue(result.endswith("outro\r\n"))

    def test_bad_table(self):
        with self.assertRaises(ParseError):
            parse("no table\n")

    def test_add_after_row_without_final_newline(self):
        source = ("| ID | Task | Owner | Branch | Status | Notes |\n"
                  "|---|---|---|---|---|---|\n"
                  "| T0 | First | codex | | todo | |")
        doc = parse(source)
        self.assertEqual(render(doc), source)
        doc.rows.append(TaskRow("T1", "Second", "codex", "", "todo"))
        self.assertEqual(len(parse(render(doc)).rows), 2)


if __name__ == "__main__":
    unittest.main()
