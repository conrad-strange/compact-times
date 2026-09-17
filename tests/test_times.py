import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "skills/times/scripts/times.py"
SPEC = importlib.util.spec_from_file_location("times", SCRIPT)
times = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(times)
THREAD = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


def meta(**extra):
    return {"type": "session_meta", "payload": {"id": THREAD, **extra}}


def compact(**extra):
    return {"type": "compacted", "payload": {"message": "", **extra}}


class TimesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / "sessions/2026/09/17" / f"rollout-date-{THREAD}.jsonl"
        self.log.parent.mkdir(parents=True)

    def write(self, *records):
        self.log.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")

    def test_zero_one_multiple_and_repeat(self):
        for count in (0, 1, 5):
            with self.subTest(count=count):
                self.write(meta(), *(compact(window_id=str(i)) for i in range(count)))
                self.assertEqual(times.count_compactions(self.log, THREAD), count)
                self.assertEqual(times.count_compactions(self.log, THREAD), count)

    def test_body_and_nested_records_do_not_count(self):
        self.write(meta(), {"type": "response_item", "payload": {
            "text": '"type":"compacted"', "history": [compact()]}})
        self.assertEqual(times.count_compactions(self.log, THREAD), 0)

    def test_duplicate_ids_but_multiple_compactions_in_one_turn(self):
        self.write(meta(), compact(window_id="a", turn_id="same"),
                   compact(window_id="a", turn_id="same"),
                   compact(window_id="b", turn_id="same"))
        self.assertEqual(times.count_compactions(self.log, THREAD), 2)

    def test_legacy_records_without_ids(self):
        self.write(meta(), compact(), compact())
        self.assertEqual(times.count_compactions(self.log, THREAD), 2)

    def test_inherited_history_is_rejected(self):
        for records in ((meta(parent_thread_id=OTHER), compact()),
                        (meta(), meta(id=OTHER), compact())):
            with self.subTest(records=records):
                self.write(*records)
                with self.assertRaises(times.CountError):
                    times.count_compactions(self.log, THREAD)

    def test_missing_or_wrong_identity(self):
        for records in ((), (compact(),), (meta(id=OTHER),)):
            with self.subTest(records=records):
                self.write(*records)
                with self.assertRaises(times.CountError):
                    times.count_compactions(self.log, THREAD)

    def test_invalid_record_or_partial_tail(self):
        for tail in (b'{broken}\n', b'{"type":', b'[]\n'):
            with self.subTest(tail=tail):
                self.write(meta())
                with self.log.open("ab") as stream:
                    stream.write(tail)
                with self.assertRaises(times.CountError):
                    times.count_compactions(self.log, THREAD)

    def test_complete_final_record_without_newline(self):
        self.write(meta())
        with self.log.open("ab") as stream:
            stream.write(json.dumps(compact()).encode())
        self.assertEqual(times.count_compactions(self.log, THREAD), 1)

    def test_find_current_and_archived_log(self):
        self.write(meta())
        self.assertEqual(times.find_rollout(self.root, THREAD), self.log)
        target = self.root / "archived_sessions" / self.log.name
        target.parent.mkdir()
        self.log.rename(target)
        self.assertEqual(times.find_rollout(self.root, THREAD), target)

    def test_missing_or_ambiguous_log(self):
        with self.assertRaises(times.CountError):
            times.find_rollout(self.root, THREAD)
        self.write(meta())
        duplicate = self.root / "archived_sessions" / self.log.name
        duplicate.parent.mkdir()
        duplicate.write_bytes(self.log.read_bytes())
        with self.assertRaises(times.CountError):
            times.find_rollout(self.root, THREAD)

    def test_invalid_thread_id_rejected(self):
        for value in (None, "", "*", "../sessions"):
            with self.subTest(value=value), self.assertRaises(times.CountError):
                times.validate_thread_id(value)
        self.assertEqual(times.validate_thread_id(THREAD), THREAD)

    def test_cli_explicit_id_overrides_environment(self):
        self.write(meta(), compact(window_id="a"), compact(window_id="b"))
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--thread-id", THREAD,
             "--codex-home", str(self.root)],
            env={**os.environ, "CODEX_THREAD_ID": OTHER},
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("压缩了 2 次", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_cli_missing_current_id_is_an_error(self):
        self.write(meta())
        environment = dict(os.environ)
        environment.pop("CODEX_THREAD_ID", None)
        result = subprocess.run(
            [sys.executable, "-I", str(SCRIPT), "--codex-home", str(self.root)],
            env=environment, capture_output=True, text=True,
            encoding="utf-8", timeout=10,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertNotIn("0 次", result.stdout)


if __name__ == "__main__":
    unittest.main()
