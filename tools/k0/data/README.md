# K0 generated-data status

The checked-in 2025 CSV, summary JSON and report were generated before the population-loader and kernel-memory projection corrections on the `worker5/k0-population-and-classification-fixes` branch.

Do not use those historical counts or percentages as current K0 results. Regenerate all three artifacts with `tools/k0/study.py` against a complete, pinned CVE List V5 checkout after this change is merged. The corrected loader rejects incomplete identifier-year directory sets, malformed JSON and malformed Linux-published records rather than silently accepting a partial population.
