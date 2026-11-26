# Halyard research review and reproducible baseline protocol

**Issue:** #290 (RESEARCH-MEDIA-001)  
**Research snapshot:** 2026-11-26  
**Scope:** R8.1–R8.6 / H1–H6  
**Status:** scoped literature review and preregistration-style experimental protocol; no experimental result or novelty claim is asserted.

## 1. Executive assessment

The literature establishes substantial prior art in verified parsing, format-aware fuzzing, media clock synchronisation and real-time callback discipline. Halyard must therefore make narrow, falsifiable claims about the combination of its contracts and measured behaviour, not claim to be the first safe parser, first zero-copy parser, or first rational media clock.

The most consequential research gap is the boundary between local parser limits and aggregate, compositional resource ownership across a graph. Existing work gives strong ingredients—verified format combinators, structure-aware input generation, explicit clock models and real-time execution rules—but does not by itself establish Halyard's proposed end-to-end conservation model for aliases, derived buffers, queues, worker lifetimes, cancellation and concurrent admission.

The six hypotheses below are research questions, not product guarantees. The current Halyard implementation remains a bounded prototype. In particular, public mutable struct fields, sequential-only accounting, incomplete parser-allocation coupling, absent device scheduling and incomplete clock/discontinuity semantics are material limitations (see `CORE-PRIMITIVES.md` and `ARCHITECTURE.md`).

## 2. Reproducible search protocol

### 2.1 Snapshot and search scope

- Search snapshot: 2026-11-26 (UTC).
- Primary publication window: 2015–2026; older foundational work and standards are included where still normative or operationally important.
- Sources searched: ACM Digital Library and publisher pages; USENIX proceedings; arXiv; Microsoft Research / Project Everest; official standards bodies and RFC Editor; official project documentation for OSS-Fuzz, GStreamer and FFmpeg; CWE entries.
- Search was targeted, not systematic: citation chaining and searches were used to identify directly relevant primary work and mature implementation documentation. No claim of exhaustive coverage is made.

Representative search strings:
- `media parser decompression bomb resource exhaustion resource accounting`
- `format-aware differential fuzzing media parser FormatFuzzer`
- `verified binary parser media format parser serialization zero-copy`
- `real-time audio callback scheduling allocation locks deadline`
- `rational timestamps media clock drift A/V synchronization RFC`
- `media parser fuzzing corpus sanitizer OSS-Fuzz`

### 2.2 Inclusion and exclusion

Include primary papers, standards, authoritative security taxonomies and mature implementation documentation when they provide at least one of: a formal property, an implementable mechanism, a reproducible evaluation method, a relevant threat model, or a well-defined operational contract.

Exclude unsupported vendor performance claims, unsourced blog claims, demonstrations without a reproducible method, and papers whose problem is only superficially similar. Practitioner guidance is retained only as engineering guidance, not elevated to formal evidence. A reference implementation is a benchmark or differential oracle, never an implementation dependency: Halyard's Capstan-only implementation constraint remains in force.

### 2.3 Evidence handling

For each included source, record the exact edition/revision, access date, relevant section, the claim it supports and what it does not support. Standards interpretation is adjudicated against the normative standard, not majority agreement among implementations. Corpus files must have provenance, licence status, version, hashes and a documented reason for inclusion.

## 3. Findings by research area

### 3.1 Decompression amplification and aggregate resource accounting

CWE-409 defines improper handling of highly compressed data as accepting compressed input whose expansion is disproportionate; its examples include ZIP and XML entity-expansion bombs. This is a useful root-cause classification, but it is not a complete media resource model: image dimensions, frame/sample counts, metadata, nested containers, parser work, queue retention and concurrent workers can exhaust resources without a high compression ratio.

The design implication is to preflight each untrusted dimension before allocation or expensive traversal, then charge the resulting object and its lifetime to an aggregate budget. Per-file and per-object caps remain useful defence-in-depth but cannot substitute for graph-wide admission. Charges must distinguish cumulative work (which is not refunded when an object is released) from live retained resources (which are released with the object's lease). Admission and multi-dimensional reservation must be failure-atomic.

Relevant anchors:
- MITRE, [CWE-409: Improper Handling of Highly Compressed Data](https://cwe.mitre.org/data/definitions/409.html).
- Halyard's own normative starting points: `CORE-PRIMITIVES.md`, `SECURITY-ASSURANCE.md`, and R8.1 in `RESEARCH-AGENDA.md`.

### 3.2 Verified parsing, serialization and safe codec boundaries

EverParse (USENIX Security 2019) demonstrates verified, zero-copy parsers and serializers for TLV-style formats, with memory-safety, parser/serializer correctness and non-malleability properties. PulseParse / EverCBOR / EverCDDL (CCS 2025) extend verified parsing and serialization to recursive CBOR/CDDL formats using separation logic and address constant-stack parsing for a class of recursive structures. Vest (USENIX Security 2025) is a contemporary verified, high-performance Rust parsing/serialization framework.

These are direct prior art for H2. Halyard's research question is not whether verified parsers are possible, but whether a Capstan-native format-description and combinator pipeline can express realistic media structures (dependent lengths, chunk/box hierarchies, indexes, sample extents, streaming boundaries), generate useful conformance evidence, and maintain a credible correspondence between the specification, generated/handwritten implementation and executable tests.

The distinction between a verified parser library and an unverified format-description frontend matters: the trusted computing base, specification interpretation and refinement obligations must be itemised. Zero-copy is not automatically safer or faster; it changes ownership and retention obligations.

Relevant anchors:
- Ramananandro et al., [EverParse, USENIX Security 2019](https://www.usenix.org/conference/usenixsecurity19/presentation/delignat-lavaud).
- Ramananandro et al., [PulseParse / EverCBOR, CCS 2025](https://doi.org/10.1145/3719027.3765120).
- Cai et al., [Vest, USENIX Security 2025](https://www.usenix.org/conference/usenixsecurity25/presentation/cai-yi).
- Project Everest, [EverParse documentation](https://project-everest.github.io/everparse/).

### 3.3 Zero-copy ownership and memory lifetime

Zero-copy removes copies but can increase aliasing, pinning, retained memory, fragmentation and lifetime coupling. The correct comparison is therefore not just bytes copied. It must include peak live bytes, duration of retention, alias count, lease-transfer cost, fragmentation, GC pressure, cache behaviour and cleanup under cancellation or worker failure.

A defensible experiment compares copy, immutable borrow, reference-counted lease and ownership-transfer variants under the same graph and input. Every variant must preserve identical output semantics. Include adversarial stale-handle, double-release, use-after-revoke and cancellation-at-each-transition tests. A zero-copy result that reduces copying by retaining large backing buffers longer may be a regression.

EverParse provides evidence that zero-copy can coexist with verified parser properties in a constrained design; it does not prove Halyard's graph-wide lifetime accounting or Capstan's current public struct representation safe.

### 3.4 Real-time scheduling

Real-time audio is a deadline problem, not an average-throughput problem. Callback-reachable code must avoid unbounded allocation, deallocation, blocking locks, I/O and operations with unknown worst-case timing. Preallocation and control-plane/data-plane separation are established engineering practices. They are not, by themselves, a worst-case execution-time proof: scheduler behaviour, page faults, cache effects, interrupt load, device behaviour and OS policy remain assumptions or measured environmental variables.

The experiment must report callback-time distributions and deadline misses under controlled load, not only average CPU use. Include overload and failure behaviour; silent drops or unbounded buffering must not be treated as success.

Relevant anchor: Ross Bencina, [Real-time audio programming 101: time waits for nothing](https://w2.mat.ucsb.edu/240/A/2017/05/17/realtime.html) (practitioner guidance; not a formal WCET result).

### 3.5 Rational clocks and A/V synchronisation

RTP (RFC 3550) explicitly warns that timestamps from different media streams may use different rates and independent offsets; direct comparison is not sufficient. It relates media timestamps to a shared reference clock using RTCP sender reports. RFC 7273 further addresses signalling reference clock sources. GStreamer provides a mature operational model based on a selected pipeline clock, buffer timestamps, segments, base time, running time and latency compensation. FFmpeg exposes rational stream time bases for timestamp representation.

The design implication is to preserve source/media timestamps and clock-domain identity separately from estimated presentation time. Rational arithmetic avoids cumulative floating-point drift, but cannot alone solve clock-rate estimation, discontinuity handling, resampling, jitter buffering or latency policy. Experiments must include clock skew and drift, wraparound, discontinuities, pause/resume, seek, variable frame rate, hot-plug and network jitter.

Relevant anchors:
- [RFC 3550 — RTP](https://www.rfc-editor.org/rfc/rfc3550.html).
- [RFC 7273 — RTP Clock Source Signalling](https://www.rfc-editor.org/rfc/rfc7273.html).
- GStreamer, [Clocks and synchronisation](https://gstreamer.freedesktop.org/documentation/application-development/advanced/clocks.html).
- FFmpeg, [AVStream time_base](https://ffmpeg.org/doxygen/trunk/structAVStream.html).

### 3.6 Format-aware fuzzing and semantic oracles

FormatFuzzer shows that grammar-derived generation and mutation can produce valid structured inputs and uncover bugs that generic byte mutation may miss. OSS-Fuzz documents practical corpus seeding, dictionaries, size limits, coverage and sanitizer configurations. These are complementary techniques: byte-level coverage-guided fuzzing remains useful for parser robustness, while format-aware generation reaches deeper semantic states.

Differential agreement is not a correctness oracle. Two parsers may share a bug or accept ambiguous encodings. Every disagreement must be reduced and resolved against the exact normative format edition. Metamorphic properties (round trip, permitted chunk permutation, irrelevant metadata insertion, truncation at every boundary, equivalent encodings) provide independent checks where a complete expected-output oracle is difficult.

Relevant anchors:
- Dutra, Gopinath and Zeller, [FormatFuzzer](https://doi.org/10.1145/3628157).
- Google, [OSS-Fuzz project guide](https://google.github.io/oss-fuzz/getting-started/new-project-guide/).

## 4. H1–H6: falsifiable hypotheses and experiments

The following maps the six H-MEDIA hypotheses (H1–H6) to the R8 research work packages. H7 (format-aware fuzzing) is a cross-cutting method used in the parser and codec experiments; H8/H9 remain outside this issue's six-hypothesis scope.

| Hypothesis | Baselines and controlled comparison | Corpus / workload | Primary metrics | Failure / negative result |
|---|---|---|---|---|
| **H1 / R8.1 — compositional resource semantics**: graph-wide accounting prevents over-admission where local caps fail, at acceptable cost. | Per-object caps; per-node budgets; aggregate graph ledger; single-owner admission versus synchronised shared admission. | Nested containers; shared/aliased buffers; derived PCM/RGBA; fan-out/fan-in graphs; concurrent decode jobs; cancellation and worker death at every transition. | Peak retained bytes; over-admission count; rejected-work precision; admission p50/p99; contention; cleanup latency; cumulative work charged. | Reject H1 if graph accounting does not prevent over-admission under declared assumptions, if accounting is forgeable, or if the cost exceeds preregistered limits. |
| **H2 / R8.2 — verified format descriptions**: format descriptions and shared combinators can prove useful properties for realistic media structures at practical cost. | Handwritten Capstan parser; declarative Capstan description; Vest and PulseParse/EverParse as external research baselines/oracles. | RIFF/WAVE first, then a selected bounded image format and a restricted ISO BMFF profile; valid, malformed, truncated and ambiguous cases. | Proof/validation effort; accepted-input agreement; round-trip correctness; ambiguity rejection; peak memory; allocations; throughput; rejected-input work; refinement coverage. | Reject H2 if realistic dependent/recursive constraints cannot be expressed, the description frontend becomes an unreviewed TCB, or proof/runtime cost is impractical. |
| **H3 / R8.3 — ownership-safe zero-copy**: explicit leases reduce data movement while retaining a provable live-memory bound. | Copying; immutable borrow; reference-counted lease; ownership transfer. | Large frame/sample pipelines; fan-out; retained slices; cancellation; worker termination; stale/double-release adversarial cases. | Bytes copied; peak live bytes; retention duration; allocation count; fragmentation; GC pressure; p50/p99 latency; cleanup time. | Reject H3 if lower copy count causes unbounded or materially higher retention, or if lease safety cannot be enforced/refined. |
| **H4 / R8.4 — preflighted real-time audio**: a preflighted plan bounds callback work under declared platform assumptions and reduces deadline misses. | Naive dynamic graph; preallocated immutable plan; bounded command queue / graph-swap protocol. | Fixed and variable block sizes; dense graphs; plugin-like callbacks (test doubles only); CPU contention; device reconfiguration; overload. | Worst observed and p99/p99.9 callback duration; deadline misses/x-runs; jitter; queue high-water; allocations/locks/I/O in callback; recovery time. | Reject H4 if any callback-reachable unbounded/blocking operation remains or deadline misses do not improve without silent data loss. Observed maxima are not WCET proofs. |
| **H5 / R8.5 — rational multi-clock synchronisation**: explicit clock domains and rational timestamps make drift/discontinuity behaviour reproducible and bounded. | Single nominal clock; fixed master clock; audio-master; video-master; adaptive clock mapping. | Synthetic and recorded skew/drift; VFR; wraparound; pause/resume; seek; clock step; hot-plug; jitter and packet loss/reordering. | A/V skew distribution; convergence time; buffer occupancy; latency; dropped/repeated frames; resampling ratio variation; arithmetic rejection. | Reject H5 if the controller hides source-time discontinuities, accumulates unbounded error/latency, or fails declared drift envelopes. |
| **H6 / R8.6 — proof-preserving graph optimisation**: optimisation reduces copies/energy while preserving declared semantics and resource envelopes. | Unoptimised reference graph; fusion; copy elimination; SIMD; hardware path only when available and independently checked. | Deterministic audio/image pipelines with numerical edge cases, alpha/colour/channel order, timestamps, errors and budget boundaries. | Bit-exact equality or declared tolerance; resource-cost delta; copies/bytes moved; allocations; throughput; latency tails; energy; CPU/GPU parity. | Reject an optimisation on any semantic mismatch, hidden resource increase, nondeterministic error change or energy/latency regression outside preregistered tolerance. |

### 4.1 Shared experimental controls

- Pin source revision, compiler version, build flags, OS/kernel, CPU/GPU, device firmware, power mode and all external oracle versions.
- Hash every input corpus and preserve the exact corpus manifest, seeds, mutator version and generated cases.
- Separate warm-up from measured runs; use repeated independent trials and report median, dispersion, p95/p99 and raw samples.
- Keep functional correctness and security gates as hard constraints, not weighted score terms.
- Measure both normal and adversarial inputs; report rejected-input work and resource consumption.
- Run software reference and accelerated paths separately. Do not compare unlike output quality or feature profiles.
- Where real-time guarantees depend on an OS scheduler or hardware clock, state the assumptions and report measurements as empirical evidence, not proof.

## 5. Baseline systems and corpora

### 5.1 External baselines (test/measurement only)

- **Verified parsing:** Vest; PulseParse/EverCBOR/EverCDDL; EverParse/LowParse.
- **Format-aware generation:** FormatFuzzer.
- **Coverage-guided fuzzing infrastructure:** libFuzzer/AFL++/Honggfuzz/Centipede through OSS-Fuzz where suitable.
- **Media pipeline behaviour:** FFmpeg and GStreamer as isolated differential/operational baselines, not build or runtime dependencies.
- **Clock/synchronisation semantics:** RFC 3550, RFC 7273, relevant ISO/IEC 14496 and SMPTE ST 2110 editions; GStreamer and FFmpeg behaviour as implementation comparisons.
- **Real-time callback practice:** Bencina's callback guidance as a checklist, plus platform-specific audio API documentation when a concrete host is selected.

External implementations are not treated as ground truth. Compare only matching format profiles, codec features, output precision, error policy and resource limits.

### 5.2 Corpus plan

1. **RIFF/WAVE:** normative PCM fixtures across 8/16/24/32-bit, mono/multichannel, chunk order, padding, unknown chunks, duplicate chunks, malformed lengths, truncation and overflow-shaped values.
2. **Image:** choose one format only after licence/security review; include dimension/stride/plane boundaries, metadata, orientation, alpha, colour profiles, malformed chunk trees and compressed expansion cases.
3. **ISO BMFF:** use a version-pinned restricted profile; mutate every box size, parent boundary, table count, sample-description index, chunk/sample offset and media extent.
4. **Graph/resource:** synthetic DAGs with aliases, fan-out, derived buffers, nested containers, queue retention, concurrent workers, cancellation and partial construction.
5. **Clock:** deterministic generated traces for independent clock rates, skew, drift, wrap, VFR, discontinuity, pause/resume, seek and jitter.
6. **Audio callback:** synthetic workloads with fixed and variable block sizes, CPU contention, queue saturation, graph replacement and device loss.

Every corpus item records source, licence, format edition/profile, expected result, rationale, SHA-256, generator/mutator version and whether it is valid, invalid or intentionally ambiguous.

## 6. Metrics, confounders and reporting

### 6.1 Required metrics

Report correctness and safety first: accepted/rejected classification, exact output or fidelity error, malformed-input handling, maximum admitted resource vector, failure atomicity, cleanup completeness and differential divergences. Then report performance: throughput, latency distribution, peak/steady retained memory, allocation/copy counts, CPU utilisation, queue high-water, energy (if measurable), startup/seek/recovery time and fuzz bugs per CPU-hour.

### 6.2 Confounders

Control or disclose allocator/GC behaviour, list growth policy, cache warmth, CPU frequency scaling, NUMA placement, page faults, background load, compiler optimisation, SIMD dispatch, GPU driver/firmware, thermal throttling, device clock calibration, corpus composition, fuzzer budget and oracle version. For parser comparisons, ensure each implementation receives the same byte corpus and the same accepted feature profile. For energy claims, record measurement hardware and idle baseline.

### 6.3 Negative-result policy

Publish null results, regressions and inconclusive experiments. A hypothesis is not supported merely because a prototype passes its own tests. If an experiment cannot isolate a confounder, label it inconclusive. Do not discard malformed cases because they reduce throughput. Do not tune one implementation to a benchmark while leaving the others at defaults without documenting the asymmetry. Never use majority vote to adjudicate parser disagreement; consult the normative specification and preserve unresolved cases as unresolved.

No composite score may hide a severe security, fidelity, deadline or resource regression. No publication-quality claim is permitted until the corpus, scripts, raw data, environment and independent reproduction are available.

## 7. Mapping to Halyard work packages and decisions

| Work package | Research dependency / output |
|---|---|
| #294 / R8.1 | H1 resource algebra; distinguish live leases from cumulative work and define alias/derivation conservation. |
| #295 / R8.2 | H2 format descriptions; begin with RIFF/WAVE and one selected image/container profile. |
| #296 / R8.7 | Cross-cutting fuzzing method for H2/H3 and codec parser work; grammar-aware and metamorphic cases. |
| #297 / R8.5 | H5 clock-domain model, rational time and discontinuity state machine. |
| #298 / R8.4 | H4 preflighted callback execution and deadline telemetry. |
| #300 / R8.6 | H6 graph IR, semantics-preserving rewrites and resource-cost deltas. |
| #284–#285 / MC1 | Prerequisite byte-source/sink and aggregate-ledger contracts; research findings must not be presented as implementation completion. |
| #293 / MC1 | Opaque ownership and reservation lifecycle; required before public hostile-input trust-boundary claims. |

The immediate engineering decisions supported by this review are conservative:

1. Keep local parser limits and aggregate live/cumulative budgets distinct.
2. Do not expose mutable source, ledger or reservation internals as a hostile-input security boundary.
3. Start formal parser work with one deliberately restricted format profile and an explicit frontend TCB.
4. Keep audio control-plane planning outside the callback; do not claim WCET from observed timings.
5. Preserve source timestamps and clock domains; derive presentation time through an explicit mapping.
6. Treat independent parsers as differential oracles, not authorities; adjudicate against standards.
7. Keep every external implementation out of the Capstan media build/runtime.

## 8. References

1. MITRE, [CWE-409: Improper Handling of Highly Compressed Data](https://cwe.mitre.org/data/definitions/409.html).
2. T. Ramananandro et al., [EverParse: Verified Secure Zero-Copy Parsers for Authenticated Message Formats](https://www.usenix.org/conference/usenixsecurity19/presentation/delignat-lavaud), USENIX Security 2019.
3. T. Ramananandro, G. Ebner, G. Martínez and N. Swamy, [Secure Parsing and Serializing with Separation Logic Applied to CBOR, CDDL, and COSE](https://doi.org/10.1145/3719027.3765120), ACM CCS 2025.
4. Y. Cai et al., [Vest: Verified, Secure, High-Performance Parsing and Serialization for Rust](https://www.usenix.org/conference/usenixsecurity25/presentation/cai-yi), USENIX Security 2025.
5. R. Dutra, R. Gopinath and A. Zeller, [FormatFuzzer: Effective Fuzzing of Binary File Formats](https://doi.org/10.1145/3628157), 2024.
6. H. Schulzrinne et al., [RFC 3550: RTP: A Transport Protocol for Real-Time Applications](https://www.rfc-editor.org/rfc/rfc3550.html), IETF, 2003.
7. C. Perkins et al., [RFC 7273: RTP Clock Source Signalling](https://www.rfc-editor.org/rfc/rfc7273.html), IETF, 2014.
8. GStreamer, [Clocks and synchronisation](https://gstreamer.freedesktop.org/documentation/application-development/advanced/clocks.html), project documentation.
9. FFmpeg, [AVStream reference: time_base](https://ffmpeg.org/doxygen/trunk/structAVStream.html), project documentation.
10. Google, [OSS-Fuzz: new project guide](https://google.github.io/oss-fuzz/getting-started/new-project-guide/), project documentation.
11. R. Bencina, [Real-time audio programming 101: time waits for nothing](https://w2.mat.ucsb.edu/240/A/2017/05/17/realtime.html), practitioner guidance.

---

**Disposition:** this document satisfies the literature-review and baseline-protocol design deliverable for #290 at the research-plan level. It does not establish novelty, experimental results, independent reproduction, MC0/MC1 gate completion, or implementation readiness. Those remain explicitly separate evidence obligations.
