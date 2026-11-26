# ECE / CCAM contract crosswalk

**Status:** implementation-aware research crosswalk; no end-to-end ECE or evaluator-refinement claim  
**Issue:** [#219](https://github.com/DavidFernee/Capstan/issues/219)  
**Snapshot:** main at commit `635eaf5d2e319bf4835c7ecae1ab316cd94b8ef2` (2026-11-26)  
**Normative authority:** [CCAM v0.1](../architecture/CCAM.md)  
**ECE proposal:** [Evidence-Carrying Execution](EVIDENCE-CARRYING-EXECUTION.md)  
**Obligation ledger:** [ECE proof and implementation obligations](EVIDENCE-CARRYING-EXECUTION-OBLIGATIONS.md)

## 1. Executive summary

The repository has meaningful integrated CCAM implementation, test and model-proof increments. It does **not** yet have evidence-carrying execution, a complete normative CCAM implementation, a whole-program Lean machine for the concrete multi-function evaluator, or a refinement theorem connecting that evaluator to the Lean model.

This crosswalk separates four evidence classes:

1. **Normative contract:** what CCAM v0.1 requires.
2. **Executable implementation and tests:** what current Capstan code implements and tests.
3. **Formal model/theorems:** what Lean proves about the formal objects it defines.
4. **Missing link:** what remains unproved, unimplemented or unbound to the exact executable artefact.

A test does not discharge a theorem obligation. A theorem about a Lean model does not establish that the concrete Capstan evaluator refines that model. A successful build or native executable does not establish source-to-platform correctness.

### 1.1 Integrated mainline foundation

The following PRs are merged and are part of the implementation history:

| PR | Integrated increment | Merge commit |
|---|---|---|
| #142 | Capstan-native single-frame evaluator | `992b5b017c56045ac1391aa68fd95deba18b407c` |
| #151 | Lean single-frame validation model/proofs | `360043c8704546857caa4c82f2978c7709399016` |
| #163 | Bounded typed in-memory structural validator | `294d34361c31dc768e60a017a3fd0718f7a00313` |
| #207 | Bounded multi-function call-frame evaluator | `d7a1196370d3afd3e8ee1230b886929f4e306f28` |
| #210 | Checked scalar source-to-CCAM lowering | `d635940c209d28b569f4776b3e443ab9632bf7f1` |
| #212 | Experimental freestanding Linux x86-64 backend | `2b3f0cebea767837dd5e56a6afe69355ad4db62e` |

The current implementation is in Capstan source:
- `verification/ccam_core.cap`: single-frame arithmetic, typed registers, instruction execution, step budget, in-memory validation, byte-output extension and associated tests.
- `verification/ccam_calls.cap`: multi-function frames, call-site side tables, signatures, recursive calls, shared step/depth limits, aggregate admission and associated tests.
- `verification/ccam_lowering.cap`: checked scalar source lowering, loops, direct calls, literal print lowering and associated tests.
- `verification/ccam_native_x64.cap` and `tools/native_driver.cap`: experimental native path.

The executable implementation is materially ahead of the Lean whole-machine model, but it remains transitional relative to the normative JSON CCAM contract.

## 2. Contract reconciliation: terminality and fall-through

### 2.1 Normative rule

CCAM v0.1 specifies reachability-based control-flow validation:
- control-flow analysis begins at instruction 0;
- every reachable nonterminal instruction must have an in-function successor;
- a reachable infinite loop is permitted;
- unreachable instructions must still satisfy schema, index and static-type rules;
- an unreachable nonterminal final instruction does not itself cause a fall-through error.

This is explicit in the control-flow paragraph of [CCAM.md](../architecture/CCAM.md).

### 2.2 Executable validator rule

The current Capstan single-frame validator in `verification/ccam_core.cap` uses a worklist over reachable instructions and implements that rule. It includes tests named:
- `CCAM validator rejects invalid branch targets and reachable fallthrough`;
- `CCAM validator permits unreachable fallthrough but validates unreachable instructions`;
- `CCAM validator accepts unreachable nonterminal final instruction`.

The multi-function validator in `verification/ccam_calls.cap` also has a reachability worklist in `ccam_validate_function_control_flow`, with terminal cases for return/void-return/explicit-trap and successor checks for reachable nonterminal instructions.

### 2.3 Lean proof-profile rule

The Lean model in `verification/lean/CapstanVerification/Machine.lean` defines `FiniteProgram` with a proof field requiring the final instruction to satisfy `machineInstrIsTerminal`. `ProgramValidator.lean` carries this through `validateSingleFrameProgram`. Its comments explicitly state that this is stronger than normative CCAM v0.1: it rejects an unreachable nonterminal final instruction even where no reachable path falls off the function.

The model also has a deliberately restricted `validateSingleFrameProfile` that requires entry PC zero, matching the concrete single-frame evaluator's start-at-zero behaviour.

### 2.4 Resolution for the first ECE target

Freeze the initial proof/certificate target as **CCAM-SF-P** (single-frame proof profile), a documented conservative subset of normative CCAM v0.1:

- entry PC is zero;
- no function calls;
- no byte-output extension;
- only the instruction constructors represented by the Lean single-frame model;
- all register, operand, target and return-type checks are satisfied;
- the final instruction has an explicit control effect, as required by the current Lean `FiniteProgram` representation;
- the shared instruction budget is enforced.

This resolves the mismatch for the first certificate target without changing normative CCAM semantics: every CCAM-SF-P program is intended to be a valid CCAM v0.1 program, but some valid normative programs are deliberately excluded. In particular, the current executable validator accepts the unreachable-nonterminal-final test vector while CCAM-SF-P rejects it. The certificate checker must expose that conservative rejection; it must not claim to implement the full normative acceptance predicate.

For a later profile that aims to cover the full normative single-frame subset, replace the unconditional `last_is_terminal` premise with a formal reachability/no-reachable-fall-through predicate and prove it sound. Do not weaken the normative contract to fit the current Lean representation.

## 3. Additional semantic and representation mismatches

### 3.1 Internal byte-output opcode is not normative CCAM v0.1

The current executable evaluator defines `CCAM_OP_EMIT_BYTES` (opcode value 18), stores byte payloads in `CCAMInstruction.byte_data`, appends to an in-memory output buffer and enforces `max_output_bytes` (default ceiling 1 MiB). Tests cover exact append, one-step charging, empty output, invalid byte values, atomic budget rejection and aggregate literal limits across functions.

The source lowerer emits this instruction for literal `print`/`println` calls. The normative CCAM v0.1 instruction table in `docs/architecture/CCAM.md` does not include `emit_bytes`; its JSON decoder proposal likewise has no normative output opcode. The current output operation is therefore an implementation extension, not part of the versioned v0.1 instruction set.

**Resolution:** exclude `emit_bytes` from CCAM-SF-P and from any v0.1 certificate. Keep the current source-lowering/output tests as evidence for an experimental extension only. If output is to become normative, specify its effect, output byte unit, accounting point, atomicity, trap outcome and host/adapter boundary in a new CCAM version before treating it as part of ECE.

### 3.2 Multi-function calls use transitional side tables

Normative CCAM represents a call as a closed instruction object containing the callee function name, argument-register list and nullable destination. The current `ccam_calls.cap` representation stores a `CCAMCallSite` side-table record containing instruction index, callee function-table index, argument registers and destination metadata. `CCAMInstruction` itself does not carry the normative named-call JSON object.

The multi-function validator checks function names, signatures, call-site indices and aggregate bounds in this in-memory representation. The evaluator uses a lookup table from instruction index to side-table entry. This is a real executable call-frame increment, but it is not the normative external program representation or a completed decoder.

**Resolution:** keep multi-function execution outside CCAM-SF-P. Before a multi-function ECE profile, define the mapping from normative named calls to the internal representation and prove that decoding/validation preserves function identity, argument order, return destination and call-site uniqueness. Do not treat side-table indices as the canonical program format.

### 3.3 JSON decoder remains a proposal

`docs/architecture/CCAM-JSON-DECODER.md` explicitly labels itself an implementation-contract proposal, not yet implemented or normative CCAM v0.1. It specifies iterative bounded parsing, duplicate-key detection after escape decoding, exact integer parsing, closed objects, bounded strings/containers and whole-program validation before executable-state construction.

Current `ccam_core.cap` and `ccam_calls.cap` validate already-decoded in-memory Capstan values. They do not parse untrusted JSON, detect duplicate JSON keys, validate raw UTF-8/escapes or prove exact JSON number handling.

**Resolution:** no certificate may be described as validating arbitrary CCAM JSON until the bounded decoder is implemented and its raw-input-to-typed-program relation is proved or independently validated. The first profile should use a precisely frozen, bounded encoding and reject unsupported fields/opcodes.

### 3.4 Native backend status metadata

The opening status paragraph of `docs/architecture/CCAM.md` described the freestanding Linux x86-64 backend as "proposed in PR #212". PR #212 is merged (merge commit above). The correct status is that an experimental Linux x86-64 backend is integrated; it does not establish a CCAM-to-native refinement theorem or a complete source-to-platform correctness chain.

The metadata correction is included with this crosswalk. No CCAM instruction semantics are changed.

## 4. Implementation, tests and formal model by layer

### 4.1 Executable source and colocated tests

| Layer | Main source | Current integrated behaviour | Representative tests | Boundary |
|---|---|---|---|---|
| Arithmetic | `verification/ccam_core.cap` | Checked signed-64 add/sub/mul/div/rem; zero division and overflow traps; truncation toward zero | overflow, MIN/-1, remainder sign and divide-by-zero tests | Tests exercise Capstan implementation; no full evaluator refinement theorem |
| Registers | `verification/ccam_core.cap` | Typed int/bool registers, initialisation state, invalid-index/type rejection | register type, uninitialised state and constructor rejection | Formal runtime-register bridge is a model, not whole evaluator simulation |
| Single-frame execution | `verification/ccam_core.cap` | Arithmetic, moves, comparisons, branches/jumps, returns, explicit traps, shared step counter | checked arithmetic, branch arms, trap precedence, void halt, invalid PC/opcode and step-boundary tests | In-memory instruction sequence; no JSON decoder |
| Single-frame validation | `verification/ccam_core.cap` | Register/opcode/target/type/return checks; reachability worklist; bounded instruction/register and byte-literal admission | reachable fall-through, unreachable final instruction, backward CFG, return contracts, malformed program | Not full normative JSON/whole-program validation |
| Multi-function execution | `verification/ccam_calls.cap` | Function frames, argument transfer, direct/recursive calls, continuations, atomic return preflight, shared steps/depth | int/bool/void calls, recursion, depth boundary, argument order, return failure atomicity | Internal call-site side tables, not normative named-call JSON |
| Multi-function validation | `verification/ccam_calls.cap` | Function uniqueness/signatures, call-site mapping, control flow, aggregate functions/registers/instructions/args/name bytes | signature mismatch, count/aggregate limits, invalid names and call-site bounds | In-memory data only; no raw decoder |
| Source lowering | `verification/ccam_lowering.cap` | Checked scalar locals/arithmetic, while/for, break/continue, direct calls/recursion, literal output | source subset, loop patching, recursive calls, void/bool calls, print literal and unsupported construct tests | Tests only; no formal source-to-CCAM simulation |
| Native backend | `verification/ccam_native_x64.cap`, `tools/native_driver.cap` | Experimental Linux x86-64 freestanding emission/driver path integrated by #212 | Native backend fixtures/CI in the backend workstream | No proof that generated native code simulates all CCAM outcomes/effects/resources |

The tests are declared in Capstan source and run through the repository test harness. They are executable evidence for the tested cases, not proofs of all executions.

### 4.2 Lean model and theorem inventory

| Lean module | Existing formal object/result | What it proves | What it does not prove |
|---|---|---|---|
| `Machine.lean` | Typed single-frame `MachineInstr`, `FiniteProgram`, `MachineState`, `machineStep`, budgeted step | Typed register/PC invariants; step counter increment/limit; call-stack push/pop lemmas over a generic frame type | No call instruction or integrated multi-function machine; no concrete evaluator simulation |
| `Progress.lean` | `machineStep_progress_or_explicit_outcome`, determinism, bounded `runFuel` residual-state typing | Functional one-step outcome classification/determinism for the current single-frame model | Not whole-program multi-function progress; meta-fuel exhaustion is not CCAM `step_limit_exceeded` |
| `ProgramValidator.lean` | Raw single-frame instruction validation and `validateSingleFrameProfile` | Bounded indices, typed instructions, return-contract rejection, entry-zero profile, conservative final-terminal condition | Not full JSON/whole-program validator soundness; profile is stricter than normative reachability acceptance |
| `Validator.lean` | Single decoded-instruction conversion to intrinsically typed syntax | Successful raw instruction conversion produces typed machine syntax and bounded targets | Not a JSON decoder, whole-program validation or implementation refinement |
| `RuntimeBridge.lean` | `RuntimeRegisterFileRelation`, read/write preservation/correspondence | Representation-level register read/write properties under an explicit relation | Does not prove the concrete CCAM evaluator establishes/preserves that relation at every machine step |
| `NativeRegisterBridge.lean` | Native-style register model and type/read/write correspondence | Model-level native register representation and operation lemmas | Not a whole native backend refinement theorem |
| `ExplicitTrap.lean` | Explicit-trap reason byte model and dispatch | Detail preservation and model-level step/exhaustion behaviour | Not proof that the executable evaluator/decoder matches the model |

Key theorem names currently present include:
- `machineStep_preserves_well_typed`, `machineState_pc_is_in_range`;
- `consumeStep_increments`, `consumeStep_within_limit`, `consumeStep_exhausted_traps`;
- `pushCallFrame_top`, `pushCallFrame_increments_depth`, `pushCallFrame_within_limit`, `popNestedCallFrame_restores_caller`;
- `machineStep_progress_or_explicit_outcome`, `machineStep_deterministic`;
- `validateMachineInstr`-related return/index/type results and `validateSingleFrameProfile_entry_zero`;
- `runtimeWriteRegister_preserves_relation`, `runtimeReadInt_corresponds`, `runtimeReadBool_corresponds`;
- `explicitTrap_preserves_detail`, `explicitTrap_dispatch_consumes_one`.

The call-stack lemmas in `Machine.lean` are generic list/stack lemmas. They are not yet integrated into `MachineInstr`, `machineStep`, or a whole-program multi-frame state theorem.

## 5. ECE obligation crosswalk

The ECE obligation identifiers below retain their ledger status: **all theorem/implementation obligations remain open** unless and until the required artefact, exact revision, assumptions and reproduction procedure exist. "Implementation evidence" below means partial code/tests exist; it does not close the obligation.

### A. Semantic identity and certificate format

| ID | Normative/source evidence | Implementation/tests | Formal evidence | Missing link / dependency |
|---|---|---|---|---|
| ECE-001 canonical encoding and semantics ID | CCAM v0.1 JSON schema and CCAM.md define intended program/function/opcode fields | No canonical encoder or raw JSON decoder | No canonical-byte/hash theorem | Choose profile/version, canonical bytes, exact scalar/Unicode rules and digest domain; decoder/checker owner |
| ECE-002 certificate schema and bounded decoder | CCAM-JSON-DECODER.md is a proposal only | No certificate decoder; in-memory validators receive typed values | No decoder soundness theorem | Closed versioned certificate schema, size/depth/node limits, duplicate/unknown-field rejection and bounded parse |
| ECE-003 binding | ECE proposal specifies digest, semantics, limits and capability manifest conceptually | No evidence bundle or mutation suite | No binding theorem | Bind exact canonical bytes, semantics/profile, resource limits, grants and checker identity; add stale/mutated-field tests |
| ECE-004 acceptance predicate | CCAM.md gives normative structural and dynamic preconditions | Partial single-/multi-function validators implement subsets | Lean raw instruction/profile predicates only | Define formal accepted-program predicate for the exact certificate profile; include decoder and aggregate limits |
| ECE-005 checker soundness | Required by ECE proposal | No independent certificate checker | Instruction-level validator lemmas only | Prove acceptance implies the exact formal predicate; no producer trust |
| ECE-006 completeness/conservatism | Normative v0.1 defines broader acceptance than current Lean proof profile | Runtime validator accepts unreachable nonterminal final instruction; Lean profile rejects it | `validateSingleFrameProfile` is deliberately conservative | Name/profile the accepted subset and classify rejected valid-v0.1 programs as unsupported, not invalid |

### B. Execution correspondence

| ID | Normative/source evidence | Implementation/tests | Formal evidence | Missing link / dependency |
|---|---|---|---|---|
| ECE-010 whole-program small-step semantics | CCAM.md specifies frames, calls, returns, traps and shared counters | ccam_core and ccam_calls implement single-/multi-frame transitions | Lean Machine.lean models only single-frame transitions | Define versioned whole-program model including function table, call-site, continuation, output extension exclusion and trap ordering |
| ECE-011 state invariants | CCAM.md specifies typed registers, PC, frame and resource bounds | Concrete state structs track registers, PC, frame depth, steps and output | Lean register/PC typing invariants and generic CallStack bounds | Whole-stack typed frame/continuation invariants and relation to concrete CCAMCallMachine |
| ECE-012 preservation/progress | Normative dynamic checks/traps | Many positive/negative evaluator tests | Single-frame preservation/progress classification/determinism | Extend Lean machine to calls/returns and prove the exact selected profile's preservation/progress-or-trap |
| ECE-013 concrete evaluator relation | Concrete structs in ccam_core/calls | Runtime implementation uses CCAMRegister/CCAMFrame and list state | RuntimeBridge/NativeRegisterBridge define abstract representation relations | Define relation over full concrete machine state, call frames, PC, counters, outputs and trap fields |
| ECE-014 one-step simulation | Normative instruction outcomes and order | ccam_machine_step / ccam_call_machine_step implement transitions | Register-level correspondence only | Prove each concrete success/trap transition corresponds to reference step and preserves observations |
| ECE-015 initial-state correspondence | CCAM entry/configuration contract | Constructors validate in-memory input and create entry state | Lean initialMachineState exists for formal state | Prove accepted profile program/config creates a related concrete entry state; decoder premise absent |
| ECE-016 terminal outcome correspondence | CCAM.md defines Halt/HaltVoid/Trap and trap fields/precedence | Evaluator records halt values, trap code/function/pc/detail; tests cover trap precedence and explicit detail | Lean MachineOutcome and ExplicitTrap model lemmas | Prove concrete outcomes match formal outcomes, including explicit detail, location, void/value and limit precedence |
| ECE-017 source lowering | Source language checker/lowering is integrated by #210 | ccam_lowering.cap has scalar, loop, call and literal-output tests | No source-to-CCAM simulation theorem | Freeze supported source subset and prove checker/lowering preserves semantics; exclude emit_bytes unless separately specified |
| ECE-018 native backend | Experimental backend integrated by #212 | Native driver/emitter and Linux x86-64 path exist | No full backend simulation theorem | Prove CCAM-to-native outcome/effect/resource refinement; define ABI/OS assumptions and test exact backend |

### C. Resource contracts

| ID | Normative/source evidence | Implementation/tests | Formal evidence | Missing link / dependency |
|---|---|---|---|---|
| ECE-020 units/accounting | CCAM.md normatively defines maxSteps/maxDepth; ECE proposes broader resource vector | Evaluator implements steps/depth and an extra 1 MiB output buffer ceiling | Lean StepBudget model | Define live heap, cumulative allocation, stack bytes, validation work and output semantics; classify emit_bytes as non-normative extension |
| ECE-021 shared fuel | CCAM.md specifies one instruction counter including call/return/trap | ccam_calls increments shared steps for calls/returns and reuses frame step state; boundary tests exist | consumeStep and budgetedMachineStep prove abstract counter properties | Prove concrete multi-frame counter monotonicity/no reset/wrap and exact one-step accounting |
| ECE-022 call-depth/stack | CCAM.md specifies maxDepth and preflight before push | ccam_calls enforces frame_depth/max_depth; depth tests exist | Generic CallStack push/pop lemmas | Prove concrete stack-depth correspondence and byte-accurate frame/stack ceiling including allocator/alignment overhead |
| ECE-023 function summaries | ECE proposal defines need for compositional summaries | No static summary system | No summary algebra | Define algebra for sequence/branch/loop/call/recursion and unknown callees; coordinate #221 |
| ECE-024 summary soundness | No normative static-bound semantics yet | No static analyser | No soundness theorem | Prove reported bound dominates all executions under explicit assumptions |
| ECE-025 evidence state | ECE proposal distinguishes static bounds/runtime ceilings conceptually | No typed evidence-state representation | No evidence-state theorem | Represent proved/runtime-enforced/measured/unknown without promotion; coordinate #221 |
| ECE-026 validator resource bound | CCAM-JSON-DECODER.md proposes raw input/aggregate limits | In-memory validators bound registers, instructions, functions, names, call sites, args and output literals; tests cover aggregate boundaries | No proof that validator work/allocation is bounded | Implement raw decoder, preflight all aggregate allocations and prove/check bounded work before execution |
| ECE-027 heap and I/O | ECE resource table specifies heap/I/O/adapter contracts | Byte output buffer has max-output check and atomic append tests; no heap allocator ledger or OS I/O adapter | No allocator/adapter refinement theorem | Couple exact allocation and host I/O accounting; failure atomicity, exact boundaries and adapter tests |

### D. Capability and effect contracts

| ID | Normative/source evidence | Implementation/tests | Formal evidence | Missing link / dependency |
|---|---|---|---|---|
| ECE-030 capability algebra | ECE and Anchor docs discuss desired capabilities; #222 survey reviews prior art | Existing grant/policy work is not a capability-typed CCAM contract | No CCAM capability algebra | Define kinds/scopes/operations/ceilings/delegation/revocation; coordinate Anchor and #222 |
| ECE-031 effect summaries | CCAM v0.1 has no general effect-row system | Internal emit_bytes extension only; no function effect summaries | No effect typing model | Define effects separately from authority; specify host operations and call summaries |
| ECE-032 authority inclusion | Normative call signatures validate value types only | No call-site capability requirements | No authority inclusion theorem | Add required-capability summaries and call-site subset check |
| ECE-033 attenuation/no escalation | No normative capability algebra | No typed attenuation path in CCAM | No no-escalation theorem | Define derivation/attenuation and prove no ambient acquisition |
| ECE-034 grant/provenance binding | ECE bundle sketches launch grant and provenance | No launch grant bound to program certificate | No grant-binding proof | Bind actual launch decision, grant digest, policy version and delegation chain |
| ECE-035 host-adapter mediation | CCAM v0.1 excludes IO and privileged host effects | No capability-gated host adapter in CCAM evaluator | No mediation theorem | Enumerate all privileged paths and prove/verify adapter gate; start with one bounded effect |
| ECE-036 secret non-disclosure | Language roadmap separates IFC/secret policies | No CCAM information-flow model | No non-interference theorem | Define confidentiality/integrity labels and declassification separately; coordinate #222 |

### E. Assurance integrity and reproducibility

| ID | Normative/source evidence | Implementation/tests | Formal evidence | Missing link / dependency |
|---|---|---|---|---|
| ECE-040 evidence freshness | ECE proposal names compiler/checker/toolchain identities | Git commits, CI runs and release provenance exist independently | No certificate freshness/binding theorem | Bind exact source, compiler, verifier, semantics, toolchain and target to evidence |
| ECE-041 proof dependency audit | Verification workflow and axiom-audit infrastructure exist | Lean project/build is run in formal workflow | Model-specific theorem/axiom audit, not ECE acceptance bundle | Pin exact proof commit, imports/axioms, checker/kernel and independent replay result |
| ECE-042 checker TCB | ECE proposal requires small independent checker | No certificate checker to measure | No checker TCB proof | Implement minimal checker; inventory dependencies/code size/complexity and attack surface |
| ECE-043 negative certificate suite | Existing evaluator tests reject malformed programs | No forged/stale/mismatched certificate tests | No certificate theorem | Add malformed, truncated, oversized, forged, stale, digest/semantics/limit/grant mutation vectors |
| ECE-044 reproducibility | Repository CI, test harness and formal workflow exist | tests/run.sh and pinned workflow jobs execute code/tests | Lean build reproducible at workflow level | Add one-command ECE reproduction for exact profile/certificate/checker/proofs and expected outputs |
| ECE-045 independent review | No ECE-specific independent review record | PR reviews exist for individual increments, not whole ECE argument | No independent review of complete proof chain | Assign reviewer independent of implementation/proof author; record issues and dispositions |

## 6. Smallest end-to-end ECE vertical slice

The smallest honest first slice is **CCAM-SF-P certificate validation and single-frame evaluation**, not the current multi-function/native path.

### Included

- Entry at instruction zero.
- Signed-64 integers and booleans.
- Typed, initially uninitialised registers.
- Constants, moves, checked arithmetic, comparisons, boolean negation, jump, branch, int/bool/void return and explicit trap.
- No calls, no heap, no strings, no byte output, no I/O, no concurrency, no grants/capabilities and no native backend.
- Conservative final-instruction explicit-control-effect restriction.
- One shared instruction budget, with exact pre-execution exhaustion semantics.

### Evidence sequence

1. Freeze profile ID, semantics ID, canonical encoding and exact accepted-program predicate.
2. Implement a bounded decoder for that closed profile; reject duplicate/unknown/missing fields and oversized input before constructing the typed program.
3. Implement a small independent checker. The producer may generate a certificate, but the checker recomputes or validates all acceptance-critical facts.
4. Bind the certificate to canonical program bytes, profile/semantics version and maxSteps. Any mutation must invalidate it.
5. Prove checker soundness against the Lean CCAM-SF-P predicate.
6. Prove the concrete single-frame evaluator refines the Lean machine for every instruction and observable outcome in the profile.
7. Run positive, negative, exact-boundary and mutation tests on the exact head; record proof dependencies and reproduce the build independently.

### Explicit exclusions

- Multi-function calls and side-table mapping: later increment after a whole-program Lean machine exists.
- emit_bytes: non-normative extension; exclude until specified in a new CCAM version.
- JSON general-purpose decoder: implement only the frozen bounded profile first, but do not claim arbitrary JSON conformance.
- Capabilities/effects/IFC: later increment; absence from the profile is not evidence of a general authority or confidentiality guarantee.
- Native backend: later source/CCAM/native refinement step.
- Heap/GC, dynamic allocation, wall-clock, concurrency and OS effects: later resource/host obligations.

This first slice demonstrates independent validation and concrete evaluator refinement for a closed deterministic subset. It does not yet demonstrate the full ECE proposition involving authority and broad resource guarantees.

## 7. Owners, dependencies and ordering

| Work package | Responsible role | Dependencies | Next evidence gate |
|---|---|---|---|
| Canonical profile/decoder/checker (ECE-001..006) | CCAM validator / assurance implementation | Normative CCAM v0.1; CCAM-SF-P decision; ECE schema | Bounded decoder tests, formal acceptance predicate, checker soundness |
| Whole-program semantics and evaluator refinement (ECE-010..016) | Formal verification + CCAM runtime | Current CCAM semantics; multi-frame evaluator; explicit outcome contract | Multi-frame Lean machine and exact-head simulation theorem |
| Source lowering (ECE-017) | Compiler/lowering | #210 merged source subset; CCAM-SF-P semantics | Source-to-CCAM simulation for the frozen source subset |
| Native backend (ECE-018) | Native backend | #212 merged experimental backend; CCAM semantics | Backend simulation/refinement for a stated target |
| Resource summaries/accounting (ECE-020..027) | CCAM runtime + Halyard/resource-analysis | #221 resource survey; current step/depth/output code | Resource algebra, static soundness and exact runtime accounting |
| Capability/effect/IFC (ECE-030..036) | Anchor/policy + language semantics | #222 survey; host adapter requirements | One bounded capability-gated effect with call-site inclusion and mediation |
| Evidence freshness/TCB/reproducibility (ECE-040..045) | Assurance/release engineering + independent reviewer | Checker and proof artifacts exist | Pinned bundle, negative certificate corpus, TCB inventory and independent replay |

No individual owner is inferred here. Work-package roles must be assigned explicitly in the coordination board before implementation starts.

## 8. Required corrections and next actions

1. Correct the CCAM.md status paragraph: PR #212 is merged; describe the backend as experimental/integrated, not proposed.
2. Keep the ECE obligation IDs open. This crosswalk records partial implementation/test/model evidence; it does not discharge the required proof or refinement predicates.
3. Adopt CCAM-SF-P as the first conservative proof/certificate profile, or separately fund the Lean reachability predicate if full normative single-frame acceptance is required.
4. Exclude emit_bytes and multi-function side-table calls from CCAM-SF-P; do not silently fold them into v0.1.
5. Implement the bounded raw decoder and canonical certificate before claiming acceptance of external CCAM documents.
6. Extend the Lean model to multi-function calls only after the single-frame evaluator relation is established.
7. Treat source lowering and native backend as separate later refinement links.
8. Coordinate resource analysis with #221 and capability/effect semantics with #222 before making ECE language contracts normative.

## 9. Snapshot and reproduction references

All statements in this crosswalk are pinned to main commit `635eaf5d2e319bf4835c7ecae1ab316cd94b8ef2`. The primary source files and proof modules inspected are:

- `docs/architecture/CCAM.md`
- `docs/architecture/CCAM-JSON-DECODER.md`
- `docs/architecture/CCAM-PROGRESS-RESULT.md`
- `verification/ccam_core.cap`
- `verification/ccam_calls.cap`
- `verification/ccam_lowering.cap`
- `verification/ccam_native_x64.cap`
- `tools/native_driver.cap`
- `verification/lean/CapstanVerification/Machine.lean`
- `verification/lean/CapstanVerification/Progress.lean`
- `verification/lean/CapstanVerification/Validator.lean`
- `verification/lean/CapstanVerification/ProgramValidator.lean`
- `verification/lean/CapstanVerification/RuntimeBridge.lean`
- `verification/lean/CapstanVerification/NativeRegisterBridge.lean`
- `verification/lean/CapstanVerification/ExplicitTrap.lean`
- `verification/README.md`
- `tests/run.sh`

The exact test/proof command and passing run identifiers must be attached to any future obligation closure. This document does not claim to have rerun the full test suite or formal build locally.
