import CapstanVerification.Machine

namespace CapstanVerification

/-!
Progress and finite-execution results for the current finite, single-frame
CCAM fragment.

This module deliberately does NOT claim whole-CCAM progress: MachineInstr has
no call constructor and the model has no validated multi-function program.
It proves that the current evaluator is total over its intrinsically bounded,
well-typed state space, and that every one-step result is a continuation,
successful halt, void halt, or explicit trap.
-/

/-- Every current-fragment machine state has a classified one-step outcome. -/
theorem machineStep_progress_or_explicit_outcome
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : MachineState n m types) :
    (∃ next, machineStep program state = .nextState next) ∨
    (∃ value, machineStep program state = .halt value) ∨
    machineStep program state = .haltVoid ∨
    (∃ reason, machineStep program state = .trap reason) := by
  cases hstep : machineStep program state with
  | nextState next =>
      exact Or.inl ⟨next, rfl⟩
  | halt value =>
      exact Or.inr (Or.inl ⟨value, rfl⟩)
  | haltVoid =>
      exact Or.inr (Or.inr (Or.inl rfl))
  | trap reason =>
      exact Or.inr (Or.inr (Or.inr ⟨reason, rfl⟩))

/-- The functional one-step semantics is deterministic. -/
theorem machineStep_deterministic
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : MachineState n m types)
    (left right : MachineOutcome n m types)
    (hleft : machineStep program state = left)
    (hright : machineStep program state = right) :
    left = right :=
  hleft.symm.trans hright

/-- Result of executing at most a fixed number of single-frame instructions. -/
inductive BoundedExecutionResult (n m : Nat) (types : RegTypes n) where
  | fuelExhausted (state : MachineState n m types)
  | halt (value : Val)
  | haltVoid
  | trap (reason : Trap)

/-- Meta-fuel-bounded evaluator used to make Lean execution structurally recursive.
Exhausting this recursion fuel is not a CCAM machine trap. The separate
`budgetedMachineStep` below models the normative instruction budget: it
consumes one step before each instruction, traps before executing when the
budget is exhausted, and charges a step to instructions that halt or trap. -/
def runFuel {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types) :
    Nat → MachineState n m types → BoundedExecutionResult n m types
  | 0, state => .fuelExhausted state
  | fuel + 1, state =>
      match machineStep program state with
      | .nextState next => runFuel program fuel next
      | .halt value => .halt value
      | .haltVoid => .haltVoid
      | .trap reason => .trap reason

/-- If bounded execution exhausts its meta-level fuel, the residual state is well typed. -/
theorem runFuel_fuel_exhausted_state_well_typed
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (fuel : Nat)
    (state final : MachineState n m types)
    (h : runFuel program fuel state = .fuelExhausted final) :
    WellTyped types final.registers := by
  induction fuel generalizing state with
  | zero =>
      simp [runFuel] at h
      cases h
      exact MachineState.registers_well_typed final
  | succ fuel ih =>
      simp only [runFuel] at h
      cases hstep : machineStep program state with
      | nextState next =>
          exact ih next (by simpa [hstep] using h)
      | halt value =>
          simp [hstep] at h
      | haltVoid =>
          simp [hstep] at h
      | trap reason =>
          simp [hstep] at h

end CapstanVerification
