# Wait-for analysis and deadlock classification

**Status:** research specification plus a bounded executable two-task classifier for JOIN, channel-message, channel-capacity, resource-availability and external EVENT waits in `verification/concurrency_wait_for.cap`; exact-head CI is pending.  
**Scope:** finite task, channel, join, and resource dependencies for the Capstan concurrency reference machine.  
**Prerequisites:** the single-waiter blocking model and the runtime-refinement gap analysis. The single-waiter exact-head CI gate remains outstanding.

## 1. Problem statement

A scheduler state with no runnable task is not, by itself, a deadlock. A task may be waiting for a timer, device completion, network input, another process, or a scheduler-managed event. Conversely, a graph cycle is not, by itself, a complete deadlock proof: a task in the cycle may have an alternative enabling event, a resource may be releasable by an external actor, or a dependency may be satisfied by any one of several providers.

The analysis therefore has two separate jobs:

1. explain the dependencies that prevent each blocked operation from completing; and
2. classify the global state using the transition system and explicit environment assumptions.

The graph is a diagnostic abstraction of the model state. It must never override the transition relation or claim more than the represented dependencies justify.

## 2. Typed dependency representation

Represent a wait as a first-class record:

`Wait = (task, operation, predicate, mode, dependencies, environment)`

Where:

- `task` is the blocked task identity;
- `operation` identifies the suspended operation instance;
- `predicate` is the exact condition required for resumption;
- `mode` is `ALL` or `ANY`;
- `dependencies` is a finite set of typed dependency records;
- `environment` states whether a declared external event can satisfy the predicate.

Dependency kinds in the initial model:

- `TaskTerminal(task_id)`: a joined task must reach a terminal outcome;
- `ChannelMessage(channel_id)`: a committed message or delivery reservation must become available;
- `ChannelCapacity(channel_id)`: a committed queue slot must become available;
- `ResourceAvailable(resource_id, amount)`: a resource ledger must admit the requested amount;
- `Event(event_source_id, event_kind)`: a declared event source must produce a matching event.

Do not collapse these into untyped task-to-task edges. A channel receive depends on a possible producer and on channel state; a capacity wait depends on a consumer releasing capacity; a join depends on one specific task's terminal transition. The type determines which transitions can discharge the dependency.

## 3. AND and OR dependencies

A wait predicate may require all dependencies or any one dependency:

- `ALL`: every listed dependency must be discharged before the operation can resume. Example: admission requiring two independently held resources.
- `ANY`: one listed dependency is sufficient. Example: a select operation waiting for one of several channels.

Nested predicates are permitted in the abstract definition, but the first executable model should use a bounded, explicit Boolean expression rather than infer AND/OR semantics from graph shape.

For each wait, preserve the exact enabling predicate. A graph projection that turns an OR wait into several mandatory edges can invent deadlocks. A projection that turns an AND wait into alternatives can hide deadlocks.

A dependency is discharged only by a transition that actually makes the wait predicate true. Merely waking a task or observing that a resource might eventually be released is not discharge.

## 4. Provider and release obligations

For each dependency, record the set of model actors or environment sources that can discharge it. Each provider record includes:

- provider identity and kind;
- the transition(s) by which it can satisfy the dependency;
- whether the provider is currently runnable, blocked, terminal, or external;
- any resource or channel prerequisites for that transition;
- whether the provider is optional, required, or one of several alternatives.

A task that owns a resource is not necessarily a viable provider: it may itself be blocked on a dependency cycle. A channel with a consumer is not necessarily able to release capacity: the consumer may be blocked elsewhere. Provider reachability must be derived from the transition system, not guessed from task roles.

The model must distinguish a provider that is impossible (terminal or permanently unavailable under the model) from one that is merely not runnable at this instant.

## 5. Graph projections and their limits

Build a typed bipartite graph:

- task nodes represent tasks;
- condition nodes represent wait predicates or dependency instances;
- provider edges point from a condition to actors or event sources that may satisfy it;
- obligation edges point from a blocked task to the condition it requires.

For a simple single-provider dependency, the projection may be rendered as a conventional wait-for edge from waiter to provider. For multiple providers, preserve the alternative-provider set as a hyperedge or explicit condition node. Do not flatten it into ordinary edges for classification.

Strongly connected components (SCCs) are useful for finding candidate cycles in the simple single-provider subgraph. They are diagnostic only. An SCC is not a deadlock proof when any member has an alternative provider, an external event, or an enabled transition that escapes the component. Absence of a cycle is not a complete deadlock proof for arbitrary resource predicates or hidden dependencies.

The canonical classification must inspect the complete bounded transition relation after graph construction.

## 6. Classification contract

The classifier returns one of the following mutually exclusive outcomes, with a witness or explanation:

1. `TERMINAL_SUCCESS`: all required tasks and cleanup obligations have completed successfully.
2. `TERMINAL_FAILURE`: all required work is terminal, with at least one failure outcome.
3. `TERMINAL_CANCELLED`: all required work is terminal through cancellation.
4. `PROGRESS_ENABLED`: at least one internal transition is enabled.
5. `ENVIRONMENT_WAIT`: no internal transition is enabled, but at least one live declared environment source is permitted to satisfy a pending wait.
6. `DEADLOCK`: no internal transition is enabled; no admitted environment event can satisfy any pending wait; and nonterminal obligations remain.
7. `BOUNDED_UNKNOWN`: exploration, dependency expansion, or resource analysis reached a declared bound before classification.
8. `INVALID_STATE`: a state invariant or dependency consistency check failed.

Classification order matters. Invariant failure is not deadlock. Incomplete exploration is not deadlock freedom. A state with an enabled internal transition is not deadlocked even if a particular task is permanently blocked. An environment wait is not deadlock unless the environment contract rules out the event.

For a finite closed model, a quiescent state with nonterminal tasks and no enabled transition is a deadlock state. For an open model, it is `ENVIRONMENT_WAIT` unless the environment contract proves all relevant sources unavailable.

## 7. Conservative algorithm

Given a state (s):

1. Validate task, wait, ownership, resource, and channel invariants. Return `INVALID_STATE` on failure.
2. Enumerate all internal transitions enabled in (s). If nonempty, return `PROGRESS_ENABLED` with the enabled transition set.
3. Determine whether all required tasks and cleanup obligations are terminal. If so, classify success, failure, or cancellation from terminal outcomes.
4. Enumerate every pending wait predicate and its declared provider set.
5. Determine whether any permitted external source can still satisfy any predicate under the explicit environment contract. If yes, return `ENVIRONMENT_WAIT` with the source and wait witness.
6. If the model is open and source availability is unknown, return `BOUNDED_UNKNOWN`, not `DEADLOCK`.
7. If the model is closed, finite, fully explored, and nonterminal obligations remain with no enabled internal or admitted external transition, return `DEADLOCK` with a minimal blocked-task/dependency witness.
8. If any bound prevented a complete determination, return `BOUNDED_UNKNOWN`.

The graph helps produce the witness and identify cycles; the enabled-transition and environment checks determine the classification.

## 8. Counterexample and witness requirements

A deadlock witness must include:

- the complete canonical state identifier;
- all nonterminal task identities and execution states;
- each active wait and its exact predicate;
- typed dependencies and all possible providers;
- resource ownership and channel queue/reservation state relevant to those dependencies;
- the closed-world/environment assumptions used;
- the SCC or dependency chain, if one exists;
- evidence that no internal transition is enabled;
- evidence that no admitted external event can satisfy a wait.

A witness must be independently replayable from the initial state. The shortest witness should be retained under breadth-first exploration. Do not print only a cycle while omitting the conditions that make every escape path impossible.

## 9. Soundness obligations

The implementation must establish these obligations before using the classifier in an assurance claim:

1. **Dependency completeness:** every transition that can unblock a wait is represented by at least one provider/dependency relation.
2. **Predicate fidelity:** AND/OR structure exactly matches the operation's enabling predicate.
3. **Provider soundness:** every listed provider has a real transition path in the model; speculative providers are marked unknown, not viable.
4. **Environment fidelity:** only explicitly declared event sources are considered; closed-world assumptions are visible inputs.
5. **State fidelity:** graph construction uses the complete state, including reservations, cancellation, queue order, and resource ledgers.
6. **Classification conservatism:** unknown, truncated, or unsupported cases never become `DEADLOCK` or deadlock-free.
7. **Witness replay:** each reported deadlock witness replays and remains quiescent under the same environment assumptions.
8. **Monotonicity under added providers:** adding a genuine provider must not create a new deadlock classification for a state that was previously deadlocked, unless other state semantics changed.

## 10. Required adversarial cases

The bounded model should cover:

- two tasks joining each other;
- a join cycle with one task independently able to terminate;
- two tasks waiting on each other's channel output;
- a channel receive with an admitted external producer event;
- a channel receive with the external source explicitly disabled;
- a task waiting on either of two channels where one is ready;
- an AND wait requiring two resources where only one is available;
- a resource cycle with one resource releasable by an enabled task outside the cycle;
- a blocked sender whose capacity provider is a blocked consumer;
- a task cancelled while it is the only provider for another task;
- a quiescent state with an unmodelled/unknown provider, which must classify as unknown;
- a state-space cap reached before all providers are explored, which must classify as unknown.

For every rejected transition, assert state preservation. For every classified deadlock, mutate one relevant assumption or enable one provider and verify that the classification changes appropriately.

## 11. Research and implementation sequence

1. **Partial:** define typed wait records for JOIN and EVENT dependencies in the two-task executable model.
2. **Partial:** add a closed-world mutual-join cycle and a replayable task/target witness; exact-head test evidence is pending.
3. Extend the executable representation to channel-message and channel-capacity dependencies.
4. Add explicit external-event sources and the `ENVIRONMENT_WAIT` result.
5. Add AND/OR predicates only after the single-provider classifier is stable.
6. Exhaustively compare graph-derived candidates with the canonical enabled-transition classifier over small finite states.
7. Only then investigate SCC-based reductions, compositional summaries, or partial-order reduction.

The executable slice currently classifies two tasks and one channel. It distinguishes JOIN, channel-message, channel-capacity and EVENT waits; runnable progress; satisfied joins; terminal success/failure/cancellation; live external-event waits; unknown environment availability; incomplete exploration; invalid wait/channel/resource identities; and closed-world deadlock. Channel waits name a provider task and channel identity, while resource waits name a provider task and resource identity, allowing two-task channel and resource dependency cycles to be represented. This remains a direct bounded state classifier: it does not yet enumerate a transition graph, establish provider completeness, model channel queue contents/reservations or resource amounts/ownership, or prove dependency completeness. The initial implementation should not claim parameterised deadlock freedom. Finite results apply only to the declared bounds and exact environment model.

## 12. Explicit non-claims

This specification does not prove deadlock freedom, scheduler fairness, starvation freedom, or completeness of a future runtime dependency graph. It does not establish that the current Capstan runtime implements these semantics. The single-waiter exact-head CI gate remains a prerequisite for executable generalisation.

## 13. Bounded explicit transition-graph prototype

A separate executable prototype now exists in `verification/concurrency_transition_graph.cap`, registered in `tests/run.sh`. It explores an explicitly supplied finite directed transition graph breadth-first from its initial state. It distinguishes reachable nonterminal sink states (deadlock witnesses), complete graphs with no reachable nonterminal sink, all-terminal reachable graphs, invalid graph declarations, and state-limit exhaustion (unknown). It includes adversarial cases for a cycle with an enabled escape, a reachable sink, an unreachable dead end, duplicate action labels, terminal-state outgoing edges, and fail-closed state limits.

This is deliberately a graph-level prototype, not yet an extractor from `CWFState` or the concrete channel/resource models. Its state IDs stand in for canonical full states; the prototype does not establish canonical-state equality, transition completeness, environment-event modelling, witness trace replay, or correspondence with the runtime. In particular, a complete graph with no reachable nonterminal sink establishes only the stated finite-graph property, not scheduler fairness, starvation freedom, or unbounded liveness. The next bridge must generate graph nodes and edges from actual model states and enabled transitions, then cross-check graph classification against the direct state classifier.
