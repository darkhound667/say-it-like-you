import contextlib
from io import StringIO
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from taskboard.cli import atomic_write, main
from taskboard.parser import parse


FIXTURE = Path(__file__).parent / "fixtures" / "tasks.md"


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tasks = self.root / "TASKS.md"
        self.tasks.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        self.briefs = self.root / "briefs"
        self.briefs.mkdir()
        (self.briefs / "TEMPLATE.md").write_text("# Brief <ID>: <short title>\n", encoding="utf-8")

    def run_cli(self, *args):
        out, err = StringIO(), StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--file", str(self.tasks), *args])
        return code, out.getvalue(), err.getvalue()

    def test_list_and_filters_do_not_write(self):
        before = self.tasks.read_bytes()
        code, out, _ = self.run_cli("list", "--status", "todo", "--owner", "codex")
        self.assertEqual(code, 0)
        self.assertIn("Build CLI", out)
        self.assertNotIn("Scaffold repo", out)
        self.assertEqual(self.tasks.read_bytes(), before)

    def test_add_set_and_atomic_cleanup(self):
        code, out, _ = self.run_cli("add", "Another | task", "--owner", "codex", "--notes", "note")
        self.assertEqual((code, out.strip()), (0, "T2"))
        code, _, _ = self.run_cli("set", "T2", "--status", "review", "--notes", "checked")
        self.assertEqual(code, 0)
        row = parse(self.tasks.read_text(encoding="utf-8")).rows[2]
        self.assertEqual((row.task, row.status, row.notes), ("Another | task", "review", "checked"))
        self.assertEqual(list(self.root.glob(".TASKS.md.*")), [])

    def test_next_and_summary(self):
        self.assertIn("T1", self.run_cli("next")[1])
        self.assertIn("done: 1", self.run_cli("summary")[1])
        self.assertIn("1/2 done", self.run_cli("summary")[1])
        self.run_cli("set", "T1", "--status", "done")
        self.assertEqual(self.run_cli("next")[1].strip(), "nothing to do")

    def test_brief_is_created_once(self):
        code, _, _ = self.run_cli("brief", "T1")
        self.assertEqual(code, 0)
        brief = self.briefs / "T1.md"
        self.assertEqual(brief.read_text(), "# Brief T1: Build CLI\n")
        brief.write_text("existing\n")
        self.assertEqual(self.run_cli("brief", "T1")[0], 0)
        self.assertEqual(brief.read_text(), "existing\n")
        self.assertEqual(list(self.briefs.glob(".T1.md.*")), [])

    def test_error_codes(self):
        self.assertEqual(self.run_cli("set", "T9", "--status", "done")[0], 2)
        self.assertEqual(self.run_cli("brief", "T9")[0], 2)
        self.tasks.write_text("bad\n")
        self.assertEqual(self.run_cli("list")[0], 1)
        self.tasks.unlink()
        self.assertEqual(self.run_cli("list")[0], 1)

    def test_bad_status(self):
        with contextlib.redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(["--file", str(self.tasks), "set", "T1", "--status", "unknown"])
        self.assertEqual(error.exception.code, 2)

    def test_atomic_write_cleans_up_after_rename_failure(self):
        before = self.tasks.read_bytes()
        with patch("taskboard.cli.os.replace", side_effect=OSError("rename failed")):
            with self.assertRaises(OSError):
                atomic_write(self.tasks, "replacement")
        self.assertEqual(self.tasks.read_bytes(), before)
        self.assertEqual(list(self.root.glob(".TASKS.md.*")), [])


if __name__ == "__main__":
    unittest.main()
