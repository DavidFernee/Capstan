# Capstan Language Safety Invariants

**Status:** normative invariant catalogue proposal  
**Scope:** safety properties that the language, typed core, machine, compiler and runtime must preserve  
**Important:** listing an invariant is not evidence that it is currently implemented or proved.

## 1. Assurance vocabulary

Capstan distinguishes four kinds of statement:

- **Specified:** a normative rule exists.
- **Implemented:** the current compiler/runtime enforces the rule on the supported path.
- **Tested:** a regression or conformance test exercises it.
- **Proved:** a machine-checked theorem establishes it under disclosed assumptions.

These statuses are independent. A rule can be specified but not implemented, implemented but not tested, or tested without a proof. No assurance claim may promote a property from one status to another implicitly.

## 2. Core type and value invariants

For every validated CCAM state:

1. **Value typing:** every initialised register contains a value of its declared type.
2. **Initialisation:** reading an uninitialised register cannot yield a fabricated default value; it produces a defined trap.
3. **Type separation:** booleans and integers remain disjoint; no representation-level aliasing permits a bool to be read as an int or vice versa.
4. **Index validity:** every register access is within the validated register vector.
5. **Integer range:** every observable integer value is within signed-64 range.
6. **Control-flow validity:** the active PC is within the active function; branch targets and call targets are validated before execution.
7. **Frame integrity:** calls and returns preserve caller/callee ownership of frames and result destinations.
8. **Determinism:** a fixed validated program, entry arguments and resource limits determine one transition sequence and one terminal outcome.

These are the first preservation/progress theorem targets.

## 3. Evaluation and effect invariants

1. Every source-level observable expression is evaluated in its specified order.
2. A trap prevents all subsequent effects in the expression/statement.
3. Each assignable location is evaluated exactly once for assignment; compound assignment reads the old value before evaluating the RHS and writes only after successful computation.
4. Short-circuit operators do not evaluate a suppressed RHS.
5. Calls receive fully evaluated arguments in source order.
6. A failed dynamic operand read prevents later operand reads.
7. An instruction that traps does not partially update a destination or caller-visible state.

A compiler pass may reorder operations only where it proves the reordering observationally equivalent under the effect model.

## 4. Arithmetic invariants

1. Checked arithmetic returns the exact mathematical result when representable and otherwise traps with the specified code.
2. Division and remainder by zero trap.
3. Signed division truncates toward zero.
4. `INT64_MIN / -1` traps; `INT64_MIN % -1` returns zero.
5. Shifts validate counts before execution; no host shift with an invalid count is permitted.
6. Wrapping operations are explicit operations and cannot be substituted for checked operations.
7. No compiler optimisation may eliminate a check unless its proof assumptions are valid at every execution point where the operation occurs.

## 5. Memory and aggregate invariants — deferred machine extension

These properties are required before the C-free machine can claim memory safety for structs, strings, lists, maps, optionals or closures:

- **Bounds:** every indexed access is within the live logical length, not merely allocated capacity. For compound assignment, the old-value read and final write are separate accesses; bounds/liveness must be revalidated or soundly proved preserved after the RHS because it may mutate the aggregate. A pre-RHS range proof alone cannot justify an unchecked post-RHS store.
- **Lifetime:** every dereferenced object is live for the duration of the access.
- **Representation:** each object layout and field offset agrees with its declared type.
- **Aliasing:** object identity and shared mutation are explicit; no optimisation may assume uniqueness without proof.
- **Mutation order:** collection reads/writes and user effects preserve source sequencing.
- **GC roots:** every live reference held by registers, frames, globals, closures and runtime temporaries is visible to the collector.
- **Pointer classification:** pointer-free and pointer-containing allocations are never confused.
- **Allocation accounting:** size arithmetic is checked before allocation; failed allocations do not corrupt heap accounting.
- **No forged references:** source programs cannot manufacture arbitrary addresses or reinterpret integers as references.

The initial scalar CCAM does not establish these properties. Heap/GC and aggregate instructions must not be added as informal runtime helpers; they require explicit abstract state and transition rules.

## 6. Information-flow and secret invariants — deferred machine extension

The current source language has distinct `Tainted`, `Html`, `LogText`, `Secret` and `Grant<P>` types. Their safety properties must be carried into typed IR and machine semantics, not erased during lowering.

Required properties include:

- **Taint preservation:** untrusted bytes remain tainted through concatenation, interpolation, slicing, decoding and aggregate storage unless a specified validator or context-appropriate escaper changes the type.
- **Contextual output safety:** HTML, log, CSV, JSON, SQL and process-argument safety are distinct contexts; an escape for one context is not a universal sanitiser.
- **Secret non-disclosure:** secret values cannot flow to ordinary output, formatting, logging, comparison or hashing operations except through explicitly permitted APIs.
- **Secret comparison contract:** timing/length leakage assumptions are explicit; equal-length content comparison does not imply length hiding.
- **Secret lifetime:** zeroisation guarantees specify the exact memory region, allocator/OS assumptions, copies, registers, crash paths and reclamation semantics. A source-level wipe call alone is not proof of erasure.
- **No laundering:** conversions, generic substitutions, closure captures, enum payloads and aggregate fields cannot silently discard taint/secret qualifiers.

## 7. Authorisation invariants — deferred machine extension

For grants and protected operations:

1. Grants are unforgeable values produced only by successful authorisation.
2. A grant is bound to the exact policy argument roles and values/identities specified by the language.
3. Protected calls revalidate the policy at the specified point; stale authorisation cannot be reused after the relevant state changes.
4. Grant values cannot be copied into unsupported storage locations or escape their permitted lifetime.
5. The compiler cannot omit a grant check based solely on an untrusted or stale analysis fact.
6. Failure is closed: malformed, missing, ambiguous, over-capacity or stale grant state denies access or is rejected before execution.

The initial CCAM has no grant representation; none of these properties follows from scalar register typing.

## 8. Resource and availability invariants

Every operation influenced by untrusted input must have an explicit resource contract covering relevant dimensions: bytes, elements, nesting, CPU steps, recursion/call depth, open handles, memory and time.

- Limits have exact inclusive/exclusive boundaries and deterministic failure behaviour.
- Size arithmetic is checked before allocation or indexing.
- A process-wide heap limit is not a substitute for a per-input bound where callers need to recover from oversized input.
- Validation of an untrusted machine program is itself resource-bounded.
- Algorithmic complexity claims require adversarial tests, not only typical-case benchmarks.
- Limit failure occurs before the prohibited allocation, state mutation or external effect.

CCAM v0.1 initially accounts instruction steps and call depth only. It does not establish heap, IO or wall-clock bounds.

## 9. Compiler and backend preservation obligations

For every accepted source program in the supported subset:

1. **Front-end soundness:** accepted source is well-typed and satisfies the source static constraints.
2. **Lowering preservation:** source evaluation corresponds to CCAM evaluation, including result values, trap kind, trap order and observable effects.
3. **IR validation:** emitted CCAM is structurally valid; the evaluator never has to guess what malformed instructions mean.
4. **Optimisation preservation:** each pass preserves the defined observable behaviour and safety invariants.
5. **Backend refinement:** native execution simulates CCAM execution and preserves halt values, traps, effect order and relevant resource semantics.
6. **Bootstrap transparency:** bootstrap components and the trusted computing base are documented; temporary C/Python bootstrap machinery is not silently treated as a semantic guarantee.
7. **Evidence freshness:** proofs and tests are tied to exact source revisions, toolchain versions and assumptions.

## 10. Initial proof order

The recommended order is:
1. CCAM program validator soundness and totality;
2. typed register preservation;
3. progress-or-defined-trap for machine states;
4. call/return frame integrity;
5. arithmetic correctness;
6. deterministic execution;
7. source-core-to-CCAM preservation;
8. native backend simulation;
9. memory/GC invariants;
10. information-flow, secrets and authorisation;
11. resource and concurrency properties.

This order intentionally proves the small scalar machine before claiming safety for features it does not model.
