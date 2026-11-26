# Provenance scalar-transfer implementation slice

**Status:** initial compiler implementation under review in PR #410  
**Scope:** scalar and metadata transfer rules in `compiler/checker.cap`  
**Normative authority:** none; the proposal in `PROVENANCE-SEMANTICS.md` remains the target contract.

## Changes in this slice

The laundering analysis is now a syntax-directed, binding-identity may-analysis with typed field/index/map access-path facts and a fail-closed fact budget. It remains a coarse monotone analysis, not the proposed control-flow-sensitive abstract heap or a complete per-value product domain. This slice closes selected scalar/metadata transfer omissions and reduces unrelated-local and disjoint-field contamination; it does not establish alias or heap soundness.

1. **Boolean expression propagation:** Boolean binary expressions (comparisons and logical connectives) inherit derivation from either operand. Unary logical negation preserves derivation.
2. **Boolean locals:** declarations and simple assignments of derived Boolean values mark the local, so a subsequent read does not discard the fact.
3. **Tainted length:** `Tainted.len()` is treated as derived metadata. The integer result is therefore still derived even though its type is `int`.
4. **Aggregate length:** `.len()` on a list or other receiver whose root has been marked by a derived aggregate write is treated as derived.
5. **Parameter summaries:** summary seeding now includes `bool`, `string` and `Tainted` in addition to `int`. Actual argument substitution remains the existing Boolean `param_to_return` / `param_to_sink` mechanism; this is not yet path-sensitive.
6. **Conversions and joins:** `to_text(x)` preserves derivation from x, and `join(xs, sep)` preserves derivation from a marked input list. Existing `int_to_str` and string-concatenation transfers remain.

The new CWE-atlas regression sends a tainted string through a helper that returns its length, stores that integer, and attempts `char_str` reconstruction. The expected outcome is compile-time rejection. A separate Boolean-to-text/write-file probe remains explicitly classified as a gap in the atlas: this slice propagates the Boolean fact, but does not yet define and enforce a complete sink policy for every output operation.

## Deliberate non-claims

This change does not establish:

- A sound general information-flow analysis or noninterference theorem.
- Control-dependence propagation into branch-selected constants, loop termination or timing.
- A path-sensitive per-value domain, structured source paths, aliases or abstract heap.
- Provenance for all aggregate constructors, enum/optional payloads, map key/value/shape paths, or mutations through helper calls.
- Complete interprocedural summaries for every type, receiver, policy, or external function.
- Correct contracts for every builtin, encoder, validator or output sink.
- Compiler, runtime, generated-code or host safety as a whole.

The first follow-on implementation now uses checker-assigned binding identities and typed field/index/map access-path keys, with dynamic indices widened and a 4096-fact fail-closed budget. The analysis remains monotone and may-based: reassignment can over-retain facts, aliases/escapes are not resolved, and weak/strong update semantics are not formalised. The Boolean and metadata rules are a targeted improvement, not closure of the TYPE finding set.

## Validation required

Before this slice can be treated as integrated:

1. The exact PR head must pass the CWE atlas and the complete compiler test matrix.
2. The new length-helper fixture must be shown to fail for the intended CWE-20 diagnostic, not a syntax or type error.
3. Existing positive tests must show no unintended regressions.
4. The implementation must be compared against the transfer rules in `PROVENANCE-SEMANTICS.md`.
5. An independent review must inspect the summary fixed point and all new transfer cases.

Until those results exist, this document records the intended change and its boundaries; it is not a test report or proof.
