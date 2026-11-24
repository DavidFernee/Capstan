# Capstan Language Semantics Extension Roadmap

**Status:** proposed sequencing for the C-free architecture  
**Principle:** no feature enters the supported machine subset before its semantics, tests and assurance obligations are explicit.

## Stage 0 — Scalar typed core (current target)

**Features:** `int`, `bool`, local variables, direct calls, returns, branches/jumps, checked arithmetic, comparisons and explicit traps.

**Required outcomes:**
- complete CCAM structural validator and evaluator in Capstan;
- canonical CCAM instruction schemas and small-step semantics;
- source-core-to-CCAM lowering contract;
- exact arithmetic, operand-order, call/return and resource-limit conformance vectors;
- machine-checked register preservation, progress-or-trap and determinism results.

**Exit gate:** evaluator, conformance suite and proof model agree on every vector; all accepted source-core programs lower to validated CCAM; no C evaluation-order or overflow behaviour is observable.

## Stage 1 — Source lowering and compiler correctness

**Features:** source declarations, expressions, structured control flow, functions and supported scalar operators lowered into the Stage 0 machine.

**Required outcomes:**
- a typed source-core definition independent of AST implementation details;
- a front-end typing judgement and rejection rules;
- a translation from checked source-core programs to CCAM;
- preservation of result values, traps, trap order and observable effects;
- differential tests for source evaluation order and compiler adversarial cases.

**Exit gate:** accepted source-core programs cannot generate malformed CCAM; source-to-CCAM preservation has machine-checked or equivalently rigorous evidence with explicit assumptions.

## Stage 2 — Aggregate memory and object identity

**Features:** structs, enums, optionals, strings as immutable byte objects, lists and maps.

**Required outcomes:**
- abstract heap and location domains; explicit object identity and aliasing;
- field and element layout rules, allocation, read/write and bounds-check transitions;
- option/tag/payload validity and exhaustive-match guarantees;
- collection mutation sequencing and iterator/insertion-order rules;
- GC root model covering registers, frames, globals and temporary values;
- pointer classification, allocation-size overflow checks and heap-limit accounting.

**Exit gate:** no source program in the supported subset can forge a reference, read outside a live object, confuse object layouts, use a reclaimed object or corrupt collector roots; tests include GC stress and adversarial aliasing.

## Stage 3 — Information-flow types and text contexts

**Features:** `Tainted`, `Html`, `LogText`, interpolation, validators and context-specific escapers.

**Required outcomes:**
- taint propagation rules for every operation and aggregate storage path;
- explicit validation/declassification transitions;
- distinct sink contexts for HTML, logs, CSV, JSON, SQL and process arguments;
- rules preventing implicit conversion from tainted or context-escaped values to unrelated trusted types;
- tests for decoding, concatenation, slicing, formatting, generic substitution and nested aggregates.

**Exit gate:** every value reaching a security-sensitive sink has a statically justified type/context, or passes through an explicit audited escape hatch.

## Stage 4 — Secrets and side-channel contracts

**Features:** opaque `Secret` values, environment import, secret comparison, password hashing and zeroisation.

**Required outcomes:**
- secret representation and permitted-operation rules;
- no implicit formatting, logging, printing, concatenation or ordinary equality;
- explicit copy and lifetime semantics;
- allocator/OS zeroisation contract, including pages, metadata, copies, registers and reclamation;
- timing and length-leakage statements for each cryptographic operation;
- cryptographic conformance vectors and adversarial memory tests.

**Exit gate:** claims are limited to the actual proven threat model. In particular, a wipe-before-free operation is not described as guaranteed erasure unless allocator and OS behaviour are included in the evidence.

## Stage 5 — Policies and grants

**Features:** policy functions, `Grant<P>`, `authorize` and protected calls.

**Required outcomes:**
- unforgeable grant value and representation;
- policy parameter role-binding rules, including identity vs value equality;
- exact revalidation point and state observed by a protected call;
- grant lifetime and prohibited storage/escape rules;
- failure-closed semantics for stale, missing, ambiguous and over-capacity grant state;
- policy tests, mutation testing and proof of grant-check preservation through optimisation.

**Exit gate:** every protected operation is reachable only through a valid grant and its required revalidation; compiler transformations cannot erase or misbind the check.

## Stage 6 — IO, capabilities and external effects

**Features:** file, directory, network, process, SQL and environment APIs.

**Required outcomes:**
- explicit capability values and authority attenuation;
- effect signatures for every external operation;
- path, host, argument and query parameter semantics;
- deterministic result/error mapping and resource limits (bytes, timeouts, handles, output);
- no ambient authority in ordinary code;
- test doubles and adversarial host-boundary conformance.

**Exit gate:** an operation cannot exceed the capabilities passed to it, and every external effect is explicit in the typed program and machine semantics.

## Stage 7 — Generics, closures and error values

**Features:** interfaces/generics, monomorphisation, by-value closures and `Result<T, E>`.

**Required outcomes:**
- type-variable and interface constraint validation before monomorphisation;
- concrete instance validation after substitution;
- closure capture-set, snapshot and aliasing semantics;
- recursive closure conversion and environment layout;
- explicit result propagation and exhaustive error handling;
- proof that generic substitution and closure capture preserve taint, secret and grant restrictions.

**Exit gate:** generated instances and closure environments are type-safe, have defined lifetimes, and cannot bypass information-flow or authorisation constraints.

## Stage 8 — Concurrency

**Features:** tasks, channels, async IO, locks and shared state.

**Required outcomes:**
- memory model and happens-before relation;
- ownership transfer and borrow/lock invariants;
- data-race freedom and deadlock/resource policy;
- cancellation, task failure and shutdown semantics;
- deterministic tests where possible and stress/model-checking where scheduling is nondeterministic.

**Exit gate:** the supported concurrency subset has a precise memory model and evidence for race freedom, authority isolation and resource accounting.

## Cross-stage rules

Every stage must publish:
1. normative syntax/type/value/effect rules;
2. small-step machine transitions and trap precedence;
3. resource bounds and failure behaviour;
4. positive, negative, boundary and adversarial tests in Capstan;
5. proof obligations and exact evidence status;
6. source lowering and backend refinement obligations;
7. migration/compatibility notes for existing programs.

A feature may be implemented experimentally before its stage is complete, but it MUST remain outside the claimed safe C-free subset. Stage completion is a conjunction of specification, implementation, tests and evidence—not a documentation milestone alone.
