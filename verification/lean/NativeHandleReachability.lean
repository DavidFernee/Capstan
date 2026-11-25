import NativeMemoryLifecycle

/-!
Generation-checked internal heap edges.

Unlike the earlier stable-ID graph abstraction, every reference-bearing field
contains an opaque ObjectHandle. Both roots and internal edges are resolved
through the same immutable slot-table snapshot and heap domain. A stale,
freed, reused, or cross-domain edge therefore cannot silently name a new
occupant. This is still an abstract model: descriptor/layout refinement,
root completeness, and an executable bounded marker remain separate gates.
-/

namespace CapstanNativeHandleReachability

open CapstanNativeMemory

universe u

inductive HandleFieldValue (slotCount : Nat) where
  | scalar (value : Int)
  | reference (target : ObjectHandle slotCount)
deriving Repr

structure HandleHeapObject (slotCount : Nat) where
  descriptor : Nat
  fields : List (HandleFieldValue slotCount)
deriving Repr

abbrev HandleHeap (slotCount : Nat) :=
  SlotTable slotCount (HandleHeapObject slotCount)

abbrev DescriptorTable := Nat → List Nat

/-- An edge is valid only when the source and target handles both resolve in
this exact heap snapshot and domain, and the source offset is descriptor-
declared reference storage. -/
inductive HandleDescriptorEdge {slotCount : Nat}
    (descriptors : DescriptorTable)
    (heap : HandleHeap slotCount) (domain : Nat) :
    ObjectHandle slotCount → ObjectHandle slotCount → Prop where
  | field {source target : ObjectHandle slotCount}
      {sourceObject targetObject : HandleHeapObject slotCount}
      {offset : Nat} :
      resolveHandle heap domain source = some sourceObject →
      resolveHandle heap domain target = some targetObject →
      offset ∈ descriptors sourceObject.descriptor →
      sourceObject.fields[offset]? = some (.reference target) →
      HandleDescriptorEdge descriptors heap domain source target

/-- Root frames contain handles, not naked object IDs. -/
abbrev HandleRootFrame (slotCount : Nat) := List (ObjectHandle slotCount)

inductive HandleReachable {slotCount : Nat}
    (descriptors : DescriptorTable)
    (heap : HandleHeap slotCount) (domain : Nat)
    (roots : HandleRootFrame slotCount) :
    ObjectHandle slotCount → Prop where
  | root {handle : ObjectHandle slotCount} :
      handle ∈ roots →
      ∃ object, resolveHandle heap domain handle = some object →
      HandleReachable descriptors heap domain roots handle
  | edge {source target : ObjectHandle slotCount} :
      HandleReachable descriptors heap domain roots source →
      HandleDescriptorEdge descriptors heap domain source target →
      HandleReachable descriptors heap domain roots target

structure HandleMarkCertificate {slotCount : Nat}
    (descriptors : DescriptorTable)
    (heap : HandleHeap slotCount) (domain : Nat)
    (roots : HandleRootFrame slotCount) where
  marked : List (ObjectHandle slotCount)
  includesRoots : ∀ handle, handle ∈ roots → handle ∈ marked
  closedUnderEdges : ∀ source, source ∈ marked →
    ∀ target, HandleDescriptorEdge descriptors heap domain source target →
      target ∈ marked

theorem handle_reachable_is_marked {slotCount : Nat}
    (descriptors : DescriptorTable)
    (heap : HandleHeap slotCount) (domain : Nat)
    (roots : HandleRootFrame slotCount)
    (certificate : HandleMarkCertificate descriptors heap domain roots)
    {handle : ObjectHandle slotCount}
    (reachable : HandleReachable descriptors heap domain roots handle) :
    handle ∈ certificate.marked := by
  induction reachable with
  | root hroot _ =>
      exact certificate.includesRoots _ hroot
  | @edge source target hsource hedge ih =>
      exact certificate.closedUnderEdges source ih target hedge

/-- A stale generation cannot be accepted as a descriptor edge target:
the edge constructor requires successful resolution of that exact handle. -/
theorem stale_internal_handle_rejected {slotCount : Nat}
    (heap : HandleHeap slotCount) (domain : Nat)
    (handle : ObjectHandle slotCount) (object : HandleHeapObject slotCount)
    (stale : resolveHandle heap domain handle = none) :
    resolveHandle heap domain handle ≠ some object := by
  simp [stale]

/-- Cross-domain internal handles are rejected by the same resolver used
for roots. -/
theorem cross_domain_internal_handle_rejected {slotCount : Nat}
    (heap : HandleHeap slotCount) (domain : Nat)
    (handle : ObjectHandle slotCount) (object : HandleHeapObject slotCount)
    (wrongDomain : handle.domain ≠ domain) :
    resolveHandle heap domain handle ≠ some object := by
  simp [resolveHandle, wrongDomain]

#print axioms CapstanNativeHandleReachability.handle_reachable_is_marked
#print axioms CapstanNativeHandleReachability.stale_internal_handle_rejected
#print axioms CapstanNativeHandleReachability.cross_domain_internal_handle_rejected

end CapstanNativeHandleReachability
