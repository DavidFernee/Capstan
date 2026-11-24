#!/usr/bin/env python3
"""Unit tests for Git-based assurance evidence freshness."""
import importlib.util
import os
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = importlib.util.spec_from_file_location(
    "assurance_validate", os.path.join(ROOT, "scripts", "assurance-validate.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def run_git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        run_git(self.repo, "init", "-q")
        run_git(self.repo, "config", "user.name", "Assurance test")
        run_git(self.repo, "config", "user.email", "assurance-test@example.invalid")
        os.makedirs(os.path.join(self.repo, "src"))
        with open(os.path.join(self.repo, "src", "covered.c"), "w", encoding="utf-8") as f:
            f.write("int value = 1;\n")
        with open(os.path.join(self.repo, "evidence.txt"), "w", encoding="utf-8") as f:
            f.write("fixture\n")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "baseline")
        self.baseline = run_git(self.repo, "rev-parse", "HEAD")
        self.old_root = MODULE.ROOT
        MODULE.ROOT = self.repo

    def tearDown(self):
        MODULE.ROOT = self.old_root
        self.tmp.cleanup()

    def test_unrelated_change_does_not_stale_covered_path(self):
        with open(os.path.join(self.repo, "unrelated.txt"), "w", encoding="utf-8") as f:
            f.write("unrelated\n")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "unrelated")
        self.assertEqual(MODULE.changed_paths(self.baseline, ["src/covered.c"]), [])

    def test_covered_implementation_change_is_detected(self):
        with open(os.path.join(self.repo, "src", "covered.c"), "w", encoding="utf-8") as f:
            f.write("int value = 2;\n")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "implementation changed")
        self.assertEqual(
            MODULE.changed_paths(self.baseline, ["src/covered.c"]),
            ["src/covered.c"])

    def test_evidence_artifact_change_is_detected(self):
        with open(os.path.join(self.repo, "evidence.txt"), "w", encoding="utf-8") as f:
            f.write("changed fixture\n")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "evidence changed")
        self.assertEqual(
            MODULE.changed_paths(self.baseline, ["evidence.txt"]),
            ["evidence.txt"])

    def test_unrelated_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.changed_paths("0" * 40, ["src/covered.c"])


if __name__ == "__main__":
    unittest.main()
