# RFC 0021 (provisional) — Bounded types, termination and compositional resource safety

Status: proposal, not ratified or implemented. Baseline d23e8debe8b8c2e7521553970b01d49f51760c0a.
Extends the [bounded-input contract](../architecture/BOUNDED-INPUT-CONTRACT.md) and [resource analysis survey](../research/COMPOSITIONAL-RESOURCE-ANALYSIS-SURVEY.md), issue #221. Reconcile with Working Standard v0.7 before ratification. Existing G0–G3 acceptance criteria are unchanged.

## Safety contract

Every admitted scalar operation must preserve its declared value domain or produce a specified failure before publishing an invalid value. No unchecked narrowing, wrapping arithmetic or resource-meter bypass is available in the mandatory security profile. Static proofs may discharge checks only when bound to the exact checked operation and execution semantics. Unknown analysis results retain checks or reject admission where a static guarantee is required.

A proposed bounded integer type denotes a closed interval [lo, hi] contained in signed 64-bit integers, with lo <= hi. Bounds are initially compile-time constants. Widening is permitted when the source interval is contained in the destination interval. Narrowing requires a proof or explicit checked conversion with a typed failure outcome. Untrusted provenance is not removed by range checking. Arithmetic retains existing checked signed-64 semantics; inferred ranges are computed in mathematical integers, not wrapping machine arithmetic. Reject invalid interval declarations and impossible conversions. Do not introduce syntax until grammar and error contracts are reviewed.

## Resource contract

Separate cumulative work and traffic, live frame/stack/heap occupancy, and platform-dependent deadlines. Every execution receives finite enforced budgets; nested calls cannot reset or refund cumulative fuel. Preflight frame admission before mutation, preserve existing failure precedence, and release frame occupancy exactly once on return. A static bound is not a wall-clock guarantee. External calls require separate authority and deadline contracts. All executions retain the same mandatory security invariants. A successful-termination contract requires a proof; otherwise mandatory metering permits specified exhaustion, not an alternative security profile.

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

## Proposed normative amendments

These identifiers supplement Working Standard v0.7; they do not supersede existing requirements. Number 0021 is provisional pending governance review.

| ID | Requirement (MUST) | Existing RFC dependencies |
|---|---|---|
| CAP-BND-001 | Admit only nonempty closed intervals within Int64; validate declarations before use. | 0002, 0003 |
| CAP-BND-002 | Infer conservative ranges in mathematical integers; unknown is never a proof. | 0003, 0009 |
| CAP-BND-003 | Require containment proof or explicit checked narrowing before publication; preserve provenance. | 0003, 0007, 0009 |
| CAP-BND-004 | Preserve checked arithmetic, operand order and exact trap semantics; prove closure before removing checks. | 0004, 0009 |
| CAP-BND-005 | Require well-founded decreasing measures on recursive cycles for successful-termination claims; enforce depth and fuel regardless. | 0004, 0015 |
| CAP-BND-006 | Require finite iteration bounds for static cost claims; meter all other iteration. | 0004, 0015 |
| CAP-BND-007 | Compose conservative cumulative costs across calls and branches. | 0015 |
| CAP-BND-008 | Account for peak stack and live memory including retained state and temporary overlap. | 0005, 0015 |
| CAP-BND-009 | Conserve aggregate budgets across calls, tasks and host adapters; no fuel reset. | 0006, 0008, 0010, 0015, 0016 |
| CAP-BND-010 | Preflight before prohibited effects; failed admission must not partially publish or reserve; preserve prior committed effects and charges. | 0004, 0015 |
| CAP-BND-011 | Remove checks only with sound, operation-specific evidence preserving observable failures and logical charges. | 0013 |
| CAP-BND-012 | Bound analysis, proof checking and certificate decoding; reject unknown mandatory evidence. | 0001, 0018 |
| CAP-BND-013 | Preserve obligations through validated CCAM, native lowering and linking; bind evidence to exact artifacts. | 0011, 0013 |
| CAP-BND-014 | Establish named vulnerability-class exclusion only under explicit noncircular adversary and environment assumptions, with concrete refinement. | 0017, 0018 |

## Mathematical core

Let I(l,h) = {x in Z | l <= x <= h}, with MIN <= l <= h <= MAX. The judgement Gamma |- e : I(l,h) means every successful evaluation of e in a related environment yields a member of I(l,h); it does not assert termination or absence of traps. Subsumption I(a,b) <: I(c,d) holds iff c <= a and b <= d. Checked narrowing succeeds exactly on membership; its failure outcome must be ratified before implementation. No conversion changes authority or taint.

For addition the mathematical interval is [a+c,b+d]; subtraction [a-d,b-c]; multiplication takes min and max of the four endpoint products. If the result is not contained in Int64, retain the existing overflow check; do not clamp away a possible failure. Division and remainder require separate zero and MIN/-1 reasoning, preserving MIN % -1 = 0. Branch refinement must be sound on both successors and joins must overapproximate all reachable states. Analysis failure is conservative.

For a recursive strongly connected component, a successful-termination certificate supplies a measure into a well-founded order, decreasing on every recursive edge. Loop certificates analogously establish invariant preservation and strict descent on every back edge. Termination alone is not a cost bound. Derive a finite cost recurrence including calls, guards and failures; otherwise retain metering without a successful-termination claim.

For cumulative dimension d, sequential costs add and exclusive branches take the maximum; total concurrent work sums across tasks. For live occupancy, a summary (peak, retained) composes sequentially as peak=max(p1,r1+p2), retained=r1+r2 for nonnegative retained additions; general release and ownership transfer require a state-indexed summary. Concurrent peak must conservatively include simultaneous live sets. Runtime charges require 0 <= q <= limit-used before addition. Live leases are released exactly once; cumulative charges never refund. Logical cost does not establish elapsed time.

## Acceptance and implementation traceability

- BND-001–004: parser/checker, interval soundness and conversion theorems, exact/one-outside and malformed declaration vectors.
- BND-005–008: cost semantics, recursion and loop certificates, factorial induction, mutual recursion and nondecreasing mutant rejection, exact/one-short fuel and depth, retained-memory overlap tests.
- BND-009–010: CCAM and runtime admission conservation, nested and concurrent budget tests, failure precedence and atomicity.
- BND-011–013: validator and compiler refinement, certificate size limits, stale or forged evidence rejection, differential execution including logical charges, negative optimisation controls.
- BND-014: map CWE-190/191/681/369/674/835/789/770/400 to scoped theorems and concrete evidence; distinguish prevented prohibited effects from permitted exhaustion and host failures.

Use existing C01/C02/C03 and later managed-runtime/optimisation work packages as integration points, with separate approved scope and traceability. No retrospective G0–G3 criterion changes. Independent review must reconcile concrete syntax, failure codes, ABI, cost units and certificate trust before ratification. No implementation or proof execution is claimed by this amendment.
