# G0 supplemental obligation disposition

Source: G0-REQUIREMENTS-REVIEW.md; architecture RFC sections below. Recommend retaining all twelve as controlled child requirements; no waiver or implementation acceptance. Proposed gate allocations require owner and reviewer approval. G0 requires the obligation and verification plan to be controlled; later gates require demonstrated satisfaction. R11.02/03 also apply to G0 itself.

| ID | RFC sections | Owner roles | Evidence gates | Required acceptance evidence |
|---|---|---|---|---|
| R06.01 | 9 | B05/D04 | G4/G7 | Capability grant, attenuation and revocation transitions; forged/stale grant negative corpus |
| R06.02 | 9,10 | B05/D04 | G4/G7 | Closed host effect policy; deny ungranted operations in assured profile; audit syscall boundary |
| R06.03 | 9 | B05/D04 | G4/G7 | Stable binding/access path provenance; contextual sink negative corpus; #554 limited candidate evidence |
| R06.04 | 7.2,9 | B05/D04 | G4/G7 | Explicit secret lifetime and controlled exit wipe; native wipe preservation |
| R06.05 | 5,9 | B05/D04 | G7 | Declare attacker/observable model and relational theorem; do not infer from taint |
| R06.06 | 14 | B05/D04 | G4/G7 | Reject unsupported concurrency or freeze versioned memory model and prove profile safety |
| R10.01 | 15 | F03 | G7 | Pin workload inputs, harness and measurement protocol for latency/runtime/peak memory/code size; approve thresholds before measurement |
| R10.02 | 3.6,10,14 | F03 | G7 | Target-specific ABI and host qualification tests; no inferred portability |
| R10.03 | 13,15 | F03 | G7 | Independent clean rebuild and variance/environment report |
| R11.01 | 6.2,12 | A01/E02/F03 | G5/G7 | Strict bounded manifest parsing; reject mismatched digest, malformed or unsupported policy |
| R11.02 | 11,12 | A01/E02/F03 | G0/G7 | Independent review of TCB and gate evidence; record reviewer, baseline and disposition |
| R11.03 | 11,16 | A01/E02/F03 | G0/G7 | Every claim states version, profile, assumptions and evidence identity; reject unsupported scope |

All 12 remain open for acceptance. No numerical performance thresholds invented. Preserve 113-row original denominator and track these 12 separately until inventory change approval. Existing #554 scope is limited; source-to-native security proof remains outstanding. No test execution or independent approval. G0 HOLD.
