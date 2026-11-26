import CapstanVerification.InjectionProvenance

namespace CapstanVerification

/-!
# Typed sink contracts for the injection-freedom model

This module makes sink context explicit and expresses encoder correctness as
an obligation carried by a contract. It does not instantiate contracts for
Capstan's runtime encoders or external adapters.
-/

/-- Protected interpretation contexts are deliberately non-interchangeable. -/
inductive InjectionSink where
  | sqlValue
  | sqlIdentifier
  | processArgument
  | htmlText
  | htmlAttribute
  | logText
  | csvField
  | filePath
  | generatedCode
  deriving DecidableEq, Repr

/-- A value carries provenance independently from its context certificates. -/
structure SinkValue where
  provenance : ProvenanceValue
  safeContexts : Finset InjectionSink
  deriving Repr

/-- Raw attacker input starts with provenance and no context certificate. -/
def rawSinkInput (source : SourceId) : SinkValue :=
  { provenance := inputProvenanceValue source, safeContexts := ∅ }

/--
Strict-profile sink admissibility: a value is accepted only if it is
independent of external sources or carries a certificate for this exact sink
context. This is a specification predicate, not yet the production checker's
judgement.
-/
def strictSinkSafe (context : InjectionSink) (value : SinkValue) : Prop :=
  (value.provenance.dataSources = ∅ ∧
    value.provenance.selectionSources = ∅) ∨
    context ∈ value.safeContexts

/-- Raw attacker-controlled input is not admissible at any protected sink. -/
theorem raw_input_rejected_at_sink
    (source : SourceId) (context : InjectionSink) :
    ¬ strictSinkSafe context (rawSinkInput source) := by
  intro hsafe
  rcases hsafe with ⟨hdata, _⟩ | hcontext
  · simp [rawSinkInput, inputProvenanceValue] at hdata
  · simp [rawSinkInput] at hcontext

/--
A context encoder contract must prove both that its output is safe for the
specific context and that it preserves data/selection provenance. This keeps
encoding distinct from declassification.
-/
structure ContextEncoder (context : InjectionSink) where
  encode : SinkValue → SinkValue
  establishes_context :
    ∀ value, context ∈ (encode value).safeContexts
  preserves_data :
    ∀ value, (encode value).provenance.dataSources = value.provenance.dataSources
  preserves_selection :
    ∀ value,
      (encode value).provenance.selectionSources =
        value.provenance.selectionSources

/-- A value produced by a correctly specified context encoder passes that sink. -/
theorem context_encoder_output_is_sink_safe
    (context : InjectionSink) (encoder : ContextEncoder context)
    (value : SinkValue) :
    strictSinkSafe context (encoder.encode value) :=
  Or.inr (encoder.establishes_context value)

/-- Context encoding does not erase direct attacker provenance. -/
theorem context_encoder_preserves_data_provenance
    (context : InjectionSink) (encoder : ContextEncoder context)
    (value : SinkValue) :
    (encoder.encode value).provenance.dataSources =
      value.provenance.dataSources :=
  encoder.preserves_data value

/-- Context encoding does not erase attacker-controlled selection provenance. -/
theorem context_encoder_preserves_selection_provenance
    (context : InjectionSink) (encoder : ContextEncoder context)
    (value : SinkValue) :
    (encoder.encode value).provenance.selectionSources =
      value.provenance.selectionSources :=
  encoder.preserves_selection value

/-- A certificate for one context is not, by itself, a certificate for another. -/
theorem context_certificate_not_transferred
    (first second : InjectionSink) (hneq : first ≠ second)
    (value : SinkValue)
    (hfirst : first ∈ value.safeContexts)
    (hsecond : second ∉ value.safeContexts) :
    ¬ strictSinkSafe second value := by
  intro hsafe
  rcases hsafe with ⟨_, _⟩ | hcontext
  · exact hsecond hcontext
  · exact hsecond hcontext

end CapstanVerification
