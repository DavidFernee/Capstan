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
