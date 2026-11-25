# Assurance pack

Documents for organisations assessing Capstan, in particular government and defence users
([DESIGN-MAP.md](../DESIGN-MAP.md), section 9).

| Document | What it covers |
|---|---|
| [MEMORY-SAFETY.md](MEMORY-SAFETY.md) | Capstan's guarantees mapped to the memory-safe language guidance of the Five Eyes cyber agencies, including ASD's ACSC, and what is not yet memory-safe |
| [THREAT-MODEL.md](THREAT-MODEL.md) | What Capstan defends against, its assumptions, its trusted base today, what is out of scope and the residual risks |
| [GRANT-SECURITY.md](GRANT-SECURITY.md) | Reference semantics and claim-specific assurance for policy grants, including limits and differential verification plan |
| [ISM-MAPPING.md](ISM-MAPPING.md) | The toolchain, process and tests mapped to the ISM's software development controls (September 2026) and NIST SP 800-218 (SSDF 1.1) |
| [EVIDENCE-FRESHNESS.md](EVIDENCE-FRESHNESS.md) | How implementation and evidence changes invalidate assurance reviews and records |
| [FORMAL-VERIFICATION-MATRIX.md](FORMAL-VERIFICATION-MATRIX.md) | Machine-checked proof obligations, current coverage, specification gates and acceptance criteria |
| [V1-RELEASE-SCORECARD.md](V1-RELEASE-SCORECARD.md) | Release-by-release evidence register and mandatory v1.0 security/assurance gates |\n| [FORMAL-VERIFICATION.md](FORMAL-VERIFICATION.md) | Allocator/GC abstract-model verification scope, implementation blockers, proof layers and evidence status |

These documents describe the repository as it is, and claim only what it demonstrates. They are
maintained with each release: before a release is tagged, each is checked against the code, tests
and the other documents ([CWE-COVERAGE.md](../CWE-COVERAGE.md), [CWE-ATLAS.md](../CWE-ATLAS.md),
[SECURITY.md](../../SECURITY.md)), and against the current edition of the ISM, which ASD publishes
quarterly, and of the SSDF.

Current implementation status as reviewed on 2026-11-25 (mainline snapshot `18760584765db6c0e540167f5532e23a1b40ffa5`): the integrated compiler execution path remains the C backend. Mainline includes a restricted Capstan-native CCAM single-frame evaluator and bounded typed structural validator for that in-memory instruction subset. These are not a conforming CCAM v0.1 machine, are not connected to the Lean model by an implementation-refinement theorem, and are not wired into production compiler execution. The multi-function evaluator, source lowering and native backend remain unmerged work and are not counted as integrated capabilities. The v1.0 design gate requires a C-free production path on Linux, macOS and Windows; that requirement is a target, not evidence that those backends already exist. The runtime memory/lifetime model remains qualified, and the claim manifest must be refreshed and reviewed before any assurance claim is promoted.
