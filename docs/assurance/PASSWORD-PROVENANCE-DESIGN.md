# Password provenance design

> Status: first fail-closed increment implemented on PR #238; exact-head CI pending. First-class Password remains a proposed follow-up for issue #232.
> This document separates properties Capstan can enforce from the application decision that identifies a value as a password.

## 1. Current weakness

The checker now rejects `Tainted` inputs to fast `hash()` and `hash_verify()` regardless of variable name. The `mentions_name()` heuristic also traverses method receivers and call arguments, closing the tested method/helper wrappers. Ordinary trusted strings with innocuous names can still reach a fast hash: the compiler cannot infer that an already-trusted string is a password without a semantic Password declaration.

`hash_password()` already uses PBKDF2-SHA256 with a fixed 600,000-iteration profile and a 256-byte input limit. The gap is not the KDF; it is the absence of reliable semantic provenance saying that a particular value is a password.

The compiler cannot infer from arbitrary bytes whether an application considers them a password. That role must be declared at an input/schema boundary. The language can then preserve the declaration and enforce the correct cryptographic operation.

## 2. Recommended layered design

### A. Fail-closed fast-hash boundary

Implemented in the current research branch: `hash()` and `hash_verify()` reject `Tainted` inputs independent of variable names. The diagnostic directs password data to `hash_password()` / `verify_password()`.

If a program genuinely needs a fast digest of non-password untrusted data (for example, a file checksum), it must make an explicit audited declassification using the existing `trust(value, reason)` escape hatch. This is deliberately stricter than treating all untrusted strings as safe for integrity hashing.

Implemented as defence in depth: password-name analysis traverses method receivers and helper-call arguments. Name scanning remains a heuristic for already-trusted strings; it is not the primary provenance guarantee.

### B. First-class `Password` type

Introduce an opaque `Password` type distinct from the existing generic `Secret` type.

- `password(value)` explicitly marks a value as a password at the application input boundary and returns `Password`.
- A dedicated `password_env("NAME")` may return `Password?` directly from an environment variable, using secret allocation. `secret_env()` remains the generic credential/token API.
- `hash_password(Password)` and `verify_password(Password, stored)` are the only ordinary password-hashing operations.
- `hash()`, `hash_verify()`, `secret_eq()`, printing, logging, interpolation, generic file output, command arguments and generic SQL parameters reject `Password`.
- Aliases, function parameters/returns, optionals, struct fields and collection elements preserve `Password` as a distinct type. It must not become `string` or `Tainted` through a helper, method or aggregate.
- The stored verifier remains an ordinary non-secret `string` with the current tagged algorithm/cost format; `needs_rehash()` remains applicable to that verifier.

`Password` is not a validator or sanitizer. It is a semantic declaration that the value is a human-chosen password and therefore requires a password KDF.

### C. Runtime memory contract

The runtime representation can remain a `CapStr*`, but the constructor must copy into the collector's secret allocation class (`cap_alloc_secret`), so the marked password object is zeroed when collected. It must never be printed or serialised by generic runtime helpers.

There is an important residual: converting an existing `Tainted` value by copying it leaves the original input buffer in ordinary GC-managed storage until collection. The implementation must state this explicitly. A future source API that reads directly into secret storage can avoid that extra ordinary copy. Do not claim deterministic erasure of registers, stack copies, the source buffer, or host-process environment copies.

## 3. Compatibility and migration

Before changing the checker, inventory all calls to `hash_password()` and `verify_password()`. Current examples and crypto tests pass `Tainted` or ordinary strings directly; they must be migrated to explicit `Password` construction or a deliberately retained compatibility overload with a documented evidence limit.

The C runtime already accepts a byte string for PBKDF2, so the native KDF need not change for the type-level first increment. The self-hosted compiler, stage-0 parser/builtins, generated C type mapping, tests and specification do need coordinated changes.

Do not silently retain an overload that lets an unmarked `Tainted` value reach password hashing while claiming first-class provenance. If a transition period is needed, make it an explicit deprecated API and keep the atlas verdict open until removed.

## 4. Required adversarial tests

Positive controls:
- ordinary non-password integrity hashing of trusted data;
- explicit audited fast hashing of a non-password `Tainted` value;
- password hashing and verification through `Password`;
- password values returned from helpers and stored in structs/lists.

Negative tests:
- `hash()` and `hash_verify()` on `Tainted`, regardless of innocuous variable name;
- fast hashing after string methods, helper calls, aliases, optional unwraps and collection/struct retrieval;
- fast hashing of `Password` through any helper or method;
- printing, interpolation, logging, file output, process arguments and generic SQL binding of `Password`;
- assignment or return that attempts to widen `Password` to `string`, `Tainted` or `Secret`.

Each test must assert the intended CWE diagnostic. The three formerly open CWE-916 atlas attempts now have compile-rejection outcomes, and an additional Tainted-input `hash_verify()` attempt is covered. Exact-head native and stage-0 CI is pending. The remaining semantic limitation is an already-trusted string with an innocuous name; first-class Password provenance is the proposed durable solution.

## 5. Claim boundary

The defensible future claim is:

> Once an application marks a value as `Password`, Capstan preserves that provenance through the checked language constructs and rejects ordinary fast hashing and generic disclosure sinks. Unmarked input is not automatically known to be a password; explicit application declarations and audited escape hatches remain part of the trust model.

This is stronger and more precise than claiming the compiler can infer password semantics from arbitrary input.
