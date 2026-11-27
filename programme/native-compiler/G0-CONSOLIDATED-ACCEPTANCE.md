# G0 consolidated acceptance register — 2026-11-27

Decision: HOLD pending recorded acceptance. This register supersedes stale status summaries, not normative criteria. CAP-004 defines G0 as pinned inventory and reviewed traceability; CURRENT-DEVELOPMENT-ASSESSMENT additionally calls for exact main/toolchain/test results. Shared STAGE-GATES.md requires readiness, not completed implementation. Do not require G1–G7 implementation evidence as a G0 condition.

| Criterion | Existing evidence | Residual decision |
|---|---|---|
| G0-01 | #542 merged; G0-PREPARATION.md | Approve architecture authority |
| G0-02 | G0-PREPARATION.md; #544 reconciled; #552 integrated | Review residual assembly/direct profile documentation |
| G0-03 | G0-REQUIREMENTS-REVIEW.md, G0-INDIVIDUAL-CLAUSE-AUDIT.md, G0-ATOMIC-PARENT-AUDIT.md, G0-SUPPLEMENTAL-DISPOSITION.md, G0-LITERAL-DEPENDENCY-INVENTORY.md | Approve pinned inventory of 113 rows and 12 supplemental candidates; distinguish missing inventory from future proof/implementation evidence |
| G0-04 | ARCHITECTURE-CROSSWALK.md; all 19 RFC gaps mapped; 48 local IDs mapped | Review bidirectional traceability and approve |
| G0-05 | WORK-BREAKDOWN.md, G0-PREPARATION.md, coordination #25 | Record explicit role owner acknowledgement and interface responsibilities |
| G0-06 | G0-CONFIGURATION-BASELINE.md, G0-SOURCE-IDENTITY-AUDIT.md, #583/#584 | Integrate provenance, pin clean checkout/tree, record actual host/tools and artifact digests |
| G0-07 | G0-OBSERVED-EXECUTION.md, G0-POST-INTEGRATION-EVIDENCE.md | Exact integrated baseline execution and independent reproduction; preserve historical results as historical |
| G0-08 | G0-REVIEW.md and this register | Independent reviewer disposition and programme authority acceptance |

## Live integration checkpoint
#583 head b2d0a29512214823ee5ea03697acddf8cbf66f66: formal 45974821025 and CodeQL 45974821002 success, CI 45974821039 in progress at inspection. Its displayed base 43d20c5971abf03f8fb95276e86270dc23570cc2 is 16 commits behind main by compare, including CCAM test changes; recheck exact tested merge identity before merging. #584 head aabf983bfea1adbb28b600f88fd93d887bcb09f3 has three successful workflows against an older baseline; do not waive freshness. Run links: https://github.com/DavidFernee/Capstan/actions/runs/45974821039.

## Closure protocol
1. Integrate one provenance PR against a verified fresh baseline; resolve redundant PR only after equivalence review.
2. Pin a baseline revision (subsequent development need not invalidate a deliberately pinned approved baseline). Record actual checkout/tree, commands, exit status, host, toolchain, artifacts and independent reproduction differences.
3. Review the existing inventory and traceability, disposition residual gaps as G0 deficiencies or named downstream obligations, acknowledge owners.
4. Independent reviewer records identity, exact evidence revision, findings and accept/hold per criterion. Programme authority records explicit acceptance only after required evidence is satisfied.
5. Update gate decision in reviewed PR. G1–G7 implementation obligations remain open as appropriate.

No new build executed, independent reviewer signature obtained, or gate approval asserted by this preparer. Do not fabricate missing record fields.


## Verified provenance and tree equivalence — 2026-11-27
Evidence verifier: ChatGPT (repository metadata and CI log inspection; not an independent build operator or programme approver).

#583 merged at `02328b31a555f282878574b2f65ee68dc2751a2a`; redundant #584 closed unmerged. The tested synthetic merge `d8dbb7c41236b77e35ea3868c4c50a8d78404775` and integrated #583 commit both have exact Git root tree `a6d553ef83f09c87801c2de65e21c733b91ae9a5` and ordered parents `c6cfc03ce0aa7217813cae728058f5abfcd65283`, `b2d0a29512214823ee5ea03697acddf8cbf66f66`. Verified directly using Git commit objects (https://api.github.com/repos/DavidFernee/Capstan/git/commits/<sha>) and CI job 140423820894, whose git rev-parse output records the same tree and successful clean checkout check. Both changed file blobs also match: .github/workflows/ci.yml `4fdc4b933e59e2a91fc38c7df841ff9163b20045`; docs/assurance/execution-boundaries.json `3f5fb0725720db410b7f1fa9bced897e105ef1ed`.

CI https://github.com/DavidFernee/Capstan/actions/runs/45974821039: Ubuntu GCC, Ubuntu Clang, macOS Clang and supply-chain jobs passed. Formal 45974821025 and CodeQL 45974821002 passed. Retained provenance artifact IDs: 15186880963 (GCC), 15186712041 (Linux Clang), 15186098618 (macOS Clang). GCC log records GCC 15.2.0, Python 3.14.4, GNU Make 4.4.1, Git 2.56.1, 562 passed/0 failed, successful bootstrap fixpoint and identical stage2.c/stage3.c SHA-256 `ad9b87ea02f3060c71d3719aa4d826d366cda9eb57138448bf9dfa3578691c4b`.

G0-06: exact integrated source-tree identity and provenance infrastructure established for #583 candidate. G0-07: bind successful CI to identical integrated tree; commit-sensitive outputs and independent clean reproduction remain distinct obligations. This checkpoint supersedes the earlier pending #583/#584 integration and tree-equivalence status only. No claim that later main revisions have the same tree, no fresh build executed, no full independent reviewer disposition or gate acceptance asserted. Overall HOLD remains pending remaining required evidence and approval.
