# Concurrency threat model and elimination requirements

**Status:** normative design extension proposed for review; not an implementation or proof  
**Applies to:** the Capstan safe concurrency profile  
**Parent design:** [Concurrency safety core](CONCURRENCY-SAFETY-CORE.md)  
**Coordination:** [issue #229](https://github.com/DavidFernee/Capstan/issues/229)

## 1. Security objective

Capstan's safe concurrency profile SHALL be fail-closed. A construct is admitted only when its memory-safety, ownership, synchronisation, resource and stated progress obligations are established by the language rules and the assurance level of the selected profile. Unsupported or unverified concurrency mechanisms are unavailable to safe code, not merely discouraged.

The engineering objective is to eliminate defined vulnerability classes from safe programs by construction or proof. It is not a claim that every possible software defect, specification error, hardware fault or operating-system defect can be eliminated.

A guarantee is valid only for the exact compiler, runtime, backend, platform adapter, target architecture and profile for which its evidence exists. Guarantees do not transfer automatically across versions or targets.

## 2. Threat model

### 2.1 Adversary and failure sources

The design must account for:
- arbitrary legal scheduling and preemption at every permitted scheduling point;
- adversarial interleavings of tasks, including cancellation, failure and shutdown;
- untrusted message contents and hostile or stalled peers;
- resource exhaustion and adversarial task/channel creation attempts;
- weak-memory execution permitted by the target architecture;
- reentrancy and callbacks into code not known to the caller;
- partial failure of OS operations, timers, worker creation and wakeups;
- compiler, runtime and platform-adapter defects as trusted-computing-base risks;
- foreign code, devices, DMA and interrupt handlers as explicit boundary risks.

### 2.2 Guarantee boundary

Safe-language guarantees cover only operations represented in the verified model. Foreign code, raw pointers, device memory, DMA, interrupts, OS callbacks and hardware-specific instructions require separate typed capabilities and contracts. If a contract is absent or unverified, the operation is unavailable to the safe profile.

The trusted computing base (TCB) must be enumerated per release: parser, type/effect/ownership checker, compiler transformations, runtime scheduler, memory allocator/collector where applicable, atomic lowering, platform adapter, linker assumptions and relevant hardware memory model. Each component requires tests, review and proof or a documented assurance argument. A proof of the abstract calculus alone is not a proof of this TCB.

## 3. Required treatment of vulnerability classes

The classifications below are requirements, not claims that Capstan currently prevents these failures.

| Class | Required prevention or assurance mechanism | Admission rule |
|---|---|---|
| Data races and conflicting unsynchronised access | Ownership, exclusive borrows, immutable sharing, typed synchronisation; race-freedom theorem | Reject any untracked shared mutable access |
| Use-after-free and dangling task references | Region/lifetime checking, task-tree ownership, join-before-destruction | Reject references whose lifetime cannot cover every task execution |
| Double free, double close, double unlock, duplicate completion | Linear/affine resource accounting and state transitions | Reject duplicate consumption; external resource contracts required |
| Use-after-scope and stack escape | Escape analysis and lifetime typing across tasks/callbacks | Reject escaping references |
| Iterator/container invalidation races | Borrowed views tied to exclusive/shared container permissions; mutation invalidates incompatible views | Reject mutation while incompatible views exist |
| Torn or non-atomic shared state | Atomic scalar API or protected aggregate invariant | No ordinary shared mutable aggregate access |
| Memory-ordering and publication bugs | Formal memory model, verified atomic lowering, litmus suite per target | Admit only memory orders with target refinement evidence |
| ABA and unsafe reclamation | No user raw-pointer atomics in baseline; versioned identities and proven reclamation for advanced APIs | Advanced reclamation unavailable until separately verified |
| Lock-order inversion and lock cycles | Static ranks, canonical multi-lock acquisition, lock graph checking | Reject unranked/ambiguous acquisitions in safe profile |
| Self-deadlock and recursive locking | Non-reentrant lock types and ownership-aware acquisition | Reject recursive acquisition unless a separately verified reentrant protocol exists |
| Lock held across suspension/blocking/callback | Effect and context checking; bounded synchronous critical sections | Reject prohibited suspension, blocking and unknown callbacks under guards |
| Lost wakeups and missed notifications | Atomic wait registration/state transition protocol | No user-implemented condition-variable primitive without verified contract |
| Waiter leaks and stale wait registrations | Linear wait handles and cancellation-safe deregistration | Wait registration must be consumed or safely retired |
| Channel message loss/duplication/reordering | Linear message ownership, explicit linearisation points and specified ordering | Only specified FIFO/ordering semantics admitted |
| Channel close/send/receive races | Verified channel state machine and exhaustive bounded interleavings | No ad hoc channel implementation in safe core |
| Cancellation races and skipped cleanup | Cancellation state machine, cancellation points, linear cleanup | Cancellation cannot bypass required cleanup |
| Callback-after-destruction / task teardown race | Structured scopes, owner-bound registration handles and join/deregister protocols | No unowned callback or detached task |
| Reentrancy and invariant exposure | Reentrancy effects, no unknown callback under protected invariant, explicit reentrant protocols | Reject hidden or unmodelled reentrancy |
| Deadlock through locks, joins, channels or protocols | Dependency graphs, typed wait capabilities, protocol state machines, bounded model checking | General unbounded deadlock freedom is not promised; unverified bounded protocols are rejected from verified profiles |
| Starvation and unfair waiter selection | Explicit scheduler/queue fairness contracts, bounded-wait or service guarantees where claimed | No starvation-free claim without assumptions and proof |
| Livelock and retry storms | Bounded retries, backoff/deadline budgets, progress contracts | Unbounded retry loops cannot claim progress |
| Priority inversion | Priority inheritance/ceiling or scheduler isolation with verified adapter semantics | Real-time profile unavailable without target-specific proof |
| Task/thread/stack/queue exhaustion | Admission control, reservation-before-publication, aggregate quotas | Reject before partial task/message publication |
| Memory and buffer exhaustion | Bounded channels, allocator quotas, checked accounting and typed failure | Every concurrency-owned allocation accounted |
| Cleanup/finalizer stalls | Non-blocking bounded destructors; explicit fallible close/finalize | Blocking or unbounded implicit cleanup forbidden |
| Scheduler shutdown and worker-loss races | Scheduler lifecycle state machine, task ownership and fail-stop semantics | No task may be silently abandoned |
| Async executor starvation by blocking calls | Blocking/async effects and dedicated bounded blocking pools | Reject blocking effects in async workers |
| Cross-task information leakage | Information-flow labels, noninterference policy and controlled declassification | Confidentiality claims only for verified flows |
| Timing/cache/power side channels | Constant-time types/operations, leakage model and target-specific evidence | Ordinary race freedom does not imply side-channel resistance |
| Speculative-execution leakage | Target mitigation contract and restricted secret-handling profile | No universal guarantee absent hardware support |
| TOCTOU on shared resources | Capability-based operations, atomic compare-and-act, versioned handles or OS transaction primitive | Check/use split rejected where resource identity can change |
| Incorrect transaction ordering / logical races | Protocol state machines, invariants, linearizability specifications and model checking | Race freedom alone is insufficient; unverified protocols cannot claim correctness |
| External callback, interrupt, DMA and MMIO races | Dedicated capabilities, ownership transfer, barriers and device-specific protocols | Excluded from baseline until target contract verified |
| Foreign-thread entry and FFI races | Explicit boundary wrapper, ownership transfer and ABI contract | Raw foreign thread entry forbidden in safe profile |
| Fault-induced partial state transitions | Transactional state updates, rollback/commit protocol and fault injection | No partially published state on typed failure |
| Nondeterministic data corruption from unsafe library code | Verified library contracts and capability boundary | Unverified libraries are outside the safe assurance claim |

## 4. Liveness is a separately specified property

Memory safety and data-race freedom do not imply deadlock freedom, starvation freedom, termination or availability.

Capstan SHALL distinguish:
- **Safety:** nothing bad happens (no invalid access, duplicate ownership, invariant violation, or forbidden state).
- **Liveness:** something good eventually happens, under explicit scheduling and environment assumptions.
- **Bounded progress:** a specified operation completes within a stated step, time or resource bound under stated assumptions.
- **Availability:** the system continues to provide service despite specified faults and load.

Unrestricted deadlock freedom and termination cannot be promised for arbitrary programs. Capstan instead provides restricted, verifiable concurrency profiles:
1. A deterministic bounded protocol profile with finite state, bounded queues, bounded task count and exhaustive state exploration.
2. A ranked-lock profile where lock-order cycles are excluded by construction.
3. A real-time profile only where scheduler fairness, priority, interrupt and timing assumptions are established for the target.
4. A general safe profile that guarantees memory/ownership safety but makes no unproved global progress claim.

A protocol that requires a liveness guarantee must declare its assumptions (scheduler fairness, peer response, deadlines, resource availability) and its property. If the checker cannot establish the property within the declared profile, the guarantee is not granted.

## 5. Fail-closed capability tiers

The language must not conflate memory-safe concurrency with fully verified concurrent protocols.

- **Tier 0 — sequential safe:** no concurrent shared state or task creation.
- **Tier 1 — memory-safe structured concurrency:** ownership, immutable sharing, bounded tasks/channels, cancellation and cleanup; no arbitrary shared mutable references.
- **Tier 2 — verified synchronisation:** ranked locks, atomics and verified library protocols with target memory-model refinement.
- **Tier 3 — bounded protocol assurance:** finite-state model checking/proofs for deadlock, ordering, fairness or bounded progress under explicit assumptions.
- **Tier 4 — platform/real-time/device assurance:** interrupts, DMA, MMIO, priority and timing claims backed by platform-specific contracts and evidence.

A program may use only the highest tier for which all required evidence exists. A lower tier must not silently inherit claims from a higher one.

## 6. Required proof and evidence ledger

Each admitted primitive must have a machine-readable assurance record containing:
- primitive and semantic version;
- source-level typing/effect/ownership rules;
- abstract transition system;
- safety invariants and proof obligations;
- liveness properties and environmental assumptions, if any;
- compiler lowering and runtime implementation mapping;
- target-specific memory-order and platform-adapter evidence;
- positive and negative compile tests;
- bounded exhaustive/model-checking results and state-space limits;
- fuzz, stress, fault-injection and mutation-test results;
- known residual risks and explicit exclusions.

Minimum core theorems:
1. Type preservation and progress for the concurrency calculus.
2. Ownership and linear-resource conservation.
3. No data races for safe shared-memory accesses.
4. No dangling references across task/callback lifetimes.
5. Structured task-tree termination and cleanup semantics.
6. Channel message conservation and linearisation correctness.
7. Lock invariant preservation and ranked-lock acyclicity.
8. Atomic-operation refinement to the target memory model.
9. Resource accounting soundness and failure atomicity.
10. Noninterference for any profile claiming confidentiality.
11. Refinement/correspondence from the compiled implementation to the abstract machine.

No theorem is complete merely because its statement appears in documentation. Each must have a proof artifact, checked assumptions and reproducible build/test evidence.

## 7. Implementation order

1. Freeze the threat model and capability-tier definitions.
2. Specify the concurrency calculus and deterministic transition machine.
3. Prove the ownership, lifetime, linearity and race-freedom core.
4. Implement a type-checker prototype with adversarial positive/negative programs.
5. Implement deterministic bounded scheduling, task scopes and cancellation.
6. Implement bounded channels and prove message conservation.
7. Implement lock ranks and prove acyclicity for the admitted lock graph.
8. Add sequentially consistent atomics and target refinement tests; add weaker orders only with proof.
9. Add protocol state machines, bounded model checking and liveness contracts.
10. Add resource admission control and fault-atomic state transitions.
11. Add information-flow and constant-time profiles as separate assurance workstreams.
12. Add platform adapters, real-time, interrupt, device and FFI capabilities only after target-specific evidence.
13. Gate release claims on the assurance ledger and exact artifact hashes.

## 8. Release gate

A concurrency feature SHALL NOT be advertised as safe merely because tests pass or because its API uses ownership-like terminology. The release gate requires:
- a closed specification for the admitted operation;
- type/effect/ownership rejection tests;
- proof of the relevant abstract properties;
- a compiler/runtime refinement argument;
- target-specific atomic and adapter evidence;
- bounded model checking where the state space is finite and relevant;
- fuzzing, fault injection and mutation testing;
- a published residual-risk statement.

Any failed or missing gate downgrades the feature to experimental or makes it unavailable in the verified safe profile.

## 9. Explicit non-claims

This specification does not assert that current Capstan code implements these controls. It does not claim universal elimination of all concurrency bugs in arbitrary programs, all logical errors, all denial of service, all timing channels, or defects in the compiler, operating system, hardware or external components.

The enforceable promise is narrower and stronger: Capstan will not grant a safe-profile guarantee without a precise property, explicit assumptions, and evidence for the exact implementation and target. Where a vulnerability class cannot be excluded generally, the corresponding operation or assurance claim is restricted rather than silently accepted.
