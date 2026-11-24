# Formal verification obligation matrix

**Status:** programme baseline; not a claim of complete language verification  
**Proof branch:** `verification/ccam-formal-core-stacked`  
**Primary formalisation:** Lean 4.19.0, pinned by `verification/lean/lean-toolchain`  
**Normative machine document on this branch:** `docs/architecture/CCAM.md`

This matrix is the control document for formal-verification claims. A proof is counted only when (1) the theorem is checked on the exact recorded commit, (2) its assumptions and axiom dependencies are audited, (3) its model is traced to the normative specification, and (4) the implementation correspondence required by the claim is separately established. A green build alone is not evidence of specification or implementation correctness.

## Status vocabulary

- **Proved in model:** a named machine-checked theorem exists. This says nothing by itself about the adequacy of the model.
- **Partially proved:** a restricted fragment or conditional representation lemma is proved.
- **Specified, unproved:** the normative document states behaviour, but no adequate theorem establishes it.
- **Not modelled:** the current formal machine has no representation of the feature.
- **Blocked by specification dependency:** formalisation must wait for an authoritative semantic decision or a dependency to be integrated.

## Obligation matrix

| Area | Normative requirement / semantic object | Current Lean evidence | Status | Required closure evidence |
|---|---|---|---|---|
| Value domain | Disjoint signed-64 integer and boolean values | `Core.lean`: value/type definitions and signed-64 boundary theorems | Partially proved | Prove representation correspondence to the production runtime's integer and boolean encodings |
| Register typing | Fixed register type vector; uninitialised reads trap; writes preserve declared type | `Core.lean`: typed reads/writes and operation preservation | Partially proved | Connect the actual CCAM parser/validator and runtime register implementation to the formal register relation |
| Addition | Mathematical addition with signed-64 overflow trap | `checkedAdd_sound`, execution preservation and operand-error precedence | Partially proved | State and prove exact arithmetic equation and trap partition for all operands; establish runtime refinement |
| Subtraction/multiplication | Mathematical operation with signed-64 overflow trap | Generic checked-op preservation and result-range results | Partially proved | Prove full operation equations and exact overflow iff conditions; establish implementation correspondence |
| Division | Truncation toward zero; zero divisor and MIN/-1 trap | Zero-divisor and MIN/-1 trap results; result-range theorem | Partially proved | Prove quotient equation, sign/absolute-value laws, uniqueness, and equivalence to runtime primitive |
| Remainder | Remainder equation and remainder-by-zero behaviour | Formal model defines `MIN % -1` as zero | Partially proved | Prove the full remainder equation, sign and range properties; establish correspondence with the Capstan primitive and evaluator |
| Comparisons/boolean | Typed integer comparisons and boolean negation | Typed execution and preservation lemmas | Partially proved | Prove exact value-level equations and validator/runtime correspondence |
| Control-flow targets | Jumps and branches remain within function instruction bounds | `Fin`-indexed targets and bounded PC model; sequential-PC lemmas | Partially proved | Formalise raw decoded targets and prove validator rejection/soundness; cover every branch form |
| Single-frame step | Each instruction yields continuation, return, or explicit trap | `machineStep`, explicit outcome classification, functional determinism | Proved in restricted model | Establish adequacy against the full CCAM transition contract; include integrated calls and resource limits |
| Register preservation | Every successful transition preserves register typing | `machineStep_preserves_well_typed` and operation-level lemmas | Proved in restricted model | Lift from single frame to every frame and the complete stack invariant |
| Call depth | Bounded stack push/pop properties | Separate call-stack abstraction lemmas | Partially proved | Integrate stack into machine state and prove depth check, call transition, return transition, and stack invariant |
| Calls and arguments | Named function lookup; left-to-right argument reads; exact arity/type checks; frame initialisation | No call instruction or multi-function program in `MachineInstr` | Not modelled | Define validated function table and dependent signatures; prove argument evaluation and callee-frame construction |
| Return semantics | Return type check; caller destination validation; atomic pop-and-write; entry return | Separate stack-pop abstraction only | Not modelled | Integrated small-step return semantics; prove no partially updated state on trap and exact caller restoration |
| Instruction budget | Consume exactly one step per executed instruction; trap before overrun | Separate budget wrapper and accounting lemmas | Partially proved | Integrate budget into whole-machine transition and prove exact accounting for calls, returns, halts and traps |
| Structural validator | Reject malformed schemas, unknown functions, bad indices, invalid signatures and fall-through | Capstan typed in-memory single-frame validator enforces 4,096-register and 65,536-instruction admission limits; no validator model or validator-soundness theorem | Executable subset only; not formally modelled | Formalise raw syntax, decoder and full validation judgment; prove accepted-input soundness and rejection properties; add raw-byte budget |
| Whole-program safety | Validated configurations preserve invariants and make progress, terminate, diverge or explicitly trap | No multi-function configuration | Not modelled | Prove whole-machine preservation, progress-or-explicit-trap, determinism, and trace-level safety |
| Runtime representation bridge | Production register-list representation corresponds to formal register file | `RuntimeBridge.lean`: conditional read/write correspondence under an explicit relation | Partially proved | Prove constructors, mutation paths, dynamic bounds checks and all runtime operations establish/preserve the relation |
| Capstan-native CCAM evaluator | The normative evaluator is implemented in Capstan and matches the formal machine | PR #142 merged the restricted single-frame evaluator in `verification/ccam_core.cap`; a typed in-memory validator now checks opcode operands/types, branch targets, return contracts and reachable fall-through; no calls/frames or Lean correspondence | Implemented in a restricted executable slice; not formally connected | Complete JSON/program validation, calls/frames and configuration semantics; prove validator soundness and evaluator refinement to the integrated Lean transition system |
| Source semantics | Source-language evaluation/lowering agrees with `LANGUAGE-CORE.md` | Source-level semantics are owned by the language-semantics workstream; no connected simulation theorem here | Blocked by specification/interface dependency | Freeze the source judgment and typed IR boundary; prove source-to-CCAM simulation |
| Derived IR / optimisations | Every transform preserves observable semantics | No connected optimisation proof chain | Not modelled | Define IR semantics and prove each pass simulation/refinement, including pass composition |
| Native code generation | Generated native code implements CCAM behaviour | No machine-code semantics or backend correctness theorem | Not modelled | Prove backend refinement to a documented ISA/ABI model; account for runtime calls and linking |
| Memory, heap, GC | Bounds, object validity, allocation and collection invariants | Excluded from CCAM v0.1 | Not modelled | Specify heap semantics and ownership/capability discipline; prove memory safety and collector correctness |
| Effects, IO, concurrency | Explicit effects, isolation, scheduling and observable traces | Excluded from CCAM v0.1 | Not modelled | Define effect/concurrency semantics; prove race freedom or the actual promised concurrency guarantees |
| Security properties | Confidentiality, integrity, capability isolation and non-interference where promised | Separate security/assurance documents; not implied by current integer/register theorems | Not modelled by this proof slice | Formal threat model, attacker model, property statements, and proofs/refinement for each guarantee |
| Proof infrastructure | No unfinished proofs/local axioms; explicit dependency and TCB accounting | Pinned Lean 4.19.0 build, unfinished-proof scan, explicit `#print axioms` audit; CI now enables `mk_all` import coverage, `leanchecker`, nanoda with `sorryAx` forbidden, and `axiom-audit` with only `propext` allowed | Partially proved; exact-head multi-checker run pending | Retain these gates, inspect their exact-head output, and consider formal verification of checker implementations; record checker/tool versions and the complete trusted computing base |

## Remainder semantics alignment

The normative `docs/architecture/CCAM.md` and the formal remainder model now agree that `MIN % -1` returns zero, while `MIN / -1` traps with `integer_overflow`. The earlier matrix note describing a specification conflict was stale and has been removed.

This alignment does not establish implementation conformance: the formal remainder model still needs complete equation, sign and range proofs, and a correspondence argument to the Capstan primitive and evaluator. Do not infer evaluator correctness merely from a theorem about the formal definition.

## Research basis and proof architecture

The programme follows the strongest relevant patterns from:

1. **Mechanised WebAssembly semantics and type soundness** (Watt; Watt et al., FM 2021): executable formal semantics, validator/type soundness, and explicit progress/preservation.
2. **CompCert** (Leroy): semantic-preservation proofs across compiler passes, with a theorem connecting generated code to source semantics.
3. **CakeML** (Kumar et al., POPL 2014; subsequent verified backend work): composition of parsing, typing, compilation, runtime and machine-code correctness.
4. **Lean4Lean** (Carneiro, TYPES 2025): independent checking and formal analysis of proof-checker infrastructure as a way to reduce dependence on one trusted implementation.

These works are methodological references, not claims that Capstan currently has equivalent coverage.

## Proof acceptance rules

1. No theorem name or comment may imply a stronger property than its quantified statement proves.
2. No invariant carried as a field of a structure may be reported as a newly established transition theorem unless the transition relation is actually used in the proof.
3. Every conditional theorem must list its premises and identify which validator/runtime theorem establishes them.
4. Every arithmetic operation needs value equations and complete exceptional-case characterisation, not only a result-range theorem.
5. Every instruction constructor must be covered by transition preservation and progress arguments; use exhaustive case analysis.
6. Calls and returns must be proved as transitions over the same machine state as ordinary instructions, not as an unrelated stack abstraction.
7. A validator soundness theorem must connect accepted raw input to the exact formal configuration consumed by the evaluator.
8. Source-to-CCAM, IR-pass, and CCAM-to-native simulations must compose. A collection of disconnected local lemmas is not an end-to-end compiler proof.
9. Axiom audits must include all exported theorems and critical definitions. Report dependencies by exact commit; do not infer soundness from the absence of `sorry` alone.
10. Do not merge this work into `main` without the owner's explicit instruction and review of the stacked dependencies.

## Next execution order

1. Resolve the CCAM specification dependency, especially remainder and machine outcome/limit semantics, against the language-semantics owner.
2. Repair and obtain a passing exact-head Lean build for the current restricted model; audit the exact head.
3. Prove the complete arithmetic equations and exceptional-case partitions.
4. Formalise the raw CCAM syntax and validator, then prove validator soundness.
5. Replace the disconnected stack abstraction with a validated multi-function machine and integrated calls/returns.
6. Prove whole-machine preservation, progress-or-explicit-trap and determinism.
7. Prove the Capstan-native evaluator refines the formal machine.
8. Connect source semantics, typed IR, optimisations and native code generation with compositional simulation theorems.
9. Expand the machine model to memory, effects, security and concurrency guarantees before making claims in those domains.
