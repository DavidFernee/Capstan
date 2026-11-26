import CapstanVerification.Core

namespace CapstanVerification

/-!
A bounded byte-output transition model for the CCAM v0.2 output extension.

The trace is a sequence of octets, not a Unicode string. The model therefore
preserves NUL and all 256 byte values without decoding or normalisation.
This file proves the abstract append/budget/step properties. The refinement
from the Capstan evaluator and Linux syscall adapter remains a separate proof. The separately emitted Linux x86-64 backend is not covered by these abstract theorems; its conformance tests and a future lowering-refinement proof remain independent obligations.
-/

inductive OutputTrap where
  | outputLimit
  | instructionLimit
  deriving DecidableEq, Repr

/-- A byte trace with a statically recorded output bound. -/
structure ByteTrace where
  bytes : List UInt8
  maxBytes : Nat
  withinLimit : bytes.length ≤ maxBytes

/-- The empty trace is valid for every non-negative output budget. -/
def emptyByteTrace (maxBytes : Nat) : ByteTrace :=
  { bytes := []
    maxBytes := maxBytes
    withinLimit := by simp }

/-- Append an exact byte sequence, rejecting before changing the trace if it will not fit. -/
def appendOutputBytes (trace : ByteTrace) (payload : List UInt8) :
    Except OutputTrap ByteTrace :=
  if hfits : payload.length ≤ trace.maxBytes - trace.bytes.length then
    .ok {
      bytes := trace.bytes ++ payload
      maxBytes := trace.maxBytes
      withinLimit := by
        simp only [List.length_append]
        have htrace := trace.withinLimit
        have hbound := hfits
        omega
    }
  else
    .error .outputLimit

/-- Successful output appends precisely the supplied bytes in order.
    This transition is intentionally byte-level: decoding and source-literal
    canonicalisation are verified at the CCAM frontend boundary instead. -/
theorem appendOutputBytes_exact
    (trace : ByteTrace) (payload : List UInt8) (next : ByteTrace)
    (h : appendOutputBytes trace payload = .ok next) :
    next.bytes = trace.bytes ++ payload := by
  unfold appendOutputBytes at h
  by_cases hfits : payload.length ≤ trace.maxBytes - trace.bytes.length
  · simp [hfits] at h
    cases h
    rfl
  · simp [hfits] at h

/-- An over-budget append traps without producing a modified trace. -/
theorem appendOutputBytes_over_limit
    (trace : ByteTrace) (payload : List UInt8)
    (h : trace.maxBytes - trace.bytes.length < payload.length) :
    appendOutputBytes trace payload = .error .outputLimit := by
  unfold appendOutputBytes
  have hnot : ¬ payload.length ≤ trace.maxBytes - trace.bytes.length := Nat.not_le.mpr h
  simp [hnot]

/-- Output execution state. The byte trace itself carries its budget invariant. -/
structure OutputMachineState where
  trace : ByteTrace
  steps : Nat
  maxSteps : Nat

/-- One output instruction either advances or traps, retaining the post-step state. -/
inductive OutputStepOutcome where
  | advanced (state : OutputMachineState)
  | trapped (reason : OutputTrap) (state : OutputMachineState)

/-- Execute one output instruction. The step is consumed before the output-limit check. -/
def stepEmitBytes (state : OutputMachineState) (payload : List UInt8) :
    OutputStepOutcome :=
  if state.steps < state.maxSteps then
    let consumed := { state with steps := state.steps + 1 }
    match appendOutputBytes state.trace payload with
    | .ok trace => .advanced { consumed with trace := trace }
    | .error reason => .trapped reason consumed
  else
    .trapped .instructionLimit state

/-- Every successful output instruction consumes exactly one step. -/
theorem stepEmitBytes_increments
    (state next : OutputMachineState) (payload : List UInt8)
    (h : stepEmitBytes state payload = .advanced next) :
    next.steps = state.steps + 1 := by
  unfold stepEmitBytes at h
  by_cases hsteps : state.steps < state.maxSteps
  · simp [hsteps] at h
    split at h
    · cases h
      rfl
    · simp at h
  · simp [hsteps] at h

/-- Empty output is still an instruction and consumes exactly one step. -/
theorem stepEmitBytes_empty
    (state : OutputMachineState)
    (hsteps : state.steps < state.maxSteps) :
    stepEmitBytes state [] =
      .advanced { state with steps := state.steps + 1 } := by
  simp [stepEmitBytes, hsteps, appendOutputBytes]

/-- An output-limit trap consumes its instruction step but leaves prior bytes unchanged. -/
theorem stepEmitBytes_output_limit_atomic
    (state : OutputMachineState) (payload : List UInt8)
    (hsteps : state.steps < state.maxSteps)
    (hover : state.trace.maxBytes - state.trace.bytes.length < payload.length) :
    stepEmitBytes state payload =
      .trapped .outputLimit { state with steps := state.steps + 1 } := by
  simp [stepEmitBytes, hsteps, appendOutputBytes,
    Nat.not_le.mpr hover]

/-- Every successful output transition retains a trace within its configured bound. -/
theorem stepEmitBytes_success_within_limit
    (state next : OutputMachineState) (payload : List UInt8)
    (h : stepEmitBytes state payload = .advanced next) :
    next.trace.bytes.length ≤ next.trace.maxBytes := by
  unfold stepEmitBytes at h
  by_cases hsteps : state.steps < state.maxSteps
  · simp [hsteps] at h
    cases htrace : appendOutputBytes state.trace payload with
    | error reason =>
        simp [htrace] at h
    | ok trace =>
        simp [htrace] at h
        cases h
        exact trace.withinLimit
  · simp [hsteps] at h

end CapstanVerification
