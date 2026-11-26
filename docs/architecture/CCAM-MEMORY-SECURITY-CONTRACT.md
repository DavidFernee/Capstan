# CCAM v0.2 memory-safety contract

**Status:** normative security target for the proposed v0.2 profile; not yet an
implemented or proven language guarantee. CCAM v0.1 is unchanged. The profile
must not be advertised as production-safe until every acceptance gate below
has evidence attached to the exact release commit.

## 1. Guarantee and scope

For a program accepted by the complete v0.2 validator and executed by a
conforming v0.2 machine, every memory operation is confined to a live,
authorised region and a live, generation-matched view. A capability cannot be
forged, duplicated, moved into an untracked storage location, used by a
non-owner frame, or used after reset, close, or owner-frame exit. Every region
is invalidated and its complete backing capacity is wiped before its owner
frame is discarded, regardless of whether that frame exits by normal return,
trap, cancellation, or resource-limit termination.

This is a conditional language guarantee over the defined v0.2 machine and
accepted program subset. It does not claim that arbitrary unsafe native code,
a compromised compiler/runtime, hardware faults, physical remanence outside
the specified storage model, side channels, or an incorrect host allocator are
made safe. Those require separate threat models and assurance evidence.

The implementation must fail closed: if validation, abstract interpretation,
resource admission, or a required runtime invariant cannot be completed within
its specified bound, the program is rejected or execution terminates with a
defined failure. No unknown opcode, type, effect, capability state, or schema
field is accepted by default.

## 2. Capability discipline

The v0.2 profile has only two capability classes:

- RegionCap: an opaque, non-forgeable authority for one region identity and
  generation, owned by exactly one live frame.
- ViewCap: an opaque, non-forgeable authority for one reserved interval,
  scalar layout, region identity and generation, also bound to that owner.

Capabilities are not integers, pointers, serialisable values, or ordinary
copyable values. They have no equality, ordering, arithmetic, formatting,
reflection, or raw-byte representation operation.

Until a formally specified borrow system exists, v0.2 is intentionally
restrictive:

1. A region is created, used, reset and closed only by its creating frame.
2. Region and view capabilities cannot be parameters, call arguments, return
   values, closure captures, globals, fields, collection elements, or persisted
   data.
3. Generic move, assignment, destructuring, pattern matching, or implicit
   coercion cannot duplicate or transfer a capability.
4. A destination containing a live capability cannot be overwritten.
5. At most one live view may exist for a region. This deliberately sacrifices
   concurrency and disjoint-view performance until alias and mutability
   proofs exist.
6. Reset increments the region generation and invalidates every view from the
   previous generation. Close invalidates the region and every derived view.
7. Region identity and generation counters use checked, non-wrapping arithmetic.
   Exhaustion fails before state mutation; identifiers are never recycled.

A compiler or validator that cannot prove these restrictions rejects the
program. Runtime owner, identity, generation, open-state, layout and bounds
checks remain mandatory defense in depth.

## 3. Control-flow typing judgement

The static analysis state for a function is a finite mapping:

    Γ = (Regions, Views)

Each region register has one of Uninit, Live(id, generation), or
Closed(id, generation). Each view register has one of Uninit,
Live(region-register, id, generation, interval, layout), or Invalid.

The analysis is path-sensitive over the validated control-flow graph.
Every reachable predecessor of a join must produce exactly the same
capability state. A validator may later adopt a sound lattice join only if it
proves that the join cannot permit a capability operation unavailable on any
incoming path. The initial profile rejects disagreement.

Required transfer rules:

- region_new: destination must not contain a live capability; produce a
  fresh identity and generation, with the current frame as owner.
- region_reset: source must be live; checked-increment generation; invalidate
  every view derived from that region; retain the region capability at the new
  generation.
- region_close: source must be live; invalidate all derived views and the
  region capability; release its accounting only after secure wipe completes.
- view_new: region must be live and owned by the current frame; destination
  must not be live; no other live view may refer to the region.
- view_use: view must be live, its owner region must be live, and identity
  and generation must match exactly.
- view_drop: same checks as view_use, then consume the view.
- call: capabilities may not appear in arguments, destinations, or any
  state visible to the callee. Until interprocedural summaries are proved,
  v0.2 rejects a call if the caller has any live region or view.
- return: no live region or view may remain in the returning frame.
- trap and every other terminal outcome: invoke the mandatory frame-unwind
  transition before discarding the frame.

The CFG validator must inspect every instruction's closed schema, including
unreachable instructions, while applying lifecycle transfer rules to every
reachable path. Analysis has explicit instruction, register, state and memory
budgets. Budget exhaustion is rejection, never acceptance.

## 4. Runtime invariants

For every open region:

- 0 <= used <= capacity == backing_bytes.length;
- exactly one live owner frame exists;
- its identity is unique among all regions ever admitted by the machine;
- its generation is positive and has never wrapped;
- live region count and aggregate live capacity remain within configured
  limits.

For every accepted view:

- the referenced region exists, is open, and has the same identity/generation;
- the current frame is the recorded owner;
- the interval is wholly inside the successfully reserved prefix;
- size, alignment and element layout match a closed scalar-layout table;
- index multiplication, offset addition and end calculation are checked before
  any backing-store access;
- no other live view aliases the region in this profile.

Every failed operation is failure-atomic: it leaves capability registers,
region table, counters, cursor and bytes unchanged, except for an explicitly
specified terminal cleanup transition.

## 5. Frame-unwind semantics

Frame exit is a machine transition, not a compiler-generated best-effort
epilogue. It applies on normal return, explicit trap, arithmetic or bounds trap,
call-depth/step limit, cancellation, and abnormal termination represented by
the CCAM machine.

Before a frame is removed:

1. Identify every open region whose owner is that frame.
2. Preflight the complete cleanup set and aggregate accounting. If metadata is
   inconsistent, do not partially mutate the set; enter a fatal machine
   integrity failure.
3. Wipe every byte in each backing capacity, including unused tail bytes and
   alignment padding.
4. Invalidate all region and view capabilities associated with those regions.
5. Release aggregate capacity and live-region accounting.
6. Only then remove the frame.

Cleanup must be idempotent. A second cleanup finds no open regions and changes
no accounting. Cleanup of one frame must not affect another frame's regions.
The runtime must not expose partially cleaned state to another instruction.

The reference model in verification/ccam_memory_unwind_model.cap specifies
and tests the cleanup-set preflight, owner isolation, complete wiping,
idempotence and accounting behavior. The current multi-function evaluator in
verification/ccam_calls.cap now assigns monotonic frame identities, invokes
the unwind transition before successful frame return, and invokes it for every
machine trap across all active frames. Tests exercise entry-frame cleanup and
nested caller/callee cleanup. However, v0.2 memory instructions are not yet
part of the executable instruction schema, so the evaluator currently owns an
empty manager except in direct integration tests that seed it. This is a
partial integration milestone, not the complete language guarantee.

## 6. Security theorem target

The principal theorem is CCAM v0.2 Memory Safety and Capability Confinement:

For every validated v0.2 program P, every conforming initial machine state
S0, and every finite execution prefix S0 ->* S, if execution has not
terminated in a defined fatal integrity failure, then:

1. Every memory read/write performed in the prefix is within the byte interval
   reserved by a live view whose identity, generation, owner and layout match
   the active frame and region.
2. No capability is duplicated, forged, used after invalidation, or observed
   outside its permitted owner frame.
3. Every open region is charged exactly once to the aggregate capacity and
   region-count budgets.
4. Every frame removed from the machine has had all its owned regions fully
   wiped and invalidated.
5. Failed memory transitions preserve the pre-transition state.

The proof is decomposed into:
- validator soundness: accepted programs satisfy the static capability rules;
- preservation: every nonterminal machine step preserves typing and memory
  invariants;
- progress-or-trap: a well-formed state either takes one defined step or
  terminates with a specified trap, never an undefined memory operation;
- cleanup correctness: frame unwind wipes and releases exactly the owned set;
- refinement: the executable Capstan evaluator simulates the abstract
  transition relation in both successful and failing cases;
- backend simulation: every native lowering preserves the abstract memory
  operation and cleanup semantics.

Tests, fuzzing and model checking are supporting evidence; they are not
substitutes for these proofs.

## 7. Mandatory release gates

The v0.2 memory profile MUST NOT be declared conforming or secure until all
gates pass on the same immutable source revision:

| Gate | Required evidence |
|---|---|
| SPEC | Closed v0.2 schemas, exact trap/error precedence, ownership and cleanup semantics frozen |
| VALID | Integrated whole-program validator; sound CFG/linear-capability analysis; negative corpus |
| REF | Capstan evaluator implements every v0.2 transition and mandatory frame unwind |
| CONF | Deterministic conformance vectors, independent arbitrary-precision oracle, fuzz and mutation campaigns |
| PROOF | Machine-checked validator soundness, preservation, progress-or-trap, cleanup and refinement results |
| NATIVE | Backend simulation proof and sanitizer/ABI/resource tests for each supported target |
| SUPPLY | Reproducible build, pinned dependencies, artifact provenance and review of the complete trusted computing base |

No gate can be waived by a passing unit test, a green CI badge, or a successful
demo. A change to the validator, evaluator, schema, compiler lowering, runtime,
or proof assumptions invalidates the relevant evidence and reruns the gates.

## 8. Current implementation status

At the time this contract is introduced:

- CCAM v0.1 remains unchanged.
- The v0.2 byte-store and lifecycle models are Capstan-native prototypes.
- The isolated CFG validator models bounded region/view registers and rejects
  aliases, escapes and unmodelled calls.
- The frame-unwind model specifies and tests complete wiping and
  failure-atomic accounting preflight.
- The multi-function evaluator now assigns monotonic frame identities and
  invokes cleanup on successful returns and all trap paths, including nested
  frames. Memory opcodes and the static capability validator remain
  disconnected from that evaluator.
- The models are not yet integrated into a normative v0.2 decoder,
  whole-program capability validator or native backend.
- No machine-checked theorem listed above has yet been established.

This document defines the security target and release criteria. It does not
certify the current implementation.
