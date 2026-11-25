# Native Capstan Garbage Collector

**Status:** implementation programme and normative design target; not an implementation or proof.  
**Owner:** Capstan native-runtime workstream  
**Scope:** replace the C collector and its C-owned metadata/algorithms with a Capstan implementation suitable for the C-free native backend.

## 1. Objective and non-negotiable boundary

The production collector algorithm, allocation metadata, object classification, tracing, sweeping, free-slot management, accounting, diagnostics, tests, fuzzers and verification models are Capstan code. The collector must not call generated C, depend on libc allocation, or rely on a C runtime.

A narrow platform-memory adapter may eventually provide page reservation/commit/decommit and process termination. It is an explicitly documented platform boundary, not a second collector. Its contract must be small enough to implement independently for each native target. The collector must not depend on host stack introspection, `setjmp`, ABI-specific conservative scanning, or compiler-specific register discovery.

This work does not make the current C-backed executable C-free. The old collector remains a compatibility backend until the native collector has passed the migration gates in §12.

## 2. Current baseline and evidence boundary

The current mainline implementation is `runtime/capstan_gc.h`: a single-threaded, non-moving, conservative mark-and-sweep collector. It uses 64 KiB pages, fourteen small-object size classes, allocation/mark bitmaps, large-object records, three allocation kinds (pointer-bearing, atomic, secret), registered globals, a register spill and current-thread stack scanning.

The mainline hardening already includes failure-atomic page-release accounting, out-of-line secret-page free-slot metadata, secret wiping, checked metadata growth, stack-bound validation and strict GC environment parsing. These are valuable behavioural requirements to preserve, not a reason to carry the C implementation forward.

Existing verification is deliberately layered. Arithmetic and selected page-release transitions have abstract-model evidence; allocator slot partition work is present in open PR #309. Those results do not establish concrete collector correctness or implementation refinement. The previous audit also identified root completeness, mark-stack bounds, physical scanning correspondence, metadata allocation failure and concrete representation as separate obligations.

Relevant existing work to reconcile rather than duplicate:
- PR #143: merged runtime lifecycle, secret-page and stack hardening.
- PR #305: merged allocator arithmetic/capacity proof work.
- PR #309: open abstract page/slot and free-list partition proof work.
- PR #255: open native register/object identity and heap mutation model; its own description records that language/compiler/runtime reference-semantics correspondence is outstanding.
- PR #246 and #262: open bounded process-lifetime region heap prototype and model bridge; useful for compiler/bootstrap allocation, but explicitly not a general GC or supported CCAM heap.

## 3. Root model: precise, explicit, compiler-owned

The native collector will not scan arbitrary machine stack words. Conservative scanning is coupled to the host ABI and can retain arbitrary objects; worse, omitting a live register or temporary can reclaim a reachable object. It is not an acceptable foundation for a portable C-free runtime.

The target is a **precise shadow-root stack** with compiler-emitted safepoint maps:

1. Every native function that can reach a GC safepoint has a frame descriptor.
2. At each safepoint, the compiler spills every live managed reference into designated root slots before entering the collector.
3. The frame descriptor identifies exactly which slots contain managed references at that safepoint. Scalar, integer, byte and raw non-managed values are never interpreted as references.
4. A linked shadow-frame chain identifies active frames. Enter/leave operations are explicit and validated; unwind/trap paths restore the previous chain.
5. Runtime helpers that can allocate publish their temporary managed references in registered root slots before the allocation call.
6. Global roots are explicit typed root records, not arbitrary pointer arrays.
7. Closure environments and aggregate fields are traced through verified object-layout descriptors.
8. The compiler/backend must prove that no live reference exists solely in an unreported register or transient location across a safepoint.

A safepoint is a semantic boundary: collection may occur only where the compiler has published a complete root set. Until precise stack maps and reference spill/reload rules are implemented and tested, the collector must not reclaim objects based on an incomplete root set.

### Logical frame-map contract (GC-R0 proposal)

The contract is intentionally stated independently of a physical register/stack ABI. The compiler/backend owners must choose and document the concrete encoding before runtime implementation.

A published frame record must identify:

- a validated frame-layout descriptor and descriptor version;
- the caller/previous-frame link, with an explicit root-chain termination value;
- the active safepoint identifier;
- the frame's root-slot storage extent;
- an immutable map from that safepoint identifier to the exact set of managed-reference slot indices.

The runtime accepts a collection entry only when the active chain is well-formed, bounded by a configured frame limit, contains no repeated frame identity, and every frame's descriptor and safepoint map are recognised. Each listed slot must be in bounds and contain a valid handle for the current heap instance. Unlisted slots are never interpreted as references. Duplicate root slots may be rejected or canonicalised, but cannot change reachability.

The compiler-side proof obligation is stronger than map well-formedness: at every permitted safepoint, every reference live after the safepoint must either be in a listed root slot or be reachable through a listed object field. A reference held only in a register, spill temporary, outgoing argument area, closure environment or helper-local must be included according to its actual lifetime. The lowering must spill before publishing the safepoint and reload from the authoritative root slot after collection; stale pre-collection copies must not be used.

Frame publication and withdrawal are ordered operations. A frame is fully initialised before it becomes reachable from the active chain. Normal return, trap, panic and unwind paths restore the previous chain exactly once. Any allocation-capable helper must publish its own live temporaries before it can trigger collection. If validation fails, collection aborts before sweep and leaves all object allocation states unchanged.

These are semantic acceptance conditions, not a claim that the current native backend already emits such records. The contract does not prescribe raw stack offsets, register numbers, calling convention, frame-pointer use or a particular map encoding; those decisions require a joint compiler/runtime review and target-specific tests.

The initial implementation is single-threaded. No threads, async callbacks, signal-time allocation or concurrent mutation are permitted. A future multi-threaded collector requires per-thread root chains, a stop-the-world/safepoint protocol and synchronization proofs; it is not silently included here.

## 4. Object model and pointer classification

The collector operates on opaque object identities/handles, not forged integers or arbitrary native addresses at the Capstan API boundary. A handle identifies a heap instance, object slot and generation. Validation rejects null where forbidden, foreign-heap handles, stale generations, unallocated slots and descriptor mismatches before mutation. The heap-instance token is itself an allocation-incarnation identity: it must be globally unique for the lifetime of every handle and must never be recycled. Runtime handle construction and decomposition remain private; the public language surface exposes an opaque reference, not user-forgeable token/slot/generation integers. The current logical model assumes token uniqueness and does not yet model heap creation, token allocation or token exhaustion. Its `heap_token` corresponds to the region identity in the existing generational-handle research model.

Each allocated object has an immutable layout descriptor:
- allocation size and alignment;
- pointer-field offsets or a verified repeated-element layout;
- allocation kind: traced, atomic, or secret;
- object type/descriptor identity;
- optional bounded element count and payload extent.

Only descriptor-declared reference fields are traced. Atomic objects are never scanned. Secret objects are pointer-free by construction, wiped before reuse or release, and must not be confused with ordinary atomic allocations. The descriptor itself is trusted compiler/runtime metadata and must be immutable for the object's lifetime.

Interior pointers are not part of the initial managed-reference model. References name object identities, not arbitrary addresses. Any future pinning/FFI interface must define a bounded borrow/pin capability and cannot silently reintroduce conservative interior-pointer recognition.

## 5. Initial collection strategy

The first production-capable collector is **non-moving, precise, stop-the-world mark-and-sweep**, single-threaded. It is intentionally not generational.

A full collection:
1. enters only at a declared safepoint and freezes mutator execution;
2. validates the active shadow-frame chain and global-root records;
3. clears mark state for all allocated objects;
4. seeds a bounded worklist from precise roots;
5. marks each newly discovered object once and visits only descriptor-declared reference fields;
6. rejects invalid internal references as heap corruption; it never treats malformed metadata as a reason to free an object;
7. sweeps unmarked objects, wiping secret payloads before making their slots reusable;
8. reconstructs or validates free-slot ownership and accounting;
9. publishes the completed heap state atomically with respect to resuming the mutator.

The worklist has a hard capacity derived from the maximum object count or is grown through a failure-safe metadata arena. Capacity exhaustion must fail closed before any object is reclaimed. A two-pass mark/sweep or mark-bit plus bounded scan fallback may be evaluated, but no algorithm may silently drop pending work.

No finalisers, resurrection, weak references, ephemerons, moving/compacting, generational collection, concurrent collection or user-visible manual free in the initial profile. Generation tags on handles are still mandatory for stale-reference rejection; they are not generational collection.

## 6. Allocation and metadata

The collector owns a bounded heap quota and a separate bounded metadata quota. These are different accounting domains. Heap payload accounting must not be described as a process RSS bound.

Metadata must not be allocated recursively through the managed heap. The initial design reserves a dedicated metadata arena at runtime initialisation; its capacity and failure behaviour are explicit. Arena exhaustion is a terminal, diagnosable failure until a separately verified growth strategy exists.

Allocation is failure-atomic:
- validate descriptor, size, alignment, kind and quota before mutating allocator state;
- reserve a unique slot and update exactly one ownership structure;
- zero-initialise objects where the language contract requires it;
- publish the new handle only after all metadata and payload state is consistent;
- on failure, leave no partially allocated or multiply-owned slot.

The initial allocator may use size-class pages and separate large-object extents, but its page/slot state machine must have exactly-one-owner invariants. Reuse is allowed only after the object is unreachable under the precise root model and secret wiping (when applicable) has completed.

## 7. Page provider boundary

The collector algorithm is platform-independent Capstan code. A small platform adapter may expose only operations such as:
- reserve a page-aligned virtual range;
- commit/provision backing for a reserved range;
- decommit/discard backing while retaining reservation, if supported;
- release a reservation;
- report the exact success/failure result.

The adapter must not maintain object graphs, free lists, mark bits, roots or heap policy. Every OS operation has explicit success and failure transitions. Accounting changes only after a confirmed successful operation. Unsupported page operations are reported as unsupported; no fake success.

The initial C-free native target can use a narrowly scoped Linux syscall/ABI implementation, followed by separately reviewed macOS and other target adapters. Platform code must be generated/native Capstan or a documented minimal assembly/ABI leaf, never a hidden C shim.

## 8. Secret lifetime

Secret allocation is pointer-free and isolated from ordinary slots/pages. It is wiped with an implementation whose stores cannot be optimised away, before reuse or release. Free-slot metadata must be out-of-line so it never repopulates wiped payload bytes. Failed wipe/release cannot publish the slot as reusable.

GC reachability is not deterministic destruction. Secret-bearing APIs must not rely on collection timing for prompt erasure; explicit destruction/consumption semantics are a separate language/runtime design obligation. The collector's guarantee is limited to the specified wipe-before-reuse/release transition.

## 9. Core invariants

- **ROOT-COMPLETE:** every live managed reference at a safepoint is represented by a valid root slot or a field reachable from one.
- **ROOT-TYPED:** every root slot is classified by a compiler-checked frame map; non-reference words are never traced.
- **HANDLE-VALID:** each published handle names exactly one allocated object in its originating heap instance and generation.
- **LAYOUT-IMMUTABLE:** an allocated object's descriptor and pointer map cannot be changed by an untrusted caller.
- **TRACE-COMPLETE:** every descriptor-declared reference edge from a marked object is visited.
- **NO-FALSE-RECLAIM:** every object reachable from the published root set remains allocated after collection.
- **SLOT-PARTITION:** every slot belongs to exactly one of allocated, free-listed, or page-spare states.
- **FREE-LIST-EXACT:** each reusable slot appears exactly once in the matching free structure; no allocated/spare slot appears there.
- **MARK-WORK-COMPLETE:** every discovered but unprocessed object remains represented in the worklist; overflow cannot discard work.
- **FAILURE-ATOMIC:** rejected allocation or failed platform operation leaves all logical ownership and accounting invariants intact.
- **ACCOUNT-EXACT:** each successful allocation/release changes each accounting domain exactly once; failed operations do not.
- **SECRET-WIPE:** secret payload is wiped before reuse or release, and allocator metadata never overwrites the wiped payload.
- **SINGLE-THREAD:** all heap mutation and collection are serialized; unsupported concurrent entry is rejected.
- **NO-UNSAFE-FINALISER:** no finaliser or resurrection path exists in the initial profile.

## 10. Verification and testing plan

The implementation is not promoted on the strength of an abstract model alone. Each layer has a separate gate:

A. **Semantic model:** Capstan executable transition model for roots, descriptors, handles, allocation, tracing, sweep, free-slot ownership, quotas and failures. Include an independently represented graph oracle.

B. **Formal model:** extend the existing Lean allocator/collector models with precise roots, typed layouts, mark-work completeness and sweep safety. Preserve PR #309's partition work and reconcile its state definitions; do not create competing definitions.

C. **Concrete Capstan implementation:** executable allocator and collector modules with contracts matching the model. No C collector calls in this path.

D. **Compiler refinement:** source/CCAM liveness and root-map generation, native frame layout, spill/reload rules, safepoint placement and trap/unwind behaviour. Compare evaluator and native execution on the same adversarial programs.

E. **Platform refinement:** page adapter success/failure behaviour, alignment and address-space constraints for each target.

F. **Adversarial testing:** collect at every permitted allocation; deep/wide/cyclic graphs; duplicate aliases; empty and maximum objects; invalid/stale/foreign handles; descriptor corruption attempts; malformed frame maps; root omission negative controls; worklist exhaustion; metadata exhaustion; page-operation failures; secret wipe observation; repeated allocation/reuse; all arithmetic boundaries.

G. **Differential fuzzing:** compare the concrete collector's survivors and reclaimed set against an independently implemented graph-reachability oracle. Any disagreement that could reclaim a reachable object is a hard failure. False retention is measured separately.

H. **Performance:** measure allocation throughput, pause time, retained bytes, metadata overhead, fragmentation and worst-case work on pinned workloads. Optimisation follows correctness; generational collection is a later project requiring complete write-barrier coverage and a full-collection verifier.

## 11. Migration and compatibility

The C collector is not deleted or bypassed merely because the Capstan implementation compiles. Migration requires:
- C-free native execution and a working native runtime allocation path;
- complete precise-root maps at every allocation safepoint;
- implementation-linked root completeness and collector refinement evidence;
- differential conformance against the existing runtime on defined semantics;
- GC-stress, fuzz, mutation, fault-injection and secret-wipe tests on exact heads;
- supported-target ABI and page-adapter evidence;
- reproducible self-hosting/bootstrap evidence with no C compiler, generated-C pipeline or Capstan-owned C runtime in the production path.

The old C-backed mode remains explicitly labelled compatibility-only until the replacement is the default and release gates pass. Only then should the C implementation be deprecated and subsequently removed in a separate reviewed change.

## 12. Work packages and dependencies

1. **GC-R0 — root contract:** settle precise root-frame ABI, safepoint rules, frame descriptors, global roots, helper temporaries and unwind semantics with compiler/native-backend owners.
2. **GC-R1 — model:** *initial slice implemented; compiler execution and review pending.* The first Capstan model covers generation-tagged roots/edges, traced versus pointer-free objects, transitive and cyclic reachability, an independent fixed-point oracle, validation and transactional worklist failure. Full allocator/page/descriptor/metadata state and reconciliation with PR #309 remain outstanding.
3. **GC-R2 — handle/layout substrate:** *logical model slice implemented; concrete execution pending.* Opaque heap-instance handles, immutable descriptor validation, checked handle resolution, failure-atomic slot publication/reclamation, generation retirement, nominally typed reference stores and complete descriptor-driven logical edge enumeration are modeled. Physical payload access, descriptor storage protection and refinement to the PR #309 allocator partition remain outstanding.
4. **GC-R3 — allocator:** bounded metadata arena, page/slot allocator, large objects, exact free-list ownership and accounting.
5. **GC-R4 — precise tracer:** bounded worklist, exact root traversal, object-layout scanning and sweep.
6. **GC-R5 — platform adapter:** native page provider with explicit result semantics and per-target tests.
7. **GC-R6 — compiler integration:** emit maps and spill/reload roots at safepoints; prove evaluator/native reachability equivalence.
8. **GC-R7 — assurance:** formal/concrete refinement, fuzzing, fault injection, sanitiser-equivalent native checks and benchmarks.
9. **GC-R8 — cutover:** make the Capstan collector the default native runtime path; deprecate the C collector only after all gates pass.

**Critical dependency:** GC-R0 and the compiler/native backend's reference representation must be agreed before reclamation code is implemented. GC-R1 can proceed independently as a model. The existing CCAM register/heap semantics work (#255) and bounded region heap work (#246/#262) must be reviewed for compatibility, not assumed to settle the production object model.

## 13. Current implementation progress

The first executable model slice is in `verification/gc_model.cap` and is wired into `tests/run.sh`. It is intentionally an abstract graph model: it does not allocate native heap memory, parse compiler-emitted frame maps, implement a page provider, or establish concrete object-layout correspondence. It validates dense object identities and generation-tagged references, requires pointer-free objects to have no outgoing edges, computes mark closure with a bounded worklist, and only constructs sweep output after the worklist is completely drained. Worklist exhaustion and malformed roots/edges return the original model object list without reclamation.

An independently structured fixed-point reachability oracle is included for differential checks. Tests cover cycles, transitive reachability, duplicate roots/edges, atomic/secret leaves, empty roots, invalid and stale-generation references, missing objects, secret-wipe state transitions, and bounded-worklist exhaustion. The new test is registered in the repository test harness. **No test execution or CI result is claimed yet**; the exact branch must compile and run this file before the model can be considered executable evidence.

A second Capstan model, `verification/gc_handle_model.cap`, now specifies heap-instance-scoped handles and immutable layout metadata. It validates unique descriptor identities, bounded and non-duplicated reference offsets, bounded descriptor/slot counts, dense slot identities, positive generations, and allocated-slot descriptor membership. Handle resolution distinguishes foreign heaps, malformed/out-of-range handles, stale generations, unallocated slots and nominal descriptor mismatches. Thirty-seven tests cover these cases, including allocation publication, reclamation, generation advancement, failure atomicity, permanent retirement at generation exhaustion, and descriptor-checked field bounds/kinds. The tests construct alternative heap values rather than mutating nested struct fields, avoiding dependence on the unresolved CCAM local-copy/aliasing semantics documented in the language-compatibility work.

A descriptor-driven trace step, `gch_trace_object`, now accepts the logical reference values for one object's payload and emits edges only after validating the complete declared reference-field set. Every descriptor-declared offset must appear exactly once; duplicate, missing or scalar offsets fail closed. Every target is checked for heap, generation and nominal descriptor identity. On any failure, the operation returns an empty edge list rather than a partially traced object. Six tests cover complete enumeration, omissions, duplicates, scalar-offset substitution, stale targets and nominal-type mismatch. This is still a logical payload snapshot supplied to the model, not a physical payload load or proof that compiler layout matches descriptor metadata.

The model now also defines `gch_check_field`: after resolving a live handle, it checks a requested field offset against the descriptor's field extent and exact reference-offset map. It distinguishes out-of-range fields from scalar/reference-kind mismatches. Five tests cover reference-field acceptance, scalar-field acceptance, bounds rejection and both directions of kind mismatch. This is a pre-access validation contract only; it does not load/store payload bytes. Each reference-bearing field now declares an exact target descriptor ID; the descriptor registry rejects missing target descriptors. A reference-store check validates the owner field, then requires the target handle to resolve to a live object in the same heap with the declared nominal descriptor. Foreign-heap, stale-generation, unallocated and wrong-descriptor targets are rejected. Seven additional tests cover these cases and scalar-field rejection.

This remains a logical identity/layout model. It models allocation/reclamation as immutable state transitions over a pre-existing bounded slot table. A successful allocation returns the new heap and generation-tagged handle together; a rejected operation returns the original heap. Reclamation invalidates the current handle, reuse advances the generation, and a slot reclaimed at maximum generation is permanently retired to prevent wraparound. This does not implement physical allocation, descriptor storage protection, pointer-field loads, or refinement to physical memory. Slot selection currently scans the bounded logical slot table; it is not a second free-list design and makes no free-list complexity or ownership claim. PR #309 remains the source of the abstract exactly-one-owner/free-list invariant. The required next proof is a refinement from this logical slot transition to #309's partition and free-list operations. The two model files are registered separately in `tests/run.sh`; exact-head execution is still required. Page state and concrete allocator correspondence remain unimplemented.

The current model does not prove compiler root completeness. Its root list is an explicit premise. A root-omission negative control is now included: a complete-root oracle identifies both live objects, while a deliberately incomplete root set causes the collector model to reclaim the omitted object. This demonstrates the consequence of a missing root; it does not establish that compiler-generated roots are complete.

## 14. Explicit non-claims

This document does not claim that the collector is implemented, that any theorem applies to executable code, that all memory corruption is impossible, that process RSS is bounded, that secrets are erased at scope exit, that concurrent collection is supported, or that the C-free compiler/bootstrap is complete.
