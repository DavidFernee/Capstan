# Halyard Core primitives — MC1 contract and implementation status

> **Status:** initial Capstan-native prototype under review, 2026-11-25.
> This document distinguishes the required contract from the deliberately limited first
> implementation. Nothing here implies release readiness or concurrent safety.

## 1. Scope of the first vertical slice

`lib/halyard/core.cap` currently provides:

- construction of an in-memory byte source from a caller-owned `List<int>`;
- byte-domain validation (`0..255`) and a defensive snapshot;
- bounded `u8`, exact-byte, skip and big-endian `u32` reads;
- explicit EOF, truncation, closed and invalid-state outcomes;
- a twelve-dimensional live aggregate ledger for input bytes, retained bytes, output bytes,
  decoded units, work units, allocation-object slots, metadata entries, queue slots,
  worker slots, nesting slots, track slots and chunk slots, with one-shot reservation handles;
- a separate monotonic consumption budget for cumulative input, output, decoded-unit and work charges;
- all-dimensions-preflighted reserve and release operations;
- an in-memory bounded byte sink with preflighted writes, copy-on-commit append, defensive snapshots and explicit close.

It performs no filesystem, network, device, demuxer, decoder or encoder operations. It is
not yet a general streaming abstraction and does not implement asynchronous IO, seeking,
backpressure, cancellation tokens, deadlines, worker isolation or resource scheduling.

## 2. Required byte-source contract

A conforming source must maintain:

- `0 <= position <= length`;
- a fixed source length for the lifetime of the source;
- bytes in the closed interval `0..255`;
- no ambient filesystem, network, device or process authority;
- bounded construction and read operations;
- explicit EOF, truncation, closed and invalid-state results.

`read_exact(n)` has a transactional cursor contract: if `n < 0`, the source is closed,
its state is invalid, or fewer than `n` bytes remain, the operation fails without
advancing the cursor or returning a partial result. On success it returns exactly `n`
bytes and advances by `n`. Range admission must use `n <= length - position` after
validating the cursor, never unchecked `position + n`.

The initial implementation copies the input list. It does not yet provide a language-
enforced immutable span or opaque source representation. The fields of Capstan structs
are currently accessible to callers, so callers can mutate `source.bytes` or its cursor.
The current API therefore relies on a module-ownership convention and is not suitable
as a hostile-input trust boundary until encapsulation is enforced by the language or a
runtime-validated opaque representation is introduced.

The source API separates a cheap shape preflight (`halyard_source_shape_valid` and
`halyard_source_length`) from the full byte-domain scan (`halyard_source_validate`).
Parsers first reject an oversized source using the constant-time shape/length checks,
then scan the bounded byte vector once before parsing. This prevents an attacker-sized
input from forcing a full byte scan before the parser applies its input ceiling.

The low-level constructor copies bytes without reserving aggregate capacity and is retained
for internal tests and trusted composition only. Callers handling untrusted or aggregate-
bounded data should use `halyard_managed_source_create`, which validates the byte domain
and input ceiling, acquires a retained-byte lease, and only then makes the defensive copy.
The managed wrapper keeps the lease for the source lifetime; `halyard_managed_source_close`
closes the source and releases the lease exactly once. A failed recoverable validation or
admission returns without retaining a charge. If source construction returns a recoverable
error after admission, the wrapper attempts to roll the lease back.

## 3. Required aggregate-ledger contract

A ledger has a non-negative limit and used counter for every resource dimension.
For each dimension `d`:

`0 <= used[d] <= limit[d]`

For a reservation request `charge`, admission succeeds only if every requested amount is
non-negative and:

`charge[d] <= limit[d] - used[d]`

for every dimension. All dimensions are checked before any counter changes. If any
dimension fails, every counter remains unchanged. Release follows the same pattern:
every amount is validated against the corresponding used counter before any decrement.
No saturating arithmetic, wraparound, or partial reservation is permitted.

The supported acquisition path now returns a one-shot `HalyardReservation`
capability via `halyard_ledger_acquire`. The matching
`halyard_reservation_release` consumes that capability only after a successful
ledger decrement; a second release through the same capability is rejected without
changing counters. Rejected acquisition returns no capability. This closes the
ordinary duplicate-release path in sequential use and makes the intended ownership
protocol explicit.

This is not yet a non-forgeable lease: Capstan struct fields remain public, and the
low-level `halyard_ledger_reserve` / `halyard_ledger_release` primitives remain
available for the current regression suite and internal composition. Untrusted callers
must not be given direct access to those primitives or allowed to construct/mutate
reservation values. Opaque/linear types and synchronised ownership are still required
before this can be treated as a security boundary. No concurrent-safety claim is made.

The current `HalyardLedger` is a **live reservation ledger**, not a cumulative
consumption budget. Its counters represent currently admitted occupancy/outstanding
work; releasing a lease returns that live capacity. In particular, callers must not use
its release operation to account for total bytes parsed, output emitted, samples decoded
or CPU/work already consumed. Those quantities require monotonic counters.


The first implementation satisfies this all-or-nothing rule for sequential calls. It is
**not thread-safe**: concurrent reserve/release calls can race. No claim of atomic
concurrent admission is made. Before the ledger is shared by workers or concurrent graph
producers, it requires a specified synchronisation/ownership model and adversarial
concurrency tests (or a single-owner message-passing design that removes shared mutation).

The ledger now exposes twelve dimensions through `halyard_ledger_create_bounded`: the original input/retained/output/decoded/work dimensions plus allocation-object slots, metadata entries, queue slots, worker slots, nesting slots, track slots and chunk slots. These are logical admission quotas, not allocator-exact measurements. Parser/sample/frame allocations, deadlines, bounded cleanup and all retained-reference lifetimes are not yet fully coupled to live leases. Avoid double-charging the same physical allocation while ensuring retained references and derived outputs remain charged for their actual lifetime.

## 4. Monotonic consumption budget

`HalyardConsumptionBudget` separately tracks cumulative input bytes, output bytes,
decoded units and work units. `halyard_consumption_budget_consume` preflights all
dimensions before changing any counter. It has deliberately no release/refund operation:
completed parsing, decoding and work cannot be made free by releasing a live buffer.
This prevents a decode-and-discard loop from resetting its cumulative work allowance.

This is an initial sequential prototype. Its fields are publicly mutable and it is not
concurrency-safe. Shanty and Deadeye now expose budgeted entry points in addition to their
legacy unbudgeted convenience APIs. Those entry points charge input and bounded parser
work before parsing, and charge output/decoded units before materialising PCM or RGBA
results. Shanty charges the retained PCM data-chunk copy and separately charges the byte
validation scan and decoded sample list. Deadeye charges the temporary pixel copy plus
final RGBA payload before reading/materialising the frame. These are logical payload
charges, not allocator-exact process-memory measurements; list/object overhead and the
source's own snapshot remain separate live-retention concerns.

The legacy unbudgeted entry points remain callable and are suitable only for trusted,
explicitly bounded composition. Budgeted parsing does not yet require a managed source or
bind cumulative budget state to a non-forgeable capability. The cumulative budget and live
lease ledger must eventually share one atomic admission/ownership model without
confusing their different lifetimes. Cancellation and partial-work semantics remain open.

## 5. Failure and ownership rules

- Validation must precede allocation and state mutation.
- Failed reads and failed reservations preserve observable state.
- Returned byte lists are independent copies, not borrowed views.
- Closing is explicit and idempotence is observable (`close` succeeds once).
- No partial bytes are returned for an exact read.
- Errors are stable machine-readable categories; diagnostics must not echo attacker-
  controlled payloads or secrets.
- Resource release must be tied to ownership/lifetime, not caller guesswork.

The prototype does not yet have cancellation, deadlines, lifetime-bound reservations,
or an RAII/linear ownership mechanism. Those are explicit follow-up requirements.

## 6. Bounded in-memory byte sink

`HalyardByteSink` is a first Capstan-native in-memory sink with a per-instance payload
limit. `halyard_sink_write_exact` validates the sink state, capacity and every input byte
before constructing a replacement buffer and swapping it into the sink. Rejected writes
leave the prior contents unchanged. Snapshot returns a defensive copy; close is one-shot
and prevents further writes.

This is not yet a process-memory bound: the copy-on-commit strategy temporarily retains
both old and replacement lists, and list/object overhead is outside the payload count.
The managed sink path now couples retained/output payload charges and logical allocation-object slots to its lease. Copy-on-commit append charges the replacement while the old payload remains live, then releases the old lease after commit. This accounts for logical payload and object-slot peak admission, not allocator metadata, list capacity, GC headers or transient runtime storage. The unmanaged low-level sink remains available for trusted composition. Allocator exhaustion remains a terminal runtime outcome rather than a recoverable sink error. It is a correctness prototype, not a hostile-input output boundary.

## 5.0 Concurrency policy and executable reference model

The selected policy for aggregate media-resource admission is **single-owner
message passing**, not shared-ledger atomics. One ledger owner serialises admission
and release requests; callers submit bounded requests through a FIFO queue. Enqueue
is the ownership commit point. The owner validates and commits the complete
multi-dimensional charge as one state transition. A rejected request retains its
pre-commit ownership and changes no ledger dimension.

The Capstan-native reference machine is
`verification/halyard_resource_actor.cap`. It models two competing request
identities, a bounded FIFO, serial processing, all-or-nothing admission and one-shot
release. Its tests cover both enqueue orders, aggregate overcommit prevention,
queue-full rejection, invalid/duplicate requests, repeated release and rejection of
corrupted resource/queue state before transition. The model now has seven Capstan
test declarations; the standard test runner executes it.

This is a **policy model**, not a live concurrent actor implementation. It assumes
the owner processes transitions serially; it does not itself establish that a
multithreaded runtime enforces single ownership, that queue operations are race-free,
or that cancellation/worker death always reaches the owner. The refinement target is
the structured task/channel machine in `verification/concurrency_model.cap` and
the language/runtime work in issues #229 and #249. Until that bridge is implemented
and verified, Halyard APIs remain sequential and thread-confined.

## 5.1 Extended live-resource vector

The bounded ledger now has an opt-in extended constructor,
`halyard_ledger_create_bounded`, which adds seven live-resource dimensions to the
original byte/decode/work vector:

| Dimension | Meaning | Typical owner |
|---|---|---|
| `allocation_units` | Count of admitted allocation objects, not bytes | buffer/plane/frame allocator |
| `metadata_entries` | Live metadata records | container/track/index tables |
| `queue_slots` | Occupied bounded queue entries | packet/frame/command queues |
| `worker_slots` | Admitted active worker reservations | worker scheduler |
| `nesting_slots` | Active parser/graph nesting depth | parser or graph traversal |
| `track_slots` | Live media tracks | demux/session |
| `chunk_slots` | Live chunks/atoms/blocks | container parser |

These dimensions are admitted and released in the same all-or-nothing vector
operation as input bytes, retained bytes, output bytes, decoded units and work units.
The old five-limit constructor remains source-compatible and assigns zero capacity
to the new dimensions; callers that need them must use the bounded constructor and
supply explicit limits. A zero limit is intentional fail-closed behaviour, not an
implicit unlimited default.

The units are logical admission quotas. Managed source creation now acquires one
allocation-object slot together with its retained-byte lease before taking the defensive
snapshot. Managed sink creation similarly acquires its slot before constructing the sink;
each copy-on-commit append acquires a second slot while the old sink allocation remains
live, then releases the old slot only after commit. A one-slot ledger therefore rejects
an append without changing the existing sink.

In particular, `allocation_units` is not an allocator-exact byte count and does not charge
allocator metadata, capacity over-allocation, GC headers or transient runtime storage. The current public structs
also remain forgeable and the operations remain sequential/thread-confined. The
extended vector therefore improves the model's expressiveness but does not close
MC1's opacity, concurrency or actual-memory-accounting requirements.

The cumulative `HalyardConsumptionBudget` remains a separate monotonic object:
successful input/output/decode/work consumption is never refunded. Releasing a live
lease cannot refund cumulative work. These are different accounting lifetimes and
must not be conflated.

## 6.2 Managed sink lifetime and peak accounting

The managed sink path couples output payload ownership to the aggregate ledger.
`halyard_managed_sink_create` creates an empty sink with a zero-sized lease.
For each append, `halyard_managed_sink_write_exact` validates the request, then
acquires a replacement lease charging the *entire replacement payload* in both
`retained_bytes` and `output_bytes`. The old payload remains live while the
copy-on-commit replacement is built, so the ledger temporarily accounts for both
payloads. Only after the sink swaps to the replacement does the old lease get released.
This deliberately means a write can be rejected even when the final payload fits: the
aggregate budget must also accommodate the copy-on-commit peak.

If release of the old lease fails after commit (for example, because public ledger state
was corrupted), the old lease is retained in the managed sink and further writes are
blocked until cleanup succeeds. Close is retryable: it tracks successful release of the
current lease separately, so a failed cleanup can be retried after ledger repair without
releasing that lease twice. Close only marks the managed sink fully closed after all
leases have been released.

This is a sequential accounting protocol, not a proof of allocator-exact memory bounds,
hostile-caller safety or concurrency correctness. Public struct fields remain mutable,
allocator metadata and list/object overhead are not charged, and allocator exhaustion
has no recoverable result in the current language/runtime API.

## 6.1 Managed source lifetime

`halyard_managed_source_create` is the first composition of source construction with
aggregate retained-memory admission. It rejects negative/oversized limits and invalid
bytes before acquiring capacity, reserves `retained_bytes = input.len()`, then invokes the
defensive source snapshot constructor. The returned managed source carries the lease.
Reads go through managed-source wrappers; close first closes the source, then consumes
the lease. If lease release fails because the ledger has been corrupted, the source stays
closed and a later close call may retry release after the ledger is repaired. It does not
reopen the source or refund the lease twice.

The reservation is for the retained snapshot, not a second charge for the caller-owned
input list. The caller's original list remains outside Halyard's ownership and accounting.
This prototype does not account allocator metadata or transient implementation overhead.
The language/runtime currently exposes no recoverable allocation-result contract here;
therefore the API cannot yet promise rollback after allocator exhaustion. Admission occurs
before the copy, but true failure-atomic allocation requires a fallible allocator contract
or preallocated storage plus an ownership-transfer primitive. This remains an explicit
MC1 blocker, not a claimed guarantee. The API is also sequential and thread-confined.

## 7. Rational timebase and timestamp rescaling

`HalyardTimebase` represents seconds per tick as a positive reduced fraction
`numerator/denominator`. `halyard_timebase_create` rejects non-positive terms and
normalises by the greatest common divisor. `halyard_timestamp_rescale` converts ticks
between source and target timebases using integer arithmetic only. It cross-cancels
factors before checked multiplication and supports explicit `Exact`, `TowardZero`,
`Floor`, `Ceil` and `NearestEven` policies. Exact mode rejects non-integral results;
other modes apply their named rule, including ties-to-even. Invalid or non-normalised
public timebase values are rejected.

The implementation is intentionally only the rational conversion primitive. Its
conservative checked intermediate representation can reject a conversion when an
intermediate product is outside signed-64 range even if a wider-arithmetic implementation
could represent the final quotient. It does not itself implement stream/epoch identity,
finite-width wrap extension, discontinuity transitions, VFR duration policy, seek
generations, external-clock anchoring or rational drift correction. These semantics are
specified separately in [RATIONAL-TIMEBASE-AND-CLOCK-CONTRACT.md](RATIONAL-TIMEBASE-AND-CLOCK-CONTRACT.md),
with machine-readable vectors in
[`tests/media/fixtures/rational_timebase_vectors.json`](../../tests/media/fixtures/rational_timebase_vectors.json).
The vector oracle checks the normative expected results independently; it does not execute
the Capstan runtime. The timebase structs remain publicly mutable, so per-operation
validation is not an opaque type boundary.

## 8. Test obligations

The regression suite is expressed as 47 Capstan `test` declarations in `lib/halyard/core.cap`; Shanty and Deadeye contain 11 and 8 declarations respectively.
Run it with `bin/capstan test lib/halyard/core.cap`; the Shanty and Deadeye suites are invoked directly with `bin/capstan test lib/halyard/shanty.cap` and `bin/capstan test lib/halyard/deadeye.cap`. The module tests remain colocated Capstan declarations and are not wired through a Halyard-specific shell hook. The Halyard-specific test logic
contains no shell, Python, C, or other-language source. It covers:

- defensive snapshot from the original input list;
- invalid byte, negative limit and source over-limit rejection;
- successful byte reads, exact-read truncation atomicity, EOF and close behaviour;
- big-endian 32-bit decoding;
- exact-limit aggregate reservation;
- over-limit reservation with all counters unchanged;
- full release and release-underflow rejection;
- negative reservation rejection;
- reduced rational timebase construction and invalid numerator/denominator rejection;
- exact 48 kHz to 90 kHz timestamp conversion;
- explicit positive and negative rounding modes and nearest-even ties;
- checked overflow rejection, signed multiplication boundary identities, all sign quadrants, near-limit products, and rejection of forged non-normalised timebases;
- exhaustive exact-read counts around a four-byte source;
- exhaustive (3^5) five-dimensional admission requests;
- independent underflow rejection for every release dimension;
- defensive rejection of corrupted public ledger state;
- defensive validation of source bounds and byte contents before parser use;
- separation of cheap source-shape preflight from the bounded byte-domain scan;
- monotonic cumulative input/output/decode/work budget admission, failure atomicity and no-refund semantics;
- all-or-nothing admission/release for allocation, metadata, queue, worker, nesting, track and chunk live-resource dimensions, including per-dimension over-limit and underflow rejection;
- one-shot reservation-handle release, alias-shared release state and rejection of a handle for a failed reservation; managed source admission, retained-byte and allocation-slot accounting through close/release, zero-allocation-slot rejection, invalid-input rollback and retry after ledger repair; managed sink peak replacement accounting, allocation-slot overlap admission, rejected admission, invalid-write preservation and retryable close after ledger repair.

Still required before MC1 can pass:

1. opaque or otherwise non-forgeable source and ledger state;
2. a single-owner or synchronised concurrency model;
3. allocator-exact byte charging, recoverable allocation failure and explicit ownership transfer;
4. an allocator API that can make admission plus allocation failure-atomic (the current runtime cannot report recoverable allocation failure);
5. explicit thread-confinement until the language-level ownership/channel model from #229/#249 is available; no caller may share a mutable ledger across concurrent tasks;
6. lifetime-bound reservations and cancellation/cleanup semantics;
7. larger model/property tests over generated operation sequences and concurrent schedules;
8. malformed-state and mutation tests;
9. allocation, CPU and retained-memory measurements under adversarial inputs;
10. independent review and exact-head CI on supported platforms.

## 9. Implementation provenance

| Module | First-party source | Current status |
|---|---|---|
| Byte source | `lib/halyard/core.cap` | Prototype; public mutable representation; Capstan-native tests colocated |
| Live reservation ledger | `lib/halyard/core.cap` | Sequential all-or-nothing live lease prototype; not concurrency-safe |
| Cumulative consumption budget | `lib/halyard/core.cap` | Monotonic input/output/decode/work counters; used by budgeted Shanty/Deadeye parse/decode entry points; sequential prototype |
| Reservation handle | `lib/halyard/core.cap` | One-shot trusted-caller handle; public/forgeable until opaque types land |
| Managed byte source | `lib/halyard/core.cap` | Retained-byte lease follows source close; sequential prototype; allocator failure atomicity and opaque ownership remain outstanding |
| Regression vectors | `lib/halyard/core.cap` test declarations | Capstan-native cases; exact-head execution pending |
| Rational timebase | `lib/halyard/core.cap` | Initial checked integer rescaling with explicit rounding; no full clock/discontinuity model |
| Machine-readable format registry | Schema, prototype inventory and deterministic validator implemented (PR #373); runtime registration/discovery API not implemented | MC0 metadata registry delivered; runtime API remains future work |
| Bounded sink | `lib/halyard/core.cap` | Managed copy-on-commit sink charges old and replacement payload leases during transition; allocator metadata/OOM and opaque ownership remain outstanding |

No third-party media implementation code is used by this slice. The existing Capstan
compiler/runtime remains C-backed in the current production build and remains in the
trusted computing base until the C-free execution path is qualified.


## 5.2 Cross-ledger non-refund regression

The cumulative consumption budget and live-resource lease ledger are independent state machines. Releasing a retained-byte/allocation lease must not refund input, output, decoded-unit or work consumption. The regression test `Halyard live lease release never refunds cumulative decode or work` in `lib/halyard/core.cap` exercises the actual lease acquisition/release API between two consumption attempts: the first attempt consumes the full decoded/work allowance, releases its retained-byte/allocation lease, and the second attempt is still rejected with all cumulative counters unchanged.

This is a narrow sequential model regression. It does not establish that every parser/decoder operation charges every required work unit, that cumulative charges are coupled to every allocation/output path, or that a concurrent/cancelled worker cannot leak a lease. Those remain #303/#293 acceptance work.


## 5.3 Current budgeted parser/decoder charge schedule

The current budgeted entry points use deterministic coarse work units, not machine-instruction fuel or WCET:

| Operation | Cumulative input | Cumulative output | Decoded units | Work units |
|---|---:|---:|---:|---:|
| Shanty WAVE parse preflight | source length | 0 | 0 | source length |
| Shanty WAVE data-chunk materialisation | 0 | chunk payload bytes | 0 | chunk payload bytes |
| Shanty PCM byte-domain validation scan | 0 | 0 | 0 | PCM byte length |
| Shanty PCM sample conversion | 0 | sample count × bytes/sample | sample count | sample count |
| Deadeye BMP preflight | source length | 0 | 0 | source length |
| Deadeye BMP pixel-copy and RGBA conversion admission | 0 | source pixel bytes + 4 × pixel count | pixel count | source pixel bytes + pixel count |

These charges are monotonic: a failed later admission does not refund an earlier successful charge. In particular, the Shanty regression `Shanty repeated decode attempts consume cumulative allowance` runs the budgeted parser and decoder once, then attempts to decode the same retained wave again. The second attempt is rejected by the cumulative decoded-unit limit; its preceding byte-validation scan remains charged. This tests the repeated-decode amplification case through the actual decoder entry point, not just the generic budget primitive.

Limitations: these are coarse linear proxies. They do not count every branch, arithmetic operation or chunk-header visit independently; they do not establish worst-case execution time. The budgeted APIs coexist with legacy unbudgeted convenience entry points, and they do not yet bind consumption state to an opaque, non-forgeable capability. The live lease ledger is not yet coupled to every parser temporary, sample/pixel buffer, metadata record or decoder output lifetime. Deadline enforcement and cancellation-aware bounded cleanup are not implemented. These are still open parts of #303/#293.
