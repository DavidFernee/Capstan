# Concurrency guarantee calculus and research integration

**Status:** research proposal; no implementation, theorem, or complete vulnerability elimination is claimed  
**General sequential calculus:** [Minimal compositional guarantee calculus](COMPOSITIONAL-GUARANTEE-CALCULUS.md); this document focuses on its concurrency-specific extension and theorem ladder.  
**Target:** v0.7+ concurrency, CCAM and formal-assurance programme  
**Coordinates:** [concurrency core #229](https://github.com/DavidFernee/Capstan/issues/229), [resource analysis #221](https://github.com/DavidFernee/Capstan/issues/221), [capability/effect/information-flow survey #222](https://github.com/DavidFernee/Capstan/issues/222), [compositional guarantee calculus #227](https://github.com/DavidFernee/Capstan/issues/227), [CVE benchmark #237](https://github.com/DavidFernee/Capstan/issues/237), [allocator/GC verification #137](https://github.com/DavidFernee/Capstan/issues/137), [CCAM](../architecture/CCAM.md), [research register](RESEARCH-REGISTER.md)

## 1. Research objective

The concurrency component should not be designed as an isolated collection of thread primitives. It is a demanding application of Capstan's broader research question:

> Can a language compose semantic guarantees, authority restrictions, information-flow policies and resource bounds, and preserve those guarantees across compilation and execution boundaries?

Concurrency is an especially useful test case because memory safety, protocol correctness, liveness, resource exhaustion, information flow and platform assumptions interact. The intended contribution is therefore a **compositional guarantee system** in which a module's concurrency contract can be checked independently and safely composed with its callers and callees.

This document coordinates the concurrency design with the existing research streams. It does not replace the detailed concurrency architecture proposal or the independent literature surveys. Novelty must be established against the strongest related work, not assumed.

## 2. Assurance vocabulary

Every property must be assigned exactly one primary evidence class:

1. **By construction** — the safe typing/ownership rules have no well-formed expression for the prohibited operation.
2. **Statically proved** — a checker or proof assistant discharges a stated theorem under explicit assumptions.
3. **Dynamically enforced** — a runtime check detects a violation before the unsafe state transition commits.
4. **Environment-assumed** — the guarantee depends on a declared scheduler, OS, hardware, device or foreign-code contract.
5. **Not guaranteed** — the property is outside the profile or remains an open obligation.

A test, fuzz result, benchmark or successful build is evidence of that kind only. It is not silently upgraded to a proof. A theorem about a model is not a theorem about the compiler or machine code until a refinement bridge is established.

## 3. A compositional module contract

The proposed research experiment is a module judgment of the following conceptual form:

`Γ; Pi; Lambda; mathcal{R}; mathcal{H} dash M :
  (P Rightarrow Q) ; ! E ; @ A ; # C`

where:

- `Γ` is the typed value, ownership, borrow and task environment;
- `Π` is the set of protocol invariants and state-machine assumptions;
- `Λ` is the information-flow label environment;
- `R` is a resource contract with named units and cost semantics;
- `H` is the explicit set of environmental assumptions;
- `P` and `Q` are preconditions and postconditions, including concurrent-state invariants;
- `E` is the effect set (suspension, blocking, allocation, IO, cancellation, spawn, atomic access, etc.);
- `A` is the required capability/authority set;
- `C` is the evidence/certificate set.

This is a proposal for the smallest useful interface, not committed syntax. Capabilities and effects must remain conceptually distinct: an effect says what an operation may do; a capability says which authority is required to do it. Possessing an effect annotation must not grant authority.

### 3.1 Conservative composition

For sequential composition `M; N`, the postcondition of M must establish the precondition of N, the effect and authority requirements are conservatively combined, and resource costs compose according to declared cost semantics.

For concurrent composition `M || N`, composition additionally requires:

- disjoint ownership, or a shared-state protocol with a proved invariant;
- compatible task and cancellation lifetimes;
- compatible protocol transitions and channel/lock invariants;
- compatible information-flow policies;
- a resource reservation/admission argument for simultaneous execution;
- explicit scheduler and environment assumptions for progress claims.

Unknown callees, opaque callbacks, FFI, device operations and dynamically loaded code cannot reduce required authority, weaken an invariant, lower a resource upper bound or inherit a stronger guarantee by default. Their contract is unknown unless supplied and checked; the safe composition fails closed or introduces a visible dynamic obligation.

### 3.2 Resource contracts

Resource quantities must be dimensioned: steps/fuel, bytes, peak live bytes, stack/continuation bytes, tasks, workers, channel slots, waiters, handles, output bytes and deadlines are not interchangeable.

A resource contract should distinguish:

- static upper bound;
- amortised bound and its potential function;
- runtime-enforced quota;
- measured estimate;
- environment-dependent bound;
- unknown/unbounded.

For concurrent execution, peak memory is not generally the sum of each task's sequential allocation bound. The contract must account for overlap, queue capacity, task lifetime, stack/continuation storage, cancellation cleanup and reserved-but-not-yet-consumed capacity. Admission must reserve the resources needed to make task publication atomic; failure must not leave a partially published task or message.

## 4. Concurrency-specific semantic state

The first formal model should be a deterministic, finite transition system, not a native-thread implementation. Its configuration should explicitly represent:

- heap objects and ownership permissions;
- task identities, task states and a parent/child scope tree;
- borrow regions and their live permissions;
- channel endpoints, bounded buffers, wait queues and message ownership;
- lock identities, ranks, guards and protected invariants;
- atomic locations and a declared memory-order event relation;
- cancellation requests, completion, failure and cleanup;
- capability sets and effect permissions;
- information-flow labels and permitted observations;
- resource counters, reservations and deterministic exhaustion;
- scheduler choices and fairness assumptions.

Each transition has a precondition, a state update and a resource delta. Operations with externally visible effects have a defined linearisation/commit point. A failed operation must leave all state components unchanged except explicitly specified failure telemetry and consumed fuel.

The reference machine is an executable semantic oracle and a counterexample generator. It is not the normative implementation merely because it is executable. The eventual Capstan-native implementation and each backend must refine this transition system.

## 5. Vulnerability-class disposition

This is a working coverage register. “Target” means the design obligation, not an implemented guarantee.

| Class | Safe-profile mechanism / research obligation | Assurance target | Residual boundary |
|---|---|---|---|
| Data races | Exclusive ownership, immutable sharing, typed synchronisation | Construction + race-freedom proof | Foreign code, DMA and unsound backend |
| Use-after-free / double free | Lifetimes, affine/linear resources, verified reclamation | Construction + preservation | Unsafe FFI and allocator refinement |
| Lock misuse / static ABBA | Linear guards, ranks, ordered multi-lock acquisition | Construction for ranked subset | Dynamic protocols and non-lock waits |
| Task leaks / callback-after-owner-drop | Structured scopes, owner-bound callbacks, linear handles | Construction + lifecycle proof | Explicit supervisor/service profiles |
| Channel duplication/loss | Linear send ownership, explicit close and linearisation | Transition invariant + proof | Distributed transport failure |
| Channel deadlock | Typestate protocols, bounded model checking, wait-for graph contracts | Proved per finite protocol/bounds | Arbitrary unbounded protocol |
| Starvation / unfair wakeups | Scheduler contracts, queue discipline, fairness properties | Profile-specific liveness proof | Host scheduler and adversarial workload |
| Livelock / retry storms | Bounded retries, backoff contracts, ranking functions | Per-algorithm progress proof | Environment-dependent contention |
| Priority inversion | Priority-aware lock protocol, ceilings/inheritance where supported | Adapter contract + bounded analysis | OS scheduling policy |
| TOCTOU | Capabilities bound to object identity/version; atomic check-use operation | API construction + protocol proof | External mutable resources without atomic host support |
| ABA / unsafe reclamation | Versioned identities, generation counters, epoch/RCU protocols | Algorithm proof + memory-model proof | Counter wrap and external observers |
| Reentrancy / callback hazards | Callback effect restrictions, reentrancy types, no unknown callback under guard | Construction for declared effects | Foreign callback contract |
| Weak-memory errors | Small formal memory model, SC baseline, litmus tests, backend refinement | Model theorem + per-target refinement | Processor errata / hardware faults |
| Atomic algorithm logic errors | Verified libraries and contracts; atomics alone confer no algorithmic guarantee | Per-algorithm proof | User algorithms outside verified library |
| Resource exhaustion | Compositional budgets, atomic reservations, bounded queues and stacks | Static bound or dynamic enforcement | OS/global resource failure |
| Cancellation/shutdown races | Explicit state machine, idempotent request, structured join and cleanup | Transition proof + fault injection | Unresponsive foreign operation |
| Information leaks / secret races | Information-flow labels, non-interference contracts, secret-safe synchronisation | Scoped non-interference proof | Timing/cache/physical channels unless separately covered |
| Side channels | Constant-time effects/types, trace semantics and target-specific audit | Restricted-profile proof + target validation | Microarchitecture, power, EM and physical access |
| Distributed races / split brain | Versioned protocols, consensus/transaction contracts, fencing tokens | Protocol-specific proof | Network partitions and external consensus assumptions |
| Signal/interrupt/device races | Separate execution contexts and typed MMIO/DMA ownership | Platform-specific model/refinement | Device firmware and undocumented hardware |
| Scheduler/shutdown races | Explicit scheduler state machine and shutdown protocol | Model proof + adapter conformance | Kernel defects and process termination |
| Logical races / stale decisions | Invariants, transactions, version checks and protocol state machines | Application-specific specification | No general automatic elimination |
| Deadlock in arbitrary programs | Do not claim general decidability; restrict profiles and prove bounded instances | Explicitly scoped proof | General unrestricted deadlock remains undecidable |

The register must be versioned and expanded when the threat model, CWE taxonomy, CVE corpus or research review identifies a missing class. “All known” is a moving target; coverage requires a dated taxonomy snapshot, search protocol, independent review and negative/out-of-scope cases.

## 6. Theorem ladder

The proof programme should proceed in dependency order.

### T0 — Transition integrity

Every machine transition preserves structural well-formedness, bounds and resource-accounting consistency. Failure transitions are atomic and deterministic.

### T1 — Ownership preservation

Well-typed transitions preserve unique ownership, valid borrows and linear-resource conservation. No object is simultaneously mutably owned by independent tasks.

### T2 — Race freedom

For every reachable well-typed state, conflicting non-atomic accesses to the same location are ordered by exclusive ownership or a valid synchronisation protocol.

### T3 — Structured lifecycle

Every child task is owned by exactly one live scope; scope completion implies all descendants have terminated and all scope-bound resources have been discharged or explicitly transferred.

### T4 — Channel conservation

Each message is in exactly one state: sender-owned before commit, channel-owned after successful enqueue, receiver-owned after dequeue, or explicitly destroyed by a specified close/failure transition. No transition duplicates or silently loses ownership.

### T5 — Lock invariants

Guard acquisition grants the declared permission; every exit path restores the invariant and releases the guard. Ranked lock acquisition cannot form a cycle in the statically ranked subset.

### T6 — Resource soundness

The static or dynamic accounting relation upper-bounds the resources consumed by every modeled execution. Reservation and failure atomicity are proved, not inferred from post-hoc counters.

### T7 — Memory-model refinement

The abstract atomic event relation is preserved by every declared backend and target. A sequentially consistent baseline is the first target; weaker orders require separate proofs and litmus coverage.

### T8 — Information-flow and authority

Untrusted inputs cannot manufacture capabilities; authority cannot increase through composition; and low-observable traces do not reveal high-labelled data under the stated scheduler, timing and host assumptions.

### T9 — Qualified liveness

Progress theorems state exact fairness, boundedness and environment-response assumptions. Prove only restricted classes (e.g. acyclic ranked locks, finite channel protocols, ranking-function algorithms). No theorem is to be phrased as universal deadlock or starvation freedom.

### T10 — Refinement chain

Connect the model to Capstan source checking, CCAM lowering/evaluation, native backend, runtime and platform adapter. Each link has an explicit simulation/refinement statement and a conformance suite. A proof of T0–T9 about an isolated model is not an end-to-end language guarantee.

## 7. Research-stream integration

Concurrency is the integration experiment for several active Capstan research themes:

| Research stream | Contribution to concurrency | Required collaboration |
|---|---|---|
| CCAM typed finite-machine semantics (R1) | Small-step transition substrate, typed states, bounded execution and model-to-implementation refinement | Extend CCAM only after a minimal independent concurrency model is stable |
| Resource analysis (#221) | Compositional peak-resource bounds, task/channel/stack budgets, admission control | Compare amortised, potential, sized-type, effect and runtime quota approaches |
| Capabilities/effects/information flow (#222) | Separate authority from effects; mediate spawn, IO, clocks, entropy, shared resources and secret observations | Preserve distinct capability/effect judgments; prove non-amplification and scoped non-interference |
| Guarantee calculus (#227) | Compose pre/postconditions, effects, authority, resources, assumptions and evidence | Use the same contract form for sequential and concurrent modules |
| C-free execution (#80) | Define scheduler/atomic/allocator boundary without relying on C ABI semantics | Adapter contracts and backend refinement |
| Allocator/GC verification (#137) | Safe reclamation, root/lifetime interaction, allocation under concurrency, secret erasure limits | Do not permit concurrent GC claims until collector/safepoint/root protocol is specified |
| CVE benchmark (#237) | Validate whether claimed classes map to faithful historical bug patterns | Include concurrency CVEs and negative controls; no CWE-label-only equivalence |
| Compiler correctness / self-hosting | Ensure checks survive lowering and bootstrap stages | Differential tests, translation validation and eventually verified compiler passes |

The strongest possible research contribution is not simply “Capstan has safer threads”. It is a testable claim that one compositional contract can carry safety, authority, information-flow and resource guarantees across concurrent module boundaries and a defined execution refinement chain. This is a hypothesis to test against prior art, not a novelty assertion.

## 8. Falsifiable research hypotheses

- **H1 (compositionality):** For the restricted task/channel profile, if component contracts satisfy the stated ownership, protocol, authority and resource side conditions, composition preserves the combined safety invariant without inspecting component internals.
- **H2 (fail-closed uncertainty):** An unknown callback/callee/FFI contract cannot be composed while preserving a stronger guarantee than the known contract supports.
- **H3 (resource predictability):** For finite structured task trees and bounded channels, the calculus can derive a sound peak-memory/task bound tighter than the naive sum of independent worst-case component bounds for at least one nontrivial benchmark family, without under-approximation.
- **H4 (refinement):** A small Capstan-native deterministic concurrency machine can be shown to refine a formal transition model for the implemented subset.
- **H5 (security relevance):** A reproducible benchmark protocol can distinguish vulnerability classes prevented by construction from those merely detected, mitigated or outside the guarantee.

Each hypothesis requires a baseline, counterexample search, explicit failure criterion and independent replication. If H1 or H3 fails, narrow the calculus rather than weakening soundness.

## 9. First bounded experiment

Do not begin with native threads, lock-free structures, RCU, device memory or a general async runtime.

Implement and model-check this finite subset:

1. Move-only task transfer and immutable shared values.
2. Lexically structured task scopes with linear join handles.
3. Bounded FIFO channels with explicit capacity and linearisation point.
4. Cooperative cancellation with a finite cleanup protocol.
5. Deterministic scheduler choices and bounded task/step/message budgets.
6. A tiny protocol-state annotation sufficient to describe a producer/consumer handshake.
7. A capability requirement for task creation and channel use.
8. A resource contract for task count, queue capacity and peak buffered payload bytes.

The reference state space should be finite under explicit bounds. Explore every scheduler interleaving for small task/message limits, emit shortest counterexample traces, and retain each discovered defect as a regression case. Add lock ranks and SC atomics only after the first ownership/channel invariants hold.

### Acceptance gates

- A machine-readable transition schema and executable reference model exist.
- The invariants T0–T4 are stated mathematically and checked over exhaustive bounded state spaces.
- At least one deliberately malformed program is rejected for each ownership, lifecycle and channel rule.
- At least one positive producer/consumer program is accepted and all its bounded interleavings satisfy the invariants.
- At least one counterexample demonstrates that data-race freedom alone does not imply protocol correctness or liveness.
- Resource exhaustion and cancellation are tested at every commit boundary.
- The model's assumptions and all unproved claims are listed in a claim/evidence ledger.
- No implementation or publication claim exceeds the evidence obtained.

## 10. Open questions that require literature review

1. Which existing separation-logic, session-type, effect, capability and resource-aware systems provide the closest compositional contract? Which combination is genuinely new, if any?
2. Should the first protocol layer use session types, typestate, temporal contracts, or a deliberately smaller automaton interface?
3. Which liveness properties are tractable and useful enough for static proof, and which should be bounded model-checking obligations?
4. How should fairness be represented without making unsound assumptions about an OS scheduler?
5. Can peak-resource contracts compose tightly in the presence of cancellation, nested scopes and adversarial scheduling?
6. Which information-flow model can state useful non-interference properties without pretending to eliminate microarchitectural channels?
7. What is the smallest formal memory model that supports a credible path to ARM64 and x86-64 backend refinement?
8. Which compiler passes must be verified, translation-validated or independently checked to preserve the concurrency guarantees?

## 11. Claim discipline

Until the corresponding implementation, proof and refinement evidence exist, Capstan must not claim that it currently prevents any concurrency vulnerability class. This proposal establishes research obligations and an implementation order only.

A final assurance statement must name:
- language profile and exact compiler/runtime revision;
- supported targets and scheduler contract;
- classes prevented by construction;
- theorems proved and their assumptions;
- dynamically enforced checks and failure semantics;
- unsafe/foreign/device/distributed boundaries;
- residual classes, counterexamples and known limitations;
- reproducible test, model-check and proof commands.

The objective is not to hide residual risk. It is to make the safe subset progressively stronger, the trusted base progressively smaller, and every guarantee independently auditable.
