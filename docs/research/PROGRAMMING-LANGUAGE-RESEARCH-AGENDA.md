# Capstan Programming-Language Research Agenda

> **Status:** Research charter / proposed programme  
> **Revision:** 2026-11-25  
> **Scope:** Language theory, compiler, execution, security, assurance, developer experience and ecosystem  
> **Architecture authority:** `docs/DESIGN-MAP.md` and the relevant subsystem specifications  
> **Coordination:** GitHub issue [#25](https://github.com/DavidFernee/Capstan/issues/25)  
> **Research evidence register:** [RESEARCH-REGISTER.md](RESEARCH-REGISTER.md)

## 1. Mission and research thesis

Capstan should become a programming language whose distinctive guarantees are not merely coding conventions, library promises or optional analysis reports. A Capstan program should be able to state, and the Capstan toolchain should be able to enforce and substantiate:

- **what the program means** (semantics);
- **what it is allowed to do** (authority, effects and information access);
- **what resources it may consume** (time/fuel, stack, memory, allocation and other bounded resources);
- **which properties it must preserve** (safety, invariants and functional contracts); and
- **what evidence supports those claims** (machine-checkable certificates, independently checkable proofs, tests and explicit residual assumptions).

The long-term research proposition is an **evidence-carrying, resource-aware, capability-oriented programming system**. Its language, compiler, intermediate representation, runtime and executable format should form a coherent assurance chain. Static guarantees should compose across modules and calls where soundly derivable; residual dynamic obligations should be explicit and enforced; evidence should be bound to the exact program, semantics, target and policy to which it applies.

The objective is not to reproduce every feature of Rust, Swift, C++ or another established language. Nor should Capstan claim that those languages cannot individually support ownership, static analysis, contracts, capabilities, proof tools or resource controls. They have mature and valuable strengths. The research opportunity is to make a **particular integrated combination** a first-class, end-to-end property of Capstan: programs express authority and resource constraints, compilation preserves them, execution enforces residual obligations, and independently checkable evidence accompanies the artefact.

The competitive claim must be earned. It becomes credible only when the programme demonstrates capabilities that are difficult to obtain together in existing mainstream systems languages, and publishes reproducible comparisons showing exactly where Capstan is stronger, weaker or simply different.

### 1.1 North-star statement

> A Capstan executable should be able to carry independently checkable evidence that it was produced from a specified program under a specified semantic contract, that its permitted authority is bounded by an explicit capability policy, and that its stated resource and safety guarantees are preserved by the execution path—subject to a disclosed and minimised trusted computing base.

This is a research target, not a description of current implementation. Every claim must identify its status, scope, assumptions and supporting artefacts.

### 1.2 What would make Capstan genuinely different?

The programme will test five candidate differentiators:

1. **Unified guarantee composition.** Types, effects, ownership, capabilities, resource bounds and logical contracts compose through one coherent model rather than existing as disconnected annotations and tools.
2. **Evidence that travels with software.** Executables or packages carry compact, versioned evidence that a small independent checker can validate without trusting the full compiler or proof producer.
3. **Resource guarantees with operational meaning.** Resource contracts have defined semantics, compose across calls and modules, and are enforced or conservatively rejected when static proof is unavailable.
4. **Authority as a language-level property.** Code receives explicit, attenuable authority; ambient access is minimised; authority flow can be analysed and checked at module, function and execution boundaries.
5. **A verifiable implementation chain.** The same semantic contract connects source checking, canonical IR, validation, evaluation, native code and runtime services, with refinement obligations and evidence at each boundary.

A feature is not a differentiator merely because Capstan has syntax for it. The differentiator is the enforceable and independently assessable guarantee, including its failure modes and trust assumptions.

## 2. Research principles

1. **Specify before claiming.** Define semantics and threat model before implementing a guarantee.
2. **Make claims falsifiable.** State what observation would disprove each hypothesis.
3. **Separate model from implementation.** A theorem about a formal model is not automatically a theorem about compiler or runtime code.
4. **Compose conservatively.** Unknown or unproved bounds remain unknown; never turn absence of evidence into a guarantee.
5. **Minimise and disclose trust.** Inventory compilers, runtimes, proof checkers, platform adapters, build systems and hardware assumptions.
6. **Prefer independent checking.** Keep certificate checking smaller and simpler than certificate production where feasible.
7. **Measure against serious baselines.** Compare with established languages, compilers, verification systems and runtime models using reproducible workloads.
8. **Preserve practical usability.** A theoretically strong language that is too difficult to learn, debug or deploy will not achieve adoption.
9. **Publish negative results.** Failed hypotheses, overheads, incompleteness and limitations are research findings.
10. **Do not destabilise the foundation.** Research prototypes and experimental language features must not silently change normative CCAM or release semantics.
11. **No marketing-by-adjective.** Terms such as safe, verified, bounded, deterministic and C-free require scoped definitions and evidence.
12. **Research independently, integrate deliberately.** Work packages can progress in parallel, but shared semantic contracts and merge dependencies remain explicit.

## 3. Research portfolio

Each area below is a standing research stream. It is not a mandate to implement every fashionable feature. Each stream must identify a question that matters to Capstan's thesis, review the strongest existing approaches, and recommend either adoption, adaptation or a reasoned decision not to pursue.

### R1. Formal semantics and language foundations

**Questions**
- What is the smallest useful formal core for Capstan?
- Which source-language behaviours must be defined precisely: evaluation order, integer semantics, traps, exceptions, mutation, aliasing, concurrency and observable effects?
- Can the semantics be modular while preserving compositional reasoning?
- How should language versions evolve without invalidating old evidence?

**Candidate work:** operational and denotational semantics; contextual equivalence; refinement relations; mechanised metatheory; canonical semantic test vectors; semantics versioning.

**Success evidence:** a versioned formal core, machine-checked properties with explicit assumptions, conformance tests, and traceable correspondence to implementation.

### R2. Type systems, contracts and abstraction

**Questions**
- Can ordinary types, refinement predicates, ownership, lifetimes, effects, capabilities and resource contracts share a compositional model?
- Which guarantees should be inferred, which explicit, and which require proof?
- Can generic abstractions preserve useful guarantees without making type checking unpredictable?

**Candidate work:** refinement and dependent types where justified; linear/affine types; ownership and borrowing; effect polymorphism; trait/interface constraints; typestate; contracts; gradual or proof-carrying boundaries.

**Success evidence:** a formal typing discipline, soundness results for a clearly bounded core, usable diagnostics, and benchmarked compile-time and annotation costs.

### R3. Memory, ownership and resource lifecycle

**Questions**
- Can memory safety and resource lifecycle be expressed beyond conventional ownership/borrowing?
- How should arenas, regions, deterministic destruction, shared ownership and foreign resources compose?
- Can APIs make leaks, use-after-free, double release and invalid lifecycle transitions unrepresentable or safely rejected?

**Candidate work:** ownership, lifetimes, regions, borrow checking, affine resources, deterministic finalisation, bounded allocation, FFI ownership contracts, resource protocols.

**Success evidence:** adversarial tests, formal properties for the chosen core, measured runtime/compile-time overhead, and a documented account of what remains dynamic or trusted.

### R4. Security, capabilities, effects and information flow

**Questions**
- Can authority be explicit in function signatures and module interfaces?
- Can capabilities be attenuated, delegated, revoked or scoped without ambient privilege?
- Can the language express confidentiality and integrity constraints, including secret handling and taint propagation?
- How are effects handled across native and hosted execution?

**Candidate work:** capability types; effect systems and handlers; information-flow control; labelled data; secret lifecycle; sandbox boundaries; policy manifests; proof-carrying authority restrictions.

**Success evidence:** reference semantics, non-interference or confinement properties where feasible, hostile-host tests, capability-leak tests and explicit adapter/TCB analysis.

### R5. Resource-bounded computation

**Questions**
- Which resources can be bounded compositionally: fuel, stack, memory, allocation, output, file descriptors, tasks, energy?
- How can recursive and higher-order calls be bounded without unsound assumptions?
- What should happen when static analysis cannot establish a bound?

**Candidate work:** resource-aware types; amortised analysis; potential methods; sized types; worst-case execution-time analysis; budgets and quotas; compositional contracts; runtime monitors.

**Success evidence:** soundness conditions for each analysis, exact runtime enforcement semantics, predictable behaviour at limit boundaries, and comparisons of bound tightness and analysis cost.

### R6. Concurrency, parallelism and distributed execution

**Questions**
- Can data races, unsafe sharing and protocol misuse be excluded by construction?
- Can structured concurrency, cancellation and failure propagation be made explicit?
- Can deadlock freedom or progress properties be established for useful subsets?
- Can determinism be retained where it matters without forbidding useful parallelism?

**Candidate work:** actor and message-passing models; session types; ownership transfer; structured concurrency; effect-aware tasks; deterministic parallelism; distributed protocols and fault models.

**Success evidence:** formal guarantees for bounded models, stress/fuzz testing, scheduler-independent conformance tests, and performance comparison with Rust, Swift, C++ and relevant runtimes.

### R7. Execution models, CCAM and runtime architecture

**Questions**
- What is the smallest canonical machine that can serve as semantic authority and a stable compilation boundary?
- How can interpreters, native backends and future JITs refine the same machine?
- Which runtime services can be brought into Capstan, and what platform interfaces remain trusted?

**Candidate work:** CCAM evolution; reference evaluator; bounded validation; portable IR; native code generation; ABI contracts; deterministic execution; runtime and standard-library migration; embedded and OS use cases.

**Success evidence:** conformance across execution engines, explicit refinement obligations, target-executed tests, bounded runtime behaviour and a precise trusted-base inventory. C-free claims remain scoped to the exact compiler/build/run path demonstrated.

### R8. Compiler correctness and optimisation

**Questions**
- Which compiler stages should be verified, validated or independently checked first?
- Can optimisation passes produce certificates or be checked by translation validation?
- Can performance optimisation preserve resource and capability contracts?
- How can compiler bugs be found systematically?

**Candidate work:** multi-level IR; SSA; verified transformations; translation validation; proof-producing optimisation; differential compilation; grammar and IR fuzzing; symbolic execution; abstract interpretation; profile-guided optimisation.

**Success evidence:** per-pass semantic preservation evidence or translation validation, reproducible miscompilation testing, performance results and a disclosed proof/validation boundary.

### R9. Evidence-carrying execution and artefacts

**Questions**
- What exactly should an executable certificate assert?
- How can evidence be compact, compositional, versioned and independently checkable?
- How is evidence bound to source, compiler, semantics, target, capabilities and resource contract?
- How are stale, incomplete, forged or incompatible certificates rejected?

**Candidate work:** certificate formats; small checker; proof/object linkage; attestation; evidence caches; module-level evidence composition; revocation and version migration; proof-carrying code interfaces.

**Success evidence:** a checker independent of the producer; mutation and forgery tests; evidence identity and replay rules; size and checking-time measurements; and an end-to-end demonstration over a defined CCAM subset.

This stream is coordinated with the existing draft evidence-carrying execution proposal (PR #214). That proposal is not integrated merely by being drafted, and its obligations must be reconciled with the current merged CCAM and evaluator contracts before implementation.

### R10. Developer experience, diagnostics and human factors

**Questions**
- How can the compiler explain not only that a program is rejected, but which guarantee failed and why?
- Can diagnostics explain effect, authority, ownership and resource constraints in actionable terms?
- How can proof obligations be made understandable without requiring every developer to be a logician?
- What is the usability cost of stronger guarantees?

**Candidate work:** precise diagnostics; counterexample generation; interactive type/effect explanations; LSP; debugging and profiling; proof-aware IDE views; safe refactoring; error recovery; usability studies.

**Success evidence:** task-based usability studies, diagnostic comprehension measures, reduced time-to-fix, and IDE behaviour that never presents unknown or stale evidence as a verified result.

### R11. Metaprogramming, extensibility and language evolution

**Questions**
- How can compile-time computation and macros preserve hygiene, determinism and assurance?
- Can generated code carry evidence and be checked under the same contracts?
- How can the language evolve without silently changing program meaning?

**Candidate work:** hygienic macros; staged computation; compile-time evaluation; safe plugins; DSLs; generative programming; module/version systems; formal migration rules.

**Success evidence:** semantics for expansion and staging, reproducible builds, hygiene/security tests, and explicit compatibility and migration guarantees.

### R12. Interoperability, packages and software supply chain

**Questions**
- How can Capstan interoperate with C and other ecosystems without importing unsound assumptions?
- Can FFI boundaries specify ownership, effects, authority, resource and failure behaviour?
- Can package provenance and compiler evidence compose across dependencies?

**Candidate work:** stable ABI; verified FFI wrappers; module interfaces; reproducible package builds; signed provenance; dependency policy; SBOM integration; secure package manager; evidence-aware linking.

**Success evidence:** hostile FFI tests, ABI conformance, reproducible dependency builds, provenance verification and clearly identified trust boundaries.

### R13. Heterogeneous and specialised computing

**Questions**
- Can Capstan's guarantees survive compilation to GPUs, accelerators, embedded devices and distributed targets?
- Can memory, concurrency and resource contracts account for device-specific behaviour?
- Can energy or latency budgets be expressed and measured honestly?

**Candidate work:** SIMD/vectorisation; GPU kernels; FPGA and accelerator interfaces; embedded/no_std profiles; distributed/edge execution; energy-aware scheduling.

**Success evidence:** target-specific conformance, resource/energy measurements, explicit device assumptions and comparison against established toolchains.

### R14. AI-assisted programming and verified synthesis

**Questions**
- Can specifications be translated into candidate programs whose properties are checked independently?
- Can AI discover invariants, suggest repairs or optimise code without becoming part of the trusted compiler?
- Can generated code be constrained by authority and resource budgets?

**Candidate work:** spec-to-code synthesis; invariant discovery; proof-obligation generation; counterexample-guided repair; verified translation; proof search; machine-generated certificates checked by a small trusted checker.

**Success evidence:** independent checking of every accepted result, benchmarked correctness and usefulness, adversarial prompt/input testing, and strict separation between advisory AI and normative compiler decisions.

### R15. Testing, measurement and scientific reproducibility

**Questions**
- How do we know that a claimed guarantee holds beyond hand-picked examples?
- Can failures be reproduced across compilers, platforms and versions?
- How should Capstan compare fairly with established languages?

**Candidate work:** conformance suites; property-based testing; grammar/IR fuzzing; mutation testing; differential execution; sanitizers; benchmark suites; reproducible experiment harnesses; public claim/evidence register.

**Success evidence:** deterministic reproduction, published datasets and scripts, independently runnable experiments, transparent exclusions and regression gates.

## 4. Integrated research themes

The fifteen streams should not become fifteen disconnected feature programmes. Four cross-cutting themes are the centre of gravity:

### T1. Unified guarantee calculus

A common model for types, effects, ownership, authority, resource budgets and logical contracts. The research question is whether these can compose in a practical language without either unsoundness or intolerable annotation and solver cost.

### T2. Evidence from source to execution

A traceable chain from source acceptance through canonical IR, validation, evaluation/native lowering and runtime boundaries. Each transformation either preserves a guarantee by construction, supplies a checkable certificate, or identifies the residual runtime check.

### T3. Authority- and resource-aware execution

Programs execute with explicit authority and bounded budgets. The system must make the meaning of a budget precise, enforce limits at the correct boundary, and prevent privilege or resource amplification through calls, modules, callbacks and FFI.

### T4. Practical verifiability

The guarantees must be usable by ordinary developers. Diagnostics, IDE support, build tooling and package distribution must expose evidence accurately and make the common safe path straightforward.

## 5. Programme structure and work packages

Organise the research effort into six coordinated groups. These are technical responsibilities, not necessarily separate teams or permanent personnel.

| Group | Primary streams | Principal outputs |
|---|---|---|
| Language Theory and Foundations | R1, R2, R3, R5 | Formal core, type/effect/resource models, metatheory |
| Security and Authority | R4, R5, R12 | Capability model, information-flow model, secure boundary contracts |
| Compiler and Execution | R7, R8, R9 | CCAM, evaluator/backend refinement, certificates and checker |
| Concurrency and Systems | R3, R6, R7, R13 | Resource-safe systems, concurrency model, target execution |
| Developer Experience and Ecosystem | R10, R11, R12 | Tooling, metaprogramming, packages, interoperability |
| Research Infrastructure and Evaluation | R14, R15, cross-cutting | Benchmarks, proof/test infrastructure, reproducibility and claim register |

### 5.1 Work-package size

Work should be allocated as independent, reviewable increments that can be completed in one focused worker session. Each work package must contain:

- one narrowly stated research question;
- a named owner and dependencies;
- a bounded source/document/test/proof scope;
- acceptance criteria that can be checked without subjective interpretation;
- an explicit list of out-of-scope work;
- a handoff describing files changed, commands run, results, limitations and next dependency.

Do not assign a worker an open-ended task such as “implement the type system”. Prefer a sequence such as: survey candidate models; formalise one subset; define conformance vectors; implement one checker rule; prove one lemma; evaluate one benchmark; document the boundary.

### 5.2 Integration rules

- `docs/DESIGN-MAP.md` remains the architecture authority. This agenda does not override it.
- Normative subsystem specifications remain authoritative for their own contracts.
- A research proposal does not alter stable language or CCAM semantics without an explicit versioned decision.
- Workers must read coordination issue #25, claim work and identify dependencies before editing shared files.
- Shared design files require a heads-up and a single integration owner.
- Parallel branches must not independently redefine the same semantic term or contract.
- Merge only after dependency review, exact-head CI and required formal/security checks.
- Every merged research artefact must state whether it is a proposal, prototype, integrated feature, tested property or formal result.

## 6. Phased roadmap

Phases describe dependency and maturity, not rigid calendar dates. Theory and literature reviews in later phases can begin while foundational implementation proceeds.

### Phase A — Establish a trustworthy research baseline

1. Inventory the current language, compiler, runtime, CCAM, formal models and trusted computing base.
2. Create a claim register that separates aspiration, specification, prototype, integrated behaviour, test evidence, model theorem and implementation refinement.
3. Reconcile the evidence-carrying execution proposal with the exact current CCAM/evaluator contract.
4. Stabilise semantic definitions and conformance vectors for the supported core.
5. Establish reproducible fuzzing, differential testing, formal builds and benchmark infrastructure.
6. Document current resource and authority enforcement, including known gaps.

**Gate A:** No major research claim may depend on an ambiguous semantic contract or an undocumented trust assumption.

### Phase B — Demonstrate the first integrated guarantee

1. Select a small, well-defined executable subset.
2. Specify one resource contract (initially shared deterministic fuel and bounded stack are candidates).
3. Specify one capability policy with explicit authority and a narrow host adapter.
4. Define an evidence format bound to the program and semantic/policy versions.
5. Implement an independent certificate checker.
6. Demonstrate that validation and execution enforce the same contract.
7. Add negative, mutation, adversarial and differential tests.
8. Publish limitations and measured overheads.

**Gate B:** An independently reproducible vertical slice demonstrates a guarantee across source/IR/validation/execution, with no unsupported end-to-end claim.

### Phase C — Generalise and compose

1. Extend guarantee composition across functions and modules.
2. Add memory/resource lifecycle contracts.
3. Extend capability/effect checking and information-flow controls.
4. Connect native backends to semantic refinement obligations.
5. Investigate concurrency and progress properties.
6. Develop proof-producing or translation-validated optimisation.
7. Improve diagnostic and IDE presentation of evidence.

**Gate C:** The guarantee model scales beyond a toy example and has quantified precision, usability and performance costs.

### Phase D — Establish independent advantage

1. Select representative systems, security-sensitive and resource-constrained workloads.
2. Implement comparable versions in Capstan and relevant baselines.
3. Measure safety properties, rejected vulnerability classes, resource predictability, performance, compile time, binary size and developer effort.
4. Commission independent review or replication.
5. Publish results, including where Capstan loses.
6. Refine the language based on empirical findings rather than feature accumulation.

**Gate D:** At least one published, reproducible result establishes a meaningful advantage that is not reducible to syntax or marketing.

### Phase E — Production-grade ecosystem

1. Complete the C-free compiler/runtime programme under the separate architecture and release gates.
2. Stabilise package, FFI, ABI and evidence compatibility.
3. Extend target/platform support with per-target conformance.
4. Deliver practical debugging, profiling and IDE workflows.
5. Establish governance for semantic versions, evidence formats, vulnerabilities and long-term reproducibility.
6. Obtain independent security and assurance assessment.

**Gate E:** Production claims are supported by platform-specific evidence, operational tooling, documented residual risks and a sustainable ecosystem.

## 7. Comparative evaluation

Capstan should be evaluated against the strongest relevant systems, not a single straw-man competitor. The comparison set should include Rust, Swift, C++, Ada/SPARK, Zig, OCaml/Haskell where relevant, WebAssembly and specialised verification systems. The exact set varies by research question.

| Dimension | What to measure |
|---|---|
| Memory and lifecycle safety | Classes prevented statically, rejected dynamically, or left residual |
| Type and contract expressiveness | Properties expressible and composable; proof/annotation burden |
| Authority and isolation | Ambient authority, capability attenuation, confinement and information-flow guarantees |
| Resource predictability | Bound soundness, tightness, compositionality and enforcement overhead |
| Concurrency | Race freedom, protocol safety, progress/deadlock guarantees and throughput |
| Compiler assurance | Verified/validated stages, checker size, proof assumptions and known gaps |
| Runtime and native performance | Throughput, latency, memory, startup and binary size |
| Build and developer productivity | Compile time, diagnostics, debugging, refactoring and time-to-correct-solution |
| Interoperability | ABI, FFI safety, package ecosystem and integration cost |
| Portability | Actual tested targets and behavioural conformance |
| Evidence portability | Ability to independently check, cache, distribute and invalidate evidence |

Every comparison must disclose compiler versions, flags, target hardware, workloads, libraries, tuning effort and excluded cases. A language may be better on one dimension and worse on another. Do not compress unlike properties into one headline score.

### 7.1 The competitive standard

The intended proposition is not “Capstan is Rust but safer” or “Capstan replaces C++ everywhere”. It is:

> For applications that require explicit authority, bounded resource use and independently checkable assurance, Capstan will offer an integrated programming and execution model whose guarantees are difficult to reproduce with conventional language-plus-tool combinations.

This claim remains a hypothesis until demonstrated. If a baseline can achieve the same result with comparable assurance, complexity and cost, record that honestly and identify what Capstan contributes beyond it.

## 8. Publication strategy

Build a publication pipeline around independently valuable results. Candidate papers and technical reports:

1. **A compositional calculus for authority, effects and resource contracts in a systems language.**
2. **Evidence-carrying execution: independently checkable guarantees from typed IR to native execution.**
3. **A practical resource-contract system with sound composition and runtime enforcement.**
4. **Capability-oriented systems programming with explicit attenuation and host-boundary mediation.**
5. **Translation validation for a resource-aware compiler pipeline.**
6. **A reproducible evaluation of integrated language-level assurance against mainstream systems languages.**
7. **A formally specified and experimentally validated C-free bootstrap path.**
8. **Usable diagnostics for proof-, effect- and resource-aware programming.**

A paper should be submitted only when it has a precise contribution, comparison with the state of the art, reproducible artefacts and appropriately scoped claims. A repository feature is not automatically a research contribution; novelty and significance require literature review and expert scrutiny.

## 9. Hypothesis and evidence register

Every major research stream maintains a register with the following fields. The repository already has `docs/research/RESEARCH-REGISTER.md`, which remains the authoritative record for candidate papers, exact implementation/proof/test evidence, maturity, publication readiness and claim discipline. This agenda does not replace or duplicate that register: use it for programme hypotheses and work-package coordination, and update the research register when a result changes the evidence or publication status of an existing candidate. Link the two records by stable research-question or paper IDs.

| Field | Required content |
|---|---|
| ID | Stable identifier, e.g. `CAP-RQ-001` |
| Research question | One answerable question |
| Hypothesis | Falsifiable expected result |
| Prior art | Strongest known approaches and citations |
| Model | Formal definitions and assumptions |
| Experiment | Prototype, benchmark, proof or evaluation |
| Baseline | Relevant competing methods |
| Result | Positive, negative, mixed or inconclusive |
| Evidence | Commit, theorem, tests, dataset, scripts and review |
| Limitations | Unproved cases, threats to validity and residual trust |
| Status | Proposed / investigating / specified / prototype / integrated / validated / formally established |
| Owner | Responsible researcher and reviewer |

### 9.1 Initial hypotheses to investigate

- **H1 — Unified composition:** a coherent type/effect/capability/resource model can express useful cross-cutting guarantees with lower integration complexity than separate, loosely coupled analyses.
- **H2 — Independent evidence:** a small checker can validate useful execution certificates without trusting the full compiler or proof producer.
- **H3 — Resource composition:** selected resource bounds can be composed across calls and modules while remaining sound under recursion, failure and adversarial inputs.
- **H4 — Authority confinement:** explicit attenuable capabilities can prevent defined classes of ambient-authority escalation and make authority requirements reviewable at interfaces.
- **H5 — Semantic preservation:** a practical subset of source-to-CCAM-to-native compilation can be supported by a chain of conformance checks, certificates or refinement proofs.
- **H6 — Practical usability:** evidence-aware diagnostics and tooling can make these guarantees usable without prohibitive developer effort.
- **H7 — Measurable differentiation:** on selected workloads, Capstan can provide stronger assurance or resource predictability at a competitive and explicitly measured performance/productivity cost.

No hypothesis is accepted because it sounds plausible. Each requires a literature review and an experiment or proof capable of refuting it.

## 10. Immediate programme backlog

The first allocations should be small enough for one focused session and should avoid competing edits to shared architecture files.

| Priority | Work package | Deliverable | Dependency |
|---|---|---|---|
| P0 | Research baseline inventory | Current-state map of guarantees, implementations, proofs, trust boundaries and gaps | Current default branch |
| P0 | Evidence architecture reconciliation | Crosswalk between PR #214 obligations and merged CCAM/evaluator/validator contracts | Baseline inventory |
| P0 | State-of-the-art review: evidence-carrying execution | Annotated literature matrix, novelty risks and candidate contribution | None |
| P0 | Resource-contract survey | Formal comparison of resource-aware type systems and analyses | None |
| P0 | Capability/effect survey | Comparison of capability systems, effect systems and information-flow models | None |
| P1 | Unified guarantee calculus proposal | Small formal core and explicit non-goals | P0 surveys |
| P1 | Independent checker design | Certificate grammar, trust boundary, validation algorithm and threat model | Evidence reconciliation |
| P1 | Benchmark protocol | Workload selection, baselines, metrics and reproducibility harness | Baseline inventory |
| P1 | Concurrency research review | Candidate model, safety/progress properties and implementation implications | Formal core direction |
| P2 | Developer experience study | Diagnostic taxonomy and usability evaluation plan | Candidate guarantee model |

Each work package should be split further before assignment if it cannot be completed with a reviewable handoff in one session. The programme coordinator should maintain a dependency graph and avoid assigning multiple workers to the same shared file.

## 11. Claim discipline and release language

Use the following vocabulary consistently:

- **Proposed:** an idea or research question exists.
- **Specified:** a normative or research contract is written and reviewed.
- **Prototyped:** an experimental implementation exists.
- **Integrated:** present on the named branch and covered by its tests.
- **Validated:** supported by the stated conformance, adversarial and differential evidence.
- **Formally established:** a machine-checked theorem proves the exact stated model property under disclosed assumptions.
- **Refinement established:** evidence connects the formal model to the named implementation boundary.
- **Independently reproduced:** another party has repeated the stated result.

Never describe the entire language as formally verified because one component has a proof. Never claim that a guarantee applies to native execution merely because it holds in an interpreter. Never claim that resource use is bounded unless the relevant aggregate resources and enforcement paths are included. Never describe a platform as supported based only on host-independent semantics or cross-compilation.

## 12. Risks and anti-goals

### Principal risks

- The unified model becomes too complex to implement, prove or use.
- Static analysis becomes incomplete or expensive, leading to excessive false rejection.
- Resource bounds are technically sound but too loose to be useful.
- Certificate formats or proof dependencies become brittle across compiler and language versions.
- Native backends and runtime services bypass guarantees established at the core level.
- Capability systems are undermined by ambient OS authority or FFI escape paths.
- Formal proofs establish elegant models that do not faithfully represent executable code.
- Benchmark selection favours Capstan or ignores engineering cost.
- The programme fragments into disconnected features and unmaintainable prototypes.
- Novelty claims are made before a thorough literature review.

### Anti-goals

- Reimplement every feature of every mainstream language.
- Promise that all programs can have tight static resource bounds.
- Treat a proof assistant, theorem prover or AI system as infallible.
- Require developers to write proofs for every ordinary operation.
- Hide dynamic checks or residual trusted components behind a “verified” label.
- Change CCAM semantics implicitly to make a prototype easier.
- Optimise benchmark scores at the expense of representative workloads.
- Claim superiority without public, reproducible comparative evidence.

## 13. First decisions for the research steering group

The first steering review should decide:

1. Which minimal guarantee calculus is the first research target?
2. Which bounded CCAM subset is sufficiently mature for the initial end-to-end certificate experiment?
3. Which proof assistant and certificate/checker architecture best minimise the trusted base?
4. Which resource dimensions are in scope for the first compositional contract?
5. Which capability policy and host adapter provide the smallest meaningful authority experiment?
6. Which two or three mainstream baselines and workloads will make the first comparison credible?
7. Which results are intended for a peer-reviewed paper, and which are engineering prerequisites?

These decisions should be recorded as versioned architecture/research decisions, with alternatives and rejected options.

## 14. Definition of programme success

The programme succeeds only if Capstan produces all of the following:

- a coherent, precisely specified model connecting types, effects, authority, resources and contracts;
- an independently checkable evidence mechanism tied to the exact executable and its assumptions;
- demonstrated preservation or enforcement of selected guarantees across source, IR and execution;
- useful compositional resource and capability guarantees with explicit treatment of unknown cases;
- practical diagnostics, tools and ecosystem support;
- reproducible comparative results against serious baselines;
- independent technical review and publishable contributions;
- a truthful, continuously updated account of the remaining trusted base and limitations.

The ultimate goal is not merely to make Capstan another attractive systems language. It is to discover and establish a different engineering proposition: software can carry verifiable statements about its behaviour, authority and resource consumption, and the toolchain can preserve and check those statements through execution.

**The standard is not that Capstan claims to do what other languages cannot. The standard is that Capstan demonstrates, with independently checkable evidence, a coherent set of guarantees that users cannot obtain as an equally integrated and practical property from the conventional alternatives.**
