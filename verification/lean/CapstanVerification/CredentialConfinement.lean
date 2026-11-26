namespace CredentialConfinement

inductive Kind where
  | password | verifier | integrity | digest
  deriving DecidableEq

inductive Expr : Kind → Type where
  | ingress : Expr .password
  | artifact : Expr .integrity
  | kdf : Expr .password → Expr .verifier
  | decodeVerifier : Expr .verifier
  | fastHash : Expr .integrity → Expr .digest
  | alias {k : Kind} : Expr k → Expr k

def credentialOrigin : {k : Kind} → Expr k → Bool
  | _, .ingress => true
  | _, .artifact => false
  | _, .kdf _ => true
  | _, .decodeVerifier => true
  | _, .fastHash x => credentialOrigin x
  | _, .alias x => credentialOrigin x

theorem integrity_excludes_credentials (e : Expr .integrity) :
    credentialOrigin e = false := by
  induction e with
  | artifact => rfl
  | alias _ ih => exact ih

theorem fast_hash_excludes_credentials (e : Expr .integrity) :
    credentialOrigin (.fastHash e) = false :=
  integrity_excludes_credentials e

inductive StorageEvent where
  | persist : Expr .verifier → StorageEvent

theorem storage_has_verifier (s : StorageEvent) :
    ∃ v : Expr .verifier, s = .persist v := by
  cases s with
  | persist v => exact ⟨v, rfl⟩

end CredentialConfinement
