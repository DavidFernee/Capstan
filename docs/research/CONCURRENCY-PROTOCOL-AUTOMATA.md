# Typed Protocol Automata for Capstan Concurrency

**Status:** research design proposal, not an implemented language feature or a verified theorem  
**Related work:** issues #229 and #249; PRs #239, #248 and #254  
**Design dependencies:** the concurrency safety core and concurrency guarantee calculus

## Implementation status (2026-11-25)

A first bounded descriptor validator and interpreter now exists in
`verification/protocol_automata.cap`, and is included in `tests/run.sh`.
It accepts finite acyclic labelled transition systems with bounded state,
role and transition counts; rejects duplicate (source, role, operation)
labels, invalid endpoints, unreachable states, cycles and nonterminal dead
ends; and interprets one enabled transition without mutating state on
rejection. The first conformance fixture is a linear-message protocol.

This implementation is deliberately narrower than the full design above.

The descriptor now carries a per-transition contract containing a message-type
tag, owner-before and owner-after identities, a bounded resource delta, and an
effect class (allocation, transfer, or release). Validation requires these
fields to agree with the acting role and transition shape. The resource-aware
interpreter checks the message type and current owner, uses subtraction-based
budget admission, and returns the original state/owner/resource values on
rejection.

A separate executable bridge,
`verification/concurrency_protocol_refinement.cap`, maps the concrete
one-byte task/channel model's normal `produce → send → receive → release`
transitions to the abstract automaton. It checks both state correspondence
and ownership/resource correspondence at each step, plus a negative
inconsistent-queue case. Cancellation/abort, failure paths, multiple messages,
variable-size resources, native scheduling and compiler/runtime refinement
remain outside this bridge. This is a bounded refinement check for one
protocol slice, not a general refinement theorem.
It does not yet encode endpoint ownership, message types, effects,
capabilities, resource deltas, cancellation cleanup, duality between
endpoints, or compiler refinement. The validator/interpreter is a research
reference artefact, not a safe-profile language feature. Its current tests
are submitted to CI; no passing result is claimed until exact-head runs
complete.

## 1. Problem

The first executable concurrency reference machine uses a fixed producer/consumer protocol. Its explicit phases already expose a useful design boundary: task scheduling, message ownership, queue occupancy, cancellation and resource accounting cannot be specified independently. A reusable language facility needs a protocol description that makes these relations explicit and admits machine-checkable conformance tests.

The goal is not to add session-type syntax for its own sake. The goal is to make illegal protocol transitions unrepresentable in the safe profile, and to make every accepted protocol state carry enough information to terminate safely under cancellation or failure.

## 2. Protocol automaton

A protocol is a finite labelled transition system:

`P = (Q, q_0, R, \Sigma, \delta, F, C)`

where:

- `Q` is a finite set of protocol states and `q_0` is the initial state;
- `R` is a finite set of endpoint roles;
- `Σ` is the set of labelled operations;
- `δ ⊆ Q × R × Σ × Q` is the transition relation;
- `F ⊆ Q` is the set of normally terminal states;
- `C` assigns cancellation/failure cleanup obligations and resource costs to states and transitions.

Each transition label must carry more than a method name. It records:

1. the acting role and required authority/effects;
2. source and destination protocol states;
3. the required endpoint ownership and resource ownership;
4. the queue, byte, task and step budget deltas;
5. the linearisation point for shared-state effects;
6. cancellation and failure behaviour;
7. the cleanup reservation consumed or released.

A transition is enabled only when all of these preconditions hold. Its state, ownership and resource-ledger updates commit atomically. A failed precondition leaves the complete pre-state unchanged.

## 3. Endpoint typing and duality

An endpoint is conceptually indexed by its protocol and current state:

`Endpoint<P, q, role>`

The endpoint is linear: a transition consumes the old endpoint and produces the endpoint for the destination state. A send/receive pair must be dual with respect to the same message type and transfer mode. An endpoint cannot be duplicated, silently discarded, or used after its state has advanced.

The first implementation should use a deliberately small subset:

- finite, non-recursive protocols;
- statically known roles;
- move-only endpoint ownership;
- explicit send, receive, close, cancel and failure transitions;
- bounded message and queue resources.

Branching, recursion, delegation, dynamic role creation and distributed sessions should be staged only after the finite core has a precise semantics.

## 4. Product state and conservation laws

The protocol automaton is not the whole runtime state. The executable configuration is a product of:

- protocol phase;
- endpoint and message ownership;
- channel queue and close state;
- task lifecycle and linear join handles;
- cancellation/failure status;
- resource budgets and reserved cleanup credits.

The invariant checker must establish at least:

- **Endpoint uniqueness:** each linear endpoint has exactly one owner.
- **Message conservation:** each live message is owned by exactly one producer, channel, consumer or explicit disposal operation.
- **Queue consistency:** queue membership and byte accounting agree with message ownership.
- **Protocol consistency:** the current phase agrees with ownership, queue and endpoint state.
- **Task conservation:** every spawned child has exactly one join obligation until its handle is consumed.
- **Resource conservation:** allocation, transfer, release and reservation accounting balance.
- **Terminal closure:** a scope cannot terminate with live children, unconsumed handles, open channels or live resources.

The reference machine in PR #254 is the first concrete instance of these rules. Its phases (empty, produced, enqueued, received, released, aborted) are intentionally specific to one linear message; they are not yet a generic automaton implementation.

## 5. Cancellation and failure closure

Every reachable nonterminal protocol state must have a bounded cleanup strategy under the declared resource limits. This is a stronger requirement than merely defining a cancellation flag.

Admission must reserve the resources needed to:
- terminalise each accepted child by cancellation or failure;
- consume each child join handle;
- close each owned channel;
- complete or fail the enclosing scope.

A task may not be spawned if those obligations cannot be reserved. Normal completion releases the unused cancellation/failure reservation. The first child failure records scope failure and consumes the scope-cancellation request credit; later failures consume only their own terminalisation credit. This avoids double-charging a shared cancellation obligation.

Cleanup transitions must preflight all required credits before mutation. The safe profile must not accept work whose required cleanup cannot be represented within the resource contract. If a protocol has a state with no bounded cleanup path, it is not eligible for the safe profile.

Cancellation is cooperative, not magical preemption. The protocol must identify cancellation points. After a cancellation request, new work transitions are disabled at those points, while explicitly permitted cleanup and failure-reporting transitions remain available.

## 6. Failure semantics

Failure is distinct from cancellation and normal completion.

- A child failure is recorded as a failure outcome, not silently converted into cancellation.
- The first failure requests sibling cancellation.
- Resources owned by the failing child are disposed of by its declared cleanup transition.
- Resources already transferred to another endpoint are not freed by the former owner.
- The parent must join every child and close every channel before returning a failed scope outcome.
- Multiple failures are aggregated deterministically. The initial implementation may retain a primary failure plus a bounded collection of secondary failures; truncation must be explicit and must not erase the fact that additional failures occurred.

The current Boolean `scope_failed` is sufficient only for the first bounded model. It is not a final diagnostic or multi-error representation.

## 7. Model checking and state-space control

The initial checker should use breadth-first exploration of the finite product state. It must:

- enumerate every enabled actor/operation transition;
- deduplicate states using every semantic and resource field;
- retain the transition trace for each discovered state;
- check invariants after every accepted transition;
- return a shortest counterexample trace;
- fail closed when a configured state cap is reached.

A truncated search is not a proof. Partial-order reduction may be introduced only after an independence relation is defined and shown to preserve the properties being checked. A scheduler's arbitrary ordering is not itself a justification for pruning interleavings.

## 8. Proof obligations

The research sequence should establish:

1. **Automaton well-formedness:** roles, states, transitions and terminal states are coherent.
2. **Endpoint preservation:** each operation consumes and produces the correctly indexed endpoint.
3. **Ownership conservation:** no transition duplicates, loses or forges a linear resource.
4. **Protocol refinement:** implementation transitions simulate the protocol transition relation.
5. **Resource soundness:** all runtime resource deltas are bounded by the declared contract.
6. **Cancellation closure:** every admitted state has the reserved bounded cleanup path promised by its contract.
7. **Failure preservation:** child failure cannot be reported as normal success.
8. **Concurrency refinement:** the scheduler and memory model preserve the atomic transition semantics.
9. **Compiler refinement:** source typing and protocol proofs survive lowering, optimisation and native code generation.

The first eight obligations can be developed against a finite abstract machine. The ninth requires a separate compiler/backend refinement argument; it cannot be inferred from source-level typing.

## 9. Research questions

The implementation and literature review should investigate:

- How to combine linear session endpoints with Capstan's ownership, borrowing and capability/effect systems without duplicating their responsibilities.
- Whether protocol state should be encoded as a type-level index, a refinement, or a compiler-checked typestate capability.
- How to compose local endpoint protocols into a global scope protocol while avoiding unsound assumptions about independent transitions.
- How to express bounded cleanup costs compositionally, including failure aggregation and resource disposal.
- Which partial-order reduction conditions are sound for the chosen memory model.
- How to translate protocol automata into executable conformance monitors without making the monitor a second semantic authority.
- How to generate adversarial protocol traces and compare against concurrency CVEs involving lifecycle, cancellation, TOCTOU, reentrancy and resource exhaustion.

No novelty or superiority claim should be made until the related-work review and proof results support it.

## 10. Incremental acceptance plan

1. Keep the current one-message model as a small, executable reference case.
2. Stabilise and test its ownership, cancellation, failure and cleanup-reservation invariants.
3. Define a machine-readable finite protocol descriptor and validate malformed descriptors.
4. Generate transition tables and negative conformance tests from that descriptor.
5. Prove endpoint preservation and ownership conservation for the finite descriptor interpreter.
6. Generalise from one message to bounded queues and multiple roles.
7. Add branching and recursion only with explicit resource and termination contracts.
8. Establish the compiler/runtime refinement bridge before promoting the feature into the safe-profile guarantee set.

## 11. Explicit non-claims

This proposal does not establish general deadlock freedom, starvation freedom, timing guarantees, weak-memory correctness, distributed consistency, or immunity to all concurrency vulnerabilities. Those properties require separate assumptions, definitions and evidence. The finite reference machine is neither a native scheduler nor proof of arbitrary Capstan program behaviour.
