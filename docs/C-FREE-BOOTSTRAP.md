# C-Free Self-Hosting and Bootstrap Contract

**Status:** normative development contract; implementation is incomplete.  
**Scope:** compiler, execution format, native backends, runtime, and release bootstrap.  
**Release target:** Capstan 1.0. This document does not claim that the target has been implemented.

## 1. Goal and terminology

Capstan 1.0 must compile Capstan programs to executable code without generating C, invoking a C compiler, or requiring a Capstan-owned C runtime. The compiler itself must be written in Capstan and compile its complete source tree.

These terms are distinct:

- **Self-hosted:** the compiler is implemented in Capstan and can compile Capstan source. This describes implementation language, not build dependencies.
- **C-free:** the supported build and execution path does not generate or compile C and does not depend on a Capstan-owned C runtime. C must not be hidden behind an FFI or helper executable.
- **Native:** the compiler emits executable machine code or native object files for the target ABI. A CCAM interpreter alone is not a native backend.
- **Bootstrapped:** a documented seed compiler produces the next compiler stage through a bounded, auditable process.
- **Fixed point:** independently built compiler stages agree under the specified reproducibility comparison and produce the same result when compiling the same compiler source and build inputs.

The existing Python-seeded, C-generating compiler is self-hosted in the first sense, but it is not yet C-free or natively self-hosting under this contract.

## 2. Required end state

For every supported target:

1. The complete compiler, standard library, and runtime implementation are written in Capstan.
2. Capstan source is parsed, checked, lowered to the canonical typed CCAM contract, and compiled to native code without a generated-C intermediate.
3. The native executable does not require a Capstan-owned C runtime, C compiler, Python, or interpreter to execute supported native programs.
4. The compiler compiles its own complete source tree, including the compiler, release-build tools, and in-tree runtime.
5. The resulting compiler compiles that same complete source tree again. The stage comparison is deterministic and documented.
6. The same semantic conformance suite runs against the reference CCAM evaluator and every native backend.
7. Platform-specific code is isolated behind small, explicit ABI/OS interfaces. Those interfaces are part of the trusted computing base and receive separate review and tests.
8. The release process records source revision, seed compiler identity, target triple, build flags, toolchain inputs, artifact hashes, and test/proof evidence.

A platform is not C-free merely because its main compiler is written in Capstan if its runtime, launcher, code generator, or required build helper still relies on C.

## 3. Bootstrap stages

A bootstrap requires an initial executable seed: source code cannot compile itself before some implementation has run. The existence of a seed is not a defect; an opaque, permanently required external compiler is.

The intended stages are:

| Stage | Role | Permitted dependencies | Acceptance evidence |
|---|---|---|---|
| Seed (S0) | Small, independently identified compiler executable for the host/target | A documented prior release or independently built seed; no network fetch during the build | Hash, provenance, source revision, target and limitations recorded |
| S1 | S0 compiles the complete Capstan compiler source into a native compiler | S0 and explicitly documented platform linker/OS interface only | Compiler conformance; no generated C; no Python; no C compiler |
| S2 | S1 compiles the same complete compiler source | S1 and the same declared platform interface | S1/S2 reproducibility comparison and full test suite |
| S3 (audit) | S2 compiles the same source again | S2 and the same declared platform interface | S2/S3 comparison; independent rebuild and provenance record |

The release process must define the exact comparison rule. Prefer byte-identical normalized compiler artifacts. If target formats embed unavoidable nondeterministic metadata, normalize only documented fields and compare all executable sections, relocation data, symbol tables, and semantic build manifests. “Equivalent output” without a defined comparison is insufficient.

The seed may be a previously released Capstan-native executable or a separately built bootstrap executable. The Python stage-0 translator may remain temporarily as a development bridge, but it must not be a required dependency of the final C-free bootstrap or release build. A first-ever build on a new architecture may use a documented cross-build seed; it must not silently introduce GCC/Clang or Python into the claimed C-free stage chain.

## 4. Compiler pipeline contract

The C-free pipeline is:

~~~text
Capstan source
    -> lexer / parser
    -> source checker and security diagnostics
    -> typed source representation
    -> deterministic lowering
    -> validated canonical CCAM
    -> target lowering / register allocation
    -> native object or executable
    -> platform ABI and OS interface
~~~

Requirements:

- The language specification defines evaluation order, integer widths, overflow behaviour, trap semantics, call/return semantics, memory model, and observable I/O behaviour independently of any backend.
- The source checker rejects invalid programs before lowering. The lowerer independently rejects unsupported or malformed constructs; it never silently approximates them.
- CCAM is the semantic authority for the supported core. Optimisation IRs may be introduced only with an explicit refinement relation to CCAM and differential tests.
- Validation is bounded before proportional allocation. Limits cover input bytes, functions, instructions, registers, constants, names, call arguments, nesting, memory, stack depth, and execution steps. Aggregate limits are checked as well as per-item limits.
- If serialized CCAM is used at a trust boundary, it has a closed schema, duplicate-key rejection, canonical integer/number rules, bounded decoding, and whole-program validation. An in-memory validator is not evidence of safe decoding.
- Unsupported language features fail closed with stable diagnostics. Feature coverage is a machine-readable matrix; “compiles itself” must not be achieved by excluding difficult compiler modules from the self-hosting build.

## 5. Native backend and runtime contract

The native backend implements CCAM semantics for each target. It does not use generated C as an intermediate and does not delegate code generation to GCC or Clang at build time.

The implementation specifies and tests:

- target data layout, integer representation, alignment, calling convention, stack layout, register preservation, and return-value rules;
- checked arithmetic, bounds checks, division/shift traps, explicit traps, and deterministic failure behaviour;
- object format, relocations, symbol resolution, linking, executable permissions, and platform entry points;
- stack and heap limits, allocation failure, and memory reclamation;
- strings, collections, I/O, cryptographic operations, and other runtime services;
- process startup/shutdown, exit status, and interaction with the operating system.

The runtime is implemented in Capstan. Any unavoidable assembly or OS-specific boundary is small, documented, reviewed, and included in the trusted-base inventory. The target is to avoid dependence on libc as well as on a Capstan-owned C runtime; if a platform implementation temporarily relies on libc, that platform is labelled transitional and is not advertised as satisfying the strict end-state gate.

## 6. Formal and executable assurance obligations

Proof fragments and passing tests must not be promoted into claims about unproved layers. Keep separate obligations for:

1. CCAM abstract semantics and machine-state invariants.
2. The implementation validator's correspondence to the validated CCAM contract.
3. Source-checker soundness for each security rule claimed.
4. Source-to-CCAM lowering semantic preservation, including evaluation order, calls, effects, and traps.
5. Each optimisation's refinement to the canonical semantics.
6. Native backend preservation of CCAM observable behaviour.
7. Runtime memory, allocation, lifetime, and OS-interface properties.
8. Bootstrap stage correctness and reproducible-build procedure.

For each theorem, record the exact model, implementation revision, assumptions, axioms, proof toolchain, and what the theorem does not establish. A Lean model of a machine fragment is not a proof of the Capstan implementation unless an explicit implementation correspondence theorem is established.

Executable evidence includes:

- shared positive and negative conformance tests across the reference evaluator and native targets;
- differential tests comparing results, output, traps, and resource-limit behaviour;
- fuzzing of source parsing, CCAM decoding/validation, lowering, and native execution;
- malformed-input and exact-boundary/one-over resource-limit tests;
- sanitizers and platform-specific memory diagnostics where available;
- compiler self-checks (strict and release checks) at every compiler stage;
- reproducibility checks on independent clean builders.

## 7. Platform rollout

Use one language front end, canonical CCAM semantics, conformance corpus, and bootstrap protocol. Implement separate native backends and OS interfaces where ABI or object format requires them.

Minimum 1.0 target matrix:

| OS | Architectures |
|---|---|
| Linux | x86-64, AArch64 |
| macOS | x86-64, Apple Silicon (AArch64) |
| Windows | x86-64, ARM64 |

Each row is an independent acceptance target. Passing Linux does not establish macOS or Windows support. Cross-compilation may be used, but the seed, linker, sysroot, and cross-toolchain dependencies are recorded. The strict C-free gate applies separately to the build and runtime path for each target.

## 8. Release gate

Capstan 1.0 must not claim C-free self-hosting for a platform until all of the following are true:

- [ ] Compiler, standard library, and runtime sources required for the supported build are Capstan sources, except documented minimal assembly/OS boundaries.
- [ ] No generated C is produced or consumed in the release path.
- [ ] No C compiler or Python interpreter is required by the release bootstrap stages.
- [ ] No Capstan-owned C runtime or required libc dependency remains on the strict target path.
- [ ] Native backend passes the shared CCAM conformance and differential suite.
- [ ] Complete compiler source builds through S0→S1→S2→S3 with the prescribed reproducibility result.
- [ ] The compiler's own strict/release checks pass at each stage.
- [ ] Independent clean builders reproduce the compiler artifact and record provenance.
- [ ] Formal obligations and residual gaps are recorded honestly; no proof fragment is presented as end-to-end compiler correctness.
- [ ] Linux, macOS, and Windows target rows pass independently before an all-major-platform claim is made.
- [ ] The trusted-base inventory and release scorecard are updated to the exact tested commit.

A platform may be described as “C-free experimental” before this gate only if remaining C, libc, Python, interpreter, and proof limitations are stated explicitly.

## 9. Migration strategy

Keep the current v0.6 C-backed path as a compatibility and differential baseline until the native path has equivalent language coverage and stronger evidence. Do not delete the baseline merely because a small CCAM subset executes.

Proceed incrementally:

1. Stabilise the CCAM semantic contract and bounded whole-program validation.
2. Complete multi-function execution and source lowering in small fail-closed increments.
3. Establish shared differential conformance tests before backend expansion.
4. Implement a minimal native backend for one architecture and the smallest useful runtime slice.
5. Compile increasingly large portions of the compiler itself; track unsupported constructs and dependencies explicitly.
6. Move the compiler and runtime into Capstan, then establish the S0→S1→S2→S3 bootstrap.
7. Add target backends and platform interfaces, running the same conformance suite on each.
8. Remove Python/C build dependencies only after the strict bootstrap and compatibility gates pass.

This sequence permits early progress without confusing a working scalar evaluator, a source-lowering prototype, or a self-hosted C generator with a complete C-free compiler.

## 10. Current status

**Snapshot reviewed:** main at `8d0a5583d1f586544a61ca0ae5405c64ebc576c1` (2026-11-25).

The production compiler still uses the Python-seeded bootstrap and generates C for GCC/Clang; its executable uses the Capstan C runtime. It is self-hosted, but it is not C-free under the definitions in this contract.

The current CCAM development slices on main are:
- PR #142: restricted Capstan-native single-frame evaluator;
- PR #163: typed in-memory structural validator for that single-frame subset;
- PR #207: bounded multi-function call-frame evaluator, using transitional call-site side tables;
- PR #210: checked scalar source-to-CCAM lowering, not wired into the production compiler CLI;
- PR #205: concrete Lean-model correspondence lemmas for native CCAM register tags and checked field reads/writes; this is a register-representation result, not a whole-evaluator refinement theorem.

The source for a narrow freestanding Linux x86-64 native emitter is present in `verification/ccam_native_x64.cap` and described in `docs/architecture/CCAM-NATIVE-BACKEND.md` (PR #212). It is an experimental scalar backend, not a production compiler backend: it lacks full CCAM instruction coverage, a complete runtime/output path, all-instruction differential conformance and an implementation-refinement theorem to the CCAM model.

The normative CCAM v0.1 document remains explicit that the implementation is not yet a conforming v0.1 machine, does not have a Lean evaluator-refinement theorem, and is not the complete Capstan semantics. The current status of every slice must be checked against that document and exact mainline code/tests. No C-free compiler bootstrap, C-free production runtime or multi-platform C-free release is established.

Update this section only against exact source revisions and current-head test evidence. Open pull requests, stale workflow runs and design documents are not evidence of completed implementation. A passing model build is not implementation refinement; a prototype execution test is not complete backend conformance.
