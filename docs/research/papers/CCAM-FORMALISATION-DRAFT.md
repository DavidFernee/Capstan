# A Typed Finite-Machine Model for Capstan's Core Abstract Machine

## A Lean Formalisation and Its Current Proof Boundary

**Author:** David Fernee  
**Manuscript status:** Research draft — not submission-ready  
**Repository snapshot:** Capstan `main` at `294d34361c31dc768e60a017a3fd0718f7a00313` (25 November 2026)  
**Formalisation:** Lean 4.19.0  
**Formal-model introduction:** commit `360043c8704546857caa4c82f2978c7709399016` (PR #151)  
**Current implementation snapshot:** commit `294d34361c31dc768e60a017a3fd0718f7a00313` (PR #163 merged)

---

## Abstract

Capstan is a security-oriented programming language whose longer-term architecture aims to remove C from its compiler and runtime trusted computing base. A central part of that programme is the Capstan Core Abstract Machine (CCAM), a typed, register-based execution model intended to provide a stable semantic boundary between source-language compilation and native execution. This paper reports on a machine-checked Lean formalisation of a restricted, finite, single-frame fragment of that machine.

The formalisation represents register types and program counters with finite types, embeds scalar type obligations in instruction constructors, and models checked signed 64-bit arithmetic, register initialisation, control flow, explicit traps and instruction accounting. A validator model converts decoded instructions with natural-number operands into intrinsically typed machine instructions. A whole-program construction produces a finite program only when its entry index is valid, every instruction in the fixed finite table validates, and the final instruction has an explicit control effect. The resulting representation carries bounded program counters and typed register operands by construction.

The work establishes useful local invariants, including preservation of register typing for successful operations, bounded control-flow targets, signed-64 result constraints, instruction-budget accounting, and a conditional representation bridge for runtime-style register lists. A Capstan-native in-memory structural validator for the supported single-frame subset has also been merged and passed exact-head platform and formal CI, but it is not connected to the Lean validator by a refinement theorem. The formal validator does not parse JSON or represent the complete normative multi-function schema. Calls, integrated call frames, source lowering, and native code generation remain outside the present machine model. We identify a further semantic mismatch: the model's unconditional requirement that the final instruction be terminal is stronger than the normative CCAM reachability-based fall-through rule.

The contribution is therefore a documented formalisation and proof-boundary study, not an end-to-end verified compiler. We use it to identify the next proof obligations required to connect a typed abstract machine to an executable language implementation without overstating what a model-level proof establishes.

**Keywords:** programming-language semantics; Lean 4; abstract machines; dependent types; validator soundness; compiler assurance; trusted computing base.

---

## 1. Introduction

A compiler's intermediate representation (IR) is more than a convenient data structure. It is a semantic boundary: transformations on one side must preserve the behaviour defined on the other, and execution on the far side must implement the same contract. This boundary becomes especially important when a language is designed around security claims. If the representation admits malformed indices, ill-typed register operations, ambiguous arithmetic, or unbounded execution behaviour, later compiler and runtime components inherit those ambiguities.

Capstan's current integrated compiler remains C-backed. The longer-term C-free programme introduces CCAM as a typed, register-based abstract machine intended to decouple language semantics from C, the C ABI, and host-language arithmetic behaviour. The normative CCAM v0.1 design specifies signed 64-bit integers and booleans, typed function-local registers, explicit traps, control flow, direct calls, and deterministic instruction and call-depth limits [1]. The specification also requires closed JSON schemas and complete structural validation before execution.

This paper examines a deliberately smaller formal artefact already present in the repository: a Lean model of a finite, single-frame machine and a validator that constructs its intrinsically typed instruction representation. The purpose is twofold. First, we document exactly which properties the existing formalisation establishes. Second, we make explicit the distance between those properties and a verified executable pipeline.

The distinction is consequential. A theorem about a mathematical model is not, by itself, a theorem about a parser, validator, evaluator, compiler, runtime, or generated machine code. Verified compiler projects such as CompCert and CakeML obtain their strength from explicit semantic relations between successive representations and proofs that compilation preserves observable behaviour [2, 3]. Mechanised WebAssembly work similarly combines a formal semantics with type soundness and executable checking, while exposing the importance of alignment between the mechanisation and the normative specification [4, 5]. Capstan has not yet established those end-to-end connections.

### 1.1 Research questions

This work addresses three bounded questions:

1. Can a finite register machine encode register and control-flow well-formedness in its Lean types, so that malformed indices and mismatched scalar operands cannot be represented in the validated machine syntax?
2. Which local safety and execution-accounting properties can be machine-checked for that restricted model?
3. Which specification and implementation relationships remain unproved before these results can support a claim about executable CCAM?

### 1.2 Contributions

The paper makes the following limited contributions:

- It presents the repository's Lean representation of a finite, single-frame, typed register machine.
- It explains the raw-to-intrinsically-typed validation boundary, where untrusted natural-number indices are converted to `Fin` indices and register-type evidence is carried in dependent data.
- It inventories the machine-checked local invariants for register typing, checked arithmetic, control-flow bounds and instruction budgets, together with the conditional runtime-register representation bridge.
- It records the merged in-memory validator's test and CI evidence while identifying concrete gaps between the formal model, normative CCAM v0.1 and the executable evaluator.
- It proposes a staged proof plan based on specification alignment, validator soundness, evaluator refinement and source-to-machine semantic preservation.

We do not claim that these techniques are novel in isolation. Finite indices, intrinsically typed syntax and mechanised operational semantics are established methods. The research value at this stage lies in the concrete formalisation, its application to Capstan's evolving machine contract, and the explicit analysis of the proof obligations that remain.

---

## 2. System context and scope

### 2.1 CCAM's intended role

CCAM is intended to be a platform-independent execution representation. The normative design describes a program as a collection of named functions. Each function declares a register type vector, parameter count, return type and non-empty instruction sequence. The program names an entry function. Instructions include scalar constants and operations, jumps, conditional branches, calls, returns and explicit traps. Execution is bounded by configured maximum instruction and call-depth limits [1].

The external representation is JSON, but the specification requires strict validation before execution. Duplicate keys, unknown fields, invalid type tags, malformed operands, invalid function names, out-of-range indices, mismatched call signatures and invalid returns are validation errors. They are not runtime traps. The specification also requires exact integer parsing rather than conversion through an inexact floating-point representation [1].

The current formal model is not this complete machine. It is a single-frame fragment that captures scalar registers, a finite instruction table, local control flow, return forms and a budget abstraction. The current production compiler path is still generated C plus a C runtime; CCAM is not the default execution backend [6].

### 2.2 Formal artefact

The CCAM Lean project is pinned to Lean 4.19.0 in `verification/lean/`. Its principal modules are `Core.lean` (scalar values and arithmetic), `Machine.lean` (typed instructions, finite programs, machine states, budget and call-stack abstractions), `Validator.lean` and `ProgramValidator.lean` (decoded single-frame validation), `Progress.lean` (restricted step outcomes and bounded execution), and `RuntimeBridge.lean` (a list-based runtime-register representation relation). `AxiomAudit.lean` records explicit `#print axioms` declarations.

The Lean whole-program validator was merged in PR #151 (`360043c8704546857caa4c82f2978c7709399016`). The Capstan-native in-memory typed structural validator was subsequently merged in PR #163 (`294d34361c31dc768e60a017a3fd0718f7a00313`). PR #163's exact head `0e9800397c45359e216ec08c656bb9bed86cd8ef` passed the formal workflow (run [45508852082](https://github.com/DavidFernee/Capstan/actions/runs/45508852082)): the unfinished-proof/local-axiom scan, Lean build, pinned Lean 4.19 `lean4checker` replay, and axiom audit all completed successfully. The audit reports `propext` and `Quot.sound` dependencies for selected declarations; the result is not axiom-free. Nanoda ran in the separate allocator/GC job, not the CCAM job. Platform and supply-chain CI also passed on that exact PR head (run [45508852150](https://github.com/DavidFernee/Capstan/actions/runs/45508852150)).

### 2.3 Explicit exclusions

The formal machine has no call instruction and no multi-function program representation. The call-stack data structure and its push/pop lemmas are separate abstractions; they are not integrated into the machine transition relation. The formal model does not include JSON parsing, duplicate-key handling, function-name resolution, complete call signatures, argument transfer, atomic call returns, heap objects, garbage collection, taint, secrets, policies, I/O, concurrency, or native code generation. PR #163 adds a tested Capstan-native in-memory validator for the supported single-frame subset, but that implementation is not proved equivalent to the Lean validator or complete normative JSON contract.

These exclusions are part of the result, not implementation details to be inferred away.

---

## 3. Formal model

### 3.1 Scalar domain and register files

The model defines a disjoint scalar type `Ty = int | bool`. Values are integers or booleans. Integer values are admitted only when they lie in the signed 64-bit interval `−2^63 ≤ n ≤ 2^63 − 1`.

The register type vector for a machine with `n` registers is a function `RegTypes(n) = Fin(n) → Ty`. The register file maps each finite register index to an optional value: `Registers(n) = Fin(n) → Option(Val)`. 

The predicate `WellTyped types regs` states that every initialised register contains a value of its declared type. An absent value represents an uninitialised register. The model's write operation updates one finite index. The theorem `write_preserves_well_typed` proves that a write preserves the register-file invariant when the inserted value has the declared type at the destination.

This is a local representation invariant. It does not establish that an external parser or runtime constructs a register file satisfying the predicate; that relationship must be proved separately.

### 3.2 Intrinsically typed instructions

The instruction datatype `MachineInstr n m types` uses finite indices for registers and control-flow targets. Scalar instruction constructors carry equality evidence for their operand types. For example, integer constants carry a proof that the destination register is declared as an integer and a proof that the literal is in range. Arithmetic instructions carry evidence that their source and destination registers are integer-typed. A conditional branch carries evidence that its condition register is boolean and that both targets are finite instruction indices.

The representation therefore makes certain invalid states unconstructible within Lean. A value of type `MachineInstr n m types` cannot contain a natural-number register index that has not first been converted to a `Fin n`, nor can an arithmetic constructor be formed without the required type equalities.

This is a property of the formal datatype. It is not yet a proof that the production evaluator receives only values corresponding to this datatype.

### 3.3 Finite programs and control flow

A `FiniteProgram n m types` contains a code function indexed by `Fin (m + 1)`, an entry program counter of the same finite type, and a proof that the final instruction is terminal. A jump or branch target is represented as a finite index. The theorem `machineInstr_targets_in_range` follows from this representation: target bounds are carried by the target types.

The final-instruction condition prevents sequential fall-through beyond the final slot in this model. However, as discussed in Section 6, this condition is stricter than the normative specification's reachability-based rule. It must not be described as an equivalent implementation of the normative validator.

### 3.4 Raw syntax and validation

The validator accepts a decoded instruction syntax whose register and target operands are natural numbers. It attempts to convert each operand into a finite index and checks the relevant register-type constraints. Successful validation constructs a `MachineInstr`.

The whole-program model, `RawSingleFrameProgram`, contains:
- a finite instruction table indexed by `Fin (m + 1)`;
- a natural-number entry index;
- a declared return type.

Validation first converts the entry index to a finite index. It then requires every instruction in the table to validate and requires the final instruction to satisfy the terminal predicate. On success it constructs a `FiniteProgram`.

The proofs `validateSingleFrameProgram_rejects_bad_entry` and `validateSingleFrameProgram_entry_sound` establish rejection of an out-of-range entry and preservation of a successfully validated entry value. The theorem `validateFunctionInstr_rejects_return_mismatch` establishes rejection of a return instruction whose kind conflicts with the declared function return type. These are properties of the Lean validator over an already-constructed finite Lean input; they do not establish soundness or completeness of the Capstan-native validator.

The raw program is already a finite, typed Lean structure. It is not an untrusted JSON document or arbitrary-length instruction list. Thus the validator formalisation begins after parsing and does not establish schema validation, decoder correctness, duplicate-key rejection or exact numeric decoding.

### 3.5 Arithmetic and traps

The model defines checked signed-64 arithmetic over Lean integers. Addition, subtraction and multiplication compute mathematical integer results and reject results outside the signed-64 interval. Division truncates toward zero, traps on division by zero, and traps on the `(MIN / -1)` overflow case. Remainder is defined consistently with truncation toward zero; division or remainder by zero traps, while `(MIN % -1)` returns zero.

The last distinction matters: the quotient overflows in the signed-64 representation, but the mathematical remainder is zero and representable. The normative CCAM v0.1 document records the same rule [1]. The model contains lemmas for division and remainder exceptional cases and result-range properties. The formal-verification matrix correctly identifies that complete quotient/remainder equations, sign properties and correspondence to the Capstan primitive remain proof obligations [7].

---

## 4. Machine-checked properties

This section reports the properties represented by named Lean declarations in the repository. It distinguishes substantive preservation/accounting results from facts that follow directly from the datatype or from the exhaustiveness of a result type.

### 4.1 Register typing

The model proves:
- `write_preserves_well_typed`: a correctly typed write preserves the register-file invariant;
- `readValue_success_well_typed`: a successful read from a well-typed register file returns a value of the declared type;
- `readInt_success_in_range`: a successful integer read from a statically integer-typed register returns a signed-64 value;
- `executeAdd_preserves_well_typed`: a successful addition transition preserves register typing.

The machine model also carries a well-typed-register proof in its state representation, and successful continuation states must supply the invariant. The general machine-step preservation theorem therefore follows from the construction of the next-state result together with the operation-level preservation lemmas.

These results establish local safety properties of the formal model. `RuntimeBridge.lean` additionally defines `RuntimeRegisterFileRelation` and proves `runtimeReadInt_corresponds`, `runtimeReadBool_corresponds`, and `runtimeWriteRegister_preserves_relation` under explicit premises. This is a representation-level bridge between two Lean definitions, not a source-linked proof. In the executable `CCAMRegister`, `declared_type` is an integer tag (`CCAM_TYPE_INT = 1`, `CCAM_TYPE_BOOL = 2`), whereas the Lean `RuntimeRegister.declaredType` stores the `Ty` constructor directly. The Lean write model replaces a whole list element, whereas the Capstan functions update the selected payload field and `initialized` bit. No theorem yet proves the integer-tag decoding, constructor path or imperative field updates preserve `RuntimeRegisterFileRelation`. The results therefore do not establish correctness of compiled Capstan register access.

### 4.2 Control-flow bounds

Finite indices ensure that program counters and jump/branch targets are in their declared finite domains. The model includes:
- `machineState_pc_is_in_range`;
- `machineInstr_targets_in_range`;
- `executeBranch_target_is_declared`;
- `finiteProgram_targets_bounded`;
- `finiteProgram_final_instruction_has_control_effect`.

Some of these are representation theorems: the type of a program counter or target already contains its bound. Their value is that downstream semantics can consume the bounded representation without repeatedly proving a natural-number inequality. They should not be interpreted as a proof of control-flow reachability, termination, or equivalence to the complete normative validator.

### 4.3 Instruction-budget accounting

The model represents a budget as a limit and a used count, with a proof that the count does not exceed the limit. A budgeted transition attempts to consume one unit before executing an instruction. If the budget is exhausted, it returns an instruction-limit trap without executing the next machine instruction. Otherwise the machine step is evaluated and the consumed budget is retained for continuation, halt or dynamic trap outcomes.

The associated theorems establish:
- successful consumption increments the counter exactly once;
- the counter remains within the configured limit;
- an exhausted budget traps before another instruction;
- a budgeted transition consumes one unit when budget remains.

This accounting is for the restricted single-frame transition relation. The normative contract includes calls and returns, and the formal model does not yet establish whole-machine accounting across an integrated multi-function call stack.

### 4.4 Call-stack abstraction

The Lean machine file also defines a non-empty bounded call-stack structure and separate push/pop functions. Their lemmas establish that a successful push places the callee at the top and increments depth by one, and that a successful nested pop restores the caller and decreases depth.

These are useful component properties, but the call stack is not part of `MachineInstr` or `machineStep`. It would be incorrect to present these lemmas as a proof of CCAM call semantics. An integrated machine must connect the stack abstraction to function lookup, argument evaluation, parameter-register initialisation, return-value transfer, caller restoration, and budget accounting.

### 4.5 Properties not counted as substantive results

The theorem `machineStep_progress_or_explicit_outcome` classifies the result of a machine step into one of the constructors of the machine-outcome datatype by case analysis. This is an exhaustive classification, not a substantive progress theorem showing that a valid configuration can always take a semantically appropriate step.

Likewise, determinism of the current functional `machineStep` definition follows from the fact that it is a function: two evaluations of the same input are equal. This is a useful interface property, but it is not a comparison between two independently defined semantics or implementations.

The validator theorem `validateRawInstruction_returns_typed` is similarly a direct restatement of its successful-result premise. We do not count it as an independent validator-soundness result. This paper deliberately avoids inflating the theorem inventory with such tautological or representation-derived statements.

---

## 5. Relationship to prior work

Formal semantics and compiler verification have a substantial history. The appropriate comparison is not whether Capstan uses Lean or a typed IR, but whether its formal artefacts establish a chain of semantic relationships.

CompCert formalises the semantics of source and intermediate languages and proves semantic preservation across compilation. Its verification architecture uses simulation arguments to connect executions at successive levels [2]. CakeML demonstrates a much broader verified compiler and runtime architecture, including multiple intermediate languages, code generation, and verified runtime components [3]. Vellvm formalises LLVM IR and its type system, and relates different operational semantics to support verified transformations [8]. These projects provide a standard against which the scope of a compiler-verification claim should be measured.

Two particularly close bytecode-verification precedents make the novelty boundary sharper. Freund and Mitchell develop a sound type system for a substantial Java bytecode subset, a type-checking algorithm and a prototype verifier [11]. Klein and Nipkow's Jinja development unifies a Java-like source language, JVM semantics, a bytecode verifier with a correctness proof, and a compiler with semantic-preservation and well-typedness results [12]. These works already establish far more than a finite typed instruction model: they connect validation, execution and compilation in machine-checked developments. Consequently, finite indices, typed instruction constructors, local preservation lemmas and a validator model are not novel methods in themselves.

Recent Lean-specific work also narrows any possible methodological claim. LeanMachines presents a Lean 4 framework for state-based modelling and stepwise refinement with proof obligations inspired by Event-B [13]. Lean4Lean develops an external Lean typechecker and formalises parts of Lean's metatheory [14]. Capstan's use of Lean and a separately replayed proof checker is therefore an engineering choice, not a standalone research novelty. A defensible future contribution would need to lie in the exact CCAM semantics, its security/resource contract, and—most importantly—a proved relation from the actual Capstan parser, validator and evaluator to that semantics.

Mechanised WebAssembly work is particularly relevant to CCAM's validator boundary. Watt's mechanisation includes a formal specification, executable interpreter and type checker, together with a machine-checked type-soundness result [4]. Later work provides two mechanisations of WebAssembly 1.0 and discusses the relationship between the normative standard, type soundness and executable checking [5]. These efforts show that validator and semantics alignment is not merely an implementation detail: it is part of the assurance argument.

Capstan's present work is substantially narrower. It formalises a small machine fragment and uses Lean's dependent type system to make selected invariants intrinsic to the representation. It has not yet formalised the complete input language or proved a soundness theorem connecting the normative JSON validator to the machine. Nor has it established source-to-CCAM semantic preservation or a verified native backend.

Accordingly, the present work should be positioned as an early-stage formalisation and assurance-boundary study, not as a competitor to CompCert, CakeML, Vellvm or WasmCert in verification coverage. A stronger contribution may emerge when the typed representation becomes the target of a proved validator and an executable evaluator whose transitions refine the same formal semantics.

---

## 6. Specification alignment and known limitations

A formalisation can be internally consistent and still fail to model the intended language. The current comparison with CCAM v0.1 exposes several important gaps.

### 6.1 Final-instruction restriction is stronger than the normative rule

The formal `FiniteProgram` requires the final instruction in the table to be terminal, regardless of reachability. The normative CCAM specification instead requires that every *reachable* nonterminal instruction have an in-function successor; unreachable instructions must still pass structural and typing checks, but do not independently cause a fall-through error [1].

The formal condition is therefore sufficient to prevent sequential fall-through in the model, but it is not equivalent to the normative acceptance condition. It may reject programs that the specification permits, such as a program whose final instruction is unreachable and nonterminal. The model must be revised to represent control-flow reachability, or the normative contract must be deliberately changed and justified. Until that decision is made, no validator-equivalence or completeness claim is warranted.

### 6.2 Entry representation differs

The normative program names an entry function, and execution of a function begins at its first instruction. The formal `RawSingleFrameProgram` instead carries a natural-number instruction entry index. This abstraction may be useful for studying finite control flow, but it is not a direct representation of the normative program entry field. A future refinement must distinguish program-level function selection from a function's local program counter.

### 6.3 Parsing and structural validation are absent

The formal raw representation is already a Lean value with a finite instruction table. It does not model:
- JSON lexical and syntactic parsing;
- duplicate object keys;
- closed field sets and unknown-field rejection;
- exact parsing of signed-64 integer tokens;
- Unicode scalar-value validation for names;
- function-name uniqueness and lookup;
- array lengths and arbitrary untrusted collection sizes;
- schema-level resource limits.

These requirements are explicit in CCAM v0.1 [1]. They must be formalised before the model can support claims about the external CCAM validator.

### 6.4 Calls and whole-machine semantics are absent

The normative instruction set includes direct calls with named function resolution, typed argument transfer, optional return destinations and atomic return behaviour. The formal instruction datatype has no call constructor. Separate stack lemmas do not fill this gap.

The next model must represent a function table, per-function register signatures, a frame stack, caller destinations, and the transition rules for call and return. It must prove that argument reads occur in the specified order, that failures do not partially mutate machine state, that frame depth remains bounded, and that return restores the caller exactly as specified.

### 6.5 The executable evaluator is not refined to the model

The repository contains a restricted Capstan-native evaluator and, after PR #163, an in-memory structural validator. The validator checks the supported instruction subset's operand/register types, indices, branch targets, return contracts, reachable fall-through and resource limits before execution. Its tests include a 512-instruction backwards-edge chain, successful execution returning 42, malformed branch-target rejection, exact/over-limit cases and negative step-budget rejection. These are implementation and test results, not formal proofs.

`RuntimeBridge.lean` narrows one part of the gap: it proves read correspondence and conditional register-write relation preservation for an abstract runtime-style record/list model. Direct comparison with `verification/ccam_core.cap` shows that the bridge abstracts away the concrete integer type tags and the payload-field mutation sequence. No theorem currently relates those concrete operations, the actual evaluator's instruction representation, parser/validator and full state transitions to `MachineInstr` and `machineStep`. The Lean model has no integrated call instruction or multi-function configuration. The multi-function evaluator remains in open draft PR #169; scalar source-lowering PR #167 was closed without merge, and no source-to-CCAM lowering is claimed as integrated. The central gap remains a missing implementation-to-model step-simulation/refinement theorem and a complete external-input validation relation.

### 6.6 Proof replay and trusted computing base

The CCAM formal workflow passed on PR #163's exact head, including a pinned Lean 4.19 build and `lean4checker` replay. The axiom audit reports `propext` dependencies and `Quot.sound` for five selected declarations: `runtimeWriteRegister_preserves_relation`, `runtimeWriteRegister_type_at_preserved`, `runtimeWriteRegister_type_at_other_preserved`, `validateSingleFrameProgram_rejects_bad_entry`, and `validateSingleFrameProgram_entry_sound`. The workflow does not impose a blanket axiom allowlist for the CCAM package; it prints dependencies for review. The separate allocator/GC model's Nanoda configuration must not be attributed to CCAM. The exact workflow and commit should be retained as reproducibility evidence, and the full output should be archived with any submission.

A proof assistant and a second checker reduce some trust assumptions; they do not eliminate the trusted computing base. The paper must report the Lean kernel, checker version/commit, build environment and observed axiom dependencies.

---

## 7. A proof plan toward an executable CCAM result

The next stage should proceed in dependency order. Adding features before the normative contract is aligned risks proving the wrong machine.

### 7.1 Freeze a machine semantics

First, establish a versioned formal syntax and small-step semantics corresponding to CCAM v0.1. The semantics must include:
- program and function tables;
- exact function signatures and parameter initialisation;
- all instruction constructors;
- checked arithmetic and explicit trap outcomes;
- reachability-based fall-through validation;
- call and return behaviour;
- deterministic step and depth accounting;
- validation failure as distinct from runtime trapping.

The formal entry representation and final-instruction condition must be reconciled with the normative document before validator completeness is considered.

### 7.2 Prove validator soundness and completeness

Define a raw syntax that faithfully represents decoded CCAM documents, including the malformed cases that the validator must reject. Define a declarative validation judgment independently of the executable validator function.

Then prove at least:
- **soundness:** if the executable validator accepts a raw program, the resulting machine program satisfies the declarative well-formedness judgment;
- **completeness:** if a raw program satisfies the declarative judgment, the validator accepts it;
- **rejection correctness:** each specified malformed class is rejected for the specified reason or at the specified validation boundary.

The parser itself requires a separate relation from JSON bytes/tokens to raw syntax. Duplicate-key and exact-number semantics must not be silently delegated to an unspecified host library.

### 7.3 Prove evaluator refinement

Define a relation between concrete Capstan evaluator states and formal machine states. For every executable evaluator step, prove that it corresponds to a formal transition (or a permitted stuttering sequence). Conversely, establish that the evaluator does not omit a required observable result.

The proof must cover successful operations, dynamic traps, calls, returns, instruction accounting and all externally observable results. A simulation theorem should make explicit its assumptions about the parser, validated input, runtime primitives and host environment.

### 7.4 Connect source lowering

Once the machine semantics and evaluator boundary are stable, define source-language evaluation for a bounded subset and prove that lowering preserves its behaviour. This requires a source-to-CCAM simulation theorem. It must account for evaluation order, checked arithmetic, short-circuiting, control flow, function calls, and any side effects admitted by the subset.

Only after this relation exists can the project make a defensible claim that a source program's specified behaviour is preserved through the CCAM pipeline.

### 7.5 Independent evaluation

The formal results should be accompanied by:
- exact-head Lean builds and recorded checker output;
- an audited axiom report;
- generated positive and negative validator cases;
- differential tests between the Capstan evaluator and a separately defined executable model, where practical;
- mutation testing of the validator and evaluator;
- fuzzing of raw/JSON inputs and counterexample minimisation;
- independent review of the formal semantics and proof statements.

Testing complements proof; it does not replace the refinement theorem.

---

## 8. Discussion

The current formalisation demonstrates a useful design direction for CCAM: make invalid scalar register operations and out-of-range control-flow targets difficult or impossible to represent after validation. This shifts some obligations from repeated dynamic checks into the type of the machine representation. The model also makes arithmetic and instruction-budget behaviour explicit rather than inheriting host-language behaviour.

However, the results are not yet a formally verified execution architecture. The strongest local invariants apply to the Lean model, not to the Capstan-native evaluator. The validator is a model over already-decoded finite structures, not the complete normative JSON validator. The call stack is a separate abstraction rather than an integrated machine feature. The mismatch in final-instruction validation is evidence that specification alignment still needs work.

These limitations do not make the work unimportant. They identify the exact transition from a formal model to a formal assurance argument. The next research contribution should connect the following stages with explicit relations and theorems:

```text
JSON input → validated CCAM → Capstan evaluator → observable execution
Capstan source → checked core → CCAM → native execution
```



This is the architecture required to reduce the current C-backed trusted computing base. It is a programme goal, not a result established by the present paper.

---

## 9. Conclusion

We have presented a scoped account of Capstan's Lean formalisation of a finite, single-frame typed machine, including a conditional representation relation for runtime-style register lists. The model uses finite indices and intrinsically typed instructions to encode register and control-flow constraints. Its proofs establish local register-typing preservation, checked arithmetic properties, bounded control-flow representation and instruction-budget accounting. Separate call-stack lemmas provide a basis for later integration, but do not prove call semantics. The merged Capstan-native validator and its passing exact-head CI are additional implementation evidence, not a formal connection to the Lean model.

The formalisation is a meaningful foundation for further work, but its assurance boundary is narrow. It does not parse normative CCAM documents, model the complete multi-function machine, prove validator completeness, or establish refinement to the Capstan-native evaluator. It also imposes a final-instruction condition stronger than the normative reachability-based rule. These differences must be resolved before the work can support an end-to-end verification claim.

The principal research task is therefore not simply to enlarge the Lean model. It is to connect the normative specification, validator, evaluator and source lowering through explicit semantic relations. That is the route by which Capstan's C-free architecture could become a verifiable implementation rather than an architectural aspiration.

---

## References

[1] David Fernee. *Capstan Core Abstract Machine (CCAM) v0.1*. Capstan repository, `docs/architecture/CCAM.md`, design specification, reviewed 25 November 2026. [Repository](https://github.com/DavidFernee/Capstan/blob/main/docs/architecture/CCAM.md).

[2] Sandrine Blazy. “From Mechanized Semantics to Verified Compilation: the Clight Semantics of CompCert.” In *Fundamental Approaches to Software Engineering (FASE 2024)*, Lecture Notes in Computer Science 14573, pp. 1–21, 2024. DOI: [10.1007/978-3-031-57259-3_1](https://doi.org/10.1007/978-3-031-57259-3_1).

[3] Yong Kiam Tan, Magnus O. Myreen, Ramana Kumar, Anthony Fox, Scott Owens, and Michael Norrish. “The verified CakeML compiler backend.” *Journal of Functional Programming* 29, 2019. DOI: [10.1017/S0956796818000229](https://doi.org/10.1017/S0956796818000229).

[4] Conrad Watt. “Mechanising and Verifying the WebAssembly Specification.” In *Proceedings of the 7th ACM SIGPLAN International Conference on Certified Programs and Proofs (CPP 2018)*, 2018. DOI: [10.1145/3167082](https://doi.org/10.1145/3167082).

[5] Conrad Watt, Xiaojia Rao, Jean Pichon-Pharabod, Martin Bodin, and Philippa Gardner. “Two Mechanisations of WebAssembly 1.0.” In *Formal Methods (FM 2021)*, 2021. DOI: [10.1007/978-3-030-90870-6_4](https://doi.org/10.1007/978-3-030-90870-6_4).

[6] David Fernee. *Capstan README and Design Map*. Capstan repository, particularly the current execution-path and C-free architecture status. [README](https://github.com/DavidFernee/Capstan/blob/main/README.md), [Design map](https://github.com/DavidFernee/Capstan/blob/main/docs/DESIGN-MAP.md).

[7] David Fernee. *Formal Verification Obligation Matrix*. Capstan repository, `docs/assurance/FORMAL-VERIFICATION-MATRIX.md`, reviewed 25 November 2026. [Repository](https://github.com/DavidFernee/Capstan/blob/main/docs/assurance/FORMAL-VERIFICATION-MATRIX.md).

[8] Jianzhou Zhao, Santosh Nagarakatte, Milo M. K. Martin, and Steve Zdancewic. “Formalizing the LLVM Intermediate Representation for Verified Program Transformations.” In *Proceedings of the 39th ACM SIGPLAN-SIGACT Symposium on Principles of Programming Languages (POPL 2012)*, pp. 427–439. DOI: [10.1145/2103621.2103709](https://doi.org/10.1145/2103621.2103709).

[9] David Fernee. “Add bounded typed structural validator.” Capstan pull request #163, merged 25 November 2026. [Pull request](https://github.com/DavidFernee/Capstan/pull/163).

[10] Capstan CI. Formal verification run 45508852082 and platform/supply-chain run 45508852150, executed against PR #163 head `0e9800397c45359e216ec08c656bb9bed86cd8ef`. [Formal run](https://github.com/DavidFernee/Capstan/actions/runs/45508852082); [platform run](https://github.com/DavidFernee/Capstan/actions/runs/45508852150).

[11] Stephen N. Freund and John C. Mitchell. “A Type System for the Java Bytecode Language and Verifier.” *Journal of Automated Reasoning* 30(3–4), pp. 271–321, 2003. DOI: [10.1023/A:1025011624925](https://doi.org/10.1023/A:1025011624925).

[12] Gerwin Klein and Tobias Nipkow. “A machine-checked model for a Java-like language, virtual machine, and compiler.” *ACM Transactions on Programming Languages and Systems* 28(4), pp. 619–695, 2006. DOI: [10.1145/1146809.1146811](https://doi.org/10.1145/1146809.1146811).

[13] Danaël Carbonneau and Frederic Peschanski. “LeanMachines: State-based Modeling with Refinement (a Lean4 Framework).” *Formal Aspects of Computing* 38(2), Article 18, pp. 1–36, 2026. DOI: [10.1145/3796230](https://doi.org/10.1145/3796230).

[14] Mario Carneiro. “Lean4Lean: Verifying a Typechecker for Lean, in Lean.” In *31st International Conference on Types for Proofs and Programs (TYPES 2025)*, LIPIcs 384, Article 2, 2026. DOI: [10.4230/LIPIcs.TYPES.2025.2](https://doi.org/10.4230/LIPIcs.TYPES.2025.2).

---

## Reproducibility and artefact map

The formal artefacts discussed here are in the Capstan repository:

- `verification/lean/CapstanVerification/Core.lean`
- `verification/lean/CapstanVerification/Machine.lean`
- `verification/lean/CapstanVerification/Validator.lean`
- `verification/lean/CapstanVerification/ProgramValidator.lean`
- `verification/lean/CapstanVerification/Progress.lean`
- `verification/lean/CapstanVerification/RuntimeBridge.lean`
- `verification/lean/AxiomAudit.lean`
- `verification/lean/lean-toolchain`

The Lean toolchain is pinned to `leanprover/lean4:v4.19.0`. The formal whole-program validator was introduced in merged PR #151 (`360043c8704546857caa4c82f2978c7709399016`). The executable typed in-memory validator was merged in PR #163 (`294d34361c31dc768e60a017a3fd0718f7a00313`). PR #163's exact head `0e9800397c45359e216ec08c656bb9bed86cd8ef` passed formal run [45508852082](https://github.com/DavidFernee/Capstan/actions/runs/45508852082) and platform/supply-chain run [45508852150](https://github.com/DavidFernee/Capstan/actions/runs/45508852150). The CCAM formal job ran the Lean build, pinned `lean4checker` replay and axiom audit; selected declarations report `propext`, and the five declarations listed in Section 6.6 also report `Quot.sound`. The checker source was pinned to commit `e11f65c651edd58d68ba260015d2bfde5102cd7f`. The CCAM job did not run Nanoda.

**Reproduction commands (CCAM formal job):** from `verification/lean/`, run `lake build CapstanVerification --wfail`; obtain `lean4checker` at tag `v4.19.0` and verify commit `e11f65c651edd58d68ba260015d2bfde5102cd7f`; verify its `lean-toolchain` matches the project's; build the checker with `lake build`; run `lake env lean4checker/.lake/build/bin/lean4checker CapstanVerification`; then run `lake env lean AxiomAudit.lean`. The workflow also performs an explicit scan rejecting `sorry`, `admit` and local `axiom` declarations before the build. The recorded CI run is the authoritative successful execution of these steps.

**Reproduction status:** an exact-head successful CI record now exists for the CCAM Lean project and merged validator. Complete logs, a full axiom-dependency inventory and independent human reproduction/review are still required before submission.

## Author and submission notes

- Confirm the author's preferred affiliation and contact details before submission.
- Complete a systematic related-work search and novelty assessment.
- Re-run the Lean build and pinned `lean4checker` on the exact manuscript revision; archive complete logs and axiom output. Keep the separate allocator/GC Nanoda result distinct.
- Resolve the normative/formal final-instruction mismatch and the instruction-entry/function-entry abstraction mismatch.
- Prove the relationship between the merged Capstan-native validator and the Lean validator/model; a typed result representation alone is not implementation refinement.
- Do not submit this draft as a paper claiming a verified compiler or verified CCAM implementation.
