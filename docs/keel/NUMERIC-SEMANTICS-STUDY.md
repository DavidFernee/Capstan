# Keel numeric semantics: comparative study protocol

**Status:** proposed research protocol; no numeric representation selected  
**Phase:** K0 evidence preparation for K1  
**Owners:** Keel KR-01 / KR-06, coordinated with Capstan language, CCAM and runtime work  
**Related decisions:** KOD-001, KOD-002, KOD-004, KOD-008, KOD-011, KOD-015

This document turns the open numeric-design questions into an executable comparison plan.
It does not amend Capstan's language semantics and does not authorise Keel to ship a
private numeric type system.

## 1. Current implementation constraints

The current Capstan language defines signed 64-bit integer values with checked
addition, subtraction, multiplication and negation; division truncates toward zero,
and divide-by-zero and overflow are controlled failures. Explicit wrapping arithmetic
exists for hashing and cryptographic operations. It is not a substitute for a wide
intermediate in geometry or fixed-point arithmetic.

The current lexer has integer literals only. The parser and type checker have no
floating-point source type. CCAM v0.1's current scalar machine subset is `int` and
`bool`; its checked integer operations do not yet implement floating-point values.
The current K1 baseline therefore cannot assume native IEEE-754 source or CCAM
semantics.

This is a capability statement about the inspected branch, not a claim that Capstan
cannot acquire floating-point support. Any language/runtime extension must be owned
and reviewed by the corresponding Capstan stream.

Shroud already has a narrower fixed-point presentation geometry in `lib/shroud/geom.cap`:
its `FX = 256` scale represents 1/256 of a device-independent pixel and supports an
integer raster path with exact golden-image checks. This is valuable evidence that
bounded integer presentation geometry works in this repository. It is not a general
3D world/simulation numeric contract, and Keel does not import Shroud's geometry module
as its spatial authority. Any reuse of individual helpers requires a separate audit of
their input bounds and intermediate-overflow preconditions.

## 2. Separate numeric domains

A single representation is unlikely to be optimal for all engine operations. Evaluate
at least three domains independently:

1. **Simulation state:** positions, velocities, integration, constraints and replay.
   The contract prioritises explicit error bounds and reproducible state transitions.
2. **Geometry predicates:** orientation, intersection, containment, degeneracy and
   topology-changing decisions. A wrong sign can change connectivity; robustness is
   more important than smooth approximate values.
3. **Rendering:** camera transforms, interpolation, shading and rasterisation.
   Approximation is acceptable only with explicit precision, exceptional-value and
   image-error policies.

Do not infer deterministic simulation from deterministic geometry predicates, or
deterministic pixels from either.

## 3. Candidate families

### A. Fixed-point arithmetic

Evaluate at least Q16.48, Q32.32 and a configurable/scaled representation.

**Advantages**
- Integer operations provide a path compatible with current Capstan scalar semantics.
- Rounding and overflow can be specified exactly.
- Repeatability across supported targets is tractable if every intermediate is defined.

**Risks and unresolved engineering**
- The integer range and fractional resolution trade against one another.
- Multiplication and division need wider intermediates or a proven decomposition;
  silently using wrapping 64-bit arithmetic is incorrect.
- Accumulation, normalization, square root, trigonometry and ill-conditioned systems
  require explicit algorithms and error budgets.
- Fixed-point does not make an unstable simulation stable.

**Required proof obligations:** exact intermediate-width analysis, checked overflow,
round-to-nearest/ties policy (or another explicitly justified policy), signed division
rules, conversion bounds, and no undefined host arithmetic.

### B. IEEE-754 binary32/binary64

Evaluate native compiler/runtime support as a future Capstan language capability,
not as an assumed current feature.

Specify, at minimum, rounding mode, subnormal handling, NaN propagation/canonicalisation,
infinity, signed zero, comparison semantics, conversion, fused multiply-add policy,
transcendental functions and exception behaviour.

**Advantages**
- Broad hardware support and a mature ecosystem.
- Strong fit for rendering and many numerical algorithms.
- Often better throughput than software-emulated arithmetic.

**Risks**
- Host compiler flags, FMA contraction, libm and target differences can alter results.
- Reproducibility requires a narrower profile or a software implementation.
- NaN and infinity can contaminate scene state unless checked at boundaries.
- Adding a source type affects lexer, parser, checker, code generation, runtime, CCAM,
  serialization, testing and formal models.

### C. Restricted deterministic floating point

Evaluate a restricted profile with specified rounding and operation ordering, potentially
using software arithmetic or controlled hardware operations.

It may offer better dynamic range than fixed-point, but the restrictions and performance
cost must be measured. A label such as "deterministic float" is not a specification:
the exact bit-level operation semantics and transcendental policy must be published.

### D. Integer/adaptive robust predicates

Evaluate exact or adaptively widened integer predicates for topology-sensitive geometry,
with approximate coordinates allowed elsewhere. Establish input bounds and exact
intermediate requirements for orientation, plane-side, intersection and winding tests.

The predicate API must return a defined result or a controlled "indeterminate / range
exceeded" outcome. It must not silently fall back to an arbitrary epsilon.

### E. Hybrid domain

Evaluate fixed-point or a restricted deterministic profile for simulation state,
robust integer/adaptive predicates for topology, and approximate floating point for
rendering. Define explicit conversions and state boundaries.

This is the leading architecture hypothesis, not an accepted decision. Its complexity
and conversion error may outweigh its benefits; the experiments must be allowed to
reject it.

## 4. Comparative workload suite

All candidate implementations must run the same versioned workloads and input data.
The initial suite should include:

| Workload | Required observation | Independent oracle |
|---|---|---|
| Constant-acceleration integration | Position/velocity error over fixed steps; energy drift | Closed-form solution |
| Harmonic oscillator | Phase and amplitude drift; long-run stability | Analytical solution |
| Semi-implicit rigid-body integration | Momentum/energy drift and constraint residual | High-precision reference |
| 2D orientation and segment intersection | Correct sign near collinearity and large coordinates | Exact integer/rational predicate |
| 3D orientation / tetrahedron volume sign | Degenerate and near-degenerate classification | Exact integer/rational predicate |
| Transform composition/inversion | Round-trip error and conditioning | High-precision matrix oracle |
| Normalisation and square root | Relative/absolute error; zero and subnormal policy | High-precision reference |
| Camera projection and raster coordinates | Pixel coverage and edge consistency | Integer/reference raster vectors |
| Trigonometric lookup/evaluation | Error envelope and periodicity | High-precision reference |
| Serialization round-trip | Bit/value preservation and canonical output | Independent decoder and canonical vectors |

Every workload must include ordinary, boundary, adversarial and malformed inputs.
Include large/small magnitudes, cancellation, nearly parallel vectors, near-zero
denominators, degenerate triangles, maximum representable values and overflow attempts.

## 5. Required measurements

For every candidate and workload, record:

- correctness against an independent oracle;
- absolute, relative and ULP error where applicable;
- overflow, underflow, saturation and exceptional-value counts;
- deterministic replay hash and first divergent step;
- cross-process, cross-build and cross-architecture divergence;
- throughput and tail latency, not only average throughput;
- code size, allocation count and peak live memory;
- compiler/runtime changes required and the additional trusted code;
- failure behaviour when an input exceeds the documented numeric domain.

Publish raw inputs, seeds, outputs, compiler flags, exact source revision, hardware,
operating system, toolchain versions and benchmark harness. Retain failed and excluded
runs with reasons.

## 6. Normative rules pending selection

Until KOD-001 and KOD-002 are closed:

1. Do not expose a public Keel `float`, `Real`, `Scalar` or fixed-point type whose
   semantics are still unsettled.
2. Do not use approximate epsilon comparisons for topology-changing decisions.
3. Do not permit NaN, infinity or overflow to silently enter persistent simulation state.
4. Do not claim cross-platform determinism based on same-process repeatability.
5. Keep simulation stepping fixed and single-threaded for K1.
6. Use checked integer arithmetic for integer-domain work; never use wrapping arithmetic
   as an overflow workaround.
7. Any temporary experiment type must be private to its benchmark/prototype and must
   not become a serialized format or public API by accident.

## 7. Decision gates

**Gate N0 — protocol ready:** workload definitions, oracle strategy, candidate semantics
and required metadata reviewed.

**Gate N1 — arithmetic kernels:** checked integer baseline, at least two fixed-point
configurations, one floating-point reference where available, and exact geometry
predicates have executable test vectors. If a candidate cannot be implemented on
current Capstan, record the missing language/runtime capability rather than silently
moving the implementation into C.

**Gate N2 — workload comparison:** all candidates complete the common suite; error,
stability, throughput, memory and determinism results are published.

**Gate N3 — architecture decision:** select separate contracts for simulation,
geometry predicates and rendering, or document why a unified design wins. Update KOD-001,
KOD-002, KOD-004, KOD-011 and KOD-015 with evidence and rejected alternatives.

**Gate N4 — implementation acceptance:** public APIs, serialization and CCAM changes
(if any) have owner-approved specifications, conformance vectors, failure tests and
formal/refinement scope. No Keel implementation may claim stronger guarantees than
those underlying Capstan components.

## 8. Initial falsifiable hypotheses

- **H1:** a fixed-step, single-threaded schedule is sufficient to make the K1 simulation
  state repeatable within one exact build and execution target, provided operation order
  and numeric semantics are explicit.
- **H2:** exact/adaptive predicates reduce topology misclassification on adversarial
  near-degenerate geometry relative to fixed-epsilon floating-point predicates.
- **H3:** a hybrid numeric architecture improves the joint accuracy/performance/
  reproducibility frontier over any single representation, after conversion overhead
  is included.
- **H4:** a deterministic software arithmetic profile can meet the chosen simulation
  error budget without unacceptable throughput or code-size cost.

Each hypothesis may be rejected. "Promising" demonstrations do not close a gate;
the common suite and raw data do.
