import Std

namespace CapstanVerification

/-!
A finite transaction typestate and linear-owner-context model for the first
vertical slice of issue #325.

This specifies the protocol and a linear typing-context invariant. It is not
yet connected to the Capstan parser, type checker, compiler, generated code,
runtime transaction implementation, or CCAM evaluator.
-/

inductive TxPhase where
  | open
  | prepared
  | commitDecided
  | committed
  | aborted
  | released
  deriving DecidableEq, Repr

inductive TxOperation where
  | write
  | prepare
  | decideCommit
  | commit
  | abort
  | release
  | use
  deriving DecidableEq, Repr

/-- Only protocol-preserving operations have a transition. -/
def txTransition : TxPhase → TxOperation → Option TxPhase
  | .open, .write => some .open
  | .open, .prepare => some .prepared
  | .open, .abort => some .aborted
  | .prepared, .decideCommit => some .commitDecided
  | .prepared, .abort => some .aborted
  | .commitDecided, .commit => some .committed
  | .committed, .release => some .released
  | .aborted, .release => some .released
  | _, _ => none

/-- A live typing-context entry: stable resource identity and current typestate. -/
abbrev TxOwner := Nat × TxPhase
abbrev TxContext := List TxOwner

def txOwnerIds (context : TxContext) : List Nat :=
  context.map Prod.fst

/-- No resource identity may occur twice in a well-formed ownership context. -/
def LinearTxContext (context : TxContext) : Prop :=
  (txOwnerIds context).Nodup

/-- Change only the typestate of the uniquely owned resource. -/
def updateTxPhase (context : TxContext) (resource : Nat)
    (next : TxPhase) : TxContext :=
  context.map fun owner =>
    if owner.1 == resource then (owner.1, next) else owner

/--
A transition is admitted only for a well-formed linear context, an existing
owner, and an operation enabled by that owner's current typestate. Invalid
contexts and invalid transitions fail closed.
-/
noncomputable def advanceTxContext (context : TxContext) (resource : Nat)
    (operation : TxOperation) : Option TxContext := by
  classical
  exact
    if LinearTxContext context then
      match context.find? (fun owner => owner.1 == resource) with
      | none => none
      | some owner =>
        match txTransition owner.2 operation with
        | none => none
        | some next => some (updateTxPhase context resource next)
    else
      none

/-- The transition relation preserves the multiset/order of owner identities. -/
theorem txOwnerIds_update_preserved (context : TxContext)
    (resource : Nat) (next : TxPhase) :
    txOwnerIds (updateTxPhase context resource next) = txOwnerIds context := by
  induction context with
  | nil => rfl
  | cons owner rest ih =>
    cases owner with
    | mk id phase =>
      cases hmatch : (id == resource) <;>
        simp [updateTxPhase, txOwnerIds, hmatch, ih]

/-- Updating a resource's phase cannot introduce a second owner. -/
theorem update_preserves_linear_context (context : TxContext)
    (resource : Nat) (next : TxPhase)
    (hlinear : LinearTxContext context) :
    LinearTxContext (updateTxPhase context resource next) := by
  unfold LinearTxContext
  rw [txOwnerIds_update_preserved]
  exact hlinear

/-- Every accepted context transition preserves unique ownership. -/
theorem advance_preserves_linear_context (context next : TxContext)
    (resource : Nat) (operation : TxOperation)
    (hlinear : LinearTxContext context)
    (hstep : advanceTxContext context resource operation = some next) :
    LinearTxContext next := by
  classical
  unfold advanceTxContext at hstep
  simp only [if_pos hlinear] at hstep
  cases hfind : context.find? (fun owner => owner.1 == resource) with
  | none =>
    simp [hfind] at hstep
  | some owner =>
    cases htransition : txTransition owner.2 operation with
    | none =>
      simp [hfind, htransition] at hstep
    | some phase =>
      simp [hfind, htransition] at hstep
      cases hstep
      exact update_preserves_linear_context context resource phase hlinear

/-- A duplicate commit is not a legal transition. -/
theorem duplicate_commit_rejected :
    txTransition .committed .commit = none := by
  rfl

/-- Abort is no longer available after the commit decision. -/
theorem abort_after_commit_decision_rejected :
    txTransition .commitDecided .abort = none := by
  rfl

/-- Writes stop being available once prepare has succeeded. -/
theorem write_after_prepare_rejected :
    txTransition .prepared .write = none := by
  rfl

/-- A released transaction has no further usable operations. -/
theorem use_after_release_rejected :
    txTransition .released .use = none := by
  rfl

/-- A duplicated resource identity is not a well-formed ownership context. -/
theorem duplicate_owner_context_rejected (resource : Nat) :
    ¬ LinearTxContext
      [(resource, TxPhase.open), (resource, TxPhase.open)] := by
  simp [LinearTxContext, txOwnerIds]

/-- Even a legal-looking operation fails closed on a duplicated owner context. -/
theorem aliased_transaction_cannot_advance (resource : Nat) :
    advanceTxContext
      [(resource, TxPhase.open), (resource, TxPhase.open)]
      resource .prepare = none := by
  classical
  simp [advanceTxContext, LinearTxContext, txOwnerIds]

/-- An unknown resource identity cannot be advanced. -/
theorem unknown_transaction_cannot_advance
    (resource missing : Nat) (hDifferent : resource ≠ missing) :
    advanceTxContext [(resource, TxPhase.open)] missing .prepare = none := by
  classical
  simp [advanceTxContext, LinearTxContext, txOwnerIds, hDifferent]

/-- An accepted transition changes the phase but not the owner identity list. -/
theorem advance_preserves_owner_ids (context next : TxContext)
    (resource : Nat) (operation : TxOperation)
    (hstep : advanceTxContext context resource operation = some next) :
    txOwnerIds next = txOwnerIds context := by
  classical
  unfold advanceTxContext at hstep
  by_cases hlinear : LinearTxContext context
  · simp only [if_pos hlinear] at hstep
    cases hfind : context.find? (fun owner => owner.1 == resource) with
    | none => simp [hfind] at hstep
    | some owner =>
      cases htransition : txTransition owner.2 operation with
      | none => simp [hfind, htransition] at hstep
      | some phase =>
        simp [hfind, htransition] at hstep
        cases hstep
        exact txOwnerIds_update_preserved context resource phase
  · simp [hlinear] at hstep

/-- The canonical successful path: write, prepare, decide, commit, release. -/
theorem canonical_commit_path :
    txTransition .open .write = some .open ∧
    txTransition .open .prepare = some .prepared ∧
    txTransition .prepared .decideCommit = some .commitDecided ∧
    txTransition .commitDecided .commit = some .committed ∧
    txTransition .committed .release = some .released := by
  decide

/-- Abort is permitted before the irreversible commit decision. -/
theorem abort_before_commit_decision :
    txTransition .open .abort = some .aborted ∧
    txTransition .prepared .abort = some .aborted := by
  decide

end CapstanVerification
