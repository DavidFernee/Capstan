# Changelog

Every release is gated by `scripts/release-check.sh` and the full test suite
(`tests/run.sh --full`) on Linux (GCC, Clang) and macOS (Clang). See
[docs/TESTING.md](docs/TESTING.md).

## 0.4.0 (unreleased)
- Struct methods
- String interpolation: `$"Hello {name}"`, with every taint and context rule preserved
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
