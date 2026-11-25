import CapstanVerification.RuntimeBridge

namespace CapstanVerification

/-!
Concrete register-field refinement boundary for verification/ccam_core.cap.

The executable representation uses integer tags (1 = int, 2 = bool), an
initialisation bit, and separate integer/boolean payload fields. This module
models those concrete fields explicitly and proves that tag decoding, reads,
and successful field updates correspond to the typed RuntimeRegister model.

This is still a representation-level theorem. It does not prove Capstan's
object-identity semantics, List indexing/mutation implementation, compiler
lowering, or the evaluator's whole-state transition relation.
-/

/-- The concrete tag assigned by CCAMRegister to integer registers. -/
def nativeIntTypeTag : Int := 1

/-- The concrete tag assigned by CCAMRegister to boolean registers. -/
def nativeBoolTypeTag : Int := 2

/-- Decode the integer type tag used by the Capstan-native CCAM substrate. -/
def decodeNativeTypeTag (tag : Int) : Option Ty :=
  if tag = nativeIntTypeTag then some .int
  else if tag = nativeBoolTypeTag then some .bool
  else none

theorem decodeNativeTypeTag_int_iff (tag : Int) :
    decodeNativeTypeTag tag = some .int ↔ tag = nativeIntTypeTag := by
  simp [decodeNativeTypeTag, nativeIntTypeTag, nativeBoolTypeTag]

theorem decodeNativeTypeTag_bool_iff (tag : Int) :
    decodeNativeTypeTag tag = some .bool ↔ tag = nativeBoolTypeTag := by
  simp [decodeNativeTypeTag, nativeIntTypeTag, nativeBoolTypeTag]

/-- Explicit model of the fields in the executable CCAMRegister structure. -/
structure NativeCCAMRegister where
  declaredTypeTag : Int
  initialized : Bool
  intValue : Int
  intValue_in_range : inI64 intValue
  boolValue : Bool

/-- The abstract runtime register created from a typed register declaration. -/
def runtimeRegisterInit (ty : Ty) : RuntimeRegister :=
  { declaredType := ty
    initialized := false
    intValue := 0
    intValue_in_range := by change inI64B 0 = true; decide
    boolValue := false }

/-- The native register constructor used after the type tag has been checked. -/
def nativeRegisterInit (tag : Int) : NativeCCAMRegister :=
  { declaredTypeTag := tag
    initialized := false
    intValue := 0
    intValue_in_range := by change inI64B 0 = true; decide
    boolValue := false }

/-- Relate the concrete integer tag and payload fields to the abstract record. -/
def NativeRegisterMatches
    (native : NativeCCAMRegister) (runtime : RuntimeRegister) : Prop :=
  decodeNativeTypeTag native.declaredTypeTag = some runtime.declaredType ∧
  native.initialized = runtime.initialized ∧
  native.intValue = runtime.intValue ∧
  native.boolValue = runtime.boolValue

theorem nativeRegisterInit_matches_int :
    NativeRegisterMatches (nativeRegisterInit nativeIntTypeTag)
      (runtimeRegisterInit .int) := by
  refine ⟨rfl, rfl, rfl, rfl⟩

theorem nativeRegisterInit_matches_bool :
    NativeRegisterMatches (nativeRegisterInit nativeBoolTypeTag)
      (runtimeRegisterInit .bool) := by
  refine ⟨rfl, rfl, rfl, rfl⟩

/-- Integer read from the concrete register fields, before list-index checking. -/
def nativeRegisterReadInt (reg : NativeCCAMRegister) : Except Trap Int :=
  if reg.initialized then
    if reg.declaredTypeTag = nativeIntTypeTag then
      .ok reg.intValue
    else
      .error .typeMismatch
  else
    .error .uninitialisedRegister

/-- Boolean read from the concrete register fields, before list-index checking. -/
def nativeRegisterReadBool (reg : NativeCCAMRegister) : Except Trap Bool :=
  if reg.initialized then
    if reg.declaredTypeTag = nativeBoolTypeTag then
      .ok reg.boolValue
    else
      .error .typeMismatch
  else
    .error .uninitialisedRegister

/-- The same read operation over the abstract typed runtime record. -/
def runtimeRegisterReadInt (reg : RuntimeRegister) : Except Trap Int :=
  match reg.value? with
  | none => .error .uninitialisedRegister
  | some (.int value) => .ok value
  | some (.bool _) => .error .typeMismatch

/-- The same boolean read operation over the abstract typed runtime record. -/
def runtimeRegisterReadBool (reg : RuntimeRegister) : Except Trap Bool :=
  match reg.value? with
  | none => .error .uninitialisedRegister
  | some (.int _) => .error .typeMismatch
  | some (.bool value) => .ok value

theorem nativeRegisterReadInt_corresponds
    (native : NativeCCAMRegister) (runtime : RuntimeRegister)
    (hmatch : NativeRegisterMatches native runtime) :
    nativeRegisterReadInt native = runtimeRegisterReadInt runtime := by
  rcases hmatch with ⟨htag, hinit, hint, hbool⟩
  cases htype : runtime.declaredType with
  | int =>
      have htagInt : native.declaredTypeTag = nativeIntTypeTag :=
        (decodeNativeTypeTag_int_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      cases hruntimeInit : runtime.initialized
      · have hnativeInit : native.initialized = false := by
          rw [hinit, hruntimeInit]
        simp [nativeRegisterReadInt, runtimeRegisterReadInt,
          RuntimeRegister.value?, htagInt, hnativeInit, hruntimeInit, htype]
      · have hnativeInit : native.initialized = true := by
          rw [hinit, hruntimeInit]
        simp [nativeRegisterReadInt, runtimeRegisterReadInt,
          RuntimeRegister.value?, htagInt, hnativeInit, hruntimeInit, htype, hint,
          nativeIntTypeTag, nativeBoolTypeTag]
  | bool =>
      have htagBool : native.declaredTypeTag = nativeBoolTypeTag :=
        (decodeNativeTypeTag_bool_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      cases hruntimeInit : runtime.initialized
      · have hnativeInit : native.initialized = false := by
          rw [hinit, hruntimeInit]
        simp [nativeRegisterReadInt, runtimeRegisterReadInt,
          RuntimeRegister.value?, htagBool, hnativeInit, hruntimeInit, htype,
          nativeIntTypeTag, nativeBoolTypeTag]
      · have hnativeInit : native.initialized = true := by
          rw [hinit, hruntimeInit]
        have htags_ne : nativeBoolTypeTag ≠ nativeIntTypeTag := by decide
        simp [nativeRegisterReadInt, runtimeRegisterReadInt,
          RuntimeRegister.value?, htagBool, hnativeInit, hruntimeInit, htype,
          htags_ne]

theorem nativeRegisterReadBool_corresponds
    (native : NativeCCAMRegister) (runtime : RuntimeRegister)
    (hmatch : NativeRegisterMatches native runtime) :
    nativeRegisterReadBool native = runtimeRegisterReadBool runtime := by
  rcases hmatch with ⟨htag, hinit, hint, hbool⟩
  cases htype : runtime.declaredType with
  | int =>
      have htagInt : native.declaredTypeTag = nativeIntTypeTag :=
        (decodeNativeTypeTag_int_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      cases hruntimeInit : runtime.initialized
      · have hnativeInit : native.initialized = false := by
          rw [hinit, hruntimeInit]
        simp [nativeRegisterReadBool, runtimeRegisterReadBool,
          RuntimeRegister.value?, htagInt, hnativeInit, hruntimeInit,
          nativeIntTypeTag, nativeBoolTypeTag]
      · have hnativeInit : native.initialized = true := by
          rw [hinit, hruntimeInit]
        have htags_ne : nativeIntTypeTag ≠ nativeBoolTypeTag := by decide
        unfold runtimeRegisterReadBool
        simp [nativeRegisterReadBool, RuntimeRegister.value?,
          htagInt, hnativeInit, hruntimeInit, htags_ne, htype, hint,
          nativeIntTypeTag, nativeBoolTypeTag]
  | bool =>
      have htagBool : native.declaredTypeTag = nativeBoolTypeTag :=
        (decodeNativeTypeTag_bool_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      cases hruntimeInit : runtime.initialized
      · have hnativeInit : native.initialized = false := by
          rw [hinit, hruntimeInit]
        simp [nativeRegisterReadBool, runtimeRegisterReadBool,
          RuntimeRegister.value?, htagBool, hnativeInit, hruntimeInit, htype]
      · have hnativeInit : native.initialized = true := by
          rw [hinit, hruntimeInit]
        simp [nativeRegisterReadBool, runtimeRegisterReadBool,
          RuntimeRegister.value?, htagBool, hnativeInit, hruntimeInit, htype, hbool,
          nativeIntTypeTag, nativeBoolTypeTag]

/-- Model the native integer-field assignment and initialization-bit update. -/
def nativeRegisterWriteInt
    (reg : NativeCCAMRegister) (value : Int) (hvalue : inI64 value) :
    NativeCCAMRegister :=
  { reg with initialized := true, intValue := value, intValue_in_range := hvalue }

/-- Model the abstract runtime record's corresponding integer-field assignment. -/
def runtimeRegisterWriteInt
    (reg : RuntimeRegister) (value : Int) (hvalue : inI64 value) :
    RuntimeRegister :=
  { reg with initialized := true, intValue := value, intValue_in_range := hvalue }

/-- Model the native boolean-field assignment and initialization-bit update. -/
def nativeRegisterWriteBool
    (reg : NativeCCAMRegister) (value : Bool) : NativeCCAMRegister :=
  { reg with initialized := true, boolValue := value }

/-- Model the abstract runtime record's corresponding boolean-field assignment. -/
def runtimeRegisterWriteBool
    (reg : RuntimeRegister) (value : Bool) : RuntimeRegister :=
  { reg with initialized := true, boolValue := value }

theorem nativeRegisterWriteInt_preserves_relation
    (native : NativeCCAMRegister) (runtime : RuntimeRegister)
    (value : Int) (hvalue : inI64 value)
    (hmatch : NativeRegisterMatches native runtime) :
    NativeRegisterMatches
      (nativeRegisterWriteInt native value hvalue)
      (runtimeRegisterWriteInt runtime value hvalue) := by
  rcases hmatch with ⟨htag, _, _, hbool⟩
  exact ⟨htag, rfl, rfl, hbool⟩

theorem nativeRegisterWriteBool_preserves_relation
    (native : NativeCCAMRegister) (runtime : RuntimeRegister)
    (value : Bool)
    (hmatch : NativeRegisterMatches native runtime) :
    NativeRegisterMatches
      (nativeRegisterWriteBool native value)
      (runtimeRegisterWriteBool runtime value) := by
  rcases hmatch with ⟨htag, _, hint, _⟩
  exact ⟨htag, rfl, hint, rfl⟩

/-- A successful integer write can be read back from the native register. -/
theorem nativeRegisterWriteInt_readback
    (native : NativeCCAMRegister) (value : Int) (hvalue : inI64 value)
    (htag : native.declaredTypeTag = nativeIntTypeTag) :
    nativeRegisterReadInt (nativeRegisterWriteInt native value hvalue) = .ok value := by
  simp [nativeRegisterReadInt, nativeRegisterWriteInt, htag]

/-- A successful boolean write can be read back from the native register. -/
theorem nativeRegisterWriteBool_readback
    (native : NativeCCAMRegister) (value : Bool)
    (htag : native.declaredTypeTag = nativeBoolTypeTag) :
    nativeRegisterReadBool (nativeRegisterWriteBool native value) = .ok value := by
  simp [nativeRegisterReadBool, nativeRegisterWriteBool, htag]

/-- The native integer writer's local type check followed by its field update. -/
def nativeRegisterWriteIntChecked
    (reg : NativeCCAMRegister) (value : Int) (hvalue : inI64 value) :
    Except Trap NativeCCAMRegister :=
  if reg.declaredTypeTag = nativeIntTypeTag then
    .ok (nativeRegisterWriteInt reg value hvalue)
  else
    .error .typeMismatch

/-- The abstract integer writer's corresponding type check and field update. -/
def runtimeRegisterWriteIntChecked
    (reg : RuntimeRegister) (value : Int) (hvalue : inI64 value) :
    Except Trap RuntimeRegister :=
  if reg.declaredType = .int then
    .ok (runtimeRegisterWriteInt reg value hvalue)
  else
    .error .typeMismatch

/-- The native and abstract integer writers agree, including type-mismatch traps. -/
theorem nativeRegisterWriteIntChecked_corresponds
    (native : NativeCCAMRegister) (runtime : RuntimeRegister)
    (value : Int) (hvalue : inI64 value)
    (hmatch : NativeRegisterMatches native runtime) :
    (nativeRegisterWriteIntChecked native value hvalue).map
      (fun updated => (updated.declaredTypeTag, updated.initialized,
        updated.intValue, updated.boolValue)) =
    (runtimeRegisterWriteIntChecked runtime value hvalue).map
      (fun updated => (native.declaredTypeTag, updated.initialized,
        updated.intValue, updated.boolValue)) := by
  rcases hmatch with ⟨htag, hinit, hint, hbool⟩
  cases htype : runtime.declaredType with
  | int =>
      have htagInt : native.declaredTypeTag = nativeIntTypeTag :=
        (decodeNativeTypeTag_int_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      simp [nativeRegisterWriteIntChecked, runtimeRegisterWriteIntChecked,
        htagInt, htype, hbool, nativeIntTypeTag, nativeBoolTypeTag, nativeRegisterWriteInt, runtimeRegisterWriteInt, Except.map]
  | bool =>
      have htagBool : native.declaredTypeTag = nativeBoolTypeTag :=
        (decodeNativeTypeTag_bool_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      simp [nativeRegisterWriteIntChecked, runtimeRegisterWriteIntChecked,
        htagBool, htype, hbool, nativeIntTypeTag, nativeBoolTypeTag, nativeRegisterWriteInt, runtimeRegisterWriteInt, Except.map]

/-- The native boolean writer's local type check followed by its field update. -/
def nativeRegisterWriteBoolChecked
    (reg : NativeCCAMRegister) (value : Bool) :
    Except Trap NativeCCAMRegister :=
  if reg.declaredTypeTag = nativeBoolTypeTag then
    .ok (nativeRegisterWriteBool reg value)
  else
    .error .typeMismatch

/-- The abstract boolean writer's corresponding type check and field update. -/
def runtimeRegisterWriteBoolChecked
    (reg : RuntimeRegister) (value : Bool) :
    Except Trap RuntimeRegister :=
  if reg.declaredType = .bool then
    .ok (runtimeRegisterWriteBool reg value)
  else
    .error .typeMismatch

/-- The native and abstract boolean writers agree, including type-mismatch traps. -/
theorem nativeRegisterWriteBoolChecked_corresponds
    (native : NativeCCAMRegister) (runtime : RuntimeRegister)
    (value : Bool)
    (hmatch : NativeRegisterMatches native runtime) :
    (nativeRegisterWriteBoolChecked native value).map
      (fun updated => (updated.declaredTypeTag, updated.initialized,
        updated.intValue, updated.boolValue)) =
    (runtimeRegisterWriteBoolChecked runtime value).map
      (fun updated => (native.declaredTypeTag, updated.initialized,
        updated.intValue, updated.boolValue)) := by
  rcases hmatch with ⟨htag, hinit, hint, hbool⟩
  cases htype : runtime.declaredType with
  | int =>
      have htagInt : native.declaredTypeTag = nativeIntTypeTag :=
        (decodeNativeTypeTag_int_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      simp [nativeRegisterWriteBoolChecked, runtimeRegisterWriteBoolChecked,
        htagInt, htype, hint, nativeIntTypeTag, nativeBoolTypeTag, nativeRegisterWriteBool, runtimeRegisterWriteBool, Except.map]
  | bool =>
      have htagBool : native.declaredTypeTag = nativeBoolTypeTag :=
        (decodeNativeTypeTag_bool_iff native.declaredTypeTag).mp (by
          simpa [htype] using htag)
      simp [nativeRegisterWriteBoolChecked, runtimeRegisterWriteBoolChecked,
        htagBool, htype, hint, nativeIntTypeTag, nativeBoolTypeTag, nativeRegisterWriteBool, runtimeRegisterWriteBool, Except.map]

end CapstanVerification
