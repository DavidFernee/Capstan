import CapstanVerification.MultiFrame

namespace CapstanVerification

/-!
First integration layer for the CCAM multi-frame machine.

This module deliberately composes the existing typed return protocol with the
heterogeneous call stack. It does not yet define ordinary instruction dispatch,
function-table validation, calls, output or the complete whole-machine step.
The transition is immutable: failure returns no successor stack; success
returns the resumed caller stack with the result write already committed.
-/

/-- Commit a non-void return and remove the active callee in one abstract
stack transition. The stack is ordered active-frame first. -/
def commitTypedReturnOnStack (stack : TypedMultiCallStack)
    (value : Val) : Except Trap TypedMultiCallStack :=
  match hframes : stack.frames with
  | callee :: caller :: rest =>
      match commitTypedReturnToCaller callee caller value with
      | .error reason => .error reason
      | .ok resumedCaller =>
          .ok {
            frames := resumedCaller :: rest
            maxDepth := stack.maxDepth
            nonempty := by simp
            within_limit := by
              have hdepth : rest.length + 2 ≤ stack.maxDepth := by
                have h := stack.within_limit
                rw [hframes] at h
                simpa using h
              simp
              omega
          }
  | _ => .error .invalidControlFlow

/-- A successful return removes exactly the active callee frame. -/
theorem commitTypedReturnOnStack_decreases_depth
    (stack next : TypedMultiCallStack) (value : Val)
    (hreturn : commitTypedReturnOnStack stack value = .ok next) :
    next.frames.length + 1 = stack.frames.length := by
  unfold commitTypedReturnOnStack at hreturn
  cases hframes : stack.frames with
  | nil =>
      simp [hframes] at hreturn
  | cons callee tail =>
      cases htail : tail with
      | nil =>
          simp [hframes, htail] at hreturn
      | cons caller rest =>
          cases hcommit : commitTypedReturnToCaller callee caller value with
          | error reason =>
              simp [hcommit] at hreturn
          | ok resumedCaller =>
              simp [hcommit] at hreturn
              cases hreturn
              simp

/-- A successful return preserves the configured stack-depth bound exactly. -/
theorem commitTypedReturnOnStack_preserves_depth_limit
    (stack next : TypedMultiCallStack) (value : Val)
    (hreturn : commitTypedReturnOnStack stack value = .ok next) :
    next.maxDepth = stack.maxDepth := by
  unfold commitTypedReturnOnStack at hreturn
  cases hframes : stack.frames with
  | nil =>
      simp [hframes] at hreturn
  | cons callee tail =>
      cases htail : tail with
      | nil =>
          simp [hframes, htail] at hreturn
      | cons caller rest =>
          cases hcommit : commitTypedReturnToCaller callee caller value with
          | error reason =>
              simp [hcommit] at hreturn
          | ok resumedCaller =>
              simp [hcommit] at hreturn
              cases hreturn
              rfl


/-- Commit a void return and remove the active callee in one abstract stack
transition. A void callee must have no caller destination. The entry frame is
not removed here; entry termination is a separate machine outcome. -/
def commitTypedVoidReturnOnStack (stack : TypedMultiCallStack) :
    Except Trap TypedMultiCallStack :=
  match hframes : stack.frames with
  | callee :: caller :: rest =>
      match commitTypedVoidReturnToCaller callee caller with
      | .error reason => .error reason
      | .ok resumedCaller =>
          .ok {
            frames := resumedCaller :: rest
            maxDepth := stack.maxDepth
            nonempty := by simp
            within_limit := by
              have hdepth : rest.length + 2 ≤ stack.maxDepth := by
                have h := stack.within_limit
                rw [hframes] at h
                simpa using h
              simp
              omega
          }
  | _ => .error .invalidControlFlow

/-- A successful void return removes exactly one active callee frame. -/
theorem commitTypedVoidReturnOnStack_decreases_depth
    (stack next : TypedMultiCallStack)
    (hreturn : commitTypedVoidReturnOnStack stack = .ok next) :
    next.frames.length + 1 = stack.frames.length := by
  unfold commitTypedVoidReturnOnStack at hreturn
  cases hframes : stack.frames with
  | nil =>
      simp [hframes] at hreturn
  | cons callee tail =>
      cases htail : tail with
      | nil =>
          simp [hframes, htail] at hreturn
      | cons caller rest =>
          cases hcommit : commitTypedVoidReturnToCaller callee caller with
          | error reason =>
              simp [hframes, htail, hcommit] at hreturn
          | ok resumedCaller =>
              simp [hframes, htail, hcommit] at hreturn
              cases hreturn
              simp

/-- A successful void return preserves the configured maximum stack depth. -/
theorem commitTypedVoidReturnOnStack_preserves_depth_limit
    (stack next : TypedMultiCallStack)
    (hreturn : commitTypedVoidReturnOnStack stack = .ok next) :
    next.maxDepth = stack.maxDepth := by
  unfold commitTypedVoidReturnOnStack at hreturn
  cases hframes : stack.frames with
  | nil =>
      simp [hframes] at hreturn
  | cons callee tail =>
      cases htail : tail with
      | nil =>
          simp [hframes, htail] at hreturn
      | cons caller rest =>
          cases hcommit : commitTypedVoidReturnToCaller callee caller with
          | error reason =>
              simp [hframes, htail, hcommit] at hreturn
          | ok resumedCaller =>
              simp [hframes, htail, hcommit] at hreturn
              cases hreturn
              rfl


/-- Construct the typed argument vector from a caller's register snapshot.
The source-index vector fixes argument order; no caller register is modified
while the values are collected. -/
theorem typedCallArgumentsWellTyped
    {p : Nat} (caller : TypedMultiFrame)
    ({n : Nat} (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (sources : Fin p → Fin caller.registerCount)
    (hsnapshot : ∀ i, caller.registers (sources i) = some (arguments i))
    (hsources :
      ∀ i, caller.signature.registerTypes (sources i) =
        signature.parameterTypes i) :
    ArgumentsWellTyped signature arguments := by
  intro i
  have hstored := caller.registers_well_typed (sources i) (arguments i)
    (hsnapshot i)
  rw [hsources i] at hstored
  exact hstored


/-- Enter a validated typed callee from an immutable caller-register snapshot.
The caller continuation is advanced and saved in the callee frame. The callee
is pushed only when the configured depth admits it. Argument values and the
return destination are statically checked before this transition is called;
the concrete evaluator's step-counter and dynamic trap precedence are outside
this constructor's present scope. -/
def enterTypedCall
    {p n : Nat}
    (caller : TypedMultiFrame) (rest : List TypedMultiFrame)
    (maxDepth : Nat) (hwithin : (caller :: rest).length ≤ maxDepth)
    (calleeFunctionIndex entryPC : Nat)
    (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (sources : Fin p → Fin caller.registerCount)
    (hsnapshot : ∀ i, caller.registers (sources i) = some (arguments i))
    (hsources :
      ∀ i, caller.signature.registerTypes (sources i) =
        signature.parameterTypes i)
    (destination : Option (Fin caller.registerCount))
    (hdestination : ReturnDestinationMatches caller.signature.registerTypes
      signature.returnType destination) :
    Except Trap TypedMultiCallStack :=
  if hdepth : (caller :: rest).length < maxDepth then
    let continuation := caller.pc + 1
    let harguments := typedCallArgumentsWellTyped caller signature
      arguments sources hsnapshot hsources
    let callee := makeTypedMultiFrame calleeFunctionIndex entryPC
      continuation (destination.map Fin.val) signature arguments harguments
    let resumedCaller := { caller with pc := continuation }
    .ok {
      frames := callee :: resumedCaller :: rest
      maxDepth := maxDepth
      nonempty := by simp
      within_limit := by
        have hlength :
            (callee :: resumedCaller :: rest).length =
              (caller :: rest).length + 1 := by simp
        rw [hlength]
        exact Nat.succ_le_of_lt hdepth
    }
  else
    .error .callDepthLimit

/-- A successful typed call increases the heterogeneous stack depth by one. -/
theorem enterTypedCall_increases_depth
    {p n : Nat}
    (caller : TypedMultiFrame) (rest : List TypedMultiFrame)
    (maxDepth : Nat) (hwithin : (caller :: rest).length ≤ maxDepth)
    (calleeFunctionIndex entryPC : Nat)
    (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (sources : Fin p → Fin caller.registerCount)
    (hsnapshot : ∀ i, caller.registers (sources i) = some (arguments i))
    (hsources :
      ∀ i, caller.signature.registerTypes (sources i) =
        signature.parameterTypes i)
    (destination : Option (Fin caller.registerCount))
    (hdestination : ReturnDestinationMatches caller.signature.registerTypes
      signature.returnType destination)
    (next : TypedMultiCallStack)
    (hcall := enterTypedCall caller rest maxDepth hwithin
      calleeFunctionIndex entryPC signature arguments sources hsnapshot
      hsources destination hdestination = .ok next) :
    next.frames.length = (caller :: rest).length + 1 := by
  unfold enterTypedCall at hcall
  by_cases hdepth : (caller :: rest).length < maxDepth
  · simp only [hdepth, ↓reduceDIte] at hcall
    cases hcall
    simp
  · simp [hdepth] at hcall

/-- A successful typed call leaves the caller continuation immediately after
the call site, while storing that same continuation in the active callee. -/
theorem enterTypedCall_preserves_continuation
    {p n : Nat}
    (caller : TypedMultiFrame) (rest : List TypedMultiFrame)
    (maxDepth : Nat) (hwithin : (caller :: rest).length ≤ maxDepth)
    (calleeFunctionIndex entryPC : Nat)
    (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (sources : Fin p → Fin caller.registerCount)
    (hsnapshot : ∀ i, caller.registers (sources i) = some (arguments i))
    (hsources :
      ∀ i, caller.signature.registerTypes (sources i) =
        signature.parameterTypes i)
    (destination : Option (Fin caller.registerCount))
    (hdestination : ReturnDestinationMatches caller.signature.registerTypes
      signature.returnType destination)
    (next : TypedMultiCallStack)
    (hcall := enterTypedCall caller rest maxDepth hwithin
      calleeFunctionIndex entryPC signature arguments sources hsnapshot
      hsources destination hdestination = .ok next) :
    ∃ callee resumedCaller,
      next.frames = callee :: resumedCaller :: rest ∧
      callee.functionIndex = calleeFunctionIndex ∧
      callee.pc = entryPC ∧
      callee.callerContinuation = caller.pc + 1 ∧
      resumedCaller.functionIndex = caller.functionIndex ∧
      resumedCaller.pc = caller.pc + 1 := by
  unfold enterTypedCall at hcall
  by_cases hdepth : (caller :: rest).length < maxDepth
  · simp only [hdepth, ↓reduceDIte] at hcall
    cases hcall
    refine ⟨makeTypedMultiFrame calleeFunctionIndex entryPC (caller.pc + 1)
      (destination.map Fin.val) signature arguments
      (typedCallArgumentsWellTyped caller signature arguments sources
        hsnapshot hsources),
      { caller with pc := caller.pc + 1 }, ?_, ?_, ?_, ?_, ?_, ?_⟩
    · rfl
    · simp [makeTypedMultiFrame]
    · simp [makeTypedMultiFrame]
    · simp [makeTypedMultiFrame]
    · rfl
    · rfl
  · simp [hdepth] at hcall


/-- Observable result of a return instruction in the whole typed stack model.
Nested returns resume a caller; entry returns halt without popping the entry
frame; malformed return contracts become explicit traps. -/
inductive TypedStackReturnOutcome where
  | resume (stack : TypedMultiCallStack)
  | haltValue (value : Val)
  | haltVoid
  | trap (reason : Trap)

/-- Execute a typed value return at the stack boundary. The singleton entry
frame is retained and converted to a terminal value; nested frames use the
atomic caller-write-and-pop transition above. -/
def returnTypedValueOnStack (stack : TypedMultiCallStack)
    (value : Val) : TypedStackReturnOutcome :=
  match hframes : stack.frames with
  | [entry] =>
      match entry.signature.returnType with
      | none => .trap .typeMismatch
      | some expected =>
          if hasTypeB value expected then
            .haltValue value
          else
            .trap .typeMismatch
  | _ :: _ :: _ =>
      match commitTypedReturnOnStack stack value with
      | .error reason => .trap reason
      | .ok resumed => .resume resumed
  | _ => .trap .invalidControlFlow

/-- Execute a typed void return. The singleton entry frame halts in place;
nested void returns restore the caller without writing a destination. -/
def returnTypedVoidOnStack (stack : TypedMultiCallStack) :
    TypedStackReturnOutcome :=
  match stack.frames with
  | [entry] =>
      match entry.signature.returnType with
      | none => .haltVoid
      | some _ => .trap .typeMismatch
  | _ :: _ :: _ =>
      match commitTypedVoidReturnOnStack stack with
      | .error reason => .trap reason
      | .ok resumed => .resume resumed
  | _ => .trap .invalidControlFlow

/-- A value-returning entry function halts with its payload rather than
popping the singleton entry frame. -/
theorem returnTypedValueOnStack_entry_halts_in_place
    (entry : TypedMultiFrame) (resultType : Ty) (value : Val)
    (hreturn : entry.signature.returnType = some resultType)
    (hvalue : hasTypeB value resultType = true) :
    returnTypedValueOnStack
      { frames := [entry], maxDepth := 1, nonempty := by simp,
        within_limit := by simp } value = .haltValue value := by
  simp [returnTypedValueOnStack, hreturn, hvalue]

/-- A void entry function halts without removing its entry frame. -/
theorem returnTypedVoidOnStack_entry_halts_in_place
    (entry : TypedMultiFrame)
    (hreturn : entry.signature.returnType = none) :
    returnTypedVoidOnStack
      { frames := [entry], maxDepth := 1, nonempty := by simp,
        within_limit := by simp } = .haltVoid := by
  simp [returnTypedVoidOnStack, hreturn]

end CapstanVerification
