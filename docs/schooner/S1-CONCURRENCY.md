# Schooner S1 concurrency contract (bounded model)

## Purpose

This note defines a candidate concurrency contract for capability-backed access and object revocation. It is an abstract reference semantics only. It does not claim that the current Capstan runtime or any kernel implementation enforces the contract.

## Operation phases and linearization

An access operation has three externally meaningful phases:

1. **Invocation** — the caller requests an operation using a previously issued capability.
2. **Admission / pin** — one indivisible operation checks the revocation gate and registers an in-flight reference. This is the proposed access linearization point.
3. **Completion** — the operation releases its in-flight reference and returns its result.

Revocation has three phases:

1. **Invocation** — revocation is requested by an authorised principal.
2. **Commit** — one indivisible transition closes the admission gate, advances the object epoch, and marks the object revoked. This is the revocation linearization point.
3. **Quiescence / return** — the revoker waits until all operations admitted before commit have dropped their in-flight references. Only then may it return and permit reclamation.

The critical ordering rule is not “no operation may return after revocation”. An operation admitted before the revocation commit may legitimately finish afterwards. Linearizability orders that overlapping access before revocation. The required safety property is that no access can be admitted after the gate closes, and that revocation cannot report quiescence or reclaim the object while a pre-commit access remains in flight.

## Atomicity obligation

The gate check and in-flight registration must be atomic with respect to revocation commit. If implemented as separate unsynchronised loads/stores, a use-after-revoke race is possible:

- Access reads `gate_open = true`.
- Revoker closes the gate, observes `in_flight = 0`, and reclaims.
- Access increments `in_flight` and dereferences the reclaimed object.

The abstract model therefore treats admission as one atomic transition. A real implementation must refine this with a proven primitive (for example, a lock-protected admission counter or a correctly designed atomic state word with acquire/release ordering). Merely using an atomic counter is insufficient unless the gate/counter protocol prevents the check-then-increment race.

## Required invariants

- `gate_open == !revoked`.
- A pinned access corresponds to exactly one in-flight reference.
- At most one access exists in this finite model; a production counter must be bounded and overflow-safe.
- Revocation commit closes the gate and advances the epoch in one linearization step.
- Revocation return and reclamation require `in_flight == 0`.
- An access whose admission follows revocation commit is rejected.
- Rejected or disabled transitions leave the state unchanged.
- State-space exhaustion is reported as unknown, never as proof of safety.

## Model scope and limitations

`verification/schooner_concurrency.cap` explores all reachable interleavings of one access and one revocation operation over a finite action alphabet. It covers the critical overlap where access is pinned before revocation commit and completes after it, as well as access attempts after revocation. The model is deliberately single-access and uses a small epoch domain; it does not model multiple simultaneous readers, counter saturation, memory reclamation algorithms, scheduler fairness, cancellation, nested capabilities, DMA/device access, interrupt contexts, weak-memory executions, or compiler/CPU refinement.

The single in-flight slot makes the core ordering obligation inspectable, but it is not a substitute for a multi-reader model. The next refinement should introduce at least two independent accessors, bounded in-flight counts, admission-counter exhaustion, and a model of the chosen implementation primitive. Weak-memory correctness requires a separate memory-model argument or litmus/model-checking evidence.

No kernel guarantee, formal proof, production readiness, or vulnerability-free claim is made by this document.
