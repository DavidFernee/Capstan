# Capstan-native verification

All executable verification artifacts for the C-free architecture are to be
written in Capstan, beginning with the CCAM machine and its conformance suite.

The initial machine design is in
[docs/architecture/CCAM.md](../docs/architecture/CCAM.md). The implementation
belongs in this directory as `.cap` source and must be runnable using the
existing Capstan compiler during the transition. The current compiler bootstrap
may still use its existing Python/C path to execute Capstan programs; that is a
temporary bootstrap dependency, not permission to implement the new machine in
Python or C.

## Required first slice

Implement in Capstan:
- signed-64 checked arithmetic and booleans;
- typed registers and explicit uninitialised state, rejecting unknown register type tags before register-file construction;
- branch and jump control flow;
- function calls and returns;
- explicit machine traps;
- deterministic instruction and call-depth limits;
- positive and negative conformance tests.

The tests must themselves be Capstan programs. Use the existing compiler's
`test` mode and repository test harness rather than introducing a second
implementation language. The normative JSON program/function/opcode schemas,
including closed field sets, `call.dst` nullability and explicit-trap reason
grammar, are defined in `docs/architecture/CCAM.md` and must be tested before
an evaluator accepts a program.

## Non-goals

Do not add a Python interpreter, C interpreter, or C runtime for CCAM. Do not
make the prototype part of the production runtime or trusted computing base.
Do not extend the machine to heap/GC, taint, secrets, grants, or IO until the
first slice is implemented and tested in Capstan.


## Bosun's Locker transaction-history model

[`bosuns_locker_history.cap`](bosuns_locker_history.cap) is the first executable
Bosun's Locker assurance artifact. It is a bounded Capstan-native oracle for
completed committed point-key histories. It enumerates candidate serial orders,
checks observed reads by replaying transactions atomically, enforces real-time
precedence, and returns one of:

- **accept** with a concrete serial-order witness;
- **reject** when no serial order satisfies the observations and real-time order;
- **inconclusive** when the explicit search-node budget is exhausted;
- **invalid** for malformed histories or inputs outside the supported bounds.

The current bounds are eight transactions, sixteen keys, thirty-two operations
per transaction and a caller-supplied search-node budget. This first slice
supports point reads and writes only. It does **not** yet model range predicates,
aborted or incomplete histories, concurrent storage execution, crash recovery,
durability, or a database implementation. Passing its tests is evidence for
the checker implementation on these bounded cases, not a proof that a database
engine is strictly serializable.

The standard `tests/run.sh` suite invokes this model directly with
`bin/capstan test`. Extend the independent anomaly corpus and formal
transaction semantics before using this checker as a release gate.
