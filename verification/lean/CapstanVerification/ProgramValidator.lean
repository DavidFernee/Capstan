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

/-- Validate a register index and its declared type. -/
def typedRegister? {n : Nat} (types : RegTypes n)
    (index : Nat) (expected : Ty) : Option (Fin n) :=
  match finOfNat? n index with
  | none => none
  | some i => if h : types i = expected then some i else none

/-- Validate three integer registers and construct their typed instruction. -/
def checkedIntRegisters? {n : Nat} (types : RegTypes n)
    (dst lhs rhs : Nat) : Option (CheckedIntInstr n types) := do
  let d ← typedRegister? types dst .int
  let l ← typedRegister? types lhs .int
  let r ← typedRegister? types rhs .int
  have hd : types d = .int := by
    unfold typedRegister? at *
    split at ‹Option (Fin n)› <;> simp_all
  have hl : types l = .int := by
    unfold typedRegister? at *
    split at ‹Option (Fin n)› <;> simp_all
  have hr : types r = .int := by
    unfold typedRegister? at *
    split at ‹Option (Fin n)› <;> simp_all
  exact ⟨d, l, r, hd, hl, hr⟩

/-- Validate a raw instruction into the existing intrinsically typed machine syntax. -/
def validateMachineInstr {n m : Nat} {types : RegTypes n}
    (raw : RawMachineInstr) : Option (MachineInstr n m types) := do
  match raw with
  | .constInt dst value =>
      let d ← typedRegister? types dst .int
      if hv : inI64B value = true then
        have hd : types d = .int := by
          unfold typedRegister? at *
          split at ‹Option (Fin n)› <;> simp_all
        exact .constInt d value hd hv
      else none
  | .constBool dst value =>
      let d ← typedRegister? types dst .bool
      have hd : types d = .bool := by
        unfold typedRegister? at *
        split at ‹Option (Fin n)› <;> simp_all
      exact .constBool d value hd
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
      have hd : types d = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hl : types l = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hr : types r = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .add ⟨d, l, r, hd, hl, hr⟩
  | .sub dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      have hd : types d = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hl : types l = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hr : types r = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .sub ⟨d, l, r, hd, hl, hr⟩
  | .mul dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      have hd : types d = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hl : types l = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hr : types r = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .mul ⟨d, l, r, hd, hl, hr⟩
  | .div dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      have hd : types d = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hl : types l = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hr : types r = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .div ⟨d, l, r, hd, hl, hr⟩
  | .rem dst lhs rhs =>
      let d ← typedRegister? types dst .int
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      have hd : types d = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hl : types l = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hr : types r = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .rem ⟨d, l, r, hd, hl, hr⟩
  | .lessThan dst lhs rhs =>
      let d ← typedRegister? types dst .bool
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      have hd : types d = .bool := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hl : types l = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hr : types r = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .lessThan ⟨d, l, r, hd, hl, hr⟩
  | .equal dst lhs rhs =>
      let d ← typedRegister? types dst .bool
      let l ← typedRegister? types lhs .int
      let r ← typedRegister? types rhs .int
      have hd : types d = .bool := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hl : types l = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hr : types r = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .equal ⟨d, l, r, hd, hl, hr⟩
  | .booleanNot dst src =>
      let d ← typedRegister? types dst .bool
      let s ← typedRegister? types src .bool
      have hd : types d = .bool := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      have hs : types s = .bool := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .booleanNot ⟨d, s, hd, hs⟩
  | .jump target =>
      let t ← finOfNat? m target
      exact .jump t
  | .branch cond ifTrue ifFalse =>
      let c ← typedRegister? types cond .bool
      let t ← finOfNat? m ifTrue
      let f ← finOfNat? m ifFalse
      have hc : types c = .bool := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .branch ⟨c, hc, t, f⟩
  | .retInt src =>
      let s ← typedRegister? types src .int
      have hs : types s = .int := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .retInt s hs
  | .retBool src =>
      let s ← typedRegister? types src .bool
      have hs : types s = .bool := by
        unfold typedRegister? at *; split at ‹Option (Fin n)› <;> simp_all
      exact .retBool s hs
  | .retVoid => exact .retVoid
  | .explicitTrap reason => exact .explicitTrap reason

/-- Raw single-frame program: untrusted entry and instruction operands. -/
structure RawSingleFrameProgram (n m : Nat) (types : RegTypes n) where
  code : Fin (m + 1) → RawMachineInstr
  entry : Nat

/-- A successful whole-program validation produces the formal finite machine program. -/
def validateSingleFrameProgram {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types) : Option (FiniteProgram n m types) := do
  let entry ← finOfNat? (m + 1) raw.entry
  let decoded := fun pc => validateMachineInstr (m := m + 1) (raw.code pc)
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

/-- The accepted code is total and intrinsically typed at every finite PC. -/
theorem validateSingleFrameProgram_code_typed
    {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types)
    (program : FiniteProgram n m types)
    (h : validateSingleFrameProgram raw = some program)
    (pc : Fin (m + 1)) :
    MachineInstr n (m + 1) types (program.code pc) := by
  exact program.code pc

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
