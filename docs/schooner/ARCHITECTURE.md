# Schooner operating system architecture

**Status:** research and architecture proposal; no kernel implementation or security claim
**Date:** 2026-11-26
**Programme:** Capstan platform / Helm
**Implementation constraint:** first-party implementation in Capstan only. Architecture-specific assembly is a separately inventoried, minimal platform boundary. Generated C, C compilers, libc and C runtimes are not permitted dependencies of the eventual Schooner build/run path.

## 1. Mission and scope

Schooner is the operating system programme for the Capstan ecosystem. Helm is its kernel programme; Schooner names the complete operating system, including kernel, boot chain, platform adapters, system services, security policy, developer tools and user-facing environment. This naming preserves the existing Helm programme and its ownership rather than replacing it.

The objective is a general-purpose, secure, reliable, high-performance OS whose guarantees are explicit, compositional and backed by evidence. No claim of being the world's best, vulnerability-free, production-ready, or formally verified is made by this proposal.

## 2. Governing principles

1. **Authority is explicit:** no ambient authority in safe application/service APIs. Every privileged operation consumes a typed, scoped capability.
2. **Isolation is enforced twice:** Capstan's static/effect/ownership rules constrain programs; kernel mechanisms enforce process, address-space and device boundaries.
3. **Resources are compositional:** CPU fuel, stack, heap, memory mappings, IPC queues, handles, storage, I/O, network and device buffers have explicit budgets. Nested components cannot reset or multiply an aggregate budget.
4. **Failure is a specified outcome:** operations define error, trap, cancellation, timeout, partial-progress and rollback behaviour. Admission and reservation are failure-atomic.
5. **Trusted computing base is minimised:** drivers, filesystems, network stacks, graphics and policy-heavy services run outside the kernel when feasible.
6. **Proofs have implementation links:** a theorem about a model is not an implementation proof without a checked refinement/correspondence argument.
7. **Performance is measured against equivalent workloads:** include latency distributions, throughput, tail latency, memory footprint, energy where measurable, and adversarial load.
8. **No unsafe escape by convenience:** all architecture-specific instructions, MMIO, DMA, interrupt entry, boot protocol and firmware interactions are narrow, enumerated and independently reviewed.

## 3. Proposed system decomposition

- **Schooner/Helm kernel:** address spaces, scheduling primitives, interrupt/trap entry, capability object table, bounded IPC, timers and minimum hardware abstractions.
- **Boot and platform layer:** verified/validated image loading, memory map handoff, CPU feature discovery, entropy/clock provenance, interrupt controller and architecture-specific entry/exit.
- **Memory service:** physical-frame allocation policy, virtual-memory mapping policy, reclamation, quotas and accounting. Mechanisms that must be privileged remain kernel-enforced.
- **Process and supervision service:** process construction, executable identity, lifecycle, structured supervision, restart policy and resource assignment.
- **Device services:** isolated drivers, explicit device capabilities, MMIO and DMA mediation, IOMMU policy and device reset/revocation.
- **Storage:** block-device service, Bosun's Locker integration, filesystem services, crash-consistency and recovery.
- **Networking:** isolated network drivers and protocol services, Topsail integration, explicit endpoint and packet budgets.
- **Graphics and interaction:** Shroud native host/presentation integration; Keel may provide graphics/geometry services without becoming kernel code.
- **Media:** Halyard services with bounded parsing, decode, queues and device access.
- **System policy and identity:** capability provisioning, authentication, audit and update policy. No service may mint authority outside its delegated policy.
- **Developer and administration tools:** Anchor and Capstan-native diagnostics, tracing, debugging, image construction and recovery.

Service names express intended boundaries, not current implementation status. Existing product architecture documents remain authoritative for their own APIs.

## 4. Kernel architecture decision: open research question

Do not assume a microkernel is automatically superior. Compare three candidates against the same threat model, hardware target and workloads:

A. **Microkernel:** minimal privileged mechanisms; services and drivers in isolated address spaces; IPC-heavy design.
B. **Modular monolithic kernel:** more services execute in kernel privilege but are separated by strict module and capability contracts.
C. **Hybrid:** microkernel-like isolation for high-risk services with selected performance-critical mechanisms in kernel space.

Score each on:
- privileged code and reachable attack surface;
- fault containment and restartability;
- proof tractability and trusted computing base size;
- authority propagation and confused-deputy resistance;
- IPC/context-switch/cache costs;
- memory footprint and resource-accounting complexity;
- driver ecosystem and hardware support;
- observability, debugging and operational recovery.

**Initial hypothesis:** begin with a microkernel-oriented prototype, but keep the decision reversible until equivalent prototype measurements and proof obligations exist. The kernel should expose mechanisms, not embed policy.

## 5. Security invariants

The following are target invariants; each requires a precise definition, implementation mapping and adversarial evidence before being claimed:

- **S-01 Authority confinement:** an operation succeeds only with a valid capability for the exact object, operation and scope.
- **S-02 No ambient privilege:** untrusted processes cannot discover or acquire authority by naming global objects, environment variables or inherited descriptors.
- **S-03 Object identity:** handles are bound to object identity and generation; stale/recycled identifiers cannot authorise a different object.
- **S-04 Revocation:** revocation has a defined linearisation point and bounds all in-flight use; no stale derived handle remains usable beyond the specified semantics.
- **S-05 Address-space isolation:** user mappings cannot access kernel memory or another process's private mappings; mapping transitions are validated and synchronised.
- **S-06 Memory safety:** safe Capstan code cannot express invalid memory access; kernel/platform unsafe boundaries have explicit contracts and proofs/tests.
- **S-07 DMA isolation:** devices cannot read/write memory outside explicitly mapped, bounded DMA regions; teardown waits for device quiescence and invalidation completion.
- **S-08 Resource confinement:** aggregate quotas are conserved across delegation, IPC, child processes and services; overflow, exhaustion and failed reservation are deterministic and failure-atomic.
- **S-09 Concurrency safety:** safe shared-memory access is race-free under the declared memory model; interrupt and device concurrency use separate explicit protocols.
- **S-10 Availability boundaries:** every parser, queue, retry loop, wait, interrupt path and cleanup operation has a finite resource/work bound or an explicitly documented external liveness assumption.
- **S-11 Information flow:** secrets and privileged data do not cross process/service boundaries without explicit declassification and auditable authority.
- **S-12 Boot/update integrity:** image authenticity, rollback policy, measurement and recovery are specified; hardware/firmware trust assumptions are disclosed.
- **S-13 Failure containment:** a failed user service cannot corrupt kernel state or silently retain authority/resources after its declared teardown boundary.
- **S-14 Evidence integrity:** release claims bind to exact source commit, toolchain, target, configuration, test outputs, proof artifacts and residual TCB.

## 6. Resource contract

Adopt the shared Capstan platform programme's compositional resource model. Every resource-bearing API must declare:
- unit and maximum;
- owner and transfer/delegation rules;
- admission/reservation point;
- commit and rollback behaviour;
- release/reclamation condition;
- overflow and exhaustion result;
- accounting source and observability;
- cancellation and failure semantics.

A child process/service receives a sub-budget carved from its parent's remaining budget, not a fresh independent maximum. Reservations are all-or-nothing unless a streaming API explicitly specifies bounded partial progress. Wall-clock deadlines are distinct from deterministic CCAM fuel.

## 7. Boot and hardware target

Select one emulator/virtual hardware target for H0 only after inventorying available Capstan-native backend and boot support. The first target should have documented boot protocol, serial diagnostics, timer, interrupt controller and virtual memory facilities. Do not claim physical hardware support from emulator success.

Architecture-specific assembly is permitted only as a small, audited boundary with:
- exact instruction and ABI contract;
- preconditions/postconditions;
- register/stack/clobber specification;
- interrupt and privilege assumptions;
- reproducible disassembly and test evidence;
- explicit list of instructions not expressible in safe Capstan.

No hidden C shim, compiler runtime, libc, Python runtime or host shell dependency may be presented as part of a Capstan-only boot/run path.

## 8. Dependency and integration rules

Schooner depends on the C-free Capstan execution path, CCAM semantics/validator, native backend, runtime, ownership/effect/capability model and platform adapters. It must not assume unfinished features. Use the Helm work packages and gates in `docs/architecture/PLATFORM-PROGRAMME.md` as the current programme baseline. Coordinate changes to shared compiler, runtime, concurrency and platform contracts with their owners; do not fork duplicate implementations.

## 9. Release gates

- **S0 Architecture:** threat model, hardware target, TCB inventory, architecture decision record and machine-readable invariants reviewed.
- **S1 Boot:** reproducible emulator boot, bounded diagnostics, deterministic failure and no unsupported hardware claim.
- **S2 Isolation:** kernel/user and process address-space isolation with adversarial tests and implementation-linked proof obligations.
- **S3 Execution:** bounded task lifecycle, scheduling, interrupt handling and process supervision.
- **S4 Authority:** object capabilities, attenuation, transfer, revocation and confused-deputy tests.
- **S5 Services:** isolated storage, network and device services with fault containment and quotas.
- **S6 Production candidate:** update/recovery, hardening, independent security review, exact-platform evidence and residual TCB publication.

Documentation alone cannot pass an implementation gate. A bootable prototype does not establish a secure general-purpose OS.

## 10. Status discipline

Every implementation claim names branch, commit, platform/emulator, build path, tests actually run, CI exact-head status, proof scope and residual assumptions. UNKNOWN is the correct status when evidence is absent or stale. No admitted theorem, hidden axiom, unchecked assembly, untested target, or model-only result may be described as a completed implementation guarantee.
