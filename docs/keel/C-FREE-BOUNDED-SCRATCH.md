# C-Free bounded scratch memory: design contract

**Status:** proposed language/runtime contract; not implemented and not a proof.  
**Owners:** Capstan compiler/runtime, with Keel as the first demanding client.  
**Motivation:** Keel KR-14/KR-16 require exact peak-memory admission for topology algorithms; the current growable `List<T>` and sort interface cannot establish that bound.  
**Related:** [C-Free execution](../architecture/C-FREE-EXECUTION.md), [CCAM](../architecture/CCAM.md), [runtime memory model](../assurance/RUNTIME-MEMORY-MODEL.md), [mesh topology assurance](MESH-TOPOLOGY-ASSURANCE.md), [mesh ownership and BVH](MESH-OWNERSHIP-AND-BVH.md).

## 1. Decision sought

Introduce a language-level, bounded scratch-memory capability for temporary algorithm workspaces. It must be usable by ordinary Capstan code and implemented in the eventual C-Free runtime, not as a Keel-specific wrapper over the existing C runtime.

The capability provides:

- an explicit byte budget and an exact charged-byte counter;
- checked, aligned, non-growing reservations;
- a scoped lifetime with explicit reset/release semantics;
- typed, bounds-checked views over reserved storage;
- recoverable exhaustion before any operation mutates caller-visible state;
- deterministic algorithms whose auxiliary storage is either zero or explicitly reserved;
- test hooks for deterministic allocation failure and accounting inspection.

This document does not prescribe source syntax, concrete object representation, garbage collector integration, or a native ABI. Those decisions belong to the CCAM/runtime design and must be resolved before implementation.

## 2. Non-goals

This is not:
- a replacement general-purpose heap or garbage collector;
- an excuse to expose raw pointers or unchecked memory access to Capstan programs;
- an implicit promise that current `List<T>` operations become bounded;
- a persistent allocator for published mesh assets;
- a concurrency primitive or cross-thread shared arena;
- a claim that a language-level budget equals process RSS or physical memory use.

Scratch memory is temporary algorithm workspace. Persistent owned buffers and resource-accounted heap objects require separate lifetime and ownership contracts.

## 3. Abstract model

A scratch region is an owned capability with state:

`Region = (capacity_bytes, used_bytes, generation, state)`

where state is either `open` or `closed`, and:

`0 <= used_bytes <= capacity_bytes`

The region is created with a fixed capacity. It never grows. Its storage is private to the capability and cannot be accessed through a raw address in the source language.

A successful reservation returns a view:

`View<T> = (region identity, generation, byte offset, element count)`

The view is valid only while:
- the region remains open;
- its generation matches the region generation;
- its byte interval lies entirely inside the reserved prefix;
- the requested access is within the view's element range.

The source type system/runtime must prevent a view from escaping the region's lifetime. If static lifetime checking is not yet available, the runtime must perform generation and state checks on every view operation. A runtime check is a safe transitional implementation, not equivalent to a compile-time borrow proof.

The region is exclusive during construction and use. Sharing across threads is forbidden until a separate synchronization and memory-model contract exists.

## 4. Byte-exact reservation contract

### 4.1 Inputs

A reservation request contains:
- element layout (size and alignment), known from the compiler's closed type-layout rules;
- requested element count;
- an optional purpose tag for diagnostics and accounting.

No caller-supplied size or alignment may override the compiler's layout for a typed view.

### 4.2 Checked calculation

For element size (s), alignment (a), count (n), and current cursor (u), compute:

1. Require (s > 0), (a > 0), and (a) to be a supported power of two.
2. Check (n 	imes s) for overflow.
3. Compute aligned start (p = align_up(u,a)) using checked addition.
4. Check (p + n 	imes s) for overflow.
5. Require the end offset to be no greater than capacity.
6. Only after all checks succeed, commit the cursor to the end offset and return the view.

All arithmetic is over the specified unsigned byte-count domain, not host signed overflow. The exact maximum capacity and offset width are an explicit implementation decision; values outside that domain return a typed range error.

Alignment padding is charged. The accounting invariant is:

`used_bytes = end offset of the last successful reservation`

and therefore includes all alignment gaps. No reservation may be partially committed.

### 4.3 Failure atomicity

A failed reservation:
- leaves `used_bytes` unchanged;
- returns a stable typed error (invalid layout, arithmetic overflow, or budget exhausted);
- does not return a partially usable view;
- does not mutate any client data.

A failed multi-reservation plan must leave the region unchanged. Clients should calculate and reserve the complete workspace before beginning an algorithm's mutation phase.

### 4.4 Accounting scope

The region's charged bytes include its full backing capacity and all in-region alignment padding. The backing allocation's fixed header, page rounding, allocator metadata and external fragmentation are not silently represented as payload bytes. They must be reported separately by the runtime's physical-allocation layer if a stronger process-memory claim is required.

For algorithm admission, the caller supplies the region capacity. The runtime must either successfully create exactly that logical capacity or return an allocation error before exposing the region. A runtime that cannot honour this contract must not claim a hard scratch bound.

## 5. Lifetime and access rules

1. A region has one owner and one active generation.
2. Views are borrowed capabilities; they do not own or extend the region lifetime.
3. Closing a region invalidates every view.
4. Reset is permitted only when no view can be used afterward. Reset increments the generation, invalidating stale views.
5. Nested scopes, if supported, use explicit checkpoints. Rewind is legal only to a checkpoint from the same open region and generation.
6. A view cannot be stored in persistent state, returned beyond the region scope, captured by a longer-lived closure, or published to another task.
7. No reference-bearing element layout may be admitted until the collector/rooting interaction is specified. The initial scratch profile should be restricted to non-reference scalar/record layouts.
8. Secret-bearing scratch requires a distinct wiping contract and is excluded from the initial profile. Ordinary reset is not secure erasure.

The first implementation should prefer one region per synchronous algorithm invocation. Reentrancy uses a separately reserved child region or a separately bounded invocation; it must not silently share mutable cursor state.

## 6. Mutation protocol

Algorithms follow a reserve-then-execute discipline:

1. Validate input counts and domains without proportional allocation.
2. Calculate every workspace size with checked arithmetic.
3. Reserve all required regions/views.
4. Initialise workspace completely.
5. Execute the algorithm, with all output mutation staged privately where failure remains possible.
6. Commit caller-visible output only after successful completion.
7. Close/reset the region on every exit path.

If an algorithm can fail after partially changing output, it must either:
- stage output in scratch and commit atomically; or
- define and prove a rollback protocol.

Budget exhaustion must never be discovered halfway through a mutation sequence.

## 7. Deterministic sorting contract

Sorting is a foundational operation because Keel's incidence algorithms depend on deterministic sort-and-scan.

### 7.1 Comparator

A sort accepts a total-order comparator over a closed element type. The comparator must:
- be deterministic and side-effect-free;
- define a total order (including tie-breaking);
- never access mutable external state;
- not allocate;
- not fail or trap for valid elements.

If a comparator cannot meet this contract, it is not eligible for the bounded sorting primitive.

### 7.2 Initial algorithm candidates

Two implementations should be compared:

**A. In-place heapsort**
- (O(n log n)) worst-case comparisons;
- (O(1)) auxiliary element storage;
- deterministic control flow for a fixed input and comparator;
- not stable, so callers requiring stable results must include a unique deterministic tie-break key.

This is the preferred first implementation because it avoids hidden temporary allocation entirely.

**B. Bottom-up mergesort with caller-owned scratch**
- (O(n log n)) worst-case comparisons;
- (O(n)) caller-reserved auxiliary elements;
- stable when implemented with a specified equal-key rule;
- peak bytes are exactly calculable from the element layout and reserved count.

It is a candidate when stability materially simplifies the proof or downstream representation. Its scratch must be reserved before sorting begins.

Do not recursively implement quicksort as the default: adversarial pivot patterns can violate the desired work bound or consume unbounded call stack unless introspective fallback and explicit stack bounds are proved.

### 7.3 Sort failure and postconditions

The preferred in-place sort has no allocation failure after entry. The caller-owned mergesort may fail only during preflight/reservation, never during its mutation phase.

On success, the output is a permutation of the input and is monotonically nondecreasing under the comparator. Tests must verify both properties independently. For a total comparator with unique tie-break keys, the resulting sequence is fully deterministic regardless of input emission order only when the key itself is canonical; the sort does not make noncanonical inputs canonical.

## 8. Resource budgets and admission

The API distinguishes:
- **capacity budget:** fixed bytes available in the region;
- **charged bytes:** current cursor including alignment;
- **work budget:** algorithm-specific comparisons, visits, or transitions;
- **persistent allocation budget:** outside this abstraction.

A memory bound does not imply a work bound. Every algorithm must preflight or incrementally enforce a separate work limit. If a work limit can be hit after mutation begins, output must be staged or rollback must be specified.

For a multi-region operation, aggregate admission must be atomic: either all requested regions are admitted or none are. The runtime must not report success after reserving only a prefix of the request.

## 9. Initial Keel workspace calculation

The current mesh limits are:
- (T_{max}=131072) triangles;
- at most (3T=393216) vertex-link edges;
- at most (6T=786432) endpoint occurrences.

The compact vertex-link proposal needs (at minimum):
- endpoint records: (6T);
- compact endpoint IDs: (6T), unless written directly into preallocated endpoint slots;
- link-edge endpoint pairs: (3T);
- union-find parent and rank/state: up to (6T);
- canonical duplicate-link-edge keys: (3T);
- per-centre diagnostic accumulators, bounded by the admitted vertex count.

The exact byte expression cannot be finalised until Capstan fixes the in-memory layout and alignment of the chosen record types. That is a compiler/runtime deliverable, not a value to guess in Keel documentation. With a typed region, the client can request each typed view and the runtime can report exact charged offsets. The admission request must include simultaneous live views, not merely the largest individual array.

The in-place heapsort candidate removes an additional (O(n)) merge temporary from the endpoint-record and duplicate-key sorts. If stable sorting is selected instead, its temporary array must be explicitly reserved and included in the same aggregate budget.

## 10. C-Free and CCAM integration requirements

The abstraction must be specified as language/runtime semantics before it is exposed in the standard library.

Required sequence:

1. Define fixed-width byte-count, alignment and overflow semantics in the core language/CCAM memory model.
2. Define region creation, reservation, view access, reset, close and error outcomes in the runtime contract.
3. Extend the reference abstract machine only after its value and memory model can represent the capability without host pointers or host allocation semantics leaking into CCAM.
4. Implement the executable reference semantics in Capstan. Host-language arrays or allocators may be used only by an independent test oracle, not by the implementation.
5. Add a backend-independent conformance corpus.
6. Implement the first native target's storage mechanism behind the same semantics.
7. Establish a refinement argument from source operations through CCAM to the backend representation.

The existing CCAM v0.1 specification has registers and scalar values but no general heap/region operations. Therefore this document does not claim that scratch regions can currently be expressed or executed in CCAM. The CCAM extension is an explicit dependency and must be versioned.

## 11. Formal invariants and proof obligations

For every reachable region state:

- **R1 Bounds:** (0 le used le capacity).
- **R2 Monotonic reservation:** successful reservation never decreases `used`.
- **R3 Failure atomicity:** failed reservation leaves all region state unchanged.
- **R4 Non-overlap:** successful live views have pairwise disjoint byte intervals.
- **R5 Alignment:** each view offset satisfies its layout alignment.
- **R6 Extent:** every view's computed end is within capacity.
- **R7 Lifetime:** closed or stale-generation views cannot be read or written.
- **R8 Isolation:** a region cannot be accessed by a non-owner or concurrent task.
- **R9 Reset:** reset invalidates all pre-reset views and sets `used` to the selected checkpoint.
- **R10 Sort permutation:** sorting preserves the multiset of input elements.
- **R11 Sort order:** adjacent output elements satisfy the comparator order.
- **R12 No hidden allocation:** bounded sort and view operations perform no allocation outside admitted regions.

Proof decomposition:
- arithmetic lemma for multiplication and alignment;
- reservation transition preservation;
- pairwise non-overlap by monotonic cursor allocation;
- stale-view rejection by generation/state check;
- sorting permutation and ordering;
- implementation refinement for each target.

A proof of the abstract transition system does not prove compiler lowering, runtime storage, allocator behaviour or native memory safety. Each layer needs an explicit correspondence argument and executable tests.

## 12. Verification and fault-injection plan

Minimum test families:

- zero elements, one element, exact-capacity fill, one-byte-over, one-element-over;
- every alignment class, padding at capacity boundary, and overflow in multiplication/addition/alignment;
- repeated reservations with interleaved alignments and exact cursor checks;
- failure after a successful prefix in an aggregate plan (must roll back completely);
- stale view after reset, closed-region access, out-of-range index and wrong owner;
- nested checkpoint rewind and invalid checkpoint;
- deterministic failure injection at region backing allocation;
- heapsort empty/singleton/two-element, sorted/reverse/all-equal/adversarial patterns and maximum count;
- comparator-law checks on generated triples (antisymmetry, transitivity, totality);
- sort permutation and order checks against an independent arbitrary-precision oracle;
- mutation tests for off-by-one bounds, omitted padding, wrapped multiplication, stale-generation acceptance and skipped sort elements.

Run the same conformance vectors against the reference semantics and every native target. Record exact commit, target, compiler build, seed, budget and failure point. Keep memory-safety sanitizer results separate from semantic proof claims.

## 13. Security and failure analysis

| Hazard | Required mitigation |
|---|---|
| Integer overflow underestimates allocation | Checked multiplication, alignment and end-offset addition before cursor mutation |
| Hidden growth or temporary allocation | Fixed capacity; no-grow views; bounded sort with zero or caller-reserved scratch |
| Use-after-reset/close | Generation-tagged views and runtime checks until static lifetime enforcement exists |
| Cross-task data race | Single-owner restriction; no sharing until a concurrency contract is implemented |
| Budget bypass through nested calls | Explicit child budgets or shared account with atomic reservation |
| Partial mutation on exhaustion | Reserve-before-mutate and staged commit |
| Reference retention / GC confusion | Initial profile excludes reference-bearing elements |
| False secure-erasure claim | Separate secret region and wipe proof; ordinary reset is not erasure |
| RSS overclaim | Distinguish logical payload budget from allocator metadata, page rounding and physical residency |
| Comparator-induced nondeterminism | Closed, pure, total comparator with canonical tie-break keys |

## 14. Acceptance gates

| Gate | Evidence | Blocks |
|---|---|---|
| SCR-1 | Reviewed byte arithmetic, alignment, state and lifetime semantics | Any public scratch API |
| SCR-2 | CCAM memory/region extension and reference semantics | Claim of executable C-Free scratch |
| SCR-3 | Capstan implementation, backend-independent conformance and deterministic fault injection | Keel production use |
| SCR-4 | Formal invariants plus implementation correspondence evidence | Hard safety/byte-bound claims |
| SCR-5 | Keel vertex-link workspace passes exact maximum-budget and differential tests | Vertex-link production API |
| SCR-6 | Native target implementation with no generated-C/runtime dependency on the strict path | C-Free claim |

No gate is satisfied by this proposal. Existing v0.6 List/sort operations remain unchanged and are not made safe for hard-budget claims by this document.

## 15. Immediate work items

- **SCR-01 (specification):** settle byte-count width, supported alignment set, view lifetime enforcement strategy and error algebra.
- **SCR-02 (CCAM):** propose a versioned region/memory extension with explicit load/store and region lifecycle semantics.
- **SCR-03 (compiler):** define target-independent type layout and expose layout metadata to checked reservation.
- **SCR-04 (runtime):** implement fixed-capacity region creation and accounting behind the CCAM contract.
- **SCR-05 (sort):** implement and compare in-place heapsort with caller-scratch bottom-up mergesort; retain both only if evidence justifies both.
- **SCR-06 (Keel):** turn the compact vertex-link cardinality plan into an exact typed workspace request once layouts are fixed.

The next implementation decision is the CCAM memory model, not a Keel-local allocator API. Keel remains a demanding consumer and acceptance workload.
