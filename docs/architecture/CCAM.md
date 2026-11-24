# Capstan Core Abstract Machine (CCAM) v0.1

**Status:** initial machine design; Capstan-native implementation is the required next step. This is deliberately a small subset, not yet the complete Capstan semantics.

This document defines the intended semantics for the first machine slice. Its executable implementation and conformance tests must be written in Capstan. No Python or C implementation is to serve as the normative reference.

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
| `div_i` | `dst, lhs, rhs` | Signed division truncating toward zero; trap on zero divisor and `MIN / -1` overflow. |
| `rem_i` | `dst, lhs, rhs` | Signed remainder paired with truncation-toward-zero division; trap on zero divisor; `MIN % -1` returns zero. |
| `eq_i`, `lt_i` | `dst, lhs, rhs` | Integer equality / signed less-than; write bool. |
| `not_b` | `dst, src` | Boolean negation. |
| `jump` | `target` | Set PC to target instruction. |
| `branch` | `cond, if_true, if_false` | Read bool and select target PC. |
| `call` | `dst, function, args` | Invoke named function. `dst` is a register index or null for void. Arguments are register indices. |
| `ret` | `src` | Return the value in src from the current function. |
| `ret_void` | none | Return from a void function. |
| `trap` | `reason` | Terminate execution with the named explicit trap. |

A function may not fall off the end of its instruction sequence. Every branch/jump target must be within the function. Calls must name an existing function. Structural validation MUST reject duplicate/empty function names, an absent or invalid entry, unknown type tags, invalid register or instruction indices, static operand/destination type mismatches, wrong call arity/signature, incompatible return destinations, invalid return instructions, out-of-range branch targets and any path that can fall off a function. Validation is deterministic and completes before the first instruction executes. A malformed program is a validation error, not a runtime trap. Dynamic checks remain mandatory even for validated programs, including uninitialised-register reads and resource limits.

## 4. Arithmetic semantics

Let `MIN = -2^63` and `MAX = 2^63-1`. For addition, subtraction and multiplication, calculate the mathematical integer result (r). If (r < MIN) or (r > MAX), execution traps with `integer_overflow`; otherwise the result is `Int64(r)`.

Division truncates toward zero. Remainder is defined mathematically by `a = q*b + r`, where `q` is the unbounded mathematical quotient truncated toward zero and `|r| < |b|`; a nonzero remainder has the sign of the dividend. Division or remainder by zero traps with `division_by_zero`. `MIN / -1` traps with `integer_overflow`. `MIN % -1` returns `0`: the mathematical remainder is representable even though the corresponding quotient is not. The evaluator MUST special-case this pair before using any host remainder operator that could overflow or be undefined. This preserves the existing Capstan source-language behaviour.

No operation wraps, saturates, or depends on host-language overflow behaviour.

## 5. Small-step machine state

A machine state consists of:
- a stack of frames;
- each frame's function, program counter, register vector, and optional caller destination;
- a monotonically increasing instruction-step counter;
- configured maximum steps and maximum call depth.

The active frame is the top of a non-empty stack. The entry frame counts as call depth 1. One transition executes exactly one instruction and increments the step counter, including a call, return or explicit trap. A limit of N permits N instructions; if another instruction is required after N have executed, `step_limit_exceeded` occurs before that instruction is executed. An instruction that produces a dynamic trap has still been executed and consumes its step. Structural validation is outside this budget. A call reads and checks argument registers left-to-right, then checks the call-depth limit; if pushing would exceed the configured maximum, it traps with `call_depth_exceeded` without pushing. Otherwise it advances the caller PC to the continuation and pushes a new frame. A return reads and checks its result, then validates the caller frame and destination index/type before modifying the frame stack; the callee pop and caller-destination write are one atomic transition. Returning from the entry function produces `Halt(value)` or `HaltVoid` for a void entry. Reaching a limit traps deterministically.

The executable evaluator, register files, frames, instruction sequences, and conformance tests are to be represented using Capstan types and collections. Host-language data structures or a host-language interpreter are not an acceptable implementation of CCAM. The current compiler bootstrap may temporarily be used to compile and run this Capstan source; that bootstrap boundary does not alter the implementation-language requirement.

## 6. Observable outcomes

Execution returns exactly one of:
- `Halt(value)` for a successful non-void entry-function return;
- `HaltVoid` for a successful void entry-function return; or
- `Trap(code, function, pc)` for a defined dynamic machine trap.

A complete source-program entry has zero arguments and returns `int` or `void`. Internal functions may return `int`, `bool` or `void`. Structural program errors are reported as validation failures before execution, not as dynamic traps.

The Capstan implementation must represent machine traps as explicit values or controlled results. Host exceptions must not leak as language-level outcomes; malformed program descriptions are rejected before execution.

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

The first mechanised proof target is preservation of the register typing invariant and progress-or-trap for well-formed CCAM programs. The Capstan implementation is an executable semantic artifact, not a proof of these theorems.

## 9. Conformance vectors

Conformance vectors and the machine implementation must be written in Capstan under `verification/`. The same vectors must be used by later native backends and any independent proof-assistant model.

## 10. Versioning

CCAM v0.1 is a deliberately narrow first slice. New value kinds, instructions, effects, heap operations, and security constructs require explicit specification changes and tests. Existing instruction meanings must not be changed incompatibly without a machine-version change.
