# Deterministic execution-budget contract proposal

**Status:** research proposal; not normative language semantics and not implemented.  
**Scope:** address the CPU/loop availability gap recorded in issue #428.  
**Compatibility:** this proposal must not silently impose a default fuel limit on existing programs.

## 1. Problem

Capstan documents bounded inputs, heap exhaustion and stack/recursion protection. None bounds total computation. A program can run an arbitrarily long loop, repeatedly call functions, or loop forever without exhausting heap. Wall-clock timeouts are not a deterministic language-level substitute: scheduler load, host clock behaviour and platform differences affect when they fire.

A distinct deterministic execution-work budget is needed. Keep it separate from input bytes, live heap, call depth, deadlines and cancellation. No claim that the current production compiler/runtime provides deterministic CPU or loop bounds is made here.

## 2. Goals and non-goals

A future supported profile should provide deterministic charging, complete coverage of control-flow cycles and calls, compositional accounting, fail-closed exhaustion, checked accounting arithmetic, backend parity, explicit treatment of built-ins/host operations, and a migration path that preserves existing unmetered semantics.

Fuel does not promise termination, a wall-clock upper bound, fairness, pre-emption or universal WCET. It bounds only work charged by a versioned cost model under stated assumptions. Fuel units are abstract units, not CPU cycles or nanoseconds.

## 3. Abstract model

Each top-level execution receives a finite non-negative integer allowance. Its execution context contains remaining fuel, monotonic consumed fuel, a cost-model version, and terminal exhaustion state.

A charge of c units succeeds iff c is valid, non-negative and no greater than the remaining allowance. On success, subtract exactly c and add exactly c to consumed fuel using checked arithmetic. Otherwise terminate with the resource-exhaustion outcome before the operation being charged has observable effects.

Fuel is never replenished by returning from a function, entering a nested scope, allocating less than expected, or taking an error path. Calls share the caller's remaining allowance. They do not receive fresh independent budgets. Any future child-budget partition must be affine/non-duplicable and explicitly reserved.

## 4. Candidate charging rules

These are starting points for review, not an approved schedule.

### 4.1 Source execution

Charge before each source-level statement/expression evaluation that advances execution. Define exact costs for declaration/initialisation, assignment, condition evaluation, branch selection, loop conditions, loop steps, break, continue, return, function entry/return, short-circuit operators, method calls, built-ins, and failure paths.

Every loop condition evaluation is charged, including the final false condition. Every loop iteration must incur a charge even if its body is empty. Short-circuit operators charge only evaluated operands.

The compiler must not erase required charges when optimising away or combining machine instructions. Either charges are explicit semantic effects preserved by all optimisations, or the language defines source-level costs and the compiler establishes that emitted accounting is at least that cost. The latter requires stronger proof/validation.

### 4.2 Loops, calls and recursion

All loop forms and lowered CFG cycles require coverage: while, for, nested loops, break, continue and future constructs. Every reachable back-edge must have a dominating charge, or the verifier must reject the program/profile. Source instrumentation alone is insufficient unless the checker proves complete coverage and generated code cannot bypass it.

Recursive and sequential calls share one total allowance. Call-depth remains a separate live-nesting bound; it does not replace total fuel.

### 4.3 Variable-cost operations

A flat charge is insufficient for work that scales with data. Define explicit formulas for bytes scanned/copied/zeroised, collection elements or buckets examined, comparisons and moves, parser tokens/members/nesting, allocation size, cryptographic operations, and output bytes.

Every variable-cost primitive needs preflight or incremental charging that cannot publish partial state on exhaustion. If incremental charging is used, intermediate state must remain private until success or partial-progress semantics must be explicitly documented.

## 5. Runtime and host boundaries

Fuel cannot bound a host operation that blocks indefinitely. A finite read_line(max) or read_bytes(n) bound does not bound time spent waiting for input; this is separately tracked by issue #473.

Classify every built-in/host operation as:
1. deterministically metered by a specified cost function;
2. bounded by a deterministic resource parameter with a specified cost bound;
3. deadline/cancellation controlled under explicit host clock, scheduler and cancellation assumptions; or
4. potentially blocking/unbounded and unavailable in a strict bounded-execution profile unless the caller explicitly accepts the risk.

Do not equate a timeout with deterministic fuel consumption, or charge a fixed constant for hidden unbounded host work.

## 6. Exhaustion and failure atomicity

Candidate outcome: stable resource-exhaustion trap named execution_budget_exhausted, associated with CWE-400. Exact diagnostic, exit status and machine trap mapping require a normative decision.

Charge before externally visible effects. For compound operations, preflight and reserve the full cost where possible, or keep intermediate state private until success. Do not partially publish collection mutations, output, file writes or decoded values after a failed charge unless partial progress is explicitly part of the API contract. Never refund consumed fuel.

Distinguish fuel exhaustion from heap exhaustion, call-depth exhaustion, input-size rejection, deadline expiry, cancellation and OS errors.

## 7. Decisions required before implementation

1. **Profile:** Should metering initially be opt-in (for example, a declared bounded-execution profile), or become mandatory for a future safe profile? Existing programs must not silently acquire a default cap.
2. **Budget source:** Host/launcher, program manifest, or both? Program code must not increase its caller's allowance.
3. **Cost semantics:** Source-level operations, stable abstract-machine instructions, or conservative upper bounds? Source costs are optimisation-independent but harder to bridge; IR costs are easier to implement but may vary with optimisation.
4. **Built-ins:** Which operations have deterministic formulas, and which are excluded pending host contracts?
5. **Nesting:** How do callbacks, imported modules, tests, compiler invocations and future tasks inherit or partition fuel?
6. **Diagnostics:** Stable trap, exit status and source-location requirements?
7. **Versioning:** How is the cost schedule versioned so compiler upgrades cannot silently change the meaning of an existing budget?

Until these are decided, do not add an arbitrary default cap or describe release mode, heap limits or recursion limits as CPU bounds.

## 8. Required implementation and assurance sequence

1. Inventory every source construct, generated control-flow edge, runtime helper, library operation and host call; identify unmetered work.
2. Publish a versioned cost table with exact charge points/formulas, including loops, calls, short-circuiting, failure paths and built-ins.
3. Implement a small Capstan-native fuel ledger and executable reference transition model with exact-boundary and one-over vectors.
4. Instrument the source/IR pipeline and verify that every reachable cycle and call transition is charged. Fail closed on unsupported constructs.
5. Implement identical accounting in stage 0 and every supported backend; prove/validate optimisation cannot erase or reorder charges.
6. Test zero fuel, exact exhaustion, one-unit-short, empty/infinite loops, nested loops, all break/continue paths, recursion, repeated calls, short-circuit expressions, large collections, malformed inputs, and exhaustion immediately before every side effect.
7. Differentially compare result, trap, consumed fuel and side effects across reference evaluator, stage 0, native/generated execution and optimisation levels.
8. Prove ledger monotonicity, no underflow/overflow, charge-before-effect, CFG cycle coverage and preservation across in-scope transformations. State host/scheduler assumptions.
9. Advertise only the exact profile, cost-model version, backend and host operations covered by evidence.

## 9. Acceptance criteria for this design increment

- Reviewed, versioned cost semantics.
- Every source construct and runtime/host operation has a charging or exclusion disposition.
- Every reachable loop/back-edge and call transition has a specified charge.
- Fuel is monotonic, non-duplicable and cannot be increased by untrusted program code.
- Exhaustion is deterministic and failure-atomic.
- Configuration and compatibility policy are explicit.
- Deterministic work bounds are distinguished from elapsed-time/cancellation guarantees.
- No assurance claim is promoted merely because an abstract ledger model passes tests.

## 10. Limitations and repository context

A complete fuel model does not establish a wall-clock deadline. A host syscall, page fault, scheduler delay, device operation or blocking read may still take arbitrarily long unless separately constrained. Nor does a fuel bound prove algorithmic usefulness: valid work may exhaust its allowance. WCET for a named processor/OS requires separate platform-specific analysis.

The current CCAM specification defines evaluator maxSteps and maxDepth configuration, but explicitly says its implementation is not yet a conforming v0.1 machine, is not linked to the Lean model by refinement, and is not the complete Capstan semantics. These limits are useful design precedent, not evidence of production source-level metering.

The current threat model records the generated-C plus C-runtime path as production and does not claim formal compiler/runtime correctness. This proposal does not upgrade those claims.

## References

- Issue #428: exact-commit adversarial assurance campaign and CPU/loop availability gap.
- Issue #473: blocking input deadlines and cancellation.
- docs/SPEC.md: source semantics and bounded-input APIs.
- docs/architecture/CCAM.md: abstract-machine step/depth limits and current implementation boundary.
- docs/assurance/THREAT-MODEL.md: current threat model and limitations.
