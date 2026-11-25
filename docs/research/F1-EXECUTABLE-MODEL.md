# F1 executable guarantee model

**Status:** Research prototype; executable Capstan reference model  
**Implementation:** `verification/f1_guarantee_model.cap`  
**Runner:** `tests/run.sh`  
**Normative authority:** None yet. This prototype does not amend the language specification.

## 1. Purpose

F1 investigates whether provenance, confidentiality, context safety, authority, effects and resource bounds can be composed without one dimension accidentally erasing or impersonating another.

The first artefact is deliberately implemented in Capstan. It is a finite abstract model with explicit transfer functions and adversarial tests. It is not a source analyser, a compiler pass, a proof of soundness, or evidence that the current compiler enforces these properties.

The experiment is intended to make design choices falsifiable before they become language features. The current implementation uses a product-shaped record with factored fields and transfer operations; it is a baseline artefact, not a decision between the factored-judgement and unified-product formulations.

## 2. Abstract value

The prototype represents a value as:

```text
Value = (
  data_provenance, data_top,
  selection_provenance, selection_top,
  control_provenance, control_top,
  confidentiality,
  context_guarantees
)
```

The components are independent:

- Data provenance records direct dependencies.
- Selection provenance records dependencies that determine which aggregate element is observed.
- Control provenance records dependencies that determine which branch or control decision selected an observable result. It is kept distinct from data and selection provenance so integrity-validation policies need not be conflated with confidentiality policies.
- The top flags mean that the finite source abstraction is no longer precise. They must not be interpreted as an empty set.
- Confidentiality is an ordered lattice: Public < Secret < Unknown.
- Context guarantees are a finite set. A sink is permitted only when its required context is present.

The model uses integer bit masks for small, stable test identities. The only value marked safe in all four contexts is the empty string, which contributes no content; arbitrary string literals are not assumed safe. A production analysis must use a collision-free identity discipline within its compilation scope, an explicit bounded representation, and a sound widening rule. These masks are not a proposed user-facing source identity representation.

## 3. Transfer rules

Let `⊔` be provenance union, with `top` absorbing, and let `∧` be context-set intersection.

### Derivation

For a binary value-producing operation:

```text
data(out)       = data(left) ⊔ data(right)
selection(out)  = selection(left) ⊔ selection(right)
control(out)    = control(left) ⊔ control(right)
conf(out)       = max(conf(left), conf(right))
contexts(out)   = contexts(left) ∧ contexts(right)
```

The context intersection is intentionally conservative: a concatenation is safe in a context only if every component is safe in that context.

### Selection

For `container[index]` returning `selected`:

```text
data(out)       = data(selected) ⊔ data(index)
selection(out)  = selection(selected) ⊔ data(index) ⊔ data(container)
conf(out)       = max(conf(selected), conf(index), conf(container))
contexts(out)   = contexts(selected)
```

This is a deliberately conservative first rule. A later model must distinguish container shape, key/index selection, aliasing and aggregate-content dependencies more precisely.

### Control dependence

For a branch with condition `c` and arms `t` and `f`, the result joins the arm values and records the condition's data, selection and control provenance in a separate control-dependence component. Confidentiality joins with the condition even when both arms return constants. This is important for secret-dependent predicates and branch-only disclosures.

This is still an abstract branch rule: the prototype does not model path-sensitive equivalence of the arms, program-counter stacks, termination channels, timing, or declassification. A production system must state exactly which control observations it tracks and where.

### Context-specific encoding

Each encoder establishes exactly its own context guarantee. HTML, log, CSV and JSON guarantees are not interchangeable. Encoding does not declassify secrets or erase provenance.

### Interprocedural summaries

A complete summary separately states whether the result has data, selection or control dependence on an argument, and whether a data-dependent result preserves the argument's context guarantee. Applying an incomplete summary returns top provenance, top selection dependence and unknown confidentiality. The model does not treat a missing summary as a pure function.

A real summary must be derived from a function body or independently checked evidence. The prototype's hand-authored summaries only test the transfer rule.

### Authority and effects

Authority requirements and computational effects are represented independently. Sequential composition unions both sets. Attenuation is set intersection:

```text
child_authority = parent_authority ∩ requested_authority
```

Unknown authority/effect bits are rejected rather than silently discarded. The prototype checks non-amplification only. It does not yet model object-bound grants, revocation, delegation, lifetime, module interfaces, host adapters or confused-deputy behaviour.

### Resources

Sequential fuel and memory bounds are added. Both additions are checked before evaluation. Unknown or overflowing bounds fail closed. Memory is summed rather than assuming non-overlapping lifetimes; this is conservative but imprecise.

This model does not yet cover stack, allocation counts, file descriptors, tasks, energy, concurrency, target-specific cost models or amortised potential transfer.

## 4. Adversarial properties exercised

The Capstan test program currently checks:

1. Provenance survives repeated interprocedural identity summaries.
2. Byte-reconstruction helpers preserve input provenance while losing unrelated context guarantees.
3. Secret-derived predicates remain confidential.
4. HTML and CSV guarantees cannot be substituted, and mixed-context concatenation loses both.
5. Capability attenuation cannot create authority absent from the parent.
6. Authority and effects compose as distinct sets.
7. Resource composition is exact at the declared boundary.
8. Resource overflow and unknown bounds are rejected rather than wrapped or silently weakened.
9. Secret-dependent branch results retain control dependence and confidentiality.
10. An incomplete function summary widens to unknown.
11. Invalid source identities widen rather than aliasing.
12. Fuel and memory overflow are both rejected.
13. Selection dependencies survive even when the selected payload itself is not returned.
14. Invalid authority/effect sets and invalid sink-context identifiers are rejected.

The standard runner invokes this artefact through `bin/capstan test`. It must remain in that runner; an uninvoked model is not conformance evidence.

## 5. Research questions and next experiments

### RQ-F1-A: factored judgements versus a unified product domain

Compare two formulations over the same syntax and transition system:

- **Factored judgements:** independently defined provenance, confidentiality, context, authority/effect and resource judgements, with explicit compatibility and composition rules.
- **Unified product domain:** one product abstract value and one transfer relation, with independent projections and joins.

Measure:
- soundness obligations and proof decomposition;
- whether any component can erase another component's facts;
- summary size and compositionality;
- widening behaviour and termination;
- precision on aliases, aggregates and control-flow joins;
- analysis time and memory on the same Capstan corpus.

Do not choose a formulation on aesthetic grounds. Publish counterexamples, proof obligations, precision loss and cost.

### RQ-F1-B: summary derivation

Replace hand-authored summaries with summaries derived from actual Capstan function bodies. Test direct calls, nested helpers, early returns, branch joins, loops, struct fields, lists, maps, enum payloads, aliases and mutation. Unknown or unsupported constructs must widen or reject, not produce an optimistic summary.

### RQ-F1-C: contextual output

Replace the abstract context tags with parser-aware context state. HTML text, quoted attributes, URL attributes, event handlers, script/style content, comments and malformed/incomplete templates require distinct states. A successful local escape call is not enough to prove safety of a multi-statement template.

### RQ-F1-D: resource composition

Compare conservative additive memory bounds with region/lifetime-aware bounds and an amortised potential model. Include recursion, loops, allocation, aliasing, early termination and concurrent tasks. Every bound must state whether it is a static upper bound, a runtime quota, or both.

## 6. Threats to validity

- The model's own transfer functions may be wrong. Tests can find counterexamples but cannot establish general soundness.
- The model is finite and does not represent arbitrary program state or source identity.
- The model is not derived from the compiler's AST or checked source semantics.
- The test runner and current compiler/runtime remain in the trusted execution path.
- Passing the model does not prove the generated C, runtime, host or platform safe.
- The chosen test cases are not an exhaustive attack corpus.
- The abstract authority and context sets omit important operational semantics.

These limitations are deliberate and must remain visible until the corresponding research gates are closed.

## 7. Acceptance gate

Do not promote F1 from research prototype to a language guarantee until:

1. the semantic rules are versioned and reviewed;
2. summary derivation is connected to actual Capstan source;
3. unsupported cases fail closed;
4. adversarial conformance tests are in the standard runner;
5. a soundness argument is machine-checked for a clearly bounded subset;
6. the implementation is shown to refine that subset's semantics;
7. the trusted computing base and residual platform assumptions are disclosed; and
8. exact-head CI and independent review evidence are available.

No universal absence-of-vulnerabilities claim follows from this gate. Each CWE class and ecosystem component needs its own threat model, evidence and residual-risk statement.
