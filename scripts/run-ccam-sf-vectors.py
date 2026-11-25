#!/usr/bin/env python3
"""Execute the canonical CCAM-SF-P corpus against the Capstan-native evaluator.

The oracle remains the JSON corpus. This driver generates temporary Capstan test
source, invokes the repository's own interpreter/test runner, and compares the
exact dispatched-PC trace, step count, terminal PC, trap, and return payload.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "verification" / "ccam_sf_vectors.json"
VALIDATOR = ROOT / "scripts" / "validate-ccam-sf-vectors.py"
CAPSTAN = ROOT / "bin" / "capstan"

OPS = {
    "const_i": ("CCAM_OP_CONST_I", {"dst": "dst", "value": "int_value"}),
    "const_b": ("CCAM_OP_CONST_B", {"dst": "dst", "value": "bool_value"}),
    "add_i": ("CCAM_OP_ADD_I", {"dst": "dst", "lhs": "lhs", "rhs": "rhs"}),
    "sub_i": ("CCAM_OP_SUB_I", {"dst": "dst", "lhs": "lhs", "rhs": "rhs"}),
    "mul_i": ("CCAM_OP_MUL_I", {"dst": "dst", "lhs": "lhs", "rhs": "rhs"}),
    "div_i": ("CCAM_OP_DIV_I", {"dst": "dst", "lhs": "lhs", "rhs": "rhs"}),
    "rem_i": ("CCAM_OP_REM_I", {"dst": "dst", "lhs": "lhs", "rhs": "rhs"}),
    "eq_i": ("CCAM_OP_EQ_I", {"dst": "dst", "lhs": "lhs", "rhs": "rhs"}),
    "lt_i": ("CCAM_OP_LT_I", {"dst": "dst", "lhs": "lhs", "rhs": "rhs"}),
    "branch": ("CCAM_OP_BRANCH", {"cond": "lhs", "if_true": "if_true", "if_false": "if_false"}),
    "jump": ("CCAM_OP_JUMP", {"target": "target"}),
    "move": ("CCAM_OP_MOVE", {"dst": "dst", "src": "src"}),
    "not_b": ("CCAM_OP_NOT_B", {"dst": "dst", "src": "lhs"}),
    "ret": ("CCAM_OP_RET", {"src": "lhs"}),
    "ret_void": ("CCAM_OP_RET_VOID", {}),
    "trap": ("CCAM_OP_TRAP", {"reason": "reason"}),
}
RETURN_TYPES = {"int": "CCAM_RETURN_INT", "bool": "CCAM_RETURN_BOOL",
                "void": "CCAM_RETURN_VOID"}
REGISTER_TYPES = {"int": "CCAM_TYPE_INT", "bool": "CCAM_TYPE_BOOL"}


def literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if value == -(1 << 63):
            return "CCAM_I64_MIN"
        if value == (1 << 63) - 1:
            return "CCAM_I64_MAX"
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    raise ValueError(f"unsupported Capstan literal: {type(value).__name__}")


def instruction_source(instruction: dict, index: int) -> list[str]:
    op = instruction["op"]
    opcode, fields = OPS[op]
    variable = f"instruction_{index}"
    lines = [f"    CCAMInstruction {variable} = ccam_instruction({opcode});"]
    for source_field, target_field in fields.items():
        lines.append(f"    {variable}.{target_field} = {literal(instruction[source_field])};")
    lines.append(f"    code.push({variable});")
    return lines


def vector_test(vector: dict) -> str:
    ident = vector["id"]
    expected = vector["expected"]
    accepted = expected["profile_validation"] == "accept"
    lines = [f'test "CCAM-SF-P corpus {ident}" {{',
             "    List<int> register_types = new List<int>();"]
    for ty in vector["register_types"]:
        lines.append(f"    register_types.push({REGISTER_TYPES[ty]});")
    lines.append("    List<CCAMInstruction> code = new List<CCAMInstruction>();")
    for index, instruction in enumerate(vector["instructions"]):
        lines.extend(instruction_source(instruction, index))
    lines.extend([
        "    CCAMMachineCreateResult created = ccam_machine_create_validated(",
        f"        register_types, code, {vector['max_steps']}, {RETURN_TYPES[vector['return_type']]});",
    ])
    if not accepted:
        lines.extend([
            "    assert(!created.ok);",
            "    assert(created.state.steps == 0);",
            "    assert(created.state.instructions.len() == 0);",
            "    ccam_machine_step(created.state);",
            "    assert(created.state.steps == 0);",
            "}",
        ])
        return "\n".join(lines)

    outcome = expected["outcome"]
    lines.extend([
        "    assert(created.ok);",
        "    CCAMMachineState state = created.state;",
        "    List<int> trace = new List<int>();",
        "    while (!state.halted) {",
        "        int before_pc = state.pc;",
        "        int before_steps = state.steps;",
        "        ccam_machine_step(state);",
        "        if (state.steps == before_steps + 1) { trace.push(before_pc); }",
        "    }",
        f"    assert(state.steps == {expected['steps']});",
        f"    assert(trace.len() == {len(expected['trace_pcs'])});",
    ])
    for index, pc in enumerate(expected["trace_pcs"]):
        lines.append(f"    assert(trace[{index}] == {pc});")

    if outcome["kind"] == "halt":
        value = outcome["value"]
        lines.append(f"    assert(state.pc == {expected['trace_pcs'][-1]});")
        lines.append('    assert(state.halted && state.trap_code == "");')
        lines.append("    assert(state.halt_has_value);")
        lines.append('    assert(state.trap_detail == "");')
        if value["type"] == "int":
            lines.append(f"    assert(state.halt_value == {value['value']});")
            lines.append("    assert(!state.halt_bool_value);")
        else:
            lines.append("    assert(state.halt_value == 0);")
            lines.append(f"    assert(state.halt_bool_value == {literal(value['value'])});")
    elif outcome["kind"] == "halt_void":
        lines.extend([
            f"    assert(state.pc == {expected['trace_pcs'][-1]});",
            "    assert(state.halted && state.trap_code == \"\");",
            "    assert(!state.halt_has_value);",
            "    assert(state.halt_value == 0 && !state.halt_bool_value);",
            '    assert(state.trap_detail == "");',
        ])
    elif outcome["kind"] == "trap":
        lines.extend([
            f"    assert(state.halted && state.trap_code == {literal(outcome['code'])});",
            f"    assert(state.pc == {outcome['pc']});",
            "    assert(!state.halt_has_value);",
            "    assert(state.halt_value == 0 && !state.halt_bool_value);",
            '    assert(state.trap_detail == "");',
        ])
    else:
        raise ValueError(f"{ident}: unsupported admitted outcome {outcome['kind']}")
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    if not CAPSTAN.is_file():
        print(f"missing Capstan runner: {CAPSTAN}", file=sys.stderr)
        return 2
    validation = subprocess.run(
        [sys.executable, "-I", str(VALIDATOR)],
        cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if validation.returncode:
        print(validation.stdout, file=sys.stderr)
        return validation.returncode

    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    admitted = [v for v in corpus["vectors"]
                if v["expected"]["profile_validation"] == "accept"]
    rejected = [v for v in corpus["vectors"]
                if v["expected"]["profile_validation"] == "reject"
                and v["expected"]["normative_validation"] == "reject"
                and v["profile_entry"] == 0]
    expected_ids = {f"SF-{i:03d}" for i in range(1, 21)} | {
        "SF-021", "SF-022", "SF-023"}
    out_of_profile_ids = {"SF-X01"}
    actual_ids = {v["id"] for v in corpus["vectors"]}
    actual_out_of_profile_ids = {v["id"] for v in corpus["out_of_profile"]}
    if (actual_ids != expected_ids or actual_out_of_profile_ids != out_of_profile_ids
            or len(admitted) != 17 or len(rejected) != 4):
        print(f"unexpected corpus partition: vectors={sorted(actual_ids)}, "
              f"out_of_profile={sorted(actual_out_of_profile_ids)}, "
              f"admitted={len(admitted)}, rejected={len(rejected)}",
              file=sys.stderr)
        return 2
    by_id = {v["id"]: v for v in corpus["vectors"]}
    if (by_id["SF-019"]["expected"]["profile_execution"]["kind"] != "not_run"
            or by_id["SF-019"]["expected"]["normative_validation"] != "accept"
            or by_id["SF-020"]["expected"]["normative_validation"] != "not_applicable"
            or by_id["SF-020"]["profile_entry"] == 0):
        print("normative-only or Lean-only vector disposition changed", file=sys.stderr)
        return 2
    if any(v["profile_entry"] != 0 for v in admitted):
        print("admitted vector has nonzero proof-profile entry", file=sys.stderr)
        return 2

    generated = "\n\n".join(vector_test(v) for v in admitted + rejected) + "\n"
    build_dir = ROOT / "build"
    build_dir.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".cap",
                                     prefix="ccam-sf-", dir=build_dir, delete=False) as handle:
        handle.write(generated)
        generated_path = Path(handle.name)
    try:
        try:
            result = subprocess.run(
                [str(CAPSTAN), "test", str(ROOT / "verification" / "ccam_core.cap"),
                 str(generated_path)],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            captured = exc.stdout or b""
            if isinstance(captured, bytes):
                captured = captured.decode("utf-8", errors="replace")
            print(captured, end="", file=sys.stderr)
            print("CCAM-SF-P concrete evaluator exceeded the 120-second harness timeout",
                  file=sys.stderr)
            return 124
        print(result.stdout, end="")
        if result.returncode:
            return result.returncode
    finally:
        generated_path.unlink(missing_ok=True)

    print(f"CCAM-SF-P concrete evaluator: {len(admitted)} admitted vectors executed; "
          f"{len(rejected)} rejected vectors confirmed non-executable")
    print("SF-019 (normative-only), SF-020 (Lean/profile-only), and SF-X01 "
          "(out-of-profile explicit trap) intentionally excluded from this driver.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
