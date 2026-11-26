import Std

namespace CapstanVerification

/-!
A bounded representation for normative CCAM application-defined explicit-trap
reasons. This is a policy/data-model increment only. It does not yet prove
that the concrete Capstan validator/evaluator constructs this representation.
-/

def explicitReasonFirstByte (b : Nat) : Bool :=
  97 ≤ b && b ≤ 122

def explicitReasonTailByte (b : Nat) : Bool :=
  explicitReasonFirstByte b || (48 ≤ b && b ≤ 57) || b == 95

/-- Exact normative ASCII token grammar: [a-z][a-z0-9_]{0,63}. -/
def validExplicitReasonBytes (bytes : List Nat) : Bool :=
  1 ≤ bytes.length && bytes.length ≤ 64 &&
    match bytes with
    | [] => false
    | first :: rest =>
        explicitReasonFirstByte first && rest.all explicitReasonTailByte

/-- A reason carries its validated byte representation, not a machine Trap tag. -/
structure ExplicitTrapReason where
  bytes : List Nat
  valid : validExplicitReasonBytes bytes = true
  deriving Repr

structure ExplicitTrapRecord where
  code : String
  functionIndex : Nat
  programCounter : Nat
  detail : List Nat
  stepsUsed : Nat
  deriving DecidableEq, Repr

inductive ExplicitTrapDispatch where
  | explicitTrap (record : ExplicitTrapRecord)
  | instructionLimit (functionIndex programCounter stepsUsed : Nat)
  deriving DecidableEq, Repr

/-- Construct the observable application-trap record without mapping its reason
    onto any built-in machine-trap enumeration. -/
def makeExplicitTrapRecord (functionIndex programCounter stepsUsed : Nat)
    (reason : ExplicitTrapReason) : ExplicitTrapRecord :=
  { code := "explicit_trap"
    functionIndex := functionIndex
    programCounter := programCounter
    detail := reason.bytes
    stepsUsed := stepsUsed }

/-- An explicit trap dispatch consumes one instruction. If the budget is already
    exhausted, dispatch does not occur and the program counter is unchanged. -/
def dispatchExplicitTrap (limit used functionIndex programCounter : Nat)
    (reason : ExplicitTrapReason) : ExplicitTrapDispatch :=
  if used < limit then
    .explicitTrap (makeExplicitTrapRecord functionIndex programCounter
      (used + 1) reason)
  else
    .instructionLimit functionIndex programCounter used

/-- The application-defined detail is preserved byte-for-byte. -/
theorem explicitTrap_preserves_detail
    (functionIndex programCounter stepsUsed : Nat)
    (reason : ExplicitTrapReason) :
    (makeExplicitTrapRecord functionIndex programCounter stepsUsed reason).detail
      = reason.bytes := by
  rfl

/-- Successful explicit-trap dispatch consumes exactly one step. -/
theorem explicitTrap_dispatch_consumes_one
    (limit used functionIndex programCounter : Nat)
    (reason : ExplicitTrapReason)
    (h : used < limit) :
    dispatchExplicitTrap limit used functionIndex programCounter reason =
      .explicitTrap (makeExplicitTrapRecord functionIndex programCounter
        (used + 1) reason) := by
  simp [dispatchExplicitTrap, h]

/-- An exhausted budget traps before dispatch and preserves PC and step count. -/
theorem explicitTrap_exhausted_before_dispatch
    (limit used functionIndex programCounter : Nat)
    (reason : ExplicitTrapReason)
    (h : limit ≤ used) :
    dispatchExplicitTrap limit used functionIndex programCounter reason =
      .instructionLimit functionIndex programCounter used := by
  simp [dispatchExplicitTrap, Nat.not_lt.mpr h]

/-! Boundary and malformed-reason vectors for the exact token grammar. -/

example : validExplicitReasonBytes [105] = true := by decide
example : validExplicitReasonBytes
    [105, 110, 116, 101, 103, 101, 114, 95, 111, 118, 101, 114, 102, 108, 111, 119]
    = true := by decide
example : validExplicitReasonBytes
    (97 :: List.replicate 63 95) = true := by decide
example : validExplicitReasonBytes [] = false := by decide
example : validExplicitReasonBytes [65] = false := by decide
example : validExplicitReasonBytes [97, 45, 98] = false := by decide
example : validExplicitReasonBytes [97, 95, 66] = false := by decide
example : validExplicitReasonBytes (97 :: List.replicate 64 98) = false := by decide
example : validExplicitReasonBytes [97, 128] = false := by decide

end CapstanVerification
