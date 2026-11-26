# Capability-I/O host API v0.1 — Shroud Linux/Wayland profile

**Status:** versioned API contract candidate for review; not an approved public declaration or implementation  
**Contract ID:** capstan-host-io/0.1  
**Target profile:** linux-unix/0.1, initially x86-64 and AArch64 little-endian  
**Parent:** [Shroud Linux/Wayland prerequisites](SHROUD-LINUX-WAYLAND-PREREQUISITES.md)  
**Shared requirements:** [Anchor capability-I/O requirements](../ANCHOR-CAPABILITY-IO-REQUIREMENTS.md), [Shroud S1 host contract](../SHROUD-HOST.md)  
**Issue:** [#224](https://github.com/DavidFernee/Capstan/issues/224)

## 1. Purpose and status

This document supplies the missing concrete API contract and deterministic mock-host contract for the first Shroud S1 Linux/Wayland host substrate. It is a versioned semantic contract candidate, not compilable Capstan source, an approved standard-library declaration or a syscall implementation.

The contract is deliberately layered:

- Capstan source owns capability values, ownership, state machines, bounded protocol parsing, event normalization and UI policy.
- A shared Capstan host-I/O API owns opaque handles, byte progress, readiness, descriptor transfer, shared-memory objects, deadlines and typed errors.
- A minimal target-specific ABI module performs kernel entry and exact ABI marshalling only.
- The deterministic mock backend implements the same host-I/O contract without invoking the host OS.

The API does not expose raw descriptors, descriptor integers, raw pointers, arbitrary syscall numbers, ambient paths or environment lookups. An effect describes an operation; a capability supplies the authority to perform it. Declaring an effect never manufactures authority.

### 1.1 Non-goals

- No Wayland protocol implementation in the ABI module.
- No native window, event pump, XKB/IME or AT-SPI implementation.
- No general process API; Anchor A1-P remains a separate capability family.
- No generic asynchronous runtime, epoll/eventfd/timerfd or worker-thread abstraction.
- No C-free or verified-syscall claim.
- No final Capstan source syntax until opaque type, ownership, effect and Result semantics are approved by the language/runtime owners.

## 2. Versioning and compatibility

The contract identifier is capstan-host-io/0.1. The Linux binding profile is linux-unix/0.1.

A conforming implementation records:
- contract ID and revision;
- target ABI profile and architecture;
- capability-kind and error-enum versions;
- maximum values for every configured byte, handle, descriptor, queue and deadline dimension;
- implementation identity and exact source revision.

A change to capability meaning, ownership/transfer semantics, error classification, partial-progress semantics, deadline interpretation or resource accounting requires a new minor/major contract version as appropriate. A new syscall binding that preserves all observable semantics may be a platform-profile revision, but must still be recorded in provenance.

Unknown capability kinds, operation tags, error variants and contract versions fail closed. Implementations must not reinterpret unknown fields as defaults.

## 3. Abstract public types

The following names define semantic types, not current Capstan declarations.

| Type | Kind and authority | Ownership rule |
|---|---|---|
| DisplayEndpoint | Opaque authority to connect to one host-selected Unix-domain display endpoint | Issued only by a trusted host/session provider; not constructible from a path or environment variable |
| DisplayConnection | One connected Unix stream with bounded send/receive/readiness rights | Owned handle; close consumes the owner; no raw descriptor conversion |
| TransferableHandle | An explicitly transferable owned handle, initially restricted to approved shared-memory objects | Sender retains its own handle; transfer creates a receiver-side descriptor; only approved kinds may be sent |
| ReceivedHandle | Receiver-owned opaque handle returned by validated ancillary-data processing | New owner; validated against expected kind and grant before use |
| SharedMemoryAuthority | Authority to create bounded anonymous backing objects under a byte ceiling | Issuer-supplied; attenuation may reduce size ceiling, never increase it |
| SharedMemoryObject | Owned anonymous backing object with exact declared size and bounded offset I/O | Owned handle; no ambient path; no implicit resize |
| MappedRegion | Opaque mapping of a bounded range of one SharedMemoryObject | Lifetime tied to the backing object; no raw pointer exposure; unmap consumes the mapping |
| MonotonicClock | Read-only authority to sample one monotonic clock domain | Issuer-supplied; cannot set time or choose wall clock |
| Deadline | Absolute monotonic instant plus clock-domain identity | Immutable value; never accepted from untrusted event payload as an authorization clock |
| DirectoryRoot | Separate authority for relative font/configuration reads beneath one opened root | Not implied by DisplayEndpoint or DisplayConnection |
| HostError | Closed stable error taxonomy | Native error numbers are optional diagnostic metadata only |
| Outcome<T,E> | Semantic success/error sum: Ok(T) or Err(E) | Carries exactly one terminal result; partial-progress operations use their own result variants |
| OwnedHandle | Closed union of runtime-private owned resource handles | Cannot be cloned or converted to a descriptor integer |
| ResourceId | Opaque diagnostic identity for a resource whose release outcome is ambiguous | Not authority; cannot be used to reopen or operate on the resource |
| MonotonicInstant | Nonnegative monotonic value plus clock-domain identity | Immutable; comparable only within the same clock domain |
| RelativePath / FileRights / FileHandle | Root-relative filesystem name, requested rights and one opened file | Exists only under a separately issued DirectoryRoot |

### 3.1 Capability/effect separation

The operation catalogue declares abstract effects separately from required authority:

| Operation family | Effect label | Required capability |
|---|---|---|
| Connect | host.socket.connect | DisplayEndpoint |
| Send/receive | host.socket.send, host.socket.receive | DisplayConnection |
| Readiness wait | host.wait | DisplayConnection |
| Create/size shared backing | host.shm.create, host.shm.resize | SharedMemoryAuthority / SharedMemoryObject |
| Offset read/write | host.shm.read, host.shm.write | SharedMemoryObject |
| Descriptor transfer | host.fd.transfer | DisplayConnection plus explicit TransferableHandle list |
| Map/unmap | host.memory.map, host.memory.unmap | SharedMemoryObject and mapping rights |
| Clock sample | host.clock.read | MonotonicClock |
| Close | host.resource.close | Owned handle being closed |
| Font/config read | host.fs.read | DirectoryRoot, separately issued |

An effect annotation states that a computation may perform an operation. The capability argument is the authority required to perform it. Neither is inferred from the other. A handler or adapter is trusted only to the extent that all relevant OS paths are forced through it.

## 4. Error model

The API uses a closed sum type called HostError. Final source syntax may use the future standard Result<T,E>; the semantic distinction is required now.

| Error variant | Meaning | Retry rule |
|---|---|---|
| invalid_argument | Invalid size, offset, flag, handle combination or encoding | No retry without changing input |
| invalid_capability | Forged, wrong-kind, stale-generation or revoked capability | No |
| permission_denied | Capability exists but lacks the required right/scope | No |
| not_found | The scoped relative object does not exist | No unless the caller explicitly retries after a separate creation event |
| wrong_object_type | The opened object is not the required file/directory/socket kind | No |
| already_exists | A create-exclusive operation found an existing object | No unless the caller changes the requested operation |
| resource_exhausted | Kernel or configured resource ceiling reached | Only after a separately observable release/retry condition |
| limit_exceeded | Requested bytes, descriptors, queue entries or mapping exceed an explicit ceiling | No; caller must reduce request |
| would_block | Nonblocking operation cannot currently make progress | Wait for readiness; never busy-loop |
| interrupted | Operation interrupted before progress | Retry only under the operation-specific deadline policy |
| timed_out | Absolute monotonic deadline expired | No, unless caller supplies a new deadline |
| cancelled | Owning task/operation was cancelled | No; cleanup is still required |
| peer_closed | Peer closed/reset or hangup makes further I/O unavailable | No on this connection |
| protocol_violation | Truncated, malformed or unexpected data/ancillary descriptor | No; close invalid resources and fail the connection if required |
| unsupported | Operation not provided by this target/profile | No |
| platform_failure | Other OS/ABI failure | Retry only if a specific stable code is documented as retryable |
| cleanup_failure | Resource release failed or outcome is platform-ambiguous | Resource enters terminal/poisoned state; never silently reuse |

HostError may carry a bounded operation identifier and optional numeric platform code. It must not rely on an OS error string for program control flow or UI output.

Linux mapping is operation-sensitive but must preserve these stable categories: EAGAIN/EWOULDBLOCK maps to would_block; EINTR to interrupted unless retried internally under the original deadline; ETIMEDOUT to timed_out; ECONNRESET/EPIPE/ENOTCONN to peer_closed; EACCES/EPERM to permission_denied; EBADF to invalid_capability or stale/closed handle; ENOMEM/ENFILE/EMFILE/ENOBUFS to resource_exhausted; EOVERFLOW to limit_exceeded; EINVAL to invalid_argument. Filesystem ENOENT/ENOTDIR/ELOOP map to not_found/wrong_object_type/permission_denied according to the operation and must not reveal paths outside the DirectoryRoot.

EOF is distinct from failure. Partial progress is distinct from both. A timeout is distinct from cancellation. A limit rejection is distinct from kernel resource exhaustion.

## 5. Common progress and deadline semantics

### 5.1 Byte progress

Every byte-stream send/receive result reports exact positive progress. A zero-byte write while bytes remain is not success. A caller must not assume a full read/write unless the specific operation guarantees it.

Conceptual records:
- IoProgress { bytes: Nat }
- SendReceipt { bytes_committed: Nat, descriptors_committed: Bool }
- ReceiveBatch { bytes: ByteString, handles: List<ReceivedHandle>, handles_offset: Nat }
- ReadResult ::= Data(ByteString) | EndOfStream
- ReceiveResult ::= Batch(ReceiveBatch) | EndOfStream | Pending
- WriteResult ::= Complete(IoProgress) | Pending(IoProgress) | Failed(HostError, IoProgress)

The handles_offset in ReceiveBatch is a zero-based offset within the returned bytes slice at which the ancillary descriptor set is associated. It is not an OS descriptor or pointer.

### 5.2 Absolute deadlines

All blocking-capable operations take an optional finite Deadline. A Deadline is an absolute monotonic instant, not a relative timeout silently restarted after each EINTR or partial transfer.

- Relative durations are converted to absolute deadlines with checked arithmetic.
- EINTR handling recomputes remaining time from the same monotonic clock.
- A would-block result transitions to readiness wait.
- A timeout never extends itself after partial progress.
- A clock regression, invalid clock-domain identity or conversion overflow returns a failure and fails closed for guard/security decisions.
- Infinite waits are not available in the initial safe profile.

### 5.3 Resource admission

Every operation preflights all relevant dimensions before allocation or side effect:
- payload bytes;
- queued bytes;
- descriptor count;
- handle count;
- shared-memory object bytes;
- aggregate in-flight buffer bytes;
- mapping count and mapped bytes;
- wait-set size.

Cumulative counters (bytes read/written) are monotonic and are not released. Live counters (open handles, live backing objects, mappings and in-flight buffers) are reserved and released exactly once. A failed multi-dimensional reservation changes no counter. The child operation cannot increase its caller's ceilings.

## 6. Operation catalogue

The following signatures are semantic pseudocode. They define argument/return meaning and ownership, not compilable source syntax.

### 6.1 Display endpoint and connection

connect_display(endpoint: DisplayEndpoint, deadline: Deadline) -> Outcome<DisplayConnection, HostError>

- Connects only to the endpoint selected by the issuer.
- Uses a Unix-domain stream socket in the Linux profile.
- The endpoint does not expose a path string to the caller.
- The returned connection is nonblocking and close-on-exec.
- Completion of a nonblocking connect is verified using the socket error state; writability alone is not success.
- On failure, any partially created descriptor is closed before returning.
- The result is one owned connection; no raw integer descriptor is returned.

### 6.2 Sending bytes and descriptors

send_frame(connection: DisplayConnection, bytes: ByteString, handles: List<TransferableHandle>, deadline: Deadline) -> SendResult

SendResult ::= Complete(SendReceipt) | Pending(PendingSend, SendReceipt) | Failed(HostError, SendReceipt)

PendingSend is an opaque, owned continuation containing the remaining bytes, exact byte offset, descriptor-transfer state and connection generation. It can be resumed only on the same connection.

Rules:
- The first successful sendmsg that transfers ancillary descriptors marks descriptors_committed exactly once. This means the local kernel accepted the descriptor control message for transmission; it does not prove that the peer application has received or accepted the descriptors.
- If the first send makes no progress and transfers no descriptors, a retry may still include them.
- Once descriptors_committed is true, every retry sends remaining bytes without reattaching descriptors.
- Partial bytes are never resent.
- Sender ownership of each original handle remains unchanged; SCM_RIGHTS creates receiver-side descriptor ownership.
- A PendingSend cannot be cloned, replayed on another connection or resumed after connection close.
- The operation never claims that the complete Wayland frame was delivered merely because the descriptor control message was accepted. Every result, including failure, preserves the exact byte and descriptor progress so a caller cannot accidentally resend a committed descriptor or duplicate bytes.

This stateful contract avoids duplicate descriptor transfer after a short send or would-block.

### 6.3 Receiving bytes and descriptors

receive_batch(connection: DisplayConnection, max_bytes: Nat, max_handles: Nat, deadline: Deadline) -> Outcome<ReceiveResult, HostError>

Rules:
- The operation uses close-on-exec semantics for every received descriptor.
- It rejects payload/control truncation.
- It validates descriptor count and allowed handle kinds before publishing the batch.
- Every excess, malformed, unexpected or unclaimed descriptor is closed on all error paths.
- A descriptor batch is associated with the exact stream offset returned in ReceiveBatch.
- A protocol parser must not attach descriptors to a different frame because of buffering or partial reads.
- An orderly peer shutdown with no bytes is returned as EndOfStream, not as an empty successful message. A reset/error is HostError.peer_closed.

### 6.4 Readiness wait

wait_ready(connection: DisplayConnection, interest: Readable | Writable | Either, deadline: Deadline) -> Outcome<ReadyState, HostError>

- Linux binding uses poll or ppoll in the first profile.
- ReadyState distinguishes readable, writable, hangup and error.
- EINTR is handled against the original absolute deadline.
- A closed/stale connection is rejected.
- The initial API accepts a bounded set of handles only if a later version adds multi-handle wait; v0.1 is one connection per call.
- No busy-loop or implicit background thread is permitted.

### 6.5 Shared-memory object

create_shared_memory(authority: SharedMemoryAuthority, byte_length: Nat) -> Outcome<SharedMemoryObject, HostError>

- Creates anonymous backing, close-on-exec, with a checked exact size.
- byte_length must be positive and within both per-object and aggregate live-byte limits.
- Linux uses memfd_create followed by ftruncate.
- The object has no filesystem path and cannot be reopened by name.
- The authority determines the maximum size and whether descriptor transfer is permitted.

write_at(object: SharedMemoryObject, offset: Nat, bytes: ByteString, deadline: Deadline) -> WriteResult

read_at(object: SharedMemoryObject, offset: Nat, max_bytes: Nat, deadline: Deadline) -> Outcome<ReadResult, HostError>

- offset + length is checked before kernel entry.
- Access outside the exact declared object size is rejected.
- Short progress is explicit; the caller must resume at the returned offset.
- No implicit extension, sparse growth or resizing occurs through write_at.
- For the first Wayland profile, write_at uses pwrite; it does not require client mmap.

### 6.6 Checked mapping

map_region(object: SharedMemoryObject, offset: Nat, length: Nat, access: ReadOnly | ReadWrite) -> Outcome<MappedRegion, HostError>

unmap_region(region: MappedRegion) -> UnmapOutcome

UnmapOutcome ::= Unmapped | Failed(HostError, MappedRegion) | Poisoned(HostError, ResourceId)

- offset and length are nonzero/range checked; offset alignment is checked against the target page size.
- offset + length must fit inside the object's declared size and the caller's mapping-byte budget.
- Execute permission is never available; W+X is forbidden.
- The region is opaque. Ordinary code receives bounded copy_from/copy_to operations, not a raw pointer or integer address.
- A mapping retains the backing object until successful unmap.
- A mapping cannot outlive its backing capability; close of a mapped backing object is rejected or deferred until all mappings are released.
- unmap consumes the mapping on success. On failure, the runtime returns the still-owned mapping with the error, or moves it to a documented poisoned terminal state; it must never silently mark a still-live mapping as released.
- Mapping is part of the broader T6 profile, not required for the first Wayland memfd+pwrite path.

### 6.7 Monotonic clock

monotonic_now(clock: MonotonicClock) -> Outcome<MonotonicInstant, HostError>

- Linux binding uses clock_gettime(CLOCK_MONOTONIC).
- The result is a nonnegative, normalized seconds/nanoseconds pair or a checked monotonic integer unit.
- Conversion to milliseconds/nanoseconds is overflow checked.
- The runtime records the last value per clock identity and rejects regressions.
- Wall-clock time, event timestamps and caller-selected time sources cannot substitute for this capability.

### 6.8 Close and ownership

close_handle(handle: OwnedHandle) -> CloseOutcome

CloseOutcome ::= Closed | CloseFailed(HostError, ResourceId)

CloseOutcome distinguishes successfully closed from close failure/terminal ambiguity. The public handle is invalidated exactly once regardless of whether the platform reports an error after the underlying resource may have been released. A closed handle can never be reused by stale identity or descriptor-number reuse.

The sender's handle remains owned after SCM_RIGHTS send. The receiver's accepted descriptor is a distinct owned ReceivedHandle. An API that wants move semantics must explicitly consume the sender handle in a separate operation with its own failure/uncertainty result.

### 6.9 Separate filesystem authority

open_relative(root: DirectoryRoot, relative_path: RelativePath, rights: FileRights) -> Outcome<FileHandle, HostError>

This is not a display capability operation. The root is separately issued for fonts/configuration. Traversal is handle-relative; no cwd, environment or string-prefix security decision is allowed. The detailed filesystem contract belongs to the shared capability-I/O standard and must be reconciled with Anchor before final API adoption.

## 7. Linux ABI inventory

The ABI module contains only kernel entry, argument/result marshalling and native error conversion. It does not parse Wayland protocol messages, select UI actions, manage widgets or decide capability policy.

| ABI operation | API operation | Required handling |
|---|---|---|
| socket(AF_UNIX, SOCK_STREAM, flags) | connect_display | Nonblocking/CLOEXEC; close on all failed paths |
| connect | connect_display | Bounded endpoint representation; EINPROGRESS state |
| getsockopt(SO_ERROR) | connect_display | Verify connection completion; typed platform failure |
| fcntl or socket flags | connection setup | Only approved flag transitions; no arbitrary descriptor mutation |
| sendmsg | send_frame | Bounded iovec/control data; SCM_RIGHTS; MSG_NOSIGNAL; exact partial-progress state |
| recvmsg | receive_batch | Bounded buffers; MSG_CMSG_CLOEXEC; reject MSG_TRUNC/MSG_CTRUNC; close excess FDs |
| poll / ppoll | wait_ready | Finite timeout; EINTR recomputes against absolute deadline |
| memfd_create | create_shared_memory | CLOEXEC; bounded name; explicit sealing policy |
| ftruncate | create_shared_memory | Exact checked length before use |
| pwrite | write_at | Checked offset/length; short writes/EINTR; no implicit extension |
| pread | read_at | Checked range; short reads/EOF semantics |
| fstat | validate shared object | Metadata treated as untrusted and compared to declared limits |
| openat2 | open_relative | Handle-relative path resolution beneath DirectoryRoot; CLOEXEC; RESOLVE_BENEATH/NO_MAGICLINKS/NO_SYMLINKS where supported; no ambient cwd |
| read / write | bounded file/stream operations | Explicit partial progress, EOF, EINTR and error mapping; no unbounded buffers |
| mmap / munmap | map_region / unmap_region | Page alignment; range/protection checks; no executable or W+X mapping; exact ownership |
| clock_gettime(CLOCK_MONOTONIC) | monotonic_now | Nonnegative normalized value; overflow/regression checks |
| close | close_handle | Exactly-once logical close; terminal ambiguity documented |

The Linux profile must record its minimum kernel version and exact feature availability. A fallback to openat or another ABI is permitted only if it preserves the same handle-relative confinement and symlink semantics and is separately versioned/tested.

Not in the v0.1 Shroud host profile: epoll, eventfd, timerfd, ioctl, process creation, arbitrary filesystem open, arbitrary signals or raw memory-address conversion. Those require separate contracts and evidence.

## 8. Deterministic mock-host contract

The mock host is a deterministic implementation of the same semantic interface, not a mock of Linux syscall numbers. It must not invoke the host OS, inspect environment variables, read arbitrary files, use wall-clock time or expose host descriptors.

### 8.1 Mock state

A MockHost instance contains:
- a virtual monotonic clock with explicit advance and regression injection;
- a finite table of opaque endpoint, connection, shared-memory and mapping identities;
- a scripted peer byte stream and receive-queue;
- a scripted ancillary-descriptor queue with descriptor kinds and ownership;
- a MockWaylandPeer that can emit valid, fragmented, coalesced and malformed protocol messages with descriptors associated to selected byte offsets;
- per-operation resource ceilings and live/cumulative counters;
- a deterministic readiness schedule;
- an operation trace with sequence number, operation, capability identity, input length, result/progress and resource delta.

The mock returns the same HostError categories and progress records as the Linux backend. It does not invent success for unsupported operations.

### 8.2 Scriptable fault injection

The test harness must be able to schedule:
- connect success, refusal, EINPROGRESS, timeout and peer close;
- send/receive short progress, would-block, EINTR, zero progress, EOF and reset;
- ancillary descriptor delivery, excess descriptors, malformed control data, MSG_TRUNC and MSG_CTRUNC;
- memfd/ftruncate/pwrite/pread/fstat/mmap/munmap failure at each step;
- clock regression, conversion overflow and deadline expiry;
- resource-limit rejection before acquisition;
- close failure and owner cancellation during pending I/O.

Each injection is deterministic by operation sequence number, not random wall-clock timing. Fuzzing may generate scripts, but every failure is replayable from a saved seed and trace.

### 8.3 Required conformance suites

| Suite ID | Test | Required assertion |
|---|---|---|
| MOCK-01 | Capability forgery | Integers, paths and stale IDs cannot construct a capability |
| MOCK-02 | Attenuation | Derived rights/scope/byte ceiling never exceed parent |
| MOCK-03 | Connect lifecycle | Failed connect leaves no live connection or descriptor |
| MOCK-04 | Partial send with SCM_RIGHTS | Descriptor transfer is marked once; retry sends only remaining bytes |
| MOCK-05 | Partial receive with SCM_RIGHTS | Received descriptors remain associated with the exact returned stream offset |
| MOCK-06 | Ancillary truncation | All rejected/excess descriptors are closed; no batch is published |
| MOCK-07 | Readiness/deadline | EINTR does not extend absolute deadline; would-block never busy-loops |
| MOCK-08 | Shared-memory bounds | Exact limit succeeds; one byte over fails before allocation/resize |
| MOCK-09 | Mapping ownership | Out-of-range/misaligned/W+X maps fail; backing cannot close while mapped |
| MOCK-10 | Close and stale identity | Close consumes ownership once; descriptor-number reuse cannot revive old handle |
| MOCK-11 | Clock regression | Regression/overflow fails closed and resets guard-dependent host state |
| MOCK-12 | Failure cleanup | Every injected failure restores live counters or records an explicit poisoned resource |
| MOCK-13 | Ambient authority | No operation reads cwd, environment or arbitrary paths without a DirectoryRoot |
| MOCK-14 | Trace determinism | Identical script/inputs produce byte-identical operation traces and outcomes |
| MOCK-15 | Wayland header framing | Reject message sizes below 8 bytes, non-four-byte-aligned sizes, oversized frames and invalid object IDs/opcodes before allocation/dispatch |
| MOCK-16 | Fragmented/coalesced protocol stream | Correctly reassemble split headers/payloads and process multiple frames without losing byte or descriptor offsets |
| MOCK-17 | Descriptor-to-frame association | A descriptor delivered at a frame boundary is attached to that frame only; malformed/ambiguous association fails closed and closes the descriptor |
| MOCK-18 | Protocol object lifecycle | Reject unknown object IDs, illegal object transitions, duplicate IDs and unsupported interface versions |
| MOCK-19 | Protocol argument bounds | Reject oversized arrays/strings, invalid enums, malformed strings and aggregate queue/message limits before allocation |
| MOCK-20 | Malformed-frame cleanup | A malformed frame closes every unclaimed descriptor, releases temporary buffers and leaves no partially published object state |

### 8.4 What the mock does not prove

A passing mock suite establishes that Capstan clients and state machines obey the specified abstract host contract for the tested scripts. It does not prove:
- Linux kernel or compositor correctness;
- syscall ABI correctness;
- absence of kernel bugs or side channels;
- exact equivalence of every Linux errno/ancillary-data corner case;
- that a real C/assembly shim implements the mock contract.

A separate Linux conformance suite must run against the exact ABI adapter and target kernel, with the adapter revision recorded.

## 9. Staged implementation plan and language boundary

| Stage | Can be specified/tested now | Requires later platform/language support |
|---|---|---|
| H0 — semantic API | Capability kinds, error taxonomy, progress, deadlines, ownership and mock state machine | None beyond documentation |
| H1 — mock implementation | Deterministic mock host, fault scripts, conformance vectors and resource traces | Opaque/affine types may initially be simulated inside a test-only harness |
| H2 — capability values | Host-issued opaque handles and rights attenuation | Runtime representation, ownership/borrowing support and capability checking |
| H3 — byte/socket API | Partial progress, readiness, descriptor-transfer state machine | T6 Unix socket/sendmsg/recvmsg/poll ABI bindings |
| H4 — shared backing | Exact size, offset writes, release lifecycle | memfd_create/ftruncate/pwrite/fstat/close bindings |
| H5 — clock and deadlines | Virtual-clock tests and deadline arithmetic | CLOCK_MONOTONIC ABI binding and monotonic regression handling |
| H6 — generic mapping | Range/alignment/protection/ownership contract and mock tests | T6 mmap/munmap binding and safe opaque region access |
| H7 — Wayland host | Protocol framing/state machine in Capstan and mock peer tests | Real Linux socket, descriptor and shared-memory backend |
| H8 — other platforms | Contract reuse and platform-specific mock conformance | Separately audited Windows/macOS handle, socket, mapping and clock backends |

The API contract deliberately does not define final generic syntax or a public Result declaration. The language roadmap places explicit capabilities/effect signatures in Stage 6 and generic Result/error values in Stage 7. The runtime owner must reconcile these semantics with those stages before declarations are frozen. The semantic contract and mock can be reviewed now without pretending those language features already exist.

## 10. Trust boundary and release claims

- The issuer of DisplayEndpoint, SharedMemoryAuthority, MonotonicClock and DirectoryRoot is trusted to grant the intended initial scope.
- The ABI module is trusted for exact kernel entry and result marshalling until it is formally verified or independently audited.
- The kernel, compositor, peer process and received descriptors are untrusted.
- The Wayland parser and all buffer/object state machines are Capstan code and require bounded input, adversarial tests and later formal refinement.
- The mock host is a deterministic test oracle, not a security boundary.
- A passing mock suite is not a Linux ABI proof.
- A working Linux backend is not a C-free compiler or verified syscall layer.
- Windows/macOS support requires separate capability mappings and exact-head conformance; it cannot be inferred from Linux.

## 11. Exit gate for API adoption

The v0.1 candidate is ready for approval only after:
1. the capability/effect research decision preserves the separation between effects and authority;
2. the language/runtime owners approve opaque-handle, ownership, Result/error and attenuation semantics;
3. the T6 owner confirms the ABI inventory and target calling conventions;
4. the runtime/security owner approves descriptor-transfer and cleanup semantics;
5. the Shroud owner approves the Wayland-specific capability and shared-buffer lifecycle;
6. the deterministic mock suite has a runnable implementation and all listed vectors pass;
7. a real Linux conformance plan is assigned to the exact ABI adapter;
8. the C-free trusted-base inventory records every temporary platform boundary.

Until that gate is met, this is a reviewed contract candidate, not an approved shipped API or implementation.
