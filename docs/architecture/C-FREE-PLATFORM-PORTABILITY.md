# C-free platform portability and OS boundary

**Status:** implementation contract proposal; no native backend or C-free platform support is claimed  
**Programme:** C-free execution / CCAM  
**Related:** [C-free execution programme](C-FREE-EXECUTION.md), [compiler pipeline audit](COMPILER-PIPELINE-AUDIT.md), [CCAM](CCAM.md)

## 1. Purpose

The C-free programme must not replace one host-specific dependency with another. CCAM semantics and conformance tests are platform-independent; native code generation, executable loading, process startup, memory management and operating-system services are platform-specific boundaries.

This document proposes a minimum major-platform target set and the evidence required before a target is called supported. It does not select a final ISA, object format, ABI, linker, runtime memory manager or native backend.

## 2. Minimum platform target set

The programme's eventual supported-platform claim should cover all three major desktop/server operating-system families:

| Operating system | Required CPU targets | Native CI requirement |
|---|---|---|
| Linux | x86-64 and AArch64 | Native runner for each declared target; at least one mainstream distribution per architecture |
| macOS | arm64 and x86-64 | Native Apple Silicon and Intel execution, or a documented retirement decision for Intel hardware |
| Windows | x86-64 and ARM64 | Native Windows runner for each declared target; test the supported Windows ABI and executable format |

The table is a target requirement, not a statement of current support. The current C-backed CI matrix (Linux/GCC, Linux/Clang, macOS/Clang) does not establish any C-free target support and does not test Windows.

A target may be added in stages. The first native backend should use one architecture/ABI to keep the code generator small. That sequencing must not silently narrow the programme's eventual platform commitment. The portable CCAM evaluator and its conformance suite should remain runnable on every available CI host from the outset.

If hardware or runner availability prevents native testing for a target, mark that target **not yet validated** rather than inferring support from cross-compilation alone.

## 3. Separate semantic portability from native portability

Three layers must be reported separately:

1. **Semantic conformance:** the same validated CCAM program has the same observable result, trap class, and deterministic step/depth behaviour on every host. This layer must not depend on host pointer width, endianness, filesystem semantics, thread scheduling, or C integer behaviour.
2. **Native backend conformance:** generated code obeys the selected ISA, object format, calling convention, stack alignment, register preservation, relocation and unwind requirements for that target.
3. **Platform adapter conformance:** OS-facing operations implement the specified Capstan contract, including errors, resource limits, path handling, entropy quality, process arguments and environment, clocks, and file semantics.

Passing one layer does not imply passing the others. In particular, an interpreter or cross-compiled binary passing CCAM tests is not evidence that a native backend, executable loader, garbage collector or OS adapter is correct.

## 4. Narrow platform adapter boundary

Keep operating-system dependencies behind a small, explicit interface. The initial adapter inventory should classify each operation as required, optional, or excluded for the relevant runtime profile:

- process entry, exit status, arguments and environment;
- standard input/output/error and file open/read/write/close;
- path representation, path normalisation and filesystem error mapping;
- monotonic clock and wall-clock access;
- cryptographically secure random bytes;
- virtual memory reservation/commit/decommit and page-size queries, if required by the allocator/collector;
- thread creation, joining, synchronisation and thread-local state, only when concurrency is specified;
- stack bounds/guard pages and signal/exception integration, only where the runtime design requires them;
- dynamic library loading and foreign calls, only if explicitly admitted by the language/runtime contract.

The adapter API must expose Capstan-level result/error types. Do not leak raw platform error numbers, native handles, pointer-sized integers, or platform path encodings into CCAM semantics. Handle ownership and lifetime must be explicit. Any adapter operation that can block, allocate, fail, or observe external state must have a documented effect and resource contract.

Do not assume POSIX as the abstract API. The current runtime's use of `unistd.h`, `fcntl`, `fstat`, `/dev/urandom`, pthreads, signals, `mmap` and platform-specific stack APIs is evidence that the existing runtime is not made Windows-portable merely by adding a Windows CI runner.

## 5. Portability invariants

- CCAM integer arithmetic is defined over signed 64-bit values; host `long`, pointer width and native overflow behaviour must not alter it.
- Serialized machine data uses an explicitly defined byte order and exact integer decoding; native struct layout is never a wire format.
- Unicode behaviour is defined in terms of Unicode scalar values and specified encodings, not the host's `wchar_t` width or locale.
- Filesystem paths are not assumed to be UTF-8 byte strings on every host. The adapter must define conversion, rejection and round-trip behaviour.
- Timeouts and execution budgets use a monotonic time source; wall-clock changes must not extend or shorten a relative timeout.
- Entropy must come from the platform's cryptographically secure source; deterministic test entropy must be injected explicitly and must never be the production default.
- Native stack/register/ABI details remain backend concerns and must not leak into language-level evaluation order or observable semantics.
- Runtime resource ceilings must be checked before allocation or platform calls that can exceed them.

## 6. CI and release gates

A platform/architecture combination is **supported** only when all applicable gates pass on that target:

1. Compiler and runtime build without generated C, a C compiler, or a C runtime in the ordinary build/run path.
2. CCAM semantic conformance suite passes natively on the target.
3. Backend tests cover arithmetic edge cases, calls/returns, stack discipline, traps, relocations, and executable startup/exit.
4. OS adapter tests cover success, failure, boundary and resource-exhaustion paths for every implemented service.
5. Runtime memory-management tests cover allocation limits, stack/root handling, collection and failure behaviour on that ABI.
6. Security tests cover secret handling, entropy acquisition, path and file boundaries, and capability/grant checks where those features are enabled.
7. The release records compiler revision, target triple, ABI, object format, runner/host, toolchain versions and any external trusted components.

Cross-compilation is useful as an additional build check, but does not replace execution on a native runner. Emulation may supplement native CI for regression coverage; it must be labelled and must not be the sole basis for a supported-platform claim.

The existing C-backed workflow should remain separate and clearly labelled until the C-free build is independently runnable. Adding Windows to the existing C workflow would test the legacy runtime port, not complete the C-free platform requirement.

## 7. Suggested rollout

| Phase | Deliverable | Exit evidence |
|---|---|---|
| P0 | Host-independent CCAM conformance suite | Same tests and expected outcomes on Linux, macOS and Windows CI hosts where available |
| P1 | First native backend on one declared target | Native build/run, backend validation and documented ISA/ABI boundary |
| P2 | Second architecture and macOS target | Native arm64/x86-64 execution plus backend/adapter conformance |
| P3 | Windows target | Native Windows build/run and explicit Windows OS adapter; no POSIX compatibility layer treated as the architecture |
| P4 | Complete minimum matrix | All OS/architecture combinations in §2 meet the support gates |

The order may change for engineering reasons, but the acceptance criteria must not. Every deferred target remains visibly outstanding.

## 8. Non-claims

This proposal does not claim that Capstan currently has a C-free compiler, native backend, Windows runtime, cross-platform C-free garbage collector, or a verified OS adapter. The current generated-C backend and POSIX-oriented runtime remain the active production path. The CCAM evaluator is a semantic foundation, not an end-to-end replacement for that path.
