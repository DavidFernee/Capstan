# Bosun's Locker — architecture and research programme

**Status:** initial architecture proposal; implementation not yet claimed  
**Date:** 2026-11-25  
**Implementation language:** Capstan only  
**Semantic foundation:** Capstan type/effect/ownership model and CCAM  
**Formal proof baseline:** repository-pinned Lean 4.19.0 unless an ADR changes it  
**Initial deployment profile:** single-node, durable, strict-serializable transactional database

## 1. Mission

Bosun's Locker is the Capstan-native transactional database and storage engine. Its purpose is to demonstrate that Capstan can implement a large, concurrent, persistent, security-sensitive system without generated C or a C implementation runtime.

The engineering objective is not merely high throughput. Bosun's Locker must provide explicit, testable and compositional guarantees for:

- transaction isolation and atomicity;
- crash consistency and acknowledged-commit durability;
- memory safety, ownership and data-race freedom;
- bounded resource consumption and overload behaviour;
- tenant and object-level authority;
- query semantics and deterministic error behaviour;
- backup, restore, migration and operational recovery;
- performance across low-contention, skewed, hot-key and analytical workloads.

No blanket claim of “bug-free”, “unhackable”, “zero data loss” or “formally verified database” is permitted. Each guarantee must identify its precise property, implementation revision, platform, assumptions, tests, proofs and residual trusted computing base.

## 2. Architectural principles

1. **Specify before optimising.** Transaction, storage and recovery semantics are normative contracts. An algorithm is replaceable only behind those contracts.
2. **One semantic authority.** The executable reference model and transaction specification define allowed behaviour; tests do not infer semantics from the current implementation.
3. **Strict serializability as the default target.** The initial public transaction profile targets strict serializability (serializable execution respecting real-time order). Weaker profiles are not silently substituted for performance. Any additional profile needs explicit semantics, API naming and conformance tests.
4. **Durability is an observable protocol.** The exact point at which commit is acknowledged, the persistence primitive relied upon, and the recovery guarantee are specified.
5. **Compositional resource accounting.** A transaction's CPU, memory, locks, versions, I/O, temporary storage, query work and network usage draw from explicit budgets. Local limits cannot reset aggregate budgets.
6. **Authority is explicit.** Database handles, schema/table access, administrative operations, backup, replication and filesystem access are capability-scoped. No ambient authority.
7. **Concurrency is structural.** Ownership, immutable sharing, locks, atomics, task scopes and cancellation follow the Capstan concurrency contract. No hidden detached tasks.
8. **Model/implementation boundary is tested.** Every abstract storage operation has a contract; generated model traces are executed against the real implementation.
9. **Recovery is tested as a first-class execution path.** Faults are injected at filesystem, kernel, device and process boundaries; recovered state is checked independently.
10. **C-free by construction.** All first-party production implementation, tests, generators and tooling are Capstan. No generated C, C/C++/Rust/Python implementation or foreign-language test harness is introduced. External OS/device interfaces remain narrow, documented trust boundaries.
11. **Evidence is revision-bound.** A proof or benchmark for one commit is not automatically evidence for another.
12. **Performance is measured, not asserted.** Compare with appropriate established systems on reproducible workloads and publish raw data and configuration.

## 3. System boundary and component architecture

```
                  Capstan applications / Topsail
                              |
                    typed query & transaction API
                              |
+----------------------------------------------------------------+
|                         Bosun's Locker                          |
|                                                                |
|  SQL front end       Schema/catalogue       AuthZ/capabilities  |
|       |                    |                       |             |
|  Typed logical plan -> Optimizer -> Physical execution engine   |
|                                      |                         |
|                         Transaction coordinator                |
|                    snapshot / validation / commit               |
|                                      |                         |
|                  MVCC version & conflict manager                |
|                                      |                         |
|       Indexes <-> Buffer/cache manager <-> Page/storage layer   |
|                                      |                         |
|                          Durable log                            |
|                                      |                         |
|                    Recovery / consistency checker               |
|                                                                |
|  Backup/restore | telemetry | migration | quota/admission       |
+----------------------------------------------------------------+
                              |
              Capability-scoped storage/device adapter
                              |
            Host OS initially; Helm service in future
```

This is a logical decomposition, not a required process topology. Begin as a single-node embedded/server process with explicit internal interfaces. Do not introduce a network hop between transaction coordination and storage merely to imitate a disaggregated architecture. A separate concurrency-control service is a research option, not the initial topology.

### 3.1 Trust boundaries

- Client requests and query text are untrusted.
- Serialized pages, logs, indexes, snapshots and backups are untrusted until validated.
- Filesystem and block-device outcomes may be partial, reordered, delayed or failed according to the adapter contract.
- OS flush and persistence guarantees must be documented per platform and filesystem/device combination.
- Replication peers are untrusted protocol participants, even when authenticated.
- Extensions and user-defined functions receive no authority by default.
- The compiler/runtime, cryptographic primitives, storage adapter and hardware form part of the declared trusted base until individually verified.

### 3.2 Process and deployment profiles

**Profile A — embedded library:** one process, local durable store, caller-provided capabilities, bounded query execution.

**Profile B — standalone server:** isolated service, authenticated clients, multi-tenant capability enforcement, quotas and operational APIs.

**Profile C — replicated service:** added only after single-node transaction and recovery gates; explicit consistency and failure model.

The profiles share transaction semantics. They may differ in transport and deployment adapters, not in what an acknowledged commit means.

## 4. Initial semantic decisions

### D-001 — Default isolation target

Target strict serializability for the initial transaction API. Define transaction histories with invocation/response events, read/write sets or equivalent logical dependencies, commit/abort outcomes and real-time order. The verifier must reject histories that are not equivalent to a serial order consistent with real-time precedence.

This is a target contract, not a claim that an implementation exists. The concrete concurrency-control algorithm remains open until formal analysis and benchmark comparison.

### D-002 — Explicit weaker profiles

Do not expose “snapshot isolation” or “read committed” as vague tuning switches. If weaker profiles are added, each must have a formal definition, documented anomalies, API-visible selection and a separate conformance suite. Application code must be able to state the guarantee it requires.

### D-003 — Single-node before distributed

The first implementation is a single-node durable database. Distributed commit, consensus, replication, sharding and global serializability are deferred. The architecture must avoid choices that make them impossible, but must not pay their coordination cost prematurely.

### D-004 — MVCC is the baseline candidate, not a sacred choice

Use MVCC as the primary design candidate because it supports snapshot reads and separates reader/writer lifetimes. Compare at least:
- strict two-phase locking (S2PL);
- optimistic concurrency control (OCC);
- serializable snapshot isolation / dependency tracking;
- timestamp ordering or deterministic scheduling;
- hybrid policies selected by workload.

No algorithm is selected solely from literature throughput figures. A candidate must satisfy the same reference semantics, crash model and resource contract.

### D-005 — Durable commit semantics

A successful durable-commit response means the transaction's commit record and all data needed to recover its effects have crossed the documented persistence boundary. A response must never imply durability based solely on data residing in volatile process memory or an unflushed device cache.

The precise protocol (WAL, group commit, checksums, flush/barrier sequence, torn-write protection and platform calls) is specified in the storage design before implementation.

### D-006 — Query language

A typed, parameterised relational query interface is the target. SQL compatibility is a product decision to be staged; the first vertical slice may use a small typed query AST and a deliberately limited SQL subset. Do not implement a broad SQL parser before transaction and storage semantics are stable.

### D-007 — Proof toolchain

Align formal work with the repository's pinned Lean 4.19.0 proof baseline. Research techniques from Isabelle/HOL and Rocq/Iris may inform models and proof structure, but must not silently add a second or third mandatory proof toolchain. Any change requires an explicit ADR.

## 5. Storage architecture

### 5.1 First durable storage profile

The initial store is a page-oriented durable file format with:
- explicit format version and feature flags;
- fixed-width, endian-defined fields;
- page identity, generation and checksum;
- bounded page size and allocation limits;
- typed record encoding and strict validation;
- explicit free-space and page-reuse rules;
- a durable log describing state transitions;
- recovery metadata and checkpoint protocol.

The choice between B+ tree, LSM tree and hybrid indexing remains open for the first implementation. Evaluate by read/write mix, write amplification, tail latency, compaction/maintenance costs, recovery time, memory footprint and proof complexity. A B+ tree is a reasonable initial row-store candidate; an LSM design is a strong write-heavy candidate. Do not assume one wins across workloads.

### 5.2 Write-ahead logging and recovery

The storage protocol must specify:
- log sequence number allocation and monotonicity;
- log record framing, checksums and maximum lengths;
- transaction begin, update, commit and abort representation;
- pageLSN or equivalent relation between data pages and log;
- write ordering and required flush/barrier operations;
- group commit and acknowledgement semantics;
- checkpoint start/end and recovery truncation rules;
- torn, missing, duplicated, corrupt and reordered writes;
- idempotent redo and any required undo;
- log exhaustion and disk-full behaviour;
- recovery after repeated crash during recovery.

No page may become durable in a state that recovery cannot reconcile with its durable log. Recovery itself must be restartable and idempotent. A commit must not be acknowledged before the declared durability boundary.

### 5.3 MVCC and version lifecycle

Represent versions with explicit creator/commit metadata and visibility rules. Define:
- snapshot acquisition and timestamp/epoch allocation;
- read visibility and own-write visibility;
- write-write conflict detection;
- predicate/range conflict handling needed for strict serializability;
- commit validation and serialization order;
- aborted/in-flight version treatment;
- safe version reclamation;
- long-running transaction impact and retention quotas;
- vacuum/compaction concurrency and crash recovery.

No version may be reclaimed while a live snapshot, cursor, backup, replication stream or recovery operation can still observe it. This is a lifetime/epoch invariant, not a best-effort heuristic.

### 5.4 Indexes and query execution

Separate logical query semantics from physical operators. Initial operators should be deliberately few and fully tested: point lookup, bounded range scan, insert, update, delete, filter, projection and a basic join only after the storage core is stable.

Index entries must preserve transaction visibility and be recoverable from durable state. The query planner must use bounded search and memory; a malformed or adversarial query cannot trigger unbounded optimizer work. Query plans are typed internal values, not strings assembled for execution.

## 6. Transaction API and lifecycle

Conceptual API only; syntax is not committed:

```text
with_transaction(capability, budget, isolation = StrictSerializable) {
    read(table, key)
    insert(table, key, value)
    update(table, key, value)
    delete(table, key)
    commit()
}
```

Transaction states are explicit:

```
Created -> Active -> Preparing -> Committed
                   |             |
                   +-> Aborted <-+
```

The actual state machine must distinguish commit decision, durable commit record, externally acknowledged commit and recovery resolution. A client timeout after sending commit is not proof of abort. Provide a transaction-status/idempotency mechanism so clients can resolve an ambiguous response without blindly replaying non-idempotent business effects.

Required invariants:
- no read observes an uncommitted write from another transaction;
- each committed transaction has one serialization position;
- strict serializability respects real-time precedence;
- aborted transactions have no visible effects;
- successful durable commit survives the declared crash model;
- no partial transaction becomes visible after recovery;
- commit/abort are terminal and idempotent at the protocol boundary;
- cancellation before commit follows a defined abort path;
- cancellation after the durable commit decision cannot roll back an acknowledged commit;
- resource exhaustion cannot leave an unresolvable half-committed state.

## 7. Resource, concurrency and authority contracts

### 7.1 Per-transaction budgets

Every transaction has explicit ceilings for:
- CPU/fuel and planning steps;
- memory and temporary allocations;
- rows/keys scanned and result cardinality;
- lock/conflict wait and retry attempts;
- versions created and retained;
- log bytes and storage growth;
- I/O operations and bytes;
- open cursors and concurrent subtasks;
- wall-clock deadline (separate from deterministic fuel).

Budgets compose with database, tenant and process budgets. A child query operator cannot reset a transaction's aggregate counters. A transaction cannot escape tenant quotas by opening multiple sessions.

### 7.2 Concurrency and cancellation

Use Capstan's structured task model. Every transaction-owned task, cursor, lock guard, buffer lease and I/O request has an owner and bounded lifetime. No detached work is permitted in the safe profile.

Cancellation is cooperative. It cannot interrupt a critical section between invariant-breaking and invariant-restoring operations. Cleanup is explicit for resources whose close/flush can fail. The API distinguishes cancellation requested, abort initiated, abort completed, commit durable and response delivered.

### 7.3 Capability model

Capabilities are explicit and attenuable:
- database-open capability;
- schema/table read and write capabilities;
- row/column policy capability where required;
- schema migration/admin capability;
- backup/restore capability;
- replication membership/transport capability;
- metrics/diagnostic capability with secret-redaction policy.

A query's authority is the intersection of caller authority, transaction authority and object policy. Query text cannot amplify authority. Avoid confused-deputy paths through views, stored routines, callbacks, backup, import/export and administrative APIs.

## 8. Research programme: problems to solve

Each item is a research hypothesis, not a promised result. Success requires a reproducible improvement over relevant baselines without weakening semantics.

### R-01 — Mechanised end-to-end strict serializability

Build a formal history model and prove the selected protocol implements strict serializability. Extend the proof across the transaction manager/storage interface. Investigate modular specifications and refinement mappings inspired by VerIso and recent separation-logic isolation work.

**Potential contribution:** a Capstan/Lean-friendly compositional proof that connects transaction API histories, MVCC visibility, index operations and storage commit semantics, rather than proving only an isolated protocol model.

### R-02 — Executable spec-to-implementation conformance

Generate traces from a finite abstract storage model and execute them against the actual Capstan storage implementation. Cover every reachable abstract state for small bounds; use coverage-guided sampling and state-space reduction for larger cases.

**Potential contribution:** a reusable model-to-implementation test generator that checks both operation results and durable post-crash state.

### R-03 — Recovered-state durability verification

Build a crash harness that injects failures at every persistence boundary and validates the recovered logical database against an independent transaction-history oracle. Include filesystem/kernel/device failure points, short writes, reorderings, torn pages, flush failures, disk-full and repeated crashes during recovery.

**Potential contribution:** a recovery oracle based on allowed committed histories and checksummed state graphs, rather than checking only that the database restarts or that WAL records parse.

### R-04 — Correctness-preserving adaptive concurrency control

Measure conflict rate, abort rate, hot-key concentration, queue depth, retry amplification and tail latency. Adapt admission, wait/abort policy and backoff with hysteresis. The adaptive controller may select among pre-verified policies but cannot alter isolation semantics, commit ordering or validation rules.

**Potential contribution:** a formally constrained controller whose decisions are performance-only refinements. Prove that every selected mode implements the same strict-serializable contract; test controller stability under oscillating and adversarial workloads.

### R-05 — Resource-bounded transactions with useful tail guarantees

Create compositional budgets and admission control so overload is rejected or queued predictably before it becomes unbounded memory growth, retry storms or latency collapse.

**Potential contribution:** resource semantics that cover the whole transaction path, including optimizer, MVCC versions, log, recovery, replication and maintenance, rather than per-component limits only.

### R-06 — Hybrid MVCC version management

Investigate memory-resident commit metadata with durable/out-of-memory version storage, transaction-aware compaction and safe visibility metadata. Compare with conventional in-memory MVCC and LSM-based approaches.

**Potential contribution:** a version representation with predictable memory ceiling and low commit overhead while retaining constant- or bounded-cost visibility checks. Must prove no visibility regression and safe reclamation.

### R-07 — Crash-consistent multi-tier storage

Explore DRAM + SSD/NVMe initially; NVM/persistent memory only when available and specified. Model ordering, write granularity, barriers, DMA and cache persistence explicitly.

**Potential contribution:** a portable persistence contract and refinement-tested adapter that separates abstract durability from platform-specific persistence primitives. Do not claim NVM support without actual hardware/semantics.

### R-08 — Proof-aware query optimisation

Define relational operators with explicit semantics, cardinality/resource bounds and transaction snapshot. Validate optimisations by equivalence checking or translation validation against the logical plan.

**Potential contribution:** query optimisation that emits a proof/evidence object for each rewrite, with runtime checks where static proof is unavailable. No unvalidated AI-generated rewrite enters execution.

### R-09 — Serializable predicate and range conflict detection

Investigate phantom prevention and predicate locking/index-range dependency tracking under concurrent inserts, deletes and range scans.

**Potential contribution:** precise range-conflict tracking that limits false conflicts while preserving strict serializability, with mechanised counterexample search.

### R-10 — Online schema migration and index replacement

Model concurrent readers/writers during schema/index version transitions, including crash and rollback.

**Potential contribution:** a staged migration protocol with explicit compatibility windows and proof that each committed transaction observes a coherent schema version.

### R-11 — Replication and global transaction semantics

After single-node correctness, investigate consensus-backed replication, deterministic state-machine execution and global strict serializability. Separate safety from liveness and availability assumptions.

**Potential contribution:** compositional proof across local storage commit, replication log commit, leader change and client acknowledgement. No distributed transaction feature before the failure model and commit semantics are explicit.

### R-12 — Privacy-preserving observability

Ensure query plans, logs, traces and metrics do not leak secrets or tenant data. Define data minimisation, bounded labels, redaction and access capabilities.

**Potential contribution:** type/effect-aware telemetry that carries sensitivity labels and proves or tests redaction at sink boundaries.

## 9. Evaluation programme

### 9.1 Workloads

- read-heavy and write-heavy OLTP;
- uniform and Zipfian key distributions;
- hot-row and hot-range contention;
- short and long transactions;
- mixed point/range scans;
- bulk load and update;
- large and skewed values;
- mixed OLTP/analytical scans;
- multi-tenant noisy-neighbour workloads;
- crash/recovery and backup/restore;
- adversarial queries and resource exhaustion.

Use standard public benchmarks where suitable (e.g. TPC-C-like workloads, YCSB and TPC-H/DS-style analytical workloads), while publishing schema, workload generator, seeds, hardware, OS, compiler, configuration and raw measurements. Do not claim benchmark compliance or official results without following the relevant rules.

### 9.2 Metrics

Report throughput, p50/p95/p99/p99.9 latency, abort/retry rate, lock/conflict wait, CPU, resident memory, bytes written per logical byte, log amplification, compaction cost, recovery time, time to restore, query-plan stability and resource-limit enforcement.

Compare with mature systems selected by workload and deployment model. Report both wins and losses. Never use a single peak throughput number as a general performance claim.

### 9.3 Correctness and resilience metrics

- history checker accepted/rejected results;
- model-state and transition coverage;
- generated conformance traces and implementation mismatches;
- crash points injected and recovered states checked;
- mutation score for transaction/storage invariants;
- fuzz corpus coverage and minimized counterexamples;
- proof theorem coverage and unresolved assumptions;
- recovery idempotence across repeated crashes.

## 10. Milestones and gates

| Milestone | Deliverable | Exit criteria |
|---|---|---|
| BL-0 Research baseline | Research register, threat model, decision log | Relevant literature mapped to concrete open problems; no algorithm prematurely fixed |
| BL-1 Transaction semantics | History model and transaction state machine | Strict-serializable contract, real-time order and abort/commit semantics unambiguous |
| BL-2 Reference oracle | Executable model and independent history checker | Positive and negative histories; anomaly counterexamples |
| BL-3 Storage contract | Page/log/flush/recovery specification | Crash model, durable acknowledgement and idempotent recovery specified |
| BL-4 Minimal durable store | Capstan-only key/value or narrow relational slice | Create/read/update/delete, restart recovery and bounded resource behaviour |
| BL-5 MVCC/serializable core | Concurrent transactions | Strict serializability validated against independent histories; formal protocol model |
| BL-6 Implementation conformance | Model-generated test runner | Actual storage implementation passes bounded exhaustive and randomized conformance suites |
| BL-7 Query engine | Typed query AST and initial physical operators | Query semantics, bounded planner/executor, proof/evidence for supported rewrites |
| BL-8 Hardening | Fault injection, fuzzing, recovery and security suite | Recovered-state checks pass under declared crash/failure model |
| BL-9 Performance | Baselines and adaptive controller | Reproducible performance gains without changed isolation semantics |
| BL-10 Replication | Replicated profile | Explicit consistency model, fault model, proof and failure-injection evidence |

No milestone is complete merely because its document exists. Each has an implementation, test and evidence artifact.

## 11. Initial pullable work packages

| ID | Priority | Work | Definition of done |
|---|---:|---|---|
| BL-001 | P0 | Transaction history semantics | Normative history/event model with real-time order and commit/abort rules |
| BL-002 | P0 | Independent serializability checker | Checks strict serializability for bounded histories; includes known anomalies |
| BL-003 | P0 | Transaction state machine | Explicit state transitions, linearisation points and cancellation/timeout cases |
| BL-004 | P0 | Storage fault model | Enumerates allowed/rejected write, flush, reorder, torn-write and crash outcomes |
| BL-005 | P1 | Page/log format ADR | Versioned format, record framing, checksum and compatibility rules |
| BL-006 | P1 | Recovery model | Executable redo/recovery semantics and idempotence properties |
| BL-007 | P1 | Crash injection harness | Deterministic failure points and recovered-state oracle |
| BL-008 | P1 | MVCC visibility model | Snapshot visibility, own writes, conflicts, aborts and reclamation rules |
| BL-009 | P1 | Algorithm comparison | S2PL/OCC/SSI/timestamp/deterministic candidate benchmark and proof-complexity matrix |
| BL-010 | P1 | Capability-scoped API | Typed database/table capabilities and negative authority tests |
| BL-011 | P1 | Aggregate transaction budgets | Compositional CPU/memory/I/O/version/query budgets and exhaustion tests |
| BL-012 | P2 | Typed query AST | Small relational algebra and deterministic type errors |
| BL-013 | P2 | Proof-aware rewrite checker | Validates a bounded set of relational rewrites |
| BL-014 | P2 | Adaptive admission controller | Hysteresis-based admission policy preserving verified transaction protocol |
| BL-015 | P2 | Hybrid MVCC prototype | Compares memory/durable metadata representations under same conformance suite |

## 12. Explicit non-goals for the first release

- distributed serializable transactions;
- SQL feature completeness;
- arbitrary stored procedures or native plugins;
- automatic schema changes without an explicit migration protocol;
- unbounded query execution or unlimited transactions;
- transparent exactly-once side effects across arbitrary external systems;
- automatic adaptive changes to isolation semantics;
- claims of zero data loss outside the declared storage/flush failure model;
- claims of implementation formal verification before correspondence theorems exist.

## 13. Open decision records

The following choices require benchmark and proof evidence before implementation is locked:
- B+ tree vs LSM vs hybrid primary index;
- S2PL vs SSI/dependency tracking vs OCC vs timestamp/deterministic concurrency;
- WAL record design, group commit and page layout;
- timestamp/epoch source and wraparound strategy;
- MVCC version placement and reclamation;
- SQL subset and compatibility target;
- embedded vs server-first product packaging;
- storage adapter and supported host OS/device matrix.

## 14. Research references reviewed (2025–2026)

1. Ghasemirad et al., **VerIso: Verifiable Isolation Guarantees for Database Transactions**, PVLDB 2025. Mechanised protocol verification and counterexample discovery.
2. Mathiasen, Timany and Birkedal, **Verifying Isolation Levels of Database Implementations for Free Using Separation Logic**, 2026 preprint. Derives isolation guarantees from implementation-level separation-logic specifications and verifies an MVCC key-value implementation in Rocq/Iris.
3. Schultz and Demirbas, **Design and Modular Verification of Distributed Transactions in MongoDB**, VLDB 2025; related MongoDB engineering report, 27 February 2026. Compositional protocol/storage specification and model-generated implementation conformance tests.
4. **Fawkes: Finding Data Durability Bugs in DBMSs via Recovered Data State Verification**, SOSP 2025. Fault injection and recovered-state verification identified durability defects across mature systems.
5. **Fast Verification of Strong Database Isolation (Extended Version)**, arXiv:2511.14067, 18 November 2025. Hyper-polygraph encoding and SMT verification of serializability and snapshot isolation.
6. **Stabilizing Distributed OLTP under High Contention via Measurement-Driven Adaptive Concurrency Control**, Scientific Reports, 9 July 2026. Runtime measurement, hysteresis and admission/backoff regulation; results require independent replication and workload-specific assessment.
7. **Concurrency Control as a Service**, arXiv:2603.13897, 14 March 2026. Decoupled execution/concurrency-control/storage architecture; latency and coordination trade-offs make this a later research direction.
8. **REGSwan: Hybrid MVCC Management for Efficient Transaction Processing in LSM-Tree-Based Key-Value Stores**, VLDB 2026 programme. Hybrid in-memory/out-of-memory MVCC and LSM integration.
9. Wang et al., **Crash consistency in an NVM-enabled hybrid storage system: Problems, solutions, and verification**, Journal of Systems Architecture, May 2026. Write ordering, granularity and parallel-write persistence problems.

Literature is a source of hypotheses and methods, not proof that a technique will work in Bosun's Locker. Before implementation decisions, obtain and review full papers, artifacts and benchmark methodology; record limitations and reproduce relevant results where feasible.

## 15. Definition of done for Bosun's Locker 1.0

A 1.0 release is not a prototype with a SQL prompt. It requires:
- stable, versioned transaction and storage specifications;
- a documented strict-serializable transaction profile;
- crash-consistent durable commit and repeatable recovery;
- an independent history checker and model-generated implementation conformance suite;
- bounded, compositional resource accounting;
- capability-based authority and tenant isolation;
- reproducible benchmarks against named baselines;
- a Capstan-only first-party implementation and build/run dependency inventory;
- platform-specific storage guarantees and failure assumptions;
- proof reports that distinguish model theorems from implementation correspondence;
- external review and a published residual risk register.

The first deliverable is BL-001 through BL-004: transaction semantics, independent history checker, transaction state machine and storage fault model. These make every subsequent algorithm decision testable.
