# F1 source-derived abstract-state design

**Status:** Research design with a first compiler implementation slice; non-normative  
**Target:** Replace the scalar-slice variable-name may-analysis in `compiler/checker.cap`  
**Related:** [F1 executable model](F1-EXECUTABLE-MODEL.md), [provenance semantics](../assurance/PROVENANCE-SEMANTICS.md), [scalar slice](../assurance/PROVENANCE-SCALAR-SLICE.md)

## 1. Problem statement

The current checker represents derived provenance as membership in `Flow.vars: Map<int>`. This is a useful conservative prototype, but it conflates a variable's identity with the value currently stored in it. It cannot express:

- strong replacement of a scalar local after reassignment;
- distinct provenance for `record.public_name` and `record.private_name`;
- distinct list element, map key and map value dependencies;
- reference aliases between variables;
- writes through aliases or through helper calls;
- summaries that describe which input path affects which output path;
- a principled distinction between a known-empty fact and an unknown fact.

The next implementation must not merely replace `Map<int>` with a more elaborate map while retaining these semantic ambiguities. It needs an explicit abstract state and transfer relation derived from the actual typed AST.

## 2. Design constraints

1. **Source-derived:** abstract facts are computed from checked Capstan AST nodes and declared types, never hand-authored per-function summaries.
2. **Name-independent:** renaming a local must not change the security result.
3. **Alias-conservative:** every may-alias write is visible through every possible alias.
4. **Path-aware:** fields, list elements, map keys and map values are separate abstract locations where the representation permits it.
5. **Monotone at joins:** branch and loop joins retain every possible dependency.
6. **Strong updates only with proof:** a write may kill an old fact only when the analysis proves a unique, non-escaped target and a complete replacement.
7. **Fail closed:** unsupported AST forms, unknown call effects, exhausted budgets or failed convergence cannot produce an optimistic summary or silently skip a sink.
8. **Deterministic:** source ordering and local spelling do not affect the result.
9. **Bounded:** every map, path depth, source set, worklist and iteration count has an explicit bound; exceeding a bound widens to top or rejects compilation.
10. **Separate dimensions:** provenance, confidentiality, validation, context guarantees, authority, effects and resources remain distinct components.

## 3. Abstract domain

### 3.1 Source sets

Let `Source` identify an input origin within one compilation analysis. The provenance lattice is:

```text
Prov = Finite(Set<Source>) | ManySources
bottom = Finite({})
join(Finite(a), Finite(b)) = Finite(a union b), if within budget
join(_, ManySources) = ManySources
```

A source identity is an analysis identity, not a variable name or runtime tag. If source identity allocation exceeds its budget, the result is `ManySources`; identities must never wrap, collide or be dropped.

### 3.2 Access paths

An abstract access path is rooted at a local or parameter and extended by typed selectors:

```text
Path ::= Root(binding_id)
       | Field(Path, field_id)
       | ListElement(Path)
       | MapKey(Path)
       | MapValue(Path)
       | EnumPayload(Path, variant_id, field_id)
       | OptionalValue(Path)
       | UnknownChild(Path)
```

Selectors are based on resolved AST/type identity, not source spelling. Dynamic list indices share a list-element summary. Dynamic map lookups separately depend on the key expression and may observe the map-value summary. `UnknownChild` is a conservative summary for unsupported or unbounded nesting.

Path-prefix queries are conservative: a fact at an aggregate root may affect any child; a fact at one known field does not automatically taint a disjoint field. A write to an unknown child joins into the aggregate's unknown-child summary.

### 3.3 Abstract values and heap

The proposed state is:

```text
AValue {
  data: Prov,
  selection: Prov,
  confidentiality: Conf,
  validation: ValidationFacts,
  contexts: ContextFacts
}

State {
  locals: BindingId -> AValue,
  refs: BindingId -> Set<Loc>,
  heap: (Loc, AccessPath) -> AValue,
  escaped: Set<Loc> | AllLocations
}
```

`Conf`, `ValidationFacts` and `ContextFacts` use their own lattices and joins. No operation that adds a context guarantee may erase provenance or reduce confidentiality. A validator may add only its documented predicate on the successful result. An encoder may add only its documented output-context guarantee.

Locations are abstract allocation identities. The first implementation may use allocation sites plus a summary location for repeated allocations. If location cardinality exceeds the budget, locations widen to `AllLocations`, and writes/reads must conservatively interact with that summary.

### 3.4 State join

At a control-flow join, locals are joined by binding identity, reference targets are unioned, and heap facts are joined pointwise. Missing entries mean bottom only when the location is known to be absent; otherwise they mean unknown and must widen. The implementation must make this distinction explicit rather than overloading missing map entries.

## 4. Transfer rules

### 4.1 Scalar assignment

For `x = e`, evaluate `e` in the pre-state and replace the scalar binding's abstract value with the result. This is a strong update because a scalar local stores one value at that program point.

The current monotone `mark(name)` operation cannot express this rule and therefore retains provenance after a safe overwrite. The replacement analysis must preserve soundness at joins and loops while avoiding this permanent name taint.

### 4.2 Aggregate construction

For a struct/list/map/enum/optional construction, evaluate each component and store its abstract value at the corresponding access path. Do not collapse all components into one root bit. If the constructor shape is not fully known, join the unknown components into `UnknownChild`.

### 4.3 Field and element reads

- A field read obtains the field's heap value and joins any root-level or unknown-child summary that may apply.
- A list read joins the selected element summary and the index expression's selection provenance.
- A map read joins the selected value summary, the lookup-key provenance and the map's unknown-value summary.
- A missing or unsupported shape yields top, not bottom.

Selection provenance is distinct from data provenance: choosing a public element using a secret or untrusted key still records that the selection itself depends on that key.

### 4.4 Aggregate writes

A write through a reference updates every abstract location in the receiver's points-to set. A strong update is permitted only for a singleton, non-escaped location with a complete selector. Otherwise perform a weak update by joining the new value into the old abstract value.

For a dynamic index or key, update the corresponding element/value summary. A write through `UnknownChild` affects all possibly overlapping children.

### 4.5 Aliases and escape

Copying a reference copies its points-to set. If two bindings may refer to the same location, reads and writes must share the same heap facts. Passing a reference to a call with unknown effects marks the reachable locations escaped and widens their mutable contents. Returning a reference propagates its points-to set into the caller summary.

No alias precision may be obtained by assuming that two differently named variables refer to different objects. If the language's actual value/reference semantics are not yet established for a type or operation, the analysis must choose the conservative reference interpretation or reject that case pending a semantic decision.

### 4.6 Calls and summaries

A function summary is a relation over abstract input paths, output paths, sink effects and heap effects, not a Boolean per parameter:

```text
Summary {
  return_dependencies: Path -> DependencyKinds
  heap_reads: Set<FormalPath>
  heap_writes: Set<FormalPath>
  sink_dependencies: SinkId -> Set<FormalPath>
  authority_requirements: EffectSet
  completeness: Complete | Unknown
}
```

The first source-derived subset may omit authority/effect fields if they are not yet connected, but it must not fabricate purity. For an unknown or incomplete summary, mutable arguments and reachable locations are conservatively escaped; the return is top; and any applicable sink/effect policy is treated as unknown.

Recursive and mutually recursive summaries are computed as a least fixed point over a finite-height bounded domain. Widening must be monotone and explicit. If the worklist or iteration budget is exhausted before convergence, compilation fails with a deterministic diagnostic. A magic round count is not a proof of convergence.

### 4.7 Control dependence

The existing proposed provenance semantics excludes pure control dependence by default, while the F1 model tests strict control dependence for confidentiality. This design does not silently choose between them. The abstract state reserves a distinct control-provenance component, but propagation and sink policy remain disabled or experimental until the semantic conflict is resolved by counterexamples and a reviewed decision.

## 5. Required AST and language-semantics inventory

Before coding transfers, record the actual parser/checker representation and operational semantics for:

- `N_DECL`, `N_ASSIGN`, `N_GETF`, `N_INDEX`, `N_METHOD`, `N_NEW`, `N_INIT`, `N_NEWLIST`, `N_NEWMAP`, `N_ENUMVAL`, `N_MATCH`, `N_IF`, `N_WHILE`, `N_FOR`, `N_RETURN`;
- struct and enum field identity and layout;
- List/Map copy, mutation, indexing and iteration semantics;
- optional unwrapping and enum payload extraction;
- whether assignment and parameter passing copy values, copy references or move ownership;
- built-in methods' read/write/escape effects;
- function return and recursion semantics.

No transfer rule should infer ownership or aliasing from syntax alone if the runtime representation says otherwise.

## 6. Adversarial conformance matrix

The implementation is not ready until source-derived tests cover at least:

| Case | Required result |
|---|---|
| Scalar taint then overwrite with literal | Old scalar provenance does not survive the overwrite |
| Branch: tainted on one arm, literal on other | Join retains possible taint |
| Loop-carried scalar dependency | Fixed point retains every possible dependency |
| Two disjoint struct fields | Writing one field does not taint the other absent alias/aggregate dependence |
| Nested field write/read | Exact path or conservative ancestor summary is observed |
| List element write then read | Element provenance is preserved |
| Map key versus value | Key selection and stored value dependencies remain distinct |
| Two aliases, write through either | Read through the other observes the write |
| Alias passed to mutating helper | Caller heap state reflects the helper write |
| Unknown external call on reference | Reachable mutable state widens; no assumed purity |
| Recursive helper chain | Summary reaches fixed point or rejects on explicit budget exhaustion |
| Path/source/location budget exhaustion | Top or deterministic rejection, never fact deletion |
| Local renaming | Identical acceptance and diagnostics modulo source positions |
| Declaration reordering | Identical semantic result where language semantics permit reordering |
| Unsupported AST node | Explicit unknown/reject path, never silent bottom |

Each test must include both a positive control and a negative control where meaningful. Tests must assert the intended diagnostic code and location, not merely nonzero exit status.

## 7. Implementation sequence and gates

**A0 — Semantic inventory.** Confirm AST forms and runtime value/reference semantics. Deliver a source-linked table and identify unresolved ownership questions.

**A1 — Scalar environment.** Introduce binding identities and explicit `AValue` facts for scalar locals. Implement replacement and branch/loop joins. Keep aggregate analysis conservative. Add overwrite, branch and loop tests.

**A2 — Path-sensitive value state.** Add typed access paths for struct fields, enum payloads and optionals. Add nested read/write tests.

**A3 — Aggregate heap and aliases.** Add abstract locations, points-to sets, strong/weak update conditions and escaped-state widening. Add alias mutation tests.

**A4 — Source-derived summaries.** Derive return, sink and heap-effect summaries from function bodies. Add recursive/mutual recursion and unknown-call tests.

**A5 — Policy composition.** Connect the abstract state to explicit sink contracts and context-specific validation/encoding. Do not treat generic file output as a vulnerability sink without a documented policy.

Each gate requires exact-head standard tests, differential tests against a small executable reference semantics, bounded-resource tests and independent review. A passing finite test suite is evidence for the listed cases only, not a soundness proof.

## 8. Research questions

- Can a bounded path-sensitive heap domain achieve useful precision without whole-program points-to analysis?
- Which Capstan types are values and which are references at each backend, and can this be made backend-independent?
- Is allocation-site abstraction sufficient for the standard library's collection semantics?
- Which summary representation is both compositional and small enough for separate compilation?
- Can the same abstract state support data provenance, confidentiality and context safety without cross-domain erasure?
- What is the measured false-positive and compile-time cost of each widening policy?

The experiment must compare the factored-judgement and product-domain formulations on the same corpus. No representation is selected in advance.

## 9. Non-claims

This document is not a compiler implementation, formal proof, language guarantee, or claim that all known vulnerabilities are inexpressible. It does not settle Capstan ownership semantics, control dependence, complete sink policy, or backend refinement. The current scalar-slice checker remains the only implementation experiment until the staged gates above are completed.


## 11. Implementation progress (2026-11-26)

The first compiler slice now assigns a stable `binding_id` to each lexical declaration and propagates that identity to variable-reference AST nodes during name resolution. Provenance facts no longer use source spelling as the identity key, preventing unrelated locals in disjoint scopes from contaminating one another.

The flow domain now stores bounded typed access-path facts rooted at those binding identities:

- struct fields use distinct `.field` selectors;
- constant list indices use distinct `[index]` selectors;
- dynamic list indices widen to `[*]`;
- map key and value summaries use distinct `{key}` and `{value}` selectors;
- nested descendants contribute conservatively to aggregate observations;
- the domain is capped at 4096 facts and refuses compilation if the cap is exceeded.

This is still a monotone, syntax-directed may-analysis. It does not yet have a control-flow graph or explicit branch/loop state joins; it does not track reference aliases or escaped heap locations; and it does not perform strong updates. Aggregate and dynamic selectors are intentionally conservative. The next gates are explicit branch/loop joins, an alias/escape model with bounded abstract locations, strong-update proof conditions, and adversarial positive/negative tests for each transfer rule. These additions must be checked against the normative provenance semantics before any stronger guarantee is claimed.


The checker now also computes limited return/sink summaries for aggregate parameters. This does not model mutation effects or alias sets: the alias-laundering case is deliberately retained as an executable CWE-20 gap until heap/alias propagation is implemented.
