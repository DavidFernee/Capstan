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
- source-location metadata for diagnostics and trap mapping.

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

The instruction schemas in `docs/architecture/CCAM.md` are retained, subject to the semantic corrections in `LANGUAGE-CORE.md`. Each instruction is atomic at the machine-state level. Operands are read in the order in which they are listed in its schema. An instruction either completes its single state transition or produces one terminal trap; no partial register write is observable on a trap.

A call reads/checks its argument registers in list order, then pushes a callee frame. A return reads/checks its result before popping the frame and writing the caller destination. A non-void callee MUST have a compatible caller destination; a void callee MUST have none.

## 4. Validation boundary

Program validation occurs before execution and returns either a validated program or a deterministic validation error. It MUST check the entire function table and every instruction's structural shape, indices, static types, call signature, return convention, branch target and termination/fall-through properties.

The runtime evaluator consumes only validated programs. It still performs dynamic state checks (notably register initialisation and resource limits). It MUST NOT rely on validation to prove that a register has been initialised along every path in v0.1; the dynamic uninitialised-register trap remains part of the semantics.

Validation must be total over malformed program descriptions: arbitrary malformed data must yield a validation error, not a host panic, out-of-bounds access, nontermination or partial execution. A validator implementation needs explicit limits for input size, function count, instruction count and nesting if its input is attacker-controlled. These validation resource limits are distinct from the CCAM instruction-step budget.

## 5. Machine state and transition

The abstract machine state is:
- validated immutable program;
- stack of frames;
- each frame: function identity, program counter, typed register vector with initialisation state, and caller return destination;
- executed instruction count;
- configured maximum instruction count and call depth.

The entry frame begins at depth 1, with its PC at the first instruction and all parameter registers initialised from entry arguments (the source-program entry has no arguments). Every executed instruction increments the step count exactly once. A call pushes one frame; a return pops one frame. A successful return from the entry frame yields `Halt(value)` or `Halt(void)`. Reaching a limit yields the specified terminal trap before the prohibited operation takes effect.

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

Every emitted instruction SHOULD carry source-span metadata (file identity, start/end byte offsets, line/column mapping). Metadata must survive lowering and optimisation sufficiently to attribute a runtime trap to the source operation responsible for it. It does not affect semantic equality of machine states except as diagnostic metadata.

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
