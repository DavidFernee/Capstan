# CAP-007 — Schedule and dependency network

Planning assumptions: five existing hourly agent streams are not five full-time engineers; throughput and CI queue time are unmeasured. WBS estimates are effort ranges, not elapsed forecasts. Re-estimate after A01 with measured throughput and remaining scope.

| Milestone | Indicative elapsed week | Gate |
|---|---|---|
| Baseline | 1–2 | G0 |
| Semantic contracts | 2–5 | G1 |
| Scalar evaluator/frontend | 4–10 | G2 |
| Scalar native | 8–16 | G3 |
| Managed runtime | 12–24 | G4 |
| Optimisation and certification | 16–28 | G5 |
| Self-hosting candidate | 24–40 | G6 |
| Fully assured release | Not yet estimable | G7 |

Likely dependency chain A01 -> B02 -> B04 -> D01 -> D02 -> D03 -> F01 -> F02 -> F03; E01 and D04 can become competing critical paths. Not a computed CPM until task estimates and capacity are validated. C01/C02/C03/C04 can overlap after their interfaces freeze. Optimisation must not delay the initial unoptimised vertical slice; G5 is not a prerequisite for experimental self-hosting.

First tranche: inventory main and existing PRs; reconcile #542; consume #540/#545 result-ABI evidence and #547/#549 proof work; freeze scalar acceptance corpus; assign next unclaimed task. Weekly update planned vs actual, capacity, CI latency, dependencies and risk. Escalate unresolved semantic ambiguity rather than building around it.
