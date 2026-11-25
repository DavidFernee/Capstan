# Schooner research agenda

**Status:** proposed research programme; hypotheses, not results
**Date:** 2026-11-26
**Parent architecture:** [Schooner architecture](ARCHITECTURE.md)

## Research R1 — Compositional capability revocation

**Question:** Can a capability system support efficient attenuation, delegation and revocation with a precise linearisation point, bounded metadata growth and no stale-authority window?

**Hypothesis:** A generation-tagged object identity plus an explicit derivation graph or bounded revocation domain can provide revocation semantics that compose across IPC and process boundaries without global scans on every operation.

**Work:**
1. Define object identity, capability rights lattice, derivation and attenuation.
2. Define concurrent revoke/use ordering and in-flight operation semantics.
3. Build a small executable Capstan reference model with bounded object/edge counts.
4. State invariants: no rights amplification; no use after revocation point; stale generations never alias; bounded traversal/work.
5. Explore per-domain epochs, revocation trees and indirection-table designs; compare worst-case work and memory.
6. Prove model invariants and refine the selected kernel object/IPC implementation.

**Falsifiers:** stale authority can be exercised after the specified revocation point; delegated rights increase; revocation work is unbounded under an admitted bound; generation wrap permits identity reuse.

## Research R2 — Compositional resource accounting across IPC

**Question:** How can CPU fuel, memory, queue capacity and device buffers remain conserved when resources cross asynchronous service boundaries?

**Hypothesis:** Linear budget tokens with failure-atomic split/join operations can prevent budget duplication and accounting drift, while separating deterministic work units from wall-clock deadlines.

**Work:**
1. Define resource vectors and units; distinguish capacity, occupancy, cumulative work and rate.
2. Specify split, transfer, reserve, commit, rollback and reclaim.
3. Model parent/child/service budget conservation and cancellation races.
4. Test overflow, repeated delegation, partial I/O, queue backpressure and failed cleanup.
5. Prove conservation and failure atomicity for the bounded model; implement in Capstan and compare counters to the model.

**Falsifiers:** a valid transition creates capacity; failed admission mutates state; local counters reset on delegation; aggregate usage exceeds the root budget without an explicitly modelled external source.

## Research R3 — Bounded IPC with authority and backpressure

**Question:** Can message transfer, capability transfer, cancellation and queue backpressure be made atomic and bounded without deadlocking the kernel or allowing sender/receiver confusion?

**Hypothesis:** Explicit endpoint state machines and reservation-before-publication can yield bounded queue operations and clear linearisation points.

**Work:**
1. Define endpoint ownership, close, peer death, cancellation and delivery states.
2. Specify message size/count quotas and capability-slot quotas.
3. Model send/receive/close/cancel interleavings.
4. Define whether delivery consumes sender authority and when receiver authority becomes usable.
5. Add model-based and adversarial tests, then machine-checked transition invariants.

**Falsifiers:** duplicate delivery, lost ownership, capability amplification, unbounded queue growth, non-atomic partial publication, or a deadlock in the declared bounded protocol.

## Research R4 — Verified memory reclamation for process and device teardown

**Question:** How can the kernel establish that no CPU, interrupt handler, service or DMA device can access a memory region before it is reclaimed?

**Hypothesis:** A staged revoke-quiesce-invalidate-reclaim protocol with explicit acknowledgements and device fences can make reclamation conditions compositional.

**Work:**
1. Define actors and references: page tables, TLBs, CPUs, interrupt handlers, IPC pins and DMA engines.
2. Specify teardown phases and permitted transitions.
3. Model delayed acknowledgements, CPU offline, device reset failure and cancellation.
4. Prove no access after reclaim and no double reclaim under stated hardware contracts.
5. Implement fault injection and emulator tests before enabling DMA.

**Falsifiers:** any execution permits access after reclaim; failed invalidation is treated as success; teardown can reclaim while an actor retains a reference.

## Research R5 — Small-kernel proof-to-code refinement

**Question:** What is the smallest useful kernel core for which the CCAM model, Capstan implementation and architecture-specific boundary can be connected by credible proof obligations?

**Hypothesis:** Start with a uniprocessor transition system for capability lookup, bounded IPC and task state; keep hardware-dependent operations behind a narrow adapter whose contract can be separately validated.

**Work:**
1. Choose a tiny kernel state and transition relation.
2. Specify invariants and observable outcomes.
3. Build the Capstan reference implementation and deterministic transition tests.
4. Define a refinement map from implementation state to model state.
5. Prove transition simulation for the supported subset; disclose any trusted primitives.
6. Expand only when each new mechanism has an evidence path.

**Falsifiers:** implementation transition cannot be mapped to the model; proof relies on untracked assumptions; hidden runtime or C support is required for the claimed C-free path.

## Research R6 — Architecture trade-off under equal evidence

**Question:** Under the same workloads and threat model, which microkernel, modular-monolithic or hybrid design gives the best combined assurance, latency, throughput and resource footprint?

**Method:** implement comparable bounded prototypes for IPC, scheduling, driver fault recovery and memory isolation. Report source/privileged LOC, TCB, proof obligations, p50/p95/p99 latency, throughput, context switches, memory use, restart time and adversarial behaviour. Publish workloads and harnesses. Do not select by microbenchmark alone.

## Shared experimental protocol

- Freeze a versioned specification before implementation.
- Build a bounded reference model in Capstan where practical.
- Include positive, negative, boundary, stateful/property-based and adversarial tests.
- Use fault injection for allocation, IPC, mapping, interrupt, device and teardown failures.
- Compare implementation traces against model traces.
- Machine-check safety invariants and clearly state liveness assumptions.
- Record exact toolchain, commit, platform, configuration, seeds and reproducible commands.
- Separate model evidence, implementation tests, refinement proofs and independent review.
- Treat any counterexample as a design result; do not weaken the invariant merely to make tests pass.

## Initial priority

R1 and R2 should precede substantial kernel implementation because authority and resource semantics shape every kernel/service API. R3 follows directly. R4 is a prerequisite for robust memory mapping and DMA. R5 provides the proof/evidence spine. R6 informs the architecture decision rather than assuming a winner.
