# Mesh topology assurance: vertex links, orientation and intersections

**Status:** research design and acceptance contract. This document does not claim that these properties are implemented or proved.

## Purpose

The current mesh report classifies edge incidence, duplicate indexed faces, connected components and referenced/isolated vertices. Those facts are useful but are not a manifoldness certificate. In particular, an edge-manifold complex can still have a non-manifold vertex: two otherwise separate surface fans may meet at one indexed vertex. A mesh can also have locally consistent edge incidence yet contain a globally non-orientable component, or have geometrically intersecting triangles whose indices do not reveal the intersection.

The next topology increment is split into three independent predicates. Each returns a structured classification, not a single overloaded `valid` bit.

## 1. Vertex-link manifoldness

For a vertex v, construct its link multigraph:

- each incident triangle (v,a,b) contributes one link edge (a,b);
- link vertices are the distinct indexed neighbours of v;
- repeated link edges remain repeated and must not be silently deduplicated.

For a 2-manifold triangle complex, the link of each referenced vertex must be exactly one connected cycle (interior vertex) or one connected path (boundary vertex). A cycle has degree two at every link vertex. A path has exactly two degree-one vertices and all remaining vertices degree two. Branching (degree greater than two), multiple components, duplicate link edges, or any other degree sequence is a defect. A vertex with an empty link is isolated and is already reported separately.

This criterion must be evaluated only after edge incidence is known. Edges with more than two incident faces make the local surface classification non-manifold before vertex links are interpreted. The report should retain enough detail to distinguish:
- manifold interior vertices;
- manifold boundary vertices;
- disconnected link fans (pinched vertices);
- branching links;
- duplicate/parallel link edges;
- malformed or unsupported incidence.

A global count alone is insufficient for diagnostics. The API should expose bounded counts and, in a later diagnostic mode, stable offending vertex IDs. IDs must be deterministic and must not expose mutable internal storage.

### Complexity and storage

The target is O(T log T) time and O(T+V) scratch entries, where T is triangle count and V is vertex count. Do not implement per-vertex rescans of the entire triangle list (O(VT)). Candidate implementations should sort canonical link incidences keyed by (centre vertex, neighbour vertex), then build per-centre adjacency ranges. Connectivity must be checked without allocating an unbounded per-vertex object graph. The final design must account for all sort temporaries and adjacency/union-find arrays against the runtime's byte budget before allocation.

A degree-sequence-only test is not accepted: it misses two disjoint cycles or paths sharing the same centre vertex. Connectivity of each link is a required invariant.

## 2. Component-wide orientability

The current `inconsistent_winding_edges` field is a property of the supplied face ordering: it counts two-face edges traversed in the same direction. It is not a test of whether the underlying connected surface can be oriented.

For each edge with exactly two incident faces, derive a parity constraint between those faces:
- if their current directed traversals along the shared undirected edge are opposite, their flip bits must be equal;
- if their traversals are the same, exactly one face must be flipped.

This gives a signed dual-graph constraint system. Solve it per connected face component using a parity disjoint-set structure or bounded breadth-first traversal. A contradictory parity cycle means the component is non-orientable. Boundary edges impose no constraint. Edges with more than two incident faces are outside the ordinary 2-manifold orientability contract and must be reported separately rather than assigned an arbitrary pairwise rule.

The result should distinguish:
- orientable component;
- non-orientable component (contradictory parity cycle);
- indeterminate component because it contains non-manifold edge incidence;
- isolated/degenerate cases rejected by the input contract.

The algorithm must be invariant under reordering triangles and under independently reversing any subset of input face windings. The number of local winding conflicts may change under such reversals; orientability must not. This metamorphic property is a mandatory test.

## 3. Geometric self-intersection

Combinatorial topology cannot detect geometric intersections between triangles with unrelated indices. A self-intersection predicate must therefore operate on positions as well as index adjacency.

The first implementation should be a bounded, deterministic reference algorithm, not an unbounded all-pairs production routine:
1. Generate a conservative closed AABB for each triangle using checked coordinate operations.
2. Enumerate candidate pairs in stable triangle-ID order, excluding only pairs whose shared indexed simplex is explicitly permitted by the declared policy.
3. Apply exact integer/rational narrow-phase predicates for triangle-triangle intersection.
4. Classify proper crossing, coplanar positive-area overlap, non-coplanar touch, shared-edge/shared-vertex contact, and disjointness separately.
5. Return `none` on arithmetic-domain failure or budget exhaustion; never silently treat an unclassified pair as disjoint.

The policy for coincident positions with different vertex indices must be explicit. Topological adjacency is based on indices; geometric coincidence is based on coordinates. Welding is a separate canonicalisation operation and must not happen implicitly during validation.

A production broad phase (BVH, sweep structure or spatial hash) is a later optimisation and must be differential-tested against the bounded reference implementation. The reference pair cap, candidate cap, sort storage and narrow-phase operation budget must be enforced before work begins. Exact coplanar handling is mandatory; a floating-point epsilon test is not an acceptable substitute.

## 4. Shared evidence protocol

Each predicate requires:
- a formal input domain and explicit overflow proof for every intermediate;
- a Capstan-native implementation, with no C or third-party geometry library implementation;
- an independent arbitrary-precision oracle;
- exhaustive small-complex enumeration where feasible;
- deterministic generated tests with recorded seeds;
- metamorphic tests (triangle permutation, vertex renaming, face reversal, component translation within the coordinate domain);
- adversarial fixtures for pinched vertices, disconnected links, branching links, duplicate faces, non-orientable complexes, coplanar overlap, near-degenerate contact and coordinate extrema;
- mutation tests that deliberately break incidence grouping, parity propagation, link connectivity and intersection classification;
- exact pre-allocation byte accounting and explicit work limits;
- benchmark comparisons against the current edge/face incidence baseline.

Tests must distinguish a bug in the oracle from a bug in the implementation by retaining minimized counterexamples and, where practical, a second independent formulation.

## 5. Acceptance gates

| Gate | Required evidence | Blocks |
|---|---|---|
| VT-1 | Vertex-link graph definition, edge-case policy and complexity proof | Any vertex-manifold claim |
| VT-2 | Capstan implementation plus independent and exhaustive-small oracles | Integration of vertex-link report |
| OR-1 | Parity-constraint specification and proof of reversal/permutation invariance | Any orientability claim |
| OR-2 | Capstan implementation, contradictory-cycle fixtures and metamorphic oracle | Integration of component orientability |
| SI-1 | Exact triangle-triangle classification including coplanar cases and explicit contact policy | Any self-intersection claim |
| SI-2 | Bounded reference implementation, differential broad-phase tests and hostile corpus | Production self-intersection validation |
| OWN-1 | Compiler/runtime-enforced ownership and byte-exact pre-allocation accounting | Persistent trusted mesh assets and retained acceleration structures |

No gate is satisfied by this document. The existing topology report remains a stateless incidence summary. Mesh ownership and BVH publication remain blocked on the language/runtime contracts in [Mesh Ownership and BVH Design Gates](MESH-OWNERSHIP-AND-BVH.md).

## 6. Research hazards and mitigations

- **False manifoldness from edge-only tests:** require connected vertex links, not merely edge incidence.
- **False orientability from local winding counts:** solve the global parity constraints and test invariance under arbitrary face reversals.
- **Missed coplanar intersections:** implement exact coplanar projection/overlap classification as part of the narrow phase.
- **Topology/geometry conflation:** keep indexed adjacency and coordinate coincidence separate.
- **Resource exhaustion:** cap candidate pairs and all scratch arrays before allocation; return a distinct budget-exhausted result.
- **Nondeterministic diagnostics:** sort stable IDs and never rely on hash iteration order.
- **Proof laundering:** state separately what is proved about the mathematical model, the Capstan source, generated code and runtime execution.

## 7. Non-goals

This increment does not choose a universal policy for non-manifold assets, automatically repair meshes, weld duplicate positions, generate normals, build a persistent mesh asset, or implement a BVH. Those are separate decisions with provenance, determinism and resource implications.


## 8. Vertex-link implementation refinement: compact incidence indexing

The O(T+V) storage target can be met without a dense V-by-V table and without resetting a V-element disjoint-set for every centre vertex. The implementation should use compact endpoint records.

For each input triangle (a,b,c), emit three link edges:
- centre a: link edge (b,c);
- centre b: link edge (c,a);
- centre c: link edge (a,b).

There are exactly 3T link edges and 6T endpoint occurrences. For every endpoint occurrence emit a record containing:
- the composite key (centre, neighbour);
- the link-edge ordinal;
- which endpoint of that link edge it represents.

The composite key is `centre * 65536 + neighbour`. Since both indices are in [0,65535], it is at most 2^32−1 and fits signed int64. Sort endpoint records by (composite key, link-edge ordinal, endpoint side). Scan equal composite keys and assign one compact node ID to each distinct (centre, neighbour). Write that compact ID into the endpoint slot for its link-edge ordinal and side. The resulting number of link nodes is at most 6T; no dense V² allocation is required.

Allocate union-find parent/rank arrays sized to the actual compact-node count, then union the two compact endpoint IDs for each of the 3T link edges. Each compact node belongs to exactly one centre because the centre is part of its key. Consequently, a single global union-find is safe: it cannot accidentally connect links belonging to different centre vertices.

For diagnostics, the sorted endpoint records also provide contiguous ranges of compact nodes for each centre. Accumulate each node's link degree by counting endpoint occurrences. Separately sort canonical link-edge keys `(centre, min(neighbour_a, neighbour_b), max(neighbour_a, neighbour_b))`; any key with multiplicity greater than one is a repeated/parallel link edge and is a defect. This duplicate check must preserve multiplicity rather than collapsing it before degree accumulation.

For each centre with incident triangles:
- count compact link nodes and link edges;
- count distinct union-find roots among its compact nodes;
- inspect every node degree;
- classify as a cycle iff there is exactly one link component and every node has degree two;
- classify as a path iff there is exactly one link component, exactly two nodes have degree one, and all remaining nodes have degree two;
- classify every other case as defective, with separate flags/counts for repeated edges, branching degrees, and disconnected components.

The classification is only a local link-shape criterion. The whole mesh is vertex-manifold only if every referenced vertex has an accepted path or cycle link and the edge-incidence policy is also satisfied. A vertex incident to an edge with more than two faces must remain explicitly non-manifold/indeterminate; do not let an apparently cycle-shaped link override the edge defect.

### Resource accounting

At the current T cap of 131072:
- link edges: at most 3T = 393216;
- endpoint records: at most 6T = 786432;
- compact link nodes: at most 6T = 786432;
- union-find entries: at most 6T = 786432;
- duplicate-edge keys: at most 3T = 393216.

These are cardinality maxima, not byte budgets. Before allocating, the implementation must compute checked byte totals for every record array, sort temporary, compact-ID slot, parent/rank array and diagnostic accumulator. The total must be compared with a configured mesh-topology scratch budget. If the runtime cannot provide reliable element-size and allocation-failure semantics, this predicate must remain unavailable rather than claiming a hard memory bound. Avoid retaining both the full endpoint records and an equally large sort temporary unless both are included in the byte budget.

The comparison count is O(T log T); scanning, compaction, union-find and degree aggregation are O(T α(T)) or O(T). Stable secondary sort keys make diagnostics independent of sort implementation details. The input triangle order may affect original edge ordinals, but must not affect classification counts; stable diagnostic IDs should be derived from canonical vertex-index keys, not emission order.

### Required differential and metamorphic tests

The independent oracle must construct each vertex link directly from triangles and classify connected components without reusing the compact-indexing algorithm. Include:
- two closed fans sharing exactly one centre vertex (two cycles, rejected);
- two open fans sharing exactly one centre vertex (two paths, rejected);
- a single valid interior fan and a single valid boundary fan;
- a branching link (degree three or greater);
- repeated triangles producing parallel link edges;
- a link with degree pattern that appears path-like but has two disconnected components;
- edge-non-manifold input, which must not be reported vertex-manifold;
- unused vertices, which remain isolated rather than receiving an empty path/cycle classification.

Permuting triangles and cyclically rotating each triangle must preserve all classifications. Reversing arbitrary subsets of triangle winding must preserve vertex-link shape. Renaming vertices through a bijection must preserve counts and classifications after mapping diagnostics back through that bijection.


## 9. Current Capstan collection/runtime blocker (source audit)

The compact algorithm above is a viable data-structure design, but the current source-level collection API is not yet sufficient to enforce its promised byte budget:

- `List<int>.sort()` lowers to the runtime's `cap_list_sort_i`. The current runtime allocates a `CapVal` temporary array of length `List.len` before merge sort. The temporary allocation is additional to the list backing array.
- `List<T>.push()` grows backing storage through a capacity-growth policy. A bound on final list length is therefore not, by itself, an exact bound on allocated capacity or cumulative allocation.
- The current sort API does not return an allocation-failure result or accept a caller-supplied scratch buffer/budget.
- The current Keel mesh source is compiled through the existing generated-C/runtime path. It is not a C-Free native implementation and must not be presented as one.

Consequently, a source-level preflight calculation based only on logical element counts cannot prove the peak bytes consumed by a sequence of List allocations and sorts. The algorithm remains a research design until one of the following is delivered and verified:

1. a Capstan-native bounded scratch-buffer abstraction whose capacity and byte accounting are explicit and whose sort operates in caller-owned scratch; or
2. a runtime collection/sort contract that exposes exact capacity, checked reservation, bounded allocation admission and failure as a recoverable result, with formal and fault-injection evidence.

The preferred direction is (1), provided it is genuinely implemented in the C-Free execution path rather than merely wrapping the existing C runtime. Until then, do not add a production `keel_mesh3_vertex_links` API that claims a hard byte bound. A test-only oracle or bounded small-input prototype may be used to validate the mathematics, but must be labelled accordingly.
The cross-cutting proposed remedy is specified in [C-Free Bounded Scratch Memory](C-FREE-BOUNDED-SCRATCH.md). That proposal deliberately places the next decision in the CCAM memory model; it does not make the current List/sort path bounded and does not authorise a production vertex-link implementation.
