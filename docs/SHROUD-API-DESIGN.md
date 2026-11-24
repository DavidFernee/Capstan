# Shroud public API: developer-experience design RFC

**Status:** design proposal; not a normative API specification  
**Scope:** public programming model, ergonomics, diagnostics and migration  
**Related:** issue #88; production-readiness programme in `SHROUD-PRODUCTION-READINESS.md`

## 1. Product test

Shroud should be a reason to choose Capstan, not merely a library available after choosing Capstan. A developer coming from another language should be able to build a polished, interactive screen quickly, understand the model without framework folklore, and scale to a complex application without abandoning the toolkit.

The test is not whether Shroud resembles SwiftUI, Flutter, Qt or React. The test is whether its own model is easier to learn, reason about, debug and extend.

Every public API proposal should answer:

1. What common task becomes simpler?
2. What new concept must the developer learn?
3. Can the behaviour be explained precisely?
4. Can it be tested deterministically?
5. Can an application override or extend it without forking Shroud?
6. What happens when input, resources, platform services or user data are hostile or unavailable?

## 2. Current API: strengths and friction

The current model has several good foundations:

- Views are values rebuilt from application state.
- Widgets emit messages rather than calling application callbacks.
- Application state and update logic remain outside the widget implementation.
- Composition uses ordinary functions and chained modifiers.
- Layout and interaction are separate from the platform embedder.
- Accessibility metadata and stable view keys are represented in the model.

The current gallery demonstrates the model clearly. A form is assembled from `column()`, `row()`, `text_field()`, `button()` and modifiers; an application-owned `update(Model, Msg)` handles emitted messages.

There are also visible limitations that should not become permanent design decisions:

### 2.1 Stringly typed actions

Today, widgets carry string action names and `Msg` carries a loosely structured payload. This is a pragmatic bridge while Capstan's type system matures, but it permits misspellings, accidental action collisions and payload mismatches that should be compile-time errors.

**Direction:** make the application message type part of the view's type once the language can express it cleanly. Do not add a parallel callback system merely to avoid strings.

### 2.2 Mutable construction and hidden aliasing questions

The current builder methods mutate and return a `View`. That is concise, but the API must specify whether a view can be reused, whether adding a child aliases shared state, and whether modifiers mutate only the receiver or can affect another reference.

**Direction:** retain concise fluent construction only if value semantics and ownership are unambiguous. Prefer immutable builders or compiler-enforced ownership where that materially improves reasoning. Do not assume immutable syntax is automatically simpler.

### 2.3 Manual application loop

The explicit `Ui` loop is excellent for deterministic testing and embedding, but it currently asks every application to coordinate render, platform events, messages, timing and redraws.

**Direction:** keep the low-level driver as a stable foundation and add a small optional application runner when native hosts exist. The runner must not obscure lifecycle, scheduling, errors or event ordering.

### 2.4 Identity and state lifecycle

Stable keys currently identify nodes across rebuilt trees. The public contract needs to explain state retention, key changes, duplicate keys, conditional removal, focus, text editing and scroll position.

**Direction:** publish a concise identity/lifecycle model with executable examples. Do not introduce persistent widget objects as a shortcut.

### 2.5 Styling and design systems

Per-view modifiers are expressive, but large applications need reusable tokens, component variants, themes and consistent responsive rules.

**Direction:** make design tokens and theme composition first-class, while retaining escape hatches for bespoke drawing and layout.

## 3. Candidate message models

Explore these alternatives with executable prototypes before choosing:

| Model | Benefits | Risks |
|---|---|---|
| Generic `View<M>` and typed `Msg<M>` | Compiler checks message identity and payload; composition can preserve one application message type | Requires sufficiently expressive generics and inference |
| Tagged message union | Explicit, inspectable variants; robust serialization and exhaustive handling | Can become verbose; union ergonomics depend on language support |
| Generated action bindings | Concise call sites and compiler-generated type checks | Tooling complexity; generated semantics can be hard to inspect |

**Provisional preference:** a typed application message model, ideally `View<M>`, with explicit mapping/composition when a child component has its own message type. This is a direction, not a commitment to syntax before Capstan's type-system capabilities are known.

String action names may remain as an explicitly dynamic escape hatch, but should not be the default for new applications once typed messages are available.

## 4. State, events and effects

The toolkit should distinguish three things:

- **State:** application-owned data that determines the view.
- **Messages:** typed descriptions of user intent or platform events.
- **Effects:** requests to perform work outside pure view construction, such as reading a file, starting a task, requesting clipboard access or scheduling a timer.

The core update transition should be explainable as:

`(state, message) -> (new state, effects)`

Effects need explicit ownership, cancellation and failure semantics. They must not run as accidental consequences of rebuilding a view. Asynchronous results should return as messages, with a defined policy for stale results and cancellation.

Do not prescribe a hook-based state API merely because it is fashionable. Evaluate whether explicit state/update functions are clearer in Capstan and whether local component state can be expressed without obscuring ownership.

## 5. Composition and custom components

A developer should be able to create a reusable component using the same public tools as Shroud itself.

The design should cover:

- parameterised components and typed messages;
- composition of child messages into parent messages;
- slots/content parameters without requiring closures before the language supports them;
- reusable behaviour and styling without inheritance;
- custom drawing and hit testing with explicit bounds and resource limits;
- focus, accessibility semantics and keyboard behaviour;
- component-local state only where its lifetime is explicit.

A custom component must not need to modify Shroud internals to participate in layout, accessibility, theming or input.

## 6. Layout and visual design

The common path should be simple: rows, columns, overlays, scrolling, responsive breakpoints, alignment, spacing and flexible sizing should be easy to compose.

The advanced path must remain precise: constraints, intrinsic sizing, clipping, transforms, virtualised collections and custom layout should have documented semantics and bounded work.

Design tokens should cover semantic colour, typography, spacing, shape, elevation and motion. Components should consume semantic tokens rather than hard-coded palette values. Themes must support contrast and accessibility requirements, not only light/dark palettes.

Avoid introducing a large CSS-like cascade unless experiments show that it is easier to understand than explicit composition.

## 7. Diagnostics and inspection as product features

Shroud should explain its decisions. The developer experience should include:

- a view-tree inspector showing identity, properties and state boundaries;
- a layout inspector explaining constraints, measured size, overflow and clipping;
- hit-test and focus-path inspection;
- accessibility-tree inspection and validation;
- warnings for duplicate identities, inaccessible controls, missing labels and suspicious state churn;
- deterministic event replay and frame capture;
- resource-budget and performance diagnostics.

Diagnostics should be structured data that tools can consume, not only log strings. Sensitive text-field contents and secrets must never leak into diagnostics or captures by default.

## 8. The first-fifteen-minutes acceptance exercise

A new developer should be able to complete this sequence from the getting-started guide:

1. Create a project and run it without manually assembling compiler internals.
2. Build a polished screen containing text, layout, a text field, a button and a list.
3. Handle input and update application state.
4. Apply a theme and make the screen adapt to a narrow window.
5. Navigate the screen by keyboard and inspect its accessibility tree.
6. Add one reusable custom component.
7. Understand a deliberately introduced layout error using diagnostics.

Record time, unclear concepts, documentation lookups, errors and workarounds. Repeat with developers unfamiliar with Capstan. Do not claim success from an internal author's walkthrough alone.

## 9. Representative application prototypes

Do not judge the API using only the existing form gallery. Prototype at least:

- **Settings/form application:** validation, focus, keyboard navigation, async save, errors.
- **Data-heavy application:** large scrolling list, selection, filtering, empty/loading/error states.
- **Navigation application:** nested navigation, state restoration, responsive sidebar/small-screen layout.
- **Custom visual component:** drawing, pointer and keyboard interaction, accessibility semantics.
- **International text application:** mixed scripts, bidi, IME composition, fallback fonts and dynamic resizing.

Each prototype should include a concise implementation, test coverage, accessibility inspection and performance measurements.

## 10. Non-goals and guardrails

- Do not chase syntax novelty for its own sake.
- Do not make the high-level runner mandatory; embedding and deterministic tests remain important.
- Do not hide asynchronous work or platform permissions behind view construction.
- Do not let the visual designer become a second source of truth; source remains authoritative.
- Do not promise identical native controls where Shroud intentionally owns rendering. Define where visual consistency is desired and where platform conventions should be respected.
- Do not claim the API is production-ready before external developer evaluation.

## 11. Staged plan

1. **Audit:** document current semantics and identify concrete friction in the gallery and core API.
2. **Prototype:** compare typed message, component composition and effects models using the same representative screens.
3. **Validate:** run the first-fifteen-minutes exercise with developers new to Capstan.
4. **Specify:** publish normative state, identity, event, effect, layout and accessibility contracts.
5. **Implement incrementally:** preserve compatibility where practical; provide migration tooling or clear breaking-change boundaries where not.
6. **Measure continuously:** track onboarding completion, API misuse, diagnostics usefulness, performance and accessibility conformance.

## 12. Decision requested

Review the direction and challenge the provisional preference for typed application messages. The next design revision should be based on actual language capabilities and executable prototypes, not speculative syntax. Until that work is complete, the current API remains the implementation baseline, not a guarantee of the final public contract.
