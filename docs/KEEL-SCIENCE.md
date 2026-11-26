# Keel Science: scientific computing, digital twins and biomedical research

**Working name:** Keel Science  
**Status:** K0 domain architecture proposal; no implementation, scientific validation or regulatory status is claimed.  
**Parent:** Keel engine and Capstan assurance programme.

## 1. Purpose and intended use

**Implementation constraint:** Keel Science is to be implemented from scratch in Capstan. No third-party scientific, imaging, numerical, medical-data or geometry library may provide runtime functionality. Standards such as DICOM, FHIR, BIDS, NIfTI and OME-NGFF may be implemented from their normative specifications through original Capstan code, subject to legal review. See [the Capstan-only policy](keel/FROM-SCRATCH-AND-CAPSTAN-ONLY.md).

Keel provides 3D rendering, spatial representation, simulation and resource-governed execution. Keel Science is a companion library for scientific and domain-specific models built on those foundations.

Intended research and engineering domains:
- industrial, infrastructure and environmental digital twins;
- robotics, autonomous systems and manufacturing simulation;
- computational anatomy, biomechanics and movement science;
- medical imaging, segmentation and image-derived geometry;
- computational physiology and biophysical modelling;
- neuroscience, neuroimaging, microscopy and bioimaging;
- geospatial, climate and other physical-science models.

Initial scope is research and engineering. The library is not a diagnostic system, treatment planner, clinical decision-support product or medical device by virtue of rendering or simulating biomedical data. Any future clinical intended purpose requires a separate safety, quality, validation and regulatory programme before implementation or deployment.

## 2. Design thesis: scientific meaning is data

Scientific correctness must be represented in the model, not left to comments or visual conventions. Scientific objects and derived results should carry:
- physical quantity, unit and dimension;
- coordinate reference frame and transform history;
- acquisition, observation, simulation and processing times as distinct concepts;
- source identity, version, provenance and lineage;
- method, algorithm, model and parameter versions;
- uncertainty, confidence or an explicit unknown state;
- calibration state and calibration provenance;
- quality flags, validation status and known limitations;
- distinction between measured, derived, estimated, imputed and simulated values.

A renderer must not turn missing, uncertain or invalid data into apparently authoritative output. Visualisation should expose uncertainty and data quality rather than conceal them.

## 3. Package boundaries

Keel Science is above Keel, not part of the engine core and not a dependency of Keel.

| Module | Responsibility |
|---|---|
| science.core | Quantities, units, dimensions, coordinate frames, time, uncertainty and provenance |
| science.data | Typed datasets, schemas, metadata, lineage, quality and validation reports |
| science.twin | Asset identity, hierarchy, telemetry, state estimation, synchronisation and lifecycle |
| science.imaging | Volumes, voxel geometry, image orientation, segmentation and derived surfaces |
| science.anatomy | Anatomical structures, regions, landmarks, meshes and relationships |
| science.biomechanics | Rigid/deformable bodies, tissue/material models, joints, loads and boundary conditions |
| science.physiology | Domain state variables and coupled model interfaces |
| science.neuro | Neuroimaging datasets, spaces, surfaces, tracts and experiment metadata |
| science.interop | Versioned import/export adapters for external standards |
| science.validation | Dimensional, spatial, temporal, statistical, schema and provenance checks |

These are conceptual modules. They do not assert that corresponding Capstan packages or APIs already exist. Public syntax and package layout must be reconciled with the actual compiler and module system before implementation.

## 4. Foundational contracts

### 4.1 Units and dimensions
- Quantities distinguish values from units; conversions are explicit and dimensionally checked.
- Incompatible dimensions cannot be silently combined.
- SI is the default internal convention where appropriate, while source units and original values remain traceable.
- Derived quantities record formula/model version and input lineage.
- Affine units, logarithmic quantities, angles, concentrations and domain-specific units require explicit conversion policies.

### 4.2 Coordinate frames
- Every spatial value belongs to a named, versioned frame.
- Handedness, axis directions, origin, units and conventions are explicit.
- Transform direction and composition order are specified.
- Scanner, voxel, patient, anatomical, atlas, world, device and display frames are distinct.
- Left/right and radiological/neurological conventions are never inferred from appearance.
- Transform chains retain provenance and uncertainty. Singular or ill-conditioned transforms fail explicitly.

### 4.3 Time and synchronisation
- Acquisition, observation, simulation, processing and wall-clock time are distinct.
- Time basis, timezone/offset, clock source and synchronization uncertainty are represented where relevant.
- Original timestamps and monotonic sequence information are preserved.
- Digital twins define stale-data thresholds, out-of-order handling, clock drift and missing-sample behaviour.
- Simulation clocks are never conflated with real-world timestamps.

### 4.4 Uncertainty and quality
- Measurement uncertainty, model-parameter uncertainty, numerical error and algorithmic confidence are different concepts.
- Missing uncertainty is unknown, not zero.
- Confidence scores from different methods are not assumed comparable.
- Propagation rules are declared for supported operations; unsupported propagation is reported.
- Visual encodings expose uncertainty, missingness, provenance and quality flags.

### 4.5 Provenance and lineage
Derived datasets retain source identifiers/hashes where permitted, acquisition and ingestion metadata, transformations, filters, software and algorithm versions, parameters, random seeds, validation results and unresolved warnings. Where an export format cannot preserve lineage, report the loss and retain a sidecar manifest.

## 5. Digital twin semantics

A digital twin is not merely a 3D model. It is a versioned relationship between a physical or conceptual asset and one or more digital representations.

A twin distinguishes:
1. asset identity, authority and asset class;
2. structure, components, topology and spatial frames;
3. observations, sensor measurements, timestamps, calibration and quality;
4. state estimates, method, uncertainty and freshness;
5. physical, statistical or learned model, version and validity envelope;
6. simulation initial conditions, inputs, solver and execution record;
7. interventions, scenarios and counterfactuals;
8. validation against observations, residuals, drift and failure modes.

Observed, estimated, simulated, planned and counterfactual states must never overwrite or masquerade as one another. Each update has source, timestamp, sequence and quality metadata. Synchronisation must handle stale, delayed, duplicated and contradictory telemetry within explicit budgets. Calibration changes create new model versions. Simulation output is never represented as measured reality.

Research targets include uncertainty-aware state estimation, bounded event ingestion, model-drift detection, multi-rate synchronisation, hybrid discrete/continuous simulation and reproducible scenario replay.

## 6. Biomedical and medical-research scope

Initial research workflows may include medical-image geometry, volume inspection, segmentation, anatomical landmarks, registration, finite-element and rigid-body biomechanics, gait and musculoskeletal simulation, computational physiology, neuroimaging and cohort-level research visualisation using appropriately governed data.

Imaging rules:
- preserve source pixels/voxels and acquisition metadata separately from derived surfaces and display assets;
- preserve orientation, spacing, origin, direction cosines and frame-of-reference identifiers;
- distinguish voxel indices, patient coordinates, atlas coordinates and renderer coordinates;
- track segmentation provenance, label maps, algorithm/model versions and reviewer edits;
- report topology and geometric error when surfaces are extracted;
- never treat a rendered mesh as a substitute for source images or acquisition metadata.

Model rules:
- record equations, model version, units, parameters, initial and boundary conditions;
- record calibration data/method, solver, discretisation, convergence and stability diagnostics;
- separate calibration data from independent validation data;
- state applicable population, tissue, device or operating range, exclusions and failure modes.

A model that converges numerically is not thereby physiologically valid. Visual plausibility is not scientific validation. The initial library must not diagnose, triage, recommend treatment or claim patient-specific clinical accuracy.

## 7. Interoperability strategy

Do not invent replacement healthcare or scientific data standards. Implement narrow, versioned adapters and preserve source semantics.

| Standard/ecosystem | Role | Initial scope |
|---|---|---|
| DICOM | Medical imaging and related metadata | Read-only import and conformance fixtures before write support |
| HL7 FHIR | Healthcare resource exchange | Explicitly scoped resource profiles and pinned versions |
| BIDS | Neuroimaging research organization | Dataset discovery, metadata validation and spatial provenance |
| NIfTI | Volumetric neuroimaging | Geometry-preserving import/export and header validation |
| OMOP CDM | Observational health research | Metadata/analysis integration, not a 3D scene format |
| OME-NGFF | Large bioimaging and multidimensional data | Future chunked, multiscale access |
| glTF | 3D scene/asset interchange | Geometry/material interchange; scientific metadata needs documented extensions or sidecars |

DICOM conformance is specific to parts, profiles and transfer syntaxes. FHIR, BIDS, NIfTI and OMOP versions and conventions evolve. Each adapter publishes a version-pinned conformance matrix. Start with metadata and structural validation, then read-only ingestion, then derived representations. Defer round-trip writing until semantic preservation is demonstrated.

## 8. Security, privacy and governance

Biomedical data can contain direct identifiers, quasi-identifiers, sensitive health information and re-identifying metadata. Removing names is not sufficient to establish anonymity.

Required design:
- data classification, purpose and authority metadata;
- consent, ethics approval, data-use agreement and jurisdictional constraints as governance inputs;
- least-privilege access and separation of identity data from research datasets;
- encryption and key management through reviewed Capstan/platform facilities;
- audit events for access, export, transformation and deletion;
- bounded, isolated parsing of every medical/scientific format;
- safe handling of private tags, free text, overlays and sidecars;
- controlled export and disclosure review;
- retention, deletion and backup semantics;
- no telemetry/crash upload of source medical data by default;
- synthetic fixtures for ordinary CI; real human data only in separately governed environments.

Pseudonymisation is not anonymisation. The library must not infer de-identification from superficial field removal. It must not ship real patient data in source control, tests, benchmarks, examples or bug reports.

## 9. Verification and validation

Keep these evidence layers distinct:
- **Software verification:** does the implementation satisfy its specification?
- **Numerical verification:** are discretisation, solver and floating-point errors controlled?
- **Model validation:** does the model represent the intended phenomenon for the stated use?
- **Data validation:** are inputs coherent, traceable and fit for the analysis?
- **Clinical validation:** if ever relevant, does the system perform safely and effectively for a defined clinical intended purpose?

Methods include dimensional-analysis tests, analytical and manufactured solutions, conservation laws, mesh/time-step convergence, independent solver comparison, uncertainty propagation, sensitivity analysis, calibration/validation separation, regression corpora and reproducible experiment manifests. Each result states whether it is analytical, measured, estimated, simulated or illustrative.

## 10. Research work packages

- **KS-01 — Typed units, frames and provenance:** test whether a compact scientific type layer prevents dimensional/frame errors; measure compiler/runtime overhead and mutation-test deliberate unit and transform mistakes.
- **KS-02 — Trustworthy image-to-geometry:** investigate geometry-preserving volume ingestion, segmentation, surface extraction and registration; measure spatial error, topology defects, metadata loss, resource use and parser robustness.
- **KS-03 — Digital-twin state and uncertainty:** test coexistence of observed, estimated, simulated and counterfactual state under delay, dropout, drift and contradictory observations.
- **KS-04 — Reproducible multi-physics:** investigate deterministic orchestration of rigid-body, deformable, fluid/thermal and domain-specific solvers; define coupling stability and error budgets.
- **KS-05 — Biomedical model validation:** establish independent biomechanics/physiology validation protocols; separate calibration from validation and quantify parameter/population uncertainty.
- **KS-06 — Privacy-preserving research workflows:** investigate minimisation, local processing, auditing, pseudonymisation boundaries and controlled exports; make no privacy guarantee without a precise threat model and evidence.
- **KS-07 — Standards conformance:** build version-pinned fixtures and measure semantic preservation, round-trip loss and conformance.

## 11. Milestones and gates

| Gate | Deliverable | Acceptance evidence |
|---|---|---|
| KS0 | Domain architecture and intended-use boundary | Reviewed data semantics, trust model, standards matrix and non-clinical scope |
| KS1 | Scientific core prototype | Unit/frame checks, uncertainty/provenance records and property tests |
| KS2 | Synthetic digital-twin slice | Timestamped telemetry, state estimation, stale-data handling, model versioning and replay |
| KS3 | Synthetic/public volumetric imaging slice | Validated geometry, segmentation fixture, surface extraction and measured spatial error |
| KS4 | Research model integration | One biomechanics or physiology model with independent analytical/numerical validation |
| KS5 | Governed interoperability | Version-pinned read-only adapters, security review and data-governance procedures |
| KS6 | Independent scientific evaluation | Reproducible experiments, external domain review, limitations and publication-ready evidence |

No gate implies clinical readiness or regulatory clearance.

## 12. First vertical slices

The first digital-twin demonstration uses a fully synthetic industrial asset (for example, a pump): known ground-truth state, synthetic timestamped sensors, delayed/missing/corrupted telemetry, a state estimator with explicit uncertainty, a 3D scene linked to asset identity and a replayable experiment manifest.

The first biomedical demonstration uses synthetic or public, appropriately licensed imaging data after format licensing and governance review. It demonstrates geometry preservation, coordinate transforms and segmentation provenance—not diagnosis.

## 13. Standards references

Pin exact editions and profiles when each adapter is implemented:
- DICOM: https://www.dicomstandard.org/current
- HL7 FHIR: https://hl7.org/fhir/
- BIDS: https://bids.neuroimaging.io/
- NIfTI: https://nifti.nimh.nih.gov/
- OHDSI OMOP CDM: https://ohdsi.github.io/CommonDataModel/
- OME-NGFF: https://ngff.openmicroscopy.org/
- glTF: https://www.khronos.org/gltf/

This list identifies candidate ecosystems, not conformance or endorsement.
