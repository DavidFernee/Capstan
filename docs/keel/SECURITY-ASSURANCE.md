# Keel security assurance

**Status:** proposed threat model and acceptance contract. It describes required design properties, not implemented protections or a security certification.

## 1. Security objective

Keel's long-term objective is to become the most secure general-purpose 3D rendering and simulation engine supported by independently reproducible evidence. This is an ambition, not a factual claim about the current project.

The primary security objective is to prevent compromise of the engine or host through hostile content, contain component failures, and bound resource consumption. The engine must remain predictable when assets are malformed, scenes are enormous, network peers are hostile, optional devices fail or resource budgets are exhausted.

Security is not established merely by writing application code in Capstan. The assurance case must account for the compiler, generated code, current C runtime, native host adapters, external libraries, operating system, GPU driver, device firmware and build supply chain.

## 2. Assets and trust boundaries

Protected assets:
- integrity and confidentiality of project files and user data;
- integrity of engine and editor state;
- availability within declared resource budgets;
- integrity of simulation and replicated world state;
- signing keys, credentials and build provenance;
- host resources and capabilities.

Untrusted inputs include:
- project manifests and scene files;
- meshes, skeletal rigs, animation clips and material graphs;
- textures, images, fonts, audio and video;
- compressed archives and package metadata;
- shader source and shader intermediate representations;
- plugins, scripts and extensions;
- network packets, replication messages and remote asset references;
- user-controlled command-line arguments and editor automation.

Trust boundaries:
1. external bytes to parser;
2. parser output to canonical asset representation;
3. canonical assets to scene/world state;
4. material/shader input to compiler and GPU command generation;
5. engine core to native platform/device adapters;
6. plugin/extension to engine services;
7. network peer to replicated state;
8. editor project to trusted editor process;
9. build inputs and dependencies to release artifacts.

Each boundary must specify validation, ownership, capabilities, resource budgets, failure behaviour and test evidence.

## 3. Adversary model

Assume an adversary can:
- supply arbitrary malformed or oversized files;
- construct valid files with pathological complexity;
- control network messages and timing;
- cause cancellation, disconnection, device loss and resource pressure;
- exploit parser/compiler/driver defects if a boundary is not isolated;
- exploit dependency or build-system compromise where supply-chain controls fail.

The baseline model does not assume protection against a malicious developer with repository write access, a fully compromised operating system/kernel, physical attacks on hardware, or a compromised GPU firmware. These residual risks must be disclosed rather than silently ignored.

A plugin or extension is not trusted merely because the project author installed it. Its authority must be explicit and revocable.

## 4. Required security properties

### 4.1 Input safety

- Parse from bounded byte spans; no unchecked pointer arithmetic or implicit trust in declared lengths.
- Validate counts, offsets, strides, dimensions, indices, recursion and cross-references before allocation or traversal.
- Reject integer overflow, invalid encodings, duplicate/conflicting fields and unsupported features according to a versioned schema.
- Define canonicalization and duplicate handling to prevent parser differentials.
- Avoid general-purpose object deserialization for untrusted content.
- Make parsing cancellation-safe and failure-atomic where practical.

### 4.2 Resource governance

Every subsystem must maintain both per-object and aggregate budgets. Required categories include:
- input bytes, decompressed bytes and expansion ratio;
- objects, nodes, children, references and hierarchy depth;
- vertices, indices, primitives, bones, animation tracks and keyframes;
- texture dimensions, mip levels, decoded bytes and upload bytes;
- shader instructions, control-flow complexity, compile time and temporary storage;
- scene memory, cache residency, streaming queues and in-flight I/O;
- physics bodies, contacts, solver iterations and simulation steps;
- audio voices, channels, decoded samples and buffers;
- network packet size, message count, queue depth and per-peer state;
- diagnostics, logs, traces and crash artifacts.

Each budget records unit, scope, default, maximum, accounting owner, preflight check, failure result, cleanup semantics and test. A per-file limit is not an aggregate process limit. A budget checked after allocation is not a pre-allocation guarantee.

### 4.3 Isolation and least authority

High-risk parsers, decoders, shader compilation and extension execution should be isolated where the platform and Capstan capability model permit. Isolation must define:
- process or execution boundary;
- allowed input/output channels;
- filesystem, network, process and device capabilities;
- memory, CPU, time and output limits;
- cancellation and termination semantics;
- crash recovery and output validation.

No plugin receives ambient host authority. No asset decoder can write arbitrary project files or invoke network/process APIs merely because the editor can.

### 4.4 GPU and driver boundary

The GPU and its driver are part of the trusted computing base for accelerated rendering unless a stronger isolation argument is demonstrated. CPU-side validation cannot prove vendor driver correctness.

Required controls:
- validate command/resource descriptions before submission;
- bound buffer sizes, dimensions, descriptor counts and command work;
- track ownership and lifetime of buffers and staging resources;
- validate shader IR before backend translation;
- handle device loss, timeout and reset without assuming pending work completed;
- avoid unsafe reuse of in-flight resources;
- keep software reference execution available for correctness and recovery where practical;
- document driver, firmware and hardware assumptions.

Do not describe the GPU backend as memory-safe or formally verified based solely on Capstan-side validation.

### 4.5 Network security

- Use authenticated, versioned protocols with explicit peer identity and authorization.
- Bound packet size, decompression, nesting, queue depth, rate and per-peer memory.
- Validate all state transitions and object references.
- Define replay, duplicate, reordering and timeout behaviour.
- Separate transport authentication from game/application authorization.
- Never allow replicated data to bypass local invariants or resource budgets.

### 4.6 Supply chain and build integrity

- Pin dependencies and toolchain versions.
- Produce SBOMs and provenance for release artifacts.
- Verify signatures and checksums through documented procedures.
- Reproduce builds where the toolchain permits; disclose non-reproducible components.
- Scan dependencies and generated artifacts.
- Keep build-time tools and runtime assets separate.
- Document the trusted computing base and update policy.

## 5. Security assurance evidence

For each security claim, maintain an assurance record containing:
- exact claim and scope;
- threat assumptions and excluded conditions;
- affected code, branch and commit;
- design mechanism;
- tests, fuzzers, proofs or audits supporting it;
- test corpus and tool versions;
- residual risks and known bypasses;
- owner and review date.

Required validation includes:
- grammar- and structure-aware fuzzing of every untrusted parser;
- mutation testing of validators and budget checks;
- sanitizer-enabled testing where the implementation language/toolchain permits;
- differential testing against independent parsers or reference models;
- fault injection for allocation failure, cancellation, I/O errors and device loss;
- long-duration stress and resource-exhaustion tests;
- independent code and architecture review;
- coordinated vulnerability disclosure and security patch policy.

A passing fuzz campaign is evidence about the tested corpus, harness and duration; it is not proof of absence of vulnerabilities.

## 6. Assurance milestones

| Gate | Required evidence | Claim permitted after passing |
|---|---|---|
| KSA-0 Threat model | Attack-surface inventory, adversaries, assumptions, TCB and residual-risk register | Threat model specified |
| KSA-1 Bounded input | Parser contracts, pre-allocation checks, fuzzing and malformed-input regression corpus | Named parsers validated against stated input/resource properties |
| KSA-2 Isolation | Capability policy, isolation tests, fault containment and resource-limit evidence | Named components isolated within stated platform scope |
| KSA-3 Formal assurance | Machine-checked properties plus implementation correspondence | Only the exact proved properties may be called formally verified |
| KSA-4 Adversarial assessment | Independent review, penetration testing, stress and remediation evidence | Assessment completed for the named revision and scope |
| KSA-5 Release assurance | SBOM, provenance, signatures, vulnerability process, supported-platform matrix and residual risks | Release assurance package published |

No gate implies that the entire engine is vulnerability-free. Claims must identify the components, versions, configurations and assumptions covered.

## 7. Vulnerability response

Before public production use, Keel must publish:
- a security contact and coordinated disclosure policy;
- severity and affected-version assessment process;
- supported release and backport policy;
- patch verification and regression requirements;
- public advisories with clear impact and mitigation;
- a policy for third-party dependencies and platform-specific issues.

Security fixes must receive regression tests and be incorporated into the adversarial corpus. A vulnerability report must not be dismissed merely because it violates an undocumented input assumption.

## 8. Initial K0 exit criteria

K0 security work is complete only when:
1. every proposed subsystem has a preliminary threat boundary;
2. all untrusted-input classes are inventoried;
3. the resource-budget register has owners and units, even where numeric limits remain to be experimentally determined;
4. the GPU/driver and native-host trust boundaries are explicit;
5. plugin and shader authority is not ambient;
6. security assurance milestones and claim discipline are adopted;
7. all unresolved questions are recorded as decisions or research tasks.

At K0, none of these requirements should be interpreted as an implemented security control.
