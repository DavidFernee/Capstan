import Std

namespace CapstanVerification

/-!
# Injection-freedom provenance foundation

This module defines the first mechanised fragment of Capstan's proposed
provenance semantics. It models explicit data dependence and selection
dependence independently. It is intentionally not a source-language checker,
a CCAM machine, or an implementation-refinement proof.

Normative design input:
  docs/assurance/PROVENANCE-SEMANTICS.md

The model is conservative about the dependencies it represents. Pure implicit
control dependence, validation soundness, heap aliasing, interprocedural
summaries, sinks, and compiler/evaluator correspondence are separate obligations.
-/

abbrev SourceId := Nat

/-- The set of external sources on which an abstract value may depend. -/
abbrev Provenance := Finset SourceId

/-- Explicit information-flow facts, kept separate by dependency kind. -/
structure ProvenanceValue where
  dataSources : Provenance
  selectionSources : Provenance
  deriving DecidableEq, Repr

/-- A literal has no external data or selection dependency. -/
def emptyProvenanceValue : ProvenanceValue :=
  { dataSources := ∅, selectionSources := ∅ }

/-- An externally controlled source contributes direct data provenance. -/
def inputProvenanceValue (source : SourceId) : ProvenanceValue :=
  { dataSources := {source}, selectionSources := ∅ }

/-- Combining values joins both kinds of explicit dependency. -/
def combineProvenance (left right : ProvenanceValue) : ProvenanceValue :=
  { dataSources := left.dataSources ∪ right.dataSources
    selectionSources := left.selectionSources ∪ right.selectionSources }

/--
Selecting a value preserves the selected value's data provenance and records
the selector as selection provenance. Existing selection dependencies on both
operands are retained.
-/
def selectProvenance (selected selector : ProvenanceValue) : ProvenanceValue :=
  { dataSources := selected.dataSources
    selectionSources :=
      selected.selectionSources ∪ selector.dataSources ∪ selector.selectionSources }

/-- A small expression language for the explicit-flow provenance fragment. -/
inductive ProvenanceExpr where
  | literal
  | input (source : SourceId)
  | combine (left right : ProvenanceExpr)
  | select (selected selector : ProvenanceExpr)
  deriving Repr

/-- Abstract evaluation of the explicit-flow expression fragment. -/
def evalProvenance : ProvenanceExpr → ProvenanceValue
  | .literal => emptyProvenanceValue
  | .input source => inputProvenanceValue source
  | .combine left right =>
      combineProvenance (evalProvenance left) (evalProvenance right)
  | .select selected selector =>
      selectProvenance (evalProvenance selected) (evalProvenance selector)

/-- A source introduced by an input expression is present in its data provenance. -/
theorem input_source_is_data_provenance (source : SourceId) :
    source ∈ (evalProvenance (.input source)).dataSources := by
  simp [evalProvenance, inputProvenanceValue]

/-- Combining expressions cannot discard the left operand's data provenance. -/
theorem combine_preserves_left_data
    (left right : ProvenanceValue) :
    left.dataSources ⊆ (combineProvenance left right).dataSources := by
  intro source hsource
  simp [combineProvenance, hsource]

/-- Combining expressions cannot discard the right operand's data provenance. -/
theorem combine_preserves_right_data
    (left right : ProvenanceValue) :
    right.dataSources ⊆ (combineProvenance left right).dataSources := by
  intro source hsource
  simp [combineProvenance, hsource]

/-- Combining expressions cannot discard either operand's selection provenance. -/
theorem combine_preserves_selection
    (left right : ProvenanceValue) :
    left.selectionSources ∪ right.selectionSources ⊆
      (combineProvenance left right).selectionSources := by
  intro source hsource
  exact hsource

/-- The selector's data dependence is retained as selection dependence. -/
theorem select_preserves_selector_data
    (selected selector : ProvenanceValue) :
    selector.dataSources ⊆ (selectProvenance selected selector).selectionSources := by
  intro source hsource
  simp [selectProvenance, hsource]

/-- Selection preserves the selected value's direct data provenance. -/
theorem select_preserves_selected_data
    (selected selector : ProvenanceValue) :
    selected.dataSources ⊆ (selectProvenance selected selector).dataSources := by
  intro source hsource
  exact hsource

/-- Selection preserves pre-existing selector and selected-value dependencies. -/
theorem select_preserves_prior_selection
    (selected selector : ProvenanceValue) :
    selected.selectionSources ∪ selector.selectionSources ⊆
      (selectProvenance selected selector).selectionSources := by
  intro source hsource
  simp [selectProvenance] at *
  rcases hsource with hsource | hsource
  · exact Or.inl hsource
  · exact Or.inr (Or.inr hsource)

/-- Literal evaluation introduces no external provenance. -/
theorem literal_has_no_provenance :
    evalProvenance .literal = emptyProvenanceValue := by
  rfl

/-- All source identities syntactically introduced by an expression. -/
def expressionSources : ProvenanceExpr → Provenance
  | .literal => ∅
  | .input source => {source}
  | .combine left right => expressionSources left ∪ expressionSources right
  | .select selected selector =>
      expressionSources selected ∪ expressionSources selector

/-- Sources represented in either direct-data or selection provenance. -/
def representedSources (value : ProvenanceValue) : Provenance :=
  value.dataSources ∪ value.selectionSources

/--
Every input source syntactically introduced by an expression remains present
in either its direct-data or selection provenance. In particular, selecting
trusted-looking data with an input-derived selector does not erase the input's
influence.
-/
theorem expression_sources_preserved (expr : ProvenanceExpr) :
    expressionSources expr ⊆ representedSources (evalProvenance expr) := by
  induction expr with
  | literal =>
      simp [expressionSources, representedSources, evalProvenance,
        emptyProvenanceValue]
  | input source =>
      simp [expressionSources, representedSources, evalProvenance,
        inputProvenanceValue]
  | combine left right ihLeft ihRight =>
      intro source hsource
      simp only [expressionSources, Finset.mem_union] at hsource
      simp only [representedSources, evalProvenance, combineProvenance,
        Finset.mem_union]
      rcases hsource with hleft | hright
      · exact Or.inl (ihLeft hleft)
      · exact Or.inl (ihRight hright)
  | select selected selector ihSelected ihSelector =>
      intro source hsource
      simp only [expressionSources, Finset.mem_union] at hsource
      simp only [representedSources, evalProvenance, selectProvenance,
        Finset.mem_union]
      rcases hsource with hselected | hselector
      · have hrepresented := ihSelected hselected
        simp only [representedSources, Finset.mem_union] at hrepresented
        rcases hrepresented with hdata | hselection
        · exact Or.inl hdata
        · exact Or.inr (Or.inl hselection)
      · have hrepresented := ihSelector hselector
        simp only [representedSources, Finset.mem_union] at hrepresented
        rcases hrepresented with hdata | hselection
        · exact Or.inr (Or.inr (Or.inl hdata))
        · exact Or.inr (Or.inr (Or.inr hselection))

end CapstanVerification
