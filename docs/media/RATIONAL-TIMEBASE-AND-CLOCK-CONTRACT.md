# Rational timebases, timestamp arithmetic and clock epochs

**Status:** normative MC1 specification; implementation is partial. This document defines the contract for timestamps and clock transitions. It does not claim that wrap tracking, discontinuity handling, seeking or external-clock synchronisation is implemented in Halyard.

## 1. Design rules

1. Integer ticks and positive rational timebases are authoritative. Floating-point seconds, frame rates and wall-clock conversions are presentation values only; they MUST NOT decide ordering, duration, admission, seek position or synchronisation.
2. A timebase is seconds per tick, (n/d), where (n,d) are positive signed-64-bit integers and (gcd(n,d)=1). A constructor MUST reduce the fraction. A consumer MUST reject a non-positive, out-of-range or non-reduced representation rather than silently normalising a forged value.
3. A timestamp is a signed 64-bit integer tick count associated with exactly one timebase, stream and clock epoch. The integer alone is not a globally meaningful time.
4. Presentation timestamps (PTS), decode timestamps (DTS), durations and external-clock readings are separate values. They MUST NOT be conflated.
5. Every conversion and state transition is checked and failure-atomic. Overflow, ambiguity, invalid metadata and unsupported clock transitions are errors, never wraparound or saturation.

The existing implementation is in `lib/halyard/core.cap`: `halyard_timebase_create`, `halyard_timebase_valid` and `halyard_timestamp_rescale`. It uses integer arithmetic, cross-cancellation, checked signed-64 multiplication and explicit rounding. Because the implementation only has signed-64 intermediates, it may conservatively reject a mathematically representable final quotient when a required intermediate is out of range. This is a documented limitation, not permission to use floating point.

## 2. Timebase and rescaling semantics

For source timebase (S=n_s/d_s) and target timebase (T=n_t/d_t), converting source tick count (x) to target ticks computes the exact rational value:

[
q = x 	imes rac{n_s d_t}{d_s n_t}.
]

The implementation MUST reduce/cross-cancel factors before multiplication and use checked arithmetic. No intermediate may overflow, and the final rounded result MUST fit signed 64-bit. A wider-integer implementation may accept additional cases, but MUST produce the same result wherever the current checked implementation succeeds.

Rounding policies are normative:

- **Exact:** succeed only when (q) is integral; otherwise return `inexact`.
- **TowardZero:** truncate the fractional part toward zero.
- **Floor:** choose the greatest integer not greater than (q).
- **Ceil:** choose the least integer not less than (q).
- **NearestEven:** choose the nearest integer; exact half-way cases choose the even integer, including for negative values.

A conversion error leaves caller state unchanged. Invalid timebases return `invalid_timebase`; unrepresentable arithmetic returns `overflow`; Exact on a non-integral value returns `inexact`; an unknown rounding tag returns `invalid_rounding`. The result must not contain a partially converted timestamp.

## 3. Timestamp identity and ordering

A timestamp identity is the tuple:

`(stream_id, epoch_id, timebase, clock_kind, ticks)`.

The clock kind identifies at least PTS, DTS, duration, media clock or external monotonic clock. Comparison is defined only for values in the same stream and epoch after checked rescaling to a common timebase. Cross-epoch ordering is undefined unless an explicit epoch mapping is supplied. A consumer MUST NOT compare raw tick integers from different timebases or streams.

Negative PTS/DTS values are valid when the container or codec profile permits them (for example, decode preroll or an edit offset). They remain signed values; they are not sentinels. Missing timestamps and unknown durations use explicit optional/validity fields, never magic integer values such as -1.

## 4. Variable frame rate and duration

Every timed sample or frame carries:
- a PTS, if presentation timing is known;
- a DTS, if decode ordering timing is known and applicable;
- an optional explicit duration in the same stream timebase;
- a stream identity and epoch identity.

An explicit duration is a non-negative tick count; for a presented video frame with a known duration, it MUST be positive. Unknown duration is represented as absent, not guessed. Variable-frame-rate streams MUST preserve each sample's own PTS and duration. A nominal or average frame rate is descriptive metadata only and MUST NOT be used to synthesise missing per-frame timestamps or durations unless a separately selected, explicit constant-frame-rate policy authorises it.

PTS need not be monotonic in decode/packet arrival order. DTS ordering and PTS presentation ordering are separate constraints. A demuxer MUST NOT infer timestamp wrap by assuming that packet arrival order is PTS order.

## 5. Finite-width timestamp wrap

Wrap extension is a separate operation from rational rescaling. It is permitted only when the source format explicitly declares a modulo counter of width (w), with (1 leq w leq 63), and identifies the sequence to which the counter belongs.

Let (M=2^w). A raw counter (r) MUST satisfy (0 leq r < M). Given an already-unwrapped anchor (a), compute the modular forward difference (delta=(r-(a mod M)) mod M). The nearest signed modular displacement is:
- (delta), if (delta < M/2);
- (delta-M), if (delta > M/2);
- **ambiguous**, if (delta=M/2).

The half-range case MUST be rejected as ambiguous. The caller MUST additionally provide a maximum permitted absolute displacement (W), with (0 leq W < M/2); if the selected displacement exceeds (W), reject it as out of window. Add the displacement to (a) with checked signed-64 arithmetic. No wrap extension may silently cross an epoch boundary.

This nearest-anchor rule is valid only for an ordered counter sequence whose true displacement is known to be less than half the modulus. It MUST NOT be applied to reordered PTS values, arbitrary packet arrival order, or timestamps from independent streams. Formats with explicit discontinuity indicators or stronger wrap metadata MUST follow their format-specific rules and retain that provenance.

## 6. Discontinuities and epochs

A discontinuity starts a new epoch. Causes include a container discontinuity marker, source restart, clock reset, unannounced timestamp jump accepted by an explicit policy, stream replacement, and seek.

An epoch record contains a monotonically allocated epoch identifier, stream identity, timebase, origin/anchor, and reason. Epoch identifiers MUST NOT be reused during the lifetime of a stream session. The transition is atomic: either the new epoch and its anchor are committed together, or the previous clock state remains unchanged.

Default policy is **reject** unexplained backward/forward jumps outside the configured tolerance. A caller may explicitly choose:
- **Reset:** start a new epoch with no cross-epoch time mapping.
- **Rebase:** start a new epoch and provide an explicit old-to-new anchor mapping, with checked rational conversion.
- **Reject:** preserve the old epoch and report the discontinuity.

There is no implicit "smooth over" operation. Interpolation, duration accumulation and A/V drift estimation MUST NOT cross epochs without a declared mapping. A decoder or renderer MUST discard stale queued work whose epoch identifier no longer matches the active epoch.

## 7. Seek and resynchronisation

A seek creates a new seek generation and a new clock epoch, even when the demuxer reports a timestamp close to the previous position. The seek result supplies the new stream/timebase anchor. Packets and asynchronous completions tagged with an older generation MUST NOT update the new clock state or be presented after the seek. Decode preroll may be processed when required by the codec, but presentation before the requested target is trimmed using integer timestamp comparisons within the new epoch.

Resynchronisation to an external clock requires an explicit pair of anchors:
- media anchor ((m_0, T_m));
- external monotonic-clock anchor ((c_0, T_c));
- an epoch/generation binding and a maximum permitted correction window.

For a media timestamp (m), the nominal external-clock projection is (c_0 + operatorname{rescale}(m-m_0,T_m,T_c)), with checked subtraction, checked rescaling and checked addition. The external clock MUST be monotonic and its timebase MUST be explicit. Wall-clock time (UTC, civil time, NTP-derived display time) is not a substitute for a monotonic scheduling clock.

A resync operation either accepts the new anchor atomically or leaves the old mapping unchanged. Drift estimation and correction are separate from timestamp conversion: any rate correction MUST be represented as a bounded rational ratio with explicit limits, update interval and slew policy. No floating-point PLL or unbounded instantaneous timestamp jump is permitted as the authoritative mapping. A discontinuity or seek invalidates prior resync anchors unless a new mapping is explicitly installed.

## 8. Invalid inputs and failure atomicity

Reject, without mutating clock state:
- non-positive, non-reduced or out-of-range timebases;
- raw wrap counters outside their declared modulus;
- wrap widths outside 1..63, half-range ambiguity or out-of-window displacement;
- arithmetic overflow or unsupported intermediate range;
- missing stream/epoch/generation identity;
- implicit cross-epoch comparison or mapping;
- negative duration, and zero duration where a known presented-frame duration must be positive;
- non-monotonic external clock observations where monotonicity is required;
- stale seek-generation updates;
- unsupported rounding or discontinuity policy values.

Error reporting MUST be stable and machine-readable, MUST NOT include untrusted payload text, and MUST distinguish invalid metadata, inexact conversion, overflow, ambiguous wrap, out-of-window wrap, epoch mismatch, stale generation and discontinuity rejection.

## 9. Conformance corpus

`tests/media/fixtures/rational_timebase_vectors.json` is the initial machine-readable normative vector set. Integers are encoded as decimal strings to avoid loss in JSON consumers that use IEEE-754 numbers. The corpus covers exact and rounded rescaling, negative timestamps, signed limits, invalid timebases, VFR durations, wrap extension, half-range ambiguity, discontinuities, seek generations and external-clock resynchronisation.

The corpus is a specification oracle, not evidence that the current runtime implements every operation. Each future implementation must run the applicable vectors against its own code and add adversarial/property tests. The current Halyard tests cover timebase construction and integer rescaling only; they do not yet cover stateful wrap, epoch, seek or resynchronisation transitions.

## 10. Implementation gates

Before claiming a complete MC1 clock subsystem:
1. Implement typed stream/epoch/generation state and failure-atomic transitions in Capstan.
2. Implement wrap extension only behind explicit format metadata and a caller-supplied window.
3. Implement seek invalidation and stale-completion rejection.
4. Implement external monotonic-clock anchors and bounded rational drift correction.
5. Execute the full corpus against the concrete implementation; add property tests for all sign quadrants, boundary values, wrap windows, reordered packets and transition failures.
6. Prove or mechanically check arithmetic bounds and transition invariants against the concrete implementation. Keep model-only proofs separate from implementation refinement.
7. Document each supported container's timestamp width, epoch/discontinuity rules, edit-list semantics, PTS/DTS constraints and timebase provenance.

Until these gates pass, status remains **partial specification and partial integer-rescaling implementation**, not a complete clock implementation or a verified media scheduler.
