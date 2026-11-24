# CCAM progress theorem — current result and boundary

**Status:** machine-checked candidate theorem; whole-program progress remains incomplete  
**Proof branch:** `verification/ccam-formal-core-stacked`  
**Module:** `verification/lean/CapstanVerification/Progress.lean`  
**Semantic authority:** `docs/architecture/CCAM.md`

## Result added

The current finite, single-frame CCAM evaluator is a total Lean function over intrinsically bounded program counters, finite register indices, and intrinsically well-typed machine states. The new module states and proves:

- `machineStep_progress_or_explicit_outcome`: every state in this model yields exactly one of a continuation, value halt, void halt, or explicit trap.
- `machineStep_deterministic`: two results of the same functional step are equal.
- `machineStep_progress_preserves_register_types`: every continuing state retains the register typing invariant.
- `machineStep_progress_preserves_pc_bounds`: every continuing state has an in-range PC.
- `runFuel_fuel_exhausted_state_well_typed`: bounded meta-level execution preserves the register invariant in its residual state.

The bounded evaluator's `fuelExhausted` result is a proof/exploration bound, not a CCAM runtime trap. It must not be conflated with the specified `step_limit_exceeded` outcome.

## Exact scope limitation

These results close the progress classification only for the existing finite, single-frame instruction fragment. They do **not** establish progress for complete CCAM programs. The model still lacks:

- a validated finite multi-function program and function-name lookup;
- call instructions and statically checked call signatures;
- argument evaluation and callee-frame construction;
- caller continuation/destination invariants;
- atomic return and caller restoration integrated into execution;
- whole-program validator soundness and the proof that validation establishes the model's premises;
- source/CCAM implementation correspondence.

The theorem is therefore not evidence that arbitrary well-typed Capstan programs are safe. The single-frame model's totality is partly guaranteed by its representation: register/PC indices use `Fin`, instruction constructors carry static type equalities, and state construction requires a register-typing proof. The validator-to-model bridge is still a separate obligation.

## Next proof tranche

1. Define a dependent multi-function CCAM program model without weakening the normative CCAM schema.
2. Define function signatures, register files, instructions, frame continuations and caller destinations.
3. State validated-program invariants for unique function names, valid PCs, in-range registers/targets, argument arity/types, return types and control-flow termination/fall-through.
4. Define total small-step transitions for calls and returns. Calls must read arguments left-to-right, check depth before push, and advance the caller continuation; returns must validate the result and caller destination before one atomic pop-and-write.
5. Prove preservation for each frame and whole-stack invariant, then progress-or-explicit-trap and determinism for validated configurations.
6. Prove validator soundness: every accepted CCAM document decodes to a value satisfying the formal validated-program predicate.
7. Establish a separate refinement argument from the Capstan-native CCAM evaluator to this model.

No claim is made that these steps are complete. The normative specification remains authoritative; if its call/return details are ambiguous, resolve them with the language-semantics owner before formalising a choice.
