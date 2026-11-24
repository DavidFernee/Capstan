# Shroud Unicode text correctness and spoof-resistant presentation

Status: design proposal for issue #95. This document is not a claim that the
algorithms described here are implemented.

## 1. Decision

Shroud must preserve the logical Unicode text supplied by an application while
producing a correct, deterministic visual representation. Security policy must
not silently corrupt ordinary prose, scripts or emoji.

The current blanket replacement of selected invisible code points is a useful
initial defence against a narrow class of spoofing, but it is not a viable
international text policy. In particular, U+200C/U+200D, U+200B, U+00AD,
U+2060 and emoji tag characters have legitimate language, line-breaking or
emoji semantics. A single `is_deceptive()` predicate cannot decide how all
these characters should be processed in every UI context.

Adopt a two-representation model:

- **Logical text** is the exact decoded Unicode scalar sequence supplied by the
  application or user. It remains the source of truth and retains its
  `Tainted` provenance where applicable.
- **Display runs** are the result of segmentation, paragraph direction,
  bidi resolution, line breaking, shaping, font fallback and raster placement.
  They retain source ranges back to logical text.
- **Security annotations** describe suspicious controls or confusable patterns
  without silently mutating the logical value. A context-specific presentation
  policy decides whether an annotation is rendered as a visible marker,
  warning, or ordinary formatting behaviour.

The mapping from display clusters and glyphs back to source code-point and
UTF-8 byte ranges is mandatory. Selection, caret movement, hit testing,
accessibility, copy/paste and diagnostics must all use the same mapping.

## 2. Text pipeline

The intended pipeline is:

```
UTF-8 bytes
  -> strict decoder (source byte spans, replacement for malformed sequences)
  -> logical Unicode scalar sequence (Tainted provenance preserved)
  -> paragraph segmentation and script/language itemisation
  -> grapheme and line-break opportunities
  -> bidi paragraph resolution
  -> font fallback and OpenType shaping
  -> line layout and visual-order runs
  -> glyph rasterisation
  -> pixels + source mapping + accessibility representation
```

The stages have distinct responsibilities. Do not merge spoof detection into
UTF-8 decoding or mutate the logical text in order to simplify rendering.

### 2.1 Decoding and source mapping

- Keep strict UTF-8 validation and the existing maximal-subpart replacement
  behaviour for malformed sequences.
- Every decoded scalar records its original byte start/end. Replacement
  scalars record the malformed byte span they represent.
- Enforce byte and scalar-count budgets before large allocations.
- Do not perform implicit NFC/NFKC normalisation on user text. Normalisation
  changes identity and can be inappropriate for passwords, source text,
  filenames and user-authored content. Any normalisation belongs to a
  separately named, domain-specific validation operation.
- Keep the original logical value available to application code as
  `Tainted`; shaping or display does not validate it.

### 2.2 Grapheme segmentation and editing

Implement UAX #29 extended grapheme cluster boundaries before defining
user-perceived cursor movement or deletion.

- Left/right movement, backspace, delete, selection and truncation operate on
  grapheme boundaries, not UTF-8 bytes or arbitrary scalar boundaries.
- A cluster can contain combining marks, variation selectors, emoji modifiers,
  regional-indicator pairs and joiner sequences.
- Preserve source byte ranges through cluster construction.
- Resource limits apply to pathological cluster length and segmentation work;
  limit behaviour must be explicit and non-corrupting.

### 2.3 Line breaking

Implement UAX #14 line-break opportunities. Shaping and line layout must account
for the chosen break opportunities, language tailoring and available width.

- U+200B ZERO WIDTH SPACE, U+00AD SOFT HYPHEN and U+2060 WORD JOINER must retain
  their defined line-breaking semantics in ordinary text.
- Soft hyphen is normally invisible when no break occurs and may produce a
  visible hyphen when a break is taken.
- Line breaking must not split an extended grapheme cluster.
- The initial release may document a limited set of language tailorings, but
  must not claim full UAX #14 conformance until the official test suite passes.

### 2.4 Bidirectional layout

Implement UAX #9 paragraph resolution and visual ordering. Bidi controls are
formatting instructions, not ordinary visible glyphs.

- Resolve bidi per paragraph and preserve logical storage order.
- Support explicit embeddings, overrides, isolates, weak/neutral resolution,
  paired brackets and reordering according to the selected Unicode version.
- Enforce explicit embedding/isolate depth and paragraph-size budgets.
- Do not replace all bidi controls with U+FFFD in ordinary prose. Doing so
  breaks legitimate right-to-left text and mixed-direction content.
- Security-sensitive views may annotate or visibly expose direction-changing
  controls, but must not implement an ad-hoc visual order that differs from the
  actual UAX #9 result.
- Provide a deliberate, accessible diagnostic mode that shows control names
  and source positions. Avoid ambiguous replacement glyphs that can themselves
  be confused with user text.

### 2.5 Shaping and fallback

Implement a Capstan-native OpenType shaping pipeline with deterministic integer
metrics and bounded work.

Required initial coverage:
- script and language itemisation;
- GSUB substitutions, including required features, ligatures and contextual
  substitutions;
- GPOS positioning, mark attachment, cursive attachment and pair positioning;
- legacy kern table support where required;
- variation selectors and emoji presentation selection;
- fallback across an ordered font set without splitting grapheme clusters.

HarfBuzz is an independent differential oracle in tests, not a runtime
dependency of Shroud. Compare glyph IDs, cluster/source ranges, advances,
offsets and line-break results for pinned fonts and language/script corpora.
Where raster output legitimately differs, compare shaping output separately
from rasterisation.

CFF/CFF2, variable fonts and colour-font tables need their own bounded parsers
and fuzzing programmes. Do not add them by accepting arbitrary table data in
the TrueType parser.

## 3. Context-sensitive security presentation

Security is a property of the use context, not a blanket property of a code
point. Provide explicit presentation profiles rather than one universal
sanitiser.

### 3.1 Ordinary prose and conversation

- Preserve valid Unicode semantics, including joiners, variation selectors,
  emoji tag sequences and line-break controls.
- Apply UAX #9 for correct visual ordering.
- Detect and annotate suspicious overrides or controls when appropriate, but
  do not silently rewrite the stored message.
- The UI must make logical text inspectable when a user needs to investigate
  a suspicious sequence.

### 3.2 Security-sensitive identifiers

Examples include account names, executable names, filenames, package names,
hostnames, policy identifiers and security labels.

- Preserve the exact logical value.
- Offer a security presentation that exposes bidi controls and other
  contextually suspicious format characters with unambiguous labelled
  annotations and source positions.
- Use Unicode security mechanisms (including confusable skeleton analysis
  where the domain requires it) as advisory or validation signals; do not
  mistake visual similarity for string equality.
- Do not strip joiners or normalise identifiers implicitly. Define
  domain-specific canonicalisation and comparison rules at the validation
  boundary.
- For filenames and executable names, show enough logical-order information
  to prevent a bidi override from disguising the suffix.

### 3.3 Accessibility

Accessibility output must not be a second, inconsistent sanitisation path.

- Preserve the logical accessible name/value where that is the correct semantic
  content, while exposing security annotations through a deliberate mechanism.
- Keep the visual and accessibility representations consistent about the
  actual order and content.
- Password fields must never expose secret values through annotations,
  diagnostics, inspector output or accessibility metadata.
- Test JSON serialization, native bridge output and screen-reader behaviour
  independently. A JSON tree alone does not prove accessible behaviour.

## 4. Determinism and resource safety

All stages that process user-controlled text need explicit budgets:

| Resource | Required bound |
|---|---|
| Input bytes and decoded scalars | Per-value limits before allocation |
| Grapheme cluster length | Maximum scalars/bytes per cluster |
| Paragraph and line count | Per-layout limits |
| Bidi nesting | Explicit embedding/isolate depth limit |
| Shaping | Bounded lookups, substitutions, recursion and output glyph count |
| Font fallback | Bounded font count and fallback attempts per cluster |
| Glyph masks and cache | Per-mask, per-font and aggregate budgets |
| Source mapping | Bounded entries, with no unbounded per-glyph duplication |

Budget exhaustion must produce a deterministic, documented fallback or a
reported layout failure. It must not silently drop arbitrary text, loop
without bound, or leave accessibility and visual output disagreeing.

The software renderer remains the reference backend. Fixed-point geometry and
deterministic rounding must be specified for shaping metrics and glyph
placement. If a future GPU renderer differs, compare it against this reference
with declared tolerances.

## 5. Conformance and differential testing

Pin the Unicode data version used by the implementation and record it in the
repository. A Unicode upgrade is a reviewed compatibility change.

Required test layers:

1. **Decoder:** retain the existing Python differential UTF-8 tests and add
   source byte-span assertions for malformed maximal subparts.
2. **Grapheme:** run the official UAX #29 GraphemeBreakTest data.
3. **Line breaking:** run the official UAX #14 LineBreakTest data, including
   soft hyphen, word joiner and zero-width space cases.
4. **Bidi:** run the official UAX #9 BidiTest and BidiCharacterTest data,
   including isolates, paired brackets, controls and mixed scripts.
5. **Shaping:** differential tests against a pinned HarfBuzz build and pinned
   font corpus, covering Arabic, Persian, Hebrew, Devanagari, Bengali, Thai,
   Latin combining marks, ligatures, emoji and fallback.
6. **Editing:** property tests that caret/selection/delete operations never
   split a grapheme cluster and always map to valid source byte boundaries.
7. **Security presentation:** golden cases for deceptive filenames, mixed
   direction identifiers, joiner-dependent words, emoji ZWJ sequences and
   accessibility output.
8. **Fuzzing:** malformed UTF-8, Unicode scalar sequences, font tables, shaping
   lookups and combinations of large text with adversarial fonts. Run under
   sanitizers and the Capstan strict build.
9. **Determinism:** repeated shaping/layout on different supported compilers
   produces identical logical cluster maps and integer metrics.

Test corpora and font fixtures must carry their upstream licence and version.
The test runner should report conformance categories separately; a partial
subset must not be reported as full Unicode conformance.

## 6. API consequences

The public API should make the distinction between content and presentation
explicit without burdening ordinary application code.

- Ordinary `text()`, `user_text()` and text fields preserve logical content.
- Security-sensitive widgets or modifiers request an explicit identifier
  presentation policy.
- Applications can inspect logical values, but cannot obtain trusted values
  merely by rendering or shaping them.
- Text layout returns source mappings suitable for selection, caret placement,
  hit testing, accessibility and diagnostics.
- The platform host supplies committed text and IME composition events through
  a typed, bounded contract; it does not implement shaping or mutate source
  values.

Exact API names are deliberately deferred until the text pipeline and Capstan's
type-system constraints are agreed. Do not add a parallel persistent widget
tree to support text layout.

## 7. Implementation sequence

1. **Policy and source mapping:** define logical text, source spans and
   security presentation profiles; retain Tainted provenance.
2. **Unicode segmentation:** grapheme clusters and line-break opportunities,
   with official conformance fixtures.
3. **Bidi:** complete UAX #9 implementation and test suite before exposing
   mixed-direction production support.
4. **Shaping:** OpenType GSUB/GPOS and differential tests against HarfBuzz.
5. **Fallback and fonts:** bounded fallback, CFF/CFF2, variable and colour fonts.
6. **Editing and IME:** grapheme-aware editing, composition, selection, undo
   and multi-line text.
7. **Accessibility and host integration:** verify logical/visual parity with
   real screen readers and platform IME bridges.

Do not claim S2 complete until the conformance suites, differential corpus,
fuzzing and resource-budget gates pass on the supported build matrix.

## 8. Non-goals

- Do not use HarfBuzz, ICU or platform text APIs as hidden runtime dependencies
  of the cross-platform Shroud core.
- Do not normalise or strip user text as a side effect of rendering.
- Do not claim that a replacement glyph makes a string safe for every context.
- Do not claim Unicode conformance from a hand-selected example corpus.
- Do not treat successful pixel rendering as proof of correct caret movement,
  selection, copy/paste or accessibility.


## 9. Mandatory Unicode data and security edge-case contract

The Unicode data manifest is a release and conformance prerequisite, not optional
implementation bookkeeping. Before any Unicode algorithm is declared conformant,
the repository must contain a machine-readable manifest recording:

- the exact Unicode version (including any separately versioned UAX/UTS data);
- each upstream data file's canonical source, version, retrieval revision or
  immutable digest, and licence;
- the algorithm/test-suite version to which each file applies;
- any local tailoring, exclusions or generated derivatives, with reproducible
  generation instructions and their own digest.

The implementation, test runner and release metadata must identify the same
manifest revision. A data-version mismatch is a conformance failure. Upgrading
Unicode data requires an explicit compatibility review and rerunning the
relevant official suites; silently following the host's Unicode database is
prohibited.

For malformed UTF-8, each maximal-subpart replacement scalar must retain the
complete half-open source byte interval `[start,end)` consumed by that
replacement. Adjacent malformed subparts must remain distinct where the
decoder's maximal-subpart algorithm distinguishes them. A mapping may not
invent a one-byte source span for a multi-byte malformed subpart, collapse
separate malformed spans, or point into the middle of a valid scalar. Tests
must assert byte-for-byte reconstruction of the original input from the
ordered source spans, including invalid leading bytes, truncated sequences,
stray continuation bytes and invalid continuation boundaries.

Budget exhaustion is a presentation failure, never a text transformation.
The logical scalar sequence, original UTF-8 bytes and Tainted provenance remain
unchanged. Each stage must choose one documented deterministic outcome:
(a) return an explicit bounded layout error while retaining the logical value,
or (b) use a specified safe fallback representation that preserves the full
logical/source mapping and clearly reports that shaping or layout is degraded.
It must not truncate, normalise, drop controls, reorder by an ad-hoc algorithm,
or silently omit source spans. If the fallback itself cannot satisfy the
resource budget, it must return the explicit layout error.

Password and other secret-bearing values are excluded from security annotation
generation by default, not merely hidden at the final rendering layer. No
secret value, substring, scalar, byte span, control name derived from the
secret, confusable skeleton, source mapping, or annotation may be copied into
diagnostics, logs, inspectors, debug views, telemetry or accessibility output.
Password widgets expose only policy-approved non-content metadata (for example,
length buckets if explicitly approved); the default is no value-derived
metadata. This exclusion applies to intermediate caches and error paths as
well as successful rendering.
