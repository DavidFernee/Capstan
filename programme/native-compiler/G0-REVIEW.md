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
