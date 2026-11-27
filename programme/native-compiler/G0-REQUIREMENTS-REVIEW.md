# G0 requirements review
2026-11-27. Review of CAP-001 parent coverage and RTM-001–007. All acceptance statuses remain open. Parent coverage is not atomic completeness.
| Parent | Matrix coverage | Review disposition |
|---|---|---|
| R01 | 001/004 | Source grammar, binding, checked AST and lowering; add import graph and effect coverage at G1 |
| R02 | 001 | Canonical decoder, calls, validation; normative profile reconciliation G1 |
| R03 | 001/003 | Overlap terminal outcomes; use R03 as semantic parent, R07 as transport |
| R04 | 002/005 | GC subordinate to managed heap; distinguish arena/region/heap |
| R05 | 001/002/003/005 | Separate semantic fuel, physical resource and host timeout bounds |
| R06 | 004/007 | Partial coverage; dedicated authority, taint, secrecy and host boundary evidence required |
| R07 | 003 | Assembly/direct profiles separate; object loader and ABI proof pending |
| R08 | 007 | Pass validation, resource preservation, relational security |
| R09 | 006 | S0–S3, workload closure and dependency audit |
| R10 | 006/007 | Reproducibility covered; performance/target acceptance workload criteria missing |
| R11 | 006/007 | Manifest and trace binding; governance review and artifact checker pending |

## Additional controlled obligations (proposed, not accepted)
R06.01 capability acquisition/attenuation/revocation; R06.02 host-call mediation and absence of ambient authority in assured profile; R06.03 taint and contextual sink preservation; R06.04 explicit secret lifecycle; R06.05 relational confidentiality with declared observables; R06.06 concurrency exclusion or versioned memory model. B05/D04 own these; require negative corpus and source-to-native correspondence.
R10.01 pinned benchmarks for compile latency, runtime, peak memory and code size; R10.02 explicit per-target ABI and host qualification; R10.03 repeatability with environment and variance report. F03 owns thresholds before release measurement; do not invent numeric targets.
R11.01 manifest checker strict rejection of mismatch, malformed inputs and unsupported policy; R11.02 independently reviewed TCB and gate evidence; R11.03 scope and version of proof claims. A01/E02/F03.
These 12 supplemental obligations are coverage candidates, not an additive completion denominator.

## Native documentation disposition
#545 closed unmerged with failed general CI, successful formal/CodeQL. Do not merge or revive it without successor reconciliation. Main assembly documentation still has duplicate section 1, obsolete CLI status and BSS-stack wording; current verification/ccam_native_x64.cap has bounded mmap guard page and 32 MiB cap. #552 owns overlapping native files; request its owner preserve profile distinction and correct documentation. #552 is open; its result record remains experimental and C driver remains. #542 exact head aa19a6dd formal success, CI running, CodeQL queued at inspection. #548 prior head ada9b925 checks queued. No build executed. G0 HOLD.
