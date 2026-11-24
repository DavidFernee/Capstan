# Capstan Core Abstract Machine (CCAM) v0.1

**Status:** executable prototype specification; deliberately a small subset, not yet the complete Capstan semantics.

This document is normative for the prototype in `verification/reference_machine.py`. If the implementation and this document disagree, the discrepancy is a defect to resolve; the implementation is not allowed to redefine the semantics silently.

## 1. Design boundary

CCAM is a typed, register-based abstract machine. A compiler lowers a checked Capstan core program into a finite collection of functions containing basic-block control flow and explicit operations. The machine is independent of C, C ABIs, host integer overflow, and host evaluation order.

This initial version deliberately includes only:
- signed 64-bit integers and booleans;
- typed function-local registers;
- checked integer arithmetic and comparisons;
- unconditional and conditional control flow;
- direct function calls and returns;
- explicit traps;
- deterministic instruction and call-depth limits.

It does **not** yet model strings, heap objects, collections, GC, taint, secrets, policies/grants, IO, concurrency, or cryptographic services. Those are not implicitly safe or absent from Capstan; they are excluded from this first executable slice and must be added as separately specified machine features.

## 2. Values and types

The machine value domain is the disjoint union:
`Value ::= Int64(n) | Bool(b)`

where `-2^63 <= n <= 2^63-1` and `b` is exactly true or false. Booleans are not integers. No implicit coercion exists.

A register file is a finite vector with a fixed type vector `register_types` whose entries are `"int"` or `"bool"`. Every register is initially uninitialised. Reading an uninitialised register traps. A write must match the declared register type.

Each function declares:
- a unique name;
- a register type vector;
- a parameter count;
- a return type (`"int"`, `"bool"`, or `"void"`);
- a sequence of instructions.

The first `parameter_count` registers are parameters. At invocation, argument count and types must match those registers exactly. All other registers begin uninitialised.

## 3. Instruction set

Each instruction is a JSON object with an `op` field. Register and instruction indices are zero-based.

| Instruction | Fields | Semantics |
|---|---|---|
| `const_i` | `dst, value` | Write integer literal after signed-64 range validation. |
| `const_b` | `dst, value` | Write boolean literal. |
| `move` | `dst, src` | Copy a value of the same declared register type. |
| `add_i`, `sub_i`, `mul_i` | `dst, lhs, rhs` | Signed-64 arithmetic; trap on overflow. |
| `div_i`, `rem_i` | `dst, lhs, rhs` | Truncation-toward-zero division/remainder; trap on zero divisor and MIN/-1 overflow. |
| `eq_i`, `lt_i` | `dst, lhs, rhs` | Integer equality / signed less-than; write bool. |
| `not_b` | `dst, src` | Boolean negation. |
| `jump` | `target` | Set PC to target instruction. |
| `branch` | `cond, if_true, if_false` | Read bool and select target PC. |
| `call` | `dst, function, args` | Invoke named function. `dst` is a register index or null for void. Arguments are register indices. |
| `ret` | `src` | Return the value in src from the current function. |
| `ret_void` | none | Return from a void function. |
| `trap` | `reason` | Terminate execution with the named explicit trap. |

A function may not fall off the end of its instruction sequence. Every branch/jump target must be within the function. Calls must name an existing function. Structural validation is performed before execution. Dynamic checks remain mandatory even for validated programs.

## 4. Arithmetic semantics

Let `MIN = -2^63` and `MAX = 2^63-1`. For addition, subtraction and multiplication, calculate the mathematical integer result (r). If (r < MIN) or (r > MAX), execution traps with `integer_overflow`; otherwise the result is `Int64(r)`.

Division truncates toward zero. Remainder is defined by (a = q b + r), where (q) is truncation-toward-zero division and (|r| < |b|). Division or remainder by zero traps with `division_by_zero`. `MIN / -1` traps with `integer_overflow`.

No operation wraps, saturates, or depends on host-language overflow behaviour.

## 5. Small-step machine state

A machine state consists of:
- a stack of frames;
- each frame's function, program counter, register vector, and optional caller destination;
- a monotonically increasing instruction-step counter;
- configured maximum steps and maximum call depth.

The active frame is the top of the stack. One transition executes exactly one instruction and increments the step counter. A call pushes a new frame and transfers control to its first instruction. A return pops the frame and writes its result to the caller destination (if present). Returning from the entry function produces the final value. Reaching the step or call-depth limit traps deterministically.

This prototype's interpreter may use host data structures to represent the abstract state, but those structures are not part of the machine semantics.

## 6. Observable outcomes

Execution returns either:
- `Halt(value)` for a successful entry-function return; or
- `Trap(code, pc, function)` for a defined machine trap.

The prototype API raises `MachineTrap` carrying the same information. Host exceptions must not leak as language-level outcomes; malformed program descriptions are rejected as `InvalidProgram` before execution.

## 7. Determinism and evaluation order

Instructions are atomic. Operands are read left-to-right in the order listed in the instruction definition. Calls evaluate their argument register list from left to right before the callee frame is pushed. There is no unspecified operand evaluation order.

For a fixed validated program, input arguments and machine limits, execution has exactly one transition sequence and one outcome.

## 8. Initial invariants and proof obligations

The reference implementation must preserve these invariants:
1. Every frame PC is either the next instruction to execute or is immediately rejected as invalid.
2. Every initialized register contains a value matching its declared type.
3. Every caller destination is valid and has the callee's declared return type.
4. The frame stack never exceeds the configured call-depth limit.
5. The step counter never exceeds the configured instruction limit.
6. Integer values always remain in the signed-64 range.
7. No invalid register, target, function, arity, type, or return is silently accepted.

The first mechanised proof target is preservation of the register typing invariant and progress-or-trap for well-formed CCAM programs. The executable Python implementation is a reference artifact, not a proof of these theorems.

## 9. Conformance vectors

The unit tests in `verification/test_reference_machine.py` are executable conformance vectors for arithmetic boundaries, control flow, calls, register typing, traps, and resource limits. Future implementations (including a Capstan implementation and native backend) must pass the same vectors and a generated differential corpus.

## 10. Versioning

CCAM v0.1 is a deliberately narrow first slice. New value kinds, instructions, effects, heap operations, and security constructs require explicit specification changes and tests. Existing instruction meanings must not be changed incompatibly without a machine-version change.
