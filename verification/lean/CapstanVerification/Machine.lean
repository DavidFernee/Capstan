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
  registers_well_typed : WellTyped types registers

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
  ⟨min (pc.val + 1) m, by omega⟩

/-- Total small-step semantics for the finite, typed, single-frame fragment. -/
def machineStep {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types) (state : MachineState n m types) :
    MachineOutcome n m types :=
  match program.code.get state.pc with
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
  | continue next => exact next.registers_well_typed
  | halt value => trivial
  | haltVoid => trivial
  | trap reason => trivial

/-- Program counters are always in range by construction of the state type. -/
theorem machineState_pc_is_in_range
    {n m : Nat} {types : RegTypes n} (state : MachineState n m types) :
    state.pc.val < m + 1 :=
  state.pc.isLt

end CapstanVerification
