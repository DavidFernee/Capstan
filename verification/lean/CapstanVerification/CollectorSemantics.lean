import CapstanVerification.ReferenceSemantics

namespace CapstanVerification

/-!
Abstract mark/sweep semantics for a heap of reference-bearing objects.

The model separates the marker from the sweep operation. A marker is
memory-safe when it is complete for the transitive closure of the root set:
it may conservatively retain garbage, but it must not miss a reachable object.
The proofs below establish the consequences of that condition. They do not
prove that the current C collector's stack/register/global scanning computes
a complete mark set.
-/

/-- An object exposes the identities of the objects referenced by its fields. -/
abbrev ObjectEdges (Object : Type) := Object → List ObjectId

/-- Transitive reachability from explicit roots through object fields. -/
inductive HeapReachable {Object : Type}
    (heap : ObjectHeap Object) (roots : List ObjectId)
    (edges : ObjectEdges Object) : ObjectId → Prop
  | root {objectId : ObjectId}
      (hroot : objectId ∈ roots)
      (hexists : heap objectId ≠ none) :
      HeapReachable heap roots edges objectId
  | child {parent objectId : ObjectId} {object : Object}
      (hparent : HeapReachable heap roots edges parent)
      (hparentObject : heap parent = some object)
      (hedge : objectId ∈ edges object)
      (hexists : heap objectId ≠ none) :
      HeapReachable heap roots edges objectId

/-- Marker completeness: every object reachable from a root is marked. False
positives are permitted, as in a conservative collector. -/
def HeapMarkerComplete {Object : Type}
    (heap : ObjectHeap Object) (roots : List ObjectId)
    (edges : ObjectEdges Object) (marked : ObjectId → Bool) : Prop :=
  ∀ objectId, HeapReachable heap roots edges objectId → marked objectId = true

/-- Sweep keeps marked objects and removes unmarked objects. -/
def gcSweep {Object : Type} (state : ReferenceHeapState Object)
    (marked : ObjectId → Bool) : ReferenceHeapState Object :=
  { state with
    heap := fun objectId =>
      if marked objectId then state.heap objectId else none }

/-- Every reachable object survives a sweep when the marker is complete. -/
theorem gcSweep_preserves_reachable
    {Object : Type} (state : ReferenceHeapState Object)
    (roots : List ObjectId) (edges : ObjectEdges Object)
    (marked : ObjectId → Bool)
    (hcomplete : HeapMarkerComplete state.heap roots edges marked)
    (objectId : ObjectId)
    (hlive : HeapReachable state.heap roots edges objectId) :
    (gcSweep state marked).heap objectId = state.heap objectId := by
  simp [gcSweep, hcomplete objectId hlive]

/-- Every existing root object survives a complete-mark sweep. -/
theorem gcSweep_preserves_roots
    {Object : Type} (state : ReferenceHeapState Object)
    (roots : List ObjectId) (edges : ObjectEdges Object)
    (marked : ObjectId → Bool)
    (hcomplete : HeapMarkerComplete state.heap roots edges marked)
    (objectId : ObjectId) (hroot : objectId ∈ roots)
    (object : Object) (hexists : state.heap objectId = some object) :
    (gcSweep state marked).heap objectId = some object := by
  have hlive : HeapReachable state.heap roots edges objectId :=
    HeapReachable.root hroot (by simp [hexists])
  rw [gcSweep_preserves_reachable state roots edges marked
    hcomplete objectId hlive]
  exact hexists

/-- A reachable object's outgoing edge to an existing object remains valid
after sweep. This is the no-dangling-edge property for the retained graph. -/
theorem gcSweep_preserves_reachable_edges
    {Object : Type} (state : ReferenceHeapState Object)
    (roots : List ObjectId) (edges : ObjectEdges Object)
    (marked : ObjectId → Bool)
    (hcomplete : HeapMarkerComplete state.heap roots edges marked)
    (parent child : ObjectId) (object childObject : Object)
    (hparentLive : HeapReachable state.heap roots edges parent)
    (hparent : state.heap parent = some object)
    (hedge : child ∈ edges object)
    (hchild : state.heap child = some childObject) :
    (gcSweep state marked).heap child = some childObject := by
  have hchildLive : HeapReachable state.heap roots edges child :=
    HeapReachable.child hparentLive hparent hedge (by simp [hchild])
  rw [gcSweep_preserves_reachable state roots edges marked
    hcomplete child hchildLive]
  exact hchild

/-- Sweep never invents an object that was absent before collection. -/
theorem gcSweep_no_new_objects
    {Object : Type} (state : ReferenceHeapState Object)
    (marked : ObjectId → Bool) (objectId : ObjectId) (object : Object)
    (hafter : (gcSweep state marked).heap objectId = some object) :
    state.heap objectId = some object := by
  by_cases hmarked : marked objectId = true
  · simpa [gcSweep, hmarked] using hafter
  · simp [gcSweep, hmarked] at hafter

/-- Collection preserves the monotone allocation-frontier invariant. It may
remove objects below the frontier, but never allocates or reuses identities. -/
theorem gcSweep_preserves_frontier
    {Object : Type} (state : ReferenceHeapState Object)
    (marked : ObjectId → Bool)
    (hstate : ReferenceHeapWellFormed state) :
    ReferenceHeapWellFormed (gcSweep state marked) := by
  intro objectId hfrontier
  simp [gcSweep, hstate objectId hfrontier]

/-- If a retained object points to an existing child, the child is retained too.
This packages reachability closure for clients proving object-graph invariants. -/
theorem gcSweep_retained_edge_target
    {Object : Type} (state : ReferenceHeapState Object)
    (roots : List ObjectId) (edges : ObjectEdges Object)
    (marked : ObjectId → Bool)
    (hcomplete : HeapMarkerComplete state.heap roots edges marked)
    (parent child : ObjectId) (object childObject : Object)
    (hparentLive : HeapReachable state.heap roots edges parent)
    (hparent : (gcSweep state marked).heap parent = some object)
    (hedge : child ∈ edges object)
    (hchild : state.heap child = some childObject) :
    (gcSweep state marked).heap child = some childObject := by
  have hparentBefore : state.heap parent = some object :=
    gcSweep_no_new_objects state marked parent object hparent
  exact gcSweep_preserves_reachable_edges state roots edges marked hcomplete
    parent child object childObject hparentLive hparentBefore hedge hchild


/-- A collection followed by allocation preserves every object that was
reachable before collection. The allocation frontier is preserved by sweep,
so the new object receives a fresh identity and cannot overwrite a survivor. -/
theorem gcSweep_then_allocate_preserves_reachable
    {Object : Type} (state : ReferenceHeapState Object)
    (roots : List ObjectId) (edges : ObjectEdges Object)
    (marked : ObjectId → Bool)
    (hcomplete : HeapMarkerComplete state.heap roots edges marked)
    (hstate : ReferenceHeapWellFormed state)
    (newObject : Object) (objectId : ObjectId)
    (hlive : HeapReachable state.heap roots edges objectId) :
    (referenceAllocate (gcSweep state marked) newObject).1.heap objectId =
      state.heap objectId := by
  have hafterSweep :
      (gcSweep state marked).heap objectId = state.heap objectId :=
    gcSweep_preserves_reachable state roots edges marked hcomplete objectId hlive
  have hnotFrontier : ¬ state.nextObjectId ≤ objectId := by
    intro hle
    have habsent := hstate objectId hle
    have hexists : state.heap objectId ≠ none := by
      cases hlive with
      | root _ hexists => exact hexists
      | child _ _ _ hexists => exact hexists
    exact hexists habsent
  have hbelow : objectId < state.nextObjectId :=
    Nat.lt_of_not_ge hnotFrontier
  have hdistinct : objectId ≠ state.nextObjectId := Nat.ne_of_lt hbelow
  rw [referenceAllocate_preserves_other_objects
    (gcSweep state marked) newObject objectId hdistinct]
  exact hafterSweep

/-- Collection followed by allocation preserves the well-formed frontier.
This rules out reusing an identity below the frontier, even when its old
object was reclaimed by the collection. -/
theorem gcSweep_then_allocate_preserves_frontier
    {Object : Type} (state : ReferenceHeapState Object)
    (marked : ObjectId → Bool) (newObject : Object)
    (hstate : ReferenceHeapWellFormed state) :
    ReferenceHeapWellFormed
      (referenceAllocate (gcSweep state marked) newObject).1 := by
  exact referenceAllocate_preserves_wellFormed
    (gcSweep state marked) newObject
    (gcSweep_preserves_frontier state marked hstate)


end CapstanVerification
