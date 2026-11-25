# Native reachability and collector refinement

Status: **formal abstraction / research gate**, not a concrete collector implementation.

This note records the refinement boundary for `verification/lean/NativeReachability.lean`.

## What the model establishes

The model has four linked elements:

1. A root entry contains a generation-checked `ObjectHandle` and a proof that resolving it in the stated heap domain yields the recorded object ID. A root frame cannot be populated by an unchecked integer in this model.
2. Each heap object has a descriptor ID and fields. A descriptor selects the field offsets that contain references. Scalar fields and fields not selected by the descriptor do not create graph edges.
3. `DescriptorEdge` is the graph relation induced by the descriptor-selected reference fields.
4. A mark certificate is accepted only if it includes every root and is closed under every descriptor edge from every marked object. Sweeping outside this set therefore cannot reclaim a reachable object.

The Lean theorems establish:
- all objects reachable from the explicit root snapshot occur in any valid mark certificate;
- sweep preserves each such object;
- sweep cannot create an object where the old heap had none;
- every root-frame entry resolves through its exact handle/domain/table snapshot.

The certificate theorem is deliberately stronger than testing a particular trace: it is parametric over heaps, descriptors, roots and object identifiers.

## What the model does not establish

It does **not** yet prove that an executable marking algorithm can construct a valid certificate. In particular it does not yet establish:
- descriptor soundness/completeness against compiler-emitted object layouts;
- that every live reference in registers, stack slots, globals, temporary expression state and suspended calls is represented in a root frame;
- that root frames are updated correctly across calls, returns, exceptions/traps and allocation safepoints;
- that the worklist algorithm terminates within a finite resource budget and visits every reachable object;
- that descriptor offsets are in bounds, non-overlapping where required, and have the correct reference/scalar kind;
- that no untracked native pointer survives a safepoint;
- that collection and allocation compose atomically with handle publication and budget accounting;
- concurrent mutation or concurrent collection semantics. The first implementation target remains stop-the-world, single-mutator collection unless the language/runtime contract requires otherwise.

A proof-carrying mark set is not a substitute for verifying the marker. It separates the sweep-safety theorem from the algorithm/refinement proof so that neither is silently assumed.

## Required next refinements

### R1 — Concrete descriptor semantics

Define a closed descriptor format generated from checked type/layout metadata. Prove that decoding it yields exactly the reference-bearing fields of each runtime object layout. Reject malformed descriptors before allocation or publication. The proof must cover nested structs, list/map backing storage, optional values, tagged unions and any object header metadata.

### R2 — Explicit root-frame ABI

Define root frames for:
- native function parameters and live locals;
- compiler temporaries that cross allocation-capable operations;
- caller frames during nested calls;
- globals and module state;
- exception/trap state if it can retain references;
- runtime-owned worklists and collector temporaries.

The compiler must emit root maps from liveness analysis or use an explicit shadow-root stack. A conservative scan of native stack words is not the correctness argument. Root handles remain generation checked; no raw object address may outlive a protected borrow or safepoint.

### R3 — Executable marker

Specify a bounded worklist algorithm over object IDs/handles:
- seed from all validated root frames;
- resolve each handle in its domain and generation;
- visit each object at most once per collection epoch;
- scan only descriptor-selected reference slots;
- reject invalid descriptor/handle state rather than silently skipping it;
- account separately for worklist capacity, visited metadata and edge-scan work;
- fail before sweep if any bound is exceeded.

The marker must produce a certificate whose root-inclusion and edge-closure properties are proved. A failed marking pass must not sweep or mutate the live heap.

### R4 — Sweep and allocation composition

Compose the mark/sweep transition with the M1 lifecycle state:
- clear dead object reference slots before slot reuse;
- release only the exact current generation;
- retire exhausted generations rather than wrap;
- preserve all objects reachable from the root snapshot;
- leave the heap and accounting unchanged if mark validation or resource admission fails;
- publish newly allocated objects only after full initialization and metadata reservation.

### R5 — Adversarial and differential evidence

Build traces for cyclic graphs, self-cycles, shared children, deep chains, wide graphs, stale roots, cross-domain handles, descriptor corruption, removed/replaced edges, allocation during nested calls, root-frame omissions, worklist exhaustion and generation exhaustion. Compare the executable marker/sweeper with an independent graph-reachability oracle. Tests are evidence for the implementation, not a replacement for R1–R4 proofs.

## Non-negotiable safety invariant

For every accepted collection transition from a well-formed heap and complete explicit root snapshot:

`Reachable(heap, roots, object) -> heapAfter(object) = heap(object)`.

Additionally, the transition must not create objects, resurrect retired handles, wrap generations, or mutate the heap if root validation, descriptor validation, or work-budget admission fails.

## Implementation sequencing

Do not implement or integrate the production collector until R1 and R2 are expressible in the supported Capstan subset and the R3 marker algorithm has a bounded, testable contract. Keep the current C collector as a differential oracle during migration, not as a production dependency. Do not remove it until the C-Free implementation passes the native corpus, resource limits, adversarial traces and formal refinement gates.


## R3 design refinement — finite worklist and reference authority

Before proving an executable marker, the current graph abstraction needs one important tightening: FieldValue.reference currently stores a bare Nat object ID. Root entries are generation-checked, but internal object edges are not. If object IDs are recycled independently of the slot-generation table, an old field could accidentally name a new occupant. The current theorem is therefore a reachability theorem over an abstract, stable-ID heap; it is not yet a proof against stale internal references.

The concrete refinement must make every reference-bearing field an opaque, domain-bound, generation-checked handle (or prove that object IDs are globally unique and never reused for the lifetime of any extant edge). The preferred design is the former, so stale-edge rejection follows the same authority rule as root resolution. The heap lookup relation must resolve each edge through the same immutable collection snapshot used for roots. A dangling or stale internal edge is a heap-integrity failure, not an edge to silently ignore.

### Bounded marker contract

Use a deterministic FIFO worklist and a finite visited set. Its input is an immutable collection snapshot, validated descriptor table, validated root-frame snapshot, and explicit limits:

- maxObjects: maximum number of distinct objects visited;
- maxEdges: maximum number of descriptor-selected reference slots inspected;
- maxWorklist: maximum pending entries;
- maxDescriptorSlots: maximum slots scanned for one object (or a validated global descriptor-size bound).

The marker returns either Complete certificate counters or Rejected reason counters. It has no heap/table mutation capability. Sweep accepts only Complete; Rejected is a hard stop and leaves the collection snapshot and all accounting unchanged.

For a simple auditable implementation, bound execution with a fuel parameter derived from the configured limits, but do not use fuel exhaustion as successful completion. The success constructor must require an empty worklist. If fuel reaches zero with pending work, return WorkLimitExceeded and do not produce a certificate.

### Marker loop invariants

At every iteration maintain:

1. visited contains only successfully resolved objects from the snapshot.
2. Every root has been validated and is either visited or pending.
3. Every descriptor edge of each visited object has been inspected exactly once (or has an explicit per-object scan-complete state).
4. Every valid target discovered from an inspected edge is either visited or pending.
5. No object is enqueued twice; this bounds worklist growth by the number of distinct reachable objects.
6. Every pending handle resolves in the same snapshot and domain; no raw address or naked recyclable object ID enters the queue.
7. Counters never exceed their configured maxima; each increment is checked before the corresponding work is admitted.

On successful empty-worklist termination, invariants 2–4 imply root inclusion and edge closure, so the resulting visited set constructs the existing MarkCertificate. This is the central R3 theorem to prove. A second theorem must show that any rejection path returns no certificate and cannot invoke sweep.

### Cost and complexity target

With a hash-indexed visited set and FIFO queue, expected time is O(V + E) and auxiliary space O(V), where V is the number of visited objects and E is the number of descriptor-selected reference slots inspected. Those are algorithmic expectations, not worst-case guarantees for a chosen hash table. The implementation must either use a deterministic bounded-cost structure or account for adversarial collision cost explicitly. The formal resource counters should measure actual slot/edge operations rather than rely solely on asymptotic notation.

### R3 acceptance tests

In addition to the R5 graph corpus, require explicit checks that:

- a stale generation in an object field rejects the entire mark pass;
- a cross-domain edge rejects the entire mark pass;
- an invalid descriptor ID or out-of-range reference offset rejects before sweep;
- duplicate edges do not cause duplicate visits;
- a cycle terminates without recursion or unbounded stack growth;
- each configured counter can be exhausted independently;
- the exact-limit successful case completes, while one-less-than-required fails;
- rejection leaves heap, slot table, generation state and resource ledger byte-for-byte/logically unchanged.

Until internal edges are upgraded from naked IDs and the marker-construction theorem is checked in Lean, the current M2 result remains deliberately limited to the abstract stable-ID graph and certificate-conditional sweep safety.
