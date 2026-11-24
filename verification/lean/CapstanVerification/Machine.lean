import CapstanVerification.Core

namespace CapstanVerification

/-!
A finite, single-frame CCAM control-flow machine.

This is an intrinsically typed proof model: register indices and control-flow
targets are Fin values, and scalar instructions carry their static type
obligations. It is a finite control-flow slice, not yet the complete CCAM
validator/evaluator: calls, frame stacks, resource counters and source lowering
remain outside this model.
-/

/-- The initial finite control-flow instruction fragment. -/
inductive MachineInstr (n m : Nat) (types : RegTypes n) where
  | constInt (dst : Fin n) (value : Int)
      (dst_is_int : types dst = .int) (value_in_range : inI64 value)
  | constBool (dst : Fin n) (value : Bool)
      (dst_is_bool : types dst = .bool)
  | move (instr : MoveInstr n types)
  | add (instr : AddInstr n types)
  | sub (instr : CheckedIntInstr n types)
  | mul (instr : CheckedIntInstr n types)
  | div (instr : CheckedIntInstr n types)
  | rem (instr : CheckedIntInstr n types)
  | lessThan (instr : LtInstr n types)
  | equal (instr : EqInstr n types)
  | booleanNot (instr : NotInstr n types)
  | jump (target : Fin m)
  | branch (instr : BranchInstr n m types)
  | retInt (src : Fin n) (src_is_int : types src = .int)
  | retBool (src : Fin n) (src_is_bool : types src = .bool)
  | retVoid
  | explicitTrap (reason : Trap)

/-- Whether an instruction transfers control or terminates rather than falling through. -/
def machineInstrIsTerminal {n m : Nat} {types : RegTypes n} :
    MachineInstr n m types → Bool
  | .jump _ => true
  | .branch _ => true
  | .retInt _ _ => true
  | .retBool _ _ => true
  | .retVoid => true
  | .explicitTrap _ => true
  | _ => false

/-- A finite instruction table indexed by Fin, with intrinsically valid entry and targets. -/
structure FiniteProgram (n m : Nat) (types : RegTypes n) where
  code : Fin (m + 1) → MachineInstr n (m + 1) types
  entry : Fin (m + 1)
  last_is_terminal :
    machineInstrIsTerminal (code (Fin.last m)) = true

/-- The deterministic instruction budget from the CCAM resource contract. -/
structure StepBudget where
  limit : Nat
  used : Nat
  within_limit : used ≤ limit

/-- Consume one instruction slot, trapping before execution when the budget is exhausted. -/
def consumeStep (budget : StepBudget) : Except Trap StepBudget :=
  if hlimit : budget.used < budget.limit then
    .ok {
      limit := budget.limit
      used := budget.used + 1
      within_limit := Nat.succ_le_of_lt hlimit
    }
  else
    .error .instructionLimit

/-- A successful budget consumption increments the counter exactly once. -/
theorem consumeStep_increments
    (budget : StepBudget) (next : StepBudget)
    (h : consumeStep budget = .ok next) :
    next.used = budget.used + 1 := by
  unfold consumeStep at h
  by_cases hlimit : budget.used < budget.limit
  · simp [hlimit] at h
    cases h
    rfl
  · simp [hlimit] at h

/-- A successful budget consumption never exceeds the configured maximum. -/
theorem consumeStep_within_limit
    (budget : StepBudget) (next : StepBudget)
    (h : consumeStep budget = .ok next) :
    next.used ≤ budget.limit := by
  exact next.within_limit

/-- An exhausted budget traps before another instruction can be consumed. -/
theorem consumeStep_exhausted_traps
    (budget : StepBudget)
    (h : budget.limit ≤ budget.used) :
    consumeStep budget = .error .instructionLimit := by
  unfold consumeStep
  have hnot : ¬ budget.used < budget.limit := Nat.not_lt.mpr h
  simp [hnot]

/-- A running state for the single-frame machine. -/
structure MachineState (n m : Nat) (types : RegTypes n) where
  pc : Fin (m + 1)
  registers : Registers n
  registers_well_typed : WellTyped types registers

/-- Construct the initial machine state at the program's declared entry point. -/
def initialMachineState {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (registers : Registers n)
    (hregisters : WellTyped types registers) : MachineState n m types :=
  { pc := program.entry
    registers := registers
    registers_well_typed := hregisters }

/-- Every step either advances, halts, or produces a defined explicit trap. -/
inductive MachineOutcome (n m : Nat) (types : RegTypes n) where
  | nextState (state : MachineState n m types)
  | halt (value : Val)
  | haltVoid
  | trap (reason : Trap)

/-- Advance one instruction, clamping only at the final slot.

The program invariant requires the final slot to be a jump, branch, return or
trap, so a well-formed program never uses the clamped sequential edge.
-/
def sequentialPC {m : Nat} (pc : Fin (m + 1)) : Fin (m + 1) :=
  ⟨min (pc.val + 1) m, Nat.lt_succ_of_le (Nat.min_le_right _ _)⟩

/-- Total small-step semantics for the finite, typed, single-frame fragment. -/
def machineStep {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types) (state : MachineState n m types) :
    MachineOutcome n m types :=
  match program.code state.pc with
  | .constInt dst value hdst hvalue =>
      .nextState {
        pc := sequentialPC state.pc
        registers := write state.registers dst (.int value)
        registers_well_typed := write_preserves_well_typed
          state.registers_well_typed dst (.int value) (by
            simpa [hasType, hasTypeB, hdst, inI64] using hvalue)
      }
  | .constBool dst value hdst =>
      .nextState {
        pc := sequentialPC state.pc
        registers := write state.registers dst (.bool value)
        registers_well_typed := write_preserves_well_typed
          state.registers_well_typed dst (.bool value) (by
            simp [hasType, hasTypeB, hdst])
      }
  | .move instr =>
      match hmove : executeMove state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeMove_preserves_well_typed state.registers_well_typed instr hmove
          }
  | .add instr =>
      match hadd : executeAdd state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeAdd_preserves_well_typed state.registers_well_typed instr hadd
          }
  | .sub instr =>
      match hsub : executeCheckedIntOp subIntOp state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeCheckedIntOp_preserves_well_typed
                state.registers_well_typed subIntOp instr hsub
          }
  | .mul instr =>
      match hmul : executeCheckedIntOp mulIntOp state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeCheckedIntOp_preserves_well_typed
                state.registers_well_typed mulIntOp instr hmul
          }
  | .div instr =>
      match hdiv : executeCheckedIntOp divIntOp state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeCheckedIntOp_preserves_well_typed
                state.registers_well_typed divIntOp instr hdiv
          }
  | .rem instr =>
      match hrem : executeCheckedIntOp remIntOp state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeCheckedIntOp_preserves_well_typed
                state.registers_well_typed remIntOp instr hrem
          }
  | .lessThan instr =>
      match hlt : executeLt state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeLt_preserves_well_typed state.registers_well_typed instr hlt
          }
  | .equal instr =>
      match heq : executeEq state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeEq_preserves_well_typed state.registers_well_typed instr heq
          }
  | .booleanNot instr =>
      match hnot : executeNot state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .nextState {
            pc := sequentialPC state.pc
            registers := registers
            registers_well_typed :=
              executeNot_preserves_well_typed state.registers_well_typed instr hnot
          }
  | .jump target =>
      .nextState { state with pc := target }
  | .branch instr =>
      match executeBranch state.registers instr with
      | .error e => .trap e
      | .ok target => .nextState { state with pc := target }
  | .retInt src _ =>
      match readInt state.registers src with
      | .error e => .trap e
      | .ok value => .halt (.int value)
  | .retBool src _ =>
      match readBool state.registers src with
      | .error e => .trap e
      | .ok value => .halt (.bool value)
  | .retVoid => .haltVoid
  | .explicitTrap reason => .trap reason

/-- A machine state paired with a valid instruction budget. -/
structure BudgetedMachineState (n m : Nat) (types : RegTypes n) where
  machine : MachineState n m types
  budget : StepBudget

/-- Outcomes retain the post-transition budget, including when execution halts or traps. -/
inductive BudgetedMachineOutcome (n m : Nat) (types : RegTypes n) where
  | nextState (state : BudgetedMachineState n m types)
  | halt (value : Val) (budget : StepBudget)
  | haltVoid (budget : StepBudget)
  | trap (reason : Trap) (budget : StepBudget)

/-- Extract the budget after any budgeted transition outcome. -/
def BudgetedMachineOutcome.budget {n m : Nat} {types : RegTypes n} :
    BudgetedMachineOutcome n m types → StepBudget
  | .nextState state => state.budget
  | .halt _ budget => budget
  | .haltVoid budget => budget
  | .trap _ budget => budget

/-- Execute one machine instruction under the CCAM instruction budget.

The budget is consumed before instruction execution. A limit trap therefore
does not execute the next instruction; dynamic traps and halts retain the
already-consumed budget for the instruction that produced them.
-/
def budgetedMachineStep {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : BudgetedMachineState n m types) :
    BudgetedMachineOutcome n m types :=
  match consumeStep state.budget with
  | .error reason => .trap reason state.budget
  | .ok nextBudget =>
      match machineStep program state.machine with
      | .nextState next =>
          .nextState { machine := next, budget := nextBudget }
      | .halt value => .halt value nextBudget
      | .haltVoid => .haltVoid nextBudget
      | .trap reason => .trap reason nextBudget

/-- Budgeted transitions preserve the intrinsic register-typing invariant. -/
theorem budgetedMachineStep_preserves_well_typed
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : BudgetedMachineState n m types) :
    match budgetedMachineStep program state with
    | .nextState next => WellTyped types next.machine.registers
    | .halt _ _ => True
    | .haltVoid _ => True
    | .trap _ _ => True := by
  unfold budgetedMachineStep
  cases hbudget : consumeStep state.budget with
  | error reason =>
      simp [hbudget]
  | ok nextBudget =>
      cases hstep : machineStep program state.machine with
      | nextState next =>
          simp [hbudget, hstep]
          exact next.registers_well_typed
      | halt value =>
          simp [hbudget, hstep]
      | haltVoid =>
          simp [hbudget, hstep]
      | trap reason =>
          simp [hbudget, hstep]

/-- Every budgeted outcome retains a budget within its configured maximum. -/
theorem budgetedMachineStep_budget_within_limit
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : BudgetedMachineState n m types) :
    (budgetedMachineStep program state).budget.within_limit := by
  unfold budgetedMachineStep BudgetedMachineOutcome.budget
  cases hbudget : consumeStep state.budget with
  | error reason =>
      simp [hbudget]
  | ok nextBudget =>
      cases hstep : machineStep program state.machine <;> simp [hbudget, hstep]

/-- If budget remains, every outcome accounts for exactly one executed instruction. -/
theorem budgetedMachineStep_consumes_one
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : BudgetedMachineState n m types)
    (havailable : state.budget.used < state.budget.limit) :
    (budgetedMachineStep program state).budget.used = state.budget.used + 1 := by
  unfold budgetedMachineStep BudgetedMachineOutcome.budget consumeStep
  simp [havailable]

/-- An exhausted budget traps before the next machine instruction is executed. -/
theorem budgetedMachineStep_exhausted_before_instruction
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : BudgetedMachineState n m types)
    (hexhausted : state.budget.limit ≤ state.budget.used) :
    budgetedMachineStep program state = .trap .instructionLimit state.budget := by
  unfold budgetedMachineStep
  rw [consumeStep_exhausted_traps state.budget hexhausted]

/-- Every continuing machine step carries a proof of register-type preservation.

The machine state is intrinsically well-typed: a transition cannot construct a
continuation without supplying its preservation proof.
-/
theorem machineStep_preserves_well_typed
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : MachineState n m types) :
    match machineStep program state with
    | .nextState next => WellTyped types next.registers
    | .halt _ => True
    | .haltVoid => True
    | .trap _ => True := by
  cases machineStep program state with
  | nextState next => exact next.registers_well_typed
  | halt value => trivial
  | haltVoid => trivial
  | trap reason => trivial

/-- Program counters are always in range by construction of the state type. -/
theorem machineState_pc_is_in_range
    {n m : Nat} {types : RegTypes n} (state : MachineState n m types) :
    state.pc.val < m + 1 :=
  state.pc.isLt

end CapstanVerification
