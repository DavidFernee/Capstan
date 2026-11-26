# C-free execution and formal verification programme

**Status:** Proposed architecture, for review  
**Programme:** post-v0.6 architectural work (provisionally v0.7)  
**Branch:** `architecture/c-free-formal-foundation`

## 1. Decision sought

Capstan's long-term execution path must not generate C or require a C compiler or C runtime. Capstan source should ultimately compile directly to a defined execution target (native machine code and/or a separately specified portable target), with the compiler, standard library and runtime implemented in Capstan and covered by the language's guarantees.

This is consistent with the existing design-map's stated "Capstan all the way down" goal. It makes that goal an architectural constraint rather than leaving C as the implicit permanent backend. This document does **not** yet select a final native ABI, object format, instruction set, garbage collector, proof assistant or bootstrap chain.

## 2. Terminology and scope

"C-free" means C is absent from the compiler's generated output and from the trusted execution path. It does not automatically mean that every dependency is written in Capstan: operating-system interfaces, firmware, hardware, and explicitly isolated foreign components remain external trust boundaries. The programme must inventory and minimise those boundaries, and state them honestly.

"Direct from Capstan" is the end-state: Capstan source is compiled to the chosen target without a C translation stage. It does not require us to skip a small, formally specified intermediate representation or reference abstract machine. An IR is useful precisely because it gives the compiler and proofs a stable semantic boundary.

The programme covers:
- source-language static and dynamic semantics;
- compiler lowering and correctness;
- runtime services (allocation, collection, strings, collections, secrets, checks, scheduling as later applicable);
- target code generation, ABI and host/OS interface;
- bootstrap, reproducible builds and the trusted computing base;
- security properties currently implemented across the compiler and C runtime.

It does not authorise an immediate rewrite of the v0.6 runtime or changes to work owned by other contributors.

## 3. Proposed architecture

The target pipeline is:

```
Capstan source
    |
    v
lexer / parser / name and type checking
    |
    v
typed, explicitly specified Capstan IR
    |
    +----> reference abstract machine / bytecode interpreter (proof and test oracle)
    |
    +----> verified lowering and native code generation
                    |
                    v
              target machine code
                    |
                    v
          narrow OS / platform interface
```

The reference abstract machine is an assurance tool and initial executable semantics, not a commitment that the production runtime must permanently be an interpreter. The eventual production route should be selected after measuring portability, performance, debuggability, proof complexity and TCB size. A bytecode VM may remain a supported target if it offers a material benefit.

The IR must preserve relevant source distinctions (including taint, secrets, capabilities/grants, checked arithmetic and resource bounds) until the stage that enforces each property. No lowering pass may silently erase a security invariant.

## 4. Architecture principles

1. **No C backend in the end-state.** No generated C, C runtime, or C compiler is required to build or run ordinary Capstan programs.
2. **Small semantic core.** Specify the smallest useful core language and abstract machine first; desugar surface syntax into it.
3. **Proof boundary before optimisation.** Define an unoptimised semantics and prove each optimisation preserves observable behaviour and safety.
4. **Explicit trust boundaries.** Enumerate compiler, runtime, code generator, assembler/linker, OS, hardware, crypto implementations and foreign components. Do not imply that a proof covers an unverified dependency.
5. **Security properties survive lowering.** Taint, secret handling, capability checks, resource limits and memory safety are semantic obligations, not merely front-end diagnostics.
6. **No unsound bootstrap assumption.** Self-hosting is not evidence of correctness. Record the bootstrap chain and establish reproducible correspondence between stages.
7. **Evidence-led claims.** Distinguish machine-checked theorems, tested properties, reviewed assumptions and unverified platform behaviour.
8. **Keep v0.6 stable.** The existing C backend remains a temporary comparison oracle until a replacement is demonstrably conformant; it is not the foundation of the new design.

## 5. Formal verification workstream

The initial proof assistant is an open decision. Lean 4 and Isabelle/HOL are candidates; evaluate them against the required metatheory, executable extraction, proof maintenance, contributor familiarity and CI integration before selecting one.

The proof plan is layered:

### L0 — Core language
Define syntax, values, environments, stores, typing judgments, evaluation and runtime errors. State evaluation order and integer semantics precisely.

### L1 — Type and memory safety
Prove progress and preservation for the core. State and prove heap invariants, object reachability/ownership assumptions, bounds safety and absence of invalid memory operations in the abstract machine.

### L2 — Security semantics
Formalise taint propagation and validator/escaper transitions; secret observation and destruction guarantees; capability/grant provenance, binding and revalidation; and relevant non-interference properties. State exactly which side channels (for example, timing and length) are out of scope.

### L3 — Compiler correctness
Prove or establish a compositional simulation between source evaluation and IR/abstract-machine execution. Every transformation and optimisation must have a correctness argument. The theorem's assumptions about the target and runtime must be explicit.

### L4 — Native backend and platform boundary
Specify the target subset and ABI. Prove lowering correctness where feasible; otherwise isolate and document the trusted code generator, assembler/linker and platform assumptions. Add differential, fuzz, translation-validation and reproducible-build evidence.

### L5 — Bootstrap and self-hosting
Specify each bootstrap stage, compare independently built outputs, and show that the self-hosted compiler implements the same specified compiler semantics. A self-hosting fixpoint alone is not a proof.

## 6. Migration stages and gates

| Stage | Deliverable | Exit gate |
|---|---|---|
| A. Baseline | Inventory current compiler, generated C, runtime, platform dependencies and security invariants | Every current runtime guarantee maps to a proposed semantic or trusted boundary |
| B. Core specification | Core syntax, typing, evaluation and abstract machine | Reviewed specification with executable examples and unambiguous error semantics |
| C. Reference machine | Small interpreter for the abstract machine | Conformance tests, differential harness and deterministic execution |
| D. Proof foundation | Machine-checked core safety theorems | CI builds proofs; assumptions and admitted results are disclosed |
| E. Compiler/IR | Typed IR and lowering pipeline | Source-to-IR semantic preservation evidence |
| F. Native target | Direct native code generation and runtime services | No C in the build/run path; target-specific tests and correctness evidence |
| G. Self-hosting | Capstan compiler/runtime components | Reproducible bootstrap and documented TCB |
| H. Retirement | Remove temporary C backend/runtime dependencies | Full conformance and security gates pass without C |

No stage authorises removing the old backend until its replacement passes the agreed conformance and security gates.

## 7. Immediate work

1. Complete the inventory of the current compiler and runtime, including generated-C contracts and platform-specific code.
2. Extract a list of semantic guarantees from `docs/SPEC.md`, `docs/DESIGN-MAP.md`, conformance tests and runtime tests.
3. Resolve architectural choices: abstract machine vs IR boundary; bytecode representation; native target(s); memory model and GC strategy; OS ABI; proof assistant.
4. Write the core-language and abstract-machine specification before implementing a substantial replacement.
5. Establish a separate coordination lane and keep changes to shared roadmap/specification files coordinated through issue #25.

## 8. Open decisions (not yet settled)

- Lean 4 vs Isabelle/HOL (and whether another assistant merits evaluation).
- Typed SSA-like IR vs stack/register bytecode as the primary compiler IR.
- Whether the abstract machine's reference interpreter is temporary or a supported deployment target.
- First native target and supported operating systems/architectures.
- Runtime memory representation, GC design, secret storage and zeroisation contract.
- Whether a formally verified small code generator is feasible, or whether translation validation is the first practical native-code assurance boundary.
- Exact treatment of external crypto, libc-like services, syscalls and platform runtimes.

## 9. Non-goals and safeguards

- No immediate rewrite of the active v0.6 runtime.
- No claim that the language is formally verified merely because a proof assistant is introduced.
- No claim that generated machine code is verified until the compiler-to-target argument covers it.
- No silent weakening of current security guarantees to simplify the new backend.
- No direct merge to `main`; work proceeds through review and required CI.

## 10. Acceptance criteria for the programme

The programme is successful when ordinary Capstan programs can be built and executed without a C compiler, generated C or a C runtime; the compiler, standard library and runtime are implemented in Capstan to the extent set by the agreed bootstrap design; the language and execution semantics have machine-checked safety results; compiler transformations have explicit correctness evidence; and every remaining trusted component and assumption is documented.


## Appendix A. Initial repository baseline (2026-11-24)

This is a first-pass inventory from the current `main` tree, not yet a line-by-line audit.

### Observed build and bootstrap chain

- `compiler/codegen.cap` is explicitly a C code generator. It lowers Capstan types to C representations (for example, `int64_t`, `CapStr*`, `CapList*`, `CapMap*`, `CapGrant*`) and emits calls into the runtime.
- `runtime/capstan_rt.h` is the generated program's runtime interface. Its opening contract states that every compiled program is C calling this header; it includes C and POSIX headers and delegates allocation to `capstan_gc.h`.
- `Makefile` uses `CC` (default `cc`) and builds generated C with the host compiler. The self-hosted compiler is built through generated C.
- The bootstrap chain is not yet a verified chain: `bootstrap/capstan0.py` is a small unchecked Python translator; it produces a Python-hosted stage 1 compiler, which emits C; the C compiler creates stage 2; stage 2 emits stage 3 C, and the fixpoint checks byte-for-byte equality of stage 2 and stage 3 output.
- The README documents the same chain and explicitly lists a C compiler and Python 3 as build requirements.

### Assurance implications

- The byte-for-byte self-hosting fixpoint establishes a useful reproducibility/self-consistency property for the generated C, but does not establish that stage 0 is correct, that the generated C implements Capstan semantics, or that the C compiler/runtime/host ABI are correct.
- The new programme must therefore treat the Python stage-0 translator, generated-C compiler, C runtime, C compiler, linker and relevant platform interfaces as distinct baseline trust components. Their roles should be retired or narrowed deliberately, not hidden by the self-hosting label.
- The current runtime header includes process termination, stdio, allocation and POSIX interfaces. These need to be classified as language semantics, runtime policy, or OS boundary services in the new design.
- The existing C backend is useful as a differential oracle, but agreement with it is not a formal oracle: shared bugs and backend-specific behaviour remain possible. The written specification and independent reference machine must become the semantic authority.

### Immediate inventory follow-up

The next baseline pass should enumerate:
1. every emitted C construct and runtime symbol used by `compiler/codegen.cap`;
2. all runtime headers and implementation files, including GC, secrets, crypto, file/process/SQL and platform-specific code;
3. all build, test, fuzz, sanitizer, benchmark and release workflows that assume C/Python;
4. each security claim and its current enforcement location (front end, generated checks, runtime, OS/library);
5. the minimum supported target matrix and ABI assumptions.

This inventory is required before selecting the first native target or estimating the size of the replacement runtime.


## Appendix B. Capstan-native implementation rule

The initial Python reference-machine implementation has been removed. It was the
wrong implementation boundary for this programme: an executable prototype in a
second implementation language would make the intended self-hosted transition
less direct and create a parallel artefact to maintain.

The CCAM specification remains as a language-neutral description, but its
executable implementation and conformance tests are required to be Capstan
source from the first implementation. The existing bootstrap may temporarily
execute Capstan source through the current compiler/C path; that is solely a
bootstrap mechanism and must not be mistaken for the target architecture.

No Python or C interpreter/runtime for CCAM is to be introduced. The next
implementation increment is a Capstan-native, typed CCAM representation and
small evaluator, with Capstan-written positive and negative tests. Only after
that vertical slice is running should the machine be extended to heap,
collections, taint, secrets, grants, and IO.


## 11. Compiler memory profile integration

The compiler's memory requirements and the separate frame-scoped scratch-memory work are reconciled in [C-Free compiler memory integration review](C-FREE-MEMORY-INTEGRATION-REVIEW.md). The review distinguishes a process-lifetime typed compiler arena from frame-owned scratch regions; neither is promoted to normative CCAM semantics by that document.
