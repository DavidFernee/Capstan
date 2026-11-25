import NativeMemoryLifecycle

/-!
Explicit-root, descriptor-guided reachability model.

Root references carry a proof that their generation-checked handle resolves
in the current heap domain. Heap edges are defined only by reference offsets
selected by the object's descriptor; scalar fields and non-reference fields
are not traversed.

The collector is proof-carrying at this stage: it accepts a mark certificate
whose roots are included and whose marked set is closed under descriptor
edges, then sweeps everything outside that set. This proves the safety of
sweeping from a valid certificate. It does NOT yet prove an executable marker
constructs such a certificate; that is the next refinement obligation.
-/

namespace CapstanNativeReachability

open CapstanNativeMemory

universe u

inductive FieldValue where
  | scalar (value : Int)
  | reference (target : Nat)
deriving Repr, DecidableEq

structure HeapObject where
  descriptor : Nat
  fields : List FieldValue
deriving Repr, DecidableEq

/-- Descriptor table: for each layout, the field offsets that contain
references. Every other field is non-tracing data. -/
abbrev DescriptorTable := Nat → List Nat

abbrev Heap := Nat → Option HeapObject

/-- A root is not an unchecked integer: it records a live handle and the
proof that resolving that handle in this domain yields this object ID. -/
structure ResolvedRoot {slotCount : Nat}
    (table : SlotTable slotCount Nat) (domain : Nat) where
  handle : ObjectHandle slotCount
  objectId : Nat
  resolves : resolveHandle table domain handle = some objectId

/-- A stack/register/global root frame contains only resolved live roots. -/
abbrev RootFrame {slotCount : Nat}
    (table : SlotTable slotCount Nat) (domain : Nat) :=
  List (ResolvedRoot table domain)

abbrev RootFrames {slotCount : Nat}
    (table : SlotTable slotCount Nat) (domain : Nat) :=
  List (RootFrame table domain)

def rootIds {slotCount : Nat} {table : SlotTable slotCount Nat}
    {domain : Nat} (frames : RootFrames table domain) : List Nat :=
  frames.flatMap (fun frame => frame.map (fun root => root.objectId))

/-- The descriptor-guided edge relation ignores scalar fields and every
field offset not declared by the object's layout. -/
inductive DescriptorEdge (descriptors : DescriptorTable) (heap : Heap) :
    Nat → Nat → Prop where
  | field {source target : Nat} {object : HeapObject} {offset : Nat} :
      heap source = some object →
      offset ∈ descriptors object.descriptor →
      object.fields[offset]? = some (.reference target) →
      DescriptorEdge descriptors heap source target

/-- Least reachability relation from the explicit root snapshot. -/
inductive Reachable (descriptors : DescriptorTable) (heap : Heap)
    (roots : List Nat) : Nat → Prop where
  | root {objectId : Nat} :
      objectId ∈ roots →
      heap objectId ≠ none →
      Reachable descriptors heap roots objectId
  | edge {source target : Nat} :
      Reachable descriptors heap roots source →
      DescriptorEdge descriptors heap source target →
      heap target ≠ none →
      Reachable descriptors heap roots target

/-- A mark certificate must include every root and be closed under every
descriptor-selected reference edge from every marked object. -/
structure MarkCertificate (descriptors : DescriptorTable)
    (heap : Heap) (roots : List Nat) where
  marked : List Nat
  includesRoots : ∀ objectId, objectId ∈ roots → objectId ∈ marked
  closedUnderEdges : ∀ source, source ∈ marked →
    ∀ target, DescriptorEdge descriptors heap source target →
      target ∈ marked

/-- Sweep retains exactly the objects named by the accepted mark set. -/
def sweep (heap : Heap) (marked : List Nat) : Heap :=
  fun objectId => if objectId ∈ marked then heap objectId else none

/-- Every reachable object is in any mark set that includes roots and is
closed under descriptor-guided edges. -/
theorem reachable_is_marked
    (descriptors : DescriptorTable) (heap : Heap) (roots : List Nat)
    (certificate : MarkCertificate descriptors heap roots)
    {objectId : Nat}
    (reachable : Reachable descriptors heap roots objectId) :
    objectId ∈ certificate.marked := by
  induction reachable with
  | root hroot _ =>
      exact certificate.includesRoots _ hroot
  | @edge source target hsource hedge htarget ih =>
      exact certificate.closedUnderEdges source ih target hedge

/-- The sweep transition cannot reclaim a reachable object. -/
theorem sweep_preserves_reachable
    (descriptors : DescriptorTable) (heap : Heap) (roots : List Nat)
    (certificate : MarkCertificate descriptors heap roots)
    {objectId : Nat}
    (reachable : Reachable descriptors heap roots objectId) :
    sweep heap certificate.marked objectId = heap objectId := by
  unfold sweep
  simp [reachable_is_marked descriptors heap roots certificate reachable]

/-- Sweep never creates an object at a previously empty location. -/
theorem sweep_does_not_create_objects
    (heap : Heap) (marked : List Nat) (objectId : Nat)
    (empty : heap objectId = none) :
    sweep heap marked objectId = none := by
  simp [sweep, empty]

/-- Every root ID in a frame is backed by a handle that resolves to it in
the exact table/domain snapshot from which the frame was constructed. -/
theorem root_frame_entries_are_resolved
    {slotCount : Nat} {table : SlotTable slotCount Nat} {domain : Nat}
    (frame : RootFrame table domain) :
    ∀ root, root ∈ frame →
      resolveHandle table domain root.handle = some root.objectId := by
  intro root _member
  exact root.resolves

#print axioms CapstanNativeReachability.reachable_is_marked
#print axioms CapstanNativeReachability.sweep_preserves_reachable
#print axioms CapstanNativeReachability.sweep_does_not_create_objects
#print axioms CapstanNativeReachability.root_frame_entries_are_resolved

end CapstanNativeReachability
