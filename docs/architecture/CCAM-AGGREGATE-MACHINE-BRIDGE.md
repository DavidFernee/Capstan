# CCAM Aggregate Register/Heap Execution Bridge

**Status:** experimental Capstan reference transition model; not normative CCAM v0.1  
**Implementation:** `verification/ccam_aggregate_machine.cap`  
**Depends on:** `verification/ccam_heap.cap`  
**Programme:** C-free compiler integration #458 and compiler-front-end workload #481

## Purpose

This increment moves the opaque process-lifetime region heap one step closer to machine execution. It composes heap operations with a typed register file and a shared instruction-step budget. Compiler-shaped values can therefore be represented as opaque references held in registers and traversed through typed record and array operations.

The compiler arena is process-lifetime storage. It is deliberately separate from frame-scoped scratch regions and does not introduce collection or individual free.

## Executable transition surface

The bridge currently models:

- typed integer, boolean and opaque-reference registers;
- record, typed-array and immutable-byte allocation;
- typed record field reads and writes;
- typed array append, indexed read/update and logical length;
- immutable byte allocation, byte length/index reads and failure-atomic concatenation;
- register initialisation checks and exact kind checks;
- arena-instance validation before a reference enters a register;
- step-budget admission before each aggregate operation;
- fail-closed traps for invalid registers, invalid references, type mismatches, heap limits and step exhaustion.

The underlying heap continues to enforce nominal record descriptors, reference-field descriptor constraints, array logical length, mutability, initialisation, allocation/work/temporary budgets and failure-atomic rejection.

## Evidence boundary

This is a Capstan-written executable reference bridge, not yet the canonical CCAM aggregate machine. In particular, it does **not** yet:

1. integrate the candidate aggregate opcode slice into the canonical, separately versioned CCAM instruction encoding, including immutable whole-program layout validation and byte/string construction;
2. extend `CCAMCallMachine` frames with reference-valued registers;
3. lower the production AST's `List<T>`, `Map<K,V>`, optional and string operations to aggregate instructions;
4. execute the aggregate profile in the freestanding x86-64 backend;
5. establish Lean preservation/refinement from aggregate instructions to heap transitions;
6. demonstrate that the production lexer/parser execute through aggregate CCAM.

The bridge tests are regression tests for this transition model only. They are not evidence of native-backend conformance, source-to-native type preservation, or C-free self-hosting.

## Next integration gates

1. Freeze the closed candidate opcode schema as a separately versioned aggregate profile and add the immutable whole-program layout table; do not alter CCAM v0.1.
2. Complete reference-valued register/frame semantics and whole-program validation, including descriptor provenance and exact field layouts.
3. Extend the executor to cover all admitted aggregate instructions and multi-frame calls; test aliasing, trap propagation and resource boundaries.
4. Prove reference provenance, descriptor safety, initialisation and failure atomicity in Lean; audit all proof axioms and connect the model to the implementation.
5. Implement identical aggregate operations in the native backend using checked handles, never source-controlled native pointers.
6. Implement the bounded List/Map/string library actually required by `compiler/ast.cap`, `compiler/lexer.cap` and `compiler/parser.cap`.
7. Execute those production modules through the aggregate evaluator and native backend against one deterministic valid/invalid corpus.
8. Keep #451 open until source-to-CCAM and CCAM-to-native preservation obligations are discharged.

No generated-C backend or C runtime is part of the aggregate execution contract. The existing generated-C compiler remains a temporary development and differential path, not an accepted bootstrap stage under the S0–S3 contract.
