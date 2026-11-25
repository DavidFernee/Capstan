# CCAM single-frame concrete refinement contract

Status: **design contract / proof plan only**. This document does not claim an implementation-refinement theorem, a completed corpus run, or a formal verification result for the concrete evaluator.

## Purpose and scope

Define the exact relation needed to connect the Capstan-native evaluator in `verification/ccam_core.cap` to the finite, intrinsically typed Lean machine in `verification/lean/CapstanVerification/Machine.lean`.

The intended proof profile is deliberately narrower than normative CCAM v0.1. It is the existing single-frame subset, with entry point zero and the structural restrictions enforced by `ccam_validate_single_frame` / `ccam_machine_create_validated`. Calls, frame stacks, source lowering, external decoding, and resource accounting beyond the instruction-step budget are out of scope.

This is a specification of proof obligations. It must not be treated as evidence that the obligations have been discharged.

## Pinned source inputs

The contract was prepared against these default-branch file blobs:

| Artifact | Blob SHA | Role |
|---|---|---|
| `verification/ccam_core.cap` | `b29b6190d2eb3d9998a6d13d620e2e67a8165d7c` | Concrete Capstan register substrate, validator, evaluator |
| `verification/lean/CapstanVerification/Core.lean` | `3d00755ebdb50a5f9dc9894c984cab25626c7bf4` | Typed values, registers, traps, checked arithmetic |
| `verification/lean/CapstanVerification/Machine.lean` | `9af71007c8cef96e9b18e9d3dcd52ef9d4c0012f` | Finite single-frame abstract machine and step budget |
| `verification/lean/CapstanVerification/ProgramValidator.lean` | `7566ff6c33efc4b831ad613a699b8fcb541b1991` | Raw-to-typed proof-profile validation |
| `verification/lean/CapstanVerification/RuntimeBridge.lean` | `b071f237ac550e4bcf79f0304e6e33b37942c658` | Abstract list-register representation relation |

A blob SHA identifies file content, not a complete build. A future proof result must additionally pin the repository commit, Capstan compiler/toolchain revision, Lean version, build configuration, and all imported module hashes.

## Concrete/abstract state relation

For a successfully created concrete evaluator state (C), a validated abstract program (P), and abstract machine state (A), define a relation (R(C,A)) with the following components.

1. **Program identity.** The concrete instruction snapshot and abstract program denote the same instruction sequence, operand indices, constants, branch targets, return contract, and explicit-trap payload. This is stronger than merely having equal instruction counts.
2. **Program counter.** (C.pc = A.pc.val). Both machines start at zero in this profile.
3. **Register file.** The concrete `List<CCAMRegister>` is related to the abstract `Registers n` by `RuntimeRegisterFileRelation`: equal length, equal declared type at every valid index, and equal initialized value (or both uninitialized).
4. **Execution status.** While running, the concrete state is not halted and the abstract state is a running `MachineState`. Terminal outcomes are related by the explicit outcome mapping below.
5. **Fuel.** The concrete `steps` equals the abstract budget's `used`; both limits equal the same nonnegative configured maximum.
6. **Return payload.** On a value return, the concrete `halt_has_value`, `halt_value`, and `halt_bool_value` encode exactly the abstract `Val`. On void return, `halt_has_value` is false and no value is observable.
7. **Trap projection.** Concrete `trap_code` and `trap_detail` map to the abstract `Trap` constructor and, where applicable, its explicit payload. No unknown string may be silently mapped to an arbitrary abstract trap.

The concrete state is mutable. A proof must state whether it reasons about pre-state/post-state snapshots or a pure abstraction function; informal equality of mutable objects is not sufficient.

## Instruction correspondence matrix

The concrete opcode constants and Lean constructors are:

| Concrete opcode | Lean constructor | Required correspondence |
|---|---|---|
| `CONST_I` (1) | `constInt` | Same destination and signed-64 value; write initialized integer; advance PC |
| `CONST_B` (2) | `constBool` | Same destination and boolean; write initialized boolean; advance PC |
| `ADD_I` (3) | `add` | Same checked sum or `integerOverflow`; left-read error precedence; write only on success |
| `SUB_I` (4) | `sub` | Same checked difference or `integerOverflow`; preserve operand-read precedence |
| `MUL_I` (5) | `mul` | Same checked product or `integerOverflow`; preserve operand-read precedence |
| `DIV_I` (6) | `div` | Same truncation-toward-zero quotient; zero divisor and MIN/-1 trap |
| `REM_I` (7) | `rem` | Same dividend-sign remainder; zero divisor traps; MIN/-1 returns zero |
| `EQ_I` (8) | `equal` | Same integer equality and boolean destination |
| `LT_I` (9) | `lessThan` | Same signed integer ordering and boolean destination |
| `NOT_B` (10) | `booleanNot` | Same boolean negation |
| `JUMP` (11) | `jump` | Same target PC; no sequential fall-through |
| `BRANCH` (12) | `branch` | Same condition read and selected target |
| `RET` (13) | `retInt` or `retBool` | Validator's return type selects the matching abstract constructor; same payload and terminal PC |
| `RET_VOID` (14) | `retVoid` | Same void terminal outcome |
| `TRAP` (15) | `explicitTrap` | Explicit reason maps losslessly to a defined abstract trap/payload |
| `MOVE` (16) | `move` | Same typed source read and destination write; advance PC |

This table is not itself a proof. For every row, prove both success and failure behavior, including which fields remain unchanged on failure. In particular, a trap must not partially write the destination register.

## One-dispatch simulation obligation

For every validated concrete/abstract pair related by (R), with both machines running and with fuel available, a single concrete dispatch must correspond to exactly one abstract machine step.

For a continuing instruction:
- the concrete dispatch counter increases by exactly one;
- the post-state PC and register file relate to the abstract `nextState`;
- every non-destination register remains unchanged;
- destination initialization and payload agree;
- the fuel relation is preserved.

For a terminal instruction:
- the dispatch counter still increases by exactly one;
- the concrete terminal state projects to the same abstract `halt`, `haltVoid`, or `trap`;
- the final PC convention agrees (the terminal instruction's own PC for return/trap; selected target for branch/jump);
- register state is unchanged unless the instruction semantics explicitly writes one.

The proof must cover all 17 opcode constructors. It must not prove only arithmetic and infer control-flow correctness.

## Fuel correspondence

The concrete evaluator checks `steps >= max_steps` before checking the PC and before fetching/dispatching. After a valid fetch it increments `steps` before opcode dispatch.

The abstract `consumeStep` succeeds exactly when `used < limit`, increments by one, and otherwise returns `instructionLimit`.

Required lemmas:

1. If fuel is available, the concrete and abstract fuel checks both permit dispatch.
2. A dispatched instruction increments both counters exactly once, including a dynamic-trap or terminal instruction.
3. If fuel is exhausted, neither machine dispatches an instruction; PC and registers are unchanged; the terminal projection is the corresponding instruction-limit trap.
4. Calling the concrete step function after it is already halted is a stutter (no counter or state change); the harness must not count that as a dispatch.

The concrete trap spelling `step_limit_exceeded` and abstract `.instructionLimit` require an explicit mapping.

## Validation and construction boundary

The harness must use `ccam_machine_create_validated`, not `ccam_machine_create_valid`. The latter is an unchecked in-memory convenience constructor and does not establish the validator precondition.

The concrete validator and Lean proof-profile validator are not currently shown to be equivalent. The Lean module explicitly documents that its final-instruction-terminal condition is stronger than normative CCAM v0.1. Therefore prove only the chosen profile's admitted subset, and separately establish that every test input admitted by the concrete profile is representable in the Lean profile. Do not claim full normative validator equivalence.

For rejected inputs, the harness must assert:
- construction reports failure;
- no executable machine is returned as a successful result;
- the evaluator dispatch count remains zero;
- the rejection category is checked against a documented mapping, not guessed from error text.

## Trap mapping and unresolved semantic questions

The Lean model has a finite `Trap` type. The concrete evaluator uses strings. A total, reviewed mapping is required for at least:

| Concrete trap string | Candidate Lean constructor | Status |
|---|---|---|
| `integer_overflow` | `.integerOverflow` | Expected mapping; prove |
| `division_by_zero` | `.divisionByZero` | Expected mapping; prove |
| `uninitialised_register` | `.uninitialisedRegister` | Expected mapping; prove |
| `invalid_register` | `.invalidRegister` | Expected mapping; prove |
| `register_type_mismatch` | `.typeMismatch` | Expected mapping; prove |
| `step_limit_exceeded` | `.instructionLimit` | Expected mapping; prove |
| `invalid_program_counter` | `.invalidControlFlow` | Requires precondition argument; unreachable for valid related states |
| `explicit_trap` | `.explicitTrap reason` | Not automatically equivalent; payload must be represented losslessly |

The concrete evaluator also carries `trap_detail`. The current abstract `Trap` constructors do not obviously preserve arbitrary explicit-trap strings. Resolve this before asserting exact explicit-trap equivalence: either restrict the proof profile to a closed enumerated reason mapping, or extend the abstract outcome with a payload-bearing explicit trap. Do not discard detail.

The validator's error strings (`invalid_register_type`, structural operand errors, invalid targets, return mismatch, and related errors) are admission failures, not runtime traps. Keep their mapping separate.

## Corpus partition for #269

The canonical corpus must be partitioned by intended semantics rather than blindly passed through one evaluator path:

- SF-001–SF-014 and SF-021–SF-023: admitted executable SF-P cases (17).
- SF-015–SF-018: negative admission cases (4); assert rejection and zero dispatch.
- SF-019: normative-accepted / SF-P-rejected differential case; exercise the normative path separately, not the SF-P evaluator.
- SF-020: proof-harness-only nonzero raw entry case; check in the Lean/profile harness, not as a normative concrete evaluator input.
- SF-X01: out-of-profile explicit-trap case; keep separate until trap semantics and #265 are reconciled.

This partition is the assurance interpretation recorded on #269; the corpus validator must enforce the required expected-result schema for each disposition before the corpus can serve as a reliable oracle.

## Required proof and test sequence

1. **Corpus schema gate:** reject missing disposition-specific outcome, trace, step, or payload fields.
2. **Concrete conformance harness:** run admitted cases through validated construction and compare exact trace, steps, PC, outcome and payload. Run negative/differential/profile-only partitions through their proper paths.
3. **Representation lemmas:** establish that concrete validated construction yields a register-file relation and that concrete writes preserve it, using existing RuntimeBridge lemmas only after connecting their abstract record model to actual Capstan field/list semantics.
4. **Opcode simulation:** prove per-opcode success/failure correspondence.
5. **Control-flow simulation:** prove jump/branch targets and terminal-PC conventions.
6. **Fuel simulation:** prove pre-dispatch exhaustion and one-count-per-dispatch.
7. **Whole-run theorem:** induct over the number of dispatched instructions to establish trace and terminal-outcome correspondence for all validated profile programs.
8. **Implementation binding:** bind proof assumptions to source/compiler revisions and add negative controls demonstrating that deliberate semantic mutations cause proof/test failure.

A green vector suite is conformance evidence, not a proof of the universal simulation theorem. A Lean theorem over a model is not implementation evidence until the concrete operations and source revision are connected to its premises.

## Explicit non-claims

This contract does not establish:
- correctness of the Capstan compiler or runtime implementation;
- correctness of the native `List`, object, mutation, or integer semantics;
- equivalence of the concrete validator and normative CCAM validator;
- support for calls, frames, recursion, source lowering, JSON decoding, or other excluded features;
- whole-program resource safety;
- absence of all known or unknown vulnerabilities;
- a completed implementation-refinement proof.

The next implementation increment should add the concrete vector driver and exact trace assertions, then use its stable observation format as the target for the formal relation. Do not weaken the contract to match a failing implementation; investigate and resolve semantic discrepancies explicitly.
