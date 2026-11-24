# Type-system assurance and acceptance matrix

**Status:** contributor test plan; not a language specification or proof  
**Baseline inspected:** `main` at `7f057a5b1cda749e44baaab7d6cc8f30d9adff0c` (2026-11-24)  
**Related design:** [v0.5 generics, interfaces and closures proposal](V0.5-DESIGN.md), PR #49  
**Purpose:** make the type-system claims testable, distinguish existing guarantees from proposed ones, and prevent generic implementation from weakening established security checks.

This document records a test strategy. A row marked **required** is an acceptance gate for the relevant feature, not a claim that the test or feature already exists. Passing tests provide evidence, not a mechanically checked proof of soundness.

## 1. Current baseline: what is implemented

The current front end uses a recursive `Type` value with a kind, optional name and recursively nested type arguments. `type_eq` is structural; `assignable` accepts exact equality and lifting a value into an optional of that exact type. The checker has no general type variables, substitution environment, user-defined generic declarations, interface constraints or trait solver.

Current built-in type constructors include `List<T>`, `Map<T>`, `Grant<P>` and `T?`. The language specification describes these built-ins; their presence is not evidence that user-defined generics exist.

| Existing invariant | Current enforcement point | Existing test evidence / coverage |
|---|---|---|
| Exact structural type equality; no subtyping or variance | `compiler/ast.cap: type_eq, assignable` | `tests/diagnostics/type_mismatch.cap`, `tests/diagnostics/compare_different_enums.cap` and type-specific diagnostics |
| Optional values are explicit; no nested optionals; no optional collection elements | `compiler/checker.cap: check_type` | `tests/diagnostics/nested_optional.cap`, `tests/diagnostics/void_optional.cap`, `tests/reject/optional_*.cap` |
| Tainted input cannot be assigned to trusted string without validation/escaping | `mismatch`, `expect_type`, sink checks | `tests/reject/tainted_as_trusted.cap`, `tests/reject/taint_char_trusted.cap`, `tests/reject/tainted_into_html.cap` |
| Secret is not printable or coercible to ordinary text | `mismatch` and secret-specific expression/sink checks | `tests/reject/secret_*.cap`, `tests/reject/hash_of_secret.cap` |
| Context-escaped text cannot be used as ordinary trusted string | `mismatch`, contextual sink checks | `tests/reject/tainted_into_html.cap` and HTML/log-specific conformance and rejection tests |
| Grants cannot be stored in ordinary fields, enums, collections or constants, and cannot be returned | `contains_grant`, `check_type`, `check_fn`, `check_program` | `tests/reject/grant_in_collection.cap`, `grant_stored.cap`, `grant_returned.cap` |
| Protected calls require a matching grant; policy arguments remain role-bound | `check_call`, `check_fn`, runtime re-check | grant diagnostics/rejection tests and `tests/unit/grant_reference.py` |
| Enum matches reject optional values and require exhaustive variants unless there is a final `else` | `check_match` | `tests/reject/match_not_exhaustive.cap`, `tests/reject/match_optional.cap`, match diagnostics |
| Unknown names and malformed type usage produce compiler diagnostics before code generation | parser and checker | `tests/diagnostics/`, `tests/recovery/` |
| Imported source files are loaded into one declaration set; imports are path-restricted | `compiler/main.cap` | import/path tests; this is not yet the proposed public/private module model |

### Baseline caveats

- The current type representation is structurally recursive but does not define a general recursive-type or generic-instantiation algorithm.
- `contains_grant(Type)` recursively examines explicit type arguments. Named structs are separately validated field-by-field today. Once generic wrappers exist, the checker must inspect the fully substituted concrete structure; it must not assume that checking only the outer type name is sufficient.
- The current import loader flattens declarations into a shared compilation input. It is not yet a separate compilation/link model with exported interfaces or independently compiled module metadata.
- The existing suite has broad negative coverage, but that does not establish that every path through a future substitution engine is covered.

## 2. Generic implementation acceptance matrix

The following gates apply to the implementation stages in PR #49. Each security-sensitive rejection needs at least one negative test. Each positive test should prove that the feature remains usable and that the test is not merely rejected for an unrelated reason.

| Area | Required positive tests | Required negative/adversarial tests | Acceptance condition |
|---|---|---|---|
| Type parameters and parsing | Explicit type arguments; nested arguments such as `Map<List<T>>`; adjacent `>>` shift tokens remain unambiguous | Unknown parameter, duplicate parameter, wrong arity, malformed nested arguments, type parameter out of scope | Parser and resolver produce one unambiguous resolved type tree |
| Substitution | Substitute a parameter at every nested occurrence in fields, arguments, returns and enum payloads | Missing substitution, extra argument, wrong kind/arity, unresolved variable | Substitution is total for a well-formed instantiation and never leaves a free type variable |
| Invariance and assignability | Exact `Box<int>` to `Box<int>`; explicit optional lift where specified | `Box<int>` to `Box<string>`; `Box<Tainted>` to `Box<string>`; accidental covariance/contravariance | Only exact substituted arguments are assignable; existing optional rule remains unchanged |
| Security qualifier preservation | Generic identity/wrapper preserves `Tainted`, `Secret`, `Html` and `LogText` exactly | Attempt to pass substituted `Tainted` to trusted sink; print/interpolate/hash a substituted `Secret`; use `Html`/ `LogText` in wrong context | Substitution, inference, method lookup and monomorphisation preserve all security-relevant type kinds |
| Grant containment | Generic values with no grants instantiate normally | `Box<Grant<P>>`, nested `List<Box<Grant<P>>>`, generic enum payload, optional/wrapper nesting, return/storage/constant/capture through a type parameter | Every storage, return and capture prohibition is applied after substitution and recursively |
| Generic function inference | One uniquely inferred solution; explicit type arguments; nested argument constraints | Unused type parameter, ambiguous solution, inconsistent arguments, inference that would widen `Tainted` or `Secret` | Inference succeeds only when there is exactly one solution under invariant equality |
| Constraint checking | A declared interface implementation satisfies every required signature | Missing method, wrong parameter/return type, visibility mismatch, method with same name but no declared impl | Generic bodies can use only operations justified by declared constraints |
| Coherence | One implementation; repeated use of same resolved implementation | Duplicate impl in one file, duplicate across imports, overlapping concrete or parameterised impl heads, unconstrained impl parameters, reverse import order | At most one applicable implementation exists across the complete compilation/link unit; source order cannot select a winner |
| Module visibility | Public generic declaration over public types; private helper used inside its defining module | Access private declaration through alias, nested type, generic bound, interface, enum variant or re-export; public signature exposes private type | Visibility is checked at every reference and over all public signature components |
| Recursive data types | Stable recursive shape such as `Node<T> { List<Node<T>> children; }`; ordinary recursive function | Infinite type expansion; unguarded or malformed recursion if disallowed by representation | Stable recursion is accepted; expanding instantiation is rejected with a bounded diagnostic |
| Instantiation termination | Finite mutually recursive templates with stable arguments | `F<T> -> F<List<T>>`; mutually expanding `A<T> -> B<List<T>> -> A<List<List<T>>>` | Cycle detection distinguishes same-instantiation recursion from strictly expanding arguments |
| Resource bounds | Near-limit valid instantiation set; deterministic repeated builds | Many templates each below per-template cap but above global cap; deeply nested substituted types; aggregate node/work explosion | Hard global budgets cover count, depth, substituted-type size and total work; over-budget builds fail before code generation |
| Generic enum matching | Exhaustive match over concrete generic enum payloads; payload bindings have substituted types | Missing/duplicate/unknown variant; wrong payload arity; optional scrutinee; payload type confusion | Exhaustiveness and payload binding checks operate on the concrete instantiated enum |
| Diagnostics | Stable, source-located errors include template and concrete arguments | Same invalid program under reversed import/declaration order; multiple independent invalid instantiations | Diagnostic category and meaning are stable; no partial C is emitted |
| Bootstrap and backends | Stage-0 and self-hosted compiler agree; generated C builds under GCC and Clang | Divergence under bootstrap, `-O0`, `-O2`, `-O3`, sanitizers or strict C warnings | Same acceptance/rejection and program behaviour across supported compiler paths |

## 3. Interface coherence and module identity

PR #49 currently says a type/interface pair has at most one implementation in a compilation unit. That statement needs a precise boundary before implementation.

Recommended initial rule:

**Compilation-unit boundary:** for the current source-import model, one compilation unit is the root source plus the transitive closure of its imports after canonical source deduplication. Every implementation in that closure participates in one coherence check, even when the defining source is not directly imported by the root. Separate compiler invocations are separate units unless a future package/link model explicitly combines them; that future boundary must repeat the uniqueness check before executable output is produced.

1. An `impl Interface for Type` must be declared in the module defining either `Interface` or `Type` (an orphan restriction).
2. The compiler collects implementation identities across all transitively imported modules before resolving constrained generic calls.
3. Two implementations for the same resolved pair are an error, including when they originate in separate files or are imported through different paths.
4. Import order, declaration order and file traversal order cannot affect the selected implementation.
5. There is no blanket or overlapping implementation in the initial language subset.
6. A public implementation cannot expose a private interface or implementing type through a public signature.

Required fixtures should include a three-module diamond import, two modules independently implementing the same pair, and an import-order permutation. If Capstan later supports separately compiled modules, the same uniqueness rule must be enforced at the link/package boundary; per-file checks alone are insufficient.

The orphan rule must be evaluated using resolved `DeclId` ownership, not matching short names. Two modules that each declare a type named `Widget` define different nominal types; an implementation of an interface for one must not satisfy a constraint on the other. Conversely, duplicate implementations for the same resolved pair must be rejected even if the source files are reached through different import paths that canonicalize to the same module.

## 4. Recursive types versus expanding instantiation

These are different problems and must have different compiler rules.

- **Stable recursive type:** `Node<T>` contains `List<Node<T>>`. The type constructor and its argument are unchanged by the recursive edge. This is ordinary recursive data and should be accepted if the runtime representation supports it.
- **Expanding instantiation:** while checking `F<T>`, the compiler requests `F<List<T>>`, then `F<List<List<T>>>`. The argument grows at each step. This must stop under a deterministic instantiation budget, preferably with an early expansion-cycle diagnostic.
- **Mutual expansion:** `A<T>` requests `B<List<T>>`, which requests `A<List<List<T>>>`. Detection must span the instantiation stack, not just direct self-calls.
- **Ordinary recursive function:** `f<T>` calls `f<T>`. This is runtime recursion, not new type instantiation, and must not be rejected as an expanding type cycle.

Tests must assert both acceptance of stable recursion and rejection of expansion. A single generic “cycle detected” flag is not an adequate algorithm.

## 5. Resource accounting

The proposed per-template limit (256) and depth limit (32) are useful local guards but do not bound total compilation work. Before enabling arbitrary instantiation, the compiler should maintain deterministic, compilation-wide counters:

- number of distinct concrete instantiations;
- maximum active instantiation depth;
- aggregate nodes (or a conservative byte estimate) in substituted types and generated checked representations;
- a deterministic work counter for substitution, constraint resolution and type checking.

Each counter needs a hard ceiling that cannot be disabled by a user flag. If configurable limits are later exposed, configuration may lower a ceiling but must not raise it above the compiler's hard safety maximum. The failure must be an ordinary diagnostic, emitted before code generation, not a stack overflow, allocator failure or process abort.

Stress tests should generate inputs immediately below, at and above each limit. Also test many individually small templates to ensure the global budget, rather than only per-template budgets, is effective. Repeat the same source with declaration and import order permuted and require the same limit decision.

## 6. Security preservation rules

The generic checker must preserve these invariants at every boundary:

- **Taint:** a type variable inferred from `Tainted` remains `Tainted` in every substituted occurrence. No generic helper, interface method, collection operation or wrapper may make it assignable to trusted `string`.
- **Secrets:** `Secret` remains non-printable and non-interpolable after substitution. Generic formatting, equality, hashing and interface dispatch must not create an alternate route to reveal it.
- **Contextual escaping:** `Html` and `LogText` remain context-specific. Substitution cannot erase the output context or make an escaped value a general trusted string.
- **Grants/capabilities:** grant-containing types remain non-storable, non-returnable and non-capturable, including through nested generic types and aliases. Protected-call checks must survive static interface dispatch.
- **Type-level invariants:** concrete instantiation must re-check struct/enum field constraints and method contracts. A template's unchecked body is never sufficient evidence for a concrete instantiation.
- **No codegen before checking:** no unresolved type variable, failed constraint, ambiguous impl or over-budget instantiation reaches C generation.

These are semantic requirements. They are not satisfied merely because the generated C compiles or because a positive example runs.

## 7. Closures and secret lifetime (dependent feature)

Closure acceptance depends on generic and type metadata, but closure-specific runtime checks are separate:

- Capture set equals the free-variable set: no omitted or accidental capture.
- Captured scalar binding is a snapshot; copying a reference copies the pointer, not the object. Mutation through another alias remains observable.
- A captured heap object remains reachable after the creating frame returns, including nested closures and objects reachable through containers.
- A grant cannot be captured directly or through a generic wrapper.
- If secret capture is allowed, test every copy and every environment reclamation path. A tracing collector's eventual collection is not a prompt-erasure guarantee; documentation must not claim deterministic erasure unless the runtime provides it.
- Closure environments must be included in heap/resource accounting.

## 8. Test execution and release evidence

For each implementation PR:

1. Add focused parser, checker, rejection and positive conformance fixtures with the feature.
2. Run the smallest relevant test sections locally and record exact commands and results.
3. Run the full standard suite: `tests/run.sh`.
4. Run `tests/run.sh --full` before declaring the feature release-ready; this includes coverage, mutation and benchmark gates.
5. Verify bootstrap fixpoint and compiler self-check (`--strict`).
6. Verify generated C with GCC and Clang, and behaviour at `-O0`, `-O2` and `-O3`.
7. Run sanitizers and fuzz/mutation tests on parser, substitution and constraint paths.
8. Confirm no partially checked generic reaches code generation.
9. Record any unsupported proof claim explicitly. Tests, fuzzing and review are not formal verification.

Suggested feature test directories are `tests/generics/parser/`, `tests/generics/positive/`, `tests/generics/reject/`, `tests/generics/limits/`, `tests/generics/modules/` and `tests/generics/security/`. These are proposed locations, not existing directories.

## 9. Implementation gates and dependencies

| Gate | Dependency | Must pass before |
|---|---|---|
| G0 — baseline inventory | Existing compiler and tests | Any v0.5 implementation |
| G0.5 — module graph, canonical source identity, deterministic lookup and declaration IDs | G0 | Generic nominal identity, substitution keys and interface coherence |
| G1 — parameter identity and structural substitution | G0, G0.5 | Generic structs/enums/functions |
| G2 — substituted type validation and qualifier preservation | G1 | Any generic value reaches ordinary checking |
| G3 — monomorphisation and global resource budgets | G1, G2 | Generic code generation |
| G4 — constraints and cross-module coherence | G0.5, G1–G3; explicit impl ownership rule | Interface-constrained generic calls |
| G5 — generic exhaustiveness and payload typing | G1–G3 | Generic enum use in production code |
| G6 — Result and propagation | G1–G5 | Error propagation syntax |
| G7 — closures, capture and GC/secret rules | G0.5, G1–G4; runtime support | Closure expressions and Shroud typed messages |
| G8 — bootstrap, differential, fuzz and release evidence | G0–G7 | v0.5/v0.6 release claim |

The sequence is intentionally conservative. No later feature should force a weakening of an earlier security invariant to make its API convenient.

**Ordering clarification:** G0.5 is a semantic prerequisite, not a demand that the entire visibility migration be completed before generics. It establishes the identity and lookup substrate only. Public/private enforcement and recursive API-surface closure may be implemented as a later gate, but no generic nominal type, substitution cache or interface-coherence decision may use an unqualified source name as declaration identity.


## 10. Type identity and substitution contract

The current implementation makes Type a recursive value containing a kind, a string name and nested arguments. type_eq compares those fields structurally. This is sufficient for the current closed set of types, but it is not a safe identity model for generic parameters or imported declarations.

The following contract is recommended for the first generic implementation. It is an implementation constraint, not a commitment to a particular in-memory layout.

### 10.1 Parameter identity

A type parameter must have a stable identity independent of its spelling. Use a declaration identity plus a parameter ordinal (or an equivalent unforgeable compiler-local ID). The source name is retained for diagnostics only.

For example, the two parameters named T in left<T> and right<T> are distinct. Likewise, a nested declaration or imported declaration must not capture a parameter merely because its name matches. Reject duplicate parameter names within one binder, but do not use names as substitution keys.

The type representation therefore needs an explicit type-variable form whose identity is not overloaded onto the nominal type-name field. Nominal struct, enum and interface identity should likewise resolve to a declaration/module identity before equality or coherence checks; bare source spelling is not a robust cross-module key.

### 10.2 Substitution operation

Define substitution as a pure structural operation: substitute(type, environment) -> Result<Type, Diagnostic>, where the environment maps parameter identities to fully resolved concrete types.

Required behaviour:

1. A type variable is replaced only by the exact matching parameter identity.
2. A nominal type retains its resolved declaration identity and recursively substitutes each argument.
3. Built-in constructors (List, Map, optional and Grant<P>) retain their constructor and recursively substitute their arguments/policy identity.
4. Security-relevant atomic types (Tainted, Secret, Html, LogText) are never normalised to ordinary string; they remain distinct leaves.
5. A missing binding is an unresolved-variable error. An unused environment entry is not silently applied to another binder.
6. The result is validated after substitution, including arity, kind, optional restrictions, field/variant restrictions and recursive grant containment.
7. Substitution does not mutate the template AST or a shared type node. A failed substitution cannot leave a partially rewritten template for a later instantiation.
8. The operation is bounded by the same compilation-wide type-node/work budget used by instantiation; recursive traversal must not consume unbounded stack.

The substitution environment must be complete for every generic declaration being instantiated. Do not treat an unresolved variable as a wildcard or as an error type that remains assignable.

### 10.3 Equality, assignability and canonical instantiation keys

Keep three concepts separate:

- Type identity/equality: resolved nominal identity plus recursively equal arguments; type variables compare by binder identity and ordinal.
- Assignability: the language's explicit rules applied to already resolved types. Invariance means generic arguments must be equal; substitution must not introduce a variance shortcut.
- Instantiation identity: the generic declaration identity plus its ordered, canonical concrete argument vector. This key drives memoisation and cycle detection; it must not depend on source formatting or import order.

Do not use rendered type_str output as an equality or cache key. It is a diagnostic representation and can be ambiguous when declarations share names across modules.

### 10.4 Instantiation stack and growth detection

Maintain an active stack of canonical instantiation keys. Re-entering the same key is stable recursion and should reuse the in-progress checked representation where the recursive type model permits it. A new key with structurally growing arguments is a distinct instantiation and must consume the global budget.

The checker must not reject ordinary recursive calls to the same concrete function or stable recursive data such as Node<T> { List<Node<T>> children; }. Conversely, F<T> -> F<List<T>> and mutually expanding equivalents must not evade limits by alternating templates.

An early growth diagnostic is useful, but the hard global budget remains the safety backstop. Growth detection is not a substitute for bounded accounting.

### 10.5 Required focused tests

- Same parameter spelling in two generic declarations does not cross-substitute.
- Nested binders and imported declarations cannot capture one another's parameters.
- Every occurrence of a parameter is substituted in fields, enum payloads, function parameters, returns and nested arguments.
- Missing and extra bindings fail deterministically without mutating the template.
- Substitution preserves Tainted, Secret, Html, LogText and nested Grant<P> exactly.
- Nominal types with the same short name in different modules do not compare equal or collide in the instantiation cache.
- Equivalent instantiations reached through different import/declaration orders share one canonical cache entry.
- Stable recursion is accepted; direct and mutual expanding instantiation hit a deterministic diagnostic/budget.
- A deliberately deep type tree fails within the node/work budget rather than exhausting the host stack.

These tests should precede generic code generation. Until the type-variable identity, nominal identity and substitution contracts are settled, adding parser syntax alone would create an unstable foundation for constraints, coherence, diagnostics and monomorphisation.


## 11. Module identity and name resolution are prerequisites, not just visibility checks

The current compiler does not yet have the module model described by the v0.5 proposal. The import loader in compiler/main.cap flattens declarations from every loaded file into one List<Node>. Node.file preserves the source-file index, but compiler/checker.cap registers top-level declarations in global maps keyed by the unqualified source name (for example structs, enums, functions, policies and constants). Type normalisation and lookup then resolve by that name. The loader records import origin only for read-error reporting; it does not retain a durable importer-to-imported-module graph for semantic access checks.

Consequently, adding a public/private flag and checking Node.file at a few reference sites would not be enough. Before module visibility can be implemented safely, the design must define:

1. **Module identity:** a stable identity for each loaded source module, distinct from its path spelling. Define whether identity is canonicalised filesystem identity, a compiler-assigned module ID within one build, or a package/module name. State the treatment of symlinks and the same file reached through multiple import paths.
2. **Import graph:** retain directed import edges, including the importing module and import declaration location. Define whether visibility is direct-import-only or transitive, and whether re-export exists. The current breadth-first loader does not preserve these semantics as a graph.
3. **Name resolution:** define how an unqualified identifier resolves when two imported modules export the same name. Define qualified names/aliases or an explicit ambiguity error. Resolution must not depend on traversal order or whichever declaration overwrites a Map entry.
4. **Declaration identity:** resolve each nominal type, function, interface, policy and constant reference to a declaration identity before type equality, substitution, overload/impl lookup or code generation. A short name is not a stable key.
5. **Member/associated visibility:** specify how method declarations lifted out of struct bodies retain their owning module/type and visibility, and how enum variants and interface implementations participate in access checks.
6. **Public signature closure:** check every type reachable from an exported declaration, including generic parameters/bounds, nested generic arguments, fields, enum payloads, function parameters/returns, interface methods and impl methods. Aliases/re-exports must not create an alternate path to a private declaration.

Required tests: two imported modules exporting the same type/function name; one private and one public declaration with the same short name; direct versus transitive imports; import-order permutations; the same source reached through two paths; symlink/path alias policy where supported; public signatures that leak private types through nested generic arguments or constraints; and method/variant access across module boundaries. All should produce deterministic resolution independent of import queue order.

This is a design dependency for generic substitution and coherence as well as visibility: canonical type and implementation identities cannot be made reliable while nominal resolution remains name-only. It should be resolved before a module-visibility implementation or generic cache is built on top of the current global maps.


## 12. Minimum module-resolution contract for v0.5

The current loader resolves `import "lib/util.cap";` relative to the importing file, deduplicates using the resolved path string, queues imports breadth-first, and then flattens declarations into one list. `Node.file` preserves source provenance, but the checker registers declarations in global maps keyed by unqualified names. The importer's semantic graph is not retained. This is insufficient to implement the proposal's statement that each source file is a module.

The following is a conservative minimum contract, not a requirement for a package manager or separately compiled modules:

1. **Compilation-local module identity.** Assign each loaded source unit a stable internal `ModuleId`. Keep its display/source path separately. Define canonical file identity and the compilation-root boundary. Path normalization must not silently allow a physical source to be loaded twice through aliases. Specify symlink handling; where canonical identity cannot be established reliably, reject ambiguous aliases rather than treating one physical source as distinct modules.
2. **Retained import graph.** Preserve importer-to-imported-module edges, including source location and written import path. Recommended v0.5 rule: a module may refer to its own declarations and public declarations of modules it directly imports. Transitive imports are not implicitly in scope. Re-exports are out of scope and must not happen accidentally through the flattened declaration list.
3. **Deterministic lookup.** Give imports explicit aliases and require qualified cross-module references, or define a unique unqualified lookup set and reject collisions with a diagnostic listing all candidates. Resolution must not depend on breadth-first traversal, declaration order or map insertion order.
4. **Declaration identity.** Assign every nominal type, interface, policy, function and constant a stable `DeclId` associated with its `ModuleId`. Type equality, generic substitution and instantiation keys, interface coherence and generated symbol identity use declaration identity; source spelling is for diagnostics only.
5. **Recursive visibility closure.** A public declaration must not expose private declarations through parameter or return types, nested generic arguments, constraints/bounds, fields, enum variants, methods or impl-associated declarations. Specify whether member visibility inherits from its parent or is independently declared.
6. **Path/graph adversarial tests.** Cover same-named declarations in sibling imports, direct versus transitive access, aliases, ambiguity independent of import order, repeated imports, normalized path aliases, symlink aliases where supported, and private-type leaks through generic bounds, fields, variants and methods.

**Dependency gate:** module and declaration identity must be settled before generic nominal types and interface coherence are accepted as complete. If implementation is staged later, generic implementation must remain blocked from relying on unqualified global-name identity in the interim. These tests are distinct from ordinary visibility-flag tests: they establish which declaration a reference denotes before asking whether that declaration is accessible.


## 13. Generic implementation declarations must be in scope or explicitly excluded

The v0.5 proposal introduces generic structs, enums and functions, and generic interfaces, but its only `impl` example is concrete:

```capstan
impl Comparable<int> for int {
    bool less(int self, int other) { return self < other; }
}
```

It does not specify whether an implementation may bind its own type parameters, for example `impl<T> Comparable<T> for Box<T>`, or how such parameters are constrained and included in coherence. This is a material language-scope decision, not merely syntax polish.

There are two coherent choices:

1. **Support generic impls in v0.5.** Define binder identity and constraints on impl parameters, orphan ownership, and overlap checking over parameterised impl heads after substitution. Required cases include duplicate generic impls, overlapping heads such as `impl<T> I for Box<T>` versus `impl I for Box<int>`, unconstrained parameters, and coherence across the complete import closure.
2. **Exclude generic impls in v0.5.** State that impl heads must be fully concrete, reject free type parameters in impl heads, and document the limitation: generic types cannot provide one interface implementation uniformly for all type arguments. Do not silently approximate a generic impl as a finite set of observed instantiations.

Whichever choice is made, coherence must use resolved interface/type declaration identities and be independent of source and import order. If generic impls are deferred, the design must avoid syntax or inference that accidentally accepts them.

The acceptance matrix must not assume generic impls exist until the proposal explicitly selects the first option. The compiler must not accidentally accept an unconstrained or overlapping implementation merely because a concrete test instantiation happens to be unique.


## 14. Generic inference and interface dispatch must preserve security effects

The v0.5 proposal says that generic arguments are inferred from value arguments when there is exactly one valid solution, and that interface calls are resolved to direct calls after monomorphisation. Those are reasonable implementation choices, but the design does not yet define the inference relation or how protected-call requirements survive interface abstraction.

### 14.1 Inference must be structural and qualifier-preserving

Inference should be a bounded structural unification operation over the declared parameter types and actual argument types. It must not be a permissive conversion search. In particular:

- A type variable is identified by its declaration binder and ordinal, never by its spelling.
- Matching a type constructor requires the same constructor and arity; nominal types require the same resolved declaration identity.
- Repeated occurrences of one type variable must infer exactly the same type. Conflicting candidates are an error, not a widening opportunity.
- Security-relevant leaves remain exact: `Tainted`, `Secret`, `Html`, `LogText` and `Grant<P>` cannot be erased, converted to a weaker qualifier or inferred as an unrelated nominal type.
- Inference uses only the value-argument positions specified by the proposal. It must not silently use expected return type, ambient context, declaration order or runtime values to choose a candidate.
- Every declared type parameter must have one complete solution. Unused or underconstrained parameters require explicit type arguments or a diagnostic.
- The inferred substitution is immutable and is then passed through the same bounded substitution, type validation, constraint checking and grant-containment checks as explicit type arguments.

Required tests include repeated-variable conflict; nested `List<T>` and optional matching; same-short-name nominal types from different modules; explicit versus inferred argument equivalence; `Tainted` and `Secret` preservation through nested arguments; `Grant<P>` versus `Grant<Q>`; and an ambiguous or unused type variable. Permuting argument/declaration/import order must not change the result.

### 14.2 Protected-call requirements are part of an interface method contract

In the current checker, a direct protected call is not accepted merely because its arguments otherwise match. `check_call` resolves the concrete function declaration, reads its `protected(P)` annotation, and requires a first argument of exactly `Grant<P>`. The protected function body is separately checked with a privileged context. This is an explicit security boundary.

The v0.5 interface proposal describes method signatures and static dispatch, but does not specify how a protected implementation's policy requirement is represented in the interface contract. A generic caller checked only against an ordinary-looking interface signature must not be able to dispatch to a protected implementation, nor may an implementation silently introduce or weaken a protection requirement.

The design must choose and specify a rule. The minimum safe contract is:

1. A protected interface method declares its policy identity and grant parameter position as part of its callable signature/effect.
2. A generic call must provide exactly the corresponding `Grant<P>`; a grant for another policy is not substitutable.
3. An implementation must match the interface's protection contract exactly. It cannot weaken a protected requirement, substitute another policy, or add an undeclared protected requirement.
4. After substitution and implementation selection, the concrete target is checked against the interface contract before code generation.
5. The implementation body is checked under the same privileged-context rules as an ordinary protected function. Calling through an interface does not itself confer privilege.

Required negative tests: call without a grant; wrong-policy grant; implementation effect mismatch in either direction; generic substitution changing the policy identity; and an interface call whose selected implementation cannot be proven unique. Positive tests must show that the correct grant permits the protected operation without granting ambient privilege to the generic caller.

### 14.3 Grant non-escape must be one recursive rule

The current checker already uses recursive `contains_grant` for function returns, struct fields, enum payloads and constants. The generic implementation must preserve that property through arbitrarily nested type constructors and type-variable substitution. Do not duplicate shallow checks such as testing only whether the immediate collection element is `TY_GRANT`.

Define a single recursive, bounded predicate over the fully substituted type and apply it consistently to every position that can extend a grant's lifetime or hide it from a caller: aggregate storage, return values, closure environments/captures, constants, and any future generic container or interface-associated value. Keep the intentional request-scoped local/parameter use distinct from heap storage and escape. Test nested wrappers (including optional and multiple aggregate layers), aliases, substituted type variables, and closure capture. The rule must be evaluated after substitution as well as on declaration templates.

These requirements close a gap between the existing concrete protected-call model and the proposed generic/static-dispatch model. They do not require runtime dispatch or a general-purpose effect system; they require the existing policy/grant semantics to remain explicit and invariant under abstraction.


## 15. Generic templates require abstract checking; Result propagation needs a defined expression form

### 15.1 Check generic declarations independently of observed instantiations

The proposal states that generic bodies may use only operations supplied by declared constraints, and that each concrete instantiation is type-checked after substitution. It does not define the abstract checking phase that enforces the first rule before concrete call sites are considered.

Require two distinct phases:

1. **Template validation.** Check each generic declaration once in an abstract environment containing its binder-identified type variables and declared interface constraints. Every operation on a type variable must be justified by a declared bound or a language-defined operation valid for every type. Calls to other generic declarations must discharge their constraints symbolically from the caller's declared bounds. Missing or ambiguous obligations are errors at the template declaration, even if it is never instantiated. Check control flow, return completeness, protected-call/grant rules and all safety rules that do not depend on concrete layout or implementation selection.
2. **Concrete instance validation.** After substitution, resolve concrete interface implementations and recheck every property dependent on concrete types, declaration identity, layout or selected implementation. Recheck the security invariants that depend on the substituted type, including recursive grant containment and qualifier preservation. Only then may code generation consume the instance.

Neither phase emits C. A generic template must never be emitted as partially checked C. Acceptance of a template must not depend on which instantiation call sites happen to be present in the compilation unit.

Required tests:
- An invalid generic body is rejected even when the generic declaration is never instantiated.
- An operation supported by one concrete type but not justified by the generic bounds is rejected at the template.
- A generic function calling another generic function without proving its bound is rejected.
- Adding/removing unrelated instantiation sites does not change template acceptance.
- A valid abstract template whose concrete implementation is missing or ambiguous fails at concrete instance validation before code generation.
- No generated C is produced after either phase reports an error.

### 15.2 Result propagation is typed control flow, not merely a postfix operator

The proposal defines the value-level behaviour of postfix `?`, but the current expression parser's postfix loop handles member access and indexing only; it does not currently parse postfix expression operators. The existing postfix `?` in the parser is used for optional *types*. The Result operator therefore needs an explicit expression grammar and AST/control-flow representation, distinct from optional-type syntax.

Specify and test:
- Exact precedence and associativity when `?` follows a call, index, field access, parenthesised expression, or another postfix expression.
- The operand must be exactly `Result<U, E>`; the enclosing function must return `Result<V, E>` with exactly the same resolved error type. No optional lifting, error conversion, or implicit coercion.
- The success edge yields the `Ok` payload with its substituted type; the error edge constructs/returns the corresponding `Err` payload.
- The propagation edge is explicit in typed control flow and participates in definite-return/reachability analysis. It must not be modelled as an exception, hidden unwind or ordinary expression fallthrough.
- Evaluation order is left-to-right and the operand is evaluated exactly once, including when it is a call with side effects.
- Local values and temporary resources are handled consistently on both success and propagation edges. If destructors/finalizers or explicit cleanup are added, define their edge semantics before enabling `?` with them; do not silently introduce unwind behaviour.
- Nested propagation preserves the exact error type and does not change protected-call privilege or allow a grant to escape.

Required tests cover every operand form above, nested `?`, exact error-type mismatch, use outside a Result-returning function, side-effecting operand evaluated once, both CFG edges, return analysis, and cleanup/resource behaviour. Parser tests must distinguish `T?` in a type from `expr?` in an expression, including adjacent tokens in nested generic types and expressions.


## 16. Closure environments must preserve GC tracing and secret erasure independently

The closure proposal currently says that a closure environment containing captured bindings must be allocated and reclaimed through a "secret-aware runtime path" when it captures `Secret`. That wording is not compatible with the current collector's allocation model and should be corrected before implementation.

### 16.1 The environment and secret payload have different GC requirements

The current collector has three allocation kinds:
- kind 0: pointer-containing allocations, traced by the collector;
- kind 1: pointer-free atomic allocations;
- kind 2: pointer-free secret allocations, zeroed when reclaimed.

The runtime's `secret_env` creates a `Secret` as a `CapStr*` allocated with kind 2. A closure environment contains captured pointers and must therefore be pointer-scanned. Allocating the whole environment as kind 2 would suppress tracing of those captured pointers and could allow the referenced objects to be reclaimed while the closure still contains dangling references.

For the current opaque-pointer representation, the minimum safe model is:
1. Allocate the closure environment as an ordinary pointer-scanned GC object (kind 0).
2. Capture a `Secret` binding by copying its opaque pointer, not by copying its bytes into an ordinary allocation.
3. The environment's traced pointer keeps the original kind-2 secret payload reachable while the closure is reachable.
4. Once the secret allocation is unreachable, the existing collector wipes its bytes during sweep before reuse/free.
5. Captured ordinary references are traced by the same environment. Grant capture remains forbidden recursively through every nested type and capture path.

Do not mark a pointer-containing environment as atomic/secret merely to obtain wiping. If a future closure representation embeds secret bytes inline in an environment, it will need a separately specified representation that simultaneously supports pointer tracing and secret wiping; the current three allocation kinds do not provide that combination.

### 16.2 Erasure is collection-time, not lexical or deterministic

The collector conservatively scans stack and register roots. A stale pointer-shaped value can therefore keep an otherwise unreachable closure environment, and the secret it references, alive beyond the source-level scope or last apparent use. The language must describe this as wipe-on-collection, not immediate erasure at closure drop, lexical scope exit, or loss of the last source-level reference.

The guarantee is limited to the managed secret allocation. It does not establish that every transient copy in registers, stack slots, compiler temporaries, foreign libraries or OS/environment storage is synchronously erased. APIs and documentation must not overstate this guarantee.

### 16.3 Required runtime tests

- A closure retains a captured Secret across repeated forced collections; the secret remains readable only through permitted secret operations.
- Once the closure and all other references are genuinely unreachable, a subsequent collection wipes the secret allocation before reuse/free.
- Test both small-object page allocations and large-object allocations; the collector has separate sweep paths for each.
- A closure retaining ordinary reference-type captures keeps their objects alive and usable after the creating frame returns.
- Capturing a Grant directly or nested in optional/aggregate/generic wrappers is rejected.
- Test GC stress mode, GCC and Clang, and `-O0`, `-O2`, `-O3`; conservative register/stack roots can make collection timing optimisation-sensitive.
- Include a test-only observation mechanism for verifying wipe-before-reuse without exposing raw secret bytes or a production introspection API.

These are separate properties: environment reachability must be correct, grant non-escape must be enforced statically, and secret payload erasure must be verified at the collector boundary.


## 17. Closure capture analysis, aliasing and transitive capability non-escape

The closure contract needs an explicit capture-analysis algorithm. “All free-variable bindings” is not sufficient as an implementation requirement unless nested closures, aggregate values and capability-bearing types are covered.

### 17.1 Capture set is lexical, complete and deterministic

For each closure expression, compute the free-variable set relative to that closure's parameters and locally declared bindings. Capture every referenced outer binding exactly once, in deterministic declaration order (with a specified tie-breaker for nested scopes). Do not capture unrelated locals.

Nested closure conversion must be recursive:
- If an inner closure refers to a binding local to the enclosing closure, the inner closure captures that enclosing binding when it is created.
- If the enclosing closure needs an outer binding only to create or initialise the inner closure, the enclosing closure must itself capture that binding.
- A closure returned from a function must carry every binding required by its nested closures; no environment pointer may refer to the creator's stack frame.
- The compiler must not treat a name as local merely because it appears in an intermediate closure-conversion environment. Preserve the original lexical binding identity through every conversion step.

Capture identity is a binding identity, not just a variable spelling. Shadowed variables in nested scopes must never be conflated. Capture layout and generated environment fields must be deterministic across bootstrap and compiler versions.

### 17.2 By-value means snapshot of the binding, not deep immutability

Specify the following semantics:
- Scalars and immutable value-like values are copied at closure creation. Later reassignment of the original local binding does not change the captured value.
- For reference types, the pointer is copied. The referenced object is shared, not cloned; mutations through any alias are observable through the closure.
- Reassigning the original local reference variable after closure creation does not retarget the closure's captured pointer.
- A closure environment's binding slots are not implicitly mutable cells. There is no hidden reference capture or shared stack cell.
- Mutation of a captured heap object remains possible only through the language's ordinary checked mutability rules. The closure does not grant extra mutation authority.
- Function/closure values are immutable code-plus-environment pairs unless a separately specified operation replaces the entire function value. Calling a closure repeatedly observes mutations to shared captured objects, but not later reassignment of the source binding.

These rules distinguish snapshot semantics from deep-copy semantics and avoid accidental capture-by-reference of local variables.

### 17.3 Grant rejection is a recursive property of the resolved capture type

At closure creation, reject a capture if its fully resolved type contains `Grant<P>` anywhere. The predicate must recurse through:
- optional and collection constructors;
- every field of a nominal struct;
- every payload field of every nominal enum variant;
- generic type arguments after complete substitution;
- nested closure/function environment types, if function values can themselves contain captures.

The check must operate on canonical declaration identity, not a short type name, and must be bounded by the compiler's global type traversal/work budget. An unresolved type variable is not evidence that a capture is safe: the template must carry a proof/constraint that excludes Grant, or the capture must be rejected until concrete substitution proves the property.

The same grant-containment predicate must govern all escape boundaries: closure capture, function return, aggregate storage, constants, collection insertion, and any future heap allocation or asynchronous/task capture. Do not implement a weaker closure-specific check.

A grant obtained in a protected function may be used locally for the protected operation, but cannot be retained by a returned closure, nested closure, aggregate, collection or generic wrapper. A closure that does not reference the grant need not capture it.

### 17.4 Secret reachability follows the full captured object graph

A closure may capture a Secret directly or through an aggregate only under the section 16 allocation rule. The closure environment is pointer-scanned; all intermediate aggregates/containers must also be correctly traced; the original kind-2 secret payload remains reachable through that graph. Do not copy secret bytes into ordinary closure storage. Reclamation and wiping remain collection-time guarantees, not deterministic destruction.

The current runtime provides a useful starting point for container tracing: `CapList` and `CapMap` headers are allocated with `cap_alloc`; list `items`, map `keys` and map `vals` backing arrays are also allocated with `cap_alloc`, so pointer-bearing entries are scanned. The map's integer index table is allocated atomically because it contains indices, not pointers. This representation should be preserved or equivalently proven in any generic/container or closure-environment redesign. In particular, a `List<Secret>` stores opaque pointers in scanned `CapVal` entries; the secret payload itself remains a separate kind-2 allocation.

### 17.5 Required adversarial tests

- Nested closure captures a function parameter; outer closure is returned; repeated forced collections; inner closure remains valid after creator returns.
- Nested closure captures a binding that the outer closure itself captures from its creator; verify both environment links and no stack reference.
- Shadowed variables with the same spelling produce distinct captures and deterministic layouts.
- Capture a scalar, then reassign the original local; closure sees the creation-time scalar value.
- Capture a reference to a mutable object, mutate through a second alias, and verify the closure observes the mutation.
- Reassign the original reference variable to a different object; closure continues to refer to the originally captured object.
- Reject direct `Grant<P>`, optional `Grant<P>?`, collection-wrapped `Grant<P>`, and any generic wrapper whose concrete substitution contains Grant.
- Reject a nested closure that captures a Grant even if the enclosing closure does not otherwise expose it; reject an outer closure that must transitively retain a grant to construct the inner closure.
- Accept a closure in a protected function that does not capture the Grant and does not use it after the protected call.
- Capture a Secret through a struct/list/enum path; force collections and verify all intermediate objects remain reachable and the secret is wiped only after the complete graph becomes unreachable and a collection occurs.
- Verify capture ordering and generated output are deterministic across bootstrap, GCC/Clang and `-O0`, `-O2`, `-O3`.

These tests should be added when closure syntax and runtime support land; they are acceptance requirements, not claims about current closure implementation.


## 18. Bounded, cycle-safe Grant-containment analysis

The recursive Grant rule in sections 6 and 17 must be implemented as one compiler-owned semantic predicate, not as several ad hoc recursive checks over surface syntax. A conceptual interface is:

`grant_status(Type, SubstitutionEnvironment) -> ContainsGrant | ProvenGrantFree | Unknown`

The three outcomes are intentionally distinct. Unknown is never silently treated as Grant-free.

### 18.1 Resolve complete storage graphs

- Resolve nominal types by canonical declaration identity (`DeclId`), not short name.
- Inspect every field of a struct and every payload field of every enum variant.
- For generic declarations, apply the complete substitution before inspecting the instantiated storage graph.
- Traverse optional and collection constructors, generic arguments and nested function/closure environment types wherever those can contain stored values.
- For opaque, foreign or otherwise uninspectable layouts, return Unknown unless a trusted, explicit compiler contract proves the relevant property. Do not infer safety from the absence of visible Grant arguments.

### 18.2 Generic abstract and concrete obligations

A type variable is not implicitly Grant-free. If a generic body stores, returns, captures or otherwise lets a type parameter cross an escape boundary, its abstract check must establish a Grant-free obligation from declared bounds or a compiler-defined structural property. Otherwise reject the template at the declaration or defer only the concrete-dependent operation under a clearly specified rule that cannot permit an unchecked escape.

Concrete substitution must re-run the predicate over the complete resolved storage graph. This must reject a Grant hidden several nominal and generic layers below the apparent outer type. Generic helpers that only borrow or pass a Grant locally may remain valid where their signatures and protected-effect rules prove non-escape.

### 18.3 Recursive types, memoisation and bounded work

The analysis must terminate on legal recursive nominal types. Use memoisation keyed by canonical instantiated type identity, with explicit in-progress and completed states:
- Encountering an in-progress node identifies a recursive edge; it is not by itself evidence of Grant or proof of Grant-freedom.
- A completed node may reuse its established result.
- A Grant discovered anywhere in a reachable storage path makes the containing type ContainsGrant.
- A recursive strongly connected component is ProvenGrantFree only after every reachable field edge has been analysed and no unresolved/opaque edge remains.

The traversal must consume the same deterministic global type-node/work budget as substitution and instantiation analysis. Exhaustion produces a normal bounded diagnostic; it must not cause unbounded recursion, stack overflow or an optimistic Grant-free result.

### 18.4 One predicate at every escape boundary

Use the same semantic predicate for function returns, struct and enum storage, constants, collection insertion/storage, closure captures and environments, nested closures, and any future task/async capture or heap allocation. Do not maintain a weaker closure-only or collection-only approximation.

### 18.5 Required adversarial tests

- Mutually recursive nominal types with no Grant are accepted and terminate.
- Stable recursive generic structures such as `Node<T> { List<Node<T>> children; }` are accepted when the complete instantiated storage graph is Grant-free.
- A Grant hidden several nominal and generic layers down is rejected at every escape boundary.
- A recursive nominal cycle with a Grant on one reachable branch is rejected regardless of declaration or traversal order.
- An unresolved type variable is not accepted as Grant-free at return, storage, collection or closure-capture boundaries.
- A generic helper that uses a Grant locally without storing, returning or capturing it remains accepted when its effect contract proves non-escape.
- Opaque/foreign layouts without a trusted Grant-free contract produce Unknown and are rejected at escape boundaries.
- Memoisation distinguishes in-progress recursion from completed safe results and remains deterministic across declaration/import order.
- Deep and mutually recursive graphs exhaust the configured work budget with a stable diagnostic, without stack overflow or unbounded compiler work.

These are acceptance requirements for the future checker, not claims that the predicate or generic/closure features currently exist.


## 19. Concrete implementation scope, orphan ownership and protected interface effects

The v0.5 interface proposal must settle implementation scope and method effects before the checker or static-dispatch lowering is implemented. These are security and determinism requirements, not syntax preferences.

### 19.1 Recommended v0.5 scope: concrete impl heads only

For the initial milestone, require every implementation head to be fully concrete after ordinary type-name resolution. Explicitly exclude generic/blanket implementations, impl-head type variables, and wildcard patterns. Generic functions and generic types may still use interface constraints: after substitution, the concrete type must have one matching concrete implementation.

This restriction means a generic nominal type such as `Box<T>` cannot provide one blanket interface implementation for all `T`. That limitation must be documented, and concrete instantiations may only satisfy a bound where a matching concrete impl exists. Do not silently expand one generic impl into an open-ended family of instances.

Generic impls can be considered in a later milestone after declaration identity, ownership and overlap checking are implemented and tested.

### 19.2 Orphan ownership and coherence boundary

- An impl is permitted only when its declaring module owns either the interface declaration or the target nominal type declaration.
- Built-in primitive types and prelude interfaces require an explicit, fixed ownership/extension rule. Do not let arbitrary user modules implement a foreign prelude interface for a foreign primitive by accident.
- Resolve interface and target identities to canonical declaration identities before checking ownership or duplicates.
- Check all concrete impls in the root module's complete canonical transitive import closure as one coherence set. Import aliases, duplicate paths and source order must not change the result.
- Two impl declarations for the same resolved interface/target pair in that closure are a deterministic error. Do not choose by declaration order.
- An unrelated module not in the compilation closure must not affect the current compilation's impl set. If a future package/link model combines independently compiled units, it must define and repeat coherence checks at that boundary.

### 19.3 Protected interface methods carry explicit effects

An interface method contract must represent protection as part of the callable method identity/contract, not merely as an implementation detail discovered after method lookup. For a protected method, specify the policy identity and corresponding `Grant<P>` parameter position in the interface declaration. The implementation must match the policy and grant position exactly.

At a generic call site:
- the caller must provide the exact `Grant<P>` required by the interface contract;
- `Grant<Q>` is not interchangeable with `Grant<P>`, even if policies have structurally identical parameters or bodies;
- interface satisfaction does not create ambient privileged context;
- the selected concrete implementation is revalidated against the interface effect contract after substitution and before code generation;
- the implementation body is checked under the same protected-function rules as an ordinary protected function, including policy-role binding and revalidation of policy arguments.

An implementation must not weaken a protected requirement, strengthen an unprotected interface method into a protected implementation, substitute another policy, or move the grant to a different argument position. The language may choose a more concise surface syntax, but the typed interface contract must retain these facts explicitly.

### 19.4 Required adversarial tests

- Reject generic/blanket impl declarations in v0.5 with a direct diagnostic; accept concrete impls for concrete instantiations of generic nominal types.
- Reject a foreign-interface/foreign-type impl; accept an impl when the module owns either side.
- Reject duplicate concrete impls reached through different paths or aliases in one import closure, independent of source order.
- Confirm an impl in an unrelated, unimported module does not affect the compilation.
- Confirm prelude/primitive extension follows one explicit rule and cannot be claimed by arbitrary modules.
- Reject a protected interface call without a grant and reject `Grant<Q>` where `Grant<P>` is required.
- Reject implementation/interface protection mismatches in both directions, wrong policy identity, and wrong grant parameter position.
- Verify a generic caller cannot gain privileged context from an interface bound; the correct grant is required at the call site and the concrete method body is checked as protected.
- Verify concrete target selection and effect revalidation are deterministic across import/declaration order and happen before any C is emitted.

These requirements complement the generic abstract/concrete checking gates and the bounded Grant-containment analysis in sections 15 and 18.


## 20. Recursive public-API closure and visibility through generic abstractions

The proposal's rule that a public declaration may not expose a private type is necessary but underspecified. Once generic bounds, interfaces, protected methods and static implementation lookup exist, visibility must be checked over the complete semantic API surface, not only the spelling of the outermost parameter and return types.

### 20.1 Define the exported declaration closure

For every public declaration, compute a finite, cycle-safe closure of all declarations that a caller must know, name, construct, inspect, satisfy or invoke to use that API. At minimum include:

- Function and method parameter types, return types, receiver types, and every nested generic argument and optional/collection/function-type component.
- Generic parameter bounds and every referenced interface and interface method contract.
- Every nominal struct field type and enum variant payload type that is externally accessible under the language's field/variant access rules.
- Types and policy identities referenced by protected method/function contracts, including the exact `Grant<P>` policy argument and grant parameter position.
- Public constant types and any nominal declarations needed to interpret their values.
- Any declaration reached recursively through the above types, including nested generic arguments; do not stop at the first public outer type.

A public signature such as `PublicBox<PrivateRecord>` is not API-closed merely because `PublicBox` itself is public. Likewise, a public generic function with a private interface bound or a protected method whose policy is private leaks an unnameable dependency.

The closure algorithm must use resolved declaration identity, not short names, and must terminate on recursive nominal types. Unknown or unresolved declarations fail closed with a visibility diagnostic; they are not treated as public.

### 20.2 Separate type visibility from member visibility

The proposal says struct-field visibility is a separate question and that existing field access rules remain unchanged unless specified. Under the current language, fields are accessed directly and there is no separate field-level visibility syntax. Therefore, for v0.5, either:

1. Treat all fields and enum payload types of an exported nominal type as part of its externally visible API and require their types to be public; or
2. Introduce explicit member visibility and fully define cross-module construction, field access, pattern matching and generated constructor behaviour.

Do not silently treat a private field as hidden when the language has no private-field mechanism. If member visibility is deferred, option 1 is the conservative rule. The same decision must cover methods declared inside structs, enum variants, and struct-literal construction.

### 20.3 Generic inference must not bypass visibility

Visibility checks apply after name resolution and type inference as well as at explicit source references. A caller must not gain access to a private type by omitting a type argument, relying on inferred return types, selecting an overload/implementation indirectly, or passing a public wrapper whose substituted arguments contain private declarations.

If a public generic API's constraints or substituted concrete type require a private declaration, reject the use at the call site with a deterministic diagnostic. Do not expose private declaration details in diagnostics beyond the minimum needed to identify the inaccessible API boundary.

### 20.4 Interface implementations are part of the API contract

The design must decide whether an implementation in an imported module is visible to all importers in the compilation closure or only within its declaring module. This is not merely an implementation detail: public generic functions may require a concrete implementation to satisfy an interface bound after substitution.

For v0.5, specify explicitly:
- Whether impl declarations have public/private visibility and what syntax marks an exported impl.
- Whether an exported impl may mention only public interface and target types.
- Whether an unexported impl may satisfy a bound outside its declaring module.
- How orphan ownership and coherence interact with impl visibility.
- Whether a public generic function's bounds are satisfiable only from exported impls in the caller's compilation closure.

A conservative model is to make impl visibility explicit, allow private impls only for use inside their declaring module, and require an exported impl for cross-module satisfaction. An exported impl must itself be API-closed: its interface, target, method signatures, protection effects and any public constraints must not depend on private declarations.

### 20.5 Required adversarial tests

- Reject a public function whose nested parameter or return type contains a private nominal type, including `PublicBox<Private>` and deeper nesting.
- Reject a public generic function with a private interface bound, private constraint dependency or private protected policy.
- Reject an exported struct or enum whose externally accessible field/variant payload contains a private type under the chosen member-visibility model.
- Reject a public method exposing a private type through its receiver, parameter, return type or protected effect.
- Reject a public constant whose declared type is private.
- Verify recursive public types terminate in closure analysis and are accepted only when every reachable exposed dependency is public.
- Verify inference cannot instantiate a public generic API with a private type to bypass visibility.
- Verify private impls do not satisfy external generic bounds if the chosen model makes impl visibility explicit; verify exported impls do.
- Verify a private implementation detail that is not part of any public signature or exported impl remains usable internally without being accidentally exported.
- Verify diagnostics are deterministic under import order and aliases and do not crash on unresolved or cyclic declaration graphs.

These are design and acceptance requirements, not claims that v0.5 visibility or generic checking is implemented.


## 21. Deterministic generic inference, qualifier preservation and call grammar

The v0.5 proposal permits inference from value arguments when there is exactly one solution, but does not define the unification relation, conflict handling, interaction with existing assignability conversions, or concrete call grammar. These are required for a sound implementation.

### 21.1 Define inference as structural unification, not assignability

For v0.5, use a deliberately narrow algorithm:

1. Resolve the generic function and its declared type-parameter binders before examining arguments.
2. Type-check each value argument exactly once under the ordinary left-to-right evaluation rules.
3. Unify each formal parameter type with its corresponding actual argument type structurally. A type variable binds to one complete actual type; constructors and nominal declaration identities must match recursively.
4. Repeated occurrences of one type variable must produce exactly the same type identity. Conflicting deductions are an inference error, not a choice of a common supertype.
5. Generic arguments are invariant. Do not use assignment conversions, optional lifting, text conversions, interface satisfaction or method-name coincidence to invent a unification result.
6. Reject an unconstrained type variable. Do not infer from the expected return type, later use of the result, ambient context, runtime values or the set of currently available implementations.
7. After all type variables are uniquely bound, substitute the complete type vector, validate every declared interface obligation and visibility rule, and only then select concrete implementations and check the instantiated body.
8. If inference is ambiguous or conflicting, require explicit type arguments or reject the call. Never select a result based on declaration/import order.

The design should state how receiver types contribute to method inference. If they do, use the same structural rule and include the receiver as a specified inference input; do not let method lookup create a second, less constrained inference path.

### 21.2 Preserve security and nominal qualifiers

Inference and substitution must preserve the exact type constructor and nominal identity at every node. In particular:

- `Tainted` must never infer as trusted `string`, nor the reverse.
- `Secret`, `Html` and `LogText` remain distinct and cannot be erased or widened by inference.
- `Grant<P>` retains the exact resolved policy declaration identity; matching policy spelling is insufficient.
- Generic nominal arguments preserve exact declaration identity and invariance.
- Optional lifting, where allowed by ordinary assignment, occurs only after inference has produced a complete type vector; it must not weaken the unification relation.
- Interface constraints do not grant conversion or subtyping. They establish only the explicitly declared operations for the exact substituted type.

The same canonical type identity must drive inference, substitution, constraint lookup, implementation selection, visibility and security checks. Diagnostic type strings are not identity keys.

### 21.3 Make explicit type-argument syntax unambiguous

The proposal says explicit type arguments are available but gives no call-site grammar. The parser already uses `<` and `>` as expression operators and adjacent `>` tokens also form shifts and nested type closers. Choose and document a grammar that does not reinterpret ordinary comparisons.

A conservative option is a visibly distinct turbofish form, for example `identity::<int>(7)`, with a dedicated parser production. If the design instead chooses `identity<int>(7)`, require token-aware lookahead and prove that expressions such as `a < b`, `a < b > (c)`, nested generic calls, shifts and chained comparisons retain their existing parse. Do not rely on whitespace conventions.

Specify whether all type parameters must be supplied explicitly or whether a trailing subset may still be inferred. The simpler v0.5 rule is all-or-none explicit arguments, with exact arity and no partially specified lists.

### 21.4 Required adversarial tests

- Infer a single type variable from one argument and from nested generic parameter types.
- Reject conflicting repeated deductions, including `T` appearing in two argument positions with different actual types.
- Reject inference from an expected return type, later assignment, method-name coincidence or a merely available impl.
- Reject unresolved/ambiguous type variables and wrong explicit type-argument arity.
- Verify optional lifting is applied only after inference and cannot merge `T` with `T?`.
- Verify `Tainted`, `string`, `Secret`, `Html`, `LogText` and distinct `Grant<P>` identities never unify by widening or spelling.
- Verify generic constraints are checked after complete substitution and a missing/ambiguous concrete impl is rejected before code generation.
- Verify inference is independent of source/import order and does not speculate by evaluating arguments more than once.
- Parser tests cover the chosen explicit type-argument syntax, nested generic closers, `<` comparisons, `>` comparisons, shifts and malformed/partial argument lists.
- Verify the same call produces identical inferred type identities and diagnostics in bootstrap and self-hosted compiler runs.

These requirements specify acceptance criteria; they do not claim generic inference or the proposed syntax currently exists.


## 22. Interface-obligation resolution must be finite and exact

The proposal requires generic bodies to use only operations supplied by declared constraints and resolves interface implementations after substitution. It does not yet define the representation or resolution algorithm for obligations, especially when interfaces and bounds refer recursively to generic types.

### 22.1 Canonical obligation identity

Represent each required interface implementation as a canonical obligation over resolved declaration identities and fully substituted type arguments, conceptually `Implements(InterfaceDeclId, ConcreteTypeId)`. Do not key obligations by short interface/type names or rendered type strings.

For each generic instantiation:
- Substitute the complete type argument vector into every declared bound.
- Normalize and resolve the resulting interface and target identities.
- Require exactly one concrete implementation in the applicable coherence set.
- Reject zero matches and multiple matches before code generation.
- Cache only completed successful or failed results under a canonical key that includes the compilation/coherence context; never reuse an answer from a different root import closure.
- Revalidate method signatures, visibility and protected effects against the exact interface contract.

An interface bound is evidence only for the exact substituted type/interface pair. It does not provide a conversion, structural duck typing, or ambient permission to call methods not declared by the interface.

### 22.2 Bound and interface recursion

Specify whether interfaces may extend other interfaces, whether one bound can imply another, and whether associated types/default methods are in scope. The conservative v0.5 choice is to exclude interface inheritance, associated types and default methods; each bound then creates one explicit concrete obligation and each impl supplies the complete declared method set.

Even with that restriction, recursive type references and recursive generic bounds must not cause unbounded resolution. Detect an obligation already in progress using its canonical key. A repeated in-progress obligation is not automatically proof of satisfaction: reject unsupported recursive obligation cycles with a deterministic diagnostic unless the language defines a sound, terminating coinductive rule and tests it.

Do not permit impl bodies to satisfy their own interface obligations by recursively selecting the impl currently being checked. Impl validation must be a separate phase that checks the complete method set and exact signatures without executing or recursively dispatching through the implementation under validation.

### 22.3 Generic bounds are lexical contracts

A generic declaration may rely only on bounds declared by its own type-parameter binders and on language-defined universal operations. It must not inherit constraints from whichever concrete instantiation happens to be compiled first, from another function's call context, or from a private implementation visible only in a different module.

If generic nominal types can declare bounds, specify whether those bounds are required at construction, field access, method invocation or all uses. If v0.5 does not support bounds on generic struct/enum declarations, state that explicitly; do not let method bodies on `Box<T>` assume unexpressed capabilities of `T`.

### 22.4 Required adversarial tests

- Resolve one concrete obligation and reject zero or duplicate implementations.
- Verify obligation keys distinguish same-spelled declarations from different modules and distinct policy/interface identities.
- Verify a generic function's obligation is resolved only after full substitution and against the correct root import closure.
- Reject attempts to use an implementation not visible under the chosen impl-visibility rule.
- Verify an interface bound exposes only its declared methods and never authorises method-name-based structural dispatch.
- Reject unsupported recursive obligation cycles deterministically without stack overflow or accidental success.
- Verify impl validation cannot recursively use the impl being defined to prove itself.
- Verify interface inheritance, associated types, default methods and generic nominal bounds follow explicit supported/excluded decisions.
- Verify cache results do not leak between separate compilation roots with different imported implementation sets.

These are acceptance requirements for future interface checking and static dispatch, not claims that the machinery currently exists.


## 23. Result propagation semantics and typed control-flow lowering

The proposal's exact-error-type rule is a strong starting point. The language contract must additionally define expression grammar, evaluation order, propagation scope and lowering. A postfix `?` is a control-flow edge, not merely a value conversion.

### 23.1 Expression grammar and precedence

Define `?` as an expression-only postfix operator in the postfix-expression grammar, alongside member access, calls and indexing. It binds more tightly than every unary, binary and conditional expression operator and associates left-to-right with other postfix operators. Parentheses group the expression before propagation. It is not a general expression suffix on a type, statement or declaration.

The parser must distinguish this use from the existing optional-type suffix in `parse_type`. It must reject malformed forms such as a missing operand, repeated propagation with no intervening Result expression, or use in a syntactic position that is not an expression. The design must give examples of chained calls/indexing and nested expressions so precedence is not left to parser implementation.

### 23.2 Exact propagation typing

For an operand of type `Result<U, E1>` inside a function whose declared return type is `Result<T, E2>`:

- Require exact resolved identity equality `E1 == E2`; no assignability, optional lift, interface conversion, coercion or user code is permitted on the error path.
- The success expression has type `U`, subject only to ordinary typing of the surrounding expression.
- The failure edge returns the same `Err(error)` payload from the current function without wrapping, converting, logging, swallowing or retrying it.
- Reject use in a non-Result-returning function, in a function with a different error type, or where the enclosing return type is not exactly a supported `Result<T,E>` instantiation.
- Define whether `Result<void,E>` is supported. If supported, define the success payload representation and statement/expression rules; if not, reject it explicitly rather than relying on backend special cases.

The equality check must use canonical resolved type identity, including module identity and generic substitutions, not source spelling.

### 23.3 Propagation target and nested callable boundaries

Propagation targets the innermost enclosing function body whose return type is being checked. A nested block, conditional, loop, match arm or ordinary expression does not create a new propagation target. When closures are added, a closure body is a new callable boundary: `?` inside it targets the closure's declared/inferred return type, never the function that created it. A nested function similarly owns its own return type.

The language must not allow `?` inside a policy, test-only callback or other callable-like construct to escape to an outer function. Each construct must either define a Result return contract or reject propagation.

### 23.4 Evaluation and control-flow requirements

Evaluate the operand exactly once, in the ordinary left-to-right order, before inspecting its variant. On `Ok`, extract the payload and continue with the surrounding expression. On `Err`, return immediately from the current callable with the unchanged error payload. No later operand, argument, index, method call or side effect in the enclosing expression may execute after the failure edge.

Represent the success and failure paths explicitly in typed control flow (or a rigorously equivalent ANF/CFG form). Do not implement `?` as an untyped textual macro or a C expression whose evaluation order depends on compiler extensions. The generated failure edge must be an ordinary typed return, visible to return-path analysis and code review. Ensure temporaries and GC roots keep pointer-bearing operand/error payloads alive across lowering.

### 23.5 Required adversarial tests

- Success and failure propagation from direct calls, nested calls, method calls, indexing and parenthesised expressions.
- Multiple `?` operators in one expression; verify left-to-right order and exactly-once evaluation.
- Verify later call arguments and side effects do not execute after an earlier operand propagates an error.
- Exact error identity succeeds; distinct nominal error types with the same short name fail; generic substitutions preserve exact error identity.
- Reject propagation in void/non-Result functions, mismatched error types, policies, tests and other unsupported callable contexts.
- Verify nested blocks, loops and match arms propagate to the enclosing function; when closures arrive, verify propagation stays inside the closure.
- Verify `Result<void,E>` follows the explicit supported/excluded decision.
- Verify both success and failure paths satisfy definite-return and reachability analysis.
- Verify pointer-bearing success/error payloads remain GC-reachable during and after lowering.
- Verify parser precedence and malformed postfix cases, including interaction with optional type suffixes.
- Verify emitted C is warning-free and behaviour is identical under supported GCC/Clang optimisation levels.

These requirements define the acceptance contract; they do not claim `Result` or `?` is implemented in the current compiler.

## 24. Compiler phase barriers: no partially checked generic or Result code reaches C

The design states that code generation consumes only fully checked concrete instantiations. This must be an enforceable compiler invariant, not an informal ordering convention.

### 24.1 Explicit phase state

Use a distinct checked-program/instantiation representation or explicit phase marker. A concrete instantiation may become codegen-eligible only after all of the following have succeeded:

1. Type substitution completed with no unresolved type variables.
2. All substituted signatures, fields, enum payloads and bodies type-check.
3. All generic bounds and concrete interface obligations resolve uniquely.
4. Module visibility and exported API closure checks pass.
5. Grant containment and every security qualifier/taint/secret rule pass after substitution.
6. Exhaustiveness, definite-return, Result propagation and other control-flow checks pass.
7. Resource budgets have not been exceeded and all generated names/layout identities are canonical and collision-checked.

A failure in any instantiation invalidates the compilation's code-generation eligibility. Do not emit a subset of C files or functions and then report a later semantic failure as though the output were usable.

### 24.2 Whole-program emission barrier

The current `compiler/main.cap` already prints diagnostics and checks `error_count` before calling `generate` or `write_file`; it also builds the generated C as a complete string before writing it. Preserve this useful baseline invariant when adding generic instantiation: complete discovery and validation of the full root compilation closure and all reachable required instantiations before calling `generate`, and complete generation before opening or truncating the final C output path.

If future code generation is streamed, write to a temporary file and atomically publish it only after successful completion, with cleanup on failure. The current direct `write_file` path should also be reviewed for I/O-failure behaviour so an unsuccessful write cannot leave a truncated previously valid output.

The compiler must not let declaration order affect whether an instantiation is checked before emission. Interface lookup, generic recursion discovery and visibility analysis must be complete before code generation starts.

### 24.3 Determinism and resource accounting

All instantiation and obligation queues must have deterministic ordering based on canonical declaration/type identities, not hash-map iteration or import order. Enforce one aggregate resource budget across the entire compilation in addition to per-template depth/count limits: total unique instantiations, total substituted type nodes, total obligation resolutions and total checker work. Budget exhaustion is a normal diagnostic and must leave no published partial output.

### 24.4 Required adversarial tests

- A valid early instantiation followed by an invalid later instantiation produces no final C output.
- A generic function body that is abstractly invalid is rejected even if no current call instantiates it.
- A later concrete instantiation exposing a hidden error prevents all code emission.
- An unresolved interface obligation, private-type leak, Grant escape or Result control-flow error prevents output.
- Resource exhaustion at each aggregate budget boundary is deterministic and leaves no partial output.
- Permuting source/import order produces identical instantiation order, diagnostics and generated C.
- Bootstrap and self-hosted compiler agree on phase transitions and emission eligibility.
- A failed compile preserves any previously published output rather than truncating it before validation completes.

These are compiler acceptance gates, not claims about the current implementation.


## 25. Generic Result storage must preserve Grant non-escape and payload security

`Result<T,E>` is proposed as a generic enum, so its `Ok(T)` and `Err(E)` payloads are ordinary enum storage. The existing language forbids grants in enum values, struct fields, collections, constants and function returns. Generic substitution must not create a loophole around those existing lifetime rules.

### 25.1 Apply storage policy after substitution

For every concrete `Result<T,E>` instantiation, recursively evaluate both substituted payload types using the same bounded, cycle-safe Grant-containment predicate required elsewhere:

- Reject `Result<Grant<P>,E>` and `Result<T,Grant<P>>`.
- Reject nested forms such as `Result<List<Grant<P>>,E>`, `Result<T,PublicBox<Grant<P>>>` and any nominal field path that reaches a Grant.
- Reject `Result<..., ...>` when either payload's Grant status is Unknown; unknown is not proof of grant-freedom.
- Apply the same rule to user-defined generic enums and structs, not just the standard `Result` declaration.
- Do not special-case `Result` as safe because propagation returns its Err branch unchanged.

This is a storage/lifetime rule, not merely a restriction on using `?`. A value may be constructed, returned, passed or nested without ever applying postfix propagation, so all construction and storage boundaries must enforce it.

### 25.2 Preserve non-Grant payload qualifiers and reachability

Substitution must preserve the exact payload type and existing security semantics. In particular, it must not widen `Tainted` to `string`, reinterpret `Secret` as printable data, or merge `Html`/`LogText` with ordinary strings. If Secret is permitted as a Result payload, its allocation and wipe-on-reclamation rules remain in force through enum construction, matching, return and propagation. Any pointer-bearing enum payload must remain visible to the GC.

### 25.3 Required adversarial tests

- Reject direct Grant in either Result payload position.
- Reject Grant nested under collection, optional, struct, enum and multiple generic layers.
- Reject unresolved/opaque payload layouts whose Grant status is Unknown.
- Verify the same recursive predicate is used for user-defined generic enum/struct storage, constants, collection elements, returns and closure captures.
- Verify `Result<Secret,E>` and `Result<T,Secret>` preserve Secret restrictions and GC reachability if those instantiations are supported.
- Verify Tainted/Html/LogText payloads retain exact qualifiers through Ok, Err, match and `?`.
- Verify error propagation does not create a Grant escape or bypass the normal return/storage checks.

These are acceptance requirements for generic enum substitution and Result; they do not claim either feature is implemented.


## 26. Generic enum constructors must agree with the inference contract

The proposed `Result<T,E>` exposes a concrete inference edge case. A constructor for `Ok(T)` observes only `T`; a constructor for `Err(E)` observes only `E`. Neither payload uniquely determines the other type parameter. If generic inference is based only on value arguments and does not use expected return types, both constructors are underdetermined unless the caller supplies the missing type argument.

### 26.1 Choose one explicit rule

For v0.5, prefer requiring explicit type arguments whenever variant payloads do not determine every generic enum parameter. Using the proposed turbofish direction from section 21, the syntax could be:

```capstan
Result::<int, ReadError>.Ok(42)
Result::<int, ReadError>.Err(err)
```

The exact surface grammar may differ, but it must resolve the enum declaration and its full type-argument vector before variant lookup. Do not infer the missing parameter from an enclosing variable declaration, function return type, later match, or other expected-type context unless the language separately specifies and tests that as a distinct inference feature.

If the design chooses contextual inference for enum constructors instead, document it as an explicit, bounded exception to the general inference rule: define the source of the expected type, ambiguity/conflict handling, visibility checks and exact qualifier preservation. Do not leave this as implementation discretion.

### 26.2 Constructor and pattern identity

- Resolve a variant constructor against the exact generic enum declaration identity and concrete argument vector.
- Check each payload against the corresponding fully substituted variant field type.
- Reject wrong arity, missing generic arguments, excess arguments and any unresolved type parameter.
- Pattern matching derives the concrete enum arguments from the scrutinee type; it must not independently infer or widen them from pattern bindings.
- Variant names with the same spelling in different enum declarations must remain distinct.
- The generic enum constructor path must apply the same Grant-containment and visibility checks as any other enum construction.

### 26.3 Required adversarial tests

- Construct both `Ok` and `Err` with explicit full generic arguments.
- Reject `Ok(value)` and `Err(error)` when a generic argument remains underdetermined under the chosen rule.
- Verify no expected-return-type or later-assignment inference occurs accidentally.
- Verify explicit constructor arguments preserve `Tainted`, `Secret`, `Html`, `LogText` and nominal error identities exactly.
- Reject wrong enum identity, arity and payload type after substitution.
- Verify pattern bindings inherit the exact concrete payload types from the scrutinee.
- Verify generic enum constructors cannot store Grant directly or through nested payload types.

This is a design and acceptance requirement; it does not claim generic enum construction exists in the current compiler.
