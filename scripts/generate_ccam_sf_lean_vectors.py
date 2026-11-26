#!/usr/bin/env python3
"""Generate Lean profile-admission and machine-execution checks from CCAM-SF-P."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "verification" / "ccam_sf_vectors.json"
OUTPUT = ROOT / "verification" / "lean" / "CapstanVerification" / "SFVectors.lean"
MAX_VECTORS = 64
MAX_REGISTERS = 256
MAX_INSTRUCTIONS = 256
MAX_STEPS = 4096


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def require_int(value, where):
    if type(value) is not int:
        raise ValueError(f"{where}: expected integer")
    return value


def lean_integer(value, where):
    number = require_int(value, where)
    return f"({number})" if number < 0 else str(number)


def render_instruction(instruction, return_type, where):
    op = instruction["op"]

    def number(key):
        return require_int(instruction[key], f"{where}.{key}")

    if op == "const_i":
        return f'.constInt {number("dst")} {lean_integer(instruction["value"], where + ".value")}'
    if op == "const_b":
        if type(instruction["value"]) is not bool:
            raise ValueError(f"{where}.value: expected boolean")
        value = "true" if instruction["value"] else "false"
        return f'.constBool {number("dst")} {value}'
    if op == "move":
        return f'.move {number("dst")} {number("src")}'
    if op in ("add_i", "sub_i", "mul_i", "div_i", "rem_i",
              "lt_i", "eq_i"):
        constructor = {
            "add_i": "add", "sub_i": "sub", "mul_i": "mul",
            "div_i": "div", "rem_i": "rem",
            "lt_i": "lessThan", "eq_i": "equal"
        }[op]
        return (f'.{constructor} {number("dst")} '
                f'{number("lhs")} {number("rhs")}')
    if op == "not_b":
        return f'.booleanNot {number("dst")} {number("src")}'
    if op == "jump":
        return f'.jump {number("target")}'
    if op == "branch":
        return (f'.branch {number("cond")} '
                f'{number("if_true")} {number("if_false")}')
    if op == "ret":
        if return_type == "int":
            return f'.retInt {number("src")}'
        if return_type == "bool":
            return f'.retBool {number("src")}'
        raise ValueError(f"{where}: ret with void return type")
    if op == "ret_void":
        return ".retVoid"
    raise ValueError(f"{where}: unsupported instruction {op}")


def render_expected_run(vector, program_name):
    vector_id = vector["id"]
    suffix = "".join(ch for ch in vector_id if ch.isalnum())
    limit = require_int(vector["max_steps"], f"{vector_id}.max_steps")
    expected = vector["expected"]
    if expected["profile_validation"] == "reject":
        return [
            f"theorem sfP_run_{suffix} :",
            f"    (runSFProfileVector {program_name} {limit}).isNone = true := by decide"
        ]
    outcome = expected.get("outcome")
    if not isinstance(outcome, dict):
        raise ValueError(f"{vector_id}: accepted vector requires an outcome")
    steps = require_int(expected["steps"], f"{vector_id}.steps")
    trace = expected.get("trace_pcs")
    if not isinstance(trace, list):
        raise ValueError(f"{vector_id}: missing trace_pcs")
    trace_text = "[" + ", ".join(str(require_int(x, f"{vector_id}.trace_pcs")) for x in trace) + "]"
    kind = outcome.get("kind")
    if kind == "halt":
        value = outcome["value"]
        if value["type"] == "int":
            val = f'.int {lean_integer(value["value"], vector_id + ".outcome.value")}'
        elif value["type"] == "bool" and type(value["value"]) is bool:
            val = f'.bool {"true" if value["value"] else "false"}'
        else:
            raise ValueError(f"{vector_id}: unsupported halt value")
        if not trace:
            raise ValueError(f"{vector_id}: halt requires a dispatched instruction")
        pc = require_int(trace[-1], f"{vector_id}.trace_pcs[-1]")
        rhs = f"some (.halt ({val}) {pc} {steps} {trace_text})"
    elif kind == "halt_void":
        if not trace:
            raise ValueError(f"{vector_id}: halt_void requires a dispatched instruction")
        pc = require_int(trace[-1], f"{vector_id}.trace_pcs[-1]")
        rhs = f"some (.haltVoid {pc} {steps} {trace_text})"
    elif kind == "trap":
        trap_map = {
            "integer_overflow": "integerOverflow",
            "division_by_zero": "divisionByZero",
            "uninitialised_register": "uninitialisedRegister",
            "step_limit_exceeded": "instructionLimit"
        }
        code = outcome.get("code")
        if code not in trap_map:
            raise ValueError(f"{vector_id}: unsupported trap code {code}")
        pc = require_int(outcome["pc"], f"{vector_id}.outcome.pc")
        rhs = f"some (.trap .{trap_map[code]} {pc} {steps} {trace_text})"
    else:
        raise ValueError(f"{vector_id}: unsupported outcome kind {kind}")
    return [
        f"theorem sfP_run_{suffix} :",
        f"    runSFProfileVector {program_name} {limit} = {rhs} := by decide"
    ]


def generate(data):
    vectors = data.get("vectors")
    if not isinstance(vectors, list) or not vectors or len(vectors) > MAX_VECTORS:
        raise ValueError(f"corpus vectors must contain 1..{MAX_VECTORS} entries")
    lines = [
        "-- Generated from verification/ccam_sf_vectors.json.",
        "-- Regenerate with scripts/generate_ccam_sf_lean_vectors.py.",
        "-- This checks Lean profile admission and model execution, not concrete refinement.",
        "import CapstanVerification.ProgramValidator",
        "",
        "namespace CapstanVerification",
        "",
        "inductive SFRunOutcome where",
        "  | halt (value : Val) (pc steps : Nat) (trace : List Nat)",
        "  | haltVoid (pc steps : Nat) (trace : List Nat)",
        "  | trap (reason : Trap) (pc steps : Nat) (trace : List Nat)",
        "  deriving DecidableEq, Repr",
        "",
        "/-- Run the typed single-frame machine with the corpus instruction budget. -/",
        "def runBudgetedSFMachine {n m : Nat} {types : RegTypes n}",
        "    (fuel : Nat) (program : FiniteProgram n m types)",
        "    (state : BudgetedMachineState n m types) (trace : List Nat) : SFRunOutcome :=",
        "  match fuel with",
        "  | 0 => .trap .instructionLimit state.machine.pc.val state.budget.used trace",
        "  | Nat.succ remaining =>",
        "      let currentPC := state.machine.pc.val",
        "      match budgetedMachineStep program state with",
        "      | .nextState next =>",
        "          runBudgetedSFMachine remaining program next (trace ++ [currentPC])",
        "      | .halt value budget =>",
        "          .halt value currentPC budget.used (trace ++ [currentPC])",
        "      | .haltVoid budget =>",
        "          .haltVoid currentPC budget.used (trace ++ [currentPC])",
        "      | .trap reason budget =>",
        "          if budget.used > state.budget.used then",
        "            .trap reason currentPC budget.used (trace ++ [currentPC])",
        "          else",
        "            .trap reason currentPC budget.used trace",
        "",
        "/-- Start with every register uninitialised and run a validated profile program. -/",
        "def runSFProfileProgram {n m : Nat} {types : RegTypes n}",
        "    (program : FiniteProgram n m types) (limit : Nat) : SFRunOutcome :=",
        "  let initial : BudgetedMachineState n m types :=",
        "    { machine := initialMachineState program (fun _ => none) (by",
        "        intro i v h",
        "        simp at h)",
        "      budget := { limit := limit, used := 0, within_limit := Nat.zero_le limit } }",
        "  runBudgetedSFMachine (limit + 1) program initial []",
        "",
        "/-- Rejected programs produce no executable machine outcome. -/",
        "def runSFProfileVector {n m : Nat} {types : RegTypes n}",
        "    (raw : RawSingleFrameProgram n m types) (limit : Nat) : Option SFRunOutcome := do",
        "  let program ← validateSingleFrameProfile raw",
        "  pure (runSFProfileProgram program limit)",
        ""
    ]
    seen = set()
    lean_names = set()
    for vector in vectors:
        vector_id = vector["id"]
        if not isinstance(vector_id, str) or not re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", vector_id):
            raise ValueError(f"invalid vector id: {vector_id!r}")
        if vector_id in seen:
            raise ValueError(f"duplicate vector id: {vector_id}")
        seen.add(vector_id)
        suffix = "".join(ch for ch in vector_id if ch.isalnum())
        if suffix in lean_names:
            raise ValueError(f"vector id collision after Lean name conversion: {vector_id}")
        lean_names.add(suffix)
        type_name = f"sfPTypes_{suffix}"
        program_name = f"sfPProgram_{suffix}"
        register_types = vector["register_types"]
        instructions = vector["instructions"]
        if (not isinstance(register_types, list) or len(register_types) > MAX_REGISTERS
                or not isinstance(instructions, list) or not instructions
                or len(instructions) > MAX_INSTRUCTIONS):
            raise ValueError(f"{vector_id}: register/instruction arrays exceed Lean adapter bounds")
        if any(ty not in ("int", "bool") for ty in register_types):
            raise ValueError(f"{vector_id}: unsupported register type")
        return_type = vector["return_type"]
        if return_type not in ("int", "bool", "void"):
            raise ValueError(f"{vector_id}: unsupported return type")
        entry = require_int(vector["profile_entry"], f"{vector_id}.profile_entry")
        if entry < 0:
            raise ValueError(f"{vector_id}: profile entry must be non-negative")
        max_steps = require_int(vector["max_steps"], f"{vector_id}.max_steps")
        if max_steps < 0 or max_steps > MAX_STEPS:
            raise ValueError(f"{vector_id}: max_steps exceeds Lean adapter bound {MAX_STEPS}")
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
            rendered = render_instruction(instruction, return_type, f"{vector_id}.instructions[{index}]")
            lines.append(f"    | {index} => {rendered}")
        lines.append("    | _ => .retVoid")
        lines.append(f"  entry := {entry}")
        lines.append(f"  returnType := .{return_type}")
        expected_bool = "true" if expected == "accept" else "false"
        lines.append("")
        lines.append(f"theorem sfP_profile_{suffix} :")
        lines.append(
            f"    (validateSingleFrameProfile {program_name}).isSome = {expected_bool} := by decide"
        )
        lines.append("")
        lines.extend(render_expected_run(vector, program_name))
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
        print(f"SF-P Lean profile+execution adapter current: {len(data['vectors'])} vectors")
        return 0
    OUTPUT.write_text(expected, encoding="utf-8")
    print(f"generated {OUTPUT.relative_to(ROOT)} from {len(data['vectors'])} vectors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
