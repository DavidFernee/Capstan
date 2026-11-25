#!/usr/bin/env python3
"""Positive and negative controls for the media registry validator."""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("registry", ROOT/"scripts/media-registry-validate.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BASE = json.loads((ROOT/"docs/media/FORMAT-REGISTRY.json").read_text(encoding="utf-8"))

class RegistryTests(unittest.TestCase):
    def test_current_registry_valid(self):
        self.assertEqual(module.validate_registry(BASE), [])
    def test_unknown_top_level_key(self):
        x=copy.deepcopy(BASE); x["unexpected"]=1
        self.assertTrue(any("unknown property 'unexpected'" in e for e in module.validate_registry(x)))
    def test_unknown_record_key(self):
        x=copy.deepcopy(BASE); x["records"][0]["encode"]=True
        self.assertTrue(any("unknown property 'encode'" in e for e in module.validate_registry(x)))
    def test_duplicate_id(self):
        x=copy.deepcopy(BASE); x["records"][1]["id"]=x["records"][0]["id"]
        self.assertTrue(any("duplicate identifier" in e for e in module.validate_registry(x)))
    def test_conflicting_registration_with_different_id(self):
        x=copy.deepcopy(BASE); r=copy.deepcopy(x["records"][0]); r["id"] += ".duplicate"; x["records"].append(r)
        self.assertTrue(any("duplicate/conflicting registration tuple" in e for e in module.validate_registry(x)))
    def test_unknown_operation(self):
        x=copy.deepcopy(BASE); x["records"][0]["operation"]="transcode"
        self.assertTrue(any(".operation: unknown value" in e for e in module.validate_registry(x)))
    def test_decode_does_not_imply_encode(self):
        self.assertFalse(any(r["operation"]=="encode" for r in BASE["records"]))
    def test_bad_source_revision(self):
        x=copy.deepcopy(BASE); x["records"][0]["source_revision"]="main"
        self.assertTrue(any("source_revision" in e for e in module.validate_registry(x)))
    def test_bool_not_integer_bit_depth(self):
        x=copy.deepcopy(BASE); x["records"][0]["bit_depth"]=True
        self.assertTrue(any("bit_depth" in e for e in module.validate_registry(x)))

    def test_duplicate_top_level_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            module.parse_registry('{"schema_version":"1.0.0","schema_version":"1.0.0"}')

    def test_duplicate_nested_record_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
            module.parse_registry('{"records":[{"id":"one","id":"two"}]}')

    def test_nonstandard_json_constant_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-standard JSON constant"):
            module.parse_registry('{"value":NaN}')

    def test_reviewed_requires_passed_test_fuzz_and_rights_reviews(self):
        x=copy.deepcopy(BASE); r=x["records"][0]
        r.update(assurance_level="reviewed", test_status="present-not-run",
                 fuzz_status="not-run")
        errors=module.validate_registry(x)
        self.assertTrue(any("licence_review reviewed-clear" in e for e in errors))
        self.assertTrue(any("patent_review reviewed-clear" in e for e in errors))
        self.assertTrue(any("test_status passed" in e for e in errors))
        self.assertTrue(any("fuzz_status passed" in e for e in errors))

    def test_release_assured_requires_corpus_revision(self):
        x=copy.deepcopy(BASE); r=x["records"][0]
        r.update(assurance_level="release-assured", licence_review="reviewed-clear",
                 patent_review="reviewed-clear", test_status="passed",
                 fuzz_status="passed", corpus_revision="none")
        self.assertTrue(any("requires a corpus revision" in e
                            for e in module.validate_registry(x)))

if __name__ == "__main__":
    unittest.main()
