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

/-- The payload value selected by a register's declared type. -/
def RuntimeRegister.asVal (reg : RuntimeRegister) : Val :=
  match reg.declaredType with
  | .int => .int reg.intValue
  | .bool => .bool reg.boolValue

/-- Interpret the initialized payload according to the register's declared type. -/
def RuntimeRegister.value? (reg : RuntimeRegister) : Option Val :=
  if reg.initialized then
    match reg.declaredType with
    | .int => some (.int reg.intValue)
    | .bool => some (.bool reg.boolValue)
  else
    none

/-- An initialized runtime register exposes exactly its typed payload. -/
theorem RuntimeRegister.value?_of_initialized
    (reg : RuntimeRegister) (h : reg.initialized = true) :
    reg.value? = some reg.asVal := by
  cases reg with
  | mk declaredType initialized intValue _ boolValue =>
      change initialized = true at h
      cases htype : declaredType <;>
        simp [RuntimeRegister.value?, RuntimeRegister.asVal, h, htype]

/-- Dynamic list lookup used by the native register-file representation. -/
def runtimeRegisterAt (registers : List RuntimeRegister) (index : Nat) :
    Option RuntimeRegister :=
  registers[index]?

/-- Replace one list slot without changing the list's shape. -/
def runtimeSetAt : List RuntimeRegister → Nat → RuntimeRegister → List RuntimeRegister
  | [], _, _ => []
  | _ :: rest, 0, replacement => replacement :: rest
  | head :: rest, Nat.succ index, replacement =>
      head :: runtimeSetAt rest index replacement

/-- A list-slot replacement preserves the register-file length. -/
theorem runtimeSetAt_length
    (registers : List RuntimeRegister) (index : Nat)
    (replacement : RuntimeRegister) :
    (runtimeSetAt registers index replacement).length = registers.length := by
  induction registers generalizing index with
  | nil =>
      simp [runtimeSetAt]
  | cons head rest ih =>
      cases index with
      | zero => rfl
      | succ index =>
          simp [runtimeSetAt, ih]

/-- The replacement is found at the index that was updated. -/
theorem runtimeSetAt_get_same_of_exists
    (registers : List RuntimeRegister) (index : Nat)
    (old replacement : RuntimeRegister)
    (hreg : runtimeRegisterAt registers index = some old) :
    runtimeRegisterAt (runtimeSetAt registers index replacement) index =
      some replacement := by
  induction registers generalizing index with
  | nil =>
      simp [runtimeRegisterAt] at hreg
  | cons head rest ih =>
      cases index with
      | zero => rfl
      | succ index =>
          simp only [runtimeRegisterAt] at hreg
          simp only [runtimeSetAt, runtimeRegisterAt]
          exact ih index hreg

/-- Reading a different index is unaffected by a list-slot replacement. -/
theorem runtimeSetAt_get_other_of_exists
    (registers : List RuntimeRegister) (index other : Nat)
    (old replacement : RuntimeRegister)
    (hreg : runtimeRegisterAt registers index = some old)
    (hother : other ≠ index) :
    runtimeRegisterAt (runtimeSetAt registers index replacement) other =
      runtimeRegisterAt registers other := by
  induction registers generalizing index other with
  | nil =>
      simp [runtimeRegisterAt] at hreg
  | cons head rest ih =>
      cases index with
      | zero =>
          cases other with
          | zero => exact False.elim (hother rfl)
          | succ other => rfl
      | succ index =>
          cases other with
          | zero => rfl
          | succ other =>
              simp only [runtimeRegisterAt] at hreg
              simp only [runtimeSetAt, runtimeRegisterAt]
              apply ih index other hreg
              intro heq
              exact hother (congrArg Nat.succ heq)

/-- A dynamic register replacement checks bounds and preserves the declared type. -/
def runtimeWriteRegister (registers : List RuntimeRegister)
    (index : Nat) (replacement : RuntimeRegister) :
    Except Trap (List RuntimeRegister) :=
  match runtimeRegisterAt registers index with
  | none => .error .invalidRegister
  | some old =>
      if old.declaredType = replacement.declaredType then
        .ok (runtimeSetAt registers index replacement)
      else
        .error .typeMismatch

/-- A successful dynamic replacement preserves the register-file length. -/
theorem runtimeWriteRegister_length
    (registers updated : List RuntimeRegister)
    (index : Nat) (replacement : RuntimeRegister)
    (hwrite : runtimeWriteRegister registers index replacement = .ok updated) :
    updated.length = registers.length := by
  unfold runtimeWriteRegister at hwrite
  cases hreg : runtimeRegisterAt registers index with
  | none =>
      simp [hreg] at hwrite
  | some old =>
      by_cases htype : old.declaredType = replacement.declaredType
      · simp [hreg, htype] at hwrite
        cases hwrite
        exact runtimeSetAt_length registers index replacement
      · simp [hreg, htype] at hwrite

/-- A successful dynamic replacement installs the requested register at its index. -/
theorem runtimeWriteRegister_target
    (registers updated : List RuntimeRegister)
    (index : Nat) (replacement : RuntimeRegister)
    (hwrite : runtimeWriteRegister registers index replacement = .ok updated) :
    runtimeRegisterAt updated index = some replacement := by
  unfold runtimeWriteRegister at hwrite
  cases hreg : runtimeRegisterAt registers index with
  | none =>
      simp [hreg] at hwrite
  | some old =>
      by_cases htype : old.declaredType = replacement.declaredType
      · simp [hreg, htype] at hwrite
        cases hwrite
        exact runtimeSetAt_get_same_of_exists registers index old replacement hreg
      · simp [hreg, htype] at hwrite

/-- A successful dynamic replacement leaves every other register unchanged. -/
theorem runtimeWriteRegister_other_unchanged
    (registers updated : List RuntimeRegister)
    (index other : Nat) (replacement : RuntimeRegister)
    (hwrite : runtimeWriteRegister registers index replacement = .ok updated)
    (hother : other ≠ index) :
    runtimeRegisterAt updated other = runtimeRegisterAt registers other := by
  unfold runtimeWriteRegister at hwrite
  cases hreg : runtimeRegisterAt registers index with
  | none =>
      simp [hreg] at hwrite
  | some old =>
      by_cases htype : old.declaredType = replacement.declaredType
      · simp [hreg, htype] at hwrite
        cases hwrite
        exact runtimeSetAt_get_other_of_exists
          registers index other old replacement hreg hother
      · simp [hreg, htype] at hwrite

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

/-- A successful typed runtime replacement preserves the finite/list relation.

The finite model receives the value selected by the replacement's declared
type. The replacement must be initialized and retain the static register type.
-/
theorem runtimeWriteRegister_preserves_relation
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    {runtime updated : List RuntimeRegister}
    (hrel : RuntimeRegisterFileRelation types regs runtime)
    (index : Fin n) (replacement : RuntimeRegister)
    (hdecl : replacement.declaredType = types index)
    (hinit : replacement.initialized = true)
    (hwrite : runtimeWriteRegister runtime index.val replacement = .ok updated) :
    RuntimeRegisterFileRelation types
      (write regs index replacement.asVal) updated := by
  have hvalueType : hasType replacement.asVal (types index) := by
    rw [← hdecl]
    cases htype : replacement.declaredType <;>
      simp [RuntimeRegister.asVal, hasType, hasTypeB, htype]
  refine {
    length_eq := by
      rw [runtimeWriteRegister_length runtime updated index.val replacement hwrite]
      exact hrel.length_eq
    type_at := ?_
    value_at := ?_
  }
  · intro j
    by_cases hji : j = index
    · subst j
      have htarget :=
        runtimeWriteRegister_target runtime updated index.val replacement hwrite
      simp [runtimeTypeAt, htarget, hdecl]
    · have hjiVal : j.val ≠ index.val := by
        intro heq
        exact hji (Fin.ext heq)
      have hother :=
        runtimeWriteRegister_other_unchanged
          runtime updated index.val j.val replacement hwrite hjiVal
      simpa [runtimeTypeAt, hother] using hrel.type_at j
  · intro j
    by_cases hji : j = index
    · subst j
      have htarget :=
        runtimeWriteRegister_target runtime updated index.val replacement hwrite
      have hpayload :=
        RuntimeRegister.value?_of_initialized replacement hinit
      simp [runtimeValueAt, htarget, hpayload, write]
    · have hjiVal : j.val ≠ index.val := by
        intro heq
        exact hji (Fin.ext heq)
      have hother :=
        runtimeWriteRegister_other_unchanged
          runtime updated index.val j.val replacement hwrite hjiVal
      simp [runtimeValueAt, hother, write, hji, hrel.value_at j]

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
    simp [hrel.length_eq]
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
    simp [hrel.length_eq]
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
  cases hreg : runtime[index.val]? with
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
              simpa [hasType, hasTypeB, htarget] using reg.intValue_in_range
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
              simp [hasType, hasTypeB, htarget]

end CapstanVerification
