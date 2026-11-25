# Capstan guarantee and trusted-base baseline

**Snapshot:** main at 8d0a5583d1f586544a61ca0ae5405c64ebc576c1  
**Reviewed:** 2026-11-25  
**Purpose:** factual baseline for research issue [#225](https://github.com/DavidFernee/Capstan/issues/225)  
**Status:** repository-document review; not an independent security audit and not a claim that tests were executed during this review.

This report records what the default-branch documents and source establish at the snapshot above. A design contract, test fixture, workflow definition, open PR, or model theorem is not interchangeable with an integrated implementation result. Where repository documents disagree, the discrepancy is recorded rather than resolved by choosing the more optimistic statement.

## 1. Executive assessment

Capstan has a substantial self-hosted, C-backed language/compiler/runtime with targeted static checks, dynamic guards, a conservative garbage-collected runtime, grant/policy enforcement, a broad regression suite and a separate C-free/CCAM research programme.

The current production compiler path remains:

    Capstan source → Capstan checker/compiler → generated C → GCC/Clang → executable

The self-hosted compiler reproduces its generated C through a bootstrap fixpoint, but stage 0 is Python and the native executable is linked to the Capstan C runtime. This is self-hosting, not C-free self-hosting.

CCAM is the normative semantic target for a future C-free execution path. Mainline contains Capstan-native executable slices for single-frame execution, an in-memory validator, multi-function calls, checked scalar source lowering, and a freestanding Linux x86-64 emitter. The CCAM specification explicitly says the implementation is **not yet a conforming CCAM v0.1 machine**, is not connected to the Lean model by an implementation-refinement theorem, and is not the complete Capstan semantics. The production compiler CLI still does not use this path.

The formal work contains meaningful machine-checked results, but at least two distinct proof programmes exist: the CCAM/single-frame model under verification/lean/, and the collector abstract model under formal/. Results from either model must not be promoted to implementation guarantees without the corresponding refinement argument.

### Three highest-leverage gaps

1. **One specification-aligned, end-to-end CCAM vertical slice.** Close the exact decoder/validator/evaluator/model mismatches for a small declared profile, with shared vectors and a concrete implementation-to-model theorem. This is the prerequisite for trustworthy native refinement and evidence-carrying execution.
2. **A unified, compositional resource and authority contract.** Today, heap, stack, instruction fuel, call depth, backend expansion ceilings and Shroud frame budgets are separate local controls. Grant/policy enforcement is not yet a general capability/effect system or sandbox for host I/O. Define units, accounting, composition and host assumptions before claiming whole-program boundedness or least authority.
3. **An evidence system tied to exact revisions and actual execution.** The claim manifest is stale and materially incomplete; some architecture/status documents contradict one another. Refresh the machine-readable claim/evidence register and make CI, tests, proofs, source revision and refinement status one auditable chain.

## 2. Snapshot and source inventory

The following files were fetched from main at the snapshot commit above.

| Area | Primary sources | Snapshot finding |
|---|---|---|
| Language/compiler | compiler/lexer.cap, parser.cap, ast.cap, checker.cap, ranges.cap, codegen.cap, main.cap; docs/SPEC.md; docs/architecture/LANGUAGE-CORE.md | Production front end and checker are Capstan; code generation emits C. Core v0.1 is a normative proposal for the scalar/control-flow/direct-call subset, not the full language semantics. |
| Production runtime | runtime/capstan_rt.h, runtime/capstan_gc.h; docs/assurance/RUNTIME-MEMORY-MODEL.md | C runtime; non-moving conservative mark-and-sweep collector. Heap accounting is collector-managed heap, not process RSS. Conservative retention means unreachable objects may remain retained. |
| CCAM | docs/architecture/CCAM.md, docs/architecture/CCAM-IO.md, docs/architecture/ccam-v0.1.schema.json, verification/ccam_core.cap, verification/ccam_calls.cap | Normative typed register machine; integrated executable slices remain narrower than the full JSON/program contract. |
| Source lowering | verification/ccam_lowering.cap; docs/architecture/COMPILER-CCAM-LOWERING.md | Deterministic lowering for a checked scalar subset; fail-closed for unsupported constructs; no source-to-CCAM simulation theorem and not wired into the production CLI. |
| Native backend | verification/ccam_native_x64.cap; docs/architecture/CCAM-NATIVE-BACKEND.md | Linux x86-64 freestanding scalar backend prototype. It is not a production compiler backend and lacks a full runtime, output, aggregate values, other target ABIs and evaluator differential conformance. |
| Formal CCAM model | verification/lean/CapstanVerification/{Core,Machine,Validator,ProgramValidator,Progress,RuntimeBridge,NativeRegisterBridge}.lean; docs/assurance/FORMAL-VERIFICATION-MATRIX.md | Single-frame finite model and restricted theorems. PR #205 adds concrete native register type-tag/field read-write correspondence lemmas; the progress theorem still explicitly excludes calls and whole-program progress. Whole-evaluator implementation correspondence remains incomplete. |
| Formal collector model | formal/CapstanFormal.lean, formal/PROOF-RUNS.md, formal/OBLIGATIONS.md | Separate abstract model of selected collector transitions. The proof-run ledger calls the result model-only and identifies implementation-refinement blockers. |
| Security/grants | docs/assurance/THREAT-MODEL.md, docs/assurance/GRANT-SECURITY.md, compiler/checker.cap, runtime/capstan_rt.h, tests/reject/, tests/runtime/ | Targeted static checks, taint/secret handling and object-bound grant/policy revalidation exist on the C-backed path. They do not establish a general capability sandbox or eliminate arbitrary application vulnerabilities. |
| Test/evaluation | tests/run.sh, tests/spec_coverage.py, tests/fuzz/, tests/mutate_compiler.py, bench/ | Broad suite covering reject/runtime cases, fuzzing, mutation, sanitizers, bootstrap, formatter, LSP, supply chain and benchmarks. Presence of a fixture or workflow is not a passing run at this snapshot. |
| Release/evidence | docs/assurance/claims.json, docs/assurance/V1-RELEASE-SCORECARD.md, docs/CWE-COVERAGE.md, docs/assurance/THREAT-MODEL.md | Release scorecard correctly defaults missing evidence to UNKNOWN. Current JSON claim manifest is stale and only contains one old, unqualified claim. |

## 3. Claim/evidence register

“Integrated” means present on the inspected default branch, not necessarily fully conforming, independently validated or formally proved.

| ID | Property / boundary | Specification or contract | Integrated implementation | Tests / formal evidence | Status and residual gap |
|---|---|---|---|---|---|
| LANG-01 | Production source language, parser and type checker | docs/SPEC.md; docs/architecture/LANGUAGE-CORE.md | compiler/lexer.cap, parser.cap, ast.cap, checker.cap | Main suite includes spec coverage, accept/reject, diagnostics and recovery | **Integrated C-backed path.** Core v0.1 is narrower than the complete language; generated-C correctness and C toolchain remain trusted. |
| LANG-02 | Checked arithmetic, indexing, initialisation and targeted prohibited constructs | docs/SPEC.md; docs/architecture/LANGUAGE-SAFETY.md; docs/CWE-COVERAGE.md | Checker, generated checks and C runtime guards | tests/reject/, tests/runtime/, tests/run.sh | **Implemented on supported production paths with residual scope.** No blanket claim that every instance of every CWE is prevented; exact per-attempt evidence and exact-head test results are required. |
| SEC-01 | Taint-aware sinks and secret handling | Threat model; CWE coverage; security-specific design docs | Checker and runtime support for taint/secret operations | Reject/runtime/crypto tests and fuzz/sanitizer suite | **Integrated, bounded claims.** Copies can escape labels; OS, compiler, C runtime and foreign boundaries remain trusted. Deterministic erasure of all secret copies is not guaranteed. |
| AUTH-01 | Protected calls and grants bound to authorised objects | docs/assurance/GRANT-SECURITY.md | Checker/runtime grant and policy paths | Grant-specific positive/negative tests in suite | **Implemented for documented grant model.** Not a general capability/effect type system; policy correctness remains application-specific; host I/O is not comprehensively confined. |
| MEM-01 | Managed allocation and collection | docs/assurance/RUNTIME-MEMORY-MODEL.md | runtime/capstan_gc.h, runtime/capstan_rt.h | GC stress, churn, failure and sanitizer tests | **Integrated C runtime with explicit qualifications.** Conservative false retention; GC is not deterministic destruction; heap counter is not process RSS; root/ABI assumptions and implementation proof remain. |
| COMP-01 | Self-hosting compiler fixpoint | README.md and Makefile | Python stage 0 → Capstan compiler stages → generated C equality | Bootstrap section of tests/run.sh; Makefile bootstrap | **Integrated self-hosting, not C-free.** Python seed, C output, GCC/Clang and C runtime remain in the build/execution chain. |
| CCAM-01 | Single-frame CCAM evaluator | docs/architecture/CCAM.md | verification/ccam_core.cap | CCAM test section in tests/run.sh; separate Lean single-frame model | **Integrated restricted executable slice.** Consumes already validated in-memory instruction data; does not decode JSON or implement full program schema. |
| CCAM-02 | Typed in-memory single-frame validator | CCAM spec and schema | Validator functions in verification/ccam_core.cap | CCAM validator tests; separate Lean raw/single-frame validation model | **Integrated restricted validator.** Not a bounded raw JSON decoder; no duplicate-key rejection or complete normative whole-program validation. No implementation soundness/refinement theorem. |
| CCAM-03 | Multi-function calls/frames | CCAM v0.1 normative named-call contract | verification/ccam_calls.cap | Multi-function test section in tests/run.sh | **Integrated transitional evaluator.** Calls use side tables and function indices, not the normative named-call JSON representation; not connected to Lean or a native backend. Multi-function whole-program validation remains open. |
| CCAM-04 | Checked scalar source lowering | docs/architecture/COMPILER-CCAM-LOWERING.md | verification/ccam_lowering.cap | Source-lowering tests in verification suite | **Integrated restricted lowering.** Unsupported constructs fail closed; no source semantic-preservation theorem; not wired into production compiler CLI. |
| CCAM-05 | Freestanding Linux x86-64 native emission | docs/architecture/CCAM-NATIVE-BACKEND.md | verification/ccam_native_x64.cap | Assembly/ELF execution tests described by backend document | **Prototype implementation in mainline source; not production-integrated.** Scalar subset only; no complete runtime/output, no all-instruction differential suite, no machine-code refinement theorem, no macOS/Windows/AArch64 backend. |
| CCAM-06 | Byte-oriented output extension | docs/architecture/CCAM-IO.md (CCAM v0.2 proposal; PR #230) | No corresponding integrated evaluator/native output implementation identified in this baseline | Contract and required tests/proofs are specified in the document | **Specified proposal only.** Does not amend normative CCAM v0.1; no output runtime or end-to-end byte-output conformance is claimed. |
| FORM-01 | CCAM model progress/determinism/preservation | CCAM semantics; docs/assurance/FORMAL-VERIFICATION-MATRIX.md | Lean definitions in verification/lean/ | Named theorem machineStep_progress_or_explicit_outcome and machineStep_deterministic; other matrix entries | **Proved only for a restricted single-frame model.** PR #205 adds concrete native register tag/field correspondence lemmas, and the abstract RuntimeBridge contains list-model relations; Progress explicitly excludes calls and whole-machine execution. No theorem establishes that the complete Capstan evaluator transition refines the Lean machine. |
| FORM-02 | Collector arithmetic/page-release properties | formal/SPECIFICATION.md, formal/OBLIGATIONS.md | Lean model formal/CapstanFormal.lean | formal/PROOF-RUNS.md records pinned model-only proof run | **Model-only proof.** No C implementation refinement or whole-collector correctness theorem; the ledger names an implementation blocker. |
| RES-01 | Resource controls | CCAM step/depth contract; runtime memory model; Shroud-specific budgets | CCAM step/depth counters, C runtime heap cap, backend-specific stack/expansion caps, Shroud per-frame budgets | Corresponding CCAM, GC, Shroud and pathological-input tests | **Fragmented controls.** No single compositional whole-program resource contract spanning CPU, stack, heap/RSS, output, handles, tasks, I/O and host services. |
| CONC-01 | Data-race-free structured concurrency | Proposed v0.7/research issues | No integrated general task/channel concurrency semantics in CCAM or production language | Research designs/prototypes and isolated existing runtime assumptions | **Not an integrated language guarantee.** GC root scan describes current thread; no general multi-threaded collector/concurrency model is established. |
| FFI-01 | Foreign code / ABI / package isolation | Long-term design docs and release scorecard | Production runtime depends on C ABI/runtime; no general safe, capability-isolated FFI/package boundary established | No complete evidence chain identified in this baseline | **Not established.** Foreign and OS interfaces remain part of the trusted boundary; package manager/isolated FFI are future work. |

## 4. Resource and authority accounting

### 4.1 Resource controls currently present

- **CCAM execution:** deterministic instruction-step and call-depth limits in the restricted evaluator; the multi-function evaluator has bounded function/register/argument/name structures.
- **Native backend prototype:** separate maximum instruction/register expansion and dedicated stack ceilings; these are backend implementation limits, not a general resource contract.
- **Production C runtime:** CAPSTAN_MAX_HEAP and hard allocation ceilings bound collector-accounted managed heap. The memory model explicitly says this is not process-wide RSS and does not account for every process allocation.
- **Shroud:** aggregate per-frame text/metadata and PNG export amplification controls exist in their respective subsystem work; these are local workload budgets, not a universal application budget.
- **Compiler and parsers:** nesting/input/metadata limits and bounded test fixtures address selected denial-of-service paths.

### 4.2 Missing compositional contract

The repository does not yet define one common accounting semantics for fuel, stack, heap/live bytes, total allocation, output, file descriptors/handles, tasks, channel slots/buffered bytes, I/O, timers or host work. The first research model should choose a small set of measurable resources, define whether each is cumulative or peak/live, state who charges and releases it, define failure atomicity, and specify how call/module composition handles unknown or recursive callees.

### 4.3 Authority boundary

The existing grant model provides policy-specific authorisation and object binding. The threat model states that a program otherwise has the authority of the user who runs it; a hostile imported module can access files available to that user. Capability-based I/O is planned, not an integrated universal sandbox. Distinguish:
- application-level authorisation (who may access which protected object);
- language effects (which operation a function may perform);
- unforgeable capabilities (which authority is possessed and may be attenuated);
- OS/process isolation (what the host actually permits).

They are related but not interchangeable.

## 5. Formal assurance map

Two proof projects must be tracked independently.

### 5.1 CCAM formalisation: verification/lean/

The formal modules model a finite, typed, single-frame machine. PR #205 adds concrete native register type-tag and field read/write correspondence lemmas in NativeRegisterBridge.lean; RuntimeBridge.lean also proves relations over an abstract record/list model. The Progress.lean module explicitly excludes call constructors and validated multi-function programs. It proves a classification of the functional one-step result and determinism for that model. ProgramValidator.lean defines a formal raw-instruction/single-frame validator model, but a formal validator model is not proof that the Capstan implementation accepts exactly those programs or that the complete evaluator refines the model.

The obligation matrix correctly marks calls/arguments, integrated return semantics, whole-machine progress and validator/evaluator correspondence as open or partial. The PR #205 register bridge narrows one representation gap but does not establish whole-state evaluator simulation. The next high-value proof is not another isolated lemma: it is a specification-aligned, shared-vector correspondence between the concrete Capstan single-frame evaluator and the Lean profile, with a deliberately bounded scope.

### 5.2 Collector formalisation: formal/

The separate collector model covers selected checked arithmetic, page-release and related abstract transitions. formal/PROOF-RUNS.md records a successful model-only run at commit 0e57f9a68082d7be4e88aad9f6c403498c79763a, with pinned Lean/checker inputs and an independent Nanoda replay. The ledger explicitly states that this does not establish the C implementation and records a blocker involving the C page-release path. The exact theorem scope, assumptions and implementation bridge must accompany every reuse of this result.

### 5.3 Evidence rule

For each property, report separately:
1. normative specification;
2. integrated implementation path and exact revision;
3. positive, negative, adversarial and differential tests actually run;
4. model theorem and its assumptions/axioms;
5. implementation correspondence/refinement;
6. residual trusted components and platform assumptions.

A green model build is not an implementation theorem. A test fixture is not a test result. A bootstrap fixpoint is not proof of compiler correctness.

## 6. Repository consistency findings

These are actionable evidence defects, not accusations that the underlying code is wrong.

1. **The assurance README is stale against CCAM mainline.** It says multi-function evaluator, source lowering and native backend remain unmerged, while the current CCAM.md records multi-function execution (PR #207) and scalar lowering (PR #210) as integrated and a native emitter in the current source tree. The assurance README's snapshot is older. Reconcile it against the exact mainline commit.
2. **The claim manifest is stale and incomplete.** docs/assurance/claims.json records snapshot commit 48d59e406c204a582a01e77824def845dab8b32f, contains only one claim, and marks it proposed with evidence from an older revision. It cannot currently serve as a complete machine-readable assurance ledger.
3. **The bootstrap contract's status section is stale.** docs/C-FREE-BOOTSTRAP.md still describes early PR numbers and unmerged prototypes that predate the current CCAM implementation slices. Its normative target contract is useful, but its current-status paragraph must be refreshed against mainline.
4. **The research register has stale CCAM maturity entries.** R1 still describes the multi-function evaluator and source-lowering as unmerged/closed work, while the current CCAM specification records their integration. The research register is authoritative for paper maturity and should be updated with exact current evidence, not bypassed.
5. **The native backend's test description is not equivalent to full conformance.** It lists a meaningful set of Linux x86-64 ELF execution vectors, but its own gap section says there is no every-instruction differential suite or Lean machine-code simulation theorem. Keep “prototype tested on listed cases” distinct from “backend conformant”.
6. **The repository contains two Lean projects/toolchains.** CCAM formalisation lives under verification/lean/; the collector model is under formal/. Their toolchains, theorem sets and proof-run ledgers are separate. A unified assurance dashboard must not conflate them.

## 7. Dependency graph for the first integrated guarantee experiment

    Pinned source/claim baseline
              |
              v
    CCAM single-frame proof profile
              |
              v
    Shared positive/negative conformance vectors
              |
              +------> Concrete Capstan evaluator
              |
              +------> Lean single-frame machine
              |                 |
              +-----------------+
                        |
                        v
           Evaluator/profile correspondence theorem
                        |
                        v
       Small independently checkable evidence object
                        |
                        v
       One native refinement slice (later, separate gate)

Parallel inputs:
- resource-contract survey -> choose fuel/stack semantics and aggregate limits
- capability/effect survey -> choose one narrow authority policy
- security CVE cases -> test claim taxonomy against realistic failures

For the first experiment, exclude JSON decoding, multi-function calls, source lowering, native code, heap objects, I/O, grants and concurrency. These exclusions keep the first proof claim falsifiable and make the boundary clear. They are not claims that excluded layers are safe.

## 8. Reproduction and review commands

The repository documents the following clean-checkout entry points:

| Purpose | Command | What it establishes |
|---|---|---|
| Production build/bootstrap | make bootstrap | Builds the C-backed self-hosted compiler and checks the generated-C fixpoint; does not establish C-free compilation or compiler correctness. |
| Standard regression suite | tests/run.sh | Runs the documented production compiler/runtime suite, including CCAM verification tests; requires the documented host toolchain. |
| Extended suite | tests/run.sh --full | Adds long fuzzing, coverage, mutation and benchmark gates. |
| CCAM Capstan tests | bin/capstan test verification/ccam_core.cap and bin/capstan test verification/ccam_calls.cap | Exercises the in-repo evaluator/validator slices when invoked against a built compiler. |
| CCAM Lean project | From verification/lean/: lake build CapstanVerification --wfail | Builds the restricted CCAM formalisation. Exact pinned Lean toolchain is in verification/lean/lean-toolchain. |
| Collector Lean project | From formal/: follow formal/README.md and formal/PROOF-RUNS.md | Replays the separate collector model; historical run is pinned to its recorded commit/toolchain, not automatically to this snapshot. |

**Execution note:** these commands were inspected in the repository but were not run as part of this GitHub-document review. The GitHub workflow-run query for snapshot commit 8d0a5583d1f586544a61ca0ae5405c64ebc576c1 returned no associated PR-triggered runs, and the combined status endpoint returned no statuses. This is not evidence of failure; it means no exact-head CI result is asserted here.

## 9. Recommended next increments

1. **CCAM-SF-P correspondence (#243):** finish a restricted profile, independently authored vectors, concrete Capstan evaluator harness and Lean per-instruction/budget simulation. Do not include calls or JSON in the first proof.
2. **Evidence reconciliation (#219):** crosswalk every evidence-carrying execution obligation to the exact contracts, implementation, tests and proofs; distinguish producer obligations from independent checker obligations.
3. **Guarantee calculus (#227):** wait for the resource/capability surveys (#221/#222) and this baseline; propose a small conservative composition judgment with explicit unknowns.
4. **Security evidence (#236/#237):** stable per-attempt CWE records and a small CVE benchmark with at least one honest negative/out-of-scope result.
5. **Status reconciliation:** refresh the stale assurance README, C-free bootstrap status paragraph, research-register R1 and machine-readable claims manifest in separate focused documentation PRs.
6. **Concurrency (#229/#249):** retain the deterministic bounded reference machine as a separate model lane; do not present it as production concurrency until type safety, ownership/lifetime invariants and implementation refinement are established.

## 10. Review limitations

- This is a repository-document and source-path inventory, not an independent audit, penetration test, code review of every checker/runtime path or full literature review.
- No local build, test suite, fuzz campaign, sanitizer, Lean build or proof replay was executed for this report.
- Some source claims are based on subsystem specifications and test-runner declarations; exact behaviour must be confirmed by executing the named tests at a pinned commit.
- No claim of “all vulnerabilities eliminated”, complete memory safety, general deadlock freedom, end-to-end formal verification, production C-free compilation or universal platform support is made.
