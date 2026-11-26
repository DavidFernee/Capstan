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


-- Conservative provenance algebra for data and control dependencies.
structure Provenance where
  dataCredential : Bool
  controlCredential : Bool
  deriving DecidableEq

def combine (a b : Provenance) : Provenance :=
  ⟨a.dataCredential || b.dataCredential,
   a.controlCredential || b.controlCredential⟩

def select (condition yes no : Provenance) : Provenance :=
  let branches := combine yes no
  ⟨branches.dataCredential,
   condition.dataCredential || condition.controlCredential || branches.controlCredential⟩

def integrityAllowed (p : Provenance) : Bool :=
  !p.dataCredential && !p.controlCredential

theorem combine_rejects_left_credential (a b : Provenance)
    (h : a.dataCredential = true) :
    integrityAllowed (combine a b) = false := by
  simp [integrityAllowed, combine, h]

theorem combine_rejects_right_credential (a b : Provenance)
    (h : b.dataCredential = true) :
    integrityAllowed (combine a b) = false := by
  simp [integrityAllowed, combine, h]

theorem selection_rejects_credential_control (c a b : Provenance)
    (h : c.dataCredential = true) :
    integrityAllowed (select c a b) = false := by
  simp [integrityAllowed, select, h]

theorem selection_rejects_inherited_control (c a b : Provenance)
    (h : c.controlCredential = true) :
    integrityAllowed (select c a b) = false := by
  simp [integrityAllowed, select, h]


-- Conservative call summaries: every argument and the caller's PC contributes.
def callResult (arg summary pc : Provenance) : Provenance :=
  combine (combine arg summary) pc

-- Field projection retains the whole aggregate label (intentionally conservative).
def projectField (aggregate field : Provenance) : Provenance :=
  combine aggregate field

theorem call_preserves_argument (arg summary pc : Provenance)
    (h : arg.dataCredential = true) :
    integrityAllowed (callResult arg summary pc) = false := by
  simp [integrityAllowed, callResult, combine, h]

theorem call_preserves_control (arg summary pc : Provenance)
    (h : pc.controlCredential = true) :
    integrityAllowed (callResult arg summary pc) = false := by
  simp [integrityAllowed, callResult, combine, h]

theorem projection_preserves_aggregate (aggregate field : Provenance)
    (h : aggregate.dataCredential = true) :
    integrityAllowed (projectField aggregate field) = false := by
  exact combine_rejects_left_credential aggregate field h

theorem projection_preserves_field (aggregate field : Provenance)
    (h : field.dataCredential = true) :
    integrityAllowed (projectField aggregate field) = false := by
  exact combine_rejects_right_credential aggregate field h


-- Addresses identify storage, not variable names. Aliases use the same address.
def Heap := Nat → Provenance

def writeCell (heap : Heap) (addr : Nat) (value pc : Provenance) : Heap :=
  fun query => if query = addr then combine value pc else heap query

theorem alias_observes_write (heap : Heap) (addr aliasAddr : Nat)
    (value pc : Provenance) (h : aliasAddr = addr) :
    writeCell heap addr value pc aliasAddr = combine value pc := by
  simp [writeCell, h]

theorem unrelated_cell_preserved (heap : Heap) (addr other : Nat)
    (value pc : Provenance) (h : other ≠ addr) :
    writeCell heap addr value pc other = heap other := by
  simp [writeCell, h]

theorem stored_credential_rejects_integrity (heap : Heap) (addr : Nat)
    (value pc : Provenance) (h : value.dataCredential = true) :
    integrityAllowed (writeCell heap addr value pc addr) = false := by
  simp [writeCell]
  exact combine_rejects_left_credential value pc h

theorem stored_control_rejects_integrity (heap : Heap) (addr : Nat)
    (value pc : Provenance) (h : pc.controlCredential = true) :
    integrityAllowed (writeCell heap addr value pc addr) = false := by
  simp [writeCell, integrityAllowed, combine, h]

end CredentialConfinement
