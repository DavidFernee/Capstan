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

## CCAM JSON boundary

The candidate bounded JSON decoder is in `ccam_json.cap`. It parses tainted input, rejects duplicate object keys and malformed Unicode, enforces explicit resource ceilings, decodes only the closed v0.1 program schema, and invokes the multi-function validator before machine construction. Its conformance tests are part of `tests/run.sh`.

The decoder's `trust()` boundary is deliberately explicit and documented in `docs/architecture/CCAM-JSON-DECODER.md`. Treat that boundary as security-review material; do not expand it to filesystem paths, commands, source code or other external sinks. The decoder does not accept the unversioned v0.2 `emit_bytes` opcode.

## Non-goals

Do not add a Python interpreter, C interpreter, or C runtime for CCAM. Do not
make the prototype part of the production runtime or trusted computing base.
Do not extend the machine to heap/GC, taint, secrets, grants, or IO until the
first slice is implemented and tested in Capstan.

## Formal semantic correspondence

The Lean package currently models a finite single-frame machine fragment and
an abstract runtime-register bridge. It does **not** yet model the executable
multi-function JSON decoder, call-frame evaluator, or complete CCAM state.
The M2 proof contract and exact gap analysis are in
[CCAM-M2-SEMANTIC-CORRESPONDENCE.md](../docs/architecture/CCAM-M2-SEMANTIC-CORRESPONDENCE.md).

Do not infer whole-machine verification from the existing single-frame proofs.
The first multi-function formal increment now lives in
`CapstanVerification.CallPreflight`: it models ordered argument admission,
initialisation/type checks, arity rejection (including a theorem that successful
argument validation preserves declared arity), and exact return-destination
compatibility before a frame can be created. Its scope is deliberately narrow:
it does not yet model a frame stack, program counter, return continuation,
resource accounting, or implementation refinement. The next increment is a
validated multi-function program and small-step frame semantics, followed by
call/return simulation lemmas. `CapstanVerification.MultiFunctionMachine` now
introduces an explicit activation-frame record, caller continuation, bounded
multi-frame state, and budgeted callee push / nested-frame pop operations. Its
proved properties cover active-frame installation, caller-suffix preservation,
stack-depth changes, counter accounting, and restoration of the caller frame.
It remains a control-state abstraction: it does not yet execute instructions
or establish evaluator refinement. The return fragment now validates the
saved caller identity, return shape and runtime value type before updating the
caller PC/register file; out-of-range destinations trap, and successful
register replacement preserves register-file length. The model does not yet
connect frame register lists to the indexed typed-register invariant in
`Machine`, nor does it prove that the executable evaluator follows these
transitions. Decoder/validator acceptance agreement must be tested against
shared fixtures; matching field names is not a refinement proof.
