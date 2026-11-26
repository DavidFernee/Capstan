# Transaction typestate core: formal model

**Status:** bounded Lean policy/semantics model; not a compiler feature.

This is the first formal slice for issue #325. It defines a transaction protocol
with phases `open`, `prepared`, `commitDecided`, `committed`, `aborted`
and `released`. Operations are admitted only where the transition function
defines them.

The model rejects:
- a second commit after the transaction is committed;
- abort after the irreversible commit decision;
- writes after prepare;
- use after release;
- a context containing two owner entries with the same resource identity.

A successful context transition changes only the resource's typestate. The
Lean theorems establish that the list of owner identities is unchanged and
that the no-duplicate-owner invariant is preserved. A malformed context with
duplicate identities fails closed.

## Critical evidence boundary

This is a finite protocol and typing-context model. It does not yet establish
that Capstan source syntax can express this typing context, that the compiler
tracks moves across branches/loops/closures/generics/imports, or that lowering
and generated code preserve the model. It does not implement transactions or
prove database/OS transaction semantics.

The next implementation gates are:
1. Define source-level move/consume rules and branch-join behaviour.
2. Add compiler rejection fixtures for the five cases in issue #325.
3. Prove type preservation and progress for the ownership/typestate typing
   rules, including generic substitution and module boundaries.
4. Connect compiler acceptance decisions and CCAM execution to this model.
5. Specify runtime commit atomicity, crash recovery and external-system
   assumptions separately; a type system cannot prove those by itself.

No safe-profile enforcement or end-to-end soundness claim is made by this
model alone.
