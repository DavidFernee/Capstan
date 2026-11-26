# Keel: detailed technical architecture supplement

> **Status:** technical supplement to the K0 proposal; specifications only
> **Revision:** 2026-11-25
> **Parent architecture:** [Keel](KEEL.md)
> **Research programme:** [Keel research programme](keel/RESEARCH-PROGRAMME.md)
> **Security model:** [Keel security assurance](keel/SECURITY-ASSURANCE.md)
> **Depends on:** reviewed Capstan language/runtime contracts and Shroud's published host/presentation interfaces
> **Does not depend on:** Anchor
>
> This document defines an initial architecture and falsifiable foundation gates. It is
> not evidence that a renderer, GPU backend, secure asset pipeline or production engine
> already exists.

## 1. Purpose and scope

**Normative implementation constraint:** all Keel-owned subsystems and shipped supporting tools are to be authored from scratch in Capstan. Existing engines and third-party runtime libraries are not implementation dependencies. Standards and published algorithms may be implemented independently from their specifications. The current C-backed Capstan compiler/runtime is a disclosed bootstrap dependency; it is not an acceptable language for Keel subsystem code. See [the Capstan-only policy](keel/FROM-SCRATCH-AND-CAPSTAN-ONLY.md).

Keel is the proposed 3D engine for the Capstan ecosystem. Its purpose is to provide
scene construction, spatial mathematics, geometry processing, simulation, asset
ingestion and rendering through a resource-accounted API implemented primarily in
Capstan.

The design objective is not the broadest feature set. It is a small, auditable engine
whose safety and resource contracts are explicit, composable and testable. Keel should
be designed to make invalid states difficult to represent, reject malformed external
data before expensive work, and expose the assumptions that remain outside Capstan's
control.

"Most secure 3D engine" is a research and product ambition, not a current claim. A
security comparison requires named threat models, reproducible adversarial corpora,
version-pinned baselines and independent review.

## 2. Ecosystem placement and dependency rules

The intended dependency graph is:

```
                 Capstan language, compiler and runtime
                                |
                    typed values / memory / effects
                                |
               +----------------+----------------+
               |                                 |
            Shroud                              Keel
       UI and platform host             spatial and 3D engine
               |                                 |
               +---------- application ----------+
                                |
                              Anchor
                    (IDE; consumes both as needed)

       Independent assurance and research spans every boundary.
```

The graph is conceptual: it does not assert that all interfaces are implemented.

Normative dependency rules:

1. Keel may use Shroud's stable public host, input, lifecycle and presentation
   interfaces. It must not reach into Shroud private implementation modules.
2. Shroud must not depend on Keel, 3D scene types, mesh formats or renderer internals.
3. Keel must not become a compiler, language-policy or security-diagnostics authority.
   Capstan remains authoritative for source-language semantics and compiler enforcement.
4. Anchor is a consumer, not a required runtime dependency of either library.
5. Shared code is extracted only after two real consumers and a stable contract exist.
   Similarity alone is not sufficient reason to create a shared abstraction.
6. No dependency cycle is permitted. Platform-specific graphics and window-system
   interfaces remain behind narrow, separately testable adapters.

Keel should remain usable in headless tests and non-Shroud hosts. Shroud integration is
an adapter, not a requirement for scene construction, geometry validation or simulation.

## 3. Responsibility boundaries

| Concern | Owner | Explicit non-responsibility |
|---|---|---|
| Source semantics, type/effect rules, compiler security diagnostics | Capstan | 3D scene or rendering policy |
| Window, input, text, accessibility, UI composition and host lifecycle | Shroud | Scene graph, mesh semantics, GPU resource policy |
| Scene graph, transforms, geometry, simulation, asset decoding, render graph and 3D resource admission | Keel | Compiler semantics and general window toolkit |
| IDE workflows and diagnostics presentation | Anchor | Reimplementing compiler or engine policy |
| Evidence, conformance, fuzzing, proofs, provenance and TCB accounting | Assurance programme | Replacing implementation-specific review |

## 4. Layered Keel architecture

The initial logical layers are:

1. **Public API and typed handles** — explicit scene, node, mesh, material, texture,
   camera and resource identities. Public handles are opaque and validated at every
   trust boundary.
2. **Scene and snapshot model** — acyclic scene hierarchy, stable identity, explicit
   parent/child mutation rules, immutable frame snapshots and deterministic traversal.
3. **Spatial core** — vectors, matrices, quaternions, transforms, bounds, rays, planes,
   frusta and checked geometric predicates.
4. **Geometry and topology** — validated vertex/index streams, mesh invariants,
   normal/tangent generation, spatial acceleration structures and bounded algorithms.
5. **Simulation** — fixed-step scheduling, explicit state transition, deterministic
   input/event ordering and cancellation semantics.
6. **Asset pipeline** — bounded container parsing, format-specific validation,
   decompression limits, cancellation, canonical metadata and immutable decoded assets.
7. **Render graph and command generation** — explicit dependencies, resource states,
   pass ordering, bounded command buffers and backend-independent frame description.
8. **Backends** — deterministic CPU reference path first; optional GPU backends later.
   A backend must declare conformance tolerances and the assumptions it imports.
9. **Host adapters** — Shroud integration and any other host/presentation adapter.
   These translate lifecycle, input, surface and presentation contracts; they do not
   own engine semantics.

The first implementation should not begin with a large GPU API. It should establish the
spatial, scene, validation and resource contracts on a deterministic CPU path.

## 5. Security and trust boundaries

### 5.1 Untrusted inputs

Treat all imported content and host responses as untrusted, including model/mesh files,
textures, shader or material descriptions, animation data, scene documents, compressed
containers, device capabilities, surface dimensions and asynchronous completion events.

The asset pipeline must:

- validate container and chunk boundaries using overflow-safe range checks;
- reject unsupported versions, duplicate or ambiguous fields and invalid references;
- impose input-byte, decoded-byte, object-count, nesting-depth and work budgets;
- check dimensions and products before allocation (division-based bounds where needed);
- bound decompression ratio and total output, not only individual blocks;
- validate indices, vertex layouts, topology and cross-resource references before use;
- support cancellation and deterministic failure without partially publishing an asset;
- keep parsing separate from GPU upload and scene mutation.

No parser may allocate based solely on an untrusted declared count or dimension.

### 5.2 Object identity and lifetime

GPU and asynchronous resources require explicit lifecycle states. The API should distinguish
logical ownership from physical residency and device ownership.

Required design properties:

- opaque generational handles prevent stale IDs from silently naming recycled objects;
- resource creation is transactional: failure leaves no partially visible resource;
- destruction invalidates public handles immediately and defers backend reclamation safely;
- in-flight submissions retain explicit references until completion or device-loss teardown;
- cross-thread access is either immutable, transferred, or protected by a specified protocol;
- device loss invalidates backend objects without corrupting logical scene state;
- cancellation, shutdown and failure paths release reservations and references exactly once.

A generation counter is not by itself a proof against races, wraparound or use-after-free;
those obligations require concurrency design and tests.

### 5.3 Graphics driver and hardware boundary

A GPU driver, kernel graphics subsystem, firmware and hardware are outside the verified
Capstan execution model unless separately specified and evidenced. Keel must not imply
that memory-safe command construction makes a vendor driver safe.

The backend contract must document:

- command and buffer validation performed before submission;
- bounds and alignment guarantees for every uploaded range;
- synchronization and ownership transfer rules;
- what completion means and how timeouts/device loss are surfaced;
- which validation is delegated to the driver;
- which memory/resource limits are logical reservations rather than hard physical caps.

The CPU reference backend is the semantic and diagnostic baseline. GPU output may differ
within a declared tolerance; exact pixel identity is not presumed.

## 6. Resource contract

Keel needs a compositional budget model. A per-object maximum is not an aggregate
resource guarantee. Each scene, asset operation and frame receives an explicit budget
context with monotonic consumption counters.

Candidate dimensions include:

| Resource | Required accounting point |
|---|---|
| Input and decoded asset bytes | Before read/decompression/allocation |
| Scene nodes and hierarchy depth | Before node insertion or traversal |
| Vertices, indices and topology work | Before buffer creation and geometry algorithms |
| Texture dimensions, pixels and decoded bytes | Before decode output allocation |
| CPU allocations and temporary workspace | Before allocation; include simultaneous intermediates |
| Per-frame commands, passes and draw references | Before append/submission |
| GPU logical bytes and object count | Before upload/resource publication |
| Simulation steps and spawned work | Before scheduling/execution |
| Cache residency and eviction work | At admission and eviction |

Budget semantics must specify whether a limit is per operation, scene, frame, process or
device. Composition across nested operations must be explicit. Failed operations must
not consume budget permanently unless the contract says otherwise. Counters must use
checked arithmetic and must not wrap.

The initial implementation should provide deterministic logical CPU budgets. GPU budgets
must be described as admission reservations, not claims about exact physical residency.

## 7. Numerical semantics and determinism

Do not conflate deterministic simulation, robust geometry and deterministic pixels. They
are distinct properties with different assumptions.

The programme should evaluate and document two numeric domains:

- **Deterministic domain:** fixed-step simulation and geometry/topology decisions that
  must agree across supported targets. Candidate techniques include fixed-point
  arithmetic, integer predicates, canonical rounding and robust orientation tests.
- **Rendering domain:** approximate floating-point transforms, shading and rasterisation,
  with explicit NaN/infinity handling, precision requirements and backend-specific
  conformance tolerances.

Before fixing a public numeric representation, run the comparative protocol in
[NUMERIC-SEMANTICS-STUDY.md](keel/NUMERIC-SEMANTICS-STUDY.md). Compare fixed-point,
IEEE-754, restricted deterministic arithmetic and hybrid designs on common workloads.
Specify overflow, rounding, subnormal, NaN, signed-zero, fused-operation and conversion
behaviour. Do not promise cross-platform determinism merely because the same source code
is used.

Geometry algorithms must state their degeneracy policy. Robust predicates should be used
where a sign error can change topology, containment or resource growth. Tolerance-based
comparisons must not be used as a substitute for a defined predicate.

## 8. Concurrency and frame lifecycle

The first vertical slice should be single-threaded and deterministic. Parallelism is a
later optimisation behind immutable snapshots and explicit ownership transfer.

The eventual frame lifecycle is:

1. accept bounded input and simulation events;
2. apply them in a specified order;
3. advance zero or more fixed simulation steps under a step budget;
4. construct an immutable scene snapshot;
5. validate visibility, geometry references and resource reservations;
6. generate a bounded render graph/command stream;
7. execute on the selected backend;
8. publish completion or a typed failure/device-loss event;
9. retire resources only after all relevant submissions release them.

Cancellation and shutdown must be defined at every stage. No background worker may retain
unbounded references to application objects or mutate a published snapshot.

## 9. K0 specification and K1 implementation boundary

The parent proposal in [KEEL.md](KEEL.md) defines K0 as architecture, research and
security specification, with no renderer implementation implied. This supplement does
not change that gate. Its K0 work is limited to:

**K0-A — Contract and threat model**
- reconcile terminology, subsystem ownership, trust boundaries and non-goals with the
  parent proposal and [security assurance](keel/SECURITY-ASSURANCE.md);
- specify handle identity, scene invariants, numeric decision points and resource-budget
  ownership without guessing unsupported Capstan APIs;
- define malformed-input, cancellation and failure-atomicity requirements;
- record unresolved dependencies against the owning Capstan and Shroud streams.

**K0-B — Research and evidence plan**
- assign falsifiable hypotheses, baselines and reproducible experiment protocols using
  [the Keel research programme](keel/RESEARCH-PROGRAMME.md);
- identify which claims can be tested on today's C-backed Capstan path and which depend
  on future language/runtime capabilities;
- define evidence artifacts, status vocabulary and explicit non-claims.

The CPU reference scene/renderer slice belongs to **K1**, not K0. K1 implementation
should begin only after actual compiler/runtime capabilities and numeric semantics have
been checked against the repository. It should then cover, in order:

- checked spatial operations and finite-value/overflow policy; the current narrow kernels are bounded 2D/3D orientation, 2D segment relations and 3D tetrahedron containment in `lib/keel/predicates.cap`, plus checked 3D vectors and closed AABB operations in `lib/keel/spatial.cap`. Shared point types and coordinate domains live in `lib/keel/coordinates.cap`;
- bounded scene nodes, generational handles and acyclic hierarchy;
- camera, transforms and a minimal indexed primitive;
- deterministic backend-independent frame description;
- a deliberately small CPU reference raster path with golden/property tests;
- pre-allocation scene/frame budgets and malformed-scene rejection.

K1 adversarial evidence should include mutation tests for malformed lengths, indices,
cycles, non-finite values and budget boundaries; sanitizer runs where native code exists;
repeated-run determinism within the declared scope; and published seeds, exact revision,
raw outputs and reproduction instructions.

K0 does not include engine implementation. K1 does not include a production GPU backend,
shader compiler, general-purpose asset catalogue, advanced physics, networking, editor,
mobile support or security certification.

## 10. Research programme

Security findings and implementation hazards are tracked in the [Keel vulnerability and design-hazard register](keel/VULNERABILITY-REGISTER.md). A register entry is not closed by specification alone; it requires evidence for the exact implementation and threat scope.


Keel contributes to the Capstan research programme through falsifiable work packages:

- **K-R1 — Compositional resource calculus for spatial workloads.** Can scene, geometry,
  asset and frame budgets compose without hidden transient amplification? Compare static
  contracts, runtime admission and hybrid analysis.
- **K-R2 — Deterministic simulation across heterogeneous targets.** Which numeric and
  scheduling rules produce reproducible state transitions, and at what performance cost?
- **K-R3 — Robust geometric predicates in a resource-bounded language.** Can topology-
  relevant decisions be made reliable under bounded arithmetic and adversarial degeneracy?
- **K-R4 — Safe asynchronous GPU resource lifetimes.** Can a small ownership/state model
  rule out stale-handle use and premature reclamation across submission, completion,
  cancellation and device loss?
- **K-R5 — Adversarial asset ingestion.** Can format parsers provide atomic publication,
  bounded decompression and aggregate-work guarantees with reproducible fuzz evidence?
- **K-R6 — CPU/GPU rendering conformance.** What semantic subset and tolerance model allow
  accelerated backends to refine a deterministic CPU reference?
- **K-R7 — End-to-end assurance composition.** How much of a useful 3D application can be
  covered by Capstan language guarantees, Keel contracts and independently checked
  evidence, and what remains trusted in Shroud, drivers, OS and hardware?

Each work package must record related work, hypotheses, baselines, artefact revisions,
raw data, assumptions, negative results and independent reproduction. A model proof is
not an implementation proof; a parser fuzz result is not a proof of all parser inputs.

## 11. K0 acceptance criteria

K0 is complete only when:

- the parent architecture, this technical supplement and the security-assurance model
  agree on subsystem ownership and dependency direction;
- all K0 decisions, unresolved questions and external dependencies are recorded;
- the threat model inventories assets, project data, shader/extension inputs, network
  messages, host/device interfaces and residual trust;
- the resource-budget register names units, scope, owner, preflight point, failure result
  and cleanup semantics, even where numeric limits remain undecided pending experiments;
- numeric and determinism decisions distinguish simulation, geometry/topology and pixels;
- the research programme has falsifiable hypotheses, related-work tasks, baselines and
  reproducible evidence requirements;
- no K0 text implies that scene, spatial, renderer, asset or GPU controls are implemented;
- K1 prerequisites are checked against actual Capstan and Shroud interfaces rather than
  guessed APIs.

A green documentation or unit-test check alone is not a research result. Publication-
quality evidence is an explicit acceptance criterion for research claims, not a substitute
for product tests.

## 12. Current status and non-claims

| Capability | Status |
|---|---|
| Ecosystem placement and dependency rules | Specified in this document |
| K0 public API and contracts | Target / specification work |
| K1 spatial and scene implementation | Target |
| Spatial core implementation | Not evidenced on this branch |
| Scene graph implementation | Not evidenced on this branch |
| CPU reference renderer | Target |
| GPU backend | Out of K0 |
| Bounded asset ingestion | Target |
| Formal Keel proofs | Not started / not evidenced |
| Production readiness or security certification | Not claimed |

The existence of this supplement or the `keel/k0-foundation` branch is not evidence of
an implemented engine. The parent K0 proposal remains authoritative for phase gates.
Reassess every status against the exact mainline revision and CI evidence before release
claims.
