# Keel mesh ownership and BVH design gates

**Status:** architecture decision record and research plan; no immutable mesh asset or BVH implementation is claimed.  
**Scope:** K1 mesh representation, CPU spatial acceleration and the Capstan language/runtime dependencies they require.

## 1. Decision summary

Keel will not expose a persistent `KMesh` trust-bearing object until Capstan can enforce the ownership and immutability properties on which that object depends.

The current `lib/keel/mesh.cap` functions validate caller-owned mutable lists at the instant of the call. They neither retain those lists nor make later mutations safe. This is the correct boundary for the current language; wrapping the same lists in a struct would not make them immutable.

The recommended sequence is:

1. Keep validation as a stateless boundary operation.
2. Specify and implement a Capstan-level immutable owned-buffer or ownership-transfer capability, with explicit byte accounting and failure semantics.
3. Construct canonical mesh storage only through that capability; validate before publication and publish atomically.
4. Define topology classifications independently from geometric triangle validity.
5. Build a deterministic, bounded CPU BVH over published immutable geometry.
6. Add refit/incremental update semantics only after a versioned replacement or snapshot model exists.

No BVH may retain aliases to mutable caller lists, and no acceleration structure may be treated as authoritative after its geometry version changes.

## 2. Findings from the current Capstan contract

The current language and runtime documentation establishes the following facts:

- `List<T>` is growable and supports mutation; indexing is bounds-checked.
- Structs and collections are bound by identity, while scalar values are passed by value. A struct containing a list therefore does not create a deep immutable snapshot.
- The current public collection contract does not specify a deep-copy operation, immutable collection type, borrow checker, ownership transfer, or source-level destruction.
- The runtime uses a non-moving conservative mark-and-sweep collector. Reachable objects remain at stable addresses, but logical unreachability does not imply prompt reclamation.
- Collection storage is scanned conservatively; stale pointer values in vacated slots can retain objects. Collection-slot hygiene is a distinct runtime concern.
- The supported execution assumption remains one application thread entering the managed runtime. No concurrent mutation/publication protocol can be assumed.

These are not merely API inconveniences. They affect alias safety, publication atomicity, memory budgets, deterministic lifetime, and the validity of derived structures such as bounds, adjacency and BVHs.

**Consequences:** a validated list can be changed after validation; a shallow wrapper cannot prevent this; a copy implemented as ordinary repeated pushes still needs allocation-failure and aggregate-budget semantics; and GC reachability is not a deterministic resource-release contract.

## 3. Required Capstan capability

The preferred long-term primitive is a runtime-supported immutable owned buffer with a construction phase and a publication boundary. The exact source syntax is intentionally not prescribed here.

The capability must provide:

1. **Exclusive construction:** while a buffer is being populated, no published reader can observe partial contents.
2. **One-way publication:** publication consumes the construction authority; the published value exposes reads but no mutation operation.
3. **No mutable aliases:** the type/runtime must establish that no writable alias survives publication. A convention or naming rule is insufficient.
4. **Checked allocation:** element-count multiplication, header/alignment overhead and aggregate byte totals are checked before allocation.
5. **Explicit budgets:** callers provide or inherit a resource account; every allocation is charged exactly once; budget exhaustion is a recoverable, specified result where the runtime can support it.
6. **Failure atomicity:** a failed construction cannot publish a partial buffer or leak a budget reservation.
7. **Stable identity/version:** derived data records the immutable geometry version or identity from which it was built.
8. **Runtime correspondence:** the compiler's ownership rules and runtime representation must be tested together; a type-level proof alone is not evidence that generated code preserves the invariant.

A move/consume API, a borrow-checked slice, a dedicated immutable array, or a region/arena abstraction may be viable. They must be compared against the existing Capstan type system and C-free/CCAM roadmap before selection. Do not introduce a parallel ownership model inside Keel.

## 4. Mesh publication protocol

Once the Capstan capability exists, the mesh builder should follow this protocol:

1. Reserve a bounded byte budget for vertex data, index data, metadata and canonicalisation scratch.
2. Validate input counts and checked byte arithmetic before allocating owned storage.
3. Copy or consume source data into private construction storage; no source alias is retained.
4. Validate every coordinate and index; reject repeated triangle indices and exact zero-area triangles.
5. Apply the selected duplicate-position, duplicate-face and canonical-order policies while preserving a source-to-canonical provenance map where requested.
6. Construct bounds and topology summaries from the canonical data, not from the untrusted source arrays.
7. Publish one immutable mesh value only after every invariant succeeds.
8. On any failure, discard the unpublished builder and release its reservation through the defined resource-accounting mechanism.

The published mesh contract must distinguish geometric validity from topology classes. A mesh may be valid triangle soup without being a two-manifold, connected, closed, orientable, self-intersection-free or suitable for a particular physics solver. Those are separate predicates or stronger types.

## 5. Topology policy to resolve before implementation

The initial policy should preserve general-purpose use while making stronger guarantees explicit:

- **Duplicate positions:** distinct vertex indices with equal coordinates are permitted in raw geometry. Welding is an explicit canonicalisation operation because it can change seams, material boundaries, normals and provenance.
- **Duplicate faces:** exact duplicate index triples should be reported by a diagnostic; whether they are rejected or retained is a format/import policy, not a hidden side effect.
- **Disconnected components:** permitted in a general mesh. Connected-component labels are derived metadata.
- **Boundary edges:** permitted for open surfaces; count and classify them.
- **Non-manifold edges/vertices:** representable in general geometry, but classified and rejected by algorithms that require manifold input.
- **Winding:** preserve source winding. A separate orientation analysis reports inconsistent adjacent-face orientation; automatic repair must be explicit and provenance-preserving.
- **Self-intersection:** not implied by triangle non-degeneracy or edge incidence. Robust triangle-triangle intersection is a separate bounded operation.
- **Degenerate faces:** rejected by the current exact non-collinearity test; stronger scale/area tolerances do not belong in this integer predicate.

A topology report must state its domain and complexity. It must not label a mesh simply “valid” without naming the properties checked.

## 6. BVH contract and algorithm research

The first acceleration structure should be a CPU-only bounding-volume hierarchy over immutable triangle geometry. GPU acceleration is out of scope until the reference query contract is stable.

The initial candidate is a deterministic binary BVH with:

- closed integer AABBs over the current bounded coordinate domain;
- a stable split rule with deterministic tie-breaking by canonical primitive ID;
- a hard maximum node count and depth;
- a bounded explicit traversal stack (or a separately proven stackless traversal);
- leaves with bounded primitive counts and stable ranges into immutable primitive-ID storage;
- checked construction work and scratch-memory budgets;
- a defined empty-input and allocation-failure result;
- query results ordered by a documented key, not by incidental traversal order.

A median split on the longest centroid axis is a reasonable baseline, but it is not preselected as optimal. Compare it with midpoint partitioning and a bounded binned surface-area heuristic. The comparison must include build time, node/leaf count, depth, memory, worst-case traversal work, query distributions and update cost. No unbounded recursive builder is acceptable.

The first query set should be AABB overlap and bounded ray/triangle candidate enumeration. Exact ray intersection is blocked on a documented numeric model: the current integer coordinate domain is sufficient for AABBs and integer orientation predicates, but it does not by itself define a useful general ray parameter, division, tie policy or floating-point error contract. Do not invent a real-number model inside the BVH.

## 7. Refit, rebuild and stale-data rules

A BVH is derived data. It must identify the exact immutable mesh version it indexes.

- An immutable mesh never changes in place.
- A geometry edit creates a new mesh version or a new builder; it does not mutate storage underneath an existing BVH.
- Refit is permitted only when primitive identity and topology remain stable and the update protocol can prove every affected bound is recomputed.
- Topology or index changes require a rebuild.
- Queries against a BVH/mesh version mismatch fail closed.
- Incremental updates must be budgeted and deterministic; otherwise rebuild is the safe baseline.

## 8. Required verification and performance evidence

Before accepting the mesh owner:

- alias/mutation tests showing published storage cannot be changed through source or derived aliases;
- failure injection at every allocation/publication stage;
- byte-accounting tests including overflow and aggregate exhaustion;
- compiler/runtime tests proving consume/borrow rules survive lowering and optimisation;
- GC stress tests that do not confuse logical ownership with physical reclamation;
- mutation tests that deliberately reintroduce writable aliases.

Before accepting the BVH:

- differential AABB-query tests against brute force;
- deterministic-build tests across repeated runs and input permutations where canonical IDs are held fixed;
- adversarial distributions: coincident centroids, identical bounds, sorted inputs, highly elongated geometry, clustered geometry and maximum-depth cases;
- maximum-node, maximum-stack and maximum-work tests;
- query-result equivalence after refit versus rebuild;
- benchmark suites with raw data for build, memory, traversal and update costs.

The BVH must never be used as a correctness oracle: brute-force geometry remains the reference for differential tests.

## 9. Current implementation boundary

Until the Capstan ownership capability is implemented and validated:

- `keel_mesh3_valid` remains a call-time validator;
- `keel_mesh3_bounds` remains an independent call-time bounds calculation;
- callers must not cache validation as a trust token for mutable lists;
- Keel must not publish a persistent mesh object or retain source arrays;
- no BVH, adjacency cache or topology cache may retain caller-owned mutable arrays.

This is a deliberate safety gate, not a claim that the work is complete.
