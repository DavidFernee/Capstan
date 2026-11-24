# Capstan Runtime Memory and Lifetime Model

**Status:** normative v0.6 design baseline; implementation conformance is explicitly qualified below  
**Owner:** Runtime  
**Last reviewed:** 2026-11-24

This document defines the intended observable memory and lifetime contract of the current runtime, records the implementation model that contract is based on, and separates established behaviour from properties that still need implementation work or external assumptions. It does not claim that the C runtime is formally verified.

## 1. Scope and terminology

The current runtime uses a non-moving, conservative, mark-and-sweep collector implemented in `runtime/capstan_gc.h`. Runtime values and collection operations are implemented in `runtime/capstan_rt.h`.

- **Managed allocation:** storage obtained through `cap_gc_alloc`, including the pointer-bearing, atomic and secret allocation kinds.
- **Root:** a location or machine-state word from which the collector begins reachability discovery.
- **Live object:** a managed allocation reached by the collector's marking procedure during a collection.
- **Conservative retention:** an allocation retained because a machine word happens to look like a pointer into it, even if the program does not intend that word to be a reference.
- **Reclamation:** returning an unreachable allocation slot or large allocation to the allocator/operating system. Reclamation is not the same as deterministic destruction.
- **Heap accounting:** the collector's `cap_gc.heap` counter. It is not process RSS and does not include every allocation made by the process.

The collector is non-moving: it does not relocate a live allocation. A live object's address therefore remains stable across collections in the current implementation.

## 2. Allocation kinds

The allocator has three kinds. The kind is selected by the runtime allocation entry point and is metadata for the collector, not a source-level ownership type.

| Kind | Runtime entry point | Scanned for pointers? | Reclamation behaviour |
|---|---|---|---|
| Pointer-bearing | `cap_alloc` / `cap_gc_alloc(n, 0)` | Yes | Reusable slot or large allocation is reclaimed after an unmarked collection |
| Pointer-free / atomic | `cap_alloc_atomic` / `cap_gc_alloc(n, 1)` | No | Reclaimed after an unmarked collection |
| Secret | `cap_alloc_secret` / `cap_gc_alloc(n, 2)` | No | A wipe is attempted during sweep before the storage is reused or released |

The collector uses 64 KiB pages for small allocations (up to 2 KiB), with one size class and allocation kind per page. Larger allocations are allocated separately and represented in a sorted large-object table.

Strings and hash-index storage are atomic: their bytes are not interpreted as references. Pointer-bearing structures, lists and maps use traced allocations. Secret allocations are pointer-free.

The collector's allocation kind must not be confused with a source-level confidentiality label. Copying secret bytes into an ordinary string, stack buffer, file, environment, register, or foreign API does not cause those copies to inherit the secret allocation kind. The declared `CAP_MAX_LEN` is not yet enforced at the central allocator entry point on current main; PR #98 adds that central check together with checked accounting.

## 3. Roots and reachability

The current root set consists of:

1. Global locations explicitly registered through `cap_gc_root`.
2. The current thread's machine stack, scanned conservatively between a local stack marker and the stack top discovered during initialization.
3. Register values spilled into a `jmp_buf` during collection.

The collector scans pointer-bearing allocations conservatively. It supports interior pointers: a candidate address inside an allocated object can retain that object. It does not move live objects.

### Consequences

- A false positive is possible: an integer, stale stack word, or unrelated bit pattern may resemble a heap address and retain an allocation.
- A false negative must not occur for a valid reference represented in a scanned root or scanned pointer-bearing object under the supported ABI and stack assumptions. This is a central correctness obligation, not something established merely by ordinary unit tests.
- The collector scans the allocated object storage, not the logical `len` of a list or map. A vacated pointer-bearing slot can therefore remain a root unless the runtime clears it. Collection-slot hygiene is a separate required runtime fix; until it is integrated, logical removal does not imply loss of reachability.
- A registered root is an address of a root slot, not a copied value. The slot must remain valid for as long as it is registered. The current interface has no corresponding unregister operation; generated registrations are expected to refer to static/global storage.

The root set is conservative and implementation/ABI-dependent. It is not a language-level proof of exact reachability.

## 4. Object lifetime and reference validity

The current lifetime rule is reachability-based:

1. Allocation creates a managed object.
2. The object remains allocated while a collection can discover it from the root set or from another marked pointer-bearing object.
3. An unreachable object may be reclaimed at a later collection.
4. A reference to reclaimed storage is invalid. The runtime does not provide a source-level `free` operation or a general-purpose weak-reference guarantee.

Because collection is conservative, an unreachable object may be retained for an unbounded number of collections by false roots. The runtime therefore provides no upper bound on the time between logical unreachability and physical reclamation.

The collector is non-moving, so references to live allocations do not need relocation or updating. This does not make references valid after reclamation.

### Explicit resource lifetime

File descriptors, sockets, locks, processes, transactions and other operating-system resources must not rely on garbage collection for timely release. Such resources require explicit, deterministic lifecycle operations with defined success and failure behaviour.

Secrets that require deterministic destruction likewise require an explicit destruction/zeroisation abstraction. The current collector's secret kind is a best-effort reclamation mechanism, not a deterministic secret-lifetime guarantee.

## 5. Secret-memory semantics

The secret allocation kind is intended to reduce residual secret data in reclaimed managed storage. The collector attempts to wipe unreachable secret allocations during sweep. Large secret allocations use a volatile byte-wise wipe before the underlying allocation is freed; small secret slots are cleared before being returned to their page's free list.

This behaviour has important limits:

- Wiping happens only when a collection runs and only after the collector decides the allocation is unreachable.
- Conservative false roots and stale pointer-bearing slots can delay reclamation.
- A wipe of one allocation does not erase copies in registers, stack slots, compiler temporaries, ordinary allocations, kernel buffers, files, swap, crash dumps, snapshots, or device caches.
- The operating system and hardware determine whether physical media and backing stores are actually overwritten.
- A collection-time wipe does not establish a deterministic destruction deadline.
- A non-elidable wipe primitive and an explicit ownership/invalidation API are required for a stronger deterministic contract.

Accordingly, the runtime must not claim that garbage collection guarantees prompt or complete secret destruction. Tests can establish that a particular implementation path wrote zeros to a particular mapping before release; they cannot establish erasure of all copies in the system.

## 6. Resource limits and failure behaviour

The collector exposes `CAPSTAN_MAX_HEAP`; absent an override, the current implementation derives a limit from physical memory. The value is capped by the runtime's declared maximum-length constant. The configured limit is a limit on collector-accounted managed heap, not a process-wide memory budget.

The following are outside that counter or are only partially represented by it:

- Collector metadata allocated through `calloc` (page records, page tables, roots, mark stack and large-object records).
- C runtime, compiler-generated code and third-party library allocations.
- Native thread stacks, alternate signal stack and other process stacks.
- Memory-mapped regions and operating-system bookkeeping.
- File buffers and external library allocations.
- Allocator fragmentation, virtual address reservations and physical residency details.

A per-object or per-buffer length limit is not a process-wide RSS limit.

The current failure model is fail-stop:

- Runtime invariant violations reported through `cap_panic` terminate the program with status 101 (or use the test-only longjmp path).
- Collector metadata or backing-allocation exhaustion reported through `cap_gc_oom` terminates the process with status 102.
- The current allocator does not promise recoverable out-of-memory errors or caller-visible rollback.

A process-fatal failure does not establish recoverable failure atomicity. If recoverable allocation is introduced later, every multi-allocation operation must specify its commit point and rollback guarantee.

### Accounting invariant

The intended accounting invariant is:

```
cap_gc.heap =
    bytes of collector-managed page backing currently retained
  + sizes of currently registered large allocations
```

The exact definition of “retained” must track successful OS release/recommit operations. Collector metadata is excluded. The current mainline's page-release path does not check the return value of `madvise` before marking a page released and decrementing `cap_gc.heap`; this is an outstanding correctness issue addressed separately in the GC safety workstream. Consequently, the counter is not yet a fully reliable measurement of resident managed backing on every OS path.

The current mainline also contains unchecked arithmetic in allocator accounting and metadata capacity growth, and its default physical-memory limit calculation can overflow on extreme platform values. The central allocator does not yet enforce `CAP_MAX_LEN` for every direct allocation. The separate allocator-hardening workstream (PR #98) adds checked arithmetic, strict heap-limit parsing, a bounded physical-memory calculation and bounded metadata growth; until that change is integrated and validated, the corresponding stronger invariants are proposed requirements, not current guarantees. Large-object sweep also decrements `cap_gc.heap` without an explicit underflow check on current main.

## 7. Synchronisation and threads

The current collector has no stop-the-world protocol, per-thread root registration, thread-local allocation protocol, lock discipline or concurrent mark/sweep protocol. Its mutable global collector state is not synchronised.

The use of pthread APIs during initialization to discover the current thread's stack bounds does not constitute support for multiple application threads.

**Supported execution assumption:** one application thread performs managed allocation and collection. Programs must not concurrently enter the runtime from multiple threads. A future multithreaded runtime requires, at minimum:

- explicit registration and deregistration of every managed thread;
- a precise definition of stack and register roots for each thread;
- a safepoint/stop-the-world protocol or a separately specified concurrent algorithm;
- synchronization of allocator, page-table, mark-stack and root metadata;
- a memory-ordering model for pointer publication and write barriers;
- tests for thread creation, exit, blocked threads, signals and collection races.

Concurrency is intentionally not introduced as part of v0.6 hardening.

## 8. Runtime invariants

The following invariants are the basis for implementation checks and future proofs.

| ID | Invariant | Current evidence / status |
|---|---|---|
| MEM-01 | Every small object belongs to exactly one page, size class and allocation kind. | Enforced by allocator structure; needs heap-integrity verification |
| MEM-02 | A small slot is allocated iff its page allocation metadata marks it allocated. | Collector invariant; stress tests exist, exhaustive checker required |
| MEM-03 | A free slot appears exactly once in the matching free list and is not marked live. | Collector invariant; dedicated heap-integrity checker required |
| MEM-04 | A page-table entry maps a page number to exactly one page record; table capacity is a power of two and probing terminates. | Current implementation uses open addressing; corrupt-table termination and capacity hardening are in progress |
| MEM-05 | The large-object table is sorted by base address and contains each live large allocation exactly once. | Used by binary-search marking; requires invariant checker |
| MEM-06 | Metadata capacity and byte-size calculations do not wrap. | Not guaranteed on current main; PR #98 hardens the arithmetic |
| MEM-07 | Heap accounting changes exactly once for each successful page backing acquisition/release and large-object allocation/free. | Not fully established; OS release return handling and exact decrement tests remain outstanding |
| MEM-08 | Every live pointer-bearing object reachable from a supported root is marked before sweep. | Requires collector proof under explicit ABI/root assumptions and adversarial tests |
| MEM-09 | Atomic allocations are never scanned as pointer-bearing objects. | Structural allocator property; testable |
| MEM-10 | Secret wiping occurs before reclaimed storage is made available for reuse or returned to the OS. | Intended ordering; needs non-elidable wipe review and direct path-specific tests |
| MEM-11 | No concurrent runtime entry occurs under the v0.6 execution model. | External program/runtime-use assumption; not internally enforced |
| MEM-12 | A failed allocation does not return a partially initialized object to the caller. | Current failure is process-fatal; recoverable failure atomicity is not promised |

## 9. Assurance boundaries

### Suitable for formal specification and proof

- Checked integer addition, multiplication and capacity-growth helpers.
- The page/slot state machine: allocated, marked, free, spare and released.
- Correctness of mark-stack push/pop and bounded page-table probing.
- Large-object table ordering and range membership.
- The mark/sweep preservation theorem, conditional on a complete root set and correct scanning semantics.
- The allocator accounting transition system, conditional on successful OS operations being reported accurately.

### Requires implementation testing

- Collector behaviour under allocation churn and collection at every allocation boundary.
- Preservation of reachable objects through nested structures and interior pointers.
- Reclamation and reuse of dead slots/pages without corrupting live allocations.
- Root-registration and stack-scanning edge cases across supported compilers and optimisation levels.
- Failure injection for metadata, object allocation, page allocation, secret mapping and OS release.
- Secret wipe ordering and exact accounting deltas.
- ASan/UBSan, fuzzing, mutation testing and platform CI.

### Depends on external behaviour or assumptions

- Stack layout, register spill behaviour, ABI and compiler treatment of conservative roots.
- Correctness and semantics of `mmap`, `madvise`, `munmap`, `posix_memalign`, `calloc`, `free`, `pthread` and signal APIs.
- OS memory overcommit, page residency, swap, snapshots and crash-dump policy.
- Hardware and storage-device behaviour relevant to physical erasure.
- The single-threaded application-use assumption.

## 10. Verification programme

The runtime assurance programme should proceed in this order:

1. **Executable invariants:** add a debug heap verifier that walks pages, allocation/mark bitmaps, free lists, spare lists, page-table entries, large-object records and accounting after each collection.
2. **Deterministic failure injection:** inject failures at each metadata allocation, object allocation, secret mapping, page allocation and OS release boundary. Verify the documented fail-stop or rollback behaviour.
3. **Property-based tests:** generate allocation/free-by-reachability sequences, pointer graphs, list/map mutations and collection schedules; compare collector retention with a simple abstract reachability model, allowing conservative false positives but never false negatives.
4. **Stress and fuzzing:** force collection on every allocation; vary object sizes around every size-class boundary; churn large objects; mutate roots and interior pointers; run long-duration heap-integrity checks.
5. **Sanitisers:** run ASan and UBSan on GCC/Clang and supported platforms, retaining all failures as regressions.
6. **Formal model:** specify allocation, root discovery, marking, sweep, reuse, page release and accounting as state transitions. Prove that sweep never reclaims a marked object, that each free slot is represented exactly once, and that accounting transitions preserve the stated equation when OS calls succeed.
7. **C-free migration:** express the allocator/collector interface as a small capability-oriented runtime contract. Keep OS allocation, page protection and release behind explicit platform primitives whose preconditions, postconditions and failure results are specified.

A proof of the abstract collector is not a proof of the C implementation. Refinement obligations must connect each implementation transition to the abstract state, and the compiler/ABI/OS assumptions must remain visible in the assurance case.

## 11. C-free runtime interface direction

The future runtime should expose a minimal interface rather than C allocation details:

- `allocate(kind, size, alignment) -> Result<Region, AllocationError>`
- `region_read(region, offset, length) -> Result<Bytes, BoundsError>`
- `region_write(region, offset, bytes) -> Result<(), BoundsError>`
- `register_root(root_slot)` / `unregister_root(root_slot)`
- `collect() -> CollectionReport`
- `destroy_secret(secret_region) -> Result<(), DestructionError>`
- explicit external-resource operations with `close`/abort semantics.

These are design directions, not current public APIs. The eventual Capstan implementation must make invalid region access, invalid lifetime transitions and double destruction unrepresentable or a checked runtime failure. The platform layer remains a small, explicitly trusted boundary.

---

**Assurance statement:** v0.6 currently provides a non-moving conservative collector with three allocation kinds and fail-stop allocation failure. It does not provide deterministic object destruction, deterministic secret destruction, process-wide memory limits, recoverable OOM, or multithreaded collection safety. Those guarantees must not be implied by the presence of garbage collection or by passing the current test suite.
