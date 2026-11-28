# Ballast — C-to-Capstan security-preserving migration RFC

**Status:** Proposed; implementation deferred  
**Revision:** 0.1  
**Date:** 2026-11-29 (AEDT)  
**Authority:** Subject to programme approval; does not amend the language or CCAM specifications.  
**Dependencies:** [Native compiler architecture](NATIVE-COMPILER-ARCHITECTURE-RFC.md), [design map](../DESIGN-MAP.md), [threat model](../assurance/THREAT-MODEL.md), [CWE coverage](../CWE-COVERAGE.md).

## 1. Objective

Ballast discovers security defects in existing C software by attempting security-preserving migration to Capstan. Translate what can be established safe; identify what cannot; never weaken Capstan to accommodate C. Investigate whether mandatory target invariants reveal defects missed by conventional tooling. Discovery of novel vulnerabilities is a research hypothesis, not an established capability.

Ballast is an optional upstream tool, not part of the compiler trusted path or S1/G0–G3 acceptance scope. CCAM remains the canonical target execution semantics. No generated C, C runtime dependency or unchecked FFI is permitted in the eventual C-free Ballast production profile. External C tools may serve as isolated research oracles, not trusted production dependencies.

## 2. Normative requirements

MUST denotes an acceptance requirement for the proposed component, not a claim about current implementation.

| ID | Requirement | Acceptance evidence |
|---|---|---|
| B01 | Model the selected C dialect, ABI, preprocessing configuration, defined behaviour, implementation-defined choices and unspecified behaviour explicitly. | Versioned source semantics and conformance corpus |
| B02 | Emit only ordinary checked Capstan source; no escape hatch, raw pointer emulation or weakening of target checks. | Negative tests and compiler validation |
| B03 | Generate source-level security obligations for the supported subset. | Obligation coverage matrix with positive and negative fixtures |
| B04 | Preserve original source spans, macro expansion provenance and stable declaration identities. | Round-trip diagnostic mapping tests |
| B05 | Produce replayable counterexamples where feasible; label solver timeouts and unknowns distinctly. | Reproduction against model and independent validation |
| B06 | Independently validate translation against explicit source and target semantic profiles. | Checked certificate or bounded evidence with scope disclosed |
| B07 | Separate remediation from semantics-preserving translation. Require explicit approval for changed behaviour. | Patch/diff and regression evidence |
| B08 | Emit machine-readable assurance records including assumptions, residual obligations and exact revisions. | Schema, verifier and tamper-rejection tests |
| B09 | Evaluate detection and migration against independent baselines with reproducible methodology. | Frozen corpus, raw results and adjudication |
| B10 | Implement production Ballast in Capstan with bounded parsing, analysis and certificate handling. | C-free dependency audit and reproducible build |

## 3. Architecture

C source and build profile -> bounded preprocessor -> C parser/resolver/type checker -> C semantic IR -> obligation generation and analysis -> Capstan source translation -> normal Capstan checker -> validated CCAM -> native compiler and assurance manifest.

The C IR is not CCAM and has no authority over target semantics. Ballast MUST NOT bypass the Capstan source checker. A separate validation component checks the source-to-target relation; the generator is not trusted merely because it produced compiling code. Anchor may consume diagnostics through a versioned interface; neither Anchor nor Shroud is a prerequisite.

Initial profile: hosted ISO C17 subset, explicit ABI and implementation choices, scalar operations, structured control flow, fixed arrays and simple functions. Introduce allocation, aggregate layout, pointers with known provenance, aliasing, callbacks and concurrency only under separately reviewed contracts. Inline assembly, arbitrary pointer/integer casts, unrestricted external calls, variadic interfaces, volatile device access and unsupported compiler extensions remain explicitly excluded until modelled. Unsupported constructs MUST NOT be described as vulnerabilities.

## 4. Semantic and security obligations

For supported source P, environment E and declared precondition A, translation T(P) must refine permitted observable C behaviours for defined executions under A, preserving relevant termination, return values, externally visible effects and specified ordering. A deterministic target may select an allowed unspecified C behaviour only where the profile explicitly permits refinement. No equivalence claim is made for executions with undefined behaviour. New target traps on defined source executions are not semantic preservation: they require proof of unreachability or explicit remediation approval. Resource bounds and external effects are part of the declared relation.

Generate obligations for arithmetic (including unsigned wrap in security-relevant size calculations), array bounds, initialisation, lifetime, allocation, aliasing, pointer provenance, nullability, concurrency, capabilities, taint and secret flow where the target profile supports them. Distinguish source undefined behaviour from violations of stronger target policies. A compiler rejection alone is not evidence of a source vulnerability. Security claims must be scoped to the exact enforcement and proof coverage documented by Capstan.

### Dispositions

- VERIFIED: independent checker establishes stated obligation under recorded assumptions.
- GUARDED: target runtime enforcement exists; not equivalent to a proof of source safety.
- COUNTEREXAMPLE: candidate witness violates the stated obligation; requires independent replay and reachability analysis.
- UNKNOWN: insufficient evidence, timeout or unresolved environment.
- UNSUPPORTED: source feature outside profile.
- REMEDIATION_REQUIRED: translation would change defined behaviour.
- CONFIRMED_VULNERABILITY: separately adjudicated reachable defect with security impact; not an automatic compiler verdict.

A translation may be called verified only when all applicable semantic obligations are independently discharged. Partial or guarded artifacts must be labelled accordingly; unsupported or unresolved obligations cannot silently disappear.

## 5. Diagnostics and evidence

Versioned records MUST include source revision/hash, build configuration, dialect/ABI, original span and macro chain, stable obligation ID, invariant, disposition, assumptions, target span, checker/solver version, resource limits, optional witness and validation result. CWE mapping is advisory and must not inflate findings. Separate source defects, target-policy incompatibilities and tooling limitations. Bound input size, macro recursion, IR nodes, solver steps, memory, certificate size and diagnostic volume; exhaustion fails closed.

Treat source code, build metadata and certificates as untrusted. Do not run arbitrary project build scripts or generated executables outside an isolated, authorised environment. Minimise verifier TCB, record external models and dependencies, and ensure reproducible evidence.

## 6. Research and evaluation

Hypothesis: target security obligations expose previously unrecognised security defects and provide useful migration evidence beyond existing analyses. Compare against Clang Static Analyzer, Frama-C and relevant C-to-Rust migration tooling on their supported scopes; use sanitizers as complementary dynamic evidence. Evaluate on Juliet/SARD fixtures, historical vulnerable/fixed pairs, then authorised open-source projects. Freeze corpus revisions, profiles, budgets and baseline versions; separate development and held-out evaluation data. Blind adjudication where practicable.

Report precision, recall on labelled cases, unknown/unsupported rates, translation coverage, proof discharge rates, witness reproducibility, semantic regressions, runtime/compile-time overhead and independently confirmed novel findings. Do not treat unlabelled code as defect-free or extrapolate results beyond the corpus. Record false positives and negative results. Coordinate disclosure privately with maintainers before publication of novel findings; publish research artifacts only when appropriate.

## 7. Deferred implementation gates

| Gate | Deliverable | Exit condition |
|---|---|---|
| BL0 | Scope and formal contracts | Approved source/target profiles, threat model, metrics and dependencies |
| BL1 | Bounded C frontend | Conformance and adversarial parser tests pass; provenance retained |
| BL2 | Obligation engine | Known positive/negative fixtures and explicit unknown dispositions |
| BL3 | Restricted translation | Checked Capstan output and independent semantic validation |
| BL4 | Assurance and remediation | Evidence schema, verifier, explicit patch workflow |
| BL5 | Empirical evaluation | Reproducible baselines and independently adjudicated findings |
| BL6 | C-free release and Anchor integration | Dependency audit, exact-head acceptance and reviewed residual risks |

BL0 implementation authorisation requires a sufficiently stable native compiler, checked source and CCAM contracts, documented security guarantees and programme-owner approval. This RFC alone does not authorise implementation or impose any current gate dependency. No claim of formal verification, complete C compatibility, vulnerability discovery or production readiness follows from adoption.

## 8. Open decisions

Exact C semantics formalisation and proof infrastructure; ABI/profile expansion order; certificate format; benchmark licensing; disclosure governance; minimum acceptance thresholds to be agreed before held-out evaluation. All remain subject to independent review and programme authority approval.
