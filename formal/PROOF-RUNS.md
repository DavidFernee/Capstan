# Formal proof-run ledger

This ledger records proof-checking attempts, including failures and superseded runs.
A green result is scoped to the exact source revision and verification layer stated.

## Current verified abstract-model result

**Result classification: model-only proof**

- **Commit:** `0e57f9a68082d7be4e88aad9f6c403498c79763a`
- **Base:** `bbe4fe2227a48ac266ba9d3e4dd6093a60ce4f10`
- **Formal CI run:** [45360322725](https://github.com/DavidFernee/Capstan/actions/runs/45360322725)
- **Date:** 2026-11-24
- **Lean toolchain:** `leanprover/lean4:v4.36.0`
- **Lean project:** `formal/CapstanFormal.lean`

Checks completed successfully:

1. Lake build of `CapstanFormal`.
2. Lean's bundled `leanchecker`.
3. `axiom-audit`: 98 declarations under `CapstanFormal`; dependencies were all within
   `propext`, `Classical.choice`, and `Quot.sound`.
4. Pinned Nanoda 0.4.32 independently checked **60,073 declarations with no errors**.
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
- `checkedAdd_overflow_fatal`
- `release_failure_preserves`
- `release_success_exact`
- `release_idempotent`

**Scope limitation:** these are theorems about the abstract Lean model. They do not
establish that the current C runtime implements the model. In particular, the current C
`cap_gc_release` still ignores `madvise` failure; implementation refinement is blocked
until that code is corrected and connected to the specification. No C implementation
theorem or whole-collector correctness theorem is claimed.

## Earlier attempts and corrections

| Run | Commit | Result | Finding and correction |
|---|---|---|---|
| [45358020558](https://github.com/DavidFernee/Capstan/actions/runs/45358020558) | `38e5bd565fc8046ad501472c028f7e6b18deb550` | Failed | Lean action required `lake-manifest.json`; committed the empty, versioned manifest. |
| [45358146064](https://github.com/DavidFernee/Capstan/actions/runs/45358146064) | `69c4e74b5d8f15978ba49384fb8dcd57a84abd70` | Failed | Same manifest defect on a later head; manifest was then added. |
| [45358265288](https://github.com/DavidFernee/Capstan/actions/runs/45358265288) | `378f116109bd11ebb7a2dfbf57f19ba897444914` | Failed | Initial Lean proof scripts contained syntax and proof errors. Corrected against compiler diagnostics; no theorem was marked proved. |
| [45358427741](https://github.com/DavidFernee/Capstan/actions/runs/45358427741) | `866f6222dae9b2a129c752a14b7a8146c0315a10` | Failed | Convenience Nanoda action could not detect the module root in the Lake TOML package. Replaced it with a project-owned invocation. |
| [45358699169](https://github.com/DavidFernee/Capstan/actions/runs/45358699169) | `4350a81d08db19247d1bf291638dc24412a26464` | Failed | Older Nanoda debug revision was incompatible with the current NDJSON export format. Updated to signed Nanoda 0.4.32 master and pinned all checker inputs. |
| [45359093086](https://github.com/DavidFernee/Capstan/actions/runs/45359093086) | `b09714a70c6daeecc703f4e7b95770729c96ff9d` | Passed, superseded | All type checks passed, but optional axiom pretty-printing emitted a non-fatal diagnostic. Disabled that unrelated output. |
| [45359603435](https://github.com/DavidFernee/Capstan/actions/runs/45359603435) | `ec7ae1ae5c552a8957f71e4f8671d802990ef5e4` | Passed, superseded | Clean run for the earlier model where overflow was represented as an absent result; later strengthened to explicit fatal outcome. |
| [45360322725](https://github.com/DavidFernee/Capstan/actions/runs/45360322725) | `0e57f9a68082d7be4e88aad9f6c403498c79763a` | Passed | Current model including explicit `CheckedAddResult.fatal` and `checkedAdd_overflow_fatal`; all checks above passed. |

Runs cancelled while newer PR events superseded them are omitted from the failure table;
they did not produce a proof result.

## Next proof obligations

1. Extend the Lean model to checked multiplication and metadata capacity growth.
2. Prove slot partition, free-list uniqueness/completeness and page-table invariants.
3. Prove large-object ordering/range invariants and mark-stack bounds.
4. Add the C-facing ACSL/Frama-C pilot and a concrete refinement argument.
5. Revisit collector reachability only after root-scanning and physical-object-layout
   assumptions are explicit.


## Current PR-head confirmation

The same model has been rebuilt on the current PR head after the specification and
workflow updates:

- **PR head:** `612eb7d33292be98ccc63f0df9d1254ee09c25fc`
- **Formal workflow:** [45360817831](https://github.com/DavidFernee/Capstan/actions/runs/45360817831) — passed
- **Full repository CI:** [45360817794](https://github.com/DavidFernee/Capstan/actions/runs/45360817794) — passed (Ubuntu/GCC, Ubuntu/Clang, macOS/Clang and supply-chain)

These checks validate the exact PR head above, not a later synchronisation commit.
The result remains model-only.

### Axiom-policy qualification

The Lean axiom audit for the model reports dependencies within
`propext`, `Classical.choice`, and `Quot.sound`. The independent Nanoda
configuration additionally lists `Lean.trustCompiler` as permitted and sets
`unpermitted_axiom_hard_error` to `false`. Consequently this workflow is an
independent consistency check under an explicit allowlist, not a strict
no-classical, no-quotient, or no-trustCompiler proof policy. Do not describe the
result as axiom-free. A stricter policy requires a separate decision and a
workflow change that fails on every dependency outside the approved set.


## Checked multiplication and bounded-growth model

**Result classification: model-only proof**

- **Commit:** `254ccacaaf8f35fe946db9a62adf3083ef7bc2ac`
- **Formal workflow:** [45590742560](https://github.com/DavidFernee/Capstan/actions/runs/45590742560) — passed
- **Lean toolchain:** `leanprover/lean4:v4.36.0`
- **Project:** `formal/CapstanFormal.lean`

The exact-head run completed the Lake build, bundled Lean `leanchecker`, and axiom audit. The audit covered 107 declarations under `CapstanFormal`, all within the existing allowlist `propext`, `Classical.choice`, and `Quot.sound`. The independent Nanoda 0.4.32 check reported 60,082 declarations with no errors (with exported but unpermitted `sorryAx` skipped); the negative-control false theorem was rejected.

New checked declarations:

- `checkedMul_sound`
- `checkedMul_complete`
- `checkedMul_exact`
- `checkedMul_overflow_fatal`
- `capacityGrowth_sound`
- `capacityGrowth_total`

The checked-multiplication model accepts precisely products within the supplied natural-number limit and otherwise returns the explicit fatal result. The capacity-growth model preserves adequate capacity or grows directly to the requested capacity if within the limit.

**Scope limitation:** these are model-only results. The capacity-growth definition is deliberately simpler than the current C `cap_gc_next_capacity` geometric-doubling loop. It does not establish that implementation's termination, saturation behaviour, initial-capacity handling or byte-size refinement. No C implementation theorem is claimed. The repository's separate C/platform CI was still running when this proof result was recorded.


## Slot partition and free-list abstract proofs

**Result classification: model-only proof**

- **Merged PR:** [#309](https://github.com/DavidFernee/Capstan/pull/309)
- **Exact PR head:** `13313b2cce442e6a33700e847281cfefb18651c0`
- **Formal workflow:** [45627584924](https://github.com/DavidFernee/Capstan/actions/runs/45627584924) — passed
- **Repository CI:** [45627584740](https://github.com/DavidFernee/Capstan/actions/runs/45627584740) — passed

The Lean model now proves:
- `SlotPartition.Valid` is preserved by abstract allocation and release;
- unrelated slot ownership is unchanged by a single-slot transition;
- free-list push/pop preserve bounded indices, uniqueness, soundness and completeness.

The model separates slot ownership from concrete C representation. It does not prove bitmap/free-list correspondence, intrusive pointer validity for ordinary classes, secret `free_slots` array correspondence, page-table invariants or concrete page-spare transitions.

PR #309 also reconciles the specification with mainline source changes: page release consumes the `madvise` result before updating release accounting, and secret small-object pages use out-of-line free-slot indices with a volatile payload wipe before publication. Those are source-level corrections, not machine-checked C refinement.

**Next implementation-facing gate:** add a pinned Frama-C/ACSL pilot for a small production helper, with a negative control and an explicit relation to the Lean machine model. Until that exists, all current allocator/collector theorems remain model-only.
