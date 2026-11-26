# Anchor A1 capability-I/O contract requirements

**Status:** proposed contract delta for runtime review; not an approved public API and not an implementation  
**Shroud API candidate:** [Capability-I/O host API v0.1](proposals/CAPABILITY-IO-HOST-API-V0.1.md) defines the first Linux/Wayland host profile. It does not complete Anchor filesystem/process operations or replace this shared A1 requirements review.  
**Parent:** `docs/ANCHOR-A1-WORKSTREAMS.md`, `docs/ANCHOR-PROCESS-SUPERVISION.md`  
**Related:** issues [#224](https://github.com/DavidFernee/Capstan/issues/224) (Shroud/T6 host substrate), [#222](https://github.com/DavidFernee/Capstan/issues/222) (capability/effect research); `docs/SHROUD-HOST.md`, `docs/proposals/SHROUD-LINUX-WAYLAND-PREREQUISITES.md`, `docs/architecture/C-FREE-RUNTIME-BOUNDARY-INVENTORY.md`, `docs/architecture/LANGUAGE-EXTENSIONS.md`, `docs/STDLIB-V06.md`

## 1. Decision sought

Approve one shared, Capstan-native capability-I/O contract for Anchor A1-P and A1-H, implemented through the C-free runtime/platform boundary. This document identifies the minimum semantic contract and the gaps exposed by the current Anchor and Shroud requirements. It does not define final source syntax, ABI numbers, or concrete public function names.

The contract must be designed once and reused. Anchor must not grow a private process/filesystem API while Shroud grows a separate socket/clock API. Conversely, a generic descriptor API must not expose raw OS descriptors or grant ambient authority.

**Semantic constraint:** an effect describes what an operation may do; a capability describes which authority the caller must possess. These are distinct semantic questions even if the eventual language syntax integrates them. An effect annotation must never manufacture authority. The precise type/effect integration remains subject to the capability/effect research in issue [#222](https://github.com/DavidFernee/Capstan/issues/222).

## 2. Baseline audit and verified gaps

The repository's runtime-boundary inventory and v0.6 standard-library review establish the following baseline:

| Area | Current documented/implemented surface | A1 gap |
|---|---|---|
| Filesystem | Path-string `read_file` / `write_file`, path validation and bounded reads | Ambient path authority; no public directory capability, owned file handle, handle-relative traversal, structured error or atomic-write contract |
| Streams | Standard input/output helpers and byte/line reads | No common partial-progress, readiness, cancellation, deadline or ownership contract |
| Process | `run()` is a demonstration sink; runtime inventory has no child create/wait/reap/cancel API | A1-P needs an explicit executable grant, process handle, lifecycle and descendant policy |
| Sockets | No general network/socket capability API identified | A1-H needs a connected Unix stream, nonblocking readiness, and descriptor passing |
| Descriptor transfer | No public typed descriptor/handle-transfer contract identified | Wayland `SCM_RIGHTS` needs bounded send/receive, ownership and malformed-control handling |
| Shared memory | Generic mapping appears in T6 planning | Initial Wayland path can avoid client `mmap`; it needs bounded anonymous backing, exact sizing and offset writes |
| Clock | Shroud S1 requires host-sampled monotonic time | No common monotonic clock capability/deadline contract identified |
| Errors | Several existing I/O builtins collapse failures to `none` / `bool`; `Result<T,E>` remains a compiler/type-system dependency | Stable typed errors and cancellation/timeout distinctions are prerequisites |
| Capabilities/effects | Stage 6 of the language-extension roadmap specifies explicit capabilities and effect signatures | No approved, versioned external-I/O capability API is established by the inspected documents |

The T6 system-call roadmap's current list (`open`, `read`, `write`, `exit`, memory mapping and signals) is insufficient for the initial Wayland client. The existing [#224 acceptance scope](https://github.com/DavidFernee/Capstan/issues/224) also calls for checked `mmap`/`munmap` semantics as part of the broader host substrate. The Shroud Wayland prerequisites additionally require Unix-domain sockets, `SCM_RIGHTS`, readiness waits, anonymous shared-memory backing and monotonic time. The initial shm vertical slice should use `memfd` + `ftruncate` + `pwrite`, so client-side `mmap` need not block that first path; generic mapping remains a separately gated T6 deliverable.

These findings are a documentation/source audit, not proof that no experimental implementation exists anywhere in an uninspected branch. Before freezing API signatures, the runtime/T6 owner must reconcile this gap list against the active implementation branch and syscall inventory.

## 3. Architectural layers and ownership

1. **Capstan language/runtime core:** capability values, rights attenuation, effect checking, handle ownership, limits, state machines, typed error mapping, buffering policy, protocol-independent validation and resource accounting.
2. **Capstan service libraries:** filesystem operations, stream abstractions, process supervision, Unix socket transport, shared-memory object management and monotonic deadline utilities. These are written in Capstan.
3. **Minimal platform ABI:** OS entry points only: create/connect sockets, send/receive bytes and ancillary descriptors, wait for readiness, create/size/write anonymous backing objects, sample monotonic time, and (for A1-P) create/wait/terminate processes. It converts native results to a closed platform-result representation. It does not implement Anchor policy, Wayland framing, LSP framing, shell parsing or capability issuance.
4. **OS/kernel/compositor/child process:** external, fallible and untrusted. All data and metadata returned from these boundaries are validated and bounded.

The final A1 implementation must be Capstan-native. Any temporary C/assembly bootstrap entry points must be enumerated in the trusted-base inventory, kept to ABI marshalling, tested independently and removed from the claimed C-free release path. No generated-C runtime, private C process launcher or shell wrapper is an acceptable end state.

## 4. Capability model

Capabilities are opaque, non-forgeable authority values. Their representation is runtime-private and cannot be constructed from an integer, path string, PID, descriptor number or serialized workspace value.

Conceptual capability families (names are descriptive, not proposed final declarations):

| Capability | Authority represented | Must not imply |
|---|---|---|
| Directory root | Relative traversal and selected operations beneath one opened root | Access to another directory, symlink escape, process execution |
| File handle | Operations on one opened object with explicit rights | Authority to reopen its path or access siblings |
| Stream endpoint | Bounded byte input/output on one endpoint | Read/write to arbitrary process streams |
| Socket endpoint | Connect to one selected endpoint or communicate over one connected socket | Arbitrary network, filesystem or display access |
| Descriptor-transfer right | Transfer an explicitly listed transferable handle over an authorised socket | Transfer of every handle held by the process |
| Shared-memory object | Create/size/write/read a bounded anonymous backing object | Arbitrary mappings or unbounded memory allocation |
| Monotonic clock | Read monotonic time and derive deadlines | Wall-clock authority or permission to change time |
| Executable grant | Launch one pinned executable under an approved invocation profile | Arbitrary executable lookup or shell execution |
| Process handle | Observe/control one process tree owned by the supervisor | Authority inferred from a PID or control of unrelated processes |

### 4.1 Rights and attenuation

Rights are explicit and minimal (for example, read, write, enumerate, connect, send, receive, transfer, resize, wait, terminate). A derived capability may only preserve or reduce its parent's authority. It cannot add rights, widen a root, increase a budget or change an executable identity.

The runtime must define:
- capability creation/issuance authority and trusted entry-point policy;
- whether capabilities are affine/linear, move-only or explicitly clonable;
- borrow lifetime and invalidation rules;
- revocation semantics and behaviour of outstanding operations;
- owner/child relationships and shutdown ordering;
- whether a capability may cross task/thread boundaries;
- how capability provenance is represented for audit without exposing secrets.

A copyable integer wrapper is not an acceptable opaque capability. A raw descriptor/PID conversion is forbidden in ordinary Capstan code.

### 4.2 Handle identity and lifetime

Every owned handle has one logical identity and one owner. Close/drop is idempotent at the public boundary but the underlying resource is released exactly once. Use-after-close, stale-generation use, double transfer, and use after owner shutdown produce typed failures, never undefined behaviour.

A received OS descriptor is a new receiver-side handle with independent ownership. Sending a descriptor does not silently consume the sender's handle. If an API offers move-transfer, that is a distinct operation with explicit success/uncertainty semantics. On receive, every accepted descriptor is validated against the receiving capability policy; malformed, excess or unclaimed descriptors are closed on every path.

## 5. Common I/O operation semantics

All byte-oriented I/O operations share one result model. Final type names are deferred until the language's `Result<T,E>` contract is approved.

A read result distinguishes:
- positive byte progress;
- end-of-stream (not an error);
- would-block (requires readiness or another event, never busy-loop);
- interruption (retry only where operation semantics permit);
- cancellation;
- deadline expiry;
- peer closure/reset;
- permission/capability failure;
- resource/limit exhaustion;
- other platform I/O failure.

A write result reports positive partial progress. A zero-byte write while bytes remain is no progress and must not be treated as success. Callers must handle short writes. The API never promises that a write is atomic unless a specific operation and platform contract prove it.

Required invariants:
- byte counts and offset arithmetic are checked before OS entry;
- every buffer, queue, message, descriptor list and retained output has a configured upper bound;
- every potentially blocking operation has a cancellation and/or monotonic-deadline policy;
- no operation silently retries forever;
- `EINTR`/equivalent handling is operation-specific and bounded by the same deadline;
- would-block transitions to a readiness wait, not polling in a tight loop;
- EOF, peer close, timeout and cancellation remain distinguishable;
- native error numbers are diagnostic metadata, not the only application-visible error type;
- no OS-provided error string is trusted for formatting, UI labels or logs.

### 5.1 Readiness and event-loop integration

The initial A1-H host is single-threaded. It needs a bounded readiness-wait primitive over a finite set of owned handles, with read/write/error/hangup interest and a monotonic deadline. It must report each ready handle by opaque identity/generation, not a reusable raw descriptor number.

The wait operation must:
- accept a finite, bounded handle set;
- use a monotonic timeout/deadline;
- distinguish readable, writable, hangup and error conditions;
- handle interruption without extending the absolute deadline;
- reject stale/closed handles;
- return promptly on cancellation or owner shutdown;
- avoid hidden worker threads and implicit scheduling.

This is sufficient for the first Shroud event loop. Do not add epoll/eventfd/timerfd or a general async runtime merely because they may be useful later; profile and specify them separately.

### 5.2 Deadline contract

A deadline is an absolute value in one monotonic clock domain. Relative durations are converted with checked arithmetic. Wall-clock timestamps, compositor timestamps, LSP payloads and application model values cannot control timeouts or Shroud activation guards.

Clock readings must be nonnegative and nondecreasing within a clock instance. A regression, overflow, suspend/resume discontinuity or clock failure is an explicit error; security-sensitive timing fails closed. Tests require a deterministic fake clock provider, but production code cannot select a caller-controlled clock for authorization decisions.

## 6. Filesystem authority required by Anchor

A path is a name, not authority. The A1 document/workspace service must be rooted in an explicitly issued directory capability.

Minimum requirements:
- relative path components with a specified encoding and NUL policy;
- handle-relative traversal from the granted root;
- explicit no-follow/symlink policy for each component;
- object-type validation after open, not only before open;
- no string-prefix confinement checks;
- no check-then-open security decision;
- bounded directory enumeration and file sizes;
- explicit read/write/create/replace rights;
- atomic-save semantics specified separately (temporary object, flush/durability policy, rename scope and failure recovery);
- explicit treatment of hard links, mount points, reparse points and platform-specific identity guarantees;
- no implicit current-directory or ambient home-directory fallback.

The existing path-string builtins do not meet this contract. They may remain for compatibility under their current documented limits, but Anchor's security boundary must not be built on them or describe `validate_path()` as confinement.

## 7. Socket and descriptor-transfer requirements for Shroud

A1-H initially needs one selected Unix-domain stream endpoint and its connected socket. The display endpoint is explicitly supplied by a trusted host/session provider; Shroud must not call `getenv`, search `WAYLAND_DISPLAY`/ `XDG_RUNTIME_DIR`, or resolve arbitrary filesystem paths itself.

The socket contract must support:
- nonblocking connect with completion checked through the socket error state (writability alone is not success);
- bounded send and receive with partial progress;
- readiness wait with finite monotonic deadline;
- close-on-exec by default;
- explicit no-SIGPIPE behaviour for writes;
- ancillary descriptor send/receive with a bounded descriptor count and control-buffer size;
- detection of truncated payload/control data;
- close-on-exec on received descriptors;
- validation and closure of malformed, unexpected or excess received descriptors;
- explicit handling of partial stream writes when ancillary data accompanies a byte offset;
- no conversion of descriptors to ordinary integers or pointer arithmetic on descriptors.

The compositor and every message/descriptor received from it are untrusted. A display connection grants communication with that compositor only. It does not grant filesystem, process, clipboard, network or arbitrary descriptor authority.

## 8. Shared-memory object requirements for the first Wayland path

The first S1 presentation path uses an anonymous bounded backing object rather than client-side mapping:

1. validate width, height, stride and total bytes using overflow-safe arithmetic;
2. create a close-on-exec anonymous backing object;
3. set its exact length before use;
4. populate frame bytes using offset writes with explicit partial-progress handling;
5. transfer the descriptor only in the approved Wayland protocol operation;
6. track compositor release before reusing or destroying a buffer;
7. close all local/received resources on every failure and shutdown path.

The shared-memory API must enforce:
- maximum object size and aggregate host pixel/buffer budget;
- checked offset + length within the declared object size;
- no implicit extension beyond the approved size;
- explicit resize/seal policy;
- separate accounting for Shroud pixmap, staging copy, shared backing and in-flight compositor buffers;
- no reuse while the compositor still owns a buffer;
- typed failure for allocation, sizing, writing, transfer or release errors.

This requirement does not make generic `mmap` a prerequisite for A1-H. Generic virtual-memory services remain part of the broader C-free runtime programme and must be designed independently.

## 9. Process service relationship (A1-P)

Process creation is a distinct capability family and must not be smuggled into generic stream or socket authority. A1-P builds on the common handle, error, budget and deadline semantics, then adds:
- pinned executable grant and structured argv;
- explicit working-directory grant and minimal environment profile;
- explicit stdin/stdout/stderr endpoints;
- process handle and lifecycle state machine;
- bounded output pumps and backpressure;
- cancellation, confirmed termination and reaping;
- descendant containment and per-platform guarantee reporting.

The detailed policy and acceptance criteria are in `docs/ANCHOR-PROCESS-SUPERVISION.md`. A1-H does not depend on process creation. A1-P can be tested headlessly. No `system()`, `popen()`, shell string, implicit PATH search or private C launcher.

## 10. Typed errors and resource budgets

The public contract needs a closed, versioned error taxonomy at minimum covering:
- invalid argument/encoding;
- missing, revoked or insufficient capability;
- stale/closed handle;
- not found / wrong object type;
- permission denied;
- would-block / interrupted;
- end-of-stream / peer closed;
- deadline exceeded / cancelled;
- resource exhausted / configured limit exceeded;
- unsupported operation or platform guarantee;
- protocol violation / malformed ancillary data;
- platform I/O failure;
- partial initialization / cleanup failure.

Do not encode EOF as a generic failure. Do not collapse permission, missing, timeout, cancellation and limit exhaustion into `false` or `none`. Platform error codes may accompany a stable category for diagnostics.

Budgets are explicit and compositional. At minimum, account for:
- open handles and descriptors;
- outstanding operations and readiness registrations;
- bytes per read/write and aggregate queued bytes;
- message/frame size and ancillary descriptor count;
- directory entries and file bytes;
- shared-memory object size, aggregate buffers and in-flight frames;
- process count, descendants, runtime and stdout/stderr bytes;
- deadline and cancellation grace period.

A child service cannot increase a parent budget. Reservation occurs before resource acquisition; failed acquisition rolls back; release happens exactly once. Distinguish hard-enforced limits from best-effort observations and unsupported limits per target.

## 11. Formal and assurance obligations

The capability-I/O contract should be added to the formal-verification roadmap as a separate semantic layer after the scalar/heap substrate is ready. Do not claim the current CCAM evaluator models I/O; its documented machine subset explicitly excludes I/O and capabilities.

Required properties for the future model and implementation:
1. **Authority confinement:** an operation can affect only objects reachable through capabilities held by the caller.
2. **Monotone attenuation:** derived capabilities never exceed parent rights or budgets.
3. **No forgery:** application values cannot be converted into authority.
4. **Lifetime safety:** closed, transferred or revoked handles cannot be used as live handles.
5. **Accounting conservation:** successful acquisitions reserve once and terminal release restores the budget exactly once.
6. **Bounded progress:** every blocking operation has a finite deadline/cancellation path and cannot busy-loop on would-block.
7. **Result fidelity:** EOF, partial progress, timeout, cancellation, permission failure and peer failure are observably distinct.
8. **Descriptor hygiene:** no unapproved descriptor is inherited or accepted; malformed ancillary data is closed.
9. **No ambient authority:** operations do not consult implicit cwd, environment, PATH, display variables or proxy state.
10. **Failure atomicity:** partial construction does not publish a usable capability or leak resources.

Proof assumptions must name the platform ABI, kernel semantics and trusted issuer. The proof boundary cannot silently treat the OS or compositor as verified.

## 12. Conformance and adversarial test plan

Build a shared capability-I/O conformance suite before Anchor/Shroud consume the API.

| Test group | Required cases |
|---|---|
| Capability | Forged integer/path/PID rejected; attenuation cannot add rights; revoked/closed/stale handles rejected; clone/move rules tested |
| Ownership | Close/drop exactly once; failed open/connect rollback; owner shutdown closes children; transferred descriptor has independent receiver ownership |
| Read/write | Short reads/writes, zero progress, EOF, peer close, interruption, would-block, broken pipe, malformed counts |
| Readiness | simultaneous readiness, hangup/error, deadline expiry, cancellation, stale handle generation, interrupted wait without deadline extension |
| Deadline | monotonic regression, conversion overflow, fake-clock determinism, no wall-clock dependency |
| Filesystem | symlink and parent traversal, race replacement, hard links, mount/reparse points, wrong type, root escape, oversized files, atomic-save crash points |
| Socket/FD passing | descriptor count caps, malformed/truncated ancillary data, unexpected FDs, CLOEXEC, partial send with FD, peer disconnect during transfer |
| Shared memory | size overflow, one-over-budget, partial pwrite, offset overflow, resize denial, in-flight reuse, release and cleanup races |
| Process | argv/environment pinning, launch/cancel races, descendant escape, output floods, exact reaping and accounting; see process RFC |
| Robustness | fuzz public decoders and state machines; inject every platform error at every acquisition/cleanup boundary |

Every test report must identify exact source revision, target, ABI adapter revision, compiler version, test corpus and result. A passing mock backend is not evidence that Linux/Windows/macOS kernel semantics are correct.

## 13. Sequencing and ownership

1. **Runtime/T6 owner (existing issue [#224](https://github.com/DavidFernee/Capstan/issues/224)):** reconcile this delta with the actual syscall and platform-ABI implementation; publish the minimal operation inventory and capability/effect design. This document is a cross-workstream requirements synthesis for that issue, not a duplicate implementation ticket.
2. **Language/type-system owner:** approve capability value semantics, effects, `Result<T,E>`, ownership/borrowing and error representation. Do not create a temporary incompatible API.
3. **Runtime/security owner:** approve rights attenuation, issuer policy, handle lifetime, budgets and revocation.
4. **Shroud owner:** confirm the Wayland vertical slice against the socket, descriptor-transfer, shared-memory and clock requirements in sections 7–8.
5. **Anchor owner:** confirm workspace filesystem and process-service requirements against sections 6 and 9.
6. **Assurance owner:** add the state-machine and resource-accounting properties to formal/conformance work before implementation claims.

Implementation order: capability/error/limit semantics → opaque handle and ownership core → monotonic clock and readiness wait → bounded stream/socket I/O and descriptor passing → shared-memory object → directory/file capability → process service → Anchor integration. A1-H and A1-P can diverge after the shared foundations; neither may fork the public contract.

## 14. Exit gate

This specification is ready to become an approved API only when maintainers have:
- reconciled the baseline against the current T6/T7 implementation and syscall list;
- approved the capability issuer, rights, attenuation, ownership and revocation semantics;
- approved the effect and `Result<T,E>` integration;
- approved per-operation blocking, cancellation, deadline and resource-budget rules;
- approved Unix descriptor-transfer and shared-memory semantics for A1-H;
- approved executable/process authority and lifecycle semantics for A1-P;
- identified exact C-free target ABI coverage and any temporary bootstrap boundary;
- assigned conformance, fuzzing and formal-assurance ownership.

Until then, this is a requirements delta, not an implementation authorization. Anchor and Shroud must not invent private APIs or use raw OS handles to move ahead.
