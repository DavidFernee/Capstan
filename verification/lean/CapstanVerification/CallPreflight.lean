import CapstanVerification.Core

namespace CapstanVerification

/-!
A first executable multi-function call-preflight model for CCAM-M2.

This module deliberately models the validation phase only. It does not yet
model frames, program counters, return continuations, instruction fuel, or
refinement of the Capstan evaluator. Its purpose is to make call admission
rules explicit before adding state transitions.
-/

/-- The return contract of a function; none denotes a void return. -/
abbrev CallReturnType := Option Ty

/-- The call-site contract required to admit a call. -/
structure CallSignature where
  parameterTypes : List Ty
  returnType : CallReturnType
  deriving Repr

/-- Raw call operands: none represents an uninitialised source register. -/
structure CallRequest where
  arguments : List (Option Val)
  destinationType : CallReturnType
  deriving Repr

/-- Values copied into a callee frame after successful preflight. -/
structure CallPlan where
  arguments : List Val
  returnType : CallReturnType
  deriving Repr

/--
Validate arguments in source order. Arity mismatch is an invalid control-flow
contract; an uninitialised operand traps before later operands are inspected;
a value with the wrong declared type traps as a type mismatch.
-/
def validateCallArguments : List Ty → List (Option Val) → Except Trap (List Val)
  | [], [] => .ok []
  | _ :: _, [] => .error .invalidControlFlow
  | [], _ :: _ => .error .invalidControlFlow
  | expected :: expectedRest, actual :: actualRest =>
      match actual with
      | none => .error .uninitialisedRegister
      | some value =>
          if hasTypeB value expected then
            match validateCallArguments expectedRest actualRest with
            | .error reason => .error reason
            | .ok values => .ok (value :: values)
          else
            .error .typeMismatch

/-- Check that the call-site destination agrees exactly with the callee return. -/
def validateCallDestination
    (returnType destinationType : CallReturnType) : Except Trap Unit :=
  if returnType = destinationType then
    .ok ()
  else
    .error .typeMismatch

/--
Pure call preflight. No caller or machine state is accepted or mutated here:
all fallible checks complete before a future evaluator is permitted to push a
callee frame or write a return destination.
-/
def preflightCall
    (signature : CallSignature) (request : CallRequest) :
    Except Trap CallPlan :=
  match validateCallArguments signature.parameterTypes request.arguments with
  | .error reason => .error reason
  | .ok values =>
      match validateCallDestination signature.returnType request.destinationType with
      | .error reason => .error reason
      | .ok _ =>
          .ok { arguments := values, returnType := signature.returnType }

/-- Successful argument validation preserves the declared arity. -/
theorem validateCallArguments_success_length
    (expected : List Ty) (actual : List (Option Val)) (values : List Val)
    (h : validateCallArguments expected actual = .ok values) :
    values.length = expected.length := by
  induction expected generalizing actual values with
  | nil =>
      cases actual with
      | nil =>
          simp [validateCallArguments] at h
          subst values
          rfl
      | cons arg rest =>
          simp [validateCallArguments] at h
  | cons ty tys ih =>
      cases actual with
      | nil =>
          simp [validateCallArguments] at h
      | cons arg args =>
          cases arg with
          | none =>
              simp [validateCallArguments] at h
          | some value =>
              by_cases htype : hasTypeB value ty
              · cases hrec : validateCallArguments tys args with
                | error reason =>
                    simp [validateCallArguments, htype, hrec] at h
                | ok tail =>
                    simp [validateCallArguments, htype, hrec] at h
                    cases h
                    simp [ih args tail hrec]
              · simp [validateCallArguments, htype] at h

/-- The pure preflight function is deterministic. -/
theorem preflightCall_deterministic
    (signature : CallSignature) (request : CallRequest)
    (left right : CallPlan)
    (hleft : preflightCall signature request = .ok left)
    (hright : preflightCall signature request = .ok right) :
    left = right := by
  have hEq := hleft.symm.trans hright
  injection hEq

/-- Successful destination validation implies exact contract equality. -/
theorem validateCallDestination_success
    (returnType destinationType : CallReturnType)
    (h : validateCallDestination returnType destinationType = .ok ()) :
    returnType = destinationType := by
  unfold validateCallDestination at h
  by_cases heq : returnType = destinationType
  · exact heq
  · simp [heq] at h

/-- A successful preflight preserves the exact return-destination contract. -/
theorem preflightCall_destination
    (signature : CallSignature) (request : CallRequest) (plan : CallPlan)
    (h : preflightCall signature request = .ok plan) :
    signature.returnType = request.destinationType := by
  unfold preflightCall at h
  cases hargs : validateCallArguments signature.parameterTypes request.arguments with
  | error reason =>
      simp [hargs] at h
  | ok values =>
      have hdestOk :
          validateCallDestination signature.returnType request.destinationType = .ok () := by
        cases hdest : validateCallDestination signature.returnType request.destinationType with
        | error reason =>
            simp [hargs, hdest] at h
        | ok result =>
            cases result
            simpa using hdest
      exact validateCallDestination_success _ _ hdestOk

/-- A void callee can only be admitted with no return destination. -/
theorem preflightCall_void_destination
    (signature : CallSignature) (request : CallRequest) (plan : CallPlan)
    (hvoid : signature.returnType = none)
    (h : preflightCall signature request = .ok plan) :
    request.destinationType = none := by
  have heq := preflightCall_destination signature request plan h
  rw [hvoid] at heq
  exact heq.symm

/-- A value-returning callee requires a destination of the exact return type. -/
theorem preflightCall_value_destination
    (signature : CallSignature) (request : CallRequest) (plan : CallPlan)
    (returnTy : Ty)
    (hreturn : signature.returnType = some returnTy)
    (h : preflightCall signature request = .ok plan) :
    request.destinationType = some returnTy := by
  have heq := preflightCall_destination signature request plan h
  rw [hreturn] at heq
  exact heq.symm

end CapstanVerification
