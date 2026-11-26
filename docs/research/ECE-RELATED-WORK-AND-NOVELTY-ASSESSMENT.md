# Evidence-carrying execution: related work and novelty-risk assessment

**Status:** targeted state-of-the-art review and research recommendation; no novelty or implementation claim  
**Issue:** [#220](https://github.com/DavidFernee/Capstan/issues/220)  
**Reviewed:** 2026-11-26  
**Repository baseline:** current main at review time  
**Coordinates:** [Evidence-Carrying Execution proposal](EVIDENCE-CARRYING-EXECUTION.md), [ECE proof/implementation obligations](EVIDENCE-CARRYING-EXECUTION-OBLIGATIONS.md), [research register](RESEARCH-REGISTER.md), [programming-language research agenda](PROGRAMMING-LANGUAGE-RESEARCH-AGENDA.md)

## 1. Executive finding

The core ingredients in Capstan's Evidence-Carrying Execution (ECE) proposal are established research areas:

- Proof-carrying code (PCC) and certifying compilation already let an untrusted producer attach a proof or target-level annotations that a smaller consumer-side checker validates against a published safety policy.
- Foundational PCC already studies machine-code semantics and proof checking from a small logical foundation.
- Translation validation already checks each individual compilation result against a source/target semantic relation, avoiding the need to prove the compiler correct in advance.
- CompCert and CakeML demonstrate substantial mechanically verified compiler pipelines, including verified backends and, for CakeML, a verified implementation/bootstrapping chain.
- Proof-carrying data (PCD) extends proof propagation across distributed computation histories; notably, prior work explicitly applies PCD to enforcing language semantics in distributed computations.
- SLSA/in-toto and related software attestations already bind authenticated provenance and verification metadata to software artefacts, but they do not establish semantic correctness or memory safety.

Therefore, a broad claim that Capstan is novel because it combines compiler provenance, proofs, capability grants and resource bounds in an executable bundle is not defensible by itself. PCC's safety policy can already express combinations of predicates; verified compilers already establish source-to-target semantic preservation; PCD already carries proofs of computation history; and software attestations already package authenticated provenance.

The potentially distinctive research question is narrower: **can a small, independently implemented, bounded checker validate a versioned certificate bound to an exact canonical Capstan program, semantics, authority manifest and resource contract, while the evidence chain separately establishes evaluator/adapter refinement and the checker remains materially smaller and simpler than the producer?**

That is an engineering/research integration hypothesis, not an established novelty claim. It becomes publishable only if the certificate model, proof obligations, implementation boundary and empirical costs are compared directly with PCC/certifying compilers, translation validation, verified compiler pipelines and PCD.

## 2. Review method and scope

This is a targeted review of primary papers, formal developments and official standards/documentation located on 2026-11-26. It is not a systematic literature review: no exhaustive bibliographic database search, screening protocol or independent citation audit was performed. Sources were selected to cover classical PCC, certifying compilers and typed assembly, foundational proof checking, translation validation, verified compiler construction, PCD, and current software provenance/attestation standards.

The review distinguishes:
- evidence about **what a program is allowed to do** from evidence about **how an artefact was built**;
- a proof about a source/target semantic relation from a proof of a target-level safety predicate;
- a certificate from a signature or provenance statement;
- a compiler that emits a proof from a compiler whose own implementation is formally verified;
- local executable validation from cryptographic proofs about a distributed computation history.

## 3. Taxonomy

| Family | Producer output | Consumer/checker verifies | Principal trust boundary | Does not automatically establish |
|---|---|---|---|---|
| Proof-carrying code | Code plus formal proof | Target code satisfies a consumer-defined safety policy | Proof checker, logic, policy, machine semantics | Source-level functional correctness or compiler refinement unless included in policy/proof |
| Certifying compiler / typed assembly | Target code plus types/annotations/certificate | Target-level type/safety invariants | Certifier/checker, target language semantics | That target implements intended source semantics |
| Foundational PCC | Machine code plus proof in a foundational logic | Safety theorem derived from low-level machine semantics | Small proof kernel and foundational model | Correctness of unmodelled hardware/OS/FFI |
| Translation validation | One compilation result and a validation relation/proof | This particular translation preserves the chosen semantics | Validator, source/target semantics, correspondence method | A general theorem for all compiler runs; all non-semantic safety properties |
| Verified compiler | Compiler implementation plus machine-checked pass-correctness proofs | Compiler passes preserve semantics under stated assumptions | Proof assistant kernel, models, compiler/bootstrapping assumptions | Correctness of external runtime/OS/FFI outside theorem |
| Proof-carrying data | Messages/results plus proofs of invariants over their history | Each message and computation history satisfy a predicate | Proof system, cryptographic assumptions, verifier | Local binary memory safety or source-to-machine compiler correctness unless encoded |
| Software provenance/attestation | Signed/authenticated metadata about source/build/artifact | Provenance and policy claims are authentic and correctly bound | Signing identity, build platform, attestation verifier | Semantic correctness, type safety or absence of vulnerabilities |

These systems overlap, but they are not synonyms. A robust ECE design may compose them; it must not describe one evidence class as if it supplied the others.

## 4. Proof-carrying code and certifying compilation

### 4.1 Classical PCC

Necula's *Proof-Carrying Code* (POPL 1997) establishes the core producer/consumer model. The consumer publishes a safety policy. An untrusted producer supplies native code together with a formal proof that the code respects that policy. The consumer checks the proof before execution. The design moves expensive proof construction to the producer and keeps the consumer-side checker comparatively simple.

The important design choice is that the **consumer defines the policy**. The producer does not get to decide which properties are sufficient. The proof must be checked against the consumer's policy and the exact code being executed.

PCC's strengths are also its constraints:
- It can express a safety property that the logic and proof system can state.
- The producer may be sophisticated or untrusted, provided the proof checker is sound.
- The code and proof must be bound together; a proof for different code is irrelevant.
- The checker, safety policy, proof logic and machine semantics remain trusted.
- Proof generation and proof size can be expensive; a practical certificate format and checker are central engineering problems.

PCC is not limited to memory safety in principle. Consequently, Capstan cannot claim novelty simply by placing authority and resource predicates into a safety policy. It must show a useful, compositional and independently checkable construction that existing PCC systems do not already provide.

### 4.2 Certifying compilers and typed assembly

Necula and Lee's *The Design and Implementation of a Certifying Compiler* (PLDI 1998) demonstrates a compiler that emits optimised DEC Alpha assembly together with target-level evidence. An independent certifier checks type and memory safety of the generated assembly, without needing to trust the compiler's internal implementation for that property. The result is a proof or a counterexample.

Typed Assembly Language (TAL) provides a related foundation: target-level types can encode invariants about registers, stack, memory, closures and control flow. TALx86 work studies realistic native code and certificate-size/checking-time trade-offs. The 2000 work on scalable certification reports that type abbreviation, common-subexpression elimination and selective re-verification can reduce annotation size and checking cost by large factors.

**Implication:** a certificate should be designed around a small target-level accepted-program predicate, not a transcript of every internal compiler step. However, target-level type safety is not source-to-target semantic correctness. If Capstan wants a claim that a CCAM artefact means what its source program means, it needs a separate lowering simulation or translation-validation/refinement proof.

### 4.3 Foundational PCC

Appel and Felty's semantic model of types and machine instructions, Appel's Foundational Proof-Carrying Code work and related developments push the safety argument down to a foundational logic and machine semantics. This reduces reliance on an informal or separately trusted type-safety argument for the target machine language.

The approach makes the trusted base explicit rather than eliminating it. The proof checker/kernel, logical axioms, machine semantics and assumptions about the real processor remain part of the assurance boundary. A proof about an idealised instruction semantics does not automatically cover caches, speculative side channels, device behaviour or OS services unless those are in the model.

## 5. Translation validation

Pnueli, Siegel and Singerman's work (TACAS/ICALP 1998) introduced translation validation as an alternative to proving a compiler correct once and for all: each individual compilation run is followed by a validation phase checking that the generated target correctly implements the submitted source.

Necula's *Translation Validation for an Optimizing Compiler* (PLDI 2000) demonstrates this for a realistic GNU C compiler infrastructure. The validator compares intermediate representations around compiler passes and checks semantic preservation. The reported system could validate many optimisations in realistic programs, but also had a measurable compilation-time cost and occasional false alarms when the validator could not explain a transformation.

**Strengths**
- Evidence is specific to the exact compilation result.
- The compiler can evolve without re-proving its entire implementation, provided the validator still understands the output.
- It localises miscompilation evidence to a particular translation.
- A proof/validation artefact can be bound to the source and target hashes.

**Limitations**
- The validator becomes a trusted component; a bug or unsound abstraction in it defeats the result.
- Validation may fail or produce false alarms for transformations outside its supported model.
- The source/target semantic relation must be defined precisely.
- It proves only the properties included in the relation; it does not automatically prove capability confinement, resource accounting or host-adapter correctness.
- It is not a substitute for testing the decoder, certificate parser, policy implementation or runtime boundary.

For Capstan, translation validation is a strong comparator for the source-to-CCAM and CCAM-to-native links. ECE should not duplicate a compiler-correctness theorem inside a large opaque certificate if a narrower, per-artefact simulation certificate is easier to check.

## 6. Verified compilers and end-to-end implementations

### 6.1 CompCert

Leroy's CompCert work provides a mechanically verified compiler from CompCert C to multiple machine targets. Its correctness theorem states semantic preservation across the compiler pipeline under explicit source, target and environment assumptions. The current CompCert documentation records the proof development and supported targets.

CompCert demonstrates that a verified compiler is a substantial but practical alternative to trusting a general-purpose compiler. It also demonstrates the importance of exact semantics and target models.

It is not a proof-carrying executable format in the same sense as PCC: its principal assurance argument is that the compiler implementation has been verified. A consumer relying on CompCert still needs provenance that the executable was produced by the verified compiler and that the relevant compiler revision/configuration and assumptions apply.

### 6.2 CakeML

Kumar, Myreen, Norrish and Owens' CakeML work is especially relevant to Capstan's long-term C-free goal. CakeML has a machine-checked semantics and a verified compiler/implementation, including parsing, type checking, garbage collection, code generation and bootstrapping. Later compiler-backend work verifies a sequence of intermediate languages down to multiple machine targets.

CakeML shows that a self-hosting, end-to-end verified language implementation is established prior art. Capstan cannot claim novelty merely for a self-hosting compiler with a formal machine model or a staged compiler proof chain.

The relevant difference in research question is whether Capstan can make **per-program evidence** a first-class artefact that a smaller independent checker can validate, in addition to or instead of relying on one globally verified compiler implementation. These approaches can coexist: a verified compiler can emit a certificate, and a certificate checker can validate the accepted subset independently.

### 6.3 Proof-producing compilation versus verified compiler construction

These are different assurance strategies:

- A **proof-producing/certifying compiler** may be unverified, but emits a proof that a separate checker validates for each output.
- A **verified compiler** has a machine-checked proof about the compiler implementation and its semantics-preservation theorem.
- A **translation validator** checks one compilation result, using a separate relation/validator.
- A **tested compiler** has empirical evidence, but no theorem follows from test success alone.

A research paper must state which strategy it implements and which component remains trusted. Calling all four "verified compilation" obscures the critical differences.

## 7. Proof-carrying data and distributed evidence

Chiesa and Tromer's Proof-Carrying Data (PCD) work attaches proofs to messages in a distributed computation. Each proof attests not only to the message value but also to the computation history that produced it. The approach uses cryptographic proof systems and recursive composition so that components can verify properties of long-running distributed computations.

This is a significant novelty risk for Capstan. Chong, Tromer and Vaughan's *Enforcing Language Semantics Using Proof-Carrying Data* (2014) explicitly applies PCD to ensure that values received from potentially untrusted parties are well-traced with respect to language semantics. Therefore, the statement "Capstan carries proof that a computation followed language semantics" is not new without a much more precise distinction.

PCD differs from the initial Capstan ECE target:
- PCD is primarily a cryptographic, distributed-history mechanism; ECE initially targets a local executable/program plus a validated CCAM execution contract.
- PCD proofs can be recursively composed across parties/messages; ECE's first slice proposes a bounded checker over one canonical program and its declared evidence.
- PCD has cryptographic assumptions and potentially substantial prover/recursion costs; a conventional PCC/Lean proof checker has a different trust and performance profile.
- PCD can attest to arbitrary predicates over a computation history, but does not automatically provide a native-code safety policy or OS capability boundary.

Recent PCD work continues to improve proof accumulation and prover/verifier costs. A 2026 study of simulation-extractability for PCD also shows that cryptographic composition and malleability remain active research questions. Capstan should not introduce recursive SNARK/PCD machinery unless a distributed or incremental-verification use case requires it.

Authenticated data structures are another adjacent area: an untrusted server can return a result plus a compact proof that the result matches an authenticated data structure. This is useful for data integrity, but it is not compiler correctness or proof of program execution semantics.

## 8. Industrial provenance and software attestations

SLSA and in-toto provide standardised ways to record authenticated statements about software artefacts, including how an artefact was built, its source materials and relevant verification results. Sigstore and related signing infrastructure can authenticate provenance or release statements. These systems address supply-chain integrity, origin and policy evaluation.

They are not semantic proof systems:
- A signed statement can be authentic and still describe a vulnerable or incorrect build.
- A build provenance attestation establishes a claimed build process and its inputs, not that the generated executable implements the source semantics.
- A vulnerability scan/test attestation reports that a tool ran and what it reported; it does not prove the absence of vulnerabilities.
- A signature binds an identity/statement to bytes; it does not make the statement true unless its predicate is independently checked.

The SLSA attestation model itself distinguishes software attestations from remote attestation. ECE should reuse established provenance/attestation formats for build identity where practical rather than inventing a parallel supply-chain format. Semantic proofs and provenance statements should be separate typed records, cryptographically bound to the same immutable artefact digest.

## 9. Comparative literature matrix

| System / approach | Producer and evidence | Checker / trusted base | Binding and composition | Target coverage | Main limitation / implication for Capstan |
|---|---|---|---|---|---|
| PCC (Necula 1997) | Untrusted producer supplies code plus safety proof | Consumer-side proof checker, logic and policy | Proof must identify exact code and policy | Native code under a specified machine/safety model | Closest prior art for an independently checked ECE certificate |
| Certifying compiler / TALx86 | Compiler emits target code plus type annotations/proof | Small target type checker/certifier and target semantics | Target-level types encode machine invariants; modular annotations | Realistic assembly language | Type safety is not source semantic preservation |
| Foundational PCC (Appel/Felty) | Machine code plus proof in foundational logic | Small logical kernel and machine model | Strong low-level semantic grounding | Machine-level code in the formal model | Hardware/OS/FFI assumptions remain |
| Translation validation (Pnueli et al.; Necula) | Each compile run produces source/target pair and validation evidence | Validator, source/target semantics and proof method | Per-run semantic relation | Individual translations/optimisations | Validator may be incomplete; does not automatically cover runtime authority/resources |
| CompCert | Verified compiler implementation and pass proofs | Proof assistant kernel, semantics and compiler assumptions | Whole compiler pipeline theorem | Multiple machine targets | Global compiler assurance, not necessarily a per-program certificate format |
| CakeML | Verified language implementation, compiler, runtime and bootstrap | HOL4 kernel, machine semantics and environment/FFI assumptions | Composed end-to-end proof chain | Multiple native targets | Strong end-to-end prior art; large formal development |
| PCD | Cryptographic proofs attached to messages/computation histories | Cryptographic verifier and assumptions | Recursive/incremental history composition | Distributed computations | Different use case and trust model; explicit language-semantics PCD prior art exists |
| Authenticated data structures | Query result plus cryptographic authentication proof | Hash/signature/commitment verifier | Proof bound to data structure root/version | Data query/update operations | Data integrity is not code safety or compiler refinement |
| SLSA / in-toto attestations | Authenticated provenance/verification metadata | Signing identity, attestation verifier and policy | Signed statements bound to artefact/material digests | Build and software supply chain | Authenticity/provenance is not semantic truth |
| Capstan ECE proposal | Proposed canonical CCAM + validation, resource, capability and provenance evidence | Proposed small independent checker plus explicit runtime/host TCB | Bundle binds semantics, program digest, resource and capability evidence | Initially closed deterministic CCAM subset | Must demonstrate why the exact integration is useful beyond existing PCC/verified compiler/PCD systems |

## 10. Capstan baseline and gap assessment

The merged ECE proposal (#214) already identifies:
- a versioned semantics identifier and canonical program digest;
- validation, resource, capability and provenance evidence;
- an independent checker rather than trust in the producer;
- binding of certificates to program bytes, semantics, grants and resource limits;
- a staged proof/refinement chain from source through CCAM, evaluator, backend and host;
- explicit non-claims about the current C-backed pipeline.

The ECE obligations ledger correctly leaves key obligations open, including canonical encoding/decoder soundness, certificate-checker soundness, evaluator correspondence, resource semantics, capability algebra, authority inclusion, and proof/implementation refinement.

The current research register also states that Capstan is not yet an end-to-end verified C-free execution pipeline. Its CCAM model and evaluator cover selected fragments; the concrete multi-function evaluator and Lean model do not yet have a multi-frame refinement theorem; the native emitter is a narrow prototype. Those facts are important and must remain in the research framing.

### 10.1 What is already established elsewhere

| Capstan proposition | Prior-art status | Consequence |
|---|---|---|
| Untrusted producer supplies code plus proof; consumer checks before execution | Established by PCC | Not novel |
| Target-level typed annotations make machine code independently checkable | Established by certifying compilers/TAL | Not novel |
| Check each individual compilation output for semantic preservation | Established by translation validation | Not novel |
| Mechanically verify a realistic compiler pipeline and native code | Demonstrated by CompCert and CakeML | Not novel |
| Attach proofs to data/messages that attest to distributed computation history | Established by PCD | Not novel |
| Bind signed build provenance and test/scan statements to artefact digests | Established by SLSA/in-toto and related systems | Not novel |
| Combine a specific CCAM accepted-program predicate, capability requirements, resource ceilings and evaluator-refinement evidence into a versioned, bounded, independently checked artefact | Plausible integration hypothesis; not yet established by this review as novel | Requires direct comparison and an executable prototype |

### 10.2 What remains potentially underexplored

The review identifies a possible engineering contribution in the *boundary design*:
- one closed, canonical, bounded CCAM artefact;
- one explicit accepted-program predicate;
- evidence fields whose types distinguish model theorem, implementation refinement, runtime-enforced limit, host assumption and provenance;
- a small checker that verifies the exact artefact and policy without running the full producer or theorem prover;
- resource and authority contracts that are checked independently and then jointly composed at calls and host boundaries;
- an exact-revision evidence ledger and reproducible checker/validation cost measurements.

This is a candidate integration, not a claim that the combination is new. PCC's policy can be expressive; PCD can carry computation-history predicates; verified compilers can establish semantic preservation. The burden is to show that Capstan's chosen decomposition gives a useful reduction in checker TCB, certificate size/check time, modularity or operational deployment compared with these systems.

## 11. Recommended research question and falsifiable hypothesis

### Research question

For a closed deterministic CCAM subset, can Capstan define a canonical, versioned evidence bundle whose compact certificate is independently checked against the exact program bytes, semantics identifier, resource contract and capability requirements, while a separate refinement theorem connects the concrete evaluator to the reference machine?

### Hypothesis H-ECE-1

A producer-independent, bounded checker can validate the selected CCAM subset's structural/type/authority/resource acceptance facts from a compact certificate, with lower trusted-code complexity than trusting the producer's full compiler/validator pipeline, while preserving an explicit separation between (a) model-level proof, (b) implementation refinement, (c) runtime-enforced ceilings and (d) host assumptions.

This hypothesis is falsified if:
- the checker must trust the producer's acceptance decisions or reuse the producer's complex analysis code;
- certificate parsing is unbounded, non-canonical or can be made to accept stale evidence after a program/semantics/policy mutation;
- accepted certificates do not imply the exact formal accepted-program predicate;
- authority or resource claims are not bound to the exact launch configuration;
- the concrete evaluator can produce an outcome outside the reference semantics under the stated refinement assumptions;
- checker size, certificate size or verification time is not meaningfully improved over simpler alternatives on the selected subset.

### 11.1 Smallest discriminating experiment

1. Freeze one closed, deterministic CCAM subset and a versioned canonical input encoding.
2. Define the accepted-program predicate in Lean, including bounded structural validation, typed register operations, control flow, fuel/call-depth and the initial explicit authority/resource requirements.
3. Implement a small independent Capstan-native certificate checker. The compiler/producer may be untrusted; the checker must not call the producer's internal validator to decide acceptance.
4. Generate certificates for valid programs and mutation/negative vectors for invalid programs.
5. Bind the certificate to the canonical program digest, semantics identifier, capability manifest and resource contract. Mutate each field independently and require stale evidence rejection.
6. Prove checker soundness against the formal accepted-program predicate. Separately prove or establish the concrete evaluator's simulation/refinement relation to the reference machine.
7. Measure certificate size, checker code size, validation time/memory, producer time, rejection precision and the cost of revalidation without a certificate.
8. Compare against: (a) re-running the full validator, (b) a verified-compiler/translation-validation approach for the same subset, and (c) a provenance-only attestation that makes no semantic claim.

The initial experiment must stop at validated CCAM evaluation. Source-to-CCAM and native-backend refinement are later milestones. A certificate that proves only that an input is structurally well-formed must not be advertised as proving source semantics, resource compliance of the native runtime, or capability confinement by the OS.

## 12. Open questions and research risks

1. **Certificate form:** proof term, derivation tree, abstract-analysis witness, target type annotation, or a hybrid? The simplest checkable representation should win.
2. **Canonical encoding:** how are duplicate fields, unknown fields, integer widths, field order, Unicode, hash domains and version upgrades handled?
3. **Checker logic:** Lean kernel replay, a separately verified checker, a small trusted Capstan checker, or two independent checkers? Each has a different TCB.
4. **Proof binding:** which evidence is bound to CCAM bytes, and which evidence is bound to source, compiler, target binary, policy and runtime configuration?
5. **Dynamic obligations:** how are residual host checks, live resource leases, timeouts and platform assumptions represented without implying they were statically proved?
6. **Capability lifecycle:** how are creation, attenuation, delegation, expiry and revocation evidenced? A manifest is not proof that the OS adapter enforces it.
7. **Incremental changes:** can certificates be reused after local program edits, or must any semantic/policy change force full regeneration?
8. **Proof size and checking cost:** what is the practical threshold at which a certificate is preferable to recomputing validation?
9. **Trusted computing base:** include parser, hash, proof kernel, compiler, OS adapter, runtime, allocator, scheduler, toolchain, build platform and hardware assumptions.
10. **Threat model:** distinguish malicious producer, malformed artefact, compromised build platform, compromised host adapter, malicious OS, hardware fault and side-channel adversary.
11. **Distribution:** if ECE later crosses process/host boundaries, determine whether conventional certificates suffice or whether PCD/recursive cryptographic proofs solve a real need.
12. **Standards reuse:** use SLSA/in-toto provenance and established signing formats where possible; do not conflate their authenticated metadata with semantic proofs.

## 13. What Capstan should not claim or attempt first

- Do not claim novelty for PCC, certifying compilation, proof-carrying data, translation validation or verified compilation as general ideas.
- Do not call signed provenance or a test attestation a proof of program safety.
- Do not imply that a proof of a Lean model establishes concrete evaluator refinement.
- Do not imply that a type-safe CCAM program is safe against unmodelled host/OS behaviour.
- Do not include general source-language programs, arbitrary native code, concurrent execution, FFI, device access or distributed execution in the first accepted subset.
- Do not invent a new cryptographic PCD system before there is a distributed-history requirement.
- Do not put the entire producer, compiler, validator and policy engine inside the trusted checker.
- Do not let the certificate choose its own safety policy or omit a required resource/capability field.
- Do not reuse a certificate across different program bytes, semantics versions, targets, resource limits or capability manifests.
- Do not claim a compact certificate until size/check-time measurements exist.

## 14. Conclusion

PCC, certifying compilation, translation validation, verified compiler construction, PCD and software attestations are mature and overlapping bodies of work. They establish most of the broad mechanisms named in the Capstan ECE proposal. In particular, PCD has already been applied to enforcing language semantics across distributed computations, and CompCert/CakeML already demonstrate substantial verified compiler pipelines.

The defensible next step is not a novelty claim. It is a narrow, measurable experiment: a canonical CCAM subset, a producer-independent bounded certificate checker, explicit program/semantics/policy binding, a formal accepted-program predicate, and a separate evaluator-refinement argument. Compare that design with recomputation, translation validation and a verified compiler pipeline. If the result shows a meaningful reduction in checker TCB or validation cost while preserving precise evidence boundaries, Capstan may have a useful integration contribution. If it does not, that negative result should guide the architecture rather than be hidden.

## 15. Bibliography and primary references

1. George C. Necula. **Proof-Carrying Code.** POPL (1997), pp. 106–119. [Paper](https://doi.org/10.1145/263699.263712).
2. George C. Necula and Peter Lee. **The Design and Implementation of a Certifying Compiler.** PLDI (1998), pp. 333–344. [Paper](https://homes.cs.washington.edu/~mernst/teaching/6.893/readings/necula-pldi98.pdf).
3. Dan Grossman and Greg Morrisett. **Scalable Certification for Typed Assembly Language.** Types in Compilation (2000). [Paper](https://homes.cs.washington.edu/~djg/papers/tal_scale.pdf).
4. Andrew W. Appel and Amy P. Felty. **A Semantic Model of Types and Machine Instructions for Proof-Carrying Code.** POPL (2000), pp. 243–253. [Foundational PCC project bibliography](https://www.cs.princeton.edu/~appel/fpcc.html).
5. Andrew W. Appel. **Foundational Proof-Carrying Code.** LICS (2001), pp. 247–258. [Author bibliography](https://www.cs.princeton.edu/~appel/papers/).
6. Amir Pnueli, Michael Siegel and Eli Singerman. **Translation Validation.** TACAS (1998), pp. 151–166. [Paper](https://cs.nyu.edu/home/people/in_memoriam/pnueli/pss00.pdf).
7. George C. Necula. **Translation Validation for an Optimizing Compiler.** PLDI (2000), pp. 83–94. [Paper](https://people.eecs.berkeley.edu/~necula/Papers/tv_pldi00.pdf).
8. Xavier Leroy. **Formal Verification of a Realistic Compiler.** Communications of the ACM 52(7) (2009), pp. 107–115. [CompCert documentation and development](https://compcert.org/doc/).
9. Ramana Kumar, Magnus O. Myreen, Michael Norrish and Scott Owens. **CakeML: A Verified Implementation of ML.** POPL (2014), pp. 179–191. [Publication](https://doi.org/10.1145/2535838.2535841).
10. Yong Kiam Tan, Magnus O. Myreen, Ramana Kumar, Anthony Fox, Scott Owens and Michael Norrish. **The Verified CakeML Compiler Backend.** Journal of Functional Programming (2019). [Publication](https://doi.org/10.1017/S0956796818000229).
11. Alessandro Chiesa and Eran Tromer. **Proof-Carrying Data and Hearsay Arguments from Signature Cards.** (2010). [Paper](https://cs-people.bu.edu/tromer/papers/pcd.pdf).
12. Stephen Chong, Eran Tromer and Jeffrey A. Vaughan. **Enforcing Language Semantics Using Proof-Carrying Data.** (2014). [Paper](https://cs-people.bu.edu/tromer/papers/plpcd-20140113.pdf).
13. Benedikt Bünz, Alessandro Chiesa, William Lin, Pratyush Mishra and Nicholas Spooner. **Proof-Carrying Data without Succinct Arguments.** CRYPTO (2021). [Paper](https://iacr.org/archive/crypto2021/12826020/12826020.pdf).
14. Benedikt Bünz, Pratyush Mishra, Wilson Nguyen and William Wang. **Accumulation Without Homomorphism.** ITCS (2025). [Paper](https://drops.dagstuhl.de/storage/00lipics/lipics-vol325-itcs2025/html/LIPIcs.ITCS.2025.23/LIPIcs.ITCS.2025.23.html).
15. SLSA. **Software Attestations, Version 1.2.** Official specification, accessed 2026-11-26. [Attestation model](https://slsa.dev/spec/v1.2/attestation-model); [build provenance](https://slsa.dev/spec/v1.2/build-provenance).
16. in-toto. **Attestation Framework and Predicate Specifications.** Official project specifications, accessed 2026-11-26. [Vetted predicates](https://github.com/in-toto/attestation/blob/main/spec/predicates/README.md).
17. Simon Gregersen, Chaitanya Agarwal and Joseph Tassarotti. **Logical Relations for Formally Verified Authenticated Data Structures.** CCS (2025). [Paper](https://arxiv.org/abs/2501.10802).
18. **On the Simulation-Extractability of Proof-Carrying Data.** PKC (2026). [Publication record](https://eprints.whiterose.ac.uk/id/eprint/243145/).
