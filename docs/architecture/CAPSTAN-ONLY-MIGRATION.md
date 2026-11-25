# Capstan-only repository migration

**Baseline branch:** `main`  
**Baseline commit:** `7bf800f72cb5daee95e7f1ca39c10698865af70b`  
**Migration branch:** `migration/capstan-only`  
**Created:** 2026-11-25  
**Status:** migration charter and source-language inventory in progress; no implementation languages have been deleted.

## 1. Objective

The repository's executable implementation, development tools, tests, benchmarks, bootstrap and build orchestration are ultimately to be implemented in Capstan. No Python, C, shell, Lean, Rust, JavaScript or other programming-language implementation is to remain in the final repository.

This is a staged migration, not a file-extension cleanup. A non-Capstan implementation may be removed only after its Capstan replacement exists, is integrated, and passes equivalent tests. Deleting a runtime, test harness, bootstrap or proof source before replacing its behaviour is a regression, not completion.

Documentation (Markdown), licensing and legal notices, declarative repository metadata, and non-executable assets are not implementation languages and may remain in their appropriate formats. YAML workflows and Makefiles are temporary build infrastructure, not exemptions from the end-state requirement: their executable logic must ultimately move into Capstan or into a narrowly specified non-programming host interface.

## 2. Pinned baseline and current architecture

The baseline is pinned to commit `7bf800f72cb5daee95e7f1ca39c10698865af70b`. The repository already contains a more detailed trusted-base report at `docs/research/BASELINE-INVENTORY-2026-11-25.md` (that report pins its own earlier source snapshot and must not be silently conflated with this one).

At this baseline:

- The production compiler front end and checker are Capstan source under `compiler/`.
- The production code generator emits C; the build then invokes GCC or Clang.
- `bootstrap/capstan0.py` is the stage-0 Python translator; stage 1 runs under Python.
- `runtime/capstan_rt.h` and `runtime/capstan_gc.h` are C runtime components.
- Test orchestration uses shell and Python, with C test/benchmark implementations.
- Formal verification sources include Lean files. These are proof programs, not disposable documentation; they require a replacement assurance strategy before removal.
- Capstan-native CCAM and native-backend work exists in the tree, but the repository's own architecture documents explicitly distinguish those prototypes from the production compiler path.

The migration must therefore close several separate gaps: a Capstan bootstrap, a production CCAM compiler pipeline, native code generation, a Capstan runtime, a Capstan-native test runner and tooling, and a replacement for the current external-language proof/build infrastructure.

## 3. Provisional language census

The GitHub code-search index at the baseline returned the following source-file matches for common implementation extensions. These are **file-discovery counts only**, not a complete tree walk and not lines of code:

| Extension | Indexed files found | Main role observed |
|---|---:|---|
| `.cap` | at least 340 across the queried compiler, library, verification, example, benchmark and test directories | Capstan implementation, tests, examples and models |
| `.py` | 37 | Bootstrap, test, fuzz, assurance and release tools |
| `.c` | 6 | C benchmarks and runtime unit-test implementation |
| `.h` | 2 | Production C runtime and garbage collector |
| `.sh` | 6 | Test, benchmark and release orchestration |
| `.lean` | 12 | Formal models and machine-checked proofs |
| `.yml` | 5 | GitHub Actions workflows |

These counts are deliberately labelled provisional: GitHub code search is not a recursive Git tree listing, its result limit can truncate large directories, and extension counts do not capture extensionless scripts or other source formats. In particular, the `.cap` count is a lower bound assembled from directory-scoped searches. No exact total source-line count is asserted here.

## 4. Required line-count inventory

A complete inventory must be generated from the exact pinned Git tree, not from search snippets or GitHub's repository-size-in-KB field. The inventory must record:

1. Commit SHA and tree SHA.
2. Every tracked file path, blob SHA, detected language and line count.
3. Code, comment and blank-line counts separately.
4. Generated/vendor/fixture classification without silently excluding tests.
5. Totals by language and by functional area.
6. A machine-readable CSV/JSON export and a human-readable Markdown summary.
7. The exact counting-tool version and invocation, so the result can be reproduced.

The counting profile must include compiler, runtime, tests, benchmarks, examples, verification and build tooling. Documentation, lockfiles, generated fixtures and binary assets should be reported separately. The report must show both a strict source-only total and a whole-repository text-file inventory.

**Open baseline task:** obtain the full recursive tree and run a pinned line counter against every tracked text blob at `7bf800f72cb5daee95e7f1ca39c10698865af70b`. Until that has been done, the exact Capstan LOC and language LOC remain unverified.

## 5. Migration sequence and gates

### M0 — Inventory and freeze the baseline
- Produce the complete commit-pinned tree/LOC inventory above.
- Map each non-Capstan file to its owner, purpose, dependencies and replacement.
- Record which files are generated, vendored, test fixtures or proof artefacts.
- Establish baseline test commands and current CI status at the exact commit.

**Exit gate:** every tracked executable/source file is classified; totals reconcile to the tree; no unclassified implementation files remain.

### M1 — Capstan-native build and bootstrap
- Replace the Python stage-0 translator with a documented Capstan seed/bootstrap.
- Define S0/S1/S2 reproducibility and provenance requirements.
- Move build orchestration into Capstan, retaining only unavoidable platform entry points.
- Make clean-checkout bootstrap independent of Python and GCC/Clang.

**Exit gate:** a clean build produces a native Capstan compiler without generated C, Python or a C compiler.

### M2 — Production compiler and native backend
- Complete the validated typed front end and canonical CCAM path.
- Complete source-to-CCAM semantic preservation and shared conformance vectors.
- Complete at least one production native backend, including calls, memory, strings, collections, traps, I/O and runtime services.
- Keep the legacy C backend only as a temporary differential oracle.

**Exit gate:** the complete supported language profile builds and runs through the native path; the legacy backend is no longer required for production.

### M3 — Capstan runtime and platform boundary
- Replace the C runtime and garbage collector with Capstan implementations.
- Specify minimal OS/ABI primitives and isolate unavoidable assembly or platform interfaces.
- Port Shroud, Anchor and other components without weakening their security/resource contracts.

**Exit gate:** no Capstan-owned C runtime or C helper is needed to build or execute supported programs.

### M4 — Tests, tools, benchmarks and assurance
- Port Python and shell test orchestration, fuzzing, mutation testing, formatters, language-server support, release verification and benchmark drivers to Capstan.
- Port C benchmarks and runtime tests to Capstan, preserving independent reference vectors where appropriate.
- Replace Lean proof-source dependencies with a Capstan-native proof/checking system or another explicitly approved, independently verifiable evidence format. Do not delete existing proof sources until their claims and reproducibility are preserved.
- Port CI/release orchestration so no non-Capstan program is required to validate or ship Capstan.

**Exit gate:** a clean checkout can build, test, fuzz, verify and package using Capstan plus documented minimal platform interfaces.

### M5 — Remove legacy languages
- Delete superseded Python, C, shell and Lean implementation sources only after their replacement gates pass.
- Remove obsolete compilers, interpreters, build dependencies, CI setup and generated artefacts.
- Scan the full Git tree and dependency manifests for residual executable source in other languages.

**Exit gate:** every tracked executable implementation and test program is Capstan; residual non-Capstan content is limited to documentation, legal/declarative metadata, binary assets and explicitly documented platform ABI boundaries.

## 6. Non-negotiable migration rules

- No mass deletion by extension.
- No generated C hidden behind a renamed file, FFI, helper binary or build script.
- No claim of C-free or Python-free status based only on the compiler's source language.
- No reduction in tests, fuzzing, sanitizers, conformance, security checks or proof scope to make the migration appear complete.
- Every port has parity tests and a rollback path.
- Every milestone is pinned to a commit and validated on its exact head.
- Open pull requests are not treated as integrated functionality; migration work must reconcile with the current mainline and active component work.

## 7. First implementation work

The first engineering slice on this branch should be a Capstan-native inventory tool once the file-system and text-reading APIs are available in the supported Capstan runtime. It should emit the pinned manifest and line totals above. In parallel, the compiler/runtime team should establish a C-free vertical slice that compiles a small, explicitly specified Capstan program to native code without Python or generated C.

This branch intentionally starts with the migration contract and does not delete or rewrite production files before the inventory and replacement interfaces are validated.
