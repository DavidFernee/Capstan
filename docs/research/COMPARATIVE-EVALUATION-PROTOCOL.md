# Reproducible comparative evaluation protocol for Capstan

**Status:** initial protocol and preregistration template; no benchmark results or competitive claim  
**Issue:** [#223](https://github.com/DavidFernee/Capstan/issues/223)  
**Research authority:** [Programming-Language Research Agenda](PROGRAMMING-LANGUAGE-RESEARCH-AGENDA.md)  
**Evidence register:** [RESEARCH-REGISTER.md](RESEARCH-REGISTER.md)  
**Reviewed against:** `main` at the revision used to create this document (2026-11-26)

## 1. Purpose and non-goals

This protocol defines how Capstan's proposed differentiators are to be compared with established languages, compilers, verification systems and runtime designs. It is intended to prevent benchmark selection after results are known, incomparable measurements being collapsed into one score, and design intentions being reported as implemented guarantees.

This is an initial protocol. Candidate systems and workloads below are a shortlist, not a final frozen benchmark suite. Final selection must be reconciled with the related-work surveys in issues #220–#222 and the exact capability of the tested Capstan revision. No performance result, security superiority, novelty or publication readiness is asserted.

The evaluation does **not** attempt to rank programming languages overall. It evaluates named properties on named workloads, targets and toolchain versions. A system may be stronger on one dimension and weaker on another.

## 2. Research questions and hypotheses

The initial programme is organised around separable questions:

- **RQ1 — Guarantee coverage:** Which explicitly specified safety, authority, information-flow and resource properties are enforced, proved, dynamically checked, delegated to the host, or left unsupported?
- **RQ2 — Residual risk:** Which vulnerability classes or failure modes remain expressible under the tested language profile and library/runtime boundary?
- **RQ3 — Resource contracts:** For workloads with declared limits, are bounds sound, how tight are they, and what happens at and beyond each limit?
- **RQ4 — Execution cost:** What are the runtime, memory, binary-size and startup costs of the measured implementations on equivalent workloads?
- **RQ5 — Engineering cost:** What are compile-time, annotation, proof-authoring, diagnostic and maintenance costs for achieving the same specified outcome?
- **RQ6 — Reproducibility:** Can an independent party regenerate the measurements and validate the stated claims from the released artefacts?

Candidate hypotheses must be registered before the corresponding measurement run. Example forms:

- H-GUARANTEE: on a specified class of hostile-input tasks, a named Capstan profile rejects a defined set of invalid states that the selected baseline configuration accepts or leaves to runtime checks.
- H-RESOURCE: preflighted aggregate admission prevents a named cumulative-budget bypass while keeping peak memory and rejection work within a preregistered tolerance.
- H-COST: for a defined workload and target, the guarantee mechanism incurs a measured overhead distribution relative to a baseline with equivalent observable behaviour.

Each hypothesis must identify a falsifying observation. A result that is mixed, inconclusive or negative is retained, not silently replaced with a more favourable workload.

## 3. Comparison principles

1. **Equivalent task, not equivalent line count.** Implementations must satisfy the same externally observable task and input/output contract.
2. **Best-practice baseline.** Use idiomatic, maintained configurations and appropriate safety/verification tools. Do not deliberately weaken a baseline.
3. **Separate assurance dimensions.** Report guarantees, residual risks, performance and developer effort independently.
4. **No unsupported inference.** A compiler warning, test pass, sanitizer run, model theorem and implementation-refinement proof are distinct evidence types.
5. **Pin everything material.** Compiler, linker, libraries, dependencies, flags, OS, kernel, hardware, datasets, seeds and scripts are versioned.
6. **Equal optimisation opportunity.** Document tuning effort and allow each system reasonable idiomatic optimisation without changing the task contract.
7. **Report distributions.** Publish raw observations and dispersion; do not report only a best run or aggregate score.
8. **Pre-register exclusions.** State which systems, features, workloads and measurements are omitted and why before results are examined.
9. **Preserve negative results.** Publish regressions, failed hypotheses, unsupported cases and measurement limitations.
10. **Scope every claim.** Results apply only to the tested revision, profile, workload, configuration and target.

## 4. Candidate baseline families

Final choices are provisional pending the related-work surveys and workload-specific feasibility review.

| Family | Candidate systems | Appropriate comparison questions | Important qualification |
|---|---|---|---|
| Memory-safe systems languages | Rust; Swift where its ownership model is relevant | Ownership/lifetime guarantees, unsafe boundary, runtime and compile-time cost | Compare idiomatic safe subsets and disclose every `unsafe` / foreign boundary |
| Mature systems languages | C++ with current safety tooling; Zig | Performance, explicit allocation/error handling, tooling and residual unsafe operations | Pin language edition, compiler and enabled diagnostics/sanitizers |
| High-assurance language/toolchain | Ada/SPARK | Contracts, static analysis, proof coverage and proof effort | Separate Ada language features from SPARK-analyzable subset and tool qualification |
| Managed/runtime systems | Java or another managed runtime where workload-relevant | Memory lifecycle, runtime checks, throughput, startup and memory overhead | GC/runtime assumptions differ; do not treat this as a direct systems-language substitute |
| Portable sandboxed execution | WebAssembly toolchain/runtime | Validation, sandbox boundary, portability and host capability mediation | State the exact engine, host API and sandbox configuration |
| Specialist verification tools | Lean 4 or another proof assistant for formal subproblems | Proof expressiveness, checker trust, proof effort and reproducibility | Not a general-purpose runtime competitor; compare only on the formal task |

A baseline is included only when it can implement the same task without changing its essential semantics. If no fair equivalent exists, mark the comparison not applicable rather than inventing a proxy.

## 5. Workload strata

Select workloads from the following strata. The exact cases and inputs must be committed before measurements.

### 5.1 Semantic and safety conformance

- Checked integer arithmetic, boundary values and deterministic trap/error behaviour.
- Ownership/lifetime transitions, invalidated handles and resource cleanup.
- Context-sensitive output and serialization boundaries.
- Parser validation, malformed input, duplicate/unknown fields and limit boundaries.
- Capability/authority checks, including missing authority and confused-deputy cases.

For each case publish the normative expected result, positive control, negative control and oracle.

### 5.2 Adversarial resource behaviour

- Nested and cumulative input amplification.
- Many individually valid objects that exceed an aggregate budget.
- Deep nesting, long sequences, oversized declared lengths and truncated input.
- Allocation failure at each reservation/commit boundary.
- Queue saturation, cancellation and cleanup under bounded concurrency where supported.

Measure correctness of admission/rejection as well as the cost of reaching the decision.

### 5.3 Representative systems workloads

Use a small, transparent set of tasks: bounded parsing/validation, byte transformation, structured data processing, compiler-front-end workloads, and media/image/audio primitives where relevant. Include both small latency-sensitive inputs and large throughput-oriented inputs. Avoid workloads that primarily measure an unrelated library or platform component.

### 5.4 Formal and assurance workloads

Use matched properties rather than comparing proof counts. Candidate tasks include arithmetic safety, state-machine invariants, bounded evaluator semantics and refinement of a concrete operation to a reference model. Record theorem statements, assumptions, axioms, proof dependencies, checker versions and trusted computing base.

### 5.5 Developer-experience workloads

A preregistered set of representative changes should measure time-to-correct-implementation, diagnostic localisation, annotation burden, proof effort, iteration count and maintenance changes. Use multiple participants where possible; disclose experience level and avoid generalising from a single author.

## 6. Metrics and operational definitions

Do not combine these into a single score.

| Dimension | Metric | Operational definition |
|---|---|---|
| Guarantee coverage | Property disposition | For each property: statically enforced, proved in model, refinement-proved, dynamically enforced, host-delegated, tested only, unsupported or unknown |
| Residual risk | Adversarial outcome | Count and classify accepted-invalid, rejected-valid, crash, hang, resource-limit breach and oracle disagreement per fixed corpus |
| Resource soundness | Bound violations | Number of executions exceeding a declared bound under the stated measurement model; report assumptions and instrumentation limits |
| Resource tightness | Bound slack | Declared bound minus observed consumption, with units and per-workload distribution |
| Runtime | Throughput | Completed contract-equivalent operations per second after warm-up |
| Runtime | Latency | p50, p95, p99 and maximum observed latency, with sample count and measurement method |
| Memory | Peak resident and allocated bytes | OS peak RSS plus allocator-level requested/retained bytes where instrumentation is comparable; report separately |
| Allocation | Allocation count/volume | Calls and requested bytes, separated by size class where available |
| Startup | Cold start | Process launch to first contract-valid result; disclose filesystem/cache state |
| Build | Compile/build time | Clean build wall time and CPU time, with dependency cache policy |
| Artifact | Binary size | Final executable and separately reported debug/symbol artefacts |
| Proof | Proof effort | Human hours, proof lines only as descriptive metadata, machine-check time, checker and dependency versions |
| Developer effort | Task completion | Time, iteration count, defect rate and independent review outcome under a fixed task brief |
| Reproducibility | Reproduction success | Independent clean reproduction of scripts, outputs and claim ledger |

For each metric, publish raw samples, units, exclusions, instrumentation overhead and uncertainty. If measurement methods differ materially between systems, report separate measures rather than presenting false equivalence.

## 7. Experimental procedure

1. **Freeze the question.** Record the research question, hypothesis, falsification condition and intended claim.
2. **Freeze the contract.** Publish task semantics, accepted/rejected inputs, observable outputs and correctness oracle.
3. **Select baselines.** Record system/version/configuration and justify why it is a fair, strong comparator.
4. **Freeze workloads.** Version source inputs, generated inputs, corpus hashes, seeds and workload parameters.
5. **Freeze environment.** Record CPU model/microcode, RAM, storage, OS/kernel, compiler/linker, libraries, power mode and relevant environment variables.
6. **Build cleanly.** Record exact source commit, build commands, flags, dependency lockfiles and build artefact hashes.
7. **Validate correctness first.** Run conformance and oracle checks before timing. Invalid or semantically divergent implementations are not performance-comparable.
8. **Warm up and measure.** State warm-up policy, repetitions, process isolation, concurrency, sample count and stopping rule before execution.
9. **Retain raw output.** Store machine-readable observations and logs; derive summaries with versioned scripts.
10. **Repeat independently.** A second operator or clean environment reproduces at least the primary result and all claimed regressions.
11. **Review claims.** Map each sentence in the result summary to raw data, a test, a theorem or an explicit assumption.

Do not compare results collected on different hardware as if they were directly comparable. Cross-machine results may be reported as separate strata.

## 8. Reproduction package

Each experiment directory should contain, at minimum:

- `README.md`: question, contract, reproduction commands and expected artefacts.
- `manifest.json`: schema-versioned environment, source revisions, tools, flags and workload identifiers.
- `workloads/`: source inputs or deterministic generators, licence and SHA-256 hashes.
- `scripts/`: build, correctness, measurement and analysis commands.
- `raw/`: unmodified machine-readable samples and relevant logs.
- `results/`: generated tables/plots and the script that produced each.
- `claims.md`: scoped claims, evidence links, assumptions, limitations and negative results.

A minimal manifest should include:

```json
{
  "schema": "capstan-evaluation-manifest/1",
  "experiment_id": "REPLACE-BEFORE-USE",
  "source": {
    "repository": "https://github.com/DavidFernee/Capstan",
    "commit": "REQUIRED_IMMUTABLE_SHA",
    "dirty_worktree": false
  },
  "environment": {
    "os": "REQUIRED",
    "kernel": "REQUIRED",
    "cpu": "REQUIRED",
    "memory_bytes": 0
  },
  "toolchains": [],
  "workloads": [],
  "commands": [],
  "seeds": [],
  "measurement": {
    "warmup_policy": "REQUIRED",
    "repetitions": 0,
    "raw_output_format": "REQUIRED"
  }
}
```

The example is a template, not a valid completed experiment. A reproduction must reject missing required fields rather than silently substitute local defaults.

## 9. Analysis and reporting

- Publish per-workload results before any cross-workload summary.
- Report central tendency and dispersion appropriate to the distribution; preserve outliers and explain any exclusion.
- Separate compile-time, startup, steady-state, memory, binary-size and developer-effort costs.
- Report correctness failures before performance comparisons. A faster implementation that violates the task contract is not a successful result.
- For security tests, report corpus coverage, oracle quality, false positives, false negatives and known blind spots.
- For formal work, publish theorem statements, assumptions, admitted axioms, checker output and implementation-refinement status.
- For resource claims, state whether the bound is static, model-derived, dynamically enforced or empirically observed.
- Avoid percentage claims without denominators, confidence/uncertainty and a clearly defined population.

### Negative and inconclusive results

A hypothesis is rejected when its preregistered falsification condition occurs. A result is inconclusive when the sample, oracle, measurement resolution or environment cannot distinguish the alternatives. Both are reportable outcomes. Do not change the hypothesis after observing data; any revised hypothesis receives a new identifier and a new experiment record.

## 10. Threats to validity

| Threat | Mitigation |
|---|---|
| Unequal implementation maturity | Label prototype/production status; compare only supported equivalent paths |
| Baseline configuration bias | Independent review of baseline choices and tuning; publish commands and flags |
| Workload cherry-picking | Preregister workload selection and publish exclusions |
| Different semantics | Freeze a shared task contract and oracle before coding |
| Measurement noise | Repetitions, raw samples, environment controls and uncertainty |
| Toolchain/library confounding | Pin versions; separate compiler/runtime/library contributions where possible |
| Researcher expectancy | Independent reproduction and review; blind review of subjective task scoring where feasible |
| Hidden trust assumptions | Publish TCB, host, OS, hardware and toolchain assumptions |
| Survivorship/reporting bias | Preserve failed runs, negative results and abandoned hypotheses |
| Overgeneralisation | Limit conclusions to measured revisions, workloads, configurations and targets |

## 11. Current Capstan-specific guardrails

The present Capstan implementation is C-backed. CCAM and Lean results cover selected fragments; they do not establish an end-to-end verified execution pipeline or a C-free production compiler. The evaluation must preserve the distinctions in the research register:

- implementation is not the same as tested behaviour;
- tests are not formal proofs;
- a theorem about a model is not implementation refinement;
- an experimental branch is not a released capability;
- a proposed guarantee is not an enforced guarantee.

The first comparative campaign should be narrow enough to reproduce and should use only features that exist at the tested immutable revision. The Halyard media work is a promising workload family, but its current prototypes and stated limitations must be reflected honestly; no media benchmark result is implied by this protocol.

## 12. Open decisions before the first campaign

1. Final baseline set for each workload, informed by issues #220–#222.
2. Exact workload shortlist and shared task contracts.
3. Hardware and OS matrix, including whether CI runners are adequate for performance work.
4. Whether independent reviewers/participants can be recruited for developer-effort tasks.
5. Dataset licensing and redistribution constraints.
6. Statistical analysis plan for each metric family.
7. Which experiments can be fully automated in a clean checkout.

These decisions must be recorded before the first measurement run. This document is a protocol foundation, not completion of those experiments.
