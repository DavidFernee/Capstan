# Keel research programme

**Status:** proposed research agenda; no research result is claimed.  
**Programme rule:** each work package must produce both an engineering artifact and an evidence package.

## 1. Research governance

**Implementation constraint:** research prototypes intended for integration must target original Capstan implementations, not wrappers around existing engine/library code. External systems may serve as published baselines and sources of lessons; standards and algorithms may be independently implemented from their specifications. Every subsystem research plan must include a known-vulnerability/design-hazard survey and map relevant findings to explicit mitigations and regression evidence. See [the Capstan-only policy](FROM-SCRATCH-AND-CAPSTAN-ONLY.md).

Keel is integrated with the Capstan research programme. Research questions that require language, compiler, runtime, memory, concurrency, numeric or platform changes are owned jointly with the relevant foundational workstream. Keel must not fork or privately work around foundational semantics.

Each experiment receives a stable identifier and records:
- hypothesis, research question and expected contribution;
- baseline and related work;
- implementation commit and build configuration;
- machine, operating system, compiler, runtime and driver versions;
- input corpus, random seeds and scene hashes;
- correctness oracle and failure criteria;
- raw results, analysis scripts and reproduction steps;
- resource budgets and observed peak use;
- security assumptions and adversarial cases;
- conclusion, limitations and follow-up work.

Negative results are retained. Benchmark selection, excluded runs and tuning decisions must be disclosed. No performance result is accepted without correctness checks on the same build and workload.

## 2. Work packages

### KR-01 — Deterministic numeric and simulation semantics

The executable comparative protocol, candidate families, workload suite and decision gates are specified in [NUMERIC-SEMANTICS-STUDY.md](NUMERIC-SEMANTICS-STUDY.md).

**Question:** What numeric and execution model gives useful physical fidelity while making simulation state reproducible within a clearly defined platform/build scope?

**Hypotheses to test:**
- explicit fixed-step scheduling and deterministic operation ordering can make the simulation repeatable without imposing unacceptable performance costs;
- a carefully specified floating-point profile may provide a better fidelity/performance trade-off than universal fixed-point arithmetic;
- quantised state boundaries can improve replay/network reproducibility without requiring every internal operation to be quantised.

**Experiments:** compare fixed-point, standard floating-point and restricted deterministic arithmetic on identical collision, integration and animation workloads. Measure divergence, energy drift, constraint error, throughput and cross-run/platform reproducibility.

**Capstan dependency:** integer widths, overflow semantics, floating-point support, deterministic standard-library math, scheduler semantics and future concurrency model.

**Acceptance:** published semantic contract; independent reference calculations; repeatability and divergence tests; explicit scope of determinism; raw data.

### KR-02 — Virtualised geometry and visibility

**Question:** Can a hierarchical geometry and visibility architecture process scenes with very high geometric complexity while bounding memory, streaming work and frame-time variance?

**Hypotheses to test:**
- hierarchical clusters and screen-space error metrics can reduce submitted geometry while preserving a declared image-error bound;
- visibility data structures can be selected adaptively using scene and camera statistics;
- a bounded streaming scheduler can reduce stalls without unbounded residency.

**Experiments:** compare brute-force visibility, BVH/frustum approaches, hierarchical clusters, occlusion strategies and level-of-detail policies. Use synthetic adversarial scenes as well as authored scenes. Measure image error, visible/submitted primitives, CPU time, memory, upload volume and p50/p95/p99 frame time.

**Acceptance:** oracle-based correctness on small scenes; adversarial geometry tests; bounded storage/work; reproducible complexity curves; explicit quality/performance trade-offs.

### KR-03 — Global illumination and lighting

**Question:** Which combination of direct lighting, probes, screen-space methods, voxel/volume representations and ray-based methods yields the best quality/performance/resource trade-off for declared scene classes?

**Hypotheses to test:** hybrid methods can provide useful indirect-lighting quality under explicit memory and frame-time budgets; a reference path can measure error independently of the production approximation.

**Experiments:** compare against offline path-traced reference images; measure luminance error, temporal stability, light leakage, memory, update cost and performance across static/dynamic scenes.

**Acceptance:** defined scene classes and error metrics; temporal stability suite; reproducible comparisons; platform-specific limitations. No blanket claim of parity with Lumen or other systems.

### KR-04 — Secure asset ingestion and hostile-content processing

**Question:** Can every asset format be handled within a verifiable resource envelope, with parser isolation and no authority beyond the asset operation?

**Hypotheses to test:** a narrow canonical intermediate representation, strict preflight validation and isolated decoders can reduce attack surface and make resource accounting enforceable.

**Experiments:** build malformed and adversarial corpora for mesh, texture, animation, scene and compressed formats; fuzz parsers; test integer overflow, recursive expansion, oversized dimensions, pathological topology, cyclic references, decompression bombs and cancellation.

**Acceptance:** per-format grammar/schema; pre-allocation bounds; aggregate budgets; fuzzing coverage and regression corpus; fail-closed behaviour; security review. Any claim of memory safety must name the exact implementation and trusted computing base.

### KR-05 — Resource-bounded world streaming

**Question:** How can large worlds be streamed with bounded residency, predictable work and coherent simulation state under constrained memory and I/O?

**Hypotheses to test:** explicit residency budgets, priority scheduling, back-pressure and cancellation can bound worst-case behaviour while maintaining acceptable visual continuity.

**Experiments:** vary world size, object density, I/O latency, memory caps, camera velocity and concurrent requests. Measure missed deadlines, visible gaps, memory peaks, queue depth, cancellation latency and simulation discontinuities.

**Acceptance:** global/per-world/per-resource accounting; overload policy; starvation analysis; deterministic test fixtures; recovery tests.

### KR-06 — Physics, collision and numerical robustness

The first executable spatial work is deliberately narrow and exact: bounded 2D/3D orientation predicates, 2D segment relation classification, 3D point-in-tetrahedron classification, checked 3D integer vectors and closed axis-aligned bounds. Their coordinate domains and intermediate bounds are documented in `lib/keel/predicates.cap` and `lib/keel/spatial.cap`; `tests/keel/check.py` compares them against Python arbitrary-precision oracles, including random, degenerate, permutation, boundary and out-of-domain cases. This is a research prototype, not a formal proof or a general spatial numeric model.

**Question:** How can collision and constraint solvers handle degenerate, adversarial and high-condition-number scenes without unbounded computation or unstable failure?

**Experiments:** broad/narrow phase comparisons, robust predicates, continuous collision detection, constraint solvers and fixed-step integration. Compare against independent high-precision or analytical oracles on selected cases.

**Acceptance:** documented numerical error budgets; pathological geometry corpus; bounded iteration/step policies; deterministic mode tests; explicit handling of non-convergence.

### KR-07 — Secure shader and extension model

**Question:** How can user-authored shader programs and engine extensions be expressive while remaining isolated, resource-bounded and auditable?

**Experiments:** typed shader IR, static resource analysis, instruction/loop budgets, capability separation, compilation isolation and execution fault containment. Compare safe declarative material graphs with programmable shader subsets.

**Acceptance:** versioned IR; validator; resource accounting; no ambient filesystem/network/process authority; adversarial compiler tests; documented GPU/driver trust boundary.

### KR-08 — Formal assurance and refinement

**Question:** Which security- and correctness-critical components can be specified and machine-checked, and how can the proof be connected to executable code?

**Initial targets:** binary/scene decoders, bounds and resource accounting, visibility oracle, deterministic state transition, command validation and selected math kernels.

**Acceptance:** theorem statements with assumptions; proof scripts; reproducible proof environment; refinement or translation validation to implementation; mutation tests that demonstrate the assurance checks detect deliberate violations. Model-only proofs are labelled model-only.

### KR-09 — Parallel execution and frame scheduling

**Question:** Can parallel rendering and simulation improve throughput while preserving bounded queues, ownership safety and a defined determinism contract?

**Experiments:** compare sequential baseline, deterministic task graphs and work-stealing approaches once Capstan supports the required concurrency model. Measure scheduling overhead, tail latency, contention, memory retention and replay divergence.

**Capstan dependency:** concurrency primitives, memory ownership/lifetime, atomic semantics, cancellation and scheduler guarantees. No parallel engine implementation is to precede these contracts.

### KR-10 — Developer workflow and observability

**Question:** Can an integrated engine workflow make complex projects inspectable, reproducible and diagnosable without granting tools excessive authority?

**Experiments:** project import/build/replay workflows; structured diagnostics; frame captures; profiling; deterministic bug reproduction; editor interaction and accessibility tests.

**Acceptance:** reproducible project builds; stable diagnostic schemas; bounded telemetry; no secret leakage; workflow tests and Shroud platform readiness.

### KR-11 — Scientific computing, digital twins and biomedical research

**Question:** Can a reusable scientific domain library represent physical quantities, coordinate frames, temporal observations, uncertainty, provenance and model validity without allowing rendering or simulation approximations to masquerade as measured scientific facts?

**Hypotheses:** dimensional and coordinate-frame contracts can prevent scientific modelling errors; explicit observed/estimated/simulated state can prevent twin-state contamination; provenance and uncertainty can be propagated through image-to-geometry and multi-physics workflows; versioned adapters can preserve external semantics without coupling the engine core to healthcare formats.

**Domains:** industrial twins, robotics, medical imaging, computational anatomy, biomechanics, physiology, neuroscience, microscopy, bioimaging and environmental simulation.

**Experiments:** unit/frame mutation tests; synthetic telemetry with delay, dropout and drift; image geometry and segmentation error analysis; solver convergence and conservation tests; uncertainty propagation; format conformance and semantic round-trip tests; privacy and hostile-input evaluation.

**Dependencies:** Capstan numeric semantics, type/contract expressiveness, resource budgets, capability security, deterministic execution and evidence infrastructure; Keel spatial core, scene graph, asset pipeline, simulation, volume rendering and replay.

**Acceptance:** scientific-core contract; dimensional/frame conformance suite; observed/estimated/simulated state semantics; reproducible synthetic twin; validated synthetic/public imaging slice; version-pinned standards matrix; independent domain review. No clinical validity or regulatory readiness is implied.

## 3. Cross-stream integration register

| Keel need | Owning stream | Integration rule |
|---|---|---|
| Numeric semantics and floating point | Capstan language/runtime | Specify before engine math depends on it |
| Bounded allocation and resource accounting | Capstan runtime | Share normative budget semantics; do not duplicate silently |
| Capability-based filesystem/network/device access | Capstan platform/runtime | Keel requests narrow capabilities; host implementation remains separately audited |
| Concurrency and deterministic scheduling | Capstan language/runtime | No guessed threading or ownership API |
| Native window, input and presentation | Shroud host workstream | Keel Studio consumes only reviewed, shipped contracts |
| Text, IME and accessibility | Shroud | Keel Studio support follows Shroud's evidence gates |
| Formal refinement and proof infrastructure | Capstan assurance | Keel proof claims use shared proof-boundary policy |
| Build provenance and supply chain | Capstan assurance | Keel artifacts inherit and extend provenance requirements |
| Units, numeric contracts and scientific evidence | Capstan language/runtime/assurance | Domain types and proof claims use shared semantic and evidence contracts |
| Biomedical data governance and privacy | Capstan assurance + Keel Science | No real human data in ordinary CI; governed datasets require explicit controls |
| Imaging and healthcare standards adapters | Keel Science interop | Version-pinned adapters; no format-specific semantics in Keel core |

This register must be updated when a dependency is discovered. Each cross-stream change must link the relevant issue, specification and implementation PR.

## 4. Publication policy

A paper or technical report should be considered only when:
1. the research question is novel or materially advances prior work;
2. related work and baseline implementations are fairly represented;
3. methods and datasets are sufficiently described for replication;
4. raw results and limitations are available;
5. claims are no broader than the evidence;
6. security-sensitive details are reviewed for responsible disclosure concerns.

A publication is not an acceptance substitute for shipping tested code. Conversely, shipping code does not itself establish a research contribution.


### KR-12 — Game-production workflow and developer experience

See [DEVELOPER-EXPERIENCE.md](DEVELOPER-EXPERIENCE.md) for the product workflow, tooling architecture, vertical slices and task-based evaluation protocol.

**Question:** Can Keel materially reduce the time, specialist knowledge and integration burden required to build, iterate, debug, optimise and ship high-quality games, while matching or exceeding relevant quality and performance outcomes?

**Hypotheses:** a coherent Capstan-native code and scene model, progressive-disclosure tooling, integrated asset workflows, rapid iteration, structured diagnostics and reproducible builds can reduce end-to-end production friction without limiting expert control; safe defaults and capability-bounded extensions can improve security without making ordinary game development cumbersome.

**Experiments:** compare complete, matched game-development tasks against Unreal Engine and other relevant baselines. Measure time to first playable build, task completion time, seeded-defect diagnosis, manual integration steps, iteration latency, clean-checkout reproducibility, asset-import recovery, accessibility task completion, and the quality/performance/security of the resulting builds. Record participant experience, learning effects, tool versions, hardware, task definitions and exclusions.

**Dependencies:** Capstan language/compiler/runtime and debugging support; Shroud editor host, UI, input and accessibility; Keel scene, asset, rendering, simulation, profiling and packaging contracts; Anchor integration where useful.

**Acceptance:** a complete first-playable-game vertical slice; CLI and editor workflows operating on the same project model; reproducible project/build artifacts; pre-registered matched-task protocol; raw data and analysis; independent review of both developer-experience and resulting-game outcomes. No blanket superiority claim is accepted from a single demo or benchmark.


### KR-13 — Robust bounded polygon topology

Implement a bounded simple-ring validator and point classifier using exact orientation and segment predicates. The first increment caps rings at 256 vertices, rejects self-intersections, repeated non-adjacent contacts, adjacent overlap, degenerate rings and out-of-domain coordinates, and distinguishes outside/boundary/strict interior with an exact winding-number rule. Evaluate adversarial near-collinear vertices, vertex/edge query points, reversed winding, narrow concavities and maximum-size rings against an independent arbitrary-precision oracle. The first simplicity validator is an auditable $O(n^2)$ baseline under the 256-vertex cap. Compare against a Capstan-native exact plane-sweep candidate ($O(n \\log n)$ target) with explicit event ordering for vertical edges, equal-coordinate events, endpoint contacts, collinear overlaps and degeneracies; do not adopt the asymptotic design until its event comparator and active-set invariants have independent proof/test coverage. The comparator, event-group, degeneracy, proof-obligation, differential-test and benchmark gates are specified in [EXACT-SWEEP-LINE-STUDY.md](EXACT-SWEEP-LINE-STUDY.md); the 256-vertex quadratic validator remains normative until every gate passes. This is not a general planar-arrangement or polygon-boolean solution; those require separate construction semantics and complexity budgets. Self-intersecting paths are rejected pending an explicit even-odd versus nonzero-winding contract.


### KR-14 — Trustworthy mesh representation and topology

**Question:** Can Keel define a bounded, immutable, canonical mesh representation that makes index safety, geometric validity, topology and resource ownership explicit without imposing unnecessary restrictions on legitimate scientific and game geometry?

**Initial implementation:** `lib/keel/mesh.cap` supplies a deliberately narrow validation boundary for indexed triangle lists, explicit vertex/index/triangle caps, exact 3D non-degeneracy checks, independently validated vertex bounds, and a stateless deterministic edge/face incidence report. The report classifies boundary, two-face, non-manifold and inconsistent-winding edges, duplicate faces, connected components, referenced vertices and isolated vertices using bounded integer sort-and-scan and iterative union-find. It does not retain caller lists and is not a persistent trust token. See [Mesh Foundation](MESH-FOUNDATION.md) and the [Mesh Ownership and BVH Design Gates](MESH-OWNERSHIP-AND-BVH.md).

**Research questions:** distinguish malformed indices from out-of-domain coordinates; define duplicate-position and duplicate-face policy; determine whether non-manifold and disconnected meshes are valid core geometry or typed topology classes; define winding/orientation semantics; specify robust self-intersection tests; establish canonical vertex/index ordering without destroying provenance; and design immutable ownership with byte-exact aggregate resource accounting.

**Experiments:** property-based mesh generation; independent bounds and triangle-degeneracy oracles; mutation tests for index validation and arithmetic; adversarial maximum-count and repeated-index inputs; topology corpora covering boundary, non-manifold, disconnected, inverted and self-intersecting surfaces; independent edge-incidence, duplicate-face and connected-component oracles (including deterministic generated meshes); and differential canonicalisation tests preserving source mappings.

**Acceptance:** a versioned mesh contract; immutable ownership semantics supported by Capstan runtime guarantees; pre-allocation byte-budget enforcement; independent topology oracle; adversarial and mutation suites; explicit complexity/resource bounds; and evidence that canonicalisation preserves declared provenance. No manifoldness, watertightness, physical validity or GPU safety is inferred from basic triangle-list validation.


### KR-15 — Deterministic bounded spatial acceleration

**Question:** Can Keel construct and query a deterministic CPU bounding-volume hierarchy with explicit memory, depth, stack and work bounds, while preserving brute-force query semantics and safe geometry-versioning?

**Dependency gate:** persistent BVH implementation is blocked on KR-14's immutable mesh ownership capability. The current mutable-list validation interface is not a safe backing store for retained acceleration data.

**Candidate baseline:** a binary AABB hierarchy with stable primitive IDs, deterministic longest-axis median splitting and explicit tie-breaking. Compare against midpoint partitioning and a bounded binned surface-area heuristic; do not assume a heuristic is superior without matched measurements. Start with AABB overlap and candidate enumeration. General ray intersection awaits a selected numeric/ray parameter contract.

**Research questions:** establish worst-case and aggregate node/leaf counts; bound recursion or iterative traversal stack; specify deterministic partitioning under coincident centroids and equal bounds; select build/update thresholds; quantify scratch and persistent memory; and define version mismatch, refit and rebuild semantics. Determine whether any proposed heuristic has a defensible worst-case work bound under adversarial input.

**Experiments:** differential AABB queries against brute force; adversarial sorted, clustered, elongated, coincident-centroid and identical-bound geometry; maximum depth/node/stack tests; repeated-build determinism; refit-versus-rebuild equivalence; and reproducible build/query/update benchmarks with raw data.

**Acceptance:** immutable geometry identity/version binding; byte-exact budget enforcement; explicit node/depth/stack/work caps; deterministic construction; brute-force differential and mutation suites; bounded failure semantics; and evidence-backed build/query/update trade-offs. BVH output is never a correctness oracle, and no GPU backend is implied.


### KR-16 — Mesh topology assurance beyond edge incidence

**Question:** Can Keel distinguish edge-manifoldness, vertex-manifoldness, component-wide orientability and geometric self-intersection with exact, deterministic and resource-bounded predicates?

**Research contract:** [Mesh Topology Assurance](MESH-TOPOLOGY-ASSURANCE.md) defines the vertex-link criterion, parity-constraint formulation for orientability, exact triangle-intersection classifications, complexity targets, adversarial cases and acceptance gates VT-1/2, OR-1/2 and SI-1/2. These are specifications only; no implementation or proof is claimed.

**Experiments:** compare link-graph classifications against exhaustive small complexes and an independent arbitrary-precision oracle; test orientability under arbitrary triangle permutation and independent face reversal; compare bounded exact triangle-pair classification against an independent oracle, including coplanar overlap and contact cases; differential-test any later broad phase against the bounded reference path. Record pre-allocation byte budgets, candidate-pair limits, minimized counterexamples and mutation-test sensitivity.

**Acceptance:** connected vertex links classified as a single cycle or path as appropriate; global orientation parity contradictions detected independently of input winding; exact geometric intersection classes including coplanar cases; deterministic stable diagnostics; bounded storage/work; Capstan-native implementation; and separate evidence for model properties and executable implementation. Persistent mesh assets and retained BVHs remain blocked on compiler/runtime-enforced ownership and byte-exact resource accounting (OWN-1).

### KR-17 — C-Free bounded scratch memory

**Question:** Can Capstan provide temporary algorithm workspace with exact logical byte accounting, bounded lifetime, failure-atomic reservation and deterministic sorting, without exposing raw pointers or relying on the existing C runtime?

**Contract:** [C-Free Bounded Scratch Memory](C-FREE-BOUNDED-SCRATCH.md) specifies a fixed-capacity region, checked aligned reservations, generation-scoped views, reserve-before-mutate discipline, deterministic in-place/caller-scratch sorting, CCAM integration requirements, formal invariants and fault-injection gates. This is a proposal only; no scratch API or CCAM region operation is implemented by this document.

**Research questions:** determine the smallest memory/region model that can be expressed in CCAM; choose byte-count and alignment domains; establish static lifetime enforcement versus runtime generation checks; define reference-bearing storage and collector interaction; prove failure atomicity and non-overlap; and compare zero-auxiliary-space heapsort with caller-reserved stable mergesort.

**Experiments:** exhaustive boundary tests for size/alignment arithmetic; allocation failure at every reservation point; stale-view and reset tests; comparator-law and sort differential tests; memory-accounting checks at exact and one-over budgets; backend-independent conformance; and Keel's maximum-size vertex-link workspace as the first adversarial client.

**Acceptance:** SCR-1 through SCR-6 in the design contract. No public scratch API, hard byte-bound claim or C-Free claim is accepted until the CCAM semantics, Capstan implementation, native backend and refinement evidence exist.

