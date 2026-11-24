# Capstan North Star

**Status:** Proposal for cross-workstream review  
**Owner:** Codex (architecture / compiler workstream)  
**Authority:** This document proposes long-term acceptance criteria. It does not supersede `AGENTS.md`, `docs/DESIGN-MAP.md`, the normative language specification, or decisions made by the language-semantics owner.

## 1. The ambition

Capstan should become a language and toolchain in which a technically sophisticated engineer would choose to build the compiler, runtime, security-critical infrastructure, operating-system components and substantial applications—not because of marketing claims, but because Capstan offers a demonstrably stronger combination of:

- expressive power and composability;
- security and resource-safety guarantees;
- predictable native performance;
- precise, machine-checkable semantics;
- excellent diagnostics and development tools;
- a trustworthy, reproducible and increasingly self-hosted toolchain.

The objective is not to make every program formally verified by default, nor to promise that vulnerabilities can never exist. The objective is to make broad classes of defects unrepresentable or statically rejected, make remaining risks explicit, and attach evidence to every guarantee.

This ambition extends the purpose and principles already established in `docs/DESIGN-MAP.md`. It is a strategic acceptance framework, not a replacement roadmap or a second language specification.

## 2. Non-negotiable engineering principles

1. **Guarantees must have scope.** Every safety claim names the property, assumptions, exclusions, enforcement mechanism, evidence and trusted computing base (TCB).
2. **Safe by construction.** Prefer language and API designs that make invalid states and dangerous authority unavailable over warnings and programmer convention.
3. **Power without ambient authority.** Code receives explicit capabilities; dependencies cannot silently acquire filesystem, network, process, environment or secret access.
4. **Deterministic semantics.** Evaluation order, arithmetic, traps, resource accounting and concurrency behaviour are specified independently of host-language accidents.
5. **One semantic authority.** CCAM remains the canonical typed core and abstract machine. Any optimisation IR is a derived representation with validation and a documented refinement relation; it must not invent a competing semantics.
6. **Proof and testing are complementary.** Formal proofs establish stated properties under stated assumptions; fuzzing, mutation, differential testing and independent review challenge the model, implementation and assumptions.
7. **Fail closed.** Invalid programs, malformed IR, invalid binaries, exceeded resource limits and failed security checks are rejected explicitly.
8. **Performance is measured.** Optimisations require reproducible baselines and correctness evidence. No optimisation may weaken a safety guarantee silently.
9. **Trust is reduced, never hidden.** Compiler stages, runtimes, assemblers, linkers, bootstraps, package tools and external dependencies are included in the TCB inventory until evidence justifies reducing it.
10. **Compatibility is deliberate.** Existing released behaviour is preserved unless a versioned language decision explicitly changes it. Migration must be staged and testable.
11. **The development process is itself secure.** Review, CI, dependency pinning, provenance, release signing and reproducible builds are part of the product's security architecture.
12. **Claims are falsifiable.** A claim without a test, proof, audit procedure or clearly stated limitation is not an established guarantee.

## 3. Target capability profile

These are destination criteria. They are not statements that current Capstan already satisfies them.

### 3.1 Language and type system

- Strong static typing with expressive algebraic data types, exhaustive pattern matching, generics and interfaces.
- Abstractions that preserve security-relevant properties, including taint, secrecy, capabilities, ownership and resource bounds.
- Explicit error handling and predictable control flow; no hidden exception paths that bypass resource or security invariants.
- A precise account of evaluation order, aliasing, mutation, lifetime, integer behaviour and failure.
- Diagnostics that explain both the violated rule and the concrete remediation, with stable identifiers for security-relevant weaknesses.
- A coherent escape-hatch policy. Any trusted operation is explicit, justified, reviewable and included in machine-readable audit output.

The language-semantics workstream owns normative definitions. This document does not prescribe new syntax or type rules.

### 3.2 Security and resource safety

The long-term target is compile-time prevention where practical, with runtime enforcement for properties that depend on dynamic inputs or operating-system behaviour.

Required areas include:

- memory safety, bounds safety, lifetime safety and type safety;
- explicit authority and capability confinement;
- taint-aware input validation and context-safe output;
- secret handling, minimised lifetime and best-effort erasure with honest platform limitations;
- safe cryptographic APIs with reviewed constructions, bounded work factors and published test vectors;
- resource budgets for memory, CPU, recursion, input sizes, I/O and concurrency;
- safe parsing and canonicalisation of untrusted data;
- safe process execution and FFI isolation;
- supply-chain provenance, dependency capabilities and vulnerability response.

For each CWE or weakness class, the project should state whether it is prevented at compile time, rejected by validation, contained at runtime, detected by testing, or remains outside the guarantee. Coverage percentages must be reproducible and must not conflate test counts with real-world vulnerability prevention.

### 3.3 Concurrency

The target is data-race freedom by construction for safe code, with explicit ownership transfer or synchronisation for shared mutable state.

The design must specify:

- task and cancellation lifetimes;
- channel and message ownership;
- lock ownership, lock ordering and deadlock policy;
- atomic memory-order semantics where atomics are exposed;
- bounded queues, backpressure and task/resource budgets;
- structured concurrency and deterministic cleanup;
- interactions between concurrency, capabilities and secret data.

Concurrency features must not be introduced before their ownership, memory-model and resource contracts are normative and testable.

### 3.4 Native execution and performance

The destination pipeline is:

```
Capstan source
  -> checked source representation
  -> canonical typed CCAM
  -> validated native lowering
  -> object code / executable
```

No C intermediate representation is part of the target architecture. During migration, the existing C backend may remain as a compatibility path and differential oracle, but it is not the semantic authority.

The native backend must document and test:

- target ABI, calling convention, stack alignment and register preservation;
- integer and boolean representation;
- control-flow lowering, relocations and symbol resolution;
- stack-frame and spill arithmetic with overflow checks;
- trap and process-exit behaviour;
- executable memory permissions and W^X policy;
- deterministic output where the toolchain and target permit it;
- source locations and useful debug information.

Performance acceptance must use fixed workloads, pinned toolchains, recorded host details, raw samples, warm-up, repeated measurements and separate compile-time/runtime measurements. Report medians, tails, variance, binary size, memory use and workload characteristics. Compare against relevant baselines—including the current C backend and carefully selected established systems languages—without cherry-picking. Any performance target is subordinate to correctness and security.

### 3.5 Formal assurance

Build a layered correctness argument:

1. the normative source semantics are precise;
2. the CCAM specification matches the intended source-language core;
3. the executable CCAM implementation conforms to the specification;
4. source lowering preserves the semantics;
5. each IR transformation preserves or refines the semantics;
6. native code generation preserves the CCAM observable behaviour;
7. the executable/runtime boundary satisfies its stated ABI and platform assumptions.

The Lean model is a proof artefact, not automatically the truth. Its correspondence to the normative specification and executable Capstan implementation must itself be established. Every proof report must identify assumptions, axioms, admitted results, unverified code and the TCB. CI must pin the Lean toolchain and dependency graph and build the exact commit being reviewed.

Differential tests must compare complete observable outcomes, including returned values, traps, output, step/resource accounting and relevant side effects. A test pass is evidence, not a proof.

### 3.6 Tooling and developer experience

Anchor and Shroud should make secure development the easiest path, not a specialist workflow. The target includes:

- precise compiler diagnostics and incremental editor feedback;
- debugger views for types, ownership, capabilities, taint and resource state;
- integrated tests, fuzzing, sanitizers, profiling and benchmark comparison;
- explainable security and trust reports;
- reproducible builds and useful dependency/provenance views;
- accessible, responsive GUI foundations and clear platform support commitments.

The GUI and IDE workstreams retain ownership of their implementation and API decisions.

### 3.7 Ecosystem and interoperability

A mature Capstan ecosystem should provide well-maintained libraries for networking, storage, structured data, cryptography, graphics, testing and application development.

Foreign code must cross a deliberately designed, typed and auditable boundary. In-process unchecked foreign execution must not become a loophole around the language's guarantees. Package dependencies should declare provenance, compatibility, capabilities and resource expectations.

## 4. Evidence gates

A capability is not considered complete because its API exists or its happy-path test passes. Each feature should carry an evidence record containing:

| Evidence | Minimum expectation |
|---|---|
| Specification | Normative behaviour, error cases, limits and compatibility |
| Invariants | Preconditions, postconditions and preserved properties |
| Positive tests | Representative valid use and boundary values |
| Negative tests | Malformed, hostile, invalid and resource-exhausting inputs |
| Fuzzing | Reproducible seeds, retained regressions and bounded execution |
| Mutation testing | Demonstration that tests detect deliberately weakened checks |
| Differential testing | Comparison with an independent semantic reference where applicable |
| Formal results | Machine-checked theorem, assumptions and exact source revision |
| Performance | Reproducible baseline, raw samples and resource profile |
| TCB impact | New trust dependencies and how they are constrained |
| Review | Independent review by someone other than the feature author |

Not every feature needs every evidence type. Any omission must be justified, not silently assumed.

## 5. Comparative excellence programme

Capstan should be evaluated against established languages and tools, not only against its previous release. Comparisons should include relevant strengths from Rust, Ada/SPARK, OCaml, Haskell, Swift, Zig and C/C++ toolchains.

Use representative tasks rather than synthetic language shoot-outs alone:

- implement a parser for hostile input;
- implement a memory-safe binary protocol;
- build a concurrent network service with bounded resources;
- implement a cryptographic wrapper using approved primitives;
- build a GUI application;
- write a compiler optimisation and validate its correctness;
- diagnose and fix deliberately seeded vulnerabilities;
- reproduce a release build from a clean environment.

Measure correctness, security findings, implementation effort, diagnostics quality, runtime and compile-time performance, binary size, memory use and maintenance burden. Publish methodology and limitations. Capstan should claim superiority only in dimensions where evidence supports it.

## 6. Self-hosting and bootstrap trust

The long-term goal remains Capstan all the way down: compiler, standard library and runtime written in Capstan and compiled to native code without generated C.

Self-hosting alone is not a correctness proof. A reproducible compiler fixpoint demonstrates consistency of the bootstrap process, not that the compiler implements the language correctly.

Reduce bootstrap trust in stages:

1. inventory every bootstrap stage and its trusted dependencies;
2. make builds reproducible and record provenance;
3. independently test and verify the source-to-CCAM and CCAM-to-native boundaries;
4. minimise and audit the initial bootstrap implementation;
5. cross-check independently produced compiler outputs;
6. progressively replace host-language bootstrap components with Capstan implementations;
7. retain a documented recovery path and independently verifiable release artefacts.

The operating system, hardware, linker, assembler and platform ABI remain part of the TCB unless and until separately addressed.

## 7. Adoption and governance

- `AGENTS.md` governs repository collaboration and branch/PR discipline.
- `docs/DESIGN-MAP.md` remains the current project design map and roadmap.
- The language-semantics owner controls normative source and typed-core semantics.
- CCAM remains the canonical machine contract; compiler work must refine to it rather than redefine it.
- Runtime, standard-library, Shroud, Anchor and security workstreams retain their assigned implementation boundaries.
- Cross-cutting interfaces are agreed before implementation; no workstream unilaterally changes another's contract.
- This proposal should be reviewed by the active workstream owners before any shared design-map amendment or roadmap reordering.
- Each accepted target should be translated into a named milestone, owner, dependency, tests and release gate.

## 8. Immediate priorities

The ambition does not justify destabilising v0.6 or parallelising overlapping changes. The near-term order should be:

1. close semantic disagreements and establish the normative language/CCAM contract;
2. make the Lean proof workflow reproducible and verify the exact proof revision;
3. complete the smallest executable CCAM evaluator and its structural validator;
4. establish the source-to-CCAM conformance boundary;
5. implement the smallest C-free native vertical slice with adversarial tests;
6. add reproducible performance baselines before optimisation;
7. reduce runtime and bootstrap trust as the native path matures;
8. integrate concurrency and higher-level language features only after their foundations are specified.

Existing v0.6 security, runtime, standard-library, Shroud and Anchor work continues under its current ownership and compatibility constraints. The North Star is a direction and acceptance framework, not permission to bypass those workstreams.

## 9. What success means

Capstan succeeds when an independent engineer can:

- understand exactly what the language guarantees and what it does not;
- build sophisticated systems without routinely escaping those guarantees;
- inspect evidence connecting source semantics to executable behaviour;
- reproduce the compiler and release artefacts;
- test the system adversarially and obtain actionable failures;
- achieve competitive native performance without disabling safety;
- trust the development environment to make secure choices visible and practical.

The ultimate measure is not the number of features, proofs or security checks. It is the amount of justified trust an independent user can place in a Capstan program and the toolchain that produced it.
