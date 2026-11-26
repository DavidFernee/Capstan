# Security architecture and standard-library assessment

**Status:** Initial independent source assessment; not a certification or complete audit  
**Baseline:** `main`, inspected 24 November 2026  
**Working branch:** `security/architecture-stdlib-audit`  
**Scope:** language security boundary, standard-library and runtime-facing security APIs, cryptographic implementation and evidence  
**Coordination:** implementation ownership remains with the active compiler, runtime, T1 standard-library and formal-verification workstreams.

## 1. Executive assessment

Capstan has a meaningful security-oriented language design: untrusted input is represented as `Tainted`; output contexts have distinct `Html` and `LogText` types; arithmetic and collection access are checked; grants are object-bound and rechecked; and selected credential operations use a dedicated `Secret` representation. The compiler, test suite, CWE atlas, differential testing, mutation testing and sanitizer jobs provide a stronger assurance process than ordinary application-language projects.

That is not yet equivalent to a secure language implementation. The compiler and C runtime remain in the trusted computing base. The standard library is not yet a coherent capability- and resource-bounded API. Secret lifetime is nondeterministic under garbage collection. Several crypto interfaces expose caller-controlled cost parameters without a practical work budget. The Capstan-native SHA-256/HMAC/PBKDF2 implementation is tested but is not yet the implementation behind the existing builtins.

**Assessment conclusion:** Capstan has a promising and unusually explicit security architecture, but its current security claims must remain scoped to specific compiler checks, runtime behaviours and tested configurations. No whole-language memory-safety, non-interference, cryptographic-module validation or formal-verification claim is justified by this review.

## 2. Assurance boundary

| Layer | Current enforcement/evidence | Residual trust or limitation |
|---|---|---|
| Source language | Checker diagnostics, taint/secret/grant rules, checked operations | Checker soundness, unsupported flows, semantic gaps |
| Range analysis | Conservative facts and `--keep-checks` comparison tests | Analysis soundness remains a compiler proof obligation |
| Code generation | Generated C checks and exact-output/differential tests | C generation correctness and C compiler behaviour |
| Runtime | C runtime, GC, input/output, crypto and map hashing | C memory safety, OS interfaces, allocator/GC correctness |
| Standard library | Capstan source modules, currently partial | API-level resource, secret and error contracts |
| Bootstrap | Python stage-0 plus self-hosting comparison | Python translator and bootstrap trust |
| External platform | OS, kernel, C library/compiler, entropy source, hardware | Outside current Capstan guarantees |

A test passing demonstrates the tested property for the tested inputs and environment. It does not establish universal absence of a defect. Cryptographic test vectors establish functional agreement, not constant-time behaviour, side-channel resistance, key erasure, protocol security or module validation.

### Current repository reconciliation

The standard-library inventory contains historical findings about `secret_env()` embedded-NUL names and unbounded `read_line()`. These were remediated in merged PR #73 and are not current vulnerabilities on `main`: the runtime rejects embedded NUL in environment names and enforces a 1 MiB line limit. The inventory's remediation note should be treated as historical evidence, not an open finding. This audit retains the distinct live-read deadline gap in `read_file()` and the ambient filesystem authority gap.

## 3. Confirmed findings and priority register

Severity describes plausible impact; exploitability describes the preconditions visible from the current interface. These are preliminary engineering ratings, not CVSS scores.

| ID | Severity | Finding | Exploitability / impact | Required disposition |
|---|---|---|---|---|
| SEC-CRYPTO-001 | High | Runtime password verifier accepted attacker-selected PBKDF2 iteration counts | A valid stored record could request up to 100,000,000 iterations, about 166.7 times the 600,000-iteration generation profile. | **Fix submitted in PR #134:** fixed 600,000 profile and strict length-aware parser reject other costs before PBKDF2. Exact-head CI run `45373743464` passed all four jobs on head `3a19978e42e86ab6e82a27d155a2dc0d841f6318`; runtime-owner approval, Worker 5's legacy compatibility decision and architect acceptance remain pending, so do not mark accepted yet. |
| SEC-LANG-001 | Medium (partially mitigated in draft PR #238; exact-head CI pending) | Fast-hash password checks did not reject Tainted input or inspect method/call arguments | The checker now rejects Tainted inputs to `hash()` and `hash_verify()` with CWE-916 and recursively inspects method receivers and call arguments for password-like names. Dedicated reject fixtures cover innocuously named Tainted input, `hash_verify`, `password.slice(...)` and `identity(password)`; a positive control preserves audited trust for non-password integrity hashing. The three former CWE-916 atlas gaps are now compile-rejection attempts on the research branch. | Keep open until exact-head native/stage-0 CI passes and first-class Password provenance prevents ordinary trusted strings with innocuous names from being treated as passwords. This is a partial mitigation, not a complete semantic password guarantee. |
| SEC-CRYPTO-002 | High | Capstan PBKDF2 API has no upper bound on `iterations` | A caller that derives this parameter from untrusted configuration/input can request effectively unbounded CPU work. `dklen` is capped at 1 MiB, but that does not bound iteration cost or the product of output blocks and iterations. | Enforce iteration, salt, password and output limits before doing work; make invalid parameters distinguishable from valid output. |
| SEC-CRYPTO-003 | High | Capstan crypto APIs store key and intermediate material in ordinary GC-managed lists | `List<int>` scratch (padded message, HMAC pads, inner/outer state, U/T blocks and concatenated buffers) is not allocated as Secret storage and has no explicit wipe path. Collection-time wiping applies only to secret-kind allocations. | Do not use these generic list APIs for long-lived production secrets until secret-aware buffers/lifetimes and wiping evidence exist. Coordinate with T1/runtime ownership. |
| SEC-CRYPTO-004 | High | Runtime PBKDF2 amplifies long passwords by re-hashing the full HMAC key on every iteration | `cap_hmac_sha256()` hashes the entire key whenever it exceeds 64 bytes. `cap_pbkdf2()` calls it once for the first U value and again for every iteration. `hash_password()` accepts arbitrary-length `CapStr`; `read_line()` permits up to 1 MiB. A long attacker-controlled password can therefore multiply the intentionally expensive 600,000-iteration KDF by roughly `ceil(password_bytes/64)` SHA-256 blocks per HMAC. | Set and enforce a strict password-byte maximum before KDF work; precompute HMAC keyed inner/outer states once per PBKDF2 operation; bound concurrent KDF admission at service level; add boundary and instrumented work-scaling tests. |
| SEC-STDLIB-001 | High | Filesystem builtins retain ambient path authority | A path string is not a directory capability. `validate_path()` is not automatically applied by the I/O boundary and cannot prevent symlink or TOCTOU escape. | Replace with opaque directory capabilities and handle-relative resolution; keep ambient APIs explicitly legacy/unsafe until retired. |
| SEC-STDLIB-002 | High | File reads can block indefinitely after opening a stream | The current read helper clears `O_NONBLOCK` before consuming. A connected FIFO writer that stays open without sending data can hold the reader indefinitely; byte limits do not bound elapsed time. | Separate regular-file and stream APIs or require monotonic deadlines/cancellation. Add timeout-isolated FIFO regressions. |
| SEC-SECRET-001 | High | Secret erasure is tied to nondeterministic GC reclamation | A secret can remain live due to legitimate references or conservative false-positive roots. Ordinary copies and external environment copies are outside the secret allocation's wipe guarantee. | Define the precise guarantee; introduce explicit lifetime/zeroisation semantics only with language/runtime coordination. |
| SEC-CRYPTO-005 | Medium | Runtime SHA-256 compression scratch derived from HMAC keys is not explicitly wiped | `cap_hmac_sha256()` wipes its key/pad/intermediate arrays and `CapSha256` state, but `cap_sha256_block()` creates a local 64-word message schedule and scalar working state that are not wiped on return. HMAC's ipad/opad compression blocks are key-derived. | Wipe local schedule and working state with the non-elidable wipe primitive; review optimized machine code and compiler/target scope; add a focused wipe-path test where feasible. Do not claim complete physical erasure. |
| SEC-CRYPTO-006 | Medium | Runtime password verifier previously accepted noncanonical embedded-NUL/trailing suffix records | `cap_verify_password()` used `strlen()` on the suffix rather than the enclosing length-bearing `CapStr.len`, allowing components to disagree about the complete stored value. This was a parser-integrity issue, not a demonstrated authentication bypass. | **Fix submitted in PR #134:** explicit-length exact parsing rejects embedded NUL, trailing bytes and noncanonical encodings; adversarial tests cover these cases and prove rejection before KDF. Exact-head CI run `45373743464` passed all four jobs on head `3a19978e42e86ab6e82a27d155a2dc0d841f6318`; compatibility approval remains pending. |
| SEC-MEM-001 | Medium | Collection removal leaves stale pointer-bearing slots in backing arrays | `cap_list_pop_p()`, `cap_list_clear()`, `cap_list_remove()` and `cap_map_remove()` still reduce logical length without clearing all vacated pointer-capable `CapVal`/key slots. The conservative collector scans the full backing allocation, so removed references can remain GC roots and delay reclamation/wiping. | Fix remains outstanding in GC safety PR #51. Its latest head `d6f97beb05962b7f8ef43f5e0ea8434be06450fa` is not synchronised with current main, and its earlier green CI is stale. #112 allocator-accounting hardening did not address stale-slot clearing. Reconcile #51 with current main and add direct slot-zeroing plus GC-stress Secret-lifetime regressions. |
| SEC-SECRET-002 | Medium | Secret comparison reveals length | `secret_eq()` loops over the shorter length and returns a length-mismatch bit. The spec documents lengths as public; callers must not use it for length-confidential values. | Preserve explicit warning; add fixed-size/length-hiding API only if a concrete requirement and evidence exist. |
| SEC-SHROUD-001 | Medium | TrueType parser checks file bounds but not all declared table/subtable bounds | Malformed table records and cmap subtable offsets can direct reads into other regions of the font file; `FontReader` marks only whole-file out-of-bounds reads, not table-local violations. This can accept structurally invalid fonts and interpret unrelated table bytes as cmap/metrics data. | Retain and enforce each table's `[offset, offset+length)` span; validate cmap format-specific lengths/group counts, `loca` length for `num_glyphs + 1`, and `hmtx` length for `num_hmetrics` plus trailing bearings; add table-boundary mutations. |
| SEC-SHROUD-002 | High (conditional on caller-controlled pixmap dimensions/export) | Pixmap, font and PNG export can amplify memory far beyond the pixel payload | Before remediation, per-side bounds permitted a 16,384² pixmap and recursive composite-font work had only local per-glyph limits; PNG export materialises raw, compressed and output buffers plus conversion intermediates. | **Remediated at the object-budget layer:** PR #92 historically added a 2 MiB PNG raw-byte cap and bounded chunk conversion. Its encoder was absent from the current `main` tree during the 2026-11-25 audit; PR #272 restores it with a 4 MiB cap to accommodate the 1100×720 Anchor reference preview. Exact-head CI, Anchor smoke, formal verification and CodeQL for PR #272 are required before this restoration is accepted. PR #79 merged as `2be9da58b080a95260037a5aa80b1c2b86d0ed25`; exact-head CI run `45384184632` and formal run `45384184887` passed. The implementation enforces a 16,777,216-pixel aggregate pixmap cap, font/glyph/cache bounds, and a 256 aggregate composite-component-visit limit, with a 325-visit recursive regression. A bounded binary sink and process-RSS guarantee remain future work; TrueType table-local span validation remains open under SEC-SHROUD-001 / issue #121. |
| SEC-SHROUD-003 | Medium (conditional on attacker-controlled text/layout) | Newline-dense and narrow-width text amplified bounded input into large line-index arrays | Before remediation, 1 MiB text could produce over two million line indices; `View.lines` truncation happened after allocation. | **Integrated with a policy caveat:** PR #103 is merged as `063ceb290559a565da602006fdd7e0c52c185ca1`; PR #117 is merged as `bf487dac9d92b8e48737a7549c56f7ed68ad78ac`; and PR #140's full-size Tainted fail-closed integration regression is merged as `10ae9d955b2836d3c5c7184f60765e1f9359ffab`. The 2 MiB frame byte preflight and 131,072-line shared frame ceiling are therefore integrated. Issue #114 remains open for the public-limit compatibility decision; implementation presence does not settle that policy. |
| SEC-SHROUD-004 | Medium (conditional on attacker-controlled text-input events) | Single-line control filtering previously copied the accumulated output quadratically | Before remediation, a 65,536-byte alternating printable/control paste caused about 512 MiB of cumulative concatenation copying. | **Remediated:** PR #72 merged as `8975c2799f536833ebb26d33269b292420954a57`. `single_line()` now collects retained Tainted spans and uses the single-allocation `join(List<Tainted>, string)` path. The exact adversarial regression passed Ubuntu/Clang, Ubuntu/GCC and macOS/Clang in run `45381489063`: 65,536 input bytes, 32,768 retained bytes, 4,161,583 total Capstan allocation bytes on Linux and 4,161,627 on macOS, below the 16 MiB ceiling. | Keep the allocation regression in normal and ASan+UBSan CI; preserve taint and exact retained UTF-8 bytes. | The separate accessibility serializer amplification in SEC-SHROUD-005 remains open. The measured allocation is for this exact workload, not a process-wide memory guarantee. |
| SEC-SHROUD-005 | Medium (conditional on untrusted displayed text and accessibility export) | Accessibility UTF-8 conversion repeatedly copies the growing output | `utf8_from_codepoints()` appends one `char_str()` per codepoint. A 1 MiB ASCII text value yields 549,756,338,176 bytes (~512 GiB) of cumulative concatenation copying; a 64 KiB field yields 2,147,516,416 bytes (~2 GiB). The final output is only the original input size. | Replace with a linear-time UTF-8 encoder using a pre-sized byte buffer/single allocation; preserve sanitised codepoints. Add full-size ASCII/multibyte accessibility-tree tests and instrumented copy/allocation scaling. The byte/line frame budgets do not constrain this separate a11y conversion path. |
| SEC-IO-001 | Medium | `read_file` collapses distinct failures to `none`; `write_file` returns `bool` | Callers cannot reliably distinguish missing, denied, invalid, over-limit, timeout or I/O failure. This encourages fail-open and ignored-error logic. | Use agreed `Result<T,E>` after v0.5 type-system coordination. |
| SEC-IO-002 | Medium | Byte-string APIs can be mistaken for Unicode text | `string` and `Tainted` are byte sequences; byte indexing is not Unicode scalar/grapheme indexing. | Introduce separately named strict UTF-8 and Unicode abstractions; preserve taint through decoding. |
| SEC-ASSURE-001 | Medium | Crypto test suite does not establish resource or secret-lifetime properties | Existing vectors and differential tests validate outputs, not maximum-cost rejection, malformed-byte contracts, scratch erasure or side-channel properties. | Add parameter-boundary, malformed-input, resource-budget and wipe-path tests when implementation ownership is agreed. |

### Finding details

#### SEC-SHROUD-001 — font table-local bounds are not enforced

In `lib/shroud/ttf.cap`, `find_table()` validates that a table's declared `off + len` does not exceed the complete font byte array, but returns only its offset and places its length in a single scratch list. `font_load()` repeatedly overwrites that length and does not retain spans for the `cmap`, `loca` or `hmtx` tables. The cmap subtable offset is added to the cmap base without checking it against the cmap table length; format-12 group count and records are then read through `FontReader`, which checks only the whole-file boundary. Similarly, glyph location and horizontal metric reads are checked against the file, not their owning table's declared extent.

This finding is tracked in issue #121; PR #79's aggregate glyph/pixmap budgets do not establish table-span correctness. No table-local parser fix has yet been submitted. This is not an out-of-process memory-safety finding: `FontReader` still prevents reads beyond the complete input byte array. It is a parser-integrity defect. A malformed but file-bounded offset/count can cause data belonging to another table or padding region to be interpreted as cmap/metrics/loca records, allowing malformed fonts to be accepted and producing attacker-controlled glyph mappings or metrics. The parser should preserve each table span and validate every nested offset/count using subtraction-based checks against that span before reading. Add malformed fonts where cmap subtable offset/length, format-12 group count, loca entry count or hmtx metric count fits the file but exceeds its declared table.

This is separate from the resource-explosion issue addressed in draft PR #79: that branch introduces aggregate recursive outline/component and glyph-cache budgets, but does not establish table-local bounds for cmap/loca/hmtx. The assessment does not duplicate its implementation changes.

#### SEC-SHROUD-002 — pixmap, font and PNG resource amplification

The object-budget layer has a historical 2 MiB PNG cap from PR #92. The 2026-11-25 source audit found that implementation missing from current `main`; PR #272 restores the encoder and raises the ceiling to 4 MiB so the 1100 × 720 Anchor preview is supported. Its 2047 × 512 near-limit fixture is pending exact-head normal/sanitizer/Anchor validation. Historical 2 MiB GC-heap measurements are not evidence for the new limit. The documented 48.3–56.9 MiB normal and 56.4–56.7 MiB ASan+UBSan peak Capstan GC heap is a workload-specific measurement, not process RSS.

PR #79 is merged as `2be9da58b080a95260037a5aa80b1c2b86d0ed25`. It enforces pixmap side <= 16,384 and area <= 16,777,216 pixels before allocation; font file <= 32 MiB; per glyph <= 4,096 points; composite depth <= 8 and local parts <= 64; per-root aggregate points <= 16,384 and component visits <= 256; glyph mask <= 262,144 pixels; cache <= 4,096 glyphs and <= 1,048,576 cached alpha pixels. Its recursive regression exceeds the shared component-visit budget at 325 visits. Exact-head CI run `45384184632` and formal run `45384184887` passed.

The limits bound these object and traversal paths; they do not prove a process-wide RSS ceiling. The PNG path still materialises several representations, and a bounded binary sink remains future work. TrueType table-local span validation is a separate open finding under SEC-SHROUD-001 / issue #121.
 
#### SEC-SHROUD-003 — line-index allocation amplification

The 2 MiB aggregate view-tree byte preflight bounds input bytes, but not the layout representation derived from them. Before remediation, `wrap_lines()` appended two indices per explicit LF plus a final pair, and applied `View.lines` only after constructing the full line list. A trusted 1 MiB LF-only value could therefore create 2,097,154 line indices; narrow-width soft wrapping could similarly amplify ordinary untrusted `user_text(Tainted)` input. The codepoint and line-index lists alone could retain tens of MiB, with additional `Laid` nodes, pixmaps, font caches and GC overhead.

**Remediation integrated:** PR #103 and PR #117 are merged, as is PR #140's full-size Tainted integration regression. `wrap_lines_limited()` checks the shared remaining budget before every line-index pair append; explicit `max_lines()` truncation is applied during wrapping rather than after allocation. The tests cover exact and one-over aggregate boundaries, multiple views, soft wrapping, explicit truncation, cycles/nesting and a full 1 MiB untrusted narrow-width input; the line-budget test also records peak Capstan GC heap.

The line-budget implementation and its Tainted integration regression are now merged. Issue #114 remains the open policy item for whether the public 131,072-line ceiling is compatible with all supported Shroud workloads. The merged tests establish bounded allocation on their covered paths; they do not establish a process-wide memory ceiling.
 
#### SEC-SHROUD-004 — single-line filtering allocation (remediated)

PR #72 replaces repeated prefix concatenation in `lib/shroud/ui.cap::single_line()`
with retained Tainted byte-span collection followed by one `join()`. The new
`join(List<Tainted>, string)` overload uses the existing `cap_join()` runtime
path, which computes the output size and allocates the result once; the static
result type remains Tainted. If no control is removed, the original value is
returned without copying.

The adversarial regression processes 65,536 bytes alternating printable ASCII
and removed line controls. It verifies that all 32,768 printable bytes survive
and measures total Capstan allocation, rather than relying on wall-clock time.
The exact-head CI run `45381489063` passed Ubuntu/Clang, Ubuntu/GCC and
macOS/Clang: total allocation was 4,161,583 bytes on Linux and 4,161,627 bytes
on macOS, below the 16 MiB ceiling. The previous implementation's cumulative
concatenation copying was approximately 512 MiB for this same input.

This closes the quadratic field-filter finding on the tested path. The separate
accessibility serializer conversion in SEC-SHROUD-005 remains open; no
process-wide memory bound is claimed.
 
#### SEC-SHROUD-005 — quadratic copying in accessibility UTF-8 conversion

In `lib/shroud/a11y.cap`, `utf8_from_codepoints()` starts with an empty string and appends a newly allocated `char_str()` for each codepoint using `out = out + char_str(...)`. The runtime string concatenation allocates a new result and copies the accumulated prefix on every iteration. `visible_untrusted_text()` calls this function from `name_of()` for untrusted `K_TEXT` values and from `value_of()` for non-secure text fields. Those paths are reached when an embedder requests the current `a11y_tree()` or serialises it with `a11y_json()`.

The Shroud text limit is 1,048,576 bytes per widget. For a 1 MiB ASCII value, the concatenated result sizes sum to (n(n+1)/2 = 549,756,338,176) bytes (about 512 GiB) of copying/allocation, even though the final UTF-8 output is only 1 MiB. A 65,536-byte text field yields 2,147,516,416 bytes (about 2 GiB) of cumulative copying. The existing frame byte and rendered-line budgets do not bound this separate accessibility conversion work. This is a conditional CWE-400 issue: the embedder must request an accessibility snapshot for attacker-controlled displayed text.

Replace repeated concatenation with a linear-time UTF-8 encoder using a pre-sized byte buffer or single output allocation, preserving the sanitised codepoint sequence. Add full-size ASCII and multibyte accessibility-tree tests and instrumented copy/allocation scaling; wall-clock-only thresholds are not sufficient. This is independent of SEC-SHROUD-004, which is the analogous quadratic filter in `single_line()`.

#### SEC-LANG-001 — shallow password-name inspection (reproduced)

In `compiler/checker.cap`, `mentions_name()` checks variable/field names but returns `false` immediately for `N_CALL` and `N_METHOD`, rather than examining their arguments. The fast-hash check for `hash()`/`hash_verify()` and the plain-string credential comparison check call this helper. A form such as `hash(password.slice(0, password.len()))` therefore appears to evade the name-based password detection even though the receiver is named `password`. The CWE atlas now contains two wrapped-expression probes: `hash(password.slice(0, password.len()))` and `hash(identity(password))`, where `identity` preserves `Tainted`. The two adversarial CWE-916 fixtures now exercise both a method wrapper and a helper-call wrapper. They are recorded as expected gaps in `tests/cwe/atlas.py`; all three platform test jobs (Ubuntu/Clang, Ubuntu/GCC and macOS/Clang) for workflow run `45340566758` have completed successfully with these fixtures present. This reproduces the gap across the current supported CI matrix. The correct long-term control is semantic password/secret provenance, not an ever-growing identifier-name heuristic.

#### SEC-CRYPTO-001 — excessive verifier work factor

The runtime's `cap_verify_password()` parses the stored iteration count and accepts any value from 1 through 100,000,000. New hashes are generated with 600,000 iterations. The upper accepted count therefore permits a derivation cost approximately 166.7 times the normal generation cost. The risk is conditional on an application passing attacker-influenced encoded hash records to the verifier; the current runtime API itself does not impose an application-level request budget.

The regression must test the parser's acceptance/rejection boundary independently of running a maximum-cost PBKDF2 operation. The exact ceiling should be a documented policy decision, not an unexplained magic number.

#### SEC-CRYPTO-002 — unbounded PBKDF2 API

`lib/crypto.cap::pbkdf2_sha256()` rejects non-positive iteration counts and output lengths outside 1..1,048,576, but has no upper iteration count and no salt/password input bounds. Its work scales with both the number of PBKDF2 blocks and the iteration count. Invalid input returns an empty list, which is not a typed error and makes failure semantics implicit.

#### SEC-MEM-001 — stale collection slots

The current runtime collection helpers shrink logical lengths but leave vacated pointer-bearing storage uncleared. The collector scans the backing allocation rather than only the logical list/map length. Consequently, a removed object reference can remain visible to the conservative collector and delay reclamation of an object graph, including Secret allocations that would otherwise become unreachable. This is a retention/lifetime defect; it is not evidence that Capstan code can read the removed value. The fix is already identified in the active runtime/GC coordination work and is intentionally not duplicated here. Tests should inspect vacated slots directly and exercise removal under GC stress, including the map key and value arrays and all list removal/pop/clear paths.

#### SEC-CRYPTO-004 — password-length amplification in runtime PBKDF2

The runtime's `cap_hmac_sha256()` normalises a key longer than the 64-byte SHA-256 block size by hashing the entire key. `cap_pbkdf2()` invokes HMAC once for U1 and once for every subsequent iteration. It does not precompute/reuse the keyed HMAC inner/outer states across the PBKDF2 loop. `cap_hash_password()` has no password-length limit; the public `read_line()` input path accepts up to 1 MiB. Thus a long password can make each of the 600,000 HMAC iterations re-hash the entire password. At 1 MiB, this entails approximately 16,384 SHA-256 compression blocks per HMAC call, or roughly 9.8 billion key-hashing compression blocks over the PBKDF2 operation, before counting the ordinary HMAC work. The exact cost depends on input size and compiler/runtime, but the multiplicative mechanism is directly visible in source. This is an attacker-triggerable availability risk whenever an application passes attacker-controlled long passwords to `hash_password()` or `verify_password()`.

Remediation should combine a conservative documented maximum password byte length enforced before any KDF work with HMAC state precomputation inside PBKDF2. A password cap alone prevents the worst amplification but does not remove avoidable repeated work; state precomputation alone still leaves an unbounded input allocation/processing surface. Tests should exercise lengths at the limit and one byte over, and instrument or isolate work so the test proves the key is normalised once rather than once per iteration. Do not run an extreme-cost test in the normal CI process.

#### SEC-CRYPTO-006 — embedded NUL and trailing bytes in password records

The former `cap_verify_password()` parser checked the enclosing `CapStr.len` against the prefix length, but then used C string functions (`strtol` and `strlen`) for the remainder. An embedded NUL could therefore hide trailing bytes from the suffix-length check. Password verification still checked the decoded salt and digest; this was a parser/canonicalisation flaw, not a demonstrated password-authentication bypass.

**Fix submitted in current-main PR #134:** the new parser consumes only explicit `[start,end)` spans derived from `CapStr.len`, requires the exact canonical current record length and syntax, and rejects embedded NUL, trailing bytes, noncanonical decimal cost and invalid/non-lowercase hex before invoking PBKDF2. The test suite includes valid-record-plus-NUL-plus-suffix and verifies that malformed records do not enter the KDF. Exact-head CI run `45373743464` passed all four jobs on head `3a19978e42e86ab6e82a27d155a2dc0d841f6318`; compatibility-policy approval remains pending, so do not mark this finding accepted until that gate passes.


#### SEC-CRYPTO-005 — incomplete wiping of HMAC compression scratch

`cap_hmac_sha256()` explicitly wipes its local key block, ipad, opad, inner digest and `CapSha256` state. However, each call to `cap_sha256_block()` creates a local `uint32_t w[64]` message schedule and scalar working variables `a` through `h`. That schedule is derived from the compression input; for HMAC ipad/opad blocks it is key-derived. It is not explicitly wiped before returning. Wiping the caller's `CapSha256` object does not wipe this callee-local schedule. This is an incomplete best-effort stack-erasure path, not proof of a practical memory disclosure. Add a non-elidable wipe for the schedule and, where practical, working state, then inspect optimised output for each supported compiler/target. Even then, do not promise erasure from registers, spills, swap or hardware.

#### SEC-CRYPTO-003 — ordinary-memory secret intermediates

The Capstan implementation accepts `List<int>` for passwords and keys. It constructs ordinary lists for padded SHA input, HMAC pads, concatenation buffers, intermediate digests and PBKDF2 state. The implementation has no explicit zeroisation operation. The GC's secret allocation kind is not automatically conferred on these lists. This does not prove a practical disclosure exploit in isolation, but it means the implementation cannot claim secret-erasure assurance.

### Relationship to the existing cryptographic API review

The repository already contains the merged review `docs/CRYPTO-STDLIB-REVIEW.md` (PR #56), which records the low-level PBKDF2 iteration/output/salt bounds, byte-value truncation, ordinary-list secret lifecycle, ambiguous errors, and the runtime verifier's excessive cost and embedded-NUL/trailing-byte parsing issue. Those findings are not new claims of this assessment; this register cross-references them so remediation is not duplicated. SEC-CRYPTO-004 adds a distinct runtime implementation concern: long password keys are re-hashed in every PBKDF2 HMAC iteration rather than normalised once. SEC-CRYPTO-005 adds a narrower audit of caller/callee scratch erasure in the C implementation. SEC-CRYPTO-006 restates the complete-record parser defect as an independently tracked runtime trust-boundary issue.

## 4. Cryptographic implementation assessment

### Current implementation split

- Runtime builtins `hash()`, `hash_verify()`, `hash_password()`, `verify_password()` and `needs_rehash()` use the C implementation in `runtime/capstan_rt.h`.
- `lib/crypto.cap` contains Capstan implementations of SHA-256, HMAC-SHA256 and PBKDF2-HMAC-SHA256.
- `tests/crypto/check.py` compares the Capstan implementation against Python `hashlib`/ `hmac`, published examples, generated inputs and runtime results. The native run includes a one-million-byte SHA-256 input and a full-cost password-hash check; stage 0 runs a reduced set.
- The implementations have not thereby become one implementation, nor has either implementation been independently cryptographically audited.

### Positive evidence

- SHA-256, HMAC-SHA256 and PBKDF2-HMAC-SHA256 are established constructions with published specifications/vectors.
- The runtime's PBKDF2 output is algorithm-tagged and uses a random 16-byte salt.
- The runtime wipes PBKDF2's local U/T/message buffers, HMAC key/pad/intermediate buffers and the derived key buffer.
- Password verification compares the fixed-size derived key through the runtime's constant-work byte comparison helper.
- The map hash key is obtained from `/dev/urandom`; startup fails closed if entropy acquisition fails.

### Evidence gaps

- No provider-backed or validated cryptographic module is currently demonstrated.
- The custom implementations have not been externally audited in this review.
- Test vectors do not demonstrate constant-time machine code or absence of microarchitectural leakage.
- Runtime password-verifier iteration parsing has an excessive upper bound.
- Capstan-native PBKDF2 has no explicit upper work budget and stores scratch in ordinary GC lists.
- The generic Capstan crypto functions do not validate that each `List<int>` element is a byte in 0..255.
- No public secure-random API, AEAD API, key-separation abstraction, nonce lifecycle or authenticated envelope API is established in the current language surface.
- No evidence here establishes FIPS 140-3 validation. A FIPS algorithm specification is not a validated cryptographic module.

## 5. Explicit trust boundaries

1. **Untrusted source boundary:** command-line arguments, standard input, file contents, network data when introduced, environment values and imported serialized data must enter as tainted bytes.
2. **Validation boundary:** a validator may establish only the property it actually checks. Identifier validation does not validate a path, URL, SQL value or HTML fragment.
3. **Output-context boundary:** HTML, log, JSON, CSV, shell/process and SQL contexts are distinct. Escaping for one context must never be treated as validation for another.
4. **Authorisation boundary:** policy evaluation and grant rechecking establish only the encoded policy predicate. Correct business meaning and external state consistency remain application responsibilities.
5. **Filesystem boundary:** current path-based builtins exercise ambient process authority. The intended future boundary is an explicit directory/file capability plus handle-relative operations.
6. **Cryptographic boundary:** algorithm correctness depends on implementation correctness, parameters, entropy, key lifecycle, constant-time properties and provider/platform assumptions. Tags identify formats; they do not prove safe parameter choices.
7. **Secret boundary:** a Secret-typed allocation is protected from selected language-level sinks and is wiped when reclaimed; this is not a promise that all copies, environment storage, registers, swap, crash dumps or hardware remnants are erased.
8. **Runtime boundary:** C runtime, collector, C compiler, C library and operating system remain trusted implementation components.
9. **Bootstrap boundary:** the Python stage-0 translator is currently part of the bootstrap trust chain.
10. **Build/supply-chain boundary:** compiler binaries, build tools, dependencies, signing/provenance infrastructure and CI runners require their own assurance.

## 6. Security claims and assumptions

| Claim | Status | Evidence required / assumption |
|---|---|---|
| Untrusted values cannot reach selected sinks without validation/escaping | Implemented, scoped | Checker soundness, complete flow summaries, regression corpus |
| Sensitive-struct fields require protected access | Implemented, scoped | Type marking completeness and grant enforcement |
| Grants are object-bound and rechecked | Implemented, scoped | Checker/codegen/runtime agreement and adversarial identity tests |
| Integer and collection bounds are checked unless proven unnecessary | Implemented, scoped | Range-analysis soundness, differential tests and keep-checks mode |
| Collected Secret allocations are wiped | Implemented with qualifications | GC sweep-path tests; not deterministic destruction or copy erasure |
| Password hashes use PBKDF2-HMAC-SHA256 at 600,000 iterations | Implemented in C runtime | Entropy source, implementation correctness and explicit verifier work cap |
| Password verifier rejects excessive cost | **CI-verified; acceptance pending** | PR #134's exact-head run `45373743464` passed Ubuntu/GCC, Ubuntu/Clang, macOS/Clang and supply-chain on head `3a19978e42e86ab6e82a27d155a2dc0d841f6318`. Runtime-owner approval, Worker 5's current-only 600,000/legacy migration decision and architect acceptance remain outstanding. |
| Capstan-native PBKDF2 has bounded work | **Not satisfied** | No upper iteration bound |
| Capstan-native crypto intermediates are erased | **Not satisfied** | Ordinary GC-managed lists; no explicit wipe |
| Filesystem access is capability-confined | **Not implemented** | Current APIs accept ambient paths |
| Network access is capability-confined | Not implemented | No general network API |
| Runtime is memory safe | Not proven | C runtime and compiler remain trusted |
| Secret operations are constant-time | Not established generally | Compiler, target, length and microarchitecture assumptions |
| Whole Capstan language is formally verified | Not established | No completed machine-checked proof of the full implementation |

## 7. Formalisation roadmap

1. **Normative source semantics:** define taint, secret, grant, policy, declassification, arithmetic, collection and failure semantics independently of the implementation.
2. **Checker soundness:** prove or mechanically model that accepted programs preserve taint and secret restrictions, enforce protected calls and do not lose checks through incomplete analysis.
3. **Grant model:** formalise policy evaluation, object identity, role binding, revalidation and grant lifetime. Prove that code generation preserves the checker decision.
4. **Resource semantics:** make allocation, recursion, input size, iteration counts and blocking operations explicit in the abstract machine. Prove bounded operations respect declared budgets.
5. **Secret-flow model:** specify permitted observations and declassification. Treat constant-time and physical erasure as separate properties requiring target-specific evidence.
6. **Typed IR and compiler correctness:** establish a semantics-preserving translation from source to typed IR and from IR to target code; include runtime calls and traps.
7. **Runtime refinement:** verify collection, object layout, bounds checks, secret allocation/wiping and capability system-call wrappers against the abstract machine.
8. **Trusted-base reduction:** retire generated C and the unchecked bootstrap stage only after equivalent conformance and proof gates are met.

Proof obligations must identify the theorem, model, assumptions, trusted proof checker, exact source revision and reproducible command. Fuzzing, tests, static analysis and proofs are complementary evidence, not interchangeable labels.

## 8. Coordination and next actions

- Do not edit `compiler/checker.cap`, `compiler/codegen.cap`, `runtime/capstan_rt.h`, `runtime/capstan_gc.h` or `lib/std/` while their owners are active without an explicit handoff.
- Coordinate the PBKDF2 cost policy with the T1 standard-library owner and runtime owner before changing APIs or implementation.
- Coordinate formal definitions with the language-semantics and formal-verification workstreams.
- Add regression tests with each confirmed implementation fix. For expensive-path tests, test the parser/budget decision without executing the deliberately excessive operation.
- Reassess all findings against the exact current `main` and implementation branch before declaring them resolved.
- All work remains on this dedicated branch and proceeds through a reviewable PR. No merge to `main` is authorised by this assessment.

## 9. Source basis

Primary source files reviewed include `AGENTS.md`, `docs/DESIGN-MAP.md`, `docs/SPEC.md`, `docs/CWE-COVERAGE.md`, `docs/STDLIB-V06.md`, `SECURITY.md`, `lib/crypto.cap`, `runtime/capstan_rt.h`, `runtime/capstan_gc.h`, `tests/crypto/check.py`, `tests/unit/test_runtime.c` and `tests/run.sh`. Coordination issue #25 and architecture issue #80 were also reviewed. The review did not execute the test suite; all test statements above describe repository test design/source evidence, not a fresh local test run.


## Post-merge integration status — 2026-11-24

- PR #72 merged the single-line field-filter linearisation. The 65,536-byte alternating-control regression measured 4,161,583–4,161,627 total Capstan allocation bytes across Linux/GCC, Linux/Clang and macOS/Clang, versus approximately 512 MiB of cumulative prefix copying before the fix.
- PR #79 merged the pixmap/font resource budgets and recursive composite regression; TrueType table-local spans remain open under issue #121.
- PR #124 merged the C-free core semantics and typed-IR contract. This is a specification/conformance artifact, not an implementation proof of compiler correctness.
- PR #53 merged the Anchor A0 headless workbench prototype; it does not provide a live editor, LSP integration or package manager.
