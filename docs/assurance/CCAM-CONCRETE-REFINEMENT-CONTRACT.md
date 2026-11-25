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


## Additional validator audit (2026-11-26)

A source-level comparison of `ccam_validate_single_frame` at
`verification/ccam_core.cap` (blob
`b29b6190d2eb3d9998a6d13d620e2e67a8165d7c`) with
`validateSingleFrameProgram` / `validateSingleFrameProfile` in
`ProgramValidator.lean` identifies the following admission asymmetry:

- Both paths validate every instruction's opcode and operand typing, including
  unreachable instructions.
- The Lean profile requires the *last instruction in the entire instruction
  table* to be terminal.
- The concrete validator instead performs reachability from PC 0 and rejects
  fallthrough only when a reachable non-terminal instruction has no successor.
  It can therefore accept a program with an unreachable, non-terminal final
  instruction if all reachable paths terminate.
- Both implementation-alignment paths require entry zero: the concrete
  constructor starts at PC 0, while `validateSingleFrameProfile` adds the
  explicit raw-entry-zero condition.

This means the Lean proof profile is stricter for this case. It does not create
an unsafe admission relative to the concrete evaluator, but it prevents claiming
validator equivalence. The refinement theorem should state the direction it
actually needs: every Lean-profile-admitted program is accepted by the concrete
validator, with an explicit construction of the corresponding concrete input.
A separate theorem is needed if equivalence is desired.

A second boundary is explicit traps. The concrete validator accepts trap
reason strings matching `[a-z][a-z0-9_]{0,63}`; the Lean instruction model
accepts only values of its finite `Trap` inductive. This is not a total
bijection. The current SF-P corpus gate rejects explicit-trap instructions, and
SF-X01 remains out of profile. Keep explicit traps outside the implementation
simulation theorem until the profile states a closed reason mapping or the
abstract outcome carries the concrete payload.

These are source-inspection findings, not executed tests or proved theorems.


## Terminal-state and budget correspondence refinement

The abstract machine currently exposes `MachineOutcome` as `nextState | halt Val | haltVoid | trap Trap`. Its terminal constructors do not carry a post-state. The concrete `CCAMMachineState` retains observable terminal fields (PC, steps, halted, halt_has_value, integer and boolean return slots, trap_code, trap_detail). A refinement theorem must therefore use either an enriched abstract terminal result or a relational postcondition over the concrete pre-state and abstract outcome. Direct equality between the current `MachineOutcome` and the concrete post-state is not a meaningful relation.

Required terminal obligations:

- For return and dynamic trap after dispatch, the concrete PC remains the dispatched PC and the dispatch counter increases exactly once.
- For pre-dispatch budget exhaustion, PC and dispatch count remain unchanged; the concrete step-limit trap is projected to the abstract instruction-limit outcome.
- Integer return sets the integer payload and clears the boolean payload; boolean return sets the boolean payload and clears the integer payload; void return clears both payloads. Trap outcomes do not claim a return payload.
- Trap correspondence must include both reason and detail, or explicitly state which detail is abstracted away. A reason-only theorem is not a full terminal-state equivalence theorem.
- For binary arithmetic, concrete evaluation reads the left operand before the right. A failing left read prevents the right read and arithmetic. The simulation proof must preserve this observable error precedence.

The existing `budgetedMachineStep_consumes_one` theorem establishes abstract budget consumption when dispatch is permitted, and `budgetedMachineStep_exhausted_before_instruction` establishes abstract exhaustion before instruction execution. Neither theorem alone relates the concrete mutable `steps` field or terminal payloads to the abstract result. That bridge remains an explicit proof obligation.

This section refines the proof plan only. It does not add a theorem, execute a new proof, or upgrade the evidence classification of the current Lean results.


## Reachability invariants required by the concrete state relation

Inspection of `ccam_machine_create` and `ccam_machine_step` in the pinned concrete evaluator identifies additional invariants that the simulation theorem must state explicitly. The validated constructor initializes `pc = 0`, `steps = 0`, both return slots to zero, `halted = false`, `halt_has_value = false`, and empty trap code/detail. The constructor snapshots the instruction list. The theorem's initial-state relation must include these facts and the validated-program precondition; it must not quantify over arbitrary mutable `CCAMMachineState` values.

For states reachable by repeated calls to `ccam_machine_step` from that constructor, the proof must establish:

- A non-halted state has no terminal trap code/detail and no return payload; the return slots remain their initialized neutral values until a successful `CCAM_OP_RET`.
- A successful value return writes exactly one typed payload, clears the other typed payload, sets `halted` and `halt_has_value`, and leaves PC at the dispatched return instruction.
- Void return sets `halted`, clears `halt_has_value`, and leaves the initialized return slots unchanged.
- A dynamic trap uses `ccam_machine_trap`, which sets `halted`, clears `halt_has_value`, writes the trap code and clears `trap_detail`; it does not itself clear either return slot. Thus the “both return slots are neutral on trap” property follows only from the reachable-state invariant that no return can have occurred before a trap (a return halts execution), plus constructor initialization. It is not a local postcondition of the trap helper for arbitrary states.
- An explicit trap sets `trap_code = "explicit_trap"` and preserves its validated reason in `trap_detail`; it likewise leaves return slots unchanged.
- An already-halted state is inert. Step-limit exhaustion occurs before PC validation, fetch and increment; invalid-PC trapping also occurs before increment. All post-fetch instruction outcomes increment `steps` exactly once, including dynamic traps and terminal instructions.

This exposes a useful proof boundary: prove the constructor/reachability invariant first, then prove the transition simulation only for states satisfying it. Do not state payload clearing as an unconditional property of `ccam_machine_trap`. External mutation of the returned concrete state is outside this transition-system theorem and must be excluded from the theorem's execution model or handled by a stronger encapsulation argument.


## Trap-domain partition and defensive states

The current Lean `Trap` type is finite: `integerOverflow`, `divisionByZero`, `uninitialisedRegister`, `invalidRegister`, `typeMismatch`, `invalidControlFlow`, `callDepthLimit`, and `instructionLimit`. The concrete evaluator uses string trap codes and also has defensive codes that are not represented by this Lean type, including `invalid_program_counter`, `invalid_instruction`, `invalid_register_type`, and `invalid_step_limit` (constructor failures), alongside the ordinary dynamic codes.

The theorem must partition these cases rather than silently treating the finite Lean sum as the complete concrete trap domain:

1. **In-profile dynamic traps:** establish a total mapping for the dynamic codes reachable from a program admitted by the single-frame profile. At minimum, check exact correspondence for integer overflow, division by zero, uninitialised register, invalid register and type mismatch. Preserve the concrete code and any detail projection in the relation.
2. **Precondition/constructor rejection:** invalid register type and invalid step limit are constructor rejection results, not instruction outcomes. Model these in a separate construction theorem or explicitly exclude them by the validated-constructor hypothesis.
3. **Defensive impossible-state traps:** invalid program counter and invalid instruction protect internal callers that violate the validated-program/reachability assumptions. They should be covered by a separate fail-closed safety theorem if the public API can expose such states; they are not ordinary outcomes of the profile simulation theorem.
4. **Explicit trap:** concrete `explicit_trap` plus arbitrary validated reason text is not represented by the current finite Lean `Trap` constructors. Keep it outside the main theorem until the abstract domain carries a reason payload or the admitted reason language is mapped precisely.
5. **Step exhaustion:** concrete `step_limit_exceeded` must map to Lean `.instructionLimit`, but it occurs before dispatch and consumes no step. This is distinct from every post-fetch dynamic trap.

A theorem advertised as full concrete trap equivalence is premature until these partitions are either mapped or explicitly excluded in its hypotheses. In particular, a one-way theorem for the validated SF-P profile is acceptable as a first milestone; it must not be described as equivalence of the entire concrete API.


## Shared SF-P corpus checks (mainline continuation PR #391)

The canonical `verification/ccam_sf_vectors.json` corpus now feeds three paths:

1. `scripts/validate-ccam-sf-vectors.py` performs strict corpus/schema/resource validation.
2. `scripts/run-ccam-sf-vectors.py` executes 17 admitted and 4 normative-invalid in-profile vectors against the concrete Capstan evaluator, comparing exact PC traces, step counts, terminal PC and trap/return projections. It also asserts that SF-019 is normatively accepted and constructs no profile machine; SF-020 remains Lean/profile-only and SF-X01 remains out-of-profile.
3. `scripts/generate_ccam_sf_lean_vectors.py` generates Lean `RawSingleFrameProgram` definitions from the same JSON. The default Lean build checks 23 profile-admission theorems and 23 machine execution/non-execution theorems. Accepted vectors run through `budgetedMachineStep` from uninitialised registers under the vector's instruction budget; the theorems compare exact model outcome/trap, return value, PC, step count and dispatched-PC trace. Rejected profile vectors prove no executable profile program is produced.

This is stronger than profile-only validation: the same corpus now checks both concrete and Lean machine behavior. It remains **test-level cross-model evidence, not a refinement proof**. The concrete and Lean evaluators are separately implemented; no initial-state relation, one-step simulation theorem or exact concrete/abstract budget correspondence has yet been proved. In particular, the current `MachineOutcome` terminal cases still omit concrete post-state fields, and the runtime/native bridge proofs cover selected register representation rather than whole-evaluator refinement.
