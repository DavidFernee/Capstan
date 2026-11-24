import Std

namespace CapstanVerification

/-!
A deliberately small proof model of the integer/register fragment of CCAM v0.1.
Normative authority: docs/architecture/CCAM.md on the stacked CCAM branch.
This is not an evaluator and no implementation-refinement theorem is claimed.
-/

def two63 : Nat := 2 ^ 63
def maxI64Nat : Nat := two63 - 1
def minI64 : Int := Int.negSucc maxI64Nat
def maxI64 : Int := Int.ofNat maxI64Nat

/-- Executable signed-64 range check over Lean's two Int constructors. -/
def inI64B : Int → Bool
  | .ofNat n => decide (n ≤ maxI64Nat)
  | .negSucc n => decide (n < two63)

def inI64 (x : Int) : Prop := inI64B x = true

inductive Ty where
  | int
  | bool
  deriving DecidableEq, Repr

inductive Val where
  | int (value : Int)
  | bool (value : Bool)
  deriving Repr

def hasType : Val → Ty → Prop
  | .int n, .int => inI64 n
  | .bool _, .bool => True
  | _, _ => False

abbrev RegTypes (n : Nat) := Fin n → Ty
abbrev Registers (n : Nat) := Fin n → Option Val

def WellTyped {n : Nat} (types : RegTypes n) (regs : Registers n) : Prop :=
  ∀ i v, regs i = some v → hasType v (types i)

def write {n : Nat} (regs : Registers n) (index : Fin n) (value : Val) : Registers n :=
  fun j => if j = index then some value else regs j

theorem write_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (hregs : WellTyped types regs)
    (index : Fin n) (value : Val)
    (hvalue : hasType value (types index)) :
    WellTyped types (write regs index value) := by
  intro j v hread
  by_cases hji : j = index
  · subst j
    simp [write] at hread
    cases hread
    exact hvalue
  · have hold : regs j = some v := by
      simpa [write, hji] using hread
    exact hregs j v hold

inductive Trap where
  | integerOverflow
  | divisionByZero
  | uninitialisedRegister
  | invalidRegister
  | typeMismatch
  | invalidControlFlow
  | callDepthLimit
  | instructionLimit
  deriving DecidableEq, Repr

def checkedI64 (x : Int) : Except Trap Int :=
  if inI64B x then .ok x else .error .integerOverflow

def checkedAdd (a b : Int) : Except Trap Int := checkedI64 (a + b)
def checkedSub (a b : Int) : Except Trap Int := checkedI64 (a - b)
def checkedMul (a b : Int) : Except Trap Int := checkedI64 (a * b)

/-- Quotient required by CCAM: integer division truncated toward zero. -/
def truncDiv (a b : Int) : Int :=
  let magnitude : Nat := a.natAbs / b.natAbs
  let q := Int.ofNat magnitude
  if (a < 0 ∧ 0 < b) ∨ (0 < a ∧ b < 0) then -q else q

def checkedDiv (a b : Int) : Except Trap Int :=
  if b = 0 then .error .divisionByZero
  else if a = minI64 ∧ b = -1 then .error .integerOverflow
  else .ok (truncDiv a b)

def checkedRem (a b : Int) : Except Trap Int :=
  if b = 0 then .error .divisionByZero
  else if a = minI64 ∧ b = -1 then .error .integerOverflow
  else .ok (a - truncDiv a b * b)


/-- The signed-64 endpoints are accepted by the executable range predicate. -/
theorem minI64_in_range : inI64 minI64 := by
  change inI64B minI64 = true
  decide

theorem maxI64_in_range : inI64 maxI64 := by
  change inI64B maxI64 = true
  decide

/-- The immediately adjacent values outside the signed-64 interval are rejected. -/
theorem below_minI64_out_of_range : ¬ inI64 (Int.negSucc two63) := by
  change ¬ (inI64B (Int.negSucc two63) = true)
  decide

theorem above_maxI64_out_of_range : ¬ inI64 (Int.ofNat two63) := by
  change ¬ (inI64B (Int.ofNat two63) = true)
  decide

/-- A successful range check returns a signed-64 value. -/
theorem checkedI64_sound (x result : Int)
    (h : checkedI64 x = .ok result) : inI64 result := by
  cases hx : inI64B x with
  | false =>
    simp [checkedI64, hx] at h
  | true =>
    have heq : x = result := by
      simpa [checkedI64, hx] using h
    subst result
    simpa [inI64] using hx

theorem checkedAdd_sound (a b result : Int)
    (h : checkedAdd a b = .ok result) : inI64 result := by
  exact checkedI64_sound (a + b) result h


/-- Dynamic integer-register read: uninitialised and wrong-kind reads trap. -/
def readInt {n : Nat} (regs : Registers n) (index : Fin n) : Except Trap Int :=
  match regs index with
  | none => .error .uninitialisedRegister
  | some (.int value) => .ok value
  | some (.bool _) => .error .typeMismatch


/-- A successful read from a statically integer register yields an in-range integer. -/
theorem readInt_success_in_range
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (hregs : WellTyped types regs)
    (index : Fin n) (hindex : types index = .int)
    (value : Int)
    (hread : readInt regs index = .ok value) :
    inI64 value := by
  unfold readInt at hread
  cases hreg : regs index with
  | none =>
    simp [hreg] at hread
  | some v =>
    cases v with
    | int x =>
      simp [hreg] at hread
      cases hread
      have htyped := hregs index (.int value) hreg
      simpa [hasType, hindex] using htyped
    | bool b =>
      simp [hreg] at hread

/-- An addition instruction carries its static register-type obligations. -/
structure AddInstr (n : Nat) (types : RegTypes n) where
  dst : Fin n
  lhs : Fin n
  rhs : Fin n
  dst_is_int : types dst = .int
  lhs_is_int : types lhs = .int
  rhs_is_int : types rhs = .int

/-- One atomic CCAM integer-add transition, with left-to-right operand reads. -/
def executeAdd {n : Nat} {types : RegTypes n}
    (regs : Registers n) (instr : AddInstr n types) : Except Trap (Registers n) :=
  match readInt regs instr.lhs, readInt regs instr.rhs with
  | .error e, _ => .error e
  | _, .error e => .error e
  | .ok a, .ok b =>
    match checkedAdd a b with
    | .error e => .error e
    | .ok result => .ok (write regs instr.dst (.int result))

/-- A successful typed add instruction preserves the register-file invariant. -/
theorem executeAdd_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs next : Registers n}
    (hregs : WellTyped types regs)
    (instr : AddInstr n types)
    (hstep : executeAdd regs instr = .ok next) :
    WellTyped types next := by
  unfold executeAdd at hstep
  cases hleft : readInt regs instr.lhs with
  | error e =>
    simp [hleft] at hstep
  | ok a =>
    cases hright : readInt regs instr.rhs with
    | error e =>
      simp [hleft, hright] at hstep
    | ok b =>
      cases hadd : checkedAdd a b with
      | error e =>
        simp [hleft, hright, hadd] at hstep
      | ok result =>
        simp [hleft, hright, hadd] at hstep
        cases hstep
        have hresult : inI64 result := checkedAdd_sound a b result hadd
        have hvalue : hasType (.int result) (types instr.dst) := by
          simp [hasType, instr.dst_is_int, hresult]
        exact write_preserves_well_typed hregs instr.dst (.int result) hvalue


theorem checkedSub_sound (a b result : Int)
    (h : checkedSub a b = .ok result) : inI64 result := by
  exact checkedI64_sound (a - b) result h

theorem checkedMul_sound (a b result : Int)
    (h : checkedMul a b = .ok result) : inI64 result := by
  exact checkedI64_sound (a * b) result h

theorem checkedDiv_zero_traps (a : Int) :
    checkedDiv a 0 = .error .divisionByZero := by
  simp [checkedDiv]

theorem checkedRem_zero_traps (a : Int) :
    checkedRem a 0 = .error .divisionByZero := by
  simp [checkedRem]

theorem checkedDiv_min_neg_one_traps :
    checkedDiv minI64 (-1) = .error .integerOverflow := by
  simp [checkedDiv]

theorem checkedRem_min_neg_one_traps :
    checkedRem minI64 (-1) = .error .integerOverflow := by
  simp [checkedRem]

/-!
Explicit omissions: there is no instruction syntax, machine state, small-step
relation, function stack, structural validator, evaluator, or compiler relation.
The next semantics increment must follow CCAM.md and its conformance vectors.
-/


end CapstanVerification
