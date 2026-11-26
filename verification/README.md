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

## Proposed v0.2 memory work

The v0.2 memory extension is specified separately in
[CCAM-MEMORY-EXTENSION.md](../docs/architecture/CCAM-MEMORY-EXTENSION.md).
The first executable artifact,
[ccam_memory_reservation.cap](ccam_memory_reservation.cap), models only the
pure checked reservation calculation and its failure-atomic result. It admits
only the v0.2 scalar layouts (one-byte bool and eight-byte aligned i64);
arbitrary aggregate layouts are rejected. It is not a region allocator, byte
store, capability implementation, or v0.2 evaluator. It deliberately reuses
the v0.1 checked arithmetic helpers.


The next Capstan-native artifact,
[ccam_memory_region_model.cap](ccam_memory_region_model.cap), models one region's
admission, owner-frame checks, generation-scoped view validation, reset and
close transitions. It is a single-region lifecycle model with injected
admission failure; it deliberately does not claim a byte store, a multi-region
aggregate ledger, opaque runtime capabilities, static linearity validation,
frame unwinding, or a v0.2 evaluator. The model is added to the standard test
runner, while the normative v0.1 machine remains unchanged.

## CCAM v0.2 bounded multi-region byte-store prototype

[ccam_memory_store_model.cap](ccam_memory_store_model.cap) adds an explicit,
Capstan-native reference model with a fixed maximum of eight region-table
entries and 4096 aggregate logical bytes. It supports bounded region admission,
aggregate accounting, deterministic admission-failure injection, slot reuse
after close, aligned reservations, generation/owner checks, reset/close, and
actual byte-vector storage. i64 uses explicit little-endian two's-complement
encoding; bool stores only 0/1 and loads reject noncanonical bytes.

[ccam_memory_oracle.py](../tests/keel/ccam_memory_oracle.py) is an independent
Python arbitrary-precision differential oracle. It generates fixed-seed
signed-64 vectors, compiles a Capstan driver, and compares every stored byte
and every reloaded value with Python's `int.to_bytes` model. The standard
runner executes both the Capstan adversarial tests and the oracle.

This remains a reference-transition prototype, not a v0.2 evaluator or
production allocator. The fail-after-byte parameter models failure at every byte-vector
initialisation boundary before state mutation; it does not catch host
allocation failure while constructing the Capstan `List<int>` backing vector. The model does not yet implement
opaque runtime capabilities, CFG linearity validation, call/return escape
rules, frame-unwind cleanup, bounded metadata allocation, or native lowering.


## CCAM v0.2 lifecycle CFG validator prototype

[ccam_memory_flow_validator.cap](ccam_memory_flow_validator.cap) adds a bounded,
Capstan-native abstract control-flow validator for region-register lifecycle
states. It checks use-before-create, use-after-close, live-capability overwrite,
normal-return leaks, malformed targets, reachable fallthrough and exact state
agreement at CFG joins. Its worklist processes each instruction once; equal
state loops converge, while lifecycle-changing loops that revisit a node with
a different state are rejected. The analysis is bounded to eight abstract
region registers and 4096 instructions.

This is an isolated validation model, not yet wired into CCAM program decoding,
the v0.2 opcode/type schema, or the evaluator. It additionally tracks bounded view registers, their owning region and
abstract generation, and invalidates derived views on reset/close. It
conservatively permits only one live view per region and rejects view-copy,
view-escape and call instructions. Interprocedural summaries and frame-unwind
cleanup remain outstanding. A trap
edge is treated as terminal only because cleanup is a required runtime
backstop; this prototype does not itself perform that cleanup. Passing these
tests is not a claim that the language currently enforces linear capabilities.


## CCAM v0.2 memory-safety contract and unwind model

The target language guarantee and mandatory release gates are specified in
[CCAM-MEMORY-SECURITY-CONTRACT.md](../docs/architecture/CCAM-MEMORY-SECURITY-CONTRACT.md).
The Capstan-native [frame-unwind model](ccam_memory_unwind_model.cap) tests
failure-atomic cleanup-set preflight, full-capacity wiping, frame-owner
isolation, idempotence and accounting. The multi-function evaluator
(ccam_calls.cap) now assigns monotonic frame identities and invokes this
transition on successful returns and machine traps, unwinding nested frames.
Integration tests seed regions into active frames and verify complete cleanup.
The evaluator still has no v0.2 memory opcodes, and the static capability
validator is not connected to its instruction schema. The security contract
must not be treated as achieved until the normative validator, memory
instructions, evaluator and proof gates are integrated and independently
verified.
