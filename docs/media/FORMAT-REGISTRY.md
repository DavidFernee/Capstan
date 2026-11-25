# Versioned media format registry

**Status:** schema and initial prototype inventory, version 1.0.0. This is not a declaration of release support.

The machine-readable inventory is docs/media/FORMAT-REGISTRY.json. Its normative JSON Schema (Draft 2020-12) is docs/media/FORMAT-REGISTRY-SCHEMA.json. Validate with:

    python3 -I scripts/media-registry-validate.py docs/media/FORMAT-REGISTRY.json
    python3 -I tests/media/test_registry.py

One record is one exact tuple of container, codec, profile, level, operation, bit depth, chroma and channel layout. Decode, encode, demux and mux are distinct operations; a record for one operation never implies another. Ancillary formats are separate from the primary codec and container. A container claim must not imply every codec/profile it can carry.

The dependency-free validator rejects unknown properties and status values, malformed source revisions, duplicate identifiers and duplicate registration tuples. Tuple uniqueness is a semantic constraint beyond ordinary JSON Schema. Diagnostics are sorted for deterministic output.

## Evidence fields

- source_revision pins the repository commit containing the implementation snapshot.
- licence_review and patent_review are independent; not-reviewed and unknown are not clearance.
- corpus_revision is none until a versioned, independently checked corpus exists.
- test_status distinguishes tests present from tests actually run and passed.
- fuzz_status is independent of unit-test status.
- assurance_level is not inferred from tests.
- known_limitations is mandatory, including for prototypes.

## Initial inventory

Only the documented Shanty RIFF/WAVE integer-PCM and Deadeye strict BMP decode prototypes are registered. Both deliberately carry present-not-run, not-run, prototype, not-reviewed and none evidence statuses. No encode, demux, mux, playback, general PNG decode or broader codec support is claimed.

## Change control

Increment schema_version only for incompatible schema changes. Increment registry_version for any published registry change. Every compatibility claim requires review of exact profile, direction, source revision, provenance, platform and corpus. Unknown or conflicting entries block publication; never silently choose one.
