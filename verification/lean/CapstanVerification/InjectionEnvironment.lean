import CapstanVerification.InjectionSinks

namespace CapstanVerification

/-!
# Local environments and assignment for provenance analysis

This fragment formalises scalar local storage and strong updates. It shows
that provenance is a property of the current value, not the variable name:
reassignment replaces the old local fact, while other local slots are
unchanged. Heap locations and aliases remain a separate obligation.
-/

abbrev LocalSlot := Nat
abbrev LocalEnvironment := LocalSlot → ProvenanceValue

/-- A strong update to one scalar local binding. -/
def writeLocal (environment : LocalEnvironment)
    (slot : LocalSlot) (value : ProvenanceValue) : LocalEnvironment :=
  fun other => if other = slot then value else environment other

/-- Reading the slot just written returns exactly the new abstract value. -/
theorem readLocal_after_write
    (environment : LocalEnvironment) (slot : LocalSlot)
    (value : ProvenanceValue) :
    writeLocal environment slot value slot = value := by
  simp [writeLocal]

/-- A strong local update leaves every different slot unchanged. -/
theorem readLocal_other_after_write
    (environment : LocalEnvironment) (slot other : LocalSlot)
    (value : ProvenanceValue) (hne : other ≠ slot) :
    writeLocal environment slot value other = environment other := by
  simp [writeLocal, hne]

/-- Expressions with local reads, source inputs and explicit selection. -/
inductive FlowExpr where
  | literal
  | input (source : SourceId)
  | local (slot : LocalSlot)
  | combine (left right : FlowExpr)
  | select (selected selector : FlowExpr)
  deriving Repr

/-- Evaluate a flow expression in the current provenance environment. -/
def evalFlowExpr (environment : LocalEnvironment) : FlowExpr → ProvenanceValue
  | .literal => emptyProvenanceValue
  | .input source => inputProvenanceValue source
  | .local slot => environment slot
  | .combine left right =>
      combineProvenance (evalFlowExpr environment left)
        (evalFlowExpr environment right)
  | .select selected selector =>
      selectProvenance (evalFlowExpr environment selected)
        (evalFlowExpr environment selector)

/-- The minimal statement language needed to state local assignment semantics. -/
inductive FlowStmt where
  | assign (slot : LocalSlot) (value : FlowExpr)
  | sequence (first second : FlowStmt)
  deriving Repr

/-- Big-step abstract execution for assignments and sequencing. -/
def execFlowStmt (environment : LocalEnvironment) : FlowStmt → LocalEnvironment
  | .assign slot value =>
      writeLocal environment slot (evalFlowExpr environment value)
  | .sequence first second =>
      execFlowStmt (execFlowStmt environment first) second

/-- Assignment stores the abstract value evaluated in the pre-state. -/
theorem assignment_readback
    (environment : LocalEnvironment) (slot : LocalSlot)
    (expression : FlowExpr) :
    execFlowStmt environment (.assign slot expression) slot =
      evalFlowExpr environment expression := by
  simp [execFlowStmt, writeLocal]

/-- Reassignment is a strong update, not permanent tainting of a variable name. -/
theorem reassignment_replaces_prior_provenance
    (environment : LocalEnvironment) (slot : LocalSlot) :
    execFlowStmt environment (.assign slot (.literal)) slot =
      emptyProvenanceValue := by
  simp [execFlowStmt, evalFlowExpr, writeLocal, emptyProvenanceValue]

/-- Assignment to one local preserves every other local's abstract value. -/
theorem assignment_preserves_other_locals
    (environment : LocalEnvironment) (slot other : LocalSlot)
    (expression : FlowExpr) (hne : other ≠ slot) :
    execFlowStmt environment (.assign slot expression) other =
      environment other := by
  simp [execFlowStmt, writeLocal, hne]

/-- Reading a local expression returns the value currently stored in that slot. -/
theorem eval_local_is_environment_lookup
    (environment : LocalEnvironment) (slot : LocalSlot) :
    evalFlowExpr environment (.local slot) = environment slot := by
  rfl

/-- A source stored in a local survives a later read of that local. -/
theorem local_input_provenance_survives_assignment
    (environment : LocalEnvironment) (slot : LocalSlot)
    (source : SourceId) :
    (execFlowStmt environment (.assign slot (.input source)) slot).dataSources =
      {source} := by
  simp [execFlowStmt, evalFlowExpr, writeLocal, inputProvenanceValue]

end CapstanVerification
