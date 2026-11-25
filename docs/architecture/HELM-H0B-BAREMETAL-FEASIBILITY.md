# Helm H0-B — bare-metal target feasibility and implementation plan

**Status:** source-level feasibility audit; no target implementation or QEMU execution claimed  
**Date:** 2026-11-26  
**Branch:** `helm/h0b-limine-feasibility-2026-11-26`  
**Depends on:** `HELM-ADR-001.md`, `HELM-THREAT-MODEL.md`, `HELM-INVARIANTS.md`

## 1. Executive result

Capstan has a useful but deliberately narrow x86-64 native code-generation prototype on `main`. It emits scalar CCAM programs as GNU assembler source and the test suite assembles and links freestanding Linux ELF executables without a C compiler or C runtime in the *target executable*.

This is not yet a kernel backend. The current entry point, process exit path, and platform contract are Linux-specific. The current CCAM machine also lacks the memory, byte-view, I/O, interrupt, atomic and privileged-instruction semantics required for a kernel. There is no discovered Limine boot target, kernel linker script, kernel entry stub, QEMU kernel smoke test or kernel-specific build target in the inspected source paths.

**Conclusion:** a small x86-64 kernel proof-of-execution is feasible without introducing a C implementation, but it requires a distinct kernel target adapter and a narrowly specified Capstan memory/platform interface. Do not fork or relabel the Linux process emitter as a kernel emitter. Preserve the Linux backend as a conformance target and factor shared instruction emission only where the contracts genuinely match.

## 2. Evidence inspected

Repository evidence was inspected on the default branch at the source snapshot exposed by GitHub during this review. Key files:

| File | Observed implementation/evidence | Limitation |
|---|---|---|
| `verification/ccam_native_x64.cap` | Capstan-written scalar x86-64 assembly emitter; validates multi-function CCAM before emission; explicit instruction/register/stack ceilings; checked arithmetic, branches, direct calls, return/trap handling | Linux process entry/exit and scalar-only CCAM; no arbitrary memory, device I/O or privileged instruction contract |
| `docs/architecture/CCAM-NATIVE-BACKEND.md` | Documents GNU `as` and `ld`, freestanding ELF, System V AMD64, no C target output/runtime | Header still says “under review in PR #212”, which is stale: PR #212 is closed and merged |
| `docs/architecture/CCAM.md` | Defines CCAM v0.1 as typed scalar machine and explicitly excludes IO, concurrency, heap objects and other effects | Header's “proposed in PR #212” native-backend status is stale |
| `tests/run.sh` | Invokes the Capstan-native backend tests; on Linux x86-64 runs GNU `as --64`, GNU `ld`, `readelf`, `nm`, then executes ten generated ELF cases | No QEMU invocation or kernel image test in this test section |
| `Makefile` | Default compiler bootstrap remains Python-seeded and C-generating, then compiled with the host C compiler and Capstan C runtime | This is still part of the compiler/build trusted path; it is not a C-free end-to-end bootstrap |
| `docs/C-FREE-BOOTSTRAP.md` | Defines the intended C-free bootstrap and platform boundary | Normative target is incomplete; do not claim the compiler itself is C-free |

The inspected native backend PR #212 is merged. PR #213, the native CLI work, is closed without merge. The current kernel work must not assume a production target-selecting native compiler command exists.

This is a source review only. The test script was inspected, not executed in this environment. The presence of a test is not a passing test result.

## 3. Existing native backend: exact useful subset

The current path is:

```text
Capstan source
  -> lexer/parser/checker
  -> checked scalar lowering
  -> multi-function CCAM validation
  -> Capstan x86-64 assembly emitter
  -> GNU as
  -> GNU ld
  -> freestanding Linux x86-64 ELF
```

The backend supports integer/boolean constants and moves, checked signed-64 arithmetic, comparisons, boolean negation, conditional/unconditional branches, direct calls and typed returns, and explicit traps. It has finite ceilings for expanded instructions, aggregate registers, call depth and native stack bytes. It uses stack slots and initialized flags to preserve the evaluator's uninitialised-register behaviour.

The existing tests cover a basic function call, loops/conditionals, bounded recursion, overflow, division by zero, signed division overflow, the `INT64_MIN % -1` case, step limits, call-depth limits and uninitialised-register traps. The Linux test harness checks for no ELF interpreter and no undefined external symbols before executing generated programs.

These are useful foundations for a deterministic scalar code generator. They do not establish kernel execution, memory safety of a kernel, or compiler correctness.

## 4. Kernel blockers

| Blocker | Current state | Required work |
|---|---|---|
| Entry ABI | Linux `_start`; process-specific register/stack assumptions | New Limine x86-64 entry adapter with explicit register, stack, flags and non-returning contract |
| Exit semantics | Linux `syscall` exit | Kernel entry must not issue Linux syscalls; use a non-returning halt/panic path and a test-only QEMU exit adapter |
| Image layout | Existing assembly is linked as a Linux ELF executable | Dedicated higher-half kernel linker script; explicit PT_LOAD permissions; no interpreter, dynamic loader or runtime relocations |
| Boot protocol | No Limine request structures or parser identified | Capstan definitions for the pinned protocol revision; bounded response and memory-map validation |
| Memory access | CCAM v0.1 has only Int64/Bool registers and function-local scalar slots | Specify bounded read-only boot-memory views and later typed kernel memory operations; no untyped source-level raw pointer arithmetic |
| Device I/O | No CCAM I/O operation or x86 port-I/O boundary | Narrow reviewed assembly adapter for serial/debug I/O, with typed Capstan contract and no arbitrary port access from untrusted code |
| Exceptions | No kernel IDT/exception entry contract | Install own IDT before parsing untrusted pointers; bounded exception record and fail-closed halt |
| Privilege | No ring-transition or kernel/user ABI | Not part of H0-C0; specify and test separately before H1 |
| Compiler integration | Backend is an internal test/emitter path; PR #213 did not merge | Add explicit target selector only after kernel backend tests and shared conformance exist |
| Bootstrap | Compiler build still depends on Python stage 0, generated C, host C compiler and C runtime | Record as build TCB; remove only through separate C-free bootstrap gates |

### 4.1 Critical semantic gap: memory

The current CCAM v0.1 subset cannot safely parse Limine responses because it has no byte strings, pointer/view type, memory-load operation or memory model. It is not acceptable to represent a boot pointer as an ordinary signed integer and emit unchecked dereferences.

The minimum safe extension should be a **bounded memory-view abstraction**:

- A view is an opaque, kernel-created authority over a finite byte range, not an arbitrary integer address.
- Reads require an explicit offset and width; offset-plus-width uses checked arithmetic before access.
- Little-endian scalar decoding is specified exactly.
- No read can cross the view boundary, and failure leaves parser state unchanged.
- Views are read-only for the initial boot parser.
- A view cannot be forged by user code or widened by arithmetic.
- The platform shim that turns a bootloader response pointer into a view is a named TCB boundary, with its own address-canonicality, mapping and fault-containment requirements.
- Every malformed tag/count/length/pointer test has a bounded result; parsing work and aggregate bytes are capped before iteration/allocation.

This should be specified as a separate CCAM/kernel ABI extension before any boot parser implementation. It is not a justification for general-purpose unsafe pointers.

A second representation gap is equally important: CCAM v0.1 exposes signed Int64, while x86-64 canonical virtual addresses and Limine's U64 protocol fields require unsigned 64-bit bit-pattern semantics. Reinterpreting a high-half address as a signed integer and using signed comparisons is incorrect. The reference model added in `verification/helm_boot_memory_model.cap` represents U64 values as two checked U32 limbs, implements unsigned comparison/add/subtract, four-level canonicality and bounded range containment, and snapshots bounded byte views for little-endian decoding. This is a pure Capstan model over an owned byte list; it does not dereference physical memory and is not yet a machine-code backend feature.

## 5. Boot protocol choice: Limine for the first x86-64 slice

The initial architecture record previously named Multiboot2 as the boot candidate. This audit recommends **Limine x86-64** for the first kernel image, with the exact bootloader release and protocol base revision pinned in the build manifest.

Reasons:

1. The Limine x86-64 contract enters directly in 64-bit mode, with a defined System V ABI (without FP/SIMD), a bootloader-provided stack, and interrupts disabled. This avoids adding a 32-bit protected-mode-to-long-mode trampoline to the first bring-up milestone.
2. The protocol provides a memory-map response and an explicit HHDM request/response. The HHDM offset is runtime data and must never be hard-coded.
3. ELF is strongly recommended. Loadable segment permissions are reflected in mappings, so the kernel image can request distinct RX, R and RW segments.
4. Base revision 5 or later defines a more deterministic x86-64 entry state, including control-register/EFER state and an explicitly empty IDT. Helm must still install its own IDT and must not rely on bootloader descriptor tables.
5. The protocol explicitly marks responses and associated data as bootloader-reclaimable. Helm must preserve them until it has copied/consumed all required data and established its own mappings.

Security caveats are material:

- Limine's initial HHDM mappings are supervisor mappings with broad RWX permissions. They are a boot convenience, **not** Helm's final memory-protection policy.
- The bootloader's GDT and page tables are in bootloader-reclaimable memory. Do not reclaim those pages until Helm has installed its own GDT/page tables and no longer depends on the old structures.
- The memory-map response, pointers, counts, sizes and ranges are untrusted input at the kernel parser boundary. Sorted entries and alignment guarantees from the protocol are useful preconditions, not substitutes for bounds validation.
- The HHDM base may vary. The kernel must request and validate it.
- The bootloader, firmware, QEMU and pinned build artifacts remain in the initial TCB.

Multiboot2 remains a viable alternative, but its common i386 boot path enters 32-bit protected mode with paging disabled. That requires a separately reviewed long-mode transition, page-table construction and entry trampoline. For this first x86-64 proof-of-execution, Limine reduces early assembly and boot-state ambiguity.

Protocol reference: https://github.com/Limine-Bootloader/limine-protocol/blob/trunk/PROTOCOL.md  
Multiboot2 reference: https://www.gnu.org/software/grub/manual/multiboot2/multiboot.html

## 6. Proposed H0-C implementation sequence

### H0-C0 — Capstan code executes in kernel privilege

Deliver a deliberately small, non-interactive proof-of-execution:

1. A pinned Limine boot image loads a statically linked higher-half ELF kernel.
2. A minimal assembly entry stub disables interrupts, clears the direction flag, switches to a kernel-owned bounded stack and calls one Capstan-generated scalar function.
3. The Capstan function computes a fixed result using the supported scalar subset.
4. A test-only assembly exit stub writes the result to a QEMU debug-exit device; production builds use a non-returning halt loop.
5. A QEMU test asserts the expected exit code, timeout behaviour and panic marker absence.

This proves only that Capstan-generated scalar code executes at kernel privilege under the declared emulator/bootloader configuration. It does not prove boot-info safety, memory isolation or kernel correctness.

### H0-C1 — Safe boot metadata boundary

1. Specify the bounded read-only memory-view ABI described in section 4.1.
2. Install a minimal IDT and exception path before reading bootloader response memory.
3. Validate the Limine base-revision response and required request responses.
4. Validate pointer canonicality, view containment, counts, multiplication/addition overflow, alignment and aggregate byte/entry ceilings.
5. Parse the memory map into a bounded Capstan-owned snapshot.
6. Keep bootloader-reclaimable pages unavailable until all references have been eliminated.
7. Differentially test the parser against an independent fixture generator and malformed-input corpus.

### H0-C2 — Minimal diagnostics

Add a bounded serial-output adapter. The kernel owns the serial port only after the relevant platform setup. Capstan code supplies bounded byte spans; the adapter does not scan for unbounded NUL terminators or accept arbitrary port numbers. Panic output is bounded and does not disclose pointers or memory contents unnecessarily.

## 7. Build and test contract

The H0-C pipeline is expected to use:

- Capstan compiler invocation for the kernel subset;
- GNU `as` or another explicitly pinned assembler as an object-format tool;
- GNU `ld` or another explicitly pinned linker;
- `readelf` and `nm` for structural artifact checks;
- pinned Limine bootloader binaries/source and protocol revision;
- pinned `qemu-system-x86_64` for execution.

The kernel ELF audit must reject:

- `PT_INTERP`, dynamic dependencies and undefined symbols;
- unexpected writable-executable load segments;
- unexpected relocation sections or unresolved relocations;
- unexpected entry point, segment ranges or alignment;
- image segments outside the declared higher-half layout;
- unbounded or oversized boot-time stacks and static buffers.

The QEMU harness must have a hard timeout, bounded serial capture, deterministic machine/CPU/memory configuration, explicit boot media, a debug-exit result, and a hash of every input artifact. It must test both expected boot and deliberate failure cases. The harness itself is not proof that the hardware behaves like all physical machines.

The first CI gate should run on Linux x86-64 with the pinned emulator and toolchain. Other host platforms may perform code-generation/structural checks but must not report kernel execution coverage unless they actually execute the image.

## 8. Required Capstan changes

The work should be split into small independently testable changes:

1. **Target contract:** document `x86_64-unknown-helm`, object format, code model, calling convention, no-FP/SIMD rule, section policy and entry contract. Do not claim this target exists until the emitter and tests do.
2. **Backend factoring:** separate validated CCAM function-body emission from Linux process entry/exit. Preserve existing Linux output byte-for-byte where practical and keep its tests.
3. **Kernel entry emitter:** add a kernel-specific entry/exit adapter; no Linux syscall sequence, no process runtime, no C symbols.
4. **Linker/image integration:** add linker script and reproducible ELF checks.
5. **QEMU integration:** boot and execute the scalar proof-of-execution.
6. **Memory-view semantics:** specify and implement bounded boot-memory access before parsing metadata.
7. **Formal bridge:** define the machine-code/ABI relation for the scalar kernel subset and prove or explicitly scope the unproved assembly boundary.

Do not add a generic `unsafe` escape hatch, arbitrary inline assembly, arbitrary I/O ports, raw user pointers or unconstrained memory intrinsics to make the demo work.

## 9. Capstan-native boot-memory reference model

The initial executable model is in `verification/helm_boot_memory_model.cap` and is wired into `tests/run.sh`. It covers U64 limb arithmetic/carry/borrow/overflow, unsigned ordering across the signed bit, four-level x86-64 canonical-address checks, range containment and wrap rejection, bounded immutable byte snapshots, little-endian u8/u16/u32/u64 reads, and exact-end/truncated/invalid-byte cases.

The model is intentionally not described as a kernel memory accessor. It uses ordinary Capstan lists and is intended to be an executable semantic reference for the later hardware adapter. Its test status remains UNKNOWN until the exact branch is run through CI or a local Capstan test runner.

## 10. H0-B acceptance checklist

| Requirement | Current result |
|---|---|
| Existing Capstan x86-64 emitter located and reviewed | SOURCE REVIEW COMPLETE |
| Existing native execution test cases identified | SOURCE REVIEW COMPLETE; not executed in this review |
| Linux ABI/process-only assumptions identified | COMPLETE |
| C-free target artifact boundary distinguished from compiler bootstrap TCB | COMPLETE |
| Boot protocol compared and initial candidate selected | COMPLETE: Limine x86-64 recommended |
| Bare-metal target implementation | NOT STARTED |
| Kernel linker script and image | NOT STARTED |
| QEMU boot test | NOT STARTED |
| Boot-memory view semantics | SPECIFICATION REQUIRED |
| Kernel code execution at ring 0 | NOT DEMONSTRATED |
| Memory isolation/security proof | NOT CLAIMED |

H0-B is complete as a source-level feasibility and dependency assessment, with an initial Capstan reference model added for the unsigned-address and bounded-view semantics. The model has not yet been executed in this review. H0-C remains blocked on the target adapter, linker/image, pinned bootloader/emulator harness and a hardware-backed memory-view implementation. No implementation test or proof is implied by this report.

## 10. External protocol references

- Limine Boot Protocol, official specification: https://github.com/Limine-Bootloader/limine-protocol/blob/trunk/PROTOCOL.md
- GNU GRUB Multiboot2 specification: https://www.gnu.org/software/grub/manual/multiboot2/multiboot.html
