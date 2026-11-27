namespace CredentialVerifierPolicy

inductive Algorithm where
  | argon2id
  | scrypt
  | pbkdf2Sha256
  deriving DecidableEq

structure Policy where
  algorithm : Algorithm
  minCost : Nat
  maxCost : Nat
  minSaltBytes : Nat
  maxSaltBytes : Nat
  digestBytes : Nat

structure Header where
  algorithm : Algorithm
  cost : Nat
  saltBytes : Nat
  digestBytes : Nat

def Accepts (p : Policy) (h : Header) : Prop :=
  h.algorithm = p.algorithm ∧
  p.minCost ≤ h.cost ∧ h.cost ≤ p.maxCost ∧
  p.minSaltBytes ≤ h.saltBytes ∧ h.saltBytes ≤ p.maxSaltBytes ∧
  h.digestBytes = p.digestBytes

-- These are conservative global policy ceilings/floors for the abstract model.
-- Concrete KDF adapters must separately define the unit and map each algorithm's
-- native parameters into this bounded work-factor contract.
def minAllowedWork : Nat := 1
def maxAllowedWork : Nat := 1000000
def minAllowedSaltBytes : Nat := 16
def maxAllowedSaltBytes : Nat := 64
def minAllowedDigestBytes : Nat := 16
def maxAllowedDigestBytes : Nat := 64

def ValidPolicy (p : Policy) : Prop :=
  minAllowedWork ≤ p.minCost ∧
  p.maxCost ≤ maxAllowedWork ∧
  p.minCost ≤ p.maxCost ∧
  minAllowedSaltBytes ≤ p.minSaltBytes ∧
  p.maxSaltBytes ≤ maxAllowedSaltBytes ∧
  p.minSaltBytes ≤ p.maxSaltBytes ∧
  minAllowedDigestBytes ≤ p.digestBytes ∧
  p.digestBytes ≤ maxAllowedDigestBytes

-- Only this combined predicate represents an acceptable stored verifier.
-- Accepts alone is the structural header match and is deliberately insufficient.
def SecureAccepts (p : Policy) (h : Header) : Prop :=
  ValidPolicy p ∧ Accepts p h

theorem secure_accepts_requires_valid_policy (p : Policy) (h : Header)
    (accepted : SecureAccepts p h) : ValidPolicy p :=
  accepted.1

theorem secure_accepts_has_bounded_work (p : Policy) (h : Header)
    (accepted : SecureAccepts p h) :
    minAllowedWork ≤ p.minCost ∧ p.maxCost ≤ maxAllowedWork := by
  rcases accepted.1 with ⟨workMin, workMax, _, _, _, _, _, _⟩
  exact ⟨workMin, workMax⟩

theorem secure_accepts_has_bounded_salt (p : Policy) (h : Header)
    (accepted : SecureAccepts p h) :
    minAllowedSaltBytes ≤ p.minSaltBytes ∧ p.maxSaltBytes ≤ maxAllowedSaltBytes := by
  rcases accepted.1 with ⟨_, _, _, saltMin, saltMax, _, _, _⟩
  exact ⟨saltMin, saltMax⟩

theorem secure_accepts_has_bounded_digest (p : Policy) (h : Header)
    (accepted : SecureAccepts p h) :
    minAllowedDigestBytes ≤ p.digestBytes ∧ p.digestBytes ≤ maxAllowedDigestBytes := by
  rcases accepted.1 with ⟨_, _, _, _, _, _, digestMin, digestMax⟩
  exact ⟨digestMin, digestMax⟩

theorem secure_accepts_rejects_weak_cost (p : Policy) (h : Header)
    (accepted : SecureAccepts p h) (weak : h.cost < p.minCost) : False := by
  exact (Nat.not_lt_of_ge accepted.2.2.1) weak


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
