# Bounded scalar values and computation contracts

Status: proposal, not ratified or implemented. Baseline d23e8debe8b8c2e7521553970b01d49f51760c0a.
Extends the [bounded-input contract](../architecture/BOUNDED-INPUT-CONTRACT.md) and [resource analysis survey](../research/COMPOSITIONAL-RESOURCE-ANALYSIS-SURVEY.md), issue #221. Reconcile with Working Standard v0.7 before ratification. Existing G0–G3 acceptance criteria are unchanged.

## Safety contract

Every admitted scalar operation must preserve its declared value domain or produce a specified failure before publishing an invalid value. No unchecked narrowing, wrapping arithmetic or resource-meter bypass is available in the safe profile. Static proofs may discharge checks only when bound to the exact checked operation and execution semantics. Unknown analysis results retain checks or reject admission where a static guarantee is required.

A proposed bounded integer type denotes a closed interval [lo, hi] contained in signed 64-bit integers, with lo <= hi. Bounds are initially compile-time constants. Widening is permitted when the source interval is contained in the destination interval. Narrowing requires a proof or explicit checked conversion with a typed failure outcome. Untrusted provenance is not removed by range checking. Arithmetic retains existing checked signed-64 semantics; inferred ranges are computed in mathematical integers, not wrapping machine arithmetic. Reject invalid interval declarations and impossible conversions. Do not introduce syntax until grammar and error contracts are reviewed.

## Resource contract

Separate cumulative work and traffic, live frame/stack/heap occupancy, and platform-dependent deadlines. Every execution receives finite enforced budgets; nested calls cannot reset or refund cumulative fuel. Preflight frame admission before mutation, preserve existing failure precedence, and release frame occupancy exactly once on return. A static bound is not a wall-clock guarantee. External calls require separate authority and deadline contracts. Unprovable termination is permitted only in an explicitly metered profile, not in a profile promising successful termination.

## Factorial witness

For n in [0,20], factorial returns an integer in [1,2432902008176640000]. Base cases 0 and 1 return 1. On n > 1, n-1 remains in the domain and strictly decreases a natural-number measure. Induction establishes the result and absence of multiplication overflow. At most 20 factorial frames are simultaneously live (plus the entry frame). Exact fuel and stack bytes must be derived from the actual lowered program and frame layout, not inferred from the input interval alone.

Inputs -1, 21, INT64_MIN and INT64_MAX fail domain admission; 0,1,10,20 succeed with 1,1,3628800,2432902008176640000 respectively. Test exact and one-short fuel and depth limits, failed narrowing without publication, aliasing, evaluation order and native/evaluator terminal correspondence. No new trap code is assigned by this proposal.

## Implementation sequence

1. Reconcile grammar, type/effect rules, failure precedence and ABI with the existing standard and scalar contracts.
2. Mechanise interval containment, checked conversion, arithmetic transfer and factorial induction in the existing Lean development.
3. Implement checker range tracking and explicit narrowing; preserve provenance and source evaluation order.
4. Lower residual checks to validated CCAM using an approved representation and failure contract; retain exact fuel semantics.
5. Implement native correspondence and independently validate emitted checks, stack and budget accounting.
6. Bind proofs and conformance evidence to exact source and artifact revisions; audit adversarial boundary cases and optimisation check elimination.

## Assurance boundary

Target exclusion of invalid scalar states, unchecked arithmetic overflow and unmetered internal execution within the specified safe profile. This is not a proof that all vulnerabilities are impossible: application logic, confidentiality policies, compiler correctness, platform faults and external effects require their own threat models and evidence. No new theorem, test execution, or production feature is claimed here.
