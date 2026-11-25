# F1 related-work review: guarantee composition

> **Status:** research synthesis, 2026-11-26; not a novelty claim  
> **Scope:** type/effect/capability composition, ownership, information flow and resource semantics  
> **Parent:** [F1 language contract](F1-LANGUAGE-CONTRACT.md)

This is a focused first-pass related-work review for F1-D01 through F1-D05. It is not a systematic literature review: search strategy, inclusion criteria, backward/forward citation chasing and independent review remain outstanding. The papers below are relevant baselines, not evidence that Capstan has independently reproduced their results.

## 1. Main finding

The literature argues against choosing between a single monolithic type system and several unrelated analyses.

The strongest candidate for Capstan is a **factored, mutually checked guarantee derivation**:

- one source typing derivation and one operational semantics;
- distinct, explicit components for value types/provenance, ownership/lifetimes, authority/capabilities, computational effects and resource accounting;
- shared composition rules that specify how each component is transformed by every language construct;
- a single accepted-program certificate or evidence envelope binding the results to the exact program/profile/target.

This is a working hypothesis, not a final design. The components cannot be collapsed into one algebra without losing important distinctions: ownership contexts are affine/linear; information-flow labels may be ordered by a lattice or relational property; effect rows compose by effect-specific rules; capabilities are non-forgeable authority with identity and attenuation; resource bounds use quantitative potential/budgets. A simple union of annotations is not a sound composition rule for all of them.

The alternative—independent checkers with unrelated semantics—is also unacceptable: it creates gaps at generic substitution, aliasing, control flow, module boundaries and compiler transformations. The proposed architecture is therefore a shared derivation with orthogonal, explicitly coupled judgements and a single conservative acceptance decision.

## 2. Effect systems and capabilities

### 2.1 Rows and capabilities as modal effects (2026)

Wenhao Tang and Sam Lindley, “Rows and capabilities as modal effects”, *Proceedings of the ACM on Programming Languages* 10(POPL), 2026, pp. 923–950. DOI: [10.1145/3776674](https://doi.org/10.1145/3776674).

This peer-reviewed 2026 work gives a uniform framework for encoding and comparing row-based and capability-based effect systems. Its modal effect types decouple effect tracking from functions and show type- and semantics-preserving translations for the encodings studied. This is directly relevant to F1-D02: Capstan should not assume a conventional effect row or a conventional capability parameter is the only possible foundation.

**Implication:** evaluate a modal account as a common semantic layer for effect tracking, but do not infer that it automatically provides object-capability security, non-forgeable authority, attenuation, revocation or platform confinement. Those are additional properties to define and prove.

### 2.2 Effects as capabilities (2020)

Jonathan Immanuel Brachthäuser, Philipp Schuster and Klaus Ostermann, “Effects as Capabilities: Effect Handlers and Lightweight Effect Polymorphism”, *Proceedings of the ACM on Programming Languages* 4(OOPSLA), 2020, Article 126. DOI: [10.1145/3428194](https://doi.org/10.1145/3428194).

Effekt interprets effect types as capabilities required from the context and defines semantics through translation to an explicit capability-passing calculus. Its effect-safety design separates functions from values and treats functions as second-class to prevent unsafe capability capture in the studied system.

**Implication:** capability capture is a first-class soundness question, not an implementation detail. Since current Capstan has no closures, the initial calculus can deliberately begin with first-order functions; closure support must later prove how captured capabilities are represented, scoped and attenuated. Do not add closures before that design is settled.

### 2.3 Bounded abstract effects (2022)

Darya Melicher, Anlun Xu, Valerie Zhao, Alex Potanin and Jonathan Aldrich, “Bounded Abstract Effects”, *ACM Transactions on Programming Languages and Systems* 44(1), 2022, Article 5. DOI: [10.1145/3492427](https://doi.org/10.1145/3492427).

This work formalises abstract effect members with aggregation and lower/upper bounds and demonstrates reasoning about authority and attenuation.

**Implication:** Capstan's API contracts need more than a flat set of effect names if libraries are to expose abstract authority. The research should test whether bounded abstract effects can represent safe library interfaces without enabling a package to widen authority by abstraction.

### 2.4 Capability-based modules (2017)

Darya Melicher, Yangqingwei Shi, Alex Potanin and Jonathan Aldrich, “A Capability-Based Module System for Authority Control”, 2017. [ANU research record](https://researchportalplus.anu.edu.au/en/publications/a-capability-based-module-system-for-authority-control/).

The proposed module system treats first-class modules as statically typed capabilities and formalises authority-safe module composition, including non-transitive authority and attenuated wrappers.

**Implication:** the module/package design must treat imported modules as authority-bearing components. A module's authority must be inspectable from its interface and explicit construction arguments, not inferred from its implementation or package name.

## 3. Ownership and information flow

### 3.1 Oxide (2019)

Aaron Weiss, Olek Gierczak, Daniel Patterson and Amal Ahmed, “Oxide: The Essence of Rust”, arXiv:1903.00982. [Paper](https://arxiv.org/abs/1903.00982).

Oxide formalises a source-level account of ownership and borrowing, using substructural typing and lifetime/provenance reasoning, with progress and preservation results for its model.

**Implication:** any Capstan ownership model must state the operational meaning of loans/aliases and prove safety, rather than adding informal lifetime annotations. Capstan should compare value/loan semantics against a region/borrow checker before choosing a runtime representation.

### 3.2 Aeneas (2022)

Son Ho and Jonathan Protzenko, “Aeneas: Rust verification by functional translation”, *Proceedings of the ACM on Programming Languages* 6(ICFP), 2022, Article 116, pp. 711–741. DOI: [10.1145/3547647](https://doi.org/10.1145/3547647).

Aeneas uses a value-based, ownership-centric semantics for a Rust subset and translates it to a functional calculus, avoiding explicit memory reasoning for the supported subset.

**Implication:** this is a strong comparator for Capstan's C-free proof pipeline. A value/loan model may simplify proofs, but only if the concrete CCAM/runtime correspondence is established. It does not eliminate the need to model external handles, mutation, unsafe/platform boundaries or resource accounting.

### 3.3 Structural information flow (2025)

Hemant Gouni, Frank Pfenning and Jonathan Aldrich, “Structural Information Flow: A Fresh Look at Types for Non-interference”, *Proceedings of the ACM on Programming Languages* 9(OOPSLA2), 2025, Article 414, pp. 3954–3980. DOI: [10.1145/3764116](https://doi.org/10.1145/3764116).

This work revisits information-flow typing through modal-logic intuitions and targets simpler, more modular reasoning than conventional information-flow specifications.

**Implication:** Capstan's taint/secret mechanism should be evaluated against a formal non-interference account, not only sink-specific taint checks. In particular, control-flow dependence, exceptions, divergence, mutable state and observable resource use must be considered. A byte's taint bit alone cannot establish non-interference.

### 3.4 Modular information flow through ownership (2022)

Will Crichton, Marco Patrignani, Maneesh Agrawala and Pat Hanrahan, “Modular Information Flow through Ownership”, PLDI 2022. [arXiv:2111.13662](https://arxiv.org/abs/2111.13662).

The work uses ownership types to reason soundly about information flow across function boundaries using type signatures, including precompiled dependencies.

**Implication:** ownership and information-flow judgements should be designed together. The package interface must preserve enough alias/ownership and provenance information to reason modularly; a flattened import set is not a future-proof boundary.

## 4. Resource semantics

### 4.1 Automatic amortized resource analysis

Jan Hoffmann and Steffen Jost, “Two decades of automatic amortized resource analysis”, *Mathematical Structures in Computer Science*, 2022. DOI: [10.1017/S0960129521000487](https://doi.org/10.1017/S0960129521000487).

AARA provides compositional resource bounds through local typing rules, potential methods and soundness with respect to an operational cost semantics. The literature covers multiple resource metrics, evaluation strategies and polynomial/non-linear bounds.

**Implication:** Capstan should not invent an ad hoc scalar cost model. Start with a well-defined cost semantics and investigate potential-based compositional bounds. However, memory, fuel, output, handles and concurrency may need separate dimensions and different charging rules.

### 4.2 Liquid Resource Types (2020)

Tristan Knoth, Di Wang, Adam Reynolds, Jan Hoffmann and Nadia Polikarpova, “Liquid Resource Types”, *Proceedings of the ACM on Programming Languages* 4(ICFP), 2020, Article 106. DOI: [10.1145/3408988](https://doi.org/10.1145/3408988).

Liquid Resource Types combine refinement types with automated resource analysis and provide sound bounds for the supported language and analysis.

**Implication:** explore refinement predicates over input sizes and resource potentials, but keep the solver and proof boundary explicit. A solver result must not be trusted as a proof unless the checker validates the generated certificate or a separate soundness argument covers the solver.

### 4.3 Resource-aware borrowing (2025)

Qihao Lian and Di Wang, “Automatic Linear Resource Bound Analysis for Rust via Prophecy Potentials”, OOPSLA 2025. DOI: [10.1145/3720492](https://doi.org/10.1145/3720492).

RaRust combines automatic amortized analysis with Rust borrowing and uses prophecy potentials to reason compositionally about shared and mutable borrows, heap data structures, loops and recursion.

**Implication:** this is a particularly close comparator for a Capstan model that combines ownership with resource budgets. The key question is whether the ownership discipline can make resource potential composition simpler and more precise, not whether Capstan can simply add a cost field to every type.

### 4.4 Two-sided amortized resource analysis (2026 preprint)

Zimu Chen and Di Wang, “Two-Sided Amortized Resource Analysis: Verifying Resource Lower Bounds via Ill-Typing”, arXiv:2611.12925, 1 November 2026. [Preprint](https://arxiv.org/abs/2611.12925).

This recent preprint combines sufficiency and necessity reasoning in one two-sided type system, deriving upper and lower resource bounds in a safety fragment. It reports a prototype checker and 19 benchmarks; the prototype is OCaml, so it is a research comparator, not a Capstan implementation dependency.

**Implication:** upper bounds are the immediate requirement for Safe-profile admission and denial-of-service resistance. Lower bounds are additionally interesting for minimum-budget admission, cost variability and timing side-channel analysis. The result is a preprint and should be treated as provisional until peer review and independent replication.

## 5. Research synthesis and proposed experiment

The literature suggests a product of distinct semantic structures rather than a single undifferentiated annotation:

| Property | Likely mathematical structure | Main soundness question |
|---|---|---|
| Value typing/refinement | Type environment and refinement entailment | Preservation/progress and refinement soundness |
| Ownership/lifetime | Affine/linear context or loan/region relation | No invalid alias/use-after-lifetime; resource lifecycle |
| Authority | Capability context with identity and attenuation | No forgery, widening, unapproved delegation or escape |
| Effects | Effect row/modal judgement linked to capabilities | All effects are declared, handled and capability-backed |
| Information flow | Label/provenance structure plus relational non-interference | No prohibited explicit or implicit flow to observable sinks |
| Resources | Vector budget/potential and operational cost semantics | Actual consumption never exceeds admitted bounds |
| Failure | Explicit result/trap/abort semantics and state transition | No silent failure; specified cleanup and atomicity |

### 5.1 Working architecture hypothesis

Use one shared derivation with factored contexts and conclusions. Do not use independent checkers that each invent their own call/module semantics, and do not flatten all properties into one type qualifier.

An illustrative judgement is:

`Γ ; Ω ; Κ ; Η ⊢ e : τ ; ! ; ε ; 	riangleright ; ec{r}`

where `Γ` types values, `Ω` tracks ownership/loans, `Κ` tracks authority, `Η` tracks information-flow context, `ε` records effects, and `r⃗` describes resource use/bounds. The judgement is only a notation for the research prototype. Whether `Η` belongs in `Γ`, and whether effects should be represented as capabilities or translated through modal effects, remain experimental questions.

### 5.2 Minimal discriminating experiment

Build two small models of the same Capstan-like first-order language:

- **Model A — monolithic:** a single type/qualifier structure with all guarantee dimensions attached to values and functions.
- **Model B — factored derivation:** distinct typing, ownership, capability/effect, information-flow and resource components sharing operational rules and one accepted-program predicate.

Both models must cover let-binding, mutation, branches, loops, calls, lists/maps, tainted input, secret values, protected operations, explicit I/O capability, bounded allocation, traps and helper-function composition.

Adversarial corpus:
1. A tainted password renamed, sliced, wrapped by a helper and passed to a fast hash.
2. An HTML fragment placed in a CSV writer after crossing two functions.
3. A capability captured by a closure or stored in a collection (closure/collection support tested as absent or rejected initially).
4. A protected operation whose data is not labelled sensitive.
5. A helper whose local buffer is bounded but whose aggregate caller allocation exceeds the process budget.
6. A branch whose secret-dependent choice changes externally observable output or work.
7. A package wrapper that attempts to widen a narrower capability.
8. A failure path that partially mutates state before a failed resource admission.

Measure: soundness counterexamples found; expressible positive examples; size of trusted checker; derivation/checker complexity; annotation burden; diagnostic locality; module compositionality; deterministic resource cost of checking.

### 5.3 Current recommendation

Proceed with Model B as the primary experiment, while retaining Model A as a baseline. The recommendation is based on the distinct algebraic nature of the guarantees and the literature's modular approaches; it is not a theorem that Model B is superior. Model B wins only if its shared derivation prevents cross-component inconsistencies and it has a smaller or more tractable soundness argument than Model A.

The first formal target should be a first-order, sequential subset. Defer closures, user generics, concurrency and package-level separate compilation until the base preservation/composition results are established. Use Capstan as the implementation language for executable models and corpus runners; external proof/research tools remain disclosed independent oracles during migration.

## 6. Threats to validity and next work

- This review is selective, not systematic; related work may be missing.
- Publication status differs: the 2026 modal-effects paper is peer-reviewed; the November 2026 two-sided AARA item is a preprint.
- A calculus can be sound but too restrictive or unusable. Positive expressiveness and diagnostics must be measured.
- Static non-interference and resource bounds need a clearly defined observation model; wall-clock timing and hardware side channels cannot be assumed solved by source types.
- The Capstan target includes imperative mutation, a GC runtime, byte strings, CCAM and host effects. Results for pure functional subsets do not transfer automatically.
- No novelty claim is made. Any Capstan contribution must be compared to the closest formal systems and demonstrate a new, reproducible composition result.

Next: obtain full papers and technical appendices; perform backward/forward citation review; reproduce selected definitions; construct minimal counterexamples for each model; and only then select the normative judgement architecture.
