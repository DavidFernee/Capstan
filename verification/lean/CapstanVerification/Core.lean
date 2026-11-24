import Std

namespace CapstanVerification

/-!
A deliberately small proof model of the integer/register fragment of CCAM v0.1.
Normative authority: docs/architecture/CCAM.md on the stacked CCAM branch.
This is not an evaluator and no implementation-refinement theorem is claimed.
-/

def minI64 : Int := -(2 ^ 63 : Int)
def maxI64 : Int := (2 ^ 63 : Int) - 1
def inI64 (x : Int) : Prop := minI64 ≤ x ∧ x ≤ maxI64

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
  if inI64 x then .ok x else .error .integerOverflow

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

/-- A successful range check returns a signed-64 value. -/
theorem checkedI64_sound (x result : Int)
    (h : checkedI64 x = .ok result) : inI64 result := by
  have hx : inI64 x := by
    by_contra hnot
    have : False := by simpa [checkedI64, hnot] using h
    exact this.elim
  have heq : x = result := by
    simpa [checkedI64, hx] using h
  subst result
  exact hx

theorem checkedAdd_sound (a b result : Int)
    (h : checkedAdd a b = .ok result) : inI64 result := by
  exact checkedI64_sound (a + b) result h

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
