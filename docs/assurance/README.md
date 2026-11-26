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

Current implementation status as reviewed on 2026-11-26 (mainline snapshot `4a2622e53b11bbe3c08bc7355c8fa9e477dee155`): the production compiler execution path remains generated C followed by GCC/Clang and the Capstan C runtime. Mainline includes the restricted Capstan-native CCAM single-frame evaluator (PR #142), typed in-memory single-frame validator (PR #163), bounded multi-function evaluator (PR #207), checked scalar source lowering (PR #210), and concrete native register tag/field correspondence lemmas (PR #205). These are separate C-free research/verification slices; they are not wired into the production compiler CLI. The CCAM specification explicitly says the implementation is not yet a conforming v0.1 machine and is not connected to the Lean model by an evaluator-refinement theorem. The Linux x86-64 native-emitter source is present as a narrow experimental prototype (documented in `docs/architecture/CCAM-NATIVE-BACKEND.md`, associated with PR #212); it is not a production backend, does not provide full CCAM conformance, and has no machine-code refinement theorem. The v1.0 design gate requires a C-free production path on Linux, macOS and Windows; this remains a target, not evidence that those backends exist. The runtime memory/lifetime model remains qualified. The machine-readable claim manifest is stale and incomplete and must be refreshed before any assurance claim is promoted.
