# Keel from-scratch and Capstan-only implementation policy

**Status:** normative architectural constraint for Keel and Keel-owned companion systems.
**Applies to:** Keel engine, Keel Science, Keel Studio/game-development tooling, asset pipeline, renderers, simulation, Shanty audio, Deadeye video, media facilities, test fixtures, build tools and all Keel-owned shipped supporting libraries.

## 1. Governing rule

All Keel-owned implementation code must be written from scratch in Capstan. The project must not embed, wrap, vendor, fork, link against or delegate core functionality to an existing game engine, rendering engine, physics engine, scientific-computing framework, media library, parser library or general-purpose third-party runtime library.

This applies to production code, editor code, asset processing, importers, decoders, format adapters, test support that ships with the product, and runtime dependencies. A thin Capstan wrapper around a C/C++ library is not a Capstan implementation and is not permitted as a product shortcut.

The same rule applies to Keel Science: scientific types, dimensional analysis, coordinate transforms, imaging ingestion, geometry conversion, numerical methods, provenance, uncertainty propagation, twin state and validation logic are Keel-owned Capstan implementations.

## 2. What "from scratch" means

- New source code authored for this repository, with explicit design, review, tests and provenance.
- Algorithms may be informed by published mathematics, standards, peer-reviewed research and public vulnerability analyses.
- Protocols, file formats and standards may be implemented from their normative specifications, subject to applicable licensing and patent review.
- No copying or adapting implementation code from existing engines or libraries unless a separately approved legal and architectural exception is recorded. The default is no such exception.
- No hidden runtime delegation to a third-party implementation behind a nominally native API.
- Every implementation has an identified owner, threat boundary, resource contract, conformance suite and dependency record.

"From scratch" does not mean reinventing the operating system, CPU instruction set, graphics hardware or device firmware. These are external platform boundaries, not Keel implementation dependencies. Keel must interact with them through narrow, documented Capstan interfaces and explicitly account for their trust and failure assumptions.

## 3. Language and implementation boundary

All Keel-owned product implementation and shipped build/runtime tooling must be Capstan. This includes:
- spatial mathematics, geometry and scene representation;
- software rasterisation, render graph and all future GPU command construction;
- simulation, collision, physics, animation and world systems;
- audio/video processing and media format parsing/decoding;
- asset import, compression/decompression, serialization and validation;
- scientific and biomedical data structures, numerical algorithms and format adapters;
- project model, editor/authoring logic, diagnostics, profiling and build orchestration;
- networking, replication and extension/plug-in policy;
- test subject implementations, conformance fixtures and product-side benchmark workloads. Capstan-native tests are preferred wherever the language can express the required property.

No C, C++, Rust, Zig, Swift, Java, Python, JavaScript or other language implementation may be shipped as a Keel subsystem or runtime dependency. This prohibition does not forbid independent, non-shipped test oracles under the preceding rule. Independent test oracles, fuzz-input generators, corpus minimisers and analysis scripts may use another language when independence materially improves assurance (for example, arbitrary-precision arithmetic as an oracle for bounded Capstan integer code). Such tools are test-only: they must never supply product functionality, be linked into or shipped with Keel, or become a runtime/build dependency. Their language, version, inputs and role must be recorded; Capstan-native conformance tests must still exercise the actual implementation. Any temporary exception requires explicit approval, a named scope, removal criterion and migration issue; it must never silently become permanent.

## 4. Current Capstan bootstrap reality

The repository's current compiler/runtime path is not yet a fully self-hosted, C-free toolchain. The C-backed compiler path and host platform interfaces are existing Capstan bootstrap constraints. This policy does not pretend that those foundations have already been replaced.

Keel implementation must:
1. target only language and runtime features demonstrated by the exact Capstan revision in use;
2. avoid guessed syntax, APIs, memory, numeric, concurrency or platform semantics;
3. record any bootstrap dependency in the build provenance and assurance case;
4. keep Keel's own implementation source entirely in Capstan;
5. feed missing language/runtime capabilities back to the Capstan research stream;
6. migrate build and execution dependencies toward the C-free Capstan path as that path becomes validated.

The long-term target is a reproducible, self-hosted Capstan toolchain capable of building and running Keel without a C implementation of Keel subsystems. Until the bootstrap chain is proven, claims must distinguish Capstan-authored source from the compiler/runtime used to build it.

## 5. Dependency policy

The live [external dependency and trusted-boundary register](DEPENDENCY-REGISTER.md) records the current compiler/bootstrap, test-oracle, Shroud, platform and deferred GPU boundaries. It is an initial inventory, not an SBOM or proof that all transitive dependencies have been discovered.

Runtime dependencies on third-party engine/library implementations are prohibited. No vendored source, binary blobs, dynamic library, package-manager dependency or system library may silently provide Keel functionality.

Permitted external references and boundaries:
- normative specifications and standards;
- published algorithms and mathematical literature;
- public vulnerability advisories, CVEs, postmortems and security research;
- operating-system and device interfaces required to access hardware and host services;
- hardware, firmware and drivers, with explicit trust-boundary disclosure;
- independently developed test data where licensing and provenance permit.

A dependency register must classify every external item as specification, research reference, development-only tool, build-time tool, host ABI, device/driver, data fixture or prohibited runtime implementation. Each entry records version, licence/patent review where relevant, purpose, trust implications and whether it is present in a shipped artifact.

## 6. Known-problem avoidance and vulnerability coverage

The goal is not to claim that a vulnerability-free system can be guaranteed. The enforceable rule is that every known relevant vulnerability class discovered through standards, CVEs, advisories, engine postmortems, academic research, fuzzing and independent review must be:

1. entered into a versioned vulnerability and design-hazard register;
2. mapped to affected Keel components and attack surfaces;
3. addressed by an explicit design constraint or documented reason it is not applicable;
4. covered by implementation checks, tests, fuzz properties, proofs or isolation controls appropriate to the claim;
5. represented in a regression corpus where a reproducer can safely be retained;
6. assigned residual risk, owner and review status.

The live [vulnerability and design-hazard register](VULNERABILITY-REGISTER.md) is the authoritative tracking location. It is an initial register, not a complete inventory; systematic CVE/advisory/research surveys remain mandatory before each subsystem enters implementation.

Coverage must include memory and lifetime errors; integer overflow and truncation; parser differentials; decompression and resource-exhaustion attacks; path traversal and archive extraction; malformed media and image inputs; shader/compiler complexity; GPU command and driver boundary failures; race conditions and stale handles; numerical instability and geometry degeneracy; determinism failures; network desynchronisation and authentication; serialization/version confusion; plugin escape; supply-chain compromise; privacy leakage; unsafe diagnostics; and editor/project-file attacks.

A CVE catalogue is not a complete threat model. Attack classes, design hazards and failure modes must be tracked even when no CVE exists.

## 7. Research without implementation inheritance

Keel must learn from existing systems without inheriting their implementation. For each major subsystem, record:
- representative existing approaches and their documented strengths;
- known defects, vulnerabilities, postmortems and failure patterns;
- research literature and normative specifications;
- the design decision adopted or rejected and why;
- the Keel-specific implementation strategy;
- a falsifiable test plan and comparative baseline.

The objective is not to reproduce another engine's feature list. It is to understand the hard problems, design a better architecture, and demonstrate improvements with reproducible evidence.

## 8. Assurance and acceptance gates

No subsystem is accepted solely because it compiles or passes happy-path tests. Each gate requires:
- Capstan-only source audit and dependency/SBOM review;
- explicit threat model and data-flow map;
- pre-allocation and aggregate resource limits;
- positive, negative, boundary and adversarial tests;
- grammar-aware fuzzing for all untrusted parsers;
- mutation testing of validators and security checks;
- property/differential testing against independently derived oracles;
- formal verification where properties and toolchain maturity justify it, with implementation correspondence;
- reproducible performance and quality measurements;
- independent review of security-critical code;
- residual-risk record and vulnerability response plan.

Evidence must name exact commit, compiler/runtime revision, target, configuration, corpus, seeds, tools, raw outputs and reproduction procedure. Claims are scoped to the tested implementation and assumptions.

## 9. Exceptions

No exception may be inferred from convenience, performance, schedule or familiarity with an existing library. A proposed exception must state:
- the precise functionality and boundary;
- why a Capstan implementation is currently infeasible;
- security, licensing, patent and supply-chain consequences;
- the minimum interface and authority granted;
- a time-bounded removal/migration plan;
- explicit maintainer approval and public record.

An exception does not change the default architecture and must not be described as a from-scratch Capstan implementation.

## 10. Definition of done

The policy is fulfilled only when:
- all Keel-owned shipped source is Capstan;
- no prohibited third-party implementation is linked or embedded;
- the complete shipped dependency and trust-boundary inventory is published;
- each known relevant vulnerability class has a disposition and evidence;
- the self-hosted build path and its limitations are documented;
- independent reviewers can reproduce the assurance and benchmark results.

Until then, the project must describe this as a target and report the exact gaps.