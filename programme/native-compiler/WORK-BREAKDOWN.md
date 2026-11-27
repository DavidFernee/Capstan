# CAP-003 — Work breakdown structure

Estimates are engineer-weeks of remaining package effort, provisional pending A01. Owners are roles, not assigned people or agents. All packages begin as candidate/unverified; reuse existing work rather than rewrite it.

| ID | Package | Owner role | Prerequisites | Effort | Exit deliverable |
|---|---|---|---|---|---|
| A01 | Baseline inventory | Integration | — | 1–2 | Pin main, map modules/issues/PRs and evidence; reconcile #542 |
| B01 | Source semantics | Frontend | A01 | 1–2 | Approved accepted subset, evaluation order, traps, types |
| B02 | Scalar CCAM and decoder | CCAM | A01 | 2–4 | Closed schema, exact numbers, canonical calls, bounded decoding |
| B03 | Result and native ABI | Native | B02 | 1–2 | Exact terminal outcomes; coordinate #540; no exit-code aliasing |
| B04 | Memory and resource contracts | Runtime | B02 | 2–4 | Typed handles, layout, roots, quotas, atomic failures |
| B05 | Effects and capability contracts | Security | B01,B04 | 2–4 | Explicit authority and host-boundary policy |
| C01 | Scalar Lean refinement | Formal | B02 | 3–6 | Concrete evaluator correspondence; coordinate #547/#549 |
| C02 | Source lowering | Frontend | B01,B02 | 3–6 | Checked source to validated CCAM; unsupported constructs rejected |
| C03 | Scalar native vertical slice | Native | B02,B03 | 3–6 | Same-CCAM differential execution including traps and fuel |
| C04 | Object writer and linker | Native | B03 | 3–6 | Deterministic ELF, relocations, permission validation |
| D01 | Aggregate evaluator and references | CCAM | B04 | 4–8 | Versioned aggregate profile and conformance |
| D02 | Allocator and collector | Runtime | B04,D01 | 5–10 | Root completeness, stale-reference rejection, bounded collection |
| D03 | Managed native lowering | Native | C03,D01,D02 | 4–8 | Memory, calls and ABI correspondence |
| D04 | Security refinement | Security | B05,D03 | 4–8 | Capability/effect and information-flow preservation |
| E01 | Native refinement | Formal | C01,C03,C04,D03 | 6–12 | Proof or sound validation from CCAM to exact executable |
| E02 | Optimisation and certifier | Formal/Native | C01,C03 | 4–8 | Pass traces, independent validation, directed fuzzing |
| F01 | Compiler workload closure | Frontend/Runtime | C02,D03 | 4–8 | Compile actual compiler sources; dependency inventory |
| F02 | Self-host bootstrap | Integration | F01,C04 | 4–8 | S0–S3 evidence; no C/Python production dependency |
| F03 | Release acceptance | Integration | F02,E01,E02,D04 | 3–6 | Reproducibility, security review, benchmarks, exact evidence |

Each package is decomposed into one-to-three-day tasks with one active claim, bounded file scope, requirements IDs, tests, proof obligations and PR. Definition of done: approved contract, code where needed, exact-head checks, evidence review, merged and accepted; distinguish tested from proved. Avoid opening duplicate issues before mapping existing issues in A01.
