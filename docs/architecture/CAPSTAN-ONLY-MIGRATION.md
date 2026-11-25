# Capstan-only repository migration

**Base:** `main` at branch creation  
**Branch:** `migration/capstan-only-v2`  
**Date:** 2026-11-25  
**Status:** charter and initial source inventory; no legacy files deleted.

## Objective

All executable implementation, compiler, runtime, bootstrap, build/release orchestration, tests, fuzzers, tools and benchmarks are ultimately to be written in Capstan. Python, C, shell, Lean and any other programming-language implementation must be replaced before it is removed.

This is a staged migration, not a file-extension cleanup. Markdown documentation, legal notices, declarative metadata and binary assets may remain. Any platform-specific assembly or OS interface must be minimal, documented and explicitly included in the trusted-base inventory.

## Current architecture observed

- `compiler/*.cap` implements the production front end and checker, but the production code generator emits C.
- `bootstrap/capstan0.py` translates the compiler to Python for the initial stage; stage 1 runs under Python.
- `runtime/capstan_rt.h` and `runtime/capstan_gc.h` implement the production C runtime and collector.
- `tests/run.sh` orchestrates the suite and invokes Python tooling; C test/benchmark programs also exist.
- `formal/` and `verification/lean/` contain Lean proof/model sources. These are assurance artefacts, not disposable tooling; their results and reproducibility must be preserved by an explicit replacement assurance strategy before removal.
- Capstan-native CCAM/evaluator/lowering/native-backend slices are present, but the project’s architecture documents distinguish them from the production C-backed compiler path.

## Initial language census

GitHub code search was used to discover files by extension and directory. The search API is capped and is not a complete recursive tree listing. These are discovery results, **not a complete census or line-count result**:

| Language / extension | Search results observed |
|---|---:|
| Capstan `.cap` | 100 in the broad query (result cap); many additional directory-scoped results |
| Python `.py` | 37 |
| C `.c` | 6 |
| C headers `.h` | 2 |
| Shell `.sh` | 6 |
| Lean `.lean` | 12 |
| YAML workflows `.yml` | 5 |

The Capstan total is deliberately not extrapolated: overlapping directory queries and result caps make that unsafe. No exact LOC figure is claimed yet.

## Required complete baseline report

Generate this from the exact Git tree SHA, not from GitHub repository size or search snippets:

1. Enumerate every tracked path and blob SHA recursively.
2. Fetch every text blob at the pinned commit.
3. Record detected language and total/code/comment/blank lines per file.
4. Include compiler, runtime, tests, benchmarks, examples, verification, build scripts and CI support; report generated/vendor files separately rather than silently excluding them.
5. Publish machine-readable CSV/JSON and a Markdown summary with counting-tool version and reproducible command.
6. Reconcile the sum of file records to the complete tree; if GitHub reports a truncated tree, enumerate subtrees separately.

**Current blocker:** the GitHub connector exposes code search and per-file fetch but not a recursive tree-read action. A local clone was attempted but this environment could not resolve github.com. The exact Capstan LOC and full language totals therefore remain unverified. GitHub’s repository-size-in-KB value is not a substitute.

## Migration milestones

### M0 — Inventory
Complete the commit-pinned tree, language and LOC manifest; classify every executable source file by function, dependencies and replacement owner. Capture exact-head CI and test status.

### M1 — Bootstrap and build
Replace the Python seed with a documented Capstan seed/bootstrap. Define S0/S1/S2 provenance and reproducibility. Move build orchestration into Capstan and remove Python/GCC/Clang from the required clean-build chain.

### M2 — Production compiler
Complete the typed front end, canonical CCAM validation, source-to-CCAM preservation and a production native backend. Cover calls, traps, memory, strings, collections, I/O and runtime services. Keep the C backend only as a temporary differential oracle.

### M3 — Runtime and platform
Replace the C runtime and collector with Capstan implementations. Specify minimal OS/ABI primitives. Port Shroud, Anchor and other components without weakening security or resource contracts.

### M4 — Tests, tools and assurance
Port test orchestration, fuzzing, mutation tests, formatters, LSP, release verification, benchmarks and CI. Preserve proof claims and reproducibility when replacing Lean artefacts; do not simply delete them.

### M5 — Remove legacy sources
Only after replacement gates pass, remove Python, C, shell, Lean and other superseded implementation sources, generated artefacts and dependency setup. Scan the complete tree and manifests for residual non-Capstan executable source.

## Non-negotiable rules

- No mass deletion by extension.
- No C hidden behind generated files, FFI, helper executables or build scripts.
- No claim of C-free/Python-free status based solely on the compiler being written in Capstan.
- No reduction in test, fuzz, sanitizer, conformance, security or assurance coverage to make the migration appear complete.
- Every port has parity tests, exact-head CI and a rollback path.
- Open PRs are not treated as integrated functionality.
- A milestone is complete only when its evidence is reproducible from a clean checkout.

## First implementation slice

The first code deliverable should be a Capstan-native repository inventory tool once the supported filesystem/text APIs can enumerate the tracked source tree. In parallel, complete a single small end-to-end CCAM-to-native vertical slice and then expand its feature matrix. The migration must preserve the current compiler and component behaviour throughout.
