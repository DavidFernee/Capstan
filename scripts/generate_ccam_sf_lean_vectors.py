#!/usr/bin/env python3
"""Generate Lean profile-admission checks from the canonical CCAM-SF-P JSON corpus."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "verification" / "ccam_sf_vectors.json"
OUTPUT = ROOT / "verification" / "lean" / "CapstanVerification" / "SFVectors.lean"


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def render_instruction(instruction, return_type):
    op = instruction["op"]
    if op == "const_i":
        return f'.constInt {instruction["dst"]} {instruction["value"]}'
    if op == "const_b":
        value = "true" if instruction["value"] else "false"
        return f'.constBool {instruction["dst"]} {value}'
    if op == "move":
        return f'.move {instruction["dst"]} {instruction["src"]}'
    if op in ("add_i", "sub_i", "mul_i", "div_i", "rem_i",
              "lt_i", "eq_i"):
        constructor = {
            "add_i": "add", "sub_i": "sub", "mul_i": "mul",
            "div_i": "div", "rem_i": "rem",
            "lt_i": "lessThan", "eq_i": "equal"
        }[op]
        return (f'.{constructor} {instruction["dst"]} '
                f'{instruction["lhs"]} {instruction["rhs"]}')
    if op == "not_b":
        return f'.booleanNot {instruction["dst"]} {instruction["src"]}'
    if op == "jump":
        return f'.jump {instruction["target"]}'
    if op == "branch":
        return (f'.branch {instruction["cond"]} '
                f'{instruction["if_true"]} {instruction["if_false"]}')
    if op == "ret":
        if return_type == "int":
            return f'.retInt {instruction["src"]}'
        if return_type == "bool":
            return f'.retBool {instruction["src"]}'
        raise ValueError("ret with void return type")
    if op == "ret_void":
        return ".retVoid"
    raise ValueError(f"unsupported corpus instruction: {op}")


def generate(data):
    vectors = data.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        raise ValueError("corpus vectors must be a non-empty array")
    lines = [
        "-- Generated from verification/ccam_sf_vectors.json.",
        "-- Regenerate with scripts/generate_ccam_sf_lean_vectors.py.",
        "-- This checks Lean profile admission only; it is not an evaluator-refinement proof.",
        "import CapstanVerification.ProgramValidator",
        "",
        "namespace CapstanVerification",
        ""
    ]
    seen = set()
    for vector in vectors:
        vector_id = vector["id"]
        if vector_id in seen:
            raise ValueError(f"duplicate vector id: {vector_id}")
        seen.add(vector_id)
        suffix = "".join(ch for ch in vector_id if ch.isalnum())
        type_name = f"sfPTypes_{suffix}"
        program_name = f"sfPProgram_{suffix}"
        register_types = vector["register_types"]
        instructions = vector["instructions"]
        if not instructions:
            raise ValueError(f"{vector_id}: empty instruction list")
        if any(ty not in ("int", "bool") for ty in register_types):
            raise ValueError(f"{vector_id}: unsupported register type")
        if vector["return_type"] not in ("int", "bool", "void"):
            raise ValueError(f"{vector_id}: unsupported return type")
        expected = vector["expected"]["profile_validation"]
        if expected not in ("accept", "reject"):
            raise ValueError(f"{vector_id}: invalid profile expectation")
        count = len(register_types)
        last = len(instructions) - 1
        lines.append(f"def {type_name} : RegTypes {count} := fun i =>")
        if count == 0:
            lines.append("  nomatch i")
        else:
            lines.append("  match i.val with")
            for index, ty in enumerate(register_types):
                lines.append(f"  | {index} => .{ty}")
            lines.append("  | _ => .int")
        lines.append("")
        lines.append(
            f"def {program_name} : RawSingleFrameProgram {count} {last} {type_name} where"
        )
        lines.append("  code := fun pc =>")
        lines.append("    match pc.val with")
        for index, instruction in enumerate(instructions):
            rendered = render_instruction(instruction, vector["return_type"])
            lines.append(f"    | {index} => {rendered}")
        lines.append("    | _ => .retVoid")
        lines.append(f'  entry := {vector["profile_entry"]}')
        lines.append(f'  returnType := .{vector["return_type"]}')
        expected_bool = "true" if expected == "accept" else "false"
        lines.append("")
        lines.append(f"theorem sfP_profile_{suffix} :")
        lines.append(
            f"    (validateSingleFrameProfile {program_name}).isSome = {expected_bool} := by decide"
        )
        lines.append("")
    lines.append("end CapstanVerification")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="fail if the checked-in Lean file is not current")
    args = parser.parse_args()
    with CORPUS.open("r", encoding="utf-8") as stream:
        data = json.load(stream, object_pairs_hook=unique_object)
    expected = generate(data)
    if args.check:
        actual = OUTPUT.read_text(encoding="utf-8")
        if actual != expected:
            raise SystemExit("SFVectors.lean is stale; run scripts/generate_ccam_sf_lean_vectors.py")
        print(f"SF-P Lean adapter current: {len(data['vectors'])} profile vectors")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"generated {OUTPUT.relative_to(ROOT)} from {len(data['vectors'])} vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
