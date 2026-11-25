# Capstan Core Abstract Machine (CCAM) v0.1

**Status:** normative v0.1 design with a restricted Capstan-native single-frame evaluator merged to `main` (PR #142), a typed in-memory structural validator merged in PR #163, and a bounded multi-function call-frame evaluator integrated in PR #207. Checked scalar source lowering is integrated in PR #210. A freestanding Linux x86-64 native backend is integrated in PR #212. The implementation is not yet a conforming v0.1 machine, is not connected to the Lean model by a refinement theorem, and is not the complete Capstan semantics.

This document defines the intended semantics for the first machine slice. Its executable implementation and conformance tests must be written in Capstan. No Python or C implementation is to serve as the normative reference.

A separate non-normative proposal for bounded byte output in a future CCAM v0.2 is documented in [CCAM-IO.md](CCAM-IO.md). It does not amend v0.1 or imply that output support is implemented.



## 1. Design boundary

CCAM is a typed, register-based abstract machine. A compiler lowers a checked Capstan core program into a finite collection of functions containing basic-block control flow and explicit operations. The machine is independent of C, C ABIs, host integer overflow, and host evaluation order.

### 1.1 Current implementation boundary

`verification/ccam_core.cap` contains the first executable evaluator slice. It implements typed integer/boolean constants and moves, checked integer arithmetic, integer equality/less-than, boolean negation, jumps, conditional branches, typed integer/boolean returns, void returns, explicit traps, and deterministic instruction-step accounting. The evaluator snapshots the supplied instruction sequence before execution. Its input is an already-validated in-memory instruction sequence; this implementation does not decode JSON or perform the closed structural validation required below.

The single-frame evaluator remains the semantic execution substrate. `verification/ccam_calls.cap` adds a multi-function execution layer: bounded function tables and call-site side tables, typed parameter/argument transfer, direct calls, recursion, caller continuations, return destinations, atomic return preflight, and shared step/call-depth limits. It reuses the single-frame transition for ordinary instructions. The representation is still transitional: calls are associated with side-table records by instruction index and callee function-table index rather than the normative named-call JSON object. The validator merged in PR #163 checks an in-memory single-frame instruction subset; complete JSON decoding, duplicate-key rejection, whole-program closed-schema validation and validator soundness remain open. The multi-function evaluator is executable Capstan code but is not connected to the Lean machine or a native backend yet.

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
- a unique, non-empty name;
- a register type vector containing only `"int"` and `"bool"`;
- a parameter count in the range `0..register_types.length`;
- a return type (`"int"`, `"bool"`, or `"void"`);
- a non-empty sequence of instructions.

The first `parameter_count` registers are parameters. At invocation, argument count and types must match those registers exactly. All other registers begin uninitialised.

The machine's external data format is JSON. The closed structural schema is also published as [`ccam-v0.1.schema.json`](ccam-v0.1.schema.json); the prose rules here define the cross-field and execution constraints that JSON Schema cannot express. A JSON integer is accepted only if its mathematical value is integral and lies in the signed-64 range; booleans, strings, null and non-integral numbers are not integers. Implementations MUST parse integer tokens exactly and MUST NOT round them through IEEE-754 binary64 or another inexact numeric representation before range validation. A boolean field accepts only JSON `true` or `false`. Register and instruction indices are JSON integers in the range `0..2^63-1`; an index MUST additionally be less than the relevant finite register or instruction count. Implementations MUST check these bounds before indexing. A name is a non-empty string of Unicode scalar values with no embedded NUL. Function names are unique by exact scalar-value sequence; no locale or case folding is applied.

A register type vector is validated in full before any register file is constructed. The only valid tags are `"int"` and `"bool"`; unknown, empty, null, numeric or otherwise malformed tags are validation errors (the Capstan-native register-file substrate reports `invalid_register_type` as a validation error, never as a machine trap).

### 2.1 Program and function schemas

The program document is an object with exactly two fields: `entry:string` and `functions:array-of-function-objects`. The entry value names exactly one function in the array. Duplicate object keys are invalid at every level; a parser that silently keeps the first or last duplicate key is non-conforming.

Each function object has exactly these fields:
- `name:string`: unique non-empty function name;
- `register_types:array-of-string`: one `"int"` or `"bool"` tag per register;
- `parameter_count:integer`: number of leading parameter registers;
- `return_type:string`: exactly `"int"`, `"bool"` or `"void"`;
- `instructions:array-of-instruction-objects`: non-empty instruction sequence.

Missing or extra fields, a non-object function, a non-array register or instruction field, invalid scalar types, or an out-of-range parameter count are validation errors. The entry function MUST have zero parameters and return either `"int"` or `"void"`. Internal functions may have any supported parameter count and return `"int"`, `"bool"` or `"void"`.

The execution limits `maxSteps` and `maxDepth` are evaluator configuration, not program fields. `maxSteps` is in `0..2^63-1`; `maxDepth` is in `1..2^63-1`. Both are exact integers in the CCAM index domain. Implementations MUST reject booleans, fractional values, negative values and values above `2^63-1` before creating the entry frame.

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

### 3.1 Closed instruction schemas

Every instruction object MUST contain exactly the fields listed below: the `op` field and the required operands. Source spans and debug metadata are carried in an out-of-band side table keyed by function and instruction index; they are not instruction-object fields and cannot affect execution. Unknown fields, missing fields, duplicate JSON object keys, and fields of the wrong JSON type are validation errors. Optionality is represented explicitly as JSON `null`; omitted fields are never treated as null.

| Opcode | Exact fields and JSON types | Static constraints |
|---|---|---|
| `const_i` | `op:string, dst:integer, value:integer` | `value` is signed-64; `dst` declares `int`. |
| `const_b` | `op:string, dst:integer, value:boolean` | `dst` declares `bool`. |
| `move` | `op:string, dst:integer, src:integer` | Both registers exist and have the same declared type. |
| `add_i`, `sub_i`, `mul_i`, `div_i`, `rem_i` | `op:string, dst:integer, lhs:integer, rhs:integer` | All registers exist and declare `int`. |
| `eq_i`, `lt_i` | `op:string, dst:integer, lhs:integer, rhs:integer` | `lhs` and `rhs` declare `int`; `dst` declares `bool`. |
| `not_b` | `op:string, dst:integer, src:integer` | `src` and `dst` declare `bool`. |
| `jump` | `op:string, target:integer` | `target` is an instruction index in the same function. |
| `branch` | `op:string, cond:integer, if_true:integer, if_false:integer` | `cond` declares `bool`; both targets are in the same function. |
| `call` | `op:string, dst:integer-or-null, function:string, args:array-of-integers` | `function` exists; argument count and register types match parameters in order. `dst` is null iff the callee returns void; otherwise it is a valid register whose declared type exactly matches the callee return type. `args` contains exactly one valid register index per parameter. |
| `ret` | `op:string, src:integer` | Current function returns `int` or `bool`; `src` exists and matches that type. |
| `ret_void` | `op:string` | Current function returns `void`. |
| `trap` | `op:string, reason:string` | `reason` matches the explicit-trap grammar below. |

All instruction indices, register indices and call argument indices are checked against the owning function before execution. No opcode accepts additional fields. An opcode not listed above is invalid.

An explicit trap reason is 1–64 ASCII characters and MUST match `[a-z][a-z0-9_]{0,63}`. The machine reports it as `Trap(explicit_trap, function, pc, reason)`; it is not conflated with a built-in machine trap code. The grammar is intentionally closed to arbitrary objects, numbers, empty strings and unbounded payloads. Application-defined reasons use this grammar and do not create new machine trap classes.

A function may not fall off the end of its instruction sequence. Control-flow validation begins at instruction 0: every reachable nonterminal instruction must have an in-function successor, while a reachable infinite loop is permitted. Unreachable instructions must still satisfy their closed schema, index and static-type rules, but do not independently create a fall-through error. Every branch/jump target must be within the function. Calls must name an existing function. Structural validation MUST reject duplicate/empty function names, an absent or invalid entry, unknown type tags, invalid register or instruction indices, static operand/destination type mismatches, wrong call arity/signature, incompatible return destinations, invalid return instructions, malformed explicit-trap reasons, duplicate/unknown/missing instruction fields, out-of-range branch targets and any path that can fall off a function. Validation is deterministic and completes before the first instruction executes. A malformed program is a validation error, not a runtime trap. Dynamic checks remain mandatory even for validated programs, including uninitialised-register reads and resource limits.

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

The machine configuration requires `maxDepth` in `1..2^63-1` and `maxSteps` in `0..2^63-1`. These are execution-configuration parameters, not fields in the CCAM program JSON schema. Their transport MUST preserve exact integer values; if supplied as JSON, implementations MUST reject booleans, fractional values, negative values and values above `2^63-1` before creating the entry frame. The active frame is the top of a non-empty stack. The entry frame counts as call depth 1. One transition executes exactly one instruction and increments the step counter, including a call, return or explicit trap. A limit of N permits N instructions; if another instruction is required after N have executed, `step_limit_exceeded` occurs before that instruction is executed. An instruction that produces a dynamic trap has still been executed and consumes its step. Structural validation is outside this budget. A call reads and checks argument registers left-to-right, then checks the call-depth limit; if pushing would exceed the configured maximum, it traps with `call_depth_exceeded` without pushing. Otherwise it advances the caller PC to the continuation and pushes a new frame. A return reads and checks its result, then validates the caller frame and destination index/type before modifying the frame stack; the callee pop and caller-destination write are one atomic transition. Returning from the entry function produces `Halt(value)` or `HaltVoid` for a void entry. Reaching a limit traps deterministically.

The executable evaluator, register files, frames, instruction sequences, and conformance tests are to be represented using Capstan types and collections. Host-language data structures or a host-language interpreter are not an acceptable implementation of CCAM. The current compiler bootstrap may temporarily be used to compile and run this Capstan source; that bootstrap boundary does not alter the implementation-language requirement.

## 6. Observable outcomes

Execution returns exactly one of:
- `Halt(value)` for a successful non-void entry-function return;
- `HaltVoid` for a successful void entry-function return; or
- `Trap(code, function, pc, detail)` for a defined dynamic machine trap; `detail` is absent except for `explicit_trap`, which carries its validated reason.

A complete source-program entry has zero arguments and returns `int` or `void`. Internal functions may return `int`, `bool` or `void`. Structural program errors are reported as validation failures before execution, not as dynamic traps.

For the current in-memory single-frame subset, `ccam_validate_single_frame` checks register tags, opcode-specific register indices and types, branch targets, return contracts, and reachable fall-through. Its result is a validation error, separate from machine traps. This subset validator does not establish the full JSON or whole-program validation contract above; in particular it cannot inspect raw object keys or validate function tables and calls. It rejects more than 4,096 registers or 65,536 instructions before allocating its register-file or reachability storage; these are explicit admission limits for this implementation slice, not yet a complete whole-program or raw-input byte budget. Control-flow reachability uses a worklist and is linear in the validated instruction graph. The validated constructor rejects negative `max_steps` directly rather than delegating to the unvalidated constructor. The future decoder must separately cap raw input bytes before constructing these in-memory lists.

The initial dynamic trap codes are `integer_overflow`, `division_by_zero`, `uninitialised_register`, `invalid_register` and `register_type_mismatch` (the last two are defensive checks for conditions that validation should make unreachable), `step_limit_exceeded`, `call_depth_exceeded`, and `explicit_trap` with a validated reason detail matching `[a-z][a-z0-9_]{0,63}` (ASCII). The Capstan implementation must represent machine traps as explicit values or controlled results. Host exceptions must not leak as language-level outcomes; malformed program descriptions are rejected before execution.

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
