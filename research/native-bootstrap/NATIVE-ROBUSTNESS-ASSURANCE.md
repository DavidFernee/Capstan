# Native compiler and runtime robustness assurance requirements

Status: engineering requirements, not a claim that the current implementation satisfies them.

## Objective

Capstan's native compiler and runtime should be designed to make memory corruption, privilege escalation, uncontrolled resource exhaustion, and silent semantic miscompilation structurally difficult or impossible within a clearly stated threat model. The project must not claim superiority to every existing system without comparative evidence. It should instead establish stronger, independently reviewable guarantees property by property.

A feature is not production-ready because it compiles, passes examples, is self-hosted, or has an abstract proof. Production readiness requires a traceable chain from specification to implementation, executable adversarial tests, and independent assurance.

## Threat model and trust boundaries

The assurance case must state whether each component is trusted, verified, sandboxed, or merely tested. At minimum, consider:

- Malicious or malformed source programs, imports, metadata, build inputs, and serialized data.
- Adversarially deep, wide, cyclic, duplicated, or malformed object graphs.
- Stale, forged, cross-domain, out-of-range, or generation-wrapped handles.
- Integer overflow, size truncation, invalid alignment, aliasing, uninitialised state, and invalid control flow.
- Resource exhaustion, including peak temporary memory, descriptor metadata, roots, worklists, compiler recursion, diagnostics, and I/O.
- Concurrency and re-entrancy at allocation, safepoints, collection, module loading, and publication boundaries.
- Faults in the seed compiler, generated native code, linker/toolchain, build scripts, dependencies, and CI.
- Platform ABI and operating-system boundary failures.

The model must identify excluded threats explicitly. Formal proofs are conditional on their assumptions and do not prove the compiler, hardware, OS, or build infrastructure correct unless those are included in the model.

## Non-negotiable runtime invariants

1. **No source-visible raw heap addresses.** Heap references are opaque, domain-bound, generation-checked handles. Raw addresses exist only inside tightly scoped runtime implementation boundaries and never survive a safepoint.
2. **No generation wraparound.** A slot retires before its generation can repeat. Exhaustion rejects allocation rather than revalidating an old handle.
3. **One authoritative object state.** Occupancy, generation, descriptor, object extent, and ownership cannot be represented by independently mutable fields that can disagree.
4. **Descriptor safety.** Every traced offset is validated against object extent, alignment, field kind, and descriptor version before it is read. Unknown or malformed descriptors fail closed.
5. **Complete explicit roots.** Every live reference in registers, stack slots, globals, runtime frames, and foreign-call handles is represented at every safepoint. Conservative stack scanning is not a correctness basis.
6. **Atomic publication.** Allocation validates arithmetic and budgets, reserves all required resources, initializes privately, then publishes once. Rejection leaves the observable heap, handles, and accounting unchanged.
7. **Independent resource budgets.** Bound payload bytes, reserved heap, handle slots, descriptor metadata, collector metadata, roots, edges, worklist, recursion, temporary peak memory, and I/O independently. Use checked arithmetic for every admission calculation.
8. **Fail-closed collection.** Only a complete, independently validated mark certificate can authorize sweeping. Any malformed input, stale handle, budget exhaustion, interruption, or inconsistent snapshot aborts collection without reclaiming objects.
9. **Snapshot consistency.** The collector observes one coherent heap/descriptor/root snapshot. Mutator/collector coordination and memory ordering are specified, not assumed.
10. **No hidden unbounded fallback.** Failure paths must not allocate without bounds, recurse without limits, invoke unbounded formatting, or silently switch to unsafe conservative behaviour.

## Compiler and code-generation invariants

- Source semantics, intermediate representation semantics, and machine-code semantics must have explicit correspondence obligations.
- Every IR operation has validated operands, types, control-flow successors, and resource costs before code generation.
- Arithmetic, shifts, casts, pointer/handle operations, bounds checks, division, and traps have specified overflow and failure semantics.
- No optimisation may remove a check without a proof that its preconditions hold. Early bootstrap profiles should retain runtime checks where static analysis is incomplete.
- Code generation must not emit writable-and-executable memory, dynamic loader dependencies, undefined symbols, or unreviewed runtime calls in profiles that promise freestanding execution.
- Trap identity and diagnostic payloads must survive lowering or be explicitly excluded from the ABI contract.
- Return values and process results must use a specified width and encoding; OS exit status must not be mistaken for a general integer result channel.
- Native compiler output must be tested against an independent semantic oracle and a diverse test corpus.

## Required GC proof chain

The GC assurance case is decomposed so no abstract theorem is mistaken for an implementation proof:

- **R0 — Handle lifecycle:** allocation, release, reuse, retirement, domain separation, and rejection atomicity.
- **R1 — Descriptor/layout refinement:** concrete object layout and descriptor metadata agree; all offsets, extents, alignment, and reference kinds are validated.
- **R2 — Root completeness:** compiler-generated root maps cover every live reference at every safepoint, including spills, nested calls, exceptions/traps, globals, and foreign interfaces.
- **R3 — Marker correctness:** bounded traversal terminates only with an empty worklist and a checked certificate; every root is included and every valid outgoing reference edge is closed under marking.
- **R4 — Sweep refinement:** only certified, unmarked objects are reclaimed; live objects, handles, and unrelated metadata are preserved.
- **R5 — Mutator/collector protocol:** safepoint, stop-the-world or concurrent barriers, publication ordering, and snapshot consistency are proven for the selected collection mode.
- **R6 — Resource and failure atomicity:** all collector and allocation costs are bounded, and every failure path preserves heap invariants.
- **R7 — Runtime refinement:** the concrete implementation refines the verified state machine and passes instrumented differential and adversarial tests.

A gate is complete only when its proof assumptions are discharged by an earlier gate or explicitly accepted as part of the trusted computing base.

## Required validation layers

- Lean theorem compilation with pinned toolchain, no unfinished proofs, no local axioms, and theorem axiom-dependency reports. Audit use of classical axioms and choice; document where they are harmless and where executable extraction is affected.
- Property-based tests generated from the formal state machine, including stateful sequences of allocate/release/reuse/resolve.
- Adversarial tests for stale and cross-domain references, malformed descriptors, invalid offsets, cycles, duplicate edges, maximum-size roots, each budget at exact limit and one over, and interrupted traversal.
- Differential testing against a separately implemented reference semantics; the oracle must not share the same lowering or collector implementation.
- Coverage-guided fuzzing of parsers, validators, IR decoders, descriptors, module loaders, and runtime boundaries; retain minimized regressions.
- Sanitizer and memory-debug builds for the implementation language and foreign interfaces. Sanitizers are evidence, not proofs.
- Cross-compiler and cross-platform tests, reproducible builds, pinned dependencies, artifact provenance, and independent bootstrap rebuilds.
- Fault injection for allocation failures, short reads/writes, interrupted system calls, corrupt metadata, and resource-limit exhaustion.
- Performance tests with adversarial distributions as well as average workloads. A bounded algorithm must account for worst-case collision behaviour and temporary allocations, not just asymptotic expected complexity.

## Evidence and release policy

Every assurance claim must link to:

1. The invariant or theorem statement.
2. The concrete implementation component it constrains.
3. The refinement proof or explicit trusted assumption.
4. Positive and negative tests, including boundary and adversarial cases.
5. Exact source revision, toolchain versions, and reproducible CI evidence.
6. Known limitations and the conditions under which the claim does not hold.

Use explicit maturity labels: **research model**, **executable reference**, **prototype**, **verified component**, **production candidate**, and **production**. Advancing a label requires review evidence. A green CI run on an abstract model does not establish a production guarantee.

## Current status

The current native-memory work contains an abstract handle lifecycle model, abstract reachability models, and a list-based bounded-marker reference model. It does not yet establish R1 descriptor/layout refinement, R2 compiler root completeness, R4 concrete sweep refinement, R5 mutator/collector coordination, R6 concrete runtime resource accounting, or R7 production implementation refinement. The list marker is not yet accepted as production-grade: it uses linear list operations and still requires exact-head compilation, adversarial tests, and a completeness argument.

The native compiler work currently demonstrates a scalar freestanding vertical slice, not a complete Capstan compiler bootstrap. All claims must preserve that distinction.
