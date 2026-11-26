import CapstanVerification.Core

namespace CapstanVerification

/-!
First abstract model for the process-lifetime compiler arena.

This is deliberately separate from CCAM v0.1 and from frame-scoped scratch
regions. The heap is immutable state: every operation returns a new state and
an explicit result. A failed transition retains the exact prior state.
References carry an arena identity and an object identifier; resolving a
reference checks the arena identity before looking up the object.

This is a semantic model only. It does not yet prove correspondence with
verification/ccam_heap.cap, the CCAM validator/evaluator, or the native backend.
-/

inductive AggregateTrap where
  | allocationLimit
  | crossArenaReference
  | invalidReference
  | immutableField
  | typeMismatch
  deriving DecidableEq, Repr

/-- Opaque at the source-language boundary; represented explicitly in this
abstract model so that provenance checks can be stated and proved. -/
structure AggregateRef where
  arenaId : Nat
  objectId : Nat
  deriving DecidableEq, Repr

/-- Minimal object metadata needed for the first allocation/provenance proof.
Payload semantics are modelled separately by typed record fields below. -/
structure AggregateObject where
  descriptorId : Nat
  chargedBytes : Nat
  deriving DecidableEq, Repr

/-- A finite, monotonically allocated process-lifetime arena. The object table
is a total function with absent entries for unallocated identifiers. -/
structure AggregateHeap where
  arenaId : Nat
  nextObjectId : Nat
  objectCount : Nat
  maxObjects : Nat
  usedBytes : Nat
  maxBytes : Nat
  objects : Nat → Option AggregateObject
  object_count_bounded : objectCount ≤ maxObjects
  bytes_bounded : usedBytes ≤ maxBytes
  future_ids_absent : ∀ id, nextObjectId ≤ id → objects id = none

/-- Construct an empty arena with explicit object and byte ceilings. -/
def emptyAggregateHeap (arenaId maxObjects maxBytes : Nat) : AggregateHeap :=
  { arenaId := arenaId
    nextObjectId := 1
    objectCount := 0
    maxObjects := maxObjects
    usedBytes := 0
    maxBytes := maxBytes
    objects := fun _ => none
    object_count_bounded := Nat.zero_le _
    bytes_bounded := Nat.zero_le _
    future_ids_absent := by intro id _; rfl }

/-- State and result are kept together so a rejected operation can explicitly
demonstrate that no state change occurred. -/
structure AggregateHeapTransition where
  heap : AggregateHeap
  result : Except AggregateTrap AggregateRef

/-- Allocate one object after checking both resource budgets. The state update
is committed only in the success branch. Object identifiers are monotonic and
are never supplied by the program. -/
def allocateAggregateObject (heap : AggregateHeap)
    (descriptorId chargedBytes : Nat) : AggregateHeapTransition :=
  if hobjects : heap.objectCount < heap.maxObjects then
    if hbytes : heap.usedBytes + chargedBytes ≤ heap.maxBytes then
      let object : AggregateObject :=
        { descriptorId := descriptorId, chargedBytes := chargedBytes }
      { heap :=
          { arenaId := heap.arenaId
            nextObjectId := heap.nextObjectId + 1
            objectCount := heap.objectCount + 1
            maxObjects := heap.maxObjects
            usedBytes := heap.usedBytes + chargedBytes
            maxBytes := heap.maxBytes
            objects := fun id =>
              if id = heap.nextObjectId then some object else heap.objects id
            object_count_bounded := by omega
            bytes_bounded := hbytes
            future_ids_absent := by
              intro id hid
              have hne : id ≠ heap.nextObjectId := by omega
              simp [hne, heap.future_ids_absent id (by omega)] }
        result := .ok { arenaId := heap.arenaId, objectId := heap.nextObjectId } }
    else
      { heap := heap, result := .error .allocationLimit }
  else
    { heap := heap, result := .error .allocationLimit }

/-- Failed allocation leaves the arena state exactly unchanged. -/
theorem allocateAggregateObject_failure_atomic
    (heap : AggregateHeap) (descriptorId chargedBytes : Nat)
    (trap : AggregateTrap)
    (hfail : (allocateAggregateObject heap descriptorId chargedBytes).result =
      .error trap) :
    (allocateAggregateObject heap descriptorId chargedBytes).heap = heap := by
  by_cases hobjects : heap.objectCount < heap.maxObjects
  · by_cases hbytes : heap.usedBytes + chargedBytes ≤ heap.maxBytes
    · simp [allocateAggregateObject, hobjects, hbytes] at hfail
    · simp [allocateAggregateObject, hobjects, hbytes] at hfail ⊢
  · simp [allocateAggregateObject, hobjects] at hfail ⊢

/-- Successful allocation returns the next machine-issued object identifier. -/
theorem allocateAggregateObject_returns_fresh_id
    (heap : AggregateHeap) (descriptorId chargedBytes : Nat)
    (reference : AggregateRef)
    (hsuccess :
      (allocateAggregateObject heap descriptorId chargedBytes).result =
        .ok reference) :
    reference.arenaId = heap.arenaId ∧
      reference.objectId = heap.nextObjectId := by
  unfold allocateAggregateObject at hsuccess
  by_cases hobjects : heap.objectCount < heap.maxObjects
  · simp only [hobjects, ↓reduceDIte] at hsuccess
    by_cases hbytes : heap.usedBytes + chargedBytes ≤ heap.maxBytes
    · simp [hbytes] at hsuccess ⊢
      cases hsuccess
      exact ⟨rfl, rfl⟩
    · simp [hbytes] at hsuccess
  · simp [hobjects] at hsuccess

/-- Successful allocation increments object count and byte accounting by the
exact amounts charged by the new object. -/
theorem allocateAggregateObject_accounting
    (heap : AggregateHeap) (descriptorId chargedBytes : Nat)
    (reference : AggregateRef)
    (hsuccess :
      (allocateAggregateObject heap descriptorId chargedBytes).result =
        .ok reference) :
    (allocateAggregateObject heap descriptorId chargedBytes).heap.objectCount =
        heap.objectCount + 1 ∧
      (allocateAggregateObject heap descriptorId chargedBytes).heap.usedBytes =
        heap.usedBytes + chargedBytes := by
  by_cases hobjects : heap.objectCount < heap.maxObjects
  · by_cases hbytes : heap.usedBytes + chargedBytes ≤ heap.maxBytes
    · simp [allocateAggregateObject, hobjects, hbytes] at hsuccess ⊢
    · simp [allocateAggregateObject, hobjects, hbytes] at hsuccess
  · simp [allocateAggregateObject, hobjects] at hsuccess

/-- Resolve a reference only after checking that it belongs to this arena. -/
def resolveAggregateReference (heap : AggregateHeap)
    (reference : AggregateRef) : Except AggregateTrap AggregateObject :=
  if reference.arenaId = heap.arenaId then
    match heap.objects reference.objectId with
    | some object => .ok object
    | none => .error .invalidReference
  else
    .error .crossArenaReference

/-- A reference from a different arena is rejected before object lookup. -/
theorem resolveAggregateReference_rejects_cross_arena
    (heap : AggregateHeap) (reference : AggregateRef)
    (hidentity : reference.arenaId ≠ heap.arenaId) :
    resolveAggregateReference heap reference =
      .error .crossArenaReference := by
  simp [resolveAggregateReference, hidentity]

/-- The reference returned by a successful allocation resolves to the exact
descriptor and byte charge that were allocated. -/
theorem allocateAggregateObject_reference_resolves
    (heap : AggregateHeap) (descriptorId chargedBytes : Nat)
    (reference : AggregateRef)
    (hsuccess :
      (allocateAggregateObject heap descriptorId chargedBytes).result =
        .ok reference) :
    resolveAggregateReference
      (allocateAggregateObject heap descriptorId chargedBytes).heap reference =
        .ok { descriptorId := descriptorId, chargedBytes := chargedBytes } := by
  unfold allocateAggregateObject at hsuccess ⊢
  by_cases hobjects : heap.objectCount < heap.maxObjects
  · simp only [hobjects, ↓reduceDIte] at hsuccess ⊢
    by_cases hbytes : heap.usedBytes + chargedBytes ≤ heap.maxBytes
    · simp [hbytes] at hsuccess ⊢
      cases hsuccess
      simp [resolveAggregateReference]
    · simp [hbytes] at hsuccess
  · simp [hobjects] at hsuccess

/-- Aggregate types added by the process-arena profile. Reference descriptor
compatibility is checked by resolving the referenced object, not by treating a
source integer as a handle. -/
inductive AggregateTy where
  | int
  | bool
  | reference
  deriving DecidableEq, Repr

inductive AggregateValue where
  | int (value : Int)
  | bool (value : Bool)
  | reference (value : AggregateRef)
  deriving DecidableEq, Repr

def aggregateValueHasTypeB : AggregateValue → AggregateTy → Bool
  | .int value, .int => inI64B value
  | .bool _, .bool => true
  | .reference _, .reference => true
  | _, _ => false

/-- A record layout has a stable nominal descriptor and exact field metadata. -/
structure AggregateRecordLayout (n : Nat) where
  descriptorId : Nat
  fieldTypes : Fin n → AggregateTy
  fieldMutable : Fin n → Bool

abbrev AggregateRecordFields (n : Nat) := Fin n → Option AggregateValue

def AggregateRecordWellTyped {n : Nat}
    (layout : AggregateRecordLayout n) (fields : AggregateRecordFields n) : Prop :=
  ∀ index value, fields index = some value →
    aggregateValueHasTypeB value (layout.fieldTypes index) = true

def setAggregateRecordField {n : Nat}
    (fields : AggregateRecordFields n) (index : Fin n)
    (value : AggregateValue) : AggregateRecordFields n :=
  fun other => if other = index then some value else fields other

/-- Field mutation checks mutability and exact value type before producing a
new field function. The original field state is never mutated in place. -/
def writeAggregateRecordField {n : Nat}
    (layout : AggregateRecordLayout n) (fields : AggregateRecordFields n)
    (index : Fin n) (value : AggregateValue) :
    Except AggregateTrap (AggregateRecordFields n) :=
  if layout.fieldMutable index || fields index == none then
    if aggregateValueHasTypeB value (layout.fieldTypes index) then
      .ok (setAggregateRecordField fields index value)
    else
      .error .typeMismatch
  else
    .error .immutableField

/-- A successful typed field write preserves the complete record invariant. -/
theorem writeAggregateRecordField_preserves_well_typed
    {n : Nat} (layout : AggregateRecordLayout n)
    (fields next : AggregateRecordFields n) (index : Fin n)
    (value : AggregateValue)
    (hfields : AggregateRecordWellTyped layout fields)
    (hwrite : writeAggregateRecordField layout fields index value = .ok next) :
    AggregateRecordWellTyped layout next := by
  unfold writeAggregateRecordField at hwrite
  by_cases hcanwrite : layout.fieldMutable index || fields index == none
  · simp [hcanwrite] at hwrite
    by_cases htype : aggregateValueHasTypeB value (layout.fieldTypes index)
    · simp [htype] at hwrite
      cases hwrite
      intro other stored hread
      by_cases hsame : other = index
      · subst other
        simp [setAggregateRecordField] at hread
        cases hread
        exact htype
      · have hold : fields other = some stored := by
          simpa [setAggregateRecordField, hsame] using hread
        exact hfields other stored hold
    · simp [htype] at hwrite
  · simp [hcanwrite] at hwrite

/-- Failed record writes are failure-atomic: no replacement field state is
returned, and the caller retains the original fields. -/
theorem writeAggregateRecordField_failure_has_no_new_state
    {n : Nat} (layout : AggregateRecordLayout n)
    (fields : AggregateRecordFields n) (index : Fin n)
    (value : AggregateValue) (trap : AggregateTrap)
    (hfail : writeAggregateRecordField layout fields index value = .error trap) :
    ∀ next, writeAggregateRecordField layout fields index value ≠ .ok next := by
  intro next hok
  rw [hfail] at hok
  cases hok

end CapstanVerification
