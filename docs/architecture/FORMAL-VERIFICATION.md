# Capstan formal verification strategy

**Status:** initial proof programme; deliberately partial  
**Work branch:** verification/ccam-formal-core-stacked  
**Dependency:** draft PR #81, branch architecture/c-free-formal-foundation. This is a stacked proof PR: its normative CCAM specification and Capstan executable semantics are supplied by that dependency. Retarget/synchronise this proof PR after #81 integrates.
**Semantic authority:** docs/SPEC.md and docs/architecture/CCAM.md

## 1. Current evidence and claims

The mainline snapshot initially had no machine-checked proof development. The normative CCAM v0.1 specification and Capstan-native arithmetic/register substrate currently live in draft PR #81, so this proof work is stacked on that branch and reads docs/architecture/CCAM.md as its semantic authority. The CCAM Capstan source and its tests are executable semantics and conformance evidence, not proofs. The compiler bootstrap fixpoint establishes byte-for-byte reproducibility of generated output between bootstrap stages; it does not prove that the compiler implements the language specification. Conventional tests, fuzzing, sanitizers, self-hosting and reproducible builds must not be labelled formal verification.

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

The initial Lean model is in verification/lean/CapstanVerification/Core.lean. Its value typing constrains integers to the signed-64 range; checked addition, subtraction and multiplication use mathematical integer operations followed by the CCAM range check. Division uses an explicit truncation-toward-zero quotient, and remainder is defined from that quotient as a - q*b. Zero divisors and MIN/-1 are explicit traps, matching CCAM v0.1.

Current theorem statements:
- minI64_in_range and maxI64_in_range: the signed-64 endpoints are accepted by the executable range predicate.
- below_minI64_out_of_range and above_maxI64_out_of_range: the immediately adjacent out-of-range values are rejected.
- write_preserves_well_typed: updating a register with a value matching its declared type preserves the register-file typing invariant.
- checkedAdd_sound, checkedSub_sound and checkedMul_sound: successful checked arithmetic returns a signed-64 result.
- checkedDiv_zero_traps and checkedRem_zero_traps: division/remainder by zero returns the explicit CCAM division trap.
- checkedDiv_min_neg_one_traps and checkedRem_min_neg_one_traps: signed-64 minimum divided/remaindered by negative one returns the explicit overflow trap.

These are small foundational lemmas. The explicit target build and axiom audit now pass on proof-source commit `6f51a6759cda8e2b59d73faac003ae2e1d2f2afe` (Lean 4.19.0, run `45341231542`, PR merge commit `611536c`). The CI source scan rejects `sorry`, `admit` and local `axiom` declarations and passed. The theorem modules were built with `lake build CapstanVerification --wfail`; `AxiomAudit.lean` reports the dependencies below. This establishes the listed theorem declarations under Lean's kernel and the stated imported axioms; it does not establish model-to-implementation correspondence or any unlisted property. They do **not** establish type preservation for a CCAM program, progress, memory safety, function-call correctness, compiler correctness, or native-code correctness. The arithmetic model uses mathematical integers and an explicit signed-64 predicate. `truncDiv` is defined using natural-number magnitudes and a sign correction, but its quotient/remainder laws are not yet proved. Successful division/remainder range safety is also not yet proved under the required signed-64 operand preconditions. The link to Capstan's actual int and executable arithmetic routines remains to be proved and tested. The `checkedI64` helper uses a computational Bool range check over Lean's `Int` constructors. It is executable as a mathematical signed-64 model, but it is not yet proved equivalent to Capstan's native integer representation or runtime arithmetic. The compiler workstream has also surfaced an unresolved semantic discrepancy: CCAM v0.1 currently specifies `MIN % -1` as `integer_overflow`, while the existing Capstan source-language remainder semantics reportedly produce zero. The `checkedRem_min_neg_one_traps` theorem proves only the current CCAM text; it is not evidence of source-to-CCAM correctness. The language-semantics proposal now resolves the source rule as zero; the remaining blocker is adoption of that decision in the normative CCAM file and its conformance vectors on the dependency branch before a source refinement theorem can be stated.

## 5. Canonical CCAM and compiler proof architecture

The language-semantics workstream has decided that **CCAM is the canonical typed core IR and reference abstract machine**. The initial source compiler lowers the supported typed source subset directly into validated CCAM. Do not introduce a parallel primary instruction semantics.

The first compiler proof boundary is therefore:

- `SourceCore`: the normative, typed scalar/control-flow source subset.
- `ValidatedCCAM`: a finite immutable function table plus entry point, accepted by a total structural validator.
- `lowerSource : SourceCore → Except CompileError ValidatedCCAM`.
- A source evaluation relation and the CCAM small-step relation.
- A simulation/refinement theorem showing that lowering preserves returned values, explicit trap outcomes, evaluation order and observable effects.

The evaluator proof proceeds independently once a validated CCAM program is available: validator soundness; register and frame preservation; progress-or-explicit-trap; call/return invariants; deterministic resource accounting.

A later optimisation pipeline MAY introduce a typed SSA/CFG representation, but it is a derived representation rather than a second semantic authority. It must have a validator, a translation back to CCAM, a simulation/refinement argument, differential conformance tests, and pass-specific correctness theorems. Optimisations must preserve trap kind, trap-before-effect ordering, observable effects, and the approved resource-cost semantics. In particular, check elimination requires a proof that the removed trap is unreachable under the pass preconditions.

Worker 3 owns compiler/IR representation. I will not freeze additional IR constructors or duplicate CCAM semantics; theorem interfaces will follow the canonical contract in `docs/architecture/TYPED-IR.md` once that contract is integrated with the CCAM dependency branch.

**Integration blocker:** the language-semantics proposal resolves `MIN % -1` to zero, while the current CCAM v0.1 file on the PR #81 dependency branch still specifies an overflow trap. The proof branch remains explicitly stacked on PR #81 until its normative CCAM text and conformance vectors adopt the language-semantics decision. The existing `checkedRem_min_neg_one_traps` lemma proves only the current CCAM draft and is not source-to-CCAM evidence.

## 6. Trusted computing base and evidence labels

The proof assistant's kernel checks theorem terms, but the overall assurance claim also depends on the Lean executable/toolchain, imported axioms and definitions, project configuration, and the correspondence between the formal model and implementation.

| Component | Current status | Trust/evidence treatment |
|---|---|---|
| Lean kernel and pinned Lean distribution | External dependency | Trusted to check proof terms; pin and record version |
| Theorem axiom dependencies | Printed by `AxiomAudit.lean` in run 45340981405 | Four signed-64 boundary theorems have no axiom dependencies. The other eight theorem declarations depend on `propext` only. No `Classical.choice`, `Quot.sound`, local axioms or unfinished proofs are reported. |
| CCAM normative specification | Human-authored specification | Review authority; model-to-spec correspondence is not yet proved |
| Lean CCAM model | Partial definitions | Inspect definitions; not a complete machine |
| Theorems in Core.lean | Machine-checked on Lean 4.19.0, run 45341231542, proof-source commit 6f51a67 | Explicit target build passed with `--wfail`; source scan passed; axiom dependencies printed by `AxiomAudit.lean` |
| Capstan CCAM implementation | Executable Capstan source | Tests/conformance only; not proved equivalent to Lean |
| Existing bootstrap, generated C, C compiler/runtime | Current implementation dependencies | Outside the proof model and part of present TCB |
| Native backend, assembler, linker, OS, hardware | Future dependencies | Not yet modelled or verified |

No theorem in this programme should rely on sorry, admit, custom axioms, unchecked external proof or an unreviewed imported theorem. CI must build the Lean project from a clean checkout. A successful proof build establishes only the listed theorems under their definitions and imports.

## 7. Immediate coordination requirements

- Worker 1 (language architecture): confirm CCAM integer, trap, evaluation-order and control-flow semantics before the evaluator model is extended. Any ambiguity is a specification issue, not an invitation to silently choose a model.
- Worker 3 (compiler): provide the canonical CCAM compiler boundary and any proposed derived optimisation-IR representation; simulation theorems must map derived IR back to CCAM.
- This branch owns proof architecture and proof files. It does not change the normative CCAM or language specification without coordination.
- Keep this work separate from v0.6 runtime stabilisation. No direct changes to main.

## 8. Roadmap and exit criteria

| Stage | Evidence required |
|---|---|
| P0: environment | Complete on PR #89: pinned Lean 4.19.0, dependency-free Lake manifest, explicit theorem-target build, no-sorry/no-local-axiom scan and axiom audit |
| P1: core | Complete small-step semantics and mechanically checked preservation + progress-or-trap |
| P2: calls/control flow | Valid target and call graph invariants; return destination/type preservation; bounded stack |
| P3: compiler boundary | Source-to-validated-CCAM simulation; optional derived-IR-to-CCAM simulation |
| P4: optimisations | Pass-by-pass semantic preservation, including range-check elimination |
| P5: memory/security | Heap/GC invariants; taint and capability soundness; secret lifecycle/observation properties |
| P6: concurrency | Memory model, ownership/locking invariants, race freedom and explicitly scoped non-interference |
| P7: native | Target semantics, ABI model and code-generation correctness or translation validation |

A stage is complete only when the theorem source builds in CI, the theorem is stated precisely, assumptions are documented, and the implementation correspondence is separately evidenced. A proof assistant being installed is not a completed stage.
