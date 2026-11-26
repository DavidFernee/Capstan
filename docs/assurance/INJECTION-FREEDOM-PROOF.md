# Capstan injection-freedom theorem and proof plan

**Status:** theorem specified; current-checker transfer fragment formalised; implementation refinement open.

## 1. Intended theorem

Let `P` be a Capstan program accepted by a strict injection-free profile, `I` arbitrary attacker-controlled input, and `Trace(P,I)` its execution under the specified source/runtime semantics. Let `ProtectedEvents` select events where bytes are interpreted by a grammar or exercise authority (SQL, process launch, HTML, logs, filesystem paths, generated code, and other declared sinks). The intended theorem is:

```
StrictAccepted(P) ->
  forall I, forall e in ProtectedEvents(Trace(P, I)),
    SinkSafe(e)
```

`SinkSafe` is sink-specific. SQL syntax must be source-authored and values bound as parameters; process executable and argv boundaries must be fixed without shell re-parsing; HTML output must be encoded for its exact parser context; filesystem access must be constrained by path and capability policy; generated code must preserve token structure. No single generic `sanitize` predicate is sufficient.

The theorem does not require the whole execution trace to be independent of input. A program may legitimately branch on input and choose among source-authored operations. The claim is that attacker-controlled data cannot be reinterpreted as syntax or authority at a protected sink.

## 2. Strict and audited profiles

The strict profile rejects generic provenance erasure such as `trust()`. Validators establish only their documented predicates; encoders establish only their exact output context. Both preserve origin provenance. A separate audited profile may allow explicitly justified declassification, but its theorem is conditional on the audited sites and must not be called strictly injection-free.

Control dependence, confidentiality/noninterference, business-logic correctness, authorisation correctness, side channels and availability are separate properties unless explicitly added to the semantics and theorem.

## 3. Proof decomposition

1. **Source typing/checking:** every accepted source program satisfies the formal typing, provenance and sink judgements.
2. **Expression and statement semantics:** concrete evaluation is over-approximated by the abstract provenance state for every expression, assignment, branch, loop and exceptional path.
3. **Heap and aliases:** abstract locations and weak/strong updates cover every possible alias and aggregate mutation.
4. **Interprocedural summaries:** return, parameter-to-sink, receiver, heap-write, validation and context effects are conservatively instantiated at call sites; recursion reaches a least fixed point or compilation fails closed.
5. **Validator and encoder correctness:** each successful validator result satisfies its predicate; each encoder establishes only its declared context guarantee while preserving provenance.
6. **Sink separation:** every protected operation enforces its sink-specific contract.
7. **Compiler preservation:** source checking/lowering, CCAM validation/evaluation, native lowering and runtime adapters preserve the provenance and sink-event semantics.
8. **End-to-end composition:** compose the preceding simulations to obtain the theorem for actual executions.

A theorem about an abstract transfer function is not a theorem about the compiler until the checker implementation is proved to refine that function. A theorem about a formal sink adapter is not a theorem about an external database or process launcher until the concrete adapter is covered.

## 4. Current implementation evidence

`docs/assurance/INJECTION-CHECKER-CORRESPONDENCE.md` records the manually reviewed mapping from the current `compiler/checker.cap` laundering analysis to `verification/lean/CapstanVerification/InjectionChecker.lean`.

The Lean module currently proves local algebraic transfer lemmas for the restricted name-mark analysis, summary argument propagation, and monotonicity. It also contains gap witnesses for several currently missing transfers. The mapping to `checker.cap` is not machine-checked. The current production checker remains part of the trusted computing base.

Known source-level gaps include Boolean/comparison provenance, generic text conversion, collection join, length/shape, map membership/key/value facts, stored optional payloads, enum payloads, struct constructor fields, aliases, heap writes through calls, non-integer parameter summaries, policy summaries/effects and complete sink contracts. The checker fails closed when its bounded flow/summary iteration does not converge; this behaviour must be preserved by any replacement.

## 5. Release gates

No claim may be promoted to an implementation theorem until all of the following are recorded against an exact commit:

- pinned Lean build with warnings as errors;
- pinned independent proof checker replay;
- complete axiom audit for the exported theorem and critical definitions;
- parser/AST and checker-state correspondence proof or independently checkable translation validation;
- proof of every transfer and summary update, including conservative fallback behaviour;
- fixed-point and fail-closed resource-limit proof;
- validator/encoder/sink adapter refinement;
- source-to-CCAM and CCAM-to-runtime/backend refinement for the claimed execution path;
- adversarial and metamorphic tests corresponding to each formal obligation;
- explicit assumptions and trusted computing base.

No `sorry`, `admit`, custom axiom or hidden trusted assumption is acceptable. Tests supplement but do not replace proofs.

## 6. Execution order

1. Stabilise the scalar value-provenance domain and prove its transfer rules.
2. Replace variable-name marks with per-value facts and model reassignment, joins and loops.
3. Add alias-aware heap/aggregate paths and constructor/payload semantics.
4. Generalise summaries to every parameter type, receiver paths, heap writes and sink effects.
5. Prove validator and context-encoder contracts and all concrete sink adapters.
6. Mechanise checker-to-Lean correspondence and fixed-point equivalence.
7. Connect source semantics to CCAM and the selected production execution path.

