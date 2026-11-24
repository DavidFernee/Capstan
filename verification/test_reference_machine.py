import unittest

from reference_machine import (
    MAX_I64, MIN_I64, InvalidProgram, MachineTrap, execute,
)


def program(code, types, ret="int", name="main", params=0, functions=None):
    fn = {
        "name": name, "register_types": types, "parameter_count": params,
        "return_type": ret, "code": code,
    }
    return {"entry": name, "functions": (functions or []) + [fn]}


class ReferenceMachineTests(unittest.TestCase):
    def test_checked_addition(self):
        p = program([
            {"op": "const_i", "dst": 0, "value": MAX_I64},
            {"op": "const_i", "dst": 1, "value": 1},
            {"op": "add_i", "dst": 2, "lhs": 0, "rhs": 1},
            {"op": "ret", "src": 2},
        ], ["int", "int", "int"])
        with self.assertRaisesRegex(MachineTrap, "integer_overflow"):
            execute(p)

    def test_signed_division_truncates_toward_zero(self):
        p = program([
            {"op": "const_i", "dst": 0, "value": -7},
            {"op": "const_i", "dst": 1, "value": 3},
            {"op": "div_i", "dst": 2, "lhs": 0, "rhs": 1},
            {"op": "ret", "src": 2},
        ], ["int", "int", "int"])
        self.assertEqual(execute(p), -2)

    def test_remainder_has_dividend_sign(self):
        p = program([
            {"op": "const_i", "dst": 0, "value": -7},
            {"op": "const_i", "dst": 1, "value": 3},
            {"op": "rem_i", "dst": 2, "lhs": 0, "rhs": 1},
            {"op": "ret", "src": 2},
        ], ["int", "int", "int"])
        self.assertEqual(execute(p), -1)

    def test_division_by_zero_traps(self):
        p = program([
            {"op": "const_i", "dst": 0, "value": 1},
            {"op": "const_i", "dst": 1, "value": 0},
            {"op": "div_i", "dst": 2, "lhs": 0, "rhs": 1},
            {"op": "ret", "src": 2},
        ], ["int", "int", "int"])
        with self.assertRaisesRegex(MachineTrap, "division_by_zero"):
            execute(p)

    def test_min_divided_by_negative_one_overflows(self):
        p = program([
            {"op": "const_i", "dst": 0, "value": MIN_I64},
            {"op": "const_i", "dst": 1, "value": -1},
            {"op": "div_i", "dst": 2, "lhs": 0, "rhs": 1},
            {"op": "ret", "src": 2},
        ], ["int", "int", "int"])
        with self.assertRaisesRegex(MachineTrap, "integer_overflow"):
            execute(p)

    def test_branch_and_loop(self):
        p = program([
            {"op": "const_i", "dst": 0, "value": 0},
            {"op": "const_i", "dst": 1, "value": 3},
            {"op": "lt_i", "dst": 2, "lhs": 0, "rhs": 1},
            {"op": "branch", "cond": 2, "if_true": 4, "if_false": 6},
            {"op": "const_i", "dst": 3, "value": 1},
            {"op": "add_i", "dst": 0, "lhs": 0, "rhs": 3},
            {"op": "jump", "target": 2},
            {"op": "ret", "src": 0},
        ], ["int", "int", "bool", "int"])
        self.assertEqual(execute(p), 3)

    def test_direct_call(self):
        inc = {
            "name": "inc", "register_types": ["int", "int"],
            "parameter_count": 1, "return_type": "int",
            "code": [
                {"op": "const_i", "dst": 1, "value": 1},
                {"op": "add_i", "dst": 1, "lhs": 0, "rhs": 1},
                {"op": "ret", "src": 1},
            ],
        }
        main = {
            "name": "main", "register_types": ["int", "int"],
            "parameter_count": 0, "return_type": "int",
            "code": [
                {"op": "const_i", "dst": 0, "value": 41},
                {"op": "call", "dst": 1, "function": "inc", "args": [0]},
                {"op": "ret", "src": 1},
            ],
        }
        self.assertEqual(execute({"entry": "main", "functions": [inc, main]}), 42)

    def test_void_call(self):
        sink = {
            "name": "sink", "register_types": [], "parameter_count": 0,
            "return_type": "void", "code": [{"op": "ret_void"}],
        }
        main = {
            "name": "main", "register_types": ["int"], "parameter_count": 0,
            "return_type": "int", "code": [
                {"op": "call", "dst": None, "function": "sink", "args": []},
                {"op": "const_i", "dst": 0, "value": 9},
                {"op": "ret", "src": 0},
            ],
        }
        self.assertEqual(execute({"entry": "main", "functions": [sink, main]}), 9)

    def test_uninitialised_register_traps(self):
        p = program([{"op": "ret", "src": 0}], ["int"])
        with self.assertRaisesRegex(MachineTrap, "uninitialised_register"):
            execute(p)

    def test_invalid_register_is_rejected_before_execution(self):
        p = program([{"op": "ret", "src": 4}], ["int"])
        with self.assertRaises(InvalidProgram):
            execute(p)

    def test_wrong_return_type_is_rejected(self):
        p = program([
            {"op": "const_b", "dst": 0, "value": True},
            {"op": "ret", "src": 0},
        ], ["bool"])
        with self.assertRaises(InvalidProgram):
            execute(p)

    def test_step_limit(self):
        p = program([
            {"op": "jump", "target": 0},
        ], [], ret="void")
        with self.assertRaisesRegex(MachineTrap, "step_limit"):
            execute(p, max_steps=5)

    def test_call_depth_limit(self):
        recurse = {
            "name": "loop", "register_types": [], "parameter_count": 0,
            "return_type": "void",
            "code": [{"op": "call", "dst": None, "function": "loop", "args": []},
                     {"op": "ret_void"}],
        }
        with self.assertRaisesRegex(MachineTrap, "call_depth_limit"):
            execute({"entry": "loop", "functions": [recurse]}, max_call_depth=4)

    def test_bool_is_not_int(self):
        p = program([{"op": "const_i", "dst": 0, "value": True},
                     {"op": "ret", "src": 0}], ["int"])
        with self.assertRaises(InvalidProgram):
            execute(p)

    def test_rejects_fallthrough_only_dynamically(self):
        p = program([{"op": "const_i", "dst": 0, "value": 1}], ["int"])
        with self.assertRaisesRegex(MachineTrap, "invalid_pc"):
            execute(p)

    def test_malformed_type_descriptor_is_rejected_cleanly(self):
        p = program([{"op": "ret", "src": 0}], [["not", "a", "type"]])
        with self.assertRaises(InvalidProgram):
            execute(p)

    def test_runtime_trap_reports_faulting_instruction(self):
        p = program([
            {"op": "const_i", "dst": 0, "value": 1},
            {"op": "const_i", "dst": 1, "value": 0},
            {"op": "div_i", "dst": 2, "lhs": 0, "rhs": 1},
            {"op": "ret", "src": 2},
        ], ["int", "int", "int"])
        with self.assertRaises(MachineTrap) as caught:
            execute(p)
        self.assertEqual(caught.exception.pc, 2)

    def test_explicit_trap(self):
        p = program([{"op": "trap", "reason": "user_trap"}], [], ret="void")
        with self.assertRaisesRegex(MachineTrap, "user_trap"):
            execute(p)


if __name__ == "__main__":
    unittest.main()
