#!/usr/bin/env python3
"""Unit tests for Git-based assurance evidence freshness and promotion policy."""
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

    def test_live_claim_requires_passed_evidence(self):
        claim = {"id": "MEM-001", "state": "qualified", "evidence": [],
                 "review": {"reviewed_commit": self.baseline}}
        errors = MODULE.promotion_errors(claim)
        self.assertTrue(any("at least one passed evidence" in e for e in errors))

    def test_live_claim_requires_independent_review_at_reviewed_revision(self):
        claim = {
            "id": "MEM-001", "state": "active",
            "review": {"reviewed_commit": self.baseline},
            "evidence": [{
                "kind": "test", "result": "passed", "revision": self.baseline,
                "verification": {"commit": self.baseline,
                                 "run_url": "https://github.com/example/run/1"}
            }]
        }
        errors = MODULE.promotion_errors(claim)
        self.assertTrue(any("independent-review" in e for e in errors))

    def test_independent_review_must_match_reviewed_revision(self):
        other = "1" * 40
        claim = {
            "id": "MEM-001", "state": "qualified",
            "review": {"reviewed_commit": self.baseline},
            "evidence": [{
                "kind": "independent-review", "result": "passed",
                "revision": other,
                "verification": {"commit": other,
                                 "run_url": "https://github.com/example/review/1"}
            }]
        }
        errors = MODULE.promotion_errors(claim)
        self.assertTrue(any("independent-review" in e for e in errors))

    def test_proposed_claim_does_not_require_promotion_evidence(self):
        claim = {"id": "MEM-001", "state": "proposed", "evidence": [],
                 "review": {"reviewed_commit": self.baseline}}
        self.assertEqual(MODULE.promotion_errors(claim), [])

    def test_exact_commit_test_and_independent_review_satisfy_promotion_policy(self):
        claim = {
            "id": "MEM-001", "state": "active",
            "review": {"reviewed_commit": self.baseline},
            "evidence": [
                {"kind": "test", "result": "passed", "revision": self.baseline,
                 "verification": {"commit": self.baseline,
                                  "run_url": "https://github.com/example/actions/runs/1"}},
                {"kind": "independent-review", "result": "passed",
                 "revision": self.baseline,
                 "verification": {"commit": self.baseline,
                                  "run_url": "https://github.com/example/pull/1"}}
            ]
        }
        self.assertEqual(MODULE.promotion_errors(claim), [])

    def test_repository_paths_use_portable_relative_posix_syntax(self):
        self.assertTrue(MODULE.inside_repo("src/covered.c"))
        for path in ("", "/etc/passwd", "../outside", "src\\\\outside",
                     "C:/outside", "C:outside", "\\\\\\\\server\\\\share"):
            with self.subTest(path=path):
                self.assertFalse(MODULE.inside_repo(path))

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

    def test_require_fresh_rejects_active_claim_after_covered_code_changes(self):
        with open(os.path.join(self.repo, "src", "covered.c"), "w", encoding="utf-8") as f:
            f.write("int value = 2;\n")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "covered implementation changed")

        schema_path = os.path.join(self.repo, "schema.json")
        manifest_path = os.path.join(self.repo, "manifest.json")
        with open(schema_path, "w", encoding="utf-8") as f:
            f.write("{}")
        manifest = {
            "snapshot": {"commit": self.baseline},
            "claims": [{
                "id": "MEM-001", "state": "active",
                "covers": ["src/covered.c"],
                "review": {"reviewed_commit": self.baseline},
                "evidence": [{
                    "kind": "test", "result": "available",
                    "revision": self.baseline, "artifacts": ["evidence.txt"]
                }]
            }]
        }
        import json
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f)

        class FakeValidator:
            @staticmethod
            def check_schema(schema):
                return None

            def __init__(self, schema, format_checker=None):
                pass

            def iter_errors(self, manifest):
                return []

        fake = types.ModuleType("jsonschema")
        fake.Draft202012Validator = FakeValidator
        fake.FormatChecker = lambda: None
        fake.SchemaError = type("SchemaError", (Exception,), {})
        previous_module = sys.modules.get("jsonschema")
        previous_argv = sys.argv
        sys.modules["jsonschema"] = fake
        sys.argv = ["assurance-validate.py", "--schema", "schema.json",
                    "--manifest", "manifest.json", "--require-fresh"]
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
        self.assertIn("STALE MEM-001", output.getvalue())
        self.assertIn("active/qualified claims", output.getvalue())

    def test_symlink_paths_must_resolve_inside_repository(self):
        external = tempfile.TemporaryDirectory()
        try:
            external_file = os.path.join(external.name, "outside.txt")
            with open(external_file, "w", encoding="utf-8") as f:
                f.write("outside\n")
            internal_link = os.path.join(self.repo, "src", "internal-link")
            external_link = os.path.join(self.repo, "src", "external-link")
            try:
                os.symlink(os.path.join(self.repo, "src", "covered.c"), internal_link)
                os.symlink(external_file, external_link)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("symlink creation unavailable: %s" % exc)
            self.assertTrue(MODULE.resolves_inside_repo("src/internal-link"))
            self.assertFalse(MODULE.resolves_inside_repo("src/external-link"))
        finally:
            external.cleanup()

    def test_cross_volume_commonpath_error_fails_closed(self):
        from unittest import mock
        with mock.patch.object(MODULE.os.path, "commonpath", side_effect=ValueError("different drives")):
            self.assertFalse(MODULE.resolves_inside_repo("src/covered.c"))

    def test_unrelated_revision_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.changed_paths("0" * 40, ["src/covered.c"])


if __name__ == "__main__":
    unittest.main()
