"""Negative controls for source tracing and recorded mask accounting."""
import unittest

from trace_memory_storage_decisions import instrument, validate_trace_output


class TraceControls(unittest.TestCase):
    def test_exact_rewrite_keeps_original_short_circuit_operators(self):
        source = "bool sample(bool a, bool b) {\n    if (a || b) { return true; }\n    return false;\n}\n"
        rewritten, count = instrument(source, "bool sample(", "bool b)", "traced",
                                      [("a || b", ["a", "b"])])
        self.assertEqual(count, 2)
        self.assertIn("bool traced(bool a, bool b, List<int> trace)", rewritten)
        self.assertIn("assurance_trace_atom(trace, 0, (a)) || assurance_trace_atom(trace, 1, (b))", rewritten)

    def test_missing_or_duplicate_guard_fails_closed(self):
        for body in ("if (a && b) { return true; }",
                     "if (a || b) { return true; }\n    if (a || b) { return false; }"):
            source = "bool sample(bool a, bool b) {\n    " + body + "\n}\n"
            with self.assertRaises(ValueError):
                instrument(source, "bool sample(", "bool b)", "traced",
                           [("a || b", ["a", "b"])])

    def test_recorded_mask_counts_distinguish_unevaluated(self):
        log = b"ASSURANCE_TRACE 12\nASSURANCE_TRACE 01\n  pass  trace\n1 test(s), 0 failed\n"
        self.assertEqual(validate_trace_output(log, 2, 2),
                         [{"atom": 0, "false": 1, "true": 1, "not_evaluated": 0},
                          {"atom": 1, "false": 0, "true": 1, "not_evaluated": 1}])

    def test_invalid_or_missing_observations_fail_closed(self):
        summary = b"  pass  trace\n1 test(s), 0 failed\n"
        for raw in (b"", b"ASSURANCE_TRACE 1\n", b"ASSURANCE_TRACE 13\n",
                    b"ASSURANCE_TRACE 12\nASSURANCE_TRACE 12\n"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                validate_trace_output(raw + summary, 2, 1)
        with self.assertRaises(ValueError):
            validate_trace_output(b"ASSURANCE_TRACE 12\n", 2, 1)


if __name__ == "__main__":
    unittest.main()
