# RTM-007 — Optimisation and certification
Authority #542 sections 3–6 and G-12/G-18. All acceptance open.
| ID | Obligation | Required evidence |
|---|---|---|
| OPT01 | Canonical CCAM authority | Derived IR only when justified; closed verifier and roundtrip |
| OPT02 | Pass registry | Version, preconditions, observables, resource policy |
| OPT03 | Arithmetic rewrites | Checked overflow/trap equivalence, boundary oracle |
| OPT04 | CFG transformations | Reachability, effect order and termination relation |
| OPT05 | Bounds elimination | Independently checked proof of bound at use |
| OPT06 | Memory optimisations | Alias, lifetime, capability and secret preservation |
| OPT07 | Allocation/spills | Nonoverlap, spill scheduling, ABI and executable pressure tests |
| OPT08 | Resource equivalence | Preserve semantic charges or formally approved relation |
| OPT09 | Translation validation | Fail closed on unknown, timeout, mismatch; no unverified output |
| OPT10 | Artifact binding | Canonical bounded trace, exact source/target/pass/binary digests |
| OPT11 | Relational security | Separate attacker model; spills and speculative observables |
| OPT12 | Adversarial evaluation | Pass-directed fuzz, mutation tests, benchmarks and independent reviewer |
#528 supplies partial linear-scan/spill primitives; spilled operands currently rejected per PR body. #521 harness remains candidate, not verified optimizer. No fresh tests.
