import Std

namespace CapstanVerification

inductive Ty where
  | int
  | bool
  deriving DecidableEq, Repr

inductive Val where
  | int (value : Int)
  | bool (value : Bool)
  deriving Repr

def hasType : Val → Ty → Prop
  | .int _, .int => True
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
    injection hread with hv
    subst v
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

def minI64 : Int := -(2 ^ 63 : Int)
def maxI64 : Int := (2 ^ 63 : Int) - 1

def inI64 (x : Int) : Prop := minI64 ≤ x ∧ x ≤ maxI64

def checkedAdd (a b : Int) : Except Trap Int :=
  let result := a + b
  if inI64 result then .ok result else .error .integerOverflow

theorem checkedAdd_sound (a b result : Int)
    (h : checkedAdd a b = .ok result) : inI64 result := by
  simp only [checkedAdd] at h
  split at h
  · simp_all
  · simp_all

def checkedDiv (a b : Int) : Except Trap Int :=
  if b = 0 then .error .divisionByZero
  else if a = minI64 ∧ b = -1 then .error .integerOverflow
  else .ok (a / b)

theorem checkedDiv_zero_traps (a : Int) :
    checkedDiv a 0 = .error .divisionByZero := by
  simp [checkedDiv]

theorem checkedDiv_min_neg_one_traps :
    checkedDiv minI64 (-1) = .error .integerOverflow := by
  simp [checkedDiv]

end CapstanVerification
