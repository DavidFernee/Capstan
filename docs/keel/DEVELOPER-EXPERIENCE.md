# Keel developer experience and game-production architecture

**Status:** K0 product and research specification; no editor or game-production workflow is implemented by this document.
**Parent:** [Keel architecture](../KEEL.md)
**Research:** [KR-12 — Game-production workflow](RESEARCH-PROGRAMME.md)

## 1. Product objective

All Keel Studio, project, scene-authoring, asset-workflow, diagnostics, profiling and build-orchestration implementation is to be written from scratch in Capstan. The editor may use Shroud's own Capstan interfaces, but must not embed an existing editor/engine or depend on third-party runtime libraries. See [the Capstan-only policy](FROM-SCRATCH-AND-CAPSTAN-ONLY.md).

Keel must make high-quality games easier to build than with Unreal Engine, while targeting better results on clearly defined workloads. This is a product objective and a research hypothesis, not a present comparative claim.

“Easier” must be measured across the complete production loop, not inferred from a simple API or a polished demo. The target is to reduce the time, specialist knowledge, integration burden and operational complexity required to move from an idea to a shippable, performant, maintainable game.

Keel must not achieve simplicity by hiding important costs, weakening security, removing control, or limiting advanced developers to a lowest-common-denominator workflow.

## 2. Design principles

1. **Playable quickly:** a new project should reach a controllable, visible playable state through a short, documented path.
2. **Progressive disclosure:** sensible defaults and high-level workflows first; lower-level controls remain available without replacing the underlying model.
3. **One coherent workflow:** scene authoring, code, assets, input, animation, audio, UI, testing, profiling, packaging and debugging should work together rather than require fragile glue.
4. **Live iteration:** fast edit-run-inspect cycles, hot reload where semantics permit, useful diagnostics, and reliable recovery from failed edits.
5. **Data-driven, code-friendly:** visual tools and Capstan code must operate on the same explicit project and scene model. Neither is a second-class representation.
6. **Composable systems:** reusable components, prefabs/templates, materials, animation graphs and gameplay systems with clear ownership and versioning.
7. **Good defaults, explicit escape hatches:** common game patterns should be straightforward; specialised rendering, simulation and platform work must remain possible.
8. **Reproducible builds:** project configuration, assets, toolchain versions and build inputs must be identifiable and reproducible.
9. **Accessible tooling:** editor workflows, diagnostics, keyboard navigation and runtime accessibility features are designed in, with Shroud readiness as a dependency.
10. **Security without ceremony:** safe asset import, least-authority extensions, bounded execution and provenance should be defaults rather than burdens imposed on each game team.

## 3. End-to-end game-maker journey

The product must support a coherent workflow for:

- creating a project from a small set of useful templates;
- importing or creating assets with immediate validation and actionable error messages;
- assembling scenes and reusable entities visually or in Capstan code;
- implementing gameplay, UI, input and state transitions;
- authoring materials, lighting, animation, audio and camera behaviour;
- running a game in an integrated preview with inspectable state;
- testing gameplay logic, scene invariants, performance and asset budgets;
- profiling CPU, memory, rendering, streaming and frame-time behaviour;
- reproducing a bug from a project snapshot, seed, event trace and build identity;
- packaging, signing and validating a release for declared targets.

The first editor milestone must not attempt every feature. It must prove that a small game can be created, run, inspected, tested and rebuilt without manual undocumented steps.

## 4. Tooling architecture

Keel Studio is a later Shroud-based application, but the underlying authoring model must be designed before the editor exists.

- **Project model:** versioned manifest, explicit dependencies, target profiles and reproducible build inputs.
- **Scene authoring:** stable entity/component identities, deterministic serialization, validation and merge-friendly text representation where practical.
- **Code integration:** Capstan modules, diagnostics, navigation and build/run actions; no private scripting language that duplicates Capstan.
- **Asset workspace:** import queue, metadata inspection, dependency graph, previews, conversion provenance and per-asset resource budgets.
- **Live inspector:** scene hierarchy, component state, transforms, resource use and simulation state with clear read-only versus mutating actions.
- **Debugging:** breakpoints and stepping when supported by Capstan tooling; otherwise structured logs, event traces, snapshots and deterministic replay.
- **Profiling:** frame timeline, CPU work, allocations, asset decode, streaming, GPU submission and memory/residency where available.
- **Automation:** command-line project validation, test, build and package operations so CI does not depend on GUI automation.
- **Extension model:** signed/versioned packages with declared capabilities, isolated execution and explicit resource limits.

Shroud owns general UI composition, input, accessibility and host lifecycle. Keel owns 3D scene and engine-specific inspectors, render diagnostics and asset semantics. Anchor may provide code-centric workflows but is not a runtime dependency.

## 5. Quality and capability targets

Ease of development must coexist with ambitious results in:

- image quality and temporal stability;
- geometry density, visibility and world scale;
- simulation fidelity and determinism;
- loading, streaming and frame-time consistency;
- memory and CPU/GPU resource efficiency;
- asset interoperability and iteration speed;
- reliability under malformed projects and hostile assets;
- supported-platform reach and accessibility.

“Better than Unreal” is not a single meaningful metric. Every comparison must identify a game/workload class, quality target, hardware, platform, feature set, developer workflow and measured outcome. Keel should aim to outperform on selected dimensions without concealing gaps elsewhere.

## 6. Developer-experience evidence

KR-12 experiments must compare complete tasks, not isolated API calls. Candidate measures include:

- median and p90 time to first playable build;
- time to implement representative gameplay tasks;
- time to diagnose and fix seeded defects;
- number of manual steps and external tools required;
- clean-checkout reproducibility rate;
- build and iteration latency;
- asset-import success and recovery time;
- memory, frame-time and quality achieved by the resulting game;
- accessibility task completion;
- security failures and resource-limit violations during the workflow.

Studies must use matched tasks, documented participant experience, pinned engine/tool versions, equivalent quality targets and disclosed exclusions. Report learning effects and variance. A tutorial designed only for Keel or an intentionally unfamiliar baseline would invalidate the comparison.

## 7. Initial vertical slice and gates

**DX-0 — Workflow contract:** define project manifest, scene authoring model, code/asset boundary, diagnostic vocabulary, target profiles and task-based evaluation protocol.

**DX-1 — First playable game:** create a small complete 3D game using Capstan code and Keel scene/rendering primitives; include input, camera, collision or interaction, simple UI, audio placeholder or integrated audio path as available, restart/quit, tests and deterministic build metadata.

**DX-2 — Integrated authoring:** add the minimum Shroud-based editor workflow needed to inspect and modify the same project/scene model, with CLI parity for validation and builds.

**DX-3 — Production loop:** asset import, reusable scene/entity authoring, profiling, debugging/replay, packaging and CI integration.

**DX-4 — Comparative evaluation:** run pre-registered matched tasks against Unreal and other relevant engines, publish raw timings and quality/performance/security results, and document capability gaps.

A gate passes only when its workflows are exercised on a clean checkout and supported target environment, with reproducible artifacts and user-task evidence. A mock-up, static editor screenshot or demo project alone does not pass.

## 8. Non-goals and safeguards

- Do not build a second general-purpose programming language for gameplay.
- Do not make the editor mandatory for headless builds, CI or server workloads.
- Do not hide project state in opaque, non-diffable files without a documented reason and conversion path.
- Do not introduce hot reload, plugins or scripting mechanisms without defined lifetime, isolation and failure semantics.
- Do not promise cross-platform identical pixels or simulation without a measured and specified contract.
- Do not claim that fewer lines of code necessarily means easier production.
- Do not claim superiority without independent, task-matched evidence.

The product goal is a shorter and more reliable path to excellent games, not merely a smaller engine API.
