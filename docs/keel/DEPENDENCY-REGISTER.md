# Keel external dependency and trusted-boundary register

**Status:** initial inventory for K0/K1; revalidate against each release artifact.
**Scope:** Keel, Keel Science, Keel Studio, Shanty, Deadeye and Keel-owned build/test workflows.
**Policy:** [from-scratch and Capstan-only implementation](FROM-SCRATCH-AND-CAPSTAN-ONLY.md)

## Classification

- **Specification/reference:** normative text or published research; no implementation code is imported.
- **Capstan-owned:** implementation source maintained in this repository and written in Capstan.
- **Bootstrap/toolchain:** temporarily required to build or test Capstan; not Keel functionality.
- **Test-only oracle:** independent, non-shipped verification tool; cannot supply product behaviour.
- **Platform boundary:** OS, ABI, hardware, firmware or driver; external and explicitly trusted/assumed.
- **Prohibited:** third-party engine/library implementation used to provide Keel functionality.

## Current inventory

| Item | Classification | Current use / boundary | Required treatment |
|---|---|---|---|
| Capstan language/compiler | Capstan-owned | Keel source language and compiler acceptance authority | Use only syntax/features verified against the exact compiler revision |
| Current Capstan bootstrap | Bootstrap/toolchain | Repository build currently uses Python stage-0 translation, generated C, a host C compiler and Capstan's C runtime | Disclose in build provenance; never write Keel subsystem functionality in C/Python; migrate the toolchain under the C-free bootstrap contract |
| Host C compiler | Bootstrap/toolchain | Builds the current generated-C Capstan executable and test binaries | Pin/version-report; do not claim C-free Keel build or runtime until the C-free Capstan path is proven |
| Python 3 | Bootstrap/toolchain / test-only oracle | Current Capstan test suite uses Python; Keel geometry differential tests use Python arbitrary-precision integers as an independent oracle | Never linked or shipped; pin and report version; maintain Capstan-native tests of the actual implementation |
| Capstan C runtime and collector | Bootstrap/toolchain | Current compiled Capstan programs execute through this runtime | Explicit trusted computing base; audit separately; no Keel code may be delegated to it beyond generic Capstan runtime services |
| Shroud | Capstan-owned | Future UI, input, accessibility and host integration for Keel Studio | Consume only reviewed public Capstan interfaces; no Shroud private implementation coupling; no Shroud dependency in headless Keel core |
| Anchor | Capstan-owned / optional consumer | Potential code-centric project and debugging workflows | Never a Keel runtime dependency |
| Operating system and platform ABI | Platform boundary | File, process, memory, timing, display and device access | Narrow documented Capstan interfaces; least authority; platform-specific assurance |
| GPU driver, firmware and hardware | Platform boundary / deferred | No production GPU backend in K0/K1 | Defer until CPU reference semantics and driver trust assumptions are explicit; never claim driver correctness from Capstan-side checks |
| Python arbitrary-precision integer implementation | Test-only oracle | Independent oracle for exact 2D/3D orientation differential tests | Used only by tests; not a product implementation, runtime dependency or shipped artifact |
| DICOM, FHIR, BIDS, NIfTI, OME-NGFF, glTF and other interchange specifications | Specification/reference | Potential future format/semantic targets | Implement original Capstan adapters from normative specifications; version-pin; legal/patent review; no imported parser implementation |

## Prohibited runtime implementations

No third-party game engine, renderer, physics engine, geometry library, scientific-computing library, medical-imaging library, media decoder, archive library, serialization framework or general-purpose runtime library is approved to provide Keel functionality.

In particular, the project must not silently acquire functionality through transitive system packages, dynamic libraries, vendored source, binary blobs, package managers, generated bindings or command-line helper processes. A dependency cannot be reclassified as a platform boundary merely because it is installed on the host.

## Required review for every new dependency

Before approval, record:
1. exact name, version, source and hash;
2. classification and whether it enters a shipped artifact;
3. function provided and why original Capstan implementation is not yet feasible;
4. licence, patent and attribution review where applicable;
5. trust boundary, authority, data flow and failure modes;
6. known CVEs/advisories and design-hazard survey;
7. reproducible tests and removal/migration criterion;
8. explicit approval and owner.

A test-only oracle is not a product dependency, but its provenance and role remain recorded. If a test tool becomes necessary to build, run or ship Keel, it must be reclassified and reviewed.

## Current status

This is an initial inventory, not a complete SBOM or proof that no transitive dependency exists. K0/K1 have no approved third-party runtime library for Keel functionality. The current compiler/runtime bootstrap remains a disclosed transitional dependency. The exact dependency graph of every build and release artifact must be generated and reviewed before release.
