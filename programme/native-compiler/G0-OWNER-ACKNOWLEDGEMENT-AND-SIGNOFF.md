# G0 ownership and sign-off package — prepared 2026-11-27

Programme authority: David Fernée. Authority decision: “The owners will be ChatGPT and Claude under my supervision.” Target review: 2026-11-29. This is a proposed allocation for explicit Claude acknowledgement; it does not assert Claude approval or close G0.

## CAP-003 allocation

Both engineering owners coordinate under David. Primary responsibility and peer responsibilities below supplement, not replace, existing CAP-003 role names, prerequisites or exit deliverables. Actual task claims remain coordinated through issue #25.

| Package | Primary | Peer/interface reviewer |
|---|---|---|
| A01 | ChatGPT | Claude |
| B01 | Claude | ChatGPT |
| B02 | ChatGPT | Claude |
| B03 | ChatGPT | Claude |
| B04 | Claude | ChatGPT |
| B05 | ChatGPT | Claude |
| C01 | ChatGPT | Claude |
| C02 | Claude | ChatGPT |
| C03 | ChatGPT | Claude |
| C04 | ChatGPT | Claude |
| D01 | ChatGPT | Claude |
| D02 | Claude | ChatGPT |
| D03 | ChatGPT | Claude |
| D04 | ChatGPT | Claude |
| E01 | ChatGPT | Claude |
| E02 | Claude | ChatGPT |
| F01 | Claude | ChatGPT |
| F02 | ChatGPT | Claude |
| F03 | ChatGPT | Claude |

## CAP-006 interface allocation

| Interface | Producer representative | Consumer/review representative |
|---|---|---|
| I01 checked source to CCAM | Claude (frontend) | ChatGPT (CCAM) |
| I02 decoder to validator/evaluator | ChatGPT (CCAM) | Claude (peer review) |
| I03 CCAM to scalar native | ChatGPT (CCAM/native) | Claude (peer review) |
| I04 runtime objects/roots | Claude (runtime) | ChatGPT (CCAM/native) |
| I05 effects and host calls | ChatGPT (security) | Claude (runtime) |
| I06 machine code/object/load | ChatGPT (native) | Claude (peer review) |
| I07 optimisation/certificates | Claude (optimisation) | ChatGPT (formal/native) |

Both owners review changes as producer/consumer or delegated peer representatives. Where one owner represents both operational roles, retain distinct role-specific review records; do not describe peer review by a contributor as independent assurance. David resolves disputes and approves freezes and gates.

**ChatGPT acknowledgement:** This GPT-6 session accepts the above proposed ChatGPT package and interface obligations under David's supervision, including coordination, evidence, bounded scope and escalation. No authority sign-off implied.

**Claude acknowledgement (pending):** I accept the CAP-003 primary and peer responsibilities and CAP-006 interface responsibilities allocated to Claude above, subject to David's supervision. I will coordinate work claims and preserve independent-assurance limitations. [Claude to record actual acknowledgement, identity and date.]

## Acceptance checklist

- G0-01/03/04/06: ACCEPT in PR #601, scoped to pinned baseline evidence.
- G0-02: #598 now merged; #599 still draft/open at preparation. Integrate reviewed correction and verify against source before clearing.
- G0-05: ChatGPT acknowledgement recorded; Claude acknowledgement of this allocation pending.
- G0-07: #595 provides previously operated reproduction of #583 baseline. PR #601 reviewer could not execute a fresh build. Review raw evidence or execute independently and explicitly record disposition under existing G0 criteria. No fresh execution is asserted here.
- G0-08: after preceding holds resolved, David records acceptance against pinned build and final reviewed evidence revision.

## Prepared sign-off record (not executed)

Claude: [identity/date; acknowledge allocation; record evidence review disposition and limitations].

David: [date; ACCEPT or HOLD; accepted build commit 02328b31a555f282878574b2f65ee68dc2751a2a, tree a6d553ef83f09c87801c2de65e21c733b91ae9a5; final evidence commit; residual limitations; authority signature].

Full C-free self-hosting, native refinement and remaining release proof obligations stay downstream. No criteria are waived, no approval is presumed, and G0 remains HOLD until actual clearance and authority decision.
