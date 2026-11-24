# v1.0 security and assurance release scorecard

## Purpose

This scorecard is completed for each release candidate and regenerated from the exact
release commit. It records evidence for the v1.0 security and assurance acceptance criteria
in [DESIGN-MAP.md](../DESIGN-MAP.md). It is not a substitute for the threat model,
independent review or technical evidence.

A missing or unverifiable entry is UNKNOWN. UNKNOWN is not PASS.

## Release identity

| Field | Value |
|---|---|
| Release/version | |
| Exact source commit | |
| Build/toolchain identity | |
| Supported platforms and architectures | |
| Threat-model revision | |
| CWE atlas revision | |
| Scorecard generated at | |
| Scorecard generator/version | |
| Independent assessor and report | |

## Evidence states

Use exactly one primary disposition per row:

- PREVENTED — an enforceable compiler/language rule rejects the unsafe program and a regression test demonstrates rejection.
- SAFELY REJECTED/CONTAINED — a runtime or boundary check safely stops the operation; availability impact is separately recorded.
- FORMALLY ESTABLISHED — a machine-checked theorem applies to the identified implementation through a documented refinement/correspondence argument and explicit assumptions.
- RESIDUAL — the weakness remains possible within scope; impact, mitigation and explicit acceptance are recorded.
- UNKNOWN — evidence is missing, stale, incomplete or not independently reproducible.

Do not combine these states into a single coverage percentage. Report separate counts and
denominators for each state, including UNKNOWN.

## Property and CWE register

Add one row for every applicable CWE class and every cross-cutting security property. Split
rows where platforms, execution paths or threat scenarios have materially different evidence.

| ID / CWE | Threat scenario and scope | Primary state | Implementation reference | Test / proof reference | Platform(s) | Assumptions / TCB | Residual impact and mitigation | Owner | Independent reviewer | Verified commit | Release disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|
| | | UNKNOWN | | | | | | | | | BLOCKED |

## Mandatory v1.0 gates

For each gate, record PASS, FAIL or UNKNOWN. PASS requires linked evidence at the exact
release commit. A gate with UNKNOWN evidence is not satisfied.

| Gate | Required evidence | Status | Evidence references | Reviewer |
|---|---|---|---|---|
| Threat model | Current, reviewed threat model; platforms, assumptions, TCB and exclusions enumerated | UNKNOWN | | |
| CWE disposition | Every applicable atlas entry has an evidence state and owner; no silent omissions | UNKNOWN | | |
| Memory and lifetime | Bounds, validity and lifetime guarantees cover all execution paths and external-memory boundaries | UNKNOWN | | |
| Concurrency | Implemented sharing, locking, atomicity, teardown and cancellation rules are tested | UNKNOWN | | |
| Input and resource safety | Input validation and CPU, memory, recursion, concurrency and I/O limits are enforced | UNKNOWN | | |
| Authority and isolation | Capabilities/grants, identity binding, least privilege and isolation are tested | UNKNOWN | | |
| Cryptography | Approved policy, known-answer/differential tests and independent cryptographic review | UNKNOWN | | |
| Compiler and runtime | Exact release compiler, lowering, optimiser, code generator, runtime and adapters tested and scoped | UNKNOWN | | |
| Formal assurance | Proof obligations, assumptions, axioms, checker and implementation correspondence documented | UNKNOWN | | |
| C-free execution | Supported release path is C-free on every claimed platform; no silent generated-C fallback | UNKNOWN | | |
| Supply chain | Signed artefacts, SBOM, provenance, reproducibility and independent verification evidence | UNKNOWN | | |
| Independent assessment | External review complete; critical/high findings resolved or formally excepted | UNKNOWN | | |

## Platform execution matrix

Linux, macOS and Windows are the minimum major-platform targets for the v1.0 C-free gate.
Record each supported architecture separately; one passing architecture does not establish
another. A valid C-free path must not generate C, require a C compiler, or depend on a
Capstan-owned C runtime to compile or execute a supported program.

| Platform / architecture | Release backend | No generated C / C compiler / Capstan C runtime | System boundary / TCB | Conformance evidence | Status |
|---|---|---|---|---|---|
| Linux (list each supported architecture) | | UNKNOWN | | | BLOCKED |
| macOS (list each supported architecture) | | UNKNOWN | | | BLOCKED |
| Windows (list each supported architecture) | | UNKNOWN | | | BLOCKED |
| Other target | | UNKNOWN | | | BLOCKED |

Do not list a platform/architecture as supported for the v1.0 assurance claim until its row is
complete. Vendor system libraries and the operating-system kernel may remain below the Capstan
boundary, but must be named as TCB dependencies and their returned data treated as untrusted.

## Proof register

| Theorem / property | Formal model | Production component and revision | Assumptions | Axioms / trusted checker | Refinement or correspondence evidence | Unproved dependencies | Reviewer |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

A proof over an abstract model does not establish a production implementation unless the
correspondence/refinement argument is itself supported. Record counterexamples and failed
proof obligations; do not omit them from the release evidence.

## Residual-risk acceptance

| Risk | Scope and affected assets | Likelihood / impact | Existing mitigation | Further action / owner | Accepted by | Review date |
|---|---|---|---|---|---|---|
| | | | | | | |

No risk is accepted merely because it is outside the current implementation plan. Hardware,
firmware, platform, specification and unknown-vulnerability risks must be stated explicitly.

## Release decision

- [ ] All mandatory gates PASS with exact-commit evidence.
- [ ] No in-scope critical property is UNKNOWN.
- [ ] No unresolved critical/high finding remains without an approved exception and compensating control.
- [ ] Every residual risk has an accountable owner and explicit acceptance.
- [ ] The scorecard, threat model, SBOM, provenance and independent assessment are attached to the release record.

**Decision:** BLOCKED / APPROVED WITH RECORDED EXCEPTIONS / APPROVED

**Decision owner:**

**Date:**

**Exact release commit:**
