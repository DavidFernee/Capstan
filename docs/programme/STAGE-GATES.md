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
