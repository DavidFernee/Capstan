# Keel: Capstan's 3D rendering and simulation engine

**Status:** K0 architecture with a narrow K1 geometry-kernel increment; no production engine is claimed.  
**Parent:** Capstan language, compiler, runtime and assurance programme.  
**Related systems:** Shroud (GUI toolkit), Anchor (reference IDE).  
**Working principle:** research and implementation must advance together, with claims tied to reproducible evidence.

Keel is the proposed native 3D rendering, simulation and interactive-world engine for the Capstan ecosystem. Its ambition is to compete with the leading general-purpose real-time engines, including Unreal Engine, while pursuing a distinctive research agenda in security, determinism, resource governance and formal assurance.

Keel is also intended to become a demanding real-world workload for Capstan. Findings about language expressiveness, compiler correctness, runtime services, memory management, numeric semantics and concurrency must flow back into the corresponding Capstan research workstreams. Keel must not silently invent private substitutes for missing foundational capabilities.

A co-equal product objective is to make high-quality games easier to build than with Unreal Engine while pursuing better results on defined workloads. This means optimising the complete production loop—first playable build, authoring, iteration, debugging, profiling, collaboration and release—not merely simplifying the runtime API. The objective and its falsifiable evaluation plan are specified in [Keel Developer Experience](keel/DEVELOPER-EXPERIENCE.md) and research work package KR-12.

## 1. Status and claim discipline

The following terms are normative:

- **Integrated:** present on the named branch and exercised by its tests.
- **Validated:** integrated and supported by stated conformance evidence.
- **Formally verified:** the exact property is established by a machine-checked theorem, with assumptions and implementation correspondence disclosed.
- **Specified:** a contract or design exists; implementation is not implied.
- **Experimental:** a prototype exists but is not a supported contract.
- **Target:** an objective whose acceptance gates remain outstanding.

A proposal, proof of an abstract model, successful build, benchmark on one machine or passing test suite is not evidence for claims beyond its actual scope. Every status statement is branch- and revision-specific.

Keel remains predominantly specified. K1 now contains bounded exact 2D/3D orientation and topology predicates in `lib/keel/predicates.cap`, plus bounded checked 3D vector and axis-aligned bounds primitives in `lib/keel/spatial.cap`, and bounded simple-polygon validation/point classification in `lib/keel/polygon.cap`. These narrow integer-domain kernels are not a general spatial library or world-coordinate model. No production renderer, physics engine, GPU backend, editor, asset pipeline or security certification is claimed.

## 2. Relationship to Capstan, Shroud and Anchor

The dependency direction is deliberately one-way:

```
Capstan language / compiler / CCAM / runtime / platform capabilities
                         |
             +-----------+-----------+
             |                       |
           Shroud                   Keel
        GUI toolkit       3D / simulation / world engine
             |                       |
             +-----------+-----------+
                         |
                Keel Studio (later)
             Shroud-based editor and tools

Anchor remains the Capstan IDE built on Shroud; it is not a Keel dependency.
```

### Capstan

Capstan owns language semantics, compiler acceptance, runtime behaviour, memory and resource services, capability security, platform interfaces and the foundational assurance programme.

The repository's current default compiler path is C-backed. The C-free/CCAM programme is in progress and is not yet the default execution path. Keel must therefore distinguish experiments that run on today's compiler from target architecture that depends on future language/runtime capabilities.

Keel must not claim end-to-end memory safety or formal verification merely because its source is written in Capstan. The current C runtime, compiler, generated C, host C compiler, native adapters, GPU drivers and operating system remain separate trust and assurance concerns.

### Shroud

Shroud is the intended UI foundation for Keel Studio and engine tooling. Its deterministic software-rendering approach is a useful reference for Keel's own reference-renderer discipline.

Shroud's current S0 implementation is a prototype, not a production GUI toolkit. Its native host, full text shaping, IME, native accessibility and platform integration gaps remain real. Keel's core must not depend on unfinished Shroud host APIs, and Keel's renderer must not be conflated with Shroud's 2D rasteriser.

### Keel

Keel owns 3D scene representation, geometry, visibility, materials, lighting, rendering, simulation, physics, animation, world streaming, asset ingestion and engine-level diagnostics. Keel Studio will use Shroud for interface composition, not for the 3D rendering pipeline. The companion Keel Science library (working name) will build on Keel for scientific computing, digital twins, biomedical and medical-imaging research, and other evidence-sensitive domains. It is not a dependency of the engine core; see [Keel Science](KEEL-SCIENCE.md).

## 3. Architectural invariants

**Implementation constraint:** all Keel-owned shipped code, including Keel Science and game-development tooling, is to be implemented from scratch in Capstan. No existing engine or third-party runtime library may supply Keel functionality. Published standards, algorithms and vulnerability research may inform original implementations. The current C-backed Capstan bootstrap is an acknowledged transitional toolchain dependency, not permission to implement Keel subsystems in C. See the normative [from-scratch and Capstan-only policy](keel/FROM-SCRATCH-AND-CAPSTAN-ONLY.md).

1. **Capstan-native core.** Engine semantics and core subsystems are implemented in Capstan wherever the language and runtime can support them. Native code is confined to narrow, documented platform and device boundaries.
2. **Security by construction.** Untrusted data is validated before use; memory, work, recursion, queue depth, decompression and cache growth are explicitly bounded.
3. **Least authority.** Components receive only the capabilities and resources they need. Asset decoders and extension execution must not inherit editor or host authority.
4. **Deterministic reference semantics.** A portable software reference path defines correctness before accelerated implementations are introduced.
5. **Acceleration is optional.** GPU backends are capability-detected, isolated behind explicit contracts, and never required to parse assets or define scene semantics.
6. **Measured complexity.** Threading, caches, GPU work and speculative optimisation require profiling evidence and a correctness argument.
7. **Research is a deliverable.** Every major subsystem has hypotheses, baselines, experiments, reproducible artifacts and explicit limitations.
8. **No proof laundering.** A proof of a model does not prove its implementation unless the refinement/correspondence argument is established.
9. **Failure is bounded and observable.** Invalid input, exhausted budgets, device loss and component failure produce defined outcomes without corrupting unrelated engine state.
10. **No unsupported superiority claims.** Comparative claims require pinned workloads, hardware, configurations, raw data and repeatable procedures.

## 4. Proposed subsystem boundaries

| Subsystem | Responsibility | Initial assurance boundary |
|---|---|---|
| Core types and math | Vectors, matrices, transforms, bounds, coordinate conventions | Checked arithmetic, explicit numeric semantics, property tests |
| Scene model | Entities, components, hierarchy, stable identity | Schema validation, depth/count budgets, deterministic updates |
| Asset pipeline | Import, decode, validate, cache and stream content | Hostile-input boundary; parsers fuzzed and resource-bounded |
| Geometry | Mesh representation, indexing, bounds, LOD metadata | Index/range validation, overflow-safe sizing |
| Visibility | Frustum, occlusion and hierarchical visibility | Reference tests against brute-force small-scene oracle |
| Materials and shaders | Material descriptions and shader IR | Typed/validated IR; compiler isolation; no implicit host authority |
| Renderer | Pass graph, rasterisation, depth, blending, lighting | Software reference semantics; backend conformance |
| Simulation | Fixed-step world updates, events and replay | Defined ordering, bounded steps, reproducibility tests |
| Physics | Broad/narrow phase, contacts, constraints and integration | Numerical error budgets, adversarial geometry, deterministic mode |
| Animation | Skeletons, clips, blending and procedural controls | Bounded graph evaluation, validated asset references |
| World streaming | Spatial partitions, residency, asynchronous loading | Global and per-world budgets, cancellation and back-pressure |
| Audio integration | Scene audio emitters, spatial transforms, occlusion inputs, event timing and routing to Shanty | Keel owns scene-to-media orchestration only; Shanty owns decode, sample formats, mixing, resampling, synthesis and spatial DSP; bounded references and queues |
| Networking | Replication, transport abstraction and serialization | Authenticated protocol, strict parsing, bounded queues |
| Diagnostics | Profiling, traces, captures and crash reports | No secret leakage; bounded logs and stable event schemas |
| Keel Studio | Editor, inspectors, project and asset tools | Shroud dependency; project data treated as untrusted |

Subsystems are independently testable. No subsystem may bypass another subsystem's validation or resource accounting by reaching into its private storage.

## 5. Numeric and determinism policy

Keel must not assume that the language's current numeric facilities are sufficient for a high-performance 3D engine. Before committing to a numeric representation, the research programme must compare:

- fixed-point representations for exact bounded operations;
- IEEE-754 binary32/binary64 semantics where supported;
- deterministic software arithmetic or restricted floating-point modes;
- quantised state for network/replay boundaries;
- higher-precision reference calculations for error analysis.

The specification must define overflow, rounding, NaN/infinity handling, signed zero, conversion, fused operations, denormals and transcendental-function policy where relevant. A deterministic mode must state exactly what is deterministic: same build, same architecture, cross-architecture, or cross-platform. These are different claims.

The initial reference renderer should favour correctness, explicit arithmetic and a small feature set over speed. It should expose a test oracle for accelerated implementations.

## 6. Security architecture

Keel's security ambition is to become the most secure general-purpose 3D engine supported by credible, independent evidence. This is an objective, not a present fact or guarantee.

The security model assumes that project files, imported assets, network messages, plugins, shader source, compressed data and user-authored scene descriptions may be hostile. It also assumes that individual components, drivers and host services can fail.

The architecture therefore requires:
- validation before allocation or expensive processing;
- per-item and aggregate resource budgets;
- bounded parsers and decompression;
- explicit ownership and lifetime contracts;
- isolation of high-risk decoders, shader compilation and extension execution;
- capability-limited filesystem, network, device and process access;
- authenticated and versioned network protocols;
- fail-closed behaviour when security-critical initialization or validation fails;
- fuzzing, sanitizers where applicable, mutation testing and independent review;
- a public threat model, vulnerability disclosure process and residual-risk register.

See [Security Assurance](keel/SECURITY-ASSURANCE.md), the [vulnerability and design-hazard register](keel/VULNERABILITY-REGISTER.md), the [detailed technical architecture supplement](KEEL-ARCHITECTURE.md), and the [K0 decision register](keel/K0-DECISIONS.md). The supplement expands resource accounting, scene/handle invariants, asset validation, numeric semantics and CPU/GPU trust boundaries; the decision register records accepted boundaries, open technical choices and deferred work without changing the K0/K1 phase gate.

## 7. Research programme

The research programme is a first-class part of Keel, not an optional publication activity. Work packages are described in [Research Programme](keel/RESEARCH-PROGRAMME.md). The cross-cutting memory dependency for exact workspace budgets is specified in [C-Free Bounded Scratch Memory](keel/C-FREE-BOUNDED-SCRATCH.md) (proposal; not implemented).

Every research work package must record:
- question and falsifiable hypothesis;
- related work and baseline implementations;
- threat model and assumptions;
- formal model or algorithm specification;
- implementation and test corpus;
- experimental protocol, hardware/software versions and raw data;
- correctness, performance, memory and security results;
- negative results, limitations and replication instructions;
- contribution to Capstan, Shroud or other research streams.

A result is not accepted merely because it improves one benchmark. It must disclose trade-offs and test for regressions in correctness, security and resource use.

## 8. Development phases and gates

### K0 — Foundation (current)

Deliver architecture, research and security specifications; dependency map; terminology; status rules; benchmark protocol; acceptance gates. No renderer implementation is implied.

**Exit:** specifications reviewed for internal consistency; unresolved decisions and dependencies recorded; no guessed Capstan/Shroud API dependencies.

### K1 — Deterministic scene and reference-renderer slice

Begin with bounded, exact spatial kernels whose arithmetic preconditions are proved. `lib/keel/predicates.cap` contains exact 2D/3D orientation signs, 2D segment classification (disjoint, point touch, proper crossing, positive-length collinear overlap) and 3D point-in-tetrahedron classification (outside, boundary, strict interior). Degenerate tetrahedra and out-of-domain inputs return `none`. `lib/keel/spatial.cap` adds bounded 3D vector construction, validation, checked addition/subtraction, dot product, cross product and squared length, plus validated closed AABBs with containment, intersection and union. `lib/keel/polygon.cap` adds a simple-ring validator capped at 256 vertices and exact winding-number point classification with distinct outside, boundary and strict-interior results; self-intersections, repeated contacts, degenerate rings and out-of-domain inputs are rejected. The polygon simplicity check is quadratic but explicitly bounded. These are narrow integer-domain kernels, not general world-coordinate or transform representations. The differential/property harness `tests/keel/check.py`, invoked by `tests/run.sh`, compares the Capstan implementation with Python arbitrary-precision integer oracles across random inputs, degeneracies, permutations, exact extrema and every out-of-domain coordinate. The initial indexed triangle-mesh boundary in `lib/keel/mesh.cap` enforces explicit vertex/index/triangle caps, validates index ranges and exact 3D triangle non-degeneracy, and computes checked vertex bounds, and reports deterministic edge/face incidence (boundary, two-face, non-manifold, winding-conflict, duplicate-face and connected-component counts, including referenced/isolated vertices) using bounded integer sort-and-scan and iterative union-find; its contract and limitations are recorded in [Mesh Foundation](keel/MESH-FOUNDATION.md), with focused cases in `tests/keel/mesh_check.py`. Check exact-head CI before describing these kernels as validated. The follow-on [Mesh Ownership and BVH Design Gates](keel/MESH-OWNERSHIP-AND-BVH.md) and [Mesh Topology Assurance](keel/MESH-TOPOLOGY-ASSURANCE.md) records a blocking language/runtime dependency: current mutable, identity-bound Lists cannot back a persistent immutable mesh or retained BVH. KR-14 therefore gates publication on compiler/runtime-enforced ownership and byte accounting; KR-15 specifies deterministic bounded CPU-BVH research, with implementation deferred until that gate passes.

In parallel, execute the numeric comparison protocol before exposing public vector, matrix, quaternion, camera or simulation scalar APIs. Once KOD-001/KOD-002 have evidence-backed decisions, implement the minimal scene model, camera, transforms, triangle/mesh representation, clipping, depth and deliberately limited software renderer. First visible demonstration remains a rotating, textured and illuminated object, rendered from Capstan code.

**Exit:** exact 2D/3D predicate vectors and domain-boundary tests; numeric contract selected with independent oracles; golden/property tests, malformed-scene tests, bounded memory/work, reproducible output within the declared determinism scope, and measured baseline.

### K2 — Rendering foundations

Materials, texture sampling, colour management, lighting, shadowing and a documented render-pass model.

**Exit:** conformance suite, image-quality metrics, reference scenes and performance/memory baselines.

### K3 — Simulation foundations

Fixed-step updates, spatial queries, collision detection, physics integration, animation and deterministic replay.

**Exit:** repeatability tests, numerical error analysis, stress tests and bounded-step/resource behaviour.

### K4 — Optional acceleration

Introduce a GPU backend only after K1/K2 establish a stable reference contract and profiling demonstrates a meaningful bottleneck. Define device capability negotiation, command validation, buffer ownership, synchronization, timeout/device-loss handling and fallback.

**Exit:** backend conformance against the reference path, fault-injection and resource-lifetime tests, plus repeatable speed/quality measurements.

### K5 — World and production systems

Streaming, terrain, procedural generation, particles, audio, networking, profiling and production asset workflows.

**Exit:** long-running stress tests, adversarial network/asset suites, recovery tests and end-to-end project workflows.

### K6 — Keel Studio

Shroud-based editor, project management, scene inspection, asset tools, profiling and debugging.

**Exit:** native platform readiness is independently demonstrated by Shroud; editor workflows are usable and accessible on each declared supported platform.

### K7 — Competitive evaluation

Compare Keel against relevant engines, including Unreal Engine, on carefully selected equivalent workloads.

**Exit:** independently repeatable results, documented hardware and versions, raw measurements, feature gaps and narrowly scoped comparative claims.

## 9. Immediate work

The first implementation increment is the K0 specification set. The next code increment should be a minimal, Capstan-compatible scene/math/reference-renderer prototype only after its required language features and numeric semantics have been checked against the actual compiler and runtime.

Do not implement guessed floating-point, generic, concurrency, graphics API, windowing or Shroud host interfaces. If a capability is missing, open a dependency proposal in the owning Capstan/Shroud stream and record the Keel workload that motivates it.

## 10. Scientific and domain library

Keel Science is a proposed companion library for scientific data, digital twins, biomedical research, imaging, biomechanics and other physical-science domains. Units, coordinate frames, uncertainty, provenance, model validity and privacy are explicit contracts. Its initial scope is research and engineering, not diagnosis or clinical decision support. See [Keel Science architecture](KEEL-SCIENCE.md).

## 11. Game-development experience

Game development is a first-class Keel use case, not a downstream application of a research renderer. Keel must provide approachable defaults, progressive disclosure, integrated Capstan-code and visual authoring, rapid iteration, coherent asset workflows, actionable diagnostics, profiling, debugging/replay and reproducible packaging. High-level workflows must not remove expert control or compromise the security and resource contracts. The first playable-game slice and comparative developer-task protocol are defined in [Keel Developer Experience](keel/DEVELOPER-EXPERIENCE.md).

## 12. Naming

**Keel** is the project name. The keel is a principal structural element of a vessel; the name conveys a stable foundation for a complex system and fits the Capstan/Shroud/Anchor nautical naming family. Name availability and trademark status have not been assessed.
