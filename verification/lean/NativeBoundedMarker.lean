import NativeMemoryLifecycle

/-!
A bounded, fail-closed worklist marker specification over generation-checked
handles. The edge function is the descriptor-filtered reference projection
for one immutable heap snapshot; the live predicate resolves handles in that
same snapshot and domain.

This is an executable list-based reference algorithm, not the production
collector. Its linear list membership is intentionally simple; a bounded
hash/index implementation and its refinement proof remain later work.
-/

namespace CapstanNativeBoundedMarker

open CapstanNativeMemory

abbrev Handle (slotCount : Nat) := ObjectHandle slotCount

structure MarkerBudget where
  maxRoots : Nat
  maxObjects : Nat
  maxEdges : Nat
  maxWorklist : Nat
  maxDescriptorSlots : Nat
  maxWork : Nat
deriving Repr, DecidableEq

structure MarkerCounters where
  roots : Nat
  objects : Nat
  edges : Nat
  worklistPeak : Nat
  descriptorSlots : Nat
  work : Nat
deriving Repr, DecidableEq

inductive MarkerReject where
  | invalidHandle
  | invalidDescriptor
  | rootLimit
  | objectLimit
  | edgeLimit
  | worklistLimit
  | descriptorLimit
  | workLimit
  | certificateRejected
deriving Repr, DecidableEq

/-- Independent certificate validation: every root is marked; every marked
handle resolves; and every descriptor-projected edge from a marked handle
terminates in the marked set. -/
def certificateCheck {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots marked : List (Handle slotCount)) : Bool :=
  roots.all (fun root => decide (root ∈ marked)) &&
  marked.all (fun handle =>
    isLive handle && descriptorValid handle &&
    (referenceEdges handle).all (fun target => decide (target ∈ marked)))





/-- A complete result carries the successful independent certificate check.
A rejected result can never be mistaken for a partial mark set. -/
inductive MarkerOutcome {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots : List (Handle slotCount)) where
  | complete (marked : List (Handle slotCount)) (counters : MarkerCounters)
      (accepted : certificateCheck isLive descriptorValid referenceEdges roots marked = true)
  | rejected (reason : MarkerReject) (counters : MarkerCounters)


theorem certificateCheck_sound {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots marked : List (Handle slotCount))
    (checked : certificateCheck isLive descriptorValid referenceEdges roots marked = true) :
    (∀ root, root ∈ roots → root ∈ marked) ∧
    (∀ handle, handle ∈ marked → isLive handle = true) ∧
    (∀ handle, handle ∈ marked → descriptorValid handle = true) ∧
    (∀ handle, handle ∈ marked → ∀ target,
      target ∈ referenceEdges handle → target ∈ marked) := by
  unfold certificateCheck at checked
  rcases Bool.and_eq_true.mp checked with ⟨rootsChecked, markedChecked⟩
  have rootsValid := List.all_eq_true.mp rootsChecked
  have markedValid := List.all_eq_true.mp markedChecked
  refine ⟨?_, ?_, ?_, ?_⟩
  · intro root rootMember
    exact of_decide_eq_true (rootsValid root rootMember)
  · intro handle handleMember
    exact (Bool.and_eq_true.mp (markedValid handle handleMember)).1
  · intro handle handleMember
    have fieldsChecked := Bool.and_eq_true.mp (markedValid handle handleMember)
    exact (Bool.and_eq_true.mp fieldsChecked.2).1
  · intro handle handleMember target targetMember
    have fieldsChecked := Bool.and_eq_true.mp (markedValid handle handleMember)
    have edgesChecked := (Bool.and_eq_true.mp fieldsChecked.2).2
    exact of_decide_eq_true ((List.all_eq_true.mp edgesChecked) target targetMember)

/-- Proof-carrying view of an accepted marker outcome. Sweep-facing
code can require this type instead of accepting a raw candidate list. -/
structure CheckedCertificate {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots : List (Handle slotCount)) where
  marked : List (Handle slotCount)
  includesRoots : ∀ root, root ∈ roots → root ∈ marked
  allLive : ∀ handle, handle ∈ marked → isLive handle = true
  allDescriptorsValid : ∀ handle, handle ∈ marked → descriptorValid handle = true
  closedUnderEdges : ∀ handle, handle ∈ marked → ∀ target,
    target ∈ referenceEdges handle → target ∈ marked

/-- Only a complete outcome can be converted into a sweep-facing
certificate. Rejection carries no candidate mark set. -/
def certificateOfOutcome {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots : List (Handle slotCount)) :
    MarkerOutcome isLive descriptorValid referenceEdges roots →
      Option (CheckedCertificate isLive descriptorValid referenceEdges roots)
  | .complete marked _ accepted =>
      let sound := certificateCheck_sound isLive descriptorValid referenceEdges roots marked accepted
      some {
        marked := marked
        includesRoots := sound.1
        allLive := sound.2.1
        allDescriptorsValid := sound.2.2.1
        closedUnderEdges := sound.2.2.2
      }
  | .rejected _ _ => none

theorem rejected_has_no_certificate {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots : List (Handle slotCount))
    (reason : MarkerReject) (counters : MarkerCounters) :
    certificateOfOutcome isLive descriptorValid referenceEdges roots
      (.rejected reason counters) = none := rfl

/-- Append only targets that are neither visited nor already pending. -/
def freshTargets {slotCount : Nat}
    (targets visited pending : List (Handle slotCount)) :
    List (Handle slotCount) :=
  targets.foldl (fun accepted target =>
    if decide (target ∈ visited) ||
       decide (target ∈ pending) ||
       decide (target ∈ accepted) then
      accepted
    else
      accepted ++ [target]) []

/-- Fuel-bounded FIFO worklist. Every object is scanned at most once; every
budget is checked before the corresponding work is admitted. -/
def markerLoop {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (descriptorCost : Handle slotCount → Nat)
    (roots : List (Handle slotCount))
    (budget : MarkerBudget)
    (fuel : Nat)
    (pending visited : List (Handle slotCount))
    (counters : MarkerCounters) :
    MarkerOutcome isLive descriptorValid referenceEdges roots :=
  if pending.isEmpty then
    if checked : certificateCheck isLive descriptorValid referenceEdges roots visited = true then
      .complete visited counters checked
    else
      .rejected .certificateRejected counters
  else
    match fuel with
    | 0 => .rejected .workLimit counters
    | fuel + 1 =>
      match pending with
      | [] =>
        if checked : certificateCheck isLive descriptorValid referenceEdges roots visited = true then
          .complete visited counters checked
        else
          .rejected .certificateRejected counters
      | handle :: rest =>
        if counters.work >= budget.maxWork then
          .rejected .workLimit counters
        else if isLive handle = false then
          .rejected .invalidHandle { counters with work := counters.work + 1 }
        else if descriptorValid handle = false then
          .rejected .invalidDescriptor { counters with work := counters.work + 1 }
        else if decide (handle ∈ visited) then
          markerLoop isLive descriptorValid referenceEdges descriptorCost roots budget fuel
            rest visited
            { counters with work := counters.work + 1 }
        else if visited.length >= budget.maxObjects then
          .rejected .objectLimit { counters with work := counters.work + 1 }
        else
          let cost := descriptorCost handle
          if counters.descriptorSlots + cost > budget.maxDescriptorSlots then
            .rejected .descriptorLimit { counters with work := counters.work + 1 }
          else
            let outgoing := referenceEdges handle
            if counters.edges + outgoing.length > budget.maxEdges then
              .rejected .edgeLimit { counters with work := counters.work + 1 }
            else
              let discovered := freshTargets outgoing (handle :: visited) rest
              let nextPending := rest ++ discovered
              let nextPeak := max counters.worklistPeak nextPending.length
              let nextCounters :=
                { roots := counters.roots
                  objects := counters.objects + 1
                  edges := counters.edges + outgoing.length
                  worklistPeak := nextPeak
                  descriptorSlots := counters.descriptorSlots + cost
                  work := counters.work + 1 }
              if nextPending.length > budget.maxWorklist then
                .rejected .worklistLimit nextCounters
              else
                markerLoop isLive descriptorValid referenceEdges descriptorCost roots budget fuel
                  nextPending (visited ++ [handle]) nextCounters

/-- Start with deduplicated roots. The fuel bound is maxWork + 1; reaching
zero with pending work is always rejection, never successful completion. -/
def runBoundedMarker {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (descriptorCost : Handle slotCount → Nat)
    (roots : List (Handle slotCount))
    (budget : MarkerBudget) :
    MarkerOutcome isLive descriptorValid referenceEdges roots :=
  let initialCounters : MarkerCounters :=
    { roots := roots.length, objects := 0, edges := 0, worklistPeak := 0,
      descriptorSlots := 0, work := 0 }
  if roots.length > budget.maxRoots then
    .rejected .rootLimit initialCounters
  else
    let initial := freshTargets roots [] []
    let counters := { initialCounters with worklistPeak := initial.length }
    if initial.length > budget.maxWorklist then
      .rejected .worklistLimit counters
    else
      markerLoop isLive descriptorValid referenceEdges descriptorCost roots budget
        (budget.maxWork + 1) initial [] counters

/-- A successful marker result is a checked certificate, not a partial
traversal. This theorem exposes the root-inclusion and edge-closure facts
needed by a future sweep gate. -/
theorem complete_result_is_certificate {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (descriptorValid : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots marked : List (Handle slotCount))
    (accepted : certificateCheck isLive descriptorValid referenceEdges roots marked = true) :
    (∀ root, root ∈ roots → root ∈ marked) ∧
    (∀ handle, handle ∈ marked → isLive handle = true) ∧
    (∀ handle, handle ∈ marked → descriptorValid handle = true) ∧
    (∀ handle, handle ∈ marked → ∀ target,
      target ∈ referenceEdges handle → target ∈ marked) :=
  certificateCheck_sound isLive descriptorValid referenceEdges roots marked accepted

#print axioms CapstanNativeBoundedMarker.certificateCheck_sound
#print axioms CapstanNativeBoundedMarker.complete_result_is_certificate

end CapstanNativeBoundedMarker


/-! ## Executable adversarial regression cases

These closed examples exercise boundary conditions in the reference marker.
They are deliberately evaluated by Lean's kernel reduction, not by an external
test harness. They do not substitute for testing a concrete collector or
proving a refinement to one.
-/

namespace AdversarialTests

open CapstanNativeMemory
open CapstanNativeBoundedMarker

def h0 : Handle 3 := { domain := 7, slot := ⟨0, by decide⟩, generation := 0 }
def h1 : Handle 3 := { domain := 7, slot := ⟨1, by decide⟩, generation := 0 }
def h2 : Handle 3 := { domain := 7, slot := ⟨2, by decide⟩, generation := 0 }

def budget (roots objects edges worklist descriptorSlots work : Nat) : MarkerBudget :=
  { maxRoots := roots, maxObjects := objects, maxEdges := edges,
    maxWorklist := worklist, maxDescriptorSlots := descriptorSlots,
    maxWork := work }

def noEdges (_ : Handle 3) : List (Handle 3) := []
def allLive (_ : Handle 3) : Bool := true
def allDescriptorsValid (_ : Handle 3) : Bool := true
def zeroDescriptorCost (_ : Handle 3) : Nat := 0

def completes (result : MarkerOutcome allLive allDescriptorsValid noEdges [h0]) : Bool :=
  match result with
  | .complete _ _ _ => true
  | .rejected _ _ => false

/-- A single root succeeds when every independent budget is exactly sufficient. -/
example :
    completes (runBoundedMarker allLive allDescriptorsValid noEdges
      zeroDescriptorCost [h0] (budget 1 1 0 1 0 1)) = true := by
  decide

/-- Root input is charged before deduplication and rejected before resolution. -/
example :
    (match runBoundedMarker (fun _ : Handle 3 => false) allDescriptorsValid
      noEdges zeroDescriptorCost [h0, h0] (budget 1 1 0 1 0 1) with
     | .rejected .rootLimit _ => true
     | _ => false) = true := by
  decide

/-- A stale/unresolvable root fails closed. -/
example :
    (match runBoundedMarker (fun _ : Handle 3 => false) allDescriptorsValid
      noEdges zeroDescriptorCost [h0] (budget 1 1 0 1 0 1) with
     | .rejected .invalidHandle _ => true
     | _ => false) = true := by
  decide

/-- A live handle with an invalid descriptor is rejected before edge access. -/
example :
    (match runBoundedMarker allLive (fun _ : Handle 3 => false)
      noEdges zeroDescriptorCost [h0] (budget 1 1 0 1 0 1) with
     | .rejected .invalidDescriptor _ => true
     | _ => false) = true := by
  decide

/-- The total-work budget is enforced even when roots are already admitted. -/
example :
    (match runBoundedMarker allLive allDescriptorsValid noEdges
      zeroDescriptorCost [h0] (budget 1 1 0 1 0 0) with
     | .rejected .workLimit _ => true
     | _ => false) = true := by
  decide

/-- A self-cycle is accepted at the exact object, edge, worklist and work limits. -/
def selfCycle (handle : Handle 3) : List (Handle 3) :=
  if handle == h0 then [h0] else []

example :
    (match runBoundedMarker allLive allDescriptorsValid selfCycle
      zeroDescriptorCost [h0] (budget 1 1 1 1 0 1) with
     | .complete marked counters _ =>
         decide (h0 ∈ marked) && decide (counters.edges = 1) &&
           decide (counters.work = 1)
     | .rejected _ _ => false) = true := by
  decide

/-- The same self-cycle is rejected when the edge budget is one below need. -/
example :
    (match runBoundedMarker allLive allDescriptorsValid selfCycle
      zeroDescriptorCost [h0] (budget 1 1 0 1 0 1) with
     | .rejected .edgeLimit _ => true
     | _ => false) = true := by
  decide

/-- Duplicate outgoing edges are charged as inspected edges but enqueue once. -/
def duplicateEdges (handle : Handle 3) : List (Handle 3) :=
  if handle == h0 then [h1, h1] else []

example :
    (match runBoundedMarker allLive allDescriptorsValid duplicateEdges
      zeroDescriptorCost [h0] (budget 1 2 2 1 0 2) with
     | .complete marked counters _ =>
         decide (marked.length = 2) && decide (counters.edges = 2) &&
           decide (counters.work = 2) && decide (counters.worklistPeak = 1)
     | .rejected _ _ => false) = true := by
  decide

/-- A descriptor cost is independently bounded, including exact-limit success. -/
def unitDescriptorCost (_ : Handle 3) : Nat := 1

example :
    (match runBoundedMarker allLive allDescriptorsValid noEdges
      unitDescriptorCost [h0] (budget 1 1 0 1 1 1) with
     | .complete _ counters _ => decide (counters.descriptorSlots = 1)
     | .rejected _ _ => false) = true := by
  decide

example :
    (match runBoundedMarker allLive allDescriptorsValid noEdges
      unitDescriptorCost [h0] (budget 1 1 0 1 0 1) with
     | .rejected .descriptorLimit _ => true
     | _ => false) = true := by
  decide

/-- Pending-work growth is bounded independently of total object capacity. -/
def branchingEdges (handle : Handle 3) : List (Handle 3) :=
  if handle == h0 then [h1, h2] else []

example :
    (match runBoundedMarker allLive allDescriptorsValid branchingEdges
      zeroDescriptorCost [h0] (budget 1 3 2 1 0 3) with
     | .rejected .worklistLimit _ => true
     | _ => false) = true := by
  decide

end AdversarialTests
