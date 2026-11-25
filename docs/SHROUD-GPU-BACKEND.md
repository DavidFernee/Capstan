# Shroud GPU backend: architecture and acceptance contract

**Status:** G0 contract and G1 display-list recording/reference executor implemented on the GPU development branch; no hardware backend exists yet.
**Scope:** optional rendering acceleration for Shroud. The software rasteriser remains normative.

## 1. Current architectural constraint

The current renderer is immediate-mode. `paint_tree` recursively paints `Laid` nodes into a mutable `Canvas`; `Canvas` calls `fill_rect`, `fill_path`, glyph rasterisation and per-pixel blending directly against a Capstan `Pixmap` backed by `List<int>`. The rasteriser uses integer fixed-point geometry, 16 vertical sub-samples, exact integer blend operations and premultiplied `0xAARRGGBB` pixels.

There is no immutable frame/display-list representation, no GPU resource abstraction, no shader compiler/runtime contract, no native graphics context and no device/presentation host API. A GPU implementation added directly to the current call graph would either duplicate widget painting or introduce an implicit platform dependency. Neither is acceptable.

## 2. Intended architecture

```
View / Laid tree
      |
paint recording (immutable, bounded DisplayList)
      |                         |
software executor           GPU executor
      |                         |
reference Pixmap          device-owned targets
      |                         |
headless PNG/test oracle   narrow host present/readback boundary
```

The display list is the key prerequisite. It must record only validated, backend-neutral operations (clear, rectangle, path, glyph run, clip push/pop, opacity and image). It owns immutable copies or stable frame-scoped references; it must not retain pointers into mutable `Ui`, `Laid`, font parser state or application buffers. Commands, path segments, glyph references, aggregate bytes and frame work must be budgeted before publication. Frame construction is failure-atomic.

The first GPU executor should target a narrow, explicit backend API (Vulkan is the preferred cross-platform candidate, subject to dependency and host review). Do not add Vulkan calls to `lib/shroud` or make a C graphics runtime part of the toolkit. A native adapter may own instance/device/queue/swapchain and synchronization, but only behind a versioned host capability contract. Platform-specific presentation remains host-owned.

## 3. Normative rendering semantics

The software renderer remains the deterministic oracle. The backend contract must explicitly specify:

- pixel format: premultiplied `0xAARRGGBB` at the Shroud API boundary;
- blend: source-over in the documented colour space, with alpha premultiplication performed exactly once;
- clipping: intersection with the current clip, including nested clip-stack behaviour;
- geometry: fixed-point input and documented edge inclusion / fill-rule semantics;
- gradients: endpoint, interpolation and degenerate-vector semantics;
- image sampling, colour conversion, glyph mask interpretation and pixel snapping;
- surface origin, row stride, device scale and readback ordering.

The GPU may use a different internal representation, but conversion at the boundary must be explicit. Exact byte equality is required for integer-exact operations. Operations that cannot be reproduced exactly must have a separately approved, measured per-channel tolerance and golden corpus. No global tolerance may conceal blend, clipping or geometry defects. Deterministic mode must always be able to select software.

## 4. Selection and fallback contract

- `software-only` never probes or creates a GPU device.
- `prefer-gpu` selects GPU only when API version, required pixel semantics, dimensions and resource budget are all supported; otherwise it selects software with a stable diagnostic reason.
- `require-gpu` fails explicitly if any required capability is absent; it must never silently render in software.
- Device loss, context loss, allocation failure or unsupported command invalidates the in-flight GPU frame. It must not publish a partially rendered surface.
- After loss, stop GPU submissions, invalidate device-owned handles, release accounting exactly once, recreate only through the host lifecycle contract, and use software until a new device passes capability checks.
- Fallback must preserve the same logical frame and input/layout state. It must not replay side effects or dispatch input twice.

## 5. Resource and concurrency contract

Every GPU allocation is charged against a per-device and per-process budget before creation. Arithmetic uses subtraction-based capacity checks. Resource handles are opaque, generation-tagged and cannot be used after device loss or close. Destruction is idempotent; deferred destruction is bounded and tied to explicit completion fences. No host pointer or raw device handle enters application-visible Shroud values.

Frame submission is single-owner initially. Do not introduce background GPU threads until frame ownership, cancellation, queue back-pressure and shutdown are specified. At most a bounded number of frames may be in flight. Resize creates a new generation; old-generation completions cannot publish into the new surface.

## 6. Delivery stages

1. **G0 — contract:** backend semantics, capability negotiation, resource accounting, loss/fallback and executable reference model. Implemented on this branch.
2. **G1 — display list:** bounded command recording and software replay are implemented on this branch. The UI render path records rectangle, flattened path, glyph-mask and individual blend commands, then replays them through the existing integer rasteriser. Each command snapshots its effective clip and bounded opacity/coverage. Published frame command sequences and all nested variable-sized payloads are deep-copied: flattened path coordinate arrays and glyph alpha arrays receive frame-owned storage, so later recorder/cache mutation cannot alter a published frame. Snapshot admission recomputes command and payload bounds rather than trusting mutable recorder counters, checks parallel path-array shape before allocation, and independently copies each array so malformed recorder state cannot cause an unchecked cross-array read during snapshotting. Direct and replayed blend operations reject coordinates outside the surface or active clip and clamp coverage/opacity before multiplication. The public replay boundary validates the complete command sequence, clip rectangles, paint values, path-array shape and coordinate ranges, mask dimensions and canonical 0..255 alpha values, rejects variable-sized payloads attached to command kinds that do not consume them, and checks payload totals and opacity before touching the destination; malformed frames fail closed without partial output. Frame limits cap command count, aggregate geometry/mask payload, per-path geometry and conservative aggregate raster work. Rectangle work is charged by clipped pixel area; path work includes clipped scanline edge scans, per-sub-scanline crossing/sort work and the clipped output-pixel pass; mask work is charged by its full pixel payload. Frames exceeding the work budget are rejected before the destination is touched. Differential behaviour tests compare immediate and replayed pixels, exercise empty glyphs, verify snapshot isolation, reject malformed display-list metadata and cover invalid blend coordinates/coverage. Exact golden/CI validation is still required before G1 is considered complete.
3. **G2 — host capability:** reviewed native host interface for device creation, submission, completion, presentation and readback; no ambient OS lookup.
4. **G3 — first GPU executor:** offscreen integer-target rendering of a restricted command subset; software fallback for unsupported commands.
5. **G4 — parity and resilience:** differential goldens, device-loss injection, resize generations, allocation failures, long-run resource accounting.
6. **G5 — measured enablement:** representative benchmark suite demonstrates a material benefit on named hardware; default policy remains software until data justifies a change.

## 7. Acceptance gates for a production backend

- No GPU dependency or device probe in software-only/headless builds.
- The software golden corpus is unchanged by display-list introduction.
- Every command has defined semantics and bounded resource/work cost.
- Differential tests cover solids, alpha, gradients, nested clips, paths, glyphs, resize, scale and malformed/over-budget frames.
- Device loss and all allocation/submit/readback errors are failure-atomic and recover to software.
- No stale generation can publish after resize or close.
- Cross-platform CI includes builds without GPU SDKs and optional backend builds with pinned SDK versions.
- Benchmarks report raw frame-time distributions, CPU/GPU time, memory, upload/readback cost, hardware, driver, OS, compositor and workload. No performance claim without reproducible measurements.

## 8. Explicit non-goals of G0

This branch adds no GPU driver, shader, native window, Vulkan dependency, C shim, hardware detection, asynchronous execution or performance claim. The display list is a prerequisite, not evidence of hardware acceleration. The software executor remains the only production executor until G2–G5 are implemented and validated.
