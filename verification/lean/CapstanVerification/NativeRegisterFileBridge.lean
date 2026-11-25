import CapstanVerification.NativeRegisterBridge

namespace CapstanVerification

/-!
List-level bridge for the concrete CCAM register file.

The executable substrate stores NativeCCAMRegister-shaped records in a list.
This module adds bounds-aware list operations and relates successful indexed
reads and writes to the existing RuntimeBridge list model.

The model deliberately keeps the host-language list/object update semantics
outside its theorem boundary. It proves properties of the corresponding
mathematical list operations, not yet that Capstan's List implementation
refines those operations.
-/

/-- Replace one native register slot, preserving the list shape. -/
def nativeRegisterSetAt :
    List NativeCCAMRegister → Nat → NativeCCAMRegister →
      List NativeCCAMRegister
  | [], _, _ => []
  | _ :: rest, 0, replacement => replacement :: rest
  | head :: rest, Nat.succ index, replacement =>
      head :: nativeRegisterSetAt rest index replacement

/-- Native list replacement preserves length. -/
theorem nativeRegisterSetAt_length
    (registers : List NativeCCAMRegister) (index : Nat)
    (replacement : NativeCCAMRegister) :
    (nativeRegisterSetAt registers index replacement).length =
      registers.length := by
  induction registers generalizing index with
  | nil => simp [nativeRegisterSetAt]
  | cons head rest ih =>
      cases index with
      | zero => rfl
      | succ index => simp [nativeRegisterSetAt, ih]

/-- A native replacement is observable at the updated slot. -/
theorem nativeRegisterSetAt_get_same
    (registers : List NativeCCAMRegister) (index : Nat)
    (replacement : NativeCCAMRegister)
    (hbound : index < registers.length) :
    (nativeRegisterSetAt registers index replacement)[index]? =
      some replacement := by
  induction registers generalizing index with
  | nil => simp at hbound
  | cons head rest ih =>
      cases index with
      | zero => rfl
      | succ index =>
          simp only [List.length_cons] at hbound
          simp only [nativeRegisterSetAt, List.get?_cons_succ]
          exact ih index (by omega)

/-- A native replacement leaves a distinct, in-bounds slot unchanged. -/
theorem nativeRegisterSetAt_get_other
    (registers : List NativeCCAMRegister) (index other : Nat)
    (replacement : NativeCCAMRegister)
    (hbound : index < registers.length)
    (hother : other < registers.length)
    (hdistinct : other ≠ index) :
    (nativeRegisterSetAt registers index replacement)[other]? =
      registers[other]? := by
  induction registers generalizing index other with
  | nil => simp at hbound
  | cons head rest ih =>
      cases index with
      | zero =>
          cases other with
          | zero => exact False.elim (hdistinct rfl)
          | succ other => rfl
      | succ index =>
          cases other with
          | zero => rfl
          | succ other =>
              simp only [List.length_cons] at hbound hother
              simp only [nativeRegisterSetAt, List.get?_cons_succ]
              apply ih index other replacement
              · omega
              · omega
              · intro heq
                exact hdistinct (congrArg Nat.succ heq)

/-- A list relation pairing every corresponding native and runtime register. -/
structure NativeRuntimeRegisterFileRelation
    (native : List NativeCCAMRegister)
    (runtime : List RuntimeRegister) : Prop where
  length_eq : native.length = runtime.length
  matches_at : ∀ index nativeReg runtimeReg,
    native[index]? = some nativeReg →
    runtime[index]? = some runtimeReg →
    NativeRegisterMatches nativeReg runtimeReg

/-- Bounds-checked integer read over the native register list. -/
def nativeRegisterReadIntAt
    (registers : List NativeCCAMRegister) (index : Nat) :
    Except Trap Int :=
  if index < registers.length then
    match registers[index]? with
    | none => .error .invalidRegister
    | some reg => nativeRegisterReadInt reg
  else
    .error .invalidRegister

/-- Bounds-checked boolean read over the native register list. -/
def nativeRegisterReadBoolAt
    (registers : List NativeCCAMRegister) (index : Nat) :
    Except Trap Bool :=
  if index < registers.length then
    match registers[index]? with
    | none => .error .invalidRegister
    | some reg => nativeRegisterReadBool reg
  else
    .error .invalidRegister

/-- The corresponding bounds-checked integer read over RuntimeBridge lists. -/
def runtimeRegisterReadIntAt
    (registers : List RuntimeRegister) (index : Nat) :
    Except Trap Int :=
  if index < registers.length then
    match registers[index]? with
    | none => .error .invalidRegister
    | some reg => runtimeRegisterReadInt reg
  else
    .error .invalidRegister

/-- The corresponding bounds-checked boolean read over RuntimeBridge lists. -/
def runtimeRegisterReadBoolAt
    (registers : List RuntimeRegister) (index : Nat) :
    Except Trap Bool :=
  if index < registers.length then
    match registers[index]? with
    | none => .error .invalidRegister
    | some reg => runtimeRegisterReadBool reg
  else
    .error .invalidRegister

/-- Related files agree on an in-bounds integer read at a paired slot. -/
theorem nativeRegisterReadIntAt_corresponds
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hrel : NativeRuntimeRegisterFileRelation native runtime)
    (index : Nat) (nativeReg : NativeCCAMRegister)
    (runtimeReg : RuntimeRegister)
    (hbound : index < native.length)
    (hnative : native[index]? = some nativeReg)
    (hruntime : runtime[index]? = some runtimeReg) :
    nativeRegisterReadIntAt native index =
      runtimeRegisterReadIntAt runtime index := by
  have hmatch := hrel.matches_at index nativeReg runtimeReg hnative hruntime
  have hruntimeBound : index < runtime.length := by
    rw [← hrel.length_eq]
    exact hbound
  simp [nativeRegisterReadIntAt, runtimeRegisterReadIntAt,
    hbound, hruntimeBound, hnative, hruntime,
    nativeRegisterReadInt_corresponds nativeReg runtimeReg hmatch]

/-- Related files agree on an in-bounds boolean read at a paired slot. -/
theorem nativeRegisterReadBoolAt_corresponds
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hrel : NativeRuntimeRegisterFileRelation native runtime)
    (index : Nat) (nativeReg : NativeCCAMRegister)
    (runtimeReg : RuntimeRegister)
    (hbound : index < native.length)
    (hnative : native[index]? = some nativeReg)
    (hruntime : runtime[index]? = some runtimeReg) :
    nativeRegisterReadBoolAt native index =
      runtimeRegisterReadBoolAt runtime index := by
  have hmatch := hrel.matches_at index nativeReg runtimeReg hnative hruntime
  have hruntimeBound : index < runtime.length := by
    rw [← hrel.length_eq]
    exact hbound
  simp [nativeRegisterReadBoolAt, runtimeRegisterReadBoolAt,
    hbound, hruntimeBound, hnative, hruntime,
    nativeRegisterReadBool_corresponds nativeReg runtimeReg hmatch]

/-- Both list readers reject every out-of-range native index. -/
theorem nativeRegisterReadIntAt_invalid
    (registers : List NativeCCAMRegister) (index : Nat)
    (hbound : ¬ index < registers.length) :
    nativeRegisterReadIntAt registers index = .error .invalidRegister := by
  simp [nativeRegisterReadIntAt, hbound]

/-- Both list readers reject every out-of-range boolean index. -/
theorem nativeRegisterReadBoolAt_invalid
    (registers : List NativeCCAMRegister) (index : Nat)
    (hbound : ¬ index < registers.length) :
    nativeRegisterReadBoolAt registers index = .error .invalidRegister := by
  simp [nativeRegisterReadBoolAt, hbound]

/-- A successful native list replacement preserves file length. -/
theorem nativeRegisterSetAt_preserves_length
    (registers : List NativeCCAMRegister) (index : Nat)
    (replacement : NativeCCAMRegister) :
    (nativeRegisterSetAt registers index replacement).length =
      registers.length :=
  nativeRegisterSetAt_length registers index replacement

/-- The runtime model's replacement has the same target-slot behaviour. -/
theorem runtimeRegisterSetAt_get_same
    (registers : List RuntimeRegister) (index : Nat)
    (replacement : RuntimeRegister)
    (hbound : index < registers.length) :
    runtimeRegisterAt (runtimeSetAt registers index replacement) index =
      some replacement := by
  have hlookup : runtimeRegisterAt registers index ≠ none := by
    simp [runtimeRegisterAt, List.get?_eq_none]
    omega
  cases hreg : runtimeRegisterAt registers index with
  | none => exact False.elim (hlookup hreg)
  | some old =>
      exact runtimeSetAt_get_same_of_exists
        registers index old replacement hreg

end CapstanVerification
