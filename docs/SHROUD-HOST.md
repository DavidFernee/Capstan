# Shroud S1: native host contract

**Status:** design contract for S1; not a shipped API.
**Scope:** the boundary between Shroud's existing, deterministic, headless UI core and a native platform embedder.
**First target:** Linux/Wayland. Windows and macOS follow the same contract with platform-specific backends.

This document is normative for the responsibilities and security properties of an S1 embedder. Names such as `HostWindow`, `FrameLease` and `HostEvent` below describe concepts, not current Capstan declarations. Do not implement against guessed signatures. Concrete Capstan APIs require the v0.6 capability-I/O and T6 system-call work, and must be reviewed as a versioned public API before implementation.

## 1. Ownership boundary

Shroud owns:
- the `View` and `Laid` trees, layout, hit testing, widget state, rendering, software rasterisation and message generation;
- the canonical event vocabulary and normalization rules;
- the trusted-clock policy used by activation guards;
- the accessibility semantics and mapping from Shroud roles/states to platform accessibility providers;
- the public host lifecycle and presentation contract.

The platform embedder owns:
- native window creation/destruction and OS event-pump integration;
- acquisition of a monotonic clock and sampling it at the host boundary;
- conversion between native client coordinates, physical pixels and Shroud's fixed-point coordinates;
- native surface/buffer allocation, pixel-format conversion where needed, and presentation/vsync;
- OS keyboard, pointer, focus, capture, text-input and clipboard facilities;
- platform accessibility-provider registration and native notification delivery;
- translating native failures into explicit host errors without silently fabricating successful operations.

Anchor and applications consume the Shroud host API. They must not implement a second widget toolkit, write directly into Shroud's internal state, or bypass the embedder's input and presentation rules.

One `Ui` belongs to one top-level window. S1 initially supports one window per host instance; multi-window ownership and shared resources are a later extension.

## 2. Existing core contract (S0)

The current public construction and drive pattern is:

```capstan
Ui ui = new_ui(font, bold, light_theme(), width_px, height_px, scale);
ui.render(view_of(model), monotonic_time_ms);
Pixmap frame = ui.pixmap;
List<Msg> messages = ui.handle(event);
```

The current implementation has no native window, event pump, resize operation, buffer lease, clipboard, IME composition, or platform accessibility provider. The JSON accessibility tree is diagnostic output, not a native accessibility implementation.

The existing pixel buffer stores premultiplied `0xAARRGGBB` integer pixels, row-major, with a tightly packed `w * h` pixel list. The current `Ui` mutates and reuses its pixmap on subsequent renders. An embedder must not retain a pointer or view into that mutable storage for asynchronous presentation after another render has begun.

## 3. Coordinate and DPI contract

- `width_px` and `height_px` are the physical client-area pixel dimensions of the software-rendered surface, not the outer window frame and not logical points.
- `scale` is Shroud fixed-point scale: 256 means 1.0 device pixels per dp; 384 means 1.5; 512 means 2.0. The native adapter computes it from the platform's effective window DPI/scale using integer arithmetic and reports the actual physical surface dimensions separately.
- Pointer coordinates are relative to the client-area origin, in physical device pixels converted to Shroud FX units: `x_fx = x_px * 256`, `y_fx = y_px * 256`. Do not pass screen coordinates, title-bar offsets, logical points, or unscaled dp values.
- A DPI transition is a resize/scale transition. The host must update both the physical surface dimensions and scale as one coherent change; it must not render one frame with a new scale and an old-size surface.
- Fractional scaling must preserve integer rounding rules and be tested at 100%, 125%, 150%, 175% and 200%, including monitor-to-monitor transitions.

S0 has no `Ui.resize` method. S1 must introduce a reviewed resize operation or an explicit state-preserving reconstruction contract. Reconstructing `Ui` with `new_ui` currently resets focus, scroll offsets, caret positions and activation-guard history; the host must not pretend those states survive. Until a preserving resize API exists, a resize that reconstructs `Ui` is a documented state reset, not a transparent resize.

## 4. Clock and event-time trust

The activation guard is measured from the clock passed to `Ui.render`, not from `Event.time_ms`. This distinction is security-critical.

- The host samples a monotonic OS clock itself. It must not use wall-clock time, a timestamp supplied by an input event, a client message, a remote peer, or application-controlled data.
- The host passes the sampled value to `render` and stamps normalized events from the same monotonic clock domain.
- The host must clamp or reject clock regressions before calling Shroud. It must never advance the clock to make an event appear old enough to activate a guarded control.
- Native event timestamps may be retained for diagnostics only after validation; they are not authoritative for guard decisions.
- On suspend/resume, clock discontinuity, or clock-source failure, the host must fail closed: reset/restart guarded-control delays and avoid dispatching queued stale activation events until a fresh frame has been rendered.
- Event timestamps do not prove human intent, visibility, event provenance, or that a frame reached the display. The guard is a timing mitigation, not proof of informed consent.

The current API accepts signed integer milliseconds. S1 must define overflow-safe conversion and wrap handling for the chosen Capstan integer width and host clock source.

## 5. Frame ownership and presentation

The host receives a completed Shroud pixmap after `render`.

- Treat each frame as immutable for the duration of presentation.
- Because S0 reuses the same backing list, the host must either copy pixels into a host-owned presentation buffer before the next render, or synchronously complete consumption before allowing another render to mutate the pixmap.
- An asynchronous compositor/GPU upload must own its copied/staged data until the platform signals completion. Never enqueue a borrowed pointer to `ui.pixmap.px` and then render again.
- Preserve premultiplied alpha. The canonical logical pixel is `0xAARRGGBB`; a backend whose native byte order or surface format differs must convert explicitly and test channel order and alpha.
- The current row stride is exactly `width * 4` bytes. A future external-buffer API must make stride, format, ownership and lifetime explicit rather than infer them.
- Presentation failure is a host error. Do not report a frame as displayed merely because Shroud rendered it. The host should retain enough state to repaint after exposure, occlusion or surface loss.
- Initial S1 may present a full frame on every render. Damage tracking and vsync pacing are later optimisations; they must not change the reference software-rendering result.

## 6. Input normalization

The embedder translates OS events into the existing Shroud event vocabulary. It must not dispatch directly to widget actions or bypass `Ui.handle`.

| Native input | Shroud event | Contract |
|---|---|---|
| Pointer motion | `EV_POINTER_MOVE` | Client-area physical coordinates in FX |
| Pointer button press/release | `EV_POINTER_DOWN` / `EV_POINTER_UP` | Normalized button policy; S1 initially maps primary activation only |
| Pointer exits client area | `EV_POINTER_LEAVE` | Clear hover; does not itself imply release |
| Wheel/trackpad scroll | `EV_WHEEL` | Client coordinates and a documented signed delta convention; normalize platform units before dispatch |
| Physical/logical key command | `EV_KEY` | Map to Shroud key constants and modifier bits; do not encode committed text as key codes |
| Committed text | `EV_TEXT` | UTF-8 delivered as `Tainted`; never mark user text trusted |

Additional requirements:

- Use the native window's focused state. Do not deliver keyboard or text events to an inactive window.
- Capture the pointer from primary-button down through release/cancel so Shroud receives the terminal event even if the pointer leaves the client area. A release outside the hit target must cancel activation; it must not be converted into an in-bounds release.
- Send a leave event when the pointer leaves the client area. Do not synthesize a pointer move to the last in-bounds location on exit.
- Normalize key repeat deliberately. Repeated navigation/editing keys may be supported; repeated activation keys must not accidentally produce multiple destructive activations.
- Deliver committed text separately from key events. Do not synthesize text by interpreting keycodes in Shroud or in Anchor.
- S0 has no composition/pre-edit API. An embedder must not claim complete IME support by sending each composition update as committed `EV_TEXT`. S2 must add explicit composition state, candidate-window geometry and commit/cancel semantics before full CJK/Indic input is advertised.
- S0 has no clipboard or selection API. Do not implement copy/paste by injecting privileged text or by reading/writing the clipboard behind the application's back. Clipboard support needs an explicit, permission-aware API and secure-field policy.
- Coalesce high-frequency pointer motion only when doing so preserves the final position and does not drop button transitions, wheel events, key events or committed text.

## 7. Focus, activation and lifecycle

- Native window activation and Shroud widget focus are distinct. On loss of native focus, stop dispatching keyboard/text input and clear transient pressed/hover state through an explicit host-to-core transition; do not silently leave a control visually pressed.
- Tab order and keyboard activation remain owned by Shroud. The host maps native keys/modifiers; it must not create a second focus order.
- Pointer capture is a host mechanism used to deliver a complete press/release sequence; it does not grant a widget focus or activation.
- On close request, the host asks the application to decide whether to close. Destruction is explicit and idempotent; after destruction, no event, frame callback or accessibility notification may target the old `Ui`.
- Surface loss, display sleep, monitor removal and compositor restart require a recoverable host state transition. A stale surface must never be presented as current.
- The initial contract is single-threaded: all calls mutating a `Ui` occur on its owning UI thread. Background I/O may signal the event loop, but it must not call `render`, `handle`, resize or mutate `Ui` concurrently.
- Shutdown must stop event delivery, cancel pointer capture and pending text composition, unregister accessibility providers, release native buffers/surfaces, then release Shroud-owned resources.

## 8. Accessibility bridge

The S0 `a11y_tree()`/JSON output provides roles, names, values, states and bounds for tests and diagnostics. It is not yet a platform accessibility provider and does not establish WCAG conformance.

S1's platform bridge must:
- expose native accessible objects whose role, name, value, disabled/checked/focused state and bounds derive from the same Shroud view/layout state used for painting and input;
- use Shroud's sanitised visible representation for untrusted text; never reintroduce original bidi or invisible controls into the native accessible name/value;
- keep password values undisclosed, including through notifications, debug logs and platform value interfaces;
- map native accessibility actions back through the same Shroud event/action path, with the same disabled, guarded and focus checks as pointer/keyboard input;
- notify assistive technology when the tree, focus, value, checked state or bounds change, without exposing stale nodes after rebuild/destruction;
- maintain stable native object identity only where Shroud identity is unique and valid; report duplicate-key diagnostics rather than merging unrelated accessible nodes;
- test actual Narrator/NVDA/JAWS, VoiceOver and Orca behaviour on supported platforms before claiming support.

A JSON snapshot alone is not a substitute for UI Automation, NSAccessibility or AT-SPI. S1 support must be stated per platform and per tested screen reader.

## 9. Security properties and limits

| Property | Required embedder behaviour | What it does not prove |
|---|---|---|
| Trusted guard clock | Sample host monotonic time; ignore event-supplied timestamps for authorization | That a human saw the control or that native overlays are absent |
| Frame/input coherence | Dispatch only against the last successfully rendered frame; discard stale queued input after surface loss/resize | That the compositor displayed the frame or that no other window obscured it |
| Event routing | Route every input through `Ui.handle`; preserve down/up/cancel provenance and coordinates | That OS input is genuine rather than injected by accessibility tools, automation or malware |
| Text safety | Preserve `Tainted` on committed user text and Shroud sanitisation in accessibility output | That arbitrary application-provided trusted labels are truthful |
| Password privacy | Never copy password values into host logs, accessibility values, clipboard or diagnostics | Protection from screen capture, process memory inspection or malicious host software |
| Native accessibility | Mirror Shroud semantics and enforce the same action checks | Full assistive-technology equivalence without platform testing |

Native overlays, malicious accessibility clients, remote-control software, OS-level input injection, screen capture and deceptive content drawn by the application remain outside the protection boundary of the headless S0 core. The embedder reduces specific attack surfaces; it cannot establish trusted display hardware or prove user intent.

## 10. Errors and resource limits

S1 must make native failures explicit and recoverable where the OS permits:
- window/surface creation, resize, buffer allocation, mapping, presentation, event-pump and accessibility-provider failures;
- unsupported protocol versions, missing Wayland globals, lost display connections and device removal;
- invalid or out-of-range dimensions, scale values, event coordinates and timestamps;
- partial initialization and shutdown after any intermediate failure.

The current `new_pixmap()` rejects invalid dimensions by stopping the process. Before native embedding, the public host construction/resize boundary must validate dimensions and return a typed failure before calling that path. Platform errors and OS-provided strings are untrusted; they must not become trusted labels or format strings.

All buffers must have checked size/stride arithmetic and explicit maximum dimensions. The current software pixmap limit is 16,384 pixels per side; practical host limits should be lower and configurable to avoid allocating near the theoretical maximum. Native buffers, staging copies and accessibility objects must be released on every failure path.

## 11. Platform rollout

1. **Linux/Wayland first:** xdg-shell lifecycle, wl_shm presentation, seat/pointer/keyboard, monotonic clock, fractional scale, then text-input-v3 and AT-SPI. Start with shm rather than GPU buffers so the software pixmap remains the reference.
2. **Windows:** Win32 window/message pump and DPI awareness; GDI or DXGI presentation; UI Automation provider; TSF text input. System-library calls stay in the narrow audited platform module and their results are treated as untrusted.
3. **macOS:** NSWindow/NSView host and Retina surface; Core Animation/IOSurface presentation; NSAccessibility and NSTextInputClient. System-library calls stay in the narrow audited module.
4. **Cross-platform acceptance:** same Shroud behaviour and pixel goldens; explicit per-platform pixel conversion; event/focus/capture tests; DPI transition tests; accessibility action/name/value tests with real assistive technology.

Do not add native backends until the Capstan capability-I/O and T6 system-call prerequisites exist. A C shim may be used only as a narrowly audited OS ABI boundary if the language cannot yet express a required system call; it must not contain layout, widget, rendering, event-policy or accessibility semantics.

## 12. Acceptance checklist

An S1 backend is not ready until it demonstrates:

- [ ] Native lifecycle is explicit, idempotent and recoverable after partial failure.
- [ ] Physical client size and DPI scale are updated atomically and tested across fractional-DPI transitions.
- [ ] Event coordinates are converted to FX correctly at every scale and monitor origin.
- [ ] Guard timing uses a host monotonic clock; future-dated input cannot satisfy the delay.
- [ ] Pointer capture delivers release/cancel outside the client area without false activation.
- [ ] Key repeat, text commit, focus loss and window deactivation have deterministic tests.
- [ ] Frame buffers obey copy/lease lifetime and premultiplied ARGB semantics.
- [ ] Surface loss and resize cannot present stale frames or dispatch stale queued events.
- [ ] Native accessibility names/values use sanitised text; password values remain hidden.
- [ ] Accessibility actions re-enter Shroud's checked event path.
- [ ] Native resources are released on normal close and every injected failure path.
- [ ] Real-platform smoke tests and supported screen-reader tests are recorded per OS.
