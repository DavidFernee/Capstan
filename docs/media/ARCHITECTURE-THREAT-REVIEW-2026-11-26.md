# Halyard architecture and threat-boundary review

**Review date:** 2026-11-26  
**Reviewed baseline:** main at 189f19dd2a39c169e033691856d675b070fb2864  
**Disposition:** architecture direction accepted with explicit implementation and assurance blockers. This is an independent documentation review, not a formal verification result or release approval.

## 1. Review scope and source inventory

Reviewed:
- docs/media/HALYARD.md — product identity, ecosystem integration and implementation principle.
- docs/media/ARCHITECTURE.md — component graph, layers, codec boundary, threat model and stage gates.
- docs/media/FORMAT-CATALOGUE.md — format/profile and operation separation.
- docs/media/CORE-PRIMITIVES.md — byte sources/sinks, ownership, live and cumulative resource accounting, clocks.
- docs/media/SECURITY-ASSURANCE.md — vulnerability accounting, threat catalogue, test and release policy.
- docs/media/SHANTY-WAVE.md and lib/halyard/shanty.cap — current RIFF/WAVE prototype.
- docs/media/DEADEYE-BMP.md and lib/halyard/deadeye.cap — current strict BMP prototype.
- lib/shroud/png.cap and tests/shroud/png_budget.cap, tests/shroud/check_png_budget.py — PNG export and its tests/oracle.
- docs/ANCHOR.md and docs/ANCHOR-ARCHITECTURE.md — Anchor's current client boundary.
- docs/architecture/CCAM.md — CCAM semantics and current evaluator/refinement status.
- docs/architecture/C-FREE-EXECUTION.md — C-free compiler/runtime direction and remaining trust boundary.

The mainline lib/ directory contains crypto.cap, halyard/ and shroud/. No Keel implementation module is present in that inventory; Keel is an architectural consumer/orchestration target, not an implemented Halyard dependency in this baseline.

## 2. Architecture decisions

### Accepted component ownership

| Component | Owns | Must not own |
|---|---|---|
| Capstan language/compiler/runtime | Source semantics, compilation, execution and language/runtime safety | Media container or codec semantics |
| Media Core | Bounded byte sources/sinks, resource and ownership contracts, checked arithmetic, clocks/timebases, format registration and shared media errors | Audio/image codec policy or product-specific UI |
| Shanty | Audio ingest, decode/encode, playback/capture and audio processing | Video/image semantics or Shroud UI |
| Deadeye | Image/video ingest, demux/decode, encode and frame/image processing | Audio-engine semantics or Shroud UI |
| Shroud core | Deterministic rendering, widgets, input, accessibility and PNG export | Media decoding, codec selection or media resource policy |
| Keel | Future application/media graph and lifecycle orchestration | Duplicate codec semantics or bypass Core resource contracts |
| Anchor | IDE/workspace, compiler/LSP process adapter and Shroud presentation | Compiler verdicts, codec semantics or assurance authority |
| CCAM | Defined abstract execution semantics and implementation-linked verification target | A media codec runtime or a substitute for parser conformance |

These boundaries are coherent. Core remains below Shanty and Deadeye; the engines remain independent; Shroud remains media-independent; the optional Halyard–Shroud adapter is the only planned bridge. Anchor and Keel are consumers, not providers of media semantics.

### Dependency graph

The provider-to-consumer graph in ARCHITECTURE.md is acyclic. A valid topological ordering is:

1. Capstan language/compiler/runtime (common execution substrate);
2. Media Core and Shroud core;
3. Shanty and Deadeye (each depends on Media Core, neither on the other);
4. Keel and the optional Halyard–Shroud adapter;
5. Anchor (which may consume the adapter).

The declared edges are Capstan→Core/Shroud/Shanty/Deadeye/Keel/Anchor; Core→Shanty/Deadeye; Shroud/Shanty/Deadeye→Keel; Shroud/Shanty/Deadeye→optional adapter; adapter→Anchor. No edge returns from a consumer to a provider. This confirms the declared architecture graph, not every possible future source import; CI should eventually enforce the graph against actual module imports.

### Format model

Container, codec, profile, level, operation direction and ancillary data must remain separate. A WAV container record is not a generic audio codec claim; BMP profile support is not general image support; PNG export is not PNG decode; decode never implies encode. The format catalogue's target rows remain non-claims until backed by exact implementation and evidence records.

## 3. Cross-system integration review

- **Capstan / C-free:** Halyard is authored in Capstan, but the production compiler/runtime still has a C-backed generated-C path. Until the C-free bootstrap and native execution path are qualified, that compiler, C runtime, host C compiler, linker and platform ABI remain part of the Halyard trusted computing base. Capstan-authored media source alone does not close this boundary.
- **CCAM:** CCAM provides a separate, Capstan-native evaluator and a path toward defined machine semantics. Its current documentation explicitly says it is not yet a conforming v0.1 machine and has no Lean refinement theorem connecting the evaluator to the model. It can support future parser/decoder semantics work, but no Halyard implementation property is currently proved by CCAM.
- **Shroud:** PNG source is an encoder/export path. The tests include bounded export and an external Python zlib oracle; neither establishes a general image decoder. Shroud core must remain independent of Halyard.
- **Anchor:** Anchor is a client of the compiler, LSP and Shroud. Its architecture correctly treats projects/files as untrusted and requires bounded child-process I/O, explicit command allowlists and visible provenance. A native Shroud host is not present in the baseline; do not claim a production GUI integration.
- **Keel:** The Halyard graph places Keel above media engines as a consumer/orchestrator. No Keel implementation module was found in mainline lib/; keep the dependency as a target contract and do not introduce reverse dependencies into Core, Shanty or Deadeye.

## 4. Threat-boundary inventory

| Boundary / adversary | Principal threat | Required control | Current evidence/status |
|---|---|---|---|
| Untrusted media bytes → byte source | Forged length, truncation, stale/mutated backing storage, offset overflow | Immutable bounded spans, checked offsets, opaque ownership, EOF/short-read contract | In-memory source prototype and tests exist; public mutable structs and ownership enforcement remain open (#293). |
| Parser → allocation/resource ledger | Decompression/work amplification, aggregate exhaustion, under-accounted temporary overlap | Atomic reservations, monotonic work budgets, live leases, every allocation tied to a ledger | Sequential prototype; cumulative/live semantics and parser allocation coupling incomplete (#303, #285). |
| WAV/BMP parser → decoded output | Malformed chunks/headers, integer overflow, invalid row stride/alignment, partial output | Strict profile, checked arithmetic, fail-closed parsing, no partial value, exact corpus and fuzzing | Narrow prototypes and colocated tests exist; independent corpus/fuzz/implementation-refinement evidence incomplete. |
| Decoder → colour/sample interpretation | Silent channel, alpha, bit-depth, gamma, profile or timebase reinterpretation | Typed descriptors and explicit conversion; no guessed fallback | WAV integer-domain and BMP opaque-alpha semantics documented; full colour management and clock model absent. |
| Codec worker → host | Arbitrary filesystem/network/process/device authority, malformed worker output, hangs | Restricted capabilities, bounded IPC, timeout/cancel, typed failure, OS sandbox where available | Architecture requirement only; no general codec-worker isolation implementation. |
| Media graph → concurrent resource state | Race in admission/release, double release, leaked leases, cancellation races | Single-owner or proved atomic concurrent ledger, structured cancellation and finite cleanup | Sequential reference/prototype only; no concurrent production ledger (#293, #303). |
| Shroud / Anchor host → OS | Native input/output, process, filesystem, window and accessibility boundary confusion | Explicit host capabilities, bounded adapters, no ambient authority | Shroud headless S0 exists; Wayland/native host contract and process adapter remain gated (#224, #279). |
| Build/dependency supply chain → shipped binary | Unknown provenance, vulnerable toolchain, copied codec code, unreviewed licence | SBOM/advisory reconciliation, pinned provenance, source audit, legal review | General supply-chain controls exist; media registry/legal review and media-specific advisory inventory are not complete. |
| Compiler/runtime → media execution | C runtime memory safety, compiler miscompilation, ABI/OS assumptions | C-free bootstrap, native codegen, implementation-linked proofs, reproducible build and TCB inventory | C-free programme and CCAM are active; current production path remains C-backed and not fully proved. |

## 5. Residual assumptions and blockers

1. The host OS, hardware, allocator, filesystem and platform APIs remain trusted or separately isolated boundaries; the language cannot prove their behaviour.
2. Current source/budget/lease objects are publicly mutable and sequential. Client discipline is not an enforceable ownership boundary.
3. Logical payload counters are not allocator-exact RSS/heap bounds. Temporary objects, list/object overhead and collector retention remain relevant.
4. Admission cannot yet guarantee rollback after allocator exhaustion because a recoverable allocation-result contract is absent.
5. Legacy unbudgeted media entry points remain callable; budgeted paths are not yet a mandatory security boundary.
6. Cancellation, worker isolation, real-time scheduling and complete clock/discontinuity semantics remain target contracts, not shipped guarantees.
7. Halyard parser tests and independent Python oracles do not establish Lean refinement, exhaustive correctness or absence of unknown vulnerabilities.
8. BMP licensing/patent applicability requires legal review; no media format entry may be marked cleared by inference.
9. The current C-backed compiler/runtime and host toolchain remain in the trusted computing base until C-free native execution is qualified.

## 6. Required follow-up gates

- MC0: publish the strict format registry and deterministic compatibility reporting (issue #287).
- MC1: opaque Core types, resource reservation ownership and separate cumulative-work/live-lease semantics (#293, #303, #285); independently validated WAV and BMP corpora (#288 and Deadeye follow-up).
- DE0: retain the narrow BMP profile, complete provenance/legal review and add adversarial corpus/fuzz coverage; no general PNG support claim.
- Cross-cutting: bind parser and decoder properties to CCAM/Lean models and concrete Capstan execution; preserve the distinction between tests, models, proofs and implementation refinement.
- Platform: do not ship native Shroud host or codec workers until capability/syscall contracts and sandbox tests are complete.
- Release: apply SECURITY-ASSURANCE.md to every shipped parser, codec, worker and transitive dependency; unresolved critical/high findings block release.

## 7. Review conclusion

The architecture's dependency direction and component ownership are coherent and acyclic as declared. The strongest design decision is the separation of Media Core resource/ownership contracts from independent audio and image/video engines, with Shroud remaining media-independent. The main risk is not an identified cycle; it is the gap between specified contracts and enforceable implementation: mutable state, incomplete live resource accounting, no general worker isolation, no full media corpus/fuzz evidence, and a C-backed production TCB. These are explicit blockers, not reasons to weaken the architecture.

This review closes only the architecture/threat-model review deliverable. It does not close implementation, security, C-free, formal verification or release-readiness work.
