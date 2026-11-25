# Keel research programme

**Status:** proposed research agenda; no research result is claimed.  
**Programme rule:** each work package must produce both an engineering artifact and an evidence package.

## 1. Research governance

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
