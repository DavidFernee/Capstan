# Capstan-only language and library foundation

> **Status:** proposed governing programme and acceptance contract
> **Revision:** 2026-11-26
> **Scope:** Capstan language, compiler, CCAM, runtime, standard library, modules, packages, build and assurance tooling
> **Research coordination:** `docs/research/PROGRAMMING-LANGUAGE-RESEARCH-AGENDA.md` and `docs/research/RESEARCH-REGISTER.md`
> **Related streams:** vulnerability prevention PR #238; standard-library v0.6 roadmap; construction-safety contract PR #326

This document establishes the language-and-library foundation programme. It is a design and research contract, not a claim that the guarantees described here are already implemented. The default branch, exact-head tests and independently checkable evidence determine implementation status.

## 1. Governing objective

Capstan is to become a Capstan-implemented programming system in which authority, information flow, resource consumption, object lifetime, concurrency, error handling and externally visible effects are explicit and checked compositionally.

The governing security objective is:

> No known vulnerability pattern within a declared Capstan execution profile may be accepted as an executable program or introduced through a compiler, runtime, standard-library, module, package, build or platform-adapter path. If the system cannot establish that a construct is safe under its declared threat model, it must reject it, require a separately verified boundary, or classify the result as unsupported. Unknown evidence is not a pass.

This is deliberately stronger than “secure by default”, warning-only lint, or a catalogue of safe APIs. The compiler and trusted execution boundary must enforce the contract. Application discipline is not an enforcement mechanism.

### 1.1 Necessary precision: what can and cannot be claimed

“No known vulnerability” is an operational acceptance rule, not a proof that unknown defects do not exist. The halting problem, incomplete requirements, incorrect specifications, hostile hardware/OS behaviour and defects in the trusted computing base prevent an honest universal claim that every possible program is vulnerability-free.

Accordingly:

- A known exploit pattern that is representable in a supported profile is a blocker until it is made unrepresentable, rejected, safely trapped before harmful effects, or confined behind an explicitly excluded and independently assured boundary.
- A weakness attributed to “business logic” or “programmer intent” is not automatically dismissed. Research must test whether contracts, refinement types, typestate, policy specifications, protocol/session types, proof obligations or verified components can prevent a useful and well-defined subset.
- Where intent cannot be inferred, the language must provide a way to state the relevant invariant and check it; the absence of a specification must not be reported as a security guarantee.
- Deliberately malicious or invalid programs may appear as source fixtures in negative tests and vulnerability corpora. They must not pass the supported compiler acceptance path or execute as successful artefacts.
- A vulnerability in an excluded host, OS, firmware, hardware, vendor library or human process must be named as a residual trust-boundary risk, never silently counted as prevented.

## 2. Capstan-only implementation policy

All new production implementation, executable tests, reference models, fuzzers, benchmarks, build orchestration, package tooling and assurance utilities are to be written in Capstan.

The research process may read and cite external literature, standards, advisories, CVEs, datasets and independent implementations. These are research evidence and comparison oracles, not implementation dependencies.

Migration rules:

1. No new production feature may add a C, C++, Rust, Python, shell, JavaScript or other-language implementation dependency.
2. Existing non-Capstan code is inventoried as migration debt. It is not deleted until a Capstan replacement has parity, security, reproducibility and platform evidence.
3. Temporary bootstrap tools and platform interfaces must be explicit in the trusted-computing-base register. “Capstan-only target implementation” must not be confused with “Capstan-only build and bootstrap”.
4. External OS interfaces are narrow, versioned adapters. Their input, output, ownership, authority, error, blocking and resource semantics are specified and validated.
5. External research code may generate comparison data, but checked-in fixtures and the acceptance runner must be executable and reproducible using the Capstan toolchain.
6. Every non-Capstan file added or retained must have a named owner, reason, migration/removal criterion and current status. No hidden language exceptions.

## 3. Construction-safety requirements

These requirements apply to the language and every ecosystem component, including code generators, compilers, package resolvers, build tools, IDE services and platform adapters.

### 3.1 Authority and effects

- No ambient filesystem, network, process, environment, clock, entropy, device or privileged service access in the safe profile.
- Authority is represented by opaque, scoped, attenuable capabilities and explicit effect contracts.
- Names such as paths, URLs, hostnames and process arguments are not authority.
- Capability acquisition is confined to an explicit application boundary; authority cannot be forged, widened, stored or delegated without a checked rule.
- External calls have explicit failure, cancellation, deadline and resource semantics.
- Safe APIs do not fall back to current directory, ambient proxy, implicit credentials, shell parsing or unbounded retries.

### 3.2 Memory, ownership and lifetime

- Safe code cannot express out-of-bounds access, use-after-free, double release, invalid aliasing, uninitialised reads or type-confused object access.
- Resource handles have checked ownership and lifecycle transitions; close, cancellation and failure paths are included.
- Aggregate allocation and work are budgeted, not merely individual buffers.
- Secret handling has explicit lifetime and copy semantics. Garbage-collection timing is not described as deterministic erasure.
- Foreign/platform resources cross only a narrow contract that validates identity, size, ownership and lifetime.

### 3.3 Types, information flow and output contexts

- Taint, secret, password/credential provenance, trusted text and context-encoded output remain distinct through aliases, containers, generics, calls, returns, closures, serialization and module boundaries.
- No generic “sanitize” or “trust” operation may erase provenance. Declassification is explicit, narrow, auditable and policy-checked.
- HTML, attributes, URLs, JavaScript, CSS, JSON, CSV, SQL, shell/process arguments, logs and terminal output are distinct contexts where their grammars and sinks differ.
- Escaped fragments are not complete serialized documents and cannot be silently reinterpreted as another context.
- The type checker must preserve security qualifiers after substitution, inference, monomorphisation, inlining and optimisation.
- Passwords, API tokens, keys and other credentials have distinct provenance/usage contracts where their security requirements differ.

### 3.4 Parsing, text and numeric semantics

- Byte strings, validated UTF-8, Unicode scalar sequences and grapheme sequences are different abstractions.
- Malformed encodings, ambiguous canonical forms, duplicate keys, invalid numeric forms and trailing data have explicit rejection rules.
- Parsing has limits for input bytes, nesting, tokens, decoded strings, aggregate storage, CPU work and output.
- Integer conversion, offsets, lengths, dimensions, time arithmetic and allocation calculations are checked before effects or allocation.
- Canonicalisation is explicit and context-specific; no silent replacement or normalisation of security-sensitive identifiers.

### 3.5 Concurrency and protocols

- Data races, use-after-close, double completion, stale callbacks, invalid state transitions and unbounded task creation are excluded or dynamically stopped under explicit contracts.
- Structured concurrency, cancellation propagation, bounded queues, deadlines and backpressure are language/runtime concepts, not ad hoc library conventions.
- Protocol APIs encode legal states and message order where practical; malformed peers are treated as hostile.
- A timeout is an absolute monotonic deadline with defined cancellation and cleanup behaviour, not a retry count or best-effort hint.

### 3.6 Compiler, optimiser, module and package integrity

- Every compiler stage preserves types, taint, authority, effects, ownership and resource contracts.
- Optimisations require proof, translation validation or a conservative no-optimise fallback for the relevant property.
- Module interfaces are versioned and checked; visibility, generic substitution, effect and capability requirements are validated across imports.
- Package resolution is deterministic and pinned. Package content, source identity, build inputs, generated artefacts and assurance evidence are cryptographically bound.
- No package hook or plugin executes during resolution or workspace inspection. Extensions require a separately specified isolation and capability boundary.
- Stale, missing, forged, incompatible or unverifiable evidence is a hard failure for profiles that require it.

## 4. Evidence and vulnerability-prevention protocol

The existing CWE atlas and CVE benchmark are retained and expanded. Their counts are research inventory metrics, not percentages of vulnerabilities prevented.

Every weakness attempt must record:

1. Stable identifier, weakness/root cause, primary source and version/date.
2. Attacker capabilities, trust boundary, preconditions, target effect and security impact.
3. Minimal Capstan source reproducer or negative compile fixture.
4. Supported profile and exact compiler/runtime revision.
5. Expected and observed result, including diagnostic/trap, side effects and resource use.
6. A positive control proving that the legitimate operation remains expressible.
7. Classification: unrepresentable, compile-time rejected, runtime prevented before effect, neutralised, excluded by explicit boundary, possible, or unknown.
8. Independent review of mapping and semantic fidelity.
9. Regression test, evidence provenance and any residual limitation.

Rules:

- One successful negative test does not establish class-wide prevention.
- A CWE label is not a faithful CVE reproduction. CVE studies must model the actual root cause and disclose semantic differences.
- Every compiler rejection and runtime stop must be tested at exact boundaries and through aliases, wrappers, generics, containers, modules and optimisation.
- Fuzzing, mutation testing, differential testing, adversarial corpora and resource-exhaustion tests are mandatory where applicable.
- Formal proofs must state their model, assumptions, axioms, trusted checker, exact revision and implementation-refinement status.
- A proof about a model is not a proof about compiler/runtime code until the correspondence is established.
- Every newly discovered bypass becomes a regression test and a blocker for affected profiles until disposition.
- No vulnerability is marked closed solely because a scanner is clean, a dependency has no assigned CVE, or an advisory is absent.

### 4.1 Release-blocking security status

Each feature and profile has one of four statuses:

- **Blocked:** known exploitable path, failed invariant, unresolved high-impact finding, or missing mandatory validation.
- **Unknown:** evidence is missing, stale, irreproducible, contradictory or not independently interpretable.
- **Qualified:** the exact stated property has passed its declared tests/proofs and residual assumptions are explicit.
- **Accepted:** all profile-specific gates pass, independent review is recorded, and no known in-scope vulnerability remains open.

Only **Accepted** features may be presented as part of a supported security profile. Unknown is never green. Risk acceptance cannot relabel a known in-scope vulnerability as prevented; any exception must be a clearly named excluded profile with a disclosed residual risk.

## 5. Research programme: questions before features

The following are active research questions, not a mandate to adopt fashionable language features. Each work package must review prior art, state a falsifiable hypothesis, define a minimal formal model, build a Capstan prototype, produce adversarial counterexamples and compare against serious baselines.

| Workstream | Research question | First deliverable |
|---|---|---|
| L1 Semantics and core language | What is the smallest compositional semantics that can express authority, effects, resource use and failure? | Versioned normative core and executable conformance vectors |
| L2 Type system and contracts | How do ownership, lifetimes, refinements, effects, taint, secrets, typestate and generics compose soundly? | Formal typing rules, negative compiler corpus and metatheory |
| L3 Resource semantics | Can time, memory, stack, allocation, output, tasks and I/O be bounded compositionally? | Shared budget algebra, admission semantics and implementation correspondence |
| L4 Runtime and memory | Which runtime services can be implemented in Capstan without inheriting unsafe lifetime or allocator assumptions? | Capstan-native bounded allocation/ownership vertical slice |
| L5 Standard library | What minimal APIs cover text, collections, filesystem, networking, serialization, time, crypto and processes without ambient authority? | Capability-first API specifications and one vertical slice per domain |
| L6 Modules and packages | How can independently versioned libraries compose types, effects, capabilities and evidence reproducibly? | Module interface and package-lock/provenance specification |
| L7 Concurrency and protocols | Which useful concurrency models make races and lifecycle misuse unrepresentable? | Bounded structured-task/session-type model |
| L8 Compiler and optimisation | How can every transformation preserve security and resource semantics? | Translation-validation prototype for one real optimisation |
| L9 Evidence-carrying artefacts | What small independent checker can validate program, package and build claims? | Versioned evidence envelope and independent Capstan checker |
| L10 Bootstrap and C-free execution | What stage chain removes C and other languages from the production build/run path without circular trust? | Reproducible Capstan-native stage with explicit seed/TCB ledger |
| L11 Vulnerability prevention | Which known root causes can be made unrepresentable, and where do current guarantees fail? | Expanded CWE/CVE corpus with independently reviewed mappings |
| L12 Usability and diagnostics | How can rejection explain the failed invariant and guide safe repair without weakening the rule? | Actionable diagnostics and measured repair study |

Research must cover state of the art: mechanised metatheory, refinement/linear/affine/effect systems, capability security, information-flow control, resource-aware type systems, verified compilation, translation validation, proof-carrying code, memory-safe runtimes, protocol/session types, reproducible builds and supply-chain attestations. Prefer combinations supported by evidence over novelty for its own sake.

## 6. Delivery sequence and gates

### Gate F0 — baseline truth

- Pin the exact default-branch commit and inventory language, compiler, runtime, standard library, tests, build tools and all non-Capstan files.
- Reconcile every research branch/PR and distinguish merged, open, stale, superseded and unverified work.
- Reproduce the current CWE atlas and CVE benchmark at exact head.
- Publish the current trusted-computing-base and known-vulnerability register.
- No implementation claim without reproducible evidence.

### Gate F1 — normative language contract

- Freeze source semantics, type rules, error/trap order, authority/effect model and resource semantics.
- Define the security profile and excluded host/platform assumptions.
- Specify type-system soundness and compiler acceptance/rejection obligations.
- Establish a language-versioned conformance suite before feature expansion.

### Gate F2 — safe runtime and standard-library core

- Define capability-first filesystem, byte/text, bounded parsing, Result/error, clock/deadline, entropy and resource APIs.
- Resolve ownership/lifetime and deterministic cleanup contracts before exposing handles.
- Integrate cryptography only through reviewed, versioned algorithms/providers and misuse-resistant APIs; no new home-grown primitive.
- Close known gaps in the CWE atlas that are within the language's declared scope.

### Gate F3 — module and package foundation

- Add separately checked module interfaces, visibility and dependency graph validation.
- Add reproducible lockfiles, content-addressed packages, signed provenance and evidence binding.
- Ensure package acquisition/build is bounded, deterministic and non-executing until explicit user action.
- Require the same security and resource contracts across package boundaries.

### Gate F4 — C-free Capstan implementation chain

- Port compiler, runtime, standard library, tests, fuzzers, benchmarks and build/release orchestration to Capstan.
- Preserve external seed compilers only as disclosed comparison/bootstrap evidence, not final dependencies.
- Prove or validate each lowering/backend boundary; test generated executables on each claimed target.
- Retire C and other implementation languages only after parity and trust-base gates pass.

### Gate F5 — independently assessed security profile

- Complete adversarial source, IR, module, package and runtime testing.
- Close all known in-scope findings or remove the affected feature/profile from support.
- Obtain independent review and reproducible evidence replay.
- Publish precise residual assumptions and non-claims.

## 7. Initial priority order

1. Reconcile PR #238 and the CWE/CVE research corpus against current main; verify every stated count and exact-head status.
2. Make the six current CWE atlas gaps explicit blockers for the affected safe profile; research type-level and contract-level closure, including cross-statement context and credential provenance.
3. Reconcile the v0.5 type-system proposal, construction-safety contract and v0.6 stdlib roadmap into one normative dependency graph. Do not implement APIs that depend on unmerged semantics.
4. Define a minimal effect/capability/resource/ownership model before expanding filesystem, networking, process or concurrency APIs.
5. Start with a small Capstan-native vertical slice and executable negative tests; add no convenience surface before its enforcement model exists.
6. Reconcile the current C/Python/shell/Lean inventory and define the Capstan-native test/proof/build path, including the explicit status of the current Lean-based research tools.

## 8. Change control

Every feature proposal must include: threat model, research prior art, normative semantics, known attack patterns, capability/effect/resource contract, positive and negative tests, proof obligations, implementation/TCB boundary, migration plan and explicit non-claims.

Changes to language semantics, security types, declassification, authority, resource accounting, module interfaces or proof formats require cross-workstream review. No subsystem may invent a parallel type, error, capability or assurance convention.

A change is not ready to merge merely because its tests pass. It must pass the exact-head required checks, satisfy the affected proof/evidence obligations, preserve all existing guarantees and add regression coverage for every discovered defect.
