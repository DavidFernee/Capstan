import Std

namespace CapstanVerification

/-!
# Injection provenance: formal model of the current checker fragment

This module intentionally models the current variable-mark analysis in
compiler/checker.cap, rather than the stronger proposed heap/path domain.

It proves transfer facts for the operations the checker currently recognises
and records executable counterexamples for known missing transfers. The
source-to-model correspondence is documented separately and remains a
manual refinement obligation: Lean does not parse or execute checker.cap.
-/

/-- The current checker only marks integer and string locals. -/
inductive FlowLocalKind where
  | int
  | string
  | bool
  | aggregate
  deriving DecidableEq, Repr

def FlowLocalKind.isMarkedScalar : FlowLocalKind → Bool
  | .int => true
  | .string => true
  | .bool => false
  | .aggregate => false

/--
The fragment of expressions recognised by checker.cap's derived function,
plus explicit constructors for important operations it does not currently
propagate. The latter evaluate to false in the checker abstraction.
-/
inductive FlowExpr where
  | literal
  | inputByte
  | local (slot : Nat)
  | neg (value : FlowExpr)
  | bitNot (value : FlowExpr)
  | field (base : FlowExpr)
  | index (base selector : FlowExpr)
  | mapGet (base key : FlowExpr)
  | intToStr (value : FlowExpr)
  | stringConcat (left right : FlowExpr)
  | collectionRead (base : FlowExpr)
  | arithmetic (left right : FlowExpr)
  | wrapping (left right : FlowExpr)
  | comparison (left right : FlowExpr)
  | toText (value : FlowExpr)
  | join (collection separator : FlowExpr)
  | length (value : FlowExpr)
  | mapHas (base key : FlowExpr)
  | mapKeys (base : FlowExpr)
  | mapRemove (base key : FlowExpr)
  | optionalPayload (value : FlowExpr)
  | enumPayload (value : FlowExpr)
  | structConstruct (field : FlowExpr)
  deriving Repr

/-- Variable-name marks used by the current checker flow pass. -/
abbrev FlowMarks := List Nat

def MarksSubset (left right : FlowMarks) : Prop :=
  ∀ slot, slot ∈ left → slot ∈ right

/-- base_marked: recursively reduce a field/index to its root local. -/
def checkerBaseMarked (marks : FlowMarks) : FlowExpr → Bool
  | .local slot => slot ∈ marks
  | .field base => checkerBaseMarked marks base
  | .index base _ => checkerBaseMarked marks base
  | _ => false

/-- Transfer implemented by the current derived checker routine. -/
def checkerDerived (marks : FlowMarks) : FlowExpr → Bool
  | .literal => false
  | .inputByte => true
  | .local slot => slot ∈ marks
  | .neg value => checkerDerived marks value
  | .bitNot value => checkerDerived marks value
  | .field base => checkerBaseMarked marks base
  | .index base selector =>
      checkerBaseMarked marks base || checkerDerived marks selector
  | .mapGet base key => checkerBaseMarked marks base || checkerDerived marks key
  | .intToStr value => checkerDerived marks value
  | .stringConcat left right =>
      checkerDerived marks left || checkerDerived marks right
  | .collectionRead base => checkerBaseMarked marks base
  | .arithmetic left right =>
      checkerDerived marks left || checkerDerived marks right
  | .wrapping left right =>
      checkerDerived marks left || checkerDerived marks right
  | .comparison _ _ => false
  | .toText _ => false
  | .join _ _ => false
  | .length _ => false
  | .mapHas _ _ => false
  | .mapKeys _ => false
  | .mapRemove _ _ => false
  | .optionalPayload _ => false
  | .enumPayload _ => false
  | .structConstruct _ => false


/--
One-step reference dependency contract for the checker expression fragment.
For each operator, the reference contract states which immediate operands
contribute dependency. It is deliberately not a recursive source-language
semantics; recursive composition is covered only where the child expression
is itself in SupportedFlowExpr.
-/
def semanticDerived (marks : FlowMarks) : FlowExpr → Bool
  | .literal => false
  | .inputByte => true
  | .local slot => slot ∈ marks
  | .neg value => checkerDerived marks value
  | .bitNot value => checkerDerived marks value
  | .field base => checkerBaseMarked marks base
  | .index base selector =>
      checkerBaseMarked marks base || checkerDerived marks selector
  | .mapGet base key =>
      checkerBaseMarked marks base || checkerDerived marks key
  | .intToStr value => checkerDerived marks value
  | .stringConcat left right =>
      checkerDerived marks left || checkerDerived marks right
  | .collectionRead base => checkerBaseMarked marks base
  | .arithmetic left right =>
      checkerDerived marks left || checkerDerived marks right
  | .wrapping left right =>
      checkerDerived marks left || checkerDerived marks right
  | .comparison left right =>
      checkerDerived marks left || checkerDerived marks right
  | .toText value => checkerDerived marks value
  | .join collection separator =>
      checkerDerived marks collection || checkerDerived marks separator
  | .length value => checkerDerived marks value
  | .mapHas base key =>
      checkerBaseMarked marks base || checkerDerived marks key
  | .mapKeys base => checkerBaseMarked marks base
  | .mapRemove base key =>
      checkerBaseMarked marks base || checkerDerived marks key
  | .optionalPayload value => checkerDerived marks value
  | .enumPayload value => checkerDerived marks value
  | .structConstruct field => checkerDerived marks field

/-- The expression fragment whose immediate-operand transfer is implemented. -/
inductive SupportedFlowExpr : FlowExpr → Prop where
  | literal : SupportedFlowExpr .literal
  | inputByte : SupportedFlowExpr .inputByte
  | localVar (slot : Nat) : SupportedFlowExpr (.local slot)
  | neg {value : FlowExpr} : SupportedFlowExpr value → SupportedFlowExpr (.neg value)
  | bitNot {value : FlowExpr} : SupportedFlowExpr value → SupportedFlowExpr (.bitNot value)
  | field {base : FlowExpr} : SupportedFlowExpr base → SupportedFlowExpr (.field base)
  | index {base selector : FlowExpr} :
      SupportedFlowExpr base → SupportedFlowExpr selector →
      SupportedFlowExpr (.index base selector)
  | mapGet {base key : FlowExpr} :
      SupportedFlowExpr base → SupportedFlowExpr key →
      SupportedFlowExpr (.mapGet base key)
  | intToStr {value : FlowExpr} :
      SupportedFlowExpr value → SupportedFlowExpr (.intToStr value)
  | stringConcat {left right : FlowExpr} :
      SupportedFlowExpr left → SupportedFlowExpr right →
      SupportedFlowExpr (.stringConcat left right)
  | collectionRead {base : FlowExpr} :
      SupportedFlowExpr base → SupportedFlowExpr (.collectionRead base)
  | arithmetic {left right : FlowExpr} :
      SupportedFlowExpr left → SupportedFlowExpr right →
      SupportedFlowExpr (.arithmetic left right)
  | wrapping {left right : FlowExpr} :
      SupportedFlowExpr left → SupportedFlowExpr right →
      SupportedFlowExpr (.wrapping left right)

/--
The implementation transfer and its one-step contract agree for every
expression in the supported grammar. This is a model theorem; the separate
source-to-model mapping remains manually reviewed.
-/
theorem checkerDerived_agrees_on_supported
    (marks : FlowMarks) {expression : FlowExpr}
    (hsupported : SupportedFlowExpr expression) :
    checkerDerived marks expression = semanticDerived marks expression := by
  cases hsupported <;> rfl


/-- Apply the current parameter-to-return summary to actual arguments. -/
def checkerSummaryReturn (marks : FlowMarks) :
    List (Bool × FlowExpr) → Bool
  | [] => false
  | (depends, actual) :: rest =>
      (depends && checkerDerived marks actual) ||
        checkerSummaryReturn marks rest

/-- Apply the current parameter-to-sink summary to actual arguments. -/
def checkerSummarySink (marks : FlowMarks) :
    List (Bool × FlowExpr) → Bool
  | [] => false
  | (depends, actual) :: rest =>
      (depends && checkerDerived marks actual) ||
        checkerSummarySink marks rest

/-- Call-site transfer corresponding to the current derived() summary branch. -/
def checkerCallDerived (marks : FlowMarks) (returnsDerived : Bool)
    (parameterReturns : List (Bool × FlowExpr)) : Bool :=
  returnsDerived || checkerSummaryReturn marks parameterReturns

/-- The current summary solver seeds only integer parameters. -/
def checkerSummarySeeds (kind : FlowLocalKind) : Bool :=
  kind == .int

/-- A summary return dependency propagates a derived actual argument. -/
theorem summary_return_propagates
    (marks : FlowMarks) (actual : FlowExpr)
    (rest : List (Bool × FlowExpr))
    (hactual : checkerDerived marks actual = true) :
    checkerSummaryReturn marks ((true, actual) :: rest) = true := by
  simp [checkerSummaryReturn, hactual]

/-- A summary sink dependency detects a derived actual argument. -/
theorem summary_sink_propagates
    (marks : FlowMarks) (actual : FlowExpr)
    (rest : List (Bool × FlowExpr))
    (hactual : checkerDerived marks actual = true) :
    checkerSummarySink marks ((true, actual) :: rest) = true := by
  simp [checkerSummarySink, hactual]

/-- The current interprocedural summary phase ignores non-integer parameters. -/
theorem summary_seed_ignores_boolean :
    checkerSummarySeeds .bool = false := rfl

/-- The current interprocedural summary phase seeds integer parameters. -/
theorem summary_seed_includes_integer :
    checkerSummarySeeds .int = true := rfl


/--
The current pass is monotone: it inserts a local mark when a derived value is
assigned to an int/string local, and never removes that mark on reassignment.
-/
def checkerWrite (marks : FlowMarks) (slot : Nat)
    (kind : FlowLocalKind) (value : FlowExpr) : FlowMarks :=
  if kind.isMarkedScalar && checkerDerived marks value then
    slot :: marks
  else
    marks

/-- Existing marks are never removed by the current assignment transfer. -/
theorem checkerWrite_monotone
    (marks : FlowMarks) (slot : Nat) (kind : FlowLocalKind)
    (value : FlowExpr) :
    MarksSubset marks (checkerWrite marks slot kind value) := by
  intro x hx
  by_cases h : kind.isMarkedScalar && checkerDerived marks value
  · simp [checkerWrite, h]
    exact Or.inr hx
  · simp [checkerWrite, h]
    exact hx

/-- A derived integer/string assignment marks the destination local. -/
theorem checkerWrite_marks_derived
    (marks : FlowMarks) (slot : Nat) (kind : FlowLocalKind)
    (value : FlowExpr)
    (hkind : kind.isMarkedScalar = true)
    (hderived : checkerDerived marks value = true) :
    slot ∈ checkerWrite marks slot kind value := by
  simp [checkerWrite, hkind, hderived]

/-- The current implementation does not mark Boolean locals on assignment. -/
theorem checkerWrite_omits_boolean
    (marks : FlowMarks) (slot : Nat) (value : FlowExpr) :
    checkerWrite marks slot .bool value = marks := by
  simp [checkerWrite, FlowLocalKind.isMarkedScalar]

/--
Unlike a value-sensitive environment, the current name-mark set retains a
mark after a local is overwritten with a literal. This is conservative but
can cause false positives.
-/
theorem checkerWrite_retains_old_mark
    (marks : FlowMarks) (slot : Nat)
    (hmarked : slot ∈ marks) :
    slot ∈ checkerWrite marks slot .int .literal := by
  simp [checkerWrite, FlowLocalKind.isMarkedScalar, checkerDerived, hmarked]

/-- A source byte is always recognised as derived. -/
theorem input_byte_is_derived (marks : FlowMarks) :
    checkerDerived marks .inputByte = true := rfl

/-- Arithmetic preserves a derived left operand. -/
theorem arithmetic_preserves_left
    (marks : FlowMarks) (left right : FlowExpr)
    (hleft : checkerDerived marks left = true) :
    checkerDerived marks (.arithmetic left right) = true := by
  simp [checkerDerived, hleft]

/-- Arithmetic preserves a derived right operand. -/
theorem arithmetic_preserves_right
    (marks : FlowMarks) (left right : FlowExpr)
    (hright : checkerDerived marks right = true) :
    checkerDerived marks (.arithmetic left right) = true := by
  simp [checkerDerived, hright]

/-- Concatenation preserves a derived component in the implemented string case. -/
theorem concat_preserves_left
    (marks : FlowMarks) (left right : FlowExpr)
    (hleft : checkerDerived marks left = true) :
    checkerDerived marks (.stringConcat left right) = true := by
  simp [checkerDerived, hleft]

/-- Indexing by a derived selector is recognised as derived. -/
theorem index_preserves_selector
    (marks : FlowMarks) (base selector : FlowExpr)
    (hselector : checkerDerived marks selector = true) :
    checkerDerived marks (.index base selector) = true := by
  simp [checkerDerived, hselector]

/-- A field read from a marked root local is recognised as derived. -/
theorem field_preserves_root_mark
    (marks : FlowMarks) (slot : Nat)
    (hmarked : slot ∈ marks) :
    checkerDerived marks (.field (.local slot)) = true := by
  simp [checkerDerived, checkerBaseMarked, hmarked]

/-- int_to_str preserves a derived integer in the current checker model. -/
theorem int_to_str_preserves
    (marks : FlowMarks) (value : FlowExpr)
    (hderived : checkerDerived marks value = true) :
    checkerDerived marks (.intToStr value) = true := by
  simp [checkerDerived, hderived]

/-- A derived key selecting from a map is recognised by the current rule. -/
theorem map_get_preserves_key
    (marks : FlowMarks) (base key : FlowExpr)
    (hkey : checkerDerived marks key = true) :
    checkerDerived marks (.mapGet base key) = true := by
  simp [checkerDerived, checkerBaseMarked, hkey]

/- The current flow_walk also marks the local introduced by a direct optional
   unwrap when its condition is derived. Stored optional payloads are not
   represented by the local-mark domain. -/
def checkerOptionalBranch (marks : FlowMarks) (slot : Nat)
    (condition : FlowExpr) : FlowMarks :=
  if checkerDerived marks condition then slot :: marks else marks

theorem checkerOptionalBranch_marks_derived_condition
    (marks : FlowMarks) (slot : Nat) (condition : FlowExpr)
    (hcondition : checkerDerived marks condition = true) :
    slot ∈ checkerOptionalBranch marks slot condition := by
  simp [checkerOptionalBranch, hcondition]

/-- Comparison results currently lose provenance: TYPE-08/09 gap witness. -/
theorem comparison_result_not_derived (marks : FlowMarks) :
    semanticDerived marks
      (.comparison .inputByte .literal) = true ∧
    checkerDerived marks (.comparison .inputByte .literal) = false := by simp [semanticDerived, checkerDerived, checkerBaseMarked]

/-- Generic text conversion currently loses provenance: TYPE-05 gap witness. -/
theorem to_text_result_not_derived (marks : FlowMarks) :
    semanticDerived marks (.toText .inputByte) = true ∧
    checkerDerived marks (.toText .inputByte) = false := by simp [semanticDerived, checkerDerived]

/-- Collection-consuming join currently loses provenance: TYPE-06 gap witness. -/
theorem join_result_not_derived (marks : FlowMarks) :
    semanticDerived marks (.join .inputByte .literal) = true ∧
    checkerDerived marks (.join .inputByte .literal) = false := by simp [semanticDerived, checkerDerived]

/-- Length/shape observation currently loses provenance: TYPE-07/15 gap witness. -/
theorem length_result_not_derived (marks : FlowMarks) :
    semanticDerived marks (.length .inputByte) = true ∧
    checkerDerived marks (.length .inputByte) = false := by simp [semanticDerived, checkerDerived]

/-- Map membership currently loses provenance: TYPE-12 gap witness. -/
theorem map_has_result_not_derived (marks : FlowMarks) :
    semanticDerived marks (.mapHas .literal .inputByte) = true ∧
    checkerDerived marks (.mapHas .literal .inputByte) = false := by simp [semanticDerived, checkerDerived]

/-- Map key-set provenance currently has no transfer: TYPE-10 gap witness. -/
theorem map_keys_gap :
    semanticDerived [1] (.mapKeys (.local 1)) = true ∧
    checkerDerived [1] (.mapKeys (.local 1)) = false := by
  simp [semanticDerived, checkerDerived, checkerBaseMarked]

/-- Map removal result provenance currently has no transfer: TYPE-12 gap witness. -/
theorem map_remove_gap (marks : FlowMarks) :
    semanticDerived marks (.mapRemove .literal .inputByte) = true ∧
    checkerDerived marks (.mapRemove .literal .inputByte) = false := by simp [semanticDerived, checkerDerived]

/-- Stored optional payload propagation is absent: TYPE-13 gap witness. -/
theorem optional_payload_not_derived (marks : FlowMarks) :
    semanticDerived marks (.optionalPayload .inputByte) = true ∧
    checkerDerived marks (.optionalPayload .inputByte) = false := by simp [semanticDerived, checkerDerived]

/-- Enum payload propagation is absent: TYPE-17 gap witness. -/
theorem enum_payload_not_derived (marks : FlowMarks) :
    semanticDerived marks (.enumPayload .inputByte) = true ∧
    checkerDerived marks (.enumPayload .inputByte) = false := by simp [semanticDerived, checkerDerived]

/-- Struct constructor field propagation is absent: TYPE-14 gap witness. -/
theorem struct_constructor_not_derived (marks : FlowMarks) :
    semanticDerived marks (.structConstruct .inputByte) = true ∧
    checkerDerived marks (.structConstruct .inputByte) = false := by simp [semanticDerived, checkerDerived]

end CapstanVerification
