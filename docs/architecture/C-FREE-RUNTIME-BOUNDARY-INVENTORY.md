# C-free runtime boundary inventory

**Status:** source-level architecture audit; proposal, not an implementation or proof  
**Baseline:** `main` runtime headers and Makefile inspected 2026-11-25  
**Programme:** C-free execution / CCAM  
**Related:** [C-free execution programme](C-FREE-EXECUTION.md), [compiler pipeline audit](COMPILER-PIPELINE-AUDIT.md), [platform portability contract](C-FREE-PLATFORM-PORTABILITY.md), [CCAM](CCAM.md), [coordination issue #80](https://github.com/DavidFernee/Capstan/issues/80)

## 1. Purpose and classification

This inventory identifies the responsibilities currently concentrated in `runtime/capstan_rt.h` and `runtime/capstan_gc.h`, then separates language/runtime semantics from the small set of operations that genuinely require an operating-system or hardware boundary.

It is a source-level inventory, not a claim that every call path, generated symbol, test, or platform-specific branch has been audited exhaustively. The existing C runtime remains the production implementation. Nothing in this document authorises replacing it before the replacement contracts and conformance gates are agreed.

The key architectural rule is:

- **Capstan runtime core:** deterministic language-visible semantics, data structures, validation, resource policy, cryptographic algorithms, capability checks, and error mapping. These should ultimately be implemented in Capstan.
- **Platform adapter:** the smallest unavoidable interface to process state, file descriptors/handles, clocks, entropy, virtual memory, threads, and executable loading. It should expose typed Capstan results rather than raw OS handles, errno values, or platform encodings.
- **Backend/ABI:** instruction execution, calling convention, stack layout, object format, relocation, and native entry/exit glue. These are target-specific and are not CCAM semantics.
- **Build/test tooling:** Python, shell, C compilers, assemblers, linkers, sanitizers, and CI orchestration. These are distinct from the runtime used by an ordinary Capstan executable and should be tracked separately in the bootstrap TCB.

A service being implemented in C today does not mean its semantics belong in the OS adapter.

## 2. Runtime service inventory

| Current surface | Observed responsibility / dependency | End-state owner | Proposed boundary and invariants |
|---|---|---|---|
| `cap_panic`, `cap_unreachable`, `cap_assert`, test-mode `setjmp/longjmp` | Formats source location and diagnostic to stderr, then exits (status 101); tests can non-locally return through a C jump buffer | Runtime core owns trap construction and diagnostic policy; process adapter owns final stderr write and process termination | Represent failures as typed runtime outcomes until the outermost process boundary. Preserve stable exit mapping and source locations. Do not use non-local host exceptions as language semantics. Test interception must be an explicit test harness interface. |
| `cap_add/sub/mul/div/mod/neg`, shifts, wrapping operations and `*_proved` variants | Signed 64-bit checked arithmetic, division/remainder edge cases, bitwise semantics; currently C compiler builtins and unsigned arithmetic | Runtime/CCAM semantic core | Define exact Int64 operations independently of host integer width/overflow. Keep checked and proved operations distinct; proved variants require a sound compiler proof obligation. Test MIN/MAX, zero, MIN/-1, shift 0/63 and invalid shift counts. |
| `cap_alloc`, `cap_alloc_atomic`, `cap_alloc_secret` | Allocation-kind façade over collector | Runtime memory manager; collector implementation in Capstan | Define object kinds, pointer-scanning policy, zero-initialisation, allocation limits, OOM result, and secret lifecycle in the language/runtime contract. Avoid exposing raw allocation to ordinary source code. |
| `CapStr`, `cap_str_new/perm/concat/eq/at/slice`, `cap_int_to_str`, `cap_char_str`, `CapBuf` | Length-prefixed byte strings, NUL terminator for C interop, checked sizing, immutable string operations and byte buffers | Runtime core | Specify byte-string versus Unicode-string types explicitly. Length and capacity checks precede allocation/conversion. No C NUL-termination assumption in core representation. Permanent literals need an explicit static-data/lifetime model rather than host `malloc`. |
| `CapList`, `CapBList`, sorting, insert/remove/pop, growth helpers | Generic tagged values, packed booleans, bounds checks, checked capacity growth, stable merge sort | Runtime core | Implement as Capstan collections over the managed heap. Preserve insertion/order guarantees, pointer tracing, checked capacity arithmetic, and the distinction between pointer-bearing and atomic storage. Test exact and one-over limits. |
| `CapMap`, SipHash, map key initialisation and reindexing | Ordered key/value map with open addressing; SipHash-1-3 keyed from `/dev/urandom` to resist chosen-key hash flooding | Runtime core plus entropy adapter | Map semantics, insertion order, load factor, probe invariants and SipHash belong in Capstan. A typed `secure_random(bytes)` adapter supplies the process key; failure must fail closed. Seed injection is test-only and must not become a production fallback. |
| `CapGrant`, grant binding, policy recheck and grant checks | Policy identity, object-role binding, bounded arguments and revalidation against TOCTOU | Runtime/security core | Preserve exact policy identity, argument-role/object identity and recheck-before-use. Replace C function pointers/opaque callback storage with a specified Capstan policy reference or closure representation. No OS adapter is needed for the core checks. |
| `cap_print/println/flush`, `cap_read_line/read_bytes` | Standard stream IO through stdio | Runtime core + process/stream adapter | Core owns byte limits, EOF/result semantics, buffering contract and taint of input. Adapter owns stdin/stdout/stderr handles and partial read/write handling. Specify whether writes are atomic (normally they are not) and propagate I/O errors rather than silently dropping them. |
| `cap_args`, `cap_secret_env`, `cap_exit` | Process arguments, secret environment lookup, exit status | Process adapter | Define argument/environment encoding, invalid-byte handling, ownership and maximum sizes. Environment values remain tainted/secret as specified. Exit is only available at process boundary; library/embedded execution needs a returned outcome instead. |
| `cap_path_ok`, `cap_validate_path`, `cap_read_file_max/read_file`, `cap_write_file` | Path validation, NUL rejection, file open/read/write, file type checks, nonblocking FIFO handling, size limits | Runtime core + filesystem adapter | Core validates the Capstan path type and enforces byte budgets. Adapter maps path representation, open flags/handles, file metadata, read/write loops, close and OS errors. Avoid check-then-open path security; define symlink/reparse-point and directory traversal policy. Windows path conversion must be explicit. |
| `cap_run` | Child process execution and argument passing | Optional process adapter | Keep process creation outside CCAM v0.1. If retained as a standard capability, define executable resolution, argv/environment, inherited handles, working directory, timeout, resource limits, exit/signal mapping and cancellation. No implicit shell interpolation. |
| `cap_sql_query` | SQL template/parameter handling and external database interaction | Runtime library plus optional database adapter | Separate deterministic placeholder validation/parameter binding from network/database driver. Parameterisation must remain mandatory; connection, transaction, timeout, cancellation and error mapping are adapter contracts. Exclude from minimal C-free core until an explicit effect/capability API exists. |
| UTF-8 sequence validation, log/HTML/JSON/C/CSV escaping and taint validators | Input validation and context-specific encoding | Runtime/security core | Implement algorithms in Capstan with context-specific types; do not conflate HTML, JSON, shell, SQL, C-literal or log escaping. Define UTF-8 scalar validity and reject malformed sequences consistently. No OS dependency. |
| SHA-256, HMAC-SHA-256, PBKDF2, password record parsing and constant-time comparison | Hashing, password KDF, verification, bounded password input and explicit wiping of intermediates | Runtime/crypto core; optional platform secure-memory support | Algorithms and record formats belong in Capstan or a separately audited crypto implementation. Preserve iteration/size limits and constant-time comparison contract. State compiler/CPU side-channel assumptions. A secure wipe primitive may need platform/compiler guarantees; ordinary managed GC cannot promise immediate zeroisation. |
| `cap_wipe`, secret allocations and secret collector pages | Volatile byte wipe; secret allocations separated from pointer-bearing objects; wipe on reuse/collection; large secrets use dedicated mappings | Runtime security core + memory adapter | Specify secret lifetime, copies, temporary buffers, crash/core-dump exposure, swap/hibernation and zeroisation limits. Adapter may provide locked/non-dumpable memory where supported, but the guarantee must be platform-qualified. Never claim absolute erasure from ordinary process memory. |
| `cap_gc_init/alloc/collect`, page tables, conservative stack scanning, root registration | Mark/sweep collector; conservative stack/register roots; heap limits; page-size/alignment assumptions; metadata allocation; memory release | Collector algorithm in Capstan; virtual-memory and thread/stack interfaces in platform adapter | Separate collector policy/data structures from page acquisition/release and stack discovery. Specify precise vs conservative roots, ABI stack/register capture, stop-the-world/thread model, object maps, metadata OOM behaviour and deterministic heap ceilings. A C-free backend must not assume the current C stack layout. |
| GC stack bounds, guard page, SIGSEGV handler and stack-growth handling | pthread/platform stack-bound discovery, signal handler, guard page, stack overflow detection | Platform adapter/backend, only if selected GC design requires it | Do not port the signal handler mechanically. Choose an explicit stack/guard strategy per ABI; document async-signal-safety, alternate signal stack, exception/unwind interaction and per-thread state. Consider eliminating conservative stack scanning in favour of explicit roots. |
| GC page acquisition/release (`posix_memalign`, `mmap`, `munmap`, `madvise`) | Aligned pages, large allocations, secret mappings, release/reuse and heap accounting | Platform virtual-memory adapter | Abstract reserve/commit/decommit/release, page size, alignment and failure semantics. Preserve accounting only after successful OS operations. POSIX APIs are not the abstraction; Windows needs VirtualAlloc/VirtualFree semantics. |
| GC metadata (`malloc/calloc/realloc/free`, qsort) | Collector metadata and large-object arrays allocated outside managed heap | Runtime core initially; later either managed metadata arena or minimal platform allocator | Avoid a recursive dependency on the managed collector. Specify bootstrap allocator, metadata limits, failure handling and sorting requirements. Do not let unbounded metadata allocations bypass the configured heap/resource budget. |
| GC concurrency primitives (`pthread`) | Thread-related runtime setup/stack information; collector currently includes pthread facilities | Platform adapter only if concurrency is part of the supported runtime | First decide whether the runtime is single-threaded or stop-the-world multi-threaded. If threads are supported, specify safepoints, root registration, thread attach/detach, synchronization, TLS and collector coordination before selecting APIs. |
| `cap_map_key_init`, password salt generation | `/dev/urandom` file reads for cryptographic entropy | Entropy adapter | One API returning exactly N cryptographically secure bytes or a hard failure. Use OS-native secure random facilities; no time/PID/address fallback. Distinguish deterministic test provider from production provider. |
| Process diagnostics and GC reports | stderr/stdout formatting via stdio | Runtime core + stream adapter | Keep formatting deterministic and bounded in core; stream adapter performs writes. Avoid printf-family formatting in the trusted core where possible. |

## 3. GC-specific boundary: the largest portability risk

The collector is not merely an allocator wrapper. The current `capstan_gc.h` combines:

1. **Collector policy and algorithm:** size classes, page/object metadata, allocation bitmaps, free lists, mark stack, root traversal, mark/sweep, heap/live/peak accounting, growth thresholds, secret-object handling, and collection triggers.
2. **Host memory mechanics:** aligned page allocation, large-object mappings, page release advice, page size and address-range assumptions.
3. **Execution-context discovery:** stack bounds, register spilling/scanning, pthread stack queries, signal/guard-page setup, and platform-specific stack conventions.
4. **Bootstrap metadata allocation:** host `malloc/calloc/free` for collector metadata, outside the managed heap.

Only (2) and selected parts of (3) are inherently platform-specific. The mark/sweep algorithm, size-class policy, accounting, and secret-slot state machine should not be duplicated per OS.

The current conservative collector assumes that pointers can be discovered by scanning machine words in the active stack and saved registers. That assumption is ABI- and compiler-sensitive. A native Capstan backend should explicitly choose among:
- precise stack maps/register maps emitted by the compiler;
- explicit shadow-stack/root frames maintained by generated code;
- a conservative scanner with a rigorously specified per-target stack/register capture interface.

The first two options reduce reliance on C ABI and compiler-specific stack discovery, but require compiler/runtime agreement and proof/testing of root publication across calls, safepoints and allocation. This is an architectural decision, not a routine portability patch.

Secret memory requires a separate design review. The current code has dedicated secret allocation kind, zeroes slots on allocation, wipes dead secret slots, and uses dedicated mappings for large secret allocations. These are valuable mechanisms, but they do not by themselves establish erasure from registers, compiler temporaries, copies, swap, hibernation, crash dumps, or physical remanence. The future contract must state exactly what is guaranteed and on which platforms.

## 4. Recommended narrow platform interface

The initial adapter should be deliberately small and typed. Names below are illustrative contracts, not approved API names:

| Interface family | Minimal operations | Required result semantics |
|---|---|---|
| Process | `process_args`, `process_env`, `process_exit` | Owned byte sequences; explicit encoding/invalid-data policy; exit only at outer process boundary |
| Streams | `stdin_read`, `stdout_write`, `stderr_write`, `flush` | Partial progress, EOF, interruption, broken pipe and other failures are explicit |
| Filesystem | `open`, `read`, `write`, `stat/type`, `close`, optional directory operations | Opaque typed handles; explicit ownership; path conversion; no raw OS error leakage |
| Entropy | `secure_random(n)` | Exactly n bytes or hard failure; cryptographic quality defined by platform source |
| Clock | `monotonic_now`, optional `wall_clock_now` | Monotonic duration source distinct from civil time; defined resolution and failure |
| Virtual memory | `page_size`, `reserve`, `commit`, `decommit/release` | Alignment, accounting, access permissions and failure semantics specified |
| Threads (optional) | `thread_create/join`, `mutex`, `condition`, `thread_local` | Only after memory model, safepoints and collector concurrency contract are fixed |
| Dynamic loading / FFI (optional) | `library_open/symbol/close`, foreign-call entry | Excluded from minimal profile until ABI, capability, lifetime and error rules are specified |

Every adapter operation must document: whether it can block; whether it can allocate; whether it can fail; whether it can observe or mutate external state; cancellation/timeout semantics; resource accounting; handle lifetime; and thread-safety. Platform error codes are translated at the adapter edge into a closed Capstan error type plus an optional diagnostic payload.

The adapter must not expose `errno`, POSIX file descriptors, Windows HANDLEs, native pointers, `size_t`, `wchar_t`, or raw platform structs to CCAM or ordinary Capstan code.

## 5. Suggested implementation sequence

1. **Freeze contracts, not code.** Agree the memory model, string/byte model, effects, IO error model, process capabilities, entropy contract and GC root strategy.
2. **Build a pure Capstan runtime core.** Port deterministic arithmetic, strings, lists/maps, validation/escaping, SipHash, SHA-256/HMAC/PBKDF2 and grant logic behind existing language-level types. Keep all current C behaviour as differential evidence, not semantic authority.
3. **Define the platform adapter specification.** Begin with process startup/exit, streams, secure entropy and virtual memory. Defer files, subprocesses, SQL, dynamic loading and concurrency until their effect/capability contracts are explicit.
4. **Choose one native target and root strategy.** Implement ABI entry/exit and explicit roots or stack maps before porting the collector. Do not assume the C collector's stack scanning can be reused.
5. **Port collector policy independently of OS calls.** Keep deterministic collector metadata and accounting in Capstan; use the adapter only for pages and platform-specific execution-context support.
6. **Add per-service conformance tests.** Include success, failure, exact-limit, one-over-limit, partial IO, malformed path/encoding, entropy failure, allocation failure and secret-wipe lifecycle tests.
7. **Retire C service by service.** A service is removed from the C runtime only after the Capstan implementation and adapter pass the same conformance suite on each declared target and its security contract is reviewed.

## 6. Immediate design blockers and risks

- **GC root model:** conservative stack/register scanning is tightly coupled to ABI and compiler behaviour. This is the first major architecture decision for a C-free runtime.
- **Secret erasure claims:** ordinary GC and a volatile wipe do not establish complete erasure. The security contract must be explicit about copies, registers, swap and crash dumps.
- **Entropy availability:** map hashing and password hashing currently fail closed when `/dev/urandom` cannot provide bytes. The adapter must preserve fail-closed behaviour on every platform.
- **Path semantics:** current path validation is byte-oriented and POSIX-shaped. Windows drive paths, UNC paths, reparse points, case folding and Unicode conversion require a defined cross-platform policy.
- **Blocking and partial IO:** the current stdio wrappers hide many host details. A typed adapter must specify partial reads/writes, interruption, cancellation and broken-pipe behaviour.
- **Effects and capabilities:** subprocess, filesystem, environment, SQL and entropy access should not become ambient powers merely because the platform adapter can provide them.
- **Resource accounting:** GC metadata and host allocations currently exist outside the managed heap. The future design must state whether metadata counts toward process/runtime budgets and how OS allocation failure is surfaced.

## 7. Non-claims

This inventory does not claim that any C-free runtime service or platform adapter has been implemented. It does not establish that the current C runtime is free of defects, that the collector is portable to Windows, or that secret data is completely erased. It records observed responsibilities and proposes boundaries for review. CCAM v0.1 remains limited to integer/boolean machine semantics and does not yet define heap, GC, strings, IO, crypto, grants or concurrency.
