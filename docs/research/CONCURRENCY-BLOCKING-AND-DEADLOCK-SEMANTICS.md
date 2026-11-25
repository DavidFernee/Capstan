# Blocking, wakeup and deadlock semantics for Capstan concurrency

**Status:** research specification; bounded single-waiter reference-model code is present. The earlier blocking-receive failures were traced to test fixtures that removed the producer-owned message before invoking send; those fixtures have been corrected. Exact-head CI for the corrected branch remains pending. The general scheduler and liveness claims remain unimplemented and unproven.  
**Scope:** the next extension of the bounded task/channel reference machine.  
**Prerequisites:** `CONCURRENCY-PROTOCOL-AUTOMATA.md`, `CONCURRENCY-GUARANTEE-CALCULUS.md`, and the bounded reference machine. The follow-on multi-waiter design is specified separately in `CONCURRENCY-MULTI-WAITER-SEMANTICS.md`.

## 1. Why this increment is necessary

The current reference machine treats a receive with an empty channel as a rejected transition. That is appropriate for an operation that violates its protocol, but it does not model the normal behaviour of a concurrent receive: the operation is valid, cannot complete yet, and suspends the calling task until a matching event occurs.

A scheduler model that omits suspension and wakeup cannot establish meaningful claims about blocking, deadlock, cancellation responsiveness, or progress. It can validate a sequentially enabled handshake, but it cannot yet represent all legal interleavings of independent producer and consumer instruction streams.

The distinction is semantic, not merely an implementation detail:

- **Invalid:** the operation is forbidden by the protocol or caller's authority.
- **Disabled:** the operation is valid in principle but its enabling condition is currently false.
- **Blocked:** the task has registered a wait for a named enabling condition.
- **Runnable:** the condition has become true and the task may be scheduled.
- **Completed:** the operation has linearised and its result is available.
- **Deadlocked:** the global state has no permitted transition that can make progress or complete required cleanup, under the stated environment assumptions.

A disabled operation must not mutate state. A block operation must atomically register the wait and relinquish execution. A wakeup must not itself transfer message ownership; ownership changes at the operation's documented linearisation point.

## 2. Product-state extension

Extend each task with an execution state distinct from its lifecycle outcome:

`NEW | RUNNABLE | BLOCKED | DONE | CANCELLED | FAILED`

A blocked task additionally carries a typed wait reason, for example:

- receive from channel (c), waiting for a message or terminal closure;
- send to channel (c), waiting for capacity or terminal closure;
- join child (t), waiting for its terminal outcome;
- resource admission, waiting for a resource-release event;
- timer or external event, only where the runtime explicitly supports such an event source.

Wait records must be owned by the task and registered with the awaited object. They must be removable exactly once. The model must make stale waiter entries and duplicate wakeups unrepresentable or detectably invalid.

The scheduler state must include:
- runnable task identities;
- blocked task identities and typed wait records;
- channel queue occupancy and closure;
- waiter ordering policy;
- pending cancellation requests;
- resource reservations for wakeup and cleanup;
- event sources capable of making progress.

The initial implementation should remain bounded and deterministic: fixed task count, fixed channel count, finite message types, bounded queues and a finite transition budget.

## 3. Blocking receive and send

A receive on an open, empty channel is not an error. It produces a blocked task state and a registered receive waiter, without changing message ownership or queue accounting.

When a message is committed to the channel, the channel's linearisation transition must atomically:
1. reserve the receiving task's wakeup obligation;
2. commit the message to channel ownership or directly to a selected receiver under a separately specified rendezvous rule;
3. remove exactly one eligible waiter;
4. make that task runnable;
5. record the wakeup cause.

The receiving task performs the receive operation only when scheduled again. If the design uses direct handoff, the ownership transfer and wakeup must be one indivisible abstract transition; there must be no intermediate state in which the message has no owner or two owners.

A send on a full bounded channel follows the symmetric rule: it blocks with a typed capacity wait. A dequeue may make one sender runnable. Queue capacity and waiter reservations must be updated atomically.

Do not silently choose between FIFO waiter queues, unspecified wake order, work stealing, or barging. The first reference model should state one deterministic policy. Alternative policies can then be explored against the same safety invariants.

## 4. Closure and cancellation

Channel closure must wake all waiters whose operations are resolved by closure:
- blocked receivers wake and observe end-of-stream if no committed message remains;
- blocked senders wake and observe a closed-channel failure;
- already committed messages remain drainable unless the channel's declared disposal policy says otherwise.

Cancellation of a blocked task must remove its waiter registration exactly once, release any reservations owned by that wait, and terminalise the task through its declared cleanup path. A concurrent wakeup and cancellation must have a single winner at a linearisation point. The losing event must be harmless and idempotent; it must not duplicate ownership, wake a terminal task, or leak a reservation.

The implementation must test both event orders:
- cancellation wins before wakeup;
- wakeup wins before cancellation is observed;
- cancellation and closure race;
- message arrival and cancellation race;
- repeated cancellation requests.

Cooperative cancellation does not imply arbitrary instruction preemption. Cancellation points and non-cancellable cleanup regions must be explicit.

## 5. Deadlock is not the same as temporary quiescence

A state with no currently runnable tasks is not automatically deadlocked. It may be waiting for an external event, timer, I/O completion, or another scheduler-managed source.

Define a wait-for graph with typed edges:
- task-to-channel for receive/send waits;
- task-to-task for joins;
- task-to-resource for admission waits;
- event-source-to-task for possible wakeups.

For a closed, finite model with no external event sources, a quiescent state in which tasks remain blocked and no transition can enable them is a deadlock candidate. For models with external events, report **environment-dependent quiescence**, not deadlock, unless the environment contract proves the event cannot occur.

Deadlock detection must account for resource cycles and channel dependencies, not just graph cycles. A cycle is a useful witness but is not by itself a complete proof when alternative enabling transitions exist.

Report distinct outcomes:
- normal terminal completion;
- failure terminal completion;
- cancellation terminal completion;
- bounded-step exhaustion;
- resource-admission refusal;
- deadlock witness;
- environment-dependent quiescence;
- state-space truncation.

Truncation or an unknown environment outcome must never be reported as deadlock freedom.

## 6. Safety and liveness properties

The first implementation should prove or exhaustively check safety properties over its finite bounds:

1. Every task is in exactly one execution state.
2. Every blocked task has exactly one live wait registration.
3. Every wait registration refers to a live channel, task or declared event source.
4. A terminal task has no wait registration and cannot be woken.
5. Every message has exactly one owner.
6. Queue count and byte accounting agree with message ownership.
7. A wakeup reservation is consumed or released exactly once.
8. Cancellation/wakeup races cannot duplicate or lose a message.
9. Closing a channel resolves all channel waiters according to the close contract.
10. Scope completion requires no runnable or blocked descendants, no live waiters, no unconsumed join handles and no live resources.

Liveness claims require additional assumptions and separate arguments:

- **Eventual wakeup:** an enabling event occurs and the scheduler eventually runs the awakened task.
- **Starvation freedom:** continuously enabled tasks are not postponed forever under the stated scheduler fairness policy.
- **Deadlock freedom:** every reachable nonterminal state has a progress path, under the declared closed-world/environment assumptions.
- **Cancellation responsiveness:** a cancellation request reaches a cancellation point within a stated bound.

Do not infer any liveness property from finite safety exploration alone. State the fairness model (for example weak fairness or strong fairness) and identify which transitions it applies to.

## 7. Model-checking strategy

Extend the breadth-first explorer to enumerate scheduler actions, not only successful application operations. Preserve shortest counterexample traces.

The model must include:
- block and register-wait transitions;
- event arrival and wakeup transitions;
- close and cancellation transitions;
- waiter removal and reservation release;
- terminal and deadlock classification.

State deduplication must include every semantic field, including waiter identities/order, blocked reasons, pending events, cancellation state and all resource reservations. Hashing may accelerate lookup but equality must compare the complete state; hash equality is never state equality.

The state cap must fail closed. Report the explored-state count and whether the graph was complete. Do not use partial-order reduction until an independence relation accounts for shared channels, wait queues, cancellation, resource ledgers and wakeup effects. Two operations on different tasks are not independent merely because their actor IDs differ.

The first conformance scenarios should include:
1. consumer blocks before producer sends, then wakes and receives;
2. producer blocks on a full channel, then wakes after a receive;
3. channel closes with blocked receivers;
4. channel closes with blocked senders;
5. cancellation removes a blocked receiver;
6. cancellation races with message arrival;
7. two receivers compete for one message;
8. two senders compete for one free slot;
9. a join cycle is detected as a deadlock witness;
10. an external event wait is classified as environment-dependent quiescence.

## 8. Research questions

The implementation should be informed by the concurrency literature rather than assuming a scheduler policy is novel. In particular, investigate:

- compositional deadlock analysis for session-typed and structured-concurrency systems;
- wait-for graphs for mixed channel, join and resource dependencies;
- fairness assumptions required by liveness proofs;
- cancellation safety for blocked operations and async task state machines;
- linearisation and memory-order requirements for wakeup queues;
- sound partial-order reduction with dependent wakeup and cancellation transitions;
- bounded model checking versus inductive invariants for parameterised task/channel systems.

A claimed research contribution must be stated as a precise problem, compared with prior methods, and supported by proof or reproducible evaluation.

## 9. Initial implementation status\n\nThe initial C1 slices are implemented in `verification/concurrency_blocking.cap` and `verification/concurrency_blocking_send.cap`, both registered in `tests/run.sh`. They cover a single blocked receiver and a single blocked sender, atomic wait-registration removal and wakeup on message arrival or capacity release, resumed operations, close/EOF wakeup, draining a committed message after close, cancellation of blocked tasks, stale-wakeup prevention, and rejection of duplicate registrations. The models deliberately keep one producer, one consumer, at most two message identities and a capacity-one channel; they do not yet implement multiple waiters, a native scheduler, wait-for graph analysis, or liveness proofs.\n\nThe implementation is an abstract reference machine. Its test registration is not evidence that the suite has passed; exact-head CI remains the acceptance oracle.\n\n## 10. Acceptance gates

**Gate A — semantics:** document the task execution-state machine, wait reasons, wakeup winner rules, close semantics and scheduler policy.

**Gate B — reference model:** implement one channel, one producer, one consumer and one message with block/wakeup, including all interleavings and cancellation races.

**Gate C — exhaustive finite checks:** demonstrate complete state exploration within declared bounds, invariant preservation, and correct classification of deadlock versus external quiescence.

**Gate D — generalisation:** add multiple waiters, multiple messages, bounded sender/receiver queues and deterministic waiter selection.

**Gate E — source/runtime bridge:** connect the abstract transitions to typed source operations, then prove or validate the compiler/runtime refinement through lowering and native execution.

**Gate F — assurance:** add adversarial tests, fuzz-generated schedules, sanitizer coverage and regression fixtures. Promote no liveness guarantee into the safe profile until its assumptions and evidence are explicit.

## 11. Explicit non-claims

This document does not establish deadlock freedom, starvation freedom, bounded cancellation latency, fairness, weak-memory correctness or correctness of a native scheduler. It defines the next research and implementation target. The current reference machine remains a bounded sequentially enabled protocol model.
