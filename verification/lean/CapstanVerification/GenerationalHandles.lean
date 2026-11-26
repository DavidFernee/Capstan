namespace CapstanVerification

/-!
Region-scoped generation-checked object handles for a future explicit-root
Capstan runtime. This contract is aligned with the region/slot/generation
identity proposed in the bounded CCAM region-heap research stream.

Resolution checks region, slot and generation. Reusing a slot advances its
generation; bounded counters refuse to wrap, requiring permanent retirement.
This remains an abstract target contract, not the current conservative C GC.
-/

/-- Stable region, slot and allocation-incarnation identity. -/
structure ObjectHandle where
  region : Nat
  slot : Nat
  generation : Nat
  deriving DecidableEq, Repr

/-- A region-indexed slot table storing the current generation and payload. -/
abbrev HandleHeap (Object : Type) := Nat → Nat → Option (Nat × Object)

/-- Resolve only when region, slot occupancy and generation all match. -/
def handleResolve {Object : Type}
    (heap : HandleHeap Object) (expectedRegion : Nat)
    (handle : ObjectHandle) : Option Object :=
  if handle.region = expectedRegion then
    match heap expectedRegion handle.slot with
    | none => none
    | some (generation, object) =>
        if generation = handle.generation then some object else none
  else
    none

/-- Install an object at a region/slot under a caller-supplied generation. -/
def handleAllocateAt {Object : Type}
    (heap : HandleHeap Object) (region slot generation : Nat) (object : Object) :
    HandleHeap Object :=
  fun candidateRegion candidateSlot =>
    if candidateRegion = region && candidateSlot = slot then
      some (generation, object)
    else
      heap candidateRegion candidateSlot

/-- Reclaim one region/slot. All handles to its previous generation stop resolving. -/
def handleReleaseAt {Object : Type}
    (heap : HandleHeap Object) (region slot : Nat) : HandleHeap Object :=
  fun candidateRegion candidateSlot =>
    if candidateRegion = region && candidateSlot = slot then none
    else heap candidateRegion candidateSlot

/-- A bounded generation counter advances only while below its configured
maximum. At the maximum it returns none: callers must permanently retire the
slot rather than wrap and risk reviving an old handle. -/
def boundedNextGeneration (maximum current : Nat) : Option Nat :=
  if current < maximum then some (current + 1) else none

/-- A successful bounded increment is strictly greater than the previous
generation. -/
theorem boundedNextGeneration_strict
    (maximum current next : Nat)
    (hnext : boundedNextGeneration maximum current = some next) :
    current < next := by
  have hresult : current < maximum ∧ current + 1 = next := by
    simpa [boundedNextGeneration] using hnext
  rcases hresult with ⟨hlt, heq⟩
  omega

/-- The bounded generation counter never emits a value above its maximum. -/
theorem boundedNextGeneration_bounded
    (maximum current next : Nat)
    (hnext : boundedNextGeneration maximum current = some next) :
    next ≤ maximum := by
  have hresult : current < maximum ∧ current + 1 = next := by
    simpa [boundedNextGeneration] using hnext
  rcases hresult with ⟨hlt, heq⟩
  omega

/-- Once the maximum generation is reached, allocation is refused rather
than wrapping to zero. -/
theorem boundedNextGeneration_retires_at_limit (maximum : Nat) :
    boundedNextGeneration maximum maximum = none := by
  simp [boundedNextGeneration]

/-- A slot already at its maximum cannot issue another generation. -/
theorem boundedNextGeneration_no_wrap
    (maximum : Nat) (next : Nat)
    (hnext : boundedNextGeneration maximum maximum = some next) :
    False := by
  simp [boundedNextGeneration] at hnext

/-- A newly installed handle resolves to its payload in the matching region. -/
theorem handleResolve_new_allocation
    {Object : Type} (heap : HandleHeap Object)
    (region slot generation : Nat) (object : Object) :
    handleResolve (handleAllocateAt heap region slot generation object) region
      { region := region, slot := slot, generation := generation } = some object := by
  simp [handleResolve, handleAllocateAt]

/-- A handle from an older generation cannot resolve after slot reuse. -/
theorem handleResolve_rejects_stale_generation
    {Object : Type} (heap : HandleHeap Object)
    (region slot oldGeneration newGeneration : Nat) (object : Object)
    (hne : newGeneration ≠ oldGeneration) :
    handleResolve (handleAllocateAt heap region slot newGeneration object) region
      { region := region, slot := slot, generation := oldGeneration } = none := by
  simp [handleResolve, handleAllocateAt, hne]

/-- Releasing a region/slot invalidates every handle to that slot. -/
theorem handleRelease_invalidates_handle
    {Object : Type} (heap : HandleHeap Object)
    (region slot generation : Nat) :
    handleResolve (handleReleaseAt heap region slot) region
      { region := region, slot := slot, generation := generation } = none := by
  simp [handleResolve, handleReleaseAt]

/-- Reallocation under a different generation cannot resurrect the released
handle, even if the same region/slot is reused immediately. -/
theorem handleRelease_then_reuse_rejects_stale
    {Object : Type} (heap : HandleHeap Object)
    (region slot oldGeneration newGeneration : Nat) (object : Object)
    (hne : newGeneration ≠ oldGeneration) :
    handleResolve
      (handleAllocateAt (handleReleaseAt heap region slot)
        region slot newGeneration object) region
      { region := region, slot := slot, generation := oldGeneration } = none := by
  exact handleResolve_rejects_stale_generation
    (handleReleaseAt heap region slot) region slot oldGeneration newGeneration object hne

/-- Updating one region/slot leaves every distinct region/slot unchanged. -/
theorem handleAllocateAt_preserves_other_slots
    {Object : Type} (heap : HandleHeap Object)
    (region slot otherRegion otherSlot generation : Nat)
    (object : Object)
    (hdistinct : otherRegion ≠ region ∨ otherSlot ≠ slot) :
    handleAllocateAt heap region slot generation object otherRegion otherSlot =
      heap otherRegion otherSlot := by
  by_cases hregion : otherRegion = region
  · by_cases hslot : otherSlot = slot
    · rcases hdistinct with hne | hne
      · exact (hne hregion).elim
      · exact (hne hslot).elim
    · simp [handleAllocateAt, hregion, hslot]
  · simp [handleAllocateAt, hregion]

/-- A handle cannot be resolved through a different region, even when slot
and generation values happen to match. -/
theorem handleResolve_rejects_cross_region
    {Object : Type} (heap : HandleHeap Object)
    (handle : ObjectHandle) (otherRegion : Nat)
    (hregion : otherRegion ≠ handle.region) :
    handleResolve heap otherRegion handle = none := by
  simp [handleResolve, hregion.symm]

/-- The resolver never accepts a mismatched generation in the selected region
and slot. -/
theorem handleResolve_requires_current_generation
    {Object : Type} (heap : HandleHeap Object)
    (region slot generation currentGeneration : Nat) (object : Object)
    (hslot : heap region slot = some (currentGeneration, object))
    (hne : currentGeneration ≠ generation) :
    handleResolve heap region
      { region := region, slot := slot, generation := generation } = none := by
  simp [handleResolve, hslot, hne]

end CapstanVerification
