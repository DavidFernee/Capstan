# Capstan research register

**Status:** initial research inventory; hypotheses and evidence map, not publication claims  
**Last reviewed:** 2026-11-25  
**Repository:** [DavidFernee/Capstan](https://github.com/DavidFernee/Capstan)

This register separates implemented engineering from research hypotheses, formal results,
empirical results and publication readiness. Inclusion here does not establish novelty,
correctness, completeness or peer-review readiness. Every paper claim must be tied to an
exact source revision, reproducible evidence and an explicit scope statement.

## 1. Research programme

The overarching research question is:

> Can a security-oriented, self-hosting language progressively reduce its trusted
> computing base by combining a typed core execution model, mechanically checked
> semantic properties, bounded runtime behaviour and reproducible assurance evidence?

The present implementation remains C-backed. The C-free/CCAM programme is active work,
not the default compiler or an end-to-end verified execution pipeline. This distinction
is a hard constraint on all abstracts, diagrams and claims.

### Candidate papers

| ID | Working title / question | Current contribution | Maturity | Publication decision |
|---|---|---|---|---|
| R1 | **A Typed Finite-Machine Model for Capstan's Core Abstract Machine** — what properties are established for a bounded typed core machine, and what remains to connect it to execution? | Lean finite single-frame model (PR #151); Capstan-native in-memory typed validator merged in PR #163; conditional register representation bridge in `RuntimeBridge.lean`; exact-head formal/platform CI passed. Multi-function evaluator PR #169 remains draft; source-lowering PR #167 closed unmerged. | Research prototype; exact-head proof replay exists, but final-instruction and entry abstractions differ from the normative contract; no validator/evaluator refinement theorem. | Flagship candidate as a formalisation/proof-boundary study; do not claim a verified execution architecture. |
| R2 | **Memory Safety and Secret Isolation in a Conservative Garbage-Collected Runtime** — which concrete runtime invariants can be enforced and tested in a conservative non-moving collector? | Runtime hardening merged in PR #143: stale-root handling, page-release failure atomicity, secret-page isolation/wiping, stack-bound and signal-path hardening, stress/failure tests. | Substantial engineering; independent validation and comparative evaluation needed. | Strong systems/security paper candidate. |
| R3 | **Deterministic Resource-Bounded Rendering in a Garbage-Collected GUI Framework** — how can rendering and export reject adversarially large inputs before expensive allocation? | Shroud per-frame aggregate text budget PR #103 and PNG export amplification bounds PR #92 merged; additional Shroud issues/work remain. | Implemented bounded paths; scope is not a process-wide memory guarantee; platform/accessibility coverage incomplete. | Strong systems paper candidate after workload and adversarial evaluation. |
| R4 | **An Empirical Evaluation of Security Guarantees in Restricted Programming-Language Runtimes** — how accurately can a language's security claims be evaluated against real vulnerability records? | K0 Linux-kernel CVE study and methodology; PR #153 corrects population/classification/conservatism issues but remains open. | Dataset regeneration and independent relabelling/review not complete; headline figures are not publication-grade. | High-potential empirical paper; freeze claims until replication. |
| R5 | **Resource-Bounded Cryptographic Primitives in a Constrained Runtime** — how should work, allocation and intermediate state be bounded for password derivation? | PBKDF2 work/output/input bounds and HMAC-state reuse merged in PR #149. | Focused implementation contribution; broader novelty and performance/security comparison not established. | Likely a section or case study unless evaluation reveals a distinct contribution. |
| R6 | **A C-Free Self-Hosting Compiler and Its Assurance Boundary** — what staged architecture and proof obligations are required to remove C from the compiler/runtime trusted base? | C-free bootstrap contract PR #172 draft; CCAM and lowering work; current design map and threat model explicitly identify remaining C/Python/toolchain trust. | Architecture and early implementation only; no C-free default pipeline or end-to-end proof. | Long-term flagship direction; not yet a results paper. |

## 2. Evidence ledger

The following is a starting point, not an independent audit of each PR's current CI.

| Evidence item | Repository anchor | What it supports | What it does not support |
|---|---|---|---|
| Finite single-frame CCAM model | PR #151, merged; exact head `360043c8704546857caa4c82f2978c7709399016` | A Lean model and proofs for the enumerated finite instruction/program fragment, including typed operand conversion, instruction validation and bounded control-flow targets. The exact PR #163 head passed the Lean build and pinned `lean4checker` replay in run [45508852082](https://github.com/DavidFernee/Capstan/actions/runs/45508852082). | Full CCAM JSON/function-table validation; source compiler correctness; implementation refines to Lean; native-code or runtime correctness. |
| Typed structural validator | PR #163, merged at `294d34361c31dc768e60a017a3fd0718f7a00313` | Bounded Capstan-native in-memory validation of the supported single-frame subset; tests include a 512-instruction backwards-edge chain, execution returning 42, malformed-target rejection and exact/over resource limits. Exact-head platform/supply-chain CI passed in run [45508852150](https://github.com/DavidFernee/Capstan/actions/runs/45508852150). | Normative JSON decoder coverage, multi-function validation, formal refinement to Lean. |
| Multi-function evaluator | PR #169, open draft | A proposed bounded call-frame evaluator and stated frame/step/recursion limits. | Not merged; complete normative call encoding, proof of evaluator correctness, production integration. |
| Scalar source lowering | PR #167, closed unmerged | A narrow source/check/lower/validate/execute vertical slice was developed on a draft branch. | Not integrated on `main`; complete language lowering, native backend, source-to-CCAM simulation theorem. |
| Runtime register bridge | `verification/lean/CapstanVerification/RuntimeBridge.lean` | Conditional read correspondence and register-write relation preservation for an abstract runtime-style record/list model. | A proof about compiled Capstan source or complete evaluator refinement. |
| Shroud resource bounds | PRs #92 and #103, merged | Explicit per-frame text and PNG export bounds with regression/verification tests described by the PRs. | A process-wide memory bound, streaming output, complete native GUI support. |
| PBKDF2 bounds | PR #149, merged | Explicit input/output/work ceilings and HMAC-state reuse. | Deterministic destruction of all secret material or a general cryptographic proof. |
| K0 empirical study | `docs/K0-KERNEL-CVES.md`; PR #153 open | A documented method and initial classification study; PR #153 identifies corrections to population and conservative classification. | Final 98.7% assurance claim, complete pinned dataset, independent human relabelling or generalisation to arbitrary kernel code. |
| Architecture and threat boundary | `docs/DESIGN-MAP.md`; `docs/assurance/THREAT-MODEL.md` | Explicit statement that current integrated path is generated C plus C runtime and that CCAM/Lean work covers selected fragments. | A C-free production implementation or whole-toolchain formal assurance. |

For every merged PR above, record the exact merge commit, CI run URLs and successful
platform matrix before treating the item as a reproducible result. The CCAM formal CI run
uses pinned Lean 4.19 `lean4checker`; the separate Nanoda job in the same workflow checks
the allocator/GC model, not CCAM. The CCAM axiom audit reports `propext` and `Quot.sound`
for selected declarations, so the result must not be described as axiom-free. PR state alone is not
test evidence. In particular, an empty or unavailable status response is **unknown**, not
a pass.

## 3. Required research record for each candidate

Before a candidate is described as journal-ready, create a paper folder containing:

1. **Research question and hypotheses** — falsifiable, bounded and distinct from a product goal.
2. **Related-work review** — search papers, standards and comparable implementations; identify
   the closest prior art and state the difference without assuming novelty.
3. **Contribution statement** — theorem, algorithm, architecture, dataset, measurement or
   empirical finding; distinguish each category.
4. **Formal specification** — definitions, assumptions, invariants, theorem statements and
   proof dependencies where applicable.
5. **Implementation provenance** — exact commit SHA(s), toolchain versions, generated artefacts
   and configuration.
6. **Reproduction package** — one-command scripts, pinned datasets, seeds, raw results,
   environment description and expected outputs.
7. **Evaluation** — baselines, ablations, adversarial cases, performance/resource costs,
   failure analysis and uncertainty.
8. **Independent verification** — a reviewer who did not author the implementation or original
   experiment; record disagreements and corrections.
9. **Limitations and counterexamples** — explicit non-claims, known gaps and conditions under
   which the result fails.
10. **Publication record** — target venue, article type, word/page constraints, ethics/data
    statements, submission version and review outcome.

## 4. Mandatory claim discipline

Use these labels in papers, talks and repository documentation:

- **Implemented:** code is present at a named revision.
- **Tested:** specified tests ran successfully at an exact revision and environment.
- **Formally proved:** a named theorem was checked by a named prover/version, with assumptions
  and axiom dependencies disclosed.
- **Refinement established:** a proof connects the executable implementation to the formal
  model. A model proof alone is not refinement.
- **Independently replicated:** a separate party reproduced the result from the released
  materials.
- **Proposed/projected:** a design or future capability, not a current result.

Never use “formally verified Capstan”, “C-free Capstan”, “memory safe” or a projected K0
percentage without a nearby scope qualification and supporting evidence.

## 5. Priority work and acceptance gates

### R1 — CCAM formal execution architecture (highest priority)

- [ ] Freeze a normative CCAM semantics and versioned input schema.
- [ ] Specify decoder behaviour, duplicate/unknown fields, integer ranges, resource accounting,
      function signatures, calls, returns, traps and deterministic evaluation order.
- [ ] Complete validator/evaluator implementation against that contract.
- [ ] Prove validator soundness and completeness relative to the normative accepted-program
      predicate, or state a narrower theorem precisely.
- [ ] Prove evaluator step correspondence to the Lean machine model, including calls/frames.
- [ ] Establish source-checker/lowering simulation for the declared source subset.
- [ ] Audit all axioms, assumptions, trusted libraries and exact-head proof replay.
- [ ] Run independent differential/property/fuzz testing and publish counterexamples.
- [ ] Only then describe the result as a verified execution pipeline, and only for the proved scope.

### R2 — Runtime memory and secret isolation

- [ ] Turn each intended invariant into a named specification and executable test.
- [ ] Add adversarial allocator/GC schedules, allocation-failure injection and platform matrix.
- [ ] Verify secret-page lifecycle from allocation through reuse/release, including copies and
      compiler/runtime temporaries.
- [ ] Compare overhead and retention against a documented baseline.
- [ ] Obtain independent review of the C implementation and sanitiser/fuzz evidence.

### R3 — Shroud resource-bounded rendering

- [ ] Define the resource model: per-frame, per-widget, export, transient and process-wide.
- [ ] Prove or test preflight-before-allocation properties for every bounded input path.
- [ ] Add adversarial Unicode, font, nesting, image and output-I/O tests.
- [ ] Measure worst-case time, peak memory and rejection behaviour on pinned platforms.
- [ ] State clearly which native GUI/accessibility backends are implemented versus headless.

### R4 — K0 empirical security study

- [ ] Pin the complete upstream CVE dataset, retrieval timestamp, source revision and hashes.
- [ ] Regenerate the entire dataset after PR #153's corrections are integrated.
- [ ] Publish inclusion/exclusion rules, taxonomy mapping and all per-record decisions.
- [ ] Independently blind-review a statistically justified sample and all ambiguous cases.
- [ ] Report inter-rater agreement, uncertainty, sensitivity analysis and classification errors.
- [ ] Separate measured current capability from hypothetical design projections in every chart.
- [ ] Release scripts, data where licensing permits, and machine-readable record-level results.

### R5 — Cryptographic resource limits

- [ ] Confirm exact-head tests and all supported platform CI.
- [ ] Document bounds as a public API contract and test boundary values.
- [ ] Evaluate worst-case latency/memory and compatibility with legitimate workloads.
- [ ] Specify secret lifetime and wiping limitations, including managed-language copies.
- [ ] Compare against established KDF API guidance and implementations.

### R6 — C-free bootstrap

- [ ] Define what “C-free” means across bootstrap, compiler, runtime, standard library,
      FFI, linker, build scripts and host dependencies.
- [ ] Define a staged trust-reduction plan and reproducible bootstrap procedure.
- [ ] Keep the current C-backed path clearly identified until a C-free path is integrated.
- [ ] Prove or independently validate each stage's semantic preservation.
- [ ] Publish the residual trusted computing base rather than claiming zero trust.

## 6. Publication strategy

Recommended sequence:

1. **CCAM formalisation and proof-boundary study** — current flagship manuscript; a stronger execution-architecture claim is contingent on validator/evaluator refinement.
2. **Runtime memory and secret isolation** — independent systems/security paper once invariants
   and platform evaluation are complete.
3. **Shroud bounded rendering** — independent systems paper once resource accounting and
   adversarial evaluation are broader than the two merged fixes.
4. **K0 empirical study** — publish only after dataset regeneration and independent relabelling.

R5 should be folded into a broader runtime/security paper unless the evaluation supports a
standalone contribution. R6 is a longer-term programme and should not be presented as a
completed result.

## 7. Research integrity and change control

- Every paper result must point to immutable source/data/proof revisions.
- A change to semantics, code, tests, dataset or proof assumptions invalidates affected evidence
  until rerun or explicitly reviewed.
- Open PRs and draft branches are leads, not results.
- Do not silently update historical figures; preserve prior versions and explain corrections.
- Publish negative results, failed proof obligations and material limitations.
- Keep this register current as PRs merge, tests run and independent reviews are completed.

## 8. Initial assessment

Capstan has several credible **research candidates** and a growing body of concrete
engineering evidence. It does not yet have, on the evidence recorded here, a demonstrated
end-to-end formally verified C-free compiler/runtime, a final independently replicated K0
study, or four completed journal papers. The immediate research task is to turn promising
implementation and proof fragments into tightly scoped, reproducible claims.
