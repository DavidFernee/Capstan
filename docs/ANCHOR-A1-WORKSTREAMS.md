# Anchor A1: host and process workstream decomposition

**Status:** proposed sequencing decision; no implementation is implied
**Parent:** docs/ANCHOR.md; docs/ANCHOR-CAPABILITY-IO-REQUIREMENTS.md; docs/SHROUD-HOST.md; docs/proposals/SHROUD-LINUX-WAYLAND-PREREQUISITES.md
**Decision owner:** Anchor/Shroud/runtime maintainers jointly

## 1. Problem found in the A1 milestone

The existing Anchor roadmap calls A1 “Host process adapter” and lists native window/embedder work and supervised compiler child processes together. They are related to the IDE but are not the same architectural dependency.

A native Shroud host does not need to spawn a compositor or helper process. The Wayland prerequisite RFC explicitly excludes process creation from the initial toolkit host. Conversely, Anchor can supervise the compiler/LSP in a headless or scripted host without a native Shroud window.

Treating both as one milestone couples two different trust boundaries, runtime prerequisites, platform surfaces and test suites. It creates avoidable critical-path coupling and makes partial progress hard to report accurately.

## 2. Proposed decision: split A1 into independently gated tracks

### A1-P — Process service for Anchor

Delivers the capability-scoped process API and Anchor supervisor required for LSP and explicit compiler commands.

Dependencies:
- Capstan capability-I/O and typed resource/error contracts;
- process creation, wait/reap, cancellation and descendant-containment primitives;
- compiler executable identity and toolchain configuration;
- bounded asynchronous I/O and monotonic deadlines.

Acceptance is governed by docs/ANCHOR-PROCESS-SUPERVISION.md. This track can be developed and tested with a headless Anchor harness. It does not require Shroud's native window.

### A1-H — Shroud native host

Delivers the first native window and event/presentation adapter for Shroud, initially Linux/Wayland.

Dependencies:
- reviewed S1 host lifecycle and event contract in docs/SHROUD-HOST.md;
- minimal capability-I/O, Unix-domain socket, descriptor passing, poll, memfd, pwrite and monotonic-clock primitives;
- bounded Capstan Wayland protocol implementation;
- frame ownership, input/focus/capture transitions and platform failure recovery.

This track does not depend on process creation. It must not add a hidden helper executable or shell-based launcher.

### A1-I — Anchor integration

Connects the Anchor model and Shroud presentation to the completed host and process services. The app itself remains Capstan; Shroud remains the UI toolkit; compiler/LSP remain semantic authorities.

Integration acceptance requires:
- explicit host lifecycle and clean shutdown;
- process service invoked only through approved capability grants;
- stale workspace/document/process generations discarded;
- UI remains responsive while process I/O runs;
- every user-triggered command displays its exact fixed operation profile and outcome;
- no unsupported editor, IME, clipboard or accessibility capability is claimed.

## 2.1 Process-service ownership decision

A1-P has one proposed owner: the **Capstan runtime/process service**. The platform ABI is a narrow implementation boundary, not a second policy owner. Anchor constructs only approved invocation profiles and owns LSP/command presentation. Shroud owns the native window host and does not spawn or supervise compiler children. The decision and rejected alternatives are recorded in `ANCHOR-PROCESS-SUPERVISION.md`; runtime approval and versioned API publication remain an explicit gate.

## 3. Dependency graph

    Capability-I/O + typed errors + resource accounting
                  /                         \
                 v                           v
       A1-P process service             A1-H host primitives
                 |                           |
       Anchor LSP/CLI supervisor       Shroud Wayland backend
                 \                           /
                  v                         v
                       A1-I integration

The two tracks may proceed in parallel only after the shared capability-I/O contracts are versioned. Neither may invent private host calls or bypass the public capability layer.

## 4. Platform rollout

- **A1-H first platform:** Linux/Wayland, matching the current Shroud S1 contract.
- **A1-P first platform:** Linux x86-64, then Linux AArch64; Windows/macOS require independently specified executable, process-tree and I/O semantics.
- **Anchor integration:** headless test harness first; native window integration after A1-H has passed its own acceptance gate.

Do not claim cross-platform support because a shared Capstan API compiles. Each OS needs executable lifecycle, output, cancellation, descendant and path-identity tests.

## 5. C-free constraint

The target implementation is Capstan-native. A narrow platform ABI may expose only OS entry points and typed results; it must not implement process policy, shell parsing, UI, Wayland protocol, LSP framing or Anchor semantics.

Any temporary C/assembly bootstrap boundary must be explicit in the trusted-base inventory, limited to the minimum ABI glue, tested independently and removed from the claimed C-free release path. It must not become a private Anchor shortcut. No generated-C runtime or shell wrapper is accepted as the final A1 implementation.

## 6. Explicit non-goals

- No project-defined build hooks, task runners or package scripts.
- No arbitrary executable selection from project metadata.
- No shell terminal or general-purpose command palette.
- No native helper process for Wayland.
- No GPU presentation requirement in the first host; the software renderer remains the reference.
- No IME, clipboard, full text editor or native accessibility claim until their separate Shroud contracts and conformance suites exist.
- No general sandbox claim for a child process merely because it is launched without a shell.

## 7. Existing issue alignment and work packages

This plan extends existing work rather than creating duplicate tickets:
- [#224](https://github.com/DavidFernee/Capstan/issues/224) owns the Shroud/T6 Linux Wayland capability and syscall vertical slice; the shared contract in `ANCHOR-CAPABILITY-IO-REQUIREMENTS.md` is a requirements synthesis/input to that work.
- [#279](https://github.com/DavidFernee/Capstan/issues/279) owns the Anchor process-adapter decision and mock conformance harness; `ANCHOR-PROCESS-SUPERVISION.md` supplies the lifecycle/security contract, but does not complete the harness or API-owner decision.
- [#222](https://github.com/DavidFernee/Capstan/issues/222) remains the research authority for the broader capability/effect model. This A1 design must consume its reviewed result rather than pre-empt it.

## 7.1 Work packages ready for assignment

| ID | Work package | Deliverable | Blocker / exit gate |
|---|---|---|---|
| A1-CAP-01 | Capability-I/O contract delta | Opaque endpoint/handle, rights, ownership, error and budget model | Runtime/capability review |
| A1-PROC-01 | Process lifecycle semantics | State machine, cancellation, reaping, descendant ownership | A1-CAP-01 |
| A1-PROC-02 | Linux process backend | Capstan-native launch/wait/terminate/pipe implementation | T6/T7 ABI support; adversarial suite |
| A1-PROC-03 | Supervisor and output pumps | Bounded stdout/stderr, deadlines, circuit breaker | A1-PROC-01/02 |
| A1-PROC-04 | Anchor compiler/LSP profiles | Fixed argv builders, executable pinning, toolchain identity | A1-PROC-03 |
| A1-HOST-01 | Wayland protocol core | Bounded wire codec/object state machine | Capability-I/O socket contract |
| A1-HOST-02 | Shared-memory presentation | memfd/pwrite/SCM_RIGHTS buffer lifecycle | Descriptor passing + file primitives |
| A1-HOST-03 | Event/focus/clock adapter | Pointer capture/cancel, focus, monotonic clock | Host clock and event contract |
| A1-HOST-04 | Linux native lifecycle | xdg-shell create/resize/close/recovery | A1-HOST-01..03 |
| A1-INT-01 | Anchor model integration | Host-backed shell + process service | A1-P and A1-H |
| A1-ASSURE-01 | Evidence and adversarial tests | Exact-head test report and threat-boundary evidence | All implementation work packages |

Work packages are contracts and ownership suggestions, not permission for parallel workers to edit shared runtime APIs. The runtime team owns public capability definitions; Shroud owns its host API; Anchor owns adapters and application integration.

## 8. Status vocabulary and reporting

Report each track separately as proposed, specified, implementation in progress, integrated, tested or validated. A design document is not an implementation. A host window smoke test is not a full Shroud S1 gate. A child process exit code is not proof that descendants were terminated. A successful compiler check is not an Anchor security certification.

## 9. Decision requested

Approve the A1-P/A1-H/A1-I split before implementation. If maintainers reject the split, record the coupling rationale and explicit cross-track acceptance conditions in an ADR; do not silently recombine the work.
