import CapstanVerification.Machine

namespace CapstanVerification

/-!
A first validator model for the *decoded, single-instruction* CCAM subset.

The input deliberately uses untrusted natural-number register and branch
indices. Successful validation converts those indices to `Fin` values and
constructs the existing intrinsically typed `MachineInstr` representation.
This is not yet a JSON decoder, whole-program validator, reachability checker,
or refinement proof for the Capstan implementation.
-/

/-- Decoded instruction syntax before register/target validation. -/
inductive RawInstr where
  | constInt (dst : Nat) (value : Int)
  | constBool (dst : Nat) (value : Bool)
  | jump (target : Nat)
  | branch (cond ifTrue ifFalse : Nat)
  | retInt (src : Nat)
  | retBool (src : Nat)
  | retVoid
  | explicitTrap (reason : Trap)
  deriving Repr

/-- Convert an untrusted natural index to a bounded finite index. -/
def finOfNat? (bound index : Nat) : Option (Fin bound) :=
  if h : index < bound then some ⟨index, h⟩ else none

/-- A successful natural-to-finite conversion preserves the index value. -/
theorem finOfNat?_value {bound index : Nat} {i : Fin bound}
    (h : finOfNat? bound index = some i) : i.val = index := by
  unfold finOfNat? at h
  split at h
  · injection h with hi
    subst i
    rfl
  · contradiction

/-- Validate one decoded instruction against a register signature and code size. -/
def validateRawInstruction {n m : Nat} {types : RegTypes n}
    (raw : RawInstr) : Option (MachineInstr n m types) :=
  match raw with
  | .constInt dst value =>
      match finOfNat? n dst with
      | none => none
      | some dst =>
          if htype : types dst = .int then
            if hvalue : inI64B value = true then
              some (.constInt dst value htype hvalue)
            else none
          else none
  | .constBool dst value =>
      match finOfNat? n dst with
      | none => none
      | some dst =>
          if htype : types dst = .bool then
            some (.constBool dst value htype)
          else none
  | .jump target =>
      match finOfNat? m target with
      | none => none
      | some target => some (.jump target)
  | .branch cond ifTrue ifFalse =>
      match finOfNat? n cond, finOfNat? m ifTrue, finOfNat? m ifFalse with
      | some cond, some ifTrue, some ifFalse =>
          if htype : types cond = .bool then
            some (.branch {
              cond := cond
              cond_is_bool := htype
              if_true := ifTrue
              if_false := ifFalse
            })
          else none
      | _, _, _ => none
  | .retInt src =>
      match finOfNat? n src with
      | none => none
      | some src =>
          if htype : types src = .int then
            some (.retInt src htype)
          else none
  | .retBool src =>
      match finOfNat? n src with
      | none => none
      | some src =>
          if htype : types src = .bool then
            some (.retBool src htype)
          else none
  | .retVoid => some .retVoid
  | .explicitTrap reason => some (.explicitTrap reason)

/-- Every successful result is already a value of the intrinsically typed machine syntax. -/
theorem validateRawInstruction_returns_typed
    {n m : Nat} {types : RegTypes n}
    (raw : RawInstr) (instr : MachineInstr n m types)
    (h : validateRawInstruction raw = some instr) :
    ∃ typed : MachineInstr n m types, validateRawInstruction raw = some typed := by
  exact ⟨instr, h⟩

/-- Every jump and branch target in the machine syntax is in range by construction. -/
def MachineInstrTargetsInRange {n m : Nat} {types : RegTypes n} :
    MachineInstr n m types → Prop
  | .jump target => target.val < m
  | .branch instr => instr.if_true.val < m ∧ instr.if_false.val < m
  | _ => True

/-- Intrinsic finite indices make every machine instruction's control targets safe. -/
theorem machineInstr_targets_in_range
    {n m : Nat} {types : RegTypes n} (instr : MachineInstr n m types) :
    MachineInstrTargetsInRange instr := by
  cases instr <;> simp [MachineInstrTargetsInRange]

/-- Successful raw validation cannot introduce an out-of-range branch or jump. -/
theorem validateRawInstruction_target_sound
    {n m : Nat} {types : RegTypes n}
    (raw : RawInstr) (instr : MachineInstr n m types)
    (_h : validateRawInstruction raw = some instr) :
    MachineInstrTargetsInRange instr :=
  machineInstr_targets_in_range instr

/-- Successful validation of a raw jump preserves its target and bounds it. -/
theorem validateRawInstruction_jump_target_sound
    {n m : Nat} {types : RegTypes n}
    (target : Nat) (instr : MachineInstr n m types)
    (h : validateRawInstruction (RawInstr.jump target) = some instr) :
    ∃ bounded : Fin m, instr = .jump bounded ∧ bounded.val = target := by
  unfold validateRawInstruction at h
  cases htarget : finOfNat? m target with
  | none =>
      simp [htarget] at h
  | some bounded =>
      simp [htarget] at h
      cases h
      exact ⟨bounded, rfl, finOfNat?_value htarget⟩

/-- Successful raw branch validation preserves both raw targets and the boolean condition. -/
theorem validateRawInstruction_branch_targets_sound
    {n m : Nat} {types : RegTypes n}
    (cond ifTrue ifFalse : Nat) (instr : MachineInstr n m types)
    (h : validateRawInstruction (RawInstr.branch cond ifTrue ifFalse) = some instr) :
    ∃ c : Fin n, ∃ t : Fin m, ∃ f : Fin m,
      ∃ htype : types c = .bool,
        instr = .branch {
          cond := c
          cond_is_bool := htype
          if_true := t
          if_false := f
        } ∧ c.val = cond ∧ t.val = ifTrue ∧ f.val = ifFalse := by
  unfold validateRawInstruction at h
  cases hc : finOfNat? n cond with
  | none => simp [hc] at h
  | some c =>
    cases ht : finOfNat? m ifTrue with
    | none => simp [hc, ht] at h
    | some t =>
      cases hf : finOfNat? m ifFalse with
      | none => simp [hc, ht, hf] at h
      | some f =>
        by_cases htype : types c = .bool
        · simp [hc, ht, hf, htype] at h
          cases h
          exact ⟨c, t, f, htype, rfl,
            finOfNat?_value hc, finOfNat?_value ht, finOfNat?_value hf⟩
        · simp [hc, ht, hf, htype] at h

/-- A successful integer constant validation carries the declared integer type. -/
theorem validateRawInstruction_constInt_type_sound
    {n m : Nat} {types : RegTypes n}
    (dst : Nat) (value : Int) (instr : MachineInstr n m types)
    (h : validateRawInstruction (RawInstr.constInt dst value) = some instr) :
    ∃ index : Fin n, types index = .int ∧ inI64 value := by
  unfold validateRawInstruction at h
  cases hindex : finOfNat? n dst with
  | none => simp [hindex] at h
  | some index =>
      by_cases htype : types index = .int
      · by_cases hvalue : inI64B value = true
        · simp [hindex, htype, hvalue] at h
          cases h
          exact ⟨index, htype, hvalue⟩
        · simp [hindex, htype, hvalue] at h
      · simp [hindex, htype] at h

/-- A successful boolean constant validation carries the declared boolean type. -/
theorem validateRawInstruction_constBool_type_sound
    {n m : Nat} {types : RegTypes n}
    (dst : Nat) (value : Bool) (instr : MachineInstr n m types)
    (h : validateRawInstruction (RawInstr.constBool dst value) = some instr) :
    ∃ index : Fin n, types index = .bool := by
  unfold validateRawInstruction at h
  cases hindex : finOfNat? n dst with
  | none => simp [hindex] at h
  | some index =>
      by_cases htype : types index = .bool
      · simp [hindex, htype] at h
        cases h
        exact ⟨index, htype⟩
      · simp [hindex, htype] at h

end CapstanVerification
