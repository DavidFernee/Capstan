namespace CredentialVerifierPolicy

structure Policy where
  algorithm : Nat
  minCost : Nat
  maxCost : Nat
  minSaltBytes : Nat
  maxSaltBytes : Nat
  digestBytes : Nat

structure Header where
  algorithm : Nat
  cost : Nat
  saltBytes : Nat
  digestBytes : Nat

def Accepts (p : Policy) (h : Header) : Prop :=
  h.algorithm = p.algorithm ∧
  p.minCost ≤ h.cost ∧ h.cost ≤ p.maxCost ∧
  p.minSaltBytes ≤ h.saltBytes ∧ h.saltBytes ≤ p.maxSaltBytes ∧
  h.digestBytes = p.digestBytes

theorem rejects_weak_cost (p : Policy) (h : Header)
    (weak : h.cost < p.minCost) : ¬ Accepts p h := by
  intro accepted
  exact (Nat.not_lt_of_ge accepted.2.1) weak

theorem rejects_excessive_cost (p : Policy) (h : Header)
    (large : p.maxCost < h.cost) : ¬ Accepts p h := by
  intro accepted
  exact (Nat.not_lt_of_ge accepted.2.2.1) large

theorem rejects_other_algorithm (p : Policy) (h : Header)
    (wrong : h.algorithm ≠ p.algorithm) : ¬ Accepts p h := by
  intro accepted
  exact wrong accepted.1

theorem rejects_short_salt (p : Policy) (h : Header)
    (short : h.saltBytes < p.minSaltBytes) : ¬ Accepts p h := by
  intro accepted
  exact (Nat.not_lt_of_ge accepted.2.2.2.1) short

theorem rejects_wrong_digest (p : Policy) (h : Header)
    (wrong : h.digestBytes ≠ p.digestBytes) : ¬ Accepts p h := by
  intro accepted
  exact wrong accepted.2.2.2.2.2


theorem rejects_excessive_salt (p : Policy) (h : Header)
    (large : p.maxSaltBytes < h.saltBytes) : ¬ Accepts p h := by
  intro accepted
  exact (Nat.not_lt_of_ge accepted.2.2.2.2.1) large

theorem rejects_inconsistent_cost_policy (p : Policy) (h : Header)
    (bad : p.maxCost < p.minCost) : ¬ Accepts p h := by
  intro accepted
  exact (Nat.not_lt_of_ge (Nat.le_trans accepted.2.1 accepted.2.2.1)) bad

theorem rejects_inconsistent_salt_policy (p : Policy) (h : Header)
    (bad : p.maxSaltBytes < p.minSaltBytes) : ¬ Accepts p h := by
  intro accepted
  exact (Nat.not_lt_of_ge (Nat.le_trans accepted.2.2.2.1 accepted.2.2.2.2.1)) bad

theorem accepts_policy_boundary (p : Policy)
    (costOK : p.minCost ≤ p.maxCost)
    (saltOK : p.minSaltBytes ≤ p.maxSaltBytes) :
    Accepts p ⟨p.algorithm, p.minCost, p.minSaltBytes, p.digestBytes⟩ := by
  exact ⟨rfl, Nat.le_refl _, costOK, Nat.le_refl _, saltOK, rfl⟩

end CredentialVerifierPolicy
