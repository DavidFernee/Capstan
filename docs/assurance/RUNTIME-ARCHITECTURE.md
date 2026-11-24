# Runtime architecture and v0.6 safety assessment

**Status:** initial source audit; implementation and proof work remain outstanding  
**Baseline:** main, inspected 2026-11-24  
**Scope:** runtime/capstan_gc.h, runtime/capstan_rt.h, runtime tests, design map and assurance documents

This document separates current implementation from proposed work. A passing test suite is evidence about tested executions, not a proof of memory safety.

## 1. Executive assessment

Capstan currently has a single-process, single-threaded, conservative, non-moving mark-and-sweep collector. It is a useful foundation, but it does not yet implement generational collection, explicit object destruction, deterministic resource lifetimes, or a concurrency memory model.

The current language has no user-visible pointers or manual deallocation. This substantially narrows the surface for ordinary Capstan programs, but it does not justify the blanket statement that use-after-free is impossible: the C runtime, generated C, conservative root discovery, and allocator metadata remain trusted components. A stale pointer is not a language-level capability and the collector does not validate every dereference.

**Release position:** do not enable a generational collector or claim stronger runtime safety until the barriers, root model, arithmetic bounds, secret-erasure contract, and verifier have been specified and adversarially tested. Concurrency remains unsupported; the collector is not thread-safe.

## 2. Existing architecture

### Allocation classes and metadata

- Small objects (up to 2 KiB) use 64 KiB pages, one size class per page, with allocation and mark bitmaps.
- Larger objects are individually allocated and tracked in a base-address-sorted array; collection sorts that array before binary-search pointer recognition.
- Three allocation kinds exist: pointer-bearing, pointer-free/atomic, and pointer-free secret.
- Page lookup uses an open-addressed hash table keyed by page number. Interior addresses are mapped to their containing allocation slot.
- Collector metadata (page arrays, bitmaps, roots, mark work stack and large-object records) is allocated separately with libc calloc/free; it is not itself traced by the collector.
- Empty pages may be retained for reuse or advised back to the OS while their virtual address reservation and page-table entry remain.

### Roots and tracing

The collector conservatively scans registered global roots, a setjmp register spill, and the current machine stack up to the recorded stack top. Pointer-bearing objects are scanned word by word. Any aligned machine word that falls inside an allocated object, including an interior address, retains that object. Atomic objects are not scanned.

Consequences:

- False positives retain objects; they do not by themselves prove reachability.
- Stack and register liveness depends on ABI/compiler behaviour and the collector's platform-specific stack discovery.
- The root model is for the current thread only. There is no stop-the-world protocol or per-thread root registration.
- A pointer into an allocation is treated as retaining the entire allocation; there is no subobject lifetime model.

### Collection and allocation

A collection is a full mark-and-sweep. It sorts large-object metadata, marks from roots, drains a dynamically grown mark stack, sweeps page slots and large allocations, wipes unreachable secret allocations, and adjusts the allocation threshold. Stress mode requests collection every N allocations. The collector has a configurable heap ceiling and reports OOM/limit failures through process termination or a runtime panic.

There are no generation bits, minor collections, card table, write barriers, remembered set, or full-vs-minor verifier in the inspected implementation.

## 3. Runtime safety findings

| Area | Current state | Assessment / required action |
|---|---|---|
| Use-after-free / double-free | No language-level free; tracing reclamation | Strong mitigation for well-typed programs, not an end-to-end proof. Audit every C pointer path and allocator state transition; add invariant checks and adversarial stale/interior-pointer tests. |
| Bounds and object identity | Runtime checks exist for collection access; collector recognises interior pointers | Specify object-start/slot arithmetic and validate all lengths before pointer arithmetic. A collector's reachability lookup is not a dereference bounds check. |
| Allocation-size arithmetic | Heap and metadata sizes use size_t; dynamic metadata arrays grow by doubling and multiply element counts | Audit every addition, doubling and multiplication before allocation. Add checked size helpers and fail closed on overflow before changing allocator state. |
| OOM | calloc/page allocation failures terminate; some heap-limit paths panic | Distinguish user heap-limit failure from metadata OOM. Ensure failed metadata growth leaves all existing state intact. |
| Secrets | Secret allocations are wiped when reclaimed by collection | This is nondeterministic erasure, not prompt erasure. The small-object path currently uses ordinary memset; replace with a non-elidable wipe primitive and test generated code/optimised builds. Define explicit destruction/zeroing before claiming deterministic erasure. |
| Finalisation | No finaliser/destructor protocol in the collector | Keep it that way until a precise, non-resurrecting, bounded, non-throwing finalisation model exists. Never use GC timing for file, lock, transaction or secret cleanup. |
| Resources | Existing I/O helpers perform bounded operations; no general RAII/linear resource model | v0.6 capabilities need explicit close/consume semantics and failure-path tests. GC may be a last-resort memory reclamation mechanism only. |
| Aliasing / ownership | No exposed raw pointers; structs, lists, maps and grants are traced heap objects | Specify aliasing as shared reachability, not unique ownership. v0.5 closure capture must keep environments rooted; grant/capability containment must be transitive. |
| Concurrency | No language threads/tasks yet; collector state is global and unsynchronised | Explicitly unsupported. Do not expose threads or async callbacks until root registration, stop-the-world/safepoint protocol, allocator synchronization and data-race rules are implemented. |
| Stack | Stack guard uses platform-specific discovery and signal handling; fallback stack-top heuristic exists | Test stack direction, alternate-stack installation failure, nested signals, platform bounds and sanitiser interaction. The fallback must not silently imply a reliable guard. |
| Type confusion | Static type checking and typed code generation; GC itself scans conservatively | Document runtime object layout and allocation-kind invariants. Add debug headers/canaries or equivalent metadata checks where practical. |

### High-priority code audit targets

1. Every capacity growth expression: capacity multiplied by two, count multiplied by sizeof(T), and used plus requested.
2. Heap accounting expressions such as heap plus n, page accounting and threshold/reserve arithmetic.
3. Pointer-range expressions such as base plus size, scan end addresses and page-index calculations.
4. Failure atomicity: no partially updated free list, page table, large-object array or root table after allocation failure.
5. Secret wipe implementation and every copy/conversion path for secret-bearing values.
6. Root registration lifetime and generated global-root correctness.

These are audit targets, not assertions that each expression is currently exploitable. Each proposed fix must carry a reproducer or a property test.

## 4. Generational collector: design constraints

A generational collector is a performance optimisation, not a safety feature. The first implementation should be a conservative two-generation, non-moving design with a full-collection fallback.

### Proposed invariants

- Every allocated slot belongs to exactly one generation and one allocation kind.
- A young object is reclaimed by a minor collection only if it is unreachable from all roots and all remembered old-to-young edges.
- Every pointer store into an old object that may create an old-to-young edge records the destination card before the next collection can rely on the remembered set.
- Runtime collection operations and generated stores use the same barrier contract.
- A promotion scans the promoted object and establishes remembered-set state for any young referents.
- Minor collection never reclaims old objects. A full collection traces the complete graph and resets generation/remembered-set state.
- Allocation, barrier and collection failure are fail-closed; no partial collection is observable by the program.
- Secret objects are never considered erased merely because a minor collection ran or an object became unreachable.

### Suggested staged algorithm

1. **Instrument before collecting generationally.** Introduce a single write-barrier ABI and route every generated pointer-bearing field/list/map/grant store and every runtime mutation through it. Keep full mark-sweep as the only collector.
2. **Add verifier mode.** Record dirty cards and, after each simulated minor trace, run an independent full trace. Assert that every object reachable by the full trace would be retained by the minor trace. Initially this mode must not reclaim objects.
3. **Add generation metadata.** Promote only at a full-collection boundary in the first version. Objects allocated since that boundary are young; previously live objects are old. This avoids promotion of an object whose outgoing edges have not been traced.
4. **Add minor collection behind an opt-in test flag.** Trace stack/register/global roots, then scan remembered old cards, then trace young objects. Sweep young only. Preserve dirty cards conservatively until a verified rescan proves they no longer contain young references.
5. **Stress and differential phase.** Run the entire suite, bootstrap, mutation/differential fuzzing, GCC/Clang and ASan/UBSan with verifier enabled. Generate adversarial graphs with old-to-young, young-to-old, cycles, interior pointers, atomic payloads and repeated mutation.
6. **Enable only after evidence.** Compare pause time and total work against full collection on representative workloads. Retain a forced-full mode and a deterministic fallback threshold.

### Conservative-collector caveat

The proposed card barrier is only sound if every pointer write that can create a heap edge is instrumented. Conservative scanning of arbitrary object bytes, hidden pointer writes in C helpers, and future foreign-memory interfaces complicate that premise. If the runtime cannot establish complete store coverage, do not implement minor reclamation; keep full tracing or adopt a more precise object-layout/root representation first.

## 5. Object lifetime and resource semantics

### Heap objects

- Allocation creates a zero-initialised object with a stable address.
- A value/reference in a root or reachable object keeps its allocation alive.
- Aliases refer to the same allocation; mutation through one alias is observable through the others.
- Scope exit removes stack roots but does not imply destruction.
- Reclamation occurs only after a collector proves the object unreachable under its root model.
- There is no user-visible manual free and no promise about when unreachable memory is reclaimed.

This is reachability-based lifetime, not deterministic ownership. It is suitable for ordinary memory, not scarce or externally visible resources.

### External resources

For capabilities, files, sockets, processes, locks and transactions, use explicit scoped/linear handles:

- A successful acquisition yields one live handle with a declared capability set.
- Operations require a live handle and cannot widen its authority.
- Explicit close/consume invalidates the handle; repeated use is rejected.
- Scope exit must close resources through compiler-generated cleanup on every normal and error exit, or the language must require explicit close and statically reject a live handle at scope exit. Choose one model and specify it before exposing the API.
- GC finalisation must not be the correctness mechanism. A finaliser may run late, never run before process exit, or be skipped after abnormal termination.
- Resource limits and timeouts are explicit and checked; an untrusted peer cannot force unbounded buffering.

### Secrets

- GC reachability may keep a secret alive; it cannot promise erasure at a chosen time.
- Provide a non-elidable wipe operation and a non-copying/linear secret container where feasible.
- Define whether secrets can be captured by closures, stored in aggregates, formatted, cloned or returned. Prefer prohibiting implicit copies and requiring explicit audited duplication.
- Wipe all owned copies on explicit destruction and on any eventual collector reclamation.
- State the limits: registers, compiler-created temporaries, swap, core dumps and hardware side channels require separate controls and cannot be solved by a heap wipe alone.

### Finalisation

Do not introduce arbitrary user finalisers in v0.6. If later required, finalisers must be bounded, non-blocking, non-throwing, non-resurrecting, ordered only by explicit dependency rules, and isolated from collector metadata mutation. Prefer explicit resource cleanup over finalisation.

## 6. Trusted computing base

For the current runtime safety claim, the trusted computing base includes:

- runtime/capstan_gc.h and runtime/capstan_rt.h;
- compiler type checking, code generation and generated root/store instrumentation;
- GCC or Clang and their C ABI/code-generation behaviour;
- libc allocation, memory, signal, pthread and I/O routines;
- OS virtual-memory, process-stack, signal and scheduling behaviour;
- bootstrap implementation and build/test scripts insofar as they produce the shipped compiler;
- hardware and platform memory model.

ASan, UBSan, fuzzers, differential tests, coverage and mutation tests are evidence-producing controls, not members of a proof of absence. The collector's conservative root model and platform stack assumptions remain explicit trust assumptions.

## 7. Acceptance evidence before v0.6

- Checked-arithmetic unit/property tests for every capacity, byte-size, heap, page and pointer-range calculation, including SIZE_MAX boundaries.
- Allocator failure injection at every metadata allocation site; verify allocator invariants and no leaks/corruption after each injected failure.
- GC graph tests: cycles, interior pointers, false roots, root removal, global roots, large objects, all allocation kinds, page reuse and repeated collection.
- Secret wipe tests at -O0/-O2/-O3 with both GCC and Clang, inspecting observable memory after explicit wipe and eventual reclamation.
- Old-to-young barrier matrix: field, list, map, grant, closure environment, nested aggregate, mutation after promotion, and runtime-internal writes.
- Verifier/full-trace differential check on every minor collection; verifier must detect deliberately omitted barriers.
- Stack tests on Linux and macOS, including alternate-stack setup failure and deeply nested calls.
- ASan/UBSan plus integer-overflow instrumentation where supported; fuzz allocator metadata transitions and collection schedules.
- Repeatable stress seeds and minimized regression cases; report exact compiler, flags, OS and commit SHA.
- No concurrency claims until a separate memory model and collector synchronization protocol are implemented.

## 8. Coordination and implementation boundary

The runtime/GC work is isolated on runtime/gc-safety-v06. The active compiler/grant work reported on coordination issue #25 touches runtime/capstan_rt.h; this assessment therefore avoids that shared header and the compiler/codegen. Generational work must coordinate the write-barrier ABI with the compiler contributor before either side changes stores. Shroud and Anchor are out of scope.

The design map currently labels generational collection as a v0.4 remaining item and concurrency as v0.7. This v0.6 work should not silently move concurrency forward or describe an unimplemented collector as complete. Update the map only through a separate coordinated handoff once the design and shared interfaces are agreed.


## 9. Initial hardening implemented on this branch

The first implementation pass addresses concrete arithmetic and erasure weaknesses in the collector without changing the collection algorithm:

- Added checked size addition and multiplication helpers, plus checked geometric capacity growth. The page table, page array, spare-page array, mark stack, large-object array and global-root array now size their metadata allocations through checked helpers.
- Replaced potentially wrapping heap-limit comparisons with subtraction-based checks and guarded heap-accounting additions/subtractions. Allocation counters now fail closed on overflow.
- Validated allocation-kind indices and rejected allocation requests above the runtime's documented maximum length.
- Validated GC stress and heap-limit environment values. Heap suffix scaling and the physical-memory-derived default are bounded before conversion or multiplication.
- Reworked conservative scan alignment and end checks to avoid overflowing the scan pointer while rounding/alignment and checking whether a complete word remains.
- Replaced small-object secret wiping with a volatile-store wipe primitive; large-object secret reclamation uses the same primitive. Secret pages now keep free-slot indices in collector metadata rather than writing free-list pointers into the secret payload. Newly formatted secret pages are zeroed, and a regression test checks every reclaimed secret free slot remains all-zero.
- Hardened stack-fault classification against pointer-arithmetic overflow and made signal-handler output use fixed lengths. Failure to install the alternate signal stack or handlers now fails closed when stack-guard setup is requested.
- Added unit coverage for checked addition, multiplication, capacity growth and the wipe primitive, in addition to the existing collector stress and secret-reclamation tests.

These changes do **not** make garbage-collection-time erasure prompt or deterministic: they only ensure the wipe is not elided when reclamation actually occurs. They do not add explicit secret destruction, allocation-failure injection, a generational collector, or concurrency support.

CI is the required executable validation for this branch. Until all GCC/Clang Linux/macOS jobs complete successfully, the implementation should be treated as unverified. The exact commit and CI results are recorded in the pull request.
