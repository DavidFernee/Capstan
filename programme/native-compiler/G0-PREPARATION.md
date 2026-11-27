# G0 preparation — 2026-11-27
## Architecture disposition
Compared full RFC and ledger text at #542 aa19a6dd and #544 5d83b352. Retain #542. Unique #544 lines are older CHIR/CMIR/CLIR/CTIR terminology, narrower pass contracts and duplicate translation rows; valid substance covered by #542. Do not revive #544.
## Native documentation
#540 closed unmerged; successor #552 head 42ef40c1 open, claims direct static ELF, bounded scalar fuel, fd3 raw and opt-in CCAMRES record. No direct calls/output, C driver, no native refinement. #545 documents assembly profile, not direct profile. Preserve both profiles and require #552 reconciliation before claiming result ABI closure. #545 also has duplicate section number 1 and stale BSS wording; owner should correct against main, not overwrite concurrent #552.
## Ownership proposal
Integration A01 F02 F03; native compiler B03 C03 C04 F01; CCAM/runtime B02 B04 D01 D02; frontend (native stream) B01 C02; security B05 D04; formal C01 E01; native/runtime D03; formal/native E02. Cross-stream reviewers required for I01–I07. Existing schedules unchanged, ownership confirmation open.
## Evidence manifest (fill on integrated main)
- main commit/tree, clean checkout status, submodule/dependency digests
- RFC and programme merged PRs and exact heads, workflow URLs and conclusions
- host OS/architecture, toolchain versions and hashes, compiler seed identity, flags
- repository-prescribed commands, exit codes, stdout/stderr artifact digests, test counts and failures
- Lean version, axiom audit output, theorem/profile scope
- independent reproduction identity, comparison and differences
- known baseline defects, later-gate obligations, reviewer, date and disposition
No values invented for unexecuted build.
## Requirements review disposition
113 entries include parent/subordinate overlaps (RTM-002/005, RTM-001/003, RTM-003/006); retain trace links, never add them as independent completion denominator. All 19 RFC gaps mapped. Dedicated security and performance evidence remain G1/G7 obligations. Atomic full inventory review against integrated main still open.
G0 remains HOLD. No fresh build or proof executed.
