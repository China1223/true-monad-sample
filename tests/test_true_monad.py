import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "true-monad" / "service" / "true_monad.py"
SPEC = importlib.util.spec_from_file_location("true_monad", str(MODULE_PATH))
tm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tm)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patchers = [
            mock.patch.object(tm, "ROOT", root), mock.patch.object(tm, "NEXT", root / "next"),
            mock.patch.object(tm, "CURRENT", root / "current"), mock.patch.object(tm, "END", root / "end"),
            mock.patch.object(tm, "ARCHIVE", root / "archive"),
        ]
        for patcher in self.patchers:
            patcher.start()
        tm.ensure_workspace()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temp.cleanup()

    def test_create_instruction_uses_next_number(self):
        first = tm.create_instruction("I", "one")
        second = tm.create_instruction("I", "two")
        self.assertEqual(first["name"], "I-001.md")
        self.assertEqual(second["name"], "I-002.md")

    def test_rejects_path_traversal(self):
        with self.assertRaises(tm.PactError):
            tm.save_instruction("../I-001.md", "bad")

    def test_validate_detects_bad_header(self):
        (tm.CURRENT / "current_question.csv").write_text("wrong,header\n1,2\n", encoding="utf-8")
        checks = tm.validate_workspace()
        self.assertEqual(checks[0]["status"], "error")

    def test_archive_preserves_csv_special_characters(self):
        question_path = tm.CURRENT / "current_question.csv"
        with question_path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=tm.CURRENT_SCHEMAS["question"])
            writer.writerow({"id": "Q1", "round_id": "r0", "created_at": "now", "question": "a, b\n\"c\"", "context": "ctx", "status": "open", "decision": ""})
        tm.create_instruction("I", "do it")
        (tm.END / "summary.md").write_text("done", encoding="utf-8")
        result = tm.archive_round()
        self.assertEqual(result["counts"]["question"], 1)
        archived = tm._read_csv(tm.ARCHIVE / "archive_questions.csv")
        self.assertEqual(archived["rows"][0]["question"], "a, b\n\"c\"")
        self.assertFalse(any(tm.NEXT.glob("*.md")))
        self.assertTrue((tm.CURRENT / "compressed_monad.md").exists())


if __name__ == "__main__":
    unittest.main()
