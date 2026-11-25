# Transition-graph refinement: canonical states and enabled actions

**Status:** implementation design for the next wait-for/transition-graph increment. The graph-level prototype exists; this document specifies the bridge to executable concurrency states.  
**Prerequisite:** exact-head CI for PR #302 remains mandatory before merge.

## 1. Objective

Replace hand-authored integer graph nodes with graph nodes derived from complete concurrency reference-machine states. Edges must be generated only by actions whose preconditions hold in the source state and whose transition function produces the destination state.

The graph is a derived view of the transition system. It is not an independent scheduler semantics and must not invent transitions from wait-for edges.

## 2. Canonical state identity

A canonical state key must include every field that can affect:
- whether an action is enabled;
- the resulting state of an action;
- task terminality or required cleanup;
- message/resource ownership;
- wait registration and waiter ordering;
- cancellation, close, and pending wakeup behaviour;
- environment assumptions and pending external events.

At minimum, the blocking-channel models require task status, task wait kind, wait target, channel identity, message identity and owner, queue occupancy/order, closed state, producer/consumer role state, and all cancellation or wakeup reservations.

The key must be a collision-free canonical encoding within the finite model bounds. A hash may index the visited-state table, but equality must compare the full canonical encoding. Hash equality is never state equality.

Canonicalisation may reorder only semantically unordered fields. FIFO queues, ticket order, ownership ledgers, and action-relevant identities must retain their order and identity.

## 3. Action relation

Define one pure transition function per action:

`step(state, action) -> (accepted, next_state, rejection_reason)`

A rejected action must return a state byte-for-byte/canonically equal to its input. An accepted action must satisfy all state invariants.

The enabled-action enumerator must enumerate the finite action alphabet and retain exactly those actions for which `step` accepts. It must not infer enabledness from a wait-for graph, task role, or expected future provider.

Each graph edge records:
- canonical source-state key;
- action identity and parameters;
- canonical destination-state key;
- optional event class (internal, cancellation, close, environment);
- transition witness sufficient to replay the action.

## 4. Breadth-first exploration

Use a FIFO frontier. Insert the canonical initial state once. For each dequeued state:
1. validate invariants;
2. enumerate all enabled actions;
3. if the state is nonterminal and the enabled set is empty, retain it as a reachable deadlock witness;
4. apply every enabled action through the pure transition function;
5. validate each successor;
6. canonicalise and compare the full key against visited states;
7. retain the first predecessor/action pair for shortest witness reconstruction;
8. stop with `BOUNDED_UNKNOWN` if a state, edge, or transition budget is reached before the frontier is exhausted.

Do not stop at the first deadlock if the desired result is a complete graph inventory. A fast diagnostic mode may stop early, but its result must say exploration was partial and must not be presented as a complete graph.

## 5. Classification cross-check

For every reachable state, independently compute:
- direct enabled-action count;
- wait-for classifier result;
- graph out-degree;
- terminal/cleanup status;
- environment availability classification.

Required consistency checks:
- nonterminal state with a nonempty enabled-action set must not be classified as a closed-world deadlock;
- a reachable nonterminal graph sink must have zero enabled internal actions;
- an environment-enabled wait must be represented by an explicit admitted environment transition or remain classified as environment wait, never silently converted to closed-world deadlock;
- terminal states must not have ordinary continuation actions unless the model explicitly includes cleanup transitions;
- graph and direct-state classifiers must agree on deadlock versus progress for every fully explored closed-world state.

A mismatch is a model defect and must fail verification. Do not resolve disagreement by weakening the more conservative classifier.

## 6. Witness format

A replayable witness is a sequence of canonical state keys and action records from the initial state to the sink. The final record includes:
- nonterminal task identities;
- typed active waits;
- channel queue and message ownership;
- resource ownership and reservations;
- pending cancellation/close state;
- the complete enabled-action enumeration (empty for a closed-world sink);
- environment assumptions;
- graph exploration completeness and configured bounds.

Replaying each action from the preceding state must reproduce the next canonical state exactly. The final state must revalidate and have no enabled internal action.

## 7. Required adversarial tests

1. A wait-for cycle with an enabled action leaving the cycle.
2. A reachable nonterminal sink with a shortest replayable trace.
3. An unreachable sink that must not contaminate reachability results.
4. Two distinct states with equal hashes but different canonical encodings.
5. Two identical canonical states reached by different schedules and deduplicated.
6. A rejected action that leaves every state field unchanged.
7. A wakeup that is enabled only after a capacity-release transition.
8. Cancellation and wakeup in both orders, with exactly one winner.
9. A live environment event that is explicit in the transition relation.
10. State, edge, and action-enumeration limits, each failing closed.
11. A deliberate mismatch between graph out-degree and direct enabled-action count, which must fail.
12. A witness whose replay is corrupted, which must be rejected.

## 8. Acceptance boundary

The bridge is complete only when graph nodes are actual canonical model states, edges are generated by the model's own enabled transition functions, every edge replays, all state invariants hold, and the graph/direct classifier cross-check passes over the complete declared finite bounds.

Even then, the result is bounded safety evidence for that model. It does not prove scheduler fairness, starvation freedom, unbounded deadlock freedom, native runtime correctness, or compiler/runtime refinement.
## 9. Completeness rule for deadlock witnesses

A discovered reachable sink is a witness, not permission to stop claiming complete exploration. The explorer must continue traversing every other reachable branch. If any configured state/edge/action budget is exhausted before the frontier is empty, the overall result is `BOUNDED_UNKNOWN`, even if a candidate sink was already observed; the partial witness may be retained for diagnostics but must not be reported as a complete classification. Only after the frontier is exhausted may the explorer return a complete deadlock result with its first breadth-first sink witness.
## 10. First model-derived graph slice

An executable bridge prototype now exists in `verification/concurrency_generated_graph.cap` and is registered in `tests/run.sh`. Unlike the illustrative graph explorer, it stores bounded channel states, enumerates the finite action alphabet (receive, close, cancel), calls the model transition function to determine enabledness and produce successors, validates each successor, and performs BFS over collision-free mixed-radix state keys. The explored slice covers an empty open channel, receive suspension, close/wakeup, EOF observation and cancellation. It checks rejected-action identity, wake-before-EOF ordering, cancellation cleanup, reachable-state count and fail-closed state limits.

This is a separately encoded, deliberately small model of the empty-channel lifecycle; it is not yet a direct adapter over the full `CBState` implementation, and it does not include message payload ownership, channel capacity, producer transitions or the capacity-blocked sender model. The canonical key is collision-free only for the explicitly bounded field domains documented in the source. The BFS currently returns a coarse progress/deadlock/terminal classification and does not yet emit predecessor-linked replayable traces or cross-check every state against the full wait-for classifier. Those are the next refinement obligations, not established properties.

## 11. Capacity-blocked sender graph slice

A second generated explorer is now present in `verification/concurrency_generated_capacity_graph.cap`, registered in `tests/run.sh`. It models a capacity-one FIFO with a queued first message and a producer-owned second message. Its action alphabet includes the full-channel send (which is an enabled blocking operation), dequeue and atomic capacity-wait removal, producer resumption and commit, consumer ownership/release, cancellation, and explicit consumer completion.

The graph's mixed-radix key includes producer status and wait registration, consumer status, queue occupancy, both message owners, and channel closure. Every generated successor is checked against the model invariants. The bounded tests cover the blocked-send ownership rule, wakeup without premature commit, resumed commit, cancellation/stale-action rejection, second-message receipt, terminal completion preconditions, and fail-closed state limits.

This remains an independently encoded model slice mirroring the capacity-send reference semantics, not a shared transition implementation with `concurrency_blocking_send.cap`. It does not yet establish multi-producer fairness, multi-consumer ordering, close-versus-send races, or production runtime correctness. A direct common transition kernel and replayable graph traces remain required before this is considered a refinement bridge.
