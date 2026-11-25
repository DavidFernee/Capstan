# Anchor: editor and language services

**Status:** proposed design specification; not implemented
**Parent:** docs/ANCHOR.md

## Goals

Provide professional source editing without a second Capstan parser or semantic engine. Compiler/LSP remain authoritative for syntax and semantic diagnostics. Editor presentation state is derived and version-bound.

## Document identity and versions

A document is identified by workspace ID, stable file identity where available, canonical workspace-relative path and open-instance generation. URI strings alone are insufficient identity.

Each mutation increments a monotonically increasing in-memory version. Requests and responses carry that version. A response for version N MUST NOT replace state for N+1. Closing/reopening creates a new generation so late responses cannot attach to a new instance.

Track original disk bytes, decoded text/encoding, current text, last saved identity, external disk identity and compiler diagnostic version.

## Text and encoding

Specify Unicode scalar and line-ending models, cursor/selection indexing, malformed UTF-8 handling and byte-offset conversion. Compiler ranges and editor positions use an explicit negotiated encoding; implicit UTF-16/UTF-8 assumptions are forbidden.

Malformed input is reported and preserved where feasible. Lossy replacement is an explicit conversion, never a silent save side effect. Mixed line endings and final-newline state are preserved unless normalized by user choice.

## Editing transactions

An edit contains document identity, expected version, non-overlapping ranges, replacement text and origin. It applies only when the expected version matches. Conflicts are rejected or handled by a specified rebase algorithm, never silently applied to shifted offsets.

Undo/redo is transaction-based. Formatter output is previewable and applies only to the intended version. External changes and source transformations have explicit transaction boundaries.

## Save and external changes

Save via same-directory temporary file and atomic replacement where supported. Recheck target identity and external modification immediately before replacement. Symlink substitution, path escape and target-type changes fail closed.

If disk content changed, present a three-way comparison (base, buffer, disk). Never silently overwrite either side. Recovery state is bounded, workspace-scoped and excludes secrets/protected buffers.

## LSP adapter

Implement only the currently documented subset: initialize/shutdown/exit, didOpen/didChange/didClose and publishDiagnostics. Do not claim completion, hover, definition, references, rename, semantic tokens, code actions, formatting requests or workspace symbols until compiler server support is specified and implemented.

Bound JSON-RPC frame bytes, nesting, collections, pending requests and queue depth. Handle partial reads, multiple messages per read, malformed JSON, invalid IDs, oversized frames and truncated streams. Stdout is protocol-only; stderr is separately bounded.

Use one supervised LSP child per workspace initially, subject to the approved process API. Restart uses capped backoff and a circuit breaker. Cancellation and shutdown have deadlines; late messages are discarded by process generation and document version.

## Diagnostics

Preserve URI, document version, source, severity, code, range, message and codeDescription URL. Keep compiler diagnostics distinct from Anchor operational errors and external assurance findings.

Escape hostile diagnostic text. Mark stale/unmappable ranges rather than guessing. CWE links are references, not proof of vulnerability or absence. Zero diagnostics means only that the named compiler accepted the submitted source under recorded options.

## Syntax presentation

Do not market regex highlighting as compiler-accurate. A future token API specifies token kinds, offsets, encoding, incomplete-source behaviour, incremental invalidation, version association and stability. Until then, plain text and diagnostics are the honest baseline. Best-effort lexical decoration, if offered, cannot drive refactoring or security decisions.

## Navigation and refactoring

Definition, references, rename and completion require compiler-owned symbol identity and ranges. Rename is a workspace transaction with preview, file-identity revalidation, conflict detection and rollback on partial failure; text matches alone are insufficient.

Refactorings require compiler-provided edits or a source transformation API preserving comments, formatting and unrelated expressions. If safety cannot be established, refuse and explain.

## Accessibility and input

A professional editor requires multiline text, selection, clipboard, IME composition, candidate-window geometry, bidi handling, screen-reader text navigation and large-document virtualisation. Shroud S0 does not provide these. Do not simulate full IME/accessibility support with committed-text events or single-line fields. These require a Shroud-owned versioned contract and cross-platform conformance tests.

## Resource limits

Set hard ceilings for open documents, bytes/document, aggregate dirty buffers, diagnostics/document, LSP frame size, outstanding requests, output bytes and restart frequency. Exhaustion is explicit and recoverable.

## Acceptance criteria

Out-of-order diagnostics cannot overwrite newer state; fuzzed framing cannot crash/deadlock Anchor; save detects symlink/path races and external modification; encoding round trips have property tests; stale edits are rejected; unsupported LSP features are not exposed; editor accessibility is tested against the actual host contract.
