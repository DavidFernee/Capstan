/-
  Capstan allocator/GC formal model.

  This module is intentionally a model of target transition semantics. It does not
  yet prove that runtime/capstan_gc.h refines these definitions.
-/

namespace CapstanFormal

/-- Explicit result of checked arithmetic: success returns a value; overflow is fatal. -/
inductive CheckedAddResult where
  | success (value : Nat)
  | fatal
  deriving DecidableEq, Repr

/-- Mathematical model of the C checked-add helper.
    The limit represents SIZE_MAX; inputs are natural-number encodings of size_t values. -/
def checkedAdd (limit a b : Nat) : CheckedAddResult :=
  if a ≤ limit ∧ b ≤ limit - a then .success (a + b) else .fatal

/-- A successful checked addition returns the exact mathematical sum, within limit. -/
theorem checkedAdd_sound (limit a b result : Nat)
    (h : checkedAdd limit a b = .success result) :
    result = a + b ∧ a + b ≤ limit := by
  unfold checkedAdd at h
  by_cases hfit : a ≤ limit ∧ b ≤ limit - a
  · simp [hfit] at h
    constructor <;> omega
  · simp [hfit] at h

/-- Every in-range mathematical sum is accepted by the checked-add model. -/
theorem checkedAdd_complete (limit a b : Nat)
    (h : a + b ≤ limit) :
    checkedAdd limit a b = .success (a + b) := by
  unfold checkedAdd
  have hfit : a ≤ limit ∧ b ≤ limit - a := by omega
  simp [hfit]

/-- The checked-add model accepts exactly the sums representable below limit. -/
theorem checkedAdd_exact (limit a b : Nat) :
    (∃ result, checkedAdd limit a b = .success result) ↔ a + b ≤ limit := by
  constructor
  · rintro ⟨result, h⟩
    exact (checkedAdd_sound limit a b result h).2
  · intro h
    exact ⟨a + b, checkedAdd_complete limit a b h⟩

/-- Overflow takes the terminal fatal outcome; it is not a recoverable return. -/
theorem checkedAdd_overflow_fatal (limit a b : Nat)
    (h : limit < a + b) :
    checkedAdd limit a b = .fatal := by
  unfold checkedAdd
  have hfit : ¬ (a ≤ limit ∧ b ≤ limit - a) := by omega
  simp [hfit]

/-- Whether the OS accepted an advice operation on a retained page. -/
inductive PageBacking where
  | resident
  | released
  deriving DecidableEq, Repr

/-- Minimal accounting state for one page, isolated from large-object accounting. -/
structure PageLedger where
  backing : PageBacking
  heapBytes : Nat
  deriving DecidableEq, Repr

/-- Target release semantics: failed advice is a no-op; successful advice is committed
    exactly once; a previously released page is not charged/decremented again. -/
def releasePage (ledger : PageLedger) (adviceSucceeded : Bool)
    (pageBytes : Nat) : PageLedger :=
  match ledger.backing with
  | .released => ledger
  | .resident =>
      if adviceSucceeded then
        { backing := .released, heapBytes := ledger.heapBytes - pageBytes }
      else ledger

/-- Failed OS advice must not change page state or heap accounting. -/
theorem release_failure_preserves (ledger : PageLedger) (pageBytes : Nat) :
    releasePage ledger false pageBytes = ledger := by
  cases h : ledger.backing <;> simp [releasePage, h]

/-- Successful advice for a resident page changes its state and subtracts exactly
    one page charge, assuming the accounting precondition. -/
theorem release_success_exact (ledger : PageLedger) (pageBytes : Nat)
    (hResident : ledger.backing = .resident)
    (hAccounted : pageBytes ≤ ledger.heapBytes) :
    let after := releasePage ledger true pageBytes
    after.backing = .released ∧ after.heapBytes + pageBytes = ledger.heapBytes := by
  cases h : ledger.backing with
  | resident =>
      simp [releasePage, h]
      omega
  | released =>
      simp [h] at hResident

/-- Release is idempotent: a second release cannot decrement accounting again. -/
theorem release_idempotent (ledger : PageLedger) (pageBytes : Nat) :
    releasePage (releasePage ledger true pageBytes) true pageBytes =
      releasePage ledger true pageBytes := by
  cases h : ledger.backing <;> simp [releasePage, h]

end CapstanFormal
