# Compiler assurance, adversarial testing and performance plan

**Status:** test strategy for the C-free compiler workstream  
**Date:** 2026-11-24  
**Branch:** `compiler/direct-native-prototype`  
**Semantic authority:** CCAM specification and Capstan-native executable implementation; no parallel semantics are introduced here.

## 1. Current evidence and scope boundary

The current main-branch baseline contains the C-generating compiler, C runtime and Python/C bootstrap described in `COMPILER-PIPELINE-AUDIT.md`. The initial CCAM proposal and Capstan-native arithmetic/register substrate are currently on the separate PR #81 branch `architecture/c-free-formal-foundation`, not yet part of main at the time of this plan.

Observed PR #81 state:
- `docs/architecture/CCAM.md` defines CCAM v0.1 for signed-64 integers, booleans, typed local registers, arithmetic, branches, calls/returns, traps and deterministic step/call-depth limits.
- `verification/ccam_core.cap` currently implements checked arithmetic and a typed register-file substrate. It is not yet a complete evaluator.
- The PR head's GitHub Actions workflow run #582 completed successfully. This is CI evidence for that exact PR head, not evidence of a completed evaluator, native backend or formal proof.

The first native backend must wait for the CCAM instruction/evaluator interfaces and the formal/runtime owners' agreement. This plan can be adopted now without creating a competing machine.

## 2. Assurance principles

1. **One oracle:** use the normative CCAM specification plus its Capstan-native conformance implementation as the semantic reference. The old C backend is a useful migration comparator, not the authority.
2. **Validate before execution:** untrusted or compiler-produced IR is structurally validated before it can reach an interpreter or backend. Backend preconditions are explicit and rechecked at the trust boundary.
3. **Fail closed:** malformed programs are rejected, not partially executed. Resource exhaustion becomes a specified deterministic outcome.
4. **Differential testing is not proof:** mismatches are bugs; agreement is evidence only for tested cases.
5. **Optimise after correctness:** first establish a simple unoptimised backend and stable baseline. Each optimisation must preserve outcomes and be independently switchable.
6. **Measure reproducibly:** pin target, compiler flags, host, workload, warm-up, repetitions and statistical method. Keep raw results.
7. **No benchmark-driven semantic changes:** arithmetic, traps, order and resource semantics do not change to improve a score.

## 3. Validation and adversarial test matrix

### 3.1 Program and IR structural validation

Every invalid input below must be rejected before execution/code generation, with a bounded diagnostic and no crash, hang, memory blow-up or partial executable.

| Attack / malformed input | Required validator property |
|---|---|
| Duplicate or empty function names | Function namespace is unique and canonical |
| Missing entry function / wrong entry signature | Entry contract is checked before execution |
| Unknown instruction opcode / missing or extra fields | Instruction schema is closed and exhaustive |
| Negative, oversized or out-of-range register index | Every register reference is range-checked without indexing first |
| Invalid register type tag | Only specified type constructors are accepted |
| Parameter count exceeds register count | Function signature is internally consistent |
| Call to missing function | Every call target resolves |
| Wrong call arity or argument types | Call arguments match callee parameters positionally |
| Non-void call with absent destination; void call with destination | Call destination agrees with callee result type |
| Destination register has wrong type | Every write's result type matches destination |
| Uninitialised register read | Static validation rejects when provable; dynamic semantics trap otherwise |
| Invalid jump/branch target | All control-flow targets are within the owning function |
| Branch condition is not bool | Operand type is checked |
| Return type mismatch / return from void with value | All returns agree with function signature |
| Reachable fall-through / empty function | No path can run beyond the instruction sequence |
| Malformed trap reason | Trap codes are enumerated or validated against the normative set |
| Extremely large function/register/program counts | Size limits checked before allocation and iteration |
| Cyclic call graph / deep recursion | Deterministic call-depth semantics; no host stack escape |
| Repeated validation of same program | Deterministic verdict; no mutation or stale validation cache |

The validator must have its own negative tests. It is not enough that the evaluator happens to trap when malformed input reaches it.

### 3.2 Dynamic CCAM conformance

For each instruction, include:
- minimum valid operands and representative normal cases;
- signed-64 boundary values and values one step beyond where representable in the input encoding;
- invalid register/type/initialisation cases;
- exact trap code, function and PC;
- step count and call-depth boundary behaviour;
- state invariants before and after each transition.

Arithmetic properties:
- add/sub/mul: compare against arbitrary-precision mathematical integers, then classify success iff result is in `[INT64_MIN, INT64_MAX]`;
- div/rem: verify truncation toward zero, `a = q*b + r`, `abs(r) < abs(b)`, and remainder sign follows dividend; zero and MIN/-1 trap;
- boolean/int disjointness and comparison result typing;
- no host undefined behaviour or accidental wraparound.

Control-flow/call properties:
- branch true and false edges; jump to first/last valid instruction;
- loops terminating exactly at the step limit and one step beyond;
- direct, nested and mutually recursive calls;
- return value transfer to the correct caller destination;
- void calls, entry return, and call-depth boundary including the entry frame;
- traps in a callee propagate without corrupting caller state;
- left-to-right argument register reads and atomic instruction effects.

### 3.3 Differential and property-based testing

Use the same Capstan-authored vectors for:
1. the CCAM evaluator;
2. the unoptimised native backend;
3. the optimised native backend (when introduced);
4. an independent formal model/checker when available.

Compare complete observable outcomes, not only exit codes:
- `Halt(value)` or `Trap(code, pc, function)`;
- exact standard output/error if the subset includes IO;
- instruction steps and deterministic resource-limit outcomes;
- externally visible memory/runtime effects when later machine versions add them.

Generate valid typed programs from a grammar constrained by the CCAM type environment. Separately generate malformed programs by mutating every structural field. Keep seeds, shrink failures to minimal counterexamples, and add each minimized failure to permanent Capstan conformance tests.

Avoid using the same helper implementation in the generator and oracle for critical operations; correlated bugs reduce differential value.

### 3.4 Native backend and ABI adversarial tests

For the first target, test:
- instruction encoding and branch displacement boundaries;
- relocation/symbol resolution and section bounds if the backend writes object files;
- stack alignment at every call boundary;
- callee-saved/caller-saved register preservation;
- parameter and return-value placement;
- nested calls and register spills;
- stack-frame size arithmetic overflow;
- executable entry point and exit status;
- W^X policy and executable-memory permissions where applicable;
- malformed object/assembly rejection by the selected assembler/linker;
- deterministic output bytes from identical validated IR and build parameters.

Use disassembly-based structural assertions for the tiny supported subset. If an external assembler/linker is used, include its version and invocation in the TCB and reproducible-build record.

### 3.5 Compiler and validator denial-of-service tests

Apply explicit input budgets before allocating large structures. Test:
- huge source files, functions, instruction vectors and register files;
- deeply nested expressions and CFGs;
- very long identifiers and repeated duplicate names;
- dense and sparse CFGs;
- worst-case branch target and call graph patterns;
- repeated validation of adversarial inputs;
- infinite loops and recursion at exact step/depth boundaries;
- large integer literals, malformed encodings and truncated input;
- cancellation/timeout behaviour in external assembler/linker steps.

Record peak RSS, CPU time and output size. A process killed by an external timeout is not a correct deterministic CCAM trap; distinguish build-tool resource failure from language semantics.

## 4. Efficiency programme

Do not benchmark until the unoptimised native backend passes the same conformance vectors as CCAM. Then measure at three levels.

### 4.1 Compiler cost

- source bytes and functions per second;
- parse/check/IR-validation/lowering/code-emission time separately;
- peak resident memory;
- IR size and emitted text/object size;
- scaling curves for instruction count, blocks, functions and register count;
- cold and warm builds, with tool versions recorded.

### 4.2 Generated executable

- executable/object size and section breakdown;
- static instruction count for simple functions;
- register spills and stack-frame size;
- branch count and call overhead;
- startup/exit overhead;
- no-op, arithmetic, branch, loop and direct-call microbenchmarks.

### 4.3 End-to-end workloads

Use small deterministic workloads that can be run both by CCAM and native execution:
- arithmetic throughput;
- tight counted loop;
- branch-heavy loop;
- direct and nested calls;
- register pressure/spill stress;
- mixed arithmetic/control-flow workload.

For every benchmark:
- use fixed source/IR inputs and deterministic seeds;
- run a warm-up phase and at least 20 measured repetitions for initial comparisons;
- report median, p95 and dispersion, not only the fastest run;
- pin optimisation level, target triple, toolchain version and host;
- keep raw samples and the exact generated binary hash;
- report compile-time and run-time separately.

The existing C benchmarks are useful context, but do not compare unlike semantics or use C performance as a correctness gate. A C comparison becomes meaningful only when both programs implement the same work and checked/trapping behaviour.

### 4.4 Performance regression gates

Do not set arbitrary thresholds before a stable baseline exists. Initially publish results without failing CI. After enough stable CI history:
- set per-workload regression limits based on observed noise;
- use robust medians and repeated-run thresholds;
- keep a size/code-quality budget as well as speed;
- require every optimisation to pass the full differential suite;
- retain a `--no-opt` or unoptimised path for diagnosis and assurance.

## 5. Optimisation order and proof obligations

Suggested order:
1. Correct direct lowering with fixed stack slots and conservative register use.
2. Local instruction selection that has an obvious one-step correspondence.
3. Liveness analysis and register allocation.
4. Spill/reload insertion.
5. Basic-block layout and branch shortening.
6. Constant folding and dead-code elimination only after a typed-IR semantics and pass-validation framework exist.

For each pass, document:
- source/target invariants;
- preservation of value types and security/effect annotations;
- preservation of observable outcomes and trap locations (or an explicitly approved source-location mapping);
- preservation of deterministic resource accounting, or an explicit statement that the pass changes the machine's cost model and therefore is not semantics-preserving;
- translation validation or a machine-checked simulation proof;
- adversarial and property-based tests.

An optimisation must never remove a checked operation merely because the target instruction happens to wrap, trap differently, or exploit host flags. Checked arithmetic must be lowered to a sequence with the exact CCAM outcome.

## 6. CI stages

**Per commit (fast):**
- typed-IR structural validation tests;
- all fixed CCAM conformance vectors;
- native-vs-CCAM differential corpus;
- malformed-IR rejection corpus;
- backend encoding/ABI smoke tests;
- deterministic output test.

**Nightly (extended):**
- seeded property-based generation and mutation fuzzing;
- sanitizer runs for any C/C++ tooling in the temporary build path;
- larger resource/DoS corpus;
- all benchmark workloads with raw data retained;
- multiple optimisation levels and available host toolchains.

**Before release or backend promotion:**
- full differential corpus with preserved seeds;
- target-specific ABI and object-format checks;
- reproducible build from clean environment;
- review of TCB delta and assurance claims;
- proof/translation-validation evidence for every enabled optimisation.

The CI must distinguish `not run`, `failed`, `passed`, and `not applicable`. A missing run is never a pass.

## 7. Promotion gates

A native backend is not promoted beyond prototype until:
1. CCAM's relevant instruction semantics and evaluator are stable and reviewed.
2. Structural validator rejects the negative corpus before code generation.
3. All fixed and generated well-typed programs agree with CCAM.
4. Trap identity, order and deterministic limits agree.
5. ABI, stack and register preservation tests pass.
6. Fuzzing has a documented campaign duration/seed corpus and no unresolved crash or mismatch.
7. Build outputs are reproducible for fixed toolchain inputs.
8. Every remaining trusted component is documented.
9. Formal verification claims accurately distinguish proved, tested, reviewed and assumed properties.

## 8. Known gaps in the current CCAM v0.1 slice to resolve before backend implementation

These are specification/test questions, not alternative semantics proposed by the compiler workstream:

- Define exact structural validation rules, including duplicate function names, invalid type tags, entry signature, call destination/return compatibility, and path-sensitive fall-through.
- Specify the permitted trap-code set and whether arbitrary trap reasons are valid.
- Define whether the step counter increments for a call/return instruction once, and whether validation itself consumes no execution steps.
- Define whether maximum call depth counts the entry frame.
- Clarify whether a caller's destination is validated at call time and whether a non-void callee must always produce a value on every path.
- Specify source-location metadata and how it is preserved through lowering.
- Confirm how malformed program descriptions are represented in the Capstan-native implementation; the document's JSON notation must not imply a required JSON runtime or host parser.
- Ensure type mismatch is checked before or after initialisation in a way that is explicit and tested; tests must cover both uninitialised wrong-type reads and initialized wrong-type reads.
- The current register substrate's negative tests should include unknown declared type tags, empty/invalid signatures, out-of-range writes, and initialized wrong-type reads.

These items should be resolved by the CCAM/semantics owner and reflected in the normative CCAM spec and shared vectors before backend code relies on them.
