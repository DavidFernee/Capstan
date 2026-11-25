# Helm architecture decision record 001 — capability-oriented microkernel

**Status:** architecture selected; implementation gates open  
**Date:** 2026-11-26  
**Scope:** kernel decomposition, trust boundaries, first platform and delivery gates

## 1. Decision

Helm will be developed as a **capability-oriented microkernel**. Kernel mode contains only mechanisms that require privilege or must be indivisible to enforce isolation. Device drivers, filesystems, network stacks, policy services and ordinary system services execute as isolated Capstan processes.

This is an architectural decision, not a claim that Helm exists, boots, is secure or is formally verified. The decision remains subject to the measurable acceptance gates in this record. If the implementation cannot meet its security, latency, throughput, tail-latency or resource targets, the design must be revised on evidence.

First-party kernel and service code is Capstan. Architecture-specific assembly is restricted to small, reviewed entry/exit and hardware-transition stubs. Generated C, a C compiler, libc or a C runtime must not be hidden dependencies of the claimed kernel image or execution path.

## 2. Rationale and research baseline

The primary design objective is to minimise the privileged trusted computing base (TCB), not merely the number of source files. The kernel is the ultimate authority over address-space isolation, scheduling, capabilities and hardware access. Moving policy-heavy code and complex parsers out of privilege mode reduces the consequences of defects in those components and gives them independent restart, resource and capability boundaries.

The choice is informed by:

- **seL4:** demonstrates that a small capability-based microkernel can combine high performance with machine-checked implementation and security proofs. Its proof scope is configuration-specific; Helm must establish its own implementation correspondence.
- **Genode:** demonstrates recursively composed systems in which components run in sandboxes and receive explicit rights and resources. The microkernel is only one layer of the overall architecture.
- **L4 lineage:** demonstrates that IPC and context-switch overhead need not make a microkernel impractical. Helm must measure its own end-to-end service costs rather than borrow another kernel's benchmark claims.

The microkernel best aligns with Helm's primary objectives: isolation, least authority, a small proof target, fault containment and independently testable services. It is not selected on the false premise that a microkernel is automatically secure or faster.

## 3. Alternatives considered

| Architecture | Advantages | Disadvantages for Helm | Decision |
|---|---|---|---|
| Monolithic kernel | Direct calls, shared internal data structures, potentially lower transition overhead; mature driver ecosystem | Large privileged TCB; subsystem and driver faults can corrupt shared kernel state; difficult isolation and restart | Rejected |
| Modular monolithic | Clear internal modules; less IPC than a microkernel | Modules still execute with kernel privilege and commonly share the kernel address space; module boundaries do not enforce isolation | Rejected |
| Hybrid kernel | Can move selected services out of privilege while retaining performance-sensitive subsystems in kernel mode | Risk of an expanding privileged middle ground; inconsistent isolation model; boundary can become difficult to audit | Rejected as default |
| Capability-oriented microkernel | Small privileged mechanism set; user-space services; explicit authority; fault containment; tractable formal model | IPC, scheduling and address-space transitions require careful performance engineering; user-space service architecture adds complexity | **Selected** |

A privileged mechanism may be added only when it cannot be implemented safely and efficiently outside the kernel. Each addition requires a written rationale, threat-model update, invariant impact analysis, proof/test obligations and TCB delta.

## 4. Kernel responsibility boundary

The initial kernel mechanism set is:

1. Boot handoff and immutable boot-information validation.
2. Physical-memory ownership and page-frame assignment/retyping.
3. Address-space and page-table operations with architecture-specific validation.
4. Thread creation, lifecycle, context switching and bounded scheduling.
5. Capability-space operations and kernel-object access checks.
6. Synchronous IPC endpoints and bounded notification primitives.
7. Interrupt routing/acknowledgement and timer mechanisms.
8. Minimal fault delivery, diagnostics and shutdown/restart primitives.

The kernel does not implement policy-rich filesystems, network protocols, device-specific drivers, user authentication, package management, GUI, database services or general-purpose application allocation.

The steady-state kernel should have no general-purpose heap. Kernel objects are backed by explicitly owned, bounded memory resources. Any unavoidable boot-time allocator must be bounded, monotonic, separately specified, and retired or frozen before untrusted processes start. Kernel stacks, queues, IPC buffers and per-thread metadata have explicit maxima.

### 4.1 Initial process architecture

The first useful system is a small static service graph:

- **Root task/system manager:** receives the initial resource inventory and constructs the first capability graph.
- **Memory service:** manages user-level physical memory allocation and address-space construction through explicit kernel capabilities.
- **Timer/interrupt service:** owns permitted interrupt capabilities and routes notifications.
- **Console service:** owns the emulator's initial serial device.
- **Test task:** exercises address-space, capability and IPC boundaries.

The root task is part of the initial system TCB until its authority is safely subdivided. The kernel must not silently retain ambient access to every device or physical page after boot handoff.

## 5. Security architecture

### 5.1 Capability model

All privileged operations require an explicit, unforgeable object capability. A capability identifies a kernel object and carries a bounded rights set. Possession is authority; object names, process IDs and numeric handles alone are not authority.

Before implementation, the capability contract must specify slot/object identity and stale-reference resistance; rights attenuation and non-amplifying derivation; copy, mint, transfer and deletion semantics; revocation scope and worst-case work; object lifetime; IPC transfer; failure atomicity; and boot-time root authority reduction.

No raw kernel pointer, physical address, device register address or object index supplied by user space is sufficient authority. User-controlled indices are validated before use. Capabilities are not serialized as reusable bearer tokens outside protected capability spaces.

### 5.2 Address-space isolation

Each process receives a distinct address space. User mappings cannot map kernel-private memory or writable-executable memory unless a separately justified policy permits it. Page-table updates validate ownership, alignment, permissions, canonical address ranges and architecture-specific reserved bits before mutation.

Mapping changes are failure-atomic: either the complete transition commits or the old state remains. Page reclamation requires proof that no CPU, address space, device or in-flight IPC operation can still access the frame. TLB invalidation and shootdown completion are part of the mapping lifecycle.

### 5.3 IPC

IPC is both a security boundary and a performance-critical path. The initial contract uses typed, bounded messages, explicit sender/receiver authority, defined cancellation and timeout semantics, and explicit capability transfer. No kernel allocation is proportional to an untrusted message length.

A later fast path may use registered shared-memory windows or ownership transfer, but only after the copying path is correct and the same access-control and lifetime invariants are preserved. Shared memory does not imply shared authority.

### 5.4 Scheduling

Scheduling must be bounded and auditable. The first design uses explicit priorities and budgeted execution contexts, with defined replenishment, donation, blocking and cancellation semantics. Priority inheritance/donation must have a finite specified chain and must not permit unbounded authority or execution-time amplification.

The uniprocessor scheduler is the initial correctness target. SMP is a separate milestone after interrupt, memory-reclamation and scheduler invariants are established on one CPU.

## 6. Initial platform and boot strategy

**First target:** x86-64 under QEMU with an explicitly versioned virtual machine configuration. This is a development target, not a hardware-support claim.

**Initial boot protocol:** Limine x86-64, with a pinned bootloader release and a pinned protocol base revision (minimum base revision 5 for the initial x86-64 target). Limine provides a native 64-bit entry contract and an ELF-oriented image path, avoiding a 32-bit protected-mode-to-long-mode trampoline in the first kernel slice. Firmware and bootloader remain explicit trusted inputs. The kernel must install its own IDT immediately, establish its own GDT and page tables before reclaiming bootloader memory, and treat every response pointer, count, range and memory-map entry as untrusted input. The bootloader's higher-half direct-map mappings are not the kernel's final protection policy; Helm must replace them with explicit permissions and ownership tracking. The protocol's HHDM offset is discovered, never hard-coded. Multiboot2 remains a possible alternative if later compatibility requirements justify its additional entry-transition work.

The existing Capstan native backend emits a freestanding Linux process using the System V AMD64 process ABI and Linux syscalls. It is not a bare-metal kernel backend. Its process entry point and syscall conventions must not be reused as if they were valid at kernel privilege.

The kernel target must define the ELF image layout and linker script; Limine request/base-revision contract; higher-half image and entry contract; stack handoff; GDT, IDT, exception and interrupt entry/exit; Capstan kernel calling convention; privileged instruction boundary; serial output; and reproducible image build. The Limine x86-64 entry ABI is System V AMD64 without FP/SIMD; the first kernel subset must not emit floating-point or SIMD instructions.

The minimum assembly surface is limited to boot entry, privilege/interrupt entry and return, context switch, and narrowly defined register/CPU operations. Each stub has a typed Capstan-facing contract and a testable register, stack and flags-preservation specification.

ARM64 is the next architecture design target. Shared kernel contracts must not bake x86 page-table formats, interrupt models or calling conventions into architecture-independent code.

## 7. Performance design and acceptance

Helm will not optimise by intuition or quote third-party benchmarks as its own. Every benchmark records CPU model, QEMU version/configuration, compiler revision, build flags, workload, warm-up, repetitions, raw samples, variance and measurement method.

The benchmark suite must include null syscall/trap round trip; same-address-space call baseline; cross-address-space IPC ping-pong; payload-size sweep; capability lookup/derivation; address-space switch and TLB invalidation; thread wakeup/context switch; scheduler dispatch and tail latency under load; interrupt-to-service latency; service restart/fault recovery; and later filesystem/network throughput and p50/p95/p99 latency.

Optimisations are accepted only if the invariant suite still passes and tail latency/starvation do not materially worsen. Fast paths require a simple reference path and differential tests. Batching, direct handoff, per-core queues and shared-memory transport are candidates, not assumptions.

## 8. Formal assurance strategy

1. Write a small executable reference model for each kernel transition.
2. State preconditions, postconditions, frame conditions and resource bounds.
3. Prove the abstract transition preserves named invariants.
4. Implement the corresponding Capstan transition with explicit state and bounded inputs.
5. Differentially test implementation traces against the model.
6. Establish a refinement relation from concrete state to model state.
7. Prove the implementation transition simulates the model, including failure paths.
8. For generated machine code, verify code generation/ABI boundaries or retain them explicitly in the TCB.

A proof of a page-table model is not a proof of the Capstan page-table implementation, assembly entry code, compiler or CPU. Every result identifies exact commit, tool versions, theorem scope, axioms/imports, assumptions, unproved obligations and code boundary. No admitted theorem or hidden axiom may be reported as completed verification.

## 9. H0–H6 delivery gates

| Gate | Deliverable | Required evidence |
|---|---|---|
| H0-A Architecture | ADR, threat model, invariant ledger and dependency map | Reviewed decision, explicit assumptions and TCB inventory |
| H0-B Toolchain feasibility | Bare-metal x86-64 target feasibility report | Exact compiler/backend gaps; assembly ABI; linker/image format; reproducible tool inventory |
| H0-C Boot | Minimal image enters kernel and emits bounded serial diagnostics in QEMU | Exact QEMU config, bootloader version, image hash, automated success/failure tests |
| H1 Isolation | Kernel/user privilege boundary and independent address spaces | Adversarial negative tests; page ownership/mapping model; no user-to-kernel write/execute path |
| H2 Processes | Threads, capability checks and IPC | Lifecycle, authority, malformed-message, cancellation, exhaustion and fault-injection tests |
| H3 Storage | User-space block/filesystem services | Crash consistency/recovery tests; kernel does not parse filesystem metadata |
| H4 Network | User-space network stack and isolated NIC driver | Protocol conformance, parser fuzzing, DMA/IOMMU and exhaustion evidence |
| H5 SMP | Multicore operation | Memory-ordering, race, shootdown, scheduler and scalability evidence |
| H6 Release | Production candidate | External review, exact-platform evidence, proof/refinement report and residual TCB |

No gate passes on documentation alone. H0-C is not H1. A bootable image is not a secure general-purpose operating system.

## 10. Immediate implementation dependencies

Bare-metal work must not assume capabilities the compiler does not yet provide. H0-B must inventory and close, in order:

1. Capstan freestanding target profile and explicit no-runtime mode.
2. Kernel code generation for the selected scalar/record subset, without process ABI assumptions.
3. Linker script and Limine-compatible higher-half ELF image construction.
4. Minimal entry assembly and register/stack contract.
5. Explicit privileged-instruction interface.
6. Deterministic serial output and panic/fault path.
7. QEMU boot harness with timeouts, output bounds and image-hash capture.
8. Negative boot tests for malformed boot information, missing memory regions and invalid CPU features.

The first kernel slice is deliberately staged: (a) enter x86-64 kernel code, switch to a kernel-owned bounded stack, invoke a Capstan-generated scalar entry routine and halt through a test-only QEMU exit device; (b) install a minimal exception IDT and validate bounded Limine handoff data through a separately specified Capstan memory-view interface; (c) initialise serial diagnostics. It must not enable interrupts, start user tasks, enable DMA or claim memory isolation until those properties have their own specifications and tests.

## 11. Non-goals for the first kernel

Linux/POSIX compatibility; general desktop support; SMP before uniprocessor invariants; USB, Wi-Fi, GPU or broad device support; dynamic kernel modules; arbitrary third-party kernel extensions; a general-purpose kernel heap; speculative-execution security claims; DMA before IOMMU and device-ownership contracts; or a claim that all known/unknown vulnerabilities are impossible.

## 12. Research references

- seL4 project documentation and verified configuration matrix: https://docs.sel4.systems/projects/sel4/
- seL4 FAQ, capability semantics, minimal kernel boundary and resource management: https://docs.sel4.systems/projects/sel4/frequently-asked-questions
- seL4 fact sheet and proof/performance overview: https://sel4.systems/About/fact-sheet.html
- Genode Foundations, recursive sandbox and resource/authority architecture: https://genode.org/documentation/genode-foundations/24.05/introduction/Operating-system_framework.html
- Gernot Heiser, The seL4 Microkernel – An Introduction, seL4 Foundation white paper, revision 1.4.1 (2026-07-17): https://sel4.net/About/seL4-whitepaper.pdf

These references inform design; they do not substitute for reproducing benchmarks, auditing assumptions or proving Helm's implementation.

## 13. Decision review triggers

Reopen this decision if measured IPC/context-switch costs fail declared workload budgets after optimisation; required hardware functionality cannot be safely isolated in user space; the privileged TCB grows beyond the reviewed mechanism set; capability revocation or resource accounting cannot be bounded; formal refinement becomes intractable; or a materially better architecture is demonstrated by reproducible evidence.

**Decision summary:** microkernel selected; x86-64 QEMU boot slice proposed; bare-metal compiler/backend support is an explicit prerequisite; all security and performance claims remain unproven until their gates pass.
