# Keel K0 decision register

**Status:** living architecture decision record; narrow K1 predicate implementation is recorded separately  
**Parent:** [Keel architecture](../KEEL.md)  
**Technical detail:** [architecture supplement](../KEEL-ARCHITECTURE.md)  
**Research:** [Keel research programme](RESEARCH-PROGRAMME.md)  
**Last reviewed:** 2026-11-25

This register prevents an attractive implementation choice from silently becoming a
normative contract. Decisions marked **Accepted** establish architectural direction.
Decisions marked **Open** require alternatives, evidence and an explicit decision record.
**Deferred** means the question is intentionally outside the current phase.

## 1. Accepted architectural decisions

| ID | Decision | Rationale and constraint |
|---|---|---|
| KAD-001 | Capstan owns language semantics, compiler acceptance, runtime and capability policy. | Keel must not create a parallel language/security authority. Current C-backed execution remains the actual implementation baseline; C-free claims are scoped to demonstrated paths only. |
| KAD-002 | Keel owns 3D scene, spatial, geometry, simulation and rendering semantics. | These are not Shroud responsibilities and must not leak into the GUI toolkit. |
| KAD-003 | Shroud is an optional host/presentation adapter for Keel and the future Keel Studio. | Keel core remains headless-testable; Shroud must never depend on Keel. Keel Studio uses Shroud for UI, not for 3D rendering. |
| KAD-004 | K0 is specification and research preparation; K1 is the first implementation phase. | No scene graph, spatial library or renderer is to be represented as integrated during K0. |
| KAD-005 | A CPU reference path precedes accelerated rendering. | It supplies a small semantic oracle and deterministic test target. GPU backends must state their conformance relation and tolerance. |
| KAD-006 | Acceleration is optional and isolated behind a backend contract. | Driver, firmware, OS graphics service and hardware remain explicit external trust boundaries. |
| KAD-007 | Resource accounting is both per-object and aggregate, with checks before allocation or expensive work. | Per-file or per-buffer limits do not establish process, scene, frame or device-wide bounds. |
| KAD-008 | Research packages require implementation artifacts and reproducible evidence. | A model proof, benchmark or passing test is reported only for its actual scope; negative results and assumptions are retained. |
| KAD-009 | K1 begins with a single-threaded deterministic baseline. | Parallel execution is deferred until Capstan's concurrency, cancellation and ownership contracts are mature enough to support a justified design. |
| KAD-010 | Keel Science is a downstream scientific library, not part of Keel's engine core. | Scientific units, uncertainty, provenance, digital-twin state and biomedical-domain semantics belong above the generic engine; see `docs/KEEL-SCIENCE.md`. The library consumes Keel/Capstan contracts but must not make Keel depend on domain-specific science packages. |
| KAD-011 | Headless and command-line workflows remain first-class; Keel Studio is a later Shroud-based application. | Engine builds, tests, servers and CI must not require the editor. The editor consumes the same project/scene model and must not invent a second gameplay language. |
| KAD-012 | Developer-experience claims are evaluated through matched production tasks. | Time-to-first-playable, iteration, debugging, reproducibility, accessibility and resulting build quality must be measured against documented baselines; API brevity or a polished demo is insufficient. |
| KAD-013 | Keel-owned code and supporting tools are implemented from scratch in Capstan. | No third-party engine/library implementation is embedded or wrapped; published standards and algorithms may inform original implementations. Bootstrap and platform trust boundaries are disclosed in the [Capstan-only policy](FROM-SCRATCH-AND-CAPSTAN-ONLY.md). |
| KAD-014 | Known vulnerabilities and design hazards are tracked in a live register with implementation-specific evidence. | The [vulnerability register](VULNERABILITY-REGISTER.md) distinguishes specified mitigations from implemented and independently validated controls. |

### K1 implementation increment: bounded spatial primitives

The current branch contains the following narrow executable increment:

- `lib/keel/coordinates.cap`: shared bounded `KPoint2`/`KPoint3` types, coordinate-domain constants and validation helpers; it owns no geometry algorithms.
- `lib/keel/predicates.cap`: exact bounded 2D/3D orientation, 2D segment relation and 3D point-in-tetrahedron predicates; imports `coordinates.cap`.
\n- `lib/keel/polygon.cap`: bounded simple-ring validation (maximum 256 vertices) and exact winding-number point classification; invalid/self-intersecting/degenerate rings are rejected, boundary is distinct from strict interior, and all topology decisions use the exact orientation/segment predicates.\n- `lib/keel/spatial.cap`: bounded 3D integer vectors with checked arithmetic and validated closed axis-aligned bounds with containment, overlap and union; imports `coordinates.cap` directly, not the predicate implementation.
- `tests/keel/check.py`: deterministic differential/property checks against Python arbitrary-precision integer oracles; `tests/run.sh` invokes the harness as part of the standard suite.

The polygon ring is bounded to 256 vertices and uses the ±(2^30−1) 2D coordinate domain. The vector and 3D point/bounds domain is ±(2^18−1). Dot products and squared lengths are bounded below signed-64 limits; cross-product and orientation intermediates are also bounded, while vector results outside the public component domain return `none`. `spatial.cap` imports `predicates.cap` for the shared `KPoint3` and coordinate-domain contract. This is not a choice of world units, handedness, transform convention, simulation scalar or rendering scalar. It does not close KOD-001 through KOD-004 or establish production readiness. Exact-head CI is required before calling the increment validated.

## 2. Open K0 decisions

No choice below should be hard-coded into public APIs until the alternatives and
consequences are documented.

| ID | Question | Alternatives to evaluate | Required evidence / decision trigger |
|---|---|---|---|
| KOD-001 | Numeric representation for simulation and geometry | IEEE-754 binary32/64; fixed-point; restricted deterministic floating point; hybrid with integer predicates | Accuracy, stability, throughput, cross-target divergence, overflow and implementation support in current Capstan. Comparative protocol: [NUMERIC-SEMANTICS-STUDY.md](NUMERIC-SEMANTICS-STUDY.md). |
| KOD-002 | Scope of determinism | Same process; same build/architecture; cross-architecture; cross-platform | Repeatability experiments, source of nondeterminism inventory, acceptable performance and explicit user-facing contract; use the common replay and divergence protocol in [NUMERIC-SEMANTICS-STUDY.md](NUMERIC-SEMANTICS-STUDY.md). |
| KOD-003 | Coordinate convention | Handedness, up axis, forward axis, world units and angle units | Interoperability review, conversion cost, camera/physics/asset conventions and canonical test vectors |
| KOD-004 | Transform representation and composition | Matrix layout, vector convention, quaternion conventions, parent/local composition order | Round-trip and metamorphic tests, numerical conditioning, serialization and backend mapping |
| KOD-005 | Scene storage model | Hierarchical object/component model; data-oriented entity/component storage; hybrid | Mutation/query workloads, cache behaviour, identity/lifetime complexity, serialization and tooling needs |
| KOD-006 | Scene identity and mutation API | Generational handles; stable UUIDs; split authoring/runtime identity | Stale-reference tests, deterministic serialization, mutation atomicity, replication/replay requirements |
| KOD-007 | Initial asset interchange format | A deliberately narrow existing format subset; a canonical internal interchange format; both with a conversion boundary | Threat-model review, format complexity, ecosystem interoperability, parser availability, fuzz corpus and bounded decoder feasibility |
| KOD-008 | Colour and image semantics | Linear/sRGB policy, transfer functions, alpha convention, texture origin and mip generation | Reference vectors, image-quality metrics, platform/backend consistency and asset-format mapping |
| KOD-009 | CPU rasterization rules | Coverage convention, clipping, depth precision, interpolation, blending and sample rules | Small exact/reference scenes, edge-case vectors and cross-target reproducibility |
| KOD-010 | Material and shader model | Declarative material graph first; restricted typed shader IR; later programmable subset | Threat model, resource analysis feasibility, driver boundary and K2 requirements |
| KOD-011 | Physics scope and numerical policy | Collision-only foundation; rigid-body subset; broader solver architecture | Independent analytical/high-precision oracles, stability and error budgets, bounded iteration behaviour |
| KOD-012 | Resource-budget scopes and defaults | Operation, asset, scene, frame, world, process and logical GPU admission budgets | Peak-live-set measurements, nested-operation composition, failure atomicity and overload policy |
| KOD-013 | Initial platform matrix | Headless CI first; Linux CPU host; later macOS/Windows and GPU-specific targets | Actual Shroud host readiness, compiler/runtime support, CI capacity and target-user requirements |
| KOD-014 | Asset and scene canonical serialization | Canonical binary encoding; canonical text encoding; versioned pair | Duplicate-field handling, stable hashes, signing/provenance, parser attack surface and diff usability |
| KOD-015 | Floating-point transcendental functions | Host libm; deterministic software routines; explicitly approximate functions | Cross-platform variance, speed, accuracy and current Capstan runtime support |

## 3. Deferred decisions

| ID | Topic | Deferred until |
|---|---|---|
| KDD-001 | Parallel renderer/simulation scheduler | Capstan concurrency, ownership, cancellation and structured-task contracts are specified and tested; sequential K1 baseline exists |
| KDD-002 | Production GPU API and backend selection | CPU reference semantics and K2 profiling identify a real bottleneck; device/resource lifecycle contract is reviewed |
| KDD-003 | Plugins, scripting and third-party extensions | Capability isolation, resource limits, provenance and revocation are specified and independently tested |
| KDD-004 | Networking and distributed world replication | Core scene identity, canonical serialization, authority model and bounded protocol semantics exist |
| KDD-005 | World streaming and residency scheduler | Scene/asset budgets and cancellation/back-pressure contracts have measurements |
| KDD-006 | Keel Studio project/editor workflows | Shroud's native host, text input, accessibility and platform readiness gates are met |

## 4. Decision protocol

Every decision that changes a public contract must include:

1. problem statement and phase in which it blocks progress;
2. at least two credible alternatives, including the option to defer;
3. related work and interoperability constraints;
4. security, resource, numerical and portability consequences;
5. a small executable experiment or formal model where appropriate;
6. compatibility and migration impact;
7. exact decision owner, date, status and links to implementation/evidence;
8. a reversal condition explaining what evidence would justify revisiting it.

Do not decide a numeric or API question merely because one representation is convenient in
the current language subset. If Capstan lacks a required primitive, record a dependency
proposal in the owning Capstan workstream rather than implementing a private substitute
inside Keel.

## 5. Repository constraints verified during K0 review

These are observations about the current Capstan/Shroud documentation and implementation
baseline, not permanent architectural limits. Recheck them against the exact revision before
starting K1.

| Area | Current repository evidence | Consequence for Keel |
|---|---|---|
| Source and CCAM numeric subset | [Language specification](../SPEC.md) defines signed 64-bit `int` with checked arithmetic and no floating-point source type; the current [lexer](../../compiler/lexer.cap) has integer but no floating-literal token, and the [parser](../../compiler/parser.cap) has no floating-point type; [CCAM specification](../architecture/CCAM.md) currently defines machine scalar types as `int` and `bool`. | Do not assume the current language or CCAM can execute IEEE-754 transforms or simulation. KOD-001 must select an integer/fixed-point strategy supported by the chosen path, or open a foundational numeric-semantics proposal. |
| CCAM scope | The current CCAM slice excludes heap objects, collections, I/O, concurrency and cryptographic services; its evaluator is not yet a general runtime. | Keel must not present CCAM as the implementation path for a full engine. K1 must name whether it runs on the existing C-backed path or a specifically demonstrated C-free subset. |
| Filesystem and byte input | [Language specification](../SPEC.md) exposes `read_file(path[, max])`, `read_bytes(n)` and `write_file(path, data)`; [standard-library assessment](../STDLIB-V06.md) records ambient path authority and no capability-scoped filesystem API in the current surface. | Keep K1 scenes procedural/source-defined initially. Do not accept arbitrary project/asset paths as trusted authority; use narrow test fixtures and explicit small byte budgets. Asset import needs a separate capability and parser contract before it enters the engine. |
| Source data and collections | [Language specification](../SPEC.md) defines byte strings, growable `List<T>`, insertion-ordered `Map<T>` and reference-type structs; the standard-library assessment notes missing strict UTF-8 and general typed serialization contracts. | Asset parsing must operate on bounded byte spans and preserve taint/provenance. Do not treat arbitrary strings as validated Unicode or assume a reusable binary serialization API exists. |
| Runtime concurrency | [Runtime architecture](../assurance/RUNTIME-ARCHITECTURE.md) states that the collector is single-threaded and not thread-safe, with no language threads/tasks or per-thread root registration. | K1 remains single-threaded. No worker pool, asynchronous mutation or parallel render/simulation until the Capstan concurrency and GC protocols are implemented and reviewed. |
| Shroud host | [Shroud host contract](../SHROUD-HOST.md) states that S0 has no native window, event pump, clipboard, IME composition or native accessibility provider; concrete host APIs require later capability-I/O and system-call work. | K1 must be headless or use a separately justified minimal host boundary. Do not make engine-core progress depend on guessed Shroud host signatures. Keel Studio follows Shroud's own readiness gates. |
| Default compiler path | [Design map](../DESIGN-MAP.md) records the default path as generated C plus host C compiler/runtime; C-free execution remains staged work. | All K1 status and security claims must name the actual execution path. Writing Keel in Capstan does not remove the current compiler/runtime trust base. |

### K1 dependency gate

Before implementing the first scene/math/rendering slice, produce a short capability audit
for the exact target branch covering:

1. integer widths, checked arithmetic and any wider intermediate arithmetic;
2. floating-point types, conversions and math-library semantics, if present;
3. list/array/record representation and aggregate-allocation limits;
4. byte-oriented file input and the actual bounded I/O API;
5. module/import and build behaviour for a multi-file library;
6. deterministic execution assumptions and the current runtime/GC trust boundary;
7. the chosen headless output mechanism and its output-size budget.

Each item must be marked **available and tested**, **available with a documented limitation**,
or **missing**. A missing capability becomes an issue/PR in its owning Capstan stream; Keel
must not quietly create a private substitute that changes language or runtime semantics.

## 6. K1 implementation status

The initial geometry kernel now contains exact bounded 2D and 3D orientation predicates in `lib/keel/predicates.cap`. The 2D domain is ±(2^30−1); the 3D domain is ±(2^18−1), chosen so the determinant's intermediate values remain strictly within signed 64-bit range. Both reject out-of-domain inputs before arithmetic and return an optional sign. The differential harness `tests/keel/check.py` covers random inputs, every vertex permutation, exact extrema, near-zero determinants and every out-of-domain coordinate using Python arbitrary-precision integers as an independent test-only oracle. It is invoked by `tests/run.sh`; execution status must be verified on the exact branch head before claiming it passes.

 The same module now classifies bounded 2D segment pairs as disjoint, point-touching, properly crossing or positively overlapping when collinear; it composes exact orientation signs with inclusive coordinate intervals and performs no unchecked coordinate subtraction. The differential harness also covers random segment pairs, endpoint reversal, segment-pair swapping, zero-length segments, all collinear interval relations and every out-of-domain coordinate position.

 The module also provides a 3D point-in-tetrahedron classifier using four exact face-orientation signs; it distinguishes outside, boundary and strict interior, and returns `none` for a degenerate tetrahedron or out-of-domain input. The test oracle covers random tetrahedra, known interior/boundary/exterior points, degeneracy and every coordinate-validation branch.

This does not select a general 3D scalar representation, define transforms, or establish renderer readiness. The [vulnerability register](VULNERABILITY-REGISTER.md) tracks the remaining geometry and numerical hazards.

## 7. Immediate K0/K1 sequence


1. Review KAD-001 through KAD-009 against the Capstan design map and Shroud contracts.
2. Resolve only decisions that block a coherent K1 vertical slice; leave the rest open.
3. Inspect actual Capstan compiler/runtime support for integer widths, floating point,
   collections, memory, file access and deterministic execution before writing K1 code.
4. Choose the smallest asset/scene input surface that can be fuzzed and independently
   validated.
5. Turn each K1 contract into executable conformance vectors before implementation.
6. Keep all performance and security claims marked proposed until exact-head evidence
   exists.
