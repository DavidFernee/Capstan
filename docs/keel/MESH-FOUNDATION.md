# Keel K1 mesh foundation

**Status:** initial bounded triangle-mesh validation implementation and focused conformance tests; not a complete mesh asset format or renderer contract.  
**Implementation:** `lib/keel/mesh.cap`  
**Tests:** `tests/keel/mesh_check.py`, invoked by `tests/run.sh`

## 1. Scope

The first mesh increment establishes a narrow, auditable input boundary for indexed triangle geometry. It does not define materials, vertex attributes, normals, tangents, UV sets, skinning, morph targets, meshlets, compression, GPU buffers, serialization or ownership transfer.

The module deliberately validates caller-owned lists without retaining them. A successful result describes the supplied values at validation time only. It is not a persistent validated asset handle: callers must not assume the lists remain valid after mutation.

## 2. Data contract

An indexed mesh is represented at the call boundary by:

- a non-empty list of 3D positions;
- a non-empty index list whose length is divisible by three;
- each consecutive index triple describing one triangle.

Current explicit limits:

| Quantity | Limit |
|---|---:|
| Vertices | 65,536 |
| Indices | 393,216 |
| Triangles | 131,072 |
| Coordinate component | (pm(2^{18}-1)) |

These are element-count limits, not byte-allocation guarantees. An owning asset container must enforce byte budgets before constructing the lists.

All vertices, including unreferenced vertices, must lie in the exact coordinate domain. Unreferenced vertices are permitted in this first increment and contribute to the computed bounds. A future canonicalisation stage may remove them, but must preserve a documented source-to-canonical mapping.

Every triangle must satisfy:

- all three indices are non-negative and strictly less than the vertex count;
- all three indices are pairwise distinct;
- the three referenced positions are not collinear.

The geometric non-degeneracy check uses the exact integer cross product. Coordinate differences are less than (2^{19}); each product is less than (2^{38}), and each cross-product component is a difference of two such products, so signed 64-bit arithmetic is sufficient. The result is only a zero/non-zero test; the cross product is not returned as a public vector.

## 3. Failure semantics

- Unsupported counts, empty geometry, malformed index cardinality, out-of-range indices, repeated triangle indices and degenerate triangles return `false`.
- An out-of-domain vertex returns `none`, distinguishing invalid numeric input from a structurally invalid mesh.
- Bounds computation independently validates count and every coordinate. Empty, oversized or out-of-domain input returns `none`.
- Neither operation mutates caller data or retains references.
- No allocation is performed by the validation routines themselves beyond the caller's existing lists.

The boolean/optional distinction is intentional and must remain consistent across subsequent geometry APIs.

## 4. Bounds

`keel_mesh3_bounds` computes the closed axis-aligned bounds over every vertex. It validates its own inputs and does not assume mesh validation was previously performed. It does not validate topology or indices.

The current bounds are in the same narrow integer coordinate domain as the input positions. They are not world-space bounds and carry no unit, handedness, origin or frame semantics.

## 5. Call-time topology incidence report

`keel_mesh3_topology(vertices, indices)` first applies the full mesh validator, then computes a deterministic edge/face incidence summary without retaining either caller list. It returns `none` for invalid input.

The report contains:

- unique undirected edge count;
- boundary edges (one incident face);
- edges with exactly two incident faces;
- non-manifold edges (more than two incident faces);
- two-face edges whose incident faces traverse the edge in the same direction;
- duplicate faces, counted as extra occurrences independent of winding; 
- connected components of the referenced-vertex graph; 
- referenced and isolated vertex counts.

Edges are represented by packed bounded vertex-index pairs plus a direction bit. Face keys are canonical sorted triples. Both arrays are integer-sorted and scanned, giving (O(T \log T)) comparisons and (O(T)) scratch entries for (T) triangles. The fixed triangle/index/vertex caps therefore bound the scratch element counts: at most three edge codes and one face key per triangle, plus one parent/rank/reference entry per vertex and the integer merge-sort temporary arrays. This is an element/work bound, not yet a pre-allocation byte-budget guarantee. Integer packing remains below (2^{33}) for directed edges and (2^{48}) for faces.

Connected components are computed with an iterative union-find structure using path compression and union by rank. Isolated vertices are vertices absent from every triangle. This report does not establish vertex-manifoldness, orientability of an entire component, watertightness, geometric self-intersection freedom or physical validity. Duplicate positions with different indices are not welded. Duplicate faces are reported, not rejected by the base mesh validator. It is a diagnostic classification, not a universal mesh-validity predicate. The focused test harness includes hand-constructed degeneracy fixtures and 64 deterministic random meshes compared against a separate Python arbitrary-precision oracle for edge incidence, winding, duplicate faces and connected components.

## 6. Known limitations and next gates

This is not yet a safe persistent mesh object. The next increment must decide ownership and immutability using Capstan's actual collection/runtime semantics, not an ad hoc copy convention. A validated mesh asset should eventually own immutable canonical arrays and a precomputed bounds record, with all count and byte budgets charged to an explicit owner.

Before broadening the representation, add:

1. property-based generation of valid and invalid indexed meshes;
2. differential tests for bounds against an independent arbitrary-precision oracle;
3. exhaustive index-boundary cases, including negative and maximum integer indices;
4. maximum-count and resource-exhaustion tests;
5. mutation-after-validation tests demonstrating why the current API is a validation operation rather than a persistent trust token;
6. an independently reviewed ownership/immutability design;
7. independent topology oracles and mutation tests for edge packing, incidence grouping, duplicate-face counting and winding classification;
8. topology policy decisions for duplicate positions, disconnected components, vertex-manifoldness, orientability and self-intersection.

No manifoldness, watertightness, orientability, self-intersection freedom, physical validity or GPU safety is implied by `keel_mesh3_valid`. Those are separate properties with separate algorithms and evidence gates.
