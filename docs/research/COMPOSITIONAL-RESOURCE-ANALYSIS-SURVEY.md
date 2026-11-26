# Compositional resource analysis for Capstan: comparative survey

**Status:** targeted literature review and design recommendation; no resource-analysis implementation or guarantee is claimed by this document  
**Issue:** [#221](https://github.com/DavidFernee/Capstan/issues/221)  
**Reviewed:** 2026-11-26  
**Repository baseline:** current main at review time  
**Coordinates:** [F1 language contract](../F1-LANGUAGE-CONTRACT.md), [research register](RESEARCH-REGISTER.md), [concurrency guarantee calculus](CONCURRENCY-GUARANTEE-CALCULUS.md), [Halyard Core primitives](../media/CORE-PRIMITIVES.md), [Halyard architecture](../media/ARCHITECTURE.md)

## 1. Executive recommendation

Capstan should not model "resources" as one scalar budget. It should specify a **dimensioned resource contract** and keep at least three fundamentally different classes separate:

1. **Cumulative consumption** — work/fuel, input bytes processed, output bytes produced, decoded units and similar monotonic counters. A successful charge is never released.
2. **Live/peak occupancy** — retained bytes, live objects, queue slots, worker slots, open handles and other resources that are acquired and later released. The instantaneous usage must remain within a limit; the peak is the maximum over the execution.
3. **Environment-dependent quantities** — wall-clock time, CPU cycles, energy, I/O latency and scheduler delay. These require a platform/measurement model and cannot be inferred from a source-level work count alone.

The first Capstan subset should combine **runtime-enforced cumulative fuel and byte/work budgets** with **failure-atomic live-resource leases**. Static analysis should initially target a deliberately small pure subset: scalar and bounded collection programs with explicit size parameters, direct calls, structurally bounded recursion and statically bounded loops. Where the static analyser cannot derive a sound bound, the result is unknown, never zero or an optimistic estimate; the runtime budget remains the enforcement boundary.

This recommendation aligns with existing Capstan work. CCAM already has a shared execution-step budget in its selected evaluator subset. Halyard Core has a sequential prototype with a twelve-dimensional live aggregate ledger, one-shot reservation handles, and a separate monotonic input/output/decoded/work consumption budget. That prototype is explicitly not concurrency-safe, its public struct fields remain mutable, and its live accounting is not yet allocator-exact or coupled to every parser/sample/frame allocation. It is a useful experiment, not evidence that Capstan currently provides a complete resource guarantee.

## 2. Review method and scope

This is a targeted review of primary papers, formal systems and official implementation documentation located on 2026-11-26. It is not a systematic review or exhaustive search of every resource-aware language and WCET tool. Sources were selected to cover automatic amortised resource analysis (AARA), sized types and implicit complexity, region inference, resource-aware concurrency, static WCET analysis and dynamic fuel/quota enforcement.

The survey distinguishes:
- a **static upper-bound proof** from a runtime limit;
- a runtime limit from an empirical maximum;
- cumulative work from peak/live occupancy;
- source-level cost from target-specific elapsed time;
- a formal model theorem from a theorem about the compiled implementation.

## 3. Resource semantics: the dimensions must be explicit

A resource contract is meaningful only if it specifies the measured quantity, unit, accounting point, composition rule, overflow behaviour and enforcement boundary.

| Resource class | Examples | Natural composition | Release? | Typical evidence |
|---|---|---|---|---|
| Cumulative work | evaluator steps, abstract fuel, parser work units | Add across sequential work; sum across all tasks for total work | No | Static cost semantics and/or dynamic monotonic meter |
| Cumulative traffic | bytes read, bytes emitted, decoded samples/pixels | Add across operations and calls | No | Adapter/source/sink counters with preflight |
| Live occupancy | retained bytes, live objects, queue slots, handles, workers | Track current usage; peak is maximum over time | Yes, on a verified lifecycle transition | Atomic reservation/lease protocol and ownership |
| Stack occupancy | call frames, stack bytes, recursion depth | Peak along a call path; concurrency has per-task and aggregate dimensions | On return/unwind | Static recursion/depth proof plus runtime guard |
| Wall-clock time | elapsed execution time, deadline | Not generally additive without scheduler/parallelism assumptions | No | Target-specific WCET analysis or measurement with limited claims |
| CPU cycles | processor cycles | Target and microarchitecture dependent | No | Hardware-specific timing model/counters |
| Energy | joules, battery use | Platform/device dependent | No | Device-specific model and calibrated measurement |
| External resources | file descriptors, sockets, GPU buffers, processes | Live count/bytes plus operation/work budgets | Yes, if close/release succeeds | Host-adapter accounting and OS contract |

### 3.1 Cumulative and live resources are different algebras

For a cumulative dimension c, maintain a monotonic counter u and limit L. A charge q is admitted only if q is non-negative and q <= L - u; it then commits u := u + q. There is no release operation. A failed preflight must not partially charge a multi-dimensional request.

For a live dimension l, maintain current usage u and limit L. A reservation q is admitted only if q is non-negative and q <= L - u, and creates an owned lease. Release is a separate transition that consumes that lease exactly once and decrements the matching usage. A stale, forged, duplicated or already-consumed lease must not decrement the ledger again.

These two models cannot safely be conflated. Releasing a work/fuel charge would permit budget recycling and could enable an infinite computation. Failing to release a live resource lease would create a leak; releasing it twice could undercount actual occupancy.

### 3.2 Peak memory is not cumulative allocation

Cumulative allocated bytes and peak live bytes answer different questions. A program may allocate and free a large amount over time while keeping peak memory low; conversely, it may allocate little cumulatively but retain a large working set. If allocation and copying temporarily overlap, the peak includes both old and new buffers until commit completes.

A compositional peak-memory summary therefore needs retained-state information, not merely a sum of per-function allocation totals. For a simple sequential composition, the peak of the second component is offset by memory retained from the first; for concurrent composition, simultaneous live sets may add. A precise algebra must state ownership transfer and release points.

### 3.3 Work, span and latency differ under concurrency

Total work is the sum of operations across tasks. Span is the critical-path work under an idealised unlimited-processor model. Wall-clock latency additionally depends on the scheduler, processor count, OS, I/O and interference. A work bound alone does not imply a deadline bound. Likewise, bounding each task's local allocation does not bound aggregate memory if many tasks run simultaneously.

## 4. Automatic amortised resource analysis (AARA)

Hofmann and Jost introduced a type-based method for deriving worst-case resource bounds using potential annotations. Later work extended AARA to polynomial bounds, multiple resource metrics, imperative features, higher-order functions, lazy evaluation, concurrency and probabilistic settings. Resource Aware ML (RAML) provides a practical implementation for OCaml-like programs; its documentation describes automatic upper/lower bounds for evaluation steps, allocated heap cells and user-defined ticks, with inference reduced to linear optimisation.

The 2022 review by Hoffmann and Jost surveys two decades of the technique and its extensions. It is an important baseline: Capstan should not claim novelty for deriving compositional resource bounds from types or potential functions.

**Strengths**
- Bounds can be compositional across functions and data structures.
- Potential functions account for amortised costs that are not visible from one operation in isolation.
- Multiple resource metrics and polynomial bounds are possible.
- The proof argument can connect a typing derivation to a formal cost semantics.
- A derived type/constraint solution can act as a certificate or reproducible analysis artefact.

**Limitations and counterexamples**
- Bound inference is undecidable in general. A practical analyser is necessarily incomplete and may fail to derive a bound for a valid program.
- Precision depends on the supported language, data structures, size measures, recursion and evaluation strategy. Mutable aliases, dynamic dispatch, callbacks, foreign calls and unbounded loops complicate or defeat simple summaries.
- A sound bound on abstract evaluation steps is not automatically a bound on native CPU cycles, wall-clock time, energy or OS service latency.
- A bound on allocated cells is not automatically a bound on peak resident memory unless object sizes, headers, allocator fragmentation, copies and runtime metadata are included.
- Unknown or unanalysable code must not silently inherit a caller's budget or receive a zero-cost summary.

AARA is a strong candidate for a **static work/allocation analysis of a small source subset**, not a replacement for runtime accounting of external resources.

## 5. Sized types and implicit computational complexity

Sized types annotate data types with information about the size of values. Hughes, Pareto and Sabry use them to reason about properties such as termination, productivity and bounded behaviour in reactive systems. Later work by Avanzini and Dal Lago combines sized-type analysis, a ticking transformation and constraint solving to automate complexity analysis of higher-order programs.

**Strengths**
- Size information is naturally propagated through structural recursion and data constructors.
- It can support termination and productivity arguments as well as resource bounds.
- Size-indexed function contracts can describe how output sizes relate to input sizes.
- Higher-rank size polymorphism and constraint solving can handle examples beyond simple first-order recursion.

**Limitations and counterexamples**
- A proof that recursion structurally decreases a size measure does not by itself bound the cost tightly; the recurrence and per-step cost still matter.
- A function may terminate on every input but take exponential or otherwise unacceptable time.
- A size bound on a list or tree does not automatically bound work hidden in a callback, foreign function, dynamic dispatch or I/O operation.
- A size bound on a value does not establish a bound on allocator overhead, peak live memory or platform latency.
- Size analyses are language- and recursion-discipline-specific; arbitrary unrestricted recursion cannot be made statically bounded by adding a size annotation alone.

Sized types are useful for the **input/output size and recursion discipline** of the first static subset. They should complement a cost analysis, not be mistaken for a complete resource calculus.

## 6. Region-based memory management

Tofte and Talpin's region inference uses a type-and-effect analysis to determine region allocation and deallocation points. A stack of regions can reclaim groups of values at once without tracing garbage collection; the system includes a soundness argument relating region deallocation to a standard semantics. The ML Kit provides an important implementation case study, and later retrospective work records practical experience with region inference and region-based memory management.

**Strengths**
- Region lifetimes can make large classes of allocation/deallocation behaviour explicit.
- A sound region type system prevents deallocation while values in the region remain live.
- Bulk release can provide predictable reclamation costs and avoid per-object GC work.
- Regions are a useful implementation technique for parser arenas, frame-local scratch data and request-scoped allocations.

**Limitations and counterexamples**
- Region safety does not imply that a region has a finite size. A long-lived region can grow without bound.
- A program may be type-safe yet retain too much data in a region, producing a space leak.
- Region inference can be imprecise for values whose lifetimes cross control-flow or abstraction boundaries.
- Regions do not bound cumulative CPU work, output bytes, I/O, task count or wall-clock time.
- A region discipline does not replace explicit accounting for external buffers, OS handles or memory allocated by foreign libraries.

Regions are a candidate **memory-lifetime mechanism**, not a universal resource-analysis solution. Capstan should compare them with GC/ownership strategies on actual peak-live-memory workloads and report region retention separately from cumulative allocation.

## 7. Worst-case execution-time (WCET) analysis

Static WCET analysis combines program control-flow/value analysis with a model of the target processor. Tools such as aiT use abstract interpretation for value, cache and pipeline analysis, together with path analysis, to derive safe upper bounds under their platform and software assumptions. Industrial case studies demonstrate that this can be applied to safety-critical programs.

**Strengths**
- It addresses a question that abstract instruction fuel does not: a target-specific upper bound on execution time.
- It can account for machine-level control flow, caches and pipelines when the hardware model is sufficiently accurate.
- It can produce a bound suitable for a schedulability analysis when combined with a real-time task model.

**Limitations and counterexamples**
- The result is target-specific. Changing compiler, flags, binary, processor, cache configuration or relevant OS assumptions may invalidate it.
- Modern out-of-order, speculative and multicore processors make accurate modelling difficult; shared caches, memory controllers, interrupts and interference complicate analysis.
- Loop bounds, indirect calls, recursion and infeasible paths may require annotations or cause analysis failure.
- Sound static bounds can be pessimistic; measurement-based timing tests cannot replace a proof of an upper bound.
- A WCET bound for a function does not automatically compose into a deadline guarantee without scheduler and interference analysis.

WCET is not the first Capstan resource feature. It is a later, platform-specific assurance path for carefully selected real-time profiles. Capstan should not describe instruction fuel as WCET or treat a benchmark's maximum observed latency as a hard upper bound.

## 8. Dynamic fuel and quota enforcement

Dynamic metering provides a practical fail-safe for code that cannot be statically bounded. Wasmtime's fuel mechanism instruments WebAssembly execution so a configured fuel budget can halt execution with a trap or yield periodically in asynchronous mode. Its documentation explicitly notes that fuel is an abstract deterministic unit, not elapsed time; host functions do not automatically consume guest instruction fuel, and reported consumption on traps may be imprecise even though non-trapping execution remains bounded.

This is a useful comparator for Capstan's CCAM step budget and for host-adapter accounting.

**Strengths**
- It enforces a hard ceiling in a deterministic abstract unit, independent of whether static analysis can infer a bound.
- A shared budget can cover recursive calls and nested guest execution if the meter is not reset at call boundaries.
- It supports fail-closed admission and predictable exhaustion behaviour.
- It can be extended with explicit host-call charges for work performed outside the metered instruction stream.

**Limitations and counterexamples**
- Fuel is not wall-clock time, CPU cycles or energy. One abstract unit may have different physical cost on different targets.
- A host function that performs a large amount of work without charging the meter bypasses the guest's accounting.
- Fuel does not bound live memory, file descriptors, sockets, queue occupancy or external output unless those resources have separate budgets.
- If nested execution or callbacks receive fresh budgets, the total work may exceed the intended process-level ceiling.
- A trap may not provide exact accounting of the final partially executed operation; callers must not rely on a post-trap counter as an exact billing ledger unless the runtime guarantees it.

Dynamic quotas have a similar limitation: they can reject operations once a limit would be exceeded, but they do not prove that the application is correct, that all resource paths are metered, or that the limit is appropriate. Admission must happen before the side effect or allocation it is intended to bound.

## 9. Resource-aware session types and concurrent composition

Das, Hoffmann and Pfenning's work on resource-aware session types combines linear session types with amortised resource analysis. Protocol constructors carry potential, allowing communicating processes to transfer resources and derive worst-case bounds on total work. Their formal cost semantics tracks message exchanges and supports compositional analysis of interacting processes.

Later work extends this direction, including probabilistic resource-aware session types.

**Strengths**
- Resource contracts can be attached to protocol interfaces, not only individual functions.
- Linear ownership of channels/messages provides a natural place to transfer accounting potential.
- It addresses an important limitation of sequential AARA: communicating processes must be analysed compositionally.
- Work and protocol interaction can be bounded together for a restricted concurrent calculus.

**Limitations and counterexamples**
- A bound on total message/work cost does not automatically bound peak memory, queue occupancy or wall-clock latency.
- The analysis relies on the session-type protocol discipline and its formal cost semantics; arbitrary shared-memory concurrency is outside the same model.
- Scheduler fairness and liveness are separate obligations. A finite work bound does not prove that a task will be scheduled promptly.
- A process can be resource-bounded and still deadlock or starve if protocol/liveness assumptions fail.
- The current Capstan concurrency runtime is not yet a production scheduler; a model-level result cannot be represented as a runtime guarantee without refinement.

This is the strongest direction for a future **protocol-aware resource contract**, but it should follow the bounded task/channel semantics and ownership model rather than be introduced as an isolated annotation system.

## 10. Comparative matrix

| Approach | Primary resource/property | Static/dynamic | Compositional strengths | Main assumptions | Counterexample / limitation |
|---|---|---|---|---|---|
| AARA / RAML | Work, allocation, selected user metrics | Static | Function/data-structure potential; polynomial and higher-order extensions | Supported language, size measures and cost semantics | Unknown callback/FFI or unsupported aliasing prevents a sound inferred bound |
| Sized types | Input/output size, termination/productivity; supports complexity bounds | Static | Structural size relations through constructors and recursion | Size-indexed data and supported recursion discipline | Termination does not imply an acceptable cost or bounded I/O |
| Region inference | Allocation lifetime and bulk reclamation | Static inference + runtime region operations | Region scopes and lifetime safety | Region discipline and sound escape/lifetime analysis | One long-lived region can grow without bound |
| WCET analysis | Target-specific worst-case elapsed execution time | Static, hardware-model based | Call/control-flow and processor-state analysis | Exact binary/toolchain and credible processor/OS model | Abstract instruction count does not equal target cycles; multicore interference complicates bounds |
| Fuel metering | Abstract guest work | Dynamic | Shared monotonic budget across nested guest execution | Every guest/host work path is metered | An unmetered host call can do unbounded work |
| Live quota/lease ledger | Current retained/occupied resources | Dynamic | Multi-dimensional atomic admission and explicit release ownership | Every allocation/queue/handle path is coupled to the ledger | Public mutable counters or missing release/acquire paths permit undercount/leaks |
| Resource-aware session types | Total work across message-passing processes | Static | Protocol-level potential transfer and linear channels | Session-typed communication and cost semantics | Does not by itself bound queue peak memory, wall-clock or arbitrary shared memory |
| Empirical benchmarking | Observed time/memory/throughput | Measurement | Compares concrete end-to-end implementations | Representative workloads, environment and statistical method | Observed maximum is not a sound upper bound for unseen executions |

## 11. Recommended Capstan resource model

### 11.1 Keep four evidence states separate

Every resource dimension should carry one of these evidence states:

- **Proved upper bound:** a sound static derivation or theorem applies to the exact program and stated assumptions.
- **Runtime-enforced ceiling:** the runtime/adapter checks and rejects before the resource-consuming action commits.
- **Measured observation:** a benchmark or test observed a value; it is not a worst-case guarantee.
- **Unknown/unbounded:** no valid bound or enforcement evidence exists. Safe composition must preserve this state or reject.

A static estimate must not be promoted to a proved upper bound. A runtime ceiling does not imply that the workload will complete successfully within the ceiling.

### 11.2 Minimal first resource vector

For the first Safe-profile experiment, use this deliberately small vector:

| Dimension | Semantics | Initial mechanism |
|---|---|---|
| Evaluator work | Monotonic abstract steps | One shared fuel counter across calls/recursion |
| Input bytes | Cumulative bytes admitted/consumed | Source/adapter preflight and monotonic charge |
| Output bytes | Cumulative bytes committed | Sink preflight before append/write |
| Decoded units | Cumulative parser/decoder outputs | Charge before materialising each bounded unit |
| Retained bytes | Current live payload/storage | Owned reservation lease with exact-once release |
| Allocation objects | Current admitted logical objects | Live lease initially; do not call it allocator-exact until runtime coupling exists |
| Call depth/stack | Peak active frames/stack bytes | Preflight depth/stack bound plus runtime guard |

Do not include energy, arbitrary wall-clock deadlines, GPU/device memory, general OS process counts or a universal network budget in this first slice. They require distinct platform contracts.

### 11.3 Separate cost summaries from live leases

A function summary should expose at least:
- cumulative upper-bound costs by dimension;
- required input-size parameters and preconditions;
- peak/live occupancy requirements and release/lifetime conditions;
- external effects and adapter assumptions;
- evidence state for each bound.

For cumulative costs, sequential composition adds charges; a branch uses the maximum of its alternatives for a worst-case bound; a loop multiplies or solves a recurrence using a proven iteration bound. Recursion requires a sound recurrence/termination argument. Unknown callees produce unknown cost unless a checked summary is supplied.

For live resources, a summary must track which resources remain live across the call boundary. A simple sum of allocations is not a peak-memory summary. Concurrent composition must account for overlapping reservations and shared resources. A live lease must not be released merely because a function returns if ownership has been transferred to its caller.

### 11.4 Host and foreign-function boundary

Every host/FFI operation needs a versioned cost/resource contract that states:
- maximum input/output bytes and object counts;
- cumulative work charge or a declared unknown cost;
- live resources acquired and exact release owner;
- blocking, cancellation, deadline and failure semantics;
- whether partial side effects can occur before failure;
- the OS/device/library assumptions required for any stronger bound.

A host call that cannot be bounded must remain an explicit unknown/unbounded operation and be excluded from the Safe profile or constrained by an independently enforced process/adapter quota. A guest fuel meter alone is not sufficient.

## 12. Initial formal obligations

1. **Cost semantics:** define observable work and resource consumption for the exact source/CCAM subset.
2. **Monotonicity:** cumulative counters never decrease, reset at calls, wrap or saturate into an accepted state.
3. **Static soundness:** if the analyser reports bound B, every execution under the stated input/environment assumptions consumes no more than B.
4. **Composition:** sequential, branch, loop, recursion and call summaries preserve the bound; unknown summaries cannot reduce it.
5. **Peak/live correctness:** every acquisition is admitted before the resource is acquired; every release corresponds to an owned live lease and occurs at most once.
6. **Failure atomicity:** a failed multi-dimensional reservation changes no counter; failed output/append does not publish a partial result unless the contract explicitly allows it.
7. **Allocator correspondence:** logical object/byte charges correspond to actual allocation size, metadata, alignment, copies and allocator retention before any physical-memory claim is made.
8. **Concurrency accounting:** simultaneous task usage is charged to a shared aggregate ledger; task-local limits cannot bypass the process limit.
9. **Host-boundary accounting:** no unmetered adapter/FFI path can perform unbounded work or acquire unaccounted resources.
10. **Implementation refinement:** the concrete compiler/runtime/adapter preserves the abstract resource transitions and failure outcomes.

## 13. Benchmark and falsification proposal

### 13.1 Question

Does separating cumulative work/traffic budgets from live-resource leases prevent resource-accounting bypasses that a single scalar budget or per-object limit permits, while keeping overhead acceptable on representative Capstan workloads?

### 13.2 Baselines

- **Capstan runtime-only:** dynamic fuel/byte limits and live lease ledger, no static cost inference.
- **Capstan static subset:** static function summaries where supported, with the same runtime ceilings as a backstop.
- **RAML/AARA:** selected pure first-order/higher-order list and tree workloads where the language mapping is fair; report unsupported Capstan features rather than forcing them into the baseline.
- **Wasmtime fuel:** compare abstract instruction fuel behaviour on equivalent WebAssembly workloads, not as a memory or wall-clock guarantee.
- **Rust or C++ reference implementation:** compare end-to-end throughput, memory and error behaviour on identical parser/byte-processing tasks, with equivalent bounds and sanitizers documented.
- **Region-based variant:** only if the workload can be implemented fairly in a region system; compare peak live memory and retention, not just allocation count.

These are different baselines for different questions; no one system is a universal comparator.

### 13.3 Workloads and adversarial cases

1. Pure list/tree transformations with known size parameters and structural recursion.
2. Bounded TLV/RIFF-like parser with exact input, chunk-count, nesting and decoded-unit limits.
3. Cumulative amplification: many individually valid chunks whose total decoded output exceeds the aggregate limit.
4. Live occupancy: queue saturation, retained-buffer fan-out and copy-on-commit overlap.
5. Failure injection at each reservation, allocation, append and release transition.
6. Recursive/direct-call workloads at the exact fuel/depth boundary and one unit over.
7. A bounded concurrent producer/consumer case once the supported channel semantics exist.

For each workload, include valid positive controls, malformed/over-limit negative controls, exact-boundary cases and an independent correctness oracle.

### 13.4 Metrics

- rejection correctness and false rejection rate;
- declared upper bound versus observed cost and bound slack;
- peak live bytes, cumulative allocation and retained bytes reported separately;
- allocation count, object count, queue high-water mark and lease count;
- throughput and p50/p95/p99 latency;
- fuel/ledger overhead against an unmetered but semantically equivalent reference;
- compile time, analysis time, proof/checker time and annotation burden;
- failure atomicity and residual state after each injected failure.

Measured maxima are empirical observations, not proofs of worst-case bounds. Static bounds are assessed for soundness and tightness separately.

### 13.5 Falsification conditions

The proposed model fails its primary safety hypothesis if any accepted execution exceeds a declared enforced ceiling, if a failed multi-dimensional reservation partially mutates the ledger, if a resource can be acquired without a charge, or if duplicate/stale release reduces live usage. It fails its practical hypothesis if the overhead or rejection rate exceeds a preregistered threshold on the selected representative workloads. Both outcomes must be published.

## 14. Open design decisions

1. Which cost semantics and input-size measures should be normative for the first scalar/collection subset?
2. Which AARA/sized-type techniques are tractable for Capstan's imperative, mutable and C-backed implementation boundary?
3. How should summaries express unknown costs, recursive functions, callbacks and higher-order functions?
4. Which live dimensions should be allocator-exact, and which are initially logical quotas?
5. How will lease ownership be made opaque and affine/linear in the language?
6. How are host adapter costs charged when an operation partially succeeds or is cancelled?
7. Which concurrency semantics are stable enough for resource-aware session contracts?
8. Which platform/hardware profiles, if any, can support WCET claims?
9. What is the smallest benchmark set that distinguishes static analysis precision from runtime enforcement?

These decisions require coordination with the F1, CCAM, concurrency and Halyard owners before any normative language or runtime changes.

## 15. Conclusion

The literature does not support one universal resource calculus that statically proves time, memory, I/O, concurrency and platform latency for arbitrary systems programs. The strongest techniques are specialised: AARA derives compositional work/space bounds for supported programs; sized types express structural size/termination information; regions manage lifetimes; WCET analysis uses target-specific machine models; fuel and quotas enforce dynamic ceilings; resource-aware session types extend cost reasoning to restricted communicating processes.

Capstan's defensible path is to define these dimensions precisely, combine static bounds where they are sound with runtime admission where they are not, and preserve unknown rather than manufacture guarantees. The first experiment should prove and test the separation between monotonic cumulative budgets and failure-atomic live-resource leases, then add a small static analysis for a bounded source subset. No general resource-boundedness claim is warranted until every relevant compiler, allocator, host and concurrency boundary is accounted for.

## 16. Bibliography and primary references

1. Jan Hoffmann and Steffen Jost. **Two Decades of Automatic Amortized Resource Analysis.** Mathematical Structures in Computer Science (2022). [Paper](https://www.cs.cmu.edu/~janh/assets/pdf/HoffmannJ21.pdf).
2. Jan Hoffmann, Klaus Aehlig and Martin Hofmann. **Resource Aware ML.** CAV (2012). [Paper](https://www.cs.cmu.edu/~janh/assets/pdf/HoffmannAH12a.pdf); [RAML tool and supported metrics](https://www.raml.co/about/).
3. Jan Hoffmann. **Types with Potential: Polynomial Resource Bounds via Automatic Amortized Analysis.** PhD thesis (2011). [Dissertation](https://www.cs.yale.edu/homes/hoffmann/papers/hoffmann11diss.pdf).
4. David M. Kahn and Jan Hoffmann. **Automatic Amortized Resource Analysis with the Quantum Physicist's Method.** PACMPL ICFP (2021). [Paper](https://doi.org/10.1145/3473581).
5. John Hughes, Lars Pareto and Amr Sabry. **Proving the Correctness of Reactive Systems Using Sized Types.** POPL (1996), pp. 410–423. [Paper](https://doi.org/10.1145/237721.240882).
6. Martin Avanzini and Ugo Dal Lago. **Automated Sized-Type Inference and Complexity Analysis.** PACMPL ICFP (2017). [Paper](https://doi.org/10.1145/3110287); [preprint](https://arxiv.org/abs/1704.05585).
7. Mads Tofte and Jean-Pierre Talpin. **Region-Based Memory Management.** Information and Computation 132(2) (1997), pp. 109–176. [Paper](https://ropas.snu.ac.kr/lib/dock/ToTa1997.pdf).
8. Mads Tofte, Lars Birkedal, Martin Elsman and Niels Hallenberg. **A Retrospective on Region-Based Memory Management.** Higher-Order and Symbolic Computation 17 (2004), pp. 245–265. [Paper](https://doi.org/10.1023/B:LISP.0000029446.78563.a4).
9. Per Stenström et al. **The Worst-Case Execution Time Problem—Overview of Methods and Survey of Tools.** ACM Transactions on Embedded Computing Systems (2008). [Publication DOI](https://doi.org/10.1145/1347375.1347389).
10. Jean Souyris et al. **Computing the Worst Case Execution Time of an Avionics Program by Abstract Interpretation.** WCET Workshop / OASIcs (2008). [Paper](https://doi.org/10.4230/OASIcs.WCET.2005.810).
11. Ankush Das, Jan Hoffmann and Frank Pfenning. **Work Analysis with Resource-Aware Session Types.** LICS (2018), pp. 305–314. [Paper](https://doi.org/10.1145/3209108.3209146).
12. Ankush Das, Di Wang and Jan Hoffmann. **Probabilistic Resource-Aware Session Types.** PACMPL POPL (2023). [Paper](https://doi.org/10.1145/3571259).
13. Wasmtime. **Fuel Consumption Configuration and Store APIs.** Official documentation, accessed 2026-11-26. [Config](https://docs.wasmtime.dev/api/wasmtime/struct.Config.html); [Store](https://docs.wasmtime.dev/api/wasmtime/struct.Store.html).
