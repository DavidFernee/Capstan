# M0 — reference semantics and handle-lifecycle decision record

**Status:** research decision proposal; not normative language semantics.
**Coordination:** issue #370.
**Reviewed inputs:** main `docs/SPEC.md`; PR #255 head `research/native-register-heap-bridge-v1`; PR #262 head `research/ccam-heap-contract`; `verification/ccam_core.cap`; `compiler/codegen.cap`; current C runtime.
**Rule:** do not implement the native collector or promote the region prototype until the open semantic and representation obligations below are closed.

## 1. M0 outcome

The existing source specification already identifies structs as reference types, declares that there is no null (only explicit `T?`/ `none`), and treats struct/collection identity as relevant to policy grants. It does not yet give a complete executable reference/aliasing/lifetime contract. The additional reference rules on the current #255 head are explicitly marked proposed and are not yet normative on main.

M0 should freeze the observable source semantics independently of the native heap representation. It must not prematurely freeze a 64-bit handle layout, because the required number of heaps/regions, simultaneous slots and lifetime/reuse envelope have not yet been established.

## 2. Candidate source-level contract

The following is the minimum coherent contract to review and, if accepted, promote into the normative language specification.

### 2.1 Identity and copying

1. Each successful construction of a mutable reference object creates a fresh logical identity.
2. Assignment, argument passing, return, field storage and collection storage copy the reference value, not the referenced object.
3. A mutation through any alias is visible through every alias to that same logical identity.
4. Distinct successful constructions have distinct identities, even if the runtime later reuses the same physical storage.
5. Identity comparison remains unavailable to ordinary source code unless a separate language feature is designed; internal identity is not an address and cannot be converted to an integer.
6. The identity contract applies consistently to structs and to mutable collections if the language intends those collections to have identity semantics. Immutable byte strings remain value-semantic; their physical sharing/interning is unobservable.

### 2.2 Optionality and invalid references

- There is no null pointer/reference value in the source language.
- A `T?` is an explicit tagged optional containing either a valid `T` or `none`; it is not a nullable raw handle.
- A safe program cannot construct a reference from an integer, forge a handle, perform pointer arithmetic, or dereference an absent/reclaimed object.
- A failed internal handle resolution is a deterministic invalid-reference/runtime-integrity failure. It must never become a null-like value, silently select another object, or continue with unchecked memory access.
- The native ABI must not expose handle constructors, table storage or unchecked resolution to untrusted program data.

### 2.3 Lifetime

- Source code has no explicit free operation.
- An object reachable from a live local, parameter, global, registered root, or another reachable object's reference-bearing field/collection element remains alive.
- An unreachable object may be reclaimed. Reclamation does not alter the logical identity of any other object.
- Physical storage reuse must not cause an old, valid source reference to denote a new object.
- Every allocation-capable operation is a potential collection safepoint. Any live reference across it must be represented in the root protocol; a native stack address or unregistered temporary is not a root.
- Collection is observationally invisible except for bounded resource failure and explicitly specified diagnostics/statistics. It cannot change program values, aliasing, mutation visibility or evaluation order.

### 2.4 Failure and publication

Construction evaluates initialiser expressions in the language's specified left-to-right order. The object is not made observable until all required fields are valid and initialised. Allocation/initialisation failure must not publish a partially initialised object or mutate an existing object.

A failed operation has one defined outcome. It must not leave a half-advanced generation, leaked table slot, inconsistent accounting, partially appended collection or partially initialised object. The exact trap/result contract must be consistent between interpreter, C backend during migration, CCAM and native backend.

### 2.5 Collections

The language must explicitly decide and specify:
- whether `List<T>` and `Map<T>` are mutable reference objects (the likely compatibility-preserving choice);
- whether assignment/argument/return/storage copy collection identity;
- alias-visible effects of `push`, indexed assignment, `set`, and mutation through nested collections;
- whether iteration observes a snapshot or live mutation, and what happens when the collection changes during iteration;
- whether map key equality/hash semantics and insertion order are stable across mutation;
- how removed/replaced elements cease to be traced and how their reference slots are cleared before collection.

Do not infer these semantics from today's C implementation or tests alone. Record each as a compatibility decision with conformance vectors.

## 3. Audit of the current formal work

### 3.1 PR #255 — reference and collector models

The current PR head has materially improved the register-file correspondence predicate. `NativeHeapRegisterFileRelation` now requires:
- reference-vector and register-list lengths to match;
- every present reference slot to resolve to some existing heap object;
- the heap payload at that identity to agree with the corresponding mathematical register-list slot.

It also includes `nativeHeapRegisterFileRelation_rejects_missing_object`, which rejects the empty-heap/dangling-reference counterexample. This resolves the vacuity weakness identified in earlier review. Do not carry the stale criticism forward.

The remaining proof boundary is implementation refinement: source assignment/argument/return/field/list operations, runtime object allocation, root completeness, concrete collection and lifetime are not proved by the abstract models.

The #255 `GenerationalHandles` model is a useful resolver lemma but not yet a lifecycle machine:
- `handleAllocateAt` accepts an arbitrary caller-supplied generation;
- it can overwrite an occupied slot without a prior release;
- it does not require a generation strictly greater than the previous one;
- it does not couple generation exhaustion to permanent slot retirement;
- it does not prove allocation failure leaves the complete table unchanged.

It proves that a caller-selected different generation rejects a stale handle. It does not yet prove that every executable reuse transition must select a different generation.

### 3.2 PR #262 — region heap and slot recycle

The #262 `recycleSlot` function increments the generation before publishing a replacement, and the stale-handle theorem follows from that transition. The model explicitly leaves generation wraparound open. It does not yet combine bounded generation, slot retirement, allocation budgets, capability validation and handle publication in one transition system.

Its `RegionCapability`/issuer ledger is an abstract authority model. It is not proof that a concrete Capstan program cannot fabricate or replay the runtime representation. The `.cap` prototype also remains outside the supported CCAM subset because it uses mutable struct/list aliasing whose language/runtime correspondence is not established.

### 3.3 Required correction to claims

These formal models are useful and increasingly precise. They are not yet executable implementation proofs. Keep separate evidence labels for:
- theorem checked by Lean;
- model assumptions;
- implementation refinement theorem;
- executable conformance tests;
- differential tests;
- native binary/security tests.

No result in one category substitutes for another.

## 4. Handle lifecycle: the missing composed state machine

The critical next formal unit is not another isolated resolver theorem. It is a total, bounded state machine that owns every lifecycle transition.

### 4.1 Abstract slot state

For a finite configured generation domain `0..Gmax`, each slot is exactly one of:

- `NeverUsed` (generation 0 available);
- `Occupied(g, object)`;
- `Free(g)` (the next allocation may use generation g);
- `Retired` (never allocatable again).

No state may be represented by an ambiguous combination of occupancy and generation fields.

### 4.2 Transitions

**Allocate(slot, object):**
- accept only `NeverUsed` or `Free(g)`;
- reject `Occupied` and `Retired` without changing any state;
- validate descriptor, object size and every resource budget before publication;
- privately initialise object storage;
- atomically publish `Occupied(g, object)` and issue the opaque handle `(slot,g)`;
- on any pre-publication failure, return the original state exactly.

**Release(slot, g):**
- accept only the currently occupied generation;
- reject stale/wrong-generation handles without mutation;
- if `g < Gmax`, transition to `Free(g+1)`;
- if `g = Gmax`, transition to `Retired`;
- clear reference-bearing payload and descriptor ownership before making the slot reusable;
- do not wrap, saturate, or reset the generation.

**Resolve(handle, authority):**
- validate authority/heap domain;
- validate slot bounds;
- accept only `Occupied(g, object)` with exact generation equality;
- reject every other state, including `Free`, `NeverUsed`, `Retired`, wrong generation and wrong domain;
- return a checked object view whose lifetime cannot cross a collection/mutation safepoint unless represented as a rooted handle.

### 4.3 Mandatory invariants

1. **Unique occupancy:** each slot has at most one occupant.
2. **No generation rollback:** generations never decrease or repeat for a slot.
3. **No wrap:** a slot is retired at exhaustion.
4. **No resurrection:** every released handle remains invalid forever.
5. **Freshness:** every issued handle identifies exactly one allocation incarnation.
6. **Domain isolation:** a handle cannot resolve in another heap/region.
7. **Publication atomicity:** rejected/failed allocation leaves all externally observable state unchanged.
8. **Release atomicity:** failed release leaves state unchanged; successful release clears all object edges before reuse.
9. **Resolution soundness:** successful resolution returns exactly the object for the issued live handle.
10. **No raw-pointer escape:** a resolved address cannot outlive its protected borrow/safepoint interval.
11. **Accounting consistency:** slot state, object table, free-slot index and byte/metadata counters agree after every transition.
12. **Trace safety:** the collector never releases a reachable occupied slot; it never sweeps after incomplete marking.

The proof should establish these for every reachable state, not only for constructor-shaped examples.

## 5. Authority and representation are separate design questions

A numeric region ID is not an unforgeable capability. An opaque source type is not automatically opaque in generated machine code. The runtime boundary must prevent untrusted bytes or integers from being interpreted as a handle.

Do not commit to an ABI encoding until resource envelopes are measured. Candidate representations include:
- a single-process global slot table with a 64-bit slot/generation handle;
- a multi-heap handle with an explicit heap/domain component;
- an opaque runtime-owned handle paired with an unforgeable heap context.

Each has different bounds and costs. A 64-bit encoding must state maximum simultaneous slots, reuse count, domains, reserved bit patterns and retirement policy. A multi-heap representation cannot rely on a caller-supplied expected-region integer as its sole isolation mechanism.

The fast path should be one bounds check, one occupancy/generation check and one descriptor/layout check where needed. Security must not depend on probabilistic collision resistance or a random token unless the threat model explicitly requires and justifies it. The representation should be amenable to constant-time validation with no unchecked pointer arithmetic.

## 6. Security-by-construction and efficiency requirements

This design should remove whole classes of failure rather than add checks around raw pointers.

| Vulnerability/resource class | Construction-level prevention |
|---|---|
| Use-after-free / stale reference | Opaque handles, generation checks, no generation reuse, explicit roots |
| Type confusion | Immutable validated descriptors; typed accessors; no caller-supplied layout pointers |
| Out-of-bounds access | Checked slot/field/index resolution before address derivation |
| Double free / invalid free | No source free; collector-owned state transitions only |
| Cross-heap confusion | Domain-bound handle resolution; non-forgeable runtime authority |
| Uninitialised read | Explicit initialisation bitmap/tag; publish only fully initialised objects |
| Integer overflow in sizes | Checked multiply/add/alignment and subtraction-form budget admission |
| Partial mutation on OOM | Reserve-first, single publication point, rollback/no-visible-change failure |
| GC use-after-free | Complete explicit roots and typed edge enumeration; fail closed on incomplete marking |
| GC corruption | Collector metadata outside managed heap; validate before sweep; transactional collection phases |
| Resource exhaustion | Independent byte, metadata, object, depth, input, temporary and work budgets |
| Timing/algorithmic denial of service | Bounded hashing, worklists, recursion, parsing, map growth and collection fuel |

Efficiency requirements:
- no per-reference heap allocation;
- no cryptographic MAC on every ordinary internal reference unless a concrete threat model requires it;
- compact handles and cache-local slot metadata;
- descriptor metadata shared and immutable;
- allocation fast path uses pre-reserved slabs/arenas and a single commit;
- collector work proportional to live objects plus reference edges, with a separately bounded mark queue;
- collection metadata preallocated or separately bounded, never recursively allocated from the heap being collected;
- measure bytes per AST node, token, type, map entry and handle, as well as allocation/collection throughput and worst-case pause;
- optimise only after invariants and accounting are stable.

## 7. Research opportunity: proof-carrying lifecycle transitions

The existing PRs separately model allocation budgets, generation-checked resolution, release/recycle, and abstract reachability. A useful research contribution is to compose them into one transition system whose states carry enough structure to make illegal states unrepresentable.

The target theorem is a lifecycle preservation theorem:

> From a well-formed initial heap, every accepted allocate, resolve, release and collect transition preserves well-formedness; every rejected transition is observationally state-preserving; and no handle ever issued for an allocation can resolve to a different allocation incarnation in any reachable future state.

The collector-specific strengthening is:

> If the marker completes over the explicit root set and descriptor-defined edges, collection preserves every reachable handle/object pair; every reclaimed slot is unreachable; and future reuse is fresh by construction through generation advancement or permanent retirement.

This is more valuable than proving isolated helper functions because it connects the object identity, authority, budget, allocator and collector invariants at the exact point where implementation bugs tend to occur.

The Lean model should be executable enough to generate transition traces for differential testing against a Capstan implementation. Counterexample traces should include stale handle after release/reuse, generation exhaustion, cross-domain resolution, allocation failure at each reservation phase, descriptor mismatch, incomplete mark queue and root omission.

## 8. M0/M1 gates and deliverables

| Gate | Deliverable | Exit criterion |
|---|---|---|
| M0a | Normative reference semantics decision | Struct/list/map identity, aliasing, mutation, optionality, construction order and lifetime explicitly settled |
| M0b | Abstract value/heap semantics | Small-step or state-transition rules; no ambiguous null, stale or partially initialised states |
| M1a | Integrated handle lifecycle Lean model | Allocate/release/reuse/resolve/retire and resource admission are one state machine |
| M1b | Invariant proofs | All 12 invariants above proved for all reachable states; failed transitions are state-preserving |
| M1c | Adversarial trace corpus | Generated counterexamples cover stale reuse, exhaustion, cross-domain, OOM, invalid descriptors and malformed roots |
| M1d | Supported Capstan expression | Either implement the model using currently supported semantics, or explicitly identify the exact language features that must be added before a Capstan implementation is possible |
| M2 | Concrete bounded object storage | Descriptor/layout, reservation, accounting and publication refine M1 |
| M3 | Explicit-root collector | Root completeness and tracing implementation correspond to the formal reachability model |

Do not start M2/M3 because a helper proof passes. The integrated lifecycle machine and source-language contract are the acceptance gate.

## 9. Immediate next action

Audit the #255/#262 model APIs against the 12 invariants, then implement the integrated bounded lifecycle model in the formal verification branch owned by this workstream. Keep it separate from the other workers' branches. Run the pinned Lean checker and axiom audit on the exact commit; if the environment or workflow is not available, report that limitation rather than claiming proof completion.

In parallel, obtain an explicit decision from the language-semantics owner on whether mutable lists/maps share identity in exactly the same way as structs. This is necessary to root and trace the compiler's real AST/checker graph without relying on undocumented aliasing behaviour.
