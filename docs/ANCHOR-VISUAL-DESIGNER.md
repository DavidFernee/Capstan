# Anchor: source-authoritative visual designer

**Status:** proposed design specification; not implemented
**Parent:** docs/ANCHOR.md

## Objective

Make sophisticated Shroud interfaces easier to construct visually while keeping Capstan source the sole authoritative representation. The designer is an Anchor mode, not a separate visual application or competing project format.

## Invariants

- Visual state is a derived projection of source.
- Visual edits are source-aware transformations, never serialization of an unrelated scene graph.
- Unknown or dynamic code is preserved and marked unsupported.
- The designer does not execute untrusted project code merely to draw the canvas.
- Dynamic preview, if introduced, is isolated, capability-limited and resource-bounded.
- Visual correctness is not proof of runtime, accessibility or security correctness.

## Declarative subset

The initial designer supports only compiler-recognised declarative Shroud construction: known constructors, stable component identity, safely representable properties, layout modifiers, theme tokens and accessibility metadata.

Arbitrary expressions, dynamic control flow, unknown custom components, side-effecting closures and runtime-dependent values remain opaque. The designer must preserve them and explain why they cannot be edited. The grammar requires a compiler-owned syntax contract; this document does not invent one.

## Interaction model

- Searchable, versioned component palette.
- Source-backed hierarchy with safe reorder/nesting only where transformations support it.
- Deterministic canvas with selection overlays that do not alter hit testing.
- Typed property inspector for layout, typography, colour, state and accessibility.
- Named viewport and theme previews.
- Accessibility inspector showing the exact Shroud checker and its limits.
- Bidirectional selection/source navigation using version-bound mappings.

## Source mapping

Each visual node maps to document identity/version, stable syntax identity where available, source range and encoding, resolved Shroud API identity, and supported transformation set. Mappings are invalidated on document edits. Stale mappings cannot be used to modify source.

## Transformation protocol

A request identifies document/version, target syntax node, operation, typed parameters and preconditions. The compiler/source service validates the target and returns minimal non-overlapping edits, preservation guarantees and validation status.

Anchor previews the diff and applies it as one editor transaction. Failed preconditions reject the operation atomically. No lossy fallback is permitted. Reordering must preserve evaluation order and side-effect semantics; otherwise it is disabled.

## Layout semantics

Expose actual Shroud semantics: intrinsic size, constraints, flex distribution, alignment, spacing, clipping and overflow. Drag handles are editing affordances, not a promise that arbitrary pixel placement maps to declarative layout. Do not invent CSS-like properties absent from Shroud.

## Preview isolation

Static preview may render only structures safely interpretable without project execution. Dynamic preview requires a separate process, explicit capabilities, read-only project access by default, network/filesystem denial unless granted, CPU/memory/output/time limits, deterministic inputs and kill semantics. Preview output is untrusted and crashes cannot corrupt editor state.

## Catalogue and accessibility

Palette entries bind to exact Shroud/API versions and immutable package digests where applicable. Assurance is displayed per dimension and scope. The designer may report Shroud accessibility diagnostics but must not claim WCAG or native assistive-technology conformance from a headless tree check alone.

## Acceptance criteria

Round-trip projection preserves all source outside intended edit ranges; unknown expressions survive; mappings are version-safe; failed edits are atomic; golden tests cover themes/viewports; preview cannot access undeclared capabilities; accessibility claims name their checker and scope.
