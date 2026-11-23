# How Capstan is tested

```sh
tests/run.sh          # standard run, about two minutes
tests/run.sh --full   # adds long fuzzing campaigns and the benchmark gate
```

Every safety claim in [CWE-COVERAGE.md](CWE-COVERAGE.md) is backed by at least one test below.

## When the suite runs

| Event | What runs | Where |
|---|---|---|
| Every push and pull request | `tests/run.sh` | Linux (GCC, Clang), macOS (Clang) |
| Nightly | `tests/run.sh --full` | the same three |
| **Every release** (pushing a tag `vX.Y.Z`) | `scripts/release-check.sh`, `scripts/repro.sh`, then `tests/run.sh --full`; then SBOMs, provenance and signatures, checked by `scripts/verify-release.sh` | the same three; the release is published only if all pass, with the test reports and supply-chain evidence attached |

## Making a release

1. Set `VERSION` in `compiler/main.cap` and `LSP_VERSION` in `tools/lsp.cap`, and change the changelog heading from `## X.Y.Z (unreleased)` to `## X.Y.Z`.
2. Run `make && scripts/release-check.sh vX.Y.Z && tests/run.sh --full` locally.
3. Merge, then tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. `.github/workflows/release.yml` repeats every check on every platform and publishes the release.
   Its jobs each get only the permissions they need:
   - **verify** (every platform, read-only): bootstrap, `release-check.sh`, a reproducibility report
     (`scripts/repro.sh`: the fixpoint and the SHA-256 of `build/stage2.c` and `build/stage3.c`),
     and `tests/run.sh --full`.
   - **assemble** (read-only): the source archive (`git archive` of the tagged commit), SBOMs in
     CycloneDX 1.6 and SPDX 2.3 (`scripts/sbom.py`, validated against the official schemas by
     `scripts/sbom-validate.py`), `SHA256SUMS`, and `verify-release.sh --rebuild`, which also
     checks that every platform reported the same checksums and that the archive rebuilds to them.
   - **sign** (may request an OIDC token and write attestations, cannot write to the repository):
     SLSA build provenance for every file (GitHub artifact attestations), a keyless Sigstore
     signature for every file and for `SHA256SUMS`, then `verify-release.sh` exactly as a user runs it.
   - **publish** (may create the release, runs no repository code): uploads the verified files.

   Release assets, for version X.Y.Z:

   | File | What it is |
   |---|---|
   | `capstan-X.Y.Z.tar.gz` | the source archive |
   | `capstan-X.Y.Z.cdx.json`, `capstan-X.Y.Z.spdx.json` | SBOM (CycloneDX, SPDX): every file in the archive with its hashes, the build tools (a C compiler, make, Python 3 for stage 0 and the tests, bash), and the only run-time dependency, the platform C library; no third-party code |
   | `reproducibility-<os>-<cc>.txt` | per platform: the compiler reproduced itself, and the checksums of `build/stage2.c` and `build/stage3.c` (identical on every platform) |
   | `test-report-<os>-<cc>.txt` | the full test suite's output per platform |
   | `SHA256SUMS` | SHA-256 of every file above |
   | `*.sigstore.json` | a Sigstore signature bundle for each file above and for `SHA256SUMS` |
   | `capstan-X.Y.Z.intoto.jsonl` | the SLSA provenance attestation (also stored in the repository's attestations) |

   Every action the workflows use is pinned by commit, every workflow is read-only by default,
   and `tests/supply/workflows.py` (part of the suite) enforces both.

## Verifying a release

From a clone of the repository (read `scripts/verify-release.sh` first: it is short), with
[cosign](https://docs.sigstore.dev/cosign/system_config/installation/) 3.0 or later and the
[GitHub CLI](https://cli.github.com/) logged in (`gh auth login`):

```sh
scripts/verify-release.sh vX.Y.Z              # download the release and check everything
scripts/verify-release.sh vX.Y.Z DIR          # check files already downloaded into DIR
scripts/verify-release.sh --rebuild vX.Y.Z    # also rebuild the compiler from the archive here
```

It fails unless:

1. every file matches `SHA256SUMS`, and nothing unlisted is present;
2. every file and `SHA256SUMS` carries a Sigstore signature made by this repository's
   `release.yml` workflow for that tag, through GitHub's OIDC issuer;
3. `gh attestation verify` finds SLSA build provenance for every file, made by `release.yml`
   from that tag on a GitHub-hosted runner;
4. both SBOMs describe exactly the files in the archive (`scripts/sbom.py check`);
5. every platform's reproducibility report shows the fixpoint, with the same checksums;
6. with `--rebuild`, bootstrapping the archive here (a C compiler, make and Python 3) gives
   those same checksums: the compiler you build is byte for byte the one that was tested.

The same checks by hand:

```sh
sha256sum -c SHA256SUMS            # macOS: shasum -a 256 -c SHA256SUMS
cosign verify-blob --bundle SHA256SUMS.sigstore.json \
  --certificate-identity https://github.com/DavidFernee/Capstan/.github/workflows/release.yml@refs/tags/vX.Y.Z \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com SHA256SUMS
gh attestation verify capstan-X.Y.Z.tar.gz --repo DavidFernee/Capstan \
  --signer-workflow DavidFernee/Capstan/.github/workflows/release.yml --source-ref refs/tags/vX.Y.Z
```

`--skip-signatures` and `--skip-attestations` leave out checks 2 and 3, for machines without
network access; the remaining checks then show only that the files are consistent with each
other, not who made them.

## Conformance

`docs/SPEC.md` defines the **conformance areas**, one per language feature. Every test declares the
areas it covers with a `// spec: area ...` line, and `tests/spec_coverage.py` fails the run if any area
has no tests or a test names an unknown area. The generated matrix is in [CONFORMANCE.md](CONFORMANCE.md).
A new feature is not finished until its area is in the spec and covered.

## Sections

| Section | What it proves |
|---|---|
| **spec coverage** | Every conformance area in the specification has at least one test. |
| **unit** | Runtime correctness against published reference vectors: SHA-256 (FIPS 180-2), HMAC-SHA256 (RFC 4231), PBKDF2-SHA256 (RFC 7914). Every validator and escaper against its specification: `validate_path` (traversal, absolute paths, NUL bytes, the 4096-byte limit), `validate_range`, `escape_csv` (every formula prefix), `escape_log` (C1 controls, bidirectional overrides, line separators, invalid and overlong UTF-8, plus every 2-byte input), `secret_eq`; `read_file`, `write_file` and `read_line` with every byte value, NUL bytes, directories, missing files and `/proc`. Also tampered password hashes failing closed, 100,000-key maps and collector retention. `escape_log` must agree byte for byte with stage 0 on 73,000 inputs. *Interval properties:* the range analysis's arithmetic, compiled from the compiler's own sources, is checked against exact arithmetic for every pair of intervals over the 64-bit edge values (180,500 operations). *Lint table:* every credential format, magic-number name and comment marker, each with a near miss that must not be flagged. |
| **reject** | Vulnerable programs (SQL/command/log injection, null dereference, hard-coded credentials, weak crypto, missing authorisation, grant misuse, policy weaknesses) are refused, each with its CWE number. |
| **diagnostics** | Ordinary mistakes (type errors, unknown names, syntax errors, missing returns) produce the exact expected message. |
| **recovery** | A file with several syntax errors reports every one of them, at the exact line and column, in one run; a file with very many stops after 50. |
| **runtime** | Programs that can only fail at run time (out-of-bounds access, overflow, division by zero, a grant replayed on another object, runaway recursion) stop safely with exit code 101 and the named CWE. |
| **ranges** | The range analysis proves exactly the expected checks unnecessary (`// expect-proved: N`), `--keep-checks` gives the same result with every check in place, and the compiler reports how many of its own checks it proves away. Runtime tests (`tests/runtime/range_*.cap`) cover each trap: loops up to the 64-bit limits, lists shrinking in the body, the condition or through an alias, reassigned variables and boundary guards. |
| **io** | A program reads standard input (NUL bytes, CRLF, a 10,000-byte line, escape sequences, an unterminated last line) and writes and reads files (every byte value, empty files, directories, missing files, a NUL in the path), under both the native compiler and stage 0, which must agree with each other and with the expected output. |
| **portability** | Every conformance program and every safety stop behaves identically at `-O0`, `-O2` and `-O3`, with each C compiler available (GCC and Clang in CI). |
| **conformance** | Programs covering each section of the language reference must (1) print exactly the expected output, (2) agree with the independent stage-0 implementation, and (3) produce C that compiles with `-Wall -Wextra -Werror`. |
| **gc** | Memory stays bounded: the churn test allocates more than 500 MB with a peak heap under 64 MB. Collecting on every single allocation must not change any value. The compiler's output is unchanged under collector stress. |
| **limits** | Pathological input (100,000 nested parentheses or blocks, 50,000-term expressions, 20,000-statement functions) gets a diagnostic or compiles; it never crashes the compiler. |
| **cwe atlas** | An attempt to write each of about 250 code-level CWEs in Capstan; every verdict (rejected, stopped, neutralised, inexpressible, gap) is re-checked. |
| **fuzz** | *Differential:* random well-typed programs (a third of them also built with ASan and UBSan, including signed-overflow detection, so undefined behaviour is caught even when the output happens to match) (values near the 64-bit limits, zero divisors, edge-case indexes, and guards, limit loops and shrinking lists aimed at the range analysis) must give identical output and exit codes from the native compiler and stage 0, which has no range analysis, including identical safety stops. *Mutation:* corrupted versions of every program in the repository must never crash or hang the compiler, and any program it accepts must produce valid C. |
| **sanitizers** | The compiler (under collector stress), the formatter, the runtime unit tests and every conformance program and example run clean under AddressSanitizer and UndefinedBehaviorSanitizer. |
| **bootstrap** | The compiler reproduces itself byte for byte; it does so when built with a different C compiler too; stage 0 still bootstraps to the identical compiler; the compiler passes its own `--strict --release` checks; its generated C is warning-free. |
| **examples** | Example programs pass `--release` checks (including mandatory denial tests) and their own tests. The test runner itself reports failures correctly and keeps going after one. |
| **fmt** | The formatter produces the expected layout and is idempotent; every source file in the repository is already formatted; `--check` changes nothing; unscannable files are refused. *Whitespace fuzz:* every formatted file, with its indentation, spacing, tabs, trailing whitespace and blank lines scrambled, must be restored byte for byte. *Corruption fuzz:* randomly corrupted files are formatted or refused, never crash or hang the formatter. Building the formatter must report exactly one warning: the AUDIT for its single `trust()`. |
| **supply chain** | SBOMs are deterministic, record the build tools and the C library as the only run-time dependency, and `sbom.py check` catches a changed file; the reproducibility report matches the build; `verify-release.sh` accepts a correct release (rebuilding its archive) and rejects a changed, missing or unlisted file, a path in `SHA256SUMS`, a missing or mismatched SBOM, a failed fixpoint, platforms that disagree and an unsigned release; the workflows pin every action by commit, default to read-only and expand no untrusted data in scripts (`tests/supply/`). |
| **lsp** | The language server (`tests/lsp/`). *Agreement:* every program in `tests/reject`, `tests/diagnostics` and `tests/accept` is opened in the server, which must publish exactly the diagnostics `capstanc` reports (line, column in UTF-16 units, severity, code, CWE link, message, and the test's own `// expect:` text), and clear them on close; `tests/lsp/diagnostics.cap` must give exactly `tests/lsp/diagnostics.json`. *Protocol:* lifecycle and exit codes, full and incremental sync, UTF-16 and UTF-8 positions, `\u` escapes and surrogate pairs, imports from open documents and from disk, `--strict` through `initializationOptions`, and the JSON-RPC error for each kind of malformed JSON, invalid request, unknown method, bad framing (missing, invalid or repeated lengths, 200 KB header lines, too many headers, a body without a header) and a message over 16 MiB, each followed by a request that must still be answered. *Fuzz:* sessions of random and corrupted JSON, random requests and mutated programs (with intact framing, they must still answer `shutdown` and exit 0) and of corrupted framing and random bytes: never a crash, a runtime stop, output on stderr, a hang or a malformed reply. The same sessions run under ASan and UBSan with collector stress. The build must report no warnings (so no `trust()`). |
| **coverage** | (`--full`) Line coverage of the compiler, the formatter and the runtime under the suite's workloads, through the `#line` mapping (`tests/coverage.py`, report in [COVERAGE.md](COVERAGE.md)); no file may fall below its floor in `tests/coverage_floors.txt`. |
| **compiler mutation** | (`--full`) Mutants of the compiler (a flipped comparison, `&&` for `\|\|`, an inverted boolean, a deleted diagnostic or guard) must each be caught by the suite (`tests/mutate_compiler.py`); see below. |
| **bench** | (`--full`) Speed against equivalent hand-written C, failing if any benchmark exceeds the regression limit. |

## Two independent implementations

The stage-0 bootstrap (`bootstrap/capstan0.py`) is a separate, deliberately simple
implementation of Capstan's semantics. Running programs both ways and requiring
identical results catches code-generation bugs that neither implementation would
reveal alone. In development it has already found bugs in stage 0 itself
(escape handling, constant initialisation order, source encoding).

## Reproducing a fuzz failure

Failing inputs are saved to `tests/fuzz/failures/`. Re-run with the reported seed:

```sh
python3 -I tests/fuzz/gen.py 1000 <seed>
python3 -I tests/fuzz/mutate.py 50000 <seed>
FUZZ_SEED=<seed> tests/run.sh            # formatter fuzzing; failures go to tests/fmt/failures/
```

Fixed failures should be minimised and added to the relevant directory as
permanent regression tests.

## Adding a test

- A rejected program: `tests/reject/name.cap`, with first line `// expect: CWE-nnn`
  (optionally `// flags: --strict` or `--release`).
- A runtime stop: `tests/runtime/name.cap`, with `// expect-runtime: CWE-nnn`.
- A range-analysis count: add `// expect-proved: N` to any test; the suite counts the operations in its C whose check was proved unnecessary.
- A conformance program: `tests/accept/name.cap` plus `name.out` with the exact expected output.
- A formatter case: `tests/fmt/name.cap` (the input) plus `name.fmt` (the exact expected result).
- Every test file carries a `// spec:` line naming the conformance areas it covers.
- A runtime test may set environment variables with `// env: NAME=value`.

## Measuring the tests themselves

Two tools measure how good the suite is, rather than how good the compiler is.

**Coverage** (`tests/coverage.py`) runs every test program, example, the CWE atlas and short
fuzzing campaigns through instrumented builds and reports which lines of the compiler, the
formatter and the runtime were reached, as Capstan source lines. Its first run found 28 checker
diagnostics that no test had ever triggered, eight of them security checks, and runtime functions
(`validate_path`, `validate_range`, `escape_csv`, `secret_eq`, file and line input) that were
compiled by tests but never executed. Writing those tests found two real bugs: `read_line` lost
bytes after a NUL and merged lines, and `read_file` on a directory stopped the program instead of
returning `none`. Reviewing `escape_log` while testing it found that it let C1 controls, Unicode
bidirectional overrides and line separators through.

**Mutation testing** (`tests/mutate_compiler.py COUNT SEED [files]`) builds compilers with one
deliberate bug each and runs the suite's oracles against them. A surviving mutant is behaviour no
test pins down: it becomes a test, or is recorded below as equivalent. `--replay REPORT` re-runs
the survivors of an earlier report.

```sh
python3 -I tests/coverage.py --check              # report, and fail below the floors
python3 -I tests/mutate_compiler.py 80 7          # 80 mutants of ranges.cap and checker.cap
python3 -I tests/mutate_compiler.py --replay old.log
```

Equivalent mutants found so far (changes that cannot alter behaviour), with the reason:

- `checker.cap`, the laundering fixpoint: mutating `same_summary`, the per-round resets of
  `returns` and `sinks`, or `changed = false` only makes the bounded fixpoint run more rounds;
  its result is the same.
- `codegen.cap`, `forget(...)` for match and if-let bindings, and `ranges.cap`, `mentions()`
  in loop steps: defence in depth. Capstan forbids shadowing, so a binding can never reuse the
  name of a variable with recorded facts, and a loop variable is not yet in scope when its
  step is analysed, so its range is already "any value".
- `codegen.cap`, `g.ind` (indentation of the generated C) and `lexer.cap`, `lx.pos > part` before
  a `{{` (it can only add an empty `+ ""` to an interpolated string): output layout only.
- `ranges.cap`, `literal_value()`'s test for a negated literal: only called once `is_literal()`
  has confirmed one of the two shapes it handles.
- `lexer.cap`, the digit counter of a hexadecimal literal: it is only ever compared with zero.
- `checker.cap`, the not-an-enum fallback of `simple_enum()` (only ever called with an enum's
  name) and the grant-parameter loop's bound (one step further reaches the body node, which is
  never a grant).

Results so far: the first campaign (80 mutants of the range analysis and checker, 40 of the
lexer, parser and code generator) killed 62% and 82%. Every non-equivalent survivor became a test,
and those tests found four real bugs (above, and the `exit()` warning and a stage-0 scoping bug).
A fresh campaign on new seeds then killed 60 of 70 at once (86%); of the other ten, five were
equivalent and five became tests, so every non-equivalent mutant in it is now caught.

Mutating only the lines a change adds (`file.cap:FROM-TO` targets) is how new features are
checked: the bitwise operators first scored 58%, and their survivors became tests (laundering
through every arithmetic operator, the ranges of `|`, `^`, `>>`, `>>>`, lowercase hex digits,
unspaced `x>(y)`). Making the mutation oracles require warning-free C, as the conformance section
does, also found that a statement discarding a value (`xs.remove_at(0);`) produced C that
warned; it is now cast to `void`, and the safety-stop tests are compiled with `-Werror` too.
