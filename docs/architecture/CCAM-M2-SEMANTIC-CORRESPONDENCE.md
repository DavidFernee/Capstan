# CCAM-M2: semantic correspondence and proof plan

**Status:** design contract and gap analysis; no multi-function refinement theorem is claimed.  
**Depends on:** `CCAM.md`, `CCAM-JSON-DECODER.md`, PR #312.  
**Target:** a machine-checked correspondence between the Capstan-native CCAM decoder/validator/evaluator and an independently defined Lean semantics.

## 1. Current assurance boundary

The current Lean package is not yet a formal model of the executable multi-function CCAM implementation.

- `CapstanVerification.Machine` defines an intrinsically typed, finite, single-frame instruction fragment. Its register and control-flow indices are `Fin`; it excludes calls, concrete call frames, output effects, and the complete evaluator state.
- `ProgramValidator` validates a raw single-frame program into that finite model. It does not validate the multi-function JSON schema.
- `RuntimeBridge` proves properties about an abstract list-of-registers representation and a relation to the finite typed register model. It does not establish that the actual `.cap` implementation refines that relation.
- `ccam_calls.cap` implements multi-function frames and call-site side tables. `ccam_json.cap` decodes JSON into that representation. Neither is presently connected to the Lean definitions by a theorem.

Consequently, the existing proofs are useful components, not evidence that PR #312 or the multi-function evaluator is formally verified. The implementation and proof model currently have different semantic coverage.

## 2. Normative semantic object

The proof target is the abstract program, not the JSON syntax tree and not the transitional call-site side table.

Define a validated program as:

```text
Program = {
  functions : Vector Function functionCount,
  entry     : Fin functionCount
}

Function = {
  name           : ScalarString,
  registerTypes  : Vector Ty registerCount,
  parameterCount : Nat,
  returnType     : ReturnTy,
  code           : Vector Instr instructionCount
}

Instr.call = {
  dst      : Option RegisterIndex,
  callee   : Fin functionCount,
  args     : Vector RegisterIndex parameterCount
}
```

All indices are finite values after validation. The named JSON callee is resolved exactly once to a finite function index. A call's destination is absent exactly when the callee return type is void. Argument count and argument register types agree with the callee's leading parameter registers. Function names are unique and the entry function has zero parameters and a non-void return contract, as specified in CCAM v0.1.

The mathematical model must use exact signed-64 values and explicit checked arithmetic. It must not inherit host-language overflow, float conversion, evaluation order, or implicit coercion.

## 3. Machine state and transition relation

A concrete abstract machine state is:

```text
State = {
  frames       : NonEmptyList Frame,
  stepsUsed    : Nat,
  stepsLimit   : Nat,
  maxDepth     : Nat,
  output       : ByteVector,
  status       : Running | Halted Result | Trapped Trap
}

Frame = {
  functionIndex : Fin functionCount,
  pc            : Fin instructionCount(functionIndex),
  registers     : RegisterFile(functionIndex),
  continuation  : Option Continuation
}

Continuation = {
  callerFrameDepth : Nat,
  destination      : Option RegisterIndex,
  expectedReturn   : ReturnTy
}
```

The operational relation is a deterministic small-step relation `step : Program → State → StateResult`. It must explicitly specify:

1. step-budget check before instruction execution;
2. checked arithmetic and all trap cases;
3. register initialization and typed reads/writes;
4. branch/jump transitions;
5. call preflight (callee existence, arity, argument initialization and types, destination compatibility, depth budget) before frame mutation;
6. parameter transfer and fresh uninitialized callee registers;
7. return preflight before caller mutation, including return type and destination compatibility;
8. restoration of the caller continuation;
9. entry-frame return as halt rather than nested pop;
10. bounded output effects for the separately versioned output extension.

The formal relation must make failed preflight atomic: a failed call or return produces a trap without partially modifying the frame stack, caller registers, or output. Whether the concrete implementation currently satisfies each clause is a proof obligation, not an assumption.

## 4. Representation relations

Three relations are required and must remain separate.

### 4.1 JSON decode relation

`decode(bytes) = ok p` implies that `p` is exactly the abstract program represented by the JSON document under the normative schema.

The parser's byte-level obligations (UTF-8 scalar validity, surrogate pairing, duplicate decoded keys, exact number tokens, depth/node/string budgets) precede schema decoding. Schema decoding then establishes exact field sets and field types. Name resolution must be total for successful results.

### 4.2 Validator soundness relation

`validate(raw) = ok p` implies `WellFormed p`.

`WellFormed` includes all local and cross-function properties: register type correctness, operand bounds, return contracts, entry signature, unique names, call arity/types/destination, call-site uniqueness and correspondence, reachable control-flow successor validity, and resource ceilings.

This theorem must cover unreachable instructions for structural/type/index validity while applying fall-through reachability only to reachable instructions, matching CCAM.md.

### 4.3 Runtime representation relation

A concrete Capstan state is related to an abstract Lean state when:
- function and frame indices identify the same abstract functions;
- each concrete register slot has the same declared type and initialization state;
- initialized payloads denote the same exact abstract value;
- PC and continuation/call-site lookup denote the same next abstract transition;
- counters, limits, output and terminal/trap state agree.

The current `RuntimeBridge` is only a partial register-file foundation. It must be extended to frame stacks, program-counter updates, call-site lookup, continuation handling, output, and complete state transitions. It must then be connected to the actual Capstan source through a mechanically checked extraction, translation-validation, or verified compiler boundary. A hand-written correspondence argument is insufficient.

## 5. Theorem sequence and acceptance criteria

| ID | Theorem / deliverable | Required result |
|---|---|---|
| M2.1 | `decode_sound` | Every successful decode yields the unique abstract program represented by the input. |
| M2.2 | `validate_sound` | Every successful validation establishes `WellFormed`. |
| M2.3 | `register_read_write_simulation` | Concrete register operations preserve the representation relation and match abstract operations. |
| M2.4 | `call_step_simulation` | Every successful concrete call transition matches one abstract call transition; failed preflight is atomic. |
| M2.5 | `return_step_simulation` | Every successful return restores the right continuation and result; failed preflight is atomic. |
| M2.6 | `ordinary_step_simulation` | Arithmetic, control flow, traps, and budgets preserve simulation. |
| M2.7 | `whole_machine_simulation` | The concrete evaluator simulates the abstract machine for every well-formed decoded program. |
| M2.8 | `determinism` | A well-formed state has at most one next transition. |
| M2.9 | `resource_safety` | Frame depth, steps, register totals, argument totals, and output remain within declared limits. |

The principal result is a forward simulation theorem. A stronger bisimulation may be pursued only if the concrete machine has no implementation-only transitions that need stuttering or abstraction.

No theorem may be discharged by adding an axiom for the desired result, weakening a definition until the theorem is trivial, or using `sorry`/`admit`. The formal CI must build with warnings as errors and run the repository's independent proof checker and axiom audit. Permitted Lean kernel axioms must be reported; project-local axioms are prohibited.

## 6. Immediate implementation tasks

1. Add a Lean multi-function syntax and `WellFormed` predicate that matches the normative CCAM v0.1 schema.
2. Add a small-step multi-frame semantics, including explicit call and return transitions and atomic preflight.
3. Prove local lemmas for typed register access, frame push/pop, call argument transfer, return destination writes, and resource counters. The current `MultiFunctionMachine` fragment now has bounded frame push/pop, caller-identity and return-contract checks, checked return-value placement, and a register-list length-preservation lemma. These are local model properties only: frame registers are still list-based and are not yet related to `Machine.Registers`, and no concrete evaluator simulation is established.
4. Specify a machine-readable intermediate representation shared by the Capstan decoder and the proof model, or add a checked translation validator. Do not claim correspondence merely because field names look similar.
5. Add positive and negative fixtures generated from the same abstract examples, and test that the Capstan decoder and Lean validator agree on acceptance/rejection.
6. Extend the proof CI to build the new CCAM modules and include them in the axiom audit and independent checker root.

## 7. Non-claims

This document is a proof contract and gap analysis, not a proof. It does not establish parser correctness, validator soundness, implementation refinement, memory safety, native backend correctness, or C-Free bootstrapping. Those remain separately gated deliverables.
