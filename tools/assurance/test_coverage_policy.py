import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[2] / "tests" / "coverage.py"
spec = importlib.util.spec_from_file_location("coverage_runner", source)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class CoveragePolicyTests(unittest.TestCase):
    def test_valid_policy(self):
        self.assertEqual(runner.parse_floors(["# comment", "compiler/a.cap 99.0 # floor"]),
                         {"compiler/a.cap": 99.0})

    def test_invalid_policies(self):
        for lines in ([], ["# only"], ["a"], ["a 90 extra"], ["a 90", "a 80"],
                      ["a NaN"], ["a inf"], ["a -1"], ["a 0"], ["a 101"], ["a abc"]):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                runner.parse_floors(lines)

    def test_missing_data(self):
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            runner.gcov_lines(d, {})

    def test_failed_gcov(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "fixture.gcda").touch()
            result = subprocess.CompletedProcess([], 1, b"", b"failure")
            with patch.object(runner, "run", return_value=result), self.assertRaises(ValueError):
                runner.gcov_lines(d, {})

    def test_successful_gcov(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "fixture.gcda").touch()
            result = subprocess.CompletedProcess([], 0,
                b"        -:0:Source:compiler/a.cap\n        1:1:x\n    #####:2:y\n", b"")
            counts = {}
            with patch.object(runner, "run", return_value=result):
                runner.gcov_lines(d, counts)
            self.assertEqual(counts, {"compiler/a.cap": {1: True, 2: False}})

if __name__ == "__main__":
    unittest.main()
