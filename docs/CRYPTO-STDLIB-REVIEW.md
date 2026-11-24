# Cryptographic standard-library review

**Status:** independent API/security review, 24 November 2026. Review-only: no cryptographic implementation or test files changed. This document assesses the current `lib/crypto.cap` public helper surface and its tests, and additionally inspects the runtime password-verifier boundary; it does not certify the implementation or replace a cryptographic audit.

## Scope and evidence

Reviewed:

- `lib/crypto.cap`: `sha256`, `hmac_sha256`, `pbkdf2_sha256`, byte conversion and hex formatting helpers.
- `tests/crypto/vectors.cap` and `tests/crypto/check.py`: published vectors, deterministic generated inputs, Python `hashlib` differential checks, stage-0 agreement, and comparison with runtime `hash()` / `hash_password()`.
- `runtime/capstan_rt.h`: `cap_verify_password()`, `cap_pbkdf2()`, and `cap_needs_rehash()`.
- `tests/unit/test_runtime.c`: malformed password-record checks and PBKDF2/password-hash vectors.
- `docs/SPEC.md`: built-in password hashing uses PBKDF2-SHA256 with 600,000 iterations; the low-level library API is separate from those builtins.

The test suite is valuable evidence of functional agreement over its exercised domain. It is not evidence of resistance to hostile parameter choices, secret erasure, constant-time execution, or cryptographic-module validation.

## Findings

### C1 — PBKDF2 work is not bounded by an enforceable policy (high)

`pbkdf2_sha256(password, salt, iterations, dklen)` rejects `iterations < 1`, but has no upper bound on iterations. Its loop performs work proportional to the caller-supplied iteration count. It also permits up to 1 MiB of derived output; PBKDF2 computes a separate block for each 32 output bytes, so the permitted output size multiplies the expensive iteration work by as many as 32,768 blocks.

This is a resource-exhaustion hazard if an application passes untrusted or policy-controlled values to the helper. A heap ceiling does not bound CPU time. A single synchronous call has no cancellation or deadline.

**Recommendation:** replace the raw parameter surface with validated parameters that carry an explicit work budget and conservative upper bounds for iterations and output length. The password-hashing API should use a fixed, versioned cost policy rather than accept a request-controlled cost. Once `Result<T,E>` is available, reject invalid/excessive parameters with a typed error; do not encode failure as an empty byte list. Add tests at each accepted maximum and immediately above it. The exact maxima should be chosen against supported platforms and measured worst-case latency, not guessed in this review.

### C2 — Salt length can amplify work across PBKDF2 output blocks (high)

For each output block, `pbkdf2_sha256` constructs `first` by copying the entire salt with `concat_bytes(salt, new List<int>())`, then appends the four-byte block counter. With a large salt and a large derived output, this repeatedly copies the same attacker-influenced input. The function has no explicit salt or password length limit.

**Recommendation:** validate password and salt lengths before work begins; impose a small, documented maximum salt length appropriate to the API; avoid copying the salt for every output block where the implementation can safely stream or reuse a bounded buffer. Include large-salt / maximum-output stress tests and assert a predictable upper bound on work and allocation.

### C3 — Invalid byte values are silently truncated rather than rejected (medium)

The documented representation is `List<int>` with each element in 0..255. `sha256` nevertheless applies `& 0xFF` to every message element, and the HMAC/PBKDF2 paths ultimately hash values through the same low-byte behaviour. An accidental value such as -1 or 256 is therefore silently mapped to a byte instead of producing an invalid-input result.

This is not a SHA-256 algorithm mismatch; it is an API-contract ambiguity that can conceal caller bugs or inconsistent input canonicalisation.

**Recommendation:** introduce a byte-specific validated representation when the type system permits it, or validate every element at the public boundary and return a typed invalid-byte error. Keep an explicitly named truncating conversion only if modulo-256 behaviour is genuinely needed. Add negative and greater-than-255 input tests.

### C4 — Password and key material use ordinary lists, not secret-aware values (medium)

The low-level APIs accept and return ordinary `List<int>` values. The language specification describes special handling for `Secret`, but this library interface does not accept a `Secret` or establish that its intermediate lists are secret-protected. Passwords, HMAC keys, derived key material and intermediate state can therefore be copied, retained and exposed through ordinary list operations unless the caller takes additional precautions.

The repository's statement that secret memory is zeroed when collected must not be extended to ordinary lists. Nor would collection-time wiping establish prompt erasure: collection timing is nondeterministic.

**Recommendation:** clearly document these functions as low-level byte primitives that do not provide secret-lifecycle guarantees. Design a separate secret-aware facade after the standard library's secret and ownership contracts are agreed. Do not claim deterministic erasure or constant-time behaviour without compiler/runtime and platform evidence. Keep formatting, logging and generic serialization APIs from accepting secret values implicitly.

### C5 — Error signalling is ambiguous (medium)

For `iterations < 1`, `dklen < 1` or `dklen > 1,048,576`, `pbkdf2_sha256` returns an empty list. That is currently distinguishable from a successful result because successful `dklen` is at least one, but it does not identify the failure and is easy for callers to ignore or mis-handle.

**Recommendation:** use the agreed `Result<List<int>, CryptoError>` contract when the v0.5 type-system work is ready. Distinguish invalid parameters, resource-budget exceeded and provider/implementation failures where applicable. Do not introduce a second optional/empty-list error convention.

### C6 — Runtime password verification accepts non-canonical records and a very high attacker-selected work factor (medium)

The runtime verifier parses the iteration count with `strtol` and accepts values up to 100,000,000, although newly generated records use the fixed 600,000-iteration policy. This is a 166.7-fold work-factor increase over the current policy for a single verification attempt. If an attacker can influence stored password records (for example through a writable credential store or imported account database), a syntactically valid record can force substantial synchronous CPU work. The existing test rejects an overflowing decimal count, but does not pin a policy-level maximum close to the current cost.

There is also a length/canonicalisation issue: `cap_verify_password()` uses `strlen(p)` to validate the salt/digest suffix rather than comparing the parsed fields against the enclosing `CapStr.len`. A record containing a valid textual record followed by an embedded NUL and additional bytes can therefore be accepted while the bytes after the NUL are ignored. This does not bypass the password check, but it means verification is not a validation of the complete stored value and can create inconsistencies between components that compare or preserve the full length-bearing string.

**Recommendation:** define an explicit accepted verification-cost policy (including any intentional legacy range) and reject costs above it before PBKDF2 work. Parse the complete `CapStr` by length, reject embedded NUL and trailing bytes, and require a canonical decimal cost representation. Add tests for costs just above the policy limit, leading signs/whitespace/zero padding if non-canonical forms are to be rejected, and valid-record-plus-NUL-plus-suffix inputs. Keep any compatibility range deliberate and documented rather than using a very large defensive ceiling.

## Test coverage assessment

Current positive evidence:

- SHA-256 FIPS 180-4 examples, including long messages.
- Every message length from 0 through 200 and deterministic longer messages.
- HMAC keys shorter than, equal to and longer than the 64-byte block.
- PBKDF2 differential cases with 1–20 iterations, password lengths 0–79, salt lengths 0–39 and derived lengths 1–100.
- One runtime `hash_password()` interoperability check at 600,000 iterations.
- Native and stage-0 comparison with Python's `hashlib`.
- Runtime password verifier tests for wrong passwords, tampering, empty/malformed tags, zero cost and an overflowing cost field.

Material missing cases for a security-oriented API:

- zero, negative, maximum and above-maximum iteration/output parameters;
- very large password and salt inputs and aggregate work limits;
- invalid byte values (<0 and >255);
- failure-path assertions (including that callers cannot mistake failure for valid output);
- runtime verifier policy-boundary and complete-length/canonical-record tests;
- secret-flow tests for accidental formatting/logging/serialization, once a secret-aware facade exists;
- resource/time budget tests on the slowest supported target.

The current deterministic generator in `tests/crypto/vectors.cap` is appropriate for reproducible differential testing. It is not a cryptographically secure random generator and must never be repurposed to generate salts, nonces or keys.

## Release recommendations

1. Keep the current implementation labelled as a tested in-language implementation, not a certified or independently audited cryptographic module.
2. Do not expose `pbkdf2_sha256` directly to untrusted parameters until C1/C2 have enforceable limits and typed errors.
3. Keep the runtime password-hashing builtins' fixed, tagged cost policy separate from this general low-level primitive; test that verification rejects malformed and excessive encoded costs before doing expensive work.
4. For encryption and random generation, select a reviewed provider or well-reviewed implementation. Do not add a home-grown AEAD, nonce generator or DRBG.
5. Coordinate any changes to `lib/crypto.cap` and `tests/crypto/` with the T1 standard-library migration owner; this review intentionally does not edit those files.

## Overall assessment

The current tests establish useful algorithmic agreement for SHA-256, HMAC-SHA256 and PBKDF2-HMAC-SHA256. The principal gap is at the API boundary: a correct primitive can still be unsafe when callers can request excessive work, supply unbounded inputs, pass invalid byte values silently, mistake ordinary byte lists for secret-protected storage, or provide non-canonical password records. Those boundaries should be fixed before these helpers are promoted as general-purpose security APIs.
