# Shroud: bounded path and raster work

## Status

Design gate for the next S0 resource-safety increment. This document does not claim
that the renderer is already bounded, nor does it select production limits before
measuring representative workloads. The limits become normative only when the
implementation, adversarial tests, and benchmark evidence land together.

## Problem statement

Shroud currently caps curve flattening at `MAX_CURVE_SEGMENTS = 64` per curve.
That is a useful local bound, but it is not a path or frame bound:

- a path can contain an unbounded number of verbs and points;
- a path can contain an unbounded number of individually bounded curves;
- flattening allocates segment arrays proportional to the aggregate curve output;
- `fill_segments` scans all edges for every pixel row, then scans row edges on
  each of 16 sub-scanlines and sorts the resulting crossings;
- the cost is multiplied across every path painted in a frame.

The current pixmap pixel cap bounds destination allocation, not the work required
to produce those pixels. A small path with long vertical edges or many overlapping
edges can therefore cause disproportionate CPU work even when each curve respects
its local segment cap.

## Required resource model

The implementation must enforce three nested budgets.

### 1. Path construction and flattening

A path has explicit limits for:

- verbs and encoded points;
- flattened segments;
- arithmetic range of every coordinate and intermediate curve expression.

Every verb has a fixed point arity. Appending a verb must preserve the invariant
that the verb count and point count agree exactly with the sum of those arities.
Malformed or over-limit paths become invalid; they must never be silently
truncated into a different shape.

Flattening must stop as soon as its segment budget is exhausted. It must return
an explicit invalid/over-budget result rather than a partial segment list that
could be mistaken for a complete contour. The per-curve 64-segment cap remains
a quality bound, not the aggregate resource policy.

### 2. Raster operation budget

Each frame receives one shared raster-work budget, consumed by all paint calls.
A per-path or per-widget budget alone is insufficient because an attacker can
multiply individually acceptable paths.

The work counter must conservatively account for at least:

- path/segment validation and edge preparation;
- edge-versus-row candidate tests;
- sub-scanline crossing candidate tests;
- crossing ordering (charge a conservative comparison bound, not merely the
  number of crossings);
- span/coverage updates;
- pixel blends.

The accounting must use checked or subtraction-based arithmetic. No counter
update may overflow, wrap, become negative, or increase the remaining allowance.
The budget must be shared across nested clips and all widgets in the frame.

### 3. Frame publication and failure atomicity

A budget failure must not publish a partially rendered frame. The renderer must
either:

1. complete the frame within the budget and publish it; or
2. discard the incomplete surface and publish a deterministic, safe fallback
   frame (the window background plus a diagnostic available to the host).

The fallback must not retain stale pixels from the previous frame. Input hit
testing must not treat an incomplete frame as a successfully presented frame.
The host-facing result should distinguish successful rendering from resource
exhaustion without exposing attacker-controlled details.

## Design constraints

- Keep all rendering and resource policy in Capstan. Platform adapters only
  transport completed frames and normalized input.
- Preserve deterministic output across supported C compilers and operating
  systems. Work accounting must not depend on wall-clock time.
- Avoid floating point and use existing fixed-point conventions.
- Keep the software rasterizer as the reference implementation.
- Do not turn ordinary complexity exhaustion into process termination.
- Do not silently clip, drop edges, or render a prefix of a path.
- Keep accessibility and input state coherent when a frame is rejected.
- Make all limits explicit, documented, and testable; avoid magic constants.

## Adversarial test matrix

The implementation PR must include boundary and over-boundary tests for:

1. a path at and above the verb/point cap;
2. a path with many curves, each individually below 64 segments;
3. a path whose flattened segment count reaches and exceeds its cap;
4. many individually valid paths whose combined frame work exceeds the budget;
5. long vertical edges spanning the full clip height;
6. dense crossings on every sub-scanline, including equal-x and opposite-winding edges;
7. large off-screen geometry and deeply nested clips;
8. tiny destination clips with very large edge counts;
9. counter values at zero, exactly the limit, one unit over, and near integer limits;
10. exhaustion after earlier paint operations, proving that no partial frame or
    stale prior pixels are published.

Run the matrix in the normal test suite and under ASan/UBSan. Include deterministic
operation-count assertions; timing-only tests are not acceptable.

## Calibration and acceptance gates

Before selecting the default frame budget, capture operation counts for:

- Anchor's representative screens and resize/scroll interactions;
- text and icon-heavy layouts;
- rounded rectangles, borders, ellipses and gradients;
- dense vector artwork;
- the largest supported software surface.

Record both worst-case operation counts and memory/peak-heap measurements.
Choose a default with an explicit safety margin over representative workloads,
then demonstrate that adversarial inputs are rejected before the budget is
exceeded. Publish benchmark fixtures, compiler/platform details, and exact commit
identifiers with the result.

Acceptance requires all of the following:

- path invariants hold under strict compilation and adversarial tests;
- flattening is bounded in both allocation and work;
- aggregate frame accounting is shared by every paint operation;
- budget exhaustion is failure-atomic and invalidates the corresponding hit-test
  frame;
- operation-count tests pass identically on GCC and Clang, Linux and macOS;
- ASan/UBSan reports no errors;
- measured normal workloads remain within the calibrated budget.

Until these gates pass, Shroud's path/raster CPU cost must be described as
**not yet proven bounded**.
