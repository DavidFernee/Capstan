# K0 classifier checks

Hand labels for the K0 kernel CVE study (`tools/k0/study.py`, `docs/K0-KERNEL-CVES.md`). Each row
is a CVE from the study year and the class a reader assigned from its fix description, using the
class names in `tools/k0/classify.py`.

- `labels.csv`: 60 CVEs drawn at random. The classifier's rules were refined after this sample was
  read, so its agreement here is optimistic.
- `labels-heldout.csv`: 40 further CVEs drawn at random and labelled before the classifier's answer
  was looked at; no rule was changed afterwards. This is the agreement the report quotes.

Both sets were labelled by Claude (the AI assistant that wrote the classifier). An independent
reviewer relabelling them is the next step for the study's credibility.
