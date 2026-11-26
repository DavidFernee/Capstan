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


## Bosun's Locker transaction assurance models

- `bosuns_locker_history.cap` is a bounded strict-serializability oracle for completed committed point-key histories. It returns an explicit serial-order witness, rejection, invalid-input result or budget-exhausted inconclusive result.
- `bosuns_locker_protocol.cap` models transaction lifecycle, recovery idempotence and WAL/page persistence ordering.

These are executable reference models, not an implemented database, durable WAL, recovery engine or implementation-refinement proof. Bounds and unsupported history classes are documented in the source and Bosun semantics contract.
