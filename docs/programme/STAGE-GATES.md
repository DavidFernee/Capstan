# Shared stage gates and product exit criteria

**Status:** programme baseline for review  
**Revision date:** 2026-11-25

## Gate protocol

Every work package records: gate, exact commit, implementation scope, tests/proofs, platform/configuration, assumptions, known exclusions, reviewer and decision.

| Gate | Entry condition | Required evidence to pass |
|---|---|---|
| G0 Ready | Work package proposed | Single outcome; bounded scope; owner; dependencies; risk/threat assumptions; acceptance tests/evidence; no unresolved design ambiguity |
| G1 Specified | G0 passed | Reviewed normative contract; inputs/outputs; error/trap semantics; resource limits; compatibility/versioning; security boundary |
| G2 Implemented | G1 passed | Code integrated on a review branch; focused tests; no unreviewed generated artefacts; documented operational behaviour |
| G3 Verified | G2 passed | Relevant conformance and negative tests; fuzz/property/adversarial tests where applicable; resource measurements; formal obligations or explicit not-applicable rationale |
| G4 Independently assessed | G3 passed | Independent review report; findings triaged; reproducible evidence; assumptions/TCB and residual risks explicit |
| G5 Accepted | G4 passed | Product owner accepts exact revision; release/compatibility notes; support and rollback plan; claims manifest updated |

Decision values:
- **PASS:** all required evidence is present and reviewed.
- **CONDITIONAL PASS:** a narrow, explicitly stated exception is accepted with owner and expiry; claims are restricted accordingly.
- **FAIL:** acceptance criteria not met.
- **UNKNOWN:** evidence absent, stale, unrepeatable or insufficient. UNKNOWN blocks promotion.

## Product exit criteria

### Capstan
- Normative language and CCAM contracts are versioned and conformance-tested.
- Decoder, validator, evaluator and backend boundaries have explicit schemas, failure behaviour and resource limits.
- Differential vectors cover the supported profile; implementation/model correspondence is claimed only where proved.
- Compiler, runtime, standard library, native backend and bootstrap trust boundaries are separately inventoried.
- C-free status is reported per pipeline stage, platform and dependency; no generated-C fallback is concealed.
- Formal results identify exact theorem, model, assumptions, axioms/checker, implementation revision and correspondence scope.

### Shroud
- Layout, text, widget, input, focus/cancellation and rendering contracts are specified.
- Per-operation and aggregate resource bounds are enforced before expensive allocation/work.
- Image/font/export parsers are bounded and fuzzed; output amplification and cumulative memory are measured.
- Platform hosts expose minimal, documented capability/syscall surfaces.
- Accessibility, Unicode integrity, deterministic test fixtures and platform conformance are evaluated.
- A frame budget is not described as a process-wide memory guarantee.

### Anchor
- Editor and language services consume canonical Capstan diagnostics and compiler APIs.
- Workspace/project files are treated as untrusted; path traversal, symlink, archive, subprocess and environment boundaries are tested.
- Build/test/debug tasks have bounded resources, explicit cancellation and reproducible command provenance.
- Extensions/plugins (if supported) have a documented permission and isolation model.
- No duplicate parser/type checker silently diverges from Capstan's acceptance rules.
- A minimal vertical slice opens a project, edits source, reports compiler diagnostics, builds/tests and safely handles malformed/untrusted projects.

### Keel
- Scene graph, transforms, asset formats, import pipeline and resource ownership have normative contracts.
- CPU/GPU allocation, lifetime, synchronization and teardown are bounded and failure-atomic where promised.
- Shader and asset ingestion are treated as hostile-input boundaries; parsers and compilation stages are fuzzed and resource-limited.
- Deterministic simulation/replay has a defined scope, numeric model and platform caveats.
- Rendering correctness is tested against reference scenes, invariants and differential/golden outputs; tolerance and nondeterminism are explicit.
- A vertical slice demonstrates asset ingestion through scene update to rendered frame without overstating driver/hardware verification.

### Capstan Media Core
- Bounded byte-source/sink contracts specify ownership, EOF, short reads/writes, cancellation, seeking and failure atomicity.
- Rational/integer timebases and checked timestamp rescaling specify overflow, wrap, rounding, discontinuity, seek and VFR behaviour.
- Aggregate resource ledger reserves bytes, allocations, tracks, chunks, samples, pixels, frames, work, threads and queue capacity before expensive work.
- Format/codec registry separates container, codec, profile, level, ancillary data and operation direction; registrations are versioned and deterministic.
- Codec-worker protocol has explicit capabilities, quotas, cancellation, timeout, crash handling and independent output validation.
- Core has no dependency on Shanty or Deadeye; media primitives are not duplicated in either engine.

### Shanty
- Initial WAV/RIFF parser and PCM sample-frame path pass a legally redistributable, independently checked corpus including malformed and boundary cases.
- Audio graph, sample formats, channel layouts, resampling and mixing semantics are explicit and deterministic for the declared profile.
- Real-time device callbacks do not block, allocate unpredictably, perform I/O or acquire contended locks; device APIs are separately gated.
- Capture/playback, codecs, synthesis, spatial audio and streaming are individually qualified by exact format/profile/direction and platform.
- No playback or codec support is claimed merely from parser support or offline vectors.

### Deadeye
- The initial image format is selected after parser, licensing, patent, provenance and security review; Shroud PNG output is not assumed to be a general decoder.
- Image/frame descriptors define dimensions, stride, pixel format, alpha, colour primaries, transfer, matrix and range.
- Image/video parsers, demuxers, decoders, encoders and subtitle/metadata handlers have bounded resource use and adversarial corpora.
- Rational presentation timestamps, VFR, frame duration, seek and discontinuity semantics are tested.
- Hardware/software paths and decode/encode directions are reported separately; no video playback claim before the full path is integrated and tested.

### Cross-product media integration
- Shroud core remains media-independent; optional Halyard–Shroud adapters consume versioned media presentation APIs without introducing a reverse dependency from either media engine.
- Keel may consume and orchestrate media graphs but does not redefine container/codec semantics or bypass Core budgets.
- A/V synchronisation defines master-clock policy, drift correction, pause/seek/resync and clock-domain transitions.
- Anchor exposes media inspection/playback workflows only through approved APIs and bounded project/workspace permissions.

## Media-specific gate sequence

The media family uses the product gates in `docs/media/ARCHITECTURE.md` in addition to shared G0–G5:

| Media gate | Scope | Required exit evidence |
|---|---|---|
| MC0 | Architecture and threat model | Reviewed acyclic dependencies, ownership, threat model, format taxonomy, provenance/licence/patent policy and research hypotheses |
| MC1 | Core substrate | Byte/stream contract, rational timebase, aggregate ledger and format registry; executable conformance vectors and adversarial boundary tests |
| SH0 | Shanty first slice | WAV/PCM offline decode, exact sample vectors, malformed corpus and deterministic output |
| DE0 | Deadeye first slice | Selected image format, bounded decode, frame descriptors, malformed corpus and pixel oracle |
| MC2 | Codec-worker boundary | Capability-minimal protocol, quotas, cancellation, crash/timeout handling and independently validated output |
| SH1 / DE1 | Device/presentation foundations | Audio callback and video presentation contracts, platform integration and timing tests |
| MC3 | Synchronized graph | Master clock, VFR, drift correction, bounded queues, seek/pause/discontinuity tests |
| MC4 | Compatibility expansion | Versioned format matrix, per-profile/per-direction corpus results and legal review |
| MC5 | Assurance/performance | Vulnerability ledger, SBOM/advisory reconciliation, fuzz/sanitizer evidence, proof scope and reproducible benchmarks |
| MC6 | Scientific/professional integration | Separately specified scientific/digital-twin, HDR, spatial-audio and production workflows |

MC0–MC6 are media-family gates; they do not replace shared G0–G5. Passing an architecture gate does not imply a codec is implemented. See [media architecture](../media/ARCHITECTURE.md) and [media security assurance](../media/SECURITY-ASSURANCE.md).

## Evidence requirements

For each result, retain:
- source commit and branch/ref;
- toolchain, dependency lock and platform/architecture;
- exact commands and environment;
- raw test/proof/benchmark output and exit status;
- input corpus/seed and expected output;
- reviewer identity/role and date;
- limitations, exclusions and known failures.

A benchmark without a workload definition, hardware/software identity and repeatable harness is not a programme result. A proof without an audited model-to-specification trace and required implementation correspondence cannot support an implementation correctness claim.

## Release qualification

Each product has an independent release scorecard and release decision. The ecosystem has a compatibility matrix covering Capstan compiler/runtime versions, Shroud API, Anchor compiler-service protocol and Keel/Shroud rendering interfaces. No product inherits another product's release approval.
