import CapstanVerification.Machine

namespace CapstanVerification

/-!
Reachability-aware control-flow model for the finite single-frame machine.

Unlike FiniteProgram, this representation does not require the final table
slot to be terminal unconditionally. It requires only that every reachable
nonterminal instruction has an in-function successor. Reachability starts at
instruction zero; jumps and both branch arms contribute edges; ordinary
instructions fall through. Returns and traps are terminal and have no
successors. Cycles are allowed.
-/

/-- A control-flow edge in a finite instruction table. -/
inductive HasControlSuccessor {n m : Nat} {types : RegTypes n}
    (code : Fin (m + 1) → MachineInstr n (m + 1) types) :
    Fin (m + 1) → Fin (m + 1) → Prop
  | jump {pc target}
      (hcode : code pc = .jump target) :
      HasControlSuccessor code pc target
  | branchTrue {pc instr}
      (hcode : code pc = .branch instr) :
      HasControlSuccessor code pc instr.if_true
  | branchFalse {pc instr}
      (hcode : code pc = .branch instr) :
      HasControlSuccessor code pc instr.if_false
  | fallthrough {pc}
      (hordinary : machineInstrIsTerminal (code pc) = false)
      (hbeforeLast : pc.val < m) :
      HasControlSuccessor code pc ⟨pc.val + 1, by omega⟩

/-- Reachability is the reflexive-transitive closure of control-flow edges from PC zero. -/
inductive ReachablePC {n m : Nat} {types : RegTypes n}
    (code : Fin (m + 1) → MachineInstr n (m + 1) types) :
    Fin (m + 1) → Prop
  | entry : ReachablePC code 0
  | step {pc next}
      (hreached : ReachablePC code pc)
      (hedge : HasControlSuccessor code pc next) :
      ReachablePC code next

/-- A validated reachability-aware program permits unreachable trailing data.

Every instruction is still represented by intrinsically typed machine syntax;
the progress invariant applies only to instructions reachable from PC zero.
-/
structure ReachableValidatedProgram (n m : Nat) (types : RegTypes n) where
  code : Fin (m + 1) → MachineInstr n (m + 1) types
  reachableProgress :
    ∀ pc, ReachablePC code pc →
      machineInstrIsTerminal (code pc) = true ∨
        ∃ next, HasControlSuccessor code pc next

/-- The first instruction is reachable by definition. -/
theorem entry_pc_reachable
    {n m : Nat} {types : RegTypes n}
    (code : Fin (m + 1) → MachineInstr n (m + 1) types) :
    ReachablePC code 0 :=
  ReachablePC.entry

/-- A reachable final instruction must be terminal: it cannot fall through. -/
theorem reachable_final_instruction_terminal
    {n m : Nat} {types : RegTypes n}
    (program : ReachableValidatedProgram n m types)
    (hreached : ReachablePC program.code (Fin.last m)) :
    machineInstrIsTerminal (program.code (Fin.last m)) = true := by
  rcases program.reachableProgress (Fin.last m) hreached with hterminal | ⟨next, hedge⟩
  · exact hterminal
  · cases hedge with
    | jump hcode =>
        simpa [hcode, machineInstrIsTerminal]
    | branchTrue hcode =>
        simpa [hcode, machineInstrIsTerminal]
    | branchFalse hcode =>
        simpa [hcode, machineInstrIsTerminal]
    | fallthrough _ hbeforeLast =>
        have hlast : (Fin.last m).val = m := rfl
        rw [hlast] at hbeforeLast
        omega

/-- A reachable ordinary instruction before the last slot has its sequential edge. -/
theorem reachable_ordinary_has_fallthrough
    {n m : Nat} {types : RegTypes n}
    (program : ReachableValidatedProgram n m types)
    (pc : Fin (m + 1))
    (hreached : ReachablePC program.code pc)
    (hnonterminal : machineInstrIsTerminal (program.code pc) = false)
    (hbeforeLast : pc.val < m) :
    HasControlSuccessor program.code pc ⟨pc.val + 1, by omega⟩ :=
  HasControlSuccessor.fallthrough hnonterminal hbeforeLast

end CapstanVerification
