# Shroud public API: low-friction application experience

**Status:** reviewed design proposal for issue #88, based on the current `lib/shroud/view.cap`, `ui.cap`, `layout.cap`, `a11y.cap` and `examples/shroud/gallery.cap`. This is an API direction and migration plan, not a claim that the proposed typed API is implemented.

## Decision in brief

Keep Shroud declarative and application-state-driven. Preserve the current value-tree and explicit `update(Model, Msg)` architecture; do not add widget callbacks, hidden global state, or a second persistent widget-object tree. When Capstan generics are available, make the message type a parameter of the view tree (`View<M>`) and make every interactive constructor accept an `M`, not a string. Keep effects explicit and owned by the application loop.

The first fifteen minutes should be: create a window/surface, write a small model and view function, render, dispatch input messages through one update function, and save or present the resulting frame. The current headless PNG path already supports a reproducible first run; platform-window startup remains a separate S1 deliverable.

## 1. Current API audit

### What is already coherent

- `View` is a value description, rebuilt from application state; `row()`, `column()`, `stack()`, modifiers and `add()` provide a small compositional vocabulary.
- `Ui` owns per-window transient state (focus, hover, pressed state, scroll offsets and carets). The application owns durable model state and the event/update loop.
- `Ui.handle(Event)` returns messages; widgets do not invoke application callbacks.
- `View.key()` gives explicit identity for stateful nodes. Duplicate identities are detected and reported.
- Layout is constraint-driven and single-pass. Text and view-tree admission have per-frame limits.
- Accessibility roles, names, values, states and bounds are exported separately; keyboard navigation and diagnostics are part of the library rather than optional application callbacks.
- `examples/shroud/gallery.cap` is a runnable, scripted example of text input, password input, toggles, radio selection, a slider, destructive-action guarding, PNG output and accessibility JSON.

### Friction and semantic gaps

1. **Stringly-typed actions.** `View.action` and `Msg.action` are strings. Misspellings and incompatible payload use are discovered at runtime. A single `Msg` has both `value` and `Tainted text`, so a handler must know which field is meaningful for each action.
2. **No typed component boundary.** A helper can return `View`, but it cannot express the message type it emits. Reusable components therefore rely on agreed string names and payload conventions.
3. **Input payloads are weakly discriminated.** Text edits, button activation, slider changes and selection values share one record shape. The application must validate the action and payload relationship.
4. **Effects are application-defined but undocumented as a lifecycle.** The current core has no async/effect runtime, which is good for determinism, but examples do not yet establish a standard way to request work, cancel stale work or deliver completion messages.
5. **Identity semantics need a public contract.** Keys currently drive retained scroll/caret/guard state. The API should state that keys are stable within a logical sibling scope, unique among siblings, and preserved only when the semantic control identity is preserved. Duplicate-key repair is diagnostic containment, not a supported state model.
6. **Accessibility inspection is export-oriented.** The JSON tree and checks are useful, but there is no first-class explanation of why a node received its bounds, constraints, focus order or clipped status.
7. **Platform lifecycle is not yet the first-run experience.** The current example is headless and scripted. Native windows, IME composition, clipboard, accessibility bridges and platform event pumps remain embedder work; the public API must not imply they already exist.
8. **Text and layout breadth remain staged.** The current Latin-oriented text implementation does not yet provide shaping, full bidi, grapheme-aware editing or IME composition. International text must be a core acceptance track, not a modifier added after widgets.

## 2. Message API alternatives

### A. Generic message parameter — recommended

Illustrative future API, contingent on Capstan generics:

```java
enum AccountMsg { NameChanged(Tainted), Create, Cancel, Delete }

View<AccountMsg> account_view(Account model) {
    return column()
        .add(text_field(model.name, AccountMsg.NameChanged))
        .add(button("Create", AccountMsg.Create));
}
```

- **Advantages:** compile-time checking from each control to the application's message enum; no string dispatch; reusable components can be generic over their parent message type; preserves the existing explicit update loop.
- **Costs:** requires generics and a principled way to construct enum variants / payload values; type inference and variance rules must be designed. It does not require closures.
- **Assessment:** strongest fit with Capstan's type-system roadmap and Shroud's deterministic model.

### B. Typed action tokens without generic views

Illustrative shape:

```java
Action<Tainted> name_changed = action<Tainted>(...);
Action<Unit> create = action<Unit>(...);
View view = column()
    .add(text_field(model.name, name_changed))
    .add(button("Create", create));
```

- **Advantages:** narrower language feature than generic `View<M>`; action payload types can be checked at construction.
- **Costs:** action tokens need a safe application-owned registry or dispatch layer; tokens can become an implicit callback system; reusable components still need a way to map local actions into parent actions.
- **Assessment:** viable fallback if generic view values prove too expensive, but risks introducing a second event abstraction and lifecycle.

### C. Callback/closure handlers

Illustrative shape:

```java
button("Create", () => create_account(model));
```

- **Advantages:** locally readable and familiar; simple demonstrations can be concise.
- **Costs:** captures application state, complicates ownership/lifetimes, makes deterministic replay and testing harder, and encourages widgets to call application code. It is a poor match for a pure value tree and should not be the default.
- **Assessment:** reject as the core interaction model. A future adapter may offer callbacks at an application boundary only if ownership and scheduling are explicit.

## 3. Component composition alternatives

1. **Plain functions returning `View<M>` (recommended).** A component is a pure function of explicit inputs and returns a subtree. It can map its local event type into the parent's `M` using a typed mapping function. This is simple, testable and needs no privileged framework internals.
2. **Public component protocol.** A component exposes `view(model)`, `update(model,msg)` and optional `inspect(model)`. This supports encapsulated local state, but risks creating a second component runtime, nested update routing and hidden state ownership. Defer unless function composition proves insufficient.
3. **Trait/interface-based renderers.** Components implement a common render interface. This could support dynamic plugin-like composition, but needs trait objects, object-safety and lifecycle rules not yet established in Capstan. Do not make this a prerequisite for ordinary custom widgets.

Recommendation: start with plain functions, explicit model slices and typed message mapping. Add a protocol only after real applications demonstrate a concrete limitation.

## 4. State, identity and effects

- **Durable state:** owned by the application model. A view is a snapshot of that state; rebuilding it must not perform I/O or mutate the model.
- **Ephemeral interaction state:** owned by one `Ui` instance: pointer state, keyboard focus, caret, scroll position and guard timing. It is never silently promoted into application state.
- **Identity:** keys preserve only UI-owned state across rebuilds. Keys must be stable for the same logical item and unique within their documented scope. A changed semantic control should receive a new key. Index-derived keys are unsafe for reorderable collections unless item identity is position-based by design.
- **Effects:** update logic may return explicit effect descriptions alongside the next model. The host executes them and sends typed completion/cancellation messages back through the same update function. Effects must have stable IDs, explicit cancellation and stale-result policy. Rendering itself remains pure.
- **Time:** animation and delayed work use an injected monotonic clock / explicit frame tick, never wall-clock reads hidden inside a view function.

## 5. Executable prototype and first-run path

The existing `examples/shroud/gallery.cap` is the executable baseline for the current API. It already demonstrates the critical first-run loop:

1. define a small `Model`;
2. write `view_of(Model) -> View`;
3. create a `Ui` with fonts, theme, surface size and scale;
4. call `ui.render(view_of(model), monotonic_time)`;
5. pass `Event` values to `ui.handle`, then route returned `Msg` values through `update`;
6. write a PNG and inspect `a11y_json` / `a11y_problems`.

Build from the repository root using the documented command:

```sh
capstanc build -o gallery.c lib/shroud/*.cap examples/shroud/gallery.cap
cc -O2 -Iruntime gallery.c -o gallery
./gallery out-dir
```

The gallery is intentionally an executable current-API prototype, not a pretend implementation of the future typed API. The future API should preserve the same explicit model/view/update flow while replacing string action names with typed message values.

Representative next prototypes required before declaring this design validated:

| Prototype | Current executable baseline | Gap to close |
|---|---|---|
| Form | `gallery.cap` | typed messages, field validation errors, focus/error announcement |
| Navigation | not yet present as a complete example | stable route identity, back/forward semantics and keyboard navigation |
| Data-heavy view | not yet present | virtualisation/windowing and bounded row identity |
| Custom component | helper functions are possible; no documented typed mapping | demonstrate reusable component with parent message mapping and no privileged internals |
| Accessible interaction | gallery and `a11y` checks | inspection of focus order, clipped nodes and computed bounds |

## 6. Diagnostics and inspection

The public diagnostic surface should converge on a structured report, not parseable human strings:

- view identity and duplicate-key location;
- parent constraints, child constraints and chosen size;
- frame before and after clipping / pixel snapping;
- flex allocation and overflow/truncation reason;
- focusability and computed focus order;
- accessibility role, name, value, state and bounds;
- text fallback / unsupported-script status when shaping lands.

Reports should be deterministic and available to tests. A developer-facing inspector can render the same report, but must not be required for correctness or accessibility testing. Avoid exposing mutable internal `Laid` nodes as the long-term public API.

## 7. Responsive layout, accessibility and international text

- Keep layout in device-independent units with explicit scale conversion; add breakpoint/adaptive helpers only after their semantics are defined for finite and unbounded constraints.
- Define minimum target sizes and focus visibility as testable policies. Keep keyboard, pointer, touch and assistive-technology activation on the same semantic message path.
- Make focus order, labels, descriptions, error announcements and state changes observable in the accessibility tree.
- Specify text editing in grapheme-cluster coordinates while retaining source-byte mappings internally. Add Unicode bidi, line breaking, shaping, fallback and IME as separately testable capabilities. Never equate valid UTF-8 decoding with correct international text layout.
- Animation should be frame-tick-driven, bounded and deterministic under a fake clock. Reduced-motion preferences must be exposed by the embedder and testable.

## 8. Compatibility and staged implementation

1. **Now, no compiler changes:** document the current API honestly; improve diagnostics and examples; add a structured layout explanation report and missing navigation/custom-component prototypes.
2. **When generic enums / generics land:** prototype `View<M>` in a separate branch and compile representative form, navigation and custom-component applications. Compare ergonomics and type errors with alternatives A/B/C.
3. **Typed migration:** add typed constructors and typed message mapping alongside current string constructors. Mark string actions deprecated only after all in-repository examples migrate and an external compatibility window is agreed.
4. **Effects:** introduce explicit effect descriptions only with cancellation, stale-result and deterministic test semantics. Do not bind effects to widget lifecycle callbacks.
5. **Diagnostics and platform:** add structured layout/a11y inspection; deliver a real first-run window only when the relevant platform embedder is available. Keep headless execution as the deterministic test oracle.
6. **Validation:** recruit developers unfamiliar with Shroud; measure time to first useful screen, time to add a custom component, invalid-action/type-error discoverability, number of concepts needed, and success on keyboard/screen-reader tasks. Record results before claiming low friction.

## 9. Unresolved questions

- What exact generic-enum and function-value syntax will Capstan expose, and can a generic `View<M>` remain an ordinary value?
- Should typed message mapping be an explicit `map_msg` operation, a constructor argument, or a generic helper?
- What is the smallest public key scope that supports lists and nested reusable components without collisions?
- Should layout diagnostics be a structured value returned by layout, an opt-in trace sink, or both?
- What virtualisation contract can preserve deterministic layout and accessibility order for large collections?
- How should asynchronous effects express cancellation and stale completion without introducing hidden tasks?
- Which platform embedder is the first supported interactive target, and what is the minimum viable IME/accessibility contract?
- How should grapheme-aware caret/selection APIs coexist with current UTF-8 byte-offset storage during migration?

## 10. Evidence boundary

This proposal is based on the current source API and existing gallery. It does not implement typed messages, effects, native windows, virtualised lists, full international text shaping or a visual inspector. It does not claim user validation. Issue #88 should remain open until the required executable prototypes, reviewed compatibility plan and developer validation evidence exist.
