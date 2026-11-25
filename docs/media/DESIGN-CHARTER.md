# Halyard — design charter

> **Status:** governing design principles, 2026-11-25.
>
> This charter governs Halyard: Capstan Media Core, Shanty and Deadeye, and their
> integration with Capstan, Shroud, Keel, Anchor and the research stream.

## 1. Ambition

Build the most secure, efficient, effective, usable and scientifically consequential
media components possible. These are simultaneous design objectives, not alternative
product profiles and not marketing adjectives.

The products are to be implemented from scratch in Capstan. External standards,
specifications, research, advisories and test corpora may inform the work; third-party
multimedia implementation code is not to become part of the shipped implementation.

## 2. Five co-equal objectives

### 2.1 Security and assurance

- Minimise trusted code, ambient authority, parser complexity and attack surface.
- Treat every byte from an external source as hostile until validated.
- Bound aggregate memory, CPU work, dimensions, queues, threads, recursion and time.
- Make ownership, cancellation, state transitions and failure semantics explicit.
- Isolate fault-prone work and validate all boundary outputs.
- Maintain a complete, evidence-backed ledger of known applicable vulnerabilities.
- Turn every discovered defect into a retained regression and, where appropriate, a
  fuzz target and a design-level invariant.
- State precisely what has been tested, fuzzed, model-checked, formally verified and
  refined to implementation. Never overstate assurance.

### 2.2 Efficiency

Optimise the whole pipeline, not a single codec microbenchmark.

- Measure throughput, end-to-end and tail latency, memory footprint, allocation count,
  bytes moved, power/energy where measurable, startup, seeking and recovery.
- Design for data locality, cache behaviour, SIMD, parallelism and zero-copy operation
  where these improve measured outcomes without weakening ownership or isolation.
- Make backpressure and resource costs visible to the graph planner.
- Avoid unnecessary conversions and intermediate representations.
- Preserve deterministic software reference paths for correctness comparisons.
- Benchmark against relevant alternatives on identical hardware and publish reproducible
  inputs, scripts, configurations and raw results.

### 2.3 Effectiveness and fidelity

- Correctly represent the semantics of the supported standards and profiles.
- Preserve sample accuracy, timestamps, channel layouts, colour spaces, bit depth and
  metadata where the format and operation permit it.
- Make lossy transformations explicit, measurable and user-controlled.
- Support professional, scientific, medical, simulation and real-time workflows through
  well-defined extension points and domain-specific validation.
- Distinguish format recognition, partial decoding, full conformance and production
  readiness in all capability claims.

### 2.4 Usability and developer experience

- Make common correct operations straightforward and advanced operations possible.
- Provide coherent, composable, typed APIs across Core, Shanty and Deadeye.
- Use safe defaults, explicit opt-ins for risky or lossy behaviour, and predictable errors.
- Make resource limits, performance costs, format limitations and processing decisions
  inspectable.
- Provide excellent diagnostics, examples, fixtures, documentation and migration policy.
- Avoid forcing application developers to understand codec internals for ordinary tasks.
- Ensure expert users can still control clocks, graph topology, quality, colour, channels,
  scheduling and resource policies.

### 2.5 Research contribution

Every major subsystem should identify a concrete unresolved question, a falsifiable
hypothesis, a baseline and an experimental method. Research is part of the engineering
loop, not a separate publication exercise.

Initial candidate questions include:

- Can aggregate, transactional resource accounting provide stronger decompression-bomb
  resistance with lower overhead than conventional per-object limits?
- Can typed ownership and bounded queues enable practical zero-copy media graphs while
  retaining simple cancellation and lifetime guarantees?
- Can a rational-timebase scheduler bound audiovisual drift across variable-frame-rate
  streams, seeks and clock discontinuities?
- Can a Capstan-native parser substrate achieve competitive throughput while making
  malformed-input states easier to reason about and verify?
- Can structure-aware differential fuzzing systematically find semantic disagreements
  between independently developed decoders?
- Can graph-level cost planning reduce memory traffic and energy while preserving
  reference output semantics?
- Can colour, timing and metadata semantics be represented so that scientific and
  medical workflows can state and verify their transformation provenance?

These are hypotheses, not claimed results. The research register must track literature,
assumptions, protocols, baselines, data, negative results and reproducibility artefacts.

## 3. How to resolve trade-offs

No single metric is allowed to silently dominate.

1. Security invariants, data integrity and declared correctness are hard constraints.
2. Within those constraints, optimise measured end-to-end performance and resource use.
3. Preserve fidelity and make unavoidable transformations explicit.
4. Minimise user-facing complexity without hiding consequential choices or costs.
5. Prefer designs that expose useful research questions and permit independent evaluation.

When objectives conflict, document the conflict, quantify it where possible, record the
decision and provide an escape hatch when appropriate. A performance gain does not
justify an unbounded resource path. An abstraction does not justify hiding a security
boundary. A simpler API does not justify silently changing output.

## 4. Evidence required for superlative claims

Do not use claims such as "most secure", "fastest", "best quality" or "easiest" as
established facts until there is comparative evidence.

For each claim, publish:
- the precise property and scope;
- competing implementations and versions;
- hardware, operating system, compiler and configuration;
- input corpus, hashes and test methodology;
- raw results, statistical treatment and known limitations;
- security review and residual risks where relevant;
- reproducible scripts and independent replication status.

The product ambition can be maximal while the public claims remain exacting and modest.

## 5. Product consequences

- **Media Core** supplies the safe, bounded, composable substrate.
- **Shanty** applies it to audio, from deterministic sample processing to professional
  production, spatial sound and real-time systems.
- **Deadeye** applies it to images and video, from faithful bounded raster operations to
  high-end production, scientific imaging and synchronised presentation.
- **Shroud core** remains media-independent; an optional Halyard–Shroud adapter presents media without duplicating parsers or codec implementations.
- **Keel** may orchestrate application and media graphs without owning codec semantics.
- **Anchor** and other applications should benefit from the same coherent developer
  experience and inspectable guarantees.

The architecture must support scientific and medical imaging, digital twins, simulation,
broadcast, games, accessibility and professional creative work without pretending that
all these domains have identical requirements. Domain-specific profiles and validation
must sit on shared, rigorously defined primitives.

## 6. Design review checklist

Every substantial component proposal must answer:

1. What user or research problem does it solve?
2. What is the smallest trusted implementation and authority required?
3. What are its input, output, ownership and cancellation contracts?
4. What aggregate resources can it consume, and how are they reserved?
5. What malformed, adversarial and failure cases are in scope?
6. What correctness and fidelity properties are testable?
7. What is the measured performance baseline and target?
8. How does a developer discover, use, debug and compose it?
9. What research hypothesis or new capability does it enable?
10. What evidence is required before calling it implemented, secure, conformant or fast?

A component is not complete merely because it compiles. It must meet its declared
correctness, security, usability, performance and documentation gates.
