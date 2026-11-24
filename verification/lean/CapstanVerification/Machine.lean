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

/-- Instructions whose control effect is explicit and cannot fall through. -/
def HasExplicitControlEffect {n m : Nat} {types : RegTypes n} :
    MachineInstr n m types → Prop
  | .jump _ => True
  | .branch _ => True
  | .retInt _ _ => True
  | .retBool _ _ => True
  | .retVoid => True
  | .explicitTrap _ => True
  | _ => False

/-- The executable terminal predicate exactly characterizes explicit control effects. -/
theorem machineInstrIsTerminal_iff_control_effect
    {n m : Nat} {types : RegTypes n}
    (instr : MachineInstr n m types) :
    machineInstrIsTerminal instr = true ↔ HasExplicitControlEffect instr := by
  cases instr <;> simp [machineInstrIsTerminal, HasExplicitControlEffect]

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
  unfold consumeStep at h
  by_cases hlimit : budget.used < budget.limit
  · simp [hlimit] at h
    cases h
    exact Nat.succ_le_of_lt hlimit
  · simp [hlimit] at h

/-- An exhausted budget traps before another instruction can be consumed. -/
theorem consumeStep_exhausted_traps
    (budget : StepBudget)
    (h : budget.limit ≤ budget.used) :
    consumeStep budget = .error .instructionLimit := by
  unfold consumeStep
  have hnot : ¬ budget.used < budget.limit := Nat.not_lt.mpr h
  simp [hnot]

/-- A non-empty call stack with an intrinsic maximum-depth invariant. -/
structure CallStack (Frame : Type) where
  frames : List Frame
  maxDepth : Nat
  nonempty : frames ≠ []
  within_limit : frames.length ≤ maxDepth

/-- Start execution with the entry frame at depth one. -/
def initialCallStack {Frame : Type}
    (entry : Frame) (maxDepth : Nat) (hmax : 1 ≤ maxDepth) : CallStack Frame :=
  { frames := [entry]
    maxDepth := maxDepth
    nonempty := by simp
    within_limit := by simpa using hmax }

/-- Push a callee frame, trapping before the push if it would exceed maxDepth. -/
def pushCallFrame {Frame : Type}
    (stack : CallStack Frame) (callee : Frame) : Except Trap (CallStack Frame) :=
  if hdepth : stack.frames.length < stack.maxDepth then
    .ok {
      frames := callee :: stack.frames
      maxDepth := stack.maxDepth
      nonempty := by simp
      within_limit := by
        simp
        exact Nat.succ_le_of_lt hdepth
    }
  else
    .error .callDepthLimit

/-- A successful call-frame push places the callee at the top of the stack. -/
theorem pushCallFrame_top
    {Frame : Type} (stack : CallStack Frame) (callee : Frame)
    (next : CallStack Frame)
    (h : pushCallFrame stack callee = .ok next) :
    next.frames.head? = some callee := by
  unfold pushCallFrame at h
  by_cases hdepth : stack.frames.length < stack.maxDepth
  · simp [hdepth] at h
    cases h
    simp
  · simp [hdepth] at h

/-- A successful call-frame push increases the stack depth by exactly one. -/
theorem pushCallFrame_increments_depth
    {Frame : Type} (stack : CallStack Frame) (callee : Frame)
    (next : CallStack Frame)
    (h : pushCallFrame stack callee = .ok next) :
    next.frames.length = stack.frames.length + 1 := by
  unfold pushCallFrame at h
  by_cases hdepth : stack.frames.length < stack.maxDepth
  · simp [hdepth] at h
    cases h
    simp
  · simp [hdepth] at h

/-- Every successful push remains within the configured call-depth limit. -/
theorem pushCallFrame_within_limit
    {Frame : Type} (stack : CallStack Frame) (callee : Frame)
    (next : CallStack Frame)
    (h : pushCallFrame stack callee = .ok next) :
    next.frames.length ≤ stack.maxDepth := by
  unfold pushCallFrame at h
  by_cases hdepth : stack.frames.length < stack.maxDepth
  · simp [hdepth] at h
    cases h
    simp
    exact Nat.succ_le_of_lt hdepth
  · simp [hdepth] at h

/-- Pop a nested callee and return the remaining caller stack.

The singleton entry frame is deliberately not popped here: returning from the
entry function is a halt, handled by the enclosing machine semantics.
-/
def popNestedCallFrame {Frame : Type}
    (stack : CallStack Frame) : Except Trap (Frame × List Frame) :=
  match stack.frames with
  | callee :: caller :: rest => .ok (callee, caller :: rest)
  | _ => .error .invalidControlFlow

/-- A successful nested return restores the caller at the top of the frame list. -/
theorem popNestedCallFrame_restores_caller
    {Frame : Type} (stack : CallStack Frame)
    (result : Frame × List Frame)
    (callee caller : Frame) (rest : List Frame)
    (hframes : stack.frames = callee :: caller :: rest)
    (h : popNestedCallFrame stack = .ok result) :
    result.2.head? = some caller := by
  simp [popNestedCallFrame, hframes] at h
  cases h
  rfl

/-- A successful nested return decreases call depth by exactly one. -/
theorem popNestedCallFrame_decreases_depth
    {Frame : Type} (stack : CallStack Frame)
    (result : Frame × List Frame)
    (h : popNestedCallFrame stack = .ok result) :
    result.2.length + 1 = stack.frames.length := by
  cases hframes : stack.frames with
  | nil =>
      simp [popNestedCallFrame, hframes] at h
  | cons first tail =>
      cases htail : tail with
      | nil =>
          simp [popNestedCallFrame, hframes, htail] at h
      | cons second rest =>
          simp [popNestedCallFrame, hframes, htail] at h
          cases h
          simp

/-- A successful nested return remains within the configured call-depth limit. -/
theorem popNestedCallFrame_within_limit
    {Frame : Type} (stack : CallStack Frame)
    (result : Frame × List Frame)
    (h : popNestedCallFrame stack = .ok result) :
    result.2.length ≤ stack.maxDepth := by
  have hdepth := popNestedCallFrame_decreases_depth stack result h
  have hlt : result.2.length < stack.frames.length := by
    rw [← hdepth]
    exact Nat.lt_succ_self _
  exact Nat.le_trans (Nat.le_of_lt hlt) stack.within_limit

/-- The entry frame is retained; its return is not a nested stack pop. -/
theorem popNestedCallFrame_entry_refused
    {Frame : Type} (entry : Frame) (stack : CallStack Frame)
    (hentry : stack.frames = [entry]) :
    popNestedCallFrame stack = .error .invalidControlFlow := by
  simp [popNestedCallFrame, hentry]

/-- A full call stack traps before another frame is pushed. -/
theorem pushCallFrame_exhausted_traps
    {Frame : Type} (stack : CallStack Frame) (callee : Frame)
    (hfull : stack.maxDepth ≤ stack.frames.length) :
    pushCallFrame stack callee = .error .callDepthLimit := by
  unfold pushCallFrame
  have hnot : ¬ stack.frames.length < stack.maxDepth := Nat.not_lt.mpr hfull
  simp [hnot]

/-- The final instruction cannot fall through to a sequential successor. -/
theorem finiteProgram_final_instruction_has_control_effect
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types) :
    HasExplicitControlEffect (program.code (Fin.last m)) :=
  (machineInstrIsTerminal_iff_control_effect _).mp program.last_is_terminal

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

/-- Sequential execution advances by one slot before the final instruction. -/
theorem sequentialPC_increments_before_last
    {m : Nat} (pc : Fin (m + 1)) (h : pc.val < m) :
    (sequentialPC pc).val = pc.val + 1 := by
  unfold sequentialPC
  simp [Nat.min_eq_left (Nat.succ_le_of_lt h)]

/-- The clamped sequential successor of the final slot is the final slot itself.

Well-formed programs require that slot to have an explicit control effect, so
this clamped edge is never a valid instruction fall-through.
-/
theorem sequentialPC_at_last
    {m : Nat} (pc : Fin (m + 1)) (h : pc.val = m) :
    (sequentialPC pc).val = m := by
  unfold sequentialPC
  simp [h]

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
    (budgetedMachineStep program state).budget.used ≤
      (budgetedMachineStep program state).budget.limit :=
  (budgetedMachineStep program state).budget.within_limit

/-- If budget remains, every outcome accounts for exactly one executed instruction. -/
theorem budgetedMachineStep_consumes_one
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state : BudgetedMachineState n m types)
    (havailable : state.budget.used < state.budget.limit) :
    (budgetedMachineStep program state).budget.used = state.budget.used + 1 := by
  have hconsume : consumeStep state.budget =
      .ok {
        limit := state.budget.limit
        used := state.budget.used + 1
        within_limit := Nat.succ_le_of_lt havailable
      } := by
    simp [consumeStep, havailable]
  unfold budgetedMachineStep
  rw [hconsume]
  cases hstep : machineStep program state.machine <;>
    simp [hstep, BudgetedMachineOutcome.budget]

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
