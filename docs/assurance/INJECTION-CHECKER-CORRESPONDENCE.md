# Injection provenance: current checker correspondence

**Status:** model of a restricted checker fragment; source correspondence is reviewed, not mechanised.
**Source baseline:** `main` at `943e6bad014888bd64117f1417752375008796f2` (2026-11-26).
**Source file:** `compiler/checker.cap`; the exact laundering-analysis section is pinned in `verification/lean/fixtures/injection_checker_laundering_source.cap`.
**Lean module:** `verification/lean/CapstanVerification/InjectionChecker.lean`.

## 1. Purpose and claim boundary

The end-to-end theorem and compositional proof obligations are specified in [INJECTION-FREEDOM-PROOF.md](INJECTION-FREEDOM-PROOF.md). This document records only the current source-checker fragment and its refinement gap.

This document connects the current implementation's narrow byte-reconstruction laundering analysis to a mechanised abstract model. It does not claim that the production checker is a sound general-purpose taint analysis, nor that the entire Capstan language is injection-free.

The Lean module proves algebraic properties of the model's transfer functions. It also proves that several known unsupported expression forms evaluate to un-derived in that model. Those latter theorems are deliberate gap witnesses, not desired language semantics.

The source-to-model correspondence is currently a human-reviewed mapping between `checker.cap` and `InjectionChecker.lean`. Lean does not parse `checker.cap`, execute its AST visitor, or prove that the compiled checker implements these definitions. The implementation-refinement theorem remains open.

## 2. Current checker algorithm

The relevant implementation is the `FlowSummary` / `Flow` / `derived` / `base_marked` / `flow_walk` / `flow_body` / `summarise` / `check_laundering` region of `compiler/checker.cap`.

| Implementation operation | Current behaviour | Lean representation |
|---|---|---|
| `N_METHOD .at()` on `TY_TAINT` | A byte read is derived | `FlowExpr.inputByte` |
| `N_VAR` | Derived if the variable name is in `Flow.vars` | `FlowExpr.local`; `FlowMarks` |
| Unary `-`, `~` | Propagate operand derivation | `neg`, `bitNot` |
| `N_GETF` | Inherit the mark of the root variable/aggregate | `field`, `checkerBaseMarked` |
| `N_INDEX` | Derived if the base root is marked or the selector is derived | `index` |
| Map `.get(key)` | Derived if base is marked or key is derived | `mapGet` |
| `int_to_str` | Propagate derived integer | `intToStr` |
| String `+` | Propagate either derived operand | `stringConcat` |
| `.pop()`, `.get()`, `.remove_at()` | Propagate marked base | `collectionRead` / `mapGet` |
| Integer arithmetic | Propagate either derived operand | `arithmetic` |
| Wrapping arithmetic | Propagate any inspected argument | `wrapping` (two-operand fragment) |
| Direct optional unwrap `if (let ...)` | Mark bound local if condition is derived | `checkerOptionalBranch` |
| `char_str(derived)` | Report CWE-20 | Sink diagnostic in `flow_walk` (not yet formalised as a sink theorem) |
| Function calls | Use return and parameter-to-return/sink summary facts | `call`, `checkerSummaryReturn`, `checkerSummarySink`; integer-only parameter seed predicate |

The implementation marks only `int` and `string` locals in its ordinary declaration/assignment transfer. Marks are monotone: reassignment does not clear an earlier variable-name mark. The Lean model proves both facts. This is conservative but can produce false positives and is not value-sensitive storage semantics.

Interprocedural summaries currently contain only `returns_derived`, `param_to_return`, and `param_to_sink`. The Lean fragment now models their call-site propagation and the integer-only parameter seed rule. There is no summary component for heap writes, parameter paths, validation facts, or context certificates. Summary solving is bounded and fails closed if it does not converge within the configured rounds. The intraprocedural analysis likewise refuses to compile if its fixpoint budget is exhausted.

## 3. Mechanised properties

The Lean module proves:

- Derived source bytes are recognised.
- Unary/arithmetic/string-concatenation transfers preserve derivation for the represented cases.
- Derived selectors and marked aggregate roots propagate through the represented index/field/map-read cases.
- `int_to_str` preserves derivation.
- The current local-mark update is monotone and marks derived int/string writes.
- Boolean locals are not marked by the ordinary write transfer.
- Reassignment with a literal does not clear a prior mark.
- Direct optional-unwrapping conditions can mark the bound local.
- Parameter-to-return and parameter-to-sink summary dependencies propagate to derived actual arguments; only integer parameter seeds are admitted by the current summary model.

These are model-level transfer lemmas. The transfer-agreement theorem is conditional on the expression belonging to `SupportedFlowExpr`; the excluded cases are not covered. They are not a proof that the source checker code has the same behaviour, and they are not a concrete execution theorem.

## 4. Mechanised gap witnesses

The model explicitly includes expression constructors that the current `derived` implementation does not propagate. The following Lean theorems prove a pair: the reference dependency semantics returns `true`, while the current checker abstraction returns `false`:

| Gap | Lean witness | Existing conformance finding |
|---|---|---|
| Comparison/Boolean result | `comparison_result_not_derived` | TYPE-08 / TYPE-09 |
| Generic text conversion | `to_text_result_not_derived` | TYPE-05 |
| Collection-consuming join | `join_result_not_derived` | TYPE-06 |
| Length/shape | `length_result_not_derived` | TYPE-07 / TYPE-15 |
| Map membership | `map_has_result_not_derived` | TYPE-12 |
| Map key set | `map_keys_gap` | TYPE-10 |
| Map removal | `map_remove_gap` | TYPE-12 |
| Stored optional payload | `optional_payload_not_derived` | TYPE-13 |
| Enum payload | `enum_payload_not_derived` | TYPE-17 |
| Struct constructor field | `struct_constructor_not_derived` | TYPE-14 |

Additional source-level gaps remain outside this fragment: aliases and heap identity, interprocedural aggregate parameters and heap writes, non-integer parameter summaries, map key/value/shape separation, receiver paths, policy parameter summaries, policy purity/effects, and a formal sink contract for `char_str` and other output contexts. See `PROVENANCE-CONFORMANCE.md` and `PROVENANCE-SEMANTICS.md`.

## 5. What is needed to prove the implementation

1. **Freeze the source interface.** Define a stable checker transfer interface in Capstan source, with explicit transfer cases and a versioned semantic identifier. Avoid maintaining a second informal list of cases.
2. **Executable reference semantics.** Make the Lean transfer relation executable over a serialisable expression/flow-state representation. Define the same representation at the checker boundary, or a lossless translation into it.
3. **Translation validation.** For every AST constructor and builtin, prove or independently check that the checker-side transfer result refines the Lean transfer result. Unsupported constructs must map to an explicit conservative top/reject state, never silently to `false`.
4. **Flow-state correspondence.** Relate the concrete `Flow.vars` and `FlowSummary` structures to the formal state. Prove every `flow_walk` update preserves the relation.
5. **Fixed-point correspondence.** Prove monotonicity and termination for the formal summary/intraprocedural worklists, and show the implementation either reaches the same least fixed point or rejects before diagnostics are treated as complete.
6. **Sink theorem.** Formalise every laundering sink and prove that a concrete prohibited dependency implies the checker reports/rejects it.
7. **Full-language coverage.** Extend beyond the current restricted analysis to value provenance for all scalar types, aggregate paths, aliases, interprocedural heap effects, validators, context encoders and all protected sinks.

Until those obligations are complete, the claim is limited to the model fragment and the source cases listed above. The source checker remains part of the trusted computing base.

## 6. Next implementation increment

The highest-value next change is the scalar value-provenance stage: track provenance for Boolean results and locals, comparisons, generic text conversions, joins and length/shape observations; add positive and negative regressions; and replace name-only monotone marks with per-value abstract facts so reassignment can be modelled precisely. Heap aliases and interprocedural aggregate effects remain a separate subsequent stage.



## 6. Fail-closed source identity gate

`verification/lean/check_injection_checker_source.py` compares the complete laundering-analysis
section of `compiler/checker.cap` byte-for-byte with the reviewed fixture and checks that the expected checker transfer,
sink, fixpoint and Lean model declarations are present. Run it from the
repository checkout:

```sh
python3 verification/lean/check_injection_checker_source.py
```

The gate intentionally fails on any edit to the pinned laundering-analysis section. Unrelated checker changes do not invalidate this model. The
reviewer must inspect any changed transfer and flow-walk logic, update the
Lean model and correspondence record, and only then refresh the source fixture.
This prevents accidental drift between the implementation under review and
the model baseline.

**Proof boundary:** this is mechanically checked section identity plus
declaration-presence validation. It does not parse Capstan ASTs, compare
individual AST transfer results, or prove semantic refinement. In particular,
a matching section fixture is evidence that the analysed transfer region has not changed;
it is not evidence that the Lean definitions correctly implement that source.
The next bridge must replace the section fixture with parser-produced
AST/flow certificates and a Lean-checked translation relation.
