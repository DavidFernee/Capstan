import CapstanVerification.NativeRegisterFileBridge
import CapstanVerification.ReferenceSemantics

namespace CapstanVerification

/-!
A first explicit heap model for the reference semantics used by CCAM registers.

A register file contains object identities; the heap maps identities to mutable
register records. This separates slot identity from object state. The model
makes the no-alias condition explicit and proves that mutating the object
referenced by one slot has the same observable effect as the mathematical
register-list replacement, provided distinct slots do not share an identity.

This is a semantic model and refinement lemma, not yet a proof that the
executable allocator or field-assignment implementation realizes it.
-/

/-- Heap object identities are natural numbers. -/
abbrev NativeRegisterObjectId := Nat

/-- A finite heap represented as a total map with absent objects mapped to none. -/
abbrev NativeRegisterHeap := NativeRegisterObjectId → Option NativeCCAMRegister

/-- Mutate one heap object in place, preserving all other object identities. -/
def nativeRegisterHeapWrite
    (heap : NativeRegisterHeap) (objectId : NativeRegisterObjectId)
    (replacement : NativeCCAMRegister) : NativeRegisterHeap :=
  fun candidate => if candidate = objectId then some replacement else heap candidate

/-- View a CCAM register heap as an instance of the generic language heap. -/
def nativeRegisterHeapState
    (nextObjectId : NativeRegisterObjectId)
    (heap : NativeRegisterHeap) : NativeRegisterHeapState :=
  { nextObjectId := nextObjectId, heap := heap }

/-- The CCAM heap-update operation is exactly the generic reference write
when the referenced object exists. -/
theorem nativeRegisterHeapWrite_is_referenceWrite
    (nextObjectId : NativeRegisterObjectId)
    (heap : NativeRegisterHeap) (objectId : NativeRegisterObjectId)
    (old replacement : NativeCCAMRegister)
    (hobject : heap objectId = some old) :
    referenceWrite (nativeRegisterHeapState nextObjectId heap)
      objectId replacement =
    some (nativeRegisterHeapState nextObjectId
      (nativeRegisterHeapWrite heap objectId replacement)) := by
  simp [referenceWrite, nativeRegisterHeapState, nativeRegisterHeapWrite, hobject]
  rfl
@[simp] theorem nativeRegisterHeapWrite_target
    (heap : NativeRegisterHeap) (objectId : NativeRegisterObjectId)
    (replacement : NativeCCAMRegister) :
    nativeRegisterHeapWrite heap objectId replacement objectId = some replacement := by
  simp [nativeRegisterHeapWrite]

@[simp] theorem nativeRegisterHeapWrite_other
    (heap : NativeRegisterHeap) (objectId other : NativeRegisterObjectId)
    (replacement : NativeCCAMRegister) (hdistinct : other ≠ objectId) :
    nativeRegisterHeapWrite heap objectId replacement other = heap other := by
  simp [nativeRegisterHeapWrite, hdistinct]

/-- Register-slot references are injective: no two distinct slots alias. -/
def NativeRegisterReferencesNoAlias (references : List NativeRegisterObjectId) : Prop :=
  ∀ (left right : Nat) (objectId : NativeRegisterObjectId),
    references[left]? = some objectId →
    references[right]? = some objectId →
    left = right

/-- The reference vector and heap describe the same register state as a
mathematical list of native register records. -/
def NativeHeapRegisterFileRelation
    (references : List NativeRegisterObjectId)
    (heap : NativeRegisterHeap)
    (registers : List NativeCCAMRegister) : Prop :=
  references.length = registers.length ∧
  (∀ (index : Nat) (objectId : NativeRegisterObjectId),
    references[index]? = some objectId →
    ∃ register, heap objectId = some register) ∧
  (∀ (index : Nat) (objectId : NativeRegisterObjectId)
    (register : NativeCCAMRegister),
    references[index]? = some objectId →
    heap objectId = some register →
    registers[index]? = some register)

/-- In-place mutation of one referenced object refines list-slot replacement
when the reference vector is alias-free. -/
theorem nativeRegisterHeapWrite_refines_setAt
    {references : List NativeRegisterObjectId}
    {heap : NativeRegisterHeap}
    {registers : List NativeCCAMRegister}
    (hnoalias : NativeRegisterReferencesNoAlias references)
    (hrel : NativeHeapRegisterFileRelation references heap registers)
    (index : Nat) (objectId : NativeRegisterObjectId)
    (old replacement : NativeCCAMRegister)
    (href : references[index]? = some objectId)
    (hold : heap objectId = some old) :
    NativeHeapRegisterFileRelation references
      (nativeRegisterHeapWrite heap objectId replacement)
      (nativeRegisterSetAt registers index replacement) := by
  unfold NativeHeapRegisterFileRelation
  constructor
  · rw [nativeRegisterSetAt_length]
    exact hrel.1
  · constructor
    · intro other otherId hotherRef
      by_cases hsame : other = index
      · subst other
        have hsameId : otherId = objectId :=
          Option.some.inj (hotherRef.symm.trans href)
        subst otherId
        exact ⟨replacement, by simp [nativeRegisterHeapWrite]⟩
      · have hotherIdNe : otherId ≠ objectId := by
          intro heq
          subst otherId
          exact hsame (hnoalias other index objectId hotherRef href)
        obtain ⟨otherRegister, hotherLive⟩ := hrel.2.1 other otherId hotherRef
        exact ⟨otherRegister, by
          simpa [nativeRegisterHeapWrite, hotherIdNe] using hotherLive⟩
    · intro other otherId otherRegister hotherRef hotherHeap
      by_cases hsame : other = index
      · subst other
        have hsameId : otherId = objectId :=
          Option.some.inj (hotherRef.symm.trans href)
        subst otherId
        simp only [nativeRegisterHeapWrite_target] at hotherHeap
        have hreplacement : otherRegister = replacement :=
          (Option.some.inj hotherHeap).symm
        subst otherRegister
        have hslot := hrel.2.2 index objectId old href hold
        have hbound : index < registers.length :=
          list_get?_some_implies_lt registers index old hslot
        exact nativeRegisterSetAt_get_same registers index replacement hbound
      · have hotherIdNe : otherId ≠ objectId := by
          intro heq
          subst otherId
          exact hsame (hnoalias other index objectId hotherRef href)
        have holdOther := hrel.2.2 other otherId otherRegister hotherRef
          (by simpa [nativeRegisterHeapWrite_other heap objectId otherId replacement hotherIdNe] using hotherHeap)
        have hslot := hrel.2.2 index objectId old href hold
        have hindexBound : index < registers.length :=
          list_get?_some_implies_lt registers index old hslot
        have hotherBound : other < registers.length :=
          list_get?_some_implies_lt registers other otherRegister holdOther
        have hunchanged := nativeRegisterSetAt_get_other registers index other
          replacement hindexBound hotherBound hsame
        rw [hunchanged]
        exact holdOther

/-- A canonical initial reference vector assigns one distinct identity per
register slot. -/
def nativeRegisterInitialReferences (count : Nat) : List NativeRegisterObjectId :=
  List.range count

theorem nativeRegisterInitialReferences_noAlias (count : Nat) :
    NativeRegisterReferencesNoAlias (nativeRegisterInitialReferences count) := by
  unfold NativeRegisterReferencesNoAlias
  intro left right objectId hleft hright
  have hleftBound : left < count := by
    have h := (List.getElem?_eq_some_iff).mp hleft
    simpa [nativeRegisterInitialReferences] using h.1
  have hrightBound : right < count := by
    have h := (List.getElem?_eq_some_iff).mp hright
    simpa [nativeRegisterInitialReferences] using h.1
  have hleft' : (List.range count)[left]? = some objectId := by
    simpa [nativeRegisterInitialReferences] using hleft
  have hright' : (List.range count)[right]? = some objectId := by
    simpa [nativeRegisterInitialReferences] using hright
  rw [List.getElem?_range hleftBound] at hleft'
  rw [List.getElem?_range hrightBound] at hright'
  have hleftValue : left = objectId := Option.some.inj hleft'
  have hrightValue : right = objectId := Option.some.inj hright'
  exact hleftValue.trans hrightValue.symm

/-- The canonical allocator's next identity is outside its initial vector. -/
theorem nativeRegisterInitialReferences_fresh (count : Nat) :
    (nativeRegisterInitialReferences count)[count]? = none := by
  simp [nativeRegisterInitialReferences]

/-- The canonical initial register records, one per declared type tag. -/
def nativeRegisterInitialFile (typeTags : List Int) : List NativeCCAMRegister :=
  typeTags.map nativeRegisterInit

/-- The canonical initial heap places each initial record at its slot identity. -/
def nativeRegisterInitialHeap (typeTags : List Int) : NativeRegisterHeap :=
  fun objectId => (nativeRegisterInitialFile typeTags)[objectId]?

/-- The canonical constructor model establishes the heap/register-file
correspondence: each slot refers to its own heap object, and that object holds
the record at the same mathematical list position. -/
theorem nativeRegisterInitialHeap_matches_file (typeTags : List Int) :
    NativeHeapRegisterFileRelation
      (nativeRegisterInitialReferences typeTags.length)
      (nativeRegisterInitialHeap typeTags)
      (nativeRegisterInitialFile typeTags) := by
  unfold NativeHeapRegisterFileRelation
  constructor
  · simp [nativeRegisterInitialReferences, nativeRegisterInitialFile]
  · constructor
    · intro index objectId href
      have href' : (List.range typeTags.length)[index]? = some objectId := by
        simpa [nativeRegisterInitialReferences] using href
      have hindex : index < typeTags.length := by
        have h := (List.getElem?_eq_some_iff).mp href'
        simpa using h.1
      have hobject : objectId = index := by
        rw [List.getElem?_range hindex] at href'
        exact (Option.some.inj href').symm
      subst objectId
      have hslot : ∃ register, (nativeRegisterInitialFile typeTags)[index]? = some register := by
        let tag := typeTags[index]'hindex
        refine ⟨nativeRegisterInit tag, ?_⟩
        simp [nativeRegisterInitialFile, tag, hindex]
      obtain ⟨register, hregister⟩ := hslot
      exact ⟨register, by simpa [nativeRegisterInitialHeap] using hregister⟩
    · intro index objectId register href hheap
      have href' : (List.range typeTags.length)[index]? = some objectId := by
        simpa [nativeRegisterInitialReferences] using href
      have hindex : index < typeTags.length := by
        have h := (List.getElem?_eq_some_iff).mp href'
        simpa using h.1
      have hobject : objectId = index := by
        rw [List.getElem?_range hindex] at href'
        exact (Option.some.inj href').symm
      subst objectId
      exact hheap

/-- A reference vector cannot satisfy the relation when one of its target
objects is absent. This rules out the vacuous empty-heap model. -/
theorem nativeHeapRegisterFileRelation_rejects_missing_object
    (register : NativeCCAMRegister) :
    ¬ NativeHeapRegisterFileRelation [0]
      (fun _ => none) [register] := by
  intro hrel
  unfold NativeHeapRegisterFileRelation at hrel
  obtain ⟨present, hpresent⟩ := hrel.2.1 0 0 (by simp)
  simp at hpresent

/-- Initial register heaps are immediately safe for the list-update refinement:
the constructor supplies both the no-alias invariant and the heap/file relation. -/
theorem nativeRegisterInitialHeap_write_refines_setAt
    (typeTags : List Int) (index : Nat) (old replacement : NativeCCAMRegister)
    (hbound : index < typeTags.length)
    (hslot : (nativeRegisterInitialFile typeTags)[index]? = some old) :
    NativeHeapRegisterFileRelation
      (nativeRegisterInitialReferences typeTags.length)
      (nativeRegisterHeapWrite (nativeRegisterInitialHeap typeTags)
        index replacement)
      (nativeRegisterSetAt (nativeRegisterInitialFile typeTags) index replacement) := by
  have hnoalias :=
    nativeRegisterInitialReferences_noAlias typeTags.length
  have hrel := nativeRegisterInitialHeap_matches_file typeTags
  have href : (nativeRegisterInitialReferences typeTags.length)[index]? = some index := by
    simp [nativeRegisterInitialReferences, hbound]
  have hheap : (nativeRegisterInitialHeap typeTags) index = some old := by
    simpa [nativeRegisterInitialHeap] using hslot
  exact nativeRegisterHeapWrite_refines_setAt hnoalias hrel index index
    old replacement href hheap

/-- The no-alias invariant is a property of the reference vector alone;
changing heap contents cannot change it. -/
theorem nativeRegisterReferencesNoAlias_independent_of_heap
    (references : List NativeRegisterObjectId)
    (hnoalias : NativeRegisterReferencesNoAlias references) :
    NativeRegisterReferencesNoAlias references := hnoalias

/-- Reading a slot through its heap reference agrees with the mathematical
register-file lookup whenever the heap/file relation holds. -/
theorem nativeRegisterHeapRead_matches_list_get
    {references : List NativeRegisterObjectId}
    {heap : NativeRegisterHeap}
    {registers : List NativeCCAMRegister}
    (hrel : NativeHeapRegisterFileRelation references heap registers)
    (index : Nat) (objectId : NativeRegisterObjectId)
    (register : NativeCCAMRegister)
    (href : references[index]? = some objectId)
    (hheap : heap objectId = some register) :
    registers[index]? = some register := by
  unfold NativeHeapRegisterFileRelation at hrel
  exact hrel.2.2 index objectId register href hheap


end CapstanVerification
