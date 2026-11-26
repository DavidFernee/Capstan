import CapstanVerification.NativeRegisterBridge

namespace CapstanVerification

/-!
A language-level reference-semantics model, separate from the CCAM
register-file refinement.

A reference is an opaque object identity. Copying a reference copies that
identity, not the object. The heap is the authoritative mutable object store.
Allocation uses a monotone next-object identity and requires the well-formedness
invariant that no identity at or above the frontier is already allocated.

The model is polymorphic in object payload, so the same identity/allocation
laws apply to ordinary structs, collection objects, and CCAM register objects.
It remains a mathematical semantics, not a compiler/runtime correctness proof.
-/

abbrev ObjectId := Nat
abbrev ObjectHeap (Object : Type) := ObjectId → Option Object

structure ReferenceHeapState (Object : Type) where
  nextObjectId : ObjectId
  heap : ObjectHeap Object

def ReferenceHeapWellFormed {Object : Type}
    (state : ReferenceHeapState Object) : Prop :=
  ∀ objectId, state.nextObjectId ≤ objectId → state.heap objectId = none

/-- A reference copy preserves identity; it does not clone its referent. -/
def copyReference (reference : ObjectId) : ObjectId := reference

@[simp] theorem copyReference_identity (reference : ObjectId) :
    copyReference reference = reference := rfl

/-- Allocate at the current frontier and advance it monotonically. -/
def referenceAllocate {Object : Type}
    (state : ReferenceHeapState Object) (object : Object) :
    ReferenceHeapState Object × ObjectId :=
  let objectId := state.nextObjectId
  ( { nextObjectId := objectId + 1
      heap := fun candidate =>
        if candidate = objectId then some object else state.heap candidate },
    objectId )

@[simp] theorem referenceAllocate_returns_frontier
    {Object : Type} (state : ReferenceHeapState Object) (object : Object) :
    (referenceAllocate state object).2 = state.nextObjectId := rfl

@[simp] theorem referenceAllocate_stores_object
    {Object : Type} (state : ReferenceHeapState Object) (object : Object) :
    (referenceAllocate state object).1.heap state.nextObjectId = some object := by
  simp [referenceAllocate]

theorem referenceAllocate_preserves_other_objects
    {Object : Type} (state : ReferenceHeapState Object) (object : Object)
    (other : ObjectId) (hne : other ≠ state.nextObjectId) :
    (referenceAllocate state object).1.heap other = state.heap other := by
  simp [referenceAllocate, hne]

theorem referenceAllocate_preserves_wellFormed
    {Object : Type} (state : ReferenceHeapState Object) (object : Object)
    (hstate : ReferenceHeapWellFormed state) :
    ReferenceHeapWellFormed (referenceAllocate state object).1 := by
  intro objectId hfrontier
  change state.nextObjectId + 1 ≤ objectId at hfrontier
  have hlt : state.nextObjectId < objectId :=
    Nat.lt_of_succ_le hfrontier
  have hne : objectId ≠ state.nextObjectId := Nat.ne_of_gt hlt
  rw [referenceAllocate_preserves_other_objects state object objectId hne]
  exact hstate objectId (Nat.le_of_lt hlt)

/-- A well-formed allocator frontier is fresh relative to the existing heap. -/
theorem referenceAllocate_uses_fresh_identity
    {Object : Type} (state : ReferenceHeapState Object) (object : Object)
    (hstate : ReferenceHeapWellFormed state) :
    state.heap (referenceAllocate state object).2 = none :=
  hstate state.nextObjectId (by simp [referenceAllocate])

/-- Allocation cannot reuse the identity of any currently allocated
object. This follows from the frontier invariant, not from object payload
inequality. -/
theorem referenceAllocate_does_not_reuse_live_identity
    {Object : Type} (state : ReferenceHeapState Object)
    (object : Object) (old : ObjectId) (previous : Object)
    (hstate : ReferenceHeapWellFormed state)
    (hlive : state.heap old = some previous) :
    (referenceAllocate state object).2 ≠ old := by
  intro heq
  change state.nextObjectId = old at heq
  subst old
  have hfresh : state.heap state.nextObjectId = none :=
    hstate state.nextObjectId (Nat.le_refl _)
  rw [hlive] at hfresh
  cases hfresh

/-- Dereference an identity. An absent identity is an invalid reference. -/
def referenceRead {Object : Type} (state : ReferenceHeapState Object)
    (reference : ObjectId) : Option Object :=
  state.heap reference

/-- Mutate the object reached through a reference, leaving other heap cells
unchanged. This is the semantic primitive for mutable field assignment. -/
def referenceWrite {Object : Type} (state : ReferenceHeapState Object)
    (reference : ObjectId) (updated : Object) :
    Option (ReferenceHeapState Object) :=
  match state.heap reference with
  | none => none
  | some _ =>
      some { state with
        heap := fun candidate =>
          if candidate = reference then some updated else state.heap candidate }

/-- A successful reference write is observable through the written reference. -/
theorem referenceWrite_readback
    {Object : Type} (state : ReferenceHeapState Object) (reference : ObjectId)
    (old updated : Object)
    (hread : referenceRead state reference = some old) :
    ∃ next,
      referenceWrite state reference updated = some next ∧
      referenceRead next reference = some updated := by
  cases h : state.heap reference with
  | none => simp [referenceRead, h] at hread
  | some previous =>
      refine ⟨{ state with
        heap := fun candidate =>
          if candidate = reference then some updated else state.heap candidate }, ?_, ?_⟩
      · simp [referenceWrite, h]
      · simp [referenceRead]

/-- Two aliases to the same object identity observe the same heap object. -/
theorem copiedReferences_alias
    {Object : Type} (state : ReferenceHeapState Object) (reference : ObjectId) :
    referenceRead state (copyReference reference) =
      referenceRead state reference := rfl

/-- Mutation through one reference is visible through a copied alias. -/
theorem referenceWrite_visible_through_alias
    {Object : Type} (state : ReferenceHeapState Object)
    (reference alias : ObjectId) (old updated : Object)
    (hread : referenceRead state reference = some old)
    (halias : copyReference reference = alias) :
    ∃ next,
      referenceWrite state reference updated = some next ∧
      referenceRead next alias = some updated := by
  obtain ⟨next, hwrite, hvisible⟩ :=
    referenceWrite_readback state reference old updated hread
  refine ⟨next, hwrite, ?_⟩
  rw [← halias]
  simpa [copyReference] using hvisible

/-- Apply an object-field update through a reference. The update function
receives the current object payload and returns the replacement payload. -/
def referenceModify {Object : Type} (state : ReferenceHeapState Object)
    (reference : ObjectId) (modify : Object → Object) :
    Option (ReferenceHeapState Object) :=
  match referenceRead state reference with
  | none => none
  | some old => referenceWrite state reference (modify old)

/-- A field update through one reference is visible through every copied
alias to the same object. -/
theorem referenceModify_visible_through_alias
    {Object : Type} (state : ReferenceHeapState Object)
    (reference alias : ObjectId) (old : Object)
    (modify : Object → Object)
    (hread : referenceRead state reference = some old)
    (halias : copyReference reference = alias) :
    ∃ next,
      referenceModify state reference modify = some next ∧
      referenceRead next alias = some (modify old) := by
  unfold referenceModify
  rw [hread]
  exact referenceWrite_visible_through_alias state reference alias
    old (modify old) hread halias

/-- The concrete CCAM integer-field update is visible through a copied
reference alias, using the same field-update function as NativeRegisterBridge. -/
theorem nativeRegisterFieldWrite_visible_through_alias
    (state : ReferenceHeapState NativeCCAMRegister) (reference alias : ObjectId)
    (old : NativeCCAMRegister) (value : Int) (hvalue : inI64 value)
    (hread : referenceRead state reference = some old)
    (halias : copyReference reference = alias) :
    ∃ next,
      referenceModify state reference
        (fun reg => nativeRegisterWriteInt reg value hvalue) = some next ∧
      referenceRead next alias =
        some (nativeRegisterWriteInt old value hvalue) :=
  referenceModify_visible_through_alias state reference alias old
    (fun reg => nativeRegisterWriteInt reg value hvalue) hread halias

/-- A successful write cannot alter a different object identity. -/
theorem referenceWrite_other_identity
    {Object : Type} (state : ReferenceHeapState Object)
    (reference other : ObjectId) (old updated : Object)
    (hread : referenceRead state reference = some old)
    (hne : other ≠ reference) :
    ∃ next,
      referenceWrite state reference updated = some next ∧
      next.heap other = state.heap other := by
  cases h : state.heap reference with
  | none => simp [referenceRead, h] at hread
  | some previous =>
      refine ⟨{ state with
        heap := fun candidate =>
          if candidate = reference then some updated else state.heap candidate }, ?_, ?_⟩
      · simp [referenceWrite, h]
      · simp [hne]

/-- Specialise the generic heap semantics to the concrete CCAM register record. -/
abbrev NativeRegisterHeapState := ReferenceHeapState NativeCCAMRegister

end CapstanVerification
