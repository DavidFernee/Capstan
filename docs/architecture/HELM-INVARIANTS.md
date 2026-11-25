# Helm invariant ledger — initial kernel contract

**Status:** proposed invariant catalogue; all entries OPEN until implementation evidence exists  
**Date:** 2026-11-26  
**Dependencies:** HELM-ADR-001.md and HELM-THREAT-MODEL.md

Every invariant must identify (1) the state predicate, (2) enforcement point, (3) positive test, (4) adversarial negative test, (5) reference-model property, and (6) implementation-refinement obligation. An invariant without all six is incomplete.

| ID | Invariant | Enforcement boundary | Required adversarial evidence | Status |
|---|---|---|---|---|
| HINV-BOOT-01 | No boot-provided address, length or offset is dereferenced before checked range validation | Boot parser | Truncated, overlapping, wrapping, misaligned and out-of-range tags | OPEN |
| HINV-BOOT-02 | Boot parsing has finite byte, record, string and work limits | Boot parser | Exact-boundary and one-over-limit corpus | OPEN |
| HINV-MEM-01 | Every physical frame has exactly one authoritative owner or is explicitly unowned | Physical memory manager | Duplicate ownership, stale owner, double-release and exhaustion | OPEN |
| HINV-MEM-02 | A mapping cannot grant rights exceeding the caller's live frame/address-space capability | Page-table syscall | W^X, privilege escalation, wrong-object and stale-capability attempts | OPEN |
| HINV-MEM-03 | Kernel-private memory is inaccessible from user mode | MMU configuration and page-table validation | Read/write/execute probes from every user address space | OPEN |
| HINV-MEM-04 | A frame is not reused until all mappings, CPUs and permitted device references are quiescent | Mapping teardown/reclamation | Alias, concurrent unmap, TLB shootdown and delayed-reference stress | OPEN |
| HINV-MEM-05 | Mapping updates are failure-atomic | Page-table transition | Inject failure at every allocation and mutation point | OPEN |
| HINV-CAP-01 | Every privileged object operation requires a live capability with sufficient rights | Syscall/object dispatcher | Guessing IDs, wrong object type, stale and insufficient-rights attempts | OPEN |
| HINV-CAP-02 | Capability derivation cannot amplify rights | Capability mint/derive | Exhaustive rights-subset and malformed derivation tests | OPEN |
| HINV-CAP-03 | Revocation has explicit scope, linearisation point and finite worst-case work | Capability revoker | Revoke/transfer/destroy races and maximum-depth derivation trees | OPEN |
| HINV-CAP-04 | Slot/object reuse cannot resurrect stale authority | Capability allocator | Identity wrap and slot-reuse tests | OPEN |
| HINV-IPC-01 | IPC validates complete bounded message structure before protected-state mutation | IPC endpoint | Malformed lengths, offsets, types, aliasing and truncation | OPEN |
| HINV-IPC-02 | IPC capability transfer is all-or-nothing | IPC transfer path | Receiver slot exhaustion and injected failure at each transfer step | OPEN |
| HINV-IPC-03 | Kernel IPC work is bounded by declared message and operation limits | IPC dispatcher | Maximum-size payloads, queue saturation and adversarial sequences | OPEN |
| HINV-SCHED-01 | A thread cannot execute beyond its admitted budget without a specified replenishment/transfer event | Scheduler | Budget exhaustion, donation chains, cancellation and timer wrap | OPEN |
| HINV-SCHED-02 | Priority/budget transfer cannot create unbounded amplification or starvation outside declared policy | Scheduler | Adversarial priority inversion and donation-chain stress | OPEN |
| HINV-IRQ-01 | Interrupt context performs no unbounded allocation, blocking or parsing | IRQ entry/dispatch | Interrupt storm and nested-interrupt fault injection | OPEN |
| HINV-DEV-01 | No device can DMA to memory without explicit device capability and enforced IOMMU mapping | Device/IOMMU layer | Unauthorized DMA mapping and stale IOTLB attempts | OPEN; DMA disabled |
| HINV-RES-01 | Every kernel queue, stack, table and parser has a finite explicit capacity | All kernel subsystems | Capacity boundary, aggregate exhaustion and arithmetic overflow | OPEN |
| HINV-FAIL-01 | Rejected operations preserve pre-operation protected state | Every state transition | Allocation failure and injected failure at each commit point | OPEN |
| HINV-FAIL-02 | Failure diagnostics are bounded and do not disclose protected data | Panic/fault/diagnostic path | Oversized error inputs and secret-bearing state | OPEN |
| HINV-SMP-01 | Reclamation and shared-state transitions are safe under declared memory model | SMP scheduler/MMU | Model checking and stress after SMP begins | DEFERRED |
| HINV-SIDE-01 | No side-channel guarantee is claimed without attacker model and mitigation evidence | CPU/architecture boundary | Timing/speculation/cache side-channel research | OUT OF H0 SCOPE |

## Exit rule

A row may move from OPEN only when all evidence links exist for the exact implementation revision. A proof of an abstract predicate alone does not close the row. A passing test alone does not close a proof obligation. Deferred and out-of-scope rows remain visible in every assurance summary.
