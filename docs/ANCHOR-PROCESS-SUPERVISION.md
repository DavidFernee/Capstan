# Anchor A1: process supervision and capability contract

**Status:** proposed architecture RFC; no process API is implemented by this document.
**Parent:** docs/ANCHOR.md; docs/ANCHOR-ARCHITECTURE.md; docs/ANCHOR-WORKSPACE-SECURITY.md
**Related:** [existing Anchor process-adapter issue #279](https://github.com/DavidFernee/Capstan/issues/279); docs/SHROUD-HOST.md; docs/architecture/C-FREE-RUNTIME-BOUNDARY-INVENTORY.md; docs/research/BASELINE-INVENTORY-2026-11-25.md

## 1. Decision sought

This RFC is the architecture/specification deliverable for the existing Anchor process-adapter work item [#279](https://github.com/DavidFernee/Capstan/issues/279). It supersedes neither that issue's mock-conformance-harness acceptance criteria nor its required explicit owner decision. A deterministic test-only reference-model harness is now proposed separately in [PR #321](https://github.com/DavidFernee/Capstan/pull/321); it is not evidence for a production backend.

Anchor needs to launch and supervise the configured Capstan compiler/LSP and explicit build/test/format commands. The current public runtime surface has no child-process creation, wait, cancellation or process-group API. Anchor must not work around that absence with shell commands, `system()`, `popen()`, private C shims or an ambient PATH lookup.

This RFC specifies the required semantics for a Capstan-native, capability-scoped process service. It deliberately does not invent public function signatures or claim that the service exists. The runtime, capability-I/O and T6/T7 owners must approve the capability model, effects, lifecycle and target ABI before implementation.

## 2. Scope and non-goals

In scope:
- start one explicitly identified executable with structured arguments;
- configure a minimal environment, working directory and standard streams;
- supervise process lifetime, bounded output, deadlines and cancellation;
- collect exit/signal status and provenance;
- contain descendants to the extent guaranteed by each supported OS;
- support LSP and explicit user-initiated CLI tasks.

Not in scope:
- arbitrary shell or command-language execution;
- project-defined build hooks, task scripts or package install scripts;
- a general remote execution service;
- a complete sandbox for arbitrary native code;
- process spawning as a prerequisite of the Shroud Wayland window host;
- claims that a process group or job object alone provides a security sandbox.

## 2.1 Proposed ownership decision for issue #279

**Selected architectural owner: the Capstan runtime/process service.** The public process capability contract, lifecycle state machine, handle ownership, resource accounting, stream supervision and process-tree policy belong to one Capstan-native process service in the runtime/standard-library layer. The narrow platform adapter supplies only target-specific OS process and handle operations.

The responsibilities are deliberately split:

| Owner | Responsibility | Explicit exclusion |
|---|---|---|
| Capstan process service | Public capability API; validate start requests; create/wait/terminate/reap; process-handle lifetime; budgets; bounded stream endpoints; platform-result mapping | Anchor command policy, LSP semantics, shell interpretation |
| OS platform adapter | Minimal ABI entry points for spawn/exec, wait, signal/job operations, pipe/handle creation and close; exact platform error conversion | Policy, executable selection, argument construction, UI, JSON-RPC |
| Anchor application | Trusted toolchain selection and pinning; fixed `lsp/check/build/test/fmt` profiles; argv construction; workspace/document provenance; JSON-RPC correlation, LSP generation/restart policy and presentation | Direct OS calls, raw PID/descriptor handling, alternate process launcher |
| Shroud native host | Window, input, display transport, frame presentation and native lifecycle | Child-process creation or compiler supervision |

This is one ownership decision, not a shared-ownership arrangement: **Capstan owns process creation and supervision semantics; the OS adapter implements only the kernel boundary; Anchor is a client.** Shroud is not a process-service owner.

Rejected alternatives:
- **Shroud-owned process API:** couples a reusable GUI toolkit to unrelated compiler/build policy and gives every Shroud application a process surface it does not need.
- **Anchor-private platform launcher:** duplicates capability, ownership and error semantics, creates a second OS boundary, and would tempt a C shim or shell workaround.
- **Direct raw OS API in Anchor:** leaks PID/descriptor semantics and makes confinement dependent on application discipline.

The exact source syntax, capability representation and effect annotations remain blocked on the reviewed capability/effect result in issue [#222](https://github.com/DavidFernee/Capstan/issues/222) and the T6/runtime contract. That dependency does not change the ownership boundary selected here. Runtime maintainers must approve/version the public interface before implementation; this RFC records the proposed decision for review, not an already approved API.

## 3. Capability model

The API is capability-oriented, not descriptor-oriented. Proposed conceptual authorities (names are illustrative):

- **ExecutableGrant:** pins one executable identity and permitted invocation profile. It is issued by trusted toolchain configuration, not by project metadata.
- **DirectoryGrant:** identifies a working directory with a specific access scope. Workspace paths are resolved under a separately validated workspace-root authority.
- **EnvironmentProfile:** immutable allowlist of named variables and explicitly supplied values; no ambient environment inheritance.
- **StreamEndpoint:** bounded input/output endpoint with explicit ownership and byte budget.
- **ProcessBudget:** maximum runtime, output, process count, descendants, and other supported resource ceilings.
- **ProcessHandle:** opaque identity for one started process and its lifecycle. It is not a PID and cannot be forged from an integer.
- **CancellationAuthority:** permission to request termination for a process and its owned descendants.

Capabilities must be non-forgeable, non-serializable and non-interchangeable. Copy/clone semantics are explicit. Authority is not inferred from a path string or integer OS handle. Revocation and owner-lifetime semantics must be specified before API approval.

The process service must not accept an arbitrary executable path from a workspace file. A user or administrator configures a toolchain; Anchor resolves and records the executable identity before any operation.

## 4. Start request semantics

A start request is an immutable value containing:
- pinned executable grant;
- argument vector as a sequence of distinct strings;
- explicit working-directory grant;
- environment profile;
- stdin/stdout/stderr endpoint policy;
- resource budget and deadline;
- descendant-containment policy;
- operation purpose (LSP, check, build, test, format);
- workspace and document provenance for audit.

The request is validated completely before any child becomes observable. Failure must not leave a partially started process or leaked descriptors. The API never accepts a shell string, shell mode, command substitution, globbing or implicit PATH search.

Executable identity must be pinned strongly enough to detect replacement between configuration and launch. The platform contract must state what is guaranteed: canonical file identity, digest/signature policy, opened executable handle semantics, or a documented residual race. A display path alone is insufficient.

Arguments remain separate through the public API. Platform backends must implement OS-correct argv construction; Windows command-line serialization is an internal backend concern and must be covered by round-trip tests for quotes, backslashes, empty arguments and Unicode. Application code must never perform Windows quoting itself.

## 5. Environment and inherited authority

Default environment is empty. A reviewed profile may add a minimal set of values required by the compiler/runtime, each with a reason and provenance. Do not inherit PATH, loader injection variables, shell startup variables, credential agents, cloud tokens, SSH agents, proxy credentials or user secrets by default.

The child receives only explicitly selected standard streams and capabilities. Unneeded file descriptors/handles are closed or marked close-on-exec. No ambient network, display, clipboard, filesystem or secret authority is implicitly granted. If the compiler needs workspace files, it receives the minimum read/write authority required by the operation; a read-only check/LSP profile should not receive write authority.

## 6. Process lifecycle state machine

The supervisor owns an explicit state machine:

    Created -> Starting -> Running -> ExitObserved -> Reaped
                    |          |
                    v          v
                  Failed   TerminationRequested
                                |
                         TerminationConfirmed
                                |
                              Reaped

- **Created:** validated request, no OS process exists.
- **Starting:** launch in progress; no success is published yet.
- **Running:** OS confirms process creation and the supervisor owns its handle.
- **TerminationRequested:** cancellation/deadline/output policy requested termination; process may still execute.
- **TerminationConfirmed:** OS confirms the process has exited or has been terminated.
- **ExitObserved:** exit code or signal information has been collected.
- **Reaped:** all process and stream resources are closed and accounting released.
- **Failed:** launch failed with typed error and no live child or leaked authority.

A cancellation request is not a completion result. Anchor must not show “stopped” until termination is confirmed and the process is reaped. Repeated cancellation is idempotent. A lost supervisor connection or failed termination is an explicit unresolved state, not success.

## 7. Descendant containment

LSP/compiler processes may launch descendants accidentally or maliciously if the executable is compromised. The contract must create an owned process group/session or equivalent OS job/container primitive at launch, with close-on-exec and no breakaway by default where supported.

Termination must target the owned process tree, not only the direct child. The backend must specify and test:
- POSIX process-group/session creation, races with immediate child exit, signal delivery and reaping;
- Windows job-object assignment before untrusted child code can spawn descendants, kill-on-job-close and breakaway policy;
- what happens when the OS cannot guarantee containment;
- whether the service can report a descendant that escaped containment.

If a supported platform cannot guarantee the required descendant boundary, Anchor must disable untrusted workspace execution on that platform or state a narrower, explicit guarantee. Do not call process groups a sandbox.

## 8. Output and backpressure

stdout and stderr are byte streams, not trusted terminal markup. The supervisor must drain both without deadlock and preserve channel identity. It enforces:
- maximum bytes per stream and aggregate output;
- maximum retained in-memory output;
- bounded event queue and chunk size;
- explicit truncation marker and total bytes observed;
- no blocking of UI thread on child output;
- redaction as defence in depth, never as permission to log secrets.

Once output budget is exhausted, the policy is explicit: terminate the child or continue draining while discarding excess bytes. The initial Anchor policy should terminate build/test commands on output abuse; LSP has a separately bounded protocol channel and fails the server on protocol/output violation. No silent unbounded disk spooling.

For LSP, stdout is exclusively JSON-RPC framing. stderr is diagnostic text. Build/test output is displayed as escaped text. Control characters, bidi controls and deceptive terminal sequences must not execute or create trusted hyperlinks.

## 9. Deadlines, resource limits and cancellation

Each invocation has a monotonic absolute deadline. Relative timeout conversion is checked for overflow. The host clock is trusted platform input; wall clock and child-supplied timestamps do not control deadlines.

The service enforces hard caps for:
- concurrent children per workspace and per user session;
- process lifetime and shutdown grace period;
- stdout/stderr bytes and retained output;
- open handles/descriptors;
- process descendants;
- CPU, memory and other OS resource limits where reliable primitives exist.

Limits must be distinguished as **enforced**, **best-effort**, or **not available** per platform. Do not label a CPU/memory limit enforced if the backend only observes usage. A child that exceeds a hard policy is terminated and reaped; cleanup failure is surfaced.

Cancellation sequence:
1. mark cancellation requested and stop accepting new work for that operation;
2. send graceful termination to the owned process group/job where appropriate;
3. wait until the monotonic grace deadline;
4. force termination of remaining owned descendants;
5. confirm exit and reap;
6. close streams and release accounting;
7. publish a terminal result with cause (normal exit, user cancel, timeout, output limit, protocol violation, supervisor failure).

The sequence is idempotent and bounded. It must not wait indefinitely for a child that ignores termination.

## 10. Error model

The public Capstan layer returns typed outcomes, not raw errno or ambiguous booleans. Required categories include invalid request, missing/revoked capability, executable identity mismatch, permission denied, resource exhausted, launch failure, interrupted, would-block, deadline exceeded, cancelled, I/O failure, protocol violation, termination failure and unsupported platform guarantee.

Platform-specific codes may be retained as diagnostic metadata but are not the only application contract. Error values must not include secrets or attacker-controlled format strings.

## 11. Anchor invocation profiles

| Purpose | Executable/arguments | Filesystem | Network | Output |
|---|---|---|---|---|
| LSP | Pinned compiler identity, fixed `lsp` subcommand | Workspace read-only initially | Denied | stdout framed protocol; bounded stderr |
| Check | Pinned compiler, fixed `check` arguments | Workspace read-only | Denied | Bounded stdout/stderr |
| Format | Pinned compiler, fixed `fmt` arguments | Exact selected files writable only after explicit action | Denied | Bounded output |
| Build | Pinned compiler, fixed `build` arguments | Workspace read; designated output path write | Denied | Bounded output |
| Test | Pinned compiler, fixed `test` arguments | Workspace read; isolated designated test outputs | Denied by default | Bounded output |

The current CLI surface is limited to `check`, `build`, `test`, `fmt` and `lsp`. Do not expose `run`, project hooks or arbitrary custom arguments as an MVP feature. The command adapter constructs the allowed argv from typed options; user-provided values are validated as individual arguments and never concatenated into a shell command.

## 12. LSP-specific supervision

One LSP child per workspace is the initial policy. Each process generation owns a separate JSON-RPC session. Requests are correlated to that generation and document version. On crash or protocol violation:
- fail all outstanding requests with a typed server-restarted error;
- discard late output from the old generation;
- close/reap the old process before starting another;
- restart with capped exponential backoff and jitter;
- trip a circuit breaker after a small bounded number of repeated failures;
- require explicit user action or a cooldown before resetting a tripped breaker.

Do not spawn restart storms. A restarted server must receive a fresh initialize sequence and current open-document snapshots. Diagnostics from a previous generation are stale and cannot overwrite current state.

## 13. Audit and privacy

Record operation ID, workspace identity (not source contents), toolchain identity/digest, fixed subcommand, redacted argument metadata, environment profile ID, start/end times, exit status, cancellation cause, resource-limit outcomes and output truncation. Never record environment values, credentials, source buffers or full arbitrary output as telemetry.

The local output panel may display process output after safe text rendering. Diagnostic retention and export have explicit user control.

## 14. Verification plan

Required conformance and adversarial tests:
- argv round-trip corpus including empty args, quotes, backslashes, Unicode and shell metacharacters;
- executable replacement between selection and launch;
- malicious PATH/loader/environment sentinels not inherited;
- descriptor/handle leakage and close-on-exec;
- child that floods stdout, stderr or both concurrently;
- child that writes one byte at a time, closes one stream, or never closes either;
- child that ignores graceful termination;
- child that forks/spawns descendants then exits;
- cancellation racing normal exit and cancellation racing launch;
- timeout clock overflow/regression;
- process/handle/output budget exhaustion before partial publication;
- LSP malformed/oversized frames, stdout noise, stderr flood and stale generation messages;
- Windows quoting and job-object assignment race tests;
- POSIX process-group escape and reaping tests.

Property-based state-machine tests should assert: each successfully started child is reaped exactly once; no terminal result precedes confirmed termination; resource accounting returns to baseline; no result from a prior generation mutates current state.

## 15. Acceptance gates

The process service is not ready for Anchor integration until:
1. Capstan-native public capability and effect contracts are approved and versioned.
2. The C-free implementation path exists for every claimed target; any temporary bootstrap boundary is explicitly inventoried and cannot become a hidden release dependency.
3. Executable identity, argv, environment and working-directory semantics are tested per platform.
4. Descendant containment guarantees are documented and adversarially tested.
5. Output, deadlines, cancellation and resource limits have deterministic failure semantics.
6. Fuzzing and state-machine tests cover the protocol/lifecycle boundary.
7. The exact implementation revision passes required CI and is linked to an evidence record.

Until these gates pass, Anchor may display its planned process integration but must not launch children through an improvised mechanism.
