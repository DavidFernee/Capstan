# Schooner S1 reference-model assurance record

**Status:** initial bounded executable models added; CI evidence pending.
**Scope:** sequential abstract transitions only.
**Models:** `verification/schooner_capability.cap`, `verification/schooner_budget.cap`.

## Capability model

The model represents one object and two capability slots. A handle binds object identity, object generation, slot identity, slot generation, rights and revocation epoch. Resolution checks every field against the current object and slot record. Delegation is attenuation-only. Object-wide revocation advances the epoch before invalidating both slots. Slot generations and the epoch fail closed at exhaustion rather than wrapping.

Nine tests cover root issuance, subset rights, attempted rights amplification, wrong object, wrong object generation, wrong slot, wrong slot generation, stale epoch, delegated-slot revocation and generation-safe reuse, object-wide revocation, insufficient revoke authority, duplicate slot use, generation/epoch exhaustion and failure atomicity.

**Critical limitation:** the model's `SCMHandle` is an ordinary Capstan struct. A caller can construct one. This is not an unforgeable capability representation, does not validate issuer isolation, and does not establish runtime/kernel enforcement. The model checks the transition semantics conditional on trusted issuance and intact state.

## Resource-budget model

The model has one root, one child and one grandchild account and a bounded total of at most 1,000,000 abstract units. Splitting moves units from parent to child. Consumption moves units to a spent ledger. Returning a lease is generation-checked and one-shot; a parent cannot reclaim while a descendant lease remains live.

The invariant is:

`root_balance + child_balance + grandchild_balance + spent = total`

All account balances are non-negative, all leases have consistent live state, and all transitions preserve the invariant. Eight tests cover nested conservation, exact consumption, descendant-before-parent release, one-shot returns, stale-generation rejection, slot reissue, failure-atomic invalid, zero and over-budget operations, and exhaustive nested split/consume/return sweeps for totals 1 through 8. **Critical limitation:** `SBMHandle` is an ordinary transparent Capstan struct and can be constructed by a caller. The model does not establish unforgeable lease ownership or an authenticated root issuer. It checks generation and accounting transitions conditional on trusted API entry and intact state. It does not yet cover concurrent split/consume/return races, physical resource measurement, wall-clock deadlines, DMA, or implementation refinement.

## Evidence ladder

| Claim | Current level | Not established |
|---|---|---|
| Model transition semantics execute in Capstan | Pending exact-head CI | Local run unavailable in this editing session |
| Listed sequential invariants hold for included tests | Pending exact-head CI | Exhaustive state-space proof |
| Capability handles are unforgeable | Not established | Kernel representation, trusted issuer and adversarial boundary tests |
| Revocation is linearizable under concurrency | Not established | Concurrent operation model and runtime refinement |
| Resource budgets cannot be duplicated concurrently | Not established | Concurrent transition model and implementation proof |
| Kernel enforces these properties | Not established | Kernel implementation and target-platform evidence |

No vulnerability-free, formally verified, production-ready or kernel-enforced claim is made. A green test run will establish only that these bounded tests pass for the checked revision.
