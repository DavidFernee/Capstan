# Capstan Injection-Freedom Proof Programme

**Status:** initial Lean provenance fragment added; no source-checker, sink, compiler, or runtime theorem claimed.
**Implementation branch:** `security/injection-freedom-foundation`
**Formal toolchain:** Lean 4.19.0, inherited from `verification/lean/lean-toolchain`.

## 1. Security claim

The intended top-level claim is:

> For every well-formed Capstan program accepted under the strict injection-free profile, and every attacker-controlled input, execution cannot cause attacker-controlled bytes to be interpreted as syntax or authority at a protected sink.

This is a conditional compiler-and-runtime security theorem, not merely a claim that values have a Tainted label. It will be established only after the source checker, provenance analysis, validators/encoders, sink adapters, lowering, and execution semantics are connected by proved refinement obligations.

The theorem is deliberately not stated as whole-trace noninterference. Legitimate programs may branch on input and choose among source-authored operations. The property constrains injection-relevant interpretation at protected sinks, not every observable control-flow event.

## 2. Formal property

Let P be a source program accepted by the strict profile, I arbitrary attacker-controlled input, Exec(P,I) its execution, Sinks(Exec(P,I)) the protected sink events, and Auth(P) the syntax and authority explicitly authorised by the source program and declared capabilities.

```
StrictAccepted(P) ->
  forall I, forall e in Sinks(Exec(P, I)),
    SinkSafe(P, I, e)
```

SinkSafe is defined per sink, not by a single generic escaping predicate:

| Sink | Required invariant |
|---|---|
| SQL | Query syntax is a source-authored fixed query structure; attacker input occupies bound value parameters. Identifier positions require a separately validated identifier capability. |
| Process execution | Executable identity and argument-vector boundaries are fixed by source/capability policy; input can occupy only permitted data argument positions. No shell or interpreter re-parsing is permitted by the strict profile. |
| HTML | Values are encoded for the exact HTML parsing context; text, attributes, URL, script and style contexts are not conflated. |
| Logs/terminal | Untrusted bytes cannot create control records, terminal control sequences, or forged log structure under the documented log encoding. |
| CSV | Formula-leading fields are handled under a documented client-specific policy; no universal spreadsheet guarantee is implied. |
| Filesystem | Untrusted paths are validated against the selected root/capability policy; canonicalisation alone is not treated as authority. |
| Generated code | Source-derived bytes cannot alter generated-language token structure; literals, identifiers and numeric tokens use their respective encoders/validators. |

The theorem assumes the sink adapter implements its stated contract. A model theorem about a SQL or process sink does not prove a real database driver or process launcher.

## 3. Provenance model

The first Lean module is `verification/lean/CapstanVerification/InjectionProvenance.lean`. It defines a finite source-identity domain, separate direct-data and selection provenance sets, conservative union for expression composition, selection transfer that preserves the selected value's provenance and records the selector's provenance, a small expression grammar and abstract evaluator, and preservation lemmas including `expression_sources_preserved`.

The key design distinction is selection dependence. Reading a trusted literal from a table using an attacker-controlled index is not independent of that index. The result may be a literal, but the selection event remains attacker-influenced.

The module is imported into `CapstanVerification.lean` and its theorem dependencies are listed in `AxiomAudit.lean`.

**Scope of this first theorem:** it proves a property of the small formal expression grammar only. It does not yet model Capstan's parser, checker, assignments, heap, aliases, aggregate operations, function calls, validators, output sinks, or generated code. It is not evidence that the current compiler enforces the model.

## 4. Required semantic layers

1. **Source semantics.** Define the typed source language fragment and evaluation order, including all builtins that can create, transform, select, or emit data.
2. **Provenance transfer.** Prove assignment, conversion, arithmetic, Boolean results, optionals, enums, list/map/struct operations, alias effects, and interprocedural summaries preserve all represented dependencies. Unknown operations widen or reject.
3. **Checker soundness.** Prove that every accepted source expression/program satisfies the formal provenance and sink typing judgements. The implementation checker must refine this formal checker.
4. **Validation and encoding.** Prove each validator establishes its precise predicate and each encoder establishes only its named context guarantee. Neither is a generic declassification.
5. **Sink separation.** Prove that well-typed sink calls meet the sink-specific invariant. SQL values and SQL identifiers are distinct; process executable, argv positions and shell interpretation are distinct; HTML subcontexts are distinct.
6. **Lowering preservation.** Prove source-to-CCAM lowering preserves values, provenance, sink events, order, traps and effects.
7. **Validator/evaluator correspondence.** Prove decoded and validated CCAM is the same object the evaluator executes, and that the concrete evaluator refines the formal semantics.
8. **Backend/runtime boundary.** Prove native code generation and runtime adapters preserve the sink semantics, or explicitly stop the claim at the last proved boundary.

The top-level theorem is the composition of these obligations. A missing edge means the claim cannot be promoted beyond that edge.

## 5. Trust and declassification policy

The strict profile rejects `trust()` and any equivalent operation that discards provenance. It permits only predicate-specific validation and context-specific encoding with proved contracts.

A separate audited profile may permit explicit declassification. Its theorem is conditional on every declassification site's justification and review. That profile must not be called strictly injection-free without qualification.

Pure control dependence is outside the initial explicit-provenance theorem. A stricter information-flow profile may track control dependence, termination and resource effects, but those are separate guarantees. The present theorem also excludes business-logic correctness, authorisation correctness, confidentiality/noninterference, timing and availability.

## 6. Current Capstan boundary

The repository already has a substantial provenance design document at `docs/assurance/PROVENANCE-SEMANTICS.md`. It specifies data and selection dependencies, heap/alias behaviour, interprocedural summaries, validation facts, context-safety facts, conservative unknowns and fail-closed analysis budgets. That document is design intent, not proof of the production checker.

The production compiler currently uses the C-backed path. The C-free CCAM/Lean work is a separate restricted path. The injection theorem must not be reported as proving either path until their checker, lowering, sink and runtime correspondences are demonstrated.

Where an operation is only a demonstration sink or no real adapter exists, the theorem covers only the formal interface contract—not external execution.

## 7. Proof and release gates

Every claimed theorem must have an exact source commit and clean-checkout build command; pinned Lean and independent checker versions; explicit `#print axioms` output and audited dependencies; assumptions and trusted computing base; a mapping to normative language and sink specifications; implementation-refinement status; and adversarial counterexample tests for the same semantic obligation.

No `sorry`, `admit`, custom axiom, or unreviewed theorem assumption is permitted. Tests are complementary evidence, not substitutes for proofs.

The initial Lean module must pass the existing `lake build CapstanVerification --wfail` and pinned checker/axiom-audit workflow on the exact branch head before its theorem is counted as machine-checked.

## 8. Next proof increments

1. Prove environment assignment/reassignment and expression evaluation preserve provenance.
2. Add typed sink contexts and a formal sink judgement; prove untrusted values cannot flow directly to a protected sink.
3. Add predicate-specific validator and context encoder contracts, with soundness obligations kept explicit.
4. Model map/list selection, key/value provenance, alias-aware heap updates and function summaries.
5. Connect the actual Capstan checker transfer functions and diagnostics to the formal judgement.
6. Add the strict-profile adversarial suite, including byte reconstruction, untrusted lookup into trusted tables, branch/aggregate/helper laundering, cross-context encoding and trust rejection.
7. Extend through CCAM lowering and evaluator refinement.
