import CapstanVerification.MultiFunction

namespace CapstanVerification

/-!
Heterogeneous multi-frame return protocol for the C-free CCAM profile.

This is a typed protocol model for the concrete evaluator's caller/callee
boundary. Each frame may have a different register count and signature. It
proves typed callee construction and atomic, type-preserving caller result
commit. It does not yet model instruction dispatch, function-table lookup,
step accounting, or the complete mutable-list implementation in
verification/ccam_calls.cap.
-/

/-- A frame in a heterogeneous call stack. The signature and register file
are indexed by that frame's own parameter and register counts. The caller
continuation and destination are stored in the callee frame. -/
structure TypedMultiFrame where
  parameterCount : Nat
  registerCount : Nat
  signature : FunctionSignature parameterCount registerCount
  registers : Registers registerCount
  registers_well_typed : WellTyped signature.registerTypes registers
  functionIndex : Nat
  pc : Nat
  callerContinuation : Nat
  callerDestination : Option Nat

/-- Construct a typed frame from arguments already checked against the
callee signature. All non-parameter registers start uninitialised. -/
def makeTypedMultiFrame {p n : Nat}
    (functionIndex entryPC continuation : Nat)
    (destination : Option Nat)
    (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (harguments : ArgumentsWellTyped signature arguments) :
    TypedMultiFrame :=
  let frame := enterTypedFunction signature arguments harguments
  {
    parameterCount := p
    registerCount := n
    signature := signature
    registers := frame.registers
    registers_well_typed := frame.registers_well_typed
    functionIndex := functionIndex
    pc := entryPC
    callerContinuation := continuation
    callerDestination := destination
  }

/-- The callee frame constructor preserves the function identity and entry PC. -/
theorem makeTypedMultiFrame_identity_and_entry {p n : Nat}
    (functionIndex entryPC continuation : Nat)
    (destination : Option Nat)
    (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (harguments : ArgumentsWellTyped signature arguments) :
    let frame := makeTypedMultiFrame functionIndex entryPC continuation
      destination signature arguments harguments
    frame.functionIndex = functionIndex ∧ frame.pc = entryPC := by
  rfl

/-- The heterogeneous frame constructor carries a well-typed register file. -/
theorem makeTypedMultiFrame_registers_well_typed {p n : Nat}
    (functionIndex entryPC continuation : Nat)
    (destination : Option Nat)
    (signature : FunctionSignature p n)
    (arguments : Fin p → Val)
    (harguments : ArgumentsWellTyped signature arguments) :
    (makeTypedMultiFrame functionIndex entryPC continuation destination
      signature arguments harguments).registers_well_typed := by
  exact (enterTypedFunction signature arguments harguments).registers_well_typed

/-- A successful caller-result commit changes only the continuation PC and
the designated destination register. Its register invariant is reconstructed
from the callee return contract and the caller's exact destination type. -/
def writeTypedReturn (caller : TypedMultiFrame) (continuation : Nat)
    (destination : Fin caller.registerCount) (resultType : Ty)
    (value : Val) (hvalue : hasType value resultType)
    (hdestination :
      caller.signature.registerTypes destination = resultType) :
    TypedMultiFrame :=
  {
    caller with
    pc := continuation
    registers := write caller.registers destination value
    registers_well_typed := write_preserves_well_typed
      caller.registers_well_typed destination value (by
        simpa [hdestination] using hvalue)
  }

/-- A non-void callee return is committed only when the returned value matches
the callee signature, the caller destination exists, and its declared type
matches exactly. Every rejection happens before a caller frame is returned. -/
def commitTypedReturnToCaller (callee caller : TypedMultiFrame)
    (value : Val) : Except Trap TypedMultiFrame :=
  match callee.signature.returnType with
  | none => .error .typeMismatch
  | some resultType =>
      if hvalue : hasType value resultType then
        match callee.callerDestination with
        | none => .error .invalidControlFlow
        | some rawDestination =>
            if hbound : rawDestination < caller.registerCount then
              let destination : Fin caller.registerCount :=
                ⟨rawDestination, hbound⟩
              if hdestination :
                  caller.signature.registerTypes destination = resultType then
                .ok (writeTypedReturn caller callee.callerContinuation
                  destination resultType value hvalue hdestination)
              else
                .error .typeMismatch
            else
              .error .invalidRegister
      else
        .error .typeMismatch

/-- Any successful non-void return commit preserves the caller's register
typing invariant, even when caller and callee have different register widths. -/
theorem commitTypedReturnToCaller_preserves_well_typed
    (callee caller : TypedMultiFrame) (value : Val)
    (next : TypedMultiFrame)
    (hcommit : commitTypedReturnToCaller callee caller value = .ok next) :
    next.registers_well_typed := by
  unfold commitTypedReturnToCaller at hcommit
  cases hreturn : callee.signature.returnType with
  | none =>
      simp [hreturn] at hcommit
  | some resultType =>
      simp only [hreturn] at hcommit
      by_cases hvalue : hasType value resultType
      · simp only [dif_pos hvalue] at hcommit
        cases hdestination : callee.callerDestination with
        | none =>
            simp [hdestination] at hcommit
        | some rawDestination =>
            simp only [hdestination] at hcommit
            by_cases hbound : rawDestination < caller.registerCount
            · simp only [dif_pos hbound] at hcommit
              let destination : Fin caller.registerCount :=
                ⟨rawDestination, hbound⟩
              by_cases hdestinationType :
                  caller.signature.registerTypes destination = resultType
              · simp only [dif_pos hdestinationType] at hcommit
                cases hcommit
                exact (writeTypedReturn caller callee.callerContinuation
                  destination resultType value hvalue hdestinationType).registers_well_typed
              · simp [hdestinationType] at hcommit
            · simp [hbound] at hcommit
      · simp [hvalue] at hcommit

/-- A void return restores the caller continuation but never writes a value.
A value-returning callee or a void call carrying a destination is rejected. -/
def commitTypedVoidReturnToCaller (callee caller : TypedMultiFrame) :
    Except Trap TypedMultiFrame :=
  match callee.signature.returnType with
  | some _ => .error .typeMismatch
  | none =>
      match callee.callerDestination with
      | some _ => .error .invalidControlFlow
      | none => .ok { caller with pc := callee.callerContinuation }

/-- A successful void return preserves the caller's register invariant. -/
theorem commitTypedVoidReturnToCaller_preserves_well_typed
    (callee caller next : TypedMultiFrame)
    (hcommit : commitTypedVoidReturnToCaller callee caller = .ok next) :
    next.registers_well_typed := by
  cases hreturn : callee.signature.returnType with
  | some resultType =>
      simp [commitTypedVoidReturnToCaller, hreturn] at hcommit
  | none =>
      cases hdestination : callee.callerDestination with
      | some rawDestination =>
          simp [commitTypedVoidReturnToCaller, hreturn, hdestination] at hcommit
      | none =>
          simp [commitTypedVoidReturnToCaller, hreturn, hdestination] at hcommit
          cases hcommit
          exact caller.registers_well_typed

/-- A typed multi-frame stack may contain frames with distinct register
layouts; every stored frame is intrinsically well-typed by construction. -/
abbrev TypedMultiCallStack := CallStack TypedMultiFrame

/-- Push a fully constructed callee frame, refusing the push at max depth. -/
def pushTypedMultiFrame (stack : TypedMultiCallStack)
    (callee : TypedMultiFrame) : Except Trap TypedMultiCallStack :=
  pushCallFrame stack callee

/-- A successful typed frame push makes the requested callee active. -/
theorem pushTypedMultiFrame_active
    (stack next : TypedMultiCallStack) (callee : TypedMultiFrame)
    (hpush : pushTypedMultiFrame stack callee = .ok next) :
    (next.frames.head?).map (fun frame => frame.functionIndex) =
      some callee.functionIndex := by
  have htop := pushCallFrame_top stack callee next hpush
  simpa using congrArg (Option.map (fun frame => frame.functionIndex)) htop

/-- A successful typed frame push increases depth by exactly one. -/
theorem pushTypedMultiFrame_depth
    (stack next : TypedMultiCallStack) (callee : TypedMultiFrame)
    (hpush : pushTypedMultiFrame stack callee = .ok next) :
    next.frames.length = stack.frames.length + 1 :=
  pushCallFrame_increments_depth stack callee next hpush

/-- A typed frame stack still refuses a push at its configured depth bound. -/
theorem pushTypedMultiFrame_exhausted
    (stack : TypedMultiCallStack) (callee : TypedMultiFrame)
    (hfull : stack.maxDepth ≤ stack.frames.length) :
    pushTypedMultiFrame stack callee = .error .callDepthLimit :=
  pushCallFrame_exhausted_traps stack callee hfull

end CapstanVerification
