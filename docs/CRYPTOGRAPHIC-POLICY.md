# Cryptographic policy

**Status:** Proposed policy for review; not a cryptographic certification  
**Applies to:** Capstan language builtins, standard library, runtime and future cryptographic providers  
**Owner:** Security architecture / standard-library workstream

## 1. Policy objectives

Capstan must use established cryptographic constructions, expose misuse-resistant APIs, bound attacker-influenced work, preserve algorithm agility and state its assumptions honestly. Cryptographic code is security-critical even when written in a memory-safe language: arithmetic, encoding, parameter parsing, nonce management, side channels and key lifecycle remain relevant.

This policy does not certify any implementation or provider. It is a normative direction pending review by the language, runtime, T1 standard-library and formal-verification owners.

## 2. Approved construction families

| Purpose | Construction | Policy |
|---|---|---|
| General-purpose collision-resistant digest | SHA-256 or stronger approved SHA-2/SHA-3 member | SHA-256 is acceptable for current integrity tagging and HMAC/PBKDF2 use. Do not use a bare digest as a password hash or MAC. |
| Message authentication | HMAC-SHA-256 or stronger approved HMAC | Prefer a reviewed provider where practical. Compare fixed-length tags without content-dependent early exit. |
| Password-based key derivation | PBKDF2-HMAC-SHA-256, or a reviewed memory-hard password KDF where deployment policy permits | Parameters must be versioned, explicit, bounded and calibrated to the deployment. |
| Authenticated encryption | A reviewed AEAD construction such as AES-GCM or ChaCha20-Poly1305 | Not yet exposed as a Capstan standard API. Do not implement a bespoke mode or combine encryption and MAC ad hoc. |
| Randomness | Operating-system CSPRNG or reviewed provider interface | No PRNG, timestamp, process ID or map hash key may be repurposed as application cryptographic randomness. Fail closed on entropy failure. |

Algorithm selection must be revisited against the current Australian Government ISM/ASD guidance, relevant NIST publications and deployment requirements before a release claims approved-cryptography alignment. Algorithm names alone do not imply module validation.

## 3. Password hashing and PBKDF2

- Password storage must use a password-hashing/KDF API, never `hash()`, SHA-256 or HMAC directly.
- The current runtime generation profile is PBKDF2-HMAC-SHA-256, 600,000 iterations, a fresh 16-byte random salt and a 32-byte derived key. Treat this as the current format profile, not a universal forever-value.
- Encoded records must carry a strict algorithm identifier, parameter version, iteration count, salt and derived-key encoding. Parsing must reject non-canonical, truncated, oversized, overflowed and trailing data.
- **Every cost parameter must have both a minimum policy and a hard maximum work budget.** A stored record is untrusted input. The verifier must not accept an arbitrary iteration count simply because it fits an integer.
- Password byte length is also a KDF cost parameter. Enforce a conservative maximum before hashing or verification begins. In the current runtime, HMAC key normalisation re-hashes a password longer than 64 bytes on every PBKDF2 iteration; until the implementation precomputes the keyed HMAC states once, this creates a multiplicative CPU amplification. A 1 MiB password can cause roughly 16,384 SHA-256 compression blocks of key-normalisation work per HMAC invocation, repeated across the KDF.
- The current C runtime verifier accepts iteration counts up to 100,000,000 despite generating at 600,000. This ceiling is not accepted as a suitable resource policy and must be reduced to a documented, calibrated ceiling.
- The Capstan-native `pbkdf2_sha256()` currently has no maximum iteration count, no salt/password size limits and a 1 MiB derived-output ceiling. That API does not yet meet this policy.
- A work budget must account for iteration count multiplied by PBKDF2 output blocks, plus input sizes and concurrent requests. Per-request limits do not replace process-wide admission control or rate limiting.
- Rate limiting, concurrency control and account lockout are application/service concerns and must be separately designed; expensive hashing alone is not a rate limiter.
- Verification must compare the fixed-length derived key without data-dependent early exit. The encoded cost and format may be parsed before derivation; parsing and error behaviour must not expose password-dependent distinctions.
- Parse encoded records using the enclosing byte length, not C-string termination. Reject embedded NUL, trailing bytes, malformed fields and non-canonical numeric encodings before invoking PBKDF2. A syntactically valid prefix must never legitimise unparsed suffix bytes.
- A lower-cost legacy record may be verified only under an explicit migration policy and should trigger rehash. The application must not silently treat `needs_rehash()` as optional where policy requires upgrade.

## 4. Input and output limits

All public cryptographic entry points must define:

- maximum password/key length;
- maximum salt length and minimum salt entropy/length for the construction;
- exact output length or a small documented range;
- allowed iteration/cost range;
- maximum aggregate work and allocation;
- malformed input behaviour;
- concurrency/admission expectations where used in a service.

Reject invalid parameters before allocating large buffers or beginning expensive computation. Invalid parameters must return a distinguishable error under the agreed `Result<T,E>` model; an empty byte list must not ambiguously mean both a valid result and invalid request.

Byte-oriented interfaces must validate every element is in 0..255, or use a byte type that makes out-of-range values unrepresentable. Do not silently mask arbitrary integers into bytes at an API boundary.

## 5. Key and secret lifecycle

- Secret keys, passwords and intermediate key material must use secret-aware storage, not ordinary general-purpose collections, where the runtime can provide a meaningful isolation/wipe contract.
- Minimise copies and lifetime. Wipe temporary key material on all success and failure paths using a non-elidable primitive with platform/compiler evidence.
- Audit callee-local cryptographic scratch as well as caller-owned buffers. Wiping an outer HMAC state does not erase message schedules or working variables created inside the SHA-256 compression function. Verify wipe behaviour in optimised machine code for each claimed compiler/target.
- Garbage-collection-time wiping is a fallback for reclaimed secret allocations, not deterministic destruction. Do not promise when collection occurs.
- Document that environment variables may remain in the host process environment after copying into a Capstan Secret.
- Do not claim erasure from registers, compiler spills, swap, crash dumps, hibernation images, hardware caches or physical media without separate platform controls.
- Keep secret values out of logs, diagnostics, formatting, panic messages, serialization and error details.
- Secret comparisons must state whether length is observable. A fixed-length comparison does not become length-hiding merely because its byte loop is constant-work.

## 6. Randomness

- Use the operating system's cryptographically secure random source or an independently reviewed provider.
- Failure to obtain the requested number of bytes is a hard failure; never fall back to a time-seeded or predictable generator.
- Random API contracts must specify blocking behaviour, failure behaviour, platform coverage and whether output is suitable for keys, salts, nonces or identifiers.
- Salts need uniqueness/unpredictability appropriate to the KDF. AEAD nonces have construction-specific uniqueness requirements and must never be generated by an ad hoc counter without persistent uniqueness guarantees.
- Per-process SipHash keys protect hash-table collision resistance; they are not a general-purpose random API.

## 7. Authenticated encryption

No public `seal()`/`open()` API is currently established. Before introduction:

- choose an established AEAD construction and reviewed implementation/provider;
- bind algorithm/version, nonce, tag and associated-data semantics in a canonical envelope;
- require unique nonces per key where the construction requires it;
- define key separation, rotation, key identifiers and failure handling;
- reject truncated tags and malformed envelopes before releasing plaintext;
- ensure decryption does not expose unauthenticated plaintext;
- bound ciphertext, plaintext and associated-data sizes;
- test published vectors, tampering, truncation, nonce reuse handling, cross-version decoding and independent implementations.

Do not design a custom encryption mode or invent cryptographic primitives.

## 8. Provider and assurance requirements

For each implementation/provider, record:

- exact algorithm and parameter profile;
- implementation name, version, build options and platform;
- source and supply-chain provenance;
- published vectors and independent differential tests;
- fuzzing and malformed-input tests;
- side-channel/constant-time evidence and its target/compiler scope;
- key/temporary erasure evidence;
- known limitations and unsupported platforms;
- whether a validated cryptographic module is used.

FIPS 180-4 or RFC conformance is not FIPS 140-3 module validation. A self-implemented primitive, even with passing vectors, must not be described as validated or independently audited.

### Additional current implementation gaps

- Runtime `hash_password()` and `verify_password()` do not enforce a maximum password byte length. Because `cap_hmac_sha256()` re-hashes keys longer than 64 bytes on every PBKDF2 iteration, long attacker-influenced passwords can amplify the intended KDF cost dramatically. The implementation should both enforce a password-size limit and precompute the keyed HMAC states once per derivation.
- Runtime `cap_sha256_block()` has local message-schedule and working-state scratch that is not explicitly wiped, despite caller-side wiping in `cap_hmac_sha256()`.
- Runtime `cap_verify_password()` uses NUL-terminated string parsing over a length-bearing `CapStr` and can ignore suffix bytes after an embedded NUL. Complete-record parsing must be length-aware and canonical.

## 9. Current Capstan status

- Runtime SHA-256, HMAC-SHA-256 and PBKDF2-HMAC-SHA-256 exist in `runtime/capstan_rt.h`; the runtime's password generation profile is 600,000 PBKDF2 iterations with a 16-byte salt and 32-byte derived key.
- The verifier currently accepts up to 100,000,000 iterations. This is a resource-exhaustion finding requiring remediation.
- `lib/crypto.cap` implements SHA-256, HMAC-SHA-256 and PBKDF2-HMAC-SHA-256 and is compared against Python `hashlib`/`hmac`, published examples and runtime outputs.
- The Capstan PBKDF2 API lacks a maximum iteration count and uses ordinary GC-managed `List<int>` scratch. It is not yet suitable as a secret-lifecycle-safe general-purpose API.
- The current test suite does not establish constant-time machine code, complete scratch erasure, a maximum-cost policy or cryptographic-module validation.
- There is no current public AEAD or general secure-random API in the language reference.

## 10. Required release gates

A cryptographic release must not pass solely because known-answer tests pass. Require:

1. reviewed algorithm and parameter policy;
2. strict, bounded input parsing and work limits;
3. published known-answer vectors;
4. independent implementation comparison;
5. malformed-input and mutation/fuzz tests;
6. boundary tests for every parameter and allocation limit;
7. concurrency and request-admission analysis for expensive operations;
8. secret-lifecycle and error-path review;
9. platform/compiler-specific side-channel claims, if any;
10. documented provider, dependency and trusted-base assumptions.

Any failed or unavailable gate must be recorded as an explicit limitation, not silently waived.
