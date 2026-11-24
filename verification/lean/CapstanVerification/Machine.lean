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

/-- A finite, non-empty instruction vector with an intrinsically valid entry and targets. -/
structure FiniteProgram (n m : Nat) (types : RegTypes n) where
  code : Vector (MachineInstr n (m + 1) types) (m + 1)
  entry : Fin (m + 1)
  last_is_terminal :
    machineInstrIsTerminal (code.get (Fin.last m)) = true

/-- A running state for the single-frame machine. -/
structure MachineState (n m : Nat) (types : RegTypes n) where
  pc : Fin (m + 1)
  registers : Registers n

/-- Every step either advances, halts, or produces a defined explicit trap. -/
inductive MachineOutcome (n m : Nat) (types : RegTypes n) where
  | continue (state : MachineState n m types)
  | halt (value : Val)
  | haltVoid
  | trap (reason : Trap)

/-- Advance one instruction, clamping only at the final slot.

The program invariant requires the final slot to be a jump, branch, return or
trap, so a well-formed program never uses the clamped sequential edge.
-/
def sequentialPC {m : Nat} (pc : Fin (m + 1)) : Fin (m + 1) :=
  ⟨min (pc.val + 1) m, by omega⟩

/-- Total small-step semantics for the finite, typed, single-frame fragment. -/
def machineStep {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types) (state : MachineState n m types) :
    MachineOutcome n m types :=
  match program.code.get state.pc with
  | .constInt dst value _ _ =>
      .continue { state with
        pc := sequentialPC state.pc
        registers := write state.registers dst (.int value) }
  | .constBool dst value _ =>
      .continue { state with
        pc := sequentialPC state.pc
        registers := write state.registers dst (.bool value) }
  | .move instr =>
      match executeMove state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .continue { state with pc := sequentialPC state.pc, registers := registers }
  | .add instr =>
      match executeAdd state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .continue { state with pc := sequentialPC state.pc, registers := registers }
  | .lessThan instr =>
      match executeLt state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .continue { state with pc := sequentialPC state.pc, registers := registers }
  | .equal instr =>
      match executeEq state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .continue { state with pc := sequentialPC state.pc, registers := registers }
  | .booleanNot instr =>
      match executeNot state.registers instr with
      | .error e => .trap e
      | .ok registers =>
          .continue { state with pc := sequentialPC state.pc, registers := registers }
  | .jump target =>
      .continue { state with pc := target }
  | .branch instr =>
      match executeBranch state.registers instr with
      | .error e => .trap e
      | .ok target => .continue { state with pc := target }
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

/-- A successful nonterminal machine step preserves all initialized register types. -/
theorem machineStep_preserves_well_typed
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (state next : MachineState n m types)
    (hregisters : WellTyped types state.registers)
    (hstep : machineStep program state = .continue next) :
    WellTyped types next.registers := by
  unfold machineStep at hstep
  cases hinstr : program.code.get state.pc with
  | constInt dst value hdst hvalue =>
      simp [hinstr] at hstep
      have hregsEq : write state.registers dst (.int value) = next.registers := by
        have h := congrArg MachineState.registers hstep
        simpa using h
      rw [← hregsEq]
      have htyped : hasType (.int value) (types dst) := by
        simpa [hasType, hasTypeB, hdst, inI64] using hvalue
      exact write_preserves_well_typed hregisters dst (.int value) htyped
  | constBool dst value hdst =>
      simp [hinstr] at hstep
      have hregsEq : write state.registers dst (.bool value) = next.registers := by
        have h := congrArg MachineState.registers hstep
        simpa using h
      rw [← hregsEq]
      have htyped : hasType (.bool value) (types dst) := by
        simp [hasType, hasTypeB, hdst]
      exact write_preserves_well_typed hregisters dst (.bool value) htyped
  | move instr =>
      cases hmove : executeMove state.registers instr with
      | error e =>
          simp [hinstr, hmove] at hstep
      | ok registers =>
          simp [hinstr, hmove] at hstep
          have hregsEq : registers = next.registers := by
            have h := congrArg MachineState.registers hstep
            simpa using h
          rw [← hregsEq]
          exact executeMove_preserves_well_typed hregisters instr hmove
  | add instr =>
      cases hadd : executeAdd state.registers instr with
      | error e =>
          simp [hinstr, hadd] at hstep
      | ok registers =>
          simp [hinstr, hadd] at hstep
          have hregsEq : registers = next.registers := by
            have h := congrArg MachineState.registers hstep
            simpa using h
          rw [← hregsEq]
          exact executeAdd_preserves_well_typed hregisters instr hadd
  | lessThan instr =>
      cases hlt : executeLt state.registers instr with
      | error e =>
          simp [hinstr, hlt] at hstep
      | ok registers =>
          simp [hinstr, hlt] at hstep
          have hregsEq : registers = next.registers := by
            have h := congrArg MachineState.registers hstep
            simpa using h
          rw [← hregsEq]
          exact executeLt_preserves_well_typed hregisters instr hlt
  | equal instr =>
      cases heq : executeEq state.registers instr with
      | error e =>
          simp [hinstr, heq] at hstep
      | ok registers =>
          simp [hinstr, heq] at hstep
          have hregsEq : registers = next.registers := by
            have h := congrArg MachineState.registers hstep
            simpa using h
          rw [← hregsEq]
          exact executeEq_preserves_well_typed hregisters instr heq
  | booleanNot instr =>
      cases hnot : executeNot state.registers instr with
      | error e =>
          simp [hinstr, hnot] at hstep
      | ok registers =>
          simp [hinstr, hnot] at hstep
          have hregsEq : registers = next.registers := by
            have h := congrArg MachineState.registers hstep
            simpa using h
          rw [← hregsEq]
          exact executeNot_preserves_well_typed hregisters instr hnot
  | jump target =>
      simp [hinstr] at hstep
      have hregsEq : state.registers = next.registers := by
        have h := congrArg MachineState.registers hstep
        simpa using h
      rw [← hregsEq]
      exact hregisters
  | branch instr =>
      cases hbranch : executeBranch state.registers instr with
      | error e =>
          simp [hinstr, hbranch] at hstep
      | ok target =>
          simp [hinstr, hbranch] at hstep
          have hregsEq : state.registers = next.registers := by
            have h := congrArg MachineState.registers hstep
            simpa using h
          rw [← hregsEq]
          exact hregisters
  | retInt src hsrc =>
      cases hread : readInt state.registers src with
      | error e =>
          simp [hinstr, hread] at hstep
      | ok value =>
          simp [hinstr, hread] at hstep
  | retBool src hsrc =>
      cases hread : readBool state.registers src with
      | error e =>
          simp [hinstr, hread] at hstep
      | ok value =>
          simp [hinstr, hread] at hstep
  | retVoid =>
      simp [hinstr] at hstep
  | explicitTrap reason =>
      simp [hinstr] at hstep

/-- Program counters are always in range by construction of the state type. -/
theorem machineState_pc_is_in_range
    {n m : Nat} {types : RegTypes n} (state : MachineState n m types) :
    state.pc.val < m + 1 :=
  state.pc.isLt

end CapstanVerification
