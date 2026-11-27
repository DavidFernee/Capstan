import CapstanVerification.IntegratedMachine

namespace CapstanVerification

/-!
Ordered dynamic call-argument reads for the integrated CCAM call machine.

The concrete evaluator charges the CALL instruction before call-site lookup,
then snapshots argument registers from left to right. A read/type failure
terminates the call before depth checking, callee-frame construction, caller-PC
advance, or stack push. This module formalises the argument-read subtransition
only; it does not yet model call-site lookup or the whole mutable evaluator.
-/

/-- One argument read pairs the callee's expected parameter type with the
caller's source register. The list order is the normative read order. -/
abbrev CallArgumentRequest (n : Nat) := Ty × Fin n

/-- The ordered values produced by successful call-argument reads. -/
inductive CallArgumentValuesWellTyped {n : Nat} :
    List (CallArgumentRequest n) → List Val → Prop where
  | nil : CallArgumentValuesWellTyped [] []
  | cons {ty : Ty} {source : Fin n}
      {requests : List (CallArgumentRequest n)}
      {value : Val} {values : List Val} :
      hasTypeB value ty = true →
      CallArgumentValuesWellTyped requests values →
      CallArgumentValuesWellTyped ((ty, source) :: requests) (value :: values)

/-- Read all call arguments in source order. The first failed read or type
check is returned; later arguments are not observed after that failure. -/
def readCallArguments {n : Nat} (registers : Registers n) :
    List (CallArgumentRequest n) → Except Trap (List Val)
  | [] => .ok []
  | (expected, source) :: rest =>
      match readValue registers source with
      | .error reason => .error reason
      | .ok value =>
          if hasTypeB value expected then
            match readCallArguments registers rest with
            | .error reason => .error reason
            | .ok values => .ok (value :: values)
          else
            .error .typeMismatch

/-- A failure reading the first argument takes precedence over every later
argument, regardless of the later requests. -/
theorem readCallArguments_first_read_error
    {n : Nat} (registers : Registers n)
    (expected : Ty) (source : Fin n)
    (rest : List (CallArgumentRequest n)) (reason : Trap)
    (hread : readValue registers source = .error reason) :
    readCallArguments registers ((expected, source) :: rest) =
      .error reason := by
  simp [readCallArguments, hread]

/-- A type mismatch on the first successfully read argument takes precedence
over any failure in the remaining argument list. -/
theorem readCallArguments_first_type_error
    {n : Nat} (registers : Registers n)
    (expected : Ty) (source : Fin n)
    (rest : List (CallArgumentRequest n))
    (value : Val)
    (hread : readValue registers source = .ok value)
    (hwrong : hasTypeB value expected = false) :
    readCallArguments registers ((expected, source) :: rest) =
      .error .typeMismatch := by
  simp [readCallArguments, hread, hwrong]

/-- The first argument's read error is observable even when a later argument
would also fail. This makes left-to-right trap precedence explicit. -/
theorem readCallArguments_masks_later_failure
    {n : Nat} (registers : Registers n)
    (expected : Ty) (source : Fin n)
    (rest : List (CallArgumentRequest n))
    (reason laterReason : Trap)
    (hread : readValue registers source = .error reason)
    (_hlater : readCallArguments registers rest = .error laterReason) :
    readCallArguments registers ((expected, source) :: rest) =
      .error reason := by
  exact readCallArguments_first_read_error registers expected source rest
    reason hread

/-- If every requested argument is read successfully, the returned list has
the same order and each value satisfies its callee parameter type. -/
theorem readCallArguments_success_well_typed
    {n : Nat} (registers : Registers n)
    (requests : List (CallArgumentRequest n))
    (values : List Val)
    (hread : readCallArguments registers requests = .ok values) :
    CallArgumentValuesWellTyped requests values := by
  induction requests generalizing values with
  | nil =>
      simp [readCallArguments] at hread
      cases hread
      exact .nil
  | cons request rest ih =>
      rcases request with ⟨expected, source⟩
      simp only [readCallArguments] at hread
      cases hsource : readValue registers source with
      | error reason =>
          simp [hsource] at hread
      | ok value =>
          by_cases htyped : hasTypeB value expected = true
          · simp only [hsource, htyped, if_pos] at hread
            cases htail : readCallArguments registers rest with
            | error reason =>
                simp [htail] at hread
            | ok tail =>
                simp [htail] at hread
                cases hread
                exact .cons htyped (ih htail)
          · have hfalse : hasTypeB value expected = false := by
              cases hvalue : hasTypeB value expected <;> simp_all
            simp [hsource, hfalse] at hread

/-- Atomic call-argument snapshot: on success it returns the ordered
values together with the unchanged caller register file. On failure there is
no successor register state. -/
def readCallArgumentsAtomic {n : Nat} (registers : Registers n)
    (requests : List (CallArgumentRequest n)) :
    Except Trap (List Val × Registers n) :=
  match readCallArguments registers requests with
  | .error reason => .error reason
  | .ok values => .ok (values, registers)

/-- A successful argument snapshot leaves every caller register unchanged. -/
theorem readCallArgumentsAtomic_preserves_registers
    {n : Nat} (registers next : Registers n)
    (requests : List (CallArgumentRequest n))
    (values : List Val)
    (hsnapshot :
      readCallArgumentsAtomic registers requests = .ok (values, next)) :
    next = registers := by
  unfold readCallArgumentsAtomic at hsnapshot
  cases hread : readCallArguments registers requests with
  | error reason =>
      simp [hread] at hsnapshot
  | ok snapshot =>
      simp [hread] at hsnapshot
      cases hsnapshot
      rfl

/-- A failed argument snapshot has no successor machine/register state. -/
theorem readCallArgumentsAtomic_failure_has_no_successor
    {n : Nat} (registers : Registers n)
    (requests : List (CallArgumentRequest n)) (reason : Trap)
    (hfailure :
      readCallArgumentsAtomic registers requests = .error reason) :
    readCallArguments registers requests = .error reason := by
  unfold readCallArgumentsAtomic at hfailure
  cases hread : readCallArguments registers requests with
  | error actual =>
      simp [hread] at hfailure
      cases hfailure
      exact hread
  | ok values =>
      simp [hread] at hfailure

end CapstanVerification
