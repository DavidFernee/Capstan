# Source-language type-safety assurance programme

**Status:** active; initial Lean model added, not yet verified against the production compiler.  
**Owner:** Capstan maintainers.  
**Scope:** the Safe source-language profile, with explicit exclusions for every unproved feature.

This programme separates three claims that must not be conflated:

1. **Checker soundness:** every source program accepted by the production checker satisfies the formal typing judgement.
2. **Semantic preservation:** every execution step of an accepted program preserves the typing invariant, or terminates in a specified result/trap.
3. **Implementation refinement:** the production compiler, generated code, runtime and supported native backends implement the semantics used by the proof.

A theorem about a mathematical model is not a theorem about the compiler until a reviewed correspondence argument connects the implementation to that model.

## Initial formal slice (TS.1)

`verification/lean/CapstanVerification/SourceCore.lean` introduces an intentionally small closed-expression model and states preservation, progress and determinism. It is a proof-development foothold only.

**Included:** integer and boolean literals; conditionals whose condition is represented as a boolean literal; exact branch-type agreement.

**Excluded:** variables and environments; functions and calls; arithmetic and machine overflow; strings and collections; optionals; nominal declarations; taint, secret, HTML/log/JSON context types; grants and capabilities; mutation; IO; imports; parser/checker/codegen correspondence.

The restricted conditional form is deliberate for this first proof slice: it avoids silently claiming evaluation-context or environment lemmas that have not been formalised. It must be generalised before it can serve as the language-level theorem.

## Required theorem ladder

| Gate | Required result | Evidence needed | Status |
|---|---|---|---|
| TS.1 | Core progress and preservation | Lean declarations, clean CI build, axiom audit, independent checker replay | Model introduced; exact-head CI pending |
| TS.2 | Expression typing uniqueness and full conditional evaluation | Contextual small-step semantics; nested conditions; preservation/progress | Not started |
| TS.3 | Variables, lexical environments, `let`, functions and calls | Environment typing; substitution or store typing; call/return preservation | Not started |
| TS.4 | Production checker soundness | Formal judgement plus executable checker-to-judgement correspondence; parser AST coverage | Not started |
| TS.5 | Security qualifier preservation | Formal kinds for Tainted, Secret, Html, LogText, JsonText and Grant; no implicit qualifier erasure | Not started |
| TS.6 | Aggregate and generic soundness | Substitution totality; recursive grant containment; invariant type arguments; termination/resource bounds | Not started |
| TS.7 | Runtime and backend preservation | Typed runtime value relation; codegen simulation; C/native boundary contracts; bootstrap equivalence | Not started |
| TS.8 | Independent evidence | Pinned Lean build, axiom audit, independent proof replay, negative controls and adversarial tests | CI integration pending |

## Non-negotiable invariants

- No implicit cast, coercion, unchecked deserialisation or backend conversion may erase a security qualifier.
- A value's runtime representation must satisfy its declared source type at every observable boundary.
- Every successful evaluation step preserves the typing invariant; stuck states are impossible for well-typed programs except for explicitly specified traps, divergence or resource exhaustion.
- Every type constructor that can contain values participates recursively in qualifier and capability containment checks.
- Generic substitution must preserve exact nominal identity and all security-relevant type kinds.
- Generated code and runtime helpers are part of the trusted computing base until their refinement obligations are discharged.
- Tests, fuzzing and static analysis are necessary supporting evidence, but do not replace theorems.

## Dependencies and related work

- [Issue #232](https://github.com/DavidFernee/Capstan/issues/232): password provenance. A name-based heuristic is not a type-safety theorem; first-class password provenance must be represented in the formal qualifier model.
- [Issue #250](https://github.com/DavidFernee/Capstan/issues/250): typed JSON fragments and sinks. JSON fragment/document context must not be erased into ordinary strings.
- [docs/TYPE-SYSTEM-ASSURANCE.md](../TYPE-SYSTEM-ASSURANCE.md): existing implementation inventory and generic acceptance matrix.
- [formal/OBLIGATIONS.md](../../formal/OBLIGATIONS.md): existing allocator/GC proof ledger. Keep source-language obligations separate from memory-manager model claims.

## Release claim policy

Until TS.4 and TS.7 are discharged, Capstan must not claim that the production compiler is formally type-safe. The accurate claim is that selected properties of a restricted formal model are machine-checked, while implementation correspondence remains open.

Promotion from model-only to implementation-verified requires an exact implementation revision, reproducible proof run, complete assumptions/axiom inventory, reviewed refinement relation, and adversarial regression tests on the exact PR head.
