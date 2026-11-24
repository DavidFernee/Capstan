import CapstanVerification.Validator

namespace CapstanVerification

/-!
Whole-program validator for the current finite, single-frame machine fragment.

Raw indices are naturals. Successful validation converts every register and
control-flow index to Fin, checks every instruction (including unreachable
instructions), checks the entry point, and requires the final instruction to
have an explicit control effect. The latter is exactly the invariant needed
by FiniteProgram to rule out reachable sequential fall-through at the end.
-/

/-- All instruction constructors supported by the current single-frame machine. -/
inductive RawMachineInstr where
  | constInt (dst : Nat) (value : Int)
  | constBool (dst : Nat) (value : Bool)
  | move (dst src : Nat)
  | add (dst lhs rhs : Nat)
  | sub (dst lhs rhs : Nat)
  | mul (dst lhs rhs : Nat)
  | div (dst lhs rhs : Nat)
  | rem (dst lhs rhs : Nat)
  | lessThan (dst lhs rhs : Nat)
  | equal (dst lhs rhs : Nat)
  | booleanNot (dst src : Nat)
  | jump (target : Nat)
  | branch (cond ifTrue ifFalse : Nat)
  | retInt (src : Nat)
  | retBool (src : Nat)
  | retVoid
  | explicitTrap (reason : Trap)
  deriving Repr

/-- A successful register lookup carries its declared type as data. -/
def typedRegister? {n : Nat} (types : RegTypes n)
    (index : Nat) (expected : Ty) : Option {i : Fin n // types i = expected} := do
  let i ← finOfNat? n index
  if h : types i = expected then some ⟨i, h⟩ else none

/-- Validate a raw instruction into the existing intrinsically typed machine syntax. -/
def validateMachineInstr {n m : Nat} {types : RegTypes n}
    (raw : RawMachineInstr) : Option (MachineInstr n m types) := do
  match raw with
  | .constInt dst value =>
      let d ← typedRegister? types dst .int
      if hv : inI64B value = true then
        exact .constInt d.1 value d.2 hv
      else none
  | .constBool dst value =>
      let d ← typedRegister? types dst .bool
      exact .constBool d.1 value d.2
  | .move dst src =>
      let d ← finOfNat? n dst
      let s ← finOfNat? n src
      if hs : types d = types s then
        exact .move ⟨d, s, hs⟩
      else none
  | .add dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      exact .add ⟨d.1, l.1, r.1, d.2, l.2, r.2⟩
  | .sub dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      exact .sub ⟨d.1, l.1, r.1, d.2, l.2, r.2⟩
  | .mul dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      exact .mul ⟨d.1, l.1, r.1, d.2, l.2, r.2⟩
  | .div dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      exact .div ⟨d.1, l.1, r.1, d.2, l.2, r.2⟩
  | .rem dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      exact .rem ⟨d.1, l.1, r.1, d.2, l.2, r.2⟩
  | .lessThan dst lhs rhs =>
      let d ← typedRegister? types dst .bool
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      exact .lessThan ⟨d.1, l.1, r.1, d.2, l.2, r.2⟩
  | .equal dst lhs rhs =>
      let d ← typedRegister? types dst .bool
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      exact .equal ⟨d.1, l.1, r.1, d.2, l.2, r.2⟩
  | .booleanNot dst src =>
      let d ← typedRegister? types dst .bool
      let s ← typedRegister? types src .bool
      exact .booleanNot ⟨d.1, s.1, d.2, s.2⟩
  | .jump target =>
      let t ← finOfNat? m target
      exact .jump t
  | .branch cond ifTrue ifFalse =>
      let c ← typedRegister? types cond .bool
      let t ← finOfNat? m ifTrue
      let f ← finOfNat? m ifFalse
      exact .branch ⟨c.1, c.2, t, f⟩
  | .retInt src =>
      let s ← typedRegister? types src .int
      exact .retInt s.1 s.2
  | .retBool src =>
      let s ← typedRegister? types src .bool
      exact .retBool s.1 s.2
  | .retVoid => exact .retVoid
  | .explicitTrap reason => exact .explicitTrap reason

/-- Function-level return contract for a single CCAM function. -/
inductive RawReturnType where
  | int
  | bool
  | void
  deriving DecidableEq, Repr

/-- Add the function's return contract to instruction validation. -/
def validateFunctionInstr {n m : Nat} {types : RegTypes n}
    (returnType : RawReturnType) (raw : RawMachineInstr) :
    Option (MachineInstr n m types) :=
  match raw with
  | .retInt _ =>
      if returnType = .int then validateMachineInstr raw else none
  | .retBool _ =>
      if returnType = .bool then validateMachineInstr raw else none
  | .retVoid =>
      if returnType = .void then validateMachineInstr raw else none
  | _ => validateMachineInstr raw

/-- A return instruction cannot validate against a different function return type. -/
theorem validateFunctionInstr_rejects_return_mismatch
    {n m : Nat} {types : RegTypes n}
    (returnType : RawReturnType) (raw : RawMachineInstr)
    (hmismatch :
      (match raw with
       | .retInt _ => returnType ≠ .int
       | .retBool _ => returnType ≠ .bool
       | .retVoid => returnType ≠ .void
       | _ => False) ) :
    validateFunctionInstr (n := n) (m := m) (types := types)
      returnType raw = none := by
  cases raw <;> simp_all [validateFunctionInstr]

/-- Raw single-frame program: untrusted entry and instruction operands. -/
structure RawSingleFrameProgram (n m : Nat) (types : RegTypes n) where
  code : Fin (m + 1) → RawMachineInstr
  entry : Nat
  returnType : RawReturnType

/-- A successful whole-program validation produces the formal finite machine program. -/
def validateSingleFrameProgram {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types) : Option (FiniteProgram n m types) := do
  let entry ← finOfNat? (m + 1) raw.entry
  let decoded := fun pc => validateFunctionInstr (m := n) (m := m + 1) raw.returnType (raw.code pc)
  if hall : ∀ pc, (decoded pc).isSome then
    let typed : Fin (m + 1) → MachineInstr n (m + 1) types :=
      fun pc => (decoded pc).get (hall pc)
    if hlast : machineInstrIsTerminal (typed (Fin.last m)) = true then
      exact {
        code := typed
        entry := entry
        last_is_terminal := hlast
      }
    else none
  else none

/-- Validation rejects an entry index outside the finite instruction table. -/
theorem validateSingleFrameProgram_rejects_bad_entry
    {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types)
    (hentry : m + 1 ≤ raw.entry) :
    validateSingleFrameProgram raw = none := by
  unfold validateSingleFrameProgram
  have hnot : ¬ raw.entry < m + 1 := Nat.not_lt.mpr hentry
  simp [finOfNat?, hnot]

/-- Successful validation returns a program whose entry is the supplied raw entry. -/
theorem validateSingleFrameProgram_entry_sound
    {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types)
    (program : FiniteProgram n m types)
    (h : validateSingleFrameProgram raw = some program) :
    program.entry.val = raw.entry := by
  unfold validateSingleFrameProgram at h
  cases hentry : finOfNat? (m + 1) raw.entry with
  | none => simp [hentry] at h
  | some entry =>
      simp [hentry] at h
      split at h
      · split at h
        · simp_all
        · simp_all
      · simp_all

/-- Every accepted program has an explicit control effect at its final slot. -/
theorem validateSingleFrameProgram_final_terminal
    {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types)
    (program : FiniteProgram n m types)
    (h : validateSingleFrameProgram raw = some program) :
    HasExplicitControlEffect (program.code (Fin.last m)) :=
  finiteProgram_final_instruction_has_control_effect program

/-- Every accepted jump/branch target is bounded by the program's finite code size. -/
theorem validateSingleFrameProgram_targets_bounded
    {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types)
    (program : FiniteProgram n m types)
    (h : validateSingleFrameProgram raw = some program)
    (pc : Fin (m + 1)) :
    MachineInstrTargetsInRange (program.code pc) :=
  machineInstr_targets_in_range (program.code pc)

end CapstanVerification
