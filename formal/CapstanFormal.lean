/-
  Capstan allocator/GC formal model.

  This module is intentionally a model of target transition semantics. It does not
  yet prove that runtime/capstan_gc.h refines these definitions.
-/

namespace CapstanFormal

/-- Explicit result of checked arithmetic: success returns a value; overflow is fatal. -/
inductive CheckedAddResult where
  | success (value : Nat)
  | fatal
  deriving DecidableEq, Repr

/-- Mathematical model of the C checked-add helper.
    The limit represents SIZE_MAX; inputs are natural-number encodings of size_t values. -/
def checkedAdd (limit a b : Nat) : CheckedAddResult :=
  if a ≤ limit ∧ b ≤ limit - a then .success (a + b) else .fatal

/-- A successful checked addition returns the exact mathematical sum, within limit. -/
theorem checkedAdd_sound (limit a b result : Nat)
    (h : checkedAdd limit a b = .success result) :
    result = a + b ∧ a + b ≤ limit := by
  unfold checkedAdd at h
  by_cases hfit : a ≤ limit ∧ b ≤ limit - a
  · simp [hfit] at h
    constructor <;> omega
  · simp [hfit] at h

/-- Every in-range mathematical sum is accepted by the checked-add model. -/
theorem checkedAdd_complete (limit a b : Nat)
    (h : a + b ≤ limit) :
    checkedAdd limit a b = .success (a + b) := by
  unfold checkedAdd
  have hfit : a ≤ limit ∧ b ≤ limit - a := by omega
  simp [hfit]

/-- The checked-add model accepts exactly the sums representable below limit. -/
theorem checkedAdd_exact (limit a b : Nat) :
    (∃ result, checkedAdd limit a b = .success result) ↔ a + b ≤ limit := by
  constructor
  · rintro ⟨result, h⟩
    exact (checkedAdd_sound limit a b result h).2
  · intro h
    exact ⟨a + b, checkedAdd_complete limit a b h⟩

/-- Overflow takes the terminal fatal outcome; it is not a recoverable return. -/
theorem checkedAdd_overflow_fatal (limit a b : Nat)
    (h : limit < a + b) :
    checkedAdd limit a b = .fatal := by
  unfold checkedAdd
  have hfit : ¬ (a ≤ limit ∧ b ≤ limit - a) := by omega
  simp [hfit]


/-- Mathematical checked multiplication contract. The product is accepted exactly
    when it is representable at or below the supplied size limit. -/
def checkedMul (limit a b : Nat) : CheckedAddResult :=
  if a * b ≤ limit then .success (a * b) else .fatal

/-- A successful checked multiplication returns the exact product within the limit. -/
theorem checkedMul_sound (limit a b result : Nat)
    (h : checkedMul limit a b = .success result) :
    result = a * b ∧ a * b ≤ limit := by
  unfold checkedMul at h
  by_cases hfit : a * b ≤ limit
  · simp [hfit] at h
    exact ⟨h.symm, hfit⟩
  · simp [hfit] at h

/-- Every representable product is accepted by the checked-multiplication model. -/
theorem checkedMul_complete (limit a b : Nat)
    (h : a * b ≤ limit) :
    checkedMul limit a b = .success (a * b) := by
  unfold checkedMul
  simp [h]

/-- Checked multiplication accepts exactly the products within the limit. -/
theorem checkedMul_exact (limit a b : Nat) :
    (∃ result, checkedMul limit a b = .success result) ↔ a * b ≤ limit := by
  constructor
  · rintro ⟨result, h⟩
    exact (checkedMul_sound limit a b result h).2
  · intro h
    exact ⟨a * b, checkedMul_complete limit a b h⟩

/-- An out-of-range product takes the explicit fatal outcome. -/
theorem checkedMul_overflow_fatal (limit a b : Nat)
    (h : limit < a * b) :
    checkedMul limit a b = .fatal := by
  unfold checkedMul
  have hfit : ¬ a * b ≤ limit := by omega
  simp [hfit]

/-- Capacity growth retains an adequate current capacity, otherwise grows directly
    to the requested capacity if it is within the configured limit. Failure is explicit. -/
def capacityGrowth (limit current required : Nat) : Option Nat :=
  if required ≤ current then some current
  else if required ≤ limit then some required
  else none

/-- Any successful capacity-growth result covers the request and remains within limit,
    provided the incoming capacity was itself within limit. -/
theorem capacityGrowth_sound (limit current required result : Nat)
    (hCurrent : current ≤ limit)
    (h : capacityGrowth limit current required = some result) :
    required ≤ result ∧ result ≤ limit := by
  unfold capacityGrowth at h
  by_cases hEnough : required ≤ current
  · simp [hEnough] at h
    subst result
    exact ⟨hEnough, hCurrent⟩
  · simp [hEnough] at h
    by_cases hFits : required ≤ limit
    · simp [hFits] at h
      subst result
      exact ⟨Nat.le_refl _, hFits⟩
    · simp [hFits] at h

/-- Capacity growth succeeds exactly when the request fits the configured limit,
    assuming the existing capacity is already valid. -/
theorem capacityGrowth_total (limit current required : Nat)
    (hCurrent : current ≤ limit) :
    (∃ result, capacityGrowth limit current required = some result) ↔
      required ≤ limit := by
  constructor
  · rintro ⟨result, h⟩
    exact (capacityGrowth_sound limit current required result hCurrent h).1
      |> fun hRequired => Nat.le_trans hRequired
        (capacityGrowth_sound limit current required result hCurrent h).2
  · intro hRequired
    unfold capacityGrowth
    by_cases hEnough : required ≤ current
    · exact ⟨current, by simp [hEnough]⟩
    · exact ⟨required, by simp [hEnough, hRequired]⟩


/-- One geometric metadata-capacity growth step, saturating at the largest
    representable element count instead of allowing multiplication to wrap. -/
def capacityGrowthStep (maxCount current : Nat) : Nat :=
  if current > maxCount / 2 then maxCount else current * 2

/-- A growth step never shrinks a valid positive capacity and never exceeds maxCount. -/
theorem capacityGrowthStep_bounds (maxCount current : Nat)
    (hCurrent : current ≤ maxCount) :
    current ≤ capacityGrowthStep maxCount current ∧
      capacityGrowthStep maxCount current ≤ maxCount := by
  unfold capacityGrowthStep
  by_cases hHalf : current > maxCount / 2
  · simp [hHalf]
    omega
  · simp [hHalf]
    omega

/-- Unless already at the maximum, geometric growth makes strict progress. -/
theorem capacityGrowthStep_strict (maxCount current : Nat)
    (hPositive : 0 < current) (hBelow : current < maxCount) :
    current < capacityGrowthStep maxCount current := by
  unfold capacityGrowthStep
  by_cases hHalf : current > maxCount / 2
  · simp [hHalf]
    omega
  · simp [hHalf]
    omega

/-- Whether the OS accepted an advice operation on a retained page. -/
inductive PageBacking where
  | resident
  | released
  deriving DecidableEq, Repr

/-- Minimal accounting state for one page, isolated from large-object accounting. -/
structure PageLedger where
  backing : PageBacking
  heapBytes : Nat
  deriving DecidableEq, Repr

/-- Target release semantics: failed advice is a no-op; successful advice is committed
    exactly once; a previously released page is not charged/decremented again. -/
def releasePage (ledger : PageLedger) (adviceSucceeded : Bool)
    (pageBytes : Nat) : PageLedger :=
  match ledger.backing with
  | .released => ledger
  | .resident =>
      if adviceSucceeded then
        { backing := .released, heapBytes := ledger.heapBytes - pageBytes }
      else ledger

/-- Failed OS advice must not change page state or heap accounting. -/
theorem release_failure_preserves (ledger : PageLedger) (pageBytes : Nat) :
    releasePage ledger false pageBytes = ledger := by
  cases h : ledger.backing <;> simp [releasePage, h]

/-- Successful advice for a resident page changes its state and subtracts exactly
    one page charge, assuming the accounting precondition. -/
theorem release_success_exact (ledger : PageLedger) (pageBytes : Nat)
    (hResident : ledger.backing = .resident)
    (hAccounted : pageBytes ≤ ledger.heapBytes) :
    let after := releasePage ledger true pageBytes
    after.backing = .released ∧ after.heapBytes + pageBytes = ledger.heapBytes := by
  cases h : ledger.backing with
  | resident =>
      simp [releasePage, h]
      omega
  | released =>
      simp [h] at hResident

/-- Release is idempotent: a second release cannot decrement accounting again. -/
theorem release_idempotent (ledger : PageLedger) (pageBytes : Nat) :
    releasePage (releasePage ledger true pageBytes) true pageBytes =
      releasePage ledger true pageBytes := by
  cases h : ledger.backing <;> simp [releasePage, h]

/-! ## Finite allocator slot partition

This model records the abstract ownership class of every slot in a bounded page.
It deliberately separates the partition invariant from the concrete in-band
free-list representation. The latter needs a separate refinement relation.
-/

/-- Abstract ownership classes for slots in one allocator page. -/
structure SlotPartition where
  capacity : Nat
  free : Nat → Prop
  allocated : Nat → Prop
  spare : Nat → Prop

/-- Every in-range slot belongs to exactly one of the free, allocated, or spare sets. -/
def SlotPartition.Valid (s : SlotPartition) : Prop :=
  ∀ i, i < s.capacity →
    (s.free i ∨ s.allocated i ∨ s.spare i) ∧
    ¬ (s.free i ∧ s.allocated i) ∧
    ¬ (s.free i ∧ s.spare i) ∧
    ¬ (s.allocated i ∧ s.spare i)

/-- Allocate a designated free slot, moving it from free to allocated. -/
def allocateSlot (s : SlotPartition) (slot : Nat) : SlotPartition :=
  { s with
    free := fun i => s.free i ∧ i ≠ slot
    allocated := fun i => s.allocated i ∨ i = slot }

/-- Releasing an allocated slot moves it back to the free set. -/
def releaseSlot (s : SlotPartition) (slot : Nat) : SlotPartition :=
  { s with
    free := fun i => s.free i ∨ i = slot
    allocated := fun i => s.allocated i ∧ i ≠ slot }

/-- Allocation preserves the exact-one-owner partition invariant. -/
theorem allocateSlot_preserves_partition
    (s : SlotPartition) (slot : Nat)
    (hValid : s.Valid)
    (hBound : slot < s.capacity)
    (hFree : s.free slot) :
    (allocateSlot s slot).Valid := by
  intro i hi
  by_cases hEq : i = slot
  · subst i
    have hNotSpare : ¬ s.spare slot := by
      intro hSpare
      exact (hValid slot hBound).2.2.1 ⟨hFree, hSpare⟩
    simp [allocateSlot, hFree, hNotSpare]
  · have h := hValid i hi
    simpa [SlotPartition.Valid, allocateSlot, hEq] using h

/-- Release preserves the exact-one-owner partition invariant. -/
theorem releaseSlot_preserves_partition
    (s : SlotPartition) (slot : Nat)
    (hValid : s.Valid)
    (hBound : slot < s.capacity)
    (hAllocated : s.allocated slot) :
    (releaseSlot s slot).Valid := by
  intro i hi
  by_cases hEq : i = slot
  · subst i
    have hNotFree : ¬ s.free slot := by
      intro hFree
      exact (hValid slot hBound).2.1 ⟨hFree, hAllocated⟩
    have hNotSpare : ¬ s.spare slot := by
      intro hSpare
      exact (hValid slot hBound).2.2.2 ⟨hAllocated, hSpare⟩
    simp [releaseSlot, hNotFree, hAllocated, hNotSpare]
  · have h := hValid i hi
    simpa [SlotPartition.Valid, releaseSlot, hEq] using h

/-- Allocation changes ownership only at the selected slot. -/
theorem allocateSlot_other_slots_unchanged
    (s : SlotPartition) (slot i : Nat) :
    (allocateSlot s slot).free i = (s.free i ∧ i ≠ slot) ∧
    (allocateSlot s slot).allocated i = (s.allocated i ∨ i = slot) := by
  constructor <;> rfl

/-- Release changes ownership only at the selected slot. -/
theorem releaseSlot_other_slots_unchanged
    (s : SlotPartition) (slot i : Nat) :
    (releaseSlot s slot).free i = (s.free i ∨ i = slot) ∧
    (releaseSlot s slot).allocated i = (s.allocated i ∧ i ≠ slot) := by
  constructor <;> rfl


/-! ## Free-list representation invariant

The abstract list representation establishes boundedness, uniqueness and
completeness relative to the free-slot predicate. Concrete pointer links and
their page/class tags are a separate representation-refinement obligation.
-/

/-- A free list contains each free slot exactly once and no non-free or out-of-range slot. -/
def FreeListInvariant (capacity : Nat) (isFree : Nat → Prop)
    (entries : List Nat) : Prop :=
  entries.Nodup ∧
  (∀ slot, slot ∈ entries → slot < capacity ∧ isFree slot) ∧
  (∀ slot, slot < capacity → (isFree slot ↔ slot ∈ entries))

/-- Inserting a newly free slot preserves boundedness, uniqueness and completeness. -/
theorem freeListPush_preserves
    (capacity slot : Nat) (isFree : Nat → Prop) (entries : List Nat)
    (hInvariant : FreeListInvariant capacity isFree entries)
    (hBound : slot < capacity)
    (hNotFree : ¬ isFree slot) :
    FreeListInvariant capacity (fun i => isFree i ∨ i = slot) (slot :: entries) := by
  have hNotMem : slot ∉ entries := by
    intro hMem
    exact hNotFree ((hInvariant.2.2 slot hBound).mpr hMem)
  refine ⟨List.nodup_cons.mpr ⟨hNotMem, hInvariant.1⟩, ?_, ?_⟩
  · intro i hMem
    rcases List.mem_cons.mp hMem with hEq | hTail
    · subst i
      exact ⟨hBound, Or.inr rfl⟩
    · rcases hInvariant.2.1 i hTail with ⟨hInRange, hFree⟩
      exact ⟨hInRange, Or.inl hFree⟩
  · intro i hInRange
    constructor
    · intro hFree
      rcases hFree with hFree | hEq
      · exact List.mem_cons.mpr (Or.inr ((hInvariant.2.2 i hInRange).mp hFree))
      · subst i
        exact List.mem_cons.mpr (Or.inl rfl)
    · intro hMem
      rcases List.mem_cons.mp hMem with hEq | hTail
      · subst i
        exact Or.inr rfl
      · exact Or.inl ((hInvariant.2.2 i hInRange).mpr hTail)

/-- Popping the head slot for allocation preserves the free-list representation invariant. -/
theorem freeListPop_preserves
    (capacity slot : Nat) (isFree : Nat → Prop) (entries : List Nat)
    (hInvariant : FreeListInvariant capacity isFree (slot :: entries)) :
    FreeListInvariant capacity (fun i => isFree i ∧ i ≠ slot) entries := by
  have hNodup := List.nodup_cons.mp hInvariant.1
  have hNotTail : slot ∉ entries := hNodup.1
  refine ⟨hNodup.2, ?_, ?_⟩
  · intro i hMem
    have hWhole : i ∈ slot :: entries := List.mem_cons.mpr (Or.inr hMem)
    rcases hInvariant.2.1 i hWhole with ⟨hBound, hFree⟩
    have hNe : i ≠ slot := by
      intro hEq
      subst i
      exact hNotTail hMem
    exact ⟨hBound, hFree, hNe⟩
  · intro i hBound
    constructor
    · intro hFree
      have hWhole := (hInvariant.2.2 i hBound).mp hFree.1
      rcases List.mem_cons.mp hWhole with hEq | hTail
      · exact False.elim (hFree.2 hEq)
      · exact hTail
    · intro hMem
      have hWhole : i ∈ slot :: entries := List.mem_cons.mpr (Or.inr hMem)
      have hFree := (hInvariant.2.2 i hBound).mpr hWhole
      have hNe : i ≠ slot := by
        intro hEq
        subst i
        exact hNotTail hMem
      exact ⟨hFree, hNe⟩

end CapstanFormal
