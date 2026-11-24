import CapstanVerification.Core

namespace CapstanVerification

/-!
A refinement boundary for the Capstan-native CCAM register representation.

The executable Capstan slice stores a declared type, an initialization bit,
and separate integer/boolean payload slots in a list. The proof core uses a
finite index and an optional typed value. This file states the relation between
those representations and proves the read path commutes. It does not yet prove
the mutable list writes or validator/index checks refine the finite model.
-/

/-- Abstract record matching the fields of the Capstan-native CCAM register. -/
structure RuntimeRegister where
  declaredType : Ty
  initialized : Bool
  intValue : Int
  intValue_in_range : inI64 intValue
  boolValue : Bool

/-- Interpret the initialized payload according to the register's declared type. -/
def RuntimeRegister.value? (reg : RuntimeRegister) : Option Val :=
  if reg.initialized then
    match reg.declaredType with
    | .int => some (.int reg.intValue)
    | .bool => some (.bool reg.boolValue)
  else
    none

/-- Dynamic list lookup used by the native register-file representation. -/
def runtimeRegisterAt (registers : List RuntimeRegister) (index : Nat) :
    Option RuntimeRegister :=
  registers[index]?

/-- The runtime register's declared type at a dynamic index. -/
def runtimeTypeAt (registers : List RuntimeRegister) (index : Nat) : Option Ty :=
  (runtimeRegisterAt registers index).map RuntimeRegister.declaredType

/-- The initialized value at a dynamic index, or none for an uninitialized slot. -/
def runtimeValueAt (registers : List RuntimeRegister) (index : Nat) : Option Val :=
  (runtimeRegisterAt registers index).bind RuntimeRegister.value?

/-- Representation relation between the native list and the finite typed model. -/
structure RuntimeRegisterFileRelation {n : Nat}
    (types : RegTypes n) (regs : Registers n)
    (runtime : List RuntimeRegister) : Prop where
  length_eq : runtime.length = n
  type_at : ∀ i, runtimeTypeAt runtime i.val = some (types i)
  value_at : ∀ i, runtimeValueAt runtime i.val = regs i

/-- Native-style dynamic integer read, including the invalid-index check. -/
def runtimeReadInt (registers : List RuntimeRegister) (index : Nat) :
    Except Trap Int :=
  if index < registers.length then
    match runtimeValueAt registers index with
    | none => .error .uninitialisedRegister
    | some (.int value) => .ok value
    | some (.bool _) => .error .typeMismatch
  else
    .error .invalidRegister

/-- Native-style dynamic boolean read, including the invalid-index check. -/
def runtimeReadBool (registers : List RuntimeRegister) (index : Nat) :
    Except Trap Bool :=
  if index < registers.length then
    match runtimeValueAt registers index with
    | none => .error .uninitialisedRegister
    | some (.int _) => .error .typeMismatch
    | some (.bool value) => .ok value
  else
    .error .invalidRegister

/-- Related native and finite register files produce the same integer reads. -/
theorem runtimeReadInt_corresponds
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    {runtime : List RuntimeRegister}
    (hrel : RuntimeRegisterFileRelation types regs runtime)
    (index : Fin n) :
    runtimeReadInt runtime index.val = readInt regs index := by
  have hbound : index.val < runtime.length := by
    simpa [hrel.length_eq] using index.isLt
  unfold runtimeReadInt
  rw [if_pos hbound, hrel.value_at index]
  cases hvalue : regs index with
  | none =>
      simp [readInt, hvalue]
  | some value =>
      cases value <;> simp [readInt, hvalue]

/-- Related native and finite register files produce the same boolean reads. -/
theorem runtimeReadBool_corresponds
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    {runtime : List RuntimeRegister}
    (hrel : RuntimeRegisterFileRelation types regs runtime)
    (index : Fin n) :
    runtimeReadBool runtime index.val = readBool regs index := by
  have hbound : index.val < runtime.length := by
    simpa [hrel.length_eq] using index.isLt
  unfold runtimeReadBool
  rw [if_pos hbound, hrel.value_at index]
  cases hvalue : regs index with
  | none =>
      simp [readBool, hvalue]
  | some value =>
      cases value <;> simp [readBool, hvalue]

/-- A related native register file cannot contain a value of the wrong declared type. -/
theorem runtimeRelation_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    {runtime : List RuntimeRegister}
    (hrel : RuntimeRegisterFileRelation types regs runtime) :
    WellTyped types regs := by
  intro index value hread
  have hvalue : runtimeValueAt runtime index.val = some value := by
    rw [hrel.value_at index, hread]
  unfold runtimeValueAt runtimeRegisterAt at hvalue
  cases hreg : registers[index.val]? with
  | none =>
      simp [hreg] at hvalue
  | some reg =>
      simp [hreg] at hvalue
      have htype : reg.declaredType = types index := by
        have h := hrel.type_at index
        simp [runtimeTypeAt, runtimeRegisterAt, hreg] at h
        exact h
      cases hdecl : reg.declaredType with
      | int =>
          have htarget : types index = .int := by
            rw [hdecl] at htype
            exact htype.symm
          cases hinit : reg.initialized with
          | false =>
              simp [RuntimeRegister.value?, hdecl, hinit] at hvalue
          | true =>
              simp [RuntimeRegister.value?, hdecl, hinit] at hvalue
              cases hvalue
              simpa [hasType, hasTypeB] using reg.intValue_in_range
      | bool =>
          have htarget : types index = .bool := by
            rw [hdecl] at htype
            exact htype.symm
          cases hinit : reg.initialized with
          | false =>
              simp [RuntimeRegister.value?, hdecl, hinit] at hvalue
          | true =>
              simp [RuntimeRegister.value?, hdecl, hinit] at hvalue
              cases hvalue
              simp [hasType, hasTypeB]

end CapstanVerification
