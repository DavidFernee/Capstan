# Concurrency runtime refinement gap: reference machine to executable runtime

**Status:** source-level architecture gap analysis. No scheduler implementation, native concurrency runtime, or compiler/runtime refinement proof is claimed here.  
**Scope:** identify the proof and implementation boundary between Capstan's bounded concurrency reference models and a future supported runtime.  
**Prerequisites:** `CONCURRENCY-SAFETY-CORE.md`, `CONCURRENCY-BLOCKING-AND-DEADLOCK-SEMANTICS.md`, `CONCURRENCY-MULTI-WAITER-SEMANTICS.md`, and the CCAM/runtime boundary specifications.

## 1. Executive finding

Capstan has a growing collection of bounded executable reference models for task lifecycle, typed protocol transitions, ownership/resource conservation, and single-waiter blocking/backpressure. These models are useful semantic artefacts. They are not a scheduler, a task runtime, a native thread implementation, or evidence that generated programs can execute concurrently.

The concurrency architecture document explicitly says that no concurrency runtime is currently claimed to exist. The C-free runtime boundary inventory treats threads as an optional platform-adapter family, to be considered only after the memory model, safepoints, and collector concurrency contract are fixed. The current implementation must therefore not be described as having structured concurrency, async scheduling, channels, locks, or atomics merely because the reference models exercise analogous abstract transitions.

This gap analysis makes that boundary explicit and establishes the sequence needed to cross it without importing undefined host-runtime semantics.

## 2. Evidence classification

| Layer | Current evidence | What it does not establish |
|---|---|---|
| Task and channel abstract state | Bounded Capstan reference model files under `verification/` | A runtime task, worker, continuation, queue, or channel exists |
| Protocol descriptions | Finite typed automata validator/interpreter and one-message refinement fixture | General endpoint typing, arbitrary protocol refinement, or native execution |
| Blocking receive/send | Single-waiter bounded reference slices | Multi-waiter scheduling, fairness, native blocking, or wakeup correctness under real parallelism |
| Research semantics | Architecture and research specifications | Implementation, theorem, or conformance |
| C runtime / collector | Existing C runtime; platform inventory records pthread-related collector/execution-context dependencies | A general Capstan task scheduler or channel runtime |
| CCAM / C-free work | Separate execution and backend workstreams | That concurrency operations have source syntax, CCAM operations, native lowering, or adapter implementations |

The exact-head status of the current blocking reference slice remains unresolved until CI runs against its corrected commit. A test file being registered or a workflow being green on an earlier commit is not current-head evidence.

## 3. Required semantic layers

Do not collapse these layers into one implementation milestone.

### Layer S — source contract

Specify the source-visible operations and their static rules:

- task spawn consumes transferable captures and arguments;
- task handles are linear and owner-scoped;
- await is a suspension effect;
- send moves payload ownership at a defined commit point;
- receive returns a typed message/EOF/cancel/failure outcome;
- channel close authority is explicit;
- cancellation points and cleanup effects are explicit;
- locks, guards and atomics are separate APIs with separate effects.

Required evidence: positive and negative type-checker tests, including captures, nested aggregates, borrowed lifetimes, use-after-move, handle duplication/drop, suspension with a live guard, and forbidden blocking in atomic contexts.

### Layer M — abstract machine

Define the full small-step machine, including:

- task lifecycle and runnable/blocked queues;
- continuation or resumable operation identity;
- channel buffers and ordered wait queues;
- reservations and message ownership;
- cancellation, close, failure and cleanup;
- scheduler choices and bounded resource exhaustion;
- observable outcomes for deadlock, quiescence, starvation and truncation.

Required evidence: complete state equality, exhaustive bounded exploration, invariant preservation, shortest counterexamples, fail-closed state limits, and separately stated fairness/environment assumptions.

### Layer R — runtime scheduler

Implement the machine's operational responsibilities:

- task allocation and continuation storage;
- runnable queue and worker wake/sleep protocol;
- typed wait registration and deregistration;
- exactly-once wakeup/reservation handling;
- task completion and linear join handles;
- cancellation delivery and cleanup execution;
- bounded queues, stacks, task counts and scheduler metadata;
- shutdown and worker failure handling.

The first runtime should be a deterministic single-worker scheduler. This deliberately avoids claiming parallel memory-model correctness while validating scheduling, suspension, resumption, queue ordering, cancellation, and resource accounting.

Required evidence: runtime adapter conformance tests against the abstract machine, deterministic trace replay, forced allocation/wakeup failures, task cancellation at every cancellation point, and state/ownership checks at every transition.

### Layer P — platform execution

Only after Layer R is stable should the platform adapter introduce multiple workers or OS threads.

The adapter contract must define:

- worker creation/join and shutdown;
- wake/sleep signalling without lost wakeups;
- memory ordering at queue publication and task-state transitions;
- thread-local and task-local state;
- stack and continuation limits;
- cancellation and worker-failure semantics;
- time source and timeout semantics if timers are supported;
- error mapping and resource limits.

No raw pthread or platform handle should become part of the Capstan source contract. The adapter must expose typed results and a closed set of platform outcomes.

### Layer G — garbage collector integration

Parallel execution cannot be enabled safely by adding worker threads alone. The collector needs a defined protocol for:

- task stack/continuation roots;
- register roots and safepoint publication;
- thread attach/detach;
- stop-the-world coordination or a separately specified concurrent collector;
- allocation during task switching and at safepoints;
- root visibility during cancellation and teardown;
- collector shutdown and worker failure.

Until this protocol is implemented and verified, a multi-worker runtime must not be enabled for programs that allocate managed objects concurrently.

### Layer C — compiler/backend refinement

For every source operation, identify the lowering sequence and its linearisation point. The refinement relation must cover:

- source task and channel state to CCAM state;
- CCAM state to generated runtime calls or native instructions;
- ownership and resource-ledger preservation;
- scheduler queue and wait-queue updates;
- atomic ordering and wakeup protocol;
- trap/failure/cancellation mapping.

A source-level proof does not establish correctness of generated C or native code. Translation validation, differential tests, and eventually verified compiler passes are separate evidence.

## 4. Why the deterministic scheduler comes first

A deterministic single-worker scheduler is not a concession in the assurance design. It is the smallest executable runtime capable of validating the task-state machine without introducing host data races or weak-memory behaviours.

It permits exhaustive testing of:

1. runnable FIFO selection and task yield;
2. blocked receive followed by message arrival and resumption;
3. blocked send followed by capacity release and resumption;
4. close while receiver and sender waits exist;
5. cancellation before and after wakeup commitment;
6. nested structured scopes and join completion;
7. failure propagation and cleanup reservation consumption;
8. bounded queue/task/stack exhaustion;
9. deterministic trace replay and shortest failure traces.

A single worker does not establish fairness unless the scheduler policy says how runnable tasks are selected. It also does not establish multi-worker memory ordering. Those are deliberately later gates.

## 5. Parallel worker protocol: proof obligations

When multiple workers are introduced, the following transitions must be treated as synchronisation protocols, not ordinary queue operations:

### 5.1 Publish runnable task

The task continuation and all state needed by its next step must be fully initialised before publication. Publication must happen-before a worker's successful dequeue and continuation access.

### 5.2 Register blocked task

The enabling-condition check and waiter registration must be atomic with respect to the event that can satisfy the condition. Otherwise an event can occur between check and registration and be lost.

### 5.3 Wake blocked task

The wakeup transition must atomically claim the wait registration, install or preserve any required message/capacity reservation, and publish the task as runnable. Exactly one concurrent event may claim the registration.

### 5.4 Cancel blocked task

Cancellation and wakeup must contend on one linearisation point. A cancelled task cannot remain in a queue, own a live wait ticket, or be made runnable by a stale notifier.

### 5.5 Worker shutdown

Shutdown must prevent new publication, resolve or cancel all accepted work according to policy, wake sleeping workers, join them, and prove that no task, wait registration, continuation or managed root remains live.

For each operation, specify acquire/release or stronger ordering as required by the abstract happens-before relation. Do not default to relaxed atomics or assume x86-64 ordering is portable evidence.

## 6. Runtime assurance gates

**RR0 — current reference baseline**
- Corrected single-waiter test fixtures pass exact-head CI.
- The reference models' invariants and rejected-transition non-mutation tests pass on supported CI compilers.
- No multiple-waiter code is accepted as verified before this gate.

**RR1 — deterministic scheduler**
- One worker, bounded tasks, explicit continuation state.
- Every scheduler transition maps to the abstract machine.
- Blocking, wakeup, cancellation, close, join and failure traces replay deterministically.
- No host threads or parallel allocation.

**RR2 — GC/safepoint contract**
- Root publication and task switching are specified.
- Allocation and collection at every permitted safepoint are tested.
- Cancellation and teardown cannot hide or lose roots.
- Collector behaviour is proven/tested under the chosen single-worker task scheduler.

**RR3 — multi-waiter channels**
- FIFO sender/receiver queues, wait tickets and reservations.
- Multiple waiters under adversarial scheduler choices.
- Exhaustive bounded cancellation/close/send/receive interleavings.
- Runtime traces refine the reference model.

**RR4 — multi-worker adapter**
- Worker wake/sleep and shutdown protocol.
- Explicit memory model and litmus suite.
- Lost-wakeup, duplicate-wakeup, queue-publication and task-migration stress.
- ThreadSanitizer and platform-specific testing where available; sanitizers are evidence, not proof.

**RR5 — compiler/backend bridge**
- Source typing and effects survive lowering.
- Generated operations refine abstract transitions.
- Cross-target tests and translation validation.
- Safe-profile claims limited to the proven/refined subset.

## 7. Research problems and potential contributions

The work should address genuine open problems rather than claim novelty from combining familiar components. Candidate research questions:

1. **Compositional wait-for analysis:** how can task/channel/join/resource dependencies be combined while preserving sound deadlock classification in the presence of external event sources?
2. **Cancellation-safe resource reservations:** can bounded cleanup obligations be composed across nested scopes, multiple wait queues, and committed-but-not-yet-resumed operations?
3. **Protocol-aware scheduler reduction:** which partial-order independence relation preserves FIFO selection, reservations, cancellation outcomes and liveness counterexamples?
4. **Resource-bounded liveness:** how can queue, task, stack and cleanup budgets participate in a progress argument without conflating resource admission with deadlock?
5. **Compiler/runtime refinement:** what is the smallest machine-checkable relation that connects linear source endpoints and structured tasks to scheduler and platform events?

For each candidate, require a related-work comparison, formal problem statement, explicit assumptions, proof obligations, and reproducible benchmarks/counterexamples before claiming a research contribution.

## 8. Explicit non-claims

This document does not establish that Capstan currently has a scheduler, async runtime, channel implementation, native worker pool, memory model for parallel execution, concurrent collector, or compiler/runtime refinement proof. It does not promise that all concurrent programs terminate, are starvation-free, or are deadlock-free. It is a staged engineering and assurance plan that prevents the bounded reference models from being mistaken for production runtime evidence.
