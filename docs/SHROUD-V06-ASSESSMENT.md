# Shroud v0.6 architecture, security and integration assessment

**Review baseline:** `main` at `457b9c54699404da3e1c2517059ca6d714b31365` (24 November 2026). This is a historical implementation snapshot, including the merged destructive-action clock hardening in PR #54. Subsequent changes integrated after that baseline include PRs #57 (duplicate view identities), #58 (accessibility-text sanitisation), #63 (disabled-control hit blocking), #65 (linear caret placement), and #73 (NUL-safe secret environment names, bounded `read_line()`, and fail-closed local taint analysis); these are merged into `main`. PR #72 (Unicode line-control sanitisation) remains open and draft; its changes are not counted as delivered. PR #79 (aggregate raster/font resource budgets) remains open and draft pending the nested-composite cumulative-budget regression and exact-head validation. PR #92 addresses PNG export amplification with a bounded preflight and a standard-runner independent verifier, but its current 2 MiB scanline ceiling and non-atomic file-write limitation remain explicit. PR #82 tracks the separate streaming/bounded-byte-sink follow-up. PR #51's runtime/GC work remains draft pending collection backing-slot hygiene and complete validation. This document assesses the historical Shroud baseline and should not be read as a claim that pending changes are delivered.

**Scope:** Shroud only. This assessment does not propose changes to compiler or runtime internals and does not implement Anchor.

## 1. Executive assessment

Shroud S0 is a substantial, headless, software-rendered GUI foundation written in Capstan. It already contains fixed-point geometry, constraint/flex layout, a software rasteriser, a bounded TrueType parser, UTF-8 decoding, a small widget set, pointer and keyboard handling, focus traversal, themes, and a JSON accessibility tree. The repository has differential and adversarial tests for several of its most security-sensitive components.

It is not yet a desktop GUI toolkit in the operational sense. There is no native window, event pump, presentation surface, platform accessibility provider, clipboard, input-method integration, or window lifecycle. S0's PNG and scripted-event driver is a test/reference backend, not a production embedder.

The strongest architectural decision is that Shroud draws its own controls and pixels in Capstan, keeping font parsing, text decoding, layout and rasterisation inside the language's safety model. The largest near-term risks are at the boundaries between the visual tree, event dispatch and accessibility representation—not in the basic scanline renderer.

**Recommendation:** finish S0 security invariants and tests before broadening widgets or beginning native embedders. Treat S1 as a separate trusted-platform-boundary project with a versioned contract for clocks, event source, window lifecycle, pixel presentation and accessibility.

## 2. Architecture and maturity

| Layer | Implemented on the review baseline | Maturity / remaining work |
|---|---|---|
| View model | Rebuilt `View` tree; modifiers; `Msg` action/payload | Useful declarative core. Actions remain string/int/text rather than application-typed messages. |
| Layout | Fixed-point constraints; rows, columns, stacks, padding, grow, alignment, scroll; pixel snapping | S0 foundation. Needs property-based constraint tests, duplicate-key handling and stronger clipping/visibility semantics. |
| Paint | Theme-driven widgets, hover/pressed/disabled/focus states | Software-only. No damage tracking, transforms, layers, animation or native compositor. |
| Raster | Integer scanline antialiasing, vector paths, gradients, clipping, premultiplied compositing | Strong deterministic reference backend. GPU backend remains future work and must be differential-tested against this renderer. |
| Text | Strict UTF-8 decode; selected deceptive-character replacement; wrapping and glyph drawing | Latin-focused. No OpenType shaping, UAX #9 bidi, grapheme-aware editing, font fallback or IME composition. |
| Fonts | Bounds-checked TrueType tables, cmap 4/12, simple/composite glyphs and cache | Fuzzed and differential-tested against fontTools for bundled fonts. No CFF/CFF2, variable fonts, colour fonts or system-font discovery. |
| Input | Pointer, wheel, key and text events; hit testing against last laid-out tree | No native event source, pointer-cancel/window-deactivation model, event provenance authentication or multi-window routing. |
| Focus | Tab/Shift+Tab reading-order traversal; keyboard activation; focus ring | No explicit focus-scope/dialog model, no platform focus bridge, and no demonstrated scroll-into-view behaviour for offscreen focused descendants. |
| Accessibility | Roles, names, values, states, bounds; JSON export; name/target/contrast diagnostics | A data model, not yet an OS accessibility implementation. Geometry/clipping/focus equivalence needs adversarial tests and real screen-reader validation. |
| Themes | Light/dark themes and contrast checks | Good baseline. High-contrast/system theme adaptation is not implemented. |
| Platform | PNG output and scripted events | No production Windows, macOS or Linux embedder. |
| Lifecycle/resources | Per-window `Ui`, pixmap and font state | No native window lifecycle, cancellation, device-loss, resource-handle or shutdown contract yet. |

The public surface currently centres on `View`, `Msg`, `Ui`, `Event`, `Pixmap`, and `a11y_tree()` / `a11y_json()`. The application owns the loop and supplies the time passed to `Ui.render(root, time_ms)`.

## 3. Security assessment

### 3.1 What is already useful

- Text fields produce `Tainted` values, so application code must validate user input before treating it as trusted data.
- `untrusted_codepoints()` replaces a selected set of bidi controls, zero-width characters, controls, BOM/soft-hyphen and tag characters before visual rendering.
- UTF-8 decoding rejects overlong forms, surrogate encodings and values above U+10FFFF using replacement behaviour.
- Password fields draw bullets rather than laying out the value; the accessibility representation reports length rather than content.
- Destructive-style buttons use a 500 ms guard. PR #54 changes the guard to use the clock advanced by `Ui.render()`, so a future-dated input event cannot satisfy the delay by itself.
- Font parsing is bounds-checked and fuzzed with truncation, hostile offsets/counts and damaged composite glyphs.
- Resource bounds include view count/depth, a 65,536-byte interactive field-insertion limit, and font/glyph limits; the insertion limit is not currently enforced on initial field values or across the whole laid-out tree. PR #79 adds a proposed 16,777,216-pixel per-pixmap cap; until merged, `main` still enforces only the 16,384-per-side limit.
- Raster output is deterministic and compared against independent geometric coverage and golden-frame references.

These mechanisms reduce specific attack surfaces. None should be described as a complete defence against a malicious application, malicious embedder, arbitrary overlay or synthetic input.

### 3.2 Findings and remaining risks

**A. Event provenance and activation timing**

PR #54 is merged. Guard timing now depends on the `Ui.render()` clock, not the activating event's `time_ms`. This closes the specific future-timestamp bypass in which an event could claim that 500 ms had elapsed.

The caller still supplies the render timestamp. The platform adapter must source it from a trusted monotonic clock and must not allow application-controlled or wall-clock time to stand in for it. Shroud cannot authenticate event provenance, prove that a pixmap was actually presented, establish that a person saw a control, or prevent an OS-level synthetic event. The 500 ms guard mitigates some repositioning/reappearance attacks; it is not a complete clickjacking defence.

**B. Duplicate view identities — pending PR #57**

On the review baseline, explicit `.key()` values are copied directly into `Laid.id` without checking uniqueness. `hit_id()` searches later siblings first (topmost visual order), but `find_laid()` resolves the first matching ID. Overlapping siblings with the same key can therefore cause a click on the visible topmost widget to be dispatched to a different widget's action. Focus resolution can also select the wrong node.

PR #57 proposes unique per-frame internal IDs for duplicate keys, an accessibility diagnostic and an overlapping-stack regression test. It is not yet merged. Even after the dispatch fix, applications must use unique stable keys; duplicate-key state retention remains semantically ambiguous.

**C. Accessibility text discrepancy — pending PR #58**

On the review baseline, `user_text()` accessible names and ordinary text-field values are JSON-escaped from the original `Tainted` bytes. JSON escaping does not perform the bidi/invisible-character mapping used by visual rendering. Assistive technology can consequently receive a different string from the one represented by the pixels.

PR #58 proposes applying the same sanitisation before accessibility serialization and tests bidi override and zero-width-space cases. It is not yet merged. This fixes only the text-value discrepancy; it does not establish equivalence of accessible bounds, clipping, focus order, widget state or platform-provider behaviour.

**D. Unicode is a partial mitigation, not Unicode security completion**

The current character filter is an explicit list, not a complete Unicode property implementation or the Unicode Bidirectional Algorithm. It does not provide shaping or grapheme-aware editing. Additional format characters, combining marks, variation selectors and script-specific invisible characters need review against pinned Unicode data. Replacement marks also do not explain which code point was hidden; a diagnostic/inspection affordance may be useful for security-sensitive workflows.

**E. Accessibility tree and visual equivalence**

The tree is generated from the laid-out view tree, not from the final clipped/presented pixels. Scroll descendants remain in the tree with their laid-out bounds, including descendants outside the scroll viewport; keyboard traversal also collects focusable descendants without an explicit visibility/scroll-into-view step. This may be acceptable for some screen-reader navigation models, but the current headless implementation does not define the platform semantics needed to make it safe and predictable.

Before shipping a native accessibility bridge, define whether offscreen descendants are exposed, how their bounds are clipped or scrolled into view, how focus changes update the viewport, how disabled/hidden states map to platform roles, and how actions are routed back to the exact current node. Validate against UI Automation, NSAccessibility and AT-SPI rather than relying on JSON snapshots alone.

**F. Destructive-action confirmation**

`.danger()` supplies danger styling and a timing guard. It is not a confirmation dialog and does not prove informed consent. Irreversible operations should use an explicit application confirmation flow until Shroud provides a well-defined dialog/confirmation primitive. The confirmation must identify the action and target, and its accessible name and default/cancel behaviour must match the visual presentation.

**G. Focus, cancellation and event state**

The current `Event` set has pointer leave but no explicit pointer-cancel, window-deactivated, focus-lost, capture-lost or device-reset event. A native embedder must not leave `pressed` or focus state stale when the OS cancels a gesture, deactivates a window, or changes input capture. These transitions need explicit event semantics and tests. Event timestamps alone do not authenticate physical input.

**H. Overlays and application deception**

Shroud's z-order and hit testing follow its own view tree. It cannot determine whether another native window, an OS surface, a remote-control overlay or an application-drawn deceptive overlay obscures the control. The embedder can report visibility/activation state where the OS exposes it, but such reporting remains platform-specific evidence, not proof of human perception. Within the Shroud tree, `hit_id()` deliberately searches for the innermost interactive view; decorative/non-interactive siblings do not block pointer input. An application can therefore draw a decorative label or panel over a control while the underlying control remains the hit target. This is a composition hazard that must be explicit in application design; the current toolkit has no general pointer-capture/overlay-blocking policy.

**I. Disabled-control click-through — pending PR #63**

On the review baseline, `hit_id()` treats a disabled button as a hit blocker, but other disabled interactive widgets are omitted because `focusable()` returns false. In an overlapping stack, a click on a disabled checkbox, radio, switch, text field or slider can therefore fall through to an enabled control underneath. PR #63 proposes treating every disabled interactive widget as a pointer hit blocker while keeping it unfocusable and non-activating, with an overlapping-stack regression test. It does not address native overlays or synthetic input.

**J. Quadratic caret placement — pending PR #65**

The field limit is 65,536 bytes, but the original `place_caret()` loop decoded and measured every prefix independently. Clicking in a maximum-sized field could therefore require quadratic CPU work on the UI thread. PR #65 adds byte-end offsets to the existing strict maximal-subpart UTF-8 decoder and accumulates glyph advances in one pass, retaining malformed-input and secure-field semantics. The pre-sync head passed the complete CI matrix. The current PR #65 head has a successful complete CI run; it remains unmerged and is not counted as delivered on `main`.

**K. Non-ASCII line separators in single-line fields — pending PR #72**

`single_line()` on the review baseline removes raw C0 bytes and DEL, but it does not decode Unicode before filtering. UTF-8 encoded C1 controls such as U+0085 NEXT LINE and U+2028/U+2029 LINE/PARAGRAPH SEPARATOR therefore remain in the `Tainted` value sent to the application, even though the display path replaces them with a visible mark. A downstream log, header or record consumer may interpret those code points as line boundaries. The existing “smuggled line breaks” claim is consequently incomplete. PR #72, stacked on PR #65 because both touch `ui.cap` text editing, proposes filtering decoded C0/C1 controls and U+2028/U+2029 using strict decoder byte-end offsets, preserving retained source bytes, rejecting raw paste events over `MAX_FIELD_BYTES` before decoding, and testing both the helper and resulting `Msg.text`. The current PR #72 head fails the formatter/house-style checks for `lib/shroud/ui.cap` on all three platform jobs; the functional, sanitizer, bootstrap, supply-chain and LSP checks passed on Ubuntu/Clang. It remains stacked on #65 and needs formatting correction, a fresh CI run, and retargeting after #65 is integrated.

**L. Pixmap allocation amplification — pending PR #79**

On the review baseline, `new_pixmap()` limits each side to 16,384 but does not limit the product. A request for 16,384 × 16,384 can therefore attempt 268,435,456 list elements (about 2 GiB of 64-bit pixel payload before collection overhead). PR #79 adds a 16,777,216-pixel per-pixmap budget and checks `w <= MAX_PIXMAP_PIXELS / h` after validating positive dimensions, avoiding overflow in the area check. Its regression tests cover exact-budget and over-budget dimensions and verify that the constructor rejects an oversized request before allocation. This is a per-pixmap pixel-payload bound, not a process-wide or aggregate memory limit; multiple pixmaps, list metadata, staging copies and native buffers need separate accounting.

**M. PNG export peak-memory amplification — follow-up required**

`png_encode()` builds the uncompressed scanlines in `raw`, copies them into a stored-DEFLATE stream in `z`, then copies that stream into the final `out` list. These image-sized lists coexist. `png_write()` then calls `bytes_text()`, which builds a further list of one-character strings before joining them into the file contents. Consequently, the pixmap's per-instance pixel cap does not bound PNG export peak memory to the pixmap size; the encoder has multiple full-image copies and no independent output budget. This is currently the deterministic screenshot/golden backend, not the native S1 presentation path, but large or untrusted render dimensions can still amplify memory consumption. Follow-up options are a bounded PNG export contract and a streaming/chunked writer that avoids retaining `raw` and `z` simultaneously. Do not claim the pixmap cap resolves this issue.

**N. Recursive composite-font expansion and glyph-cache amplification — pending PR #79**

The font parser previously bounded recursion depth and the number of components in each composite glyph, but those local limits did not bound the total expansion across the recursive tree. A malicious font could place composites inside composites and multiply the work at each level. The glyph cache also had a 4,096-entry limit but no aggregate alpha-mask pixel budget, and a single glyph could request a large scratch pixmap. PR #79 introduces a shared per-outline budget of 16,384 points and 256 composite components across all recursive levels, a 262,144-pixel per-mask cap, and a 1,048,576-pixel aggregate cache budget per font. These bounds reduce this parser's CPU and memory amplification surfaces; they do not establish a global process-memory limit or replace fuzzing with adversarial composite-font fixtures.

**O. Aggregate layout text expansion — follow-up required**

`layout.cap` permits up to 100,000 views (depth 200). Each text-bearing `Laid` node can retain a decoded code-point list (`cps`) and line-index data (`lines`). `codepoints_of()` decodes the complete trusted text or `Tainted` value during layout. The 65,536-byte `MAX_FIELD_BYTES` limit is enforced when inserting new interactive text, but the initial `View.value` is not visibly rejected at the layout boundary, and there is no aggregate decoded-text budget across the tree. A large pre-populated field or many text-bearing views can therefore amplify memory and layout CPU well beyond the per-interaction insertion limit. The 100,000-view cap bounds node count but not the aggregate text retained by those nodes. A follow-up should enforce a per-field input bound at layout entry and a checked aggregate text-byte/code-point budget before decoding, with exact-limit, one-byte-over, and many-view aggregate regressions. Implementation must be coordinated with PR #57 (which also changes `layout.cap`) and the UI text-editing branches #65/#72.

### 3.3 Security properties to make testable

1. A guarded action cannot be activated until at least 500 ms of trusted monotonic render-clock time has elapsed since its visible identity/geometry changed.
2. An event timestamp cannot advance that guard.
3. A hit-tested node and the node resolved for focus/activation must be the same unique laid-out identity.
4. Untrusted text rendered visually and exposed through accessibility must use the same sanitisation mapping.
5. Password values must not appear in pixels, accessible values, diagnostic strings or exported trees; only an explicitly documented length/empty-state signal may be exposed.
6. Pointer cancellation, window deactivation and focus loss must clear or reconcile transient input state.
7. Accessibility bounds, roles, names, values and states must correspond to the current visible/interactable widget model, with documented offscreen behaviour.
8. Pixmap dimensions and area must be checked before allocation using overflow-safe arithmetic; aggregate render/native-buffer budgets must be explicit at the host boundary.
9. PNG export must have its own checked output/peak-memory budget or a streaming implementation; a pixmap budget alone is insufficient.
10. Recursive font expansion must have aggregate point/component budgets across the entire glyph, not only per-node/depth limits; cached masks must have aggregate pixel budgets.
11. Other resource limits must fail predictably and must not leave partially updated interaction state or stale identity maps.\n12. Initial and aggregate view text must be bounded before UTF-8 decoding and retained code-point/line allocation; the interactive insertion limit alone is insufficient.

## 4. Test evidence and gaps

The existing `tests/shroud/check.py` suite is unusually strong for an early GUI library:

- Behaviour tests for layout, pointer actions, guard timing, keyboard focus, text editing, accessibility, themes, scrolling, raster basics and high-DPI scaling.
- Random polygon raster coverage compared against independent exact-area clipping.
- Font glyph indices, advances and outline bounds compared with fontTools.
- Thousands of UTF-8 edge cases and random byte strings compared with Python's decoder.
- PNG structure/CRC/zlib and pixel-by-pixel checks.
- Damaged-font fuzzing and ASan/UBSan execution.
- Golden hashes for gallery frames and accessibility JSON.

However, the current suite does not yet demonstrate:
- Native window lifecycle, OS input provenance, pointer cancellation or focus-loss handling.
- Real screen-reader behaviour on any platform.
- Accessibility bounds/scroll/focus equivalence for partially visible and fully offscreen descendants.
- Adversarial duplicate-key routing on the merged baseline (covered by pending PR #57).
- C1 and Unicode line/paragraph-separator removal from one-line pasted input on the review baseline (proposed by PR #72; current head needs formatter correction and a fresh CI run).\n- Per-field initial-value and aggregate layout-text limits before decoding; no such aggregate budget is currently implemented.
- Accessibility bidi/invisible-text equivalence on the merged baseline (covered by pending PR #58).
- Full Unicode bidi, shaping, grapheme and IME conformance.
- Multi-window isolation, device loss, clipboard security or destructive confirmation flows.

The current behaviour assertion count should be read from the latest CI log, not copied from the original S0 documentation: the pending security regressions increase it.

## 5. Roadmap towards v0.6

### S0 hardening — do before native embedders

- Merge and retain the duplicate-identity and accessibility-text fixes after full CI and review.
- Add explicit duplicate-key tests across nested containers, scroll views and focus traversal.
- Add pointer-cancel, window-deactivate and focus-loss semantics, with no stale activation after cancellation.
- Specify the render-clock contract and monotonicity/failure behaviour.
- Add property tests for accessibility tree consistency, clipping and focus visibility.
- Clarify that `.danger()` is a guard/style, not confirmation.
- Add adversarial tests for Unicode format characters not currently in the filter.
- Remove C0/C1 controls and U+2028/U+2029 from one-line field values, with tests against the exact `Msg.text` bytes.\n- Add per-field initial-value and aggregate layout-text byte/code-point budgets before decoding; coordinate with #57, #65 and #72 because they touch the same layout/UI surfaces.

### S1 platform boundary

- Draft host contract is available in [PR #70](https://github.com/DavidFernee/Capstan/pull/70) (`docs/SHROUD-HOST.md`); it remains a proposal until reviewed and merged.
- Define a small, versioned embedder contract before implementation: window creation/destruction, event pump, monotonic clock, input provenance metadata, pixmap presentation, DPI/scale negotiation, focus/capture/cancel events, clipboard/IME and accessibility provider callbacks.
- Implement Wayland first only after capability I/O and the system-call boundary are available; keep system-library results untrusted and confined.
- Add Windows and macOS embedders with their native accessibility and text-input APIs.
- Test lifecycle teardown, resize, monitor-scale changes, occlusion/deactivation and device loss.

### S2 text and internationalisation

- Implement OpenType shaping, font fallback, UAX #9 bidi, UAX #14 line breaking and UAX #29 grapheme segmentation.
- Use pinned Unicode conformance data and differential tests against established reference implementations.
- Add selection, multiline editing, IME composition and clipboard semantics; paste remains `Tainted`.

### S3 rendering and motion

- Keep the integer software rasteriser as the reference implementation.
- Add GPU backends only behind a stable scene interface and differential image tests.
- Add image decoders in Capstan with fuzzing and resource budgets before exposing image widgets.

### S4–S7 product breadth and assurance

- Add virtualised collections, tables, menus, dialogs, navigation and other widgets only after focus, accessibility and lifecycle primitives exist.
- Add typed `View<M>` messages when the language type-system milestone supports them.
- Validate WCAG 2.2 AA, EN 301 549 and Section 508 with real assistive technologies.
- Add secure-field, screen-capture, protective-marking and audit capabilities only with explicit OS-level contracts and assurance evidence.

## 6. Current Anchor integration contract

Anchor A0 may consume the existing headless surface, but must not assume that a native embedder exists.

### Available now

- Build a `View` tree from application state.
- Call `Ui.render(view, monotonic_time_ms)`.
- Read the resulting `Ui.pixmap` for headless output.
- Deliver scripted `Event` values to `Ui.handle(event)`.
- Apply returned `Msg` values to application state.
- Read `a11y_tree()` / `a11y_json()` for diagnostics or a headless inspector.

### Contractual constraints

- Use unique, stable `.key()` values for stateful controls and list items. Do not rely on duplicate-key behaviour.
- The caller-supplied `render` timestamp must come from a trusted monotonic platform clock. Do not use wall-clock time or an event's timestamp as a substitute.
- `Event.time_ms` is adapter metadata, not proof of physical input. Shroud does not authenticate it.
- Treat `Msg` action names and payloads as application messages, not as an authorization decision. Revalidate application state and permissions when applying them.
- Preserve `Tainted` input until application validation. Do not turn a UI value into a trusted path, command or query merely because it came through a widget.
- Password fields expose no password value through the current accessibility JSON contract. Do not add clipboard or logging paths that copy the secret.
- The accessibility JSON is not a native accessibility provider and must not be presented as full platform accessibility support.
- Anchor must own its own window lifecycle and must label native presentation, clipboard, IME, accessibility and multi-window support unavailable until Shroud supplies and tests those APIs.

### Not available yet

Native window creation, event-source integration, lifecycle notifications, authenticated event provenance, OS accessibility actions, clipboard, drag/drop, IME composition, GPU presentation, multi-window routing, animation and screen-capture protection.

## 7. Release gates

Shroud should not be described as production-ready on a platform until all of the following are true:

- The complete CI matrix passes, including Shroud behavioural, raster, font, UTF-8, fuzz, golden and sanitizer checks.
- S0 security invariants 1–11 above have regression tests.
- The embedder contract and platform-specific trust assumptions are documented.
- Real keyboard-only and screen-reader workflows pass on the target OS.
- Resize, DPI, occlusion, focus loss, cancellation, shutdown and resource-failure paths are tested.
- The implementation does not claim that a timing guard prevents arbitrary clickjacking or that an accessibility JSON tree proves platform accessibility conformance.

## 8. References

- [Shroud implementation](../lib/shroud/)
- [Shroud S0 documentation and roadmap](SHROUD.md)
- [Shroud behaviour and differential tests](../tests/shroud/)
- [Anchor architecture and A0 prototype, PR #53](https://github.com/DavidFernee/Capstan/pull/53)
- [Agent coordination issue #25](https://github.com/DavidFernee/Capstan/issues/25)
- [PR #54 — merged activation-clock hardening](https://github.com/DavidFernee/Capstan/pull/54)
- [PR #57 — merged duplicate-key identity hardening](https://github.com/DavidFernee/Capstan/pull/57)
- [PR #58 — merged accessibility text sanitisation](https://github.com/DavidFernee/Capstan/pull/58)
- [PR #63 — merged disabled-control hit blocking](https://github.com/DavidFernee/Capstan/pull/63)
- [PR #65 — merged linear-time caret placement](https://github.com/DavidFernee/Capstan/pull/65)
- [PR #72 — open draft for Unicode single-line input sanitisation; not yet delivered](https://github.com/DavidFernee/Capstan/pull/72)
- [PR #70 — draft S1 native host contract](https://github.com/DavidFernee/Capstan/pull/70)
- [PR #73 — merged runtime input and local-taint hardening](https://github.com/DavidFernee/Capstan/pull/73)
- [PR #79 — draft aggregate raster/font resource budgets](https://github.com/DavidFernee/Capstan/pull/79)
- [PR #92 — PNG export budget and verifier](https://github.com/DavidFernee/Capstan/pull/92)
- [Issue #82 — bounded streaming byte-sink follow-up](https://github.com/DavidFernee/Capstan/issues/82)
