"""Test mutation campaign accounting without compiling the production compiler."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch

source = Path(__file__).resolve().parents[2] / "tests" / "mutate_compiler.py"
spec = importlib.util.spec_from_file_location("mutation_runner", source)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

def candidate(n):
    return ("checker", (n, n + 1, "x", f"site {n}"))

class MutationCampaignTests(unittest.TestCase):
    def run_campaign(self, pool, count, build="compiler", oracle="detected"):
        with patch.dict(os.environ, {"JOBS": "1"}), \
             patch.object(runner, "build_mutant", return_value=build), \
             patch.object(runner, "oracles", return_value=oracle), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            return runner.campaign({}, pool, count, 1)

    def test_zero_requested(self):
        self.assertEqual(self.run_campaign([], 0), 2)

    def test_empty_pool(self):
        self.assertEqual(self.run_campaign([], 1), 2)

    def test_duplicate_sites(self):
        self.assertEqual(self.run_campaign([candidate(1), candidate(1)], 2), 2)

    def test_unbuildable_mutants(self):
        self.assertEqual(self.run_campaign([candidate(1)], 1, build=None), 2)

    def test_all_killed(self):
        self.assertEqual(self.run_campaign([candidate(1), candidate(2)], 2), 0)

    def test_survivor(self):
        self.assertEqual(self.run_campaign([candidate(1)], 1, oracle=None), 1)

if __name__ == "__main__":
    unittest.main()
