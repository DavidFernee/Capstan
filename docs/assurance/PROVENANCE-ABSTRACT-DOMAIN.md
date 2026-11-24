# Capstan Provenance — Abstract Domain and Transfer-Rule Addendum

**Status:** Formalisation companion to PROVENANCE-SEMANTICS.md  
**Purpose:** Refine the provenance relation, lattice, path model, and summary substitution before implementation.

This addendum refines the conceptual domains in the parent specification. It is a proposed design, not a proof or a description of the current checker.

## 1. Paths and symbolic origins

### 1.1 Access paths

The finite access-path alphabet contains:

- Field(f)
- Element(i), for a known constant index
- AnyElement, for an unknown or summarised list position
- MapKey(k), where k is a known abstract key
- AnyMapKey
- MapValue(k)
- AnyMapValue
- OptionalPayload
- EnumPayload(variant, position)
- Length
- KeySet
- VariantTag

A path is a finite sequence of selectors. The empty path denotes the whole value.

The implementation may collapse paths using a finite abstraction. For example, all non-constant list indices may map to AnyElement. Path collapse is a widening and must over-approximate the collapsed paths.

### 1.2 Symbolic origins

During function-summary analysis, origins are symbolic rather than concrete call-site sources:

- Param(i, p): path p of formal parameter i.
- Fresh(site): a source introduced within the function at source site site.
- Global(g, p): path p of global or externally visible state g.
- UnknownOrigin: an unknown source.

At a call site, Param(i, p) is substituted with the abstract provenance of actual argument i at path p. The receiver is treated exactly like every other formal parameter.

For a top-level body analysis, taint-producing expressions introduce concrete analysis-local source identities. The identity is associated with the expression/source site, not a local variable name. Secret sources additionally carry confidentiality facts.

### 1.3 Dependency atoms and kinds

A dependency atom is a pair:

    OriginPath = (Origin, AccessPath)

A dependency fact is:

    DepFact = (OriginPath, DepKind)

where DepKind is one of:

- Data
- Selection
- Shape
- ExplicitPredicate

ExplicitPredicate is used for a Boolean value computed from an input-dependent comparison or predicate. It is not implicit program-counter dependence.

A provenance relation is a finite set of DepFact values, or TopDep if the configured bound is exceeded.

The distinction between dependency kinds is semantically significant. A sink may reject Selection dependence even where the selected value itself has no Data dependence on the selector.

## 2. Abstract value and lattice

An abstract value is:

    AVal = {
      deps: Dep,
      confidentiality: Conf,
      validations: Set(ValidationCertificate),
      contexts: Set(ContextCertificate),
      shape: Shape
    }

The dependency lattice is the powerset lattice:

    D1 <= D2 iff D1 is a subset of D2
    D1 join D2 = D1 union D2

TopDep denotes every dependency representable by the implementation's finite universe. It is not equivalent to an empty set.

Confidentiality is an independent lattice. A minimal domain is:

    Public <= SecretDerived <= UnknownConfidentiality

The exact ordering may be refined, but joins must never downgrade a possible secret to Public.

Validation and context certificates are must-facts: a certificate is retained at a control-flow join only if it is valid on every incoming path. Therefore:

    CertJoin(C1, C2) = C1 intersection C2

This is deliberately the opposite polarity from may-dependencies. A value is context-safe after a join only if every possible incoming value is safe in that context.

Shape is a may-abstraction and joins by union/widening. An unknown shape is not treated as empty or trusted.

## 3. Transfer rules

Write D(v) for the dependency relation of abstract value v. Let join denote dependency union.

### 3.1 Constants and copies

A literal has empty dependencies unless it is explicitly declared secret or otherwise source-bearing.

A copy preserves all components:

    D(copy(x)) = D(x)

A cast, wrapper, unwrap, or ordinary formatting operation also preserves dependencies unless its specific contract states otherwise.

### 3.2 Unary and binary operations

For a unary operation whose result is computed from operand x:

    D(op(x)) = D(x)

For a binary operation whose result is computed from operands x and y:

    D(op(x, y)) = D(x) join D(y)

For a comparison, relabel the contributing dependency kind as ExplicitPredicate while retaining origin paths:

    D(compare(x, y)) =
      relabel(D(x), ExplicitPredicate)
      join relabel(D(y), ExplicitPredicate)

This relabelling means the Boolean result explicitly represents a predicate of its inputs. It does not mean the analysis tracks subsequent implicit branch effects.

A conditional expression is treated as a selection operation: its result depends on the condition as Selection, and on both possible branch values as Data, unless path-sensitive facts prove one branch unreachable.

### 3.3 Field and element reads

For a read from abstract location set L at path p:

    D(read(L, p)) =
      join over l in L of Heap[l, p].deps
      join selector dependencies

For a constant field name, selector dependencies are empty. For an input-dependent index i:

    selector dependencies = relabel(D(i), Selection)

If a location or path is unknown, the read includes the corresponding unknown heap dependency. It must not default to empty dependencies.

### 3.4 Aggregate writes

For a write of value v to location set L at path p:

- If L contains exactly one uniquely identified abstract location and p is strongly updateable, replace that abstract cell.
- Otherwise weakly update each possible cell:

    Heap'[l, p].deps = Heap[l, p].deps join D(v)

For list insertion, the element cell receives D(v), and the Length/Shape cell receives the dependencies controlling whether insertion occurs and which position is affected.

For map insertion of key k and value v:

    Heap'[l, AnyMapKey].deps  includes D(k)
    Heap'[l, AnyMapValue].deps includes D(v)
    Heap'[l, KeySet].deps includes relabel(D(k), Shape)

The key and value facts must never be collapsed into one undifferentiated bit if doing so would make a later operation appear independent of a key.

### 3.5 Map operations

For get(k):

    D(result payload) =
      D(selected map value)
      join relabel(D(k), Selection)

For keys():

    D(result elements) = D(map key paths)
    D(result Length/Shape) = D(map KeySet/Shape)

For has(k):

    D(result bool) =
      relabel(D(k), ExplicitPredicate)
      join relabel(D(map KeySet), ExplicitPredicate)

For remove(k):

    D(result bool) =
      relabel(D(k), ExplicitPredicate)
      join relabel(D(map KeySet), ExplicitPredicate)

Removal also applies the corresponding abstract heap update. If the implementation cannot determine whether a particular key was removed, it weakly updates the possible entries.

### 3.6 Optional and enum operations

An optional value stores the payload AVal at OptionalPayload and a presence predicate dependency separately.

Successful optional unwrapping transfers the payload AVal without dropping dependencies or must-certificates.

An enum constructor stores each argument at EnumPayload(variant, position). A pattern binding reads exactly the matching payload path. The variant tag is a separate path and may carry selection or explicit-predicate dependencies.

### 3.7 Length and shape

For list length:

    D(len(list)) = relabel(D(list.Length), ExplicitPredicate)

The implementation may classify this as Shape rather than ExplicitPredicate, but the fact must remain distinguishable from element data. Map size, key-set observation, and emptiness tests follow the same principle.

Whether a particular sink rejects Shape dependence is a policy choice. The analysis must preserve the fact so that policy can make that choice.

## 4. Heap and alias transfer

The reference environment maps each reference variable to a set of abstract locations. Assignment of a reference copies that set.

If two variables have intersecting location sets, they may alias. A write through either variable updates the shared abstract heap cells. The analysis must not maintain independent per-variable copies of aggregate provenance.

An allocation-site abstraction may merge multiple concrete allocations. In that case, writes are weak unless the analysis proves that the abstract location denotes one concrete object at that program point.

When points-to information is unknown, reads and writes widen to an unknown heap region. The fallback is conservative, even if that causes false positives.

## 5. Function summaries and substitution

A function summary maps symbolic input paths to output and effect paths:

    Summary = {
      return: Relation(ParamPath, ReturnPath, DepKind),
      heap_writes: Relation(ParamPath, FormalHeapPath, WrittenPath, DepKind),
      sinks: Relation(ParamPath, SinkId, DepKind),
      validations: Relation(ParamPath, ReturnPath, ValidationCertificate),
      contexts: Relation(ParamPath, ReturnPath, ContextCertificate),
      effects: EffectSet
    }

For a call f(a0, ..., an), instantiate each Param(i, p) by reading the abstract value of actual argument ai at path p. The receiver is substituted identically to any other argument.

The instantiated return dependencies are joined with dependencies introduced inside the callee. Heap-write effects update caller heap locations reachable from the corresponding actual reference arguments. Sink effects are checked at the call site using the actual argument's abstract value.

A summary that cannot resolve an argument path, heap path, or effect must widen to unknown. It must not omit that relation.

## 6. Fixed-point and termination requirements

The domains are finite after bounding source identities, path depth, abstract locations, and certificate parameters. Every bound requires a sound top/widening element.

The summary solver and intraprocedural solver must be monotone over their respective lattices. Strong updates are allowed only under a proof of uniqueness; otherwise use weak updates.

A solver may stop when the state is unchanged. If an implementation-specific iteration or memory budget is reached before convergence, compilation must fail closed with a diagnostic. It is unsound to run sink checks against partial summaries.

## 7. Consequences for implementation review

An implementation claiming conformance must demonstrate at least:

1. Dependency facts for every scalar type, not just int/string.
2. Separate key, value, and shape paths for maps.
3. Payload paths for optionals and enums.
4. Heap location sharing across aliases.
5. Path-sensitive parameter and receiver substitution.
6. Must-join semantics for validation and context certificates.
7. Conservative unknown handling and fail-closed widening.
8. Tests showing both rejection of unsafe flows and acceptance of valid context-encoded or validated flows.

This addendum makes the proposed abstract domain more precise. It does not resolve product-policy questions such as the default rejection of length or shape disclosures; those remain explicit review decisions in the parent specification.
