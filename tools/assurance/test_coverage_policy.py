import importlib.util
from pathlib import Path
import subprocess
import sys
import shutil
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

    def test_branch_counts(self):
        report = "branch  0 taken 0 (fallthrough)\nbranch  1 taken 1\nbranch  2 never executed\n"
        self.assertEqual(runner.branch_counts(report), {"branches": 3, "covered": 1})

    def test_unknown_branch_count(self):
        with self.assertRaises(ValueError):
            runner.branch_counts("branch  0 taken 50%")

    def test_empty_line_records(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "fixture.gcda").touch()
            result = subprocess.CompletedProcess([], 0, b"no records\n", b"")
            with patch.object(runner, "run", return_value=result), self.assertRaises(ValueError):
                runner.gcov_lines(d, {})

    def test_real_gcov(self):
        self.assertIsNotNone(shutil.which(runner.GCC), "GCC required for integration control")
        self.assertIsNotNone(shutil.which(runner.GCOV), "gcov required for integration control")
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "branch.c"
            src.write_text("int main(int n, char **v) { if (n > 1) return 1; return 0; }\n")
            exe = Path(d) / "branch"
            subprocess.run([runner.GCC, "--coverage", str(src), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)
            counts, branches = {}, {}
            runner.gcov_lines(d, counts, branches)
            self.assertEqual(len(branches), 1)
            self.assertEqual(next(iter(branches.values())), {"branches": 2, "covered": 1})

class CoverageWorkloadTests(unittest.TestCase):
    def setUp(self):
        runner.WORKLOADS.clear()

    def test_real_success_and_expected_rejection(self):
        runner.checked_workload("positive", [sys.executable, "-c", "print('ok')"])
        runner.checked_workload("negative", [sys.executable, "-c",
            "import sys; print('CWE-190', file=sys.stderr); sys.exit(101)"],
            allowed=(101,), expected_stderr="CWE-190")
        self.assertEqual([row["status"] for row in runner.WORKLOADS],
                         ["completed", "completed"])

    def test_unexpected_success_rejected(self):
        with self.assertRaises(ValueError):
            runner.checked_workload("negative", [sys.executable, "-c", "pass"],
                                    allowed=(101,))
        self.assertEqual(runner.WORKLOADS[-1]["status"], "failed")

    def test_wrong_diagnostic_rejected(self):
        with self.assertRaises(ValueError):
            runner.checked_workload("negative", [sys.executable, "-c",
                "raise SystemExit(101)"], allowed=(101,), expected_stderr="CWE-190")

    def test_unexpected_exit_rejected(self):
        with self.assertRaises(ValueError):
            runner.checked_workload("positive", [sys.executable, "-c", "raise SystemExit(1)"])
        self.assertEqual(runner.WORKLOADS[-1]["returncode"], 1)

    def test_timeout_is_incomplete(self):
        with self.assertRaises(ValueError):
            runner.checked_workload("timeout", [sys.executable, "-c",
                "import time; time.sleep(2)"], timeout=0.1)
        self.assertEqual(runner.WORKLOADS[-1]["status"], "incomplete")
        self.assertEqual(runner.WORKLOADS[-1]["error"], "TimeoutExpired")

    def test_missing_executable_is_incomplete(self):
        with self.assertRaises(ValueError):
            runner.checked_workload("missing", ["/nonexistent-capstan-coverage-executable"])
        self.assertEqual(runner.WORKLOADS[-1]["status"], "incomplete")

if __name__ == "__main__":
    unittest.main()
