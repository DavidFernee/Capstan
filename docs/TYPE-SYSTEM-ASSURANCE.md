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
| Coherence | One implementation; repeated use of same resolved implementation | Duplicate impl in one file, duplicate across imports, overlapping impls, reverse import order | At most one applicable implementation exists across the complete compilation/link unit; source order cannot select a winner |
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

1. An `impl Interface for Type` must be declared in the module defining either `Interface` or `Type` (an orphan restriction).
2. The compiler collects implementation identities across all transitively imported modules before resolving constrained generic calls.
3. Two implementations for the same resolved pair are an error, including when they originate in separate files or are imported through different paths.
4. Import order, declaration order and file traversal order cannot affect the selected implementation.
5. There is no blanket or overlapping implementation in the initial language subset.
6. A public implementation cannot expose a private interface or implementing type through a public signature.

Required fixtures should include a three-module diamond import, two modules independently implementing the same pair, and an import-order permutation. If Capstan later supports separately compiled modules, the same uniqueness rule must be enforced at the link/package boundary; per-file checks alone are insufficient.

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
| G0 — baseline inventory | Existing compiler and tests | Generic syntax work |
| G1 — parameter identity and structural substitution | G0 | Generic structs/enums/functions |
| G2 — substituted type validation and qualifier preservation | G1 | Any generic value reaches ordinary checking |
| G3 — monomorphisation and global resource budgets | G1, G2 | Generic code generation |
| G4 — constraints and cross-module coherence | G1–G3; module identity model | Interface-constrained generic calls |
| G5 — generic exhaustiveness and payload typing | G1–G3 | Generic enum use in production code |
| G6 — Result and propagation | G1–G5 | Error propagation syntax |
| G7 — closures, capture and GC/secret rules | G1–G4; runtime support | Closure expressions and Shroud typed messages |
| G8 — bootstrap, differential, fuzz and release evidence | G1–G7 | v0.5/v0.6 release claim |

The sequence is intentionally conservative. No later feature should force a weakening of an earlier security invariant to make its API convenient.


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
