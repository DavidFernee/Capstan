# Formal proof-run ledger

This ledger records proof-checking attempts, including failures and superseded runs.
A green result is scoped to the exact source revision and verification layer stated.

## Current verified model result

**Result classification: model-only proof**

- **Commit:** `ec7ae1ae5c552a8957f71e4f8671d802990ef5e4`
- **Formal CI run:** [45359603435](https://github.com/DavidFernee/Capstan/actions/runs/45359603435)
- **Date:** 2026-11-24
- **Lean toolchain:** `leanprover/lean4:v4.36.0`
- **Lean project:** `formal/CapstanFormal.lean`

Checks completed successfully:

1. Lake build of `CapstanFormal`.
2. Lean's bundled `leanchecker`.
3. `axiom-audit`: 65 declarations under `CapstanFormal`; dependencies were all within
   `propext`, `Classical.choice`, and `Quot.sound`.
4. Pinned Nanoda 0.4.32 independently checked **60,041 declarations with no errors**.
   It skipped the exported but unpermitted `sorryAx`; the separate axiom audit confirms
   no `CapstanFormal` declaration depends on it.
5. Negative control: a deliberately invalid theorem claiming `False` was rejected by
   Lean, and the workflow confirmed that rejection.

Pinned independent-checker inputs:

- lean4export commit `df81913eee5519d5a88ae5b0fd701b5298cc29ab`
- nanoda_lib commit `0da9f98feadd3a0a2ef4b3dbcf52a298a6fef929`
- Rust/Cargo `1.100.0`
- Nanoda's committed `Cargo.lock`, enforced with `cargo build --locked`
- Lean action commit `ba3fdfe5c4476c925da13bf11a005ddb47e47aee`

### Theorems covered

- `checkedAdd_sound`
- `checkedAdd_complete`
- `checkedAdd_exact`
- `release_failure_preserves`
- `release_success_exact`
- `release_idempotent`

**Scope limitation:** these are theorems about the abstract Lean model. They do not
establish that the current C runtime implements the model. In particular, the current
C `cap_gc_release` still ignores `madvise` failure; implementation refinement is
blocked until that code is corrected and connected to the specification.

## Earlier attempts and corrections

| Run | Commit | Result | Finding and correction |
|---|---|---|---|
| [45358020558](https://github.com/DavidFernee/Capstan/actions/runs/45358020558) | `38e5bd565fc8046ad501472c028f7e6b18deb550` | Failed | Lean action required `lake-manifest.json`; committed the empty, versioned manifest. |
| [45358146064](https://github.com/DavidFernee/Capstan/actions/runs/45358146064) | `69c4e74b5d8f15978ba49384fb8dcd57a84abd70` | Failed | Same manifest defect on a later head; manifest was then added. |
| [45358265288](https://github.com/DavidFernee/Capstan/actions/runs/45358265288) | `378f116109bd11ebb7a2dfbf57f19ba897444914` | Failed | Initial Lean proof scripts contained syntax and proof errors. Corrected against compiler diagnostics; no theorem was marked proved. |
| [45358427741](https://github.com/DavidFernee/Capstan/actions/runs/45358427741) | `866f6222dae9b2a129c752a14b7a8146c0315a10` | Failed | Convenience Nanoda action could not detect the module root in the Lake TOML package. Replaced it with a project-owned invocation. |
| [45358699169](https://github.com/DavidFernee/Capstan/actions/runs/45358699169) | `4350a81d08db19247d1bf291638dc24412a26464` | Failed | Older Nanoda debug revision was incompatible with the current NDJSON export format. Updated to signed Nanoda 0.4.32 master and pinned all checker inputs. |
| [45359093086](https://github.com/DavidFernee/Capstan/actions/runs/45359093086) | `b09714a70c6daeecc703f4e7b95770729c96ff9d` | Passed, superseded | All type checks passed, but optional axiom pretty-printing emitted a non-fatal diagnostic because no output destination was configured. Disabled that unrelated output; clean run is 45359603435. |

Runs cancelled while newer PR events superseded them are omitted from the failure table;
they did not produce a proof result.

## Next proof obligations

1. Extend the Lean model to checked multiplication and metadata capacity growth.
2. Prove slot partition, free-list uniqueness/completeness and page-table invariants.
3. Prove large-object ordering/range invariants and mark-stack bounds.
4. Add the C-facing ACSL/Frama-C pilot and a concrete refinement argument.
5. Revisit collector reachability only after root-scanning and physical-object-layout
   assumptions are explicit.

No C implementation theorem, whole-collector correctness theorem, or complete memory
safety proof is claimed by this ledger.
