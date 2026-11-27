# G0 — Engineering baseline acceptance review
2026-11-27. Decision: HOLD pending integration and reproducible baseline. User authorized proceeding through G0, not waiver of evidence. Review is static and does not certify implementation.

| Criterion | Evidence | Disposition |
|---|---|---|
| G0-01 Architecture authority | #542 aa19a6dd; CCAM sole canonical IR | Candidate reviewed; merge pending |
| G0-02 Duplicate disposition | #544 closed unmerged | Unique-content comparison pending |
| G0-03 Requirements inventory | CAP-001–008, seven matrices, 113 parent/subordinate obligations | Draft established; review against current main pending |
| G0-04 Traceability | crosswalk maps all 19 RFC gaps to packages/gates | Draft established |
| G0-05 Scope and ownership | 19 packages, five existing workstreams, interface register | Proposed; confirm with coordination issue |
| G0-06 Configuration baseline | pinned historical main 3187b3adc3d9b2f5476c2d25ed410da1ec1c88ce | Refresh after integration; exact revision/toolchain manifest missing |
| G0-07 Reproducible verification | #542 formal-verification success, ci/CodeQL queued; #545 formal/CodeQL success, ci running; #548 b0bcddbf workflows queued at review | Hold; later documentation edits invalidate earlier head evidence for #548 |
| G0-08 Approval record | this review | Hold until all criteria dispositioned and independent review recorded |

## Exit sequence
1. Compare #544 against #542; preserve any unique valid requirements via reviewed change. Reconcile #545 against #540 backend changes.
2. Check current main and coordination issue; update branch, remove draft status after review, merge only exact-head green checks. Integrate #542 then #545 then #548, rechecking each against current main. No bypass.
3. Record integrated main SHA, toolchain versions/digests, host platform, commands, exact test results, workflow URLs and known failures. Execute repository-prescribed CI commands or obtain equivalent exact-main workflow evidence; do not invent results.
4. Refresh live PR/issue mapping and inventory; account for #538/#541 merged and #535 closed unmerged.
5. Review all seven matrices, identify gaps and duplicates; retain open G1+ obligations without claiming implementation completion. Record independent reviewer and explicit disposition.
6. Record G0 accepted in a reviewed decision only after above evidence exists. G1 work can be prepared in parallel but cannot be claimed accepted.

No compiler code or proof changed. No fresh build executed by this review. No schedules changed.

## Integrated evidence refresh — 2026-11-27
Candidate baseline: `549d5ad4d81f7a88e1d76a959aed6c65230e05c6` (merge #548); not a claim about later main revisions.

| Criterion | Updated evidence | Proposed disposition |
|---|---|---|
| G0-01 | #542 merged at `ceeb5068294e4ebd9e76b5a27c8e24c0338854e2` | Satisfied subject to review |
| G0-02 | #544 closed unmerged; full RFC/ledger comparison recorded in G0-PREPARATION.md | Satisfied subject to review |
| G0-03 | Seven matrices and supplemental coverage review in G0-REQUIREMENTS-REVIEW.md | Open: atomic inventory review against pinned revision |
| G0-04 | All 19 RFC gaps mapped in ARCHITECTURE-CROSSWALK.md | Established, review pending |
| G0-05 | Ownership proposal in G0-PREPARATION.md; coordination request posted in #25 | Open: owner confirmation |
| G0-06 | Candidate integrated revision pinned above | Partial: tree/dependency/toolchain/host manifest outstanding |
| G0-07 | #548 exact head `0b750abebacfd7c455ea97f591e49eb71adacef6` had successful ci, CodeQL and formal-verification workflows before merge | Partial: exact integrated revision verification not established; PR-only workflow lookup returned no runs for merge SHA |
| G0-08 | This successor review | HOLD: independent reviewer and explicit acceptance outstanding |

#545 is closed unmerged, not an integration dependency to revive blindly. #552 remains open for direct ELF backend reconciliation; #547 remains open; #549 has merged at `5feae0b77d77b7736cfe1cfb720567a28c91cc8b`. Preserve distinct assembly and direct execution profiles. Do not equate successful PR checks with reproducible integrated-main evidence. No fresh build executed in this refresh.

## Matrix structural review — pinned #548 baseline
All seven matrices inspected. Row counts: scalar 17, aggregate 18, native 18, frontend 18, GC 18, bootstrap 12, optimisation 12 (113 total). The count is a traceability inventory, not a completion metric. GC rows refine aggregate requirements; bootstrap and optimisation use local IDs and require explicit CAP-001 parent links. Proposed parent mapping: GC01–18 R04/R05/R09; BS01–12 R09/R10/R11; OPT01–12 R08/R05/R06/R11. Security and performance supplemental obligations remain necessary. Crosswalk still labels RTM-006/007 pending despite their presence; interpret as acceptance pending, not missing files. All 19 WBS packages have role owners and exit deliverables; actual worker acknowledgement remains outstanding. G0-03 remains open: per-row normative clause, exact current source/test/proof bindings and transitive compiler module inventory are incomplete. Static review is not independent approval or proof execution.

## Configuration manifest increment
Static Git blob identities at candidate revision `549d5ad4d81f7a88e1d76a959aed6c65230e05c6` (not executable artifact hashes):

| Input | Git blob |
|---|---|
| compiler/ast.cap | `7202b1676409773cf55a4de57c45d38db0532142` |
| compiler/lexer.cap | `6bc9bf8c12b4b9bcf8928b45d302f8e8453a02eb` |
| compiler/parser.cap | `b656da773f2aa118b0fd2eeeb537a8a4614cad1e` |
| compiler/checker.cap | `9b485cf9c467fc0c5cd15aa07b5190c6b0b5e2de` |
| compiler/ranges.cap | `91431cbf826b5953481178f67ecfe942f08094f4` |
| compiler/codegen.cap | `a43b6163a11f3d71f0e74b1758e4cf49e24d9c89` |
| compiler/main.cap | `ac1b4d3b4985ddc32b19914dd353b127d5fddc68` |
| bootstrap/capstan0.py | `f374716051640c4e2776089156fb4eff18a87c4b` |
| runtime/capstan_rt.h | `27cc7cfc6827f5745150f4bf2d5c38dd65978a06` |
| scripts/sbom-schema-requirements.txt | `f4b1f260bc4ddf120343ba78a75039fe0804b990` |
| Makefile | `effba39be3f91c98c6c6c2b99c22b5e78dd10ab5` |
| tests/run.sh | `f0b3937dad515b119deb8ec79d428b84e5713bf5` |
| .github/workflows/ci.yml | `39e08c63a2bb863ff5aeb0367bb7975253c47e38` |
| verification/lean/lean-toolchain | `7aca1d8a939cc24c413eddd793671cdce7070b74` |

Lean pin: leanprover/lean4:v4.19.0. Prescribed general CI: `make`, then `bash tests/run.sh` on Ubuntu GCC, Ubuntu Clang, macOS Clang; scheduled full run uses `--full`. Checkout action pinned at `3d3c42e5aac5ba805825da76410c181273ba90b1`. Current bootstrap is Python stage 0, Python stage 1, C stage 2/3 with generated C comparison; this is not G6 C-free evidence. Runner image labels are floating; actual compiler/Python/OS versions, transitive dependency closure, clean checkout, executed command output, test counts, Lean axiom results and independent reproduction remain unrecorded. Formal workflow path lookup was unsuccessful; do not infer its command or result. No fresh execution. G0-06/07 remain open.

## Executed historical PR verification evidence
Retrieved completed workflow and job logs for #548 head `0b750abebacfd7c455ea97f591e49eb71adacef6`. CI run 45936652072: Ubuntu GCC job 140301289731 and Ubuntu Clang job 140301289417 each 553 passed/0 failed; macOS Clang job 140301289426 534 passed/0 failed. All three logs report generated-C bootstrap fixpoint and reproducibility report with stage3.c checksum recorded; supply-chain job 140301289195 succeeded. Formal run 45936652115: existing language package job 140301289374 and allocator model job 140301289789 succeeded. Allocator log records Lean 4.36.0, commit 611c117bfaf7b7ae1cfcf246ce6fba31e8f509e9; axiom-audit v0.1.2 inspected 291 declarations under CCAMHeap, all within propext, Classical.choice, Quot.sound. Separate kernel checks report 60118/60261 declarations with no errors while skipping exported unpermitted sorryAx; do not interpret those counts as proven Capstan implementation obligations. CodeQL run 45936652122: Python/C++/Actions all successful. Run URLs use https://github.com/DavidFernee/Capstan/actions/runs/<run-id>. Counts across platforms repeat coverage, not unique tests. Historical PR evidence is not exact-main independent reproduction; exact checkout/tree equivalence, toolchain versions and independent review outstanding. G0-07 remains partial.
