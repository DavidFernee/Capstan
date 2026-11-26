import CapstanVerification.NativeRegisterFileBridge

namespace CapstanVerification

/-!
Initial-state representation correspondence for the C-free CCAM scalar
register file.

This module connects the exact constructor defaults on the native-shaped
register record to the abstract RuntimeBridge record. It deliberately proves
only the register-file initialisation boundary: it does not claim that the
Capstan evaluator's object allocation, List implementation, or whole machine
constructor refines the Lean machine.
-/

/-- Construct a native-shaped register from one already-decoded scalar type. -/
def nativeRegisterInitForType (ty : Ty) : NativeCCAMRegister :=
  nativeRegisterInit (match ty with
    | .int => nativeIntTypeTag
    | .bool => nativeBoolTypeTag)

/-- Construct the corresponding abstract runtime register. -/
def runtimeRegisterInitForType (ty : Ty) : RuntimeRegister :=
  runtimeRegisterInit ty

/-- The concrete tag, initialisation bit and payload fields agree at creation. -/
theorem nativeRegisterInitForType_matches (ty : Ty) :
    NativeRegisterMatches (nativeRegisterInitForType ty)
      (runtimeRegisterInitForType ty) := by
  cases ty with
  | int => exact nativeRegisterInit_matches_int
  | bool => exact nativeRegisterInit_matches_bool

/-- Build the native-shaped register list from a validated type vector. -/
def nativeInitialRegisterFile (types : List Ty) : List NativeCCAMRegister :=
  types.map nativeRegisterInitForType

/-- Build the abstract runtime list from the same validated type vector. -/
def runtimeInitialRegisterFile (types : List Ty) : List RuntimeRegister :=
  types.map runtimeRegisterInitForType

/-- Pairwise relation between native-shaped and abstract initial register lists. -/
inductive InitialRegisterListsMatch :
    List NativeCCAMRegister → List RuntimeRegister → Prop
  | nil : InitialRegisterListsMatch [] []
  | cons {native runtime nativeRest runtimeRest}
      (head : NativeRegisterMatches native runtime)
      (tail : InitialRegisterListsMatch nativeRest runtimeRest) :
      InitialRegisterListsMatch (native :: nativeRest) (runtime :: runtimeRest)

/-- Initial native and abstract files have the same length and pairwise fields. -/
theorem initialRegisterFiles_correspond (types : List Ty) :
    InitialRegisterListsMatch
      (nativeInitialRegisterFile types) (runtimeInitialRegisterFile types) := by
  induction types with
  | nil => exact InitialRegisterListsMatch.nil
  | cons ty rest ih =>
      exact InitialRegisterListsMatch.cons
        (nativeRegisterInitForType_matches ty) ih

/-- Convert the inductive pairwise initialisation proof to the reusable
native/runtime register-file relation used by the write/read simulation lemmas. -/
theorem InitialRegisterListsMatch.toNativeRuntimeRegisterFileRelation
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hmatch : InitialRegisterListsMatch native runtime) :
    NativeRuntimeRegisterFileRelation native runtime := by
  induction hmatch with
  | nil =>
      constructor
      · rfl
      · intro index nativeReg runtimeReg hnative hruntime
        simp at hnative
  | @cons native runtime nativeRest runtimeRest hhead htail ih =>
      constructor
      · simp
      · intro index nativeReg runtimeReg hnative hruntime
        cases index with
        | zero =>
            simp at hnative hruntime
            cases hnative
            cases hruntime
            exact hhead
        | succ index =>
            simp at hnative hruntime
            exact ih.matches_at index nativeReg runtimeReg hnative hruntime

/-- The initial native and abstract lists satisfy the established reusable
register-file relation, not merely a bespoke pairwise list predicate. -/
theorem initialRegisterFiles_nativeRuntimeRelation (types : List Ty) :
    NativeRuntimeRegisterFileRelation
      (nativeInitialRegisterFile types) (runtimeInitialRegisterFile types) :=
  InitialRegisterListsMatch.toNativeRuntimeRegisterFileRelation
    (initialRegisterFiles_correspond types)

/-- Every native register starts uninitialised, independently of its type. -/
theorem nativeInitialRegisterFile_uninitialised (types : List Ty) :
    ∀ register ∈ nativeInitialRegisterFile types,
      register.initialized = false := by
  intro register hmember
  rcases List.mem_map.mp hmember with ⟨ty, _hty, hregister⟩
  rw [← hregister]
  cases ty <;> rfl

/-- Every abstract runtime register starts uninitialised, independently of its type. -/
theorem runtimeInitialRegisterFile_uninitialised (types : List Ty) :
    ∀ register ∈ runtimeInitialRegisterFile types,
      register.initialized = false := by
  intro register hmember
  rcases List.mem_map.mp hmember with ⟨ty, _hty, hregister⟩
  rw [← hregister]
  cases ty <;> rfl

end CapstanVerification
