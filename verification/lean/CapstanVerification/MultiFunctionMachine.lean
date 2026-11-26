import CapstanVerification.CallPreflight

namespace CapstanVerification

/-!
A first explicit multi-frame state model for CCAM-M2.

The model connects frame identity, program position, register contents,
callee continuation, call-depth bounds, and instruction accounting. It is
intentionally a control-state model: it does not yet define instruction
lookup, return-value transfer into caller registers, or a refinement theorem
for the Capstan evaluator.
-/

/-- The caller state to resume after a callee returns. -/
structure CallerContinuation where
  callerFunction : Nat
  resumePC : Nat
  destination : Option Nat
  expectedReturn : CallReturnType
  deriving Repr, DecidableEq

/-- One activation record in the abstract multi-function machine. -/
structure CCAMFrame where
  functionIndex : Nat
  pc : Nat
  registers : List (Option Val)
  continuation : Option CallerContinuation
  deriving Repr

/-- The complete control state for the bounded multi-frame fragment. -/
structure MultiFunctionState where
  frames : List CCAMFrame
  stepsUsed : Nat
  stepsLimit : Nat
  maxDepth : Nat
  nonempty : frames ≠ []
  depth_bounded : frames.length ≤ maxDepth
  steps_bounded : stepsUsed ≤ stepsLimit

/-- Construct the entry state with one frame and no caller continuation. -/
def initialMultiFunctionState
    (entry : CCAMFrame) (stepsLimit maxDepth : Nat)
    (hdepth : 1 ≤ maxDepth) :
    MultiFunctionState :=
  { frames := [entry]
    stepsUsed := 0
    stepsLimit := stepsLimit
    maxDepth := maxDepth
    nonempty := by simp
    depth_bounded := by simpa using hdepth
    steps_bounded := Nat.zero_le _ }

/-- Admit a callee frame only after both budgets have room. -/
def pushCalleeFrame
    (state : MultiFunctionState) (callee : CCAMFrame) :
    Except Trap MultiFunctionState :=
  if hsteps : state.stepsUsed < state.stepsLimit then
    if hdepth : state.frames.length < state.maxDepth then
      .ok {
        frames := callee :: state.frames
        stepsUsed := state.stepsUsed + 1
        stepsLimit := state.stepsLimit
        maxDepth := state.maxDepth
        nonempty := by simp
        depth_bounded := by
          simp
          exact Nat.succ_le_of_lt hdepth
        steps_bounded := by
          exact Nat.succ_le_of_lt hsteps
      }
    else
      .error .callDepthLimit
  else
    .error .instructionLimit

/-- A successful call installs the callee as the active frame. -/
theorem pushCalleeFrame_active
    (state next : MultiFunctionState) (callee : CCAMFrame)
    (h : pushCalleeFrame state callee = .ok next) :
    next.frames.head? = some callee := by
  unfold pushCalleeFrame at h
  split at h
  · split at h
    · simp at h
      cases h
      simp
    · simp at h
  · simp at h

/-- A successful call increases stack depth by exactly one. -/
theorem pushCalleeFrame_depth
    (state next : MultiFunctionState) (callee : CCAMFrame)
    (h : pushCalleeFrame state callee = .ok next) :
    next.frames.length = state.frames.length + 1 := by
  unfold pushCalleeFrame at h
  split at h
  · split at h
    · simp at h
      cases h
      simp
    · simp at h
  · simp at h

/-- A successful call consumes exactly one instruction-budget unit. -/
theorem pushCalleeFrame_steps
    (state next : MultiFunctionState) (callee : CCAMFrame)
    (h : pushCalleeFrame state callee = .ok next) :
    next.stepsUsed = state.stepsUsed + 1 := by
  unfold pushCalleeFrame at h
  split at h
  · split at h
    · simp at h
      cases h
      rfl
    · simp at h
  · simp at h

/-- A successful call leaves the previous caller frames as an unchanged suffix. -/
theorem pushCalleeFrame_preserves_caller_suffix
    (state next : MultiFunctionState) (callee : CCAMFrame)
    (h : pushCalleeFrame state callee = .ok next) :
    next.frames.tail = state.frames := by
  unfold pushCalleeFrame at h
  split at h
  · split at h
    · simp at h
      cases h
      rfl
    · simp at h
  · simp at h

/-- A failed call leaves no partially constructed state: it returns only a trap. -/
theorem pushCalleeFrame_failure_is_trap
    (state : MultiFunctionState) (callee : CCAMFrame) (reason : Trap)
    (h : pushCalleeFrame state callee = .error reason) :
    reason = .callDepthLimit ∨ reason = .instructionLimit := by
  unfold pushCalleeFrame at h
  split at h
  · split at h
    · simp at h
    · simp at h
      exact Or.inl h.symm
  · simp at h
    exact Or.inr h.symm

/-- Pop a nested activation and expose both its frame and caller continuation. -/
def popCalleeFrame (state : MultiFunctionState) :
    Except Trap (CCAMFrame × MultiFunctionState) :=
  match state with
  | ⟨callee :: caller :: rest, stepsUsed, stepsLimit, maxDepth,
      _nonempty, depth_bounded, steps_bounded⟩ =>
      .ok (callee, {
        frames := caller :: rest
        stepsUsed := stepsUsed
        stepsLimit := stepsLimit
        maxDepth := maxDepth
        nonempty := by simp
        depth_bounded := by
          have hlen : (caller :: rest).length ≤ (callee :: caller :: rest).length := by
            simp
          exact Nat.le_trans hlen depth_bounded
        steps_bounded := steps_bounded
      })
  | _ => .error .invalidControlFlow

/-- A successful nested return restores the original caller frame at the top. -/
theorem popCalleeFrame_restores_caller
    (state : MultiFunctionState) (callee caller : CCAMFrame)
    (rest : List CCAMFrame) (returned : CCAMFrame × MultiFunctionState)
    (hframes : state.frames = callee :: caller :: rest)
    (h : popCalleeFrame state = .ok returned) :
    returned.2.frames.head? = some caller := by
  cases state with
  | mk frames stepsUsed stepsLimit maxDepth nonempty depth_bounded steps_bounded =>
      cases frames with
      | nil => simp [popCalleeFrame] at h
      | cons first tail =>
          cases tail with
          | nil => simp [popCalleeFrame] at h
          | cons second rest' =>
              have hshape : first = callee ∧ second = caller ∧ rest' = rest := by
                simpa using hframes
              rcases hshape with ⟨rfl, rfl, rfl⟩
              simp [popCalleeFrame] at h
              cases h
              rfl

/-- A successful nested return decreases stack depth by exactly one. -/
theorem popCalleeFrame_decreases_depth
    (state : MultiFunctionState) (callee caller : CCAMFrame)
    (rest : List CCAMFrame) (returned : CCAMFrame × MultiFunctionState)
    (hframes : state.frames = callee :: caller :: rest)
    (h : popCalleeFrame state = .ok returned) :
    returned.2.frames.length + 1 = state.frames.length := by
  cases state with
  | mk frames stepsUsed stepsLimit maxDepth nonempty depth_bounded steps_bounded =>
      cases frames with
      | nil => simp [popCalleeFrame] at h
      | cons first tail =>
          cases tail with
          | nil => simp [popCalleeFrame] at h
          | cons second rest' =>
              have hshape : first = callee ∧ second = caller ∧ rest' = rest := by
                simpa using hframes
              rcases hshape with ⟨rfl, rfl, rfl⟩
              simp [popCalleeFrame] at h
              cases h
              simp

/-- Returning from a nested frame preserves the instruction counters. -/
theorem popCalleeFrame_preserves_steps
    (state : MultiFunctionState) (returned : CCAMFrame × MultiFunctionState)
    (h : popCalleeFrame state = .ok returned) :
    returned.2.stepsUsed = state.stepsUsed := by
  cases state with
  | mk frames stepsUsed stepsLimit maxDepth nonempty depth_bounded steps_bounded =>
      cases frames with
      | nil => simp [popCalleeFrame] at h
      | cons first tail =>
          cases tail with
          | nil => simp [popCalleeFrame] at h
          | cons second rest =>
              simp [popCalleeFrame] at h
              cases h
              rfl


/-- Replace one in-range register, preserving every other list position. -/
def replaceRegister : List (Option Val) → Nat → Val →
    Option (List (Option Val))
  | [], _, _ => none
  | _ :: rest, 0, value => some (some value :: rest)
  | head :: rest, index + 1, value =>
      (replaceRegister rest index value).map (fun updated => head :: updated)

/-- A successful register replacement cannot change the register-file length. -/
theorem replaceRegister_preserves_length
    (registers updated : List (Option Val)) (index : Nat) (value : Val)
    (h : replaceRegister registers index value = some updated) :
    updated.length = registers.length := by
  induction registers generalizing index updated with
  | nil =>
      simp [replaceRegister] at h
  | cons head rest ih =>
      cases index with
      | zero =>
          simp [replaceRegister] at h
          cases h
          rfl
      | succ index =>
          cases hrec : replaceRegister rest index value with
          | none =>
              simp [replaceRegister, hrec] at h
          | some tail =>
              simp [replaceRegister, hrec] at h
              cases h
              simpa [ih tail index hrec]

/-- Checked update of a frame register; an out-of-range destination traps. -/
def updateFrameRegister (frame : CCAMFrame) (index : Nat) (value : Val) :
    Except Trap CCAMFrame :=
  match replaceRegister frame.registers index value with
  | none => .error .invalidRegister
  | some registers => .ok { frame with registers := registers }

/-- Successful frame-register updates preserve the declared register count. -/
theorem updateFrameRegister_preserves_length
    (frame next : CCAMFrame) (index : Nat) (value : Val)
    (h : updateFrameRegister frame index value = .ok next) :
    next.registers.length = frame.registers.length := by
  unfold updateFrameRegister at h
  cases hreplace : replaceRegister frame.registers index value with
  | none =>
      simp [hreplace] at h
  | some registers =>
      simp [hreplace] at h
      cases h
      exact replaceRegister_preserves_length _ _ _ _ hreplace

/-- Successful frame-register updates preserve control-flow identity. -/
theorem updateFrameRegister_preserves_control_fields
    (frame next : CCAMFrame) (index : Nat) (value : Val)
    (h : updateFrameRegister frame index value = .ok next) :
    next.functionIndex = frame.functionIndex ∧ next.pc = frame.pc := by
  unfold updateFrameRegister at h
  cases hreplace : replaceRegister frame.registers index value with
  | none =>
      simp [hreplace] at h
  | some registers =>
      simp [hreplace] at h
      cases h
      exact ⟨rfl, rfl⟩

/-- Validate the callee's result against the caller's saved return contract. -/
def validateFrameReturn (continuation : CallerContinuation)
    (result : Option Val) : Except Trap (Option (Nat × Val)) :=
  match continuation.expectedReturn, result, continuation.destination with
  | none, none, none => .ok none
  | some expected, some value, some destination =>
      if hasTypeB value expected then .ok (some (destination, value))
      else .error .typeMismatch
  | _, _, _ => .error .typeMismatch

/--
Complete a nested return atomically. The continuation must identify the actual
caller; the result shape and runtime value type must match the saved contract;
and a value return must target an existing caller register. The caller PC and
register file are changed only after every check succeeds.
-/
def returnFromCallee (state : MultiFunctionState) (result : Option Val) :
    Except Trap (CCAMFrame × MultiFunctionState) :=
  match state with
  | ⟨callee :: caller :: rest, stepsUsed, stepsLimit, maxDepth,
      _nonempty, depth_bounded, steps_bounded⟩ =>
      match callee.continuation with
      | none => .error .invalidControlFlow
      | some continuation =>
          if continuation.callerFunction != caller.functionIndex then
            .error .invalidControlFlow
          else
            match validateFrameReturn continuation result with
            | .error reason => .error reason
            | .ok none =>
                let resumedCaller := { caller with pc := continuation.resumePC }
                .ok (callee, {
                  frames := resumedCaller :: rest
                  stepsUsed := stepsUsed
                  stepsLimit := stepsLimit
                  maxDepth := maxDepth
                  nonempty := by simp
                  depth_bounded := by
                    have hlen : (resumedCaller :: rest).length ≤
                        (callee :: caller :: rest).length := by simp
                    exact Nat.le_trans hlen depth_bounded
                  steps_bounded := steps_bounded
                })
            | .ok (some (destination, value)) =>
                let resumedCaller := { caller with pc := continuation.resumePC }
                match hupdate : updateFrameRegister resumedCaller destination value with
                | .error reason => .error reason
                | .ok updatedCaller =>
                    .ok (callee, {
                      frames := updatedCaller :: rest
                      stepsUsed := stepsUsed
                      stepsLimit := stepsLimit
                      maxDepth := maxDepth
                      nonempty := by simp
                      depth_bounded := by
                        have hlen := updateFrameRegister_preserves_length
                          resumedCaller updatedCaller destination value hupdate
                        have hcallerLen : resumedCaller.registers.length =
                            caller.registers.length := by rfl
                        have hbound : (updatedCaller :: rest).length ≤
                            (callee :: caller :: rest).length := by
                          simp [hlen, hcallerLen]
                        exact Nat.le_trans hbound depth_bounded
                      steps_bounded := steps_bounded
                    })
  | _ => .error .invalidControlFlow

/-- A successful return restores the continuation's caller and resume PC. -/
theorem returnFromCallee_restores_continuation
    (state : MultiFunctionState) (result : Option Val)
    (callee caller : CCAMFrame) (rest : List CCAMFrame)
    (continuation : CallerContinuation)
    (returned : CCAMFrame × MultiFunctionState)
    (hframes : state.frames = callee :: caller :: rest)
    (hcontinuation : callee.continuation = some continuation)
    (hcaller : continuation.callerFunction = caller.functionIndex)
    (h : returnFromCallee state result = .ok returned) :
    returned.2.frames.head?.map (fun frame => (frame.functionIndex, frame.pc)) =
      some (caller.functionIndex, continuation.resumePC) := by
  cases state with
  | mk frames stepsUsed stepsLimit maxDepth nonempty depth_bounded steps_bounded =>
      cases frames with
      | nil => simp [returnFromCallee] at h
      | cons first tail =>
          cases tail with
          | nil => simp [returnFromCallee] at h
          | cons second rest' =>
              have hshape : first = callee ∧ second = caller ∧ rest' = rest := by
                simpa using hframes
              rcases hshape with ⟨hfirst, hsecond, hrest⟩
              subst first
              subst second
              subst rest'
              simp only [returnFromCallee, hcontinuation, hcaller] at h
              cases hvalid : validateFrameReturn continuation result with
              | error reason =>
                  simp [hvalid] at h
              | ok plan =>
                  cases plan with
                  | none =>
                      simp [hvalid] at h
                      cases h
                      simp
                  | some pair =>
                      rcases pair with ⟨destination, value⟩
                      cases hupdate : updateFrameRegister
                          { caller with pc := continuation.resumePC } destination value with
                      | error reason =>
                          simp [hvalid, hupdate] at h
                      | ok updatedCaller =>
                          simp [hvalid, hupdate] at h
                          cases h
                          have hfields :
                              updatedCaller.functionIndex = caller.functionIndex ∧
                              updatedCaller.pc = continuation.resumePC := by
                            have hpreserved := updateFrameRegister_preserves_control_fields
                              { caller with pc := continuation.resumePC }
                              updatedCaller destination value hupdate
                            exact ⟨hpreserved.1, hpreserved.2⟩
                          rcases hfields with ⟨hfunction, hpc⟩
                          simp [hfunction, hpc]

end CapstanVerification

namespace CapstanVerification

/-! ## Typed activation-record fragment

The control-stack model above deliberately uses list-backed registers. This
parallel fragment makes the static register layout explicit: every activation
record is indexed by its function's register count and type vector, and carries
the intrinsic `WellTyped` invariant. This is the first bridge toward replacing
the untyped control abstraction; heterogeneous function frames still require
an existential package and are not claimed here.
-/

/-- A continuation whose return destination is statically in the caller's file. -/
structure TypedCallerContinuation (n : Nat) (types : RegTypes n) where
  callerFunction : Nat
  resumePC : Nat
  destination : Option (Fin n)
  expectedReturn : CallReturnType

/-- A typed activation record with a proof-carrying register file. -/
structure TypedCCAMFrame (n : Nat) (types : RegTypes n) where
  functionIndex : Nat
  pc : Nat
  registers : Registers n
  registers_well_typed : WellTyped types registers
  continuation : Option (TypedCallerContinuation n types)

/-- A typed register write constructs a frame only with a valid value type. -/
def updateTypedFrameRegister
    {n : Nat} {types : RegTypes n}
    (frame : TypedCCAMFrame n types)
    (index : Fin n) (value : Val)
    (hvalue : hasType value (types index)) :
    TypedCCAMFrame n types :=
  { frame with
    registers := write frame.registers index value
    registers_well_typed :=
      write_preserves_well_typed frame.registers_well_typed index value hvalue }

/-- The destination contains the returned value after a typed update. -/
theorem updateTypedFrameRegister_destination
    {n : Nat} {types : RegTypes n}
    (frame : TypedCCAMFrame n types)
    (index : Fin n) (value : Val)
    (hvalue : hasType value (types index)) :
    (updateTypedFrameRegister frame index value hvalue).registers index = some value := by
  simp [updateTypedFrameRegister, write]

/-- A typed frame update leaves every other register unchanged. -/
theorem updateTypedFrameRegister_other
    {n : Nat} {types : RegTypes n}
    (frame : TypedCCAMFrame n types)
    (index other : Fin n) (value : Val)
    (hneq : other ≠ index)
    (hvalue : hasType value (types index)) :
    (updateTypedFrameRegister frame index value hvalue).registers other =
      frame.registers other := by
  simp [updateTypedFrameRegister, write, hneq]

/-- A typed continuation can accept a value only at its declared return type. -/
def typedReturnDestination
    {n : Nat} {types : RegTypes n}
    (continuation : TypedCallerContinuation n types)
    (value : Val) : Except Trap (Option (Fin n × Val)) :=
  match continuation.expectedReturn, continuation.destination with
  | some expected, some destination =>
      if htype : expected = types destination then
        if hasTypeB value expected then .ok (some (destination, value))
        else .error .typeMismatch
      else .error .typeMismatch
  | none, none => .error .typeMismatch
  | _, _ => .error .typeMismatch

/-- A successful typed return plan carries the proof needed for a safe write. -/
theorem typedReturnDestination_success
    {n : Nat} {types : RegTypes n}
    (continuation : TypedCallerContinuation n types)
    (value : Val) (destination : Fin n)
    (hplan : typedReturnDestination continuation value =
      .ok (some (destination, value))) :
    hasType value (types destination) := by
  unfold typedReturnDestination at hplan
  cases hreturn : continuation.expectedReturn with
  | none =>
      cases hdest : continuation.destination with
      | none => simp [hreturn, hdest] at hplan
      | some actual => simp [hreturn, hdest] at hplan
  | some expected =>
      cases hdest : continuation.destination with
      | none => simp [hreturn, hdest] at hplan
      | some actual =>
          by_cases htype : expected = types actual
          · by_cases hvalue : hasTypeB value expected
            · have hvalue' : hasTypeB value (types actual) = true := by
                simpa [htype] using hvalue
              have hsome : some (actual, value) = some (destination, value) := by
                simpa [hreturn, hdest, htype, hvalue'] using hplan
              have hpair : (actual, value) = (destination, value) :=
                Option.some.inj hsome
              have hactual : actual = destination := congrArg Prod.fst hpair
              subst destination
              simpa [hasType] using hvalue'
            · have hvalue' : ¬ hasTypeB value (types actual) = true := by
                simpa [htype] using hvalue
              simp [hreturn, hdest, htype, hvalue'] at hplan
          · simp [hreturn, hdest, htype] at hplan


/-! ## Heterogeneous typed frame stacks

A program's functions need not share a register count or type vector. The
existential package below therefore stores each frame together with its own
layout, without erasing the per-frame typing proof. This is the representation
needed for a heterogeneous stack; call-site signature matching and transition
simulation remain separate obligations.
-/

/-- A frame packaged with its own register arity and type vector. -/
abbrev PackedTypedFrame :=
  Sigma (fun n : Nat => Sigma (fun types : RegTypes n =>
    TypedCCAMFrame n types))

/-- The heterogeneous activation stack preserves each frame's dependent type. -/
abbrev TypedFrameStack := List PackedTypedFrame

/-- Push a typed callee without coercing its register layout to the caller's. -/
def pushTypedFrame (frames : TypedFrameStack) (callee : PackedTypedFrame) :
    TypedFrameStack :=
  callee :: frames

/-- The newly pushed heterogeneous frame is active. -/
theorem pushTypedFrame_active
    (frames : TypedFrameStack) (callee : PackedTypedFrame) :
    (pushTypedFrame frames callee).head? = some callee := by
  rfl

/-- Pushing a heterogeneous frame leaves the entire caller stack as its tail. -/
theorem pushTypedFrame_preserves_suffix
    (frames : TypedFrameStack) (callee : PackedTypedFrame) :
    (pushTypedFrame frames callee).tail = frames := by
  rfl

/-- A non-empty typed stack remains non-empty after a callee is pushed. -/
theorem pushTypedFrame_nonempty
    (frames : TypedFrameStack) (callee : PackedTypedFrame) :
    pushTypedFrame frames callee ≠ [] := by
  simp [pushTypedFrame]
