# Native Compiler Architecture — Implementation Gap Ledger

**Status:** Initial repository reconciliation; open work register  
**Date:** 2026-11-27  
**Architecture authority:** `docs/architecture/NATIVE-COMPILER-ARCHITECTURE-RFC.md`  
**Rule:** This ledger distinguishes integrated implementation, proposals, experiments and missing implementation. A document or test model does not count as a production implementation.

## 1. Verified baseline

The following facts were confirmed against the repository default branch during the initial architecture review:

- `docs/architecture/CCAM.md` describes CCAM v0.1 as a restricted machine and explicitly says the implementation is not yet a conforming v0.1 machine, is not connected to the Lean model by a refinement theorem, and is not complete Capstan semantics.
- The v0.1 normative machine currently specifies Int64 and Bool registers, checked scalar arithmetic, control flow, direct calls, returns, traps and step/depth limits. It excludes strings, heap objects, collections, GC, taint, secrets, policies/grants, IO, concurrency and cryptographic services.
- The implementation uses a transitional multi-function call-site side table rather than the normative named-call external representation.
- The strict JSON decoder is specified as a proposal and is not yet implemented as the normative untrusted-input boundary.
- `docs/architecture/CCAM-AGGREGATE-MACHINE-BRIDGE.md` describes an experimental aggregate bridge and explicitly lists missing integration with canonical CCAM encoding/validation, multi-frame reference registers, production List/Map/string lowering, native execution and Lean refinement.
- `docs/research/ECE-RELATED-WORK-AND-NOVELTY-ASSESSMENT.md` correctly distinguishes PCC, translation validation, verified compilation, proof-carrying data and software provenance. It identifies end-to-end correspondence and exact artifact binding as research obligations, not completed results.
- `docs/architecture/NATIVE-BOOTSTRAP-PLAN.md` is a staged plan, not evidence that S0-S3 are complete.
- The existing compiler frontend/checker/code generator remain a separate, established source path; `compiler/codegen.cap` emits C. The C-free path must not be described as the production compiler until that dependency is removed from the production build.
- `docs/architecture/TYPED-IR.md`, `docs/architecture/FORMAL-VERIFICATION.md`, `docs/architecture/COMPILER-CCAM-LOWERING.md` and `docs/architecture/CAPSTAN-NORTH-STAR.md` establish an existing architectural decision: CCAM is the single canonical typed core IR and abstract machine. The source compiler lowers the checked source subset directly to CCAM. Any SSA/CFG optimisation IR is optional, derived and must refine back to CCAM. The initial architecture draft's proposed CHIR layer would have contradicted this decision; it has been removed from the amended RFC.

This baseline is intentionally conservative. Each status must be refreshed against current main and exact-head CI before implementation claims or merges.

## 2. Blocking gaps and acceptance evidence

| ID | Gap | Dependency / risk | Acceptance evidence |
|---|---|---|---|
| G-01 | Compiler architecture contracts need consolidation across the existing typed-core, CCAM, lowering and native-backend documents | Conflicting documents could create a second semantic authority or duplicate IR | Approved reconciled RFC; CCAM remains sole semantic core; any optional derived IR has a closed schema, validator and refinement back to CCAM |
| G-02 | Source-to-CCAM semantic preservation is not established for the complete accepted subset | Native compiler may miscompile source semantics | Formal source core and source-to-CCAM lowering proof or independently checked translation validation |
| G-03 | Concrete CCAM evaluator does not refine the complete Lean machine | Model theorem may not apply to executable evaluator | Whole-machine simulation theorem tied to exact implementation/profile |
| G-04 | Normative v0.1, Lean single-frame proof profile and implementation have identified acceptance differences | False conformance claims | Explicit conservative profile plus normative reachability proof or reconciled semantics |
| G-05 | Strict external CCAM decoder is not implemented as normative boundary | Untrusted input ambiguity, duplicate keys, numeric precision and resource exhaustion | Bounded decoder, closed schema, exact integer parsing, duplicate-key rejection and adversarial corpus |
| G-06 | Multi-frame named-call canonical encoding and side-table mapping are incomplete | Function identity/argument/destination mismatch | Canonical encoding, unique call-site mapping and decoder/validator correspondence |
| G-07 | Aggregate/reference machine is experimental | Compiler AST, strings and collections cannot yet execute through canonical machine | Normative memory profile, typed references, object layouts, failure atomicity, integrated evaluator and Lean refinement |
| G-08 | Reference/object/frame/root-map ABI is not frozen | Collector and native backend could implement incompatible models | Versioned reference, layout, frame and safepoint contracts before production GC |
| G-09 | Native backend coverage is restricted | Cannot compile actual compiler workload | Required instruction/aggregate/runtime coverage and differential native conformance |
| G-10 | Native object writer/linker are not established as production Capstan-native components | External binutils remain in the toolchain | Object/relocation specification, writer/linker, loader checks and reproducible object tests |
| G-11 | ABI and trap ABI need a complete versioned contract | Arguments, results, unwinding, runtime calls and roots may disagree | ABI specification plus boundary conformance tests |
| G-12 | Optional derived optimisation IR and pass validation are incomplete | Correctness/performance gap; unsound transformations or semantic duplication | Demonstrated need; CCAM-derived construction; closed verifier; translation back to CCAM; refinement evidence; pass contracts, adversarial fuzzing and benchmark evidence |
| G-13 | Resource semantics are not yet compositional across all resource classes | Step limits do not bound heap, stack, output, IO or compile work | Multidimensional charge semantics, function summaries and runtime quotas |
| G-14 | Capability/effect/security metadata preservation across native lowering is incomplete | Authority escalation or information-flow loss | Capability-aware IR, host ABI and preservation/refinement evidence |
| G-15 | Precise GC root completeness and relocation are not established end-to-end | Use-after-free or stale references at safepoints | Safepoint/root-map ABI, liveness proof, collector implementation and adversarial tests |
| G-16 | C-free S0-S3 bootstrap is not complete | Compiler still relies on transitional bootstrap components | Independent seed, native compiler, clean-room diverse rebuild and production build without C/Python dependencies |
| G-17 | Performance and portability acceptance baselines are not published | Cannot substantiate production readiness or cross-target claims | Reproducible benchmark suite and per-target ABI/conformance suites |
| G-18 | Executable evidence manifest/checker is not complete | Claims may not bind to exact source, binary, policy and target | Canonical manifest, hashes, certificate checker and tamper/mismatch tests |
| G-19 | Native terminal-result ABI is lossy: Linux exit status cannot encode arbitrary signed-64 returns and current trap exits collapse detail/location | Native execution cannot be compared faithfully with CCAM outcomes; process/transport failures can be confused with machine results | Versioned bounded result record carrying exact Int64/Void/trap identity, function/PC/detail/step count and separate platform failures; strict launcher validation and exact differential tests |

## 3. Dependency order

Do not implement dependent layers ahead of their contracts.

```
G-01 reconcile one-semantic-authority architecture
  -> G-02 source-to-CCAM semantics and lowering contracts
  -> G-04/G-05/G-06 CCAM profile, decoder and calls
  -> G-07/G-08 memory and object ABI
  -> G-09/G-10/G-11 native backend, object and ABI
  -> G-03/G-12 end-to-end refinement and validated optimisation
  -> G-13/G-14/G-15 resource, authority and GC assurance
  -> G-16 bootstrap
  -> G-17/G-18/G-19 release evidence
```

Some work can proceed in parallel only where interfaces are frozen and recorded. In particular, native instruction encoding experiments may continue, but they cannot establish a production ABI or memory model by themselves.

## 4. First implementation tranche

### T1 — Architecture contracts
1. Review and approve the layered compiler architecture RFC.
2. Add the architecture to the repository design map and research register.
3. Keep the checked-source contract aligned with the existing typed-core work; do not add a competing source-core IR.
4. Treat SSA/CFG as optional derived optimisation IR only when a measured need justifies it; specify its closed schema, validator and refinement back to CCAM before implementation.
5. Define explicit translation contracts and metadata-preservation obligations for each representation actually selected.
6. Inventory existing frontend, checker, CCAM and native modules against these contracts.

### T2 — CCAM reconciliation
1. Freeze v0.1 compatibility and name its exact accepted profile.
2. Reconcile the Lean single-frame conservative profile with normative reachability semantics.
3. Specify v0.2 memory/reference/aggregate semantics separately.
4. Specify canonical named calls and strict external decoder.
5. Establish shared conformance vectors for validator, evaluator and Lean model.

### T3 — Native boundary
1. Freeze integer, aggregate, call, return, trap, terminal-result and runtime ABI.
2. Reconcile the candidate bounded fd-3 result record with the current native launcher and CCAM-IO contract.
3. Freeze reference, frame and safepoint representation.
4. Extend native lowering only after the preceding contracts are approved.
5. Define object format and relocation model before production linker implementation.
6. Add native-vs-reference differential tests and mutation tests covering full-width returns and every terminal outcome.

## 5. Definition of done for each gap

A gap closes only when:
- its normative contract is approved;
- implementation exists in Capstan for production runtime/compiler paths where required;
- negative and adversarial tests cover invalid and boundary inputs;
- exact-head CI passes;
- formal obligations are proved or the feature is explicitly excluded from the assured profile;
- security review records residual assumptions;
- documentation status is updated to match evidence;
- no dependent profile overclaims the feature.

A passing CI job is necessary evidence, not a semantic proof. A Lean theorem is necessary evidence only for the exact model and hypotheses it names. A merged PR is not proof of production readiness.

## 6. Review policy

- Reconcile against latest main before every implementation tranche.
- Do not overwrite or duplicate parallel-worker work; inspect existing branches and PRs first.
- Prefer small, dependency-ordered PRs with exact-head CI.
- Keep experiments out of normative specifications until reviewed and accepted.
- Do not merge failing or semantically ambiguous work merely to reduce PR count.
- Record blocked items with the precise missing dependency and a reproducible acceptance test.
- Do not assign a 10/10 verdict while any critical gate in the architecture RFC remains open.
