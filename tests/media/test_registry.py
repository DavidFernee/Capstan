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

if __name__ == "__main__":
    unittest.main()
