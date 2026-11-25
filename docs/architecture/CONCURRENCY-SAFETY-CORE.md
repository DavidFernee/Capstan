# Capstan concurrency safety core

**Status:** architecture proposal for review; no concurrency runtime is claimed to exist  
**Target:** v0.7 language and runtime workstream  
**Related:** [design map](../DESIGN-MAP.md), [C-free execution](C-FREE-EXECUTION.md), [runtime boundary inventory](C-FREE-RUNTIME-BOUNDARY-INVENTORY.md), [CCAM](CCAM.md), [coordination issue #80](https://github.com/DavidFernee/Capstan/issues/80), [concurrency issue #229](https://github.com/DavidFernee/Capstan/issues/229)

## 1. Design objective

Concurrency must be a property of the language's ownership, type, effect, lifetime and resource systems. It must not be a collection of thread APIs that rely on programmer discipline.

The safe concurrency profile is designed so that a well-typed program cannot create a data race, access an object after its lifetime, release a linear resource twice, use a lock guard after its protected access ends, or leave an owner-bound callback running after its owner is destroyed. These are language guarantees only after the corresponding rules, compiler implementation and proof/refinement gates are complete.

The design deliberately separates:
- **memory safety and race freedom**, which the safe type system must enforce;
- **protocol correctness and liveness**, which require explicit specifications, resource assumptions and, for bounded systems, model checking or proof;
- **availability**, which can still be affected by scheduling, resource exhaustion, OS failures and hardware faults;
- **functional correctness**, which is not inferred from race freedom.

A concurrency implementation that merely wraps pthreads, Windows threads or async executors is not sufficient.

## 2. Threat model and non-goals

The language must prevent safe source code from expressing unsynchronised conflicting access to shared mutable memory. It must also prevent lifetime races and unbalanced ownership of tasks, locks, callbacks, channels and external resources.

The initial profile assumes:
- the compiler and runtime implement the specified ownership and memory model;
- platform thread/scheduler primitives satisfy a narrow adapter contract;
- memory accesses by foreign code, devices and DMA are outside ordinary shared-memory guarantees unless represented by dedicated types and protocols;
- the hardware obeys the declared memory model, subject to documented processor errata and mitigations.

The initial profile does **not** promise that every arbitrary concurrent program terminates, is starvation-free, has no logical race, or is immune to OS/hardware failure. General deadlock freedom for unrestricted programs is not decidable. We must not repeat a blanket "no deadlocks are possible" claim without restricting the programming model or proving a specific protocol.

No general unsafe concurrency API is part of the safe profile. Any eventual FFI, raw pointer, volatile/device access or scheduler escape must be an explicit unsafe boundary with an audited contract. Safe callers cannot assume an unsafe implementation preserves the safe guarantees unless its contract is verified.

## 3. Core ownership and sharing rules

### 3.1 Values and access modes

Every value belongs to exactly one of these categories:

1. **Owned:** one task owns the mutable value. Ownership may be moved, not implicitly copied.
2. **Immutable shared:** many tasks may read the value; no task can mutate it after publication.
3. **Uniquely borrowed:** one task temporarily accesses an owned value while the owner is suspended from conflicting access. The borrow cannot outlive the owner or cross an incompatible suspension boundary.
4. **Synchronised shared:** mutable access is available only through a typed synchronisation object (initially a lock guard, later selected specialised primitives).
5. **Atomic scalar:** access occurs only through the atomic API, with an explicit memory order and restricted value types.

A value cannot be shared merely because its representation is pointer-sized or because a reference-counted pointer exists. The compiler derives or checks task-transfer and task-sharing eligibility structurally. The existing roadmap's Send/Sync direction is retained, but traits must be sealed/structural in the safe profile: user code cannot unsafely assert that an arbitrary type is shareable.

Proposed conceptual predicates:

- `Transfer(T)`: ownership of T can move to another task.
- `Share(T)`: immutable references to T may be held by multiple tasks.
- `SyncCell(T, P)`: mutable T is accessible only through protocol P.
- `Borrowed<'r, T>`: reference valid only within region 'r.

Pointers, mutable references, closures, captured environments, destructors and nested aggregate fields all participate in the derivation. A closure is transferable only if every captured value is transferable; it is shareable only if every capture is shareable and the closure has no hidden mutable state.

### 3.2 Task transfer

Spawning a task consumes its transferred arguments and closure environment. A moved value cannot be used by the parent afterwards. Borrowed values may cross a task boundary only where the task is statically scoped within the borrow and the child cannot outlive the borrow; the initial design should prefer move-only transfer and immutable shared borrows to reduce proof complexity.

No implicit detached task is permitted in the safe profile. Every task belongs to a lexical or resource owner scope and has an observable completion result.

### 3.3 Shared mutable state

There is no general shared mutable reference. Shared mutation requires one of:
- a `Locked<T, Rank, Invariant>` value accessed only through a non-copyable guard;
- a restricted atomic scalar;
- a later, separately specified primitive such as RCU or a verified concurrent collection.

The compiler rejects direct access to the protected payload outside its guard. The guard is affine/linear, cannot be duplicated or forgotten, and releases the lock on every normal or exceptional/trap exit. Guard lifetime is bounded to a synchronous critical section: a guard cannot be held across an `await`, task yield, blocking operation or callback into unknown code unless a specialised protocol explicitly proves this safe.

## 4. Structured concurrency and task lifecycle

### 4.1 Task scopes

The baseline construct is a structured task scope. Conceptually:

```text
scope {
    let a = spawn(work_a, moved_input_a);
    let b = spawn(work_b, moved_input_b);
    let ra = await a;
    let rb = await b;
    combine(ra, rb)
}
```

The syntax is illustrative, not a committed grammar.

A scope owns every child task created within it. The scope cannot finish while a child remains live. On ordinary exit, all children must have been joined. On failure or cancellation, the scope cancels remaining children, waits for their termination, runs cleanup and returns a typed aggregate outcome. No child may retain a borrow or resource whose owner has left scope.

Task handles are linear: joining, cancelling-and-joining, or transferring the handle consumes it. There is no silent handle drop that detaches work. An explicit supervisor construct may later permit long-lived services, but it must itself have a visible owner and shutdown protocol.

### 4.2 Cancellation

Cancellation is cooperative and delivered at specified cancellation points (at minimum, suspension and blocking boundaries). The compiler/runtime must guarantee:
- cancellation cannot interrupt a critical section while a protected invariant is temporarily broken;
- all live linear resources are either released or transferred through their declared cleanup protocol;
- cancellation does not skip required cleanup;
- a child cannot report completion while descendants it owns remain live;
- cancellation requests and completion are distinct states.

Destructors used during implicit unwind must be bounded, non-blocking and non-failing. Operations whose cleanup can fail must expose an explicit `close/finalize` result and cannot be silently hidden in a destructor. Shielded/non-cancellable regions, if ever added, require explicit bounded duration/work budgets and cannot be nested without a checked limit.

### 4.3 Failure and panic semantics

A child failure is an explicit typed result delivered to its owner. The default scope policy is fail-fast cancellation of siblings, followed by joining all children and aggregating cleanup failures without discarding the primary failure. Unhandled panic-like process termination is not the ordinary task-failure mechanism. Runtime traps remain distinct from recoverable task errors.

### 4.4 Async and blocking effects

`await` is a suspension effect. A function that may suspend cannot be called from a non-suspending context or while it holds a guard/borrow that the type system forbids across suspension. Blocking OS calls are a distinct effect and are not silently allowed on an async executor worker. The scheduler may move a task between worker threads only when its execution context and captured state permit it.

## 5. Channels and message passing

Channels are the preferred baseline for communication between independently scheduled tasks.

A channel has a payload type T that must satisfy `Transfer(T)`. Sending moves the value; receiving transfers ownership to the receiver. There is no implicit shared mutable payload. A sender cannot use the value after a successful send.

Every channel is bounded in the safe profile. Capacity and maximum message size are explicit resource parameters. An unbounded queue is excluded because it turns a producer/consumer imbalance into unbounded memory growth. A send has a typed outcome: delivered, closed, cancelled, or resource/deadline failure. A receive distinguishes message, closed-and-drained, cancelled and failure.

The design must settle:
- FIFO ordering guarantees (initial default: FIFO per channel);
- whether multi-producer ordering is defined by linearisation order;
- close semantics and which endpoint owns closure;
- whether send completion means enqueued or received (initial default: enqueued);
- backpressure behaviour when capacity is exhausted;
- fairness among blocked senders/receivers;
- cancellation races at the send/receive linearisation point;
- how channel buffers are accounted against task and heap budgets.

A successful send transfers ownership exactly once. Cancellation before linearisation retains ownership at the sender; cancellation after linearisation cannot retract a delivered message. This boundary must be observable and tested.

## 6. Locks and lock ordering

### 6.1 Typed lock guards

The existing design-map proposal `Locked<T, Spin>` is retained conceptually, but the initial user-space profile should not expose spin locks as a universal default. Blocking mutexes and scheduler-aware locks have different effects and contexts; the type must identify which one is being used.

A lock guard grants exclusive access to the payload and carries the lock's invariant. The guard is non-copyable, has a lexical lifetime, and cannot escape the critical section. Every exit path releases it. Reentrant locking is not supported in the baseline.

### 6.2 Lock ranks

Locks may declare a static rank. Acquiring a lock while holding one of equal or higher rank is rejected. This prevents statically visible lock-order cycles and self-deadlock for the ranked subset.

For two runtime-selected locks of the same rank, the API must provide an atomic ordered-acquisition operation with a canonical identity order. It must not expose "lock a, then lock b" as a safe alternative. Identity ordering must be stable, collision-safe and not forgeable by user code.

Waiting for a task, channel, timer or completion while holding a lock is rejected when the awaited operation may require code that acquires that lock. Initially, the safer rule is simpler: no `await` or potentially blocking operation while any ordinary lock guard is held.

### 6.3 Invariants and proof

A lock may carry a predicate describing the protected state. The predicate must hold whenever the lock is not held; a critical section must establish it again before guard release. Contracts and separation-logic-style ownership are the intended proof mechanism. Merely attaching a textual invariant is not evidence: the checker must discharge the obligation at the declared assurance level.

## 7. Atomics and memory model

The first safe atomic profile should be deliberately small:
- integer and boolean scalar atomics only;
- no atomic raw pointers or arbitrary aggregate values;
- explicit operations and memory-order arguments;
- a simple sequentially consistent baseline for initial correctness;
- relaxed/acquire/release operations introduced only with precise formal rules and litmus tests;
- compare-exchange returns an explicit success/failure result and expected-value update semantics.

Atomic APIs do not make an algorithm correct. They guarantee indivisible operations and the declared ordering only. Logical invariants (for example, a correct work-stealing queue) require contracts/proofs or a separately verified library. Users must not be encouraged to implement ad hoc lock-free data structures in the initial safe profile.

The compiler/backend must lower each atomic operation to target instructions or runtime helpers that satisfy the same memory model on every declared architecture. Tests must include weak-memory litmus cases, not only x86-64 execution.

## 8. Advanced concurrency primitives

These are not part of the minimum concurrency milestone and must not be implemented by copying kernel idioms without formal contracts.

- **RCU:** typed read-side region, non-escaping references, explicit publication and grace-period reclamation. Reclamation correctness must account for all participating execution contexts.
- **Sequence locks:** readers may observe retries; payload constraints and writer serialisation must be enforced. Not a generic substitute for locks.
- **Per-task/per-CPU state:** access tied to a scheduler/CPU pinning capability; migration invalidates the capability.
- **Volatile/device memory:** distinct type for MMIO/DMA; volatile access is not itself atomic or a memory barrier. Device ownership and cache-coherency protocols are explicit.
- **Wait-free/lock-free collections:** separate algorithmic proofs and progress guarantees; no "lock-free" label based solely on using atomics.

## 9. Execution contexts and platform adapter

The type/effect system tracks at least:
- `process`: may allocate and block subject to API contract;
- `async`: may suspend at declared points;
- `atomic`: cannot block, allocate without a bounded pre-reserved pool, or suspend;
- later platform profiles may add interrupt, NMI, per-CPU and device contexts.

The platform adapter owns thread creation/join, worker wake/sleep, monotonic deadlines, thread-local storage and low-level synchronisation. The Capstan runtime owns task identity, task state, structured scopes, cancellation, channel state, lock invariants, scheduling policy contracts and resource accounting. The adapter exposes typed outcomes, not pthread handles, Windows HANDLEs or OS error codes.

The scheduler contract must specify whether tasks are preemptive or cooperative, worker count, fairness assumptions, wakeup guarantees, priority policy, stack bounds, shutdown and failure behaviour. A safe program cannot assume eventual scheduling unless that fairness guarantee is explicitly part of the execution profile.

## 10. Resource and liveness model

Concurrency multiplies resource dimensions. Every runtime profile must bound or explicitly account for:
- total tasks and child tasks per scope;
- worker threads and per-task stack/continuation size;
- channel count, capacity and total buffered bytes;
- pending sends/receives and waiters;
- lock count and wait queues;
- task-local and shared heap allocations;
- scheduler queue size and cancellation/cleanup work;
- recursion, nested scopes and maximum task-tree depth.

Exceeding a budget returns a typed failure before partially publishing a task or message. Accounting updates are atomic with the operation they govern. The design must specify which resources are reserved at spawn/send time and when they are released.

Deadlock and starvation claims require explicit scope:
- static lock ranks prevent cycles in the statically ranked lock subset;
- structured scopes prevent orphaned tasks but do not by themselves prevent parent/child dependency cycles;
- bounded protocol model checking can prove absence of deadlock for a finite state model and stated bounds;
- contracts can prove selected progress obligations under scheduler fairness and environment-response assumptions;
- arbitrary unbounded programs are not promised deadlock-free or starvation-free.

## 11. Formal model and proof obligations

The concurrency core requires a small formal model before implementation. It should define:
- typed heap and ownership permissions;
- task states and parent/child tree;
- regions, borrows and lifetime constraints;
- channel states, message ownership and linearisation points;
- lock states, guard permissions and lock ranks;
- atomic events and the memory-order relation;
- cancellation, failure and cleanup transitions;
- resource counters and deterministic exhaustion outcomes.

Minimum theorems for the safe subset:
1. **Preservation:** every well-typed transition preserves typing, ownership and heap invariants.
2. **Progress (qualified):** a non-blocked, non-terminated task can take a machine step, or yields a specified typed trap; this does not imply global scheduling fairness.
3. **No data races:** conflicting non-atomic accesses to the same location are ordered by exclusive ownership/borrow, immutable sharing, or a synchronisation protocol.
4. **No dangling cross-task references:** every task-held reference is valid for the task's entire possible lifetime, including cancellation and delayed scheduling.
5. **Linear resource conservation:** task handles, guards, channel endpoints and external linear resources are consumed exactly once or remain owned.
6. **Structured termination:** scope completion implies every child and descendant is terminated and its cleanup protocol has completed.
7. **Channel ownership conservation:** each sent message is owned by exactly one endpoint/buffer/receiver across every transition, including cancellation.
8. **Lock invariant preservation:** every guard-release transition re-establishes the declared invariant.
9. **Atomic refinement:** each backend atomic operation refines the abstract memory-model event and ordering.

These theorems first apply to the abstract machine. An implementation claim additionally requires a proved or validated correspondence from compiler/type checker/runtime/backend to that model. A proof about the model alone must never be presented as proof of the shipped implementation.

## 12. Implementation and evidence sequence

1. **Research comparison:** compare Rust ownership/Send/Sync, Pony reference capabilities, Swift actor isolation, Koka/effect systems, structured concurrency designs, and Iris/VeriFast separation logic. Identify exactly which guarantees Capstan adds and which trade-offs it makes.
2. **Core calculus:** specify ownership transfer, immutable sharing, borrows, task scopes and linear handles. No OS threads required.
3. **Type checker prototype:** positive/negative programs for transfer/share, closure captures, borrows, task lifetime, lock guards and suspension.
4. **Deterministic task-machine model:** implement a single-threaded interleaving scheduler first. It gives reproducible traces and a reference semantics independent of host scheduling.
5. **Channels and cancellation:** bounded channels, ownership conservation, cancellation linearisation and scope cleanup.
6. **Locks and atomics:** ranked locks and SC atomics first; then memory-order refinement and architecture litmus suite.
7. **Formal proofs:** preservation, no-race, lifetime safety, linear conservation and scope termination for the calculus.
8. **Native scheduler adapter:** only after semantics and tests are stable; run differential tests against the deterministic machine.
9. **Advanced profiles:** RCU, device/interrupt contexts, per-CPU data and lock-free collections only with independent specifications and proofs.

The deterministic interleaving machine should be the oracle for tests and model checking. Native parallel execution is an implementation of the same task semantics, not a separate language semantics.

## 13. Required conformance and adversarial tests

The test suite must include:
- compile rejection for moving a value twice, sharing non-shareable state, aliasing mutable access, and returning a borrow past its owner;
- compile rejection for closures that capture non-transferable/non-shareable values;
- compile rejection for awaiting, yielding or blocking while holding a prohibited guard;
- compile rejection for lock rank inversions and unprotected shared mutation;
- compile rejection for unjoined/detached tasks and owner destruction with live descendants;
- compile rejection for duplicate close/release and forgotten linear resources;
- runtime tests for cancellation before/after channel send linearisation, close races, child failure, nested scope unwind and cleanup failure;
- exact and one-over resource-budget tests for every concurrency resource;
- deterministic replay of scheduler traces and exhaustive interleavings for small bounded examples;
- weak-memory litmus tests for each supported atomic ordering and architecture;
- stress, fuzz, fault-injection and sanitizer tests for scheduler, channel, lock and cancellation implementations;
- mutation tests that weaken a type rule or proof obligation and demonstrate that a negative test or theorem fails.

A test pass is evidence for tested cases, not a universal proof.

## 14. Explicit vulnerability-class targets

The safe profile is intended to eliminate these classes by construction, once the relevant gates are met:

| Class / failure mode | Primary mechanism | Residual qualification |
|---|---|---|
| Data races (CWE-362) | Ownership, immutable sharing, typed synchronisation, no raw shared mutable references | Unsafe/foreign/device access excluded unless separately verified |
| Use-after-free across tasks (CWE-416) | Borrow/lifetime checking, task-scoped ownership, join-before-owner-destruction | Compiler/runtime refinement required |
| Double free/release (CWE-415) | Linear resource types | External APIs must obey their verified ownership contract |
| Improper lock release / lock misuse (CWE-667) | Non-copyable guard with scope-bound release | Does not prove the protected algorithm is logically correct |
| Callback/task teardown races | Structured concurrency and owner-bound task scopes | OS callback/interrupt registration requires a platform-specific contract |
| ABBA/self-deadlock in ranked locks | Static lock ranks and canonical multi-lock acquisition | Only the covered lock graph; arbitrary waits and protocol cycles remain |
| Lost/duplicated message ownership | Linear channel endpoints and explicit send linearisation | Delivery semantics and cancellation are part of the verified machine |
| Unbounded queue memory exhaustion | Bounded channels and aggregate resource budgets | Other allocations and external resources need their own budgets |
| Sleep/block in atomic context | Context/effect checking | Target adapter must correctly classify operations |
| Unsafe cancellation cleanup | Cooperative cancellation points and linear cleanup | Non-cooperative foreign code can violate assumptions |

The following are not claimed eliminated by this proposal alone: logical races, starvation, arbitrary deadlock, priority inversion, denial of service from hostile peers, side channels, hardware memory-order defects, scheduler/OS bugs, and errors in protocol specifications. These need additional mechanisms, explicit assumptions and separate evidence.

## 15. Decision points for review

Before implementation, reviewers must settle:
1. Whether safe tasks are initially green-thread/fibre tasks, OS-thread tasks, or a runtime-independent task abstraction with both implementations.
2. Whether the baseline scheduler is cooperative, preemptive, or a deterministic semantic machine plus native implementation.
3. Whether scoped borrows may cross task boundaries in v0.7 or are deferred.
4. The exact cancellation and child-failure aggregation semantics.
5. Channel multi-producer ordering and fairness.
6. Lock rank syntax and dynamic identity ordering.
7. Which atomic operations and memory orders are in the first profile.
8. Whether shared ownership is available in v0.7, and if so which cycle/weak-reference rules apply.

Default recommendation: begin with a deterministic task machine, move-only task transfer, immutable shared values, bounded FIFO channels, structured scopes, cooperative cancellation, and no user-defined lock-free data structures. Add ranked locks and SC scalar atomics after the ownership/channel core is validated. This is a narrower first release with a much stronger assurance story than exposing general threads and mutexes immediately.

## 16. Non-claims

This document is a design proposal. It does not claim that Capstan currently supports concurrency, that any theorem has been proved, that the current runtime is race-free, or that all vulnerabilities can be eliminated. It establishes a target for safe-language guarantees and the evidence needed before making those claims.
