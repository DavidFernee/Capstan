# Evidence-Carrying Execution for Capstan

**Status:** research architecture proposal; not an implementation or proof claim  
**Date:** 2026-11-25

## 1. Research proposition

Capstan should make its security and resource guarantees explicit, machine-checkable properties of an executable artefact, rather than informal promises attached to a compiler or runtime.

> Can a practical systems language produce executable artefacts accompanied by independently checkable evidence that the artefact conforms to a specified execution semantics, uses no authority beyond an explicit capability grant, and remains within declared resource bounds?

The proposed contribution is an integrated **evidence-carrying execution architecture (ECE)**. It is not three unrelated features. A single assurance object binds:

1. Semantics: the versioned language/CCAM contract.
2. Code identity: the exact canonical CCAM payload or executable.
3. Safety evidence: validation and typing facts required for execution.
4. Authority evidence: capabilities available to the program and provenance/attenuation of grants.
5. Resource evidence: static bounds where derivable and mandatory runtime ceilings for residual dynamic behaviour.
6. Provenance: compiler, validator, proof checker, toolchain and build inputs, including the residual trusted computing base.

The initial target is deliberately narrower than all Capstan source programs: a closed, deterministic CCAM subset. Unsupported constructs fail closed. This proposal does not imply that current Capstan execution is already evidence-carrying.

## 2. Existing foundation and boundary

The repository already contains useful components:

- CCAM specifies typed scalar registers, deterministic instruction order, checked arithmetic, traps, call depth and instruction fuel.
- A Capstan-native in-memory single-frame validator exists, but does not implement the complete JSON decoder/function-table contract.
- Lean contains finite typed-machine and validator models, plus conditional runtime-register representation lemmas.
- The bounded multi-function evaluator is integrated on `main` (PR #207), and checked scalar source-to-CCAM lowering is integrated (PR #210). The freestanding Linux x86-64 backend is integrated (PR #212). These are real executable increments, but remain deliberately narrow: the evaluator uses transitional instruction-index/callee-index side tables rather than the normative named-call JSON representation; the current Lean machine/progress model remains single-frame; no multi-frame evaluator-refinement theorem connects the concrete evaluator to that model; and the native backend does not yet establish a complete source-to-platform correctness chain.
- Capstan has policy/grant design and runtime enforcement work, but these are not yet a capability-typed CCAM execution contract.

The current default compiler path remains C-generating and C-runtime-dependent. Existing Lean theorems concern named formal models and fragments. No claim here upgrades those facts to implementation refinement, full compiler correctness or verified execution.

## 3. Architecture

### 3.1 Artefact and evidence bundle

Define a conceptual bundle with these fields:

- format_version and semantics_id;
- program_digest;
- validation_certificate;
- resource_contract;
- capability_manifest and capability_evidence;
- compiler_provenance and checker_identity.

This is not yet a wire format. A concrete encoding must be canonical, length-bounded, duplicate-key rejecting, integer-exact and versioned. Digests must be domain-separated and cover the exact canonical bytes they identify. The bundle is not trusted because the compiler emitted it or because it is signed: the verifier independently checks evidence against the program digest and pinned semantics.

A certificate must not be reusable for a different program, semantics version, capability manifest or resource contract. Any semantics-changing transformation invalidates the certificate unless a separately checked transformation/refinement certificate bridges it.

### 3.2 Proof-carrying validation

Separate validation into two components:

- **Producer:** compiler/validator constructs a certificate, potentially using sophisticated algorithms.
- **Checker:** a small deterministic checker verifies the certificate against the canonical program and normative predicates.

The checker, not the producer, is the authority for acceptance. It rejects malformed or incomplete evidence before execution. Initially, a certificate can be a compact derivation of structural facts rather than a general theorem-prover proof term.

Required validation facts include:

- closed schema and exact scalar encodings;
- function table, entry point and signature consistency;
- finite register and instruction indices;
- static operand and return types;
- valid call arity and argument/result types;
- control-flow successor and no-reachable-fall-through;
- aggregate admission bounds and bounded validation work;
- explicit effect/capability requirements;
- resource-contract consistency.

The certificate must bind to the exact accepted-program predicate. A theorem that a decoded instruction is typed does not prove that the raw decoder rejects duplicate keys, bounds aggregate allocation, or validates every function. These are separate predicates and proof obligations.

### 3.3 Proof-to-execution correspondence

The assurance argument is a chain, not one monolithic theorem:

    source
      -> checker/lowering simulation
      -> canonical CCAM
      -> certificate-checker soundness
      -> validated CCAM
      -> evaluator simulation/refinement
      -> reference CCAM semantics
      -> backend refinement
      -> target executable
      -> runtime/host contract
      -> observable platform behaviour

For the first research increment, stop at validated CCAM evaluation. Prove properties over a small-step reference machine and establish a relation between that machine and the concrete Capstan evaluator. Keep source lowering and native code generation as later links. Tests, differential execution and model-only theorems are not substitutes for refinement proofs.

The central safety theorem should state that if certificate checking accepts a program, then every reachable evaluator state is well formed; register reads are typed and initialised; transitions preserve machine invariants; observable effects stay within granted authority; and resource counters remain within configured ceilings. Exact predicates and quantification must be fixed in Lean. This is an objective, not an established theorem.

### 3.4 Resource contracts

Use one resource vocabulary across static analysis, evaluator, backend and evidence.

| Resource | Contract | Enforcement |
|---|---|---|
| Instruction fuel | Maximum abstract-machine transitions | Mandatory shared counter; calls and returns consume specified fuel |
| Call depth / stack | Maximum live frames and derived frame bytes | Preflight before push; bounded native stack |
| Heap bytes | Maximum live or cumulative allocated bytes; distinguish them | Checked allocator accounting before allocation |
| Allocation count | Maximum allocation events | Checked counter before allocation |
| Output / I/O | Maximum emitted bytes and operation count | Bounded adapter, including partial writes |
| Validation | Maximum raw bytes, nodes, functions, instructions and work | Admission before aggregate allocation; bounded decoder |
| Wall-clock | Optional operational deadline, not deterministic fuel | Host supervisor; report separately |

Never call a resource bounded without naming its metric, accounting point, scope (per call, process or request), overflow behaviour and failure outcome. Cumulative allocation is not a live-heap ceiling; instruction fuel is not a wall-clock guarantee; call depth alone is not a byte-accurate stack bound.

Contracts should be monotonic: a callee cannot silently increase its caller's budget. A call receives a bounded sub-budget or consumes from a shared budget, according to a specified resource algebra. The first CCAM implementation should prefer shared deterministic fuel and depth counters. Heap and I/O budgets should follow only when their accounting boundaries are explicit.

#### Compositional summaries

For each function, investigate a summary containing required capabilities, maximum fuel, maximum stack bytes, maximum allocated bytes, maximum output bytes and termination class.

A summary must be classified as a proved upper bound, conservative static estimate, or unknown. These states must never be conflated. Sequential additive resources generally compose by addition; peak-live resources need a maximum/liveness analysis; nested calls add stack; recursion needs a proved ranking/recurrence or remains dynamically fuel-bounded. If a finite bound cannot be established, execution may still proceed under an explicit runtime ceiling, but no static-bound claim is issued.

Evaluate precision, analysis cost, false rejection and runtime overhead. The research question is whether useful compositional bounds can be obtained for a practical subset without making the language unusably restrictive.

### 3.5 Capability and authority contracts

Model authority as an explicit set of typed capabilities, not ambient process privilege. Candidate classes include bounded input/output, filesystem scopes, network endpoints, entropy, clock, process creation and secret access. Each capability specifies operations, resource ceilings, scope and revocation semantics.

A function's effect summary is a requirement set. A caller may invoke it only if its effective grant contains those requirements. Grants are attenuable: a callee receives no more authority than its caller explicitly passes or delegates. No implicit ambient escalation is permitted. Missing authority is a validation or invocation failure, not a silent fallback to host privilege.

Evidence binds the program's effect requirements, actual launch grant, policy decision and issuer/provenance, delegation attenuation chain, and host-adapter mapping to OS operations.

A capability manifest alone does not prove enforcement. The host adapter and every path to privileged operations remain in the trusted base until correspondence is established. Secret access needs separate lifecycle and non-disclosure properties; possession of a secret capability is not proof that secret data cannot leak.

## 4. Falsifiable research hypotheses

**H1 — Checkable acceptance.** A small checker validates certificates for a bounded CCAM subset with lower trusted complexity than the producer, rejecting malformed, stale and mismatched evidence.

**H2 — Semantic preservation.** The concrete evaluator refines a formal CCAM transition system for all accepted programs in the declared subset, including traps, evaluation order, calls and resource counters.

**H3 — Compositional resource bounds.** Function summaries compose soundly for selected deterministic resources, with measurable precision and analysis cost; dynamic ceilings cover residual cases.

**H4 — Authority non-escalation.** Capability requirements and attenuation are checked compositionally, and the evaluator/host boundary performs no effect outside the launch grant.

**H5 — Evidence integrity.** Binding evidence to canonical program identity, semantics version and contracts prevents accidental/adversarial reuse across changed artefacts; provenance identifies the remaining trusted components.

Each hypothesis requires negative controls and counterexamples, not only positive examples.

## 5. Proposed implementation sequence

1. **Inventory and freeze interfaces.** Reconcile CCAM v0.1, evaluator, grant semantics and formal models. Record exact commits and unresolved mismatches. Do not silently extend v0.1.
2. **Formalise accepted-program predicate.** Define a whole-program model for functions, calls, closed validation, effects and resource configuration. Specify raw JSON decoding as a separate boundary.
3. **Certificate prototype.** Define a deterministic certificate format for structural validation. Add a small checker and adversarial tests for stale digest, altered code, limits, capabilities, malformed proof nodes, duplicate keys and oversized evidence.
4. **Evaluator correspondence.** Model small-step multi-frame execution with shared fuel/depth. Establish transition simulation for concrete evaluator operations, including failure atomicity and trap precedence.
5. **Resource summaries.** Start with fuel and stack. Add function summaries and compare against exact execution traces over generated programs. Add heap/output only after accounting contracts stabilise.
6. **Capability subset.** Select one narrow effect, such as bounded output, and thread an explicit capability from entry to host adapter. Prove no operation occurs without it; test absent, narrowed and mismatched grants.
7. **Backend extension.** After evaluator correspondence, specify a backend simulation relation and execute the same conformance vectors on generated binaries.
8. **Reproducible evaluation.** Publish proof scripts, checker, schemas, exact revisions, CI runs, resource measurements, adversarial corpus and independent review.

Each step is independently reviewable. The first deliverable is this specification and its proof-obligation ledger. The first implementation milestone is a certificate checker for a deliberately small CCAM subset, not a new general-purpose proof language.

## 6. Evaluation design

Compare three modes on identical generated and hand-written programs:

1. Baseline: validation/evaluation without portable evidence.
2. Evidence checked: certificate checked at load time, then bounded execution.
3. Evidence plus summaries: certificate and compositional resource/effect summaries checked at load time.

Measure certificate size and checker time; producer/checker memory peaks under malformed inputs; compile/analysis time and bound precision; runtime throughput and per-transition overhead; actual versus declared fuel, stack and allocation; rejection precision and false rejection; capability-check overhead and forbidden-effect attempts; and reproducibility across clean builds and hosts.

Include exact-limit and one-over-limit cases, recursion, branching, loops, unreachable malformed instructions, deep calls, adversarial aggregate sizes, forged certificates and mutation of every bound field. Publish negative outcomes and uncertainty.

## 7. Threat model and trusted computing base

Assume cryptographic hashes are collision resistant and that the verifier binary, proof checker, semantics version, host kernel and explicitly listed platform adapters are not compromised. These assumptions must appear in every evidence report.

The certificate producer and compiler are untrusted for acceptance if the checker independently verifies their output. The verifier/checker, canonical decoder, evaluator, capability adapters and relevant OS interfaces remain trusted until each has a proved or independently validated refinement. Signatures establish provenance/identity, not semantic correctness. A valid certificate does not make a compromised host trustworthy.

Evidence is fail-closed: missing, stale, unsupported, malformed or unverifiable evidence yields UNKNOWN/REJECT, never PASS. User-facing status distinguishes statically proved, dynamically enforced, empirically tested, assumed and unknown properties.

## 8. Novelty and publication discipline

Proof-carrying code, resource-aware type systems and capability security are established research areas. The novelty claim is not that these are individually new. The candidate contribution is their integration around one versioned execution artefact and a small independently checkable assurance boundary, with explicit correspondence from language-level claims to concrete execution.

Before claiming novelty, review proof-carrying code, typed assembly, proof-carrying authorization, resource-aware type systems, cost semantics, capability machines, object-capability languages, and verified compiler/evaluator refinement. Identify precisely what is new: a theorem, certificate/checker design, resource algebra, capability composition rule, implementation result or empirical finding.

## 9. Non-claims

This proposal does not establish that current binaries carry certificates; that the current compiler/evaluator is formally verified; that existing Lean models correspond to the concrete evaluator; static termination or finite resource bounds for arbitrary programs; process-wide memory safety or complete heap accounting; complete capability isolation; a C-free production compiler/runtime; or novelty/publication readiness.

Present status is **proposed**. Promotion requires exact-revision implementation, tests, named theorems, axiom/assumption audits, correspondence evidence and independent review.
