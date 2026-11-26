# Standard-library inventory and v0.6 roadmap

**Status:** initial inventory and design proposal, 24 November 2026. This document records the current public surface visible in `docs/SPEC.md`, `docs/DESIGN-MAP.md`, `lib/crypto.cap`, `lib/shroud/` references and the test harness. It is not a claim that the v0.6 APIs below exist. The T1 standard-library integration has been claimed as a separate workstream. The claimed `feature/t1-stdlib` branch was not visible in the remote branch listing at this review snapshot, so its implementation state and API boundary remain unverified. This assessment deliberately does not change its files or compiler/runtime integration.

## Executive assessment

Capstan already has useful primitives: immutable byte strings with taint-preserving concatenation, bounds-checked lists, insertion-ordered maps using per-process-keyed SipHash-1-3, optionals, checked 64-bit arithmetic, explicit validators and context-specific escapers, bounded file reads, byte-oriented standard input, and secret-specific types and builtins. SHA-256, HMAC-SHA256 and PBKDF2-HMAC-SHA256 have a Capstan implementation with differential tests, but the existing `hash()` and password builtins still use the runtime implementation.

The largest v0.6 gap is not a missing convenience function. It is the absence of a coherent *authority and resource model* for general I/O. The native compiler now has Linux-only `workspace_open`, `workspace_read_file` and `workspace_close` builtins for descriptor-relative source loading, but these are a narrow host capability, not a general sandbox or unforgeable language-level directory type. Existing `read_file(path)` and `write_file(path, data)` still accept ambient paths; a traversal-safe `Path` abstraction, structured errors, general capability delegation, mandatory timeouts and network capability APIs remain to be designed. The design map still schedules capability-based I/O, `Path`, bounded inputs, mandatory timeouts, secure randomness and authenticated encryption for v0.6.

A second foundational gap is text semantics: the language reference defines `string` and `Tainted` as byte sequences. `len()`, `at()` and `slice()` are byte-oriented. This is a valid low-level representation, but it is not a Unicode string abstraction. APIs must distinguish bytes, validated UTF-8, Unicode scalar values and grapheme clusters rather than silently conflating them.

## 1. Existing API inventory

| Area | Existing surface | Assessment / gap |
|---|---|---|
| Strings and text | `string`, `Tainted`; `len/at/slice`; concatenation; interpolation; `int_to_str`, `char_str`, `taint_char` | Byte strings, not Unicode scalar or grapheme strings. Taint is preserved through concatenation/interpolation and selected collection operations. No general strict UTF-8 decoder/encoder or normalization API is specified. |
| Contextual text safety | `Html`, `LogText`; `escape_html`, `escape_log`, `escape_json`, `escape_csv`, `escape_c` | Strong context-specific types and escaping rules. These are not interchangeable sanitizers: callers must use the sink's exact context. Review edge cases and differential tests whenever contexts expand. |
| Collections | `List<T>` with bounds-checked indexing, push/pop/insert/remove/sort; `Map<T>` with get/set/has/remove/keys and insertion order | Useful baseline. Map hash-flooding mitigation is present (SipHash-1-3 with random process key). No first-class Set or documented iterator abstraction. Resource limits for collection growth and sort complexity need explicit API contracts. |
| Iteration and ranges | `for`, `while`, range analysis | No first-class lazy iterator/range library contract. Avoid APIs whose iteration can hide unbounded work or invalidate collection traversal assumptions. |
| Optional and errors | `T?`, `none`, `if (let ...)`; runtime checks stop safely | Optional exists. `Result<T,E>` and `?` propagation are on the v0.5 abstraction roadmap and must be coordinated with compiler work; stdlib APIs must not invent a parallel error convention. |
| Numerics | checked signed 64-bit arithmetic; explicit wrapping operations; bitwise operations and shifts | Safe checked defaults. Parsing/formatting coverage is incomplete; design map T4 calls for Capstan number conversion replacing libc formatting/parsing. |
| Filesystem | `read_file(path[, max]) -> Tainted?`, `write_file(path,data) -> bool`, `validate_path`; native-driver-only `workspace_open(root) -> int`, `workspace_read_file(root,relative,max) -> Tainted?`, `workspace_close(root)` | Workspace reads pin a root directory descriptor and use Linux `openat2` with beneath/no-symlink/no-magic-link/no-mount-crossing resolution; only regular files are accepted, size is bounded, and unsupported kernels fail closed. This protects the native compiler's source loader from symlink and path-replacement escapes. The handle is an integer process descriptor and is not an unforgeable sandbox type. General `read_file`/`write_file` remain ambient; read_file has no deadline for a connected writer, and there is no structured error or atomic write contract. `validate_path` alone cannot prevent symlink or TOCTOU traversal. |
| Process and SQL | `run(literal, args...)`, `sql_query(literal, params...)` | Both are documented as demonstration sinks that print rather than execute. Their literal/parameter constraints are useful, but are not production process or database APIs. |
| Networking | No general network API in the language reference | Capability-scoped host access, DNS/address parsing, bounded protocol parsing, connect/read/write deadlines and response limits remain to be designed. |
| Structured I/O and parsing | LSP has a Capstan JSON parser/writer; `escape_json`; `read_bytes(n)`, `read_line(max)`, `flush()` | JSON functionality exists in application code, not yet as a reusable standard API. Need strict decoder semantics, bounded nesting/tokens/strings, duplicate-key policy and taint-preserving decoded values. |
| Serialization | `escape_json`, CSV escaping | Escapers are not serializers. No general typed JSON/CSV/binary serialization contract is specified. |
| Date and time | None identified in the language reference | Needs explicit clock authority, timezone database/version policy, monotonic deadlines and deterministic test clock. |
| Cryptography | Builtins `hash`, `hash_verify`, `hash_password`, `verify_password`, `needs_rehash`, `secret_eq`, `secret_env`; `lib/crypto.cap` implements SHA-256/HMAC/PBKDF2 | T3 implementation is present and differentially tested, but the Capstan implementation is not yet wired into the builtins. No authenticated encryption or public secure-random API is specified. Do not add home-grown algorithms. |
| Testing and diagnostics | `test`, `assert`, `assert_denied`, `assert_granted`; strict/release checks; differential, fuzz, sanitizer and crypto-vector suites | Strong foundation. Standard-library APIs need explicit positive, negative, boundary, adversarial and resource-limit tests; every new conformance area must be declared in the spec and covered. |

## 2. Security review of current surfaces

### Findings and required design constraints

1. **Ambient filesystem authority (high priority).** The current path-taking read/write builtins do not express which directory or file authority the caller possesses. A string validator cannot establish authority, prevent symlink traversal, or close TOCTOU races. v0.6 should introduce opaque directory/file capabilities supplied at the entry point and relative `Path` values resolved by the capability implementation. No API should silently fall back to the process working directory or ambient environment.

2. **Path validation is not path confinement.** `validate_path` rejects `.`/`..` segments and leading `-`, but that is input validation, not a proof that a later open stays beneath a trusted directory. Symlinks, mount points, races and platform-specific path rules matter. Use handle-relative operations and no-follow semantics where available; document weaker platform guarantees rather than claiming universal race freedom.

3. **Input bounds are uneven.** `read_file` has a byte ceiling, `read_bytes` has a 2^30 maximum, and LSP has much tighter protocol-specific limits. A single large upper bound is not a practical safe default for every application. Prefer explicit bounded types/constructors, caller-selected smaller limits, and limits on aggregate allocations, nesting, element counts and time as well as individual byte length.

4. **Byte strings are not Unicode strings.** The language's string indexing and slicing are byte-based. Strict UTF-8 validation must reject overlong encodings, surrogate encodings, values above U+10FFFF, truncated sequences and stray continuation bytes. Decoding must not turn malformed input into trusted text. Replacement decoding, if provided, must be explicit and preserve provenance/taint. Normalization must be a separate, named operation; do not silently normalize identifiers, paths, hostnames or security-sensitive values.

5. **JSON escaping is not JSON parsing.** `escape_json` guarantees an escaped string fragment, not a typed serialization format. A reusable parser must bound nesting, token count, string size and total input; define duplicate object-key behaviour; reject malformed UTF-8/escape sequences according to an explicit policy; and produce tainted values when the source is untrusted. Never interpolate raw input into JSON or HTML script contexts.

6. **Crypto integration must retain a clear trust boundary.** The Capstan SHA-256/HMAC/PBKDF2 code has meaningful independent tests, but `hash()` and password functions still call runtime C. Do not describe the pure-Capstan implementation as the active builtin implementation until integration and parity tests prove it. Do not implement AEAD, random generation or key derivation casually. Prefer a reviewed provider or a well-reviewed implementation with published vectors, misuse-resistant API design, versioned algorithm tags, nonce rules, key rotation and explicit failure handling. Do not claim constant-time behaviour or reliable memory erasure without platform/compiler-level evidence.

7. **Secret lifecycle is not an API-level erasure guarantee.** The spec says secret memory is zeroed when collected. Garbage collection timing is nondeterministic; this is not equivalent to deterministic destruction or proof that copies/intermediates are erased. Keep secret values out of formatting, diagnostics, logs, serialization and error messages. Any future explicit secret-lifetime API must coordinate with the type system and runtime.

8. **Errors need to become values, not ambiguous booleans or silent stops.** `write_file` currently returns `bool`; read APIs return `none` for several distinct failure causes; runtime checks stop the process. As `Result<T,E>` becomes available, I/O APIs should return typed errors that distinguish permission denial, missing resources, invalid input, limit exceeded, timeout, unsupported operation and underlying I/O failure without leaking sensitive paths or data. No ignored failure path.

9. **Network access must be capability- and budget-bound.** The API must not accept arbitrary URLs as implicit authority. A network capability should bind allowed hosts/ports (and ideally resolved address policy), protocol, maximum request/response bytes, connection count and deadlines. Redirects must be re-authorised at every hop. DNS rebinding, private/link-local address access, proxy inheritance and TLS verification policy require explicit treatment.

10. **Determinism and clocks.** Date/time APIs must distinguish wall-clock timestamps from monotonic elapsed-time measurement. Timeouts use monotonic deadlines. Tests need an injectable clock capability; parsing must require explicit timezone/offset semantics and must not depend on machine locale.

11. **`read_file` has no time bound when consuming a live stream (availability/resource control).** `cap_read_file_max()` opens with `O_NONBLOCK` but unconditionally clears that flag with `fcntl(fd, F_SETFL, fl & ~O_NONBLOCK)` before calling `fread()`. A FIFO opened with no writer returns EOF immediately, which is consistent with the documented behaviour. However, when a writer is connected but keeps the FIFO open without sending data or closing it, the subsequent blocking read can wait indefinitely. The byte maximum bounds memory growth, not elapsed time. The same general issue applies to other stream-like or device paths that do not reach EOF promptly. This is not a violation of the narrower documented claim that opening does not block, but it is a gap for a security-oriented API whose input may be controlled by another process. The current `tests/unit/test_runtime.c::test_files()` does not exercise FIFO semantics. **Recommendation:** keep file reads and stream reads as distinct APIs, or add an explicit monotonic deadline/cancellation contract for stream-backed reads. Add timeout-isolated tests for (a) FIFO with no writer (immediate EOF), (b) connected idle writer (deadline/error rather than indefinite wait), (c) writer data followed by close, and (d) over-limit stream input. The test harness itself must enforce a timeout so a regression cannot hang CI.

12. **Path validation is not automatically applied by file I/O.** The runtime helper used by `read_file` and `write_file`, `cap_path_ok()`, checks only that the path is nonempty and contains no NUL byte. It does not call `cap_validate_path()`, reject absolute paths or `..`, or prevent symlink traversal. This is consistent with the current ambient-path API, but means the existence of `validate_path()` must not be read as an enforcement boundary for filesystem access. Even passing a `validate_path()` result would not prevent symlink/TOCTOU escape. Keep this distinction explicit until handle-relative directory capabilities replace ambient paths.

13. **Environment-variable names are C-string truncated.** The checker requires `secret_env()` to receive a string literal, but `is_literal_str()` checks only that the AST node is a string literal; it does not reject embedded NUL bytes. The language explicitly supports `\\0` in string literals. The runtime then calls `getenv(name->data)`, which interprets the name only up to the first NUL and ignores the CapStr length. Consequently, `secret_env("TOKEN\\0SUFFIX")` resolves the environment variable `TOKEN`, not a variable with the full literal name. This is a name-confusion/API-validation defect rather than an attacker-controlled arbitrary lookup, because the argument must be a source literal. **Recommendation:** reject NUL in the checker for this builtin (or validate `name->len` against the C-string length at the runtime boundary) and add a negative compile/runtime regression test.

14. **`read_line(max)` has no per-line size limit.** The runtime appends one byte at a time to a growable `CapBuf` until newline or EOF; unlike `read_file` and `read_bytes`, the API accepts no maximum. A peer controlling standard input can therefore send a very long line and drive allocations until the process-wide heap limit is reached, at which point the program may fail rather than return a bounded-input error. The global heap cap is an outer process limit, not a per-input contract. **Recommendation:** add `read_line(max)` (or a separate bounded line API) with a documented maximum and a distinct over-limit result; test a line exactly at the limit and one byte over, including input without a terminating newline.


**Remediation status (24 November 2026):** Findings 13 and 14 now have a focused implementation and regression-test proposal in draft PR [#73](https://github.com/DavidFernee/Capstan/pull/73). It rejects embedded-NUL `secret_env()` names in both the checker and runtime, and caps `read_line(max)` at 1 MiB with a CWE-789 failure for oversized lines. Cross-platform CI is pending; treat both findings as *under remediation*, not closed, until the PR passes and is integrated.

### Existing strengths to preserve

- Taint survives string concatenation/interpolation and is not implicitly erased by a decoder.
- `Html` and `LogText` are distinct output-context types.
- Collections are bounds checked; map hashing resists attacker-selected collision sets.
- Ordinary integer arithmetic is checked; wrapping arithmetic is explicit.
- File input is marked untrusted and bounded; byte-oriented input preserves NUL bytes.
- Crypto has published-vector and independent-implementation comparisons, rather than only self-consistency tests.

## 3. Prioritised v0.6 roadmap

The sequence below is a proposal, not an assertion that all listed work fits into one release. The capability and error model are prerequisites for the higher-level APIs.

| Priority | Work | Proposed contract | Security gate |
|---|---|---|---|
| P0 | Align with T1 and v0.5 | Use the agreed standard-module mechanism, visibility rules, generic/Result semantics and declassification rules; do not create parallel APIs | Cross-session API review; no stdlib-only taint escape hatch |
| P1 | Capability and path foundation | Opaque `Directory`/file capabilities; validated relative `Path`; explicit open modes; handle-relative operations | Traversal, symlink, race, NUL, absolute-path, platform and permission tests |
| P1 | Bounded byte/text primitives | `Bytes`, bounded reader/writer, explicit UTF-8 validation and decode result | Invalid UTF-8 corpus, truncation, overlong, surrogate, max-boundary and allocation-budget tests |
| P1 | Structured errors and limits | `Result<T,E>`, typed I/O/protocol errors, `Limit`/bounded input abstractions | Every error branch tested; no ignored results; no unbounded allocation or blocking |
| P2 | JSON and serialization | Typed JSON value/parser/writer; tainted decoded strings; canonicalisation only where required | RFC test vectors, malformed corpus, duplicate-key policy, nesting/token/output caps, round trips and fuzzing |
| P2 | Networking | Explicit `NetworkCapability`, host/port policy, TLS verification, mandatory monotonic deadlines, bounded streams | Redirect re-authorisation, DNS rebinding, SSRF/private IP, malformed protocol, slow peer and oversized response tests |
| P2 | Numeric parsing/formatting | Checked decimal/hex parse, exact formatting, explicit rounding and overflow semantics | Differential tests against independent implementations and boundary/property fuzzing |
| P3 | Collections/iterators/ranges | Set, safe iterator contracts, bounded/lazy ranges, stable sort/search APIs | Mutation-during-iteration semantics, overflow-safe range endpoints, complexity and memory tests |
| P3 | Date/time | Instant, Duration, civil date/time, explicit timezone conversion, monotonic deadline | DST ambiguity/gap, leap/calendar boundaries, invalid zone and deterministic-clock tests |
| P3 | Cryptographic interfaces | Reviewed AEAD and secure-random provider interfaces; algorithm-tagged envelopes and rotation | Published vectors, independent implementation, nonce misuse tests, key separation, no unsupported claims |

### Explicit non-goals for this workstream

- No new cryptographic primitive implemented from scratch.
- No shell-based process execution.
- No ambient network or filesystem fallback.
- No silent UTF-8 replacement or normalization.
- No generic serializer that turns tainted data into trusted output.
- No promise of constant-time execution, deterministic secret erasure or complete SSRF prevention without evidence.

## 4. API design principles

- **Authority is a value.** Functions that touch external resources receive an explicit capability. A path or URL is a name, not authority.
- **Limits are part of the type or required arguments.** Bound bytes, elements, nesting, time, concurrency and total work. Avoid "unlimited" defaults.
- **Untrusted stays untrusted.** Parsing and decoding transform representation, not trust. Validation is narrow, context-specific and explicit.
- **Errors are exhaustive.** Prefer `Result<T,E>`; do not collapse materially different failures into `false` or `none`.
- **No implicit environment.** Locale, timezone, current directory, proxy, DNS resolver and wall clock are dependencies to be passed or explicitly selected.
- **Names encode semantics.** `Bytes` is not `Utf8Text`; HTML text is not an HTML attribute; wall time is not monotonic time; a timeout is not a retry count.
- **Resource lifetime is visible.** File handles, sockets and streams need structured lifetime/close semantics compatible with Capstan's memory model and future ownership work.
- **No convenience bypass.** High-level helpers must be built on the same capability, taint, limit and error rules as low-level primitives.

## 5. Implementation and test sequencing

1. Complete the inventory and review the T1 integration boundary before touching standard-library source. The T1 workstream has claimed `lib/std/`, the crypto migration, and compiler/bootstrap/LSP integration, but its claimed `feature/t1-stdlib` branch was not visible remotely at this review snapshot; verify the actual handoff before editing overlapping files.
2. Resolve the v0.5 `Result<T,E>` and visibility contract with the type-system workstream. Avoid introducing a temporary result convention that must be broken later.
3. Agree filesystem capability semantics with the runtime workstream before implementing file handles or directory traversal.
4. Implement one narrow, independently testable API slice per PR. Every slice includes spec text, conformance-area coverage, positive/negative tests, boundary tests, adversarial/fuzz tests where parsing is involved, examples and changelog notes.
5. For crypto, first choose the reviewed provider/trust boundary; only then implement interfaces and vectors. A successful self-test is necessary but not sufficient evidence of cryptographic assurance.

## 6. Coordination and current status

- T1 standard-library integration has claimed `lib/std/`, migration of `lib/crypto.cap`, and compiler/bootstrap/LSP integration. The claimed `feature/t1-stdlib` branch was not visible remotely at this review snapshot; implementation status and API boundaries remain unverified. This document intentionally avoids those files.
- The v0.5 type-system design is proposed in PR #49; a separate compiler/type-system workstream is active. `Result<T,E>` availability and generic API syntax must be agreed before library APIs depend on them.
- Runtime and memory-management work is separate; filesystem/network resource handles require an explicit handoff before implementation.
- Shroud is separately claimed and lives under `lib/shroud/`; this workstream does not modify it.
- Coordination claim and updates are recorded on issue #25. This assessment branch is `docs/stdlib-v06-roadmap`.

## 7. Source basis

- `docs/SPEC.md`: language types, methods, builtins, I/O, taint, secrets, limits and conformance areas.
- `docs/DESIGN-MAP.md`: v0.5/v0.6 roadmap and T1–T5 trusted-base stages.
- `lib/crypto.cap` and `tests/crypto/check.py`: current Capstan crypto implementation and differential test strategy.
- `tests/run.sh` and `docs/TESTING.md`: current conformance, fuzzing, sanitizers, stage-0 and crypto gates.
- `CHANGELOG.md`: recent implemented API/security changes and current release status.
