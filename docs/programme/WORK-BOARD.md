# Programme Kanban — pull-ready work packages

**Status:** initial board seeded from current open GitHub issues and PR inventory  
**Snapshot:** 2026-11-25  
**Repository:** [DavidFernee/Capstan](https://github.com/DavidFernee/Capstan)

This is the worker-facing queue. It complements GitHub Issues; it does not replace issue discussions or product specifications. Existing issues are linked rather than duplicated. A worker should claim an issue before starting, state the intended branch/approach, and keep the PR within the card's acceptance criteria.

## Board policy

**Columns**
1. **Ready** — all Definition of Ready checks pass; no unresolved prerequisite.
2. **In progress** — one worker/lead has claimed the card.
3. **Review** — implementation complete; evidence and review requested.
4. **Blocked** — dependency or decision prevents progress; blocker and unblock condition recorded.
5. **Done** — merged, exact-commit evidence retained, acceptance recorded.

**Pull policy**
- WIP limit: one substantial card per worker; maximum 2 concurrent cards per product until integration capacity is demonstrated.
- Prefer small cards of roughly 0.5–3 worker-days. Larger work must be split into independently testable vertical slices.
- No card is Ready if its API, owner, test oracle or threat boundary is ambiguous.
- Cross-product cards name one lead product and list consumers.
- A PR must link its issue, state exact acceptance criteria, include tests/evidence and identify any change to claims or TCB.
- Do not close an issue merely because a PR exists. Close only after merge and acceptance evidence.
- Do not merge competing implementations of the same contract without resolving overlap.

## Definition of Ready

A card is Ready only when it has:
- one concrete deliverable and one accountable lead;
- explicit in-scope and out-of-scope statements;
- dependencies and contract versions;
- threat assumptions and resource bounds where relevant;
- acceptance criteria that can be checked by CI, test, proof or reviewer;
- expected evidence artefacts and a reproducible command;
- a size small enough for a focused PR.

## Definition of Done

- implementation and documentation are merged;
- focused positive, negative and boundary tests pass;
- fuzz/property/adversarial tests are added where the risk warrants them;
- evidence is attached to the issue/PR and tied to exact commit/platform/toolchain;
- limitations and residual risks are recorded;
- relevant research register, formal matrix, design map or release scorecard is updated;
- independent review completed for security-critical or assurance claims.

## Ready — existing work items

These are candidates for immediate pull after the worker checks current issue state, comments and dependencies. Existing PRs are shown separately so workers do not duplicate active implementation.

### Capstan — language, CCAM, runtime and assurance

| Priority | Pull card | Existing issue | Acceptance focus | Dependencies / caution |
|---|---|---|---|---|
| P0 | Run canonical SF-P vectors against the Capstan evaluator | [#269](https://github.com/DavidFernee/Capstan/issues/269) | Same versioned corpus, deterministic outcomes, explicit expected traps and budgets | Coordinate with [#243](https://github.com/DavidFernee/Capstan/issues/243) and open PRs #245/#256/#258/#266; do not duplicate vector definitions |
| P0 | Close implementation-linked CCAM proof obligations | [#235](https://github.com/DavidFernee/Capstan/issues/235) | Exact model/spec trace, named refinement relation, proof/test evidence and explicit unproved boundary | Coordinate with formal PRs #216/#255/#262; theorem claims limited to covered fragment |
| P0 | Rebuild machine-readable claims/evidence manifest | [#261](https://github.com/DavidFernee/Capstan/issues/261) | Machine-readable claim IDs, commit/evidence links, UNKNOWN handling, CI validation | Must align with [#252](https://github.com/DavidFernee/Capstan/issues/252) and V1 scorecard |
| P0 | Establish safe-profile and release evidence gates | [#252](https://github.com/DavidFernee/Capstan/issues/252) | Gate definitions, platform/profile scope, evidence states, release-blocking UNKNOWN | Do not imply C-free end-to-end or full formal verification |
| P1 | Model explicit-trap reason/detail without conflating machine traps | [#265](https://github.com/DavidFernee/Capstan/issues/265) | Normative trap taxonomy and exact evaluator/model correspondence | Must not silently change existing trap precedence or ABI |
| P1 | Typed provenance for password/secret flows | [#232](https://github.com/DavidFernee/Capstan/issues/232) | Provenance is typed and survives aliases/helpers; tests defeat name-based heuristics | Security-sensitive; define source/sink model before implementation |
| P1 | Complete context-specific output sinks and HTML-to-CSV closure | [#231](https://github.com/DavidFernee/Capstan/issues/231) | Typed sink API; context-specific escaping; regression tests for cross-context injection | Coordinate #234 and #250; no duplicated sanitisation policy |
| P1 | Track HTML output context through statements/helpers | [#234](https://github.com/DavidFernee/Capstan/issues/234) | Context state propagation, joins/unknown state, adversarial tests | Depends on canonical sink semantics; coordinate #231/#250 |
| P1 | Typed JSON fragments and output sink | [#250](https://github.com/DavidFernee/Capstan/issues/250) | No raw-string bypass for typed JSON output; parser/serializer round-trip tests | Coordinate with #231/#234 |
| P1 | Sensitive-data authorisation completeness | [#233](https://github.com/DavidFernee/Capstan/issues/233) | Every sensitive operation has explicit principal, grant and denial tests | Coordinate with typed provenance #232 |
| P1 | Deterministic structured concurrency core | [#229](https://github.com/DavidFernee/Capstan/issues/229) | Normative scheduling/cancellation/channel semantics and race-free invariants | Coordinate bounded reference machine PR #254; keep reference model distinct from production runtime |
| P1 | Allocator and GC correctness programme | [#137](https://github.com/DavidFernee/Capstan/issues/137) | Invariants, model, stress/failure tests and implementation-linked evidence | Runtime PR #143 is prior hardening, not proof of collector correctness |
| P1 | Execute per-attempt CWE evidence records | [#236](https://github.com/DavidFernee/Capstan/issues/236) | Reproducible record schema, denominator, disposition and failed/unknown cases | Coordinate CVE benchmark #237 and claims manifest #261 |
| P1 | Establish real-world CVE benchmark cases | [#237](https://github.com/DavidFernee/Capstan/issues/237) | Frozen sample, inclusion/exclusion rules, independent labels and reproducible analysis | Do not publish headline efficacy before independent relabelling |
| P2 | Define minimal compositional guarantee calculus | [#227](https://github.com/DavidFernee/Capstan/issues/227) | Formal rules, composition examples, counterexamples and comparison to related work | Research work; no security guarantee until rules are connected to implementation |
| P2 | Comparative survey of compositional resource analysis | [#221](https://github.com/DavidFernee/Capstan/issues/221) | Reproducible search protocol, taxonomy, inclusion criteria and synthesis | Research work; distinguish survey from novelty claim |
| P2 | Comparative survey of capability/effect/information-flow systems | [#222](https://github.com/DavidFernee/Capstan/issues/222) | Explicit comparison dimensions, source set and limitations | Research work |
| P2 | Evidence-carrying execution survey and contract reconciliation | [#220](https://github.com/DavidFernee/Capstan/issues/220), [#219](https://github.com/DavidFernee/Capstan/issues/219) | Related-work matrix and mapping to current CCAM evidence boundary | Coordinate the two issues; avoid duplicate literature review |
| P2 | Reproducible comparative evaluation protocol | [#223](https://github.com/DavidFernee/Capstan/issues/223) | Frozen workloads, baselines, metrics, hardware/toolchain and analysis plan | Required before performance/security comparison claims |
| P2 | Guarantee and trusted-base baseline inventory | [#225](https://github.com/DavidFernee/Capstan/issues/225) | Enumerated guarantees, assumptions, TCB components and explicit non-guarantees | Feeds all product threat models and release scorecards |

### Shroud — GUI framework and platform hosts

| Priority | Pull card | Existing issue | Acceptance focus | Dependencies / caution |
|---|---|---|---|---|
| P0 | Preserve UI state through validated resize | [#215](https://github.com/DavidFernee/Capstan/issues/215) | State-preserving resize contract, invalid input rejection, regression tests | Open PR #274; worker should review/integrate, not duplicate |
| P0 | Enforce font table-local bounds | [#121](https://github.com/DavidFernee/Capstan/issues/121) | cmap/loca/hmtx offset/length checks, malformed corpus and fuzzing | Open PRs #272/#271 mention font parsing; reconcile overlap first |
| P0 | Bound cumulative rendering/text work | [#101](https://github.com/DavidFernee/Capstan/issues/101), [#114](https://github.com/DavidFernee/Capstan/issues/114) | Aggregate budgets before allocation; overflow-safe accounting; adversarial tests | Distinguish frame budget from process-wide guarantee |
| P1 | Specify minimal Wayland host capability/syscall surface | [#224](https://github.com/DavidFernee/Capstan/issues/224) | Threat model, syscall/capability allowlist, protocol parser boundaries | Coordinate current Wayland decoder integration |
| P1 | Add pointer-cancel and native-focus-loss transitions | [#208](https://github.com/DavidFernee/Capstan/issues/208) | Explicit state machine and transition tests for cancellation/focus loss | Ensure host and widget semantics agree |
| P1 | Preserve Unicode text integrity against deceptive rendering | [#95](https://github.com/DavidFernee/Capstan/issues/95) | Defined normalization/display policy and adversarial Unicode tests | Do not silently normalize source text |
| P1 | Bound PNG export amplification and cumulative frame memory | [#82](https://github.com/DavidFernee/Capstan/issues/82) | Checked dimensions/stride/aggregate budget and failure atomicity | Reconcile merged PR #92 and open PR #272 |
| P2 | Define Shroud production-readiness/conformance programme | [#84](https://github.com/DavidFernee/Capstan/issues/84) | API compatibility, platform matrix, accessibility, resource and release gates | Use as Shroud-specific release plan |
| P2 | Define public programming experience | [#88](https://github.com/DavidFernee/Capstan/issues/88) | Usability goals and tested developer tasks | Keep separate from language semantics |

### Anchor — IDE and developer workflows

No Anchor-labelled open issue appeared in the current open-issue snapshot. Do not infer that no Anchor work exists: inspect branches, docs and PRs before creating tickets.

**First pull card to create after the audit:** Anchor product baseline and vertical-slice contract. It should define the IDE boundary, canonical compiler-service protocol, workspace threat model and minimum workflow. Do not start a large editor implementation before this contract is accepted.

### Keel — 3D engine

Open PRs #276 and #277 both describe the Keel K0 architecture/research programme. Resolve whether these are duplicate or complementary changes before another worker starts K0 documentation.

**First pull cards after PR reconciliation:**
1. K0 architecture/contract review: ownership, Shroud dependency, scene/resource model, threat boundary and research questions.
2. Minimal deterministic scene-core prototype: transforms, stable IDs, bounded entity count and deterministic update order; no GPU dependency.
3. Hostile asset-ingestion contract and bounded parser harness.
4. GPU resource ownership/lifetime design, explicitly separating engine guarantees from vendor driver trust.
5. Reference-scene conformance harness and deterministic replay scope.

These are candidate decompositions, not claims that matching issues already exist.

## In progress / integration watch

The following open PRs must be reviewed and mapped to the cards before new implementation begins:

- **Keel:** #276, #277 — K0 architecture/research programme overlap.
- **Shroud:** #274 — resize; #272 and #271 — PNG/font hardening overlap.
- **CCAM/formal/native:** #216, #245, #246, #254, #255, #256, #258, #262, #266, #228.
- **Research/assurance:** #238, #260.

The board snapshot also identified 36 open issues and 17 open PRs on 2026-11-25. This is a snapshot, not a live status guarantee. Re-run the inventory before assigning workers.

## Blocked / not yet Ready

- Anchor implementation cards until its current docs, branches, PRs and intended vertical slice are audited.
- Keel GPU implementation until the engine's resource/lifetime contract and trusted boundary are specified.
- Full C-free release claims until compiler, runtime, standard library, bootstrap and platform dependencies are separately qualified.
- End-to-end verified execution claims until the implementation/refinement chain is established.

## Worker card template

Use this structure for every new issue:

```markdown
## Outcome
One independently reviewable deliverable.

## Product / milestone
CAP | SHR | ANC | KEL — Mx

## Scope
### In
- ...
### Out
- ...

## Contract and dependencies
- Normative spec/API:
- Upstream dependency:
- Downstream consumers:

## Threat and resource assumptions
- Untrusted inputs:
- Authority boundary:
- CPU/memory/stack/I/O/GPU limits:

## Acceptance criteria
- [ ] ...
- [ ] ...
- [ ] ...

## Evidence to attach
- Exact commit and platform/toolchain:
- Commands and raw outputs:
- Tests/fuzz corpus/proof/benchmark:
- Independent reviewer:

## Risks and open questions
- ...

## Handoff
Files changed, API/schema changes, migration notes, residual limitations.
```

## Next board-maintenance actions

1. Reconcile the open PRs listed above, especially duplicate-looking Shroud and Keel work.
2. Inspect Anchor docs/branches/PRs and create only non-duplicative worker issues.
3. Convert candidate Keel slices into issues after K0 contract review.
4. Add labels consistently: `product:capstan`, `product:shroud`, `product:anchor`, `product:keel`, `type:implementation`, `type:research`, `type:assurance`, `stage:ready`, `stage:blocked`, `evidence-required`, `release-blocker`.
5. Keep issue state as the live Kanban state; this document is the programme index and should be refreshed as work moves.
