# Integrated formal assurance architecture

**Review baseline:** mainline commit `3187b3adc3d9b2f5476c2d25ed410da1ec1c88ce` (2026-11-27).  
**Formal toolchain:** Lean 4.19.0 (`verification/lean/lean-toolchain`).  
**Status:** repository review and target architecture; implementation-refinement theorem not yet established.

## 1. Decision

Capstan should have one compositional semantic spine for its executable language and compiler pipeline. Existing Lean modules are retained as component specifications and proof libraries, but no component theorem is promoted to an end-to-end guarantee until it is connected to the shared machine state and to the implementation boundary it claims to cover.

The programme is not a rewrite of all existing Lean files. It is an integration and refinement programme:

1. Freeze the normative source, typed-IR, CCAM and runtime contracts.
2. Build one validated, whole-program CCAM semantics over functions, heterogeneous frames, budgets, output and terminal outcomes.
3. Reuse existing arithmetic, register, validator, frame, output and representation lemmas as component results.
4. Prove whole-machine preservation, progress-or-terminal-outcome, determinism and resource invariants.
5. Prove the concrete Capstan implementation refines that semantics.
6. Compose source-to-IR, IR-pass, IR-to-CCAM and CCAM-to-native simulations.

The evidence vocabulary remains strict: **model theorem**, **implementation correspondence**, **composed compiler theorem** and **independent validation** are separate evidence classes.

## 2. Repository inventory and existing proof assets

The review found 37 Lean source files in the mainline tree. They are not all parts of one connected execution semantics.

### 2.1 CCAM scalar and single-frame core

| Existing module | What it establishes | Boundary still open |
|---|---|---|
| `Core.lean` | Signed-64 values, integer/Boolean types, typed register operations, arithmetic and scalar-operation lemmas | Exact correspondence to all concrete Capstan primitives and complete evaluator transitions |
| `Machine.lean` | Fin-indexed single-frame instruction subset, typed state, PC bounds, separate step-budget wrapper and call-stack utility | No function table, call instruction, integrated frame stack or output state |
| `Validator.lean` | One decoded raw instruction can be converted to intrinsically typed instruction data | Not a decoder or whole-program validator |
| `ProgramValidator.lean` | Restricted single-frame program admission, bounded indices and proof-profile constraints | Not equivalent to the full normative validator; the profile requires a terminal last instruction |
| `Progress.lean` | Outcome classification, determinism and fuelled-run facts for the current total single-frame function | Does not prove progress for the complete multi-function CCAM machine |
| `SFVectors.lean` | Lean model executions/admission theorems generated from the shared SF-P vector corpus | Differential corpus evidence is not a universal simulation theorem |

The single-frame proof model is deliberately smaller than normative CCAM. In particular, its `FiniteProgram` carries an intrinsically valid finite code vector and a last-instruction terminal condition. These are useful proof-profile constraints, not a proof that arbitrary normative CCAM input has been validated.

### 2.2 Calls, frames and runtime representation

| Existing module | What it establishes | Boundary still open |
|---|---|---|
| `MultiFunction.lean` | Function signatures, parameter/register type alignment, typed arguments and frame initialisation | No function-table validation or concrete call dispatch refinement |
| `MultiFrame.lean` | Heterogeneous typed frames, callee construction, return-destination checks, caller write preservation, abstract stack push/pop facts | No ordinary instruction dispatch over the stack, call-site lookup, step accounting or concrete `ccam_calls.cap` refinement |
| `RuntimeBridge.lean` | Mathematical list-register representation relation and abstract read/write correspondence | Does not prove Capstan List/object semantics |
| `NativeRegisterBridge.lean` | Native-shaped type tags, field values and register operations correspond to abstract records | Still a manually mirrored data model |
| `NativeRegisterFileBridge.lean` | List-slot operations and native/runtime register relation | Does not prove the actual Capstan list implementation |
| `InitialStateBridge.lean` | Native-shaped register constructor defaults correspond to abstract initial registers | Does not prove the actual machine constructor and decoder |
| `NativeMachineBridge.lean` | Initial machine projection, PC advance and pre-dispatch fuel admission correspondence | Does not prove opcode dispatch, complete state transitions, terminal observations or calls |

**Integration defect found and corrected in this branch:** `NativeMachineBridge.lean` existed in the repository but was absent from both the `CapstanVerification.lean` umbrella import and `AxiomAudit.lean`. Consequently the formal CI's explicit root build and selected theorem axiom report did not cover this bridge. This branch adds the import to both places and adds explicit axiom-audit entries for its constructor, PC and fuel lemmas. The exact-head formal workflow must confirm the repair; no pass is claimed yet.

### 2.3 Heap, GC and native-memory models

| Existing model | What it establishes | Boundary still open |
|---|---|---|
| `AggregateHeap.lean` | Process-lifetime aggregate allocation, accounting, typed record fields and failure atomicity | Not connected to `verification/ccam_heap.cap` or a production allocator |
| `ReferenceSemantics.lean` | Mathematical object identity, aliasing, fresh allocation and reference-visible writes | Not a concrete heap/runtime refinement |
| `CollectorSemantics.lean` | Conditional mark/sweep preservation assuming a complete marker | Does not prove the production collector computes a complete mark set |
| `GenerationalHandles.lean` | Abstract region/slot/generation handle policy and stale-handle rejection | Future explicit-handle contract, not the current conservative C GC |
| `NativeMemoryLifecycle.lean`, `NativeReachability.lean`, `NativeHandleReachability.lean`, `NativeBoundedMarker.lean` | Separate explicit-root handle lifecycle, reachability and bounded-certificate models | Must not be conflated with current C GC or the experimental Capstan CCAM heap |
| `formal/CapstanFormal.lean`, `formal/CCAMHeap.lean` | Separate allocator/GC and CCAM heap abstract models | Their C/runtime or Capstan heap implementation refinements remain separate |

These are valuable component models, but there are currently multiple distinct heap/lifetime abstractions. They must not be merged into one purported runtime proof until the concrete runtime architecture selects which allocation, reference and collection model is authoritative.

### 2.4 Security and language-policy models

| Existing module | What it establishes | Boundary still open |
|---|---|---|
| `InjectionChecker.lean` and `InjectionSinks.lean` | Properties of a restricted model of the current laundering checker and sink rules; includes explicit gap witnesses | No mechanically proved checker-source correspondence or complete injection-freedom theorem |
| `InjectionValue.lean` and `F1Provenance.lean` | Separate value-sensitive and access-path provenance domains | Not connected to the production checker, alias-preserving heap or all sinks |
| `Visibility.lean` | Abstract module/private/opaque field-access policy | Not extracted from or refined to the parser/checker |
| `TransactionTypestate.lean` | Abstract transaction state machine and linear-owner-context rules | Not connected to Capstan type checking, code generation or runtime |
| `CredentialConfinement.lean`, `CredentialVerifierPolicy.lean` | Credential-origin and verifier-policy properties in isolated models | Not a whole-language information-flow or runtime proof |
| `Output.lean`, `ExplicitTrap.lean` | Abstract bounded byte-output and payload-bearing explicit-trap models | Not connected to concrete output syscall adapter, evaluator or full trap domain |

These modules remain separate property-specific assurance rails until their source/IR/runtime interfaces are specified and proved. A model theorem about one of these policies is not a blanket guarantee for the language.

## 3. Concrete implementation comparison

The executable Capstan CCAM path currently has these principal layers:

- `verification/ccam_core.cap`: scalar arithmetic, register substrate, single-frame validator and evaluator.
- `verification/ccam_calls.cap`: multi-function validator, call-site side table, frame stack, dispatch, return handling, step/depth and output state.
- `verification/ccam_lowering.cap`: checked source-AST lowering into multi-function CCAM.
- `verification/ccam_heap.cap`: experimental process-lifetime region heap; explicitly not yet connected to the executable machine.
- `verification/ccam_native_x64.cap` and native aggregate modules: experimental x86-64 byte emission and linking; not a verified backend.
- `compiler/checker.cap`: source type checking and current injection/laundering analysis.
- `runtime/capstan_gc.h` and `runtime/capstan_rt.h`: current C runtime and conservative GC boundary.

The key mismatch is architectural: the executable implementation has advanced beyond the Lean execution model. In particular, `ccam_calls.cap` has function tables, call-site lookup, mutable frames, return destinations, budgets, terminal fields and output. The Lean core now has typed function/frame protocols and first integrated call-entry and return outcomes, but these protocols still do not form the complete instruction transition relation for that implementation.

The implementation refinement contract in `CCAM-CONCRETE-REFINEMENT-CONTRACT.md` is still useful for the SF-P subset. It already records concrete/abstract state fields, opcode mapping, trap-domain partition, terminal observations, budget timing and reachability invariants. It must become a layer in the larger proof chain, not be discarded.

### 3.1 Specific semantic gaps

1. **Whole-program identity:** no Lean validated-program object yet mirrors the concrete function table, function names, signatures, instruction arrays and call-site tables as one immutable snapshot.
2. **Call dispatch:** the abstract machine has no `call` instruction constructor whose transition validates the call-site relation, reads arguments in the specified order, creates the callee frame and records the caller continuation.
3. **Return transition:** the typed return commit and stack-pop transitions are not yet part of a complete instruction dispatcher. A single atomic transition must either return an error without a successor state or produce the complete resumed stack and caller write.
4. **Frame invariants:** the whole state must state that every frame is typed against its own function signature, every frame PC is in range, the active frame is the stack head, and each callee's saved continuation/destination is valid in its caller.
5. **Resource accounting:** the scalar step-budget wrapper is not integrated with calls/returns, output, trap terminalisation or the concrete mutable `steps` field.
6. **Terminal observations:** the abstract outcome and the concrete state expose different observations. A relation must include PC, steps, halt flags, integer/Boolean return payloads, trap code/detail and output trace.
7. **Validator:** current Lean validator proves a conservative single-frame profile. It does not formalise the concrete JSON decoder, full multi-function validation or the exact object consumed by `ccam_calls.cap`.
8. **Trap domain:** concrete strings and details are not isomorphic to the finite Lean `Trap` sum. Explicit trap reasons and defensive constructor failures require a precise partition, not lossy conversion.
9. **Mutable object semantics:** the current list/register models do not prove Capstan's actual object identity, list indexing, mutation, allocation or aliasing behaviour.
10. **Source compiler:** no composed theorem connects source semantics/checker, lowering, validated CCAM and execution.
11. **Native backend:** byte-level tests are not a proof of x86-64 instruction semantics, ABI conformance, linking or runtime-call correctness.
12. **Memory/security:** abstract handle, collector, provenance and policy models have not been composed with the selected production runtime and compiler paths.

## 4. Target integrated semantic spine

The target is a single Lean model with explicit, immutable state and total transition functions. Existing modules should be imported as component lemmas, not reimplemented.

### 4.1 Semantic objects

Define a validated whole program containing:

- a finite function table;
- each function's stable identity, signature, register type vector and finite instruction table;
- validated call-site metadata and resolved callee indices;
- validated branch targets and return contracts;
- explicit resource limits;
- a profile/version identifier binding the semantics to the normative CCAM specification.

A frame is dependent on the selected function signature and contains a bounded PC, typed register file, and optional caller continuation/result destination. A running machine state contains the immutable program, non-empty heterogeneous frame stack, step budget, output trace and terminal status.

The machine invariant must include:

- each frame's register file is well typed for that frame's own signature;
- every frame PC is in its function's instruction range;
- every saved continuation and result destination is valid in its caller;
- all caller/callee function indices and signatures agree;
- stack depth and instruction count remain within configured limits;
- output bytes remain within the output bound;
- a running state has no terminal payload/trap, while terminal states have a canonical outcome projection.

### 4.2 One small-step transition relation

The transition relation must cover every validated instruction constructor, not a separate call protocol:

- scalar operations reuse `Core.lean` execution functions and preservation lemmas;
- branch/jump use validated finite targets;
- call resolves a validated call site, reads arguments in the normative order, constructs a typed callee frame and pushes it under the depth bound;
- non-void return validates the callee result and caller destination, then atomically commits the value and pops the callee;
- void return restores the caller without a value write;
- entry return produces a terminal result;
- output consumes the defined step and output budget in the specified order;
- traps preserve exact code/detail and post-dispatch accounting;
- pre-dispatch fuel exhaustion consumes no instruction step;
- already-terminal states are inert.

The outcome type should retain terminal observations rather than collapse them to a reason-only sum. In particular, terminal PC, dispatch count, return payload, trap detail and output trace must be representable in the abstract observation used by the concrete relation.

### 4.3 Core theorem package

Prove, over the same transition relation:

1. **Validator soundness:** every accepted raw program constructs a well-formed validated program consumed by the evaluator model.
2. **Initial-state correspondence:** the concrete validated constructor establishes the initial relation, including all register, PC, counter, output and terminal fields.
3. **Invariant preservation:** every continuing transition preserves the complete stack/register/control/resource invariant.
4. **Progress-or-terminal:** every reachable nonterminal well-formed state has a defined successor or a specified terminal/trap outcome; distinguish semantic progress from mere totality of a function.
5. **Determinism:** one state and one validated program have at most one next outcome.
6. **Call/return correctness:** argument order, exact arity/type, depth bound, caller restoration and atomic return write are proved as transitions.
7. **Resource correctness:** exact step and output accounting, including every trap and terminal case.
8. **Trace refinement:** concrete and abstract executions produce the same observable trace and terminal result.
9. **Whole-run simulation:** compose the one-step result over arbitrary finite execution traces.

A proof that only classifies the result constructors of a total function is an outcome-exhaustiveness lemma, not by itself a meaningful progress theorem. A proof that extracts an invariant already carried by a structure is a type-by-construction fact, not an implementation refinement theorem. Names and assurance records must preserve those distinctions.

## 5. Refinement architecture

There must be explicit relations between each adjacent layer:

```
Source AST + source semantics
          |
          | source-checker/type soundness
          v
Typed source / typed IR
          |
          | lowering simulation
          v
Validated whole-program CCAM
          |
          | CCAM implementation refinement
          v
Capstan-native CCAM evaluator
          |
          | backend simulation / translation validation
          v
x86-64 ISA + ABI + runtime observation
```

The heap/runtime and security properties form cross-cutting invariants over the state components, not detached claims:

- heap validity, object identity, ownership and collection invariants attach to the memory model actually selected by the runtime;
- provenance and sink safety attach to the typed value/heap state and checker decisions;
- capability authority and non-forgeability attach to concrete capability construction and use;
- confidentiality/non-interference claims require an explicit attacker model and observation function.

A concrete source-code-to-Lean proof cannot be assumed merely because both files have similarly named functions. The bridge must be mechanically checkable: either formalise the relevant Capstan source subset and prove its evaluation/lowering relation, or define a verified extraction/translation into the Lean model with a proof that the translation preserves the relevant semantics. The exact choice is a design gate before claiming implementation refinement.

## 6. Work packages and order

| Priority | Work package | Deliverable | Exit condition |
|---|---|---|---|
| P0 | Proof graph and CI closure | All Lean modules imported by explicit roots; all critical declarations included in axiom audit; pinned toolchain/checker evidence | Clean exact-head build and independent replay; no orphan proof module |
| P1 | Normative semantic freeze | Versioned CCAM semantics for calls, returns, trap details, budget order and output | Specification decisions and test vectors agree |
| P2 | Integrated whole-program model | Validated function table, dependent frames, stack, fuel, output and terminal observations | One transition relation covers all supported instructions |
| P3 | Whole-machine theorem package | Validator soundness, preservation, progress-or-terminal, determinism, resource invariants | Theorems proved over the same state/step relation |
| P4 | Concrete evaluator refinement | Initial relation, per-instruction simulation, terminal/trace correspondence | Concrete `ccam_core.cap` and `ccam_calls.cap` refinement on the declared profile |
| P5 | Source-to-CCAM refinement | Source semantics, checker soundness, typed IR and lowering simulation | Composed source execution agrees with CCAM execution |
| P6 | Native backend refinement | Restricted x86-64 instruction/ABI semantics, encoding correctness and execution simulation | Native execution refines CCAM for the stated target profile |
| P7 | Memory and security composition | Selected heap/GC, injection, capability, secret and effect invariants | Claims tied to the actual implementation and explicit threat model |
| P8 | Bootstrap assurance | Verified compiler stage relation and self-hosting fixpoint relation | Bootstrap stages preserve the proved language/compiler semantics |

Do not start P5/P6 by adding more unrelated local theorems while P2-P4 remain disconnected. Component proofs can proceed in parallel only when they target a frozen interface and feed the same dependency graph.

## 7. Immediate corrections from this review

- Add `NativeMachineBridge.lean` to the `CapstanVerification` root and `AxiomAudit.lean`; this branch does so. It was previously present but not in either explicit proof path.
- Keep `NativeMachineBridge`'s claim limited to initial state, PC and fuel admission. It does not establish opcode refinement.
- Treat `Machine.lean` + `MultiFunction.lean` + `MultiFrame.lean` as components awaiting integration, not a complete multi-function machine.
- Keep the SF-P validator's stronger final-instruction condition as an explicitly named proof profile; do not silently call it full normative validator equivalence.
- Keep `AggregateHeap`, `CCAMHeap`, conservative C GC and explicit-root handle/marker models as separate memory architectures until runtime selection and implementation correspondence are decided.
- Keep the value-sensitive provenance model and the current checker model separate until a sound checker refinement is proved; the current checker model contains known transfer gaps.
- Do not count byte-level native emitter tests as native-code correctness.
- Require exact-commit proof builds, unfinished-proof scans, theorem axiom reports and independent proof replay for every assurance promotion.

## 8. Proof trust and reproducibility

The current formal workflow pins Lean 4.19.0, scans for unfinished proofs and local axioms, builds the formal package, replays the proof library with a pinned `lean4checker`, and reports selected axiom dependencies. The separate allocator/GC package has its own Lean/axiom/Nanoda checks. Evidence from one package must not be attributed to the other.

For each promoted theorem record:

- exact repository commit and file blob hashes;
- exact theorem statement and all transitive dependencies;
- Lean/toolchain and dependency lock revisions;
- build and independent-checker run identifiers;
- axiom list and trusted computing base;
- model-to-specification mapping;
- implementation files and the exact refinement theorem, if implementation coverage is claimed;
- explicit exclusions, assumptions and counterexample tests.

Lean 4.34.0's release notes report kernel soundness fixes and additional defensive checks; this is a reason to schedule a deliberate toolchain upgrade evaluation, not to change the pinned version in the middle of a proof programme. Upgrade only with a separate reproducibility run and review of proof/build changes. The current project remains pinned to 4.19.0 until that gate is completed.

## 9. Acceptance rule

A guarantee may be described as **formally established for Capstan implementation X** only when the proof is machine-checked on the exact implementation revision and the chain from the normative property to the concrete execution path is complete. Otherwise describe it precisely as a model theorem, a restricted profile theorem, a representation lemma, test evidence or an open obligation.

The aim is not to maximise theorem count. It is to minimise the distance between the normative claim, the Lean semantics and the executable Capstan implementation.

### 3.2 Concrete call/return ordering contract

The following ordering is observed in `verification/ccam_calls.cap` at the review baseline. It is a refinement target and must be reconciled with the normative CCAM specification before being treated as the final semantic contract.

**Common pre-dispatch path**

1. A halted machine is inert.
2. The active frame depth is checked for a valid range.
3. The global step limit is checked. If already exhausted, the machine traps without consuming another step.
4. The active frame PC is checked against its instruction sequence. An invalid PC traps before instruction accounting.
5. A valid instruction is selected. The opcode-specific path then consumes exactly one step.

**Call opcode**

1. Increment the global step counter.
2. Resolve the call-site side-table index for the active function and executing PC.
3. Resolve the callee function and call-site metadata.
4. Read and snapshot every argument in source order, using the callee parameter's declared type for each read. An argument read/type failure traps after the step has been consumed.
5. Check the maximum call depth. A depth failure also occurs after step consumption and argument reads.
6. Construct a fresh callee register file and write the snapshotted arguments into parameter registers.
7. Advance and store the caller continuation PC.
8. Construct the callee frame at entry PC zero, including the saved caller destination.
9. Push/reuse the frame slot and increment active frame depth.

The formal call transition must preserve this ordering. In particular, checking depth before argument reads would change which trap wins when both an argument read and depth check fail. Re-reading caller registers after mutation would not implement the snapshot semantics.

**Return and void-return opcodes**

1. Increment the global step counter.
2. Read the return register, if any, using the function's declared return type. A read/type failure traps after consuming the step.
3. If this is the entry frame, set the terminal halt fields and retain the entry frame; do not perform a nested pop.
4. Otherwise, inspect the saved caller destination and check presence, bounds and exact declared type.
5. For a void return, reject a callee/call-site combination that carries a result destination.
6. For a non-void return, preflight the complete destination contract before writing.
7. Commit the caller register write before reducing frame depth. This ordering is deliberate: a defensive write failure must leave the caller/callee stack unpopped.
8. Reduce active frame depth exactly once.

A formal transition that returns only `Except Trap Stack` loses an important observable: a trap after opcode dispatch has consumed a step, whereas pre-dispatch fuel exhaustion has not. The integrated outcome must therefore retain the post-attempt budget on opcode-level traps, and the unchanged budget on pre-dispatch exhaustion. It must also distinguish entry halt-with-value, entry halt-void, nested continuation and trap.

**Other opcodes**

Non-call/non-return instructions are delegated to `ccam_machine_step` through a temporary single-frame view carrying the shared global step counter and output buffer. The result counter/output are copied back, the active frame is stored, and a terminal result is translated into a call-machine trap. The whole-machine refinement must cover this delegation and prove that the temporary view and persisted active frame are related.

**Required adversarial ordering vectors**

- exhausted global budget plus invalid PC (budget trap wins, no increment);
- invalid PC with available budget (PC trap, no increment);
- valid CALL with invalid call-site metadata (one step consumed);
- CALL with both an unreadable argument and exhausted depth (argument trap wins);
- CALL with valid arguments and exhausted depth (depth trap after one step);
- RET with unreadable or wrongly typed return register (one step consumed);
- RET with absent, out-of-range or wrong-typed caller destination (one step consumed, no caller write/pop);
- RET where the defensive write helper fails (one step consumed, no stack pop);
- entry return versus nested return (halt versus caller restoration);
- void return with and without an unexpected destination;
- successful call/return pairs preserve exact caller continuation and global step count.

These cases should become shared concrete/Lean vectors. Passing the vectors is differential evidence, not a replacement for the universal transition-refinement theorem.
