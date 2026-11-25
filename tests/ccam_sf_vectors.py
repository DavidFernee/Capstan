#!/usr/bin/env python3
"""Strict structural and oracle-integrity checks for CCAM-SF-P vectors.

This does not execute the CCAM evaluator, interpret Lean, or prove that either
implementation agrees with the oracle. It checks that the shared corpus is
well-formed and that its declared traces/budgets are internally consistent.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "verification" / "ccam_sf_vectors.json"
FORMAT = "capstan-ccam-sf-vectors/1"
I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1

# Exact field sets prevent a misspelled operand from silently becoming ignored
# metadata. These are the v0.1 instruction shapes represented in CCAM-SF-P.
FIELDS = {
    "const_i": {"op", "dst", "value"},
    "const_b": {"op", "dst", "value"},
    "move": {"op", "dst", "src"},
    "add_i": {"op", "dst", "lhs", "rhs"},
    "div_i": {"op", "dst", "lhs", "rhs"},
    "rem_i": {"op", "dst", "lhs", "rhs"},
    "eq_i": {"op", "dst", "lhs", "rhs"},
    "lt_i": {"op", "dst", "lhs", "rhs"},
    "not_b": {"op", "dst", "src"},
    "jump": {"op", "target"},
    "branch": {"op", "cond", "if_true", "if_false"},
    "ret": {"op", "src"},
    "ret_void": {"op"},
}
TOP_FIELDS = {
    "id", "name", "register_types", "return_type", "profile_entry",
    "max_steps", "instructions", "expected",
}
EXPECTED_FIELDS = {
    "profile_validation", "normative_validation", "outcome",
    "trace_pcs", "steps", "profile_execution", "normative_execution",
}
OUTCOME_KINDS = {"halt", "halt_void", "trap", "not_executed"}
TRAP_CODES = {
    "integer_overflow", "division_by_zero", "uninitialised_register",
    "step_limit_exceeded",
}
errors: list[str] = []


def fail(where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


def is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_index(value: object, bound: int, where: str) -> bool:
    if not is_int(value) or not 0 <= value < bound:
        fail(where, f"index must be an integer in [0, {bound}), got {value!r}")
        return False
    return True


def check_instruction(ins: object, pc: int, registers: list[str], count: int,
                      where: str) -> None:
    if not isinstance(ins, dict):
        fail(where, "instruction must be an object")
        return
    op = ins.get("op")
    if op not in FIELDS:
        fail(where, f"opcode is not in CCAM-SF-P: {op!r}")
        return
    if set(ins) != FIELDS[op]:
        fail(where, f"{op} fields must be {sorted(FIELDS[op])}, got {sorted(ins)}")
        return

    def reg(key: str, expected: str | None = None) -> bool:
        value = ins[key]
        if not check_index(value, len(registers), f"{where}.{key}"):
            return False
        if expected and registers[value] != expected:
            fail(where, f"{key} register {value} must have type {expected}")
            return False
        return True

    if op == "const_i":
        reg("dst", "int")
        if not is_int(ins["value"]) or not I64_MIN <= ins["value"] <= I64_MAX:
            fail(where, "value must be a signed 64-bit integer")
    elif op == "const_b":
        reg("dst", "bool")
        if not isinstance(ins["value"], bool):
            fail(where, "value must be boolean")
    elif op == "move":
        dst_ok = reg("dst")
        src_ok = reg("src")
        if dst_ok and src_ok and registers[ins["dst"]] != registers[ins["src"]]:
            fail(where, "move source and destination register types must match")
    elif op in {"add_i", "div_i", "rem_i", "eq_i", "lt_i"}:
        reg("lhs", "int")
        reg("rhs", "int")
        reg("dst", "bool" if op == "eq_i" else "int" if op in {"add_i", "div_i", "rem_i"} else "bool")
    elif op == "not_b":
        reg("src", "bool")
        reg("dst", "bool")
    elif op == "jump":
        check_index(ins["target"], count, f"{where}.target")
    elif op == "branch":
        reg("cond", "bool")
        check_index(ins["if_true"], count, f"{where}.if_true")
        check_index(ins["if_false"], count, f"{where}.if_false")
    elif op == "ret":
        reg("src")  # refined against return_type by vector check below


def check_vector(v: object, seen: set[str], index: int) -> None:
    where = f"vectors[{index}]"
    if not isinstance(v, dict):
        fail(where, "vector must be an object")
        return
    if set(v) != TOP_FIELDS:
        fail(where, f"fields must be {sorted(TOP_FIELDS)}, got {sorted(v)}")
        return
    ident = v["id"]
    if not isinstance(ident, str) or not re.fullmatch(r"SF-[0-9]{3}", ident):
        fail(where, f"invalid vector id {ident!r}")
    elif ident in seen:
        fail(where, f"duplicate vector id {ident}")
    else:
        seen.add(ident)

    if not isinstance(v["name"], str) or not v["name"]:
        fail(where, "name must be a non-empty string")
    regs = v["register_types"]
    if not isinstance(regs, list) or any(t not in {"int", "bool"} for t in regs):
        fail(where, "register_types must contain only 'int' and 'bool'")
        return
    if v["return_type"] not in {"int", "bool", "void"}:
        fail(where, "return_type must be int, bool or void")
    entry = v["profile_entry"]
    if not is_int(entry) or entry < 0:
        fail(where, "profile_entry must be a non-negative integer")
    budget = v["max_steps"]
    if not is_int(budget) or budget < 0:
        fail(where, "max_steps must be a non-negative integer")
    code = v["instructions"]
    if not isinstance(code, list) or not code:
        fail(where, "instructions must be a non-empty array")
        return
    for pc, ins in enumerate(code):
        check_instruction(ins, pc, regs, len(code), f"{where}.instructions[{pc}]")
        if isinstance(ins, dict) and ins.get("op") == "ret" and is_int(ins.get("src")):
            src = ins["src"]
            if 0 <= src < len(regs) and v["return_type"] in {"int", "bool"}:
                if regs[src] != v["return_type"]:
                    fail(where, f"return at PC {pc} does not match return_type")

    expected = v["expected"]
    if not isinstance(expected, dict) or set(expected) - EXPECTED_FIELDS:
        fail(where, "expected must be an object containing only documented fields")
        return
    if expected.get("profile_validation") not in {"accept", "reject"}:
        fail(where, "profile_validation must be accept or reject")
    if expected.get("normative_validation") not in {"accept", "reject", "not_applicable"}:
        fail(where, "normative_validation must be accept, reject or not_applicable")
    outcome = expected.get("outcome")
    if not isinstance(outcome, dict) or outcome.get("kind") not in OUTCOME_KINDS:
        fail(where, "expected.outcome has an unknown kind")
    trace = expected.get("trace_pcs")
    steps = expected.get("steps")
    if trace is not None:
        if not isinstance(trace, list) or any(
            not is_int(pc) or not 0 <= pc < len(code) for pc in trace
        ):
            fail(where, "trace_pcs must contain only valid instruction indices")
        elif not is_int(steps) or steps != len(trace):
            fail(where, "steps must equal the number of dispatched PCs in trace_pcs")
    if is_int(steps) and steps < 0:
        fail(where, "steps cannot be negative")
    if expected.get("profile_validation") == "reject":
        if outcome and outcome.get("kind") != "not_executed":
            fail(where, "profile-rejected vector must have not_executed outcome")
        if trace not in (None, []):
            fail(where, "profile-rejected vector cannot have an execution trace")
        if steps not in (None, 0):
            fail(where, "profile-rejected vector must consume zero steps")
    if outcome and outcome.get("kind") == "trap":
        if outcome.get("code") not in TRAP_CODES:
            fail(where, f"unexpected in-profile trap code {outcome.get('code')!r}")
        if "pc" in outcome and not check_index(outcome["pc"], len(code), f"{where}.outcome.pc"):
            pass
    if v["id"] == "SF-019":
        if not (expected.get("profile_validation") == "reject"
                and expected.get("normative_validation") == "accept"):
            fail(where, "SF-019 must distinguish profile rejection from normative acceptance")
    if v["id"] == "SF-020" and entry == 0:
        fail(where, "SF-020 must retain a nonzero proof-model entry")


def main() -> int:
    try:
        data = json.loads(CORPUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL CCAM-SF-P corpus: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print("FAIL CCAM-SF-P corpus: top-level value must be an object", file=sys.stderr)
        return 1
    required = {"format", "profile", "normative_specification",
                "profile_specification", "oracle_policy", "vectors", "out_of_profile"}
    if set(data) != required:
        fail("root", f"fields must be {sorted(required)}, got {sorted(data)}")
    if data.get("format") != FORMAT:
        fail("root", f"format must be {FORMAT}")
    if data.get("profile") != "CCAM-SF-P":
        fail("root", "profile must be CCAM-SF-P")
    vectors = data.get("vectors")
    seen: set[str] = set()
    if not isinstance(vectors, list) or not vectors:
        fail("root.vectors", "must be a non-empty array")
    else:
        for i, vector in enumerate(vectors):
            check_vector(vector, seen, i)
    out = data.get("out_of_profile")
    if not isinstance(out, list) or len(out) != 1 or out[0].get("id") != "SF-X01":
        fail("root.out_of_profile", "expected exactly the documented SF-X01 case")
    if "SF-019" not in seen or "SF-020" not in seen:
        fail("root.vectors", "required profile-boundary vectors SF-019 and SF-020 are missing")
    if errors:
        print(f"FAIL CCAM-SF-P corpus: {len(errors)} error(s)", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(f"PASS CCAM-SF-P corpus: {len(vectors)} vectors, "
          f"{len(seen)} unique IDs, 1 out-of-profile case; schema and trace checks only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
