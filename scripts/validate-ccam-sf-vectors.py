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


def check_trace(record, where: str) -> None:
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
                    for pc in trace), f"{where}: trace PCs must be non-negative integers")


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
                if "profile_entry" in vector:
                    require(isinstance(vector["profile_entry"], int) and
                            not isinstance(vector["profile_entry"], bool) and
                            vector["profile_entry"] >= 0, f"{where}: invalid profile_entry")

                require(isinstance(vector["instructions"], list) and vector["instructions"],
                        f"{where}: instructions must be a non-empty array")
                for pc, instruction in enumerate(vector["instructions"]):
                    iw = f"{where}.instructions[{pc}]"
                    require(isinstance(instruction, dict), f"{iw}: instruction must be an object")
                    op = instruction.get("op")
                    require(op in INSTRUCTION_FIELDS, f"{iw}: unknown opcode {op!r}")
                    require(set(instruction) == INSTRUCTION_FIELDS[op],
                            f"{iw}: fields do not match opcode {op}")

                if group_name == "vectors":
                    expected = vector["expected"]
                    require(isinstance(expected, dict), f"{where}: expected must be an object")
                    for name in ("profile_execution", "normative_execution", "expected_concrete"):
                        if name in expected:
                            check_trace(expected[name], f"{where}.{name}")
                    check_trace(expected, f"{where}.expected")
                else:
                    check_trace(vector["expected_concrete"], f"{where}.expected_concrete")

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
