# CCAM single-frame proof profile

**Status:** research/verification profile; not a normative amendment to CCAM v0.1  
**Baseline revision:** `d635940c209d28b569f4776b3e443ab9632bf7f1`  
**Architecture authority:** `docs/DESIGN-MAP.md`  
**Normative machine contract:** `docs/architecture/CCAM.md`

## 1. Purpose

The current Lean development proves properties of a finite, typed, single-frame machine. Its accepted-program invariant is stricter than the normative CCAM v0.1 validator rule for reachable fall-through. This document names that strict subset so the formal result has a precise scope without silently changing CCAM.

The profile is called **CCAM-SF-P (single-frame proof profile)**. It is a conservative subset for the existing Lean machine, not a new language version, not a replacement for CCAM v0.1, and not a claim that the Capstan evaluator refines the Lean model.

## 2. Profile boundary

CCAM-SF-P covers only the single-frame instruction fragment represented by `MachineInstr` and `RawMachineInstr` in `verification/lean/CapstanVerification`:

- signed 64-bit integer and boolean values;
- finite, statically typed registers;
- typed constants and moves;
- checked integer arithmetic, equality and less-than;
- boolean negation;
- bounded unconditional and conditional branch targets;
- typed integer, boolean and void returns;
- explicit traps;
- a single entry frame, starting at instruction index zero.

It excludes calls, function tables, caller continuations, multi-frame execution, JSON decoding, duplicate-key detection, whole-program function validation, source lowering, native code generation, host effects and runtime services. The formal `Trap` type is a finite enumeration: arbitrary application-defined explicit-trap reason strings and their detail payloads are not represented by the current Lean `MachineInstr.explicitTrap` constructor. Such payload cases are outside the initial profile until a distinct bounded reason type is added.

The profile's admission predicate is `validateSingleFrameProfile`: it wraps the lower-level typed conversion, requires the entry index to be exactly zero (the concrete Capstan evaluator's initial PC), checks every instruction including unreachable instructions, and validates finite control-flow targets. The lower-level `validateSingleFrameProgram` remains a conversion helper and by itself permits any in-range entry; it is not the implementation-alignment profile predicate.

## 3. Deliberately conservative terminality rule

Normative CCAM v0.1 requires that **no reachable path falls off the end** of a function. Unreachable instructions must still be structurally and statically valid, but an unreachable final nonterminal instruction is not itself a fall-through violation.

CCAM-SF-P deliberately imposes the stronger condition:

> The final instruction slot must be an explicit control-effect instruction (jump, branch, return or trap), whether or not that slot is reachable.

This condition is sufficient for the current Lean machine's finite `Fin` program counter and clamped sequential successor. It is not necessary for normative CCAM validity. For example, a program that enters an infinite loop at instruction zero and has an unreachable nonterminal instruction in its final slot can be valid under the normative reachable-fall-through rule while being rejected by CCAM-SF-P.

This conservative restriction is intentional and must remain visible in every theorem and claim based on the current model. It must not be used to report the formal validator as a complete implementation of the normative CCAM validator.

A future refinement may replace the unconditional final-slot condition with an explicit reachable-set invariant and a successor semantics that represents end-of-function fall-through as a defined trap/invalid transition. That work must prove that no accepted reachable state can fall off the end.

## 4. Instruction-budget semantics

Two different notions of fuel exist in the Lean development and must not be conflated.

### 4.1 Normative machine budget

`Machine.lean` defines `StepBudget`, `consumeStep` and `budgetedMachineStep`. The one-step transition has the intended CCAM ordering:

1. If `used < limit`, consume exactly one instruction step.
2. Execute one machine instruction.
3. Preserve the consumed step whether the instruction continues, halts or traps.
4. If `used >= limit`, return the instruction-limit trap before executing another instruction.

The existing theorem `budgetedMachineStep_consumes_one` establishes one-step accounting when budget remains. `budgetedMachineStep_exhausted_before_instruction` establishes that an exhausted budget traps before instruction execution. These are model-level theorems about the Lean transition.

### 4.2 Lean recursion fuel

`Progress.lean` defines `runFuel` to make recursive execution structurally bounded for Lean. Its `fuelExhausted` result means only that the meta-level evaluator stopped because its recursion allowance ended. It is not the CCAM `step_limit_exceeded` outcome.

The earlier research crosswalk treated this distinction as a blocker to the one-step budget semantics. That was too broad: the normative budgeted one-step transition already exists in Lean. The remaining gap is a verified complete-execution account over that transition and, more importantly, correspondence with the Capstan-native evaluator's counter and trap behaviour.

## 5. Evidence and non-claims

At the baseline revision:

- `tests/run.sh` runs Capstan-native tests for the single-frame evaluator, multi-function evaluator and checked source-to-CCAM lowering.
- The Lean package contains a typed finite single-frame machine, a conservative terminal-slot validator, an implementation-alignment wrapper that enforces entry PC zero, and progress results.
- The Lean model has exact one-step instruction-budget accounting as described above.
- `RuntimeBridge.lean` proves selected representation/read and list-update facts for an abstract runtime-style record/list model.

These facts do **not** establish:

- that the Capstan-native validator accepts exactly the same programs as the Lean validator;
- arbitrary normative explicit-trap reason strings/details (the current Lean trap representation is a finite enum);
- that the Capstan evaluator's transitions simulate `machineStep` or `budgetedMachineStep`;
- that the source lowerer preserves source semantics;
- that multi-function calls or their frame protocol are formally modelled;
- that normative JSON decoding, duplicate-key rejection or whole-program validation is implemented;
- that native code or runtime services refine CCAM.

The tests are implementation evidence. The Lean theorems are model evidence. The implementation-refinement link remains open.

## 6. Required next proof increment

The next increment should be narrow and reviewable:

1. Define a canonical finite corpus for CCAM-SF-P, including arithmetic, branches, returns, finite-enum traps, uninitialised reads and exact step-limit boundaries; explicitly exclude arbitrary explicit-trap reason payloads.
2. Give each vector an independently specified expected validation result and execution trace/outcome.
3. Exercise the same vectors in the Capstan-native evaluator and a Lean executable model. Where the Lean model cannot represent a vector, mark it out of profile rather than silently skipping it.
4. Define a representation relation from Capstan register/program state to the Lean state; prove read/write correspondence and then one-step simulation for each instruction constructor.
5. Prove budget-counter correspondence, including dynamic trap and halt steps and pre-execution exhaustion.
6. Add the vector suite and formal build to the same CI gate.
7. Extend to calls only after the single-frame simulation theorem is stable; multi-frame execution is a separate proof increment.

Do not add a certificate format until program identity, acceptance and execution correspondence are established for this profile.

## 7. Exit criteria

CCAM-SF-P is ready to serve as a verified execution slice only when:

- its profile and acceptance predicate are versioned and explicit;
- canonical vectors have independent expected outcomes;
- validator and evaluator implementation results agree with those vectors;
- the Lean model agrees with the same vectors;
- the relevant one-step and budget-counter simulation theorems are machine checked;
- the exact CI revision passes the existing test suite, Lean build, pinned checker replay and security analysis;
- the result states clearly that calls, source lowering, JSON decoding and native execution remain outside the proved boundary.

Until then, describe this as a formal model with a conservative single-frame acceptance profile, not as an end-to-end verified compiler or execution engine.
