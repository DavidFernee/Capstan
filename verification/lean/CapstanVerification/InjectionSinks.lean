import CapstanVerification.InjectionChecker

namespace CapstanVerification

/-!
# Protected sinks for the current laundering checker fragment

This models the four concrete sink shapes recognised by checker.cap's
flow_walk: char_str, text indexing, optional text-map get, and slicing a
trusted (non-Tainted) text receiver with derived selectors.

This is a sink-recognition theorem over the existing abstract FlowExpr model.
It does not prove that the production AST visitor refines this model, nor
that an external sink adapter is safe.
-/

inductive InjectionTextKind where
  | string
  | html
  | log
  | other
  deriving DecidableEq, Repr

def InjectionTextKind.isText : InjectionTextKind → Bool
  | .string => true
  | .html => true
  | .log => true
  | .other => false

inductive ProtectedSink where
  | charString (argument : FlowExpr)
  | textIndex (resultKind : InjectionTextKind) (selector : FlowExpr)
  | optionalTextMapGet (valueKind : InjectionTextKind) (key : FlowExpr)
  | trustedTextSlice (receiverIsTainted : Bool) (selectors : List FlowExpr)
  deriving Repr

/-- Whether the current checker reports a protected reconstruction sink. -/
def checkerRejectsSink (marks : FlowMarks) : ProtectedSink → Bool
  | .charString argument => checkerDerived marks argument
  | .textIndex resultKind selector =>
      resultKind.isText && checkerDerived marks selector
  | .optionalTextMapGet valueKind key =>
      valueKind.isText && checkerDerived marks key
  | .trustedTextSlice receiverIsTainted selectors =>
      !receiverIsTainted && selectors.any (checkerDerived marks)

/-- An accepted sink is one for which the model emits no CWE-20 diagnostic. -/
def checkerAcceptsSink (marks : FlowMarks) (sink : ProtectedSink) : Bool :=
  !checkerRejectsSink marks sink

theorem char_string_derived_is_rejected
    (marks : FlowMarks) (argument : FlowExpr)
    (h : checkerDerived marks argument = true) :
    checkerRejectsSink marks (.charString argument) = true := by
  simp [checkerRejectsSink, h]

theorem text_index_derived_selector_is_rejected
    (marks : FlowMarks) (selector : FlowExpr)
    (h : checkerDerived marks selector = true) :
    checkerRejectsSink marks (.textIndex .string selector) = true := by
  simp [checkerRejectsSink, InjectionTextKind.isText, h]

theorem html_index_derived_selector_is_rejected
    (marks : FlowMarks) (selector : FlowExpr)
    (h : checkerDerived marks selector = true) :
    checkerRejectsSink marks (.textIndex .html selector) = true := by
  simp [checkerRejectsSink, InjectionTextKind.isText, h]

theorem log_index_derived_selector_is_rejected
    (marks : FlowMarks) (selector : FlowExpr)
    (h : checkerDerived marks selector = true) :
    checkerRejectsSink marks (.textIndex .log selector) = true := by
  simp [checkerRejectsSink, InjectionTextKind.isText, h]

theorem optional_text_map_get_derived_key_is_rejected
    (marks : FlowMarks) (key : FlowExpr)
    (h : checkerDerived marks key = true) :
    checkerRejectsSink marks (.optionalTextMapGet .string key) = true := by
  simp [checkerRejectsSink, InjectionTextKind.isText, h]

theorem trusted_slice_derived_selector_is_rejected
    (marks : FlowMarks) (selectors : List FlowExpr) (selector : FlowExpr)
    (hmem : selector ∈ selectors)
    (hderived : checkerDerived marks selector = true) :
    checkerRejectsSink marks (.trustedTextSlice false selectors) = true := by
  simp [checkerRejectsSink, List.any_eq_true]
  exact ⟨selector, hmem, hderived⟩

theorem accepted_char_string_has_no_derived_argument
    (marks : FlowMarks) (argument : FlowExpr)
    (h : checkerAcceptsSink marks (.charString argument) = true) :
    checkerDerived marks argument = false := by
  simp [checkerAcceptsSink, checkerRejectsSink] at h
  cases harg : checkerDerived marks argument <;> simp_all

theorem tainted_receiver_slice_is_not_lookup_sink
    (marks : FlowMarks) (selectors : List FlowExpr) :
    checkerRejectsSink marks (.trustedTextSlice true selectors) = false := by
  simp [checkerRejectsSink]

theorem non_text_index_is_not_lookup_sink
    (marks : FlowMarks) (selector : FlowExpr) :
    checkerRejectsSink marks (.textIndex .other selector) = false := by
  simp [checkerRejectsSink, InjectionTextKind.isText]

theorem non_text_optional_map_get_is_not_lookup_sink
    (marks : FlowMarks) (key : FlowExpr) :
    checkerRejectsSink marks (.optionalTextMapGet .other key) = false := by
  simp [checkerRejectsSink, InjectionTextKind.isText]

end CapstanVerification
