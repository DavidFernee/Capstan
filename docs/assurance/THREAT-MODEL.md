# Capstan threat model

What Capstan defends against, what it assumes, what it trusts today, what is out of scope, and what
risk remains. It describes the integrated repository state reviewed on 2026-11-24, and is the
maintained threat model called for in [DESIGN-MAP.md](../DESIGN-MAP.md). The default execution path
is still generated C plus the C runtime; the C-free/CCAM programme is not yet the production path.
Every claim refers to a document, implementation path or test in the repository.

## 1. What is being protected

1. **Programs written in Capstan**: that the vulnerability classes Capstan claims to prevent
   ([CWE-COVERAGE.md](../CWE-COVERAGE.md)) cannot occur in them, either because the compiler refuses
   the program or because the program stops safely at run time.
2. **The toolchain**: that the compiler, runtime and release archives are what their source says,
   and that a verdict from the compiler can be relied on.
3. **Secrets handled by programs**: credentials and keys held as `Secret` values.

## 2. Adversaries

| Adversary | Capability assumed | Capstan's defence |
|---|---|---|
| **A1. Remote or local user of a Capstan program** (the main adversary) | Controls any input the program reads: standard input, files, environment variables | Input arrives as `Tainted`; it reaches queries, commands, logs, HTML, files and policies only through validators and escapers, or an audited `trust()`. Source-level checked operations reject invalid bounds and stop on specified overflow; this does not make the C runtime, compiler, libc or host platform memory-safe (section 5) |
| **A2. A well-meaning developer who makes mistakes** | Writes ordinary code under time pressure | Targeted static checks reject specified prohibited constructs with CWE-labelled diagnostics; they do not prove every application free of every weakness. `--strict` and `--release` add stricter checks, including mandatory denial tests for policies |
| **A3. A supplier of hostile source to the compiler** | Gives the compiler arbitrary bytes as source | The compiler reads source as `Tainted` and emits text into C only through `validate_ident()`, `validate_int()` and `escape_c()`; mutation fuzzing checks that corrupted programs never crash or hang it and that accepted programs give valid C ([TESTING.md](../TESTING.md), fuzz); 100,000-deep nesting gets a diagnostic, not a crash (limits) |
| **A4. Someone who tampers with a compiler binary or build** | Replaces a compiler binary, C compiler or build input with one that inserts flaws | The compiler's self-hosting fixpoint and diverse bootstrap checks provide evidence about compiler reproduction, not a proof against a malicious toolchain. The release workflow defines SHA-256 checksums, keyless Sigstore signatures, CycloneDX/SPDX SBOMs and GitHub artifact attestations; each published release still requires verification of its actual assets and attestations |

Not considered an adversary Capstan can stop: a **malicious developer** with commit access. A
deliberate backdoor written as ordinary logic (CWE-912) is indistinguishable from intended logic
([CWE-ATLAS.md](../CWE-ATLAS.md)); code review is the defence. A program also has the full authority
of the user who runs it: a hostile module, once imported and run, can read and write any file the
user can. Capability-based I/O, which limits that, is planned for v0.6.

## 3. What Capstan defends against

### 3.1 Refused at compile time

Injection (SQL, OS command, argument, code, log, CSV formula), cross-site scripting through `Html`
values, path traversal, null dereference, uninitialised variables and fields, format strings,
unsafe C functions, hard-coded credentials under credential-like names or in known credential
formats, weak cryptography and fast password hashing, secrets printed, logged, compared with `==` or
concatenated, missing authorisation for `protected` functions and `sensitive struct` data, grants
stored or returned, permissive or tainted policies, missing `match` cases, and debug switches in
`--release` builds. Evidence: 68 programs in `tests/reject/`, each with its expected CWE; the CWE
table in [README.md](../../README.md); [CWE-COVERAGE.md](../CWE-COVERAGE.md).

### 3.2 Stopped safely at run time

Invalid source-level indexed operations, checked integer overflow and underflow, division by zero,
runaway recursion, a grant replayed on a different object, and heap exhaustion are rejected or stop
the program with the specified diagnostic/exit code and named CWE. Evidence: `tests/runtime/`.
The range analysis removes a check only where it proves the check cannot fail; `--keep-checks` keeps
all of them, and differential fuzzing compares against stage 0, which has no range analysis. These
checks do not cover memory-safety defects inside the C runtime or other trusted-base components.

### 3.3 Prevented by absence

No pointers, manual memory management, null, `eval`, shell, format strings, object deserialisation
or weak random number generator. Capstan has no threads, so data races cannot be written.

The CWE atlas counts the outcome for 254 code-level weaknesses ([CWE-ATLAS.md](../CWE-ATLAS.md)):
80 rejected, 23 stopped, 16 neutralised, 73 inexpressible, 2 possible only through an audited escape
hatch, 22 logic or design decisions, 5 gaps, 33 not applicable yet. Every verdict is re-checked on
each test run.

## 4. Assumptions

Capstan's guarantees hold only if all of these are true:

1. The trusted base (section 5) behaves as specified.
2. The compiler's checker and code generator are correct. They are tested by the conformance suite,
   a second implementation, fuzzing, line coverage with enforced floors and mutation testing, but not
   proved ([TESTING.md](../TESTING.md)).
3. Every `trust("why")` is justified. Each one is reported as an `AUDIT` warning in every build;
   the audit command that lists them across a project is planned for v0.10.
4. Policies mean what the organisation intends. Capstan proves that a check happened, and flags
   suspicious policies, but not that the rule is the right one.
5. Data that should be protected is declared `sensitive`, and critical operations are declared
   `protected` (atlas gaps CWE-862 and CWE-306).
6. The program runs as an ordinary process on a supported operating system that provides a stack
   guard page and delivers `SIGSEGV`/`SIGBUS`. Runtime initialisation must successfully install
   the alternate signal stack and the required signal handlers; failure is fail-closed through
   `cap_panic` rather than continuing with an unprotected stack-overflow path
   (`runtime/capstan_gc.h`). The named stack-overflow stop still depends on the operating
   system delivering the expected signal and on the handler being able to execute on the
   alternate stack.
7. The build machine and the C compiler installed on it have not been tampered with, beyond what
   diverse double-compiling detects.

## 5. Trusted base today

These components are not written in Capstan, so Capstan's language-level guarantees do not cover
them. A bug in any of them can break a guarantee. The table describes the current integrated
execution and build path, not the intended C-free destination.

| Component | Role | Size or source | How it is checked meanwhile | Plan to reduce ([DESIGN-MAP.md](../DESIGN-MAP.md), section 6) |
|---|---|---|---|---|
| Runtime (`runtime/capstan_rt.h`, `runtime/capstan_gc.h`) | Run-time checks, strings, collections, SHA-256, HMAC, PBKDF2, file and line I/O, garbage collector, stack guard | C implementation (line count is revision-dependent) | Runtime unit tests, ASan/UBSan, collector stress and differential fuzzing; these test but do not prove runtime correctness | C-free runtime implementation is a future target; no verified replacement is integrated |
| C standard library | I/O, memory, number formatting and parsing used by the runtime | The platform's libc | Indirectly, through runtime tests and sanitiser runs | Removal requires an implemented and tested platform interface; no such C-free replacement is integrated |
| C compiler (GCC or Clang) | Compiles generated C and the runtime | The platform's compiler | Cross-compiler and optimisation-level conformance plus bootstrap checks; these do not prove compiler correctness | Removed from the execution TCB only after a C-free native backend is implemented, validated and made the default |
| Capstan compiler | Checks and translates Capstan source and emits C | `compiler/*.cap`, written in Capstan | Self-hosting, conformance, fuzzing, coverage and mutation testing; no end-to-end formal correctness proof | Selected Lean proofs cover a separate CCAM model fragment; source checking, lowering and compiler refinement remain unproved |
| Python 3 and stage 0 (`bootstrap/capstan0.py`) | Translates the compiler once to start the bootstrap | A small, unchecked Python translator, plus the Python interpreter | Bootstrap fixpoint and differential tests; Python and stage 0 remain trusted build dependencies | Retain as a diverse bootstrap route or replace only through a separately reviewed reproducible bootstrap design |
| Generated C and native toolchain | Current backend output compiled into executable code | Generated C plus GCC/Clang and platform linker | Tested through compiler/runtime suites and cross-compiler CI; no proof of C codegen correctness | C-free native backend and runtime are future work; current path remains in the TCB |
| Shell scripts (`bin/capstan`, `Makefile`, `tests/run.sh`, `scripts/release-check.sh`) | Drive the C compiler, tests and release checks | Bash and Make | Exercised by test and release workflows | Must be reviewed as part of any bootstrap/backend transition |
| Operating system and hardware | Process isolation, memory, signals, files | The platform | Not tested by Capstan | seL4 or a Capstan microkernel are long-term options (section 7, K3) |
| GitHub and its hosted runners | Host source, CI and release assembly | `.github/workflows/` | Actions are SHA-pinned; release workflow defines checksums, keyless Sigstore signatures, CycloneDX/SPDX SBOMs and GitHub artifact attestations. Workflow configuration is not proof of a successful release or an independent rebuild | Independent rebuild outside GitHub and a higher-assurance provenance process remain future work |

The detailed allocation kinds, conservative root set, reachability rules, reclamation behaviour and explicit lifetime limitations are specified in [RUNTIME-MEMORY-MODEL.md](RUNTIME-MEMORY-MODEL.md). That document is a normative v0.6 design baseline with implementation conformance explicitly qualified; it is not a proof that the current C collector satisfies every stated property.

## 5.1 Formal-verification boundary

The active C-free programme uses CCAM as the proposed canonical typed core IR and Lean 4
to check selected mathematical properties of a model. Current proofs cover a finite
single-frame machine fragment and selected signed-64/register/arithmetic invariants. They
do not establish that the Capstan parser or checker is sound, that source lowering preserves
semantics, that the CCAM validator is sound, that the complete machine makes progress or
traps correctly, that heap/GC/calls/concurrency are safe, or that native code is equivalent
to CCAM. The Lean kernel, Lean libraries and theorem axioms are part of the proof-assurance
boundary; proof results also depend on model adequacy and the correspondence between model
and implementation. No such end-to-end correspondence is currently proved. These proofs
are not evidence that the current C-backed runtime has become memory-safe.

## 6. Out of scope

- **Logic and design errors**: a wrong formula, a missing business rule, a consistent but wrong
  policy, rate limiting, workflow order, infinite loops. The atlas lists 22 such weaknesses as
  beyond any language.
- **Deployment and configuration**: storage permissions, TLS settings, the environment a program
  runs in.
- **Hardware and processor side channels.** `secret_eq()` avoids content-dependent early exit only
  for equal-length operands; it does not hide operand lengths. Lengths must be public, and the API
  must not be used where a secret's length is confidential. A length-hiding comparison is not
  currently provided. Other timing and speculation attacks are not addressed.
- **Concurrency.** There are no threads yet, so concurrency weaknesses are neither possible nor
  addressed (v0.7).
- **Networking.** There is no network access yet; SSRF and network parsing are future work (v0.6).
- **Real databases and processes.** `sql_query()` and `run()` are demonstration sinks that print
  rather than execute ([README.md](../../README.md), Status). The type rules on them are enforced and
  tested; there is no driver to attack.
- **Availability beyond memory.** The heap limit stops runaway allocation safely; CPU time and loop
  bounds are not limited (CWE-400, Partial). A safe stop is still a stop: an attacker who can trigger
  one can end the program (denial of service), but not corrupt it.
- **Capstan Review (AI).** Planned, advisory and optional; not part of the compiler's verdict and not
  present today.

## 7. Residual risks

1. **Atlas gaps that can still be written** ([CWE-ATLAS.md](../CWE-ATLAS.md)): HTML-escaped text
   written into a CSV file (CWE-116); a password-like literal under an innocuous name (CWE-798); a
   password hashed with `hash()` when held in an innocuously named variable (CWE-916); data whose type
   was not declared `sensitive` (CWE-862); a critical operation not declared `protected` (CWE-306);
   escaped text placed into HTML that was assembled in separate statements, whose context the
   compiler does not follow (CWE-79).
2. **Laundering through control flow.** Rebuilding untrusted text by branching on each byte is how a
   validator is written, so the compiler cannot reject it (atlas, CWE-20). Laundering through helper
   functions, lists, struct fields, and lookups of trusted text by untrusted bytes (list indexes,
   slices, map keys) is rejected (`tests/reject/launder_*.cap`).
3. **Name-based heuristics.** Credential and password detection partly relies on names and known
   formats; a heuristic can miss cases and give false confidence ([DESIGN-MAP.md](../DESIGN-MAP.md),
   section 11). These rules are labelled Partial.
4. **Bugs in the trusted base** (section 5). Testing, sanitisers and diverse double-compiling make
   them less likely; they cannot show their absence.
5. **Range analysis soundness.** A flaw in the analysis could remove a needed check. Mitigations: facts
   only for variables that cannot change, property tests of its interval arithmetic, runtime tests
   that must still stop, differential fuzzing against stage 0, and `--keep-checks`.
6. **Conservative garbage collection.** A value that looks like a pointer keeps memory alive. This can
   retain memory, so it is an availability risk, not a memory-safety one.
7. **Missing exploit mitigations in generated binaries.** `bin/capstan` compiles generated C with
   `-O2 -std=gnu11 -w` and does not explicitly enable stack protectors, control-flow integrity,
   position-independent executables or `_FORTIFY_SOURCE`; only the platform compiler's defaults apply.
   These would limit the impact of a trusted-base bug (DESIGN-MAP section 6, "Defence in depth").
8. **Release integrity.** Releases are signed (keyless Sigstore), carry SBOMs and GitHub artifact
   attestations, and the workflows pin actions by commit. They are still built only on GitHub's
   runners: there is no independent rebuild elsewhere, and the build is not SLSA Build Level 3
   ([DESIGN-MAP.md](../DESIGN-MAP.md), section 8).
9. **No independent review yet.** An external security audit is planned before v1.0
   ([DESIGN-MAP.md](../DESIGN-MAP.md), section 8).
10. **Peer review is not enforced.** Changes arrive through pull requests, but nothing in the
    repository (for example a `CODEOWNERS` file) shows that review by a second person is required.

## 8. Reporting

A program Capstan accepts that contains a weakness it claims to prevent, or any way around its
checks, is a vulnerability: see [SECURITY.md](../../SECURITY.md).
