/-
  Experimental CCAM region-heap transition model.

  This is an abstract semantic model only. It does not prove that
  verification/ccam_heap.cap or any runtime implementation refines it.
-/
namespace CCAMHeapModel

abbrev RegionId := Nat
abbrev ObjectId := Nat
abbrev DescriptorId := Nat

/-- A model-level region authority token. This is deliberately only an identity
    binding: issuance, opacity and non-forgeability are not proved by this model. -/
structure RegionCapability where
  region : RegionId

def capabilityRegion (cap : RegionCapability) : RegionId := cap.region

structure HeapState where
  region : RegionId
  maxBytes : Nat
  maxObjects : Nat
  usedBytes : Nat
  maxWork : Nat
  workUsed : Nat
  maxTemporaryBytes : Nat
  temporaryPeakBytes : Nat
  nextObject : ObjectId
  objectCount : Nat
  deriving DecidableEq, Repr

def heapInvariant (s : HeapState) : Prop :=
  s.usedBytes ≤ s.maxBytes ∧
  s.objectCount ≤ s.maxObjects ∧
  s.workUsed ≤ s.maxWork ∧
  s.temporaryPeakBytes ≤ s.maxTemporaryBytes ∧
  s.nextObject = s.objectCount + 1

def hasAuthority (cap : RegionCapability) (s : HeapState) : Prop :=
  capabilityRegion cap = s.region

inductive HeapError where
  | invalidAuthority
  | byteLimit
  | objectLimit
  | invalidCharge
  | workLimit
  | temporaryLimit
  | invalidHeapState
  deriving DecidableEq, Repr

inductive AllocationResult where
  | allocated (state : HeapState) (object : ObjectId)
  | rejected (error : HeapError) (state : HeapState)
  deriving DecidableEq, Repr

def invalidHeapState (s : HeapState) : Bool :=
  decide (s.usedBytes > s.maxBytes) ||
  decide (s.objectCount > s.maxObjects) ||
  decide (s.workUsed > s.maxWork) ||
  decide (s.temporaryPeakBytes > s.maxTemporaryBytes) ||
  decide (s.nextObject ≠ s.objectCount + 1)

/-- Allocation has an explicit logical charge and requires the owning region
    capability. Failed allocation returns the original state unchanged. -/
def allocate (cap : RegionCapability) (s : HeapState)
    (charge workCharge temporaryCharge : Nat) : AllocationResult :=
  if capabilityRegion cap ≠ s.region then
    .rejected .invalidAuthority s
  else if invalidHeapState s then
    .rejected .invalidHeapState s
  else if charge = 0 then
    .rejected .invalidCharge s
  else if s.objectCount >= s.maxObjects then
    .rejected .objectLimit s
  else if s.usedBytes + charge > s.maxBytes then
    .rejected .byteLimit s
  else if s.workUsed + workCharge > s.maxWork then
    .rejected .workLimit s
  else if temporaryCharge > s.maxTemporaryBytes then
    .rejected .temporaryLimit s
  else
    .allocated
      { s with
        usedBytes := s.usedBytes + charge
        workUsed := s.workUsed + workCharge
        temporaryPeakBytes := max s.temporaryPeakBytes temporaryCharge
        nextObject := s.nextObject + 1
        objectCount := s.objectCount + 1 }
      s.nextObject

/-- Every rejected allocation is failure-atomic. -/
theorem rejected_allocation_preserves_state
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (error : HeapError) (after : HeapState)
    (h : allocate cap s charge workCharge temporaryCharge = .rejected error after) :
    after = s := by
  unfold allocate at h
  by_cases hAuth : capabilityRegion cap = s.region
  · by_cases hInvalid : invalidHeapState s
    · simp [hAuth, hInvalid] at h
      exact h.2.symm
    · by_cases hCharge : charge = 0
      · simp [hAuth, hInvalid, hCharge] at h
        exact h.2.symm
      · by_cases hObjects : s.objectCount ≥ s.maxObjects
        · simp [hAuth, hInvalid, hCharge, hObjects] at h
          exact h.2.symm
        · by_cases hBytes : s.usedBytes + charge > s.maxBytes
          · simp [hAuth, hInvalid, hCharge, hObjects, hBytes] at h
            exact h.2.symm
          · by_cases hWork : s.workUsed + workCharge > s.maxWork
            · simp [hAuth, hInvalid, hCharge, hObjects, hBytes, hWork] at h
              exact h.2.symm
            · by_cases hTemporary : temporaryCharge > s.maxTemporaryBytes
              · simp [hAuth, hInvalid, hCharge, hObjects, hBytes, hWork, hTemporary] at h
                exact h.2.symm
              · simp [hAuth, hInvalid, hCharge, hObjects, hBytes, hWork, hTemporary] at h
  · simp [hAuth] at h
    exact h.2.symm

/-- A successful allocation exposes the exact state update and every admission bound. -/
theorem allocation_success_facts
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    after = { s with
        usedBytes := s.usedBytes + charge
        workUsed := s.workUsed + workCharge
        temporaryPeakBytes := max s.temporaryPeakBytes temporaryCharge
        nextObject := s.nextObject + 1
        objectCount := s.objectCount + 1 } ∧
    object = s.nextObject ∧
    charge ≠ 0 ∧
    s.objectCount < s.maxObjects ∧
    s.usedBytes + charge ≤ s.maxBytes ∧
    s.workUsed + workCharge ≤ s.maxWork ∧
    temporaryCharge ≤ s.maxTemporaryBytes ∧
    s.temporaryPeakBytes ≤ s.maxTemporaryBytes := by
  unfold allocate at h
  by_cases hAuth : capabilityRegion cap = s.region
  · by_cases hInvalid : invalidHeapState s
    · simp [hAuth, hInvalid] at h
    · by_cases hCharge : charge = 0
      · simp [hAuth, hInvalid, hCharge] at h
      · by_cases hObjects : s.objectCount ≥ s.maxObjects
        · simp [hAuth, hInvalid, hCharge, hObjects] at h
        · by_cases hBytes : s.usedBytes + charge > s.maxBytes
          · simp [hAuth, hInvalid, hCharge, hObjects, hBytes] at h
          · by_cases hWork : s.workUsed + workCharge > s.maxWork
            · simp [hAuth, hInvalid, hCharge, hObjects, hBytes, hWork] at h
            · by_cases hTemporary : temporaryCharge > s.maxTemporaryBytes
              · simp [hAuth, hInvalid, hCharge, hObjects, hBytes, hWork, hTemporary] at h
              · simp [hAuth, hInvalid, hCharge, hObjects, hBytes, hWork, hTemporary] at h
                constructor
                · exact h.1.symm
                constructor
                · exact h.2.symm
                constructor
                · exact hCharge
                constructor
                · omega
                constructor
                · omega
                constructor
                · omega
                constructor
                · omega
                · have hOldTemporary : s.temporaryPeakBytes ≤ s.maxTemporaryBytes := by
                    by_cases hOld : s.temporaryPeakBytes ≤ s.maxTemporaryBytes
                    · exact hOld
                    · have hgt : s.temporaryPeakBytes > s.maxTemporaryBytes := by omega
                      have hBad : invalidHeapState s = true := by
                        simp [invalidHeapState, hgt]
                      exact False.elim (hInvalid hBad)
  · simp [hAuth] at h

/-- Successful allocation returns the previous next-object identity. -/
theorem allocation_returns_previous_counter
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    object = s.nextObject := by
  exact (allocation_success_facts cap s charge workCharge temporaryCharge after object h).2.1

/-- Successful allocation preserves every conjunct of the heap invariant. -/
theorem allocate_success_preserves_heapInvariant
    (cap : RegionCapability) (s : HeapState)
    (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (hInv : heapInvariant s)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    heapInvariant after := by
  rcases allocation_success_facts cap s charge workCharge temporaryCharge after object h with
    ⟨hAfter, hObject, hCharge, hObjects, hBytes, hWork, hTemporary, hOldTemporary⟩
  subst after
  have hPeak : max s.temporaryPeakBytes temporaryCharge ≤ s.maxTemporaryBytes :=
    Nat.max_le.mpr ⟨hOldTemporary, hTemporary⟩
  unfold heapInvariant
  constructor
  · omega
  constructor
  · omega
  constructor
  · omega
  constructor
  · exact hPeak
  · omega

/-- A successful allocation is charged exactly the admitted amount. -/
theorem allocation_charges_exactly
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    after.usedBytes = s.usedBytes + charge := by
  rcases allocation_success_facts cap s charge workCharge temporaryCharge after object h with
    ⟨hAfter, hObject, hCharge, hObjects, hBytes, hWork, hTemporary, hOldTemporary⟩
  subst after
  rfl

/-- Successful allocation preserves the logical byte budget, provided the
    input state is within budget. -/
theorem allocation_preserves_byte_bound
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (hInv : s.usedBytes ≤ s.maxBytes)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    after.usedBytes ≤ after.maxBytes := by
  rcases allocation_success_facts cap s charge workCharge temporaryCharge after object h with
    ⟨hAfter, hObject, hCharge, hObjects, hBytes, hWork, hTemporary, hOldTemporary⟩
  subst after
  omega

/-- Successful allocation preserves the object-count budget. -/
theorem allocation_preserves_object_bound
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (hInv : s.objectCount ≤ s.maxObjects)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    after.objectCount ≤ after.maxObjects := by
  rcases allocation_success_facts cap s charge workCharge temporaryCharge after object h with
    ⟨hAfter, hObject, hCharge, hObjects, hBytes, hWork, hTemporary, hOldTemporary⟩
  subst after
  omega

/-- Successful allocation charges exactly the admitted work units. -/
theorem allocation_charges_exact_work
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    after.workUsed = s.workUsed + workCharge := by
  rcases allocation_success_facts cap s charge workCharge temporaryCharge after object h with
    ⟨hAfter, hObject, hCharge, hObjects, hBytes, hWork, hTemporary, hOldTemporary⟩
  subst after
  rfl

/-- Successful allocation never reports a temporary peak above the admitted charge. -/
theorem allocation_bounds_temporary_peak
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    after.temporaryPeakBytes ≤ after.maxTemporaryBytes := by
  rcases allocation_success_facts cap s charge workCharge temporaryCharge after object h with
    ⟨hAfter, hObject, hCharge, hObjects, hBytes, hWork, hTemporary, hOldTemporary⟩
  subst after
  exact max_le hOldTemporary hTemporary

/-- Successful allocation preserves the cumulative work budget. -/
theorem allocation_preserves_work_bound
    (cap : RegionCapability) (s : HeapState) (charge workCharge temporaryCharge : Nat)
    (after : HeapState) (object : ObjectId)
    (hInv : s.workUsed ≤ s.maxWork)
    (h : allocate cap s charge workCharge temporaryCharge = .allocated after object) :
    after.workUsed ≤ after.maxWork := by
  rcases allocation_success_facts cap s charge workCharge temporaryCharge after object h with
    ⟨hAfter, hObject, hCharge, hObjects, hBytes, hWork, hTemporary, hOldTemporary⟩
  subst after
  omega

/-- Region authority is checked independently of object identity. -/
theorem authority_mismatch_rejected
    (cap : RegionCapability) (s : HeapState)
    (h : capabilityRegion cap ≠ s.region) :
    ∀ charge workCharge temporaryCharge, ∃ error,
      allocate cap s charge workCharge temporaryCharge = .rejected error s := by
  intro charge workCharge temporaryCharge
  refine ⟨.invalidAuthority, ?_⟩
  simp [allocate, h]

/-
  Generational object identity model.

  This is a target contract for a future handle-based runtime, not a model of
  today's conservative collector, which exposes stable raw addresses and does
  not validate generations on dereference. Recycling advances the generation
  before a slot can identify a different object.
-/

/-- Stable slot number paired with a generation to prevent stale-handle reuse. -/
structure ObjectHandle where
  region : RegionId
  slot : Nat
  generation : Nat
  deriving DecidableEq, Repr

/-- Abstract state of one reusable object slot. -/
structure ObjectSlot where
  generation : Nat
  occupant : Option ObjectId
  deriving DecidableEq, Repr

/-- Resolve only when both slot generation and object occupancy agree. -/
def resolveHandle (handle : ObjectHandle) (region : RegionId)
    (slotIndex : Nat) (slot : ObjectSlot) : Option ObjectId :=
  if handle.region = region && handle.slot = slotIndex &&
      handle.generation = slot.generation then
    slot.occupant
  else
    none

/-- Reuse a reclaimed slot by advancing its generation before publishing the
    replacement object. This transition abstracts successful reclamation. -/
def recycleSlot (slot : ObjectSlot) (replacement : ObjectId) : ObjectSlot :=
  { generation := slot.generation + 1, occupant := some replacement }

/-- A handle from the previous generation cannot resolve after slot reuse. -/
theorem stale_handle_rejected_after_recycle
    (region : RegionId) (slot : ObjectSlot) (replacement : ObjectId)
    (oldHandle : ObjectHandle)
    (hregion : oldHandle.region = region)
    (hgen : oldHandle.generation = slot.generation) :
    resolveHandle oldHandle region oldHandle.slot
      (recycleSlot slot replacement) = none := by
  simp [resolveHandle, recycleSlot, hregion, hgen] <;> omega

/-- The new generation resolves to the replacement object. -/
theorem current_handle_resolves_after_recycle
    (region : RegionId) (slot : ObjectSlot) (replacement : ObjectId) :
    resolveHandle
      { region := region, slot := 0, generation := slot.generation + 1 }
      region 0 (recycleSlot slot replacement) = some replacement := by
  simp [resolveHandle, recycleSlot]

/-- A handle cannot be resolved through a different slot, even when
    region and generation happen to match. -/
theorem wrong_slot_handle_rejected
    (handle : ObjectHandle) (region : RegionId) (slotIndex : Nat)
    (slot : ObjectSlot) (hslot : handle.slot ≠ slotIndex) :
    resolveHandle handle region slotIndex slot = none := by
  simp [resolveHandle, hslot]

/-- A handle from another region is rejected even when its slot generation
    matches. Region authority and generation identity are separate checks. -/
theorem cross_region_handle_rejected
    (handle : ObjectHandle) (region : RegionId) (slot : ObjectSlot)
    (hregion : handle.region ≠ region) :
    resolveHandle handle region handle.slot slot = none := by
  simp [resolveHandle, hregion]


/-
  Capability issuance and revocation contract.

  This model records which serials an issuer has issued and revoked. It is
  deliberately not a cryptographic or representation-level non-forgeability
  proof: a concrete runtime must hide constructors/state and prevent callers
  from fabricating a matching serial.
-/

structure CapabilityIssuerState where
  region : RegionId
  nextSerial : Nat
  issued : List Nat
  revoked : List Nat
  deriving DecidableEq, Repr

structure RegionGrant where
  region : RegionId
  serial : Nat
  deriving DecidableEq, Repr

/-- Issue the next serial and record it in the issuer's authoritative ledger. -/
def issueCapability (issuer : CapabilityIssuerState) :
    CapabilityIssuerState × RegionGrant :=
  let grant : RegionGrant := { region := issuer.region, serial := issuer.nextSerial }
  ({ issuer with
    nextSerial := issuer.nextSerial + 1
    issued := issuer.issued ++ [issuer.nextSerial] }, grant)

/-- A grant is valid only if issued by this region's issuer and not revoked. -/
def capabilityValid (issuer : CapabilityIssuerState) (grant : RegionGrant) : Prop :=
  grant.region = issuer.region ∧
  grant.serial ∈ issuer.issued ∧
  grant.serial ∉ issuer.revoked

/-- Issuance returns a grant recorded by the issuer and not already revoked. -/
theorem issueCapability_grant_valid
    (issuer : CapabilityIssuerState)
    (hfresh : issuer.nextSerial ∉ issuer.revoked) :
    capabilityValid (issueCapability issuer).1 (issueCapability issuer).2 := by
  simp [issueCapability, capabilityValid, hfresh]

/-- Issuance uses a serial not already present in the issued ledger when the
    issuer's counter is fresh. -/
theorem issueCapability_grant_fresh
    (issuer : CapabilityIssuerState)
    (hfresh : issuer.nextSerial ∉ issuer.issued) :
    (issueCapability issuer).2.serial ∉ issuer.issued := by
  simp [issueCapability, hfresh]

/-- Issuance never changes the revocation ledger. -/
theorem issueCapability_preserves_revocations
    (issuer : CapabilityIssuerState) :
    (issueCapability issuer).1.revoked = issuer.revoked := by
  simp [issueCapability]

/-- Revocation is fail-closed: only a grant for this region which was actually
    issued by this issuer can alter the revocation ledger. Repeated revocation
    is idempotent. -/
def revokeCapability (issuer : CapabilityIssuerState) (grant : RegionGrant) :
    Option CapabilityIssuerState :=
  if grant.region = issuer.region ∧ grant.serial ∈ issuer.issued then
    some { issuer with
      revoked := if grant.serial ∈ issuer.revoked then
        issuer.revoked else issuer.revoked ++ [grant.serial] }
  else
    none

/-- A valid grant revoked by its issuer no longer satisfies the validity predicate. -/
theorem revoked_capability_invalid
    (issuer : CapabilityIssuerState) (grant : RegionGrant)
    (hvalid : capabilityValid issuer grant) :
    match revokeCapability issuer grant with
    | some after => ¬ capabilityValid after grant
    | none => False := by
  rcases hvalid with ⟨hregion, hissued, hnotRevoked⟩
  simp [revokeCapability, capabilityValid, hregion, hissued, hnotRevoked]

/-- A cross-region revocation request is rejected without changing state. -/
theorem cross_region_revocation_rejected
    (issuer : CapabilityIssuerState) (grant : RegionGrant)
    (hregion : grant.region ≠ issuer.region) :
    revokeCapability issuer grant = none := by
  simp [revokeCapability, hregion]

/-- A serial not issued by this issuer cannot be revoked through its ledger. -/
theorem unissued_revocation_rejected
    (issuer : CapabilityIssuerState) (grant : RegionGrant)
    (hissued : grant.serial ∉ issuer.issued) :
    revokeCapability issuer grant = none := by
  simp [revokeCapability, hissued]

/-- A grant from another region cannot satisfy the issuer's validity predicate. -/
theorem cross_region_grant_invalid
    (issuer : CapabilityIssuerState) (grant : RegionGrant)
    (hregion : grant.region ≠ issuer.region) :
    ¬ capabilityValid issuer grant := by
  intro h
  exact hregion h.1

/-- Logical heap bytes are intentionally distinct from host RSS/allocator
    consumption. No theorem here claims a process-memory bound. -/
def logicalBytesWithinBudget (s : HeapState) : Prop :=
  s.usedBytes ≤ s.maxBytes

end CCAMHeapModel
