# Compiler pipeline audit and direct-native backend boundary

**Status:** Initial audit, 2026-11-24  
**Workstream:** `compiler/direct-native-prototype`  
**Baseline:** Capstan v0.4 compiler on `main`; v0.6 remains an independent migration baseline  
**Related programme:** [#80](https://github.com/DavidFernee/Capstan/issues/80), [#81](https://github.com/DavidFernee/Capstan/pull/81)

## 1. Scope and evidence

This is a source-level first pass, not a completed line-by-line inventory. It records the implementation observed in the repository and separates facts from design decisions still requiring coordination. The C-free lane must not redefine the Capstan Core Abstract Machine (CCAM). CCAM owns instruction semantics, machine state, traps and deterministic execution limits; this compiler workstream consumes that contract and owns the source/typed-IR/backend boundaries.

## 2. Current compilation pipeline

```
Capstan source (.cap)
  -> compiler/lexer.cap
  -> compiler/parser.cap
  -> compiler/ast.cap Node tree
  -> compiler/checker.cap (types + language/security diagnostics)
  -> compiler/ranges.cap (range facts / check elimination)
  -> compiler/codegen.cap (C text)
  -> generated C + runtime/capstan_rt.h + runtime/capstan_gc.h
  -> host C compiler (CC, normally GCC or Clang)
  -> native executable
```

The parser builds `Node` trees. The checker annotates nodes with `Type?` (`Node.ty`); there is no separately specified, immutable, validated typed IR at this boundary. Range analysis consumes the checked AST and decides whether certain generated runtime checks can be elided. The code generator then maps Capstan values and operations to C expressions/statements and runtime calls.

Important existing correctness constraints visible in the code generator include left-to-right evaluation. C does not specify evaluation order for all operands and function arguments, so `compiler/codegen.cap` explicitly hoists side-effecting expressions into temporaries where needed. This behaviour must become an explicit IR sequencing rule, not an incidental property of C emission.

## 3. Trust and dependency inventory

| Stage/component | Current role | Trust/evidence status |
|---|---|---|
| Lexer/parser | Turn source into syntax tree | Trusted implementation; covered by compiler tests/fuzzing, not independently verified |
| Checker | Enforce types and source-level safety rules | Security-critical trusted compiler code; tests and CWE atlas provide evidence, not a proof |
| Range analysis | Remove arithmetic/index checks when inferred safe | Trusted optimisation; its soundness argument is documented in source and exercised by property/differential tests, not machine-proved |
| C code generator | Translate checked AST into C and runtime calls | Trusted semantic translation layer; no translation-correctness proof |
| `bootstrap/capstan0.py` | Stage-0 translator from Capstan to Python | Unchecked bootstrap component; part of current bootstrap TCB |
| Python 3 | Executes stage-1 Python compiler and repository test/support scripts | Build/test dependency, not part of the final native program's runtime |
| GCC/Clang | Compile generated C into executable | Trusted compiler dependency; alternate-compiler and optimisation-level testing provide diversity evidence, not proof |
| Linker, C library, platform ABI | Complete and execute native program | Trusted platform/build boundary |
| `runtime/capstan_rt.h` | Arithmetic checks, panic/termination, strings, collections, IO and runtime operations | C implementation is in the execution TCB |
| `runtime/capstan_gc.h` | Allocation, conservative root scanning, mark/sweep GC, stack guard and OS memory calls | C implementation and its POSIX/pthread/signal/mmap dependencies are in the execution TCB |
| Makefile / scripts / CI | Orchestrate bootstrap, tests and release builds | Build-system trust; scripts include shell and Python |
| Self-hosting fixpoint | Compare stage-2 and stage-3 generated C | Reproducibility/self-consistency evidence only; does not prove source-language or compiler correctness |

### 3.1 Bootstrap chain

The observed Makefile chain is:

1. `bootstrap/capstan0.py` translates the Capstan compiler sources into `build/stage1.py`.
2. Python 3 runs stage 1 to emit `build/stage2.c`.
3. GCC/Clang compiles stage-2 C, together with `runtime/capstan_rt.h`, into `build/capstanc2`.
4. Stage 2 compiles the compiler sources again to `build/stage3.c`.
5. The build compares stage-2 and stage-3 C byte-for-byte, then compiles the result into `build/capstanc`.

The fixpoint establishes that the native compiler reproduces its own C output for this source/build configuration. It does not establish that stage 0 correctly translates Capstan, that the C output implements the language semantics, or that the C compiler/runtime/ABI are correct.

### 3.2 Python distinction

Python has two distinct current roles:
- bootstrap execution of the stage-0/stage-1 compiler chain;
- test, fuzzing, mutation, release and assurance tooling (for example `tests/run.sh` invokes numerous Python scripts).

The new CCAM executable implementation and conformance tests are required to be Capstan source under the direction recorded on PR #81. That does not immediately remove Python from the overall repository build/test environment. A C-free *program execution path* and a fully Python-free *development/build environment* are separate milestones.

## 4. Runtime and semantic obligations relevant to code generation

The native backend must not silently narrow the existing language contract. At minimum, source/IR/backend mapping must account for:

- signed 64-bit integer semantics, checked overflow, division by zero, the `INT64_MIN / -1` edge case, remainder semantics, and checked shifts;
- left-to-right evaluation and short-circuit boolean operators;
- structured control flow, loop exits and returns;
- function parameter/result typing and a documented target calling convention;
- bounds-checked indexing and safe collection operations;
- explicit optional representation and absence/presence semantics;
- taint/validated-text distinctions, secret storage/zeroisation, and grant/capability provenance;
- deterministic traps and bounded execution/resource use;
- object layout, allocation, GC roots, pointer maps and runtime/OS boundaries.

This list is an obligation inventory, not a redefinition of CCAM or the language specification. The semantic authority remains the normative language specification and the CCAM contract developed by the semantics/verification workstreams.

## 5. Compiler architecture proposal

Use three explicit interfaces rather than one opaque AST-to-machine-code step:

1. **Front-end contract:** parsing and checking produce a typed, fully resolved program representation. No unresolved names, error types, implicit coercions, or unchecked control-flow targets may cross this boundary.
2. **Machine-facing IR contract:** a typed IR is validated before interpretation or lowering. It records explicit control-flow edges, typed operands/results, function signatures, effects/traps and source provenance. It must retain security-relevant distinctions until the relevant enforcement point. Its instruction semantics are delegated to CCAM; this document intentionally does not duplicate them.
3. **Backend contract:** a narrow target-specific lowering consumes only validated IR and emits object/executable code. Target ABI, register allocation, stack layout, relocations and runtime imports are explicit backend concerns, not CCAM semantics.

Every pass should publish:
- input and output invariants;
- a validator or construction guarantee;
- its observable-behaviour preservation obligation;
- a negative test showing malformed input is rejected;
- differential/conformance coverage against the CCAM reference semantics;
- explicit assumptions and trusted code remaining in that pass.

### 5.1 Initial target strategy

Do not begin with a multi-target framework. Select one host-native target only after the CCAM contract and platform support matrix are confirmed. The first prototype should minimise the backend:
- one target architecture and object format;
- a deliberately small integer/control-flow/function subset;
- no heap, GC, strings, IO, grants, secrets or concurrency until their machine/runtime contracts are ready;
- a platform assembler/linker may be used initially, but it must be named in the TCB and its input/output contract recorded.

A direct machine-code emitter is not automatically more trustworthy than C generation. The first prototype should prefer simple, inspectable encodings and independently validate emitted code. If an external assembler is used, the compiler must emit a documented assembly subset and test the assembler boundary; if raw object emission is used, object-file parsing/relocation correctness becomes part of the trusted backend.

## 6. Verification and test strategy

- Treat CCAM as the semantic reference; the old C backend is a differential comparator, not the semantic authority.
- Compare observable outcomes: returned values, output, trap class/location, and deterministic resource-limit outcomes.
- Generate small well-typed programs and compare CCAM execution with native execution; preserve minimized counterexamples as regressions.
- Validate IR independently, including malformed type IDs, undefined registers, use-before-definition, mismatched branch argument types, invalid block targets, invalid function signatures, and inconsistent return types.
- For each IR transformation, use a local simulation relation and property-based differential tests. Do not optimise until the unoptimised lowering is stable.
- Use translation validation for each emitted function as an early assurance layer; pursue a proved code generator only after the target subset and semantics stabilise.
- Run target disassembly/structural checks and adversarial malformed-IR tests. Testing does not replace a proof and a proof does not validate an incorrect specification.

## 7. Bootstrap and trust-reduction plan

Reproducibility and correctness are different properties. Keep the existing fixpoint as a reproducibility gate, but do not describe it as compiler correctness.

A staged reduction is preferable:
1. Make the compiler's front-end and typed-IR contracts explicit while retaining v0.6.
2. Implement the CCAM and a Capstan-native evaluator as a separate, testable reference path.
3. Implement a minimal native backend for the same CCAM subset and differential-test it.
4. Build the new backend with the old compiler temporarily, recording the old compiler, Python stage 0, C compiler/runtime and platform tools in the bootstrap TCB.
5. Establish independent reproducible builds and compare outputs from diverse bootstrap paths.
6. Bootstrap the compiler/backend from a separately built implementation and progressively replace C/Python-dependent bootstrap stages with Capstan-native stages.
7. Retire the old C path only after semantic conformance, security regression, platform, reproducibility and assurance gates are met.

A self-hosting fixpoint can detect some accidental divergence; it cannot detect a consistently wrong compiler. Stronger evidence requires an independently specified semantics, independent implementation or checker, diverse compilation paths, and ultimately a compiler-correctness argument.

## 8. Coordination boundaries and open decisions

- **CCAM semantics owner:** owns instruction set, machine state, step semantics, traps and deterministic resource model. Backend consumes these definitions; it must not create a parallel machine.
- **Formal verification owner:** owns proof assistant selection and mechanised semantic/compiler-correctness work. Backend supplies precise pass contracts and target assumptions.
- **Runtime owner:** owns runtime service and ABI boundaries. Backend must not introduce a competing allocator, GC, panic or capability model.
- **Compiler workstream:** owns typed front-end/IR validation interfaces, IR lowering, target-specific code generation and compiler-side differential harness integration.

Before implementing shared representations, obtain agreement on:
- CCAM value and type representation, function model and calling convention;
- control-flow representation and trap/result model;
- target triple, object format and assembler/linker assumptions;
- whether typed IR is an extension of CCAM or a separate source-lowering IR with a specified refinement mapping.

No decision above is treated as final by this audit.
