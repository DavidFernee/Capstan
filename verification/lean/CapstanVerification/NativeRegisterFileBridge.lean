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

/-- Signed-index native integer read: reject negative indices before conversion. -/
def nativeRegisterReadIntAtSigned
    (registers : List NativeCCAMRegister) (index : Int) :
    Except Trap Int :=
  if index < 0 then
    .error .invalidRegister
  else
    nativeRegisterReadIntAt registers index.toNat

/-- Signed-index native boolean read: reject negative indices before conversion. -/
def nativeRegisterReadBoolAtSigned
    (registers : List NativeCCAMRegister) (index : Int) :
    Except Trap Bool :=
  if index < 0 then
    .error .invalidRegister
  else
    nativeRegisterReadBoolAt registers index.toNat

/-- Negative signed integer indices trap as invalid registers. -/
theorem nativeRegisterReadIntAtSigned_negative
    (registers : List NativeCCAMRegister) (index : Int)
    (hnegative : index < 0) :
    nativeRegisterReadIntAtSigned registers index = .error .invalidRegister := by
  simp [nativeRegisterReadIntAtSigned, hnegative]

/-- Negative signed boolean indices trap as invalid registers. -/
theorem nativeRegisterReadBoolAtSigned_negative
    (registers : List NativeCCAMRegister) (index : Int)
    (hnegative : index < 0) :
    nativeRegisterReadBoolAtSigned registers index = .error .invalidRegister := by
  simp [nativeRegisterReadBoolAtSigned, hnegative]

/-- Nonnegative signed integer indices delegate exactly to the Nat-index reader. -/
theorem nativeRegisterReadIntAtSigned_nonnegative
    (registers : List NativeCCAMRegister) (index : Int)
    (hnonnegative : 0 ≤ index) :
    nativeRegisterReadIntAtSigned registers index =
      nativeRegisterReadIntAt registers index.toNat := by
  have hnotnegative : ¬ index < 0 := by omega
  simp [nativeRegisterReadIntAtSigned, hnotnegative]

/-- Nonnegative signed boolean indices delegate exactly to the Nat-index reader. -/
theorem nativeRegisterReadBoolAtSigned_nonnegative
    (registers : List NativeCCAMRegister) (index : Int)
    (hnonnegative : 0 ≤ index) :
    nativeRegisterReadBoolAtSigned registers index =
      nativeRegisterReadBoolAt registers index.toNat := by
  have hnotnegative : ¬ index < 0 := by omega
  simp [nativeRegisterReadBoolAtSigned, hnotnegative]

/-- A checked native slot replacement rejects missing indices and preserves
the declared type tag of an existing slot. -/
def nativeWriteRegister (registers : List NativeCCAMRegister)
    (index : Nat) (replacement : NativeCCAMRegister) :
    Except Trap (List NativeCCAMRegister) :=
  match registers[index]? with
  | none => .error .invalidRegister
  | some old =>
      if old.declaredTypeTag = replacement.declaredTypeTag then
        .ok (nativeRegisterSetAt registers index replacement)
      else
        .error .typeMismatch

/-- A successful native indexed write installs its replacement at the target. -/
theorem nativeWriteRegister_target
    (registers updated : List NativeCCAMRegister)
    (index : Nat) (replacement : NativeCCAMRegister)
    (hwrite : nativeWriteRegister registers index replacement = .ok updated) :
    updated[index]? = some replacement := by
  unfold nativeWriteRegister at hwrite
  cases hreg : registers[index]? with
  | none => simp [hreg] at hwrite
  | some old =>
      by_cases htype : old.declaredTypeTag = replacement.declaredTypeTag
      · simp [hreg, htype] at hwrite
        cases hwrite
        have hbound : index < registers.length := List.isSome_get?_1 hreg
        exact nativeRegisterSetAt_get_same registers index replacement hbound
      · simp [hreg, htype] at hwrite

/-- Successful native indexed replacement preserves register-file length. -/
theorem nativeWriteRegister_length
    (registers updated : List NativeCCAMRegister)
    (index : Nat) (replacement : NativeCCAMRegister)
    (hwrite : nativeWriteRegister registers index replacement = .ok updated) :
    updated.length = registers.length := by
  unfold nativeWriteRegister at hwrite
  cases hreg : registers[index]? with
  | none => simp [hreg] at hwrite
  | some old =>
      by_cases htype : old.declaredTypeTag = replacement.declaredTypeTag
      · simp [hreg, htype] at hwrite
        cases hwrite
        exact nativeRegisterSetAt_length registers index replacement
      · simp [hreg, htype] at hwrite

/-- A successful native indexed replacement leaves any distinct in-bounds slot intact. -/
theorem nativeWriteRegister_other_unchanged
    (registers updated : List NativeCCAMRegister)
    (index other : Nat) (replacement : NativeCCAMRegister)
    (hwrite : nativeWriteRegister registers index replacement = .ok updated)
    (hindex : index < registers.length)
    (hother : other < registers.length)
    (hdistinct : other ≠ index) :
    updated[other]? = registers[other]? := by
  unfold nativeWriteRegister at hwrite
  cases hreg : registers[index]? with
  | none => simp [hreg] at hwrite
  | some old =>
      by_cases htype : old.declaredTypeTag = replacement.declaredTypeTag
      · simp [hreg, htype] at hwrite
        cases hwrite
        exact nativeRegisterSetAt_get_other registers index other replacement
          hindex hother hdistinct
      · simp [hreg, htype] at hwrite

/-- Signed-index native writes reject negative indices before conversion. -/
def nativeWriteRegisterSigned (registers : List NativeCCAMRegister)
    (index : Int) (replacement : NativeCCAMRegister) :
    Except Trap (List NativeCCAMRegister) :=
  if index < 0 then .error .invalidRegister
  else nativeWriteRegister registers index.toNat replacement

theorem nativeWriteRegisterSigned_negative
    (registers : List NativeCCAMRegister) (index : Int)
    (replacement : NativeCCAMRegister) (hnegative : index < 0) :
    nativeWriteRegisterSigned registers index replacement = .error .invalidRegister := by
  simp [nativeWriteRegisterSigned, hnegative]

/-- A successful signed native write is exactly its nonnegative Nat-index write. -/
theorem nativeWriteRegisterSigned_nonnegative
    (registers : List NativeCCAMRegister) (index : Int)
    (replacement : NativeCCAMRegister) (hnonnegative : 0 ≤ index) :
    nativeWriteRegisterSigned registers index replacement =
      nativeWriteRegister registers index.toNat replacement := by
  have hnotnegative : ¬ index < 0 := by omega
  simp [nativeWriteRegisterSigned, hnotnegative]


/-- A successful native write necessarily addresses an existing slot. -/
theorem nativeWriteRegister_index_in_bounds
    (registers updated : List NativeCCAMRegister)
    (index : Nat) (replacement : NativeCCAMRegister)
    (hwrite : nativeWriteRegister registers index replacement = .ok updated) :
    index < registers.length := by
  unfold nativeWriteRegister at hwrite
  cases hreg : registers[index]? with
  | none => simp [hreg] at hwrite
  | some old => exact List.isSome_get?_1 hreg

/-- A successful abstract runtime write necessarily addresses an existing slot. -/
theorem runtimeWriteRegister_index_in_bounds
    (registers updated : List RuntimeRegister)
    (index : Nat) (replacement : RuntimeRegister)
    (hwrite : runtimeWriteRegister registers index replacement = .ok updated) :
    index < registers.length := by
  unfold runtimeWriteRegister at hwrite
  cases hreg : runtimeRegisterAt registers index with
  | none => simp [hreg] at hwrite
  | some old =>
      have hsome : registers[index]? = some old := hreg
      exact List.isSome_get?_1 hsome

/-- Paired successful native/runtime writes preserve the pointwise register
representation relation, including the target and all untouched slots.

The two successful-write premises deliberately isolate the representation
proof from the separate obligation to show the concrete and abstract type
checks accept exactly the same inputs. -/
theorem nativeRuntimeRegisterFileRelation_write
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hrel : NativeRuntimeRegisterFileRelation native runtime)
    (index : Nat)
    (nativeReplacement : NativeCCAMRegister)
    (runtimeReplacement : RuntimeRegister)
    (hreplacement : NativeRegisterMatches nativeReplacement runtimeReplacement)
    {nativeUpdated : List NativeCCAMRegister}
    {runtimeUpdated : List RuntimeRegister}
    (hnativeWrite :
      nativeWriteRegister native index nativeReplacement = .ok nativeUpdated)
    (hruntimeWrite :
      runtimeWriteRegister runtime index runtimeReplacement = .ok runtimeUpdated) :
    NativeRuntimeRegisterFileRelation nativeUpdated runtimeUpdated := by
  refine {
    length_eq := by
      rw [nativeWriteRegister_length native nativeUpdated index nativeReplacement hnativeWrite,
        runtimeWriteRegister_length runtime runtimeUpdated index runtimeReplacement hruntimeWrite]
      exact hrel.length_eq
    matches_at := ?_
  }
  intro other nativeReg runtimeReg hnativeAt hruntimeAt
  by_cases htarget : other = index
  · subst other
    have hnativeTarget :=
      nativeWriteRegister_target native nativeUpdated index nativeReplacement hnativeWrite
    have hruntimeTarget :=
      runtimeWriteRegister_target runtime runtimeUpdated index runtimeReplacement hruntimeWrite
    rw [hnativeTarget] at hnativeAt
    rw [hruntimeTarget] at hruntimeAt
    cases hnativeAt
    cases hruntimeAt
    exact hreplacement
  · have hindexNative :=
      nativeWriteRegister_index_in_bounds native nativeUpdated index nativeReplacement hnativeWrite
    have hindexRuntime :=
      runtimeWriteRegister_index_in_bounds runtime runtimeUpdated index runtimeReplacement hruntimeWrite
    have hotherNative : other < native.length := by
      have hnewBound := List.isSome_get?_1 hnativeAt
      rw [nativeWriteRegister_length native nativeUpdated index nativeReplacement hnativeWrite] at hnewBound
      exact hnewBound
    have hotherRuntime : other < runtime.length := by
      have hnewBound := List.isSome_get?_1 hruntimeAt
      rw [runtimeWriteRegister_length runtime runtimeUpdated index runtimeReplacement hruntimeWrite] at hnewBound
      exact hnewBound
    have hnativeUnchanged :=
      nativeWriteRegister_other_unchanged native nativeUpdated index other
        nativeReplacement hnativeWrite hindexNative hotherNative htarget
    have hruntimeUnchanged :=
      runtimeWriteRegister_other_unchanged runtime runtimeUpdated index other
        runtimeReplacement hruntimeWrite htarget
    rw [hnativeUnchanged] at hnativeAt
    rw [hruntimeUnchanged] at hruntimeAt
    exact hrel.matches_at other nativeReg runtimeReg hnativeAt hruntimeAt


/-- End-to-end register-file preservation across the native list, abstract
runtime list, and finite typed register model.

Given paired successful native/runtime updates, the native/runtime relation is
preserved and RuntimeBridge's finite-register preservation theorem applies to
the same updated runtime list. This composes the concrete list update boundary
with the existing finite-register invariant; it does not yet establish that
the native and abstract dynamic type checks succeed together. -/
theorem nativeWriteRegister_preserves_finite_relation
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hnr : NativeRuntimeRegisterFileRelation native runtime)
    (hrf : RuntimeRegisterFileRelation types regs runtime)
    (index : Fin n)
    (nativeReplacement : NativeCCAMRegister)
    (runtimeReplacement : RuntimeRegister)
    (hreplacement : NativeRegisterMatches nativeReplacement runtimeReplacement)
    (hdecl : runtimeReplacement.declaredType = types index)
    (hinit : runtimeReplacement.initialized = true)
    {nativeUpdated : List NativeCCAMRegister}
    {runtimeUpdated : List RuntimeRegister}
    (hnativeWrite :
      nativeWriteRegister native index.val nativeReplacement = .ok nativeUpdated)
    (hruntimeWrite :
      runtimeWriteRegister runtime index.val runtimeReplacement = .ok runtimeUpdated) :
    NativeRuntimeRegisterFileRelation nativeUpdated runtimeUpdated ∧
    RuntimeRegisterFileRelation types
      (write regs index runtimeReplacement.asVal) runtimeUpdated := by
  exact ⟨
    nativeRuntimeRegisterFileRelation_write hnr index.val
      nativeReplacement runtimeReplacement hreplacement hnativeWrite hruntimeWrite,
    runtimeWriteRegister_preserves_relation hrf index runtimeReplacement
      hdecl hinit hruntimeWrite
  ⟩


/-- For corresponding native and runtime registers, the concrete tag check
accepts exactly when the abstract declared-type check accepts. -/
theorem nativeRegisterMatches_tag_eq_iff
    (native : NativeCCAMRegister) (runtime : RuntimeRegister)
    (nativeReplacement : NativeCCAMRegister)
    (runtimeReplacement : RuntimeRegister)
    (hmatch : NativeRegisterMatches native runtime)
    (hreplacement : NativeRegisterMatches nativeReplacement runtimeReplacement) :
    native.declaredTypeTag = nativeReplacement.declaredTypeTag ↔
      runtime.declaredType = runtimeReplacement.declaredType := by
  rcases hmatch with ⟨htag, _, _, _⟩
  rcases hreplacement with ⟨hreplacementTag, _, _, _⟩
  constructor
  · intro htags
    have hdecoded := congrArg decodeNativeTypeTag htags
    rw [htag, hreplacementTag] at hdecoded
    exact Option.some.inj hdecoded
  · intro htypes
    have hreplacementTag' :
        decodeNativeTypeTag nativeReplacement.declaredTypeTag =
          some runtime.declaredType := by
      rw [← htypes]
      exact hreplacementTag
    cases htype : runtime.declaredType with
    | int =>
        have hleft := (decodeNativeTypeTag_int_iff native.declaredTypeTag).mp
          (by simpa [htype] using htag)
        have hright :=
          (decodeNativeTypeTag_int_iff nativeReplacement.declaredTypeTag).mp
            (by simpa [htype] using hreplacementTag')
        exact hleft.trans hright.symm
    | bool =>
        have hleft := (decodeNativeTypeTag_bool_iff native.declaredTypeTag).mp
          (by simpa [htype] using htag)
        have hright :=
          (decodeNativeTypeTag_bool_iff nativeReplacement.declaredTypeTag).mp
            (by simpa [htype] using hreplacementTag')
        exact hleft.trans hright.symm

/-- Given witnesses for the same existing slot in related files, native and
abstract dynamic writes have identical success/failure acceptance decisions.
The separate preservation theorem supplies the relation between successful
outputs. -/
theorem nativeWriteRegister_accepts_iff_runtimeWriteRegister_accepts
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hrel : NativeRuntimeRegisterFileRelation native runtime)
    (index : Nat)
    (oldNative : NativeCCAMRegister) (oldRuntime : RuntimeRegister)
    (nativeReplacement : NativeCCAMRegister)
    (runtimeReplacement : RuntimeRegister)
    (hnativeSlot : native[index]? = some oldNative)
    (hruntimeSlot : runtime[index]? = some oldRuntime)
    (hreplacement : NativeRegisterMatches nativeReplacement runtimeReplacement) :
    (∃ updated, nativeWriteRegister native index nativeReplacement = .ok updated) ↔
      (∃ updated, runtimeWriteRegister runtime index runtimeReplacement = .ok updated) := by
  have hmatch := hrel.matches_at index oldNative oldRuntime hnativeSlot hruntimeSlot
  have htagEq := nativeRegisterMatches_tag_eq_iff oldNative oldRuntime
    nativeReplacement runtimeReplacement hmatch hreplacement
  constructor
  · rintro ⟨updated, hwrite⟩
    have hnativeType :
        oldNative.declaredTypeTag = nativeReplacement.declaredTypeTag := by
      by_cases htype :
          oldNative.declaredTypeTag = nativeReplacement.declaredTypeTag
      · exact htype
      · simp [nativeWriteRegister, hnativeSlot, htype] at hwrite
    have hruntimeType :
        oldRuntime.declaredType = runtimeReplacement.declaredType :=
      htagEq.mp hnativeType
    refine ⟨runtimeSetAt runtime index runtimeReplacement, ?_⟩
    simp [runtimeWriteRegister, runtimeRegisterAt, hruntimeSlot, hruntimeType]
  · rintro ⟨updated, hwrite⟩
    have hruntimeType :
        oldRuntime.declaredType = runtimeReplacement.declaredType := by
      by_cases htype :
          oldRuntime.declaredType = runtimeReplacement.declaredType
      · exact htype
      · simp [runtimeWriteRegister, runtimeRegisterAt, hruntimeSlot, htype] at hwrite
    have hnativeType :
        oldNative.declaredTypeTag = nativeReplacement.declaredTypeTag :=
      htagEq.mpr hruntimeType
    refine ⟨nativeRegisterSetAt native index nativeReplacement, ?_⟩
    simp [nativeWriteRegister, hnativeSlot, hnativeType]


/-- A successful native write has a corresponding successful abstract write,
and the resulting register files remain related. The slot witnesses make the
shared dynamic index premise explicit. -/
theorem nativeWriteRegister_success_refines_runtime
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hrel : NativeRuntimeRegisterFileRelation native runtime)
    (index : Nat)
    (oldNative : NativeCCAMRegister) (oldRuntime : RuntimeRegister)
    (nativeReplacement : NativeCCAMRegister)
    (runtimeReplacement : RuntimeRegister)
    (hnativeSlot : native[index]? = some oldNative)
    (hruntimeSlot : runtime[index]? = some oldRuntime)
    (hreplacement : NativeRegisterMatches nativeReplacement runtimeReplacement)
    {nativeUpdated : List NativeCCAMRegister}
    (hnativeWrite :
      nativeWriteRegister native index nativeReplacement = .ok nativeUpdated) :
    ∃ runtimeUpdated,
      runtimeWriteRegister runtime index runtimeReplacement = .ok runtimeUpdated ∧
      NativeRuntimeRegisterFileRelation nativeUpdated runtimeUpdated := by
  have haccepted :=
    (nativeWriteRegister_accepts_iff_runtimeWriteRegister_accepts
      hrel index oldNative oldRuntime nativeReplacement runtimeReplacement
      hnativeSlot hruntimeSlot hreplacement).mp
      ⟨nativeUpdated, hnativeWrite⟩
  rcases haccepted with ⟨runtimeUpdated, hruntimeWrite⟩
  exact ⟨runtimeUpdated, hruntimeWrite,
    nativeRuntimeRegisterFileRelation_write hrel index nativeReplacement
      runtimeReplacement hreplacement hnativeWrite hruntimeWrite⟩

/-- A successful native write refines the finite typed register update as well
as the abstract runtime-list update. This removes the previous requirement
that native and abstract writes be supplied as independently successful
premises: abstract success is derived from the native write and paired slot
witnesses. -/
theorem nativeWriteRegister_refines_finite_relation
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    {native : List NativeCCAMRegister} {runtime : List RuntimeRegister}
    (hnr : NativeRuntimeRegisterFileRelation native runtime)
    (hrf : RuntimeRegisterFileRelation types regs runtime)
    (index : Fin n)
    (oldNative : NativeCCAMRegister) (oldRuntime : RuntimeRegister)
    (hnativeSlot : native[index.val]? = some oldNative)
    (hruntimeSlot : runtime[index.val]? = some oldRuntime)
    (nativeReplacement : NativeCCAMRegister)
    (runtimeReplacement : RuntimeRegister)
    (hreplacement : NativeRegisterMatches nativeReplacement runtimeReplacement)
    (hdecl : runtimeReplacement.declaredType = types index)
    (hinit : runtimeReplacement.initialized = true)
    {nativeUpdated : List NativeCCAMRegister}
    (hnativeWrite :
      nativeWriteRegister native index.val nativeReplacement = .ok nativeUpdated) :
    ∃ runtimeUpdated,
      runtimeWriteRegister runtime index.val runtimeReplacement = .ok runtimeUpdated ∧
      NativeRuntimeRegisterFileRelation nativeUpdated runtimeUpdated ∧
      RuntimeRegisterFileRelation types
        (write regs index runtimeReplacement.asVal) runtimeUpdated := by
  obtain ⟨runtimeUpdated, hruntimeWrite, hnrUpdated⟩ :=
    nativeWriteRegister_success_refines_runtime hnr index.val
      oldNative oldRuntime nativeReplacement runtimeReplacement
      hnativeSlot hruntimeSlot hreplacement hnativeWrite
  exact ⟨runtimeUpdated, hruntimeWrite, hnrUpdated,
    runtimeWriteRegister_preserves_relation hrf index runtimeReplacement
      hdecl hinit hruntimeWrite⟩

end CapstanVerification
