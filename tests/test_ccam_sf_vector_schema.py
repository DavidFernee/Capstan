#!/usr/bin/env python3
"""Negative controls for fail-closed CCAM-SF-P oracle validation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-ccam-sf-vectors.py"
SPEC = importlib.util.spec_from_file_location("ccam_sf_validator", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class CorpusSchemaNegativeControls(unittest.TestCase):
    def test_missing_trace_is_rejected(self):
        with self.assertRaises(ValueError):
            VALIDATOR.check_trace({"steps": 0}, "negative-control")

    def test_missing_step_count_is_rejected(self):
        with self.assertRaises(ValueError):
            VALIDATOR.check_trace({"trace_pcs": []}, "negative-control")

    def test_trace_step_disagreement_is_rejected(self):
        with self.assertRaises(ValueError):
            VALIDATOR.check_trace(
                {"trace_pcs": [0], "steps": 0}, "negative-control", 1)

    def test_missing_halt_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            VALIDATOR.check_outcome(
                {"outcome": {"kind": "halt", "value": {"type": "int"}}},
                "negative-control")

    def test_trap_without_terminal_pc_is_rejected(self):
        with self.assertRaises(ValueError):
            VALIDATOR.check_outcome(
                {"outcome": {"kind": "trap", "code": "integer_overflow"}},
                "negative-control")

    def test_not_executed_cannot_smuggle_payload(self):
        with self.assertRaises(ValueError):
            VALIDATOR.check_outcome(
                {"outcome": {"kind": "not_executed", "code": "unexpected"}},
                "negative-control")


if __name__ == "__main__":
    unittest.main(verbosity=2)
