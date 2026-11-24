# Evidence freshness

The assurance validator computes freshness from Git history rather than trusting a
manually maintained status field.

Each claim declares `covers`: the repository paths whose implementation changes
invalidate its review. The review's `reviewed_commit` is the source revision against
which that review was performed. Each evidence item has its own `revision` and
artifact list. The validator compares both the covered implementation paths and
the evidence artifacts between the recorded revision and the checked-out `HEAD`.

A changed covered path marks the review stale. A changed artifact or covered path
marks the corresponding evidence stale. A revision that is not an ancestor of
`HEAD` is also stale; this prevents silently accepting evidence from an unrelated
history. The check uses Git's path-aware diff, not timestamps or branch names.

By default, stale records are reported but do not fail CI. This is deliberate while
existing claims are being brought under explicit coverage: the report must expose
the debt without pretending that the underlying claim has been re-reviewed. Release
automation can use `--require-fresh` to make stale records fatal once the assurance
owners have refreshed the reviews and evidence.

Freshness is not correctness. A fresh test record still needs a real successful run
pinned to the exact source revision; an artifact's existence is not a passing test.
Likewise, a current review does not establish that its reasoning or specification
is sound. This mechanism detects invalidation by change; it does not prove a claim.
