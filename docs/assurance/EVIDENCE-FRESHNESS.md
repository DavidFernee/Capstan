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

Before checking existence or freshness, every covered path and evidence artifact is
resolved through symlinks and required to remain beneath the repository root.
A symlink that escapes the checkout, or a resolved path on another filesystem
root/Windows drive, is rejected as an unsafe path. A cross-root containment
comparison is treated as failure rather than an uncaught platform exception.

Stale records are always reported. The `--require-fresh` gate fails when a claim in
`active` or `qualified` state has a stale review or evidence item. Proposed claims
are not presented as current assurance and may retain stale exploratory evidence;
withdrawn claims are historical. This distinction lets the manifest expose review
debt without silently treating a stale qualified claim as current. CI and release
assembly both run the validator with `--require-fresh`.

The manifest must contain at least one claim, and each claim must contain at least
one evidence record. A repository with an empty claim inventory is invalid. Claims
whose evidence has become stale must be downgraded to `proposed` until a reviewer
refreshes the review and evidence at the current implementation revision.

Freshness is not correctness. A fresh test record still needs a real successful run
pinned to the exact source revision; an artifact's existence is not a passing test.
Likewise, a current review does not establish that its reasoning or specification
is sound. This mechanism detects invalidation by change; it does not prove a claim.
