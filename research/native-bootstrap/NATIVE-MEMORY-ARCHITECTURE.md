# Native memory architecture: implementation and proof decision record

**Status:** architecture recommendation; not a normative language or CCAM change.
**Coordination:** issue #370.
**Baseline:** `main` at `189f19dd2a39c169e033691856d675b070fb2864`.
**Scope:** native compiler heap, object identity, references, collection storage, allocation and eventual Capstan-written collector.

## 1. Decision in brief

Do not port the existing conservative C collector line-for-line and do not promote the region-heap prototype in PR #246 as the production allocator.

Adopt a **handle-addressed object heap** as the long-term representation:

1. Source-visible references are opaque, generation-checked handles, never raw addresses.
2. A handle resolves through a heap-owned slot table to an object descriptor and storage location.
3. The collector owns the object table, allocation metadata, object layouts, root registry and all mutation of allocation/mark state.
4. Compiler/runtime code uses handles and checked accessors. A raw object pointer, if ever used internally for a short critical section, cannot survive an allocation/safepoint and cannot be stored in source-visible state.
5. Begin with a non-moving implementation to reduce the first implementation's relocation complexity, but preserve the handle indirection so a moving/compacting collector can be introduced without changing source-level reference identity.
6. Use explicit roots from compiler-owned execution frames and global/module roots. Do not rely on conservative scanning of native stack words as the correctness mechanism.
7. Make allocation and collection transitions bounded and failure-atomic. Resource admission is based on actual representation sizes and metadata, not only abstract payload estimates.

This is a target architecture, not an implementation claim. The current supported language subset and compiler do not yet implement the required semantics.

## 2. Evidence and current blockers

### 2.1 Existing region heap prototype (#246)

The prototype in `verification/ccam_heap.cap` has useful properties:
- typed record layouts and nominal descriptor checks;
- homogeneous typed arrays, logical length/capacity and bounds checks;
- immutable byte-string objects and embedded-NUL preservation;
- opaque numeric IDs paired with a heap token;
- explicit byte, object, work and temporary-request budgets;
- preflight checks before logical mutation, plus tests for rejected operations.

Its stated boundary is process-lifetime allocation with no individual free and no GC. Its IDs are monotonic and object lookup is by list index. The heap token is supplied by the creator. The prototype uses Capstan `List` and `string` storage internally, so its byte charges do not account for the actual backing allocations, list capacity, allocator metadata, temporary copies or process RSS. Its own PR description correctly says token uniqueness/non-reuse and runtime integration remain obligations.

Most importantly, its API mutates a `CCAMHeap` local and nested list values. PR #262 explicitly records that this depends on reference/collection aliasing excluded from the currently supported CCAM subset. It is not yet a valid executable runtime contract.

### 2.2 Reference semantics and formal work (#255)

PR #255 adds mathematical models for opaque identities, shallow reference copies, heap mutation, a monotone allocation frontier, and abstract mark/sweep reachability from explicit roots. Its current head also strengthens `NativeHeapRegisterFileRelation`: it now requires each referenced slot to resolve to an existing heap object, in addition to relating the heap payload to the mathematical register list. It includes a negative theorem rejecting a dangling slot against an empty heap. This addresses the vacuity issue raised in earlier review; the current head should not be described as still having that defect.

The remaining boundary is substantial. The PR itself does not prove:
- compiler lowering or field assignment realizes those rules;
- concrete runtime allocation creates fresh identities;
- evaluator operations preserve the invariants;
- the current C collector's stack/register/global scan is complete for the formal reachability relation.

The `GenerationalHandles` model proves rejection when a caller supplies a different generation, but its `handleAllocateAt` accepts an arbitrary generation and can overwrite a slot without a lifecycle precondition. It does not yet define one integrated allocate/release/reuse transition that enforces monotonic generation, retirement at exhaustion and failure atomicity. The collector model assumes marker completeness; it does not prove a concrete marker is complete.

### 2.3 Region-heap formal contract (#262)

PR #262 adds an abstract allocation transition, byte/object/work/temporary budgets, rejected-allocation atomicity and candidate generation-handle properties. Its `recycleSlot` transition increments a natural-number generation before publishing a replacement, and the stale-handle theorem follows for that transition. However, the model has no bounded generation maximum or retired-slot state, so it does not yet establish a finite-width implementation's no-wrap property. Its region capability remains a model-level identity/issuer ledger, not an unforgeable runtime capability; allocation and handle resolution are not yet composed into one capability-checked slot-table state machine.

It explicitly does not prove the `.cap` implementation refines Lean. The temporary-byte bound is a logical request bound, not physical RSS or allocator-metadata accounting. The prototype remains outside normative CCAM v0.1.

### 2.4 Existing C runtime

The current runtime uses a conservative, non-moving mark/sweep collector with native pointers, page/size-class metadata, explicit roots plus native stack/register scanning, and C-owned allocation metadata. It is a useful behavioural and security reference, not the desired C-Free production implementation.

A Capstan-written collector must not silently inherit the assumptions of the C implementation. In particular, the new runtime needs a defined root protocol and a concrete representation of object edges.

## 3. Object identity and handle contract

A source reference denotes an object identity, not its storage address. Copying, passing, returning or storing a reference copies the handle. Mutating the object through one alias is visible through all aliases.

### 3.1 Logical handle

Use a fixed-width unsigned 64-bit handle with fields:

| Field | Purpose |
|---|---|
| heap/region identity | Prevents cross-heap resolution |
| slot index | Selects an object-table slot |
| generation | Distinguishes successive occupants of a reused slot |
| reserved/tag bits | Canonical validation and future versioning; must be zero in v1 |

The exact bit allocation must be selected against explicit maxima for simultaneous heaps, slots and slot reuse. It must be fixed in the ABI, not chosen ad hoc by the emitter. Zero is the null/invalid handle and must never resolve.

A resolver accepts a handle only if:
- the heap identity is current and matches;
- slot index is in range;
- slot is occupied;
- generation matches exactly;
- descriptor/layout is valid for the requested operation.

Every failed resolution is a deterministic invalid-reference trap; no unchecked pointer arithmetic follows a failed check.

### 3.2 Generation exhaustion

A slot generation must never wrap. When its maximum is reached, retire the slot permanently. If the heap cannot obtain a fresh slot within its bounded slot table, allocation fails deterministically. Reuse must increment generation before publishing the new occupant.

Generation checks prevent stale-handle resurrection after slot reuse; they do not by themselves prevent use-after-free through an unchecked raw pointer. Therefore no raw pointer may be retained across an allocation or collection boundary.

### 3.3 Heap identity

Heap identity must be minted by the heap/runtime authority, not caller-supplied integer data. A heap identity must not be reused while a handle from the previous heap instance could remain observable. A process-lifetime monotone ID with exhaustion/retirement is a simple initial policy; a random token is not a substitute for a precise uniqueness/lifetime contract.

## 4. Object and storage representation

Separate three concepts which the prototype currently combines:
1. **Descriptor:** immutable, validated type/layout metadata.
2. **Handle table entry:** identity, generation, occupancy, descriptor ID, storage location and GC state.
3. **Object payload:** field slots, array elements, string bytes or other typed payload.

A descriptor contains fixed field count, field offsets/representations, mutability, initialization policy and reference-edge metadata. Descriptors are validated and frozen before any object of that type is allocated. Object payload never carries caller-controlled descriptor pointers.

Initial object kinds:
- fixed-layout records/closures;
- typed growable arrays;
- immutable byte strings;
- maps with separately bounded index and entry storage;
- compiler-specific AST nodes and symbol/type/diagnostic records, expressed using the same descriptor/array/string substrate.

Use tagged values for integers, booleans, references and any later value types. A reference slot must be distinguishable from an integer bit pattern; the collector must never guess whether an integer is a pointer. Uninitialised fields/elements must be represented explicitly and rejected on read.

For arrays, keep length and capacity separate; require 0 <= length <= capacity <= configured maximum. Only the prefix [0, length) is observable and traced. Capacity slots outside the logical length must not retain references or become roots accidentally. On shrink, clear removed reference slots before a collection can run.

Strings are immutable byte sequences with explicit byte length. UTF-8 validity is a property of the string operation/type that requires it, not an assumption of the allocator. Embedded NUL is ordinary data. Concatenation and decoding must preflight checked size arithmetic and output budgets before allocation.

## 5. Allocation protocol and failure atomicity

Every allocation is a transaction with these phases:

1. **Validate:** check descriptor, value tags, lengths, capacities, alignment and all integer arithmetic.
2. **Compute:** calculate object bytes, table/metadata growth, alignment padding, collector metadata and temporary peak using checked arithmetic.
3. **Admit:** prove every relevant budget has sufficient remaining capacity using subtraction-form checks (request <= limit - used).
4. **Reserve:** reserve all required heap and metadata capacity before publishing an object or changing existing objects.
5. **Initialise privately:** create the object with all reference slots null/uninitialised and a valid descriptor.
6. **Commit:** publish the handle-table entry and then return the handle. Publication is the single logical commit point.
7. **Rollback:** on any failure before commit, release all private reservations and leave visible heap contents, handle table, counters, generations and existing objects unchanged.

No partially initialised object may become reachable. No counter is advanced before all fallible reservation work is complete. If the implementation cannot guarantee rollback of a host allocation, it must reserve a non-failing bounded arena region first or make the allocator failure terminal before exposing any mutation.

Budgets must be separate and explicit:
- live object payload bytes;
- reserved heap bytes, including fragmentation/size-class slack;
- handle-table and descriptor metadata;
- GC mark/work queue and remembered-set metadata;
- temporary peak bytes;
- object/slot count;
- collection work/fuel;
- compiler-specific input/output and recursion budgets.

A payload-byte limit alone is not a memory limit. Report both logical payload and total reserved/committed memory. The production contract must define whether OS virtual reservation, committed physical pages and resident set are separately bounded.

## 6. Collector architecture

### 6.1 First implementation: non-moving explicit-root mark/sweep

Start with non-moving objects to keep object storage stable while validating the handle and tracing architecture. This is a staged implementation choice, not a commitment to retain fragmentation indefinitely.

The collector operates over handle-table entries:
1. Stop mutators at a defined safepoint (single-threaded compiler first).
2. Clear mark state for occupied entries.
3. Seed a bounded mark worklist from the explicit root set.
4. Validate each root handle; stale/invalid roots are an invariant failure, not ignored.
5. For each marked object, use its validated descriptor to enumerate only reference-bearing fields and the live prefix of reference arrays/maps.
6. Validate every non-null child handle before marking it.
7. Fail closed if worklist capacity/work budget is exhausted; never sweep after incomplete marking.
8. Sweep unmarked entries, incrementing generation or retiring the slot on generation exhaustion.
9. Rebuild free-slot structures and reconcile accounting before resuming mutators.

The marker must not allocate from the managed heap while collecting. Its worklist and metadata are pre-reserved or have a separate bounded allocator. If the worklist cannot represent the full discovered frontier, collection fails without reclaiming anything.

### 6.2 Explicit root protocol

The first native compiler is single-threaded, so start with explicit root frames:
- each compiler/runtime frame declares a fixed set of root slots;
- root slots contain only handles or tagged values with explicit reference tags;
- frame entry registers a root frame; frame exit unregisters it;
- every allocation-capable operation is a safepoint;
- values live across a safepoint must be in registered root slots;
- temporary handles are rooted before any further allocation;
- global/module roots are registered in a bounded table.

A raw local variable holding an object address is never a root. No conservative stack scanning is required for correctness. Debug builds should poison or validate unregistered temporary references at safepoints where practical.

For future concurrency, root frames become per-thread and collection requires a stop-the-world handshake or a separately specified concurrent algorithm. Do not imply thread safety from the single-threaded protocol.

### 6.3 Future compaction

Once the handle table is stable, a moving collector can relocate payloads and update only the table's storage locations. Source handles remain unchanged. Compaction is permitted only at safepoints with all references represented as handles; no raw payload pointer may survive relocation.

Do not implement compaction in the first milestone. Design the table indirection now so moving later is possible without changing source semantics.

## 7. Why not use the current C collector as the target design?

The current collector's conservative scanning is practical for the C-generated backend, but it is a poor foundation for a Capstan-native runtime:
- conservative scanning needs platform-specific register/stack bounds and pointer-shape heuristics;
- integer bit patterns may retain objects spuriously;
- the native compiler needs an explicit, auditable root discipline;
- a Capstan implementation should not depend on C ABI stack layout or a C helper to discover roots;
- its page and metadata allocator must itself be implemented and bounded in Capstan or through a narrowly specified OS mapping boundary.

The existing collector remains an oracle for regression workloads and memory-pressure behaviour, not a specification for the new collector's internal representation.

## 8. Staged implementation and proof gates

| Gate | Deliverable | Required evidence | Not yet claimed |
|---|---|---|---|
| M0 | Freeze source reference semantics and representation contract | Approved language rules; explicit alias, null, equality, mutability, initialisation and lifetime semantics | Runtime implementation |
| M1 | Pure handle-table model in supported Capstan subset | Generation, cross-heap, stale, null, exhaustion, no-wrap and failure-atomicity tests; no mutable struct aliasing dependency | GC |
| M2 | Bounded object arena and descriptors | Exact layout/size accounting; checked allocation; reservation rollback; typed field/array access | Reclamation |
| M3 | Explicit roots and non-moving mark/sweep | Root completeness argument; graph traversal tests; cycles, deep graphs, high fanout, invalid edge fail-closed, incomplete-worklist fail-closed | Moving/parallel GC |
| M4 | Compiler substrate | Strings, arrays, maps, AST and symbol graph under heap and work limits; allocation at every parser/checker path tested | Self-hosting |
| M5 | Native compiler integration | Compiler source compiled/executed by native compiler; no generated C or Capstan C runtime in path | Independent bootstrap |
| M6 | Collector assurance | Differential stress against reference model, allocation/collection fault injection, exact accounting, sanitizer-free native execution, formal transition correspondence | Formal compiler correctness |
| M7 | Independent seed and reproducible bootstrap | Independent S0, S1/S2/S3 provenance, clean-room rebuilds | Complete proof of correctness unless separately established |

Formal obligations are split rather than conflated:
- handle resolution soundness and stale-handle rejection;
- allocation freshness and generation monotonicity;
- object-layout/type soundness;
- root registration completeness at safepoints;
- descriptor-guided edge enumeration completeness;
- mark-worklist completeness or fail-closed behaviour;
- sweep preservation of all reachable objects;
- reclamation of unreachable objects;
- no stale handle resolves after reclamation/reuse;
- allocation failure atomicity;
- byte/metadata/work accounting soundness;
- correspondence between Capstan implementation transitions and the Lean model.

A theorem about an abstract complete marker is not evidence that the executable marker is complete. A passing regression test is not a proof of root completeness.

## 9. Immediate work items and ownership boundaries

### Native bootstrap workstream (this branch)
- Maintain this architecture and trace the required compiler object graph.
- Build an independent pure handle-table executable prototype only after confirming that its operations can be expressed in the supported language without excluded aliasing.
- Define a test corpus for handles, layouts, explicit roots and collector transitions.
- Keep implementation isolated from shared compiler/runtime/CCAM files until integration interfaces are approved.

### Existing PR owners
- **#246:** retain as a process-lifetime region prototype and source of layout/typed-array tests; do not promote it directly to a production collector.
- **#262:** retain as a resource/failure-atomicity contract proposal; clarify that its abstract temporary budget is not physical-memory accounting.
- **#255:** continue language/runtime/GC correspondence. In particular, prove actual supported semantics for struct identity, field mutation, list storage and aliasing before using the prototype's mutation style.
- **#315:** continue the bounded external CCAM decoder independently; its typed immutable program ownership is a separate compiler-input boundary and does not solve runtime heap/GC semantics.

No PR should be rebased, cherry-picked or merged by this workstream. Re-evaluate exact interfaces only after the integration worker stabilises mainline.

## 10. Immediate recommendation

The next implementation unit should be **M1: a pure handle-table transition model**, not a collector.

It should avoid `struct` mutation and mutable collection aliasing until #255's correspondence work closes that gap. If the supported language cannot express the handle-table transition without those semantics, stop and record the language/compiler prerequisite rather than quietly relying on behaviour that the language contract excludes.

Only after handle freshness, validation, no-wrap and atomicity are represented in supported Capstan semantics should M2 allocate object storage. The collector follows only after explicit root frames and typed edge metadata exist.


## 11. Concrete compiler object-graph inventory

This inventory is based on the current compiler sources at the branch baseline, not a hypothetical minimal compiler. It is included to prevent the memory design being reduced to a scalar register array.

### 11.1 Frontend graph

| Module/type | Object and edge shape | Heap requirement |
|---|---|---|
| `compiler/ast.cap: Type` | kind, name string, recursive `List<Type>` arguments | Recursive typed objects; immutable or controlled-mutation type nodes; bounded argument vectors |
| `compiler/ast.cap: Node` | kind, two strings, scalar/source positions, recursive `List<Node>` children, optional `Type` | Dominant recursive AST graph; optional reference; source-span metadata; arena/GC lifetime across checker and codegen |
| `compiler/ast.cap: Diag` | source location, code and message strings | Diagnostic graph and bounded message storage |
| `compiler/ast.cap: Ctx` | lists of paths, tainted source objects and diagnostics plus flags | Long-lived compilation roots; source buffers and diagnostics retained across phases |
| `compiler/lexer.cap: Token` | kind, string payload, integer and source position | Large flat token arrays; strings may reference source slices or own decoded content |
| `compiler/lexer.cap: Lexer` | source object, cursor state, context and token list | Lexer state and token-list ownership; bounded input/token counts |
| `compiler/parser.cap: Parser` | token list, context, recursion depth, extra declarations | Recursive parser stack plus AST allocation; explicit parser depth and node budgets |
| `compiler/checker.cap: Checker` | multiple maps of AST nodes/types, nested scope/map lists, counters and context | Hash/index storage, many aliasing references to AST nodes, scoped lifetime and deterministic map growth |
| `compiler/checker.cap: Flow/FlowSummary` | maps of flow facts and lists of boolean summaries | Repeated temporary analysis graphs and bounded fixed-point work |
| `compiler/ranges.cap: Rg/Snap` | maps of intervals, maps of lists, nested snapshots and copied environments | High temporary allocation/churn; explicit work budget and predictable snapshot cost |
| `compiler/main.cap` | paths, source list, loaded-file map, import queue, provenance arrays, combined declarations | Multi-file ownership, import-cycle/duplicate control and whole-compilation root set |

The AST is a graph, not simply a tree once checker tables, declaration maps and type references point into it. The collector must preserve shared nodes and must not assume a single-parent tree. Parser recursion, AST depth, token count, diagnostics and import count need independent bounds; a single heap-byte cap does not bound CPU or recursion.

### 11.2 Required roots and phase transitions

At minimum the compiler's root set must include:
- loaded source buffers and their path/name metadata;
- lexer token buffers while parsing is active;
- parser token stream, current construction stack, partial AST roots and lifted method declarations;
- the complete declaration list and AST roots between parse, checker, range analysis and code generation;
- checker declaration maps, nested scope maps, current expression/statement nodes and type nodes;
- range-analysis environments, snapshots, fixed-point maps and current work items;
- diagnostics until they have been rendered or deliberately discarded;
- generated assembly/output buffers while writing the artifact.

A phase boundary is not automatically a collection boundary. A node reachable only through a checker map or a diagnostic must remain live until that map/diagnostic is dropped. Conversely, after a phase completes, the compiler should be able to release phase-local roots deterministically so memory can be reclaimed before the next source file or compilation request.

For a future persistent LSP process, each open document needs an explicit ownership domain: document version, AST/type/checker roots, diagnostics, pending requests and cancellation state. Replacing a document version must detach old roots only after no in-flight request can reference them. The first native CLI can avoid concurrency, but its ownership model should not preclude this.

### 11.3 Storage and tracing consequences

- Recursive `Node.kids`, `Type.args`, nested maps and map values require descriptor-guided tracing; raw integer/string fields must not be treated as references.
- `Map<Node>`, `Map<Type>` and `Map<List<Iv>>` create graph edges through both map entry storage and nested collection storage. The map's index table is also managed memory and must be included in the accounting.
- Source substrings and decoded token strings require an explicit policy: either immutable slices retain a source-buffer handle plus byte offsets, or they own copied byte strings. A slice must never be a naked pointer into a movable or reclaimed source buffer.
- The current lexer builds decoded strings by repeated concatenation in some escape paths. The native lexer should use a bounded byte builder with checked geometric growth and one final immutable string publication, not quadratic repeated copies.
- Parser construction repeatedly appends child nodes. AST child vectors therefore need amortised growth with capacity accounting and failure atomicity.
- Checker and range analysis create short-lived maps/lists repeatedly. They need region/epoch allocation or tracing collection, not an unbounded process-lifetime arena for a persistent LSP.
- Descriptor tables and compiler metadata should be immutable after validation and rooted for the lifetime of the compiler image.

### 11.4 Concrete boundedness dimensions to measure

Before selecting heap defaults, collect real corpus maxima and enforce configurable ceilings for:
- source bytes per file and total imported source bytes;
- token count and total decoded token bytes;
- AST node count, maximum AST depth, child-vector capacity and total string bytes;
- type-node count and type-argument depth;
- diagnostics count and total diagnostic bytes;
- import count, graph depth and total path bytes;
- map entries and aggregate map index capacity;
- checker/range-analysis worklist entries, iterations and total work;
- root-frame slots and maximum live roots;
- live object count, payload bytes, reserved bytes, metadata bytes and GC work.

These are separate resource contracts. An AST with a million shallow nodes and one with extreme recursive depth stress different resources; a small source can still trigger high analysis work. The first native compiler should use conservative explicit limits and reject excess input deterministically rather than rely on host memory exhaustion.
