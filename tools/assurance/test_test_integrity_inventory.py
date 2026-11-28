import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_integrity_inventory import audit

class IntegrityTests(unittest.TestCase):
    def test_real_git_changes(self):
        old = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            try:
                os.chdir(tmp)
                def git(*args):
                    return subprocess.check_output(["git", *args])
                git("init", "-q")
                git("config", "user.name", "Fixture")
                git("config", "user.email", "fixture@example.invalid")
                Path("tests").mkdir()
                p = Path("tests/example.cap")
                p.write_text("assert(true);\n")
                git("add", ".")
                git("commit", "-qm", "base")
                base = git("rev-parse", "HEAD").decode().strip()
                p.write_text("assert(true);\nassert(false);\n")
                git("commit", "-qam", "addition")
                self.assertFalse(audit(base, "HEAD")["review_required"])
                p.write_text("assert(false);\n")
                git("commit", "-qam", "replacement")
                report = audit(base, "HEAD")
                self.assertTrue(report["review_required"])
                self.assertEqual(report["changes"][0]["deleted"], 1)
                p.unlink()
                git("commit", "-qam", "removal")
                self.assertTrue(audit(base, "HEAD")["review_required"])
            finally:
                os.chdir(old)

if __name__ == "__main__":
    unittest.main()
