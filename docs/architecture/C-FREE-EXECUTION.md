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
