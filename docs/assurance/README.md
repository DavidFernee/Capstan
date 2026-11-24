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
| [V1-RELEASE-SCORECARD.md](V1-RELEASE-SCORECARD.md) | Release-by-release evidence register and mandatory v1.0 security/assurance gates |
| [FORMAL-VERIFICATION.md](FORMAL-VERIFICATION.md) | Allocator/GC abstract-model verification scope, implementation blockers, proof layers and evidence status |

These documents describe the repository as it is, and claim only what it demonstrates. They are
maintained with each release: before a release is tagged, each is checked against the code, tests
and the other documents ([CWE-COVERAGE.md](../CWE-COVERAGE.md), [CWE-ATLAS.md](../CWE-ATLAS.md),
[SECURITY.md](../../SECURITY.md)), and against the current edition of the ISM, which ASD publishes
quarterly, and of the SSDF.

Current implementation status as reviewed on 2026-11-25 (mainline snapshot `360043c8704546857caa4c82f2978c7709399016`): the integrated execution path remains the C backend; the C-free/CCAM programme is in progress and Lean proofs cover selected model fragments only. The v1.0 design gate now requires a C-free production path on Linux, macOS and Windows, but that requirement is not evidence that those backends already exist. Open pull requests and workflow definitions are not evidence of merged implementation or a completed release. The runtime memory/lifetime model is normative design documentation, but its implementation conformance is explicitly qualified. The claim manifest (`claims.json`) is intentionally left in `proposed` state and records an older evidence snapshot; it must be refreshed and reviewed before any assurance claim is promoted.
