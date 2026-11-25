#!/usr/bin/env python3
"""Unit tests for Git-based assurance evidence freshness."""
import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import types
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

    def test_only_live_claim_states_require_freshness(self):
        self.assertTrue(MODULE.requires_freshness("active"))
        self.assertTrue(MODULE.requires_freshness("qualified"))
        self.assertFalse(MODULE.requires_freshness("proposed"))
        self.assertFalse(MODULE.requires_freshness("withdrawn"))

    def test_schema_rejects_empty_claim_inventory(self):
        import json
        schema_path = os.path.join(ROOT, "docs", "assurance", "assurance.schema.json")
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)
        self.assertGreaterEqual(schema["properties"]["claims"].get("minItems", 0), 1)
        self.assertGreaterEqual(schema["$defs"]["claim"]["properties"]["evidence"].get("minItems", 0), 1)

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


    def test_malformed_manifest_shape_fails_closed_after_schema_error(self):
        # The validator must not dereference nested fields after the schema
        # rejects their type. This used to raise AttributeError on snapshot=[].
        schema_path = os.path.join(self.repo, "schema.json")
        manifest_path = os.path.join(self.repo, "manifest.json")
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write("{}")
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write('{"snapshot": [], "claims": []}')

        class FakeValidator:
            @staticmethod
            def check_schema(schema):
                return None

            def __init__(self, schema, format_checker=None):
                pass

            def iter_errors(self, manifest):
                return [types.SimpleNamespace(
                    absolute_path=("snapshot",), message="must be an object")]

        fake = types.ModuleType("jsonschema")
        fake.Draft202012Validator = FakeValidator
        fake.FormatChecker = lambda: None
        fake.SchemaError = type("SchemaError", (Exception,), {})
        previous_module = sys.modules.get("jsonschema")
        previous_argv = sys.argv
        sys.modules["jsonschema"] = fake
        sys.argv = ["assurance-validate.py", "--schema", "schema.json",
                    "--manifest", "manifest.json"]
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                result = MODULE.main()
        finally:
            sys.argv = previous_argv
            if previous_module is None:
                sys.modules.pop("jsonschema", None)
            else:
                sys.modules["jsonschema"] = previous_module
        self.assertEqual(result, 1)
        self.assertIn("schema: /snapshot: must be an object", output.getvalue())

    def test_unrelated_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.changed_paths("0" * 40, ["src/covered.c"])


if __name__ == "__main__":
    unittest.main()
