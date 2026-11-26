# Shroud S1 Linux/Wayland prerequisites

**Status:** proposed subsystem RFC; no API or implementation is shipped by this document.  
**Parent work:** Shroud S1 host contract, T6 system-call layer and v0.6 capability-I/O work.  
**Target:** Linux/Wayland, initially x86-64 and AArch64 little-endian.  
**Purpose:** define the smallest host substrate that can support a real Shroud window without putting toolkit semantics in C or granting ambient authority.

## 1. Decision summary

Shroud's existing S0 core is a deterministic software renderer and input state machine. It is not a native window system. A Wayland host needs a transport, a bounded protocol engine, shared-memory buffers, a monotonic clock and native input services.

The current T6 roadmap lists `open`, `read`, `write`, `exit`, memory mapping and signals. That list is not sufficient for a Wayland client. In particular, Wayland requires Unix-domain sockets, descriptor passing with `SCM_RIGHTS`, readiness waits, and a way to create and populate shared-memory backing files.

The recommended architecture is:

1. **Capstan owns all Wayland protocol and UI semantics.** The Wayland wire codec, object registry, xdg-shell lifecycle, shm buffer lifecycle, input normalization, Shroud calls and error policy are Capstan code.
2. **A narrow audited host ABI owns only kernel entry.** Until the compiler/runtime can express the required low-level operations, a small platform module may marshal arguments to the Linux ABI. It must not implement Wayland messages or decide UI behaviour.
3. **Authority is explicit.** A host entry point receives a display-endpoint capability and a monotonic-clock capability. The toolkit does not search the environment, current directory or arbitrary filesystem paths for a display socket.
4. **Do not require client-side `mmap` for the first Wayland path.** Create a bounded `memfd`, size it with `ftruncate`, populate it with offset writes, and pass its descriptor to the compositor with `SCM_RIGHTS`. The compositor maps the backing file for `wl_shm`. This avoids exposing raw mapped pointers to Shroud before the verified low-level memory interface exists.
5. **Keep this a staged bring-forward of T6, not a runtime rewrite.** The minimal host slice is separate from the generic memory-mapping, signal and process facilities needed by the full C-free programme.

This proposal does not claim that a native host exists, that the temporary ABI boundary is C-free, or that the interface below is an approved public Capstan API.

## 2. Ownership and trust boundaries

| Layer | Owns | Must not own |
|---|---|---|
| Shroud S0 | View tree, layout, hit testing, rasterisation, widget state, canonical events, accessibility semantics | OS handles, socket protocol, native buffers |
| Capstan Wayland host | Wire framing, object IDs/interfaces, registry, xdg-shell, wl_shm, surface lifecycle, event dispatch, pixel serialization, input normalization | Raw pointers, ambient filesystem access, arbitrary syscalls |
| Capability-I/O API | Opaque authorities, descriptor ownership, bounded reads/writes, explicit errors, monotonic-clock capability | Wayland message semantics or UI policy |
| Linux ABI module | Exact syscall/libc ABI marshalling, errno conversion, descriptor flags, kernel resource creation | Protocol decoding, widget/layout/rendering/accessibility logic |
| Kernel/compositor | Socket transport, descriptor transfer, shared-memory mapping, surface composition and native input delivery | Any assumption of trusted or well-formed peer data |

The compositor and every message received from it are untrusted inputs. A connected Wayland socket is an authority to communicate with that compositor; it is not authority to open arbitrary files, spawn processes or access other sockets.

## 3. Capability model

The application entry point must receive capabilities explicitly. The Shroud library must not call `getenv`, inspect `WAYLAND_DISPLAY` or `XDG_RUNTIME_DIR`, resolve arbitrary paths, or silently fall back to an ambient display.

Proposed opaque capabilities (names are illustrative until the standard-library and runtime contracts are reviewed):

- **`DisplayEndpoint`** — authority to connect to one selected Wayland display endpoint. The capability provider resolves session configuration and enforces permitted endpoint scope.
- **`DisplayConnection`** — an owned connected Unix stream. It is not convertible to an integer descriptor in ordinary application code.
- **`SharedMemoryObject`** — a bounded anonymous backing object suitable for `wl_shm`; its descriptor can be transferred only through an explicit descriptor-transfer operation.
- **`MonotonicClock`** — authority to read a monotonic clock. The UI host, not an event payload or application model, samples it for guard timing.
- **`InputSeat`** — a protocol object derived from the selected display connection, not a separately ambient OS input authority.

Capabilities are non-forgeable, non-serializable and non-interchangeable. Copy/clone semantics must be explicit. Closing or dropping an owning capability must release its kernel resource exactly once; transferred descriptors create a separately owned receiver-side descriptor. No API returns a raw pointer or permits arbitrary descriptor-number arithmetic.

Filesystem authority for fonts and configuration is separate. Shroud must not infer permission to read a font merely because it has a display capability.

## 4. Minimum Linux ABI inventory

The table separates operations required by the first Wayland vertical slice from generic T6 work. Exact syscall numbers and calling conventions belong in the target-specific ABI module, never in Shroud.

| Operation | Why the host needs it | Required contract |
|---|---|---|
| `socket(AF_UNIX, SOCK_STREAM, ...)` | Create the Wayland transport | Nonblocking and close-on-exec policy is explicit; descriptor ownership is returned only as an opaque capability |
| `connect` | Connect to the selected endpoint | Endpoint comes from `DisplayEndpoint`; bounded path length; explicit in-progress/error handling |
| `fcntl` or socket flags | Configure nonblocking and close-on-exec | Only approved flag transitions; no arbitrary descriptor mutation |
| `getsockopt(SO_ERROR)` | Complete nonblocking connect | Return a typed error; never treat writability alone as successful connection |
| `sendmsg` | Send protocol bytes and optional FDs | Bounded payload/control data; `SCM_RIGHTS`; `MSG_NOSIGNAL`; partial-write semantics |
| `recvmsg` | Receive protocol bytes and FDs | Bounded payload/control data; `MSG_CMSG_CLOEXEC`; detect `MSG_TRUNC`/`MSG_CTRUNC`; close excess or malformed received FDs |
| `poll` (or `ppoll`) | Wait for readable/writable socket state | Finite timeout/deadline; handle `EINTR`; distinguish hangup, error and readiness |
| `memfd_create` | Create anonymous `wl_shm` backing | Close-on-exec; bounded name; sealing policy explicitly decided |
| `ftruncate` | Set exact shared-buffer length | Checked nonnegative size and host pixel budget before call |
| `pwrite` | Populate/repopulate frame bytes without shared file-offset races | Checked offset + length; handle partial writes and `EINTR`; no implicit extension beyond declared pool size |
| `fstat` | Validate received keymap/shared-memory descriptor size where needed | Treat metadata as untrusted; compare against protocol-declared and configured limits |
| `read` / `write` / `close` | Generic bounded descriptor I/O and lifecycle | Explicit partial progress, `EINTR`, EOF and close semantics |
| `clock_gettime(CLOCK_MONOTONIC)` | Trusted guard clock and event-loop deadlines | Nonnegative monotonic value; checked seconds-to-milliseconds conversion; reject regression/overflow |

### Explicitly not needed for the initial shm path

- Client-side `mmap`/`munmap`: the first design writes into the memfd with `pwrite`; the compositor maps the file. Keep generic mmap in T6 for other runtime needs, but do not make raw pointer access a Shroud prerequisite.
- `epoll`, `eventfd`, `timerfd`: a single-threaded initial host can use `poll` and finite deadlines. Add these only after profiling or lifecycle requirements justify them.
- Direct `ioctl` access: no initial Wayland window path requires a general ioctl capability.
- Process creation: the toolkit does not spawn a compositor or helper process.

### ABI error rules

Every operation returns a structured result with operation, stable error category and (where safe) captured platform error code. Retry only explicitly retryable conditions. `EINTR` is retried for operations whose contract permits it; nonblocking `EAGAIN` becomes readiness wait, not a busy loop. A zero-byte write with remaining data is treated as no progress/error, not success. `SIGPIPE` must not terminate the process; use `MSG_NOSIGNAL` for socket sends and define the policy for any other write path.

The public Capstan layer must use a `Result`-style error model when available. Until then, an interim optional result plus a stable error enum is preferable to process termination or an ambiguous boolean. Do not leak raw `errno` values into application logic as the only contract.

## 5. Why memfd plus pwrite is the first buffer contract

Wayland `wl_shm` requires a file descriptor for a shared-memory pool. The client does not have to map that file itself. The initial host can:

1. Validate width, height, stride and total bytes with subtraction/division-based arithmetic.
2. Create a close-on-exec anonymous memfd.
3. Set its exact size with `ftruncate`.
4. Send the descriptor once in the `wl_shm.create_pool` request using `SCM_RIGHTS`.
5. Create a `wl_buffer` with the negotiated `WL_SHM_FORMAT_ARGB8888` format.
6. Serialize the Shroud premultiplied `0xAARRGGBB` pixels into the buffer's native-endian byte order and write at a checked offset with `pwrite`.
7. Attach, damage and commit the surface.
8. Do not write to that buffer again until the corresponding `wl_buffer.release` event has been received.

On the initial little-endian targets, a logical `0xAARRGGBB` word is stored as bytes B, G, R, A for the Wayland ARGB8888 format. The implementation must state the target endianness and test the actual byte sequence; it must not assume that Capstan's integer-list representation is already a native byte buffer.

Use a small bounded buffer pool (initially two or three buffers). If all buffers are compositor-owned, wait for release or defer the frame; never overwrite a buffer still in use. Buffer count, per-buffer bytes and aggregate shared-memory bytes have independent caps. On resize, create a new generation of buffers, stop attaching old-generation buffers, and release them only after compositor ownership has ended.

This avoids an early raw-pointer/mmap API. It does not remove the need to test partial `pwrite`, descriptor transfer, pool sizing, compositor release and cleanup after disconnect.

## 6. Wayland protocol responsibilities in Capstan

The Capstan host implements protocol messages and validates every response. The first protocol set is:

- `wl_display`, `wl_registry`, `wl_callback`;
- `wl_compositor`, `wl_surface`, `wl_region`;
- `wl_shm`, `wl_shm_pool`, `wl_buffer`;
- `xdg_wm_base`, `xdg_surface`, `xdg_toplevel`;
- `wl_seat`, `wl_pointer`, `wl_keyboard`;
- `wl_output` and the selected scale/viewport protocol extensions.

The protocol engine must:

- Validate each 8-byte message header, object ID, opcode, declared size, alignment, interface version and argument count before allocation or dispatch.
- Cap one inbound message and the aggregate queued bytes; cap received descriptors and close every descriptor not accepted by a validated message.
- Handle partial stream reads/writes and ancillary descriptors without losing the byte position to which each descriptor belongs.
- Reject unknown object IDs, invalid enum values, invalid array lengths, duplicate/illegal object transitions and malformed strings.
- Track object lifetimes and destroy protocol objects idempotently on shutdown.
- Treat `xdg_surface.configure` as a required configure/acknowledgement transition before the first buffer commit.
- Keep frame callbacks and buffer-release events distinct: frame pacing is not permission to reuse a buffer.
- Recover from display disconnect or compositor restart by entering an explicit lost state; never present stale buffers as current.

Wayland protocol framing is not implemented by the syscall shim. It is Capstan code with independent parser and state-machine tests.

## 7. Input and text services

The core event contract already distinguishes pointer cancellation and native focus loss (PR #211). The Wayland host must map pointer leave, button release, seat capability loss, focus/deactivation and surface destruction into those transitions without fabricating a successful release.

Keyboard keycodes from Wayland are not Unicode text. The host needs a reviewed keymap service to interpret the compositor-supplied XKB keymap and modifier state. The options are:

1. implement the required XKB keymap parsing/lookup in Capstan; or
2. use a narrowly scoped, separately reviewed `libxkbcommon` adapter for keymap compilation and key lookup, treating its output as untrusted and documenting the library as an additional trusted dependency.

The second option is a platform-library dependency, not a syscall shim. It must not be hidden under the phrase “C-free”. Committed text and IME composition require a text-input protocol (initial candidate: `zwp_text_input_v3`) with explicit pre-edit, commit and cancel handling. Do not claim complete CJK/Indic IME support by converting each composition update into `EV_TEXT`.

The first native smoke test may validate window creation, rendering and pointer motion before full keyboard/text-input support, but that is an engineering milestone only—not an S1 release gate.

## 8. Accessibility boundary

A diagnostic JSON semantic tree is not a native accessibility provider. The Linux release gate remains a real AT-SPI bridge with accessible roles, names, values, states, bounds and actions derived from Shroud's semantic tree.

AT-SPI commonly uses D-Bus. It is a separate protocol endpoint and capability, not an extension of the Wayland display socket. Do not add ambient session-bus discovery to Shroud. Specify and grant a separate bus capability, bound message sizes/object counts, and route accessibility actions back through `Ui.handle`/the approved Shroud action path. Password values and other secret fields remain undisclosed.

AT-SPI is deliberately not part of the first Wayland window smoke-test slice, but it is mandatory before describing the Linux host as production-ready or accessibility-conformant.

## 9. Proposed safe API shape

The following is a contract sketch, not Capstan source or a shipped declaration:

- `connect_display(DisplayEndpoint) -> Result<DisplayConnection, HostError>`
- `send_protocol(DisplayConnection, TaintedBytes, List<SharedMemoryObject>) -> Result<WriteProgress, HostError>`
- `receive_protocol(DisplayConnection, max_bytes, max_fds) -> Result<ReceiveBatch, HostError>`
- `wait_ready(DisplayConnection, Readiness, Deadline) -> Result<Readiness, HostError>`
- `create_shared_memory(SharedMemoryAuthority, byte_length) -> Result<SharedMemoryObject, HostError>`
- `write_shared_memory_at(SharedMemoryObject, offset, bytes) -> Result<WriteProgress, HostError>`
- `monotonic_now(MonotonicClock) -> Result<MonotonicTime, HostError>`
- `close_resource(Resource) -> Result<(), HostError>`

The API must not expose raw descriptors, raw pointers, arbitrary syscall numbers, unbounded reads, or arbitrary path strings. The host's event loop owns the connection and buffer capabilities. UI applications receive only normalized Shroud events and explicit application-level capabilities.

The final type syntax, generic result type, byte-slice type and ownership rules must be reconciled with the active T1 standard-library and compiler work before these names become declarations.

## 10. Staged implementation plan

| Stage | Deliverable | Exit evidence |
|---|---|---|
| P0 — contract | Review this capability/syscall/API boundary | Approved API and threat model; no unresolved descriptor ownership or authority semantics |
| P1 — ABI substrate | Minimal Linux wrappers and opaque capability resources | Unit tests for every syscall result, errno, partial I/O, EINTR, timeout and cleanup path |
| P2 — transport | Capstan Unix-stream framing and SCM_RIGHTS handling | Fuzzed framing/ancillary parser; truncated/control-truncated and descriptor-leak tests |
| P3 — first window | Registry, xdg-shell configure, wl_shm pool/buffer and full-frame presentation | Real Wayland compositor smoke test; deterministic software golden frames preserved |
| P4 — pointer/keyboard | Seat lifecycle, pointer capture/cancel, focus, keymap and committed text | Native event trace tests; xkbcommon or Capstan keymap decision documented |
| P5 — lifecycle | Resize generations, disconnect/reconnect, buffer release, shutdown | No stale frame/event use; bounded resource accounting under repeated resize |
| P6 — accessibility | AT-SPI provider and actions | Real assistive-technology test matrix and semantic parity |
| P7 — release | Linux support declaration and reproducible performance/compatibility evidence | All Shroud S1 acceptance gates, security tests and release CI pass |

P1 should not wait for the full T7 verified-low-level milestone if a narrow audited ABI module is approved. Conversely, P3 must not begin by adding guessed host APIs to Shroud. The protocol and host contracts are reviewed first.

## 11. Required adversarial tests

- Socket connect refusal, timeout, peer close, hangup, `EINTR`, `EAGAIN`, short send and short receive.
- SCM_RIGHTS with zero, maximum, excess, malformed and control-truncated descriptor arrays; every rejected descriptor is closed.
- Message header sizes below 8, non-four-byte alignment, oversized sizes, invalid object IDs/opcodes, malformed arrays/strings and object-ID reuse.
- A descriptor delivered between fragmented protocol frames; partial sends where ancillary data is accepted before the remaining bytes.
- Memfd creation, size overflow, short/failed pwrite, offset overflow, pool size mismatch, buffer release ordering and compositor disconnect during resize.
- Clock regression, conversion overflow, suspend/resume and deadline timeout.
- Repeated resize and buffer-pool exhaustion with a strict aggregate shared-memory cap.
- Pixel channel order, premultiplied alpha and stride/height arithmetic at 1x, 1.25x, 1.5x, 1.75x and 2x scale.
- Input cancellation on pointer-capture loss, seat removal and surface destruction; focus loss suppresses key/text events.
- Accessibility actions cannot bypass Shroud's activation guards; secret/password values are absent from all exposed properties.

## 12. Explicit non-claims

This RFC does not claim:

- a working Wayland host, native window, text-input stack or AT-SPI provider;
- a C-free runtime or verified syscall layer;
- complete XKB/IME, fractional scaling or multi-monitor support;
- process-wide memory bounds from per-buffer/per-window limits;
- accessibility conformance from the S0 JSON tree;
- that a compositor, XKB library, D-Bus daemon, kernel or hardware is trusted.

The purpose is to make the next implementation step precise enough to build and test without weakening Capstan's authority, memory-safety or Shroud architecture boundaries.
