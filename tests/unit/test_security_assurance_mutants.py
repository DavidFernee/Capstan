"""Controls for mutation evidence classification and inventory completeness."""
from types import SimpleNamespace
import unittest

import security_assurance_mutants as campaign


class MutationEvidenceTests(unittest.TestCase):
    def test_inventory_exactly_partitioned(self):
        campaign.validate_inventory()
        self.assertEqual(len(campaign.MUTATIONS), 19)

    def test_assertion_failure_is_detected(self):
        result = SimpleNamespace(returncode=101, stderr="assertion failed")
        self.assertEqual(campaign.classify(result), "assertion_detected")

    def test_success_is_survivor_even_with_assertion_text(self):
        result = SimpleNamespace(returncode=0, stderr="assertion failed")
        self.assertEqual(campaign.classify(result), "survived")

    def test_other_failure_is_not_a_kill(self):
        for status, message in ((101, "integer overflow"), (-11, "assertion failed"),
                                (1, "assertion failed"), (124, "")):
            with self.subTest(status=status):
                result = SimpleNamespace(returncode=status, stderr=message)
                self.assertEqual(campaign.classify(result), "unexpected_execution_failure")


if __name__ == "__main__":
    unittest.main()
