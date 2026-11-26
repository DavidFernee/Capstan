# Assurance case and claim-promotion policy

## 1. Purpose

This document defines how Capstan turns security and correctness arguments into
reviewable, revision-bound assurance claims. It is deliberately conservative:
a property is not an assurance claim merely because a design document describes
it, a test fixture exists, or a theorem compiles.

The assurance case is a structured argument with five linked parts:

1. **Claim** — the exact property asserted, including scope and exclusions.
2. **Context** — threat model, attacker capabilities, execution path, platforms,
   assumptions and trusted computing base.
3. **Argument** — why the implementation should satisfy the claim.
4. **Evidence** — reproducible tests, analysis, proofs, reviews and build records.
5. **Defeaters and residual risk** — known counterexamples, gaps, assumptions and
   conditions that invalidate the argument.

The claim register in `claims.json` is the machine-readable index. This document
defines the policy; it does not itself qualify any claim.

## 2. Assurance dispositions

The manifest's lifecycle state and the evidence's result are different dimensions.
Do not collapse them into a single score.

### Claim lifecycle

- **proposed** — a candidate claim or research hypothesis. Evidence may be planned,
  incomplete or stale. It must not be presented as a current guarantee.
- **active** — a reviewed claim whose scope, assumptions and evidence are current.
  Active means the argument is maintained, not that the property is formally proved.
- **qualified** — a current claim with an explicit limitation, residual risk or
  restricted deployment scope. The qualification must be visible wherever the claim
  is presented.
- **withdrawn** — retained for audit history but no longer asserted.

### Evidence result

- **planned** — work is identified but has not been performed.
- **available** — an artefact or test procedure exists; it has not thereby passed.
- **not-run** — the procedure is defined but no result is recorded.
- **passed** — the exact recorded procedure completed successfully at the exact
  recorded source revision, with a verifiable run/review reference.
- **failed** — the procedure ran and did not meet its acceptance criteria.
- **superseded** — retained for traceability but replaced by newer evidence.

A passed test is not a proof. A proof over an abstract model is not implementation
evidence unless its refinement/correspondence boundary is established. A review is
not a test result. Record these independently.

## 3. Minimum claim record

Every claim must state:

- a unique stable identifier and a falsifiable statement;
- included program, compiler, runtime, platform and version scope;
- explicit assumptions and trusted dependencies;
- limitations and known residual risks;
- implementation paths whose changes invalidate the claim;
- evidence artefacts, exact source revision, procedure and result;
- review identity/revision and the disposition decision.

Evidence marked passed must additionally identify a full commit SHA and a GitHub
run, review or other immutable verification URL. The verification commit must
equal the evidence revision. A mutable branch name, local assertion, screenshot
without provenance, or file-presence check is not a passing result.

## 4. Promotion gate

The repository validator enforces the following minimum mechanical conditions
when CI runs with `--require-fresh`:

1. The manifest conforms to the JSON Schema and its paths resolve inside the
   checkout.
2. The claim review and each evidence record are based on an ancestor of HEAD.
3. No covered implementation path or evidence artefact has changed since the
   corresponding recorded revision.
4. At least one evidence record is marked passed and is pinned to its exact commit.
5. At least one passed `independent-review` record is tied to the same revision as
   the claim's recorded review.
6. Verification records include a full commit SHA and a GitHub run/review URL.

These checks are necessary, not sufficient. They establish record structure,
provenance shape and freshness; they do not determine whether a reviewer is truly
independent, whether a test is adequate, whether a proof theorem says what its
author claims, or whether a claim's scope is honest. Those remain review decisions.

A claim must remain proposed until a named reviewer has assessed the argument and
evidence. Do not set a claim active or qualified simply to make CI green. When an
implementation or evidence dependency changes, refresh the evidence and review or
downgrade the claim to proposed before merging.

## 5. Evidence classes and what they establish

| Evidence class | Can establish | Cannot establish by itself |
|---|---|---|
| Specification | Intended semantics and boundary | Implementation conformance |
| Positive/negative test | Observed behaviour for tested cases and environment | Absence of untested defects |
| Property/differential/fuzz test | Broader explored behavioural consistency | Exhaustive correctness |
| Static analysis | Findings under the tool's model and configuration | Complete absence of a weakness |
| Model check | Exhaustive result within the encoded state space and assumptions | Adequacy of the model to production |
| Mechanical proof | The theorem stated by the checked formal model | Parser, compiler, runtime or backend correctness without correspondence |
| Independent review | A second-party assessment of the supplied argument and artefacts | Reproducibility unless independently rerun |
| Reproducible build | Reproduction of specified outputs under recorded conditions | Source correctness or freedom from common-mode compromise |

Where relevant, combine evidence classes. Do not use a single green CI badge as a
substitute for a claim-specific evidence argument.

## 6. Formal assurance requirements

For a claim described as formally established, the assurance record must identify:

- the exact theorem names and quantified statements;
- the formal model and its normative specification revision;
- Lean/toolchain and checker versions;
- theorem dependencies and axiom audit;
- assumptions and trusted computing base;
- the implementation component to which the claim is intended to apply;
- the refinement, simulation or correspondence theorem linking model and
  implementation; and
- any unproved dependencies or excluded behaviours.

If the implementation link is missing, classify the result as a proof about the
model only. Do not call the production implementation formally verified.

## 7. Current programme boundary

At the reviewed mainline baseline for this change, the production compiler path
remains generated C, a host C compiler and the Capstan C runtime. The C-free CCAM
work is a set of integrated but restricted research slices. The Lean evidence is
not an end-to-end proof of source checking, lowering, validation, evaluation,
native code generation or runtime safety.

The current threat model also identifies residual CWE atlas gaps, trusted-base
risks, platform coverage limitations and the absence of independent external
security assessment. Those are first-class defeaters in the assurance case, not
footnotes to be hidden by a headline percentage.

The C-free programme must be assessed separately at each boundary: source
checker, typed lowering, decoder/validator, evaluator, native backend, runtime,
bootstrap and platform adapters. Each link needs its own conformance evidence and
a composable refinement argument before a system-level theorem can be claimed.

## 8. Release decision

A release decision is made per capability, execution path, platform and version.
The v1.0 scorecard remains authoritative for mandatory release gates. Missing,
stale, failed or unreviewed evidence is UNKNOWN or FAIL, never PASS. No aggregate
coverage percentage may obscure denominator changes, atlas gaps or unknown rows.

The release record must preserve:

- exact source and toolchain identities;
- completed CI and security test runs;
- formal proof/checker/axiom reports where claimed;
- SBOM, signatures, provenance and reproducibility evidence;
- independent assessment and remediation disposition; and
- explicit owner acceptance of each residual risk.

## 9. Validator boundary

`scripts/assurance-validate.py` enforces schema, path containment, Git ancestry,
freshness and the mechanical promotion prerequisites above. It is not an assurance
oracle. It cannot validate the quality or independence of a reviewer, execute every
evidence procedure, assess semantic correctness, inspect external build provenance,
or prove that a claim is true. CI output must therefore be described as
"manifest/evidence-gate validation", not "Capstan security verified".
