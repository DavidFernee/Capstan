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

## R2a — Generation-checked internal references (formal model added; CI pending)

A separate Lean module, `verification/lean/NativeHandleReachability.lean`, now models object fields as either scalars or opaque `ObjectHandle` values. The heap is a slot table of typed objects. A descriptor edge exists only when both source and target handles resolve through the same immutable slot-table snapshot and heap domain, and the source field offset is declared reference-bearing by the descriptor.

This closes the specific authority mismatch in the earlier stable-ID abstraction at the model level: a stale, freed, reused, or cross-domain internal handle cannot resolve as a new occupant. Root frames also contain handles and the reachability relation requires each root to resolve. The certificate-conditional theorem is restated over handles.

The CI workflow now explicitly compiles this module and audits its theorem axioms, and scans it for unfinished proofs/local axioms. The GitHub connector has not yet exposed a push-triggered run for the exact new head, so compilation and theorem checks are **pending**, not passed.

This is not yet an end-to-end collector proof. In particular, it does not prove descriptor/layout correspondence (R1), root completeness from compiler liveness and the safepoint ABI (R2), or that a bounded executable marker constructs the certificate (R3). The old `NativeReachability.lean` remains as a stable-ID reference model and must not be cited as stale-edge-safe.

## R3a — Bounded fail-closed reference marker (implementation added; CI pending)

A new module, `verification/lean/NativeBoundedMarker.lean`, adds an executable, list-based FIFO worklist reference algorithm over generation-checked `ObjectHandle` values. Its inputs are an immutable-snapshot liveness predicate, a descriptor-projected edge function, and a descriptor-slot cost function. It does not receive a heap mutation capability.

The marker takes an explicit descriptor-validity predicate and rejects an invalid descriptor before reading its projected edges. This does not prove the predicate matches concrete runtime layouts; that is still R1. The marker enforces six independent limits: root-frame entries scanned, distinct objects, inspected edges, pending worklist entries, cumulative descriptor slots scanned, and total work items processed. It checks the root-frame bound before deduplication, so even duplicate or adversarially large root input is bounded. It deduplicates roots and discovered targets, scans each accepted object once, and rejects stale/unresolvable handles. Exhaustion of any limit is a rejection, never successful termination. An empty pending queue is necessary but not sufficient for success: a separate certificate checker must also accept the candidate marked set.

Every `complete` outcome carries proof that this checker returned true. A sweep-facing `CheckedCertificate` can be extracted only from a complete outcome; the rejection constructor maps definitionally to `none`, with a theorem recording that no certificate is available on rejection. The soundness theorem derives (1) every supplied root is marked, (2) every marked handle resolves, and (3) every descriptor-projected outgoing edge from a marked handle targets another marked handle. A rejected outcome contains only a reason and counters; it exposes no mark certificate. Since the marker is pure and has no heap/table/accounting mutation argument, its rejection path cannot mutate collection state.

Important limits of this increment:

- The list-based implementation is an auditable reference model, not an efficient production data structure. Membership and deduplication are linear; no O(V+E) or worst-case resource guarantee is claimed.
- The edge function is assumed to be the correct descriptor projection for the immutable snapshot, and the descriptor-validity predicate is assumed to reject every malformed or out-of-range descriptor. Descriptor/layout correspondence (R1) is not proved here.
- The liveness predicate is assumed to resolve handles in the same snapshot/domain. Compiler-generated root completeness (R2) is not proved here.
- The checker proves certificate soundness, not that every valid graph within the configured budgets must complete. A traversal defect can therefore cause safe rejection; a separate algorithm-completeness theorem and adversarial tests remain required.
- The model does not yet connect a complete outcome to the production sweep implementation.

The dedicated workflow now compiles this module and audits the theorem axiom dependencies and unfinished-proof scan. The first exact-head run exposed that the output directory was not created before Lean's `-o` invocation; the workflow now creates it. The current exact-head CI is pending, so no compilation or theorem-check success is claimed yet.


### R3b — Adversarial reference regressions and accounting boundary

The bounded-marker module now includes kernel-reduced Lean examples for exact-limit success, root-limit rejection before handle resolution, stale-root rejection, invalid-descriptor rejection, total-work exhaustion, self-cycles, edge-limit exhaustion, duplicate-edge accounting/deduplication, descriptor-cost exact/over-limit cases, and worklist-growth rejection. These examples test the reference function's specified outcomes; exact-head CI compilation is still required before treating them as passing.

A critical resource-accounting limitation is now explicit: the current API receives roots and each object's outgoing edges as already-materialised List values. It calls roots.length and obtains referenceEdges handle before checking the corresponding logical budget. Its list folds, membership checks, concatenations, and temporary lists also allocate/work outside the six logical counters. Therefore these counters do not bound the memory or CPU required to construct or traverse those input lists, and the model cannot by itself prevent an oversized root/edge list from exhausting resources before rejection. It is a fail-closed logical reference model, not an implementation-level resource bound.

The production refinement must replace eager lists with bounded views over validated immutable storage: check root-frame extent before iterating; validate descriptor extent and reserve bounded collector storage before scanning; expose edges through an indexed/streaming cursor that checks and charges each slot before reading/admitting it; use preallocated bounded worklist/visited storage; and account for every probe, copy, and temporary byte. The implementation must not allocate a full outgoing-edge list as an intermediate. Its cost model must include the actual worst-case operations of the chosen data structures, including collision/probe behaviour. A new Lean interface and refinement theorem must connect those operations to the logical graph model before R3 can be considered complete.


### R3c — Certificate checking and admission must also be bounded

Further inspection of the current reference function identifies additional work outside its counters:

- The terminal `certificateCheck` traverses the full root list, marked list, and every projected outgoing-edge list. Its work is not charged to `maxWork`, `maxEdges`, or any separate validation budget.
- Root deduplication constructs a new list before the worklist bound is checked.
- For each object, the outgoing-edge list is materialised before the edge limit is checked.
- Fresh-target construction and pending-list concatenation happen before the pending-worklist bound is checked.
- List membership, append, length, and certificate validation have costs not represented by the logical counters.
- A rejected marker is pure, but purity alone does not imply bounded resource consumption.

Accordingly, the current six counters are **semantic admission limits on the abstract traversal**, not a bound on total marker execution. They must not be described as a hard CPU or memory bound.

The production design must make resource admission precede the corresponding work:

1. Receive root and descriptor storage as immutable bounded spans with validated extents. Reject over-limit extents before iteration.
2. Reserve the maximum permitted collector metadata and worklist capacity before scanning; reservation failure returns without touching heap state.
3. Use an indexed/streaming edge cursor. Charge and validate each descriptor slot before reading its contents; do not materialise an outgoing-edge list.
4. Use a preallocated queue and visited index. Check capacity before enqueue and account for every probe, comparison, copy, and write.
5. Validate the resulting certificate using the same bounded storage and an explicit validation budget, or derive the certificate theorem from the traversal invariant so that a second unmetered graph walk is unnecessary.
6. Include initialization, clearing, cancellation, and failure cleanup in the resource ledger. A failure must not trigger an unbounded fallback or allocate additional memory.

The formal contract should expose operation-level transitions (read root slot, resolve handle, inspect descriptor slot, read edge, probe visited index, enqueue, dequeue, publish certificate) and a monotonic resource ledger. The implementation proof must show each transition is admitted only when its exact resource cost fits, and that the complete marker's total cost is bounded by the configured limits. A data structure with expected constant-time hashing is insufficient unless adversarial probe cost is separately bounded; a deterministic bounded structure or an explicit probe budget is required.

Until this contract is implemented and refined, R3 remains an executable logical reference model only, and its counters must not be used as a claim of total CPU or memory boundedness.
