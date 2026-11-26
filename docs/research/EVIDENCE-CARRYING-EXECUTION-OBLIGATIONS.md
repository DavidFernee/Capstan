# Evidence-Carrying Execution — Proof and Implementation Obligations

**Status:** proposed research ledger; all entries initially open  
**Parent design:** [EVIDENCE-CARRYING-EXECUTION.md](EVIDENCE-CARRYING-EXECUTION.md)

A row is complete only when its predicate, artefact, assumptions, exact revision and reproduction procedure are recorded. Tests do not discharge theorem obligations; model theorems do not discharge implementation-refinement obligations.

## Current mainline crosswalk

See [ECE / CCAM contract crosswalk](ECE-CCAM-CROSSWALK.md), pinned to main commit `635eaf5d2e319bf4835c7ecae1ab316cd94b8ef2`. It maps every ECE-001..045 obligation to the normative CCAM contract, current Capstan implementation and tests, available Lean models/theorems, missing refinement links and responsible work-package roles. The crosswalk records partial implementation evidence only: **all obligations remain open** until their specified proof/implementation artefact, assumptions, exact revision and reproduction procedure are complete.

The first proposed certificate target is the conservative `CCAM-SF-P` single-frame profile. It deliberately excludes multi-function calls, the internal `emit_bytes` extension, I/O, capabilities and native refinement; it does not claim full normative CCAM v0.1 acceptance.

## A. Semantic identity and certificate format

| ID | Obligation | Required evidence | Status |
|---|---|---|---|
| ECE-001 | Define canonical CCAM artefact encoding and semantics identifier | Versioned schema; exact integer/Unicode rules; canonical bytes; duplicate-key rejection; hash domain separation | Open |
| ECE-002 | Define certificate schema and bounded decoder | Closed schema; byte/node/depth limits; unknown/duplicate field rejection; deterministic errors | Open |
| ECE-003 | Bind certificate to program, semantics, limits and capability manifest | Mutation tests prove every bound-field change invalidates stale evidence | Open |
| ECE-004 | Define verifier acceptance predicate | Formal predicate covering all static program and certificate conditions | Open |
| ECE-005 | Prove checker soundness | Accepted certificate implies the formal accepted-program predicate | Open |
| ECE-006 | Characterise completeness or deliberate conservatism | Accepted subset documented; rejected programs classified as unsupported or invalid | Open |

## B. Execution correspondence

| ID | Obligation | Required evidence | Status |
|---|---|---|---|
| ECE-010 | Define whole-program small-step semantics | Functions, frames, calls, returns, traps, effects and shared counters | Open |
| ECE-011 | State machine invariants | Typed/initialised registers, valid PC, continuation, frame-depth and fuel bounds | Open |
| ECE-012 | Prove preservation and progress-or-trap | Lean theorems for the exact versioned CCAM subset | Open |
| ECE-013 | Define concrete evaluator relation | Mapping from concrete frame/register representation to formal state | Open |
| ECE-014 | Prove one-step evaluator simulation | Each concrete success/trap corresponds to a reference transition, preserving observations | Open |
| ECE-015 | Prove initial-state correspondence | Validated program/configuration constructs a related entry state | Open |
| ECE-016 | Prove terminal outcome correspondence | Halt values, void halt, trap code/location/detail and precedence agree | Open |
| ECE-017 | Extend correspondence to source lowering | Checked source subset simulates to CCAM; unsupported constructs fail closed | Open |
| ECE-018 | Extend correspondence to native backend | Generated code simulates CCAM outcomes, effects and resource limits | Open |

## C. Resource contracts

| ID | Obligation | Required evidence | Status |
|---|---|---|---|
| ECE-020 | Define resource units and accounting points | Distinguish fuel, peak-live heap, cumulative allocation, stack bytes, output bytes, validation work and wall-clock | Open |
| ECE-021 | Prove shared fuel monotonicity | Calls/returns consume one shared budget; no reset or wraparound | Open |
| ECE-022 | Prove call-depth/stack bound | Frame-push preflight and concrete byte bound including alignment/overhead | Open |
| ECE-023 | Define compositional function summaries | Sound algebra for sequencing, branches, loops, calls and recursion | Open |
| ECE-024 | Prove summary soundness | Static bound is never below any reachable execution cost under stated assumptions | Open |
| ECE-025 | Distinguish proved, estimated and unknown bounds | Typed evidence state; no implicit promotion from estimate to proof | Open |
| ECE-026 | Bound validator resource use | Aggregate input bytes, nodes, functions, instructions, registers, args and work before allocation | Open |
| ECE-027 | Extend accounting to heap and I/O | Allocator/adapter preflight, failure atomicity and exact-boundary tests | Open |

## D. Capability and effect contracts

| ID | Obligation | Required evidence | Status |
|---|---|---|---|
| ECE-030 | Define capability algebra | Typed kinds, scopes, operations, ceilings, revocation and delegation | Open |
| ECE-031 | Define function effect summaries | Required capabilities and effect rows per function | Open |
| ECE-032 | Prove call-site authority inclusion | Callee requirements included in explicitly delegated caller authority | Open |
| ECE-033 | Prove attenuation/no escalation | Callee authority is a subset of caller authority; no ambient acquisition | Open |
| ECE-034 | Bind launch grant and provenance | Certificate covers actual launch grant, policy decision and delegation chain | Open |
| ECE-035 | Prove host-adapter mediation | Every privileged effect passes through the declared capability gate | Open |
| ECE-036 | Specify secret non-disclosure separately | Explicit information-flow property; capability possession alone is not confidentiality | Open |

## E. Assurance integrity and reproducibility

| ID | Obligation | Required evidence | Status |
|---|---|---|---|
| ECE-040 | Define evidence freshness | Exact source, compiler, verifier, semantics and toolchain identities | Open |
| ECE-041 | Audit proof dependencies | Lean axiom report, imported trust roots, no unfinished proofs/local axioms, independent replay | Open |
| ECE-042 | Establish checker TCB minimisation | Component inventory, code size/complexity, dependency and attack-surface review | Open |
| ECE-043 | Negative-control certificate suite | Forged, stale, malformed, truncated, oversized and mismatched evidence rejected | Open |
| ECE-044 | Reproducible build and verification | Pinned toolchains, exact commit, one-command scripts and expected outputs | Open |
| ECE-045 | Independent review | Reviewer not author of implementation/proofs; issues and dispositions recorded | Open |

## F. Initial milestone gates

### M0 — Contract reconciliation

- [ ] Reconcile normative CCAM v0.1 with latest evaluator and current draft branches.
- [ ] Resolve the known mismatch between final-instruction terminality in the Lean model and reachability-based fall-through in the normative contract.
- [ ] Identify exact multi-function and decoder status on the chosen base commit.
- [ ] Reconcile grant/policy semantics with a capability model; do not assume they are interchangeable.
- [ ] Freeze a narrow, versioned proof target before changing machine semantics.

### M1 — Structural certificate prototype

- [ ] Define canonical artefact and certificate schemas.
- [ ] Implement a bounded decoder and independent checker for the supported CCAM subset.
- [ ] Emit a certificate for typed registers, branch/call targets, signatures, reachability and resource admission.
- [ ] Add digest/semantics/contract binding and mutation-based negative tests.
- [ ] Demonstrate rejection of a deliberately forged proof object.

### M2 — Evaluator refinement

- [ ] Extend the Lean machine to multi-function calls and shared resource counters.
- [ ] Define a concrete-to-abstract state relation.
- [ ] Prove initial-state and one-step correspondence.
- [ ] Prove terminal outcome correspondence, including trap precedence and failure atomicity.
- [ ] Run formal build, axiom audit and independent proof replay on exact head.

### M3 — First compositional resource and capability slice

- [ ] Prove fuel and stack summary rules for a loop-free, non-recursive subset.
- [ ] Add one explicit bounded effect (prefer bounded output) with a typed capability token.
- [ ] Prove call-site capability inclusion and host-adapter mediation for that effect.
- [ ] Measure certificate/checker and runtime overhead against baseline.

## G. Decision rules

- If exact static resource bounds are not derivable, retain runtime ceilings and mark static bound UNKNOWN.
- If a capability effect cannot be mediated at every host boundary, issue no authority guarantee for that effect.
- If the checker cannot independently validate a claim, omit it from the certificate.
- If the implementation/model relation requires an unproved assumption, label the result conditional and expose that assumption.
- If normative specification and implementation disagree, stop and reconcile the contract before adding proofs.
