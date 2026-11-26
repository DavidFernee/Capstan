import Std

/-!
# Source-language type-safety core (TS.1)

A deliberately small, closed expression fragment used to establish the shape of
Capstan's source-language soundness argument. This is a *model*, not yet a
formalisation of the production parser/checker/code generator.

The fragment contains integer and boolean literals and conditionals whose
condition is represented as a boolean literal. It excludes variables, functions,
mutation, collections, qualifiers, grants, IO and machine integer arithmetic.
Those exclusions are explicit; no whole-language theorem is claimed here.
-/

namespace CapstanVerification.SourceCore

inductive Ty where
  | int
  | bool
  deriving DecidableEq, Repr

inductive Expr where
  | intLit (n : Int)
  | boolLit (b : Bool)
  | ifThenElse (condition : Bool) (yes no : Expr)
  deriving Repr

def isValue : Expr → Bool
  | .intLit _ => true
  | .boolLit _ => true
  | .ifThenElse _ _ _ => false

inductive HasType : Expr → Ty → Prop where
  | intLit (n : Int) : HasType (.intLit n) .int
  | boolLit (b : Bool) : HasType (.boolLit b) .bool
  | ifThenElse {condition : Bool} {yes no : Expr} {ty : Ty} :
      HasType yes ty → HasType no ty →
      HasType (.ifThenElse condition yes no) ty

def step : Expr → Option Expr
  | .ifThenElse true yes _ => some yes
  | .ifThenElse false _ no => some no
  | _ => none

/-- Every successful reduction preserves the source type. -/
theorem step_preserves_typing {e e' : Expr} {ty : Ty}
    (ht : HasType e ty) (hs : step e = some e') : HasType e' ty := by
  cases ht with
  | intLit n => simp [step] at hs
  | boolLit b => simp [step] at hs
  | @ifThenElse condition yes no ty ht hf =>
      cases condition <;> simp [step] at hs <;> cases hs <;> assumption

/-- A well-typed closed expression is a value or can take a step. -/
theorem progress {e : Expr} {ty : Ty} (ht : HasType e ty) :
    isValue e = true ∨ ∃ e', step e = some e' := by
  cases ht with
  | intLit n => exact Or.inl rfl
  | boolLit b => exact Or.inl rfl
  | @ifThenElse condition yes no ty ht hf =>
      cases condition
      · exact Or.inr ⟨no, rfl⟩
      · exact Or.inr ⟨yes, rfl⟩

/-- The one-step semantics is deterministic. -/
theorem step_deterministic {e a b : Expr}
    (ha : step e = some a) (hb : step e = some b) : a = b := by
  cases e with
  | intLit n => simp [step] at ha
  | boolLit v => simp [step] at ha
  | ifThenElse condition yes no =>
      cases condition <;> simp [step] at ha hb <;> subst a <;> subst b <;> rfl

end CapstanVerification.SourceCore
