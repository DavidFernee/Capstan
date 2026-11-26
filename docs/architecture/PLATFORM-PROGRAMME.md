# Capstan platform programme: Helm, Bosun's Locker and Topsail

**Status:** architecture programme / target-state plan  
**Date:** 2026-11-25  
**Scope:** cross-project architecture, dependencies, work packages and acceptance gates  
**Implementation claim:** this document specifies work; it does not claim that the proposed systems are implemented, tested, secure or formally verified.

## 1. Purpose and governing rule

Capstan is intended to support demanding systems and application workloads through one coherent language, compiler, execution model, runtime, security model and evidence programme. The goal is not to bolt unrelated products onto the language. The goal is to make the shared foundations unusually strong, then demonstrate them in systems whose correctness and performance are independently measurable.

The named programmes are:

| Name | Responsibility | Architectural owner |
|---|---|---|
| **Helm** | Operating-system kernel | Kernel, architecture ports, device and platform interfaces |
| **Bosun's Locker** | Transactional database and storage engine | Transactions, query execution, persistence and replication |
| **Topsail** | Web application and service platform | HTTP services, application composition, identity and deployment |
| **Keel** | 3D engine and simulation | Scene, rendering, physics and deterministic simulation |
| **Halyard** | Media architecture | Media processing, codecs, pipelines and media security |
| **Shroud** | GUI toolkit | Cross-platform UI, input, rendering and accessibility |
| **Anchor** | IDE | Capstan development, diagnostics, debugging and assurance UX |

These names denote separate programmes, not evidence of implementation maturity. Every status claim must identify the branch, commit, platform, tested artefact and assurance level.

**C-free rule:** first-party implementations are to be written in Capstan. Architecture-specific assembly and narrowly scoped platform interfaces may be necessary. Generated C, a C compiler, libc or a C runtime must not be hidden dependencies of the eventual claimed Capstan build/run path. The present C-backed implementation remains a compatibility and differential baseline until the retirement gates are satisfied.

## 2. Shared platform architecture

The intended dependency direction is:

1. Capstan language, type/effect/ownership/capability system and compiler.
2. CCAM normative semantics, bounded validator, evaluator and resource model.
3. C-free runtime, memory services, collections, I/O, cryptography and standard library.
4. Native backends and narrow ISA/ABI/OS adapters.
5. Helm and user-space services.
6. Bosun's Locker, Topsail, Keel, Halyard, Shroud and Anchor.

Helm is not a prerequisite for all Capstan development: early tools and products may run on supported host operating systems. Conversely, Helm must not assume unfinished user-space services. Its early boot and kernel core must have a deliberately small dependency surface.

Bosun's Locker and Topsail must use the shared capability, effect, concurrency and resource contracts. Neither may create a parallel permission system or silently rely on unbounded queues, implicit background tasks, ambient filesystem access or shell execution.

## 3. Shared research and engineering foundations

### FND-1 — End-to-end execution correctness

- Freeze the relevant CCAM profile and version its normative semantics.
- Complete bounded decoding and whole-program validation.
- Align the Capstan-native evaluator with the normative machine.
- Specify calls, returns, traps, effects and exact resource accounting.
- Prove validator soundness and evaluator refinement for the declared profile.
- Prove source-to-CCAM simulation for the supported source subset.
- Establish native backend refinement against an explicit ISA/ABI model.
- Execute generated binaries in conformance tests; assembly-text inspection alone is insufficient.

**Gate:** one small, useful, specification-aligned C-free program can be compiled, validated, executed natively and checked against the reference semantics with a documented evidence chain.

### FND-2 — Compositional resources

Define common units and deterministic accounting for CPU steps/fuel, call depth, stack, heap, allocation, I/O, storage, network, GPU and task/channel buffers. Specify how budgets compose across calls, tasks, processes and services; define exhaustion and cancellation semantics. Distinguish abstract-machine fuel from wall-clock deadlines and physical resource measurements.

**Gate:** nested components cannot exceed an aggregate declared budget by exploiting independently reset local counters; accounting is tested at every boundary and has a formal model for the declared subset.

### FND-3 — Authority, effects and isolation

Specify typed capabilities for filesystem, network, process, device, clock, entropy, database and administrative operations. Make authority explicit in APIs and effect signatures. Define revocation, delegation, attenuation, object identity, confused-deputy resistance and ambient-authority policy. OS isolation remains a second enforcement boundary, not a substitute for source-level authority.

**Gate:** a component receives only declared authority; negative tests demonstrate that it cannot obtain undeclared authority through aliases, callbacks, plugins, subprocesses or confused-deputy paths.

### FND-4 — Concurrency and protocols

Complete ownership transfer, safe sharing, structured task scopes, cancellation, channel semantics, lock guards and protocol-state modelling. Distinguish data-race freedom from deadlock freedom, starvation, liveness, availability and application-level correctness. Do not claim the latter from the former.

**Gate:** the language and runtime enforce the specified safe concurrency subset; model checking, stress testing and machine-checked results cover named protocol properties.

### FND-5 — Assurance and evidence

Every claim is linked to exact source revision, platform, toolchain, tests, proof artefacts, assumptions and residual trusted computing base. Missing or stale evidence is UNKNOWN. CI must not turn a model-only theorem into an implementation claim. Include fuzzing, mutation testing, fault injection, sanitizer runs where available, independent review and reproducible build provenance.

**Gate:** each release claim can be regenerated from machine-readable evidence for the exact artefact and target platform.

## 4. Helm — operating-system kernel

### 4.1 Mission

Build a small, auditable, capability-oriented kernel in Capstan. Prioritise a comprehensible trusted computing base, memory isolation, explicit authority and measurable resource behaviour over feature count.

The architecture choice between microkernel, modular monolithic and hybrid remains a decision gate. The initial research baseline should compare all three against the same workloads and threat model. A microkernel is a reasonable initial hypothesis, not a pre-approved conclusion.

### 4.2 Work packages

**HELM-0 — Requirements and threat model**
- Define supported hardware, boot environment, privilege levels and threat actors.
- Define kernel/user boundary, trusted computing base and security invariants.
- Decide initial kernel architecture using documented criteria.
- Define system-call ABI and versioning policy.
- Record device, firmware, bootloader and hypervisor trust assumptions.

**HELM-1 — Bootable minimal kernel**
- Establish the smallest supported boot path on one emulator target.
- Enter a known execution mode, initialise memory and exception handling, and emit bounded diagnostic output.
- Establish reproducible kernel image builds and deterministic test harnesses.
- Keep architecture-specific assembly minimal, reviewed and isolated.

**HELM-2 — Memory and isolation**
- Physical page allocator and virtual address spaces.
- Page-table construction and validation.
- Kernel/user privilege separation.
- Guard pages and stack bounds.
- Mapping lifecycle and safe reclamation.
- IOMMU and DMA threat model before device DMA is enabled.

**HELM-3 — Execution and interrupts**
- Trap/exception entry and return.
- Timer and interrupt controller.
- Scheduler, context switch and task lifecycle.
- Pre-emption and interrupt-safe synchronisation.
- SMP bring-up only after uniprocessor invariants are established.

**HELM-4 — Capabilities and IPC**
- Kernel object model with unforgeable handles.
- Capability derivation, attenuation, transfer and revocation semantics.
- Bounded IPC and backpressure.
- Process isolation and service supervision.
- Explicit failure and cancellation contracts.

**HELM-5 — Devices and storage**
- Driver model and device ownership.
- Safe MMIO and DMA interfaces.
- Block-device contract and fault injection.
- Filesystem service boundary and crash-consistency tests.
- No unrestricted device access from ordinary applications.

**HELM-6 — Network and production hardening**
- Network device and stack integration.
- Secure boot/update design and rollback policy.
- Crash dumps, tracing and debugging.
- Adversarial kernel fuzzing and fault injection.
- Independent review of unsafe/assembly/platform boundary inventory.

### 4.3 Helm release gates

- **H0 Boot:** reproducible boot in the declared emulator configuration; bounded diagnostics; no unsupported hardware claim.
- **H1 Isolation:** independently tested user/kernel separation, address-space isolation and privilege transitions.
- **H2 Processes:** task lifecycle, IPC and capability checks pass adversarial tests.
- **H3 Storage:** crash injection demonstrates the declared persistence/recovery properties.
- **H4 Network:** protocol conformance and resource-exhaustion tests pass.
- **H5 SMP:** concurrency invariants and scalability tests pass on named hardware/emulators.
- **H6 Release:** exact-platform evidence, external review and residual TCB published.

No gate may be passed by documentation alone. A bootable prototype is not a secure general-purpose operating system.

## 5. Bosun's Locker — transactional database

### 5.1 Mission

Build a high-performance transactional database whose isolation, durability, authority and resource guarantees are explicit and testable. It is the flagship systems workload for proving that Capstan can express complex concurrent software without relying on C.

### 5.2 Initial architecture

Separate the following components behind typed, versioned interfaces:

- SQL or query-language front end and schema/type checker.
- Query planner and execution engine.
- Transaction manager and concurrency-control protocol.
- Storage engine and page/cache manager.
- Write-ahead log or equivalent durable commit protocol.
- Recovery and consistency checker.
- Index implementations.
- Authentication, capability and row/column policy enforcement.
- Replication layer, initially separate from the single-node correctness core.
- Observability, backup, restore and migration tools.

The first implementation must not attempt to solve every database problem at once. Start with a single-node transactional profile and make the semantics precise before adding distributed transactions or replication.

### 5.3 Work packages

**BOSUN-0 — Transaction semantics**
- Define transaction lifecycle and isolation levels.
- Specify serialisability criterion and conflict/visibility semantics.
- Define linearisation points for externally visible operations.
- Define abort, cancellation, timeout and retry behaviour.
- Build a small executable reference model and history checker.

**BOSUN-1 — Durable single-node core**
- Define on-disk format, page identity, checksums and versioning.
- Implement append-only WAL or another explicitly justified commit protocol.
- Specify commit acknowledgement and durability boundary.
- Implement crash recovery and idempotent replay.
- Fuzz parsers and inject crashes at every persistence boundary.

**BOSUN-2 — Transactions and concurrency**
- Implement the selected concurrency-control protocol.
- Prove or model-check serialisability for the declared profile.
- Test write skew, lost updates, phantoms, deadlocks and abort races.
- Ensure cancellation and resource exhaustion cannot produce partial commits.
- Measure contention, tail latency and throughput.

**BOSUN-3 — Query and index engine**
- Typed schema and query representation.
- Bounded query planning and execution.
- B-tree or another justified primary index.
- MVCC visibility and vacuum/compaction strategy.
- Cost model with reproducible benchmark corpus.

**BOSUN-4 — Security and operations**
- Capability-scoped database handles.
- Least-privilege schema/table/row/column access.
- Safe parameterised query interfaces.
- Backup, restore, online migration and audit log.
- Resource quotas and tenant isolation.

**BOSUN-5 — Replication**
- Define replication consistency model and failure assumptions.
- Add replicated state machine or another selected protocol only after single-node durability and transaction semantics are stable.
- Test partitions, reordering, duplicate delivery, node loss, membership change and recovery.
- Keep consensus safety distinct from liveness assumptions.

### 5.4 Bosun's Locker acceptance gates

- **B0 Reference:** transaction specification, executable model and independent history checker.
- **B1 Durability:** all declared crash points recover to a state allowed by the durability specification.
- **B2 Isolation:** adversarial histories satisfy the declared serialisability/isolation guarantee.
- **B3 Correctness:** storage, index and recovery invariants have property tests and formal results where claimed.
- **B4 Security:** capability and tenant isolation tests reject undeclared access.
- **B5 Performance:** independently reproducible throughput, latency, memory and recovery benchmarks against named competitors.
- **B6 Replication:** fault-injection evidence for the declared consistency and availability assumptions.

A database is not “serialisable” because it uses locks or MVCC. The property must be demonstrated against histories and the actual implementation.

## 6. Topsail — web application and service platform

### 6.1 Mission

Build a secure, composable web application platform for server-side applications and services. Topsail should make secure defaults easy and dangerous authority explicit. It should be an application platform, not a second language runtime or a separate security framework.

### 6.2 Architecture

- Typed HTTP request/response model.
- Protocol adapters for HTTP/1.1, HTTP/2 and HTTP/3, each with separate conformance gates.
- Routing and middleware with explicit effect/capability signatures.
- Structured concurrency for request/task lifecycle.
- Typed input validation and output encoding.
- Identity, authentication and authorization interfaces.
- Session and token lifecycle.
- Capability-scoped access to Bosun's Locker.
- File/object storage adapters with path and object identity protections.
- TLS and cryptographic services through the audited Capstan crypto layer.
- Observability with secret redaction and bounded cardinality.
- Deployment, configuration, secrets and update mechanisms.

### 6.3 Work packages

**TOPSAIL-0 — Threat model and HTTP semantics**
- Define attacker capabilities, trust boundaries and deployment assumptions.
- Specify parsing, canonicalisation, duplicate headers, framing and request-body limits.
- Define connection, request and cancellation lifecycle.
- Build protocol conformance and parser differential tests.

**TOPSAIL-1 — Safe request pipeline**
- Typed routing and request context.
- Bounded body parsing and decompression.
- Explicit input-validation and output-encoding contracts.
- Parameterised database operations.
- No shell interpolation in framework APIs.
- Safe path/object handling with symlink and traversal policy.

**TOPSAIL-2 — Identity and authority**
- Authentication provider interfaces.
- Session rotation, expiry and revocation.
- CSRF protection for cookie-authenticated browser flows.
- Origin and CORS policy.
- Capability-scoped application services.
- Secure password and token handling through reviewed cryptographic primitives.

**TOPSAIL-3 — Async execution and resource control**
- Structured task scopes for each request.
- Bounded queues, connections, bodies and concurrent work.
- Deadline and cancellation propagation.
- Backpressure and overload behaviour.
- Prevent blocking operations from starving async executors.
- Per-tenant and aggregate resource accounting.

**TOPSAIL-4 — Data and integration**
- First-class Bosun's Locker transaction integration.
- Explicit transaction boundaries and retry policy.
- Idempotency keys and duplicate request handling.
- Upload isolation, content inspection and storage quotas.
- Outbound network capabilities with SSRF-resistant destination policy.

**TOPSAIL-5 — Production operations**
- TLS configuration and certificate lifecycle.
- Structured logs, metrics and distributed tracing.
- Secret redaction and safe error reporting.
- Health, readiness and graceful shutdown.
- Reproducible builds, signed artefacts and deployment rollback.

### 6.4 Topsail acceptance gates

- **T0 Protocol:** parser and framing conformance; malformed-input and request-smuggling tests.
- **T1 Application safety:** negative tests for injection, CSRF, SSRF, path traversal, unsafe uploads and TOCTOU.
- **T2 Isolation:** request, tenant and capability boundaries hold under concurrency and cancellation.
- **T3 Resource safety:** overload tests demonstrate bounded queues, memory, connections and work.
- **T4 Data integrity:** transactional integration passes failure and retry tests without duplicate or partial effects.
- **T5 Production:** operational recovery, observability, deployment provenance and independent security review.

No framework can guarantee that every application is vulnerability-free. Topsail must state which classes it prevents structurally, which it detects, which require correct application policy and which remain outside its guarantee.

## 7. Cross-product integration contracts

### Helm ↔ user space
- Kernel services are exposed through a small, versioned syscall/IPC ABI.
- User-space services do not receive ambient kernel authority.
- Driver and filesystem services have explicit capability boundaries.
- Kernel implementation does not depend on Bosun's Locker or Topsail.

### Bosun's Locker ↔ Topsail
- Topsail receives database capabilities scoped to the application and tenant.
- Query parameters are values, never interpolated code.
- Transaction and retry semantics are explicit.
- Network request cancellation must not silently turn an acknowledged commit into an ambiguous result; define commit-status recovery.

### Capstan ↔ all programmes
- Shared type, effect, ownership, concurrency and resource semantics.
- Common diagnostics and evidence format.
- Common fuzzing and differential-testing infrastructure.
- No product-specific bypass of compiler or runtime safety contracts.

### Shroud/Anchor ↔ all programmes
- Anchor provides project templates, build profiles, diagnostics and test/proof reports.
- Opening a workspace never executes code.
- Build and test execution is explicit, bounded and cancellable.
- Evidence UI distinguishes specified, implemented, tested, model-proved and implementation-refined claims.

## 8. Kanban-ready work packages

These are initial pullable epics. Each epic must be decomposed into reviewable issues with a specification, tests, dependencies and a definition of done.

| ID | Work package | Priority | Depends on | Definition of done |
|---|---|---:|---|---|
| FND-01 | CCAM conformance profile and shared vectors | P0 | Current CCAM spec | Validator/evaluator agree on all declared vectors and malformed cases |
| FND-02 | Aggregate resource contract | P0 | CCAM profile | Units, composition and exhaustion semantics specified and tested |
| FND-03 | Capability/effect contract | P0 | Language core | Authority is explicit in a small executable vertical slice |
| FND-04 | Concurrency semantics closure | P0 | Ownership/type core | Task/channel/lock/cancellation semantics and tests are normative |
| HELM-01 | Kernel architecture decision record | P0 | Threat model | Comparative microkernel/modular/hybrid decision with evidence |
| HELM-02 | Boot protocol and emulator harness | P1 | HELM-01, backend | Reproducible minimal boot and automated smoke test |
| HELM-03 | Exception and memory-map specification | P1 | HELM-01 | Normative platform-neutral contract plus target-specific mapping |
| BOSUN-01 | Transaction reference model | P0 | FND-01, FND-04 | Executable model and history checker |
| BOSUN-02 | Durable page/WAL format | P1 | BOSUN-01 | Versioned format, recovery specification and crash harness |
| BOSUN-03 | Serialisability test corpus | P1 | BOSUN-01 | Known anomaly histories and independent checker |
| TOPSAIL-01 | HTTP threat model and parser contract | P1 | FND-02, FND-03 | Request framing, limits and adversary model specified |
| TOPSAIL-02 | Typed request pipeline | P2 | TOPSAIL-01, FND-04 | Bounded request lifecycle and negative tests |
| TOPSAIL-03 | Identity/CSRF/session contract | P2 | TOPSAIL-01, FND-03 | Threat-modelled, testable session and browser security contract |
| ASSURE-01 | Exact-revision evidence manifest | P0 | Existing assurance docs | CI records test/proof/platform/source revision and UNKNOWN state |
| PERF-01 | Cross-product benchmark harness | P1 | Reproducible build | Reproducible baselines, raw data and competitor methodology |

Priority meanings: P0 = foundational blocker; P1 = next implementation wave; P2 = dependent product work. These are sequencing priorities, not estimates or claims that work has started.

## 9. Global release and research rules

1. Every feature has a normative contract before its implementation is treated as stable.
2. Every security claim has a threat model, scope, assumptions and counterexamples.
3. Every proof names its model and implementation boundary.
4. No model theorem is promoted to an implementation guarantee without refinement.
5. Every resource limit is compositional or explicitly declared local.
6. Every asynchronous operation has defined cancellation and ownership semantics.
7. Every persistent format has versioning, corruption handling and recovery tests.
8. Every network parser is adversarially tested and resource-bounded.
9. Every benchmark is reproducible and compared against an appropriate baseline.
10. No C-free claim is made while a C compiler/runtime/generated-C path remains in the claimed artefact's dependency chain.
11. No product may weaken a shared Capstan guarantee for convenience; exceptions require an explicit, reviewed and measurable contract.
12. Unknown evidence is not a pass.

## 10. Initial decisions and open questions

The programme can proceed with conservative defaults, but the following decisions should be recorded before their dependent implementation gates:

- **Helm kernel architecture:** compare microkernel, modular monolithic and hybrid designs; do not prematurely lock in one.
- **Initial platform:** recommended first execution target is Linux on x86-64 under an emulator, with ARM64 architecture work designed in from the beginning. This is a sequencing proposal, not a statement of current support.
- **Bosun's Locker transaction profile:** choose the initial isolation guarantee and concurrency-control protocol through a written ADR and executable model.
- **Topsail protocol scope:** implement HTTP/1.1 first with strict framing and parser conformance; add HTTP/2 and HTTP/3 as separately gated protocols.
- **Deployment model:** decide whether Topsail initially targets Helm, host Linux, containers/VMs, or multiple environments. Keep deployment adapters separate from application semantics.

## 11. First programme review

The first review should produce four concrete artefacts:

1. A Helm architecture decision record and bootable-slice specification.
2. A Bosun's Locker transaction semantics document and history-checking test plan.
3. A Topsail threat model and HTTP request-lifecycle specification.
4. A shared FND-02/FND-03/FND-04 contract tying resource accounting, authority and concurrency together.

The first milestone is not a feature-count milestone. It is the point at which all three products can be implemented against stable shared contracts without inventing incompatible semantics.
