# Bosun's Locker — transaction history and state-machine semantics

**Status:** normative candidate, review required  
**Version:** 0.1-draft  
**Parent:** BOSUNS-LOCKER-ARCHITECTURE.md  
**Purpose:** define the implementation-independent contract used by the reference model, history checker and later transaction engines.

## 1. Scope

This document defines a single-node transaction-history contract and transaction lifecycle. It deliberately does not select MVCC, locking, OCC, SSI, timestamp ordering or a storage layout. Those are implementations that must refine this contract.

The initial target is strict serializability. The formal definition below is the acceptance target; it is not a statement that the current Capstan repository implements it.

## 2. Abstract database

Let:
- K be a finite or unbounded set of logical keys;
- V be the set of typed values plus a distinguished absent value;
- D : K -> V be a committed database state;
- T be the set of transaction identifiers;
- each transaction have a finite program of reads and writes in program order.

A transaction operation is one of:
- Read(t, k) -> v;
- Write(t, k, v);
- Insert(t, k, v) (requires absent under the transaction's declared semantics);
- Delete(t, k);
- Scan(t, predicate/range) -> ordered finite result;
- Commit(t);
- Abort(t).

The first executable profile may restrict scans and values, but restrictions must be explicit and tested. Values are typed Capstan values; serialization and canonical encoding are specified separately.

## 3. History events

A history is a finite sequence of externally observable events with a global event order. At minimum:

- Invoke(t, op, args)
- Return(t, result)
- CommitInvoke(t)
- CommitDurable(t, commit_id)
- CommitReturn(t, commit_id)
- AbortInvoke(t, reason)
- AbortReturn(t, reason)
- ClientTimeout(t, operation)

The model distinguishes:
- transaction program order;
- invocation/response order;
- the durable commit decision;
- delivery of the response to the client.

A timeout or lost response is not an abort. If a durable commit exists but the client did not receive its response, the outcome is unknown to the client, not rolled back.

## 4. Real-time precedence and strict serializability

For completed transactions Ti and Tj, define Ti precedes-real-time Tj when the response of Ti precedes the invocation of Tj. The relation includes successful commit responses and completed abort responses as appropriate for the history definition.

A committed history is strictly serializable if there exists a total order over its committed transactions such that:

1. **Real-time preservation:** if Ti precedes-real-time Tj, then Ti precedes Tj in the serialization order.
2. **Program-order preservation:** each transaction's operations retain their source order.
3. **Read consistency:** every read returns the value of the latest preceding committed write to that key in the serialization order, or absent if none exists.
4. **Atomicity:** all writes of a committed transaction take effect at its single serialization position; aborted transactions have no visible writes.
5. **Predicate consistency:** a range/scan observes exactly the set and order of rows required by the database's declared logical semantics at its serialization position.

The finite history checker must decide whether such a serialization exists for its supported bounded history model. It must return a witness serialization for accepted histories and a minimized counterexample/dependency cycle or equivalent explanation for rejected histories.

For incomplete histories, define explicit completion/extension rules. A transaction whose commit outcome is unknown may be treated as committed only if a durable commit decision is observed in the model; otherwise the checker must consider all allowed completions and report ambiguity rather than inventing an outcome.

## 5. Transaction state machine

The logical states are:

- New
- Active
- Preparing
- CommitDecided
- DurableCommitted
- Aborting
- Aborted
- Failed (terminal only for unrecoverable internal fault; persistent outcome must still be resolved)

Allowed transitions:

| From | Event | To | Required property |
|---|---|---|---|
| New | begin accepted | Active | Snapshot and budgets assigned atomically |
| Active | read/write operation accepted | Active | Operation is isolated and budget charged |
| Active | commit requested | Preparing | No new user operation is admitted |
| Preparing | validation rejects | Aborting | No commit becomes visible |
| Preparing | commit decision recorded | CommitDecided | One durable protocol decision is selected |
| CommitDecided | persistence boundary reached | DurableCommitted | Recovery must preserve transaction effects |
| DurableCommitted | response delivered | DurableCommitted | Repeated status/commit query returns same outcome |
| Active/Preparing | abort requested or cancellation | Aborting | Commit cannot race to a contradictory terminal result |
| Aborting | cleanup/recovery record complete | Aborted | No transaction writes visible |
| Any nonterminal state | crash | recovery-defined | Recovery resolves from durable records only |

Implementation may use more internal states. It may not collapse states if doing so obscures the durable decision or permits contradictory outcomes.

## 6. Linearisation and acknowledgement points

The implementation must identify:
- the point at which a read's result is determined;
- the point at which a write becomes part of the transaction's private state;
- the serialization point of a committed transaction;
- the durable commit point;
- the point at which a client-visible response is produced.

These points may differ. In particular, the serialization order and persistence order must be compatible with recovery and the strict-serializability proof.

A successful durable-commit response is allowed only after the durable commit point. If the transport fails after that point, a status API using a stable transaction/idempotency identifier must resolve the outcome. Repeating the same commit request must not create a second logical transaction.

## 7. Abort, retry and cancellation

- An abort has no externally visible database writes.
- A retry is a new attempt with a distinct attempt identity but a stable logical request/idempotency identity where the application needs deduplication.
- Retry is not automatic for transactions with external side effects.
- Cancellation before CommitDecided requests abort and waits for a defined terminal outcome.
- Cancellation after CommitDecided cannot revoke the durable decision; the caller must query outcome.
- Resource exhaustion is a typed failure. It cannot silently drop an operation or report success.
- Deadlock detection/victim selection, if applicable, must be deterministic or expose its nondeterminism as an implementation policy; either way it must preserve safety and bounded resource use.

## 8. Scans and predicate conflicts

Point reads/writes alone are insufficient to define serializable relational transactions. Range scans, predicates, secondary indexes, uniqueness checks and inserts into scanned ranges create dependencies.

The model therefore treats each scan as a logical predicate read, not merely a list of returned keys. Implementations must show how they detect or prevent a concurrent transaction from inserting/deleting/updating a row that would change the scan's result at the transaction's serialization point.

The initial reference model should include:
- point read/write;
- unique-key insert;
- bounded range scan;
- range insert phantom;
- delete/update affecting a previously scanned predicate.

## 9. Independent history-checker requirements

The checker is not part of the database implementation and must not reuse its concurrency-control decision code.

Input:
- bounded history event sequence;
- initial database state;
- schema/value semantics;
- optional allowed incomplete-history policy.

Output:
- accepted plus a witness serial order; or
- rejected plus a counterexample (for example, a cycle in a dependency graph); or
- inconclusive if the configured state/solver budget is exhausted.

The checker must:
- validate event pairing and transaction program order;
- preserve real-time precedence;
- model atomic commit/abort;
- check point reads and predicate reads;
- enforce explicit limits on transactions, operations, keys and solver/search work;
- never report acceptance after truncating the search;
- produce deterministic results for deterministic inputs and limits;
- include mutation tests that deliberately introduce known anomalies.

The checker is an oracle for finite histories, not a proof of all possible implementation executions. Formal protocol verification and model-to-implementation conformance are separate obligations.

## 10. Initial anomaly corpus

At minimum, include executable histories for:

1. lost update;
2. dirty read;
3. non-repeatable read;
4. write skew under snapshot isolation;
5. phantom/range anomaly;
6. read skew / inconsistent multi-object observation;
7. stale write after a newer commit;
8. real-time order violation (strict-serializability failure despite a serial order);
9. duplicate commit after response loss;
10. abort racing with commit;
11. transaction timeout after durable commit;
12. crash after log append but before flush;
13. crash after durable commit record but before response;
14. crash during page flush;
15. repeated crash during recovery.

For each case, document whether it must be rejected by the target profile, what observation demonstrates the violation, and the expected checker result.

## 11. Proof obligations

The formal model should establish, for the declared finite/infinite abstraction:
- transition determinism where promised;
- preservation of well-formed transaction states;
- no visibility of uncommitted writes;
- atomic visibility of committed writes;
- abort invisibility;
- existence of a serialization order for all committed histories generated by the chosen protocol;
- preservation of real-time precedence;
- no conflicting terminal outcomes;
- bounded state/resource transitions where the model includes budgets.

The implementation proof chain is separate:
1. source transaction operations refine the abstract transaction API;
2. transaction manager refines the protocol model;
3. index/storage operations refine the storage abstract model;
4. durable log and recovery refine the crash/recovery model;
5. the platform persistence adapter satisfies its declared assumptions.

A proof of steps 1–4 does not establish the hardware or OS persistence guarantee in step 5.

## 12. Versioning and compatibility

This document is a candidate contract. Before marking it normative:
- review exact definitions of incomplete histories and real-time precedence;
- settle duplicate request and transaction identity semantics;
- settle whether commit response means durable commit for every supported durability mode;
- define value equality, key collation and scan ordering;
- define predicate semantics and isolation of metadata/catalogue reads;
- create positive and negative conformance vectors.

Any semantic change increments the transaction contract version and requires migration notes for stored data and clients where observable behaviour changes.
