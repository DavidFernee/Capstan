# Typed Core IR and CCAM Contract

**Status:** normative architectural proposal for review  
**Version:** Typed Core IR v0.1  
**Owner:** Language Semantics workstream, coordinated with Compiler and Formal Verification

## 1. Decision: one initial semantic IR

For the initial C-free implementation, **CCAM is the canonical typed core IR and the reference abstract machine**. The compiler MUST lower the supported checked source subset into CCAM. The Capstan-native CCAM evaluator defines execution. A native backend MUST preserve CCAM outcomes.

Do not create a second instruction set with independently stated semantics. In particular, do not let a new SSA/CFG IR silently become the semantic authority alongside CCAM.

A later compiler may introduce a distinct optimisation IR (for example, typed SSA) if there is a demonstrated need. Such an IR is a derived representation, not a second source of truth. It MUST have:
1. a static well-formedness/type validator;
2. a formal or executable translation into CCAM;
3. a simulation/refinement argument showing preservation of values, traps, observable effects and resource semantics;
4. differential conformance tests against CCAM;
5. an explicit optimisation-correctness contract for each transformation.

## 2. Program representation

A CCAM program is a finite, immutable collection of functions plus one designated entry function. Each function contains:
- a unique stable function identifier/name;
- a fixed register-type vector;
- a parameter count;
- a return type;
- a finite instruction sequence;
- an optional out-of-band source-map side table for diagnostics and trap mapping. Source metadata is not part of the CCAM v0.1 program/instruction JSON schema and cannot affect execution.

Register and instruction indices are zero-based. Indices are local to a function. Source locations are metadata and do not affect execution semantics.

The initial value/type universe is `Int64` and `Bool`; `Void` is a return convention, not a first-class value. Unknown tags are invalid. Later extensions add new types only with explicit representation and machine rules.

## 3. Instruction contract

The initial instruction vocabulary is the CCAM v0.1 vocabulary:
- constants: `const_i`, `const_b`;
- data movement: `move`;
- arithmetic: `add_i`, `sub_i`, `mul_i`, `div_i`, `rem_i`;
- comparisons: `eq_i`, `lt_i`;
- boolean: `not_b`;
- control flow: `jump`, `branch`;
- calls and returns: `call`, `ret`, `ret_void`;
- explicit termination: `trap`.

The instruction schemas in `docs/architecture/CCAM.md` are retained, subject to the semantic corrections in `LANGUAGE-CORE.md`. Source operators without a direct instruction are lowered to explicit instruction sequences: unary integer negation materialises `Int64(0)` in a typed register and uses `sub_i(dst, zeroReg, operand)` (preserving the `MIN` overflow trap); `!=`, `>`, `<=` and `>=` are derived from `eq_i`, `lt_i` and `not_b`; boolean equality/inequality are lowered with `branch`, `const_b`, `move` and `not_b`; `&&` and `||` are lowered to short-circuit control flow. No host-language operator semantics are inherited. Each instruction is atomic at the machine-state level. Operands are read in the order in which they are listed in its schema. An instruction either completes its single state transition or produces one terminal trap; no partial register write is observable on a trap.

A call reads/checks its argument registers in list order, then pushes a callee frame. A return reads/checks its result before popping the frame and writing the caller destination. A non-void callee MUST have a compatible caller destination; a void callee MUST have none.

## 4. Validation boundary

Program validation occurs before execution and returns either a validated program or a deterministic validation error. Control-flow validation starts at instruction 0: every reachable nonterminal instruction must have an in-function successor; a reachable infinite loop is permitted. Unreachable instructions still undergo closed-schema, index and static-type validation but do not independently cause a fall-through error. The external JSON encoding and closed instruction schemas are normative in `docs/architecture/CCAM.md`. The parser/validator MUST reject duplicate object keys, unknown or missing fields, wrong JSON types, unknown type tags, malformed names and invalid cross-field constraints. Numeric tokens MUST be parsed exactly; do not round through IEEE-754 binary64. Accept only mathematically integral values within the declared signed-64 or index range, and check every index against its finite vector/sequence length before indexing. Boolean fields accept only JSON `true` or `false`. It MUST then check the entire function table and every instruction's structural shape, indices, static types, call signature, return convention, branch target and termination/fall-through properties.

The runtime evaluator consumes only validated programs. It still performs dynamic state checks (notably register initialisation and resource limits). It MUST NOT rely on validation to prove that a register has been initialised along every path in v0.1; the dynamic uninitialised-register trap remains part of the semantics.

Validation must be total over malformed program descriptions: arbitrary malformed data must yield a validation error, not a host panic, out-of-bounds access, nontermination or partial execution. A validator implementation needs explicit limits for input size, function count, instruction count and nesting if its input is attacker-controlled. These validation resource limits are distinct from the CCAM instruction-step budget.

## 5. Machine state and transition

The abstract machine state is:
- validated immutable program;
- stack of frames;
- each frame: function identity, program counter, typed register vector with initialisation state, and caller return destination;
- executed instruction count;
- configured maximum instruction count and call depth, each within the signed-64 non-negative integer domain (`maxDepth >= 1`).

The entry frame begins at depth 1, with its PC at the first instruction and all parameter registers initialised from entry arguments (the source-program entry has no arguments). Every executed instruction increments the step count exactly once. A call pushes one frame; a return pops one frame. A successful return from the entry frame yields `Halt(value)` or `HaltVoid`. Reaching a limit yields the specified terminal trap before the prohibited operation takes effect.

No implementation-language stack, integer or exception semantics may be observable in the machine model.

## 6. Required invariants

At every reachable machine state:
1. each frame names a function in the validated program;
2. each PC is within that function's instruction sequence;
3. every initialised register contains a value of its declared type;
4. every frame's parameter registers are initialised;
5. each caller destination is valid and agrees with the callee return type;
6. frame depth is at least one before halt and never exceeds the configured maximum;
7. the executed-step count is bounded by the configured maximum;
8. all integer values are in signed-64 range;
9. the active frame is the only frame whose PC advances;
10. no caller-visible result is written until the callee returns successfully.

## 7. Proof boundary

The first Lean theorem boundary should be the validated CCAM evaluator, not the full Capstan source language. Prove, in stages:
1. validator soundness: every accepted program satisfies the structural invariants;
2. register preservation: every successful instruction step preserves register typing/initialisation invariants;
3. progress-or-trap: every reachable nonterminal state either takes one defined transition or produces a defined terminal trap;
4. call/return frame integrity and destination compatibility;
5. arithmetic correctness against mathematical signed-64 operations;
6. deterministic execution for a fixed validated program and limits.

The source compiler then needs a separate type-preservation/translation theorem (or independently checked translation) from the supported source core into validated CCAM. The native backend needs a forward simulation/refinement argument from CCAM steps to native execution, preserving halt values, traps, and observable effects.

The initial Lean project currently provides a partial register/arithmetic foundation. Its correspondence with this contract must be reviewed and tested; do not describe it as a proof of the complete evaluator or compiler.

## 8. Source location and diagnostics

Every emitted instruction SHOULD have a source-span entry in an out-of-band side table keyed by function and instruction index (file identity, start/end byte offsets, line/column mapping). Source spans and debug metadata MUST NOT be added as extra instruction-object fields. Metadata must survive lowering and optimisation sufficiently to attribute a runtime trap to the source operation responsible for it. It does not affect semantic equality of machine states except as diagnostic metadata.

## 9. Extension and optimisation gates

A new instruction or value type requires:
- a schema and static typing rule;
- a small-step transition rule;
- defined trap and resource behaviour;
- positive and negative conformance vectors;
- a Capstan-native implementation;
- updates to the proof model and invariants.

An optimisation is accepted only if it preserves:
- successful values and return behaviour;
- trap kind and trap-before-effect ordering;
- observable IO/security effects when those extensions exist;
- required resource accounting (or an explicitly approved abstract cost model);
- source-location attribution to a semantically equivalent operation.

Range-check elimination is therefore justified only by a sound proof that the eliminated trap is unreachable under the IR preconditions. `--keep-checks` should remain an assurance mode for differential testing; it is not a substitute for proving range analysis sound.


## 10. Small-step operational model

This section fixes the state-transition shape used by the evaluator and proof model. It is normative for the proposed initial machine.

### 10.1 Domains

Let:
- `P` be an immutable, structurally validated program;
- `R` be a finite register vector whose cells are `Uninit`, `Int64(n)` or `Bool(b)`;
- `F = (fn, pc, R, retDst)` be a frame, where `pc` is the next instruction and `retDst` is the destination in the caller, or `None` for the entry frame / void return;
- `S = (frames, steps)` be a running machine state, with the active frame at the top of a non-empty stack;
- `Outcome = Running(S) | Halt(v) | HaltVoid | Trap(code, fn, pc, detail)`.

The program and configured limits are parameters to the transition relation, not mutable state. The configuration validator requires `maxDepth` in `1..2^63-1` and `maxSteps` in `0..2^63-1` before entry-frame construction. These are machine configuration parameters rather than program-schema fields; if transported as JSON, their numeric tokens must be parsed exactly. A frame's register vector has the exact length and type vector declared by its function. Register writes preserve the declared type and set the cell to initialised.

### 10.2 Instruction dispatch and step budget

For a running state with `steps = n`:
- if `n >= maxSteps`, the next transition is `Trap(step_limit_exceeded, active.fn, active.pc, None)`; no instruction is executed and the counter remains `n`;
- otherwise, the active instruction is dispatched and the execution counter becomes `n + 1`, whether that instruction completes or produces a dynamic trap.

Thus a limit of N permits exactly N executed instructions. A dynamic failure during the Nth instruction is that instruction's trap; the step-limit trap occurs only if an (N+1)th instruction would be required. Structural validation is not counted as an executed instruction.

### 10.3 Register reads and writes

A read of register `i` succeeds only if:
1. `i` is within the active frame's register vector;
2. the cell is initialised;
3. the value constructor agrees with the register's declared type.

A failed read produces its defined trap and does not read any later operand. A write is permitted only to an in-range destination whose declared type agrees with the value. Since the program is validated, an invalid destination or type mismatch is unreachable for a well-formed evaluator state; implementations retain defensive checks.

An instruction computes all required source values and its result before writing its destination. If any source read or operation traps, the destination is unchanged.

### 10.4 Scalar instructions

Write `F[pc]` for the active instruction and `R[i]` for a register cell.

- `const_i(dst, n)`: write `Int64(n)` to `dst`; advance `pc` by one.
- `const_b(dst, b)`: write `Bool(b)` to `dst`; advance `pc` by one.
- `move(dst, src)`: read `src`, write the same typed value to `dst`, advance `pc`.
- `add_i/sub_i/mul_i/div_i/rem_i(dst, lhs, rhs)`: read `lhs`, then `rhs`; apply the exact mathematical operation from `LANGUAGE-CORE.md`; if successful, write `dst` and advance `pc`; otherwise produce the operation's trap with no destination write.
- `eq_i/lt_i(dst, lhs, rhs)`: read `lhs`, then `rhs`; write the corresponding boolean comparison and advance `pc`.
- `not_b(dst, src)`: read `src`; write its boolean negation and advance `pc`.

The register type validator requires each operand and destination to have the exact type expected by the instruction. Operand reads are left-to-right, not simultaneous or unordered.

### 10.5 Control flow

- `jump(target)`: set `pc := target`.
- `branch(cond, yes, no)`: read `cond`; if true set `pc := yes`, otherwise `pc := no`.
- Both targets are validated instruction indices in the current function. No implicit fall-through target exists beyond the function's final instruction.

### 10.6 Calls

For `call(dst, callee, args)`:
1. read each argument register in list order, checking initialisation and type;
2. if the current frame depth is already `maxDepth`, produce `call_depth_exceeded` without pushing a frame;
3. advance the caller frame's `pc` to its continuation instruction;
4. push a fresh callee frame with the argument values in its parameter registers, all other registers `Uninit`, `pc = 0`, and `retDst = dst`.

The entry frame has depth 1. A call at the depth limit is an executed instruction and therefore consumes one step; if the step budget is already exhausted, `step_limit_exceeded` takes precedence before call operands are read.

### 10.7 Returns

For `ret(src)`:
1. read and type-check `src` before modifying the frame stack;
2. if the active frame is the entry frame, produce `Halt(value)`;
3. otherwise validate the caller frame and its `retDst` index/type before modifying either frame;
4. pop the callee frame and write the returned value to the caller destination as one atomic transition, leaving the caller PC at the continuation set by the call.

For `ret_void`, validate the caller frame and the absence of a return destination before popping; then perform the frame transition without a value write. Returning from the entry frame produces `HaltVoid`.

A return whose value is uninitialised traps before the frame is popped. Structural validation rejects a return instruction that does not match its function's declared return convention.

### 10.8 Explicit trap

`trap(reason)` produces terminal `Trap(explicit_trap, fn, pc, reason)` with the validated reason attached as diagnostic detail. The reason is 1–64 ASCII characters matching `[a-z][a-z0-9_]{0,63}`; all other forms are rejected during structural validation. No caller frame is resumed and no destination is written.

### 10.9 Determinism

For a validated program and fixed limits, every running state has exactly one next transition. This follows from:
- one active frame and one next PC;
- deterministic register-read checks;
- fixed left-to-right operand order;
- total, explicitly checked scalar operations;
- validated branch/call/return structure;
- deterministic limit checks.

The proof must establish this property for the evaluator implementation, not infer it from the fact that the host implementation appears sequential.
