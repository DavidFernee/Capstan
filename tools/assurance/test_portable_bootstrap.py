"""Independent negative controls for the portable fixture oracle."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from portable_bootstrap import check_outcome, fixture_expected


class PortableOracleTests(unittest.TestCase):
    def test_matching_positive_and_negative(self):
        check_outcome(subprocess.CompletedProcess([], 0, b"ok\n", b""), 0, b"ok\n")
        check_outcome(subprocess.CompletedProcess([], 101, b"", b"CWE-190"), 101, b"CWE-190")

    def test_wrong_exit_is_never_accepted(self):
        for rc in (-11, 1, 101):
            with self.subTest(rc=rc), self.assertRaises(ValueError):
                check_outcome(subprocess.CompletedProcess([], rc, b"ok\n", b""), 0, b"ok\n")

    def test_wrong_output_or_diagnostic_is_rejected(self):
        with self.assertRaises(ValueError):
            check_outcome(subprocess.CompletedProcess([], 0, b"wrong", b""), 0, b"ok")
        with self.assertRaises(ValueError):
            check_outcome(subprocess.CompletedProcess([], 101, b"CWE-190", b"CWE-191"), 101, b"CWE-190")

    def test_missing_or_ambiguous_runtime_expectation(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "runtime"
            folder.mkdir()
            source = folder / "sample.cap"
            for content in ("int main() { return 0; }\n",
                            "// expect-runtime: CWE-190\n// expect-runtime: CWE-191\n"):
                source.write_text(content)
                with self.assertRaises(ValueError):
                    fixture_expected(source)

    def test_missing_positive_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "sample.cap"
            source.write_text("int main() { return 0; }\n")
            with self.assertRaises(FileNotFoundError):
                fixture_expected(source)


if __name__ == "__main__":
    unittest.main()
