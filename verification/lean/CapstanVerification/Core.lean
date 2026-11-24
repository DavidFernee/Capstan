import Std

namespace CapstanVerification

/-!
A deliberately small proof model of the integer/register fragment of CCAM v0.1.
Normative authority: docs/architecture/CCAM.md on the stacked CCAM branch.
This is not an evaluator and no implementation-refinement theorem is claimed.
-/

def two63 : Nat := 2 ^ 63
def maxI64Nat : Nat := two63 - 1
def minI64 : Int := Int.negSucc maxI64Nat
def maxI64 : Int := Int.ofNat maxI64Nat

/-- Executable signed-64 range check over Lean's two Int constructors. -/
def inI64B : Int → Bool
  | .ofNat n => decide (n ≤ maxI64Nat)
  | .negSucc n => decide (n < two63)

def inI64 (x : Int) : Prop := inI64B x = true

inductive Ty where
  | int
  | bool
  deriving DecidableEq, Repr

inductive Val where
  | int (value : Int)
  | bool (value : Bool)
  deriving Repr

def hasTypeB : Val → Ty → Bool
  | .int n, .int => inI64B n
  | .bool _, .bool => true
  | _, _ => false

def hasType (value : Val) (ty : Ty) : Prop := hasTypeB value ty = true

abbrev RegTypes (n : Nat) := Fin n → Ty
abbrev Registers (n : Nat) := Fin n → Option Val

def WellTyped {n : Nat} (types : RegTypes n) (regs : Registers n) : Prop :=
  ∀ i v, regs i = some v → hasType v (types i)

def write {n : Nat} (regs : Registers n) (index : Fin n) (value : Val) : Registers n :=
  fun j => if j = index then some value else regs j

theorem write_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (hregs : WellTyped types regs)
    (index : Fin n) (value : Val)
    (hvalue : hasType value (types index)) :
    WellTyped types (write regs index value) := by
  intro j v hread
  by_cases hji : j = index
  · subst j
    simp [write] at hread
    cases hread
    exact hvalue
  · have hold : regs j = some v := by
      simpa [write, hji] using hread
    exact hregs j v hold

inductive Trap where
  | integerOverflow
  | divisionByZero
  | uninitialisedRegister
  | invalidRegister
  | typeMismatch
  | invalidControlFlow
  | callDepthLimit
  | instructionLimit
  deriving DecidableEq, Repr

def checkedI64 (x : Int) : Except Trap Int :=
  if inI64B x then .ok x else .error .integerOverflow

def checkedAdd (a b : Int) : Except Trap Int := checkedI64 (a + b)
def checkedSub (a b : Int) : Except Trap Int := checkedI64 (a - b)
def checkedMul (a b : Int) : Except Trap Int := checkedI64 (a * b)

/-- Quotient required by CCAM: integer division truncated toward zero. -/
def truncDiv (a b : Int) : Int :=
  let magnitude : Nat := a.natAbs / b.natAbs
  let q := Int.ofNat magnitude
  if (a < 0 ∧ 0 < b) ∨ (0 < a ∧ b < 0) then -q else q

def checkedDiv (a b : Int) : Except Trap Int :=
  if b = 0 then .error .divisionByZero
  else if a = minI64 ∧ b = -1 then .error .integerOverflow
  else checkedI64 (truncDiv a b)

def checkedRem (a b : Int) : Except Trap Int :=
  if b = 0 then .error .divisionByZero
  else if a = minI64 ∧ b = -1 then .ok 0
  else checkedI64 (a - truncDiv a b * b)


/-- The signed-64 endpoints are accepted by the executable range predicate. -/
theorem minI64_in_range : inI64 minI64 := by
  change inI64B minI64 = true
  decide

theorem maxI64_in_range : inI64 maxI64 := by
  change inI64B maxI64 = true
  decide

/-- The immediately adjacent values outside the signed-64 interval are rejected. -/
theorem below_minI64_out_of_range : ¬ inI64 (Int.negSucc two63) := by
  change ¬ (inI64B (Int.negSucc two63) = true)
  decide

theorem above_maxI64_out_of_range : ¬ inI64 (Int.ofNat two63) := by
  change ¬ (inI64B (Int.ofNat two63) = true)
  decide

/-- A successful range check returns a signed-64 value. -/
theorem checkedI64_sound (x result : Int)
    (h : checkedI64 x = .ok result) : inI64 result := by
  cases hx : inI64B x with
  | false =>
    simp [checkedI64, hx] at h
  | true =>
    have heq : x = result := by
      simpa [checkedI64, hx] using h
    subst result
    simpa [inI64] using hx

theorem checkedAdd_sound (a b result : Int)
    (h : checkedAdd a b = .ok result) : inI64 result := by
  exact checkedI64_sound (a + b) result h



/-- General register read: uninitialised registers produce an explicit trap. -/
def readValue {n : Nat} (regs : Registers n) (index : Fin n) : Except Trap Val :=
  match regs index with
  | none => .error .uninitialisedRegister
  | some value => .ok value

theorem readValue_success_well_typed
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (hregs : WellTyped types regs)
    (index : Fin n) (value : Val)
    (hread : readValue regs index = .ok value) :
    hasType value (types index) := by
  unfold readValue at hread
  cases hreg : regs index with
  | none =>
    simp [hreg] at hread
  | some stored =>
    simp [hreg] at hread
    cases hread
    exact hregs index value hreg

structure MoveInstr (n : Nat) (types : RegTypes n) where
  dst : Fin n
  src : Fin n
  same_type : types dst = types src

/-- Atomic move with an explicit destination-type check. -/
def executeMove {n : Nat} {types : RegTypes n}
    (regs : Registers n) (instr : MoveInstr n types) : Except Trap (Registers n) :=
  match readValue regs instr.src with
  | .error e => .error e
  | .ok value =>
    if hasTypeB value (types instr.dst) then
      .ok (write regs instr.dst value)
    else
      .error .typeMismatch

theorem executeMove_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs next : Registers n}
    (hregs : WellTyped types regs)
    (instr : MoveInstr n types)
    (hstep : executeMove regs instr = .ok next) :
    WellTyped types next := by
  unfold executeMove at hstep
  cases hread : readValue regs instr.src with
  | error e =>
    simp [hread] at hstep
  | ok value =>
    have hsrc : hasType value (types instr.src) :=
      readValue_success_well_typed hregs instr.src value hread
    have hdst : hasType value (types instr.dst) := by
      simpa [instr.same_type] using hsrc
    have hdstB : hasTypeB value (types instr.dst) = true := hdst
    simp [hread, hdstB] at hstep
    cases hstep
    exact write_preserves_well_typed hregs instr.dst value hdst

/-- Dynamic integer-register read: uninitialised and wrong-kind reads trap. -/
def readInt {n : Nat} (regs : Registers n) (index : Fin n) : Except Trap Int :=
  match regs index with
  | none => .error .uninitialisedRegister
  | some (.int value) => .ok value
  | some (.bool _) => .error .typeMismatch


/-- A successful read from a statically integer register yields an in-range integer. -/
theorem readInt_success_in_range
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (hregs : WellTyped types regs)
    (index : Fin n) (hindex : types index = .int)
    (value : Int)
    (hread : readInt regs index = .ok value) :
    inI64 value := by
  unfold readInt at hread
  cases hreg : regs index with
  | none =>
    simp [hreg] at hread
  | some v =>
    cases v with
    | int x =>
      simp [hreg] at hread
      cases hread
      have htyped := hregs index (.int value) hreg
      simpa [hasType, hasTypeB, hindex] using htyped
    | bool b =>
      simp [hreg] at hread

/-- An addition instruction carries its static register-type obligations. -/
structure AddInstr (n : Nat) (types : RegTypes n) where
  dst : Fin n
  lhs : Fin n
  rhs : Fin n
  dst_is_int : types dst = .int
  lhs_is_int : types lhs = .int
  rhs_is_int : types rhs = .int

/-- One atomic CCAM integer-add transition, with left-to-right operand reads. -/
def executeAdd {n : Nat} {types : RegTypes n}
    (regs : Registers n) (instr : AddInstr n types) : Except Trap (Registers n) :=
  match readInt regs instr.lhs, readInt regs instr.rhs with
  | .error e, _ => .error e
  | _, .error e => .error e
  | .ok a, .ok b =>
    match checkedAdd a b with
    | .error e => .error e
    | .ok result => .ok (write regs instr.dst (.int result))


/-- A failed lhs read wins before any rhs-read outcome is considered. -/
theorem executeAdd_left_read_error_precedence
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (instr : AddInstr n types) (e : Trap)
    (hleft : readInt regs instr.lhs = .error e) :
    executeAdd regs instr = .error e := by
  simp [executeAdd, hleft]


/-- Dynamic boolean-register read. -/
def readBool {n : Nat} (regs : Registers n) (index : Fin n) : Except Trap Bool :=
  match regs index with
  | none => .error .uninitialisedRegister
  | some (.bool value) => .ok value
  | some (.int _) => .error .typeMismatch

/-- A branch instruction has a statically boolean condition and in-range targets. -/
structure BranchInstr (n m : Nat) (types : RegTypes n) where
  cond : Fin n
  cond_is_bool : types cond = .bool
  if_true : Fin m
  if_false : Fin m

/-- Branch selection returns one of two Fin-indexed, hence in-range, targets. -/
def executeBranch {n m : Nat} {types : RegTypes n}
    (regs : Registers n) (instr : BranchInstr n m types) : Except Trap (Fin m) :=
  match readBool regs instr.cond with
  | .error e => .error e
  | .ok true => .ok instr.if_true
  | .ok false => .ok instr.if_false

theorem executeBranch_target_is_declared
    {n m : Nat} {types : RegTypes n} {regs : Registers n}
    (instr : BranchInstr n m types) (target : Fin m)
    (hstep : executeBranch regs instr = .ok target) :
    target = instr.if_true ∨ target = instr.if_false := by
  unfold executeBranch at hstep
  cases hread : readBool regs instr.cond with
  | error e =>
    simp [hread] at hstep
  | ok value =>
    cases value with
    | true =>
      simp [hread] at hstep
      exact Or.inl hstep.symm
    | false =>
      simp [hread] at hstep
      exact Or.inr hstep.symm

/-- A successful typed add instruction preserves the register-file invariant. -/
theorem executeAdd_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs next : Registers n}
    (hregs : WellTyped types regs)
    (instr : AddInstr n types)
    (hstep : executeAdd regs instr = .ok next) :
    WellTyped types next := by
  unfold executeAdd at hstep
  cases hleft : readInt regs instr.lhs with
  | error e =>
    simp [hleft] at hstep
  | ok a =>
    cases hright : readInt regs instr.rhs with
    | error e =>
      simp [hleft, hright] at hstep
    | ok b =>
      cases hadd : checkedAdd a b with
      | error e =>
        simp [hleft, hright, hadd] at hstep
      | ok result =>
        simp [hleft, hright, hadd] at hstep
        cases hstep
        have hresult : inI64 result := checkedAdd_sound a b result hadd
        have hvalue : hasType (.int result) (types instr.dst) := by
          simpa [hasType, hasTypeB, instr.dst_is_int, inI64] using hresult
        exact write_preserves_well_typed hregs instr.dst (.int result) hvalue


theorem checkedSub_sound (a b result : Int)
    (h : checkedSub a b = .ok result) : inI64 result := by
  exact checkedI64_sound (a - b) result h

theorem checkedMul_sound (a b result : Int)
    (h : checkedMul a b = .ok result) : inI64 result := by
  exact checkedI64_sound (a * b) result h


/-- A checked integer operation whose successful results are signed-64 values. -/
structure CheckedIntOp where
  run : Int → Int → Except Trap Int
  result_in_range :
    ∀ a b result, run a b = .ok result → inI64 result

/-- A typed binary integer instruction shared by subtraction and multiplication. -/
structure CheckedIntInstr (n : Nat) (types : RegTypes n) where
  dst : Fin n
  lhs : Fin n
  rhs : Fin n
  dst_is_int : types dst = .int
  lhs_is_int : types lhs = .int
  rhs_is_int : types rhs = .int

/-- Execute a checked binary operation with left-to-right operand-read precedence. -/
def executeCheckedIntOp {n : Nat} {types : RegTypes n}
    (op : CheckedIntOp) (regs : Registers n)
    (instr : CheckedIntInstr n types) : Except Trap (Registers n) :=
  match readInt regs instr.lhs, readInt regs instr.rhs with
  | .error e, _ => .error e
  | _, .error e => .error e
  | .ok a, .ok b =>
      match op.run a b with
      | .error e => .error e
      | .ok result => .ok (write regs instr.dst (.int result))

/-- A failed lhs read takes precedence over the rhs read and arithmetic. -/
theorem executeCheckedIntOp_left_read_error_precedence
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (op : CheckedIntOp) (instr : CheckedIntInstr n types) (e : Trap)
    (hleft : readInt regs instr.lhs = .error e) :
    executeCheckedIntOp op regs instr = .error e := by
  simp [executeCheckedIntOp, hleft]

/-- Every successful checked binary operation preserves register typing. -/
theorem executeCheckedIntOp_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs next : Registers n}
    (hregs : WellTyped types regs)
    (op : CheckedIntOp)
    (instr : CheckedIntInstr n types)
    (hstep : executeCheckedIntOp op regs instr = .ok next) :
    WellTyped types next := by
  unfold executeCheckedIntOp at hstep
  cases hleft : readInt regs instr.lhs with
  | error e =>
      simp [hleft] at hstep
  | ok a =>
      cases hright : readInt regs instr.rhs with
      | error e =>
          simp [hleft, hright] at hstep
      | ok b =>
          cases hop : op.run a b with
          | error e =>
              simp [hleft, hright, hop] at hstep
          | ok result =>
              simp [hleft, hright, hop] at hstep
              cases hstep
              have hresult : inI64 result := op.result_in_range a b result hop
              have hvalue : hasType (.int result) (types instr.dst) := by
                simpa [hasType, hasTypeB, instr.dst_is_int, inI64] using hresult
              exact write_preserves_well_typed hregs instr.dst (.int result) hvalue

/-- Checked subtraction is an instance of the generic typed binary operation. -/
def subIntOp : CheckedIntOp where
  run := checkedSub
  result_in_range := by
    intro a b result h
    exact checkedSub_sound a b result h

/-- Checked multiplication is an instance of the generic typed binary operation. -/
def mulIntOp : CheckedIntOp where
  run := checkedMul
  result_in_range := by
    intro a b result h
    exact checkedMul_sound a b result h



theorem checkedDiv_zero_traps (a : Int) :
    checkedDiv a 0 = .error .divisionByZero := by
  simp [checkedDiv]

theorem checkedRem_zero_traps (a : Int) :
    checkedRem a 0 = .error .divisionByZero := by
  simp [checkedRem]

theorem checkedDiv_min_neg_one_traps :
    checkedDiv minI64 (-1) = .error .integerOverflow := by
  simp [checkedDiv]

theorem checkedRem_min_neg_one_zero :
    checkedRem minI64 (-1) = .ok 0 := by
  simp [checkedRem]


/-- Any successful checked division returns a signed-64 value. -/
theorem checkedDiv_sound (a b result : Int)
    (h : checkedDiv a b = .ok result) : inI64 result := by
  unfold checkedDiv at h
  by_cases hz : b = 0
  · simp [hz] at h
  · by_cases hov : a = minI64 ∧ b = -1
    · simp [hz, hov] at h
    · exact checkedI64_sound (truncDiv a b) result (by simpa [hz, hov] using h)

/-- Any successful checked remainder returns a signed-64 value. -/
theorem checkedRem_sound (a b result : Int)
    (h : checkedRem a b = .ok result) : inI64 result := by
  unfold checkedRem at h
  by_cases hz : b = 0
  · simp [hz] at h
  · by_cases hmin : a = minI64 ∧ b = -1
    · simp [hz, hmin] at h
      subst result
      exact minI64_in_range
    · exact checkedI64_sound (a - truncDiv a b * b) result
        (by simpa [hz, hmin] using h)

/-- Checked division is an instance of the generic typed binary operation. -/
def divIntOp : CheckedIntOp where
  run := checkedDiv
  result_in_range := by
    intro a b result h
    exact checkedDiv_sound a b result h

/-- Checked remainder is an instance of the generic typed binary operation. -/
def remIntOp : CheckedIntOp where
  run := checkedRem
  result_in_range := by
    intro a b result h
    exact checkedRem_sound a b result h

/-!
Explicit omissions: there is no instruction syntax, machine state, small-step
relation, function stack, structural validator, evaluator, or compiler relation.
The next semantics increment must follow CCAM.md and its conformance vectors.
-/


/-! ## Boolean and integer-comparison instruction fragments

These constructors follow the eq_i, lt_i, and not_b operations in
CCAM v0.1. They remain instruction fragments, not a whole-program evaluator.
-/

/-- Integer less-than writes a boolean to a statically boolean destination. -/
structure LtInstr (n : Nat) (types : RegTypes n) where
  dst : Fin n
  lhs : Fin n
  rhs : Fin n
  dst_is_bool : types dst = .bool
  lhs_is_int : types lhs = .int
  rhs_is_int : types rhs = .int

def executeLt {n : Nat} {types : RegTypes n}
    (regs : Registers n) (instr : LtInstr n types) : Except Trap (Registers n) :=
  match readInt regs instr.lhs with
  | .error e => .error e
  | .ok a =>
    match readInt regs instr.rhs with
    | .error e => .error e
    | .ok b =>
      .ok (write regs instr.dst (.bool (decide (a < b))))

theorem executeLt_left_read_error_precedence
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (instr : LtInstr n types) (e : Trap)
    (hleft : readInt regs instr.lhs = .error e) :
    executeLt regs instr = .error e := by
  simp [executeLt, hleft]

theorem executeLt_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs next : Registers n}
    (hregs : WellTyped types regs)
    (instr : LtInstr n types)
    (hstep : executeLt regs instr = .ok next) :
    WellTyped types next := by
  unfold executeLt at hstep
  cases hleft : readInt regs instr.lhs with
  | error e =>
    simp [hleft] at hstep
  | ok a =>
    cases hright : readInt regs instr.rhs with
    | error e =>
      simp [hleft, hright] at hstep
    | ok b =>
      simp [hleft, hright] at hstep
      cases hstep
      have hvalue : hasType (.bool (decide (a < b))) (types instr.dst) := by
        simp [hasType, hasTypeB, instr.dst_is_bool]
      exact write_preserves_well_typed hregs instr.dst
        (.bool (decide (a < b))) hvalue

/-- Integer equality writes a boolean to a statically boolean destination. -/
structure EqInstr (n : Nat) (types : RegTypes n) where
  dst : Fin n
  lhs : Fin n
  rhs : Fin n
  dst_is_bool : types dst = .bool
  lhs_is_int : types lhs = .int
  rhs_is_int : types rhs = .int

def executeEq {n : Nat} {types : RegTypes n}
    (regs : Registers n) (instr : EqInstr n types) : Except Trap (Registers n) :=
  match readInt regs instr.lhs with
  | .error e => .error e
  | .ok a =>
    match readInt regs instr.rhs with
    | .error e => .error e
    | .ok b =>
      .ok (write regs instr.dst (.bool (decide (a = b))))

theorem executeEq_left_read_error_precedence
    {n : Nat} {types : RegTypes n} {regs : Registers n}
    (instr : EqInstr n types) (e : Trap)
    (hleft : readInt regs instr.lhs = .error e) :
    executeEq regs instr = .error e := by
  simp [executeEq, hleft]

theorem executeEq_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs next : Registers n}
    (hregs : WellTyped types regs)
    (instr : EqInstr n types)
    (hstep : executeEq regs instr = .ok next) :
    WellTyped types next := by
  unfold executeEq at hstep
  cases hleft : readInt regs instr.lhs with
  | error e =>
    simp [hleft] at hstep
  | ok a =>
    cases hright : readInt regs instr.rhs with
    | error e =>
      simp [hleft, hright] at hstep
    | ok b =>
      simp [hleft, hright] at hstep
      cases hstep
      have hvalue : hasType (.bool (decide (a = b))) (types instr.dst) := by
        simp [hasType, hasTypeB, instr.dst_is_bool]
      exact write_preserves_well_typed hregs instr.dst
        (.bool (decide (a = b))) hvalue

/-- Boolean negation preserves the declared boolean register type. -/
structure NotInstr (n : Nat) (types : RegTypes n) where
  dst : Fin n
  src : Fin n
  dst_is_bool : types dst = .bool
  src_is_bool : types src = .bool

def executeNot {n : Nat} {types : RegTypes n}
    (regs : Registers n) (instr : NotInstr n types) : Except Trap (Registers n) :=
  match readBool regs instr.src with
  | .error e => .error e
  | .ok value =>
    .ok (write regs instr.dst (.bool (!value)))

theorem executeNot_preserves_well_typed
    {n : Nat} {types : RegTypes n} {regs next : Registers n}
    (hregs : WellTyped types regs)
    (instr : NotInstr n types)
    (hstep : executeNot regs instr = .ok next) :
    WellTyped types next := by
  unfold executeNot at hstep
  cases hread : readBool regs instr.src with
  | error e =>
    simp [hread] at hstep
  | ok value =>
    simp [hread] at hstep
    cases hstep
    have hvalue : hasType (.bool (!value)) (types instr.dst) := by
      simp [hasType, hasTypeB, instr.dst_is_bool]
    exact write_preserves_well_typed hregs instr.dst (.bool (!value)) hvalue


end CapstanVerification
