# Capstan formal verification strategy

**Status:** initial proof programme; deliberately partial  
**Work branch:** verification/ccam-formal-core  
**Semantic authority:** docs/SPEC.md and docs/architecture/CCAM.md

## 1. Current evidence and claims

The repository had no machine-checked proof development at the start of this work. The CCAM Capstan source and its tests are executable semantics and conformance evidence, not proofs. The compiler bootstrap fixpoint establishes byte-for-byte reproducibility of generated output between bootstrap stages; it does not prove that the compiler implements the language specification. Conventional tests, fuzzing, sanitizers, self-hosting and reproducible builds must not be labelled formal verification.

The current CCAM specification is intentionally narrow: signed 64-bit integers, booleans, typed local registers, checked arithmetic, branches, direct calls/returns, explicit traps, and deterministic step/depth limits. Its exclusions (heap/GC, taint, secrets, grants, IO, concurrency and cryptography) remain outside the model.

## 2. Proof environment decision

**Initial choice: Lean 4**, with a pinned toolchain and a small project under verification/lean/. Reassess after the first evaluator and simulation theorem; do not add Mathlib until a concrete theorem needs it.

| Criterion | Lean 4 | Isabelle/HOL |
|---|---|---|
| Expressiveness | Dependent types and inductive relations support typed syntax, machine states and invariants; propositions can be executable definitions where appropriate | Classical higher-order logic with mature inductive definitions and strong automation; highly expressive for operational semantics |
| Maintainability | Functional definitions and theorem statements can live beside executable specifications; tactic scripts need review and stable interfaces | Structured Isar proofs are readable and mature; Sledgehammer and simplifier reduce routine proof effort |
| Executable specifications | Lean definitions execute in the kernel/runtime; extraction/code generation is available but creates a separate extraction trust question | Code generation to functional languages is mature; generated code still has a toolchain boundary |
| Compiler verification | Suitable for syntax, typing, semantics, simulation and verified transformations; ecosystem less compiler-proof-specialised than Isabelle's | Long record of compiler verification and semantic preservation work; mature libraries and AFP material |
| Workflow | Lean toolchain can be pinned and built in CI with lake; natural fit for a small self-contained repository project | Isabelle sessions can be pinned and built in CI, but distribution/session setup is heavier |
| Long-term cost | Smaller initial surface and good integration with functional implementation; proof engineering discipline required to avoid tactic brittleness | Strong automation and mature proof style, but more specialised contributor knowledge and heavier project infrastructure |

Lean is selected as the first implementation environment, not declared universally superior. Isabelle remains a credible alternative, especially if the programme grows into large compiler-correctness proofs and its existing libraries materially reduce work. A future change of assistant must preserve theorem statements and the semantic contract, not merely translate syntax.

The first model intentionally uses Lean's standard library only. This keeps the initial dependency and trusted surface small. Any later Mathlib dependency must be pinned and included in the assurance inventory.

## 3. Layered proof plan

1. **Core definitions:** syntax, values, register types, initialisation, functions, frames, instruction semantics, outcomes and resource limits. Definitions must trace to the normative CCAM version.
2. **Local invariants:** register typing, valid PC, frame well-formedness, call destination/return-type agreement, and bounded counters.
3. **Safety:** preservation for each transition; progress-or-explicit-trap for well-formed states; arithmetic range and division preconditions; branch target validity; call/return stack invariants.
4. **Compiler boundary:** a typed IR with a typing judgement and a simulation relation to CCAM. Prove each lowering pass preserves observable outcomes, including explicit traps.
5. **Optimisations:** establish pass-specific forward simulation (or an appropriately justified bisimulation); prove check elimination only under the pass's stated preconditions.
6. **Native code:** define a target subset and ABI, then prove instruction selection/lowering or use translation validation against the formal IR semantics. Keep assembler, linker and hardware assumptions explicit.
7. **Security extensions:** add heap and object invariants, taint/validator semantics, secret observations and wiping contract, capability provenance/revalidation, resource bounds, then concurrency and non-interference.

Do not model every surface feature before the small core is coherent. New instructions or value types require specification changes, conformance vectors, and corresponding proof obligations.

## 4. Initial mechanised results

The initial Lean model is in verification/lean/CapstanVerification/Core.lean.

Current theorem statements:
- write_preserves_well_typed: updating a register with a value matching its declared type preserves the register-file typing invariant.
- checkedAdd_sound: a successful checked mathematical addition returns a signed-64 result.
- checkedDiv_zero_traps: division by zero returns the explicit CCAM division trap.
- checkedDiv_min_neg_one_traps: signed-64 minimum divided by negative one returns the explicit overflow trap.

These are small foundational lemmas. They do **not** establish type preservation for a CCAM program, progress, memory safety, function-call correctness, compiler correctness, or native-code correctness. The arithmetic model uses mathematical integers; the link to Capstan's actual int and executable arithmetic routines remains to be proved and tested.

## 5. Typed IR proof architecture

The typed IR must be owned by the compiler/IR workstream and agreed with the language and compiler architects before its representation is frozen. Proposed proof interface:

- SourceCore: normative, desugared source subset with a typing judgement.
- TypedIR Γ: IR indexed by a type environment, so ill-typed operands are unrepresentable where practical.
- CCAMProgram: validated machine program with explicit register signatures and control-flow targets.
- compile : SourceCore → Except CompileError TypedIR.
- lower : TypedIR → CCAMProgram.
- Evaluation relations for source, IR and CCAM.
- Simulation obligations: source-to-IR, IR-to-CCAM, and later CCAM-to-target. Outcomes must preserve returned values, externally observable effects and trap classes; resource-limit differences must be explicitly accounted for.

Prefer compositional pass theorems. A pass that removes a check must prove the check cannot fail under its analysis invariant. Do not use test agreement as a substitute for a simulation theorem.

## 6. Trusted computing base and evidence labels

The proof assistant's kernel checks theorem terms, but the overall assurance claim also depends on the Lean executable/toolchain, imported axioms and definitions, project configuration, and the correspondence between the formal model and implementation.

| Component | Current status | Trust/evidence treatment |
|---|---|---|
| Lean kernel and pinned Lean distribution | External dependency | Trusted to check proof terms; pin and record version |
| Lean standard library | Imported foundation | Audit imported declarations; no unreviewed axioms |
| CCAM normative specification | Human-authored specification | Review authority; model-to-spec correspondence is not yet proved |
| Lean CCAM model | Partial definitions | Inspect definitions; not a complete machine |
| Theorems in Core.lean | Machine checked only when built successfully | Do not claim CI-verified until a proof build passes |
| Capstan CCAM implementation | Executable Capstan source | Tests/conformance only; not proved equivalent to Lean |
| Existing bootstrap, generated C, C compiler/runtime | Current implementation dependencies | Outside the proof model and part of present TCB |
| Native backend, assembler, linker, OS, hardware | Future dependencies | Not yet modelled or verified |

No theorem in this programme should rely on sorry, admit, custom axioms, unchecked external proof or an unreviewed imported theorem. CI must build the Lean project from a clean checkout. A successful proof build establishes only the listed theorems under their definitions and imports.

## 7. Immediate coordination requirements

- Worker 1 (language architecture): confirm CCAM integer, trap, evaluation-order and control-flow semantics before the evaluator model is extended. Any ambiguity is a specification issue, not an invitation to silently choose a model.
- Worker 3 (typed IR/compiler): agree stable type-environment, instruction and control-flow interfaces before writing IR simulation theorems.
- This branch owns proof architecture and proof files. It does not change the normative CCAM or language specification without coordination.
- Keep this work separate from v0.6 runtime stabilisation. No direct changes to main.

## 8. Roadmap and exit criteria

| Stage | Evidence required |
|---|---|
| P0: environment | Pinned Lean toolchain; clean CI proof build |
| P1: core | Complete small-step semantics and mechanically checked preservation + progress-or-trap |
| P2: calls/control flow | Valid target and call graph invariants; return destination/type preservation; bounded stack |
| P3: IR | Typed IR definitions and source/IR/CCAM simulation theorems |
| P4: optimisations | Pass-by-pass semantic preservation, including range-check elimination |
| P5: memory/security | Heap/GC invariants; taint and capability soundness; secret lifecycle/observation properties |
| P6: concurrency | Memory model, ownership/locking invariants, race freedom and explicitly scoped non-interference |
| P7: native | Target semantics, ABI model and code-generation correctness or translation validation |

A stage is complete only when the theorem source builds in CI, the theorem is stated precisely, assumptions are documented, and the implementation correspondence is separately evidenced. A proof assistant being installed is not a completed stage.
