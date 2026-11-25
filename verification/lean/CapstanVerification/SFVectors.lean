-- Generated from verification/ccam_sf_vectors.json.
-- Regenerate with scripts/generate_ccam_sf_lean_vectors.py.
-- This checks Lean profile admission and model execution, not concrete refinement.
import CapstanVerification.ProgramValidator

namespace CapstanVerification

inductive SFRunOutcome where
  | halt (value : Val) (pc steps : Nat) (trace : List Nat)
  | haltVoid (pc steps : Nat) (trace : List Nat)
  | trap (reason : Trap) (pc steps : Nat) (trace : List Nat)
  deriving DecidableEq, Repr

/-- Run the typed single-frame machine with the corpus instruction budget. -/
def runBudgetedSFMachine {n m : Nat} {types : RegTypes n}
    (fuel : Nat) (program : FiniteProgram n m types)
    (state : BudgetedMachineState n m types) (trace : List Nat) : SFRunOutcome :=
  match fuel with
  | 0 => .trap .instructionLimit state.machine.pc.val state.budget.used trace
  | Nat.succ remaining =>
      let currentPC := state.machine.pc.val
      match budgetedMachineStep program state with
      | .nextState next =>
          runBudgetedSFMachine remaining program next (trace ++ [currentPC])
      | .halt value budget =>
          .halt value currentPC budget.used (trace ++ [currentPC])
      | .haltVoid budget =>
          .haltVoid currentPC budget.used (trace ++ [currentPC])
      | .trap reason budget =>
          if budget.used > state.budget.used then
            .trap reason currentPC budget.used (trace ++ [currentPC])
          else
            .trap reason currentPC budget.used trace

/-- Start with every register uninitialised and run a validated profile program. -/
def runSFProfileProgram {n m : Nat} {types : RegTypes n}
    (program : FiniteProgram n m types) (limit : Nat) : SFRunOutcome :=
  let initial : BudgetedMachineState n m types :=
    { machine := initialMachineState program (fun _ => none) (by
        intro i v h
        simp at h)
      budget := { limit := limit, used := 0, within_limit := Nat.zero_le limit } }
  runBudgetedSFMachine (limit + 1) program initial []

/-- Rejected programs produce no executable machine outcome. -/
def runSFProfileVector {n m : Nat} {types : RegTypes n}
    (raw : RawSingleFrameProgram n m types) (limit : Nat) : Option SFRunOutcome := do
  let program ← validateSingleFrameProfile raw
  pure (runSFProfileProgram program limit)

def sfPTypes_SF001 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF001 : RawSingleFrameProgram 3 3 sfPTypes_SF001 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 19
    | 1 => .constInt 1 23
    | 2 => .add 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF001 :
    (validateSingleFrameProfile sfPProgram_SF001).isSome = true := by decide

theorem sfP_run_SF001 :
    runSFProfileVector sfPProgram_SF001 4 = some (.halt (.int 42) 3 4 [0, 1, 2, 3]) := by decide

def sfPTypes_SF002 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF002 : RawSingleFrameProgram 3 3 sfPTypes_SF002 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 9223372036854775807
    | 1 => .constInt 1 1
    | 2 => .add 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF002 :
    (validateSingleFrameProfile sfPProgram_SF002).isSome = true := by decide

theorem sfP_run_SF002 :
    runSFProfileVector sfPProgram_SF002 4 = some (.trap .integerOverflow 2 3 [0, 1, 2]) := by decide

def sfPTypes_SF003 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF003 : RawSingleFrameProgram 3 3 sfPTypes_SF003 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 -9223372036854775808
    | 1 => .constInt 1 -1
    | 2 => .div 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF003 :
    (validateSingleFrameProfile sfPProgram_SF003).isSome = true := by decide

theorem sfP_run_SF003 :
    runSFProfileVector sfPProgram_SF003 4 = some (.trap .integerOverflow 2 3 [0, 1, 2]) := by decide

def sfPTypes_SF004 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF004 : RawSingleFrameProgram 3 3 sfPTypes_SF004 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 -9223372036854775808
    | 1 => .constInt 1 -1
    | 2 => .rem 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF004 :
    (validateSingleFrameProfile sfPProgram_SF004).isSome = true := by decide

theorem sfP_run_SF004 :
    runSFProfileVector sfPProgram_SF004 4 = some (.halt (.int 0) 3 4 [0, 1, 2, 3]) := by decide

def sfPTypes_SF005 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF005 : RawSingleFrameProgram 3 3 sfPTypes_SF005 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 7
    | 1 => .constInt 1 0
    | 2 => .div 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF005 :
    (validateSingleFrameProfile sfPProgram_SF005).isSome = true := by decide

theorem sfP_run_SF005 :
    runSFProfileVector sfPProgram_SF005 4 = some (.trap .divisionByZero 2 3 [0, 1, 2]) := by decide

def sfPTypes_SF006 : RegTypes 2 := fun i =>
  match i.val with
  | 0 => .bool
  | 1 => .int
  | _ => .int

def sfPProgram_SF006 : RawSingleFrameProgram 2 5 sfPTypes_SF006 where
  code := fun pc =>
    match pc.val with
    | 0 => .constBool 0 true
    | 1 => .branch 0 2 4
    | 2 => .constInt 1 42
    | 3 => .jump 5
    | 4 => .constInt 1 99
    | 5 => .retInt 1
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF006 :
    (validateSingleFrameProfile sfPProgram_SF006).isSome = true := by decide

theorem sfP_run_SF006 :
    runSFProfileVector sfPProgram_SF006 6 = some (.halt (.int 42) 5 5 [0, 1, 2, 3, 5]) := by decide

def sfPTypes_SF007 : RegTypes 2 := fun i =>
  match i.val with
  | 0 => .bool
  | 1 => .int
  | _ => .int

def sfPProgram_SF007 : RawSingleFrameProgram 2 5 sfPTypes_SF007 where
  code := fun pc =>
    match pc.val with
    | 0 => .constBool 0 false
    | 1 => .branch 0 2 4
    | 2 => .constInt 1 42
    | 3 => .jump 5
    | 4 => .constInt 1 99
    | 5 => .retInt 1
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF007 :
    (validateSingleFrameProfile sfPProgram_SF007).isSome = true := by decide

theorem sfP_run_SF007 :
    runSFProfileVector sfPProgram_SF007 6 = some (.halt (.int 99) 5 4 [0, 1, 4, 5]) := by decide

def sfPTypes_SF008 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .bool
  | 1 => .bool
  | 2 => .bool
  | _ => .int

def sfPProgram_SF008 : RawSingleFrameProgram 3 3 sfPTypes_SF008 where
  code := fun pc =>
    match pc.val with
    | 0 => .constBool 0 true
    | 1 => .move 1 0
    | 2 => .booleanNot 2 1
    | 3 => .retBool 2
    | _ => .retVoid
  entry := 0
  returnType := .bool

theorem sfP_profile_SF008 :
    (validateSingleFrameProfile sfPProgram_SF008).isSome = true := by decide

theorem sfP_run_SF008 :
    runSFProfileVector sfPProgram_SF008 4 = some (.halt (.bool false) 3 4 [0, 1, 2, 3]) := by decide

def sfPTypes_SF009 : RegTypes 5 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .bool
  | 3 => .bool
  | 4 => .bool
  | _ => .int

def sfPProgram_SF009 : RawSingleFrameProgram 5 5 sfPTypes_SF009 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 5
    | 1 => .constInt 1 8
    | 2 => .equal 2 0 0
    | 3 => .lessThan 3 0 1
    | 4 => .booleanNot 4 3
    | 5 => .retBool 2
    | _ => .retVoid
  entry := 0
  returnType := .bool

theorem sfP_profile_SF009 :
    (validateSingleFrameProfile sfPProgram_SF009).isSome = true := by decide

theorem sfP_run_SF009 :
    runSFProfileVector sfPProgram_SF009 6 = some (.halt (.bool true) 5 6 [0, 1, 2, 3, 4, 5]) := by decide

def sfPTypes_SF010 : RegTypes 0 := fun i =>
  nomatch i

def sfPProgram_SF010 : RawSingleFrameProgram 0 0 sfPTypes_SF010 where
  code := fun pc =>
    match pc.val with
    | 0 => .retVoid
    | _ => .retVoid
  entry := 0
  returnType := .void

theorem sfP_profile_SF010 :
    (validateSingleFrameProfile sfPProgram_SF010).isSome = true := by decide

theorem sfP_run_SF010 :
    runSFProfileVector sfPProgram_SF010 1 = some (.haltVoid 0 1 [0]) := by decide

def sfPTypes_SF011 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .int
  | _ => .int

def sfPProgram_SF011 : RawSingleFrameProgram 1 0 sfPTypes_SF011 where
  code := fun pc =>
    match pc.val with
    | 0 => .retInt 0
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF011 :
    (validateSingleFrameProfile sfPProgram_SF011).isSome = true := by decide

theorem sfP_run_SF011 :
    runSFProfileVector sfPProgram_SF011 1 = some (.trap .uninitialisedRegister 0 1 [0]) := by decide

def sfPTypes_SF012 : RegTypes 0 := fun i =>
  nomatch i

def sfPProgram_SF012 : RawSingleFrameProgram 0 0 sfPTypes_SF012 where
  code := fun pc =>
    match pc.val with
    | 0 => .retVoid
    | _ => .retVoid
  entry := 0
  returnType := .void

theorem sfP_profile_SF012 :
    (validateSingleFrameProfile sfPProgram_SF012).isSome = true := by decide

theorem sfP_run_SF012 :
    runSFProfileVector sfPProgram_SF012 0 = some (.trap .instructionLimit 0 0 []) := by decide

def sfPTypes_SF013 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .int
  | _ => .int

def sfPProgram_SF013 : RawSingleFrameProgram 1 1 sfPTypes_SF013 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 42
    | 1 => .retInt 0
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF013 :
    (validateSingleFrameProfile sfPProgram_SF013).isSome = true := by decide

theorem sfP_run_SF013 :
    runSFProfileVector sfPProgram_SF013 2 = some (.halt (.int 42) 1 2 [0, 1]) := by decide

def sfPTypes_SF014 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .int
  | _ => .int

def sfPProgram_SF014 : RawSingleFrameProgram 1 1 sfPTypes_SF014 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 42
    | 1 => .retInt 0
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF014 :
    (validateSingleFrameProfile sfPProgram_SF014).isSome = true := by decide

theorem sfP_run_SF014 :
    runSFProfileVector sfPProgram_SF014 1 = some (.trap .instructionLimit 1 1 [0]) := by decide

def sfPTypes_SF015 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .int
  | _ => .int

def sfPProgram_SF015 : RawSingleFrameProgram 1 1 sfPTypes_SF015 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 1 7
    | 1 => .retVoid
    | _ => .retVoid
  entry := 0
  returnType := .void

theorem sfP_profile_SF015 :
    (validateSingleFrameProfile sfPProgram_SF015).isSome = false := by decide

theorem sfP_run_SF015 :
    (runSFProfileVector sfPProgram_SF015 2).isNone = true := by decide

def sfPTypes_SF016 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .bool
  | _ => .int

def sfPProgram_SF016 : RawSingleFrameProgram 1 1 sfPTypes_SF016 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 7
    | 1 => .retVoid
    | _ => .retVoid
  entry := 0
  returnType := .void

theorem sfP_profile_SF016 :
    (validateSingleFrameProfile sfPProgram_SF016).isSome = false := by decide

theorem sfP_run_SF016 :
    (runSFProfileVector sfPProgram_SF016 2).isNone = true := by decide

def sfPTypes_SF017 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .bool
  | _ => .int

def sfPProgram_SF017 : RawSingleFrameProgram 1 2 sfPTypes_SF017 where
  code := fun pc =>
    match pc.val with
    | 0 => .constBool 0 true
    | 1 => .branch 0 2 99
    | 2 => .retVoid
    | _ => .retVoid
  entry := 0
  returnType := .void

theorem sfP_profile_SF017 :
    (validateSingleFrameProfile sfPProgram_SF017).isSome = false := by decide

theorem sfP_run_SF017 :
    (runSFProfileVector sfPProgram_SF017 2).isNone = true := by decide

def sfPTypes_SF018 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .int
  | _ => .int

def sfPProgram_SF018 : RawSingleFrameProgram 1 0 sfPTypes_SF018 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 7
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF018 :
    (validateSingleFrameProfile sfPProgram_SF018).isSome = false := by decide

theorem sfP_run_SF018 :
    (runSFProfileVector sfPProgram_SF018 2).isNone = true := by decide

def sfPTypes_SF019 : RegTypes 1 := fun i =>
  match i.val with
  | 0 => .int
  | _ => .int

def sfPProgram_SF019 : RawSingleFrameProgram 1 1 sfPTypes_SF019 where
  code := fun pc =>
    match pc.val with
    | 0 => .jump 0
    | 1 => .constInt 0 7
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF019 :
    (validateSingleFrameProfile sfPProgram_SF019).isSome = false := by decide

theorem sfP_run_SF019 :
    (runSFProfileVector sfPProgram_SF019 3).isNone = true := by decide

def sfPTypes_SF020 : RegTypes 0 := fun i =>
  nomatch i

def sfPProgram_SF020 : RawSingleFrameProgram 0 1 sfPTypes_SF020 where
  code := fun pc =>
    match pc.val with
    | 0 => .jump 0
    | 1 => .retVoid
    | _ => .retVoid
  entry := 1
  returnType := .void

theorem sfP_profile_SF020 :
    (validateSingleFrameProfile sfPProgram_SF020).isSome = false := by decide

theorem sfP_run_SF020 :
    (runSFProfileVector sfPProgram_SF020 2).isNone = true := by decide

def sfPTypes_SF021 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF021 : RawSingleFrameProgram 3 3 sfPTypes_SF021 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 50
    | 1 => .constInt 1 8
    | 2 => .sub 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF021 :
    (validateSingleFrameProfile sfPProgram_SF021).isSome = true := by decide

theorem sfP_run_SF021 :
    runSFProfileVector sfPProgram_SF021 4 = some (.halt (.int 42) 3 4 [0, 1, 2, 3]) := by decide

def sfPTypes_SF022 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF022 : RawSingleFrameProgram 3 3 sfPTypes_SF022 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 6
    | 1 => .constInt 1 7
    | 2 => .mul 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF022 :
    (validateSingleFrameProfile sfPProgram_SF022).isSome = true := by decide

theorem sfP_run_SF022 :
    runSFProfileVector sfPProgram_SF022 4 = some (.halt (.int 42) 3 4 [0, 1, 2, 3]) := by decide

def sfPTypes_SF023 : RegTypes 3 := fun i =>
  match i.val with
  | 0 => .int
  | 1 => .int
  | 2 => .int
  | _ => .int

def sfPProgram_SF023 : RawSingleFrameProgram 3 3 sfPTypes_SF023 where
  code := fun pc =>
    match pc.val with
    | 0 => .constInt 0 4611686018427387904
    | 1 => .constInt 1 2
    | 2 => .mul 2 0 1
    | 3 => .retInt 2
    | _ => .retVoid
  entry := 0
  returnType := .int

theorem sfP_profile_SF023 :
    (validateSingleFrameProfile sfPProgram_SF023).isSome = true := by decide

theorem sfP_run_SF023 :
    runSFProfileVector sfPProgram_SF023 4 = some (.trap .integerOverflow 2 3 [0, 1, 2]) := by decide

end CapstanVerification
