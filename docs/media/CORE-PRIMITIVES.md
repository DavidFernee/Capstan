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
- a five-dimensional aggregate ledger for input bytes, retained bytes, output bytes,
  decoded units and work units;
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

Construction copies bytes. Callers must reserve aggregate input/retained memory before
calling the constructor. A later API must combine reservation and construction into one
failure-atomic operation so the copy cannot occur before the charge is secured.

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

The first implementation satisfies this all-or-nothing rule for sequential calls. It is
**not thread-safe**: concurrent reserve/release calls can race. No claim of atomic
concurrent admission is made. Before the ledger is shared by workers or concurrent graph
producers, it requires a specified synchronisation/ownership model and adversarial
concurrency tests (or a single-owner message-passing design that removes shared mutation).

The ledger currently covers five dimensions only. Before parser implementation, expand
the resource model to cover allocations, metadata entries, tracks, chunks, nesting,
decoded samples, pixels, frames, queue depth, threads, CPU/work units, deadlines and
bounded cleanup. Avoid double-charging the same physical allocation while ensuring
retained references and derived outputs remain charged for their actual lifetime.

## 4. Failure and ownership rules

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

## 5. Bounded in-memory byte sink

`HalyardByteSink` is a first Capstan-native in-memory sink with a per-instance payload
limit. `halyard_sink_write_exact` validates the sink state, capacity and every input byte
before constructing a replacement buffer and swapping it into the sink. Rejected writes
leave the prior contents unchanged. Snapshot returns a defensive copy; close is one-shot
and prevents further writes.

This is not yet a process-memory bound: the copy-on-commit strategy temporarily retains
both old and replacement lists, and list/object overhead is outside the payload count.
The sink is not yet coupled to the aggregate ledger's output/retained/allocation charges,
there is no lifetime-bound reservation, and allocator exhaustion remains a terminal
runtime outcome rather than a recoverable sink error. It is a correctness prototype, not
a hostile-input output boundary.

## 6. Rational timebase and timestamp rescaling

`HalyardTimebase` represents seconds per tick as a positive reduced fraction
`numerator/denominator`. `halyard_timebase_create` rejects non-positive terms and
normalises by the greatest common divisor. `halyard_timestamp_rescale` converts ticks
between source and target timebases using integer arithmetic only. It cross-cancels
factors before checked multiplication and supports explicit `Exact`, `TowardZero`,
`Floor`, `Ceil` and `NearestEven` policies. Exact mode rejects non-integral results;
other modes apply their named rule, including ties-to-even. Invalid or non-normalised
public timebase values are rejected.

This is a first implementation, not a complete clock model. The conservative checked
intermediate representation can reject a conversion when an intermediate product is
outside signed-64 range even if a wider-arithmetic implementation could represent the
final quotient. It does not yet model timestamp epochs, discontinuities, wrap domains,
clock drift, resampling, A/V master-clock selection or seek/pause transitions. Those
semantics remain required before media graph scheduling. The timebase structs are also
publicly mutable; every conversion validates them, but this is not an opaque type boundary.

## 7. Test obligations

The regression suite is expressed as 18 Capstan `test` declarations in `lib/halyard/core.cap`.
Run it with `bin/capstan test lib/halyard/core.cap`. The Halyard-specific test logic
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
- checked overflow rejection, signed multiplication boundary cases in all sign quadrants, and rejection of forged non-normalised timebases;
- exhaustive exact-read counts around a four-byte source;
- exhaustive (3^5) five-dimensional admission requests;
- independent underflow rejection for every release dimension;
- defensive rejection of corrupted public ledger state.

Still required before MC1 can pass:

1. opaque or otherwise non-forgeable source and ledger state;
2. a single-owner or synchronised concurrency model;
3. atomic reservation tied to source snapshot allocation;
4. explicit thread-confinement until the language-level ownership/channel model from #229/#249 is available; no caller may share a mutable ledger across concurrent tasks;
5. lifetime-bound reservations and cancellation/cleanup semantics;
6. larger model/property tests over generated operation sequences and concurrent schedules;
7. malformed-state and mutation tests;
8. allocation, CPU and retained-memory measurements under adversarial inputs;
9. independent review and exact-head CI on supported platforms.

## 8. Implementation provenance

| Module | First-party source | Current status |
|---|---|---|
| Byte source | `lib/halyard/core.cap` | Prototype; public mutable representation; Capstan-native tests colocated |
| Aggregate ledger | `lib/halyard/core.cap` | Sequential all-or-nothing prototype; not concurrency-safe |
| Regression vectors | `lib/halyard/core.cap` test declarations | Capstan-native regression cases; exact-head CI pending |
| Rational timebase | `lib/halyard/core.cap` | Initial checked integer rescaling with explicit rounding; no full clock/discontinuity model |
| Format registry | Not implemented | MC0 / issue #287 |
| Bounded sink | `lib/halyard/core.cap` | In-memory bounded copy-on-commit prototype; aggregate allocation/retention accounting and lifetime-bound output reservation remain outstanding |

No third-party media implementation code is used by this slice. The existing Capstan
compiler/runtime remains C-backed in the current production build and remains in the
trusted computing base until the C-free execution path is qualified.
