/-!
A small, standalone model of the bounded native object-handle lifecycle.

This file intentionally does not import the in-progress #255/#262 models.
It makes allocation, release, reuse, retirement and resolution one pure
transition system so the invariants can be checked independently before
integration with the larger formal library.
-/

namespace CapstanNativeMemory

universe u v

/-- A slot has exactly one lifecycle state; occupancy cannot be represented
by a separate Boolean that can disagree with a payload pointer. -/
inductive SlotState (Object : Type u) where
  | neverUsed
  | free (nextGeneration : Nat)
  | occupied (generation : Nat) (object : Object)
  | retired
deriving Repr

/-- An issued handle identifies one slot incarnation in one heap domain. -/
structure ObjectHandle (slotCount : Nat) where
  domain : Nat
  slot : Fin slotCount
  generation : Nat
deriving Repr

/-- The table is immutable at the model level. Every operation returns a new
table or an explicit rejection containing the original table. -/
abbrev SlotTable (slotCount : Nat) (Object : Type u) :=
  Fin slotCount → SlotState Object

inductive TransitionResult (State : Type u) (Output : Type v) where
  | rejected (unchanged : State)
  | accepted (next : State) (output : Output)
deriving Repr

/-- A successful allocation may use a never-used slot at generation zero,
or a free slot at its already-advanced generation. Occupied and retired
slots are never overwritten. -/
def allocateSlot {Object : Type u}
    (maximumGeneration : Nat) (slot : SlotState Object) (object : Object) :
    Option (SlotState Object × Nat) :=
  match slot with
  | .neverUsed => some (.occupied 0 object, 0)
  | .free generation =>
      if 0 < generation ∧ generation ≤ maximumGeneration then
        some (.occupied generation object, generation)
      else
        none
  | .occupied _ _ => none
  | .retired => none

/-- Release succeeds only for the currently occupied generation. A released
slot advances once; a slot at its final generation is retired permanently. -/
def releaseSlot {Object : Type u}
    (maximumGeneration : Nat) (slot : SlotState Object) (generation : Nat) :
    Option (SlotState Object) :=
  match slot with
  | .occupied current _ =>
      if current = generation then
        if current < maximumGeneration then
          some (.free (current + 1))
        else if current = maximumGeneration then
          some .retired
        else
          none
      else
        none
  | _ => none

/-- Resolution accepts only an occupied slot with exact generation equality. -/
def resolveSlot {Object : Type u}
    (generation : Nat) (slot : SlotState Object) : Option Object :=
  match slot with
  | .occupied current object =>
      if current = generation then some object else none
  | _ => none

/-- Replace exactly one slot. The functional table representation makes
unrelated slots definitionally unchanged. -/
def updateSlot {slotCount : Nat} {Object : Type u}
    (table : SlotTable slotCount Object) (slot : Fin slotCount)
    (replacement : SlotState Object) : SlotTable slotCount Object :=
  fun candidate => if candidate = slot then replacement else table candidate

/-- Resolve a handle only in its owning domain. -/
def resolveHandle {slotCount : Nat} {Object : Type u}
    (table : SlotTable slotCount Object) (expectedDomain : Nat)
    (handle : ObjectHandle slotCount) : Option Object :=
  if handle.domain = expectedDomain then
    resolveSlot handle.generation (table handle.slot)
  else
    none

/-- Atomic table allocation. Rejection returns the exact input table. -/
def allocateAt {slotCount : Nat} {Object : Type u}
    (maximumGeneration domain : Nat)
    (table : SlotTable slotCount Object) (slot : Fin slotCount)
    (object : Object) :
    TransitionResult (SlotTable slotCount Object) (ObjectHandle slotCount) :=
  match allocateSlot maximumGeneration (table slot) object with
  | none => .rejected table
  | some (replacement, generation) =>
      .accepted (updateSlot table slot replacement)
        { domain := domain, slot := slot, generation := generation }

/-- Atomic table release. Wrong-domain, stale, unoccupied and retired-slot
releases are rejected without changing the input table. -/
def releaseAt {slotCount : Nat} {Object : Type u}
    (maximumGeneration expectedDomain : Nat)
    (table : SlotTable slotCount Object)
    (handle : ObjectHandle slotCount) :
    TransitionResult (SlotTable slotCount Object) Unit :=
  if handle.domain = expectedDomain then
    match releaseSlot maximumGeneration (table handle.slot) handle.generation with
    | none => .rejected table
    | some replacement =>
        .accepted (updateSlot table handle.slot replacement) ()
  else
    .rejected table

/-- A successful allocation always produces a handle that resolves to the
newly published object. -/
theorem allocateSlot_success_resolves
    {Object : Type u} (maximumGeneration : Nat)
    (slot : SlotState Object) (object : Object)
    (next : SlotState Object) (generation : Nat)
    (h : allocateSlot maximumGeneration slot object = some (next, generation)) :
    resolveSlot generation next = some object := by
  cases slot with
  | neverUsed =>
      simp [allocateSlot] at h
      rcases h with ⟨hnext, hgeneration⟩
      subst next
      subst generation
      simp [resolveSlot]
  | free current =>
      by_cases hpositive : 0 < current
      · by_cases hbound : current ≤ maximumGeneration
        · simp [allocateSlot, hpositive, hbound] at h
          rcases h with ⟨hnext, hgeneration⟩
          subst next
          subst generation
          simp [resolveSlot]
        · simp [allocateSlot, hpositive, hbound] at h
      · simp [allocateSlot, hpositive] at h
  | occupied current previous =>
      simp [allocateSlot] at h
  | retired =>
      simp [allocateSlot] at h

/-- A malformed free slot at generation zero or above the configured
maximum is rejected rather than issuing an out-of-policy handle. -/
theorem allocateSlot_rejects_invalid_free_generation
    {Object : Type u} (maximumGeneration generation : Nat) (object : Object)
    (hzero : generation = 0 ∨ maximumGeneration < generation) :
    allocateSlot maximumGeneration (.free generation) object = none := by
  rcases hzero with hzero | habove
  · simp [allocateSlot, hzero]
  · have hbound : ¬ generation ≤ maximumGeneration := Nat.not_le_of_gt habove
    simp [allocateSlot, hbound]

/-- Occupied slots cannot be overwritten by allocation. -/
theorem allocateSlot_rejects_occupied
    {Object : Type u} (maximumGeneration generation : Nat)
    (old replacement : Object) :
    allocateSlot maximumGeneration (.occupied generation old) replacement = none := rfl

/-- Retired slots can never be allocated again. -/
theorem allocateSlot_rejects_retired
    {Object : Type u} (maximumGeneration : Nat) (object : Object) :
    allocateSlot maximumGeneration .retired object = none := rfl

/-- A stale generation cannot release the current occupant. -/
theorem releaseSlot_rejects_stale
    {Object : Type u} (maximumGeneration current stale : Nat)
    (object : Object) (h : current ≠ stale) :
    releaseSlot maximumGeneration (.occupied current object) stale = none := by
  simp [releaseSlot, h]

/-- Releasing an object at the maximum generation retires the slot; there is
no arithmetic wrap or generation reset. -/
theorem releaseSlot_retires_at_maximum
    {Object : Type u} (maximumGeneration : Nat) (object : Object) :
    releaseSlot maximumGeneration
      (.occupied maximumGeneration object) maximumGeneration = some .retired := by
  simp [releaseSlot]

/-- A free slot's next generation is strictly greater than the released one. -/
theorem releaseSlot_advances_generation
    {Object : Type u} (maximumGeneration current : Nat)
    (object : Object) (h : current < maximumGeneration) :
    releaseSlot maximumGeneration (.occupied current object) current =
      some (.free (current + 1)) := by
  simp [releaseSlot, h]

/-- A released slot cannot resolve the just-released generation. -/
theorem resolveSlot_rejects_free_generation
    {Object : Type u} (generation : Nat) :
    resolveSlot generation (.free (generation + 1) : SlotState Object) = none := rfl

/-- Cross-domain handles are rejected independently of slot/generation. -/
theorem resolveHandle_rejects_cross_domain
    {slotCount : Nat} {Object : Type u}
    (table : SlotTable slotCount Object) (expectedDomain : Nat)
    (handle : ObjectHandle slotCount)
    (h : handle.domain ≠ expectedDomain) :
    resolveHandle table expectedDomain handle = none := by
  simp [resolveHandle, h]

/-- Every rejected allocation returns the original table, not a partially
updated table or an advanced generation. -/
theorem allocateAt_rejection_is_atomic
    {slotCount : Nat} {Object : Type u}
    (maximumGeneration domain : Nat)
    (table : SlotTable slotCount Object) (slot : Fin slotCount)
    (object : Object) (after : SlotTable slotCount Object)
    (h : allocateAt maximumGeneration domain table slot object =
      .rejected after) :
    after = table := by
  unfold allocateAt at h
  cases hslot : allocateSlot maximumGeneration (table slot) object with
  | none =>
      simp [hslot] at h
      cases h
      rfl
  | some result =>
      simp [hslot] at h

/-- Every rejected release returns the original table. -/
theorem releaseAt_rejection_is_atomic
    {slotCount : Nat} {Object : Type u}
    (maximumGeneration expectedDomain : Nat)
    (table : SlotTable slotCount Object) (handle : ObjectHandle slotCount)
    (after : SlotTable slotCount Object)
    (h : releaseAt maximumGeneration expectedDomain table handle =
      .rejected after) :
    after = table := by
  unfold releaseAt at h
  by_cases hdomain : handle.domain = expectedDomain
  · simp [hdomain] at h
    cases hslot : releaseSlot maximumGeneration
      (table handle.slot) handle.generation with
    | none =>
        simp [hslot] at h
        cases h
        rfl
    | some replacement =>
        simp [hslot] at h
  · simp [hdomain] at h
    cases h
    rfl

/-- Updating one slot cannot alter any distinct slot. -/
theorem updateSlot_preserves_other
    {slotCount : Nat} {Object : Type u}
    (table : SlotTable slotCount Object) (slot other : Fin slotCount)
    (replacement : SlotState Object) (h : other ≠ slot) :
    updateSlot table slot replacement other = table other := by
  simp [updateSlot, h]

/-- Reusing a released slot advances the incarnation, so the old handle
cannot resolve to the replacement object. This composes release, allocation
and resolution rather than proving the steps only in isolation. -/
theorem reuse_rejects_previous_incarnation
    {Object : Type u} (maximumGeneration current : Nat)
    (old replacement : Object)
    (hadvance : current < maximumGeneration)
    (hbound : current + 1 ≤ maximumGeneration) :
    let released :=
      releaseSlot maximumGeneration (.occupied current old) current
    let reallocated :=
      allocateSlot maximumGeneration (.free (current + 1)) replacement
    released = some (.free (current + 1)) ∧
      reallocated = some (.occupied (current + 1) replacement, current + 1) ∧
      resolveSlot current (.occupied (current + 1) replacement) = none := by
  constructor
  · simp [releaseSlot, hadvance]
  constructor
  · simp [allocateSlot, hbound]
  · simp [resolveSlot]


end CapstanNativeMemory


#print axioms CapstanNativeMemory.allocateSlot_success_resolves
#print axioms CapstanNativeMemory.allocateSlot_rejects_invalid_free_generation
#print axioms CapstanNativeMemory.allocateSlot_rejects_occupied
#print axioms CapstanNativeMemory.allocateSlot_rejects_retired
#print axioms CapstanNativeMemory.releaseSlot_rejects_stale
#print axioms CapstanNativeMemory.releaseSlot_retires_at_maximum
#print axioms CapstanNativeMemory.releaseSlot_advances_generation
#print axioms CapstanNativeMemory.resolveSlot_rejects_free_generation
#print axioms CapstanNativeMemory.resolveHandle_rejects_cross_domain
#print axioms CapstanNativeMemory.allocateAt_rejection_is_atomic
#print axioms CapstanNativeMemory.releaseAt_rejection_is_atomic
#print axioms CapstanNativeMemory.updateSlot_preserves_other
#print axioms CapstanNativeMemory.reuse_rejects_previous_incarnation
