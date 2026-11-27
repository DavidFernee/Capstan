# Native Compiler Research Update — 2026-11-27

**Scope:** Compiler architecture, optimisation validation, native backend assurance and security-preserving compilation  
**Repository:** Capstan  
**Status:** Research-informed design input; not an implementation claim

## 1. Executive assessment

The current architecture is directionally sound only if CCAM remains the single semantic authority, native lowering is treated as a correctness-critical compiler in its own right, and each compiler run can increasingly be checked independently.

Recent work strengthens three requirements that should be explicit in Capstan:

1. **Continuous, optimisation-directed validation.** General random fuzzing is not enough. Generate programs that trigger a particular optimisation, capture before/after IR, and validate each transformed result.
2. **Backend validation must include ABI and machine-state constraints.** Register allocation, instruction selection, stack layout and calling conventions are not merely mechanical final steps; they are another optimiser with miscompilation risk.
3. **Architectural equivalence is not confidentiality preservation.** For secret-bearing programs, compiler passes need a separate leakage/noninterference argument under an explicit attacker and microarchitectural observation model.

A separate certifier/validator is a practical route for a compiler that is actively changing. It can add assurance incrementally without requiring the entire production compiler to be rewritten inside a proof assistant.

## 2. Research findings and architectural consequences

### 2.1 Optimuzz — optimisation-directed fuzzing plus translation validation

Jaeseong Kwon, Bongjun Jang, Juneyoung Lee and Kihong Heo, “Optimization-Directed Compiler Fuzzing for Continuous Translation Validation,” *Proceedings of the ACM on Programming Languages*, 9 (PLDI), Article 172, June 2025. DOI: https://doi.org/10.1145/3729275.

The paper combines directed grey-box fuzzing with translation validation to trigger specific optimisations in LLVM and V8 TurboFan. The authors report finding 55 previously unknown LLVM miscompilation bugs.

**Capstan consequence:** build an optimisation registry and a pass-directed test generator. Each pass must expose a stable identity, preconditions and expected IR pattern. The harness must:
- generate or mutate source/CCAM inputs to activate that pass;
- preserve the exact pre-pass and post-pass representation;
- run the independent validator on the pair;
- compare complete observable outcomes with the CCAM reference evaluator;
- retain counterexamples, minimized reproductions and pass metadata;
- fail closed when validation is unknown, times out or exceeds its work budget.

This is a stronger and more actionable programme than undirected fuzzing alone. Fuzzing discovers interesting cases; validation decides whether the particular transformation is accepted under the formal relation.

### 2.2 ARM-TV — native backend translation validation

Ryan Berger et al., “Translation Validation for LLVM's AArch64 Backend,” *Proceedings of the ACM on Programming Languages*, 9 (OOPSLA2), October 2025. DOI: https://doi.org/10.1145/3763147.

The work validates translations from LLVM IR to AArch64 machine code, explicitly covering backend concerns and ABI rules. It reports 46 previously unknown backend miscompilation bugs.

**Capstan consequence:** do not treat native code generation as a trusted final printer. The native backend needs a machine-level validator or proof relation covering:
- instruction selection and legal encodings;
- register allocation, spills and live-value preservation;
- stack-frame layout, alignment and saved-register obligations;
- call/return and argument/result ABI;
- relocations and symbol resolution;
- trap paths and runtime helper contracts;
- object section permissions and entry-point policy.

The first Linux x86-64 target should have its own machine semantics and ABI validator. A future AArch64 backend must not inherit x86 assurance merely because both consume CCAM.

### 2.3 SNIP — speculative noninterference can be broken by compilation

Sören van der Wall and Roland Meyer, “SNIP: Speculative Execution and Non-Interference Preservation for Compiler Transformations,” *Proceedings of the ACM on Programming Languages*, 9 (POPL), Article 51, January 2025. DOI: https://doi.org/10.1145/3704887.

The paper develops a simulation method for preserving noninterference under speculative semantics. Its analysis found a register-allocation weakness that could violate noninterference and confirmed the issue on mainstream compiler output involving libsodium code.

**Capstan consequence:** ordinary functional equivalence is not sufficient for claims about secret handling or constant-time execution. The architecture must distinguish:
- architectural functional correctness;
- language-level information-flow/noninterference;
- microarchitectural or speculative leakage properties.

A secret/constant-time assurance profile needs an explicit attacker model, observable-event model, speculation assumptions and relational proof obligations. Register allocation, spills, instruction selection, scheduling and memory layout must be in scope. Do not claim constant-time or speculative noninterference merely because the source checker tracks secret values or because the native output is functionally equivalent.

### 2.4 A Layered Certifying Compiler Architecture

Jacco O.G. Krijnen, Wouter Swierstra, Manuel Chakravarty, Joris Dral and Gabriele Keller, “A Layered Certifying Compiler Architecture,” FUNARCH 2025. DOI: https://doi.org/10.1145/3759163.3760427.

The work presents a certifier that validates individual compiler runs using layered pass specifications, a trace interface, decision procedures and semantic-preservation proofs. It demonstrates an incremental approach for a compiler under active development.

**Capstan consequence:** the assurance programme should not wait until the entire compiler is formally verified. Add a compilation trace with exact canonical before/after snapshots for each pass, stable pass identifiers and pinned compiler/build identities. Build a separate Lean checker/certifier incrementally. The trace printer/parser becomes an explicit, small TCB component and must have canonical encoding and round-trip tests. Certificates must bind the exact source, CCAM profile, pass trace, target ABI and final executable digest.

## 3. Architecture changes required

The architecture RFC should make these requirements explicit:

1. **One semantic authority:** checked source lowers directly to CCAM; any SSA/CFG optimiser is optional, derived and validated/refined back to CCAM.
2. **Pass registry:** every transformation has a stable ID, version, input/output contract, preconditions, proof/validator status, deterministic resource budget and targeted regression corpus.
3. **Compilation trace:** record canonical pass inputs/outputs and enough provenance to bind a certificate to the exact compilation run.
4. **Independent translation validator:** validators must be isolated from optimisation producers and must reject unknown, timed-out or over-budget cases.
5. **Backend correctness boundary:** include native machine semantics, ABI, register allocation, spills, stack layout, relocations and traps.
6. **Security refinement:** confidentiality and speculative/constant-time guarantees require relational models distinct from ordinary functional refinement.
7. **Evidence levels:** distinguish tested, fuzzed, translation-validated, formally proved and artifact-certified. Do not collapse these labels.

## 4. Limits and cautions

- Optimuzz and ARM-TV are evidence that validation plus targeted testing finds real defects; they do not prove that Capstan's own proposed validators are sound.
- A validator is useful only if its specification is semantically sound and the implementation is proved equivalent to that specification or belongs to a small, independently audited trusted base.
- A bounded solver or validator timeout must yield “unknown/rejected,” not success.
- Functional translation validation does not automatically establish timing, cache, speculative or power noninterference.
- A reproducible build establishes identity/reproducibility, not semantic correctness.
- CakeML and CompCert demonstrate the value of layered, proof-linked compiler pipelines, but copying their number of IR stages is not itself a design objective. Every Capstan representation must justify its cost and proof boundary.

## 5. Recommended next engineering work

1. Add a stable pass registry and canonical compilation-trace schema.
2. Define a small CCAM-to-native machine simulation interface for the current x86-64 subset.
3. Add an independent x86-64 ABI/stack/register/relocation validator before broadening backend instruction coverage.
4. Add pass-directed fuzzing for the current lowering and native codegen operations.
5. Specify a separate secret/noninterference profile before advertising constant-time guarantees.
6. Keep the initial compiler vertical slice direct and small; add optional SSA only when an optimisation has a measurable benefit and a validator/refinement contract.

## 6. Bibliography

- Kwon, J., Jang, B., Lee, J. and Heo, K. (2025). Optimization-Directed Compiler Fuzzing for Continuous Translation Validation. *PACMPL 9 (PLDI)*, Article 172. https://doi.org/10.1145/3729275
- Berger, R. et al. (2025). Translation Validation for LLVM's AArch64 Backend. *PACMPL 9 (OOPSLA2)*. https://doi.org/10.1145/3763147
- van der Wall, S. and Meyer, R. (2025). SNIP: Speculative Execution and Non-Interference Preservation for Compiler Transformations. *PACMPL 9 (POPL)*, Article 51. https://doi.org/10.1145/3704887
- Krijnen, J.O.G. et al. (2025). A Layered Certifying Compiler Architecture. *FUNARCH 2025*. https://doi.org/10.1145/3759163.3760427
- Norrish, M. (2018). The verified CakeML compiler backend. *Journal of Functional Programming*. https://doi.org/10.1017/S0956796818000229
