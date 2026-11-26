# Exact polygon simplicity: sweep-line research gate

**Work package:** KR-13 — Robust bounded polygon topology  
**Status:** research specification only; no sweep-line implementation is claimed  
**Baseline:** `lib/keel/polygon.cap` and its exact segment predicates  
**Scope:** deciding whether a bounded closed ring is simple; not polygon arrangement or boolean construction

## 1. Decision to be made

The current validator compares every pair of edges. Its worst-case pair count is bounded by the 256-vertex input cap and is easy to audit. A plane-sweep algorithm may reduce asymptotic work, but only if its ordering and degeneracy rules are exact, complete and cheaper at the supported size.

The experiment must compare three choices:

1. retain the current quadratic validator;
2. use an endpoint sweep with grouped equal-coordinate events and an exact active-set ordering;
3. use a different exact bounded spatial partition, if a credible candidate emerges.

Do not select an implementation based on asymptotic notation alone. At (n \le 256), constant factors, memory, auditability and hostile-input worst cases may favour the quadratic baseline.

## 2. Normative input and output semantics

The candidate must preserve the current public contract exactly:

- Ring size is between 3 and 256 vertices inclusive.
- Every coordinate is in the existing exact 2D coordinate domain.
- Consecutive duplicate vertices and zero-length edges are rejected.
- A wholly collinear ring is rejected.
- Consecutive edges may meet at their one common endpoint, including the closing edge pair.
- Any other contact, proper crossing or positive-length collinear overlap is rejected.
- The point classifier continues to distinguish outside, boundary and strict interior.
- Invalid domain values return the existing controlled invalid result.
- No partial mutation or externally visible scratch state survives failure.

This work does not define fill rules for self-intersecting paths, planar arrangements, polygon booleans, triangulation or constructed intersection coordinates.

## 3. Why the comparator is the central risk

A textbook sweep often assumes general position: no shared event coordinates, no vertical segments, no collinear overlaps and no multi-way intersections. Keel's ring contract makes no such assumptions. Importing a general-position comparator would silently narrow the accepted input domain and is therefore unacceptable.

The design must define a total deterministic event key over endpoint coordinates and stable edge identity. All events at the same geometric coordinate must be processed as a single event group, not in arbitrary insertion order.

The active-set ordering must be mathematically specified for the open slab immediately to the right or left of an event group. The chosen convention must be used consistently by insertion, deletion, neighbour lookup and tie-breaking. Comparisons must not construct rounded intersection coordinates or depend on mutable comparator results while an ordered tree contains elements.

A proposal that merely compares segment y-values at the current sweep x is insufficient until it proves transitivity and stability at shared endpoints, equal-y events, vertical edges and collinear segments.

## 4. Event-group obligations

For each coordinate group, specify and justify the complete treatment of:

- left and right endpoints under the chosen sweep direction;
- vertical edges, including their interaction with every segment meeting the same x-coordinate;
- multiple endpoints at the same point;
- endpoint-on-edge contacts;
- several edges incident at one event point;
- collinear segments with disjoint, touching or overlapping intervals;
- adjacent polygon edges, whose one shared endpoint is permitted;
- non-adjacent edges, for which every contact is forbidden.

The group update must be atomic with respect to the status invariant. State precisely which edges are removed, retained, inserted and checked, and how all incident edges are identified. A single predecessor/successor test is not automatically sufficient for a multi-edge event.

Collinear overlap requires a dedicated exact interval rule. It must not be treated as an ordinary proper crossing or hidden by an event tie-break.

## 5. Required proof obligations

A candidate is not implementation-ready until a reviewer can assess all of the following.

### P1 — Event completeness

Every endpoint and every forbidden intersection/contact that could invalidate the ring is either directly detected by event-group processing or is guaranteed to become a tested neighbour pair before it can be missed.

### P2 — Status invariant

At every point between event groups, the status contains exactly the non-vertical edges intersecting the open sweep slab, with the declared order and tie-break.

### P3 — Comparator correctness

The comparator is deterministic and transitive over every simultaneously active pair. Its ordering is consistent for the entire lifetime of each status element between atomic event updates. It does not depend on mutable external sweep state in a way that invalidates the ordered structure.

### P4 — Degeneracy completeness

Vertical, horizontal, equal-x, equal-y, coincident endpoint, multi-way contact and collinear cases are all handled. No general-position precondition may be left implicit.

### P5 — Neighbour sufficiency

The algorithm proves that any forbidden pair must become adjacent and be tested, or provides another complete detection mechanism. State the argument for both insertion and deletion events and for event groups with more than two incident edges.

### P6 — Bounded resources

Give worst-case bounds for event records, active-set size, comparisons, exact arithmetic operations, temporary storage and work per event group. Include adversarial inputs that maximise tie groups and vertical-edge interactions.

### P7 — Failure atomicity and determinism

Resource exhaustion, invalid input and internal consistency failures produce a controlled result. Repeated runs on identical input produce identical results and diagnostic ordering.

If any proof requires a stronger precondition than the public ring contract, that precondition must be explicitly checked or the candidate must be rejected.

## 6. Differential and adversarial evidence

The current quadratic implementation remains the reference implementation. The independent test oracle uses arbitrary-precision integer arithmetic and must not share the candidate's event-ordering code.

Required generated families:

- random simple and non-simple rings with published fixed seeds;
- every cyclic rotation and both winding directions;
- repeated vertices and zero-length edges at every index;
- endpoint-on-edge and non-adjacent endpoint contacts;
- proper crossings with integer endpoints;
- collinear disjoint, point-touching and positive-overlap pairs;
- vertical and horizontal edges;
- large groups of equal-x and equal-y endpoints;
- several segments meeting at one coordinate;
- narrow concavities and near-collinear triples;
- maximum-size 256-vertex rings;
- coordinates at both domain extrema and one step outside;
- adversarial rings designed to maximise active-set ties and group sizes.

For every case, compare acceptance/rejection with the quadratic implementation and independent oracle. Apply rotation and winding-reversal metamorphic tests. Preserve each discovered mismatch as a fixed regression.

Mutation tests must demonstrate detection of at least: reversed event ordering, omitted vertical-edge handling, incorrect collinear interval logic, non-atomic group updates, and a broken neighbour check.

## 7. Complexity and benchmark protocol

Publish separate worst-case counts for:

- endpoint/event records and peak queue storage;
- active-set entries;
- comparator calls;
- exact integer operations per comparator;
- total temporary storage;
- maximum work for one event group;
- invalid-input and early-rejection paths.

Do not claim (O(n \log n)) from the general-position algorithm if the actual degeneracy policy has a larger bound. Derive the bound for the implemented algorithm.

Benchmark both candidates on the same pinned compiler, runtime, host and input corpus. Include random, adversarial, maximum-size and early-rejecting rings. Report p50/p95/p99 latency, comparisons, peak memory and rejected-input cost. The sweep candidate must demonstrate a material benefit at the supported cap without weakening semantics or increasing the worst-case resource envelope unacceptably.

## 8. Acceptance gate

The sweep candidate may replace the quadratic validator only when:

1. event ordering and event-group semantics have been independently reviewed;
2. P1–P7 are supported by proofs or bounded executable refinement arguments;
3. differential, metamorphic, adversarial and mutation suites pass at the exact branch head;
4. worst-case resource bounds include all degeneracies and malformed-input paths;
5. benchmarks show a material improvement at the supported 256-vertex cap;
6. all shipped implementation and support code is original Capstan code;
7. the vulnerability register, research register and geometry test matrix record evidence and residual risks.

Until every gate passes, the existing bounded quadratic implementation remains normative. This document does not claim that a sweep-line implementation exists, is correct, is faster, or has been formally verified.
