"""Executable CCAM v0.1 reference machine.

This is a specification prototype, not a production runtime or a verified
implementation. See docs/architecture/CCAM.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MIN_I64 = -(1 << 63)
MAX_I64 = (1 << 63) - 1
VALID_TYPES = {"int", "bool"}
VALID_RETURNS = {"int", "bool", "void"}


class InvalidProgram(ValueError):
    """The bytecode description is structurally malformed."""


@dataclass(frozen=True)
class MachineTrap(Exception):
    code: str
    function: str
    pc: int
    detail: str = ""

    def __str__(self) -> str:
        suffix = f": {self.detail}" if self.detail else ""
        return f"{self.code} in {self.function} at pc {self.pc}{suffix}"


@dataclass
class Function:
    name: str
    register_types: list[str]
    parameter_count: int
    return_type: str
    code: list[dict[str, Any]]


@dataclass
class Frame:
    function: Function
    pc: int
    registers: list[Any]
    caller_dst: int | None


def _is_i64(value: Any) -> bool:
    return type(value) is int and MIN_I64 <= value <= MAX_I64


def _is_bool(value: Any) -> bool:
    return type(value) is bool


def _matches(value: Any, typ: str) -> bool:
    return _is_i64(value) if typ == "int" else _is_bool(value)


def _require_keys(ins: dict[str, Any], required: set[str]) -> None:
    if set(ins) != required | {"op"}:
        missing = sorted(required - set(ins))
        extra = sorted(set(ins) - required - {"op"})
        raise InvalidProgram(f"{ins.get('op')}: missing={missing}, extra={extra}")


def _index(value: Any, upper: int, what: str) -> None:
    if type(value) is not int or not 0 <= value < upper:
        raise InvalidProgram(f"invalid {what}: {value!r}")


def validate(program: dict[str, Any]) -> dict[str, Function]:
    if not isinstance(program, dict) or set(program) != {"entry", "functions"}:
        raise InvalidProgram("program must contain exactly entry and functions")
    if not isinstance(program["entry"], str) or not isinstance(program["functions"], list):
        raise InvalidProgram("invalid entry or functions")
    functions: dict[str, Function] = {}
    for raw in program["functions"]:
        if not isinstance(raw, dict) or set(raw) != {
            "name", "register_types", "parameter_count", "return_type", "code"
        }:
            raise InvalidProgram("malformed function descriptor")
        name, types = raw["name"], raw["register_types"]
        params, ret, code = raw["parameter_count"], raw["return_type"], raw["code"]
        if not isinstance(name, str) or not name or name in functions:
            raise InvalidProgram(f"invalid or duplicate function name: {name!r}")
        if not isinstance(types, list) or any(t not in VALID_TYPES for t in types):
            raise InvalidProgram(f"{name}: invalid register type vector")
        if type(params) is not int or not 0 <= params <= len(types):
            raise InvalidProgram(f"{name}: invalid parameter count")
        if ret not in VALID_RETURNS or not isinstance(code, list) or not code:
            raise InvalidProgram(f"{name}: invalid return type or empty code")
        functions[name] = Function(name, types, params, ret, code)
    if program["entry"] not in functions:
        raise InvalidProgram("entry function does not exist")

    # Validate instruction shape, register operands, branch targets, and calls.
    schemas = {
        "const_i": {"dst", "value"}, "const_b": {"dst", "value"},
        "move": {"dst", "src"},
        "add_i": {"dst", "lhs", "rhs"}, "sub_i": {"dst", "lhs", "rhs"},
        "mul_i": {"dst", "lhs", "rhs"}, "div_i": {"dst", "lhs", "rhs"},
        "rem_i": {"dst", "lhs", "rhs"}, "eq_i": {"dst", "lhs", "rhs"},
        "lt_i": {"dst", "lhs", "rhs"}, "not_b": {"dst", "src"},
        "jump": {"target"}, "branch": {"cond", "if_true", "if_false"},
        "call": {"dst", "function", "args"}, "ret": {"src"},
        "ret_void": set(), "trap": {"reason"},
    }
    for fn in functions.values():
        for pc, ins in enumerate(fn.code):
            if not isinstance(ins, dict) or not isinstance(ins.get("op"), str):
                raise InvalidProgram(f"{fn.name}:{pc}: malformed instruction")
            op = ins["op"]
            if op not in schemas:
                raise InvalidProgram(f"{fn.name}:{pc}: unknown opcode {op!r}")
            _require_keys(ins, schemas[op])
            regs: list[tuple[str, str]] = []
            if op in {"const_i", "const_b"}:
                regs = [("dst", "write")]
                if op == "const_i" and not _is_i64(ins["value"]):
                    raise InvalidProgram(f"{fn.name}:{pc}: integer literal out of range")
                if op == "const_b" and not _is_bool(ins["value"]):
                    raise InvalidProgram(f"{fn.name}:{pc}: boolean literal is not bool")
            elif op == "move":
                regs = [("dst", "write"), ("src", "read")]
            elif op in {"add_i", "sub_i", "mul_i", "div_i", "rem_i", "eq_i", "lt_i"}:
                regs = [(k, "write" if k == "dst" else "read") for k in ("dst", "lhs", "rhs")]
            elif op == "not_b":
                regs = [("dst", "write"), ("src", "read")]
            elif op == "branch":
                regs = [("cond", "read")]
                for target in ("if_true", "if_false"):
                    _index(ins[target], len(fn.code), "branch target")
            elif op == "jump":
                _index(ins["target"], len(fn.code), "jump target")
            elif op == "call":
                if not isinstance(ins["function"], str) or not isinstance(ins["args"], list):
                    raise InvalidProgram(f"{fn.name}:{pc}: malformed call")
                callee = functions.get(ins["function"])
                if callee is None:
                    raise InvalidProgram(f"{fn.name}:{pc}: unknown callee")
                if len(ins["args"]) != callee.parameter_count:
                    raise InvalidProgram(f"{fn.name}:{pc}: wrong call arity")
                for arg in ins["args"]:
                    regs.append(("arg", "read"))
                    _index(arg, len(fn.register_types), "call argument register")
                if callee.return_type == "void":
                    if ins["dst"] is not None:
                        raise InvalidProgram(f"{fn.name}:{pc}: void call must have null dst")
                else:
                    if ins["dst"] is None:
                        raise InvalidProgram(f"{fn.name}:{pc}: value call requires dst")
                    regs.append(("dst", "write"))
            elif op == "ret":
                regs = [("src", "read")]
                if fn.return_type == "void":
                    raise InvalidProgram(f"{fn.name}:{pc}: value return in void function")
            elif op == "ret_void":
                if fn.return_type != "void":
                    raise InvalidProgram(f"{fn.name}:{pc}: void return in value function")
            elif op == "trap":
                if not isinstance(ins["reason"], str) or not ins["reason"]:
                    raise InvalidProgram(f"{fn.name}:{pc}: trap reason must be non-empty")
            for key, mode in regs:
                if key == "arg":
                    continue
                _index(ins[key], len(fn.register_types), "register")
            # Check declared types of register operands and destinations.
            if op == "move" and fn.register_types[ins["dst"]] != fn.register_types[ins["src"]]:
                raise InvalidProgram(f"{fn.name}:{pc}: move type mismatch")
            if op in {"add_i", "sub_i", "mul_i", "div_i", "rem_i", "eq_i", "lt_i"}:
                if fn.register_types[ins["lhs"]] != "int" or fn.register_types[ins["rhs"]] != "int":
                    raise InvalidProgram(f"{fn.name}:{pc}: integer operands required")
                want = "bool" if op in {"eq_i", "lt_i"} else "int"
                if fn.register_types[ins["dst"]] != want:
                    raise InvalidProgram(f"{fn.name}:{pc}: destination type mismatch")
            if op in {"const_i"} and fn.register_types[ins["dst"]] != "int":
                raise InvalidProgram(f"{fn.name}:{pc}: int destination required")
            if op in {"const_b", "not_b"} and fn.register_types[ins["dst"]] != "bool":
                raise InvalidProgram(f"{fn.name}:{pc}: bool destination required")
            if op == "not_b" and fn.register_types[ins["src"]] != "bool":
                raise InvalidProgram(f"{fn.name}:{pc}: bool source required")
            if op == "branch" and fn.register_types[ins["cond"]] != "bool":
                raise InvalidProgram(f"{fn.name}:{pc}: bool condition required")
            if op == "ret" and fn.register_types[ins["src"]] != fn.return_type:
                raise InvalidProgram(f"{fn.name}:{pc}: return type mismatch")
            if op == "call":
                callee = functions[ins["function"]]
                for arg, param in zip(ins["args"], callee.register_types[:callee.parameter_count]):
                    if fn.register_types[arg] != param:
                        raise InvalidProgram(f"{fn.name}:{pc}: call argument type mismatch")
                if ins["dst"] is not None and fn.register_types[ins["dst"]] != callee.return_type:
                    raise InvalidProgram(f"{fn.name}:{pc}: call destination type mismatch")
    return functions


def execute(program: dict[str, Any], args: list[Any] | None = None, *,
            max_steps: int = 100_000, max_call_depth: int = 256) -> Any:
    functions = validate(program)
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer")
    if type(max_call_depth) is not int or max_call_depth < 1:
        raise ValueError("max_call_depth must be a positive integer")
    entry = functions[program["entry"]]
    args = [] if args is None else args
    if len(args) != entry.parameter_count:
        raise ValueError("wrong entry argument count")
    if any(not _matches(v, t) for v, t in zip(args, entry.register_types)):
        raise ValueError("entry argument type mismatch")

    def trap(code: str, frame: Frame, detail: str = "") -> None:
        raise MachineTrap(code, frame.function.name, frame.pc, detail)

    frames = [Frame(entry, 0, list(args) + [None] * (len(entry.register_types) - len(args)), None)]
    steps = 0
    while frames:
        frame = frames[-1]
        fn, pc = frame.function, frame.pc
        if steps >= max_steps:
            trap("step_limit", frame)
        if not 0 <= pc < len(fn.code):
            trap("invalid_pc", frame)
        ins = fn.code[pc]
        op = ins["op"]
        steps += 1
        frame.pc += 1

        def read(reg: int) -> Any:
            value = frame.registers[reg]
            if value is None:
                trap("uninitialised_register", frame, str(reg))
            if not _matches(value, fn.register_types[reg]):
                trap("register_type_violation", frame, str(reg))
            return value

        def write(reg: int, value: Any) -> None:
            if not _matches(value, fn.register_types[reg]):
                trap("register_type_violation", frame, str(reg))
            frame.registers[reg] = value

        if op == "const_i" or op == "const_b":
            write(ins["dst"], ins["value"])
        elif op == "move":
            write(ins["dst"], read(ins["src"]))
        elif op in {"add_i", "sub_i", "mul_i", "div_i", "rem_i", "eq_i", "lt_i"}:
            a, b = read(ins["lhs"]), read(ins["rhs"])
            if op == "add_i": result = a + b
            elif op == "sub_i": result = a - b
            elif op == "mul_i": result = a * b
            elif op in {"div_i", "rem_i"}:
                if b == 0: trap("division_by_zero", frame)
                if a == MIN_I64 and b == -1: trap("integer_overflow", frame)
                q = abs(a) // abs(b) * (-1 if (a < 0) != (b < 0) else 1)
                result = q if op == "div_i" else a - q * b
            elif op == "eq_i": result = a == b
            else: result = a < b
            if op in {"add_i", "sub_i", "mul_i"} and not MIN_I64 <= result <= MAX_I64:
                trap("integer_overflow", frame)
            write(ins["dst"], result)
        elif op == "not_b":
            write(ins["dst"], not read(ins["src"]))
        elif op == "jump":
            frame.pc = ins["target"]
        elif op == "branch":
            frame.pc = ins["if_true"] if read(ins["cond"]) else ins["if_false"]
        elif op == "call":
            callee = functions[ins["function"]]
            call_args = [read(r) for r in ins["args"]]
            if len(frames) >= max_call_depth:
                trap("call_depth_limit", frame)
            new_regs = call_args + [None] * (len(callee.register_types) - len(call_args))
            frames.append(Frame(callee, 0, new_regs, ins["dst"]))
        elif op == "ret" or op == "ret_void":
            result = read(ins["src"]) if op == "ret" else None
            frames.pop()
            if not frames:
                return result
            caller = frames[-1]
            if frame.caller_dst is not None:
                if result is None:
                    trap("invalid_return", caller, "missing call result")
                caller.registers[frame.caller_dst] = result
        elif op == "trap":
            trap(ins["reason"], frame)
        else:  # validate() makes this unreachable; retain defensive failure.
            trap("unknown_opcode", frame, op)
    raise AssertionError("machine halted without returning")
