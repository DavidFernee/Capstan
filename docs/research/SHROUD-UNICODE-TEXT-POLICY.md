# Shroud Unicode text integrity policy

**Status:** design baseline for the first Unicode-correctness increment. This document does not claim
Unicode bidi, line-breaking, grapheme-segmentation or shaping conformance.

## 1. Problem statement

Shroud currently decodes UTF-8 into code points and applies is_deceptive() to untrusted text
before painting and accessibility serialization. That policy replaces several classes of code
points with U+FFFD, including characters with ordinary-language and emoji semantics:

- U+200C ZERO WIDTH NON-JOINER and U+200D ZERO WIDTH JOINER;
- U+200B ZERO WIDTH SPACE, U+2060 WORD JOINER and U+00AD SOFT HYPHEN;
- U+E0000..U+E007F tag characters used by emoji tag sequences.

The same transformation is used by the accessibility serializer so the accessibility tree agrees
with the renderer. This prevents some invisible-formatting attacks, but it also destroys logical
text information. JSON escaping is not a substitute for Unicode display policy, and preserving a
code point does not make its input trusted.

The fix must separate **source text**, **ordinary-prose presentation**, and **security-sensitive
identifier presentation**. A single global replacement list cannot satisfy all three.

## 2. Normative invariants

1. **Source preservation.** A valid UTF-8 input is decoded to its original Unicode scalar-value
   sequence. No display policy may mutate the stored Tainted value or the message returned to
   the application.
2. **Trust preservation.** Decoding, normalisation, shaping, escaping and rendering never remove
   Tainted. Only the existing explicit validation/trust operation may change trust.
3. **Context is explicit.** Ordinary prose and security-sensitive identifiers use different
   presentation policies. A caller must not obtain the security-sensitive policy merely by
   passing an ordinary string, nor downgrade a security-sensitive field to prose implicitly.
4. **No partial bidi.** Shroud must not implement a subset of UAX #9 and describe it as conformant.
   Until a complete, version-pinned bidi implementation is available, direction-changing
   formatting controls must not silently reorder text. Unsupported behaviour must be explicit.
5. **Logical accessibility.** Assistive technology receives the logical text value, not a
   reconstructed guess from painted glyphs. Suspicious formatting must be exposed as a separate
   diagnostic/annotation; it must not be silently erased from the accessible value.
6. **Determinism.** The same Unicode version, input, font set and rendering profile produce the
   same logical output, diagnostics, line breaks and pixels on every supported target.
7. **Bounded work.** Every decoding, segmentation, bidi, shaping, fallback and diagnostic pass is
   covered by explicit aggregate budgets and fails closed when a budget is exceeded.


## 2A. Security acceptance gate — prevention, not warning

This section is a release gate for every text-consuming Shroud API. A diagnostic or
annotation is not a security control. If a sink cannot establish that its input is safe
for that sink's semantics, it must reject the operation or use a documented inert
fallback. It must not publish a partially validated result.

1. **No implicit sink conversion.** Raw or `Tainted` text must not flow directly into
   security-sensitive identifiers, URLs/origins, executable names, filesystem paths,
   permission labels, audit records, or command-like values. Each sink requires an
   explicit, typed validation/policy step. Rendering-safe text is not identifier-safe.
2. **Validate before effects.** Validation and resource-budget checks complete before
   text is committed to a widget tree, accessibility tree, clipboard operation, host
   request, log record, or persistent state. On failure, the operation is atomic: no
   partial value or side effect escapes.
3. **Comparison uses canonical policy, not appearance.** Security decisions must use
   the original logical value plus an explicit, version-pinned comparison policy.
   Painted glyphs, normalized display strings, case-folded labels, and security
   annotations are never authoritative identity values. Where the application has
   not selected a comparison policy, reject ambiguous identifiers rather than guess.
4. **Controls cannot steer security decisions.** Bidi formatting controls, invisible
   separators, default-ignorables, confusables and mixed-script signals must be
   classified using pinned Unicode data and sink-specific rules. A visual warning is
   supplementary; security-sensitive use is rejected unless the policy explicitly
   permits the exact class and context. Do not treat every joiner or variation
   selector as malicious: validate its context and preserve its logical value.
5. **No trust laundering.** Decoding, escaping, normalization, annotation, truncation,
   shaping, copying or rendering cannot convert `Tainted` input into trusted input.
   Trust transitions require the existing explicit validation operation and must be
   auditable at the call site.
6. **Fail closed on unknowns.** Unknown Unicode versions, missing property tables,
   unsupported bidi behaviour, exhausted budgets, malformed input where a sink
   requires valid text, or unavailable policy configuration cause rejection. They
   must not silently fall back to permissive rendering or comparison.
7. **Safe observability.** Diagnostics retain source spans and code-point/property
   details but must themselves be escaped and bounded. Logs must not render attacker
   controls as active formatting, and must not disclose protected-field contents.
8. **Complete sink inventory.** Every public and internal text sink must be listed,
   classified, and covered by a negative test proving rejection of disallowed input.
   New sinks require tests and policy review in the same change. A sink without a
   classification is not approved for untrusted input.

The acceptance criterion is not "the UI displays a warning". It is: **no
security-sensitive operation consumes an unvalidated value, and a failed validation
produces no externally observable partial effect.** Conformance vectors must test both
the accepted cases and the rejection/atomicity cases.

These controls reduce the attack surface but do not constitute a proof that every
application built on Shroud is vulnerability-free. Downstream applications remain
responsible for applying the appropriate typed validation at their own trust
boundaries; Shroud must make unsafe implicit flows difficult or impossible through
its API design.

## 2B. Existing fail-closed blocker: byte-limit truncation

PR #329 now removes the silent-prefix behaviour: `string_bytes()` and
`tainted_bytes()` reject values above `MAX_TEXT_BYTES` with the library's
fail-fast exit path (status 101). Frame preflight checks text, value, accessibility
label and hint lengths, and the aggregate frame budget, before code-point decoding or
layout allocation. The helpers retain independent defensive checks for callers
outside layout. Regression coverage includes just below the limit, the exact limit,
and a hostile suffix one byte beyond it, for trusted and Tainted inputs, plus
oversized per-view text, value, label and hint cases.

This is a targeted remediation in PR #329, not yet a validated or merged fix:
required CI and review remain pending. The fail-fast process exit is deliberately
not a successful truncated conversion and no prefix is returned for a security
decision. All callers and externally observable effects still require review before
the Unicode input pipeline can be described as security-complete.

## 3. Text representations

The implementation should keep three representations distinct.

| Representation | Meaning | Mutation permitted? |
|---|---|---|
| Source | Original Tainted UTF-8 bytes supplied by the application/user | No |
| Logical text | Decoded Unicode scalar sequence plus source-byte spans | No semantic deletion or reordering |
| Presentation | Context-specific display runs, glyph clusters, line-break opportunities and diagnostics | Derived only; never written back to source |

Each logical code point needs a half-open source-byte span [start,end). Later grapheme clusters,
shaping clusters and glyph runs retain the union of their source spans. This is required for caret
movement, selection, diagnostics and mapping a visual selection back to the original value.

Malformed UTF-8 remains handled by the existing maximal-subpart decoder and produces U+FFFD in
logical text, with the exact malformed source span retained. This is a decoding decision, not a
security sanitisation decision.

## 4. Presentation contexts

### 4.1 Ordinary prose

Ordinary prose includes paragraphs, labels, hints, user-authored messages and emoji-bearing text.

- Preserve ZWJ, ZWNJ, variation selectors, emoji tag characters, soft hyphen, word joiner and
  zero-width space in the logical sequence.
- Apply Unicode grapheme segmentation (UAX #29) before cursor/selection movement.
- Apply Unicode line breaking (UAX #14) before wrapping. Soft hyphen and word joiner affect line
  opportunities; they are not interchangeable with ordinary spaces.
- Apply a complete, version-pinned Unicode Bidirectional Algorithm (UAX #9) before visual
  placement. Do not approximate it with a hand-maintained list of RTL ranges.
- Apply script shaping and mark positioning through a separately versioned shaping layer. The
  deterministic software renderer remains the reference implementation.
- Keep the original logical sequence for copy, selection, application messages and accessibility.

A renderer that lacks one of these stages must report that limitation in the supported-text
profile. It must not claim full multilingual correctness merely because UTF-8 decoding succeeds.

### 4.2 Security-sensitive identifiers

Security-sensitive contexts include account names, executable names, filenames, package identities,
URLs/origins, permission labels and audit/security logs.

- Preserve the original logical value and its trust label.
- Produce a separate security display that makes invisible, direction-changing, default-ignorable
  or otherwise policy-relevant code points inspectable (for example, a visible U+202E token).
- Report the code point, Unicode property, source-byte span and reason for each annotation.
- Do not silently normalise, delete or reorder the underlying identifier.
- Do not use the prose presentation policy as an implicit downgrade.

The initial implementation must use Unicode property data pinned to a named Unicode release.
Property classification belongs in generated/versioned data, not an incomplete ad hoc range list.
The policy must distinguish at least bidi controls, join controls, variation selectors, tags,
default-ignorable code points, noncharacters, controls and format characters. A property match is
evidence for a review/display decision, not by itself proof of malicious intent.

### 4.3 Accessibility

Accessibility names and values must carry the same logical Unicode sequence as the corresponding
control. The platform bridge may expose additional annotations/description text for suspicious
formatting, but must not substitute a lossy sanitised string for the logical value.

Secure fields remain an explicit exception: their value is not exposed; only the documented
protected-state and length behaviour is available. That exception must not be generalised to
ordinary text fields.

## 5. Algorithm and data-version boundaries

The following standards are separate obligations; passing one does not imply passing the others.

| Area | Normative reference | Required behaviour |
|---|---|---|
| Unicode properties | UAX #44 / versioned UCD data | Reproducible property classification |
| Bidirectional text | UAX #9 | Full paragraph resolution, isolates, embeddings, neutrals and mirroring |
| Line breaking | UAX #14 | Normative break opportunities, including soft hyphen and word joiner |
| Grapheme clusters | UAX #29 | Extended grapheme boundaries for caret/selection |
| Normalisation | UAX #15 | Explicitly selected form only; never silently rewrite source text |
| Script shaping | OpenType plus script-specific shaping rules | GSUB/GPOS, kerning, ligatures, marks and script reordering |

Unicode and shaping data versions must be recorded in the build/test manifest. Upgrading either
version is a reviewed compatibility change with regenerated vectors and documented differences.
HarfBuzz may be used as an independent differential oracle in tests; it is not a runtime dependency
of Shroud core and is not the normative specification.

## 6. Resource and failure model

The existing per-string and per-frame byte limits remain necessary but are not sufficient. Add
independent budgets for:

- decoded scalar values and source-span entries;
- extended grapheme clusters and segmentation work;
- bidi paragraph count, isolate/embedding depth and resolution work;
- line-break candidates and produced lines;
- shaping runs, input scalars per run, glyph count and substitution/positioning work;
- font fallback depth and total fallback attempts;
- diagnostics/annotations retained per frame.

All additions use subtraction-based budget checks before allocation or work. A budget failure must
be deterministic and atomic: no partially updated caret map, accessibility tree or rendered frame is
published. The caller receives a bounded failure/diagnostic; the original source value remains
unchanged.

## 7. Conformance and regression programme

The test programme is staged. Do not mark a stage complete from a few hand-picked examples.

### Stage U0 — source and policy vectors

- Valid and malformed UTF-8, including overlong encodings, surrogate encodings, truncated
  sequences and out-of-range scalar values.
- Persian/Arabic ZWNJ and Indic joiner-sensitive sequences.
- Emoji ZWJ families/professions, variation selectors and subdivision-flag tag sequences.
- Soft hyphen, word joiner and zero-width space.
- Bidi controls, nested isolates, mixed RTL/LTR identifiers and noncharacters.
- For each vector, assert source bytes, logical scalar sequence, source spans, prose policy,
  security annotations and accessibility logical value independently.

### Stage U1 — segmentation and line breaking

- Run the version-matched UAX #29 grapheme-break and UAX #14 line-break conformance data.
- Test cursor movement, deletion, selection and wrapping at every reported boundary.
- Include combining-mark sequences, emoji modifiers, regional-indicator pairs and ZWJ sequences.
- Verify source-span mapping after every cluster/line transformation.

### Stage U2 — bidi

- Run the version-matched UAX #9 conformance data, including explicit formatting, isolates,
  bracket pairing, neutrals, numbers and paragraph boundaries.
- Compare resolved levels and visual order with an independent reference implementation.
- Test security display separately from prose visual order.
- Verify accessibility remains in logical order and exposes diagnostics without changing value.

### Stage U3 — shaping

- Differentially compare glyph IDs, advances, offsets and cluster/source mappings against
  HarfBuzz for pinned fonts and scripts.
- Include GSUB/GPOS, kerning, ligatures, combining marks, Arabic joining, Indic reordering and
  fallback boundaries.
- Treat any intentional difference as a documented profile limitation, not a passing equivalence.

### Stage U4 — adversarial budgets

- Maximal combining-mark runs, long isolate nesting, newline-dense text, huge fallback chains,
  substitution expansion and malformed-font interactions.
- Assert bounded work, bounded retained memory, deterministic rejection and no partial frame
  publication.

## 8. Migration plan

1. Introduce source-span-preserving decode output without changing the public Tainted boundary.
2. Split the current untrusted_codepoints() responsibility into explicitly named policy functions;
   retain the old function only as a compatibility wrapper until all call sites are migrated.
3. Make prose, identifier/security and accessibility consumers choose a context explicitly.
4. Add pinned U0 vectors and assert that source/logical/accessibility values are not mutated.
5. Integrate complete UAX #29 and UAX #14 data/algorithms, then UAX #9, each behind independent
   conformance gates.
6. Add shaping only after the cluster/source mapping and deterministic glyph-run contracts are fixed.
7. Remove the compatibility wrapper only after all Shroud and downstream callers are migrated.

## 9. Current status and non-claims

The current S0 implementation provides bounded UTF-8 decoding and a conservative visible-character
transformation for untrusted text. It does **not** provide full UAX #9 bidi resolution, UAX #14 line
breaking, UAX #29 grapheme segmentation, or general OpenType shaping. The current global
sanitisation policy can replace semantically meaningful joiners and line-breaking characters.
Accessibility currently follows the sanitised visible representation, not a separate logical-value
plus security-annotation model.

This document defines a migration target and test programme. It is not evidence that any of those
algorithms or conformance suites have been implemented or passed.
