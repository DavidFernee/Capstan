# Capstan Native Compiler Architecture RFC

**Status:** Proposed architecture baseline; subject to implementation and formal validation  
**Revision:** 1.0  
**Date:** 2026-11-27  
**Target:** C-free, self-hosting, optimising, resource-aware and independently auditable Capstan compiler  
**Authority:** Governs compiler-stage boundaries and dependencies. Does not silently amend the Capstan language specification or normative CCAM v0.1.

## 1. Decision and objective

Adopt a layered compiler architecture with explicit, versioned representations and independently checkable translation obligations:

```
Capstan source
  -> lexer / parser / resolver / checker
  -> checked source core (existing typed-core contract)
  -> CCAM (canonical typed core IR and abstract execution semantics)
  -> [optional] derived optimisation IR (e.g. typed SSA/CFG)
       -> validator + refinement back to CCAM
       -> validated CCAM
  -> target-specific native lowering
       -> optional implementation-only low-level/target IRs
       -> object writer / linker
  -> executable + assurance manifest
```

The generated-C compiler remains a temporary compatibility and differential-testing path. It is not part of the target production pipeline and must not become a dependency of the C-free compiler, runtime or generated programs.

The target is not a nominal 10/10 score. It is a compiler that meets measurable acceptance gates, reports every residual assumption and refuses to claim properties that have not been established.

## 2. Governing principles

1. **One source-language specification.** The language specification defines source semantics. No backend or IR invents alternative observable behaviour.
2. **One canonical abstract execution contract.** CCAM remains the machine-level semantic authority for supported execution profiles.
3. **Multiple representations, not multiple authorities.** Each IR has a defined purpose, validity predicate and translation relation.
4. **Fail closed.** Unsupported syntax, unknown effects, unbounded inputs, invalid certificates and unsupported target features are rejected or handled by a documented safe fallback.
5. **Preserve security distinctions.** Types, ownership, taint, secrecy, authority, effects, source provenance and resource obligations survive until their enforcement or proof point.
6. **Optimise only under a stated semantic relation.** Tests and differential execution are evidence, not substitutes for proof or validation.
7. **Keep proof claims scoped.** A theorem about a model is not a theorem about a concrete executable until implementation correspondence is established.
8. **Keep the trusted computing base explicit and small.** Producers may be complex; validators, loaders and certificate checkers should be independently reviewable.
9. **Version contracts.** Semantic changes require a new version/profile or compatibility decision, never an undocumented implementation extension.
10. **Measure quality.** Correctness, security, resource behaviour, compile time, runtime performance, code size, reproducibility and usability require reproducible tests.

## 3. Representation architecture

### 3.1 Frontend AST

The parser produces a syntax tree preserving source structure and exact source spans. AST nodes are not executable and are not a trusted typed representation.

The resolver assigns stable declaration identities. Names are never the sole identity after resolution. The frontend enforces bounded source size, import count/depth, token count, nesting, AST node count and diagnostic volume using a compilation-wide budget.

### 3.2 Checked source core and direct lowering

The initial C-free frontend contract is the checked source core defined by the language-semantics workstream and the existing typed-core proposal. The compiler must preserve stable binding identity, resolved types, explicit left-to-right sequencing, short-circuit behaviour, source spans, security classifications, effect/authority requirements and bounded compilation work.

Do not introduce a separate CHIR instruction language or duplicate CCAM's value and operation semantics. The first vertical slice remains:

`source -> lexer/parser -> checker -> deterministic lowering -> complete CCAM validation -> CCAM evaluator`

The current mutable AST with optional type annotations is not automatically a trusted typed IR. The lowerer must consume only a successfully checked tree, independently enforce its accepted subset and fail closed on unsupported or inconsistent nodes. The compiler architecture workstream must coordinate any strengthening of the checked-source contract with the language-semantics owner.

### 3.3 CCAM — canonical typed core IR and abstract machine

CCAM is both the canonical typed core IR and the reference abstract execution machine for the initial C-free programme. It is the only semantic authority for the supported core. The compiler lowers the checked source subset directly into CCAM; the evaluator defines CCAM execution; native backends and derived optimisers must preserve CCAM outcomes.

- CCAM v0.1 remains frozen for its documented scalar profile, subject to the approved language-core semantic corrections. In particular, preserve the established remainder rule: remainder by zero traps, while `INT64_MIN % -1 == 0`; do not inherit host-language undefined behaviour.
- Experimental aggregate, memory, output and capability instructions are not v0.1 conformance.
- CCAM v0.2 (or separately versioned profiles) specifies typed references, object layouts, allocation, aggregate operations, strings/bytes, frame semantics, effects, traps and resource accounting before those features become normative.
- Strict decoding, duplicate-key rejection, exact integer parsing, closed schemas and whole-program validation are required before untrusted external CCAM documents are accepted.
- The internal multi-function side-table representation must have a specified, validated mapping to canonical call representation.
- Every extension defines validation, dynamic semantics, resource charges, failure atomicity, serialization and formal obligations.

The reference evaluator is an executable implementation of CCAM, not a replacement for its specification. Its concrete transition relation must be related to the Lean machine.

### 3.4 Derived optimisation IR (optional)

A typed SSA/CFG representation may be introduced only as a derived optimisation representation when a measured optimisation or analysis need justifies it. It is not a second semantic authority and is not required for the first native vertical slice.

The derived IR must:
- be constructed only from a fully validated CCAM program;
- define a closed schema, type/CFG verifier, dominance and use-def rules;
- represent traps, trap ordering, observable effects, memory dependencies and resource charges explicitly;
- retain source provenance and security metadata needed by later validation;
- provide a deterministic translation back to CCAM;
- validate the reconstructed CCAM before execution or native lowering;
- have a simulation/refinement argument to CCAM and differential conformance tests;
- give every optimisation pass a preservation contract.

The initial SSA choice (block arguments or phi nodes), memory/effect token design and resource-cost model remain deferred until a concrete prototype and proof interface are reviewed. Do not freeze additional constructors or semantics in parallel with CCAM.

No implicit undefined behaviour is introduced to simplify optimisation. Integer overflow, division by zero, invalid references, bounds violations and other language-defined failures retain their specified outcomes.

### 3.4 CCAM

CCAM remains the canonical abstract execution machine, not a generic name for every compiler IR.

- CCAM v0.1 remains frozen for its documented scalar profile.
- Experimental aggregate, memory, output and capability instructions are not v0.1 conformance.
- CCAM v0.2 (or separately versioned profiles) specifies typed references, object layouts, allocation, aggregate operations, strings/bytes, frame semantics, effects, traps and resource accounting before those features become normative.
- Strict decoding, duplicate-key rejection, exact integer parsing, closed schemas and whole-program validation are required before untrusted external CCAM documents are accepted.
- The internal multi-function side-table representation must have a specified, validated mapping to canonical call representation.
- Every extension defines validation, dynamic semantics, resource charges, failure atomicity, serialization and formal obligations.

The reference evaluator is an executable implementation of CCAM, not a replacement for its specification. Its concrete transition relation must be related to the Lean machine.

### 3.5 Native backend lowering forms (optional)

A backend may use one or more target-independent low-level representations internally, but these are implementation forms, not new semantic authorities or mandatory pipeline stages. The initial native prototype may lower validated CCAM directly to target instructions. If a reusable low-level IR is introduced, it must be explicitly versioned, bounded, validated, and connected to CCAM by a backend simulation or independently checkable translation relation. It may introduce:
- explicit machine-sized values and legalisation;
- virtual registers and register classes;
- explicit calling-convention-independent call/return operations;
- stack slots and frame objects;
- explicit loads/stores and alignment;
- safepoint/root-map operations;
- explicit trap and runtime-call ABI operations;
- target-neutral relocation and symbol intents;
- explicit resource-check operations where runtime enforcement remains necessary.

A low-level backend form does not contain unvalidated host pointers or assume a source reference is a native address. References remain opaque handles until a target/runtime lowering pass establishes their representation under the approved memory ABI.

### 3.6 Target-specific instruction representation

A target-specific instruction representation is optional and target-specific, versioned by architecture, ABI, object format and platform profile. It specifies:
- legal instruction encodings and operand constraints;
- register classes, reserved registers and calling convention;
- stack alignment and frame layout;
- register allocation and spill semantics;
- relocation kinds and range rules;
- section and segment permissions;
- symbol binding and visibility;
- unwind/trap metadata;
- stack maps and safepoint relocation;
- entry-point and runtime ABI;
- platform syscall/import boundary.

A target-specific instruction stream is valid only for its declared target profile. A target profile cannot be inferred from the build host.

## 4. Translation contracts

Every adjacent stage has a named translation and an acceptance relation.

| Translation | Required contract |
|---|---|
| Source/checker -> CCAM | Accepted-subset completeness, source semantic preservation, explicit sequencing and source-span mapping |
| CCAM -> derived optimisation IR | Validated conversion, CFG/SSA invariants and preservation of CCAM observables |
| Derived optimisation IR -> CCAM | Valid reconstruction, simulation/refinement, trap/effect/resource preservation |
| CCAM -> native target lowering (direct or through optional backend forms) | Machine-level simulation, value representation, memory and call semantics preserved |
| Target instruction stream -> object | Encoding validity, relocation correctness, section/permission correctness |
| CLIR -> CTIR | Instruction selection, register allocation, stack layout, relocations and ABI correctness |
| CTIR -> object | Encoding validity, relocation correctness, section/permission correctness |
| object -> executable | Link/load integrity, symbol resolution, segment policy and manifest binding |

Each contract specifies:
1. source and target version/profile;
2. preconditions and accepted input subset;
3. observable behaviours being preserved;
4. permitted stuttering or administrative steps;
5. traps and error mapping;
6. resource accounting and permitted overhead;
7. security properties and authority boundaries;
8. failure behaviour;
9. proof or validation method;
10. residual assumptions and trusted components.

The top-level correctness argument is compositional. It is not acceptable to infer end-to-end correctness merely because each stage has unit tests.

## 5. Semantic preservation and observable behaviour

The observable semantics include, as applicable:
- returned values and program termination;
- output bytes and ordering;
- trap class, stable code and specified source location;
- externally visible state changes;
- capability acquisition, use and attenuation;
- information-flow policy outcomes;
- resource charges and quota failures;
- concurrency observations under the specified memory model.

The refinement relation states whether it is trace inclusion, forward simulation, backward simulation, bisimulation or a combination. It accounts for target stuttering and implementation steps without hiding observable effects.

The compiler must never convert a specified trap into wraparound, undefined behaviour, an arbitrary host exception or silent process termination.

For security properties such as noninterference, the programme uses relational proofs or other appropriate hyperproperty methods. A single-run trace theorem is insufficient to establish confidentiality. The assurance model distinguishes architectural functional correctness, language-level information-flow security, and microarchitectural/speculative leakage properties. A constant-time or speculative-noninterference profile requires an explicit attacker model, observable-event model and speculation assumptions. Register allocation, spills, instruction selection, scheduling and memory layout are included in that profile's proof/validation scope; source-level secret taint alone does not establish constant-time native execution.

## 6. Optimisation and translation validation

Optimisation is a first-class subsystem, not an informal collection of rewrites.

### 6.1 Initial optimisation order

1. Constant folding and exact constant evaluation.
2. Sparse conditional constant propagation.
3. Dead-code and unreachable-block elimination.
4. Copy propagation and canonicalisation.
5. Common-subexpression elimination with explicit memory/effect dependencies.
6. Range analysis and proof-backed bounds-check elimination.
7. Inlining under code-size and resource policies.
8. Loop-invariant code motion where effect and alias proofs permit.
9. Escape analysis and allocation/lifetime optimisation.
10. Tail-call and calling-convention transformations where semantics permit.
11. Instruction selection and register allocation.

The order is a dependency guide, not a requirement to implement every pass before useful native execution.

### 6.2 Validation policy

Every optimisation pass declares:
- stable pass identifier and version;
- input/output IR versions and canonical schemas;
- invariants it assumes and establishes;
- semantic relation and observable events;
- effect and memory model;
- proof/validator status and validator identity;
- targeted negative tests, adversarial corpus and pass-directed fuzzing strategy;
- deterministic resource limits and timeout policy.

The compiler emits a canonical compilation trace containing exact pre-pass and post-pass representations, pass identity/version, compiler build identity, target/profile and relevant analysis hints. The trace encoding has a bounded strict parser, canonical serialization and round-trip tests. A certificate is bound to the exact trace and final executable digest. Trace production/parsing is a small, explicit TCB boundary.

Where a pass is not formally verified, translation validation independently checks the individual result or the pass remains outside the assured profile. Validation failure rejects the transformed output. There is no permissive fallback that silently trusts the optimiser.

A translation validator is independently reviewable relative to the transformation producer wherever practical. It binds its result to canonical hashes of the exact input, output, semantic profile, validator version and policy.

Differential testing, fuzzing, mutation testing and compiler diversity supplement validation; none is mislabeled as proof.

## 7. Memory, references and garbage collection

Memory representation is a blocking architectural dependency and must be frozen before the production collector and aggregate native backend are completed.

### 7.1 Reference representation

The normative design uses opaque, non-forgeable-at-language-level references with:
- arena/heap identity;
- slot or object identity;
- generation or equivalent stale-reference detection;
- type/layout descriptor identity;
- bounds/extent where relevant;
- explicit nullability where supported.

A source-level reference is never assumed to equal a raw native pointer. Native handles are resolved through validated runtime tables or a formally specified target representation.

### 7.2 Memory domains

Keep distinct policies for:
- compiler-lifetime arena;
- ordinary managed heap;
- frame-scoped scratch regions;
- explicitly owned external resources;
- secret-bearing storage.

Each domain has allocation, lifetime, mutation, reclamation, zeroisation and quota rules. No domain silently inherits another domain's lifetime semantics.

### 7.3 Precise GC contract

The compiler/runtime contract specifies:
- object descriptors and pointer maps;
- frame layout and root slots;
- safepoint placement;
- live-reference computation;
- root publication and relocation;
- treatment of references in registers, spills and temporaries;
- collection during runtime helpers;
- frame unwind and trap cleanup;
- collector failure behaviour.

A proof obligation establishes that every live managed reference is discoverable at every collection point and that relocated references are used after a moving collection. If the initial collector is non-moving, document that choice and do not claim relocation correctness.

## 8. Resource semantics

Resource accounting is compositional and multidimensional. The initial abstract resource vector is:

[
R=(F,S,H,O,I,W)
]

where:
- F: execution fuel / abstract machine steps;
- S: stack and call-depth consumption;
- H: heap and temporary allocation;
- O: output volume;
- I: externally charged IO;
- W: compiler/validator work, including bounded parsing and analysis.

Every operation has a specified charge point and failure atomicity. Every function/module has a resource summary with one of:
- proved upper bound;
- statically derived conservative bound;
- runtime-enforced quota;
- unknown/unbounded, rejected in profiles requiring a bound.

Composition accounts for call multiplicity, recursion, loops, exceptional paths, allocations, output and host calls. A scalar instruction budget is not a substitute for memory, stack or IO limits.

The semantics distinguish resource exhaustion from semantic traps and OS-level failures. Accounting overhead itself is bounded and documented.

## 9. Effects, capabilities and information flow

The compiler preserves explicit authority and information-flow metadata across all IRs.

- Functions declare effects and required capabilities.
- Call sites satisfy callee authority requirements.
- Capabilities are explicit values/handles with defined attenuation, lifetime and revocation semantics where supported.
- No ambient filesystem, network, process, clock, randomness or device access is implicitly granted.
- External calls are explicit effectful operations with declared failure and resource behaviour.
- Taint/validation provenance is tracked by stable binding identity and typed access path, not variable spelling.
- Secret values have explicit permitted operations, storage rules and zeroisation obligations.
- Optimisations cannot remove checks, reorder effects or leak secrets unless the corresponding proof justifies it.

The native ABI does not erase capability identity or allow a forged integer/pointer to acquire authority.

## 10. Native object and toolchain architecture

The initial supported target remains Linux x86-64, System V AMD64, with other targets added as independent profiles.

The production toolchain progressively owns:
1. target instruction selection and encoding;
2. object-file section/symbol writer;
3. relocation application and validation;
4. deterministic linker;
5. executable layout and permission policy;
6. loader/manifest validation;
7. runtime entry and syscall adapter.

GNU assembler/linker may remain development tools during transition, but their use is declared. The final C-free claim distinguishes:
- C-free generated program;
- C-free compiler implementation;
- Capstan-native object/link pipeline;
- fully self-hosted bootstrap;
- independent bootstrap assurance.

No one milestone implies the others.

The native backend has a documented ABI for integer widths, booleans, aggregates, arguments, results, stack alignment, traps, runtime calls, root maps and external capabilities. Current register-only argument limitations are prototype constraints, not the final ABI.

### 10.1 Terminal-result and trap transport

The process ABI is not the CCAM result ABI. In particular, Linux process exit status exposes only the low eight bits and cannot represent arbitrary signed-64 return values. It must never be used as the general transport for `Halt(Int64)`.

The native result contract must distinguish:
- `Halt(Int64(value))` with the exact signed-64 value;
- `HaltVoid`;
- CCAM traps, preserving stable trap code, function identity, program counter, explicit-trap detail and instruction-step count;
- platform/transport failures, kept separate from CCAM traps;
- compile-time validation failures, which produce no executable result record.

The initial Linux profile should evaluate the existing bounded fd-3 result-record proposal in `research/native-bootstrap/NATIVE-RESULT-ABI.md`. If adopted, the launcher must supply a fresh bounded result sink as an explicit capability; the executable must not discover a path or silently fall back to stdout, stderr or exit status. The record parser must reject absent, partial, overlong, malformed, duplicate or inconsistent records. The producer must use a fixed-size buffer and bounded write/retry behaviour. The concrete wire format, code assignments and maximum size require a current review and a normative versioned decision before implementation.

The process exit code reports transport/process status only. A launcher must not infer a CCAM return or trap from an exit status, signal, timeout or partial record.

## 11. Formal assurance architecture

Use Lean 4 as the primary machine-checked proof environment, with an explicitly reviewed kernel and no unexamined axioms, unsafe declarations or trusted external oracles in release theorems.

The proof programme is layered. It should be complemented by an incremental certifier that checks individual compiler runs, rather than waiting for every production compiler pass to be proved before providing any machine-checkable assurance. The certifier consumes the canonical compilation trace and checks each pass against a formal translation relation; the soundness of each relation is separately proved. A failed, unknown, timed-out or over-budget check rejects certification.

The layered proof obligations are:
|---|---|
| Source core | Type soundness and source semantic properties |
| Checked source core | Source typing and accepted-subset preservation obligations |
| CCAM | Machine progress/determinism and safety for declared profiles |
| Derived optimisation IR (if present) | CFG/SSA invariants, effect/memory consistency and refinement back to CCAM |
| Concrete evaluator | Simulation/refinement to Lean CCAM |
| Memory | Reference validity, descriptor safety, lifecycle and root completeness |
| Optimisations | Pass correctness or independent translation validation |
| Native backend forms (if present) | Machine lowering and ABI simulation |
| Object/link | Encoding, relocation, image-policy validation |
| Runtime/host | Capability, resource and memory-boundary correctness |
| Certificate | Exact binding to source, semantics, target, policy and executable |

Every theorem states exact scope, assumptions and model correspondence. CI rejects theorem changes that introduce new axioms, sorry, unsafe trust or weakened hypotheses without explicit review and documented exception.

The executable implementation and Lean model share a canonical conformance corpus. The corpus includes positive, negative, boundary, mutation, adversarial and resource-exhaustion cases.

## 12. Evidence-carrying executable format

The eventual executable package binds:
- source manifest and source digests;
- compiler build identity and dependency closure;
- language and IR versions;
- CCAM profile and semantic version;
- target triple, ABI and object format;
- optimisation passes and validation records;
- capability/effect manifest;
- resource contract and residual runtime quotas;
- proof/certificate identifiers and checker version;
- executable and relevant section hashes;
- build provenance and reproducibility metadata.

The independent checker validates canonical encodings, hashes, policy and certificates. A signature authenticates a claim's origin; it does not prove semantic correctness. The manifest never implies stronger guarantees than the checked evidence establishes.

## 13. Bootstrap and trust separation

Retain the S0-S3 bootstrap plan, with mandatory distinctions:

- S0 is an independently reviewed bootstrap seed, never a production dependency.
- S1 is the first native Capstan compiler for a declared subset.
- S2 compiles the same source and is compared against S1 under a canonical output relation.
- S3 and later stages establish reproducibility and self-hosting, not correctness by themselves.
- A diverse bootstrap path and independent clean-room build provide additional assurance.
- Production builds succeed with S0, Python, generated C and the C toolchain unavailable.
- Build manifests pin toolchain, dependencies, environment, options and inputs.
- Bootstrap trust assumptions remain disclosed; no fully verified bootstrap claim until the corresponding proof exists.

## 14. Concurrency and portability

The first assured compiler profile may be single-threaded. The architecture reserves explicit semantics for future concurrency:
- memory model and atomics;
- data-race policy;
- thread creation/join and cancellation;
- capability transfer;
- GC coordination;
- deterministic resource accounting;
- trap and unwind behaviour.

Do not claim thread safety merely because data structures are currently used by one thread.

Targets are independent assurance profiles. Linux x86-64 is the first target. AArch64, macOS and Windows require separate ABI, object, loader, syscall and runtime contracts plus their own conformance suites. Portability is not established by sharing a target-neutral IR.

## 15. Performance and engineering quality gates

A 10/10 verdict requires measured evidence, not adjectives.

The benchmark programme reports:
- compile-time throughput and peak memory;
- incremental build performance;
- executable size;
- runtime throughput and latency;
- allocation/GC throughput and pause behaviour;
- optimisation compile-time overhead;
- validation/certificate size and checking time;
- deterministic reproducibility;
- performance against clearly identified baselines;
- regressions with confidence intervals and reproducible workloads.

No performance claim is accepted without hardware, OS, compiler revision, flags, workload, warmup, repetitions and raw results. Security-critical optimisations do not bypass assurance gates for speed.

## 16. Release profiles and claim discipline

Define explicit profiles:
- **Experimental:** may include prototypes; no broad safety claim.
- **Conforming CCAM:** conforms to a named normative CCAM profile.
- **Assured scalar native:** exact scalar subset with validated native semantics and disclosed platform assumptions.
- **Assured managed native:** memory/aggregate profile with proven or independently checked runtime obligations.
- **C-free production:** no C compiler, generated C, C runtime or Python in the production compiler/program path as specifically defined.
- **Self-hosted:** compiler builds itself from Capstan source under a pinned bootstrap contract.
- **Certified:** exact executable has independently checked evidence for the named policy/profile.

A release claims only the highest profile whose gates it actually passes. Profiles are cumulative only where dependencies are satisfied.

## 17. Immediate implementation sequence

### A0 — Architecture freeze
- Review and merge this RFC.
- Add it to the design map and research register.
- Publish IR schemas and invariants.
- Inventory existing modules against the new boundaries.
- Mark incompatible prototypes experimental rather than deleting useful work.

### A1 — Semantic and memory contracts
- Reconcile normative CCAM v0.1 with Lean single-frame profile.
- Specify CCAM v0.2 aggregate/reference semantics.
- Specify canonical call encoding and strict decoder.
- Freeze handle/object/frame/root-map representation.
- Define resource vector and charge points.

### A2 — Executable foundations
- Strengthen the checked-source/lowering contract without introducing a competing semantic IR.
- Integrate aggregate semantics with the multi-frame evaluator only under a separately versioned normative CCAM profile.
- Establish one conformance corpus across evaluator, Lean and native prototype.
- Prototype a derived SSA/CFG optimiser only where justified; validate round-tripping to CCAM before adoption.

### A3 — Native foundations
- Freeze native ABI and trap ABI.
- Complete aggregate and memory lowering.
- Add validators for any selected low-level or target-specific backend representation; retain direct CCAM-to-native lowering if it is simpler and easier to assure.
- Implement object writer and relocation model.
- Add differential and adversarial native execution tests.

### A4 — Optimisation and assurance
- Add first validated optimisation passes.
- Prove or independently validate source-to-CCAM preservation for the accepted subset.
- Prove evaluator-to-Lean refinement.
- If a derived optimisation IR is adopted, prove or validate its refinement back to CCAM.
- Prove or validate CCAM-to-native simulation.
- Add certificate binding and independent checking.

### A5 — Bootstrap and release
- Compile actual compiler source through the native path.
- Demonstrate production builds with bootstrap-only dependencies absent.
- Complete diverse reproducible bootstrap.
- Publish benchmark, security and assurance reports.
- Release only under a profile whose acceptance evidence is complete.

## 18. Acceptance gates for the final 10/10 verdict

A final 10/10 verdict requires all of the following, with no unresolved critical issue:

1. **Language correctness:** normative source semantics and type-safety results are explicit and implementation-linked.
2. **IR integrity:** every representation has a closed schema, validator, invariants and versioned translation contract.
3. **CCAM conformance:** the concrete evaluator conforms to the normative declared profile; no undocumented semantic extensions.
4. **End-to-end correctness:** compositional proof or independently checked validation connects source to exact native executable.
5. **Memory safety:** references, bounds, object layouts, lifetimes, frames and GC roots are correctly enforced and evidenced.
6. **Security preservation:** authority, taint, secrets and effects survive compilation; residual host assumptions are explicit.
7. **Resource safety:** fuel, stack, heap, output, IO and compiler work are bounded or explicitly rejected as unknown under the selected profile.
8. **Optimisation integrity:** assured transformations are proved or independently validated; adversarial fuzzing and regression suites pass.
9. **Native toolchain integrity:** target ABI, exact full-width terminal-result/trap transport, encoding, relocations, object writer, linker, loader and runtime satisfy their contracts.
10. **Bootstrap integrity:** C-free self-hosting and independent reproducible bootstrap are demonstrated, with seed trust disclosed.
11. **Performance:** representative workloads meet published, reproducible performance and resource budgets against stated baselines.
12. **Portability and usability:** supported targets have independent conformance evidence; diagnostics, tooling and documentation are production quality.
13. **Supply-chain assurance:** exact source, build inputs, artefact, evidence and policy are cryptographically bound and independently verifiable.
14. **Governance:** every guarantee has an owner, status, tests, proof obligations, known limitations and a change-control policy.

A missing critical gate means the verdict is not 10/10. A design document alone cannot satisfy an implementation gate.

## 19. Explicit non-goals and safeguards

- Do not replace CCAM with an unreviewed second machine.
- Do not make SSA syntax normative language semantics.
- Do not introduce undefined behaviour to enable optimisation.
- Do not assume native pointers are safe references.
- Do not treat a passing test suite as a proof.
- Do not treat self-hosting or reproducibility as correctness.
- Do not treat signatures or provenance as semantic certificates.
- Do not make every research prototype a production dependency.
- Do not claim universal security, zero vulnerabilities or superiority to every language.
- Do not weaken assurance gates to accelerate PR merges.

## 20. Decision record

**Accepted architectural direction:** checked source core lowers directly to CCAM, the canonical typed core IR and abstract machine. Any SSA/CFG optimiser is derived, optional and must validate/refine back to CCAM. Native low-level representations are backend implementation forms with explicit simulation obligations.

**Accepted assurance direction:** compositional semantic preservation, translation validation for unverified transformations, independently checked evidence and explicit TCB.

**Accepted initial target:** Linux x86-64 freestanding native profile, with platform-specific assurance gates.

**Deferred decisions:** exact SSA encoding; moving versus non-moving initial collector; object format and linker staging; proof-certificate encoding; concurrency memory model; additional target ABIs. Each deferred decision is resolved before its dependent production feature is declared complete.

**Change policy:** any change to representation semantics, observable behaviour, memory/reference model, ABI or assurance profile requires an RFC amendment, migration plan, compatibility analysis and updated proof/test obligations.
