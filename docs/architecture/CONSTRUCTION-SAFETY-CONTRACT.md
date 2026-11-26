# Capstan construction-safety contract

**Status:** normative design constraint; implementation is staged and evidence-gated  
**Applies to:** Capstan language, compiler, CCAM, runtime, standard library and every first-party system  
**First consumer:** Bosun's Locker  
**Governing rule:** safe programs cannot express invalid states or perform invalid transitions.

## 1. Non-negotiable rule

Correctness and security properties are enforced by construction. They are not optional annotations, conventions, lint preferences, application obligations or runtime promises unsupported by the type system.

For every invariant, the implementation must identify its enforcement point:

1. **Unrepresentable:** the type system or language grammar cannot express the invalid state or operation.
2. **Uncallable:** authority/capability and effect checking make the operation unavailable to this caller.
3. **Compiler-proved:** a compiler check discharges a static obligation and rejects code when it cannot.
4. **Runtime-guarded:** an unavoidable dynamic condition is checked before the operation crosses its state-changing boundary; failure is typed, atomic and cannot be ignored as success.
5. **Externally assumed:** a hardware, OS, device, cryptographic or other boundary cannot be proved internally; the assumption is explicit, narrow, tested and versioned.

A guarantee is not satisfied by merely documenting a rule. Every production invariant must have a concrete enforcement mechanism and negative tests that attempt to violate it. Runtime guards are not a substitute for a statically expressible invariant.

## 2. Safe-profile closure

The default language and library profile is safe. In that profile:

- no unchecked pointer arithmetic, invalid memory access, data race, use-after-free, double release, unbounded recursion or implicit resource growth;
- no ambient filesystem, network, process, clock, entropy or administrative authority;
- no implicit foreign-function or native-code escape;
- no detached task whose lifetime or failure is unowned;
- no implicit weakening of isolation, durability, authentication or validation guarantees;
- no unchecked conversion from untrusted bytes to trusted typed values;
- no ignored failure from an operation required to establish an invariant.

Any operation outside the safe profile is explicitly marked, capability-gated, isolated in a separately audited module, and excluded from safe callers unless a reviewed boundary contract permits it. An unsafe module does not confer ambient unsafety on its dependants.

## 3. Required language mechanisms

These are language/compiler requirements, not assumed existing Capstan features. Each must be implemented, tested and specified before a first-party subsystem relies on it.

### 3.1 Ownership and lifetime

- affine or linear values for unique resources;
- borrowing with statically checked lifetimes and aliasing restrictions;
- explicit shared immutable access;
- mutable access exclusive by construction;
- resource destruction/release exactly once;
- no reference outliving its owner;
- structured task scopes that join or explicitly resolve every child.

### 3.2 Typestate and transitions

- state-indexed resource types;
- transition operations consume the old state and produce the new state;
- no copy, alias or reuse of consumed state tokens;
- illegal transitions are absent from the safe API;
- state transitions are atomic with respect to failure: rejection preserves the prior state.

Illustrative notation only (not current Capstan syntax):

`Transaction<Active> -> prepare -> Transaction<Prepared>`

`Transaction<Prepared> -> commit -> Transaction<Committed>`

A transaction in `Committed` has no `abort` operation. A transaction in `Prepared` has no user-write operation. This must be enforced by the compiler, not a boolean checked by every caller.

### 3.3 Effects and authority

- every effectful operation declares its effects;
- capabilities are explicit values, scoped to objects and operations;
- capability attenuation is monotonic: derived authority cannot exceed source authority;
- authority cannot be forged, cloned where unique, or recovered from ambient globals;
- effects and capabilities are checked at module and call boundaries;
- privileged operations require an explicit capability in the function signature.

### 3.4 Resource accounting

- resource budgets are explicit values associated with a scope or operation;
- child scopes receive a partition of the parent budget, never a fresh reset;
- budget tokens cannot be duplicated to multiply allowance;
- allocation, CPU/fuel, stack, I/O, rows, versions, locks, retries, waits and spawned tasks are charged at the operation boundary;
- exhaustion is a typed failure before externally visible partial success, or an explicitly specified recoverable state transition;
- no unbounded operation is admitted through the safe profile without a declared bound or cancellation contract.

### 3.5 Concurrency

- data-race freedom by ownership/borrowing or verified synchronization;
- lock ordering or deadlock-safe protocol is enforced or explicitly bounded;
- cancellation is a state transition, not asynchronous destruction at arbitrary instructions;
- task lifetime, exceptions and resource ownership are structured;
- atomic ordering and memory model are part of the language specification;
- race freedom is not conflated with protocol correctness, liveness or functional correctness.

### 3.6 Data and trust boundaries

- untrusted bytes remain untrusted until checked decoding succeeds;
- validated values carry a type that cannot be constructed through unchecked field assignment;
- integer, length, index and arithmetic operations are checked unless proven safe;
- serialization is canonical and versioned;
- cryptographic and authentication APIs do not expose unsafe default modes;
- query construction is typed and parameterised, not string concatenation.

## 4. Bosun's Locker construction rules

The database safe API must make the following states and operations unrepresentable:

- read/write after prepare;
- commit twice or commit an aborted transaction;
- abort after commit decision;
- use a transaction, cursor, page lease, buffer pin or lock after release;
- use a cursor outside its owning transaction/snapshot;
- use a page handle after its buffer lease expires;
- mutate a page without an exclusive page-write capability;
- publish uncommitted writes;
- acknowledge commit before the persistence contract is met;
- use a query plan with a schema/catalogue version other than the one it was checked against;
- execute an operation without its database/table/row capability;
- exceed a transaction's aggregate resource budget by resetting a nested operation's allowance;
- allow an unowned background task to outlive transaction or database shutdown.

The eventual public API must encode transaction state, cursor lifetime, page leases, locks and capabilities in types. Runtime state machines remain necessary at I/O and crash boundaries, but they are an implementation backstop and recovery mechanism, not the public correctness interface.

## 5. Proof and implementation discipline

For every invariant, maintain a traceability record:

| Field | Required evidence |
|---|---|
| Invariant | Precise mathematical or operational statement |
| Prevention | Type rule, effect rule, capability rule or checked transition |
| Compiler | Positive and negative compile-time tests |
| Runtime | Boundary checks and failure atomicity tests, if needed |
| Model | Executable abstract semantics and invariant |
| Proof | Theorem and explicit assumptions, or recorded open obligation |
| Refinement | Relation connecting model/compiler/runtime to the deployed implementation |
| Platform | OS/device/ABI/cryptographic assumptions |
| Revision | Exact commit and evidence artifacts |

A theorem about an abstract model is not a theorem about generated code or a deployed database until a refinement/correspondence argument connects them. A test suite is evidence, not proof. An external assumption must never be relabelled as an internal guarantee.

## 6. Required compiler conformance suite

Every mechanism above requires:
- accepted programs demonstrating legal use;
- rejected programs for each prohibited use;
- diagnostics identifying the violated rule and source span;
- module/import tests proving the rule cannot be bypassed across module boundaries;
- adversarial tests for aliasing, substitution, generic instantiation, inference, casts and deserialization;
- deterministic compiler output and revision-bound test evidence.

The compiler must fail closed: inability to establish a required safety condition rejects the program. No warning-only downgrade for safe-profile invariants.

## 7. Delivery order

1. Specify ownership, borrowing, affine/linear values and lifetime semantics.
2. Implement compiler enforcement and negative tests.
3. Specify typestate and state-consuming transitions; add generic state identity if absent.
4. Specify capabilities and effect checking.
5. Specify compositional resource tokens and structured concurrency.
6. Integrate these mechanisms into Bosun transaction, cursor, page, lock and query APIs.
7. Connect the rules to CCAM and formal verification; prove soundness of each compiler-enforced rule under explicit assumptions.
8. Remove transitional unsafe/foreign paths from first-party production profiles.

Do not implement database public APIs that depend on a missing language feature by simulating it with booleans and conventions. Such prototypes may exist as reference models only and must be labelled as such.

## 8. Acceptance criterion

A safe Capstan program that attempts any prohibited operation above must be rejected before execution. If the property depends on a dynamic external condition, the only permitted path is an explicit checked boundary with failure-atomic semantics and evidence. There is no application opt-out from the safe profile.
