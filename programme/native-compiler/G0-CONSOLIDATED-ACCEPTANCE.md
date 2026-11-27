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
