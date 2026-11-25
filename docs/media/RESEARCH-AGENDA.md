# Halyard research agenda — beyond current practice

> Status: research programme, not a claim of novelty or achieved results.
> Baseline date: 2026-11-25. Each hypothesis must be tested against current primary
> literature and mature implementations before a novelty claim is made.

## Purpose

Halyard is intended to be a media architecture whose security, boundedness, timing,
fidelity and performance properties are designed together. Research is an engineering
input: results must determine Core contracts, graph planning, codec boundaries and gates.

All implementation code remains first-party Capstan. External systems may be isolated
test oracles and benchmark baselines, never shipped media implementations.

## R8.1 — Compositional resource semantics for hostile media

**Problem.** Per-buffer limits do not bound aggregate retention, derived representations,
nested containers, concurrent decoders, queues, metadata, temporary workspaces or
cancellation cleanup. Aliases can be double-charged or released too early.

**Question.** Can a compositional resource algebra account for physical storage, logical
ownership, decoded expansion, CPU/work, queue capacity and time across a media graph,
while remaining failure-atomic and usable for parallel admission?

**Candidate contribution.** Typed resource vectors with charge provenance, reservation
leases, alias/derivation rules, atomic graph admission and a conservation invariant
relating reservations to live owned objects. Compare single-owner message passing with
synchronised shared admission; do not assume one is superior.

**Experiment.** Adversarial nested/parallel graphs; compare per-node, per-buffer and
graph-wide accounting. Measure peak live bytes, over-admission, rejection precision,
admission latency, contention and cleanup latency. Inject cancellation, worker death
and partial construction at every transition.

**H1.** The compositional ledger prevents over-admission and bounds retained resources
where local limits do not, without unacceptable throughput or tail-latency cost.

## R8.2 — Verified parser and serializer pipeline for real media formats

**Problem.** Media formats combine dependent lengths, optional/variant fields, recursive
structures, cross-field constraints, seeking, streaming and canonicalisation. A proof
of a parser model alone does not prove executable correspondence.

**Question.** Can Capstan express format descriptions from which bounded parsers and
serializers have machine-checkable memory/arithmetic safety, functional correctness,
non-ambiguity/non-malleability where relevant, and traceable implementation refinement?

**Candidate contribution.** Capstan-native declarative format language and verified
combinator substrate. Start with RIFF/WAVE and selected image chunks; later evaluate
recursive containers. Streaming and incremental parsing are first-class semantics.

**Baselines.** Vest (USENIX Security 2025), PulseParse/EverCBOR (CCS 2025), handwritten
Capstan parsers and format-aware fuzzing. Verified binary parsing is established prior
work; Halyard must not claim to be first.

**Experiment.** Proof time, automation, throughput, allocations, peak memory, rejected-
input work, round trips, ambiguity detection and model/implementation correspondence.

**H2.** A format description and shared verified combinators can prove useful properties
for realistic media structures at practical verification and runtime cost.

## R8.3 — Ownership-safe zero-copy and memory-lifetime control

**Problem.** Zero-copy can reduce bandwidth while increasing aliasing, retention,
pinning, fragmentation and lifetime complexity.

**Question.** Can linear/affine ownership, immutable spans, bounded leases and explicit
graph-edge lifetimes provide safe zero-copy across parser, decoder, transform and
presentation stages, including cancellation and worker boundaries?

**Candidate contribution.** Lease protocol with explicit transfer, borrow, clone, pin,
revoke and release semantics; graph planning charges retained storage for every live
alias. Identify language/runtime changes required.

**Experiment.** Compare copy, borrow, reference-counted lease and ownership-transfer
pipelines. Measure bytes copied, cache misses, bandwidth, peak retained memory,
fragmentation, GC pressure, p50/p99 latency and cancellation cleanup. Inject stale
handles, double release and use-after-revoke.

**H3.** Explicit leases reduce data movement while preserving a provable retained-memory
bound and eliminating stale-use/double-release states in model and implementation.

## R8.4 — Deterministic real-time audio execution

**Problem.** Audio callbacks have deadlines. Allocation, locks, page faults, I/O,
priority inversion, graph mutation and unbounded callbacks cause glitches even when
average throughput is high.

**Question.** Can a statically bounded execution plan provide measurable worst-case
work budgets and deterministic degradation across heterogeneous devices?

**Candidate contribution.** Control/data-plane split: immutable preflighted plans,
preallocated bounded buffers, callback-safe commands, explicit graph swap points,
bounded work quotas and deadline telemetry. Lock-free structures require a stated
memory-order proof and bounded-progress argument.

**Experiment.** Worst-case and tail callback time, deadline misses, x-runs, scheduler
jitter, memory faults, graph replacement and device reconfiguration under load.

**H4.** A preflighted plan bounds callback work under declared assumptions and reduces
deadline misses without hiding failure through silent drops or unbounded buffering.

## R8.5 — Multi-clock A/V synchronisation and discontinuity semantics

**Problem.** Audio, video, capture and network clocks differ. Drift, VFR, resets, seek,
pause, rate changes and packet reordering invalidate a single nominal frame rate.

**Question.** Can rational time plus explicit clock-domain estimation and a discontinuity
state machine bound sync error without unbounded latency or silently altering source time?

**Candidate contribution.** Integer/rational media time, clock-domain IDs, calibrated
mappings, bounded drift controllers and typed discontinuity transitions. Separate source
timestamp truth from estimated presentation time.

**Experiment.** Synthetic/recorded drift, VFR, wrap, clock step, hot-plug, seek/pause,
jitter and packet loss/reordering. Measure sync error, convergence, buffer occupancy
and latency across fixed-master, audio-master, video-master and adaptive policies.

**H5.** Explicit clock domains and rational timestamp semantics make drift and
discontinuity behaviour reproducible and bounded where floating-point accumulation or
implicit clock assumptions fail.

## R8.6 — Proof-preserving media graph optimisation

**Problem.** Fusion, zero-copy, SIMD and hardware acceleration can change rounding,
clipping, colour, channel order, timestamps, error handling and resource accounting.

**Question.** Can graph optimisations be justified as semantics-preserving transformations
with explicit resource-cost deltas?

**Candidate contribution.** Typed graph IR with reference semantics, transformation
contracts, resource annotations and planner-generated equivalence obligations.

**Experiment.** Differentially compare reference and optimised outputs; measure copies,
bytes moved, allocations, energy, throughput, latency and tail latency. Include numerical
edge cases and hardware/software parity.

**H6.** A proof-aware planner reduces copies and energy while preserving declared
bit-exact or tolerance-bounded semantics and the pre-admitted resource envelope.

## R8.7 — Format-aware differential fuzzing and semantic oracles

**Problem.** Random mutation often destroys structure; two implementations can agree
on the same malformed or ambiguous interpretation.

**Question.** Can grammar-aware generation, structure-preserving mutation, metamorphic
properties and independent oracles expose semantic divergences and resource bugs more
efficiently than byte fuzzing alone?

**Candidate contribution.** Format grammar producing valid seeds and near-valid mutations,
plus round-trip, permitted chunk permutation, irrelevant metadata insertion, every-
boundary truncation and equivalent-encoding properties. Resolve oracle disagreement
against the normative specification; majority vote is not truth.

**Baselines.** FormatFuzzer and coverage-guided byte fuzzers, plus isolated independent
oracles where licensing permits.

**Experiment.** Valid-input yield, semantic coverage, unique confirmed bug yield per
CPU-hour, time to divergence, minimisation quality and reproducibility.

**H7.** Grammar-aware mutation plus semantic properties and differential oracles finds
more distinct specification-relevant defects per compute-hour than byte mutation alone.

## R8.8 — Colour, HDR and scientific-data integrity

**Problem.** Pipelines conflate pixel encoding, transfer functions, primaries, white point,
range, chroma subsampling, alpha association, orientation and metadata. Scientific
pipelines add calibrated units, spatial orientation, provenance and losslessness.

**Question.** Can typed signal semantics prevent implicit conversions and make precision
loss, calibration and provenance explicit end-to-end?

**Candidate contribution.** Typed pixel/sample descriptors and transform graphs carrying
colourimetry, alpha, range, units, spatial calibration and provenance. No silent
colour-space or precision fallback.

**Experiment.** Reference patches, HDR transfer functions, gamut boundaries, chroma
siting, alpha, quantisation, lossless round trips, calibrated phantoms and CPU/GPU parity.
Medical use requires separate clinical, regulatory and interoperability qualification.

**H8.** Typed signal semantics eliminate classes of misinterpretation and make conversion
error measurable and reproducible across software and hardware paths.

## Research governance

Each workstream maintains a dated literature search log, inclusion/exclusion criteria,
threat model, assumptions, preregistered protocol where practical, named baselines,
hardware/compiler/input hashes, machine-readable raw results, scripts, independent
reproduction, negative results, and a trace from result to design decision.

A result is not state of the art because it is faster on one machine. Compare correctness,
security, worst-case resource use, latency tails, fidelity, portability, energy and
engineering cost. No composite score may conceal a severe regression in one dimension.

## Pullable research packages

| Issue | Research problem | Hypothesis | Gate / dependency |
|---|---|---|---|
| [#294](https://github.com/DavidFernee/Capstan/issues/294) | Compositional resource accounting and reservation leases | H1 | MC1; #285/#293 |
| [#295](https://github.com/DavidFernee/Capstan/issues/295) | Verified Capstan media format descriptions | H2 | MC0/MC1; #284/#285/#293 |
| [#296](https://github.com/DavidFernee/Capstan/issues/296) | Format-aware differential and metamorphic fuzzing | H7 | SH0/DE0; #288/#289 |
| [#297](https://github.com/DavidFernee/Capstan/issues/297) | Multi-clock media time and bounded A/V drift | H5 | MC1/MC3; #286 |
| [#298](https://github.com/DavidFernee/Capstan/issues/298) | Preflighted deterministic real-time audio | H4 | SH1 preparation; #285/#286/#293 |
| [#299](https://github.com/DavidFernee/Capstan/issues/299) | Distributed graph execution (deferred) | H9 | Post-MC3 |
| [#300](https://github.com/DavidFernee/Capstan/issues/300) | Proof-preserving graph rewrites | H6 | Stable graph IR; #286/#294 |
| [#301](https://github.com/DavidFernee/Capstan/issues/301) | Typed colour/HDR/scientific image semantics | H8 | DE0–MC6; #287/#289 |

## Initial literature anchors

- Yi Cai et al., “Vest: Verified, Secure, High-Performance Parsing and Serialization
  for Rust,” USENIX Security 2025:
  https://www.usenix.org/conference/usenixsecurity25/presentation/cai-yi
- Tahina Ramananandro et al., “Secure Parsing and Serializing with Separation Logic
  Applied to CBOR, CDDL, and COSE,” CCS 2025:
  https://doi.org/10.1145/3719027.3765120
- Rafael Dutra, Rahul Gopinath and Andreas Zeller, “FormatFuzzer: Effective Fuzzing
  of Binary File Formats,” 2024:
  https://doi.org/10.1145/3628157
- Leonardo Peroni and Sergey Gorinsky, “An End-to-End Pipeline Perspective on Video
  Streaming in Best-Effort Networks: A Survey and Tutorial,” ACM Computing Surveys
  57(12), 2025:
  https://doi.org/10.1145/3742472


## R8.9 — Distributed media graphs and collaborative rendering (deferred)

**Problem.** Moving DSP or media graph stages across devices, processes or cloud workers
introduces transport latency, jitter, clock drift, state migration, partial failure,
privacy exposure and non-comparable deadline measurements. Generic DAG schedulers do
not necessarily preserve block-synchronous audio semantics.

**Question.** Can Halyard represent a portable, bounded graph partition with explicit
state, clock, latency and trust contracts, and decide when remote execution is useful
without violating end-to-end deadlines or privacy constraints?

**Candidate contribution.** A graph-partition contract with serialisable node state,
bounded block transport, explicit clock mapping, capability-limited remote workers,
deterministic fallback and end-to-end cost accounting. This is deferred until local
Shanty scheduling and Media Core contracts are mature.

**Experiment.** Compare local, edge and remote partitions under measured RTT, jitter,
loss, bandwidth variation and worker failure. Report end-to-end latency distributions,
deadline misses, state-transfer cost, energy, privacy exposure and recovery behaviour.
Measure all latencies at the same pipeline boundaries.

**H9.** A contract-aware partitioner can identify workloads where distributed execution
improves throughput or collaboration without violating declared latency, resource and
privacy constraints.

These are entry points, not a complete review. R8 must extend into real-time audio,
clock synchronisation, OS scheduling, colour science, scientific imaging, ownership,
distributed DSP and formal refinement.

Additional starting points:
- O. Chaplia and H. Klym, “A Review of Cloud-Based Audio Processing Using Directed
  Acyclic Signal-Processing Graphs in Microservice Architectures,” 2026:
  https://publications.lnu.edu.ua/collections/index.php/electronics/article/view/5277
  (use as an emerging survey; independently verify venue and methods during review).
- “Multimedia group and inter-stream synchronization techniques: A comparative study”:
  https://doi.org/10.1016/j.ipm.2008.05.003
- “Consistency and Standardization of Color in Medical Imaging: a Consensus Report”:
  https://doi.org/10.1007/s10278-014-9721-0
- Ross Bencina, “Realtime audio programming 101”:
  https://w2.mat.ucsb.edu/240/A/2017/05/17/realtime.html
  (engineering guidance, not a formal worst-case execution proof).

