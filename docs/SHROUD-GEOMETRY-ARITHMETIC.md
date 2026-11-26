# Shroud checked geometry arithmetic contract

**Status:** design baseline for the first P1 geometry-hardening slice of #84. This document specifies required behaviour; it does not claim that the current implementation satisfies it.

## 1. Scope

The contract covers the fixed-point and rectangle primitives in `lib/shroud/geom.cap`:

- pixel/fixed-point conversion (`fx`, `fx_floor`, `fx_ceil`, `fx_round`);
- fixed-point multiply/divide (`fx_mul`, `fx_div`, `mul_div`);
- signed absolute value and integer square root;
- rectangle edge, containment, inset, grow, intersection and offset arithmetic;
- constraint deflation and finite-bound arithmetic.

It does not specify layout policy, rasterisation, path flattening, or host window dimensions except where those systems consume geometry results.

## 2. Normative arithmetic rules

1. Every operation must define its input domain, intermediate range, rounding rule and failure result.
2. No operation may rely on signed overflow, wraparound, implementation-defined shifts, or an unchecked intermediate merely because the final mathematical result would fit.
3. A divisor of zero is invalid. A negative denominator is invalid where the operation's contract requires a positive denominator.
4. The minimum signed integer is not representable as a positive signed integer; absolute value and negation must reject that input rather than overflow.
5. Multiplication and addition must be checked before the operation, or implemented using an equivalent operation proven not to overflow.
6. Division rounding is specified mathematically, including negative operands and ties. Implementations must not depend on the host language's signed-division convention without compensating for it.
7. Failure is an ordinary, deterministic result. Invalid geometry supplied by an application or decoded input must not terminate the host process.
8. A failed composite operation must not publish partially updated geometry or mutate caller-owned state.

## 3. Fixed-point representation

The representation remains signed integer coordinates in units of 1/256 device-independent pixel (`FX = 256`).

- `fx(px)` succeeds only when `px * FX` is representable.
- `fx_floor`, `fx_ceil` and `fx_round` must define negative-value behaviour explicitly. Their implementation must not overflow while adding a rounding bias.
- `fx_mul(a,b)` computes the exact mathematical product, divides by `FX`, and rounds to nearest with ties away from zero. The intermediate product and rounding adjustment must be checked.
- `fx_div(a,b)` rejects `b == 0`; it computes the exact mathematical quotient of `a * FX / b`, rounded to nearest with ties away from zero. Both scaling and rounding must be checked.
- `mul_div(v,num,den)` requires `den > 0`; it computes `v * num / den`, rounded to nearest with ties away from zero, with checked multiplication and rounding.

If a later implementation chooses a wider intermediate representation, the observable domain and failure semantics remain the same unless a versioned contract explicitly changes them.

## 4. Signed integer helpers

- Checked absolute value rejects the minimum signed integer.
- `int_min` and `int_max` are total over all representable inputs.
- `clamp(v,lo,hi)` requires `lo <= hi`; reversed bounds are invalid rather than silently reordered.
- `isqrt(n)` requires `n >= 0` and returns the greatest integer `r` such that `r*r <= n`. Its internal convergence arithmetic must be overflow-safe, including at the maximum input.

## 5. Rectangle semantics

Rectangles are half-open: `[x, x+w) × [y, y+h)`. Width and height must be non-negative for a valid rectangle. Empty rectangles have zero width or height.

- Edge accessors are checked additions. An unrepresentable right or bottom edge makes the rectangle invalid for operations requiring that edge.
- Point containment uses checked edges and never evaluates an overflowing `x+w` or `y+h`.
- Inset checks both origin and extent arithmetic. Over-insetting yields an empty rectangle at the mathematically defined clamped origin; arithmetic overflow is a failure, not saturation.
- Grow and offset check every addition, subtraction and multiplication. Negative growth is allowed only if the resulting dimensions remain non-negative.
- Intersection uses checked edges and returns a valid empty rectangle for disjoint inputs. Invalid input rectangles produce failure.
- Constructors and convenience pixel constructors must validate dimensions and scaling before returning a usable rectangle.

No operation silently saturates. Saturation may be introduced only as a separately named operation with an explicit use case and tests.

## 6. Constraints

Constraint bounds must satisfy non-negative minima and maxima with `min <= max`, except for the single documented `UNBOUNDED` sentinel. Deflation checks inset sums and finite-bound subtraction. The sentinel must never be treated as an ordinary finite integer in arithmetic.

Invalid constraints are rejected deterministically before layout consumes them. A failed deflation does not return a partially valid constraint object.

## 7. Required executable conformance matrix

The implementation PR must add tests for:

- zero divisors and negative denominators;
- `INT_MIN`, `INT_MAX`, and values immediately adjacent to each;
- multiplication overflow where the final divided result might otherwise appear representable;
- positive and negative division, exact halves, and values just either side of a rounding tie;
- `fx` scaling at both representable boundaries;
- floor/ceil/round around `-257, -256, -255, -1, 0, 1, 255, 256, 257`;
- absolute value of `INT_MIN`;
- square root at `0`, `1`, perfect squares, adjacent values and `INT_MAX`;
- rectangles whose right/bottom edge overflows, negative dimensions, empty dimensions, and extreme offsets/growth/insets;
- reversed constraints, sentinel deflation, and inset-sum overflow;
- failure atomicity: output values and caller-owned inputs remain unchanged after rejection.

Where the language or runtime currently traps on arithmetic failure, tests must run the operation through the public boundary and demonstrate a returned failure result rather than process termination. Property tests should compare successful results against an independent arbitrary-precision oracle and classify rejected inputs separately.

## 8. Implementation sequence and evidence boundary

1. Confirm Capstan's integer width, checked-arithmetic semantics, optional/result conventions and test-harness support.
2. Add checked primitives with explicit failure results; keep compatibility wrappers only where their failure behaviour is safe and documented.
3. Migrate rectangle and constraint operations to checked composition.
4. Add boundary/property tests and an independent oracle.
5. Audit callers in layout, path, raster and UI; reject invalid geometry at public boundaries.
6. Run normal and sanitizer suites on the exact implementation commit.

This contract is not a proof of arithmetic correctness, does not establish aggregate resource limits, and does not make Shroud production-ready. The implementation and its caller audit remain outstanding.
