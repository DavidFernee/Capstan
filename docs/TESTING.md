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
| **Every release** (pushing a tag `vX.Y.Z`) | `scripts/release-check.sh`, then `tests/run.sh --full` | the same three; the release is published only if all pass, with the test reports attached |

## Making a release

1. Set `VERSION` in `compiler/main.cap` and change the changelog heading from `## X.Y.Z (unreleased)` to `## X.Y.Z`.
2. Run `make && scripts/release-check.sh vX.Y.Z && tests/run.sh --full` locally.
3. Merge, then tag and push: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. `.github/workflows/release.yml` repeats every check on every platform and publishes the release:
   the source archive, the test reports, SHA-256 checksums and notes taken from the changelog.

## Conformance

`docs/SPEC.md` defines the **conformance areas**, one per language feature. Every test declares the
areas it covers with a `// spec: area ...` line, and `tests/spec_coverage.py` fails the run if any area
has no tests or a test names an unknown area. The generated matrix is in [CONFORMANCE.md](CONFORMANCE.md).
A new feature is not finished until its area is in the spec and covered.

## Sections

| Section | What it proves |
|---|---|
| **spec coverage** | Every conformance area in the specification has at least one test. |
| **unit** | Runtime correctness against published reference vectors: SHA-256 (FIPS 180-2), HMAC-SHA256 (RFC 4231), PBKDF2-SHA256 (RFC 7914). Also validator edge cases at the 64-bit limits, tampered password hashes failing closed, 100,000-key maps, and collector retention of interior pointers, globals and large objects. An end-to-end round trip proves every byte value survives source → compiler → C → program output. |
| **reject** | Vulnerable programs (SQL/command/log injection, null dereference, hard-coded credentials, weak crypto, missing authorisation, grant misuse, policy weaknesses) are refused, each with its CWE number. |
| **diagnostics** | Ordinary mistakes (type errors, unknown names, syntax errors, missing returns) produce the exact expected message. |
| **runtime** | Programs that can only fail at run time (out-of-bounds access, overflow, division by zero, a grant replayed on another object, runaway recursion) stop safely with exit code 101 and the named CWE. |
| **ranges** | The range analysis proves exactly the expected checks unnecessary (`// expect-unchecked: N`), `--keep-checks` gives the same result with every check in place, and the compiler reports how many of its own checks it proves away. Runtime tests (`tests/runtime/range_*.cap`) cover each trap: loops up to the 64-bit limits, lists shrinking in the body, the condition or through an alias, reassigned variables and boundary guards. |
| **conformance** | Programs covering each section of the language reference must (1) print exactly the expected output, (2) agree with the independent stage-0 implementation, and (3) produce C that compiles with `-Wall -Wextra -Werror`. |
| **gc** | Memory stays bounded: the churn test allocates more than 500 MB with a peak heap under 64 MB. Collecting on every single allocation must not change any value. The compiler's output is unchanged under collector stress. |
| **limits** | Pathological input (100,000 nested parentheses or blocks, 50,000-term expressions, 20,000-statement functions) gets a diagnostic or compiles; it never crashes the compiler. |
| **cwe atlas** | An attempt to write each of about 250 code-level CWEs in Capstan; every verdict (rejected, stopped, neutralised, inexpressible, gap) is re-checked. |
| **fuzz** | *Differential:* random well-typed programs (values near the 64-bit limits, zero divisors, edge-case indexes, and guards, limit loops and shrinking lists aimed at the range analysis) must give identical output and exit codes from the native compiler and stage 0, which has no range analysis, including identical safety stops. *Mutation:* corrupted versions of every program in the repository must never crash or hang the compiler, and any program it accepts must produce valid C. |
| **sanitizers** | The compiler (under collector stress), the formatter, the runtime unit tests and every conformance program and example run clean under AddressSanitizer and UndefinedBehaviorSanitizer. |
| **bootstrap** | The compiler reproduces itself byte for byte; it does so when built with a different C compiler too; stage 0 still bootstraps to the identical compiler; the compiler passes its own `--strict --release` checks; its generated C is warning-free. |
| **examples** | Example programs pass `--release` checks (including mandatory denial tests) and their own tests. The test runner itself reports failures correctly and keeps going after one. |
| **fmt** | The formatter produces the expected layout and is idempotent; every source file in the repository is already formatted; `--check` changes nothing; unscannable files are refused. *Whitespace fuzz:* every formatted file, with its indentation, spacing, tabs, trailing whitespace and blank lines scrambled, must be restored byte for byte. *Corruption fuzz:* randomly corrupted files are formatted or refused, never crash or hang the formatter. Building the formatter must report exactly one warning: the AUDIT for its single `trust()`. |
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
- A range-analysis count: add `// expect-unchecked: N` to any test; the suite counts the unchecked operations in its C.
- A conformance program: `tests/accept/name.cap` plus `name.out` with the exact expected output.
- A formatter case: `tests/fmt/name.cap` (the input) plus `name.fmt` (the exact expected result).
- Every test file carries a `// spec:` line naming the conformance areas it covers.
- A runtime test may set environment variables with `// env: NAME=value`.
