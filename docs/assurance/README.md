# Assurance pack

Documents for organisations assessing Capstan, in particular government and defence users
([DESIGN-MAP.md](../DESIGN-MAP.md), section 9).

| Document | What it covers |
|---|---|
| [EXECUTION-ASSURANCE-ARCHITECTURE.md](EXECUTION-ASSURANCE-ARCHITECTURE.md) | Current production and C-free execution paths, formal-model evidence rail, implementation-refinement gaps and machine-readable boundary register |
| [ASSURANCE-CASE.md](ASSURANCE-CASE.md) | Assurance-case structure, evidence classes, claim lifecycle and enforceable promotion requirements |
| [MEMORY-SAFETY.md](MEMORY-SAFETY.md) | Capstan's guarantees mapped to the memory-safe language guidance of the Five Eyes cyber agencies, including ASD's ACSC, and what is not yet memory-safe |
| [THREAT-MODEL.md](THREAT-MODEL.md) | What Capstan defends against, its assumptions, its trusted base today, what is out of scope and the residual risks |
| [GRANT-SECURITY.md](GRANT-SECURITY.md) | Reference semantics and claim-specific assurance for policy grants, including limits and differential verification plan |
| [ISM-MAPPING.md](ISM-MAPPING.md) | The toolchain, process and tests mapped to the ISM's software development controls (September 2026) and NIST SP 800-218 (SSDF 1.1) |
| [EVIDENCE-FRESHNESS.md](EVIDENCE-FRESHNESS.md) | How implementation and evidence changes invalidate assurance reviews and records |
| [FORMAL-VERIFICATION-MATRIX.md](FORMAL-VERIFICATION-MATRIX.md) | Machine-checked proof obligations, current coverage, specification gates and acceptance criteria |
| [V1-RELEASE-SCORECARD.md](V1-RELEASE-SCORECARD.md) | Release-by-release evidence register and mandatory v1.0 security/assurance gates |
| [FORMAL-VERIFICATION.md](FORMAL-VERIFICATION.md) | Allocator/GC abstract-model verification scope, implementation blockers, proof layers and evidence status |

These documents describe the repository as it is, and claim only what it demonstrates. They are
maintained with each release: before a release is tagged, each is checked against the code, tests
and the other documents ([CWE-COVERAGE.md](../CWE-COVERAGE.md), [CWE-ATLAS.md](../CWE-ATLAS.md),
[SECURITY.md](../../SECURITY.md)), and against the current edition of the ISM, which ASD publishes
quarterly, and of the SSDF.

## Reviewed implementation boundary

This assurance-pack baseline is anchored to mainline commit
`fa7cbc216c2f91aac64503aeeaefa86c831e5a43` (2026-11-26). The production compiler
execution path remains generated C followed by GCC/Clang and the Capstan C runtime.
Mainline includes restricted Capstan-native CCAM evaluation and validation, bounded
multi-function execution, checked scalar source lowering and selected Lean representation
lemmas. These are C-free research/verification slices, not an end-to-end formally verified
production compiler path. The CCAM evaluator is not yet connected to the Lean model by a
complete evaluator-refinement theorem; the experimental Linux x86-64 native emitter is
not a complete production backend. The C-free production toolchain across Linux, macOS
and Windows remains a target.

The runtime memory/lifetime model remains qualified. The threat model records residual
CWE atlas gaps, trusted-base risks, platform coverage limits and the lack of completed
independent external security assessment. The CI matrix at this baseline exercises Ubuntu
with GCC, Ubuntu with Clang and macOS with Clang; Windows and ARM64 are not covered by
that matrix.

The machine-readable claim manifest deliberately retains proposed claims until their
evidence has been refreshed and reviewed. The assurance validator checks schema, path
containment, Git ancestry, evidence freshness and minimum promotion-record requirements.
Those checks do not prove that a claim is true or that a reviewer is substantively
independent. See [ASSURANCE-CASE.md](ASSURANCE-CASE.md). Missing, stale, unrun or
unreviewed evidence is not a pass.
