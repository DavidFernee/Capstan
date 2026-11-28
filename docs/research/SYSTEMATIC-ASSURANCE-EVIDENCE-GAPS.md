# Systematic assurance: evidence boundaries and remaining work

Status: proposed engineering checklist; not acceptance evidence.

The systematic suite manifest registers executable tests and independent host
oracles. Parameter combinations are design counts, not measured executions.
The targeted mutation inventory is a bounded set, not the population of all
non-equivalent security-critical mutants.

## Production coverage requirements

The generated-C line/branch coverage campaign in PR #670 is useful for
finding execution gaps, but neither branch counts nor #line mappings alone
establish Capstan-source MC/DC.

Before claiming production MC/DC:

1. Assign stable IDs to source decisions and atomic conditions, binding IDs
   to the checked source digest and compiler revision.
2. Record actual evaluated conditions and short-circuit masks, decision
   outcome, and test identity; do not replace unevaluated values with false.
3. Independently compare instrumented and uninstrumented outcomes, including
   traps, evaluation order and resource bounds. Exclude instrumentation
   overhead from production resource-limit claims.
4. Derive witness pairs from observations, with unique-cause versus masking
   MC/DC explicitly identified. Classify infeasible pairs separately; an
   exclusion requires justification and reviewer disposition.
5. Reconcile decision inventory, trace completeness, source mapping and
   artifact hashes at the exact tested commit. Missing or stale observations
   cannot count as coverage.

The existing contract-valuation witness analyser is a precursor to step 4,
not an implementation of steps 1–3.

## Coverage harness audit

Inspection of the PR #670 coverage harness identified these remaining gaps:

- Compiler coverage invokes negative and positive workloads but does not
  classify every observed compiler exit against its expected disposition.
- Auxiliary atlas, fuzz and range/lint workloads use subprocess results
  without enforcing successful completion.
- Runtime coverage skips failed compiler or host compiler builds.
- Runtime timeout handling reports a note rather than incomplete evidence.
- Runtime unit-test build and execution failures are not enforced.
- Generated-code branch counts do not identify atomic source conditions.

These are open findings, not repaired by this checklist. Coordinate with
the coverage PR before modifying the shared coverage runner.

## Mutation acceptance

A baseline must compile and pass. Mutation anchors must identify one exact
source occurrence. Every selected experiment must be recorded. An assertion
failure is distinguished from an unexpected trap, timeout, build failure or
surviving mutant. No mutation score may be inferred from inventory size.
The current target set is intentionally limited to named reference-model
and evaluator behaviors; production runtime and compiler mutation coverage
remain separate work.

## Bootstrap and independent review

The current `bin/capstan test` wrapper invokes a C toolchain. Its passing
results are not a demonstration of C-free S1. Retain independent mathematical
and platform oracles while porting internal test orchestration to Capstan.
Independent review and programme authority disposition remain outstanding.
