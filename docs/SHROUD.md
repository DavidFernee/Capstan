# Shroud: a GUI library written in Capstan

On a ship, the shrouds are the rigging that holds the mast up. Shroud is Capstan's library for
graphical user interfaces: one codebase for Windows, macOS and Linux (and later iOS, Android and
the web). It is written entirely in Capstan, so every guarantee the language gives applies to the
whole interface stack, including font parsing, text, layout, drawing and input.

The aim is to equal or better WinUI 3, SwiftUI, Qt and Flutter. Section 7 compares Shroud with
each of them honestly, including where it is still behind. Section 8 is the plan to close those
gaps.

## 1. The model

An interface is a value, rebuilt from the application's state whenever that state changes, as in
SwiftUI, Flutter and Elm. Views are made with functions and refined with chained modifiers:

```java
View view_of(Model m) {
    return column().spacing(12).padding(24)
        .add(text("Create an account").font_size(24).bold())
        .add(text_field("name", m.name, "Display name").label("Display name"))
        .add(row().spacing(8)
            .add(spacer())
            .add(button("Delete account", "delete").danger())
            .add(button("Create", "create").accent()));
}
```

Widgets never call back into application code. An interaction produces a **message**: an action
name, plus an int or untrusted text. The application's `update` decides what each message means:

```java
void update(Model m, Msg msg) {
    if (msg.action == "name") { m.name = msg.text; }           // Tainted: what the user typed
    if (msg.action == "create") {
        if (let ok = validate_ident(m.name)) { ... }           // the only way to trust it
    }
}
```

The application owns the loop. Each turn it renders a view, hands the pixels to the platform, and
feeds the platform's input events back:

```java
Ui ui = new_ui(font, bold, light_theme(), 800, 600, 256);   // 256 = 100% scale
ui.render(view_of(model), now_ms);
List<Msg> msgs = ui.handle(event);
```

Capstan has no generics until v0.5 and no closures until v0.5, so for now actions are strings.
When generics arrive, `View<M>` will carry the application's own message enum, and the compiler
will check every action (section 8, S5).

## 2. Why Shroud draws every pixel itself

There are two ways to build a cross-platform toolkit. One wraps each platform's native controls,
as wxWidgets, SWT and early Xamarin did. The other draws everything itself and asks the platform
only for a window, input and a place to put pixels, as Flutter, Qt Quick and every game engine
do. Shroud takes the second approach, for three reasons:

1. **Identical behaviour everywhere.** The same layout, the same text breaking and the same
   pixels on every operating system. Rendering uses only integer arithmetic (Capstan has no
   floating point, and Shroud does not need it), so a frame renders to the same bytes on any
   processor and compiler. The test suite checks this with golden SHA-256 hashes of whole frames,
   on Linux with GCC and Clang and on macOS.
2. **The dangerous code stays in Capstan.** The parts of a GUI that handle untrusted data are font
   parsing, text decoding, image decoding and layout of untrusted text. In C and C++ toolkits
   these parts have a long record of exploited memory-corruption bugs: FreeType CVE-2020-15999
   (exploited in the wild through Chrome), Windows ATMFD CVE-2015-2426, Apple's font parser
   CVE-2015-1155, and the ImageIO and Skia image-decoder chains behind several zero-click
   attacks. In Shroud all of this is Capstan code, where those bugs become safe stops, or, as the
   font parser is built, are refused before they happen.
3. **Small platform layers.** Each operating system needs only an *embedder* that opens a window,
   presents a pixmap, delivers input events and publishes the accessibility tree. That is a few
   hundred lines per platform rather than a toolkit's worth of wrappers.

## 3. Architecture

```
   application: Model ── view_of() ──► View tree           update(Model, Msg)
                                          │                       ▲
   Shroud (Capstan)                   layout (flex, constraints)  │ messages
                                          │                       │
                       ┌──────────── Laid tree ────────────┐      │
                       ▼                                   ▼      │
                 paint: theme, widgets            accessibility tree, checks
                       │                                   │      │
                 rasteriser ◄── glyph masks ◄── TrueType   │   input: hit testing,
                       │                       parser      │   focus, keyboard, guards
                       ▼                                   │      ▲
                 Pixmap (premultiplied RGBA)                │      │
   ────────────────────┼───────────────────────────────────┼──────┼──── platform embedder
                       ▼                                   ▼      │
          Windows: DXGI swap chain     UI Automation      Win32 messages, TSF
          macOS:   CALayer / IOSurface NSAccessibility    NSEvent, NSTextInputClient
          Linux:   Wayland wl_shm      AT-SPI (D-Bus)     Wayland seat, text-input-v3
          today:   PNG files           JSON               scripted events (tests, examples)
```

## 4. What exists now (S0)

| File | What it does |
|---|---|
| `lib/shroud/geom.cap` | Fixed-point geometry: 1/256-pixel coordinates (`FX`), rectangles, insets, Flutter-style constraints, integer square root |
| `lib/shroud/color.cap` | 32-bit ARGB colours, premultiplied compositing with exact integer rounding, WCAG 2.2 relative luminance and contrast ratios |
| `lib/shroud/path.cap` | Vector paths (lines, quadratic and cubic Béziers), rounded rectangles, ellipses, rings, and flattening with a bounded number of segments |
| `lib/shroud/raster.cap` | Anti-aliased scanline rasteriser (16 sub-scanlines, exact horizontal coverage), nonzero and even-odd rules, solid and linear-gradient paints, rectangular clip stack, and a fast exact path for axis-aligned rectangles |
| `lib/shroud/png.cap` | PNG encoder (CRC-32, Adler-32, stored DEFLATE) for screenshots and golden tests |
| `lib/shroud/ttf.cap` | TrueType parser: `cmap` formats 4 and 12, `hmtx`, simple and composite `glyf` outlines with transforms, and a glyph cache. Every read is bounds-checked by a reader that fails softly, so damaged fonts are refused, never trusted |
| `lib/shroud/text.cap` | Strict UTF-8 decoding (maximal-subpart replacement, as Unicode specifies), safe display of untrusted text, measuring, glyph drawing at quarter-pixel positions, and line wrapping |
| `lib/shroud/view.cap` | Views and modifiers: text, user text, button (standard, accent, subtle, danger), row, column, stack, spacer, checkbox, radio, switch, text field, password field, slider, progress bar, divider, box, scroll view |
| `lib/shroud/theme.cap` | Light and dark themes in current desktop style, each checked against WCAG 2.2 contrast |
| `lib/shroud/layout.cap` | One-pass constraint layout: flex rows and columns with grow factors, alignment, space-between, stacks, vertical scroll views, size limits, padding, high-DPI scaling, and pixel snapping |
| `lib/shroud/paint.cap` | Draws every widget in every state (hover, pressed, focused, disabled, checked), focus rings after keyboard use, and scroll bars |
| `lib/shroud/ui.cap` | The window: rendering, hit testing against the frame the user saw, pointer and wheel input, keyboard navigation (Tab and Shift+Tab, Enter, Space, arrows, Home, End, Page Up and Page Down), text editing on UTF-8 boundaries, and activation guards |
| `lib/shroud/a11y.cap` | The accessibility tree (roles, names, values, states, bounds) as JSON, and accessibility checks |
| `lib/shroud/fonts/` | DejaVu Sans and DejaVu Sans Bold, subset to Latin (about 16 KB each), under the Bitstream Vera licence |

`examples/shroud/gallery.cap` shows every control in a small form, driven by a script of input
events. It writes each frame as a PNG, in both themes, plus the accessibility tree.

## 5. Security: what Shroud does that other toolkits do not

| Threat | Shroud |
|---|---|
| Untrusted input used as trusted data (CWE-20) | Every text field yields `Tainted`. The compiler makes the application validate it (`validate_ident`, `validate_int`, ...) before it can become trusted text, a file name or a query. No other toolkit types user input. |
| Deceptive text (CWE-451; Trojan Source, CVE-2021-42574) | `user_text()` and text fields show bidirectional overrides and isolates, zero-width characters, controls, BOMs and tag characters as a visible mark, so `invoice‮fdp.exe` cannot pass for `invoiceexe.pdf`. The program's own text keeps them. |
| Clickjacking and tap-jacking (CWE-1021) | A `guarded()` control, and every `danger()` button, has a 500 ms activation delay after it appears, moves, reappears, or changes its action or visible identity. The delay is measured only against the monotonic clock advanced by `render()`; an input event's timestamp cannot advance or satisfy it. The platform adapter must therefore supply a monotonic render clock from the trusted window system. Input is matched against the last rendered frame. This mitigates some deceptive repositioning/reappearance patterns and future-dated event attempts; it is not a complete defence against arbitrary overlays or synthetic events. The headless library cannot authenticate event provenance, prove that pixels were displayed, or establish that a human saw the control. |
| Password exposure (CWE-200, CWE-549) | `password_field()` draws dots and never lays out the text. The accessibility tree reports only its length, and the role `password` lets screen readers and remote-access tools treat it as protected. |
| Memory corruption in font parsing (CWE-125, CWE-787) | The TrueType parser is Capstan. Every read goes through a reader that returns 0 and marks the font bad when a read falls outside the file. Table offsets, glyph locations, end points, flags and composite records are all validated. Damaged fonts are refused or drawn partly, never a stop. Fuzzed on every test run, also under ASan+UBSan. |
| Resource exhaustion (CWE-400, CWE-674, CWE-789) | Limits on font size (32 MiB), points per glyph, composite depth and parts, curve segments, glyph size (four ems), cached glyphs, pixmap size, views per interface, nesting depth, and text-field length. |
| Smuggled line breaks | Text typed or pasted into a one-line field loses its control characters, so a paste cannot add a newline to a value written to a log or header. |
| Inconsistent rendering hiding content | Deterministic integer rendering: what a test sees is exactly what a user sees, on every platform. |

Planned (section 8): `SecureField` producing `Secret` values, screen-capture protection for
windows that show secrets, taint-aware clipboard (pasted text is `Tainted`, copying from password
fields is impossible), protective markings (PSPF classification banners) as a built-in widget,
and isolation of each platform embedder's vendor libraries (DESIGN-MAP v0.10).

## 6. Accessibility is checked, not optional

Toolkits that draw their own widgets must describe them to assistive technology themselves.
Flutter showed that this can be done well, and that it is easy to leave out. In Shroud:

- **Every frame has an accessibility tree** with roles, names, values, states and bounds. The
  embedders translate it into UI Automation (Windows), NSAccessibility (macOS) and AT-SPI
  (Linux). Plain layout containers are flattened, as screen readers expect.
- **Everything works from the keyboard.** Tab and Shift+Tab move through controls in reading
  order and skip disabled ones. Enter and Space activate. Arrow keys and Home, End, Page Up and
  Page Down adjust sliders. The focus ring appears after keyboard use and disappears after
  pointer use, as on every desktop platform.
- **Problems are reported.** `a11y_problems()` lists controls with no accessible name, targets
  smaller than 24 dp (WCAG 2.5.8), and any text drawn below 4.5:1 contrast (WCAG 1.4.3, measured
  against the actual background while painting). `theme_problems()` checks every colour pair a
  theme uses, including control boundaries and focus indicators at 3:1 (WCAG 1.4.11). The tests
  require both built-in themes to pass, and a project can make an empty report a release
  condition.

## 7. How Shroud compares

| | WinUI 3 | SwiftUI | Qt 6 | Flutter | Shroud today |
|---|---|---|---|---|---|
| Platforms | Windows | Apple only | Windows, macOS, Linux, mobile, embedded | Windows, macOS, Linux, iOS, Android, web | Headless (PNG). Windows, macOS and Linux embedders are next (S1) |
| Language memory safety | C# app; C++ framework | Swift app; Objective-C, C++ framework | C++ | Dart app; C++ engine (Skia/Impeller) | Capstan throughout, including fonts and rasterising |
| Untrusted input typed | No | No | No | No | Yes (`Tainted`) |
| Deceptive-text defence | No | No | No | No | Yes |
| Clickjacking guard | No | No | No | No | Yes |
| Declarative UI | XAML (markup) | Yes | QML | Yes | Yes |
| Deterministic, pixel-identical rendering on every platform | No | No | No | Close (Skia), not guaranteed | Yes, tested |
| Accessibility checks built in | Accessibility Insights (separate tool) | Xcode audits | No | Partial (guideline tests) | Yes, in the library and its tests |
| GPU rendering | Yes | Yes | Yes | Yes | Not yet (S3) |
| Complex scripts, bidi, shaping, IME | Yes | Yes | Yes | Yes | Not yet (S2); Latin text and UTF-8 today |
| Widget breadth | Very wide | Wide | Very wide | Very wide | 16 widgets (S4 to widen) |
| Animation | Yes | Yes | Yes | Yes | Not yet (S3) |
| Visual designer, hot reload | Yes | Previews | Qt Design Studio | Hot reload | Not yet (S6) |

Honestly stated: today Shroud is a strong foundation, not yet a replacement. Its correctness and
security are ahead of all four. Its reach (platforms, scripts, widgets, GPU, tools) is behind.
The roadmap closes that gap without giving up the first.

## 8. Roadmap

Each stage keeps the suite green, adds its own differential tests and fuzzing, and ships usable
on its own.

### S0: Foundations (done in this change)
Rasteriser, TrueType, text, layout, sixteen widgets, input, focus, accessibility tree and checks,
themes, headless driver, golden-frame tests.

### S1: Platform embedders (needs v0.6 capability I/O and the T6 system-call layer)

The normative host/adapter boundary, event and clock trust rules, frame lifetime, DPI contract,
accessibility bridge requirements and platform acceptance checklist are specified in
[SHROUD-HOST.md](SHROUD-HOST.md). This is a design contract, not an implemented host API.
- **Linux, Wayland first.** The Wayland protocol is a documented wire format over a Unix socket,
  so the client can be written entirely in Capstan: `wl_shm` buffers, `xdg-shell` windows,
  `wl_seat` input, `fractional-scale`, `text-input-v3`, clipboard. X11 follows the same way
  (XCB wire protocol). AT-SPI is D-Bus, also a wire protocol.
- **Windows.** Win32 window and message loop, presentation through a DXGI swap chain (or GDI),
  UI Automation provider, Text Services Framework for input methods, per-monitor DPI. As the
  DESIGN-MAP notes, Windows programs must reach the kernel through system libraries. Their
  results are treated as untrusted, and the calls are confined to one small, audited module
  (later an isolated process, v0.10).
- **macOS.** NSWindow and NSView with a CALayer backed by an IOSurface, NSAccessibility,
  NSTextInputClient, Retina scaling. The same rule applies to Apple's system libraries.
- Damage tracking, so each frame redraws only what changed; vsync-paced frames; multiple
  windows; drag and drop; file dialogs through the platform's portal or picker, with `Tainted`
  paths.

### S2: World-class text
- OpenType shaping in Capstan (GSUB, GPOS, kerning, ligatures, marks): a HarfBuzz equivalent,
  differentially tested against HarfBuzz on large corpora.
- Unicode bidirectional algorithm (UAX #9), line breaking (UAX #14), grapheme clusters (UAX #29),
  tested with Unicode's own conformance files.
- CFF and CFF2 outlines (.otf), variable fonts, colour emoji (COLR v1), font fallback, and system
  fonts on each platform (`Tainted` files, so the hardened parser matters more).
- Input methods (composition, candidate windows) for Chinese, Japanese, Korean and Indic scripts.
- Multi-line text editing, selection, undo, and a rich-text editor.

### S3: Rendering and motion
- A GPU backend (Vulkan, Metal, Direct3D 12, or WebGPU) behind the same scene interface, with
  the software rasteriser kept as the reference that GPU output is compared against.
- Image decoders in Capstan (PNG, JPEG, WebP, AVIF), each fuzzed and differentially tested. These
  are among the most attacked components on every platform.
- SVG icons, shadows and blur, transforms, clips with rounded corners, opacity layers.
- Animation: implicit animations and springs, at 120 Hz, using integer time.

### S4: Widget breadth
Virtualised lists and grids, data tables with sorting and editing, tree views, tabs, menus and
menu bars, context menus, dialogs, popovers and tooltips, combo boxes, date and time pickers,
navigation views, toolbars, split views, charts, and the platform-adaptive styles users expect
on each operating system (Fluent on Windows, Apple's look on macOS).

### S5: Typed messages and application structure (with v0.5 and v0.7)
`View<M>` with the application's own message enum, checked exhaustively by `match`; closures for
modifiers; async effects (network, files) as messages through tasks and channels (v0.7); state
restoration; navigation and routing; undo and redo.

### S6: Tooling (with IDE Phase B)
Live preview in the Capstan IDE, a view inspector with the accessibility tree and contrast
overlay, golden-image review tools, hot reload, and a visual designer that writes ordinary
Capstan.

### S7: Assurance and government use
- Conformance with WCAG 2.2 AA, EN 301 549 and Section 508, checked with real screen readers
  (Narrator, NVDA, JAWS, VoiceOver, Orca).
- Internationalisation and localisation: plural rules, number and date formats, right-to-left
  layout mirroring.
- For government and defence (DESIGN-MAP section 9): protective-marking banners (PSPF) as a
  built-in widget, windows that refuse screen capture when they show secrets, a `SecureField`
  that yields `Secret`, session-lock integration, and an audit log of security-relevant UI
  actions.

### S8: Mobile and web
iOS and Android embedders (touch, gestures, safe areas, platform accessibility), and the web
through the WebAssembly backend (T10) drawing to a canvas, with a DOM accessibility mirror.

## 9. Testing

`tests/shroud/check.py` runs in every suite run (`tests/run.sh`, section "shroud"), with warnings
as errors and again under AddressSanitizer and UndefinedBehaviorSanitizer:

- **behaviour**: 78 assertions on layout, buttons, guards, keyboard and focus, text editing,
  untrusted text, accessibility, themes, scrolling, compositing and high-DPI scaling
  (`tests/shroud/behaviour.cap`);
- **rasteriser**: 200 random polygons compared pixel by pixel with their exact area coverage,
  computed independently by polygon clipping (worst error 8/255, mean 0.03/255);
- **fonts**: glyph index, advance and outline bounds of every character in both fonts compared
  with fontTools (recorded in `tests/shroud/fonts.expected`, and recomputed when fontTools is
  installed);
- **UTF-8**: 3,000 random and edge-case byte strings decoded as Python decodes them;
- **PNG**: chunks, CRCs and every pixel checked with zlib;
- **font fuzzing**: 300 damaged fonts (random bytes, truncation, hostile table offsets, damaged
  glyphs, cmap, loca and headers, self-referencing composites). Each must be refused or drawn
  without a stop;
- **golden frames**: the gallery's six frames and two accessibility trees must have the
  recorded SHA-256 hashes, on every platform and compiler.

## 10. Known limitations of S0

- No platform embedder yet: interfaces render to PNG and are driven by scripted events.
- Latin text only in practice: no shaping, kerning, bidi or input-method composition. Other
  scripts display only if the font has the glyphs, without shaping.
- One font family, bundled. TrueType outlines only; no hinting.
- Rectangular clips only; no images, shadows, transforms or animation.
- Identity across rebuilds is by position unless a view is given a `key()`. Give keys to
  controls in lists that change.
- Function and type names share Capstan's single namespace until v0.5 brings module
  visibility, so a program using Shroud cannot also define its own `Rect`, `View` or `text()`.
