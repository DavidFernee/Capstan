# Native compiler bootstrap plan

**Status:** B0 architecture baseline; implementation feasibility is not yet established.
**Baseline:** `main` at `189f19dd2a39c169e033691856d675b070fb2864` (2026-11-26 audit).
**Work branch:** `research/native-compiler-bootstrap`.
**Target prototype:** Linux x86-64, System V AMD64 ABI, freestanding ELF.
**Coordination:** issue [#370](https://github.com/DavidFernee/Capstan/issues/370).

This document specifies the route to a compiler and execution path that do not depend on generated C, a C compiler/linker, Capstan's C runtime/collector, or Python at production time. It is a plan and an audit of the integrated baseline, not a claim that the bootstrap or its correctness proof already exists.

## 1. Normative terminology and end-state

- **C-free compiler build:** building the production compiler does not invoke a C compiler, compile generated C, link a Capstan C runtime, or execute a Python compiler stage.
- **C-free program build:** compiling a Capstan program does not emit C or invoke a C compiler/C linker. The selected native toolchain may use a documented assembler and linker.
- **C-free execution:** the resulting program does not load or call the Capstan C runtime, its conservative collector, libc, or a generated-C shim. OS syscalls and documented platform interfaces remain explicit boundaries.
- **Native output:** an object/executable for a specified target ABI and object format. It does not mean the compiler itself is self-hosted or verified.
- **Bootstrap seed:** a separately built initial compiler implementation used to create the first compiler stage. A seed is bootstrap-only and cannot be invoked by the production compiler or ordinary production builds.
- **Semantic agreement:** agreement on specified observable outcomes for a declared corpus/profile. It is evidence, not a proof unless connected to a formal semantics by a theorem.
- **Reproducible output:** byte-identical output under a fully specified source, toolchain, configuration and environment identity. Reproducibility is not correctness.

Production target architecture:

```
Capstan source
  -> bounded lexer/parser
  -> name/type/safety checking
  -> typed core / canonical CCAM lowering
  -> closed decoder + whole-program validation
  -> native backend
  -> explicit assembler + linker
  -> target executable
  -> Capstan-native runtime services + narrow OS boundary
```

The canonical CCAM semantics in `docs/architecture/CCAM.md` is the semantic contract for the initial scalar execution profile. The checked source frontend remains the source-language authority; CCAM is not a substitute for the full Capstan language semantics.

## 2. Staged bootstrap contract

### S0 — Independent seed

**Purpose:** establish a first executable implementation of the compiler contract without trusting the existing generated-C compiler path as the only route.

**Implementation and trust boundary:** S0 is a small, separately maintained seed in a language/toolchain independent of Capstan's existing compiler implementation. The initial candidate is a minimal Rust implementation compiled by a pinned Rust toolchain, with no C FFI, no C runtime dependency deliberately introduced by the seed, no Python, and no code execution from source input. This is a proposal, not an assertion that a suitable seed currently exists. Its own compiler, linker, standard library and host OS remain in the S0 trusted base and must be inventoried. An alternative seed may be chosen only with a written trust and portability rationale.

**Supported source subset:** a versioned, explicitly enumerated Capstan core subset sufficient to compile the S1 compiler source. Initially: modules/imports needed by the compiler, declarations, scalar `int`/`bool`/void functions, local bindings and assignments, checked arithmetic, comparisons, conditionals, loops, direct calls, recursion under explicit bounds, and the subset of records/lists/strings that S1 demonstrably requires. Unsupported syntax, type features, dynamic behavior and annotations are rejected; no silent source erasure or fallback is permitted. The initial CCAM execution subset is narrower: signed-64 integers, booleans, typed local registers, checked arithmetic, branches, direct calls/returns, explicit traps and resource limits.

**Input format:** UTF-8 Capstan source files plus a versioned manifest containing ordered source paths, import roots, target triple, language/profile version, compiler options and declared resource ceilings. File names, lengths, import depth, token count, nesting, diagnostics and total work are bounded. No implicit environment-based include search.

**Output format:** deterministic, versioned CCAM program data for the supported profile and/or a documented native object format once the seed's backend is available. CCAM interchange is canonical UTF-8 JSON only if the complete strict decoder contract is implemented: duplicate keys rejected, exact integer parsing, closed field sets, deterministic validation and bounded decoding. The current in-memory call-site side table is not this external format.

**Independent build and audit:** pin seed source revision, compiler/toolchain versions, dependencies, build flags, host image, artifact digests and provenance. Build from a clean environment; review the seed source and dependency closure; scan for undeclared FFI, C shims and dynamic loading; run positive, negative, mutation and adversarial vectors. Have a second independently operated build reproduce the artifact. Record the seed compiler's trust base rather than treating its language label as assurance.

**Non-permanence rule:** S0 may run only in the bootstrap/audit lane. S1/S2/S3 release manifests must not list it as a runtime or production compiler dependency. CI must demonstrate a production build with S0 unavailable after the compiler has been bootstrapped. Retain S0 source and signed hashes as an audit comparator; do not invoke it during ordinary compilation, execution or release. A periodic diverse-seed comparison is an assurance exercise, not a production dependency.

**Consumes:** seed source, pinned seed toolchain, S1 compiler source, source manifest, CCAM specification/profile.
**Produces:** first native S1 compiler artifact (or a canonical CCAM artifact for a separately validated native runner), build provenance, diagnostics and a complete dependency manifest.

### S1 — First native Capstan compiler

S1 is compiled by S0 and thereafter runs as a native executable. It is written in the explicitly supported Capstan subset and compiles Capstan source without emitting C. It uses canonical CCAM semantics for the scalar profile and rejects unsupported source constructs.

**Consumes:** Capstan source and manifest; the pinned CCAM/profile specification; bounded compiler configuration.
**Produces:** target-specific native object/executable, deterministic diagnostics, source maps/debug metadata, and a machine-readable build record.

**Required contracts:**
- Linux x86-64 prototype target: ELF64, little-endian, System V AMD64 calling convention, explicit entry point and syscall ABI. Other OS/architectures are separate targets.
- Integer semantics: exact signed 64-bit two's-complement values; checked add/sub/mul/div; division by zero and MIN/-1 behavior exactly as CCAM specifies. No reliance on undefined/unspecified host arithmetic.
- ABI: explicit register/stack argument placement, stack alignment, callee-saved registers, return convention, symbol naming, relocation model, entry/exit convention and unwind policy. Unsupported signatures are rejected.
- Resources: bounded source bytes, tokens, AST nodes, recursion, compiler work, IR instructions, functions, registers, arguments, code size, stack per frame, total stack and runtime steps. Arithmetic used to compute any size/offset/budget is checked before allocation or emission.
- Ownership: each buffer/vector has one documented owner; references cannot outlive backing storage; mutation/aliasing rules are specified. No heap/GC semantics are assumed from the scalar evaluator.
- Failures: invalid source, malformed CCAM, unsupported features, resource exhaustion, arithmetic trap and platform failure have deterministic, non-fallback outcomes.
- Safe interfaces carry no ambient filesystem, process, network or environment authority. File access, if later required, is capability-scoped and explicit.

**S1 exit gate:** compile and run the scalar conformance corpus through the actual native executable; compare complete outcomes, traps and step accounting with canonical CCAM vectors; demonstrate binary properties and bounded failures; bind results to exact source/toolchain identities. This is a first native compiler slice, not yet the full Capstan compiler.

### S2 — Self-hosted compiler

S2 is the compiler rebuilt by S1 from the same pinned Capstan compiler source and manifest.

**Consumes:** S1 executable, exact S1 source tree and compiler configuration.
**Produces:** S2 executable, complete compiler/source/toolchain identities and a semantic comparison report.

**Exit evidence:** S1 and S2 compile the same conformance and adversarial corpus; compare diagnostics, output behavior, traps, resource accounting and emitted artifacts under a defined normalization policy. Compare S1/S2 output hashes and explain all permitted nondeterminism. Exercise compiler-on-compiler cases, malformed input and resource exhaustion. The compiler source revision, transitive imports and all build inputs are content-addressed.

Self-hosting alone does not show that S1 or S2 implements the language specification. A malicious or defective seed can reproduce itself. Semantic agreement must be checked against an independently specified semantics and independent test vectors; formal correctness requires a separate source-to-CCAM and CCAM-to-target argument.

### S3 — Reproducible production compiler

S3 is the release compiler produced by the approved bootstrap policy, with no S0, Python, generated C, C compiler, C linker or Capstan C runtime in the production dependency closure.

**Consumes:** reviewed compiler source; S2 and at least one diverse independent bootstrap result; pinned target backend/toolchain; canonical language/CCAM specifications; hermetic build manifest.
**Produces:** signed production compiler, native runtime/stdlib artifacts, SBOM, provenance, reproducibility attestations, conformance/assurance evidence and explicit platform-boundary manifest.

**Exit evidence:**
1. Two or more independent clean builds reproduce the same artifact under the same declared inputs; record builder identity, environment, tools, flags and all digests.
2. Diverse seeds compile the same source and are compared against an independent semantic oracle/corpus. Disagreement blocks release and triggers investigation; agreement is not treated as a proof against trusting-trust.
3. The production build is repeated with the S0 seed and legacy C toolchain unavailable.
4. A dependency-closure audit confirms no Python compiler, generated C, C compiler/linker, Capstan C runtime, conservative collector or undeclared dynamic dependency.
5. Formal theorems, tests, fuzzing, static analysis, independent review and reproducibility are reported as distinct evidence classes.
6. A reviewed compiler-correctness argument connects source semantics to CCAM and the native target, or the remaining unproved backend is explicitly part of the trusted base.

**Retirement:** legacy C compiler/runtime paths may be deprecated only after all supported production build, test, package, release and user workflows have a supported replacement and their gates pass. Removing a fallback before this is demonstrated is prohibited.

## 3. Integrated native foundation audit (baseline main)

### 3.1 What is present

The following files are integrated at the baseline commit:

- `verification/ccam_core.cap`: Capstan-native single-frame typed evaluator and in-memory validator. It handles int/bool constants and moves, checked arithmetic, integer equality/less-than, boolean negation, jumps, conditional branches, typed returns, void returns, explicit traps and instruction-step accounting. It snapshots the instruction sequence supplied to it. Its input is already-constructed in-memory instructions.
- `verification/ccam_calls.cap`: bounded multi-function execution over a function table and call-site side tables; typed argument/parameter transfer; direct calls, recursion, continuations and return destinations; shared step and call-depth limits; return preflight. The side table is transitional, not the normative named-call JSON representation.
- `verification/ccam_lowering.cap`: deterministic checked-source lowering for a restricted scalar subset. The module expects an already parsed and checked AST and deliberately rejects unsupported constructs.
- `verification/ccam_native_x64.cap`: Capstan-native GNU assembler syntax emitter for a narrow Linux x86-64 freestanding ELF path. It validates the in-memory multi-function representation before emission and rejects unsupported operations/resource excess. It emits assembly text, not an ELF executable.
- `docs/architecture/CCAM.md`: normative CCAM v0.1 intent with explicit statement that implementation is not yet conforming to the complete v0.1 machine and has no Lean refinement theorem.
- `docs/architecture/C-FREE-EXECUTION.md`: broad architecture intent and a useful earlier baseline inventory; it does not specify the staged S0-S3 contracts in this document.

### 3.2 Source-language subset lowered today

The lowering module's declared and tested scope is scalar int/bool locals, checked scalar expressions, direct calls, if/else, while/for loops, short-circuit boolean operators, and return/control-flow lowering including loop break/continue fixups. It maps source int/bool/void signatures into CCAM. Recursive direct calls are covered by tests. It rejects unsupported source types, unsupported expressions/statements, unsupported top-level declarations and unsupported call forms.

This is not the full language. In particular the native path does not establish lowering for strings, lists/maps, structs/enum values, options, taint, secrets, grants/policies, IO, concurrency, dynamic dispatch, exceptions, closures, async, modules/packages as a production compiler, formatter or language server. A feature being lexed, parsed or type-checked by the full compiler does not mean it is lowered by CCAM.

### 3.3 Feature and dependency matrix

Classification refers to the current production or verification role, not whether a component is desirable in the final architecture. Retirement evidence is the minimum evidence before removing/replacing the dependency.

| Area | Integrated capability / current dependency | Current classification | Gap and retirement evidence |
|---|---|---|---|
| Lexer | `compiler/lexer.cap`, source decoding, tokens, diagnostics | Production | Port lexer into S1 Capstan source; bound bytes/tokens/comments and prove/retest UTF-8 and escape behavior; differential corpus. |
| Parser | `compiler/parser.cap`, recursive descent, nesting cap and syntax recovery | Production | S1 parser subset then full grammar; bound tokens, AST, recursion and diagnostics; malformed/deep-input tests and semantic correspondence. |
| Type checker / semantics | `compiler/checker.cap` plus type/AST modules and safety rules | Production | Full compiler language rules exceed scalar CCAM. Specify core typing/evaluation order and map every safety check to IR/runtime enforcement; negative suite and proof obligations. |
| Source-to-CCAM lowering | `verification/ccam_lowering.cap` for checked scalar AST | Test-only / bootstrap research | Extend by explicit feature slices; source-to-CCAM simulation or independently justified correspondence per construct. |
| CCAM decoder | Normative JSON contract/schema described in CCAM docs; current evaluator consumes in-memory objects; PR #315 JSON decoder is explicitly not treated as integrated here | Missing production capability; PR #315 blocked/unmerged dependency | Stable strict decoder: duplicate-key rejection, exact integer parse, closed schemas, bounded bytes/depth/tokens/arrays/strings, deterministic errors; Linux CI and interface stabilisation before use. |
| CCAM validation | In-memory single-frame and multi-function validators | Test-only / formal target | Whole-program validator and call signature/control-flow validation are not the same as JSON decoder; establish soundness and bind to exact implementation. |
| Function calls/control flow/traps | Evaluator has bounded direct calls, recursion, branches, loops and explicit traps | Test-only / bootstrap research | Native backend must preserve all edge cases, exact trap identity/location and step-count precedence; complete differential vectors and refinement evidence. |
| Strings / collections | Present in Capstan compiler/runtime generally; absent from scalar CCAM profile | Production (legacy path) | Specify immutable/mutable string and collection semantics, bounds, encoding, ownership, aliasing and quotas before lowering. PR #304 byte output is unmerged experimental work, not an available dependency. |
| Memory allocation / lifetime | Legacy C runtime and conservative GC; abstract region/heap models exist | Production (legacy) plus formal verification models | No concrete native heap/collector contract yet. PRs #246/#262 do not establish production region heap; #255 is a mathematical model, not concrete refinement. Need allocator design, ownership/root semantics, failure atomicity, bounded heap and implementation-linked proofs/tests. |
| Runtime / standard library | `runtime/*`, `capstan_rt.h`, `capstan_gc.h`, POSIX/libc services | Production (legacy) | Inventory each API and semantic guarantee; replace with Capstan-native services or narrow platform capabilities; test without runtime/collector and audit imports/symbols. |
| Native code generation | `verification/ccam_native_x64.cap` emits assembly text for narrow scalar subset | Test-only / bootstrap research | Not an executable compiler. Audit instruction semantics, ABI, stack, arithmetic and trap paths; add assembler/linker driver and binary validation; native differential tests and codegen correctness argument. |
| Assembler / linker / ELF | GNU assembler/linker are intended external tools; no integrated production interface established by emitter alone | Platform boundary (proposed) | Pin exact tools/versions/flags; no compiler-driver hidden C path; inspect ELF type, interpreter, dynamic section, relocations, undefined symbols, entry point and segment permissions. Eventually consider integrated assembler/linker only with separate design. |
| OS interfaces | Linux x86-64 syscalls for freestanding prototype | Platform boundary | Specify syscall numbers, registers, clobbers, error mapping, exit behavior and kernel assumptions. No libc or ambient process/filesystem authority. |
| Compiler bootstrap | Current `bootstrap/capstan0.py` -> Python-hosted stage -> generated C -> C compiler chain | Bootstrap-only (legacy, currently required) | S0/S1/S2/S3 replace it. Prove release compiler build with Python and C toolchains unavailable; record independent seed trust. |
| Formatter | Existing compiler formatter path | Production (legacy) | Not covered by scalar CCAM. Port as compiler-adjacent tool or compile via S1; stable parse/print/idempotence corpus. |
| Language server | Existing compiler/LSP integration | Production (legacy) | Requires full parse/check/diagnostic and protocol/runtime capabilities; define bounded transport and process/IO boundary; test without legacy compiler/runtime. |
| Tests / verification | `tests/run.sh`, existing compiler test runner and CI currently execute Capstan tests via legacy bootstrap; Lean models and vectors are separate evidence | Production test infrastructure; formal verification; differential oracle | Transitional harness may execute Capstan-authored CCAM tests through legacy compiler. This does not make resulting freestanding executable C-dependent, but test/bootstrap infrastructure remains C/Python-dependent. Add native execution harness and exact-head result capture. |
| Release / provenance | Existing CI/release workflows, SBOM/provenance and reproducibility checks | Production release tooling | Rebuild outside legacy toolchain, bind evidence to exact source/toolchain/environment, diverse seeds, prove no forbidden dependency closure. |

### 3.4 Dependency classification rules

- **Production:** required by the current supported product/build/runtime path.
- **Bootstrap-only:** required only to construct a later compiler stage; must be absent from S3 production closure.
- **Test-only:** executes or checks tests but is not needed by the shipped program/compiler.
- **Differential oracle:** comparison implementation; useful but not normative and may share bugs.
- **Formal verification:** model/proof toolchain; its results cover only stated definitions and theorems.
- **Platform boundary:** external assembler/linker, OS, ABI, hardware or explicitly scoped service.

One tool may have different classifications in different workflows. For example, the legacy C compiler is production for the current compiler build, but may be test-only for transitional test execution once S1 native artifacts can be run directly. Classification must be attached to a concrete workflow and artifact.

## 4. Trust inventory

### Existing trusted path (to retire)

1. Python interpreter and `bootstrap/capstan0.py` seed.
2. Python-hosted stage-1 compiler.
3. Capstan source frontend/checker/code generator.
4. Generated C text and its C semantics/ABI assumptions.
5. GCC/Clang and associated assembler/linker.
6. `runtime/capstan_rt.h`, `runtime/capstan_gc.h`, collector and all linked runtime dependencies.
7. libc/POSIX behavior, dynamic loader and kernel.
8. Build scripts, environment, package dependencies and release builder.

### New native path (initially trusted)

1. S0 source/toolchain and its dependency closure (bootstrap only).
2. S1 compiler source, frontend/checker, CCAM lowering and validator.
3. CCAM semantics and any reference/differential evaluator.
4. Native backend, assembler and linker (unless and until codegen/toolchain proof/validation narrows this).
5. ELF loader/kernel/syscall ABI and hardware.
6. Capstan-native runtime/stdlib once introduced.
7. Build manifest, source identity, provenance signer and independent builder.

No claim that an external assembler/linker is harmless: they transform attacker-influenced compiler output into executable code. Their exact versions, flags, accepted input language and trust role are recorded. The Linux kernel/hardware remain outside the compiler proof unless separately modelled.

## 5. Resource and failure contracts

Every stage must bound, before use: input bytes; path/import count and depth; token count; syntax nesting; AST nodes; symbol/type table entries; diagnostics; CCAM functions/instructions/registers/arguments; string/name bytes; decoded JSON depth/tokens; output bytes; assembler/linker work; native code size; frame size; call depth; total stack; execution steps; and any heap/IO quota introduced later.

All size arithmetic is checked before allocation, indexing, pointer arithmetic or emission. Validation is whole-input and completes before execution. Unknown opcodes, fields, types, unsupported language constructs, invalid control flow, unbounded resource requests and tool failures fail closed. There is no implicit retry or fallback to the legacy C backend. Failure does not leave partially published artifacts; output publication uses temporary files and atomic rename at the host-tool boundary.

The scalar evaluator's instruction and call-depth ceilings are not a complete memory/CPU budget for the compiler or generated native executable. A separate budget is required for each stage.

## 6. Dependency graph

```text
                    S0 seed + pinned seed toolchain
                                  |
                                  v
Capstan compiler source -> checked source subset -> CCAM lowering
                                  |                     |
                                  |                     v
                                  |             closed CCAM validation
                                  |                     |
                                  |                     v
                                  +--------------> S1 native backend
                                                        |
                                                        v
                                               assembler + linker
                                                        |
                                                        v
                                               S1 freestanding ELF
                                                        |
                                  S1 compiles compiler source again
                                                        |
                                                        v
                                                  S2 self-hosted
                                                        |
                            diverse seed(s) + independent build(s)
                                                        |
                                                        v
                                          S3 reproducible release
```

Orthogonal assurance dependencies: canonical source/CCAM semantics; conformance corpus; formal model and refinement proofs; binary inspection; fuzzing/mutation testing; independent builders; provenance and dependency-closure audit. None substitutes for another.

## 7. Critical path, blockers and sequencing

1. **Freeze and audit baseline:** record exact `main` commit and interfaces; do not consume unmerged PR work.
2. **S1 native backend audit:** prove by tests or identify gaps for each emitted opcode, signed overflow, call/return, stack layout/alignment, stack exhaustion, traps, step/depth accounting, and ELF entry/exit. Add a dedicated assembler/linker and ELF inspection harness outside shared build files.
3. **Strict external CCAM boundary:** stabilize PR #315's JSON decoder only after its Linux CI failures and API contract are resolved. Until then the current in-memory structures are not a file/process interface.
4. **Native execution slice:** build a minimal Capstan program through checked frontend -> lowering -> validator -> emitter -> assembler/linker; run it directly. Compare complete outcomes to canonical CCAM vectors. Keep the existing harness clearly labelled transitional.
5. **Expand compiler subset:** add the exact source constructs needed by the actual compiler, not arbitrary surface-language breadth. Prioritize strings/collections and module/import support only after memory/ownership contracts exist.
6. **Runtime semantics:** specify and implement bounded allocation, ownership/lifetime, strings, collections, IO and failure semantics. Do not borrow the abstract heap models as if they were concrete implementations.
7. **S0/S1 compiler construction:** implement the independent seed and the first compiler source subset; record source/toolchain/artifact identities.
8. **S2/S3 assurance:** diverse bootstrap, independent builds, implementation-linked semantic evidence and dependency closure; only then schedule retirement of the C/Python path.

### Principal risks

- **Backend mismatch:** an emitter can accept validated CCAM but encode a different machine behavior. Mitigation: opcode-by-opcode audit, native conformance corpus, trap/step equivalence and formal or translation-validation evidence.
- **Unbounded native stack:** a recursive native call stack may exhaust the process stack before the CCAM depth limit; an emitter counter is not automatically a stack bound. Mitigation: checked prologue stack admission or a statically bounded stack budget; deterministic overflow trap; guard-page/ulimit adversarial tests.
- **Register initialization and type invariants:** native stack slots must preserve the evaluator's initialized/type semantics; every read and write path must be checked or proven statically.
- **Assembler/linker trust:** assembly text alone is not a native artifact. Pin and inspect toolchain, output format and symbol/relocation closure.
- **Missing external decoder:** in-memory validation does not protect a file boundary. Do not invent a parallel decoder.
- **Heap/runtime scale:** full Capstan compiler uses strings, lists/maps, AST nodes and other heap objects. Scalar CCAM cannot compile/run it until those semantics are designed and implemented.
- **Bootstrap circularity:** S0 must be independent and bounded, but S1 source must not grow beyond the seed subset before S1 exists.
- **Trusting-trust:** a fixpoint or agreement among related stages can preserve malicious behavior. Diverse seeds, source audits, semantic corpus and implementation-linked correctness evidence are all required.
- **Integration churn:** active PRs may change CCAM interfaces. Keep this branch isolated and rebase only after explicit review/coordination; do not edit shared modules or active PRs.

## 8. Minimum missing semantics and proof obligations

Before native backend use as a credible execution target:
- Canonical machine input representation and strict decoder, with duplicate-key and exact-number handling.
- Whole-program validation for all functions/calls/control-flow and explicit validation-vs-trap distinction.
- Defined machine state, transition relation, instruction accounting order, trap payload, call stack and return semantics.
- Native ABI and stack contract, including alignment, maximum stack and failure on exhaustion.
- Correspondence for each supported CCAM instruction, including overflow and signed division/remainder edge cases.
- ELF/linker contract and binary-level checks: no PT_INTERP, no dynamic dependency, no undefined external symbols, expected entry point, no unexpected relocations, and intended segment permissions.
- Actual executable test evidence; generated assembly tests alone are insufficient.

Before compiling the actual Capstan compiler:
- Strings and source decoding/encoding semantics.
- Bounded dynamic arrays/maps and object representation.
- Heap allocation, ownership, aliasing, object lifetime, failure atomicity and eventual collector or explicit ownership strategy.
- AST/diagnostic/symbol/type representations and complete required language subset.
- Imports/modules and deterministic filesystem capability interface.
- Compiler-wide work/memory budgets, cancellation and failure cleanup.
- Runtime/stdlib for formatting, file IO and process exit (or explicitly constrained alternatives).
- Formatter and language-server dependencies if they are included in the claimed production toolchain.

Proof order:
1. CCAM specification/model and concrete evaluator conformance (tests/vectors, separately from proof).
2. Validator soundness and decoder correctness.
3. Lowering simulation for each source construct.
4. Native instruction/ABI correspondence for each emitted opcode and runtime check.
5. Memory/ownership/stack invariants for concrete runtime.
6. Compiler correctness composition across frontend, lowering, backend and platform assumptions.
7. Bootstrap and diverse-build assurance. Reproducibility remains separate from semantic correctness.

## 9. PR and integration dependencies

- **PR #315:** JSON decoder remains a dependency only after Linux CI failures are resolved and the public interfaces are stabilised. No duplicate decoder is to be built here.
- **PR #304:** byte-output extension is experimental/unmerged CCAM v0.2 work. This plan does not consume it or assume it is part of v0.1.
- **PRs #246 and #262:** do not establish a production region heap or implementation refinement. Native runtime work must await an agreed concrete contract.
- **PR #255:** reference/heap semantics are mathematical models, not proofs of the concrete runtime.
- **PRs #371 and #372:** current assurance contributions do not establish completed implementation refinement. This workstream will consume no unmerged code from them.
- Any future shared-file/interface change must be proposed in issue #370 and coordinated after the integration worker has stabilised the relevant mainline interface.

## 10. B1 prototype work started and native-backend audit notes

An isolated research harness now exists at `research/native-bootstrap/check-elf.sh`. It accepts assembly emitted by the Capstan-native test driver, invokes GNU `as` and `ld` directly (never a C compiler driver), requests a static `-nostdlib` ELF executable, checks ELF64/x86-64/ET_EXEC, rejects PT_INTERP and a dynamic section, rejects undefined symbols and remaining relocations, executes the result against an expected exit status, and prints tool versions and artifact hashes.

**Execution status:** the harness has been authored but has not yet been run against actual emitted assembly. No ELF artifact, runtime result or binary inspection result is claimed. The current test helper `ccam_x64_write_test_program` can write assembly from Capstan source, but it is invoked by the existing Capstan test environment; therefore the harness itself does not remove the transitional Python/C test bootstrap.

A source-level audit of `ccam_native_x64.cap` also identified two semantic/evidence items to resolve before claiming native CCAM equivalence:

1. The in-memory CCAM explicit trap carries a reason/detail, while the x86-64 emitter routes every explicit trap to a single exit status (72). This may preserve termination but does not preserve the full specified trap observation. The native profile must either define and validate a precise observable trap projection or retain reason/detail through an explicit output contract; it must not call the result fully equivalent while this information is discarded.
2. Native stack-allocation failure and uninitialised-register failure currently route to the same process exit status (75). These are distinct failure causes and should be distinguishable in the native result contract, or the documented profile must explicitly state the coarser projection and prove that no caller depends on the distinction.

The emitter's static assembly contains explicit Linux `mmap`, `mprotect` and `exit` syscalls, bounded stack sizing, guard-page setup, call-depth checks and per-instruction step checks. The stack arithmetic is bounded by the integrated validator's per-function 4096-register limit and call-depth limit of 256: the maximum frame is 65,536 bytes and the conservative reservation is 16,781,312 bytes, below the 32 MiB native-stack ceiling. This is a source-level bound, not yet an execution test of the guard-page behavior.

A further semantic mismatch is confirmed: an integer entry result is placed in `%rdi` and returned through Linux `exit(2)`. Linux process exit status exposes only the low eight bits. Therefore values such as 256 are observed as 0, and negative or large 64-bit results are not preserved. The current executable interface is only suitable for an explicitly documented 8-bit process-status projection; it is not observationally equivalent to the CCAM signed-64 return value. Before claiming the native program interface preserves CCAM results, define a result channel (for example, a fixed-width, versioned result record written to a designated file descriptor) and specify short-write/error handling and output bounds. Do not silently reinterpret an int64 function result as an exit status.

The harness's initial dynamic-section check was also corrected: GNU `readelf -d` returns success even when it reports that no dynamic section exists. The corrected harness inspects that diagnostic explicitly and additionally rejects writable+executable LOAD segments and an executable GNU_STACK. These checks have been authored but have not yet been run against Capstan-emitted output. The actual assembled ELF must still be inspected for load segments, permissions, entry point, interpreter/dynamic metadata, symbols and relocations, and the executable must be run under adversarial stack/resource tests.

## 11. Deliverable status and acceptance gates

| Deliverable | Status | Acceptance evidence |
|---|---|---|
| B0 architecture/dependency report | This document establishes the initial contract and source audit | Review against current main; refresh identities and matrix after integration changes |
| B1 native feasibility prototype | Not yet demonstrated end-to-end | Capstan source -> checked lowering -> validation -> assembly -> ELF -> direct execution; resource and binary tests |
| B2 actual compiler bootstrap feasibility | Initial blockers identified in sections 3, 7 and 8 | Inventory every compiler dependency and map to supported S0/S1 subset, missing semantics, API and proof |
| B3 integration proposal | Initial dependency/PR boundaries recorded in section 9 | Exact shared files/interfaces and PR sequence after integration stabilises |

No completion claim is made for B1-B3 by the existence of the current CCAM evaluator, lowering module or assembly emitter.
