# Capstan — Provenance and Information-Flow Semantics

**Status:** Proposed language-security specification; review required  
**Scope:** Static provenance, aggregate and alias effects, interprocedural summaries, security-sensitive transformations, and policy evaluation  
**Implementation status:** Target design only. This document does not claim that the current compiler implements these rules or that they have been machine-checked.

---

## 1. Purpose and normative language

This document defines the intended semantics of Capstan's provenance analysis. Its purpose is to make information-flow guarantees explicit, compositional, testable, and suitable for later mechanisation.

The words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY are normative.

The analysis has two distinct obligations:

1. Preserve information about where values came from and how they depend on inputs.
2. Decide whether a particular use is permitted in its security context.

Provenance is not synonymous with taint, trust, sanitisation, or confidentiality. A value can originate from untrusted input and nevertheless be safe for a particular sink after suitable validation or context-specific encoding. A value can also be derived from a secret without being untrusted.

The design therefore keeps provenance, validation evidence, confidentiality, and effect information separate.

## 2. Security objectives and explicit non-objectives

### 2.1 Objectives

The analysis MUST:

- Preserve direct data dependence through expressions, assignments, conversions, aggregates, aliases, function calls, and returns.
- Preserve selection dependence when an input determines which existing value is read.
- Track provenance of aggregate elements, map keys, map values, struct fields, enum payloads, and optional contents.
- Propagate aggregate mutations through aliases and interprocedural calls.
- Preserve provenance through Boolean results and every other value type.
- Distinguish context-specific validation and encoding guarantees.
- Detect prohibited reconstruction of trusted text from untrusted bytes.
- Fail closed when an analysis resource limit prevents a sound result.
- Produce deterministic results independent of local variable spelling and irrelevant declaration ordering.

### 2.2 Deliberate limits

The default analysis does not claim complete noninterference in the presence of arbitrary control dependence, timing, termination, resource consumption, concurrency, external state, or hardware side channels.

A program can branch on an input byte and assign different constants in each branch. Tracking all such implicit flows would make ordinary validation impractical. The default policy therefore tracks explicit data and selection dependencies, while treating pure control dependence as a documented limitation.

An optional strict information-flow mode MAY add control-dependence tracking. It MUST be separately specified and MUST NOT be silently conflated with the default semantics.

This analysis does not establish that a program's business logic is correct, that a validator implements the intended business rule, or that a malicious developer has not deliberately declassified data.

## 3. Semantic domains

### 3.1 Source identities

Each source of externally controlled data or sensitive information is assigned an abstract source identity. Examples include a particular Tainted input, a secret value, a file/environment/argument input, or an externally supplied policy value.

Source identities are analysis identities, not runtime tags. They MUST be stable within one analysis run and MUST NOT depend on local variable names.

Let Src be the finite set of source identities in the analysed compilation unit. If the implementation bounds this set, overflow MUST widen to an explicit ManySources top element; it MUST NOT discard sources.

### 3.2 Provenance

A provenance fact records the sources on which a value may depend:

    Prov ::= NoSource | Sources(S subset Src) | ManySources

The ordering is subset inclusion, with ManySources as top. Join is set union, widened to top when required by a configured bound.

A value's provenance is a may-dependence: if source s appears in P(v), the analysis cannot prove that v is independent of s.

Provenance MUST be monotone at control-flow joins unless a sound strong update replaces the value stored at a location. Reassignment of a scalar local replaces its old value provenance; it does not permanently taint the variable name.

### 3.3 Dependency kinds

The analysis distinguishes at least:

- **Data dependence:** a computed result depends on an operand's value.
- **Selection dependence:** an operand selects an element, field, key, index, or branch of a data structure whose selected value is observed.
- **Aggregate-content dependence:** a read observes data previously stored in an aggregate.
- **Control dependence:** execution or a constant assignment depends only on a predicate. This is excluded from default propagation except where the language construct explicitly returns a predicate value.

A dependency fact is a relation between input paths and output paths, not only a Boolean tainted flag.

### 3.4 Abstract values

An abstract value contains independent components:

    AVal {
        data_prov: Prov
        selection_prov: Prov
        confidentiality: Conf
        validation: ValidationFacts
        context_safety: ContextFacts
        shape: AbstractShape
    }

Conf is an ordered confidentiality domain, at minimum Public, SecretDerived, and UnknownConfidentiality.

ValidationFacts records predicates established by recognised validators.

ContextFacts records contexts for which a value has a valid encoding guarantee.

AbstractShape records scalar, optional, aggregate, enum, or reference structure as needed by transfer functions.

The implementation MAY factor these components into separate maps or domains. It MUST preserve their semantic independence.

### 3.5 Validation facts

A validation fact is not a generic assertion that data is trusted. It is a certificate for a specific predicate, such as:

- Is a valid Capstan identifier.
- Is a decimal integer in a specified closed interval.
- Is a valid path under a named path policy.
- Is valid UTF-8.
- Satisfies a particular application predicate, if the compiler has a sound way to express and verify that predicate.

A validator returning an optional value establishes its documented predicate only on the successful unwrapped value. The failure branch does not receive that certificate.

A validation certificate MUST identify its predicate and relevant parameters. A certificate for one predicate MUST NOT be treated as proof of another.

### 3.6 Context-safety facts

Context safety is sink-specific. At minimum the language distinguishes:

- HTML text, HTML attribute, and HTML script contexts where separately applicable.
- Log and terminal text.
- CSV fields.
- JSON strings and JSON embedded in HTML.
- C string or generated-C source contexts.
- SQL values and SQL identifiers.
- Operating-system executable identity and argument positions.
- Filesystem path policies.

A guarantee for one context MUST NOT be accepted as a guarantee for another. C escaping does not establish HTML safety; CSV escaping does not establish shell-argument safety.

### 3.7 Abstract locations and heap

Let Loc be abstract heap locations. A location may represent a struct allocation site, list allocation site and element region, map allocation site with distinct key and value regions, enum payload, or another reference-bearing object.

The abstract heap is a partial map:

    Heap : Loc x AccessPath -> AVal

Access paths include field names, list element summaries, map key summaries, map value summaries, and nested paths. Implementations MAY use a coarser shape, provided the abstraction is conservative.

Variables of reference type map to sets of possible abstract locations:

    EnvRef : Variable -> P(Loc)

Two variables that may reference the same abstract location MUST observe each other's writes in the abstract heap.

### 3.8 Flow state

A flow state is:

    State {
        locals: Variable -> AVal
        references: Variable -> P(Loc)
        heap: AbstractHeap
        effects: EffectSet
        path_facts: PredicateFacts
    }

Control-flow joins join corresponding local facts, reference sets, heap cells, and effects. A missing heap cell is interpreted as unknown, not as trusted or empty.

## 4. Core invariants

The implementation and its proofs MUST preserve these invariants.

**I1 — No provenance erasure by representation.** Copying, renaming, wrapping, unwrapping, storing, loading, or passing a value cannot remove its provenance.

**I2 — Alias coherence.** Reads and writes through aliases refer to the same abstract heap state.

**I3 — Key/value separation.** Map key provenance and map value provenance are represented separately. A derived key cannot be forgotten merely because its associated value is trusted.

**I4 — Type independence.** Provenance is tracked for every value type, including bool, strings, integers, optionals, enums, and references.

**I5 — Context separation.** Validation and escaping facts are tied to the exact context and predicate they establish.

**I6 — Sound call composition.** A call's return and heap effects account for every actual argument and receiver dependency described by its summary.

**I7 — Conservative unknowns.** Unknown calls, unknown alias relationships, unsupported operations, and abstraction overflow widen conservatively. They MUST NOT default to trusted.

**I8 — Fail-closed resource bounds.** Failure to reach a fixed point, exhaustion of analysis memory, or inability to represent a dependency MUST produce a diagnostic or conservative rejection, never silent acceptance.

**I9 — Stable classification.** Alpha-renaming locals or inserting semantics-preserving temporary variables cannot change a security classification.

**I10 — No implicit declassification.** Only a recognised validator, context-specific encoder, or explicit audited declassification operation may establish a new security guarantee. Ordinary casts and formatting do not.

## 5. Expression transfer semantics

Write eval(e, sigma) = (v, sigma') for evaluation of expression e in abstract state sigma, producing abstract value v and updated state sigma'. For pure expressions, sigma' = sigma. For expressions with mutation, the heap component may change.

The compiler MUST respect the language's specified evaluation order; provenance transfer must not rely on unspecified host-language evaluation order.

### 5.1 Literals and local reads

A literal has no external provenance unless the language explicitly marks it as secret or otherwise sensitive.

A local variable read returns the current abstract value from locals. It does not infer trust from the variable's declared type or spelling.

### 5.2 Assignment and reassignment

For scalar local assignment x = e, evaluate e, then replace locals[x] with its abstract value. This is a strong update to the local binding.

For field or element assignment, update the corresponding abstract heap cell. A strong heap update is permitted only when the target abstract location and access path are known to be unique in the current abstraction. Otherwise use a weak update by joining the new value with the prior cell.

Assignment MUST NOT mark a variable permanently merely because it once held a derived value. Conversely, overwriting a local MUST NOT erase provenance from an object previously stored through an alias.

### 5.3 Arithmetic and bitwise operations

For arithmetic, bitwise operations, shifts, unary numeric operations, and checked or wrapping variants, the result's data provenance is the join of the data provenance of all operands that can influence the result.

A trusted constant operand contributes no provenance. A derived shift count contributes provenance because it affects the result.

Overflow checks do not declassify. A checked operation that may terminate is still data-dependent on its operands; termination channels remain outside the default explicit-flow guarantee.

### 5.4 Comparisons and Boolean operators

Equality, inequality, ordering comparisons, and Boolean operators propagate data provenance from their operands into the resulting Boolean.

Short-circuit evaluation retains the language's evaluation semantics. The Boolean result is still dependent on the operands that determine it.

A Boolean local initialized from a derived comparison MUST retain the resulting provenance through assignment and later reads.

Pure control dependence is not introduced merely because an assignment occurs in one branch. Predicate values themselves remain explicitly data-dependent.

### 5.5 String construction and conversion

Concatenation joins provenance from both operands. Formatting, integer-to-string conversion, Boolean-to-text conversion, character conversion, and generic textual conversion preserve provenance unless a specific context encoder or validator establishes a narrower guarantee.

In particular:

- int_to_str preserves the source provenance of its integer argument.
- to_text preserves the source provenance of its argument.
- char_str preserves provenance and is subject to the reconstruction rule in Section 9.
- join joins provenance from every possible element and the separator.
- Length and other metadata operations are covered by Section 5.9.

No conversion may erase provenance merely because its result has a different static type.

### 5.6 Indexing, field access, and selection

For aggregate[index], the result depends on:

1. The provenance of the selected element or value.
2. The provenance of the index, because it determines which value is observed.
3. Any relevant alias or heap uncertainty.

For object.field, the result inherits provenance from the selected field. If the field selection itself is controlled by an input-dependent dynamic operation, that selection dependency is also retained.

An index into trusted text using an untrusted index is a selection-sensitive operation and MUST be checked against the trusted-text lookup policy. A bounds check does not neutralise the index provenance.

### 5.7 Optional values

An optional value carries the abstract value of its present payload and a presence fact. Assigning it to a local preserves both.

On successful if-let unwrapping, the bound variable receives the payload abstract value. This rule applies whether the optional is a direct expression or a previously stored local.

The presence predicate may itself be data-dependent. Its explicit Boolean observation is tracked; implicit branch dependence remains subject to the default control-flow policy.

### 5.8 Enum construction and pattern matching

An enum constructor retains provenance for each variant payload position. A match binding receives the provenance of the corresponding payload position.

If the scrutinee's variant selection is input-dependent, the match discriminant retains selection provenance. Payload values retain their own data provenance.

A pattern binding MUST NOT become trusted because the payload crossed an enum boundary.

### 5.9 Metadata and aggregate observations

Operations such as len, keys, has, remove, is_empty, iteration counts, and collection membership may reveal information about prior inputs.

The analysis MUST distinguish:

- Data provenance of returned values.
- Selection provenance of the queried key or index.
- Aggregate-shape provenance, which records whether length, membership, or key-set shape may depend on a source.

A policy decision is required for which metadata disclosures are rejected by default. The initial safe profile SHOULD retain these dependencies and reject their use in reconstruction-sensitive sinks, while allowing explicit, documented declassification where disclosure is intended. It MUST NOT silently classify metadata as independent.

### 5.10 Builtins and external operations

Every builtin and standard-library operation MUST have an explicit transfer contract. If an operation has no contract, its result and effects are conservatively unknown.

The contract records:

- Which arguments affect the return value.
- Which arguments affect selection.
- Which arguments mutate which heap paths.
- Which validation or context-safety facts are established.
- Which sinks or external effects are performed.
- Whether the operation can expose secrets or derived metadata.

## 6. Aggregate and heap transfer semantics

### 6.1 Construction

A newly allocated object receives a fresh abstract location when possible. Its fields or elements are initialised with the abstract values of constructor arguments.

For new S{field: e}, each field receives the provenance of its initializer. The object reference itself need not be data-derived merely because a field is; its heap contents are.

For list construction and insertion, each element contributes to the element summary. For map construction and insertion, key and value summaries are distinct.

### 6.2 Aliasing

Reference assignment copies the possible-location set, not the heap contents. If a and b may point to h, writes through either variable update the abstract state visible through both.

When the analysis cannot determine whether two references alias, it MUST conservatively join possible effects across the may-alias set.

### 6.3 Lists

A list abstraction records at least:

- Element provenance.
- Length/shape provenance.
- Reference aliases.
- Whether element positions are distinguishable in the current abstraction.

Push, insert, indexed assignment, removal, pop, clear, and iteration all have specified heap effects. A removed value returned by pop or remove_at inherits the removed element's provenance. The remaining list's element and shape summaries are updated conservatively.

A list containing derived elements remains capable of yielding those elements through any alias. A later clear or overwrite can remove element provenance only where a sound strong update proves the relevant cells no longer contain those values.

### 6.4 Maps

A map abstraction records at least:

- Key provenance.
- Value provenance.
- Key-set/shape provenance.
- Per-entry information where practical.
- Reference aliases.

For set(k, v), key and value dependencies are recorded independently.

For get(k), the optional result depends on the selected stored value and on k as a selector. A derived key selecting a trusted value is a selection-dependent result.

For keys(), the returned list inherits key provenance and key-set shape provenance.

For has(k) and remove(k), the Boolean result inherits key selection provenance and relevant map shape/value facts. Removal additionally updates heap state.

### 6.5 Structs

Struct references are represented by abstract locations. Field writes update heap paths; field reads retrieve the current abstract field value.

Nested fields and aliases MUST be handled transitively. Struct constructor initialisers and subsequent mutations follow the same semantics.

### 6.6 Heap abstraction and widening

The initial implementation MAY use allocation-site abstraction and summary cells for unbounded collections. If multiple concrete objects share one abstract location, writes use weak updates unless uniqueness is proven.

Widening MUST preserve soundness. It may introduce false positives by joining unrelated elements, but it must never discard a possible dependency.

## 7. Interprocedural summaries

### 7.1 Summary structure

A function summary MUST describe more than whether its return is derived.

A conceptual summary is:

    FunctionSummary {
        return_dependencies: DependencyRelation
        heap_effects: List<HeapEffect>
        selection_dependencies: DependencyRelation
        sink_effects: List<SinkEffect>
        validation_effects: List<ValidationEffect>
        context_effects: List<ContextEffect>
        external_effects: EffectSet
    }

A dependency endpoint identifies a parameter and a path within it. The receiver self is an ordinary explicit parameter for summary purposes.

### 7.2 Return dependencies

For every parameter, the summary records whether and how its value or subpaths may influence the return value. This applies to all parameter types, including strings, Booleans, structs, lists, maps, enums, optionals, and references.

A function returning a field from a struct parameter must preserve the field-path dependency. A function returning an element from a list parameter must preserve the element dependency and any index selection dependency.

### 7.3 Heap mutation effects

The summary records writes through each parameter and receiver, including the source dependencies of the written values.

At a call site, actual arguments are substituted into the summary. The caller's abstract heap is updated for all possible target locations.

This is necessary for helper functions that mutate a list, map, or struct passed by reference.

### 7.4 Sink effects

If a function sends an argument or a value derived from it to a sensitive sink, the summary records the parameter paths responsible. At call sites, the checker applies the sink contract to the corresponding actual arguments.

### 7.5 Recursive and mutually recursive functions

Summaries are solved over the call graph. Strongly connected components SHOULD be processed as units using a monotone worklist algorithm.

The analysis MUST terminate through a finite abstract domain and explicit widening. A hard iteration cap MAY remain as a safety guard, but reaching it MUST produce a diagnostic and MUST NOT permit compilation under an incomplete summary set.

### 7.6 Unknown and external functions

A function without an available body or trusted summary receives a conservative contract. The contract MUST NOT claim that arguments are independent of the return or that the function has no heap effects unless that has been established by an explicit trusted declaration.

Externally supplied summaries are part of the trusted computing base and require versioning, review, and tests.

## 8. Policies and authorization

Policies are Boolean-returning functions, but their Boolean result and effects must be analysed like any other function.

A policy summary MUST include:

- Data dependencies of the decision result.
- Dependencies on every parameter and receiver path.
- Heap reads and writes.
- External effects.
- Calls to other policies and ordinary functions.
- Validation facts, if any.

Policy parameters MUST be seeded during summary analysis. At authorize P(args), the summary is instantiated with the actual arguments.

Policies SHOULD be pure predicates. The language SHOULD reject mutation and external side effects in policies, including transitive effects through helper calls. If purity is not enforced, the language must explicitly specify repeated evaluation, side-effect ordering, and failure behaviour; silent reliance on predicate semantics is unacceptable.

The re-evaluation of a policy when a grant is checked MUST use the same abstract policy semantics. Provenance analysis does not replace grant identity, object binding, or runtime recheck validation.

## 9. Sensitive operations and sinks

### 9.1 Reconstruction from untrusted bytes

The existing Capstan rule against rebuilding trusted text from individual untrusted bytes remains a distinct policy.

A byte extracted from Tainted retains its source provenance. Numeric conversion, storage in a collection, retrieval through an alias, helper calls, enum payloads, optional locals, or Boolean tests do not erase it.

A char_str operation on a value whose provenance indicates reconstruction from untrusted bytes MUST be rejected unless a specific, reviewed declassification or validation rule applies.

The policy must also account for lookup-based reconstruction: using an untrusted key or index to select trusted text can reconstruct attacker-controlled output even if the selected text itself is a literal.

### 9.2 Context-specific encoders

Each encoder establishes only its documented context guarantee. It does not erase origin provenance.

For example:

- escape_html establishes HTML-context safety.
- escape_log establishes log/terminal safety.
- escape_csv establishes CSV-field safety under its documented formula-injection policy.
- escape_json establishes JSON-string safety under its documented embedding contract.
- escape_c establishes generated-C string-literal safety, not HTML safety.

The type system SHOULD expose distinct result types where this materially prevents accidental cross-context use. The compiler MUST reject composition or sink use that invalidates a context guarantee.

### 9.3 Validators

A validator establishes a predicate-specific certificate on its successful result. It does not generally make the original input trusted for all purposes.

For example, successful validate_ident may permit use as an identifier where the identifier grammar is sufficient. It does not permit use as HTML, shell syntax, or a filesystem path unless those policies are independently satisfied.

### 9.4 Explicit declassification

trust(value, reason) is an explicit declassification boundary. It MUST:

- Require the declared justification form.
- Emit an audit diagnostic.
- Preserve an audit record linking the declassification to its source provenance.
- Be visible to code review and assurance tooling.
- Avoid silently conferring unrelated context-safety or confidentiality guarantees.

The operation is a deliberate escape hatch, not proof that the justification is correct.

### 9.5 Secrets and confidentiality

Secret provenance is distinct from untrusted-input provenance. Operations on secrets must obey secret-handling rules even when their values are not attacker-controlled.

A secret-derived Boolean may reveal a predicate about a secret. The policy for permitted predicates (for example, password verification) must be explicit. Constant-time runtime implementation and compiler-level information-flow policy are separate obligations.

## 10. Control-flow policy

The default mode tracks explicit data and selection dependencies. It does not automatically mark every constant assigned under a data-dependent branch.

The analysis MUST nevertheless preserve provenance in:

- The Boolean predicate itself.
- Values explicitly computed from that predicate.
- Values selected through data-dependent indexes, map keys, or lookup operations.
- Aggregate values whose contents are explicitly mutated from derived values.

A strict mode MAY introduce a program-counter provenance component. In that mode, assignments and heap writes under a derived predicate inherit control provenance. The strict mode must specify treatment of validation, sanitisation, declassification, loops, panics, and termination.

The default and strict modes must have separate tests and documented guarantees.

## 11. Control-flow joins, loops, and fixed points

At a control-flow join, the analysis joins all reaching states. A fact is retained if it may hold on any incoming path.

Loops are analysed to a fixed point. The implementation SHOULD use a worklist over control-flow graph blocks rather than repeatedly traversing the entire syntax tree.

Widening is permitted only where it preserves the may-dependence over-approximation.

If a fixed point cannot be reached within a configured resource limit, the compiler MUST reject the compilation with a stable, actionable diagnostic.

## 12. Soundness obligations

The intended soundness statement is:

> For every accepted program, every concrete execution represented by the abstract semantics is covered by the abstract provenance state at each analysed program point; therefore no prohibited explicit data- or selection-dependent flow to a protected sink is omitted by the analysis.

This statement is conditional on correctness of the parser, type checker, lowering, builtin contracts, external summaries, and trusted compiler implementation. It is not a proof of whole-program noninterference or runtime memory safety.

A mechanised proof programme SHOULD establish:

1. **Expression preservation:** abstract evaluation over-approximates concrete data and selection dependencies.
2. **Assignment preservation:** local and heap updates preserve the dependency relation.
3. **Alias preservation:** may-alias writes are reflected in all possibly aliased reads.
4. **Call preservation:** summary instantiation over-approximates concrete callee behaviour.
5. **Join preservation:** control-flow joins over-approximate every incoming execution.
6. **Widening preservation:** widening cannot remove possible dependencies.
7. **Sink soundness:** if a concrete prohibited dependency reaches a sink, the abstract sink check rejects or requires explicit declassification.
8. **Fail-closed termination:** analysis failure cannot produce an accepted result based on partial facts.

A proof of these lemmas does not establish the correctness of a validator's business predicate or the absence of covert channels excluded from the model.

## 13. Required adversarial test programme

The test programme MUST contain both negative and positive cases. Each negative case is a program expected to be rejected; each positive case is a program expected to compile and preserve the documented guarantee.

### 13.1 Scalar and conversion cases

- Integer arithmetic from a tainted byte.
- Boolean equality, inequality, ordering, and compound Boolean expressions.
- Boolean values stored and reassigned through locals.
- int_to_str, to_text, char_str, and join.
- Length and other metadata observations.
- Multiple independent taint sources combined into one result.

### 13.2 Aggregate and alias cases

- List insertion, replacement, removal, pop, clear, and read.
- Direct, chained, and parameter-passed aliases.
- Mutation through one alias followed by read through another.
- Map derived keys with trusted values.
- Map trusted keys with derived values.
- keys, get, has, remove, and membership.
- Nested lists, maps, and structs.
- Struct constructor initialisers and later field writes.
- Enum payload construction and pattern binding.
- Stored optional followed by unwrapping.

### 13.3 Interprocedural cases

- Every supported parameter type as a source of return dependence.
- Every supported parameter type as a source of sink dependence.
- Aggregate mutation through helper functions.
- Receiver self read and mutation effects.
- Direct recursion and mutual recursion.
- Long dependency chains.
- Helpers that return, store, select, validate, encode, and declassify values.

### 13.4 Context and policy cases

- Every encoder used in its intended context.
- Every encoder used in an unintended context (must reject).
- Validator success and failure branches.
- Validator result stored in an optional local.
- Policy parameter dependence and helper-mediated dependence.
- Policy mutation and external effects.
- Explicit declassification with audit evidence.

### 13.5 Metamorphic properties

The following transformations MUST preserve security classification where semantics are equivalent:

- Alpha-renaming local variables.
- Introducing or removing a temporary local.
- Extracting an expression into a helper with equivalent semantics.
- Passing an aggregate through an additional alias.
- Moving an aggregate mutation into a helper.
- Storing an optional before unwrapping it.
- Reordering independent declarations.
- Replacing a direct field read with an equivalent method call.

A metamorphic test harness SHOULD generate bounded variants automatically.

## 14. Migration plan

The implementation should proceed in independently reviewable stages.

### Stage A — Specification and inventory

- Ratify the abstract domains and sink policy.
- Inventory every expression, statement, builtin, method, and external operation.
- Map existing TYPE findings to the new transfer rules.
- Establish baseline positive and negative tests.

### Stage B — Scalar value provenance

- Replace variable-name Boolean marks with per-value abstract facts.
- Add Boolean, conversion, comparison, and metadata propagation.
- Preserve current sink behaviour while adding new regression cases.

### Stage C — Heap and aliases

- Introduce abstract locations and reference sets.
- Add field-, element-, key-, and value-sensitive aggregate state.
- Add alias and nested-aggregate tests.

### Stage D — Interprocedural effects

- Introduce general parameter-path summaries.
- Add return, sink, receiver, and heap-write dependencies.
- Solve summaries using a call-graph worklist and SCC processing.
- Add recursive and mutually recursive tests.

### Stage E — Policy and context contracts

- Add policy summaries and policy-parameter seeding.
- Define and enforce policy purity, or explicitly specify its alternative.
- Audit all validators, encoders, declassification operations, and sinks.

### Stage F — Formal verification and assurance

- Mechanise the abstract domains and transfer functions.
- Prove the soundness obligations in Section 12.
- Differentially test the implementation against a small executable reference semantics.
- Run compiler acceptance/rejection suites, fuzzing, stage-0 differential checks, and sanitiser campaigns.
- Update CWE coverage claims only after evidence exists.

No stage should silently weaken an existing rejection guarantee. If a temporary implementation limitation requires conservative rejection, that is preferable to unsound acceptance.

## 15. Mapping of existing findings

This table maps the currently identified provenance findings to the target semantics. It is a design mapping, not a claim that the defects have been fixed.

| Finding | Required rule |
|---|---|
| TYPE-01 context escaper laundering | Sections 3.6, 9.2 |
| TYPE-02 aggregate parameter summaries | Sections 7.1–7.3 |
| TYPE-03 aliases | Sections 3.7, 6.2 |
| TYPE-04 interprocedural aggregate mutation | Sections 7.1, 7.3 |
| TYPE-05 to_text | Sections 5.5, 5.10 |
| TYPE-06 join | Sections 5.5, 5.10 |
| TYPE-07 tainted length | Sections 5.9, 10 |
| TYPE-08 comparison Boolean | Sections 5.4, 10 |
| TYPE-09 Boolean locals | Sections 3.4, 5.4 |
| TYPE-10 derived map keys | Sections 6.4, 5.9 |
| TYPE-11 scalar string parameters | Sections 7.1–7.2 |
| TYPE-12 map membership/removal | Sections 5.9, 6.4 |
| TYPE-13 stored optionals | Sections 5.7, 13.2 |
| TYPE-14 struct constructor fields | Sections 6.1, 6.5 |
| TYPE-15 collection size | Section 5.9 |
| TYPE-16 receiver provenance | Sections 7.1–7.3 |
| TYPE-17 enum payloads | Sections 5.8, 6 |
| TYPE-18 map value retrieval | Sections 5.9, 6.4 |
| TYPE-20 policy parameter provenance | Section 8 |
| TYPE-21 policy purity | Section 8 |

TYPE-19 remains withdrawn as a false positive and is intentionally absent.

## 16. Compatibility and open design decisions

The following decisions require explicit review before implementation is considered stable:

1. **Default metadata disclosure:** which length, membership, and shape dependencies should be rejected by default, and which may be explicitly declassified?
2. **Heap precision:** allocation-site abstraction versus more precise object sensitivity; acceptable false-positive rate and memory cost.
3. **Context types:** whether CSV, JSON, C, SQL identifier, and other contexts receive distinct nominal types or compiler-maintained context certificates.
4. **Validator contracts:** which standard-library validators produce which predicate certificates, and how user-defined validators can be trusted or verified.
5. **Control dependence:** whether strict information-flow mode is required for a release target.
6. **Policy purity:** mandatory purity versus fully specified repeated side effects. Purity is strongly preferred.
7. **External summaries:** format, trust root, version binding, and review process.
8. **Incremental compilation:** invalidation rules for summaries when a function or builtin contract changes.

These are specification decisions, not reasons to postpone the core provenance model.

## 17. Acceptance criteria for the redesign

The redesign is ready for implementation review when:

- Every language expression and statement category has a transfer rule or an explicit conservative fallback.
- Every builtin and standard-library operation has a reviewed contract.
- The abstract domains and joins are defined precisely enough to implement.
- Aliases and aggregate mutation are represented.
- All parameter types and receiver paths participate in summaries.
- Policy parameters and effects are covered.
- The adversarial and metamorphic tests are committed.
- Existing security guarantees have been mapped to explicit rules.
- The soundness theorem and proof obligations have a mechanisation plan.
- The implementation plan preserves fail-closed behaviour.

**Final status:** This document defines a proposed semantic target. It is not evidence that the current compiler meets that target. Implementation, tests, and mechanised proofs remain separate deliverables.


## 18. Abstract-domain formalisation companion

The concrete path, symbolic-origin, dependency-kind, lattice, and summary-substitution definitions are refined in [PROVENANCE-ABSTRACT-DOMAIN.md](PROVENANCE-ABSTRACT-DOMAIN.md). That addendum is part of this proposal and should be reviewed together with this document. In particular, the dependency lattice is a may-analysis, while validation and context certificates are must-facts; their join operators therefore have opposite polarity.
