# Anchor: workspace, process and trust security

**Status:** proposed design specification; not implemented
**Parent:** docs/ANCHOR.md

## Threat model

Assume a workspace may be malicious. Attackers may control source, metadata, filenames, symlinks, generated artifacts, compiler output, dependency descriptors and evidence. Threats include traversal, symlink/TOCTOU attacks, resource exhaustion, command injection, credential theft, terminal spoofing, protocol confusion and supply-chain substitution.

The design does not claim to defeat a compromised OS, kernel, hardware, user account or explicitly trusted toolchain binary.

## Workspace opening

Opening a directory is read-only inspection. It MUST NOT execute scripts, hooks, tasks, extensions, package managers or source; fetch network resources; or rewrite metadata. Project metadata is bounded declarative data with a versioned schema. Reject duplicate keys, invalid encodings, excessive nesting and oversized collections. Unknown fields are never executable instructions.

## Filesystem confinement

String-prefix checks are not confinement. Use platform-supported directory-relative operations and identity checks that resist symlink substitution and TOCTOU races. Retain workspace-root identity; reject absolute paths, parent traversal, special files and symlinks escaping the root. Where a platform cannot provide reliable race-resistant primitives, disable the operation or explicitly downgrade the guarantee.

Bound recursion depth, file count, per-file bytes and aggregate bytes. Address hard links, mount points, case folding, Unicode normalization and platform path aliases. A canonical display path is not an authorization token.

## Document writes

Revalidate directory and target identity at commit time. Use same-directory temporary files, restrictive creation modes, flush and atomic replacement where supported. Detect target replacement, permission changes and external modifications. Never follow an attacker-substituted symlink.

## Process execution

No shell. Commands are a fixed Capstan allowlist and use an explicitly configured executable identity with argv vectors. The child receives a minimal explicit environment, fixed working directory, bounded I/O, time/resource limits and controlled descriptors. Ambient credentials are not inherited.

The current runtime lacks the child-process creation/wait/cancellation/process-group contract required by Anchor. This is a blocking prerequisite. Do not bridge it with system(), popen(), shell interpolation or private C shims.

## LSP and IPC

Treat child output as hostile. Bound JSON-RPC frame size before allocation, validate framing and IDs, cap queues and diagnostics, and keep stdout protocol-only. Apply backpressure. Restart with capped backoff and a circuit breaker. Late messages are discarded by process generation and document version. A process is not considered terminated until confirmed.

## Output and secrets

Render process output as text, not terminal control or trusted markup. Escape control, bidi and zero-width characters. Links require safe scheme validation and explicit activation. Never log source, credentials or environment values. Recovery files and lockfiles contain no secret values; secret references are distinct from secrets.

## Supply chain and evidence

Workspace opening may inspect local lock/evidence data but does not fetch or install. Pin package identity by digest and complete dependency closure. Signatures, provenance, SBOMs, assurance statements and advisories are independent dimensions. Offline results identify exact trust/advisory snapshots and freshness; cached signatures do not establish current revocation status. Snapshot rollback must be detected. Missing/stale evidence is unknown/stale, never pass.

## Denial-of-service budgets

Define hard ceilings for workspace files/depth/bytes, document size and dirty-buffer aggregate, LSP frame/queue/diagnostics, process output/time/concurrency, preview CPU/memory/output, and evidence nesting/collections/decompressed bytes. Check before allocation or expensive work. Exhaustion yields a bounded recoverable error.

## Adversarial test plan

Test symlink swaps, traversal, hard links, path aliases, special files, huge sparse files, deeply nested metadata, duplicate JSON keys, oversized/truncated LSP frames, stdout/stderr floods, hung children, process-tree escape, environment sentinel leakage, bidi/control spoofing and trust-snapshot rollback. Fuzz parsers and state machines; every fix receives a regression reproducer.

## Acceptance gates

No workspace-triggered execution/network; no shell or private C process shim; demonstrated confinement per supported OS; pre-allocation bounds on parsers/queues; explicit minimal child environment; tested cancellation/timeout/restart; no secrets in logs/lock/recovery; evidence claims never exceed their scope.
