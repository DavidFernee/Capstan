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
