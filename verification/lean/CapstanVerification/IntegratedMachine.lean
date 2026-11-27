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

end CapstanVerification
