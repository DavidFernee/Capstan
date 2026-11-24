# Capstan Provenance Semantics

**Status:** Proposed normative security specification  
**Scope:** Static information-flow analysis for untrusted data, derived values, aggregate state, and security-sensitive sinks  
**Audience:** Compiler, language-semantics, verification, and security reviewers  
**Implementation status:** This document specifies the intended semantics. It does not claim that the current checker implements them.

## 1. Purpose and conformance

Capstan distinguishes the type-level fact that a value is untrusted (`Tainted`) from the flow-analysis fact that an ordinary value was computed from, selected by, or otherwise depends on untrusted input. This specification makes that distinction precise.

The analysis exists to prevent an attacker-controlled input from being reconstructed as trusted text, used to select trusted text without an explicit policy, or passed to a security-sensitive operation without the required validation or context-specific neutralisation.

A conforming implementation shall:

1. preserve provenance through every language operation that can transmit it;
2. preserve provenance through aliases, aggregate storage, calls, returns, and pattern matching;
3. distinguish data dependence from control dependence;
4. enforce sink-specific obligations rather than treating every tainted value as universally unusable;
5. fail closed when the analysis cannot establish a required fact or complete its fixed-point computation; and
6. produce deterministic results independent of local variable names, declaration order, or equivalent refactoring.

This is a semantic target, not a claim of current implementation conformance. Any intentional exception must be documented as a language-level limitation and reflected in the threat model and test suite.

## 2. Terminology and security model

### 2.1 Sources

A **source** is an operation that introduces attacker-controlled data. Examples include reading standard input, reading files or environment values, command-line arguments, and the explicit `taint(s)` testing/annotation operation.

Each source occurrence is assigned an abstract source identity `s`. Source identities need only be distinct within one analysis; they are not runtime tags.

A value may depend on multiple sources. The analysis therefore uses sets of source identities, not one Boolean taint bit.

### 2.2 Provenance is not a safety verdict

The analysis shall not collapse these different questions:

- **Origin:** which untrusted sources can influence this value?
- **Dependence:** did the value arise by computation, selection, or control dependence?
- **Validation:** which precisely defined predicates have been established about the value?
- **Contextual safety:** for which output or interpretation contexts has the value been neutralised?
- **Authority:** has an explicit, auditable declassification or trust decision occurred?

A value derived from untrusted input can be safe for a particular context without ceasing to have that origin. For example, HTML-escaped text remains input-derived but is suitable for the HTML text context covered by the escaper's contract.

### 2.3 Threat boundary

This analysis addresses accidental or adversarial information-flow mistakes in Capstan source. It does not prove the absence of compiler implementation defects, malicious compiler binaries, side channels below the language abstraction, or malicious developer intent.

Control-dependence tracking is intentionally limited by default (Section 7). That limitation must remain explicit; it must not be described as complete noninterference.

## 3. Abstract domain

The following is a specification-level domain. An implementation may choose a more efficient representation if it preserves the stated transfer and ordering properties.

### 3.1 Source sets

Let `Src` be the finite set of source identities in a compilation unit. Let:

```
Origin = P(Src)
```

where `P` is the powerset. The order is subset inclusion, bottom is the empty set, and join is set union.

An abstract value may depend on any number of sources:

```
origin(v) : Origin
```

### 3.2 Dependence kinds

For each value, track at least:

- `data(v)`: sources that directly influence the value through computation or conversion;
- `select(v)`: sources that influence which value or element is selected;
- `control(v)`: sources that influence the value solely through control-flow choice, when strict control tracking is enabled.

The first two are mandatory. Control dependence is separately configurable and is not implicitly merged into data dependence.

The dependence sets are monotone: joining control-flow paths unions the relevant sets. An operation may add dependencies but may not silently remove them.

### 3.3 Validation facts

Validation facts are typed predicates, not generic “untainted” flags. A fact has the form:

```
Validated(predicate, subject, assumptions)
```

Examples include “this string satisfies the ASCII identifier grammar” or “this integer lies in the inclusive interval [a,b]”.

A validation fact is usable only for the exact value (or a semantics-preserving copy) and predicate for which it was established. Mutation, lossy conversion, concatenation, or arbitrary helper calls invalidate it unless a transfer rule explicitly preserves it.

Validation does not erase origin. It discharges only the sink obligation that its predicate is specified to discharge.

### 3.4 Contextual safety facts

Contextual safety is a set of named contexts, not a Boolean:

```
SafeFor(v) subset of Context
Context = {HtmlText, HtmlAttribute, HtmlScriptData, LogRecord,
           CsvField, JsonString, CSourceLiteral, ...}
```

The exact context set must be maintained with the sink inventory. A value safe for one context is not thereby safe for another. In particular, C escaping, CSV escaping, JSON escaping, HTML escaping and log escaping are not interchangeable.

Context safety facts are preserved only by operations whose contracts explicitly preserve them. Concatenation is permitted only under the rules for the resulting context.

### 3.5 Abstract values

An abstract value is modelled as:

```
AbsVal = (type, data, select, control, validation, safe_for, shape)
```

where `shape` contains the abstract structure needed for aggregate and optional values. The abstract value for a literal has empty source dependencies and no validation or contextual-safety facts unless its literal form itself establishes a documented property.

The join of two values of compatible type unions dependence sets and intersects guarantees:

- origins/dependencies are unioned (may-depend);
- validation and contextual-safety guarantees are intersected (must-hold on every path);
- aggregate shapes are joined recursively.

This polarity is essential: a fact is safe to rely on only if it holds on every path represented by the abstract state.

## 4. Abstract machine state and heap

### 4.1 Environment

The abstract environment maps each in-scope variable binding to an abstract value:

```
Env : BindingId -> AbsVal
```

Bindings use compiler-resolved identities, not source variable names. Shadowed variables therefore cannot collide, and renaming a variable cannot alter analysis results.

### 4.2 Heap and aliasing

The abstract heap maps abstract allocation sites to abstract objects:

```
Heap : Location -> AbstractObject
PointsTo : BindingId -> P(Location)
```

An abstract object contains field and element paths, each associated with an abstract value. Maps additionally track key provenance and value provenance separately.

Two variables that may refer to the same allocation share the same abstract heap state. A mutation through either alias updates that shared state.

For a strong update, the points-to set must identify exactly one abstract object and the analysis must establish that the update is definite. Otherwise the implementation performs a weak update by joining the old and new abstract values. It must never discard a possible prior dependency merely because alias information is imprecise.

An implementation may begin with allocation-site abstraction and conservative weak updates. More precise context- or flow-sensitive heap abstractions are optimisation choices, not prerequisites for soundness.

### 4.3 Aggregate paths

The abstract model shall distinguish at least:

- struct fields;
- list elements;
- map keys;
- map values;
- enum payload positions;
- optional payloads;
- nested aggregate paths.

A coarse summary such as “this aggregate may contain derived data” is sound as a fallback, but it is not sufficient to justify treating every operation on the aggregate as independent of provenance. If a coarse summary causes imprecision, the implementation may conservatively reject; it may not silently accept.

### 4.4 Lifetime and mutation

Removing an element does not retroactively erase dependencies already observed by a program. It does update the current abstract heap shape. A subsequent read must use the post-mutation shape and the correct element mapping.

Collection operations must model index shifts, map replacement, key removal, clear, pop, insertion and mutation through aliases. This is required both for provenance correctness and to avoid stale abstract facts.

## 5. Transfer rules

The following rules are normative at the semantic level. “Join” means union of possible dependencies and intersection of guarantees as defined above.

### 5.1 Literals and variables

- A literal introduces no untrusted source dependency.
- A variable read returns the abstract value in `Env`.
- Assignment replaces the binding's value with the right-hand-side abstract value, subject to the language's binding and alias rules.
- Reassignment must not retain stale validation or contextual-safety facts from the previous value.
- A copy of an immutable scalar preserves its abstract value.

### 5.2 Unary and binary operations

For ordinary arithmetic, bitwise operations, shifts, comparisons and Boolean operators, the result's data dependencies include the data dependencies of every operand that can affect the result.

For example:

```
data(a + b) = data(a) union data(b)
data(a == b) = data(a) union data(b)
data(!a) = data(a)
```

The same rule applies to wrapping arithmetic. Wrapping changes numeric semantics, not provenance.

A comparison of an input-derived integer produces an input-derived Boolean. Storing that Boolean in a local must preserve its dependencies.

Short-circuit operators preserve the language's evaluation semantics. Their result carries data dependencies from operands that can determine the Boolean result. Whether branch-only effects are tracked is governed by Section 7.

### 5.3 String construction and conversion

String concatenation joins the dependencies of both operands. It preserves contextual safety only where the language's context-typed concatenation rules prove the result remains safe.

Conversions preserve source dependencies unless a specific operation has a documented, sound declassification contract. Formatting an integer, converting a Boolean to text, joining a list, slicing a string, or converting a byte to a character does not by itself remove origin.

In particular:

- `int_to_str(x)` preserves dependencies of `x`;
- `to_text(x)` preserves dependencies of `x`;
- `char_str(x)` preserves dependencies of `x` and is subject to the reconstruction sink rule;
- `join(xs, sep)` depends on the separator and every element that may contribute to the result;
- string slicing depends on the source string and on any derived index or bound that selects the result.

### 5.4 Collections

For lists:

- `push`, `insert`, indexed assignment and construction update element provenance;
- `get`, indexing, `pop` and `remove_at` return provenance from the selected element;
- `len` depends on the collection's length provenance when that length can depend on untrusted operations;
- iteration and enumeration expose the provenance of yielded elements.

For maps:

- `set(k,v)` records key provenance and value provenance independently;
- `get(k)` depends on the query key (selection dependence) and the selected stored value;
- `keys()` returns keys with their stored provenance;
- `has(k)` and `remove(k)` return Booleans dependent on the query key and on the relevant map state;
- replacement, removal and enumeration update or expose the correct key/value provenance.

The map key is not merely an implementation detail. It is observable program data and can itself encode attacker-controlled information.

### 5.5 Structs and enums

Struct construction records provenance independently for each field. Field assignment updates the field in the abstract heap. Field reads return that field's provenance, including through aliases and nested paths.

Enum construction records provenance for each payload position. Pattern matching binds each payload variable to the corresponding abstract payload value. Matching on a derived discriminant is a selection dependency; payload extraction is a data dependency on the selected variant and its payload.

### 5.6 Optionals

An optional value carries the abstract value of its possible payload. Storing an optional in a local does not erase that value. Unwrapping transfers the payload provenance to the bound variable.

If an optional may be absent, the value of the binding exists only on the present branch. The absence/presence predicate is itself dependent on the optional's provenance where that predicate is observable.

### 5.7 Functions and methods

A call applies the callee's summary to the actual arguments and the caller's heap. The summary must account for all parameter types, not only integers.

A method receiver is an ordinary dependency-bearing input and must be represented explicitly (for example, as parameter zero or a named receiver dependency).

The result receives the summary's return dependencies. Heap mutations are applied to the corresponding actual objects, including aliases. Sink effects are checked against actual argument provenance at the call site.

### 5.8 Policies and authorization

A policy is analysed as a Boolean-returning function with the same provenance rules as any other function. Its parameters must be seeded when computing summaries. Calls through `authorize` apply the policy summary to the actual arguments.

The resulting grant is an authorization capability, not a general provenance sanitizer. Possession of a `Grant<P>` does not erase provenance from the values used to obtain it.

Policy purity and repeated evaluation are separate effect-system requirements. This specification does not assume purity merely because a function is declared as a policy.

## 6. Interprocedural summaries and fixed points

A function summary must describe at least:

```
FunctionSummary {
    return_dependencies
    heap_effects
    sink_effects
    selection_effects
    validation_effects
    contextual_safety_effects
}
```

Dependencies are expressed in terms of parameter identities and paths, not just parameter types. A path may denote a scalar parameter, a struct field, an aggregate element, a map key, a map value, an optional payload, an enum payload, or a nested path.

A summary must distinguish:

- dependencies of the return value;
- mutations to objects reachable from each parameter;
- values passed to security-sensitive sinks;
- validation facts established for returned values or mutated fields;
- contextual-safety facts established by documented escapers.

Summary composition substitutes actual-argument abstract paths for formal-parameter paths. It must preserve alias relationships between arguments. If two formal parameters may refer to the same object at a call site, their effects must be combined on that object.

Recursive and mutually recursive functions are solved by monotone fixed-point iteration over the finite abstract domain. A worklist over strongly connected components is recommended. The solver must terminate by reaching a fixed point or report an analysis failure that prevents acceptance wherever the incomplete summary could affect a security decision.

An iteration cap is not itself a soundness argument. If the cap is reached, the compiler must fail closed; it must never use partial summaries to accept a program.

## 7. Control dependence

Capstan's default model intentionally distinguishes direct data dependence from information carried only by branching.

A comparison such as:

```
bool is_x = input.at(0) == 88;
```

is direct data dependence and must be tracked.

By contrast, assigning a trusted constant in one branch or another introduces control dependence:

```
if (input.at(0) == 88) {
    result = "x";
} else {
    result = "a";
}
```

The default analysis need not mark every such constant as data-derived. This preserves the ability to write validators and parsers using ordinary control flow.

However:

1. the default limitation must be documented as an intentional implicit-flow exclusion;
2. direct Boolean results of comparisons must still carry data provenance;
3. an optional strict mode may track control dependence and reject flows to configured sinks;
4. security claims must not imply complete noninterference while control dependence is excluded.

The strict mode, if implemented, must define the control-dependence scope precisely (including exceptional exits, early returns, loops and pattern matching).

## 8. Sinks, validation, escaping and declassification

### 8.1 Sink contracts

Every security-sensitive operation must have an explicit contract identifying:

- accepted abstract types;
- required validation predicates;
- required contextual-safety facts;
- whether data dependence is permitted;
- whether selection dependence is permitted;
- whether the operation itself is a sink or a declassification boundary.

The sink inventory must include at least output, HTML, logs, CSV, JSON, C source generation, SQL, process execution, filesystem paths, identifiers, credentials and trusted-text selection.

### 8.2 Reconstruction sink

`char_str` converts an integer to a one-byte string. If its argument has a data dependency on an untrusted byte source, the operation is a reconstruction sink and must be rejected unless an explicitly specified validation/declassification rule discharges that obligation.

A sequence of individually harmless operations must not erase the dependency before `char_str` is reached.

### 8.3 Selection sinks

Selecting trusted text using attacker-influenced indices, keys, bounds or predicates can disclose or reconstruct information. The analysis must inspect both the selected value and the selector.

Examples include string indexing, slicing, list indexing where the element is trusted text, and map lookup where the key is derived. The precise policy may distinguish selection of trusted text from selection of non-text data, but the distinction must be explicit and tested.

### 8.4 Context-specific escaping

Escapers establish only their documented context:

- `escape_html` establishes HTML safety;
- `escape_log` establishes log-record safety;
- `escape_csv` establishes CSV-field safety;
- `escape_json` establishes JSON-string safety;
- `escape_c` establishes C-source-literal safety only for the exact C grammar position documented by the compiler.

These outputs must not be represented as a generic trusted string if doing so permits cross-context composition. Dedicated types or equivalent unforgeable abstract facts are required.

### 8.5 Validation

Validators establish narrow predicates. For example, identifier validation must establish the exact identifier grammar required by the consuming operation. A successful range validation establishes only the checked numeric interval.

A validator must not erase dependencies unrelated to the property it proves. Nor may the compiler infer validation from a function name; it must use a trusted builtin contract or a verified function summary.

### 8.6 Explicit trust

`trust(value, justification)` is an explicit declassification boundary. It must require a non-empty literal justification and produce an auditable diagnostic or review record.

It is not a general-purpose escape hatch from sink contracts. It does not make the value safe for every output context. The implementation must preserve an audit trail that identifies the source dependencies and the exact declassification site.

## 9. Soundness obligations

The implementation must establish the following properties relative to the language's operational semantics and stated threat model.

**P1 — Source introduction.** Every designated untrusted source introduces a fresh or conservatively joined source identity.

**P2 — Transfer preservation.** For every expression and statement, the abstract transfer over-approximates concrete source dependence under the defined dependence model.

**P3 — Alias preservation.** Any two references that may denote the same concrete object are represented by abstract locations whose joined state cannot lose a possible dependency.

**P4 — Mutation preservation.** Every concrete aggregate mutation is reflected in the abstract heap; no read after mutation can rely on a stale abstract value.

**P5 — Call preservation.** Applying a function summary over-approximates the function's concrete return dependencies, heap effects and sink effects for every admissible argument and alias configuration.

**P6 — Context separation.** A contextual-safety fact is used only by a sink whose contract is covered by that fact.

**P7 — Validation integrity.** A validation fact is relied upon only when the exact predicate is established and remains valid for the consumed value.

**P8 — Fail-closed analysis.** Parse/type/analysis errors, unsupported constructs, resource exhaustion, or incomplete fixed points cannot result in acceptance based on missing provenance information.

**P9 — Refactoring invariance.** Renaming bindings, introducing equivalent copies, extracting helpers, or introducing aliases cannot make a program acceptable if the original program is rejected for the same sink obligation.

**P10 — No overclaim.** The compiler's documentation and diagnostics describe only the dependence classes and sinks actually covered by the implementation.

These are proof obligations, not claims that the current implementation already satisfies them.

## 10. Unsupported constructs and conservative fallback

The checker must have an explicit inventory of constructs and builtins with transfer rules. A newly added operation must not silently default to “no provenance”.

If a construct's effect cannot be modelled, the compiler must choose one of:

1. reject its use in an analysed context;
2. conservatively propagate the union of all relevant input dependencies and possible heap effects; or
3. require an explicitly reviewed trusted summary.

An unknown external function, native escape hatch, or future FFI must never receive a permissive default summary.

## 11. Required adversarial tests

The test suite must pair negative tests (must reject) with positive tests (must accept). Required families:

| Family | Required cases |
|---|---|
| Scalars | arithmetic, bitwise/wrapping operations, comparisons, Boolean locals, conversions |
| Aliasing | direct, chained, parameter-passed and returned aliases; mutation through each alias |
| Lists | push, insert, indexed write/read, pop, remove, clear, join, length |
| Maps | derived keys, derived values, keys, get, has, remove, replacement and iteration |
| Structs | constructor initialisers, field writes, nested fields, receiver methods |
| Enums | payload construction, nested payloads, pattern bindings, matching |
| Optionals | direct unwrap, stored optional, optional returned from helper |
| Calls | every parameter type, parameter-to-return, parameter-to-sink, mutation effects |
| Policies | parameter summaries, helper calls, derived Boolean decisions, authorize arguments |
| Contexts | cross-use among HTML, log, CSV, JSON and C escaping |
| Validation | valid and invalid values, predicate preservation, invalidation after mutation |
| Recursion | direct recursion, mutual recursion, long call chains, fixed-point exhaustion |
| Refactoring | rename, copy, alias, helper extraction and equivalent statement rearrangement |

Metamorphic tests must assert that security classification is invariant under semantics-preserving transformations. In particular, variable renaming, introducing an alias, moving aggregate mutation into a helper, storing an optional before unwrapping it, and moving a value through a struct constructor must not erase provenance.

Every regression must include a short explanation of the dependency path and the sink obligation it exercises.

## 12. Migration plan

The recommended migration is staged:

1. **Semantic inventory:** enumerate every AST node, builtin, method, type constructor, sink and validation operation; assign each an explicit transfer contract.
2. **Abstract domain:** introduce binding identities, source sets, dependence kinds and must-hold validation/context facts.
3. **Heap abstraction:** add points-to sets and aggregate paths, initially using conservative allocation-site abstraction.
4. **Interprocedural summaries:** model parameter paths, receiver dependencies, return values, heap effects and sinks; solve recursive components to a fixed point.
5. **Sink enforcement:** migrate reconstruction and selection sinks first, then context-specific output and execution sinks.
6. **Regression expansion:** add the adversarial and metamorphic matrix before removing the legacy analysis.
7. **Differential assurance:** run the existing CWE atlas, compiler acceptance/rejection suites, stage-0 differential checks, mutation/fuzz campaigns and sanitizer-backed runtime tests.
8. **Claim reconciliation:** update the CWE coverage document and threat model only after the relevant tests and implementation evidence exist.

The legacy analysis should remain available behind a temporary comparison mode during migration. A discrepancy between old and new analyses must be investigated; it must not automatically be resolved in favour of whichever accepts more programs.

## 13. Current implementation gap map

The following known findings are directly addressed by this specification:

| Finding | Semantic requirement |
|---|---|
| TYPE-01 | Context-specific safety facts and non-interchangeable escaper contracts |
| TYPE-02 | Aggregate parameter paths in summaries |
| TYPE-03 | Shared abstract heap identities for aliases |
| TYPE-04 | Interprocedural heap mutation effects |
| TYPE-05 | Conversion transfer rules for `to_text` |
| TYPE-06 | Collection-element dependencies through `join` |
| TYPE-07 | Explicit policy decision for input-derived length metadata |
| TYPE-08 | Data dependencies through comparisons and Boolean expressions |
| TYPE-09 | Provenance for all scalar local types, including Boolean |
| TYPE-10 | Separate map-key provenance and `keys()` propagation |
| TYPE-11 | Summaries for scalar string and all other parameter types |
| TYPE-12 | Key-dependent `has` and `remove` results |
| TYPE-13 | Optional payload provenance through storage and unwrapping |
| TYPE-14 | Struct constructor field provenance |
| TYPE-15 | Explicit collection-shape and length provenance |
| TYPE-16 | Receiver and struct-path dependencies in method summaries |
| TYPE-17 | Enum payload and pattern-binding provenance |
| TYPE-18 | Map value provenance through trusted-key lookup |
| TYPE-20 | Policy parameter and `authorize` call summaries |

TYPE-19 is intentionally absent: it was withdrawn as a false positive after confirming that user-defined method calls are normalised to ordinary calls before summary analysis.

TYPE-21 (policy purity) is related but not solved by provenance alone. It requires a separate effect system or a clearly specified policy evaluation model.

## 14. Relationship to existing Capstan documentation

This document refines the existing distinction between `Tainted`, derived values, contextual escaping and the documented control-flow limitation. It does not silently change the language's runtime behaviour.

Before this specification is treated as normative, the language owner should decide:

1. whether length and other aggregate metadata are prohibited from influencing protected outputs, or merely tracked for explicit sink policy;
2. whether strict control-dependence analysis is required for any supported security profile;
3. which exact grammar positions are covered by `escape_c`;
4. whether validation facts are represented by dedicated types, compiler-internal refinements, or both; and
5. which declassification operations are permitted beyond explicit `trust()`.

Until those decisions are made, the conservative interpretation is to preserve provenance and require an explicit documented sink rule rather than infer safety.

## 15. Acceptance criteria for implementation

The redesign is ready for implementation review when:

- every AST node and builtin has an explicit transfer classification;
- every security sink has an explicit contract;
- the abstract domain and join operators are defined;
- alias and heap update semantics are specified;
- summaries cover all parameter types, receiver paths and heap effects;
- fixed-point failure is fail-closed;
- the adversarial test matrix has concrete test cases;
- no known TYPE finding lacks a corresponding semantic rule or an explicitly accepted limitation; and
- the CWE coverage and threat-model claims are reconciled with actual implementation and test evidence.

The specification itself does not establish that the compiler is sound. It establishes the target against which the implementation, tests and eventual formal proofs can be assessed.
