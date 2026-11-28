import copy
import json
from pathlib import Path
import tempfile
import unittest

from verify_systematic_evidence import command_hash, digest, readback

REV = "a" * 40
TREE = "b" * 40
MANIFEST = "c" * 64
COMMANDS = [["bin/capstan", "test", "verification/a.cap"], ["python3", "b.py"]]


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.rows = []
        for i, command in enumerate(COMMANDS):
            name = f"{i:03d}.log"
            data = b"  pass  control\n1 test(s), 0 failed\n" if i == 0 else b"ok\n"
            (self.directory / name).write_bytes(data)
            self.rows.append(dict(argv=command, returncode=0, error="",
                                  elapsed_seconds=0.1, log=name, log_sha256=digest(data)))
        self.report = dict(schema=1, revision=REV, tree=TREE, group="scalar",
                           manifest_sha256=MANIFEST, expected_count=2,
                           results=self.rows, passed=True)

    def check(self, report=None):
        (self.directory / "evidence.json").write_text(json.dumps(
            self.report if report is None else report))
        return self.read()

    def read(self):
        return readback(self.directory, "scalar", COMMANDS, REV, TREE, MANIFEST)

    def test_valid_artifacts_bind_expected_and_observed_command_hashes(self):
        args = self.check()
        self.assertEqual(len(args), 26)
        self.assertEqual(args[:5], [REV, TREE, MANIFEST, "scalar", "2"])
        self.assertEqual(args[10:12], [command_hash(cmd) for cmd in COMMANDS])
        self.assertEqual(args[13], args[10])
        self.assertEqual(args[20], args[11])

    def test_stale_identity_missing_result_and_boolean_status(self):
        for key, value in (("revision", TREE), ("tree", REV), ("manifest_sha256", "d"*64),
                           ("group", "memory"), ("schema", True), ("passed", False),
                           ("expected_count", 1), ("results", self.rows[:1])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(dict(self.report, **{key: value}))
        modified = copy.deepcopy(self.report)
        modified["results"][0]["returncode"] = False
        with self.assertRaises(ValueError):
            self.check(modified)

    def test_reordered_and_duplicate_rows(self):
        for rows in (self.rows[::-1], [self.rows[0], self.rows[0]]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.check(dict(self.report, results=rows))

    def test_changed_missing_or_extra_log(self):
        self.check()
        path = self.directory / "000.log"
        original = path.read_bytes()
        path.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            self.read()
        path.unlink()
        with self.assertRaises(ValueError):
            self.read()
        path.write_bytes(original)
        (self.directory / "unexpected.log").touch()
        with self.assertRaises(ValueError):
            self.read()

    def test_zero_tests_even_with_matching_digest(self):
        raw = b"0 test(s), 0 failed\n"
        (self.directory / "000.log").write_bytes(raw)
        self.rows[0]["log_sha256"] = digest(raw)
        with self.assertRaises(ValueError):
            self.check()

    def test_duplicate_json_key(self):
        self.check()
        path = self.directory / "evidence.json"
        path.write_text(path.read_text().replace('"schema": 1', '"schema": 1, "schema": 1'))
        with self.assertRaises(ValueError):
            self.read()


if __name__ == "__main__":
    unittest.main()
