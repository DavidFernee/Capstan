# Capstan Working Standard — RFC review workspace

**Status:** unratified, incomplete implementation correspondence. This is a standards review submission, **not** a claim that Capstan 1.0, its grammar, proof obligations, implementation or comparisons are finished.

- [Working Standard v0.7](Capstan-Working-Standard-v0.7.md): full twenty-RFC user-supplied proposal, unchanged in substantive scope.
- [Formalisation bridge](FORMALISATION-BRIDGE.md): baseline-bound architectural reconciliation, scope-limited mathematical core, initial proof statements and implementation mapping.
- [Machine-readable traceability](traceability.json): one candidate mapping per RFC, distinguishing components from verified evidence and listing missing independent proof/implementation gates.
- [External research transition model](models/revocation-crash-model.py) and [recorded output](models/revocation-crash-results.txt): bounded counterexample exploration, not a Capstan proof or production dependency.

**Baseline:** `main` tree `d5efd7a8488261914cf191c39c22ba26fa43aaa1`. Re-evaluate against fresh main and open PRs before merging.

## Evidence and ratification rules

A normative statement is not necessarily an implemented feature. Source inspection is not a passed test, a finite-state result is not a universal theorem, a machine-checked abstract lemma is not compiler refinement, and a passing pipeline is not a cryptographic, side-channel or platform-isolation proof.

All 20 RFCs remain working drafts. Do not claim full conformance, vulnerability-class exclusion, zero known risks, superiority over competing languages or Foundation ratification based on these files.

## Reproduction

External research tool only:

```sh
python3 docs/rfc/models/revocation-crash-model.py
```

Compare stdout against `models/revocation-crash-results.txt`. The model's bounded domains are described in the v0.7 draft. This script is not part of the all-Capstan production toolchain.

No new Lean theorem was checked by this PR, and existing `formal/` proof claims retain their original exact-revision scope. Before ratification, require an independent reviewer, exact-ref proof replay, executable production correspondence, positive/negative conformance vectors, benchmark preregistration and CI on the actual proposed merge head.

## Deliberately unmodified overlapping paths

Do not independently rewrite `docs/DESIGN-MAP.md`, `docs/SPEC.md`, `docs/architecture/CCAM.md`, `compiler/`, `verification/`, `formal/` or the shared test runner from this workstream. Existing integrations and open PRs own those files. Stage small subsequent implementation PRs under the issue #25 coordination process.

## Review gates

1. Reconcile and pin byte-level lexical/grammar implementation and conflicts.
2. Mechanise the source type/effect system and operational transition rules.
3. Define whole-machine CCAM / runtime / native backend refinement and attack contexts.
4. Build trusted, signed evidence inventory with proof/implementation/CWE traceability.
5. Reproduce adversarial campaigns and independent comparative experiments.
6. Obtain independent standards review and Foundation governance ratification.
