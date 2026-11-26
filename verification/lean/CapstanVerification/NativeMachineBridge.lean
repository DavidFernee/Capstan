import CapstanVerification.NativeRegisterFileBridge
import CapstanVerification.Machine

namespace CapstanVerification

/-!
The first CCAM-SF-P whole-state bridge, deliberately restricted to the
constructor state and the instruction-fuel admission guard.

The source `CCAMMachineState` also carries output-byte state. That state is
outside CCAM-SF-P and is intentionally absent here. This Lean record mirrors
the remaining concrete fields; it is not generated from Capstan source and
does not prove object identity, source execution, or opcode dispatch refinement.

The register relation composes the native-field/list bridge with the existing
typed RuntimeBridge. The program-entry premise is the SF-P restriction to PC 0.
-/

/-- SF-P projection of the concrete CCAM machine fields. -/
structure NativeCCAMMachineState where
  registers : List NativeCCAMRegister
  instructionCount : Nat
  pc : Int
  steps : Int
  maxSteps : Int
  halted : Bool
  haltHasValue : Bool
  haltIntValue : Int
  haltBoolValue : Bool
  trapCode : String
  trapDetail : String

/-- Relation from the concrete-shaped state projection to the budgeted Lean
machine and its two-layer native/runtime register representation. -/
def NativeCCAMMachineStateMatches
    {n m : Nat} {types : RegTypes n}
    (native : NativeCCAMMachineState)
    (runtimeRegisters : List RuntimeRegister)
    (abstract : BudgetedMachineState n m types) : Prop :=
  native.instructionCount = m + 1 ∧
  native.pc = Int.ofNat abstract.machine.pc.val ∧
  native.steps = Int.ofNat abstract.budget.used ∧
  native.maxSteps = Int.ofNat abstract.budget.limit ∧
  native.halted = false ∧
  native.haltHasValue = false ∧
  native.haltIntValue = 0 ∧
  native.haltBoolValue = false ∧
  native.trapCode = "" ∧
  native.trapDetail = "" ∧
  NativeRuntimeRegisterFileRelation native.registers runtimeRegisters ∧
  RuntimeRegisterFileRelation types abstract.machine.registers runtimeRegisters

/-- The field values installed by the successful concrete machine constructor.
The source constructor separately validates nonnegative max_steps and creates
an empty output buffer; the latter is outside this profile. -/
def nativeCCAMMachineInitial
    (registers : List NativeCCAMRegister)
    (instructionCount maxSteps : Nat) : NativeCCAMMachineState :=
  { registers := registers
    instructionCount := instructionCount
    pc := 0
    steps := 0
    maxSteps := Int.ofNat maxSteps
    halted := false
    haltHasValue := false
    haltIntValue := 0
    haltBoolValue := false
    trapCode := ""
    trapDetail := "" }

/-- With the SF-P entry fixed at zero, the constructor's initial state agrees
with the Lean initial state, assuming the already-proved register bridges and
the supplied abstract register typing proof. This does not prove that the
concrete decoder, validator or constructor establishes that typing premise. -/
theorem nativeCCAMMachineInitial_matches
    {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types)
    (hentry : program.entry.val = 0)
    (nativeRegisters : List NativeCCAMRegister)
    (runtimeRegisters : List RuntimeRegister)
    (abstractRegisters : Registers n)
    (maxSteps : Nat)
    (hnr : NativeRuntimeRegisterFileRelation nativeRegisters runtimeRegisters)
    (hrf : RuntimeRegisterFileRelation types abstractRegisters runtimeRegisters)
    (hwellTyped : WellTyped types abstractRegisters) :
    NativeCCAMMachineStateMatches
      (nativeCCAMMachineInitial nativeRegisters (m + 1) maxSteps)
      runtimeRegisters
      { machine := initialMachineState program abstractRegisters hwellTyped
        budget := { limit := maxSteps, used := 0, within_limit := Nat.zero_le maxSteps } } := by
  simp [NativeCCAMMachineStateMatches, nativeCCAMMachineInitial,
    initialMachineState, hentry, hnr, hrf]

/-- The concrete evaluator's ordinary fall-through PC increment. -/
def nativePCAdvance (pc : Int) : Int := pc + 1

/-- At every non-final PC, the concrete integer increment agrees with the
Lean machine's sequential successor. The premise is essential: the final
instruction in CCAM-SF-P has an explicit control effect and must not fall
through. -/
theorem nativePCAdvance_corresponds
    {m : Nat} (pc : Fin (m + 1)) (hbeforeLast : pc.val < m) :
    nativePCAdvance (Int.ofNat pc.val) =
      Int.ofNat (sequentialPC pc).val := by
  rw [sequentialPC_increments_before_last pc hbeforeLast]
  simp [nativePCAdvance]

/-- The native evaluator's pre-dispatch fuel gate, projected to signed integers.
A validated machine state has nonnegative counters, so the relation below
compares it to the Nat-valued Lean budget without an unchecked conversion. -/
def nativeStepAdmission (steps maxSteps : Int) : Except Trap Int :=
  if steps >= maxSteps then
    .error .instructionLimit
  else
    .ok (steps + 1)

/-- The concrete-shaped signed-integer fuel guard agrees exactly with
`consumeStep` on every well-formed Lean budget. A successful guard increments
once; exhaustion traps before instruction execution. -/
theorem nativeStepAdmission_corresponds (budget : StepBudget) :
    nativeStepAdmission (Int.ofNat budget.used) (Int.ofNat budget.limit) =
      (consumeStep budget).map (fun next => Int.ofNat next.used) := by
  unfold nativeStepAdmission consumeStep
  by_cases h : budget.used < budget.limit
  · have hge : ¬ budget.limit ≤ budget.used := Nat.not_le_of_gt h
    simp [h, hge, Int.ofNat_add, Except.map]
  · have hle : budget.limit ≤ budget.used := Nat.le_of_not_gt h
    simp [h, hle, Except.map]

/-- An exhausted budget is rejected before the native-shaped dispatch step. -/
theorem nativeStepAdmission_exhausted
    (steps maxSteps : Int) (hexhausted : steps >= maxSteps) :
    nativeStepAdmission steps maxSteps = .error .instructionLimit := by
  simp [nativeStepAdmission, hexhausted]

end CapstanVerification
