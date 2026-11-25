# Keel K0 decision register

**Status:** living architecture decision record; no K1 implementation decisions are implied  
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

## 2. Open K0 decisions

No choice below should be hard-coded into public APIs until the alternatives and
consequences are documented.

| ID | Question | Alternatives to evaluate | Required evidence / decision trigger |
|---|---|---|---|
| KOD-001 | Numeric representation for simulation and geometry | IEEE-754 binary32/64; fixed-point; restricted deterministic floating point; hybrid with integer predicates | Accuracy, stability, throughput, cross-target divergence, overflow and implementation support in current Capstan |
| KOD-002 | Scope of determinism | Same process; same build/architecture; cross-architecture; cross-platform | Repeatability experiments, source of nondeterminism inventory, acceptable performance and explicit user-facing contract |
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

## 5. Immediate K0 sequence

1. Review KAD-001 through KAD-009 against the Capstan design map and Shroud contracts.
2. Resolve only decisions that block a coherent K1 vertical slice; leave the rest open.
3. Inspect actual Capstan compiler/runtime support for integer widths, floating point,
   collections, memory, file access and deterministic execution before writing K1 code.
4. Choose the smallest asset/scene input surface that can be fuzzed and independently
   validated.
5. Turn each K1 contract into executable conformance vectors before implementation.
6. Keep all performance and security claims marked proposed until exact-head evidence
   exists.
