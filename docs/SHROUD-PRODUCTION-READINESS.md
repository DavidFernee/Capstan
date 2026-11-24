# Shroud: production-readiness and competitive conformance

**Status:** normative programme proposal; not a statement of current implementation maturity  
**Owner:** Shroud workstream  
**Parent tracking:** [#84](https://github.com/DavidFernee/Capstan/issues/84)  
**Scope:** Shroud toolkit. Anchor is a downstream reference application, not a Shroud dependency.

## 1. Product ambition

Shroud is to become a production-grade, cross-platform GUI toolkit written primarily in Capstan. It must be suitable for long-lived desktop applications and, later, mobile and embedded applications. It should compete with Qt, Flutter, GTK and native platform frameworks on reliability, rendering quality, typography, accessibility, performance, developer experience and platform integration.

"Better than the competitors" is an ambition, not a test result. We will not make comparative claims without reproducible, version-pinned workloads, named hardware, raw measurements and independently repeatable procedures. Shroud may have a distinctive advantage in language-level safety, deterministic behaviour and auditable resource limits; those advantages do not excuse gaps in text shaping, accessibility, input methods or platform fidelity.

The current S0 implementation is a promising prototype foundation. It is not a production toolkit. The work below is a multi-stage programme and may require revising existing abstractions where evidence shows they are inadequate.

## 2. Product principles

1. **Correctness before features.** Normative semantics, conformance tests and failure behaviour precede broad widget expansion.
2. **One coherent toolkit.** Core primitives, layout, text, input, semantics, rendering and platform services have explicit contracts. Avoid unrelated widget experiments and duplicated subsystems.
3. **Capstan is the implementation language.** Untrusted text, fonts, images, layout values and application-facing data should remain inside Capstan's safety boundary wherever practical. Any native code is a small, reviewed host boundary.
4. **Source and application logic stay with the application.** Shroud emits typed messages and exposes explicit services; it does not own application business logic.
5. **Deterministic reference behaviour.** A software renderer and deterministic layout/input test model define reference semantics. Accelerated backends must conform to them within documented tolerances.
6. **Native integration is first-class.** A custom-drawn interface must still integrate properly with windows, IMEs, clipboard, drag-and-drop, accessibility, display scaling, power/lifecycle and platform conventions.
7. **Resource limits are architectural.** Every parser, tree, layout pass, raster operation, cache, animation and platform bridge has per-object and aggregate budgets, checked before allocation or expensive work.
8. **Accessibility is not an export format.** The semantic model, events, actions and text ranges are part of the toolkit contract and must be bridged to real assistive technology.
9. **Measure before optimising.** Benchmarks and profiles precede GPU, threading or cache complexity.
10. **Compatibility is deliberate.** Public API stability, deprecation, migration and platform-support policies are documented and tested.

## 3. Layered architecture

The intended dependency direction is:

```
Application model and typed messages
              |
       Shroud public API
              |
  Logical view / component model
              |
  Reconciliation and identity
              |
    Layout and interaction model
       /             \
  Display list     Semantic tree
       |                |
  Software renderer   Accessibility core
       |                |
  Raster / text       Platform bridges
       \                /
       Narrow host interface
              |
   OS windowing, input, text, clipboard,
   accessibility, timing and presentation
```

### 3.1 Public API and component model

- Preserve declarative composition and application-owned state.
- Introduce typed message composition when supported by the language; until then, isolate string actions behind a small compatibility layer.
- Define stable identity, key scope, duplicate handling and state-retention rules.
- Specify lifecycle, disposal and ownership for subscriptions, images, fonts, timers and platform resources.
- Provide a coherent primitive set before design-system breadth: layout, text, drawing, scrolling, focus, semantics, controls and overlays.
- Keep theme/design-system packages above the core primitives.

### 3.2 Reconciliation and layout

- Separate logical view description from the laid-out representation and paint/display representation.
- Specify whether and how unchanged subtrees retain state; identity must not depend on accidental traversal order.
- Define constraints, intrinsic measurement, min/max, flex, grid, baseline alignment, overflow, clipping, scrolling, transforms and snapping.
- Bound tree depth, node count, child count, layout iterations and intermediate arrays.
- Detect invalid constraints, cycles and arithmetic overflow with documented safe failure.
- Establish invalidation and incremental layout only after correctness and benchmark evidence.

### 3.3 Rendering

- Define colour space, transfer function, alpha representation, blend equations, clipping, transforms, stroke/fill rules, image sampling and pixel snapping.
- Maintain a software reference renderer with deterministic golden and property tests.
- Introduce a display list or equivalent immutable frame description to separate scene construction from raster execution.
- Define frame damage, invalidation, scheduling, occlusion and back-pressure.
- Specify image decoding formats, metadata handling, decompression limits and cancellation.
- Keep GPU acceleration out of the foundation until profiles demonstrate a bottleneck. A GPU backend must be optional, capability-detected, bounded, tested against the reference renderer and recoverable to software.

### 3.4 Typography and text

This is a critical production-readiness gap and must not be treated as a minor extension of glyph rasterisation.

- Publish the Unicode version and conformance policy.
- Implement or integrate well-specified grapheme segmentation, word/line breaking, bidirectional ordering and script shaping.
- Support OpenType GSUB/GPOS, kerning, mark attachment, script/language features, fallback, variation axes and font metrics.
- Define font discovery, registration, licensing, fallback and cache invalidation.
- Specify emoji and colour-font policy, including graceful unsupported-font behaviour.
- Define caret movement, selection, hit testing, line geometry, truncation and editing in grapheme/cluster-aware terms.
- Support composition-based input methods, marked text, candidate windows and platform text services.
- Bound font bytes, table counts, glyph counts, composite expansion, shaping work, glyph dimensions, cache entries and aggregate cache memory.
- Fuzz parsers and shaping with malformed fonts, adversarial Unicode and long combining sequences.

### 3.5 Input, focus and interaction

- Normalize pointer, mouse, touch, pen, wheel, trackpad, keyboard and platform gesture input without discarding meaningful device semantics.
- Specify capture, cancellation, hover, drag, double-click, gesture arbitration and multi-pointer identity.
- Define focus scopes, traversal order, tab groups, shortcuts, modal barriers and focus restoration.
- Treat IME composition separately from committed text.
- Define trusted host event provenance and monotonic time at the host boundary. Application-supplied or replayed timestamps must not impersonate trusted physical input.
- Ensure hidden, disabled, inert and obscured controls cannot receive unintended activation.
- Add deterministic event replay and state-machine tests.

### 3.6 Accessibility

- Define a platform-neutral semantic tree with roles, names, descriptions, values, states, relations, bounds, actions, text ranges and stable identities.
- Define semantic change events, live regions, focus changes and announcement policy.
- Bridge to UI Automation on Windows, NSAccessibility on macOS and AT-SPI on Linux.
- Support screen-reader navigation, keyboard-only use, high contrast, text scaling, reduced motion and RTL.
- Test with actual assistive technologies and platform accessibility inspectors; JSON snapshots alone are not acceptance evidence.
- Treat semantic actions as untrusted requests that pass through the same application and runtime authorization boundaries as other input.

## 4. Platform support policy

A platform is **supported** only when its declared OS/architecture/window-system combinations are built and tested continuously, have working input, text, clipboard, accessibility and lifecycle integration, and receive release-blocking regression triage.

Initial desktop targets:

| Platform | Initial target | Required integration |
|---|---|---|
| Linux | Wayland first; X11 compatibility evaluated separately | Window lifecycle, fractional scaling, seat/input, text-input/IME, clipboard, drag-and-drop, presentation, AT-SPI |
| macOS | Current supported macOS release and prior supported release, on Apple Silicon | App/window lifecycle, Retina scale, keyboard, NSEvent, NSTextInputClient, clipboard, drag/drop, NSAccessibility |
| Windows | Current supported Windows release and prior supported release, x64 first | Win32 lifecycle, per-monitor DPI, pointer/keyboard, TSF, clipboard, drag/drop, UI Automation |

The exact minimum OS versions, architectures, compositor/display-server versions and toolchain versions must be recorded in a release matrix before a target is advertised. Mobile targets follow only after the desktop host and text/accessibility contracts are stable.

Native host code is an adapter, not an alternate GUI implementation. It must not parse untrusted application data, decide application permissions or bypass Capstan's runtime security boundary.

## 5. Reliability and security model

Maintain a threat model and a resource-budget register. At minimum, budgets cover:

- logical tree depth, total nodes, children per node and semantic nodes;
- layout work, path segments, clipping depth and paint commands;
- dimensions, total pixels, scanline buffers, image bytes and PNG/intermediate expansion;
- font input bytes, table count, recursive composite work, points, glyph masks and aggregate caches;
- text bytes, grapheme count, line count, shaping operations and fallback attempts;
- event queue depth, pointer count, clipboard payloads and drag/drop payloads;
- animation count, timers, subscriptions, retained surfaces and per-window/per-process resources.

For every budget document: unit, default, maximum, accounting scope, preflight check, failure result, cleanup behaviour and test. Per-object limits must not be presented as aggregate process limits. Failure must be explicit and atomic where practical; no partially valid frame, image, semantic tree or resource should be published as success.

Test with property-based tests, differential tests, deterministic fuzz corpora, long-running stress, allocation-failure injection where supported, and platform-specific adversarial tests. Preserve every discovered defect as a regression.

## 6. Performance and competitive evaluation

Build a benchmark suite before setting public performance claims. Compare equivalent implementations of the same workloads in pinned releases of Qt, Flutter, GTK and relevant native frameworks.

Required workload families:

- startup and first interactive frame;
- static form and large scrolling list;
- deep and wide view trees;
- text-heavy multilingual editor, including bidi and complex scripts;
- image-heavy dashboard and vector-heavy scene;
- animation under input load;
- resize and multi-monitor DPI transitions;
- accessibility tree traversal and update;
- memory after warm-up, cache growth and repeated open/close;
- sustained rendering and input-to-photon latency.

Record hardware, OS, compositor, refresh rate, toolchain, framework versions, build mode, workload source, run count, variance and raw output. Report p50/p95/p99 latency, frame-time distribution, CPU, peak and steady-state memory, allocation volume, startup time and energy where measurable. Avoid a single composite score.

Targets are set only after baseline runs and must be reviewed by the independent assessor. Performance regressions have explicit thresholds and reproducible traces.

## 7. Developer experience and release engineering

A serious toolkit needs more than rendering primitives:

- stable public API and semver-compatible release policy;
- installation, packaging and deployment guidance for every supported platform;
- project templates and a coherent application lifecycle;
- inspectable view/layout/semantic trees;
- diagnostics for constraints, focus, hit testing, font fallback and resource budgets;
- test harness for unit, integration, golden, accessibility and platform tests;
- deterministic replay and crash/diagnostic capture without leaking sensitive text;
- documentation with runnable examples and migration guides;
- API deprecation policy and compatibility suite;
- supply-chain and reproducible-build practices.

Anchor should become a reference application and developer tool for Shroud. Shroud must remain independently buildable, testable and releasable without Anchor.

## 8. Maturity gates

| Gate | Meaning | Minimum evidence |
|---|---|---|
| S0 — Prototype | Core concepts and headless implementation | Existing tests and honest limitation register |
| S1 — Hardened core | Stable core semantics and bounded failure | Adversarial tests, resource accounting, exact-head CI |
| S2 — Desktop host | Real native windows and input on first desktop platform | End-to-end lifecycle, DPI, keyboard, pointer, text input and presentation |
| S3 — Production text/accessibility | Full text editing and real assistive technology | Unicode/shaping conformance, IME, screen-reader test matrix |
| S4 — Production toolkit | Supported platform matrix, stable APIs, performance and reliability | Release process, compatibility suite, benchmark reports, real applications |
| S5 — Competitive maturity | Measured leadership in selected dimensions | Independent comparative results, ecosystem, sustained support and adoption |

A gate is not passed by documentation alone. Each row requires executable tests and reviewable evidence. Features may be experimental without being misrepresented as supported.

## 9. Immediate execution order

1. Finish current S0 security/resource work (#72, #79, #82) with exact-head CI and independent review.
2. Complete and reconcile the existing Shroud assessment and S1 host contract; identify which claims are proposals versus implemented behaviour.
3. Publish subsystem RFCs for public API/identity, layout, display list/rendering, text/shaping, input/focus, accessibility and platform host.
4. Build benchmark and conformance harnesses; establish baselines before setting performance targets.
5. Implement the first native desktop host behind the reviewed host contract.
6. Close the typography and accessibility gaps before broad widget expansion.
7. Validate the toolkit through Anchor and at least one independent non-Anchor application.
8. Establish supported-platform release policy, API stability and production operations.

Parallel work must use explicit path ownership and interface agreements. Do not let multiple workers edit shared test runners, design maps or core APIs concurrently without coordination.

## 10. External architectural references

These references are useful evidence of the scope of a mature toolkit, not templates to copy:

- [Qt supported platforms](https://doc.qt.io/qt-6/supported-platforms.html): explicit platform configurations and active support policy.
- [Qt accessibility](https://doc.qt.io/qt-6/accessible.html): keyboard access, scaling, contrast and platform accessibility interfaces.
- [Qt graphics](https://doc.qt.io/qt-6/topics-graphics.html): software painting and graphics abstraction coexist; acceleration is a layer, not a substitute for a stable drawing contract.
- [Flutter architectural overview](https://docs.flutter.dev/resources/architectural-overview): explicit framework, rendering, engine and embedder layers, including lifecycle, input, accessibility and platform services.

We will compare against these systems empirically and avoid assuming that their architecture or trade-offs are universally correct.
