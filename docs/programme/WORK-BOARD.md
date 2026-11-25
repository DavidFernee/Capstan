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

Anchor has an established A0 baseline on main: `docs/ANCHOR.md`, `docs/ANCHOR-COMPONENT-CATALOGUE.md`, `examples/anchor/main.cap`, `tests/anchor/check.py` and its smoke workflow. The original A0 PR #53 is closed; the `feature/anchor` branch also exists. A0 is a headless/static Shroud S0 shell, not a functioning desktop IDE. The architecture document is explicit that there is no native window embedder or child-process API, and prohibits shell/private-C-shim workarounds.

**New pull-ready cards:**
- [#279 — A1 bounded compiler-process adapter contract](https://github.com/DavidFernee/Capstan/issues/279): Ready for contract and mock-harness work; production process launch remains blocked on an agreed upstream process/host API.
- [#280 — A2 confined workspace discovery and document loading](https://github.com/DavidFernee/Capstan/issues/280): Ready for bounded workspace-service implementation and adversarial tests.

The next Anchor sequence is A1 contract/mock harness and A2 workspace confinement, followed by implementation only when the required host/process contracts exist. A3 build/test/format workflows must use explicit user actions and structured argv. A4 WYSIWYG design remains dependent on compiler-supported source maps/transformations and Shroud component metadata; do not start by inventing a parallel visual source format.

### Keel — 3D engine

Keel K0 is represented by the open [PR #277](https://github.com/DavidFernee/Capstan/pull/277), which contains the architecture, research programme, security assurance and K0 decisions. PR #276 was closed as a duplicate of #277; PR #275 is also closed. Do not reopen duplicate documentation work or begin renderer implementation before K0 decisions are reviewed and accepted.

**New pull-ready cards:**
- [#281 — deterministic bounded scene-core reference model](https://github.com/DavidFernee/Capstan/issues/281): GPU-independent reference model; implementation is gated on accepted K0 decisions.
- [#282 — hostile asset-ingestion limits and parser conformance corpus](https://github.com/DavidFernee/Capstan/issues/282): choose one initial format and establish the bounded parser/test boundary; implementation is gated on K0 format/ownership decisions.

Next candidate slices after these: GPU resource lifetime/teardown contract; reference-scene renderer conformance harness; deterministic simulation/replay. These must be separate worker cards with explicit CPU/GPU/driver trust boundaries.

### Media family — Capstan Media Core, Shanty and Deadeye

The media proposal is already in progress in [PR #291](https://github.com/DavidFernee/Capstan/pull/291). It defines **Halyard** as the media architecture: **Capstan Media Core** supplies shared primitives, with **Shanty** (audio) and **Deadeye** (video/image) as independent engines. Shanty and Deadeye do not depend on one another. Shroud core remains media-independent; an optional Halyard–Shroud adapter integrates presentation APIs. Keel may consume and orchestrate media graphs without duplicating codec semantics.

The research agenda is tracked in [docs/media/RESEARCH-AGENDA.md](https://github.com/DavidFernee/Capstan/blob/media/shanty-deadeye-foundation/docs/media/RESEARCH-AGENDA.md). It expands R8 into eight falsifiable hypotheses covering compositional resource semantics, verified parsing/serialization, ownership-safe zero-copy, deterministic audio scheduling, multi-clock synchronisation, proof-preserving graph optimisation, semantic fuzzing and colour/scientific-data integrity. The agenda is a hypothesis register, not a novelty claim; each workstream requires literature review, baselines, reproducible raw data and independent reproduction.

The media implementation-origin rule is strict: Media Core, Shanty and Deadeye implementation code is written from scratch in Capstan. No external multimedia framework, third-party codec implementation, copied/vendored parser or generated-C/C++ media runtime may be linked or shipped. Independent implementations may be used only as isolated test oracles. The current C-backed Capstan compiler/runtime remains an explicit TCB dependency until the C-free path is implemented and independently qualified.

| Priority | Pull card | Existing issue / PR | Acceptance focus | Dependencies / caution |
|---|---|---|---|---|
| P0 | Review media architecture and threat model | [#283](https://github.com/DavidFernee/Capstan/issues/283), [PR #291](https://github.com/DavidFernee/Capstan/pull/291) | Acyclic graph, product ownership, trust boundaries, licence/patent/provenance, honest implementation status | Do not duplicate PR #291; review it against programme boundaries |
| P0 | Specify bounded byte sources, sinks and ownership | [#284](https://github.com/DavidFernee/Capstan/issues/284) | Immutable spans, output reservations, EOF/short I/O/cancellation/seek and failure atomicity | Core prerequisite for all parsers |
| P0 | Define aggregate resource ledger and atomic reservations | [#285](https://github.com/DavidFernee/Capstan/issues/285) | Overflow-safe admission and compositional budgets across nested stages/workers | Must precede parser implementation using declared sizes |
| P0 | Specify rational timebases and timestamp arithmetic | [#286](https://github.com/DavidFernee/Capstan/issues/286) | Integer/rational clocks, checked rescaling, VFR, wrap, discontinuity and seek vectors | Required before synchronised playback |
| P0 | Define versioned media format/codec registry | [#287](https://github.com/DavidFernee/Capstan/issues/287) | Container/codec/profile/level/direction separation, deterministic registration and provenance | Registry is not a codec implementation |
| P0 | Audit Capstan runtime and establish WAV/PCM corpus | [#288](https://github.com/DavidFernee/Capstan/issues/288) | Exact runtime capability gaps and independently checked PCM fixtures | Audit only; no playback or complete WAV claim |
| P0 | Audit Shroud PNG path and select first image decoder | [#289](https://github.com/DavidFernee/Capstan/issues/289) | Distinguish PNG output from decode; select one format with legal/security rationale | No assumption that Shroud has a general PNG decoder |
| P1 | Literature review and baseline protocol for bounded media | [#290](https://github.com/DavidFernee/Capstan/issues/290) | Reproducible related-work protocol, hypotheses, baselines, metrics and negative-result policy | Feeds research register R8; novelty remains a hypothesis |
| P0 | Model compositional resource accounting and reservation leases | [#294](https://github.com/DavidFernee/Capstan/issues/294) | Resource conservation model, alias/lifetime semantics, generated interleavings and benchmark | Depends on #285/#293; no concurrency claim without implementation evidence |
| P1 | Prototype verified Capstan media format descriptions | [#295](https://github.com/DavidFernee/Capstan/issues/295) | Declarative RIFF/WAVE subset, proof obligations, refinement plan and baselines | Compare Vest and PulseParse; depends on #284/#285/#293 |
| P1 | Format-aware differential and metamorphic fuzzing | [#296](https://github.com/DavidFernee/Capstan/issues/296) | Grammar-aware seeds/mutations, semantic properties, triage and corpus retention | Depends on #288/#289 and format decisions |
| P1 | Multi-clock media time and bounded A/V drift control | [#297](https://github.com/DavidFernee/Capstan/issues/297) | Clock domains, discontinuity model, drift traces and sync-error metrics | Depends on #286 and audio/image vertical slices |
| P1 | Preflighted deterministic real-time audio execution | [#298](https://github.com/DavidFernee/Capstan/issues/298) | Callback-safe plan, bounded work and deadline evidence | Depends on #293/#285/#286; SH1 preparation |
| P2 (deferred) | Contract-aware distributed media graph execution | [#299](https://github.com/DavidFernee/Capstan/issues/299) | Portable graph partitioning with clock, latency, resource, privacy and recovery contracts | Post-MC3 only; do not distract from local Core/audio/image foundations |
| P2 | Proof-preserving graph rewrites and cost accounting | [#300](https://github.com/DavidFernee/Capstan/issues/300) | Rewrite contracts, equivalence obligations and resource-cost deltas | Depends on stable graph IR and #294/#286 |
| P1 | Typed colour, HDR and scientific image semantics | [#301](https://github.com/DavidFernee/Capstan/issues/301) | Explicit signal descriptors, transform/error model and calibrated corpus | Depends on #287/#289; no clinical claims |
| P0 | Complete audio/video vulnerability accounting programme | [#292](https://github.com/DavidFernee/Capstan/issues/292) | SBOM, advisory reconciliation, root-cause ledger, regression corpus, fuzzing and release gates | Release-blocking; finite known-issue accounting is not proof of no unknown defects |

#### Media family gates

- **MC0:** architecture, threat model, ownership and format taxonomy.
- **MC1:** bounded streams, rational timebases, aggregate budgets and registry.
- **SH0:** deterministic WAV/PCM offline vertical slice.
- **DE0:** one selected bounded image/frame vertical slice.
- **MC2:** restricted codec-worker boundary and output validation.
- **SH1/DE1:** device playback/capture and video presentation foundations.
- **MC3:** synchronised A/V graph with bounded queues and explicit clock policy.
- **MC4:** format compatibility expansion with per-profile/per-direction evidence.
- **MC5:** security, fuzzing, independent assurance and reproducible performance.
- **MC6:** scientific/digital-twin, HDR, spatial audio and professional workflows.

These are media-specific gates layered on shared G0–G5. They are not claims that any listed capability is already implemented.

#### Subsequent worker slices (create only after prerequisite review)

- Shanty: RIFF/WAVE parser specification → bounded metadata parser → PCM conversion → deterministic offline mixer → real-time callback contract → device backend.
- Deadeye: image descriptor/pixel oracle → selected image decoder → image transforms → container demux → video decode/frame scheduling → presentation/encode.
- Media Core: codec-worker protocol → graph planner/backpressure → A/V clock integration → compatibility and performance harness.
- Cross-product: optional Halyard–Shroud presentation adapter; Keel media-graph orchestration; Anchor media inspection workflows.

## In progress / integration watch

The following open PRs must be reviewed and mapped to the cards before new implementation begins:

- **Keel:** #277 is the sole open K0 architecture/research PR; #276 was closed as duplicate and #275 is closed.
- **Media:** #291 is the proposed Media Core/Shanty/Deadeye architecture PR; issues #283–#290 and #292 are the existing media work packages. Do not create duplicates before review.
- **Shroud:** #274 — resize; #272 and #271 — PNG/font hardening overlap.
- **CCAM/formal/native:** #216, #245, #246, #254, #255, #256, #258, #262, #266, #228.
- **Research/assurance:** #238, #260.

The board snapshot also identified 36 open issues and 17 open PRs on 2026-11-25. This is a snapshot, not a live status guarantee. Re-run the inventory before assigning workers.

## Blocked / not yet Ready

- Anchor native process execution until an approved process/host API exists; #279 is contract/mock work, not permission to use shell or private C shims.
- Anchor native window/editor features until Shroud's public host/editor contracts exist; A0 remains headless.
- Keel scene-core and asset parser implementation until K0 decisions in #277 are accepted; #281/#282 can prepare reference models and bounded contracts without a GPU backend.
- Keel GPU implementation until the engine's resource/lifetime contract and trusted boundary are specified.
- Media parser/codec implementation until Core byte-source and aggregate-budget contracts (#284/#285), format selection (#287–#289) and relevant MC/SH/DE gates are satisfied.
- Audio/video playback until timebase and clock contracts (#286), device callback/presentation APIs and integration evidence exist.
- Media release until issue #292's applicable vulnerability ledger, regression corpus and independent security gates are satisfied.
- Full C-free release claims until compiler, runtime, standard library, bootstrap and platform dependencies are separately qualified.
- End-to-end verified execution claims until the implementation/refinement chain is established.

## Worker card template

Use this structure for every new issue:

```markdown
## Outcome
One independently reviewable deliverable.

## Product / milestone
CAP | SHR | ANC | KEL | SHANTY | DEADEYE | MEDIA CORE — Mx

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
2. Review and assign Anchor cards #279/#280; preserve the process API blocker.
3. Review and assign Keel cards #281/#282 after K0 decisions in PR #277 are accepted.
4. Review PR #291 and media architecture issue #283; reconcile all existing media cards #284–#290 and #292.
5. Prioritise Core contracts #284–#287, Shanty/Deadeye capability audits #288/#289 and the release-blocking security programme #292 before codec implementation.
6. Add labels consistently: `product:capstan`, `product:shroud`, `product:anchor`, `product:keel`, `type:implementation`, `type:research`, `type:assurance`, `stage:ready`, `stage:blocked`, `evidence-required`, `release-blocker`.
7. Keep issue state as the live Kanban state; this document is the programme index and should be refreshed as work moves.
