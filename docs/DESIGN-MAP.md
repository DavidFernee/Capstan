# Capstan design map

## 1. Purpose

Capstan's goal: **with familiar C/Java syntax, make every common vulnerability class
either impossible to express or a compile error, and say plainly what remains.**

## 2. Design principles

1. **Unsafe is unrepresentable.** Prefer removing the dangerous construct (null,
   pointers, shells, format strings, weak crypto) over warning about it.
2. **Errors name the weakness.** Every safety diagnostic carries its CWE number,
   so findings map directly onto security standards, audits and ISM controls.
3. **The compiler is deterministic.** The same source always gives the same verdict.
   AI review is advisory, or a separately recorded and cached gate, never part of type checking.
4. **Escape hatches are explicit, rare and auditable.** `trust("why")`, and later
   `unsafe` / FFI, always need a written justification and appear in audit output.
5. **Friction only where risk is.** Mandatory tests apply to policies and other
   security-critical code, not to everything.
6. **Agility without code changes.** Security primitives are abstract (`hash`,
   `hash_password`), their outputs are self-describing, and upgrading the language
   version upgrades the algorithms.
7. **Dogfooding.** The compiler is written in Capstan and must pass `--strict`.
8. **Honest claims.** The coverage document states what is not prevented.

## 3. Architecture

```
            source (.cap)
                 │
   lexer ── parser ── checker ──────────── codegen ── C ── GCC/Clang ── native
                         │  types, taint,                    ▲
                         │  grants, policies,                │ capstan_rt.h
                         │  CWE diagnostics                  │ (checks, crypto,
                         ▼                                   │  collections)
                 diagnostics ──► CLI today ──► LSP server ──► editors / Capstan IDE
                                                   ▲
                                      Capstan Review (Claude), advisory layer
```

## 4. Roadmap

Each version must keep the self-hosting fixpoint, the full test suite and the
compiler's own `--strict` check passing.

### v0.1 — Self-hosting safe core *(done)*
Structs, optionals, lists, maps, checked integers, taint tracking, secrets,
policies and grants with object binding, mandatory denial tests, agile hashing
(SHA-256 and PBKDF2), 46 vulnerability tests (39 rejected at compile time, 7 stopped at run time), and a compiler that compiles itself.

### v0.2 — Everyday language
- `enum` with payloads and exhaustive `match` (replacing int constants for roles and states)
- `else if` chains without nesting, `i++`, ternary-free conditional expressions
- string interpolation that preserves taint: `"Hello {name}"`
- methods on structs (`p.distance()`), `List.pop/insert/remove`, `Map.remove`, sorting
- `import "module"` with one file per module, public/private visibility
- better diagnostics: column numbers, source excerpts, "did you mean" suggestions, error recovery
- `capstan fmt` (formatter)

### v0.3 — Memory and performance
- garbage collector (precise, generational), replacing never-free
- unboxed optionals, monomorphised generic containers
- bounds-check elimination when the index is provably in range
- benchmark suite in CI, with a target of within 20% of C

### v0.4 — Abstraction
- user generics with interfaces (`interface Comparable<T>`)
- closures that capture by value (no dangling references)
- error handling: `Result<T, E>` with `?` propagation (no exceptions)

### v0.5 — Safe systems access
- capability-based I/O: `main(Capabilities caps)`. Code can only touch files,
  directories, network hosts and environment variables it was handed
  (addresses CWE-22, CWE-918, and supply-chain blast radius)
- `Path` type with traversal-safe joining
- real `run()` (posix_spawn, never a shell) and SQL drivers with prepared statements
- resource limits: size-bounded input types, mandatory timeouts, linear-time regex (CWE-400)
- secure random API (`random_bytes`, `random_int`)
- authenticated encryption `seal()` / `open()` with algorithm tags; key rotation support

### v0.6 — Concurrency
- tasks and channels; data shared only by moving ownership or through typed locks
  (data races become compile errors)
- `async` I/O for servers

### v0.7 — Policies, proven
- `assert never ...` policy properties checked by an SMT solver, with counter-examples
- `sensitive struct`: every access is protected by default (closes the CWE-862 "forgot to mark it" gap)
- policy coverage report in CI
- mutation testing for policies: the compiler weakens a rule and checks that a test fails

### v0.8 — Web
- typed HTML templates (`Html` type; XSS becomes a type error)
- web framework with CSRF tokens, secure cookies, session expiry and auth flows built in
- typed decoders for JSON and forms that produce `Tainted` fields

### v0.9 — Interop and packages
- FFI to C behind `unsafe extern`, with a required review annotation and tests
- package manager: signed packages, lockfiles, capability manifests per dependency
- audit command: lists every `trust()`, `unsafe` and suppressed warning in a project

### v1.0 — Stable
- language and standard library stability guarantee
- complete specification; optional formal verification of the checker's core rules
- WebAssembly backend alongside C

## 5. Tooling and IDE

### Phase A — Language server (with v0.2)
An LSP server written in Capstan, reusing the compiler front end:
- red and yellow underlines with CWE codes, linking to the CWE description
- hover types (`Tainted`, `Grant<ReadRecord>`), go to definition, find references, rename
- quick fixes: "wrap in `escape_log()`", "unwrap with `if (let ...)`",
  "generate a denial test for this policy"
- works in VS Code, JetBrains, Neovim, Zed and others from day one

### Phase B — Capstan IDE (with v0.5)
A dedicated IDE built on the same server (for example a VS Code-based distribution):
- **security view**: every policy, which functions it protects, test status, and trust/unsafe sites
- **taint view**: where untrusted input enters and every validator it passes through
- one-click `--release` build showing exactly what blocks it
- debugger with grant and taint inspection

### Phase C — Capstan Review, powered by Claude
An advisory AI layer on top of the deterministic compiler:
- reviews changed code and underlines questionable logic the type system can't see:
  - policies that contradict documentation (the ML check against requirements)
  - business-logic flaws and suspicious `trust()` justifications
- each finding cites the code and, when relevant, the requirements passage
- **Gate mode (opt-in):** "do not build if Review reports any issue". To keep builds
  reproducible, verdicts are cached against the file contents and recorded with the
  build. The same code always gets the same answer until it changes or you re-run Review.
- Model: Claude through the Anthropic API. The Mythos tier isn't generally available;
  Claude Fable 5.2 is the publicly available model in that tier and needs evaluating for this
  use, since it has extra cybersecurity safeguards. The feature shouldn't carry Anthropic's
  model names as its brand.
- Privacy: code is sent to the API. Offer an organisation-level switch and a clear
  data notice, which matters for government and PROTECTED workloads.

## 6. Quality bar

- every safety rule has at least one rejecting test, and every runtime check a stopping test
- the compiler passes its own `--strict` check
- the bootstrap fixpoint is verified in CI
- sanitiser runs (ASan/UBSan) of the compiler and examples in CI
- fuzzing of the lexer and parser (from v0.2)

## 7. Known risks

| Risk | Mitigation |
|---|---|
| Trusted base bugs (runtime, C compiler) | keep the runtime small, fuzz it, sanitiser runs; a verified backend later |
| Heuristic checks (CWE-798 names) give false confidence | label them Partial; prefer type-based rules over name heuristics |
| Friction drives developers to `trust()` | quick fixes and good validators; audit reports make overuse visible |
| AI review non-determinism | advisory by default; cached and recorded verdicts in gate mode |
| Scope | ship each version usable on its own; never break self-hosting |
