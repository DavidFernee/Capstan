# K0 classifier checks

Labelled samples for the 2025 publication-year K0 kernel CVE study (`tools/k0/study.py`, `docs/K0-KERNEL-CVES.md`). Each row
is a CVE published in 2025 (some identifiers were allocated in earlier years) and the class assigned
from its CNA description, using the class names in `tools/k0/classify.py`. The study loader scans every CVE identifier-year directory,
because identifier year and publication year are not equivalent. Run the study only against a complete
CVE List V5 checkout with a clean Git working tree and a complete materialised JSON inventory; sparse checkouts are rejected by comparing tracked and on-disk records. Run from a clean Capstan Git checkout as well. The exact 40-character CVE List and Capstan source commits are recorded in the report and summary JSON. Generated reports explicitly state NOT INDEPENDENTLY VALIDATED / RESEARCH ONLY until blind human relabelling is complete. Incomplete checkouts and malformed Linux-published records are rejected.

- `labels.csv`: 60 CVEs drawn at random for development diagnostics.
- `labels-heldout.csv`: 40 further CVEs drawn at random for a nominal held-out diagnostic.

Both sets were labelled by the same AI assistant that developed the classifier. The labels are not
independent ground truth; their agreement figures are not classifier accuracy or validation evidence.
The study reports them only as internal diagnostics and runs these fixed samples only for the 2025
publication-year population. At least two independent human reviewers must relabel a frozen sample
before the classifier's accuracy or any replacement K0 headline can be asserted.

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
