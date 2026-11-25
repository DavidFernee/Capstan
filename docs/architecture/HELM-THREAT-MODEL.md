# Helm threat model — H0 baseline

**Status:** initial threat model; implementation and platform assumptions remain open  
**Date:** 2026-11-26  
**Applies to:** Helm kernel, boot path and first static user-space service graph

## 1. Security objectives

Helm's primary objective is to preserve isolation and authority boundaries even when an unprivileged process or user-space service is malicious or compromised.

- **Confidentiality:** a process cannot read memory or device state outside its authority.
- **Integrity:** a process cannot modify kernel state, another process's memory, page tables, capability tables or protected device state without authority.
- **Availability:** untrusted input cannot force unbounded kernel memory use, queue growth, validation work or uncontrolled priority/resource amplification.
- **Authority confinement:** every privileged operation is justified by an unforgeable capability checked at the kernel boundary.
- **Fault containment:** a user-space service crash does not corrupt kernel or unrelated service state; restart does not silently restore revoked authority.
- **Failure determinism:** malformed requests, exhausted resources and invalid transitions produce specified bounded outcomes without partially committed state.

These are objectives, not present guarantees.

## 2. Assets

Kernel code/data/stacks/page tables; physical page ownership and mapping metadata; capability spaces and derivation/revocation metadata; thread state and execution budgets; IPC endpoint state and transferred capabilities; interrupt routing/timer/device ownership; boot information, kernel image and root-task authority; future cryptographic keys; audit and diagnostic records.

## 3. Adversaries

| Actor | Capability | Required defence |
|---|---|---|
| Malicious user process | Arbitrary valid/invalid syscalls, malformed IPC, timing and resource exhaustion | Complete validation, capabilities, address-space isolation, bounded work and quotas |
| Compromised user-space service | Controls its process memory and requests; may lie to clients and misuse granted rights | Least authority, process isolation, revocation, output validation and restart policy |
| Malicious device/firmware | Malformed descriptors/data, unexpected interrupts, potential DMA | Device isolation, bounded parsing, IOMMU before untrusted DMA, reset/recovery contracts |
| Malicious boot payload | Malformed boot structures or modules | Treat all boot structures as untrusted bytes; validate ranges, lengths, overlap, alignment and arithmetic |
| Malicious local user | Process creation, IPC floods, scheduling abuse and storage exhaustion | Per-principal and aggregate quotas, admission control, bounded queues and fair scheduling |
| Malicious privileged developer/build administrator | Can intentionally change kernel code or build inputs | Runtime isolation cannot stop this; require independent review, protected branches, provenance and reproducible builds |
| Compromised firmware/bootloader/hypervisor | Can falsify hardware state or load/alter the kernel | Trusted in H0; record as residual TCB and plan measured reduction/secure boot |
| Physical attacker | Can probe, replace, power-cycle or tamper with hardware | Out of H0 scope; separate physical threat model required |

## 4. Trust boundaries and initial TCB

Initial TCB includes processor privilege and memory-protection mechanisms; firmware, bootloader and QEMU configuration; kernel image and entry assembly; Capstan compiler/backend/linker pipeline; kernel exception, page-table and capability mechanisms; and the initial root task until its authority is subdivided.

User-space drivers/services are outside the kernel memory-isolation TCB only if the kernel correctly enforces address-space and capability boundaries. They remain part of the functional TCB for services they provide.

The TCB inventory changes whenever code, configuration, compiler, linker, bootloader or hardware assumptions change. Written in Capstan does not mean correct or safe by itself.

## 5. H0 scope and exclusions

H0 covers a booted kernel that validates boot handoff data, establishes a known stack, emits bounded diagnostics and halts. H0 does not yet provide untrusted processes, user/kernel isolation, interrupts, DMA, persistent storage, networking, cryptographic key storage, SMP or production secure boot.

The first QEMU target assumes the emulator accurately implements the declared CPU and device model. Firmware, bootloader, host OS, hypervisor, physical host and CI infrastructure remain trusted. Physical attacks, side channels, speculative execution, malicious microcode, hardware faults and firmware compromise are not covered by H0 claims.

## 6. Attack surfaces and mandatory controls

### 6.1 Boot handoff

Treat every bootloader-provided pointer, length, memory map, module and string as untrusted. Validate arithmetic, alignment, canonical addresses, range containment and overlap before dereferencing. Reject unknown mandatory tags, duplicate singleton tags, truncated records and inconsistent lengths. Bound total tag count, bytes, strings and parsing work. Do not use bootloader memory after its ownership/lifetime contract expires. Fail closed without partially validated state.

### 6.2 Syscalls and IPC

Validate syscall number, capability, rights, object type, message length and nested offsets. Copy small control messages into kernel-owned bounded storage before validation; avoid TOCTOU by not validating mutable user memory and later trusting it unchanged. Shared-memory paths specify pinning, ownership, mapping lifetime and revalidation. Validate capability transfer and destination capacity before commit. Failure is atomic: no partial slot insertion, queue mutation or ownership change. Bound work by message size and operation budget.

### 6.3 Memory management

Check size/page-count/address/offset arithmetic before use. Enforce physical-page ownership and mapping rights at every transition. Never free/reassign a page while any CPU, address space, DMA device or in-flight message can still reference it. Separate writable and executable permissions by default. Validate canonical virtual addresses and reserved page-table bits. TLB invalidation/shootdown completion is part of mapping transaction. Use guard pages and explicit stack bounds.

### 6.4 Capabilities

No ambient authority and no authority from guessable integer IDs. Derivation cannot amplify rights. Revocation has specified scope, termination and worst-case work. Stale slots/object reuse cannot resurrect authority. Concurrent transfer, revoke and destroy have a single specified linearisation order. Capability-table exhaustion cannot partially mutate an operation.

### 6.5 Scheduling and interrupts

Bound interrupt-disabled regions and interrupt work. Do not allocate, block or parse unbounded data in interrupt context. Define priority inversion, starvation and budget exhaustion. User-controlled priorities/budget donations cannot amplify authority or consume unbounded CPU. SMP and lock-free paths are excluded until memory-ordering and reclamation rules are specified.

### 6.6 Devices and DMA

No device DMA in H0/H1. Before DMA is enabled, require explicit device capability, bounded descriptor validation, IOMMU configuration/invalidation, bounce-buffer policy where needed, and reset/recovery semantics. MMIO mappings are aligned, range-checked, device-owned and non-executable. Interrupt storms and malformed device state cannot exhaust kernel resources.

## 7. Security invariants

The initial invariant ledger is HELM-INVARIANTS.md. At minimum: user mode cannot write kernel-private memory; kernel-private memory is not executable by user mode; every mapped physical page has exactly one authoritative ownership record; mappings never grant more rights than the source capability; a process cannot invoke an object without a matching live capability and rights; derivation never increases authority; invalid inputs do not mutate protected state; rejected operations are failure-atomic; every kernel queue, stack, table and work loop is finitely bounded; no page is reclaimed while a reference can still be used; an untrusted service cannot force work proportional to an unchecked length; and DMA is impossible until the IOMMU/device-ownership gate passes.

Each invariant must link to enforcement, an executable negative test, a model property and implementation-refinement obligation. Unimplemented invariants remain OPEN, not PASS.

## 8. Vulnerability classes and residual risks

The design targets memory corruption, out-of-bounds access, integer overflow, use-after-free, double free, stale-handle reuse, privilege escalation, confused-deputy errors, capability leakage, TOCTOU, malformed parser input, resource exhaustion, priority inversion, deadlock, interrupt abuse, DMA attacks and cross-process disclosure.

It cannot honestly claim every instance of every vulnerability class is impossible. Logic errors, incorrect policy, compromised trusted components, compiler defects, hardware defects, side channels and unknown design flaws remain possible. Publish residual risks and exact evidence rather than a blanket secure label.

## 9. Required adversarial test families

Malformed/truncated/overlapping boot information and address overflow; invalid page-table entries and permission escalation; invalid syscall numbers/capability types/rights/stale references; duplicate capability transfers and revocation races; malformed IPC lengths/offsets/types/aliasing; queue saturation/allocation failure/budget exhaustion at every transition; cancellation and service death at every ownership-transfer boundary; interrupt storms/timer wraparound/invalid device events; mapping teardown/TLB shootdown/page-reuse stress; and fault injection at every allocation and commit point.

Every defect becomes a deterministic regression vector and is classified by root cause and violated invariant.

## 10. Assurance reporting

Every report records exact repository commit and artefact hash; compiler, linker, bootloader, QEMU and CPU configuration; threat-model revision and scope; test corpus and seeds; proof tools/theorems/imports/axioms/assumptions; model-to-implementation refinement status; TCB inventory; known defects, exclusions and unresolved obligations.

No test, proof, benchmark or audit is inferred from the existence of a script or document. Missing evidence is UNKNOWN.
