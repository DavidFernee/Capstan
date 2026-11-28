import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_integrity_inventory import audit

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(os.chdir, self.old)
        os.chdir(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "core.filemode", "true")
        Path("tests").mkdir()
        self.p = Path("tests/example.cap")
        self.p.write_text("assert(x);\n")
        self.base = self.commit("base")

    def git(self, *args):
        return subprocess.check_output(["git", *args])

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD").decode().strip()

    def test_addition(self):
        self.p.write_text("assert(x);\nassert(y);\n")
        report = audit(self.base, self.commit("addition"))
        self.assertFalse(report["review_required"])
        self.assertEqual(report["protected_paths_before"], 1)

    def test_replacement(self):
        self.p.write_text("assert(y);\n")
        report = audit(self.base, self.commit("replacement"))
        self.assertTrue(report["review_required"])
        self.assertEqual(report["changes"][0]["deleted"], 1)

    def test_removal(self):
        self.p.unlink()
        report = audit(self.base, self.commit("removal"))
        self.assertEqual(report["removed_paths"], ["tests/example.cap"])
        self.assertTrue(report["review_required"])

    def test_rename_outside_scope(self):
        self.p.rename("example.cap")
        self.assertTrue(audit(self.base, self.commit("rename"))["review_required"])

    def test_additive_bypass(self):
        self.p.write_text("assert(x);\nassert(true);\n")
        report = audit(self.base, self.commit("bypass"))
        self.assertIn("possible-bypass-added", report["changes"][0]["reasons"])

    def test_workflow_bypass(self):
        p = Path(".github/workflows")
        p.mkdir(parents=True)
        (p / "test.yml").write_text("continue-on-error: true\n")
        self.assertTrue(audit(self.base, self.commit("workflow"))["review_required"])

    def test_binary(self):
        self.p.write_bytes(b"\x00\xff")
        report = audit(self.base, self.commit("binary"))
        self.assertTrue(report["review_required"])
        self.assertIsNone(report["changes"][0]["deleted"])

    def test_mode(self):
        self.p.chmod(0o755)
        report = audit(self.base, self.commit("mode"))
        self.assertTrue(report["review_required"])
        self.assertIn("mode-change", report["changes"][0]["reasons"])

    def test_unrelated_path(self):
        Path("readme.txt").write_text("x")
        self.assertFalse(audit(self.base, self.commit("unrelated"))["review_required"])

if __name__ == "__main__":
    unittest.main()
