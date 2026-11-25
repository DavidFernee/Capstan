#!/usr/bin/env python3
"""Strict structural and signed-integer validation for the CCAM-SF-P oracle corpus.

Python's JSON decoder maps integer tokens to arbitrary-precision ints, so signed
64-bit operands are checked without an IEEE-754 conversion.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CORPUS = Path(__file__).resolve().parents[1] / "verification" / "ccam_sf_vectors.json"
I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1

TOP_KEYS = {
    "format", "profile", "normative_specification",
    "profile_specification", "oracle_policy", "vectors", "out_of_profile",
}
VECTOR_REQUIRED = {
    "id", "name", "register_types", "return_type", "max_steps",
    "instructions", "expected",
}
VECTOR_OPTIONAL = {"profile_entry", "notes"}
INSTRUCTION_FIELDS = {
    "const_i": {"op", "dst", "value"},
    "const_b": {"op", "dst", "value"},
    "add_i": {"op", "dst", "lhs", "rhs"},
    "sub_i": {"op", "dst", "lhs", "rhs"},
    "mul_i": {"op", "dst", "lhs", "rhs"},
    "div_i": {"op", "dst", "lhs", "rhs"},
    "rem_i": {"op", "dst", "lhs", "rhs"},
    "eq_i": {"op", "dst", "lhs", "rhs"},
    "lt_i": {"op", "dst", "lhs", "rhs"},
    "branch": {"op", "cond", "if_true", "if_false"},
    "jump": {"op", "target"},
    "move": {"op", "dst", "src"},
    "not_b": {"op", "dst", "src"},
    "ret": {"op", "src"},
    "ret_void": {"op"},
    "trap": {"op", "reason"},
}


def reject_constant(value: str):
    raise ValueError(f"non-JSON numeric constant: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def check_i64(value, where: str) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        require(I64_MIN <= value <= I64_MAX,
                f"{where}: integer {value} is outside signed-64 range")


def check_trace(record, where: str, instruction_count: int | None = None) -> None:
    if not isinstance(record, dict):
        return
    trace = record.get("trace_pcs")
    steps = record.get("steps")
    if trace is not None or steps is not None:
        require(isinstance(trace, list), f"{where}: trace_pcs must be an array")
        require(isinstance(steps, int) and not isinstance(steps, bool),
                f"{where}: steps must be an integer")
        require(steps == len(trace),
                f"{where}: steps ({steps}) must equal dispatched PC count ({len(trace)})")
        require(all(isinstance(pc, int) and not isinstance(pc, bool) and pc >= 0
                    and (instruction_count is None or pc < instruction_count)
                    for pc in trace), f"{where}: trace PCs must be valid instruction indices")


def check_instruction(instruction, registers, instruction_count: int,
                      return_type: str, where: str, allow_trap: bool = False) -> None:
    require(isinstance(instruction, dict), f"{where}: instruction must be an object")
    op = instruction.get("op")
    require(isinstance(op, str) and op in INSTRUCTION_FIELDS,
            f"{where}: unknown opcode {op!r}")
    require(set(instruction) == INSTRUCTION_FIELDS[op],
            f"{where}: fields do not match opcode {op}")
    require(allow_trap or op != "trap",
            f"{where}: explicit trap is outside CCAM-SF-P")
    count = len(registers)

    def index(key: str, bound: int, kind: str) -> int:
        value = instruction[key]
        require(isinstance(value, int) and not isinstance(value, bool)
                and 0 <= value < bound,
                f"{where}.{key}: {kind} index out of range")
        return value

    def reg(key: str, expected: str | None = None) -> int:
        value = index(key, count, "register")
        if expected is not None:
            require(registers[value] == expected,
                    f"{where}.{key}: register {value} must have type {expected}")
        return value

    if op == "const_i":
        reg("dst", "int")
        check_i64(instruction["value"], f"{where}.value")
        require(isinstance(instruction["value"], int)
                and not isinstance(instruction["value"], bool),
                f"{where}.value: expected integer")
    elif op == "const_b":
        reg("dst", "bool")
        require(isinstance(instruction["value"], bool),
                f"{where}.value: expected boolean")
    elif op == "move":
        dst, src = reg("dst"), reg("src")
        require(registers[dst] == registers[src],
                f"{where}: move source/destination types differ")
    elif op in {"add_i", "sub_i", "mul_i", "div_i", "rem_i", "eq_i", "lt_i"}:
        reg("lhs", "int")
        reg("rhs", "int")
        reg("dst", "bool" if op in {"eq_i", "lt_i"} else "int")
    elif op == "not_b":
        reg("src", "bool")
        reg("dst", "bool")
    elif op == "jump":
        index("target", instruction_count, "branch target")
    elif op == "branch":
        reg("cond", "bool")
        index("if_true", instruction_count, "branch target")
        index("if_false", instruction_count, "branch target")
    elif op == "ret":
        src = reg("src")
        require(return_type in ("int", "bool") and registers[src] == return_type,
                f"{where}: return source type does not match return contract")
    elif op == "ret_void":
        require(return_type == "void", f"{where}: void return violates return contract")
    elif op == "trap":
        require(isinstance(instruction["reason"], str)
                and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", instruction["reason"]) is not None,
                f"{where}.reason: invalid normative explicit-trap reason")


def main() -> int:
    try:
        raw = CORPUS.read_text(encoding="utf-8")
        data = json.loads(raw, parse_int=int, parse_float=lambda x: (_ for _ in ()).throw(
            ValueError(f"floating-point token is forbidden: {x}")),
            parse_constant=reject_constant, object_pairs_hook=unique_object)

        require(isinstance(data, dict), "top-level value must be an object")
        require(set(data) == TOP_KEYS,
                f"top-level keys differ: missing={sorted(TOP_KEYS - set(data))}, "
                f"unknown={sorted(set(data) - TOP_KEYS)}")
        require(data["format"] == "capstan-ccam-sf-vectors/1", "unsupported corpus format")
        require(data["profile"] == "CCAM-SF-P", "unexpected proof profile")
        require(isinstance(data["vectors"], list), "vectors must be an array")
        require(isinstance(data["out_of_profile"], list), "out_of_profile must be an array")

        seen_ids = set()
        total = 0
        groups = (
            ("vectors", data["vectors"], VECTOR_REQUIRED, VECTOR_OPTIONAL),
            ("out_of_profile", data["out_of_profile"],
             {"id", "name", "classification", "register_types", "return_type",
              "max_steps", "instructions", "expected_concrete", "reason"}, set()),
        )
        for group_name, entries, required, optional in groups:
            for index, vector in enumerate(entries):
                where = f"{group_name}[{index}]"
                require(isinstance(vector, dict), f"{where}: vector must be an object")
                keys = set(vector)
                require(required <= keys <= required | optional,
                        f"{where}: missing={sorted(required - keys)}, "
                        f"unknown={sorted(keys - required - optional)}")
                ident = vector["id"]
                require(isinstance(ident, str) and re.fullmatch(r"SF-(?:X)?[0-9]{2,3}", ident),
                        f"{where}: invalid vector ID")
                require(ident not in seen_ids, f"duplicate vector ID: {ident}")
                seen_ids.add(ident)
                total += 1

                require(isinstance(vector["register_types"], list), f"{where}: register_types must be an array")
                require(all(t in ("int", "bool") for t in vector["register_types"]),
                        f"{where}: unsupported register type")
                require(vector["return_type"] in ("int", "bool", "void"),
                        f"{where}: unsupported return type")
                require(isinstance(vector["max_steps"], int) and
                        not isinstance(vector["max_steps"], bool) and vector["max_steps"] >= 0,
                        f"{where}: max_steps must be a non-negative integer")
                if group_name == "vectors":
                    require("profile_entry" in vector,
                            f"{where}: proof-profile vector requires profile_entry")
                if "profile_entry" in vector:
                    entry = vector["profile_entry"]
                    require(isinstance(entry, int) and not isinstance(entry, bool)
                            and 0 <= entry < len(vector["instructions"]),
                            f"{where}: profile_entry must identify an instruction")

                require(isinstance(vector["instructions"], list) and vector["instructions"],
                        f"{where}: instructions must be a non-empty array")
                for pc, instruction in enumerate(vector["instructions"]):
                    iw = f"{where}.instructions[{pc}]"
                    check_instruction(
                        instruction, vector["register_types"], len(vector["instructions"]),
                        vector["return_type"], iw, allow_trap=(group_name == "out_of_profile"))

                if group_name == "vectors":
                    expected = vector["expected"]
                    require(isinstance(expected, dict), f"{where}: expected must be an object")
                    allowed_expected = {
                        "profile_validation", "normative_validation", "outcome",
                        "trace_pcs", "steps", "profile_execution", "normative_execution",
                        "expected_concrete",
                    }
                    require(set(expected) <= allowed_expected,
                            f"{where}.expected: unknown fields {sorted(set(expected) - allowed_expected)}")
                    require(expected.get("profile_validation") in {"accept", "reject"},
                            f"{where}: invalid profile_validation")
                    require(expected.get("normative_validation") in {"accept", "reject", "not_applicable"},
                            f"{where}: invalid normative_validation")
                    if vector.get("profile_entry") != 0:
                        require(expected["profile_validation"] == "reject"
                                and expected["normative_validation"] == "not_applicable",
                                f"{where}: nonzero profile entry must be explicitly out of normative scope and rejected by SF-P")
                    if expected["profile_validation"] == "reject":
                        require(expected.get("outcome", {}).get("kind") == "not_executed"
                                and expected.get("trace_pcs") == [] and expected.get("steps") == 0,
                                f"{where}: profile-rejected vector must not execute")
                    for name in ("profile_execution", "normative_execution", "expected_concrete"):
                        if name in expected:
                            check_trace(expected[name], f"{where}.{name}", len(vector["instructions"]))
                    check_trace(expected, f"{where}.expected", len(vector["instructions"]))
                else:
                    check_trace(vector["expected_concrete"], f"{where}.expected_concrete",
                                len(vector["instructions"]))

        # Check every integer in the parsed corpus, including instruction operands,
        # PCs, budgets and expected values. Python preserves the exact JSON token.
        def walk(value, path="$"):
            if isinstance(value, dict):
                for key, child in value.items():
                    walk(child, f"{path}.{key}")
            elif isinstance(value, list):
                for i, child in enumerate(value):
                    walk(child, f"{path}[{i}]")
            else:
                check_i64(value, path)

        walk(data)
        print(f"CCAM-SF-P corpus: {total} unique vectors; strict JSON, schema, trace and signed-64 checks passed")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"CCAM-SF-P corpus validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
