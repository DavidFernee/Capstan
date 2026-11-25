# F1 — Capstan language contract (research draft)

> **Status:** F1 research draft; not yet normative and not an implementation claim  
> **Revision:** 2026-11-26  
> **Compatibility baseline:** `docs/SPEC.md` (v0.1 reference), current compiler and CCAM work  
> **Programme:** [Capstan-only foundation](CAPSTAN-ONLY-FOUNDATION.md)  
> **Research coordination:** [Programming-language research agenda](research/PROGRAMMING-LANGUAGE-RESEARCH-AGENDA.md), [research register](research/RESEARCH-REGISTER.md)

Related-work synthesis: [F1-RELATED-WORK.md](F1-RELATED-WORK.md). The related-work review recommends a factored but mutually checked guarantee derivation as the primary experiment; this remains a hypothesis, not an adopted design.

This document starts the F1 normative-language-contract work. It separates (A) semantics already stated by the current language reference, (B) requirements of the proposed safe execution profile, and (C) unresolved research decisions. It must not be read as silently adding syntax, changing compiler behaviour, or upgrading assurance claims.

A section becomes normative only after: (1) a precise definition is reviewed; (2) it is reconciled with the source reference and CCAM; (3) executable conformance vectors exist; (4) negative and positive adversarial tests pass; and (5) the implementation correspondence and residual trust assumptions are recorded.

## 1. Scope and design criterion

The contract covers source parsing and typing, evaluation, authority and effects, information flow, resource use, memory and object lifetime, failure, concurrency, modules, compiler transformations and observable behaviour.

The primary design criterion is **compositional preservation**:

> If a source component satisfies a stated contract, and it is composed only with components satisfying compatible contracts, then the composed component must retain the stated safety, authority, information-flow and resource properties—or compilation/admission must reject the composition.

A property is not compositional merely because a checker enforces it within one function. The contract must say how it behaves through calls, aliases, containers, recursion, modules, packages, lowering, optimisation and runtime boundaries.

The target is not maximal static rejection. It is the smallest coherent set of rules that makes useful guarantees enforceable and independently testable. Where a static proof is unavailable, the system must use a specified bounded runtime check or reject the operation. It must not silently assume safety.

## 2. Normative vocabulary and profiles

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** and **MAY** are reserved for provisions approved as normative. In this research draft they identify proposed requirements, not current implementation facts.

A language version identifies source semantics. An execution profile identifies additional restrictions and guarantees for a deployment target. A compiler mode such as `--strict` or `--release` is not itself a distinct semantic profile unless its exact accepted-program predicate is specified and versioned.

Proposed profile hierarchy:

- **Core:** deterministic source semantics and type rules; no implied operating-system authority or guarantee beyond the specification.
- **Safe:** rejects unsafe/ambient operations; requires explicit authority and bounded resource contracts; no unchecked escape hatch.
- **Verified:** Safe plus machine-checkable evidence for named properties and a stated implementation-refinement chain.
- **Platform adapter:** a separately specified boundary for OS, hardware, device or external service operations. Adapter assumptions and authority are visible in the importing program's contract.

A program's profile must be selected explicitly or by a documented fail-closed default. A weaker profile must never be silently substituted when a stronger one cannot be satisfied. Evidence is bound to language version, profile, target, dependency graph, compiler/validator revision and policy.

## 3. Existing source semantics to preserve or explicitly revise

The following are described in `docs/SPEC.md`; this is a documentary baseline, not an independent re-audit of every implementation path.

### 3.1 Lexical and parsing rules

- Identifiers are ASCII-shaped; bidi controls, selected zero-width controls and misplaced BOM are rejected.
- Strings are byte sequences with explicit escapes; character literals denote byte values.
- Required statement braces, definite initialisation, complete struct-field initialisation, no shadowing of enclosing names and complete non-void returns are specified.
- Expression evaluation is strictly left-to-right, including function arguments.
- Bitwise operators require explicit grouping when mixed with other operators.

F1 decision: preserve existing lexical and evaluation behaviour unless a versioned language change is approved. Parser limits and malformed-source behaviour must be specified as bounded semantics, not merely implementation constants.

### 3.2 Types and values

The current reference defines signed 64-bit `int`, `bool`, immutable byte `string`, `Tainted`, `Secret`, `Html`, `LogText`, nominal structs, `List<T>`, `Map<T>`, `Grant<P>`, `T?` and `void` return types. There is no null; optional nesting and optional collection elements are disallowed.

Current built-in type constructors do **not** imply user-defined generic declarations, type variables, inference, interfaces, traits or a general constraint solver. The current type-system assurance document explicitly records those absences.

F1 decision: do not enable generic declarations, inference, variance, interfaces, closures, subtyping or user-defined recursive type constructors as incidental extensions. Each requires a separate formal typing rule set and security-preservation matrix.

### 3.3 Arithmetic and traps

Ordinary signed-64 arithmetic is checked; division truncates toward zero; division by zero and unrepresentable results stop execution. Bit shifts have specified bounds and checked left-shift behaviour. Explicit wrapping arithmetic is available for specified bit-level algorithms.

F1 requirement: all integer operations, conversions, indices, lengths, offsets, allocation-size calculations, time arithmetic and resource counters have mathematical semantics independent of host-language undefined behaviour. The exact trap reason, evaluation order, side-effect ordering and boundary cases must be part of conformance vectors.

### 3.4 Existing authority and policy semantics

Policies return booleans; `authorize` yields an optional `Grant<P>`; protected calls require a matching grant and re-evaluate policy on the authorised arguments. Grants are not ordinary storable/returnable values.

The current system still grants programs ambient process authority for filesystem and environment access. The threat model explicitly identifies this as a residual risk. The safe profile proposed here cannot inherit that ambient model.

### 3.5 Text and serialization

The current `string` and `Tainted` abstractions are byte-oriented, not Unicode-native text. `escape_json` returns a JSON string-content fragment as `string`; `escape_csv` also returns `string`; the reference records actual cross-format misuse as a CWE gap. `Html` alone does not encode every HTML subcontext or a multi-statement template state.

F1 requirement: byte strings, validated UTF-8, Unicode scalar strings, grapheme segmentation and context-encoded serialized values must be distinct concepts. Output-context values must be sink-specific and non-interchangeable. A serialized fragment must not be assignable to a complete document or to another output grammar.

## 4. Proposed semantic judgement

The research target is a single judgement that makes the relevant guarantees explicit. Notation below is a design scaffold, not adopted syntax:

`Γ ; Ω ; Κ ; Β ⊢ e : τ ! ε ▷ ρ`

where:

- `Γ` is the typing environment, including nominal declarations and security provenance;
- `Ω` is the ownership/lifetime environment;
- `Κ` is the authority/capability environment;
- `Β` is the available resource budget and its accounting state;
- `e` is an expression or computation;
- `τ` is its value type, including security and context qualifiers;
- `ε` is its effect set/row (mutation, I/O, clock, entropy, process, network, etc.);
- `ρ` is its resource contract (upper bounds or explicitly unknown dimensions).

Research must determine whether one judgement is adequate or whether a small family of mutually related judgements is more sound and tractable. The design must avoid encoding unrelated properties in a single opaque type tag.

### 4.1 Composition rules

For every construct, define:

1. Preconditions and typing premises.
2. Result type and preserved qualifiers.
3. Authority required and authority consumed/returned.
4. Effects that may occur and their order.
5. Resource costs and budget transfer.
6. Possible normal results, typed errors and traps.
7. State mutations and externally visible effects before failure.
8. Proof obligations for the compiler/runtime boundary.

Unknown effects or resource bounds must not be treated as empty effects or zero cost. Composition must be conservative: unknown plus known is unknown unless a sound analysis discharges the unknown component.

## 5. Authority and effect system

### 5.1 Target property

The Safe profile has no ambient filesystem, network, process, environment, clock, entropy, device or privileged-service authority. An operation is permitted only when its required authority is present in the calling context and represented in the program's declared effect/capability contract.

A path, URL, hostname, process name, environment variable name or file descriptor is a *designation*, not authority.

### 5.2 Required research

Compare capability-passing, object-capability, effect-row, effect-handler and region-scoped designs. Select the smallest model that can enforce:

- least authority and attenuation;
- non-forgeable capability construction;
- explicit delegation and revocation semantics, if supported;
- authority non-escape from a lexical/dynamic scope;
- no authority widening through generic substitution, aliases, closures or package boundaries;
- call-graph and module-level effect summaries;
- explicit blocking, cancellation, deadline and failure behaviour for external effects.

A capability must identify the resource class and permitted operation set. Resource identity, lifetime, delegation and revocation must be specified separately; do not assume a single opaque `Grant<P>` solves filesystem/network authority.

### 5.3 Fail-closed rule

If an operation's required authority cannot be statically established, it is rejected in Safe profile. A runtime capability check is acceptable only where its semantics are specified, bounded, non-forgeable and checked before the protected effect. No fallback to ambient authority is permitted.

## 6. Ownership, lifetime and memory

The current runtime uses garbage collection. The language reference's statement that secrets are zeroed when collected is not a deterministic destruction guarantee; collection time is nondeterministic, and the current runtime is C-backed.

F1 must distinguish:

- memory safety of ordinary references;
- logical object lifetime;
- deterministic resource release;
- secret erasure and copies;
- external resource handles;
- allocation and aggregate memory budgets.

Proposed Safe-profile requirements:

- No source-level operation can forge an object reference, perform unchecked pointer arithmetic, access out of bounds, read uninitialised storage, or use an object after its language lifetime.
- External resources use explicit lifecycle states and cannot be duplicated, released twice or used after close.
- Secret values have defined copy, alias, serialization and destruction rules. A GC finalizer alone is not proof of erasure.
- Allocation admission accounts for aggregate live/reserved capacity and integer overflow before mutating allocator state.
- Resource acquisition is failure-atomic: failed admission does not leak authority, capacity or partially initialised externally visible state.

Research must compare ownership/borrowing, affine/linear values, regions, arenas and verified GC. It must not select one based on familiarity; evaluate the impact on recursive data, FFI/platform adapters, concurrency and Capstan-native compiler implementation.

## 7. Information flow and output contexts

Security-relevant provenance is a semantic property, not a naming convention. It must survive assignments, control flow, helper calls, method calls, generic substitution, aggregates, collection lookup, module interfaces, serialization, inlining and optimisation.

Minimum distinctions to investigate and preserve:

- untrusted bytes and validated values;
- secrets, passwords and cryptographic keys;
- trusted text;
- UTF-8 validated text;
- HTML element text, HTML attribute values, URL components, CSS/JS contexts where supported;
- JSON string content, JSON values and complete JSON documents;
- CSV field and complete CSV document;
- SQL parameters and query structure;
- log/terminal-safe text and structured log fields.

No generic `sanitize`, `trust` or cast may erase provenance. Declassification must be explicit, policy-constrained, narrowly typed and auditable. The current `trust()` escape hatch is incompatible with the proposed Safe profile unless a revised formal rule and evidence establish a safe, bounded use.

Research questions: which labels form a lattice, which contexts are nominal non-coercible types, and how should context state compose across templates and multiple statements? Do not assume all these dimensions can be represented by a single taint bit.

## 8. Resource semantics

A per-buffer limit is not a process-wide bound. A local recursion limit is not a total CPU bound. F1 therefore treats resource accounting as a semantic contract.

At minimum, investigate compositional accounting for:

- fuel/instruction steps and wall-clock deadlines;
- stack depth and call frames;
- live memory, reserved capacity and allocation count;
- input bytes, decoded bytes, parser nodes and nesting;
- output bytes and amplification;
- open handles, file descriptors and pending I/O;
- tasks, queue capacity and concurrency;
- cryptographic work factors and intermediate state.

Each resource dimension needs units, scope, admission point, charging rule, failure behaviour, overflow semantics and a rule for composition across calls. Static bounds, dynamic budgets and unknown bounds must remain distinguishable. A budget check must happen before the corresponding irreversible effect or allocation.

Research should begin with a vector budget model and test whether it composes soundly through sequential composition, branches, loops, recursion, calls and external services. Avoid claiming a single scalar "cost" if dimensions cannot be soundly combined.

## 9. Failure, errors and atomicity

The existing language uses optional values for some expected absence and runtime traps for checked failures. A general typed error/result contract is not yet part of the established core reference.

F1 must decide the boundary between:

- expected domain errors represented as values;
- capability denial;
- resource exhaustion;
- cancellation/deadline;
- I/O and platform failure;
- programmer invariant violations;
- compiler/runtime integrity failures.

The semantics must specify whether each failure is recoverable, whether it consumes budget, whether it may occur after partial mutation, and what cleanup is guaranteed. Error propagation must not silently discard security-relevant failures. `Result<T,E>` is a candidate, not an assumed existing feature.

For each operation, state its atomicity class: no effect before success, prefix effects possible, or externally atomic by contract. A function must not claim failure-atomic behaviour if an external platform cannot provide it.

## 10. Concurrency and protocol semantics

The current language has no threads; data races are absent from the current source model, not solved by a concurrency type system.

Any future concurrency design must start with structured task lifetimes, cancellation propagation, bounded task creation, queue/backpressure semantics, data ownership or synchronisation, and protocol/session state. Detached tasks, unbounded spawn, implicit shared mutation and unbounded retries are not admitted in Safe profile.

The research programme must compare actor/message-passing, ownership-based sharing, session types and effect-based concurrency. No concurrency syntax is committed by this document.

## 11. Modules, packages and separate compilation

Current imports load files into a shared declaration set; this is not a stable separately compiled module interface.

The target module contract must bind:

- exported nominal type identities and visibility;
- generic/interface constraints, if later adopted;
- effect and capability requirements;
- resource contracts;
- information-flow and declassification rules;
- ABI/representation and semantic version;
- dependency identities and hashes;
- evidence and target/profile compatibility.

Import order and file traversal order must not change name resolution, type checking, authority or resource outcomes. Package resolution must be deterministic and must not execute package code. A package must not gain capabilities merely by being imported.

## 12. Compiler and execution refinement obligations

The compiler pipeline must preserve the approved source contract at every transformation. The following obligations are mandatory research targets:

1. **Lexing/parsing:** total, bounded rejection of malformed or adversarial source; no parser crash, hang or unbounded allocation within declared input budgets.
2. **Name/type/effect checking:** accepted source satisfies the formal typing and effect rules; rejected source cannot reach code generation.
3. **Lowering:** source evaluation order, checked arithmetic, traps, authority, provenance, ownership and resource charges are preserved.
4. **Canonical IR validation:** validation is total, bounded and rejects malformed, oversized, ambiguous or non-canonical encodings before execution.
5. **Evaluation/runtime:** concrete execution refines the canonical semantics, including exact budget boundaries, cleanup and failure atomicity.
6. **Optimisation:** every transformation preserves observable values, traps, effects, authority, provenance and resource guarantees; otherwise use a conservative fallback.
7. **Native backend:** generated code preserves the validated IR semantics and cannot bypass runtime checks or capability gates.
8. **Build/package:** artefacts and evidence are bound to exact source, compiler, dependencies, target and profile.

A proof about a Lean model, CCAM fragment or reference implementation is not a proof of the concrete compiler/runtime until a correspondence theorem or independently checked translation-validation argument connects them.

## 13. Conformance and adversarial evidence

Each normative rule must have:

- a stable rule identifier;
- a short positive program demonstrating legitimate use;
- a minimal negative program demonstrating rejection or safe stopping;
- adversarial variants through aliases, wrappers, nested containers, calls, imports and optimisation as applicable;
- exact expected diagnostic/trap/effect/resource behaviour;
- boundary cases immediately below, at and above limits;
- an independent or differently implemented oracle where feasible;
- exact language version, compiler revision, target and profile.

Conformance vectors must be machine-readable and executable by the Capstan-native test runner. Research tools written in other languages may help discover cases, but are not accepted as the final oracle or required execution dependency.

A test corpus is not a proof. Formal claims require a named theorem, assumptions, checker, exact revision and a documented refinement relation to the implementation.

## 14. Open decisions — F1 cannot close these by assertion

| ID | Decision | Required investigation | Blocking dependent work |
|---|---|---|---|
| F1-D01 | One combined judgement vs separate typing/effect/ownership/resource judgements | Formalise both; compare soundness, modularity, inference and implementation complexity | Generic/effect/ownership expansion |
| F1-D02 | Capability passing vs effect rows/handlers vs hybrid | Model attenuation, delegation, revocation, host adapters and least authority | Filesystem, network, process, device APIs |
| F1-D03 | Ownership/borrowing vs affine handles + GC vs region model | Prove lifecycle properties; test recursive structures, cycles, FFI and secrets | Resource handles, foreign memory, concurrency |
| F1-D04 | Information-flow lattice and context-specific nominal types | Model control/data flow, declassification and multi-statement output contexts | JSON/HTML/CSV/SQL/log sinks and generic abstractions |
| F1-D05 | Resource budget algebra | Prove sound composition for loops, recursion, branches, calls and external operations | Networking, parsing, crypto, GUI/export, concurrency |
| F1-D06 | Typed errors vs traps and effectful failure | Define atomicity, cleanup, cancellation and observable failure order | Result/error standard library and I/O |
| F1-D07 | Byte/text/Unicode type hierarchy | Specify malformed encoding, canonicalisation, segmentation and normalization policy | Unicode library and security-sensitive text APIs |
| F1-D08 | Source-to-CCAM semantic correspondence | Freeze normative CCAM schema and prove/test translation obligations | Verified profile, native backend |
| F1-D09 | Module ABI and evidence binding | Specify nominal identity, versioning, package graph and deterministic linking | Extended libraries and package manager |
| F1-D10 | Safe-profile treatment of escape hatches | Inventory `trust`, platform adapters and any unsafe primitive; formalise a quarantine boundary | Safe-profile claim and ecosystem packages |


## 14.1 Known CWE gaps that block the Safe-profile claim

The current research atlas records six distinct weakness classes that remain expressible (with three separate CWE-916 attack variants). They are explicit F1 closure targets, not accepted residual risks for a Safe-profile release:

| CWE | Current gap | F1 property required |
|---|---|---|
| CWE-116 | Context-escaped output can be sent to a different format sink (HTML-escaped text into CSV). | Sink-specific nominal serialization types and typed complete-document writers; no cross-context coercion. |
| CWE-798 | A hard-coded password-like literal can be hidden under an innocuous identifier. | Credential provenance and policy for embedded credentials; name/format heuristics are supplemental only. |
| CWE-916 | Password provenance can be hidden by an innocuous variable, method call or helper call before fast hashing. | Password-specific provenance preserved through all value transformations; ordinary integrity hashes cannot accept password provenance. |
| CWE-862 | Sensitive data may be left undeclared and therefore unprotected. | An enforceable declaration/completeness model or a narrower profile that rejects unclassified data access at the relevant boundary. |
| CWE-306 | A critical operation may be left undeclared as protected. | Explicit operation classification/completeness contract, with a fail-closed policy for the Safe profile. |
| CWE-79 | HTML context assembled across statements is not fully tracked. | Stateful structured-template/context semantics that preserve context across locals, helpers and composition. |

The atlas is a project attack corpus, not an official MITRE mapping. Its headline counts are not prevention percentages. Each gap closes only after the actual negative fixture is rejected or neutralised, a positive control passes, bypass variants are tested, the implementation and specification agree, and exact-head CI plus independent review provide evidence. These rules do not imply that all six can be solved by a type system alone; the research must compare static typing, explicit contracts, verified sinks, runtime enforcement and deployment policy.

## 15. F1 acceptance gate

F1 is complete only when all of the following are true:

- [ ] A precise threat model and execution-profile definition are approved.
- [ ] The source-language semantics and CCAM semantics are versioned and reconciled.
- [ ] The core typing rules cover all existing constructs and explicitly classify every proposed extension as absent, experimental or normative.
- [ ] Authority/effect, ownership/lifetime, information-flow and resource judgements have a formal model and sound composition rules for the accepted subset.
- [ ] Failure, trap, cancellation and atomicity semantics are precise.
- [ ] Each rule has executable positive/negative conformance vectors.
- [ ] A formal proof plan identifies theorem statements and implementation correspondence obligations; model-only results are labelled as such.
- [ ] Existing CWE gaps and known residual vulnerabilities are linked to concrete blocking rules or explicitly excluded profiles.
- [ ] Independent review has challenged the model and adversarial corpus.
- [ ] No downstream subsystem has implemented an API that assumes an unresolved F1 decision.

Until then, F1 status is **in progress**. No feature may claim the Safe or Verified profile merely by conforming to this draft.
