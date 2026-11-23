# Changelog

Every release is gated by `scripts/release-check.sh` and the full test suite
(`tests/run.sh --full`) on Linux (GCC, Clang) and macOS (Clang). See
[docs/TESTING.md](docs/TESTING.md).

## 0.4.0 (unreleased)
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
