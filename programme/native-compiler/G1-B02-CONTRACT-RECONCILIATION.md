# G1 B02 — scalar CCAM decoder contract reconciliation

Status: proposed interface review, G0 HOLD; no change to normative v0.1. Packages B01–B05 are G1 semantic contracts; C01–C04 are later implementation packages permitted experimentally.

## Blocking ambiguity B02-01: numeric grammar
CCAM.md §2 accepts mathematically integral JSON numbers in range; CCAM-JSON-DECODER.md §3 rejects all fractional/exponent tokens. Proposal: retain normative v0.1 mathematical interpretation, including 1.0, 1e0 and -0 as exact 1, 1 and 0. Apply identical rule to nonnegative indices by mathematical value. A stricter lexical profile requires explicit version/profile amendment and consumer approval. Do not silently tighten admission.

Exact bounded algorithm candidate: scan JSON grammar and retain significand digits and decimal scale; locate first/last nonzero digits, handle all-zero separately; compare exponent magnitude against a bound derived from token length and signed-64 digit limit before converting exponent; reject nonintegral nonzero values or out-of-range magnitude; accumulate at most 19 significant integer digits using checked negative accumulation, adding bounded trailing zeroes. Never allocate exponent-sized buffers or use floating point. Resource rejection is distinct from numeric range rejection. Validate exact parser refinement and bounded work before approval.

| Vector | Proposed result |
|---|---|
| 1.0, 1e0, 100e-2 | 1 |
| -0, -0.0, 0e999999 | 0 within token limits |
| 1e-1 | nonintegral rejection |
| 9223372036854775807.0 | MAX |
| -9223372036854775808e0 | MIN |
| 9223372036854775808 | range rejection |
| 1e999999, 1e-999999 | range/nonintegral rejection |
| true, null, 01 | type/grammar rejection |

## B02-02 admission and validation
Reconcile proposed aggregate limits with existing per-function evaluator limits; enforce limits before dependent allocation, and specify diagnostic priority when lexical, shape and aggregate violations coexist. No late-only aggregate check may permit excess allocation. Rejected input exposes no partial executable state. Duplicate keys compare decoded exact scalar sequences. Unknown operations and fields rejected including unreachable instructions. Reachable fall-through rejected. Runtime fuel distinct from decoder budget.

## Freeze obligations
I02 producer CCAM and consumers Formal/Native review numeric policy, admission limits and deterministic diagnostic ordering; identify proof relation and adversarial vectors. B03 preserves CCAMRES v1 without competing transport; B04/B05 remain separate contracts. No claims of implementation, test execution or gate acceptance. G1 candidate work may proceed without declaring G0 accepted.
