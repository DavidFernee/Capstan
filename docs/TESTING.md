# How Capstan is tested

```sh
tests/run.sh          # standard run, about two minutes
tests/run.sh --full   # adds long fuzzing campaigns and the benchmark gate
```

Every safety claim in [CWE-COVERAGE.md](CWE-COVERAGE.md) is backed by at least one test below.
CI runs the standard suite on Linux (GCC and Clang) and macOS (Clang) for every change,
and the full suite nightly.

## Sections

| Section | What it proves |
|---|---|
| **unit** | Runtime correctness against published reference vectors: SHA-256 (FIPS 180-2), HMAC-SHA256 (RFC 4231), PBKDF2-SHA256 (RFC 7914). Also validator edge cases at the 64-bit limits, tampered password hashes failing closed, 100,000-key maps, and collector retention of interior pointers, globals and large objects. An end-to-end round trip proves every byte value survives source → compiler → C → program output. |
| **reject** | Vulnerable programs (SQL/command/log injection, null dereference, hard-coded credentials, weak crypto, missing authorisation, grant misuse, policy weaknesses) are refused, each with its CWE number. |
| **diagnostics** | Ordinary mistakes (type errors, unknown names, syntax errors, missing returns) produce the exact expected message. |
| **runtime** | Programs that can only fail at run time (out-of-bounds access, overflow, division by zero, a grant replayed on another object, runaway recursion) stop safely with exit code 101 and the named CWE. |
| **conformance** | Programs covering each section of the language reference must (1) print exactly the expected output, (2) agree with the independent stage-0 implementation, and (3) produce C that compiles with `-Wall -Wextra -Werror`. |
| **gc** | Memory stays bounded: the churn test allocates more than 500 MB with a peak heap under 64 MB. Collecting on every single allocation must not change any value. The compiler's output is unchanged under collector stress. |
| **limits** | Pathological input (100,000 nested parentheses or blocks, 50,000-term expressions, 20,000-statement functions) gets a diagnostic or compiles; it never crashes the compiler. |
| **fuzz** | *Differential:* random well-typed programs (values near the 64-bit limits, zero divisors, edge-case indexes) must give identical output and exit codes from the native compiler and stage 0, including identical safety stops. *Mutation:* corrupted versions of every program in the repository must never crash or hang the compiler, and any program it accepts must produce valid C. |
| **sanitizers** | The compiler (under collector stress), the runtime unit tests and every conformance program and example run clean under AddressSanitizer and UndefinedBehaviorSanitizer. |
| **bootstrap** | The compiler reproduces itself byte for byte; it does so when built with a different C compiler too; stage 0 still bootstraps to the identical compiler; the compiler passes its own `--strict --release` checks; its generated C is warning-free. |
| **examples** | Example programs pass `--release` checks (including mandatory denial tests) and their own tests. The test runner itself reports failures correctly and keeps going after one. |
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
```

Fixed failures should be minimised and added to the relevant directory as
permanent regression tests.

## Adding a test

- A rejected program: `tests/reject/name.cap`, with first line `// expect: CWE-nnn`
  (optionally `// flags: --strict` or `--release`).
- A runtime stop: `tests/runtime/name.cap`, with `// expect-runtime: CWE-nnn`.
- A conformance program: `tests/accept/name.cap` plus `name.out` with the exact expected output.
