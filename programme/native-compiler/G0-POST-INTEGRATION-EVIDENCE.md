# G0 post-integration acceptance evidence — 2026-11-27

Decision: HOLD. Evidence preparer: ChatGPT. User authorises acceptance only once criteria are met. This supplement updates the historical dispositions in G0-REVIEW.md, not the gate requirements.

## Integrated candidate
#563 merged 284f7d84b363c447cad157a476873be2170964d3; #554 merged 94060f867204d936558a3d74aa9f5a3a1273e8e7; #552 merged dcfa9a0a821f9c190373d828c2d12e3599b02b1a. The last commit is the candidate for this supplement, not an assertion that main cannot have advanced. #552 base is #554 merge; #554 base is #563 merge.

## Workflow evidence
GitHub commit workflow lookup returned completed success for all following runs. Run URL prefix: https://github.com/DavidFernee/Capstan/actions/runs/.

| PR | Exact queried head | CI | Formal | CodeQL | Native ELF harness | Anchor smoke |
|---|---|---|---|---|---|---|
| #554 | 3549594cad26d1777dd893a506f48ba080e248bd | 45945118917 | 45945118916 | 45945119079 | 45945119223 | 45945118929 |
| #552 | 3dc0788bf5318c5ed67b5145e4bb4ec7600b13d8 | 45947025321 | 45947025330 | 45947025357 | 45947025391 | not returned |

These are PR-associated workflow results, not fresh build execution or exact-main reproduction. Job checkout identities, tree equivalence, toolchain digests and test counts for these runs still require extraction. Historical #548 counts must not be reused as current counts.

## Gate evidence and closure conditions
| Criterion | Evidence | Outstanding acceptance condition |
|---|---|---|
| G0-01 | #542 authoritative CCAM RFC merged | independent architecture review |
| G0-02 | #544 comparison recorded; #545 closed unmerged; #552 successor integrated | review residual assembly documentation discrepancies |
| G0-03 | 113 rows across seven matrices and 12 supplemental candidates | atomic normative clause/source/test/proof bindings, transitive inventory; disposition supplemental obligations |
| G0-04 | 19 RFC gaps mapped | parent links for GC/bootstrap/optimisation and bidirectional traceability review |
| G0-05 | 19 packages and role proposals | explicit ownership acknowledgement, interface responsibilities |
| G0-06 | candidate merge SHA above | tree hash, dependency closure, host/toolchain versions and digests, clean checkout recipe and artifact identities |
| G0-07 | nine successful PR workflow runs above | tested checkout/tree binding, exact candidate execution and independent reproduction |
| G0-08 | this evidence supplement and G0-REVIEW.md | independent reviewer, explicit signed-off disposition of all eight criteria |

## Scope limitations
#552 adds bounded scalar direct ELF generation, not full CCAM outcome equivalence; parameterless integer entry, no calls or byte output, experimental result transport, C-dependent driver and absent native refinement theorem remain. #554 addresses three tested CWE-916 fast-hash gaps, not comprehensive alias or information-flow soundness; broader CWE-20 remains #410. These are downstream obligations, not reasons to redefine G0.

## Review handoff
Independent reviewer must identify reviewed revision and evidence, record findings against each criterion, and explicitly accept or hold. Integration owner must verify branch freshness before acceptance. Do not approve this evidence solely because its documentation PR passes CI. No fresh build or independent approval was performed by this preparer.
