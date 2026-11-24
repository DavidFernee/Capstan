# K0 classifier checks

Labelled samples for the K0 kernel CVE study (`tools/k0/study.py`, `docs/K0-KERNEL-CVES.md`). Each row
is a CVE from the study year and the class a reader assigned from its fix description, using the
class names in `tools/k0/classify.py`. The study loader scans every CVE identifier-year directory,
because identifier year and publication year are not equivalent. Run the study only against a complete
CVE List V5 checkout with a clean Git working tree and a complete materialised JSON inventory; sparse checkouts are rejected by comparing tracked and on-disk records. Run from a clean Capstan Git checkout as well. The exact 40-character CVE List and Capstan source commits are recorded in the report and summary JSON. Generated reports explicitly state NOT INDEPENDENTLY VALIDATED / RESEARCH ONLY until blind human relabelling is complete. Incomplete checkouts and malformed Linux-published records are rejected.

- `labels.csv`: 60 CVEs drawn at random. The classifier's rules were refined after this sample was
  read, so its agreement here is optimistic.
- `labels-heldout.csv`: 40 further CVEs drawn at random and labelled before the classifier's answer
  was looked at; no rule was changed afterwards. This is the agreement the report quotes.

Both sets were labelled by Claude (the AI assistant that wrote the classifier). An independent
reviewer relabelling them is the next step for the study's credibility.

## Independent relabelling protocol

Before publishing replacement K0 figures:

1. Freeze the classifier source revision and the pinned CVE List commit. Give reviewers only CVE
   identifiers, publication dates, CNA titles and descriptions; hide automatic classes, existing
   review labels and projected outcomes.
2. Have at least two independent human reviewers label the existing held-out sample and a
   reproducibly selected, stratified sample of the previously reviewed population. Include every
   major class where practical and oversample rare classes; record the sampling seed and frame.
3. Record each reviewer's class, CWE, present-day outcome, rationale and uncertainty separately.
   Do not tune classifier rules against this blind sample.
4. Adjudicate disagreements after independent labels are frozen. Report raw agreement, per-class
   confusion matrices, outcome agreement and an appropriate inter-rater statistic for nominal
   labels (for example Cohen's kappa for two reviewers), with sample sizes and confidence intervals.
5. Re-run the study only after adjudication. Publish sensitivity ranges showing how disputed
   labels affect present-day prevention and K1 projections. Keep classifier agreement separate
   from human inter-rater agreement.

If two independent human reviewers or the source evidence are unavailable, mark the study's
validation status UNKNOWN; do not describe the AI-labelled samples as independent ground truth.


## Study implementation regressions

Run `python3 tests/k0/check.py` (also part of `tests/run.sh`) to verify that:
- a CVE assigned in an earlier identifier year but published in the study year is included;
- incomplete year-directory checkouts and malformed Linux-published records fail closed;
- source snapshots without Git provenance, with uncommitted/untracked changes, or with sparse/missing tracked records are rejected;
- K1.10 candidates are labelled proof-eligible projections, never as established proofs without implementation-linked machine-checked evidence;
- memory-safety consequences in the CNA body outrank non-memory causes in the title;
- teardown and data-race phrases match the K0 projection rule without matching ordinary prose;
- use-after-free and double-free remain outside today's kernel capability and project only conditionally on K1.1.
