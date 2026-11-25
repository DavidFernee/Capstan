# Multi-waiter channel semantics: design and verification plan

**Status:** design specification; not executable evidence.  
**Scope:** bounded FIFO channels with multiple producers and consumers, FIFO wait queues, cancellation, close, and wakeup reservations.  
**Prerequisite:** the single-waiter blocking model must pass exact-head CI before this design is implemented or claimed as verified.

## 1. Objective

Generalise the single-producer/single-consumer reference machine without weakening these distinctions:

- an operation may be invalid, valid-but-disabled, or enabled;
- blocking is a scheduler state, not an operation failure;
- a wakeup makes a task eligible to run; it does not execute the continuation;
- message ownership and wait registration change at explicit linearisation points;
- cancellation, close, and wakeup races have one deterministic winner;
- queue order is specified, not an artefact of container iteration.

The first implementation target is a finite bounded model. It is not a claim about arbitrary scheduler fairness or unbounded deadlock freedom.

## 2. State model

Each channel contains:

- capacity and committed FIFO message queue;
- closed flag;
- FIFO receiver wait queue;
- FIFO sender wait queue;
- optional direct-handoff and capacity reservation records;
- monotonically increasing wait-ticket counter;
- monotonically increasing transition counter.

Each task contains:

- lifecycle status: RUNNABLE, BLOCKED, DONE, CANCELLED, or FAILED;
- at most one active wait registration;
- wait kind and channel identity when blocked;
- wait ticket;
- pending operation/result;
- ownership references for uncommitted messages.

Each wait registration contains task identity, wait kind (RECEIVE or SEND_CAPACITY), unique ticket, operation identity, and—if it is a sender—the identity of its still sender-owned payload.

A task may have at most one active wait registration globally. A registration must appear in exactly one queue and agree with the task's blocked state. Queue entries are never inferred from task status alone.

## 3. Queue discipline

FIFO is defined by successful wait-registration order, not task creation order, task ID, hash order, or scheduler run order.

1. Assign the next ticket only when the operation actually blocks.
2. Append exactly one registration.
3. Remove only the head for ordinary service.
4. Remove a cancelled or invalidated waiter by its exact ticket; do not reorder surviving entries.
5. Never reuse a ticket within one model execution.
6. Reject duplicate registration and stale removal without mutating state.

A bounded implementation must state the maximum number of tasks and queue entries. Queue overflow is an explicit model-bound failure, not silent truncation or wraparound.

## 4. Linearisation rules

### 4.1 Receive

For a runnable consumer:

- If a committed message exists, dequeue the oldest message and transfer ownership to the consumer.
- If the queue is empty and the channel is closed, complete with EOF.
- If the queue is empty and open, append a receiver wait, mark the task blocked, and return a blocked transition.

A receive that blocks does not consume a future message. It records a pending receive operation.

### 4.2 Send

For a runnable producer with a producer-owned payload:

- If the channel is closed, complete with the closed-channel result; do not enqueue the payload.
- If a receiver is waiting and no committed message precedes it, select the oldest receiver and atomically transfer the payload into a receiver-delivery reservation. Remove that receiver's wait and make it runnable. The sender's send operation is committed at this transition.
- Otherwise, if committed queue capacity is available and no older sender is entitled to a reserved slot, append the payload to the channel queue and transfer ownership to the channel.
- Otherwise append a sender-capacity wait and mark the producer blocked. The payload remains producer-owned until its send is committed or cancelled.

A later sender must not bypass an older sender merely because the later sender happens to be scheduled first.

### 4.3 Dequeue and sender service

When a consumer dequeues a committed message and a sender is waiting, service the oldest sender in the same atomic transition that releases capacity.

The selected sender's payload is committed to the newly available queue slot as part of this transition; ownership changes from sender to channel, the sender wait is removed, and the sender becomes runnable with a completed-send result.

This reservation rule prevents barging between capacity release and sender resumption. The sender continuation still does not run as part of the wakeup.

An alternative design—waking a sender without reserving capacity—is excluded from the FIFO profile because it permits barging and requires a more complicated fairness contract.

### 4.4 Close

Close is a single atomic transition:

- mark the channel closed;
- wake blocked receivers in FIFO order with a pending receive result that resolves to EOF, except where a committed message or delivery reservation is available to them;
- wake blocked senders in FIFO order with a closed-channel result;
- remove every affected wait registration exactly once;
- preserve already committed messages so they remain drainable;
- leave uncommitted sender-owned payloads sender-owned until the sender resumes and observes the closed result or cancellation disposes of them under the ownership policy.

The close transition does not discard committed messages. Receivers drain committed messages in FIFO order and observe EOF only after no committed message or delivery reservation remains.

A receiver already assigned a direct-delivery reservation is governed by the reservation's earlier linearisation point: close cannot revoke an already committed send.

### 4.5 Cancellation

Cancellation competes with wakeup at a single linearisation point.

- If cancellation removes a wait registration first, the task becomes terminal and cannot be selected by a later wakeup.
- If send, dequeue, or close removes the wait and installs a delivery or capacity reservation first, cancellation observes a runnable task with a committed operation. It may cancel subsequent task execution, but cannot roll back the committed channel operation.
- Cancellation of a blocked sender before send commitment disposes of or returns its still sender-owned payload according to the task cancellation contract.
- Cancellation after send commitment does not retract the channel-owned or receiver-reserved message.
- A cancelled task is never present in a wait queue and never owns a live wait ticket.

The model must test both serialisations of each race. It must not model a race as two independent booleans that can both win.

## 5. Required invariants

Check invariants after every accepted transition and assert rejected transitions are state-preserving.

### Task / wait consistency

1. A task is blocked iff it has exactly one active wait registration.
2. Every active registration appears exactly once in exactly one matching queue.
3. No terminal task has a wait registration.
4. No runnable task remains queued.
5. No task has two active waits, including across different channels.

### FIFO and ticket integrity

6. Tickets are unique and strictly increasing in registration order.
7. Queue order is ticket order after removing cancelled entries.
8. Only the head eligible waiter may be selected.
9. A reservation is associated with exactly one selected waiter and cannot be consumed twice.
10. Queue and ticket bounds fail closed without wraparound.

### Message ownership and capacity

11. Every live message has exactly one owner: producer, channel queue, receiver reservation, or consumer.
12. A message cannot appear twice in a queue or in both a queue and reservation.
13. Committed queue length never exceeds capacity.
14. Reserved capacity plus committed queue length never exceeds capacity.
15. A sender blocked for capacity retains ownership of its uncommitted payload.
16. A committed send cannot be cancelled retroactively.
17. Close preserves all messages whose send linearised before close.

### Close and terminal behaviour

18. No new send commits after close.
19. A receiver reports EOF only after all committed messages and delivery reservations are drained.
20. Close removes or resolves every blocked wait exactly once.
21. No stale wakeup can make a terminal task runnable.

## 6. Bounded state exploration

The first model-checking instance should use small but nontrivial bounds:

- 3 producers and 3 consumers;
- channel capacities 0, 1, and 2 as separate parameterised cases;
- at most 2 messages per producer;
- bounded operation traces with explicit scheduler choices;
- one close operation and cancellation of any task;
- bounded wait-ticket space with overflow detection.

Explore all enabled task choices and all relevant serialisations of send, receive, close, and cancel. Preserve task and message identities in canonical states; counts alone are insufficient because ownership and FIFO order are identity-sensitive.

The state key must include task statuses and pending operations; exact ordered message identities; exact ordered wait queues and tickets (or a proven canonical renumbering); reservations; channel closed state; ownership map; and all semantically relevant result values.

A state cap is a failed or incomplete exploration, never a pass. Counterexamples should be shortest by transition count and print the complete state before and after every transition.

## 7. Partial-order reduction

Do not introduce partial-order reduction in the first implementation.

After exhaustive small-state exploration is stable, consider reducing only transitions proven independent. Two operations are not independent if they access the same channel queue or wait queue; affect the same task or message; compete for the same capacity slot or receiver reservation; include close or cancellation of a task/channel touched by the other operation; or can change FIFO selection order.

Every reduction rule needs a proof obligation that the reduced graph preserves the safety properties and relevant liveness counterexamples. A reduction that merely makes the test suite faster is insufficient.

## 8. Safety and liveness claims

Safety properties are unconditional within the model bounds: no duplicate ownership, queue overflow, stale wake, FIFO bypass, post-close commit, or capacity violation.

Liveness is conditional. FIFO waiter order alone does not prove eventual execution. A task made runnable can still starve if the scheduler never selects it. Any eventual-delivery claim must state the scheduler assumption (for example, weak fairness for continuously runnable tasks), bounded environmental assumptions, and whether cancellation may intervene.

Distinguish:

- **blocked:** a task has a registered wait for a condition not currently satisfied;
- **quiescent:** no task is runnable, but external input, timer, or device activity may still enable progress;
- **deadlocked:** no internal transition or admitted environmental event can make progress;
- **starved:** a task remains enabled or runnable but is not selected under the observed schedule.

A wait-for cycle is evidence only for dependencies represented in the graph. It is not by itself proof of global deadlock if external events, timers, or unmodelled resources can release a wait.

## 9. Acceptance gates

**MW1 — representation**
- Stable task/message identities, explicit wait tickets, ordered queues, reservations, and ownership map.
- Invariants reject duplicate, missing, stale, and mismatched wait registrations.

**MW2 — FIFO service**
- Multiple receivers and senders.
- FIFO selection under adversarial scheduler order.
- No sender or receiver barging.
- Direct handoff and buffered queue cases distinguished.

**MW3 — cancellation and close**
- Both serialisations of cancellation versus wakeup.
- Close with queued messages, receiver waiters, sender waiters, and reservations.
- Exact ownership accounting for every outcome.

**MW4 — exhaustive bounded exploration**
- Full state key, state cap fail-closed, shortest counterexamples.
- Exhaustive bounds and transition counts recorded in test output.
- No unqualified liveness claim.

**MW5 — refinement**
- Map each abstract transition to the eventual runtime operation and identify the concrete linearisation point.
- Prove or test preservation of FIFO order, ownership, capacity, cancellation, and close semantics.
- Keep the model explicitly abstract until this mapping is complete.

## 10. Non-claims

This design does not establish that Capstan's current runtime implements these semantics, that arbitrary programs are deadlock-free, that every runnable task is eventually scheduled, or that all concurrency vulnerabilities are eliminated. Those claims require implementation evidence, refinement, and separately stated scheduler/environment assumptions.
