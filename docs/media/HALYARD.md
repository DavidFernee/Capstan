# Halyard — Capstan's media architecture

> **Status:** governing architecture identity and integration map, 2026-11-25.
>
> Halyard is the name of the media architecture of the Capstan ecosystem. It is the
> architectural system, not a codec, player or single library. Its implementation
> consists of Capstan Media Core, Shanty and Deadeye, all authored from scratch in
> Capstan under the governing [Design Charter](DESIGN-CHARTER.md).

## 1. Architecture

<escape>Halyard
├── Capstan Media Core — shared primitives and contracts
├── Shanty             — audio engine
└── Deadeye            — image and video engine</escape>

- **Capstan Media Core** defines bounded streams and sinks, buffer ownership, checked
  arithmetic, aggregate resource reservations, rational clocks/timebases, timestamps,
  format registration, structured errors, cancellation and graph/worker contracts.
- **Shanty** is the independent audio engine: ingest, decode/encode, playback/capture,
  mixing, resampling, synthesis, spatialisation and signal processing.
- **Deadeye** is the independent image/video engine: image and video ingest, demux/decode,
  encode, frame scheduling, presentation, composition, colour management, effects and
  streaming.

Shanty and Deadeye share Core contracts but retain domain-specific types, APIs and
schedulers. Neither depends on the other. The architecture is acyclic.

## 2. Ecosystem integration

- Capstan supplies the language, compiler and execution semantics.
- Halyard supplies media semantics and processing.
- Shroud core remains media-independent. An optional, separately versioned Halyard–Shroud adapter consumes media presentation APIs and Shroud rendering/input APIs; it is not a dependency of Shanty or Deadeye.
- Keel may consume and orchestrate media graphs and application lifecycles; it does not own codec semantics.
- Anchor and other applications consume the same stable, typed APIs.

## 3. Binding implementation principle

Every shipped Halyard implementation is written from scratch in Capstan. No third-party
multimedia framework or codec/parser implementation, vendored source, copied code,
generated-C media implementation, C shim or C/C++ media runtime may be linked or shipped
as part of Halyard.

External standards, specifications, research, security advisories, test vectors and
independently generated corpora may inform the work. Independent implementations may be
used only as isolated differential-test oracles, never as build or runtime dependencies.

The C-free Capstan compiler/runtime and self-hosting programme is part of the destination.
Until it is implemented and evidenced, any existing C-backed compiler/runtime/toolchain
boundary remains explicitly within the trusted computing base. Capstan-authored source
alone is not an end-to-end security proof.

## 4. Governing objectives

Halyard is designed to pursue five co-equal objectives:

1. **Security:** minimal authority, bounded work, explicit ownership, isolation, complete
   vulnerability accounting and evidence-backed assurance.
2. **Efficiency:** exceptional end-to-end throughput, latency, memory traffic and energy
   efficiency without sacrificing correctness or security.
3. **Effectiveness and fidelity:** precise media semantics for supported formats and
   demanding professional, scientific, medical and simulation workloads.
4. **Usability:** coherent APIs, safe defaults, excellent diagnostics and composable
   developer workflows.
5. **Research contribution:** measurable advances in secure parsing, bounded processing,
   ownership, scheduling, synchronisation, differential testing and graph optimisation.

These are ambitions, not unsubstantiated market claims. Comparative claims require
reproducible benchmarks, conformance evidence, security review and independent evaluation.

## 5. Research and application reach

Halyard must be designed to support, without conflating their distinct requirements:
professional audio/video production, games, broadcast, accessibility, scientific
visualisation, medical imaging, digital twins, simulation, real-time sensor streams,
HDR/wide-gamut workflows and future media forms.

Foundational types and contracts should preserve timing, provenance, precision, colour,
channel layout, metadata and transformation history where required by the domain.

## 6. Initial implementation status

The working branch contains Capstan-native Core primitives in `lib/halyard/core.cap`:
a bounded byte source, bounded in-memory sink, sequential five-dimensional ledger and
rational timestamp rescaling, with 25 colocated regression tests. Shanty has its first
offline RIFF/WAVE integer-PCM parser and decoder in `lib/halyard/shanty.cap`, with nine
Capstan tests. The WAVE profile and explicit limitations are documented in
[SHANTY-WAVE.md](SHANTY-WAVE.md).

These are prototypes, not MC1/SH0 gate exits. Opaque state, concurrent-safe or single-owner
accounting, lifetime-bound reservations, atomic reservation plus allocation, cumulative
work budgets, complete resource dimensions, ledger-coupled sink/sample allocation and
full clock/discontinuity semantics remain outstanding. See [Core primitive contract](CORE-PRIMITIVES.md),
issues #293 and #303, and the [detailed architecture](ARCHITECTURE.md).

## 7. Normative specifications and programme

| Document | Authority |
|---|---|
| [Architecture](ARCHITECTURE.md) | Detailed component boundaries, pipeline design, formats and staged implementation |
| [Core primitives](CORE-PRIMITIVES.md) | MC1 byte-source, sink, aggregate-ledger and rational-timebase contracts and release blockers |
| [Shanty WAVE slice](SHANTY-WAVE.md) | First audio parser/decoder profile, Capstan tests, limitations and release blockers |
| [Design Charter](DESIGN-CHARTER.md) | Co-equal objectives, trade-off rules and component review checklist |
| [Security Assurance](SECURITY-ASSURANCE.md) | Vulnerability accounting, threat catalogue, testing and release gates |
| [Format Catalogue](FORMAT-CATALOGUE.md) | Target formats and per-feature compatibility status |

Implementation status is tracked by the linked GitHub issues and pull requests. A target
or specification is not evidence that a codec, backend or security property is implemented.
