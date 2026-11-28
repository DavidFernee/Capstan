import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from systematic_runner import complete, execute, validate_manifest


class SystematicEvidenceTests(unittest.TestCase):
    def test_valid_manifest(self):
        groups = {"scalar": [["bin/capstan", "test", "verification/sample.cap"]]}
        self.assertEqual(validate_manifest(groups), groups)

    def test_manifest_fails_closed(self):
        for groups in ({}, {"scalar": []}, {"../bad": [["python3", "a.py"]]},
                       {"scalar": [["python3", "../a.py"]]},
                       {"scalar": [["python3", "-c", "pass"]]},
                       {"scalar": [["bin/capstan", "build", "a.cap"]]},
                       {"scalar": [["python3", "a.py"], ["python3", "a.py"]]}):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                validate_manifest(groups)

    def test_real_execution_continues_after_failure_and_hashes_logs(self):
        commands = [[sys.executable, "-c", "print('first'); raise SystemExit(7)"],
                    [sys.executable, "-c", "print('second')"]]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "evidence"
            rows = execute(commands, directory, Path(tmp))
            self.assertEqual([r["returncode"] for r in rows], [7, 0])
            self.assertFalse(complete(commands, rows))
            for row in rows:
                self.assertEqual(row["log_sha256"],
                                 hashlib.sha256((directory / row["log"]).read_bytes()).hexdigest())
            self.assertEqual((directory / rows[1]["log"]).read_text(), "second\n")
            with self.assertRaises(FileExistsError):
                execute(commands, directory, Path(tmp))

    def test_timeout_and_missing_command_are_not_passes(self):
        commands = [[sys.executable, "-c", "import time; time.sleep(2)"],
                    ["/definitely-nonexistent-capstan-command"]]
        with tempfile.TemporaryDirectory() as tmp:
            rows = execute(commands, Path(tmp) / "evidence", Path(tmp), timeout=0.1)
            self.assertEqual([r["error"] for r in rows], ["timeout", "FileNotFoundError"])
            self.assertFalse(complete(commands, rows))

    def test_incomplete_reordered_or_boolean_status_evidence_rejected(self):
        commands = [["a"], ["b"]]
        rows = [{"argv": argv, "returncode": 0, "error": ""} for argv in commands]
        self.assertTrue(complete(commands, rows))
        self.assertFalse(complete(commands, rows[:1]))
        self.assertFalse(complete(commands, rows[::-1]))
        self.assertFalse(complete([], []))
        rows[0]["returncode"] = False
        self.assertFalse(complete(commands, rows))


if __name__ == "__main__":
    unittest.main()
