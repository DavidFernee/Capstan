import Std

namespace CapstanVerification

/-!
# F1 provenance access-path model

This is a small mathematical model of the path-key and bounded-fact operations
used by the experimental checker. It establishes properties of the abstract
path algebra only. It does NOT prove that compiler/checker.cap refines this
model, that the string encoding is collision-free, or that heap aliases are
tracked. The production source/model correspondence remains an explicit
unproved assurance boundary.
-/

inductive ProvenanceSelector where
  | field (name : String)
  | listIndex (index : Nat)
  | listAny
  | mapKey
  | mapValue
  deriving DecidableEq, Repr

structure ProvenancePath where
  root : Nat
  selectors : List ProvenanceSelector
  deriving DecidableEq, Repr

def provenanceWildcardSelector : ProvenanceSelector → ProvenanceSelector
  | .listIndex _ => .listAny
  | selector => selector

def provenanceWildcardPath (path : ProvenancePath) : ProvenancePath :=
  { path with selectors := path.selectors.map provenanceWildcardSelector }

def provenancePrefix (ancestor path : ProvenancePath) : Prop :=
  ancestor.root = path.root ∧ ∃ suffix, ancestor.selectors ++ suffix = path.selectors

/-- A conservative may-derived relation: exact, wildcard, ancestor or descendant facts. -/
def provenancePathMarked (facts : List ProvenancePath) (path : ProvenancePath) : Prop :=
  path ∈ facts ∨ provenanceWildcardPath path ∈ facts ∨
    ∃ fact, fact ∈ facts ∧
      (provenancePrefix path fact ∨ provenancePrefix fact path)

def localProvenancePath (bindingId : Nat) : ProvenancePath :=
  { root := bindingId, selectors := [] }

def listElementPath (bindingId index : Nat) : ProvenancePath :=
  { root := bindingId, selectors := [.listIndex index] }

def listWildcardPath (bindingId : Nat) : ProvenancePath :=
  { root := bindingId, selectors := [.listAny] }

def mapKeyPath (bindingId : Nat) : ProvenancePath :=
  { root := bindingId, selectors := [.mapKey] }

def mapValuePath (bindingId : Nat) : ProvenancePath :=
  { root := bindingId, selectors := [.mapValue] }

/-- A dynamic-index write conservatively marks every constant-index read. -/
theorem dynamic_write_marks_constant_read (bindingId index : Nat) :
    provenancePathMarked [listWildcardPath bindingId] (listElementPath bindingId index) := by
  right
  left
  simp [provenanceWildcardPath, listElementPath, listWildcardPath,
    provenanceWildcardSelector]

/-- Distinct lexical binding identities cannot share a root path. -/
theorem binding_identity_separates_locals (left right : Nat)
    (h : left ≠ right) :
    localProvenancePath left ≠ localProvenancePath right := by
  intro heq
  have roots := congrArg ProvenancePath.root heq
  exact h roots

/-- Map keys and map values occupy different abstract locations. -/
theorem map_key_value_paths_are_disjoint (bindingId : Nat) :
    mapKeyPath bindingId ≠ mapValuePath bindingId := by
  intro heq
  have selectors := congrArg ProvenancePath.selectors heq
  simp [mapKeyPath, mapValuePath] at selectors

/-- A fact below an aggregate root marks the aggregate as potentially derived. -/
theorem descendant_fact_marks_aggregate (bindingId : Nat)
    (selector : ProvenanceSelector) :
    provenancePathMarked
      [{ root := bindingId, selectors := [selector] }]
      (localProvenancePath bindingId) := by
  right
  right
  refine ⟨{ root := bindingId, selectors := [selector] }, by simp, ?_⟩
  left
  exact ⟨rfl, [selector], by simp [localProvenancePath]⟩

/-- Adding facts never removes an existing may-derived result. -/
theorem provenance_marking_monotone (facts : List ProvenancePath)
    (path : ProvenancePath) (extra : ProvenancePath)
    (h : provenancePathMarked facts path) :
    provenancePathMarked (extra :: facts) path := by
  rcases h with hExact | hWildcard | hRelated
  · exact Or.inl (by simp [hExact])
  · exact Or.inr (Or.inl (by simp [hWildcard]))
  · exact Or.inr (Or.inr (by
      rcases hRelated with ⟨fact, hmem, hprefix⟩
      exact ⟨fact, by simp [hmem], hprefix⟩))

/-- The executable checker has a finite path-fact budget. -/
def provenancePathLimit : Nat := 4096

def addProvenanceFactBounded (limit : Nat) (facts : List ProvenancePath)
    (path : ProvenancePath) : Option (List ProvenancePath) :=
  if path ∈ facts then some facts
  else if facts.length < limit then some (path :: facts)
  else none

/-- At capacity, a new fact is rejected rather than silently dropped. -/
theorem provenance_fact_budget_fails_closed (facts : List ProvenancePath)
    (path : ProvenancePath) (hfull : provenancePathLimit ≤ facts.length)
    (hnew : path ∉ facts) :
    addProvenanceFactBounded provenancePathLimit facts path = none := by
  have hnot : ¬ facts.length < provenancePathLimit := Nat.not_lt.mpr hfull
  simp [addProvenanceFactBounded, hnew, hnot]

end CapstanVerification
