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
  maxObjects : Nat
  maxEdges : Nat
  maxWorklist : Nat
  maxDescriptorSlots : Nat
  maxWork : Nat
deriving Repr, DecidableEq

structure MarkerCounters where
  objects : Nat
  edges : Nat
  worklistPeak : Nat
  descriptorSlots : Nat
  work : Nat
deriving Repr, DecidableEq

inductive MarkerReject where
  | invalidHandle
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
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots marked : List (Handle slotCount)) : Bool :=
  roots.all (fun root => decide (root ∈ marked)) &&
  marked.all (fun handle =>
    isLive handle &&
    (referenceEdges handle).all (fun target => decide (target ∈ marked)))





/-- A complete result carries the successful independent certificate check.
A rejected result can never be mistaken for a partial mark set. -/
inductive MarkerOutcome {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots : List (Handle slotCount)) where
  | complete (marked : List (Handle slotCount)) (counters : MarkerCounters)
      (accepted : certificateCheck isLive referenceEdges roots marked = true)
  | rejected (reason : MarkerReject) (counters : MarkerCounters)


theorem certificateCheck_sound {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots marked : List (Handle slotCount))
    (checked : certificateCheck isLive referenceEdges roots marked = true) :
    (∀ root, root ∈ roots → root ∈ marked) ∧
    (∀ handle, handle ∈ marked → isLive handle = true) ∧
    (∀ handle, handle ∈ marked → ∀ target,
      target ∈ referenceEdges handle → target ∈ marked) := by
  unfold certificateCheck at checked
  rcases Bool.and_eq_true.mp checked with ⟨rootsChecked, markedChecked⟩
  have rootsValid := List.all_eq_true.mp rootsChecked
  have markedValid := List.all_eq_true.mp markedChecked
  refine ⟨?_, ?_, ?_⟩
  · intro root rootMember
    exact of_decide_eq_true (rootsValid root rootMember)
  · intro handle handleMember
    exact (Bool.and_eq_true.mp (markedValid handle handleMember)).1
  · intro handle handleMember target targetMember
    have fieldsChecked := Bool.and_eq_true.mp (markedValid handle handleMember)
    exact of_decide_eq_true ((List.all_eq_true.mp fieldsChecked.2) target targetMember)

/-- Append only targets that are neither visited nor already pending. -/
def freshTargets {slotCount : Nat}
    (targets visited pending : List (Handle slotCount)) :
    List (Handle slotCount) :=
  targets.filter (fun target =>
    !(decide (target ∈ visited) || decide (target ∈ pending)))

/-- Fuel-bounded FIFO worklist. Every object is scanned at most once; every
budget is checked before the corresponding work is admitted. -/
def markerLoop {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (descriptorCost : Handle slotCount → Nat)
    (roots : List (Handle slotCount))
    (budget : MarkerBudget)
    (fuel : Nat)
    (pending visited : List (Handle slotCount))
    (counters : MarkerCounters) :
    MarkerOutcome isLive referenceEdges roots :=
  if pending.isEmpty then
    if checked : certificateCheck isLive referenceEdges roots visited = true then
      .complete visited counters checked
    else
      .rejected .certificateRejected counters
  else
    match fuel with
    | 0 => .rejected .workLimit counters
    | fuel + 1 =>
      match pending with
      | [] =>
        if checked : certificateCheck isLive referenceEdges roots visited = true then
          .complete visited counters checked
        else
          .rejected .certificateRejected counters
      | handle :: rest =>
        if counters.work >= budget.maxWork then
          .rejected .workLimit counters
        else if isLive handle = false then
          .rejected .invalidHandle { counters with work := counters.work + 1 }
        else if decide (handle ∈ visited) then
          markerLoop isLive referenceEdges descriptorCost roots budget fuel
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
                { objects := counters.objects + 1
                  edges := counters.edges + outgoing.length
                  worklistPeak := nextPeak
                  descriptorSlots := counters.descriptorSlots + cost
                  work := counters.work + 1 }
              if nextPending.length > budget.maxWorklist then
                .rejected .worklistLimit nextCounters
              else
                markerLoop isLive referenceEdges descriptorCost roots budget fuel
                  nextPending (visited ++ [handle]) nextCounters
termination_by fuel
decreasing_by omega

/-- Start with deduplicated roots. The fuel bound is maxWork + 1; reaching
zero with pending work is always rejection, never successful completion. -/
def runBoundedMarker {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (descriptorCost : Handle slotCount → Nat)
    (roots : List (Handle slotCount))
    (budget : MarkerBudget) :
    MarkerOutcome isLive referenceEdges roots :=
  let initial := freshTargets roots [] []
  let counters : MarkerCounters :=
    { objects := 0, edges := 0, worklistPeak := initial.length,
      descriptorSlots := 0, work := 0 }
  if initial.length > budget.maxWorklist then
    .rejected .worklistLimit counters
  else
    markerLoop isLive referenceEdges descriptorCost roots budget
      (budget.maxWork + 1) initial [] counters

/-- A successful marker result is a checked certificate, not a partial
traversal. This theorem exposes the root-inclusion and edge-closure facts
needed by a future sweep gate. -/
theorem complete_result_is_certificate {slotCount : Nat}
    (isLive : Handle slotCount → Bool)
    (referenceEdges : Handle slotCount → List (Handle slotCount))
    (roots marked : List (Handle slotCount))
    (counters : MarkerCounters)
    (accepted : certificateCheck isLive referenceEdges roots marked = true) :
    (∀ root, root ∈ roots → root ∈ marked) ∧
    (∀ handle, handle ∈ marked → isLive handle = true) ∧
    (∀ handle, handle ∈ marked → ∀ target,
      target ∈ referenceEdges handle → target ∈ marked) :=
  certificateCheck_sound isLive referenceEdges roots marked accepted

#print axioms CapstanNativeBoundedMarker.certificateCheck_sound
#print axioms CapstanNativeBoundedMarker.complete_result_is_certificate

end CapstanNativeBoundedMarker
