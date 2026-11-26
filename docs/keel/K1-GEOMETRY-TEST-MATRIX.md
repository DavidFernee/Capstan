# Keel K1 geometry kernel: test and assurance matrix

**Status:** implementation exists; validation is pending exact-head CI.  
**Implementation:** `lib/keel/coordinates.cap`, `predicates.cap`, `spatial.cap`, `polygon.cap`.  
**Harness:** `tests/keel/check.py`, invoked by `tests/run.sh`.

This matrix records the executable scope rather than implying a general-purpose geometry kernel.

## Numeric domains and failure semantics

| Surface | Domain / bound | Failure behaviour |
|---|---|---|
| 2D coordinates and orientation | Each coordinate in ±(2^30−1) | Out-of-domain input returns `none` before determinant arithmetic |
| 3D coordinates and orientation | Each coordinate in ±(2^18−1) | Out-of-domain input returns `none` before determinant arithmetic |
| 3D vector components | Each component in ±(2^18−1) | Invalid operand or result outside component domain returns `none` |
| 3D AABB endpoints | Valid 3D coordinate domain; minimum must not exceed maximum | Invalid bounds or query points return `none` |
| 2D polygon ring | 3–256 implicit-closure vertices in the 2D domain | Invalid, degenerate, non-simple, oversized or out-of-domain rings classify as `none` |

The exact-integer determinant bounds are documented beside the implementations. They depend on the input-domain checks being performed before arithmetic. Do not widen a domain or change an intermediate expression without re-deriving its bound.

## Differential and property coverage

| Kernel | Oracle / properties exercised |
|---|---|
| 2D orientation | Python arbitrary-precision determinant; random inputs, all vertex permutations, collinearity, duplicate vertices, near-zero determinants, exact extrema and every coordinate-validation position |
| 3D orientation | Python arbitrary-precision determinant; random inputs, all vertex permutations, coplanarity, exact extrema and every coordinate-validation position |
| 2D segment relation | Disjoint, point touch, proper crossing and positive-length collinear overlap; zero-length segments; endpoint reversal; segment-pair swapping; random pairs; invalid coordinates |
| Point in tetrahedron | Outside, boundary and strict interior; degenerate tetrahedra; vertex permutations; random cases; every coordinate-validation position |
| 3D vectors | Add/subtract/dot/cross/squared length; random moderate and full-domain inputs; invalid operands; result overflow relative to vector domain; direct fit-guard calls with signed-int64 extremes |
| 3D AABBs | Construction, closed-boundary containment/intersection, disjoint/touching/degenerate boxes, union, invalid endpoint order and out-of-domain inputs |
| 2D polygons | Exact winding-number classification; inside/outside/edge/vertex; reversed winding; concavity; bow-tie self-intersection; repeated closure/contact; zero-length edge; collinear ring; adjacent backtracking; invalid coordinates; maximum valid 256-vertex ring and rejected 257-vertex ring |

The fixed PRNG seed makes generated cases reproducible. The Python oracle is test-only and uses arbitrary-precision integers; it is not linked into or shipped with Keel.

## Polygon contract

A polygon is one implicit-closure ring. Holes and multi-ring topology are not represented. The simplicity validator compares every edge pair and is therefore $O(n^2)$; the hard cap of 256 vertices bounds this work. Consecutive edges may meet at their shared endpoint only. Non-adjacent contacts, crossings and positive-length overlaps are invalid. A ring must contain a non-collinear triple.

Point classification uses an exact winding-number crossing rule and returns:

- `-1`: outside;
- `0`: on the boundary;
- `1`: strictly inside;
- `none`: invalid point or invalid ring.

No division, epsilon, floating-point conversion or constructed intersection is used by this classifier. Because only simple rings are accepted, the Jordan-curve interior is unambiguous and even-odd/nonzero fill rules agree. Self-intersecting paths are rejected rather than assigned a fill rule; supporting them later requires an explicit semantic choice and dedicated crossing/tangency tests (see Hormann and Agathos, [The Point in Polygon Problem for Arbitrary Polygons](https://doi.org/10.1016/S0925-7721(01)00012-8)).

## Explicit exclusions

This increment does not implement polygon clipping/booleans, planar arrangements, holes, triangulation, mesh validation, general 3D surface intersections, exact constructions, affine/projective transforms, ray/plane intersections, floating-point or fixed-point simulation, or a general world-coordinate convention. Each requires its own numeric, complexity, construction and adversarial-test contract.

## Acceptance rule

The suite is accepted only when the exact PR head completes the standard CI workflow successfully, including the Keel differential harness under the repository's supported compiler configurations. A queued, cancelled, stale-head or partial run is not a pass. Formal verification and CodeQL results are tracked separately; neither substitutes for runtime differential tests.
