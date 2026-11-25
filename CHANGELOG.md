# Changelog

Every release is gated by `scripts/release-check.sh` and the full test suite
(`tests/run.sh --full`) on Linux (GCC, Clang) and macOS (Clang). See
[docs/TESTING.md](docs/TESTING.md).

## 0.4.0 (unreleased)
- Security assurance: make v1.0 a C-free, evidence-gated release on Linux, macOS and Windows; add mandatory CWE/security acceptance criteria, explicit unknown/residual evidence states and a per-release assurance scorecard. Current C-backend status remains explicit; this is a release requirement, not a claim of implementation.
- Security: password verifier accepts only the canonical 123-byte, 600,000-iteration PBKDF2-SHA256 record profile and caps password inputs at 256 bytes; malformed, noncanonical, oversized and legacy-cost records are rejected before KDF work. The format is unreleased in 0.4.0, so no legacy-record compatibility is promised; development credentials using older profiles must be recreated before upgrade.
- Anchor A0: headless IDE workbench prototype using Shroud S0; static navigation and read-only preview only, with no live compiler connection or project commands executed
- Anchor direction: WYSIWYG Shroud designer with Capstan source as the authoritative representation, plus a curated, version-pinned catalogue of security-reviewed components
- Anchor catalogue contract: immutable package/dependency identity, signed provenance, scoped assurance claims, offline verification with explicit revocation freshness, transitive capability accounting and authentication-specific review gates
- Security: reject embedded-NUL `secret_env` names at compile time and runtime; cap `read_line()` input at 1 MiB with a fail-closed CWE-789 diagnostic and boundary regressions
- Authorisation: reject policies with more than eight struct-identity roles at compile time instead of accepting code that later fails closed at runtime
- Security: the compiler refuses to proceed when interprocedural taint summaries exhaust their fixpoint budget; a deep helper-chain regression prevents CWE-20 laundering through incomplete analysis
- Assurance: CI and release assembly fail when active or qualified claims have stale reviews/evidence; empty claim inventories are invalid, and stale MEM-001 is downgraded pending re-review
- Assurance: claim reviews and evidence now report stale status when covered implementation or evidence artifacts change after their recorded Git revision
- Shroud, the cross-platform GUI library, begins (`lib/shroud/`, design in `docs/SHROUD.md`), written
  entirely in Capstan: an anti-aliased integer rasteriser, a hardened TrueType parser, strict UTF-8
  text, constraint layout, sixteen widgets, keyboard navigation and focus, an accessibility tree
  with WCAG 2.2 checks, and light and dark themes. Text fields yield `Tainted`, deceptive
  characters in untrusted text are shown rather than obeyed (CWE-451), and danger buttons are
  guarded against clickjacking (CWE-1021). It renders headless to PNG until the platform embedders
  arrive. Checked against exact polygon areas, fontTools, Python's UTF-8 decoder and zlib, fuzzed
  with damaged fonts, and pinned by golden frames that are identical on every platform. It bundles
  Latin subsets of the DejaVu Sans fonts (Bitstream Vera licence), which the SBOM now lists.
- CI: pushes are tested only on `main` (branches through their pull requests), and a newer commit on
  a pull request cancels the older run, so bursts of commits no longer queue dozens of runs
- `AGENTS.md` for OpenAI Codex, identical to `CLAUDE.md` (a test checks): every change through a
  pull request, claims on the coordination issue, and every commit and comment names its agent
- IDE supply-chain design (DESIGN-MAP section 5): a live SBOM including the toolchain, continuous
  checks against every vulnerability source with reachability and VEX, and remediation by default
  behind signature, capability, cooling-off, test and compatibility gates
- Collector returns empty pages to the operating system beyond a reserve, and reuses them for any
  size class before requesting new memory; empty pages are no longer swept. A program that builds
  and drops 140 MB ends at 53 MB resident instead of 180 MB and runs 2.6 times faster
- `List<bool>` stores its elements as C `bool` rather than `uint8_t`: a byte store may alias
  anything, so the C compiler reloaded the list's length and storage after every write. The
  `arrays` benchmark runs 16% fewer instructions.
- Maps hash their keys with SipHash-1-3 under a random key chosen once per process, instead of
  FNV-1a: keys an attacker chooses can no longer be made to collide and turn every lookup into a
  scan (hash flooding, CWE-407). Iteration order is unchanged (insertion order). Checked against
  the published SipHash vectors and an independent implementation; about 5% slower on the
  map-heaviest benchmark.
- `int_to_str` writes digits itself instead of calling `snprintf` (which was 38% of the `strings`
  benchmark): that benchmark goes from 1.9× C to 1.2×, and one more libc formatting call leaves the
  runtime. Checked against `snprintf` on every power-of-ten boundary and a million random values.
- T3 begins: SHA-256, HMAC-SHA256 and PBKDF2-HMAC-SHA256 written in Capstan (`lib/crypto.cap`),
  checked against hashlib on generated inputs, the FIPS 180-4 examples, and the runtime's C
  `hash()` and `hash_password()`; not yet used by those builtins (that needs T1, the standard
  library mechanism).
- Range analysis across calls: each integer parameter gets the range of its arguments at every
  call site in the program (recursion included, by an iterated and widened fixpoint), so checks in
  helpers called with small values are left out. A function called anywhere with any value gets
  nothing; `--keep-checks` still keeps every check.
- `escape_json(t)`: any text made safe inside a JSON string (always valid JSON, and safe inside an
  HTML `<script>`), and `taint_char(c)`: a byte that stays untrusted, so escapes in untrusted text
  (`%41`, `\u0041`) can be decoded without laundering it. Both requested by the language server.
- `read_file()` is bounded: it gives `none` for a file longer than its limit (default 2^30, or
  `read_file(path, max)`), so `/dev/zero` or an endless pipe cannot exhaust memory (CWE-400), and
  opening a FIFO with no writer no longer blocks. The compiler, formatter and language server read
  source files of at most 16 MiB.
- Security fixes from an attack review of the compiler (each with a regression test and an atlas
  entry): bytes of untrusted input stay untrusted when used as list indexes, slice bounds or map
  keys (CWE-20); shells, interpreters and launchers named in `run()` take only literal arguments
  (CWE-78); every computed `run()` argument follows `"--"`, and `validate_path()` refuses a leading
  `-` (CWE-88); `escape_html()` output is rejected in unquoted, URL, event-handler and style
  attributes and in script, style and comment blocks (CWE-79); `hash()` of a `Secret` is an error
  (CWE-532); bidirectional and zero-width characters are rejected in source (CWE-1007, Trojan
  Source); grants are re-evaluated at each protected call (CWE-367)
- Threat model brought up to date with signed releases, SBOMs and attestations
- `read_bytes(n)` and `flush()`: read exactly `n` bytes of standard input (untrusted, like
  `read_line`; `n` outside 0..2^30 stops with CWE-789) and write out what has been printed, so a
  Capstan program can hold a framed conversation over a pipe. The language server needs both.
- Parser error recovery: after a syntax error the parser resumes at the next statement or
  declaration, so one run reports every independent syntax error (at most 50, so the output stays
  bounded). Needed by the language server.
- The Capstan Challenge, drafted (docs/CHALLENGE.md, DESIGN-MAP section 8): a planned yearly
  prize for writing a vulnerability Capstan claims is impossible, subject to funding for a
  foundation to administer the language; until then, confirmed findings are credited in its hall
  of fame
- Bitwise operators `& | ^ ~ << >> >>>`, hexadecimal literals and `wrapping_add/sub/mul/shl`
  (trusted-base stage T2). Shift counts must be 0..63 (CWE-1335); `<<` that loses bits stops
  (CWE-190); mixing a bitwise operator with another operator needs parentheses (CWE-783);
  bitwise operators on `bool` are rejected (CWE-480). Taint flows through all of them, and the
  range analysis proves shift counts and masks.
- `capstan lsp`, the first version of the language server (DESIGN-MAP section 5, phase A), written
  in Capstan and built with the compiler's own lexer, parser and checker: editors get exactly the
  compiler's diagnostics, with CWE codes linked to cwe.mitre.org. JSON-RPC over stdio with
  Content-Length framing, a JSON parser and writer in Capstan, full and incremental sync, UTF-16
  and UTF-8 positions, imports; JSON-RPC errors for malformed input and bounded sizes (CWE-400);
  no `trust()`. Tested for agreement with the compiler on every test program, protocol behaviour,
  sanitizers and fuzzing (`tests/lsp/`). Pure Capstan, using `read_bytes()` and `flush()`
- K0, the first kernel study: every Linux kernel CVE published in 2025, classified from its fix and
  run through the CWE atlas with stated kernel adjustments (`tools/k0/`, docs/K0-KERNEL-CVES.md),
  with a hand-labelled held-out sample to measure the classifier
- K1 kernel-mode design (DESIGN-MAP section 7) aimed at what K0 found Capstan does not yet prevent:
  ownership and linear resources, data guarded by its lock, RCU as a type, execution contexts, lock
  levels, structured concurrency, typed views, checked shifts, entry-point policies, speculation
  hardening, bounded loops and declared formats; K0 projects the effect on the same CVEs
- K0 review: all 588 CVEs the classifier could not decide (or called speculative execution) read
  and classified by hand (`tools/k0/data/reviewed-2025.csv`); 4 of 2,702 remain undeterminable.
  Measured today: 60.6% prevented; with K1.1 to K1.9: 79.1%; with K1.10 proofs: 98.7%
- K1.8 extended (speculatively constant-time secrets, automatic per-processor mitigations, CFI) and
  K1.10, proof against a specification: contracts, lock invariants, protocols, termination,
  non-interference between security domains, refinement for the core, an independent proof checker,
  and the guarantee Capstan will claim, with its stated limits
- Testing measured, not assumed: line coverage of the compiler, formatter and runtime with
  enforced floors (`tests/coverage.py`, docs/COVERAGE.md), and mutation testing of the compiler
  (`tests/mutate_compiler.py`); ASan and UBSan on fuzzed programs; every conformance program and
  safety stop at -O0/-O2/-O3 with GCC and Clang; interval-arithmetic property tests; a lint table
  for every credential format, magic-number name and comment marker; end-to-end input/output tests
- 31 diagnostics that no test had triggered (eight security checks) now have tests
- Fixed: `read_line()` lost the bytes after a NUL and merged lines; `read_file()` stopped the
  program on a directory instead of giving none, and trusted the reported size (pipes, /proc)
- Fixed: `escape_log()` let C1 controls (8-bit CSI), bidirectional overrides, line separators and
  invalid UTF-8 through (CWE-117/150); `read_file()`/`write_file()` refuse paths with NUL bytes (CWE-158)
- Fixed: generated C for a function ending in `exit()` warned under -Werror; stage 0 resolved a
  local that shares an enum's name to the enum
- Struct methods
- String interpolation: `$"Hello {name}"`, with every taint and context rule preserved
- Range analysis: overflow, division and bounds checks are left out only where proved
  unnecessary (186 of the compiler's own 855); `--keep-checks` keeps them all.
  The heap is capped at 2^48 bytes, which bounds every length.
- Unboxed `int?` for `if (let v = m.get(k))` and `xs.pop()`
- Benchmarks: `calls` now measures 33 million unfoldable calls; naive Fibonacci is `fib`
- `capstan fmt` formatter (written in Capstan, whitespace-only, verified token for token),
  with `--check` for CI; the repository is formatted and the suite enforces it
- Conformance areas in the specification, with coverage enforced on every run
- Release pipeline: the full suite on every platform before a release is published
- Supply-chain evidence on every release: CycloneDX 1.6 and SPDX 2.3 SBOMs (`scripts/sbom.py`,
  schema-validated), SLSA build provenance (GitHub artifact attestations), keyless Sigstore
  signatures, per-platform reproducibility reports (fixpoint and stage2/stage3 checksums), and
  `scripts/verify-release.sh` to check a download, optionally rebuilding it; workflows pin every
  action by commit and are read-only by default, with write access only where needed
- CWE gap closures: `Html`/`LogText` context types, `sensitive struct`, credential-format
  literal scanning, laundering through collections, heap limit, secret wiping,
  `escape_csv`, `validate_path`, `validate_range`, six new lints

## 0.3.0
- Enums with exhaustive `match`; modules; diagnostics with columns, excerpts and suggestions;
  `x++`; list and map operations; packed `List<bool>`
- CWE red-team atlas covering 254 weaknesses

## 0.2.0
- Garbage collector, stack-overflow guard, `#line` source mapping
- Commercial-grade test suite: crypto vectors, differential and mutation fuzzing,
  sanitizers, GC stress, limits, benchmarks
- Apache-2.0 licence

## 0.1.0
- Self-hosting compiler with CWE-numbered safety diagnostics, taint tracking, secrets,
  policies and grants, agile hashing
