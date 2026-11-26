# A minimal compositional guarantee calculus for Capstan

**Status:** falsifiable research proposal; no normative language, CCAM or implementation change  
**Issue:** [#227](https://github.com/DavidFernee/Capstan/issues/227)  
**Reviewed:** 2026-11-26  
**Repository snapshot:** main at `9767cc7fde72726ff9f1db41405f83639545243a`  
**Inputs:** [C-free execution/trusted-boundary inventory](../architecture/C-FREE-EXECUTION.md), [C-free bootstrap contract](../C-FREE-BOOTSTRAP.md), [C-free compiler feature closure](../architecture/C-FREE-COMPILER-FEATURE-CLOSURE.md), [ECE related work](ECE-RELATED-WORK-AND-NOVELTY-ASSESSMENT.md), [resource-analysis survey](COMPOSITIONAL-RESOURCE-ANALYSIS-SURVEY.md), [capability/effect/IFC survey](CAPABILITY-EFFECT-IFC-SURVEY.md), [comparative evaluation protocol](COMPARATIVE-EVALUATION-PROTOCOL.md), [ECE proposal](EVIDENCE-CARRYING-EXECUTION.md), [ECE/CCAM crosswalk](ECE-CCAM-CROSSWALK.md), [F1 contract](../F1-LANGUAGE-CONTRACT.md), [concurrency calculus](CONCURRENCY-GUARANTEE-CALCULUS.md)

## 1. Research question and result in brief

Can Capstan give each function or module one compositional contract that connects:

1. what it means (preconditions, postconditions and invariants);
2. what it may do (effects);
3. which authority it requires (capabilities);
4. what resources it may consume (dimensioned resource bounds);
5. which environment assumptions remain (OS, scheduler, hardware and foreign code); and
6. what evidence supports each claim?

The proposed answer is a deliberately small interface judgment:

\[
\Sigma;\Gamma;K;\Omega;H \vdash M :
\{P\}\;[\mathcal{E},\mathcal{A},\mathcal{R},\mathcal{V}]\;\{Q\}
\]

where the judgement is an interface contract, not new Capstan syntax.

The key design rule is **conservative composition**: composition may combine or weaken guarantees, but it may not invent authority, lower a resource bound, discharge an unknown effect, or upgrade evidence. Unknown callees and host operations remain unknown unless an explicit checked contract or dynamic enforcement boundary is supplied.

This is an integration proposal, not a claim to have invented Hoare logic, effect systems, capability security, AARA, session types, proof-carrying code or proof-carrying data. The plausible contribution is a small, operationally defined composition rule set and a demonstrable evidence path across a restricted Capstan profile. Whether that integration is distinctive remains falsifiable.

## 2. Core judgement

The components are:

| Symbol | Meaning | Required interpretation |
|---|---|---|
| Σ | Versioned interface environment | Function/module signatures and their contract digests |
| Γ | Value and ownership environment | Types, initialisation, ownership/borrows and state invariants |
| K | Available capability environment | Actual attenuated authority available to the caller |
| Ω | Caller resource budget | Remaining cumulative budgets and live-resource ceilings |
| H | Explicit environment assumptions | OS, ABI, scheduler, hardware, runtime, allocator and FFI assumptions |
| M | Function or module body | The component being specified |
| P,Q | Precondition and postcondition | Normal and exceptional/trap outcomes are distinguished |
| E | May-effect set | Operations the component may perform |
| A | Required authority | Capability predicates needed to perform those effects |
| R | Resource summary | Dimensioned costs, peak occupancy and evidence state |
| V | Evidence references | Exact theorem, checker, runtime-enforcement, measurement and assumption records |

A judgement is valid only relative to a named language/profile semantics and an exact component identity. An evidence reference must identify the source/program digest, semantic profile, contract version, checker/proof revision and target assumptions to which it applies.

### 2.1 Effects and authority are distinct

E describes possible behaviour. A describes the authority required to perform that behaviour.

For example:
- an effect may state that a function can write a file;
- the authority requirement states that it needs a FileWrite capability scoped to a particular root/path and byte ceiling;
- possession of the effect annotation does not grant the capability;
- possession of a capability does not imply that the function actually uses it.

A call is admissible only if the caller's available capabilities cover the callee's requirements under the attenuation relation. A function cannot manufacture a capability by declaring an effect or by calling a helper with a broader ambient environment.

For the first model, a capability record is the tuple (kind, object identity, rights, scope, resource ceilings, generation/expiry state). The relation A ≤ K holds only if every required capability can be derived from a capability in K by attenuation: same object identity and valid generation; required rights are a subset; required scope is no broader; and required byte/count/deadline ceilings are no larger. There is no implicit ambient capability, name-based authority or capability creation by type coercion.

Likewise, fits(Ω,R) is component-wise: every finite cumulative charge is within the remaining monotonic budget; every live peak plus current occupancy is within its ceiling and its net delta satisfies the postcondition; and any target-dependent timing bound has a named, validated target/scheduler model. Unknown does not fit a finite Safe budget unless a separate runtime-enforced ceiling is explicitly part of the contract.

### 2.2 Resource summary

A single scalar cost is insufficient. Use three classes:

\[
\mathcal{R}=(\mathcal{C},\mathcal{L},\mathcal{T})
\]

- C: cumulative consumption bounds, such as fuel/steps, input bytes, output bytes and decoded units. These counters are monotonic and never released.
- L: live-resource summaries, such as retained bytes, live objects, open handles, tasks, queue slots and mappings. These require acquisition/release ownership and peak accounting.
- T: target/environment-dependent timing claims, such as wall-clock deadlines, CPU cycles and energy. These require a target-specific timing/scheduling model; abstract fuel is not a substitute.

Each dimension carries a bound state:
- Fin(n): finite upper bound n, with unit and accounting semantics;
- Unbounded: the contract explicitly permits unbounded consumption;
- Unknown: no sound bound is available.

Unknown is not zero. A measured maximum is not a finite upper bound. A runtime-enforced ceiling is not a static proof.

For live resources, use a summary L=(p,δ):
- p is the maximum additional live occupancy above the component's entry occupancy;
- δ is a conservative interval for net live-resource change at return.

This summary is sufficient for a first conservative sequential algebra. It is not a complete model of arbitrary aliasing or shared concurrent resources; those require explicit ownership and shared-ledger invariants.

### 2.3 Evidence state

Every guarantee component carries one primary evidence state:

| State | Meaning | May satisfy a static-proof requirement? |
|---|---|---|
| Proved | A sound theorem applies to this exact program/profile and assumptions | Yes |
| RuntimeEnforced | A runtime/adapter rejects before the relevant transition commits | No; it establishes a dynamic ceiling only |
| Assumed | Depends on a declared external contract | Only if the caller accepts the assumption |
| Measured | Observed in tests/benchmarks | No |
| Unknown | No valid evidence | No |

Evidence composition uses the weakest required premise. A measured result cannot become a proof by composition; a runtime check cannot become a static theorem; an unknown component cannot be hidden by a known caller contract.

### 2.4 Current implementation and trusted boundary

This proposal is not a description of the current production compiler/runtime. The repository's default bootstrap remains Python-seeded and C-generating, with a C compiler and C runtime in the trusted execution path. The Capstan-native CCAM evaluator, validator, source lowerer and Linux x86-64 backend are bounded increments; the native backend does not yet compile the full compiler or establish an end-to-end refinement theorem. The current C-free execution, bootstrap and feature-closure documents remain the authority for those boundaries.

Consequently, a proof of the first CCAM-SF-P model would establish only the selected profile's formal properties. It would not make the current compiler C-free, prove the C runtime, or establish native-backend correctness.

## 3. Composition rules

The rules below are semantic obligations, not implementation claims. covers(K,A) means the caller's capabilities cover the callee's requirements with no increase in scope or rights. Resource composition is component-wise and unit preserving.

### 3.1 Sequential composition

For M;N, require:

\[
Q_M \Rightarrow P_N
\]

and covers(K,A_M ∪ A_N). The combined contract has:
- precondition P_M;
- postcondition Q_N, with intermediate trap/failure outcomes retained;
- effects E_M ∪ E_N;
- authority requirements A_M ∪ A_N;
- environment assumptions H_M ∪ H_N;
- evidence references combined without upgrading their evidence state.

For cumulative dimension c:

\[
C_{M;N}(c)=C_M(c)+C_N(c)
\]

provided both are finite and use the same unit/accounting semantics. If either is Unknown or Unbounded, the result is not a finite bound.

For live dimension l, let p_M,p_N be peak increments and δ_M=[d⁻_M,d⁺_M] the net live-resource interval after M:

\[
p_{M;N}=\max(p_M,\; \max(0,d^+_M)+p_N)
\]

\[
\delta_{M;N}=\delta_M+\delta_N
\]

This is conservative: it uses the maximum possible retained increase from M when bounding N. A tighter rule may use a richer ownership/retention summary, but must not assume that resources freed by M are available if the release proof is absent.

### 3.2 Conditional composition

For if b then M else N:
- both branches must establish the declared postcondition, or a declared disjunction;
- the condition's effects, authority and resource cost are included;
- effects and authority are the union of both branches;
- cumulative worst-case cost is the component-wise maximum of the branch bounds;
- live peak is the maximum of the branch peaks;
- net live-resource change is the interval hull of the branch changes.

If one branch has an Unknown cost or authority requirement, the whole conditional summary retains that uncertainty unless the branch is statically unreachable under a proved condition.

### 3.3 Bounded loops

For a loop with a proved iteration bound n, invariant I, and body contract B:
- prove I initially;
- prove one body execution preserves I;
- prove the loop condition and variant establish termination within n;
- compose cumulative cost using a sound bound on n body executions plus condition/branch overhead;
- derive live peak from the body summary and loop invariant.

If the body retains resources across iterations, the live delta accumulates. If the body releases temporary resources on every iteration, the peak may be bounded by one iteration's peak plus the invariant's retained occupancy. The checker must prove which case applies.

An unbounded loop has no finite static work bound by default. It may be admitted only with an explicit runtime fuel ceiling, in which case the evidence state is RuntimeEnforced rather than Proved.

### 3.4 Calls and module boundaries

For a call to f:
1. the caller establishes P_f;
2. the caller's capabilities cover A_f;
3. the caller's effect context permits E_f, or a checked handler discharges an effect;
4. the callee's resource summary fits the remaining caller budget Ω;
5. the exact contract version and digest match the linked module;
6. the callee's postcondition is imported only with its stated evidence and assumptions.

A module boundary does not erase authority, resource cost, traps or environmental assumptions. A stale or mismatched contract digest invalidates the composition.

### 3.5 Recursion

Recursive calls require both:
- a termination/ranking argument for the admitted input domain; and
- a sound recurrence or amortised potential derivation for each finite cumulative resource dimension.

If either is absent, the static cost is Unknown/Unbounded. A runtime fuel/depth limit may still bound execution dynamically, but the contract must label that guarantee RuntimeEnforced and specify exhaustion behaviour.

### 3.6 Higher-order functions and callbacks

A callback parameter must carry an explicit contract for pre/postconditions, effects, authority, resources, traps and assumptions. The caller composes against that contract, not the callback's source name or presumed behaviour.

An unconstrained callback has:
- unknown effects;
- unknown authority requirements;
- unknown resource consumption;
- no useful postcondition beyond a declared failure-safe top contract.

It is rejected in a Safe composition unless wrapped by a checked adapter that attenuates its authority and dynamically bounds its resource use. The adapter does not turn unknown callback behaviour into a static proof.

### 3.7 Exceptions and traps

The postcondition includes separate normal and exceptional outcomes:

\[
Q = Q_{\mathrm{normal}} \lor Q_{\mathrm{trap}}
\]

The contract states which resources are consumed before a trap, which live resources are released/transferred, and whether partial external effects may already have committed. Cumulative fuel is never refunded. A failure-atomic operation may claim no externally visible mutation on failure only if its commit point and rollback/ownership semantics are proved or enforced.

If cleanup is not proved or enforced, the exceptional postcondition must retain the possible live-resource leak/poisoned-handle state. It cannot silently claim the normal postcondition.

### 3.8 FFI and host operations

An FFI/host call is an opaque module boundary. It must provide a versioned adapter contract with:
- effects and required capabilities;
- cumulative work/byte charges;
- live resources acquired and exact release owner;
- blocking, cancellation, partial-progress and failure semantics;
- OS/device/library assumptions;
- evidence state and exact adapter identity.

Without that contract, the call is Unknown for effects, authority and resources. It is rejected in the Safe profile or placed behind an explicit runtime sandbox/quota. A guest fuel counter alone does not bound unmetered host work.

### 3.9 Concurrency

For parallel composition M||N:
- total cumulative work is the sum of both components' work bounds;
- peak live occupancy is bounded by the sum only when the components' live resources are disjoint or separately reserved;
- shared resources require a common ledger and a proved invariant;
- task/channel ownership and cancellation lifetimes must compose;
- liveness requires explicit scheduler/fairness assumptions.

This is a later extension of the core calculus. The first formalisation is sequential; it must not infer concurrency safety from sequential composition.

## 4. Worked examples

The examples are hypothetical contracts illustrating the rules. Their numeric bounds are chosen for the example and are not claims about current Capstan implementation.

### 4.1 Accepted composition: parse then write a bounded CSV report

Assume:
- parse_rows accepts at most 4,096 input bytes;
- it is pure, requires no capability, returns CsvText on success, and has a proved work bound 12n+40 steps and peak temporary live storage 2n+128 bytes;
- write_csv accepts CsvText only, requires a FileWrite capability scoped to one output path, and has a runtime-enforced output ceiling of 8,192 bytes;
- the caller has exactly that FileWrite capability and a fuel budget large enough for the parser plus sink work.

Composition:
1. The parser's postcondition establishes the sink's input type/precondition.
2. The parser's empty authority requirement does not expand the caller's authority.
3. The sink's FileWrite requirement is covered by the caller's attenuated grant.
4. The parser's static work bound and the sink's dynamic output ceiling remain separately labelled.
5. The composed result is not described as statically bounded in output bytes unless the sink's output size is also proved; the runtime ceiling is reported as RuntimeEnforced.
6. The final effect set includes file.write, and the host adapter assumption is explicit.

This is accepted only under the stated input-size and output-path assumptions. The result is a mixed-evidence contract: parser work is Proved; output size is RuntimeEnforced; filesystem semantics are Assumed until the host adapter is refined.

### 4.2 Rejected composition: unknown callback hidden behind a safe wrapper

Assume a caller has:
- a FileWrite capability scoped to one report path;
- a 16 KiB output budget;
- no network, process or filesystem-read authority.

It calls a helper with a callback parameter, but the callback has no contract. The helper claims only that it returns a string.

The callback may:
- perform network or filesystem operations;
- allocate or retain unbounded memory;
- invoke another callback;
- fail after a partial side effect;
- consume unbounded work.

The composition checker cannot infer that the callback uses only the caller's FileWrite authority or fits the caller's resource budget. The helper is rejected in the Safe profile. It is not enough that the helper itself has a narrow type signature or that tests show a benign callback.

A separately checked adapter could attenuate the callback's authority and enforce fuel, output and live-memory ceilings. The resulting guarantee would be explicitly RuntimeEnforced at that boundary, not a static proof about arbitrary callback behaviour.

### 4.3 Unknown FFI is not free

A function that calls an unannotated foreign routine receives Unknown effects, authority and resource cost. The caller cannot compose it under a finite resource contract by assigning zero cost or by trusting a function name. It must supply a versioned adapter contract or reject the call. This prevents an unknown host operation from reducing the caller's declared resource use or increasing its authority.

## 5. Evidence and soundness obligations

The calculus is useful only if each composition rule is sound relative to an explicit operational semantics.

### 5.1 Core soundness conjectures

1. **Hoare composition.** If M and N satisfy their judgments and Q_M implies P_N, then the small-step semantics of M;N satisfies the composed pre/postcondition, including exceptional outcomes.
2. **Authority non-amplification.** If a component is invoked with capability environment K and its contract requires A with covers(K,A), then every host operation it can perform is mediated by authority no greater than K under the attenuation relation.
3. **Cumulative resource soundness.** If a judgment reports a finite cumulative bound b, every execution in the stated domain consumes no more than b units under the declared cost semantics.
4. **Live-resource soundness.** If a judgment reports peak bound p and net delta interval d, every execution respects the peak bound and returns a live-resource state inside d, assuming all acquisition/release transitions are accounted for.
5. **Unknown preservation.** If a required callee/handler/adapter property is Unknown, composition cannot return a stronger evidence state for that property without an additional checked premise.
6. **Evidence freshness.** A certificate for one program digest, profile, policy, adapter or compiler revision cannot justify a different one.
7. **Implementation refinement.** If the concrete evaluator/adapter refines the reference semantics and preserves the resource/authority transition relation, the guarantees transfer to the concrete implementation under the stated environment assumptions.

These are conjectures/targets. None is asserted proved by this document.

### 5.2 Small formal model

The first model should be a deterministic, call-by-value core with:
- scalar values, immutable byte strings and bounded collections;
- functions and direct calls;
- pre/post assertions and explicit trap outcomes;
- a finite effect set and an abstract capability environment;
- cumulative fuel/byte counters;
- live-resource acquire/release events;
- versioned function summaries and evidence labels;
- a small-step cost trace.

The semantics records each step's effect, authority use, cumulative charge, live-resource delta and observable outcome. FFI is represented as an opaque transition requiring an explicit adapter contract. Concurrency, shared memory, dynamic dispatch, arbitrary higher-order callbacks and native ABI calls are excluded initially.

### 5.3 Proof obligations

| Obligation | Required theorem/check |
|---|---|
| Contract well-formedness | Units, bounds, effects, capabilities and evidence references are well-typed and versioned |
| Pre/post soundness | Every normal/trap execution satisfies the declared outcome postcondition |
| Sequential composition | Intermediate postcondition establishes next precondition; resource algebra is sound |
| Branch composition | Both branches satisfy the common contract; worst-case bounds are conservative |
| Loop soundness | Invariant/variant and recurrence dominate all admitted iterations |
| Call soundness | Contract digest, pre/post, authority and resource budget are checked at each call |
| Authority non-amplification | Callee/handler/FFI cannot acquire rights absent from the attenuated caller environment |
| Resource soundness | Cumulative and live bounds dominate all semantic traces |
| Failure atomicity | Failed reservations/host commits preserve specified state and ownership |
| Evidence monotonicity | Composition never upgrades Measured/Assumed/Unknown to Proved |
| Refinement | Concrete CCAM evaluator and host adapter preserve the reference transitions |

## 6. Comparison with established approaches

| Prior-art family | Established strength | What this calculus reuses | What remains to be demonstrated |
|---|---|---|---|
| Hoare logic / separation logic | Preconditions, postconditions, invariants and local reasoning | Semantic contract and ownership/state assertions | Whether effects, authority, resources and evidence compose usefully in one small interface |
| Effect systems and handlers | Static description/handling of computational effects | Explicit may-effect set and checked handlers | Effects must remain distinct from granted authority and resource bounds |
| Object-capability systems | Explicit, attenuable authority and no ambient access | Capability requirement set and non-amplification rule | A practical compiler/runtime link from contracts to actual host mediation |
| AARA / RAML | Compositional amortised work/space bounds for supported programs | Cumulative and selected live-resource cost summaries | Sound integration with mutable systems code, host effects and runtime enforcement |
| Sized types / implicit complexity | Structural size, termination and complexity information | Input-size parameters and recursion obligations | Resource vectors beyond the supported size/cost model |
| Resource-aware session types | Protocol-level potential and compositional work bounds for communicating processes | Future extension for bounded channels/tasks | Peak live memory, arbitrary shared memory and platform latency |
| PCC / certifying compilation | Untrusted producer with independently checked safety evidence | Evidence references and a checker-facing contract | Whether a compact certificate checks the combined contract more efficiently than recomputing analyses |
| Translation validation / verified compilers | Source-to-target semantic preservation | Separate implementation-refinement obligation | A practical refinement chain for Capstan's concrete evaluator/adapter |

The completed #220 and #222 surveys, together with the #221 resource-analysis survey draft under review, establish that the individual mechanisms are prior art. The proposal should be described as an **engineering adaptation/integration hypothesis**, not a new general theory of contracts, effects, capabilities or resource analysis. A stronger novelty claim requires a demonstrated advantage in modularity, checker TCB, proof reuse, resource precision or deployment cost against the strongest baselines.

## 7. Smallest executable vertical slice

The first implementation/proof experiment must not depend on features that are only planned.

### 7.1 First checker/refinement target

Use the conservative CCAM-SF-P single-frame profile identified in the ECE/CCAM crosswalk:
- entry PC zero;
- typed scalar registers and checked arithmetic;
- constants, moves, comparisons, branches/jumps, returns and explicit traps;
- one shared instruction-step budget;
- no calls, output extension, I/O, capabilities, heap, concurrency or native backend.

This is intentionally narrower than normative CCAM v0.1 and narrower than the integrated multi-function evaluator. It is the current Lean model's conservative profile, not a claim that the whole CCAM contract has been formalised.

The first theorem/checker experiment:
1. freezes a canonical profile and accepted-program predicate;
2. checks a single component contract with pre/post, empty effect/authority sets, a finite step bound and exact semantics ID;
3. proves checker acceptance implies the Lean profile predicate;
4. proves the concrete single-frame evaluator refines the Lean machine for that profile;
5. tests exact fuel boundaries and trap outcomes;
6. rejects any contract that claims unsupported calls, output, capabilities or host effects.

### 7.2 Second increment: direct-call composition

Only after the single-frame refinement theorem:
- extend the Lean machine with function table, call-site representation, frames, continuations and shared step/depth counters;
- reconcile normative named-call objects with the current internal call-site side tables;
- prove a two-function direct-call example;
- add the sequence/call composition checker and capability/resource summaries;
- keep output/FFI/host operations excluded until their semantics are versioned.

This uses the already integrated Capstan multi-function evaluator as an implementation target, but does not pretend its existence supplies the missing Lean theorem.

## 8. Falsifiable hypothesis and evaluation

### H-GC-1

For a closed deterministic scalar CCAM subset, a small contract checker can compose semantic pre/postconditions, effect/authority requirements and dimensioned resource bounds so that:
- every accepted composition satisfies the reference operational semantics;
- no accepted call exceeds its declared cumulative or live-resource ceiling;
- authority requirements never exceed the caller's attenuated grants;
- unknown callback/FFI/resource behaviour is rejected or remains an explicit RuntimeEnforced obligation;
- evidence status is never upgraded by composition.

### Falsification conditions

H-GC-1 fails if:
- an accepted composition violates its postcondition or exceeds any declared bound;
- a callee obtains authority not covered by the caller's capabilities;
- an unknown callback or FFI path is accepted as statically bounded without a checked contract;
- a failed resource reservation partially mutates the ledger;
- a stale certificate is accepted after program/profile/policy mutation;
- the checker relies on the producer's acceptance decision rather than validating the contract/evidence itself.

### Baselines and metrics

Compare:
1. separate type/effect checker plus runtime quotas, without a unified contract;
2. AARA/RAML on the supported pure sublanguage;
3. a sized-type/termination analysis on the same recursive examples;
4. a conventional Hoare/separation-logic specification without integrated capability/resource composition;
5. a PCC-style certificate checker for the exact accepted-program predicate;
6. the proposed composed contract/checker.

Measure:
- accepted/rejected program precision and false rejection rate;
- soundness against exhaustive bounded execution and independent counterexample search;
- checker code size and trusted dependencies;
- certificate size and check time;
- resource-bound tightness versus observed traces;
- runtime enforcement overhead where used;
- annotation burden and time to diagnose rejected compositions.

A finite-state exhaustive check validates only the selected bounded model. It does not prove arbitrary programs, the full source language, native backends or host OS behaviour.

## 9. Alternatives considered

| Design choice | Alternative | Assessment |
|---|---|---|
| Contract form | One monolithic judgement that merges types, effects, authority, resources and proofs | Compact notation, but risks conflating distinct semantics and evidence classes; harder to evolve and audit |
| Contract form | Factored judgements with explicit compatibility rules | Recommended: preserves distinct meanings while making composition obligations explicit; the cost is a more involved checker |
| Resource model | One scalar fuel/budget for all resources | Rejected: work, output bytes, peak live memory, handles and deadlines have different units and release/composition laws |
| Resource model | Dimensioned cumulative counters plus live-resource leases and target-specific timing | Recommended: matches operational semantics and keeps static bounds, dynamic ceilings and assumptions separate |
| Authority model | Treat effects as permissions | Rejected: an effect describes possible behaviour but must not grant the authority needed to perform it |
| Authority model | Explicit capability requirements checked against attenuated caller grants | Recommended: permits no ambient fallback and supports non-amplification proofs |
| Unknown components | Assume unknown callees are pure/zero-cost unless annotated | Rejected: unsoundly hides authority and resource behaviour |
| Unknown components | Reject or require a checked adapter contract/dynamic sandbox | Recommended: fail-closed, with dynamic enforcement explicitly labelled |
| Evidence | Trust the producer/compiler's acceptance decision | Rejected for the independent-checking hypothesis; compare only as a baseline |
| Evidence | Recompute analysis or check a producer-independent certificate | Both remain candidates; the first experiment should measure checker size, certificate size and recomputation cost |
| Timing | Treat abstract fuel or benchmark maxima as WCET | Rejected: neither is a target-specific worst-case execution-time proof |

The factored judgment and dimensioned resource model are the current recommendations, not settled language design. If the first formal model shows that a simpler formulation has equal soundness and materially lower checker complexity, prefer the simpler one.

## 10. Open decisions and non-goals

1. Which assertions are first-order decidable by the initial checker, and which require external proof terms?
2. Is authority inclusion a syntactic capability-subset relation, a semantic attenuation judgment or both?
3. How are capability identity, expiry, revocation and delegation represented in the interface digest?
4. Which live-resource dimensions have precise ownership/release semantics in the first implementation?
5. Are effects a may-effect upper bound, an exact effect trace or a row with handled residuals? The first profile should choose the simplest sound interpretation.
6. How are recursive cost recurrences solved and how is solver evidence checked?
7. How are disjunctive postconditions and branch-dependent live-resource deltas represented without losing precision?
8. Which evidence references must be cryptographically bound, and which can be local proof-build metadata?
9. How does the calculus compose across module version upgrades and dynamic linking?
10. Which host assumptions can be made explicit and machine-checked, and which remain deployment declarations?

Non-goals for the first slice:
- arbitrary higher-order callbacks or dynamic dispatch;
- general exceptions, async tasks or concurrency;
- wall-clock WCET, energy or processor-cycle bounds;
- arbitrary FFI or OS operations;
- universal memory-safety or vulnerability-elimination claims;
- a new proof assistant, cryptographic PCD system or general-purpose theorem prover.

## 11. Conclusion

The smallest useful calculus keeps semantics, effects, authority, resources, environment assumptions and evidence separate in the interface, then composes them conservatively. The resource algebra distinguishes monotonic cumulative consumption from live occupancy and target-dependent timing. Unknown callees and host operations do not receive zero cost or ambient authority. Runtime enforcement remains a distinct evidence class from static proof.

The strongest existing work already supplies the component ideas. The research test is whether this factored interface yields a small, checkable and useful composition mechanism for Capstan's restricted execution model. The first proof should target CCAM-SF-P, not the multi-function/native path. Direct-call composition follows only after the single-frame evaluator refinement is established. No normative language or CCAM change is proposed here.
