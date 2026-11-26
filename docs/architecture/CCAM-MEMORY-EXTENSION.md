# CCAM v0.2 proposal: bounded scratch regions

**Status:** design proposal only; not part of normative CCAM v0.1.  
**Purpose:** specify a minimal deterministic memory extension for Capstan-native bounded workspaces without raw pointers, host allocation semantics or implicit collection.  
**Depends on:** [CCAM v0.1](CCAM.md), [C-Free bounded scratch contract](../keel/C-FREE-BOUNDED-SCRATCH.md), [C-Free execution](C-FREE-EXECUTION.md).\n**Security target:** [CCAM v0.2 memory-safety contract](CCAM-MEMORY-SECURITY-CONTRACT.md). The contract defines the required language guarantee and release gates; it does not certify this proposal or the current prototype.

## 1. Version boundary

CCAM v0.1 remains unchanged. This document proposes a separately versioned v0.2 profile. A v0.1 decoder MUST reject v0.2-only value tags and instructions. A v0.2 program MUST declare its machine version in its external envelope; implementations MUST NOT infer the version from unfamiliar opcodes.

The first v0.2 profile adds only fixed-capacity byte regions, opaque region and typed-view capabilities, checked reservation, typed scalar loads/stores, reset and close. It does not add general heap objects, references, strings, aggregates, garbage collection, shared memory, atomics, IO or foreign calls.

## 2. Fixed scalar layouts

A region is an abstract byte sequence whose bytes are integers in 0..255. No host pointer, host endianness, C object layout, allocator address or physical page size is observable.

The initial closed layout table is:

| Layout | Size | Alignment | Encoding |
|---|---:|---:|---|
| i64 | 8 bytes | 8 bytes | two's-complement, little-endian |
| bool | 1 byte | 1 byte | exactly 0x00 or 0x01 |

Padding between reservations is charged to the region cursor. No padding exists inside either scalar. These are CCAM semantics, not assumptions about a target ABI. Aggregate layouts require a later versioned extension.

## 3. Value and ownership model

The value domain extends v0.1 with opaque RegionCap and ViewCap values. A region capability identifies a region generation but exposes no numeric address. A view capability identifies a region generation, byte offset, element count and scalar layout. Neither capability can be converted to an integer or compared as an integer.

Each region-table entry records a unique identity, generation, fixed capacity, used cursor, owner frame, open/closed state and abstract byte storage. The region table is itself bounded.

Initial ownership restrictions deliberately avoid a borrow checker:
- A region is created and used only by its creating function frame.
- Region and view capabilities cannot be parameters or return values.
- Calls cannot receive capabilities.
- Capabilities cannot be stored in persistent/global state.
- Generic move cannot copy a region capability.
- Closing or leaving the creating frame invalidates all capabilities.
- Frame exit closes any still-open regions it owns.

This means the first profile does not support helper functions accepting scratch views. Such support requires a separately specified borrow/region-passing model.

## 4. Machine state and limits

The v0.2 state adds a bounded region table, unique identity source, live-region count, aggregate live logical capacity, configured maxRegions and maxRegionBytes.

For every open region:
- 0 <= used <= capacity;
- its owner frame is live;
- all accepted views match its identity and generation;
- every view interval lies within the reserved prefix;
- aggregate live capacity is no greater than maxRegionBytes;
- live region count is no greater than maxRegions.

Region-table metadata and evaluator bookkeeping require separate explicit bounds. The logical capacity budget is not a claim about RSS, allocator metadata, page rounding or fragmentation.

## 5. Proposed instruction set

Every instruction uses the closed-object schema discipline of v0.1. All register indices are checked against the current function. The proposed v0.2 register tags are region, view_i and view_b, in addition to int and bool.

| Opcode | Exact fields | Static types | Semantics |
|---|---|---|---|
| region_new | op,dst,capacity | dst:region; capacity:nonnegative integer | Create fixed-capacity region owned by current frame |
| region_reserve_i | op,dst,region,count | dst:view_i; region:region | Reserve count i64 slots, aligned to 8 |
| region_reserve_b | op,dst,region,count | dst:view_b; region:region | Reserve count bool slots, aligned to 1 |
| view_load_i | op,dst,view,index | dst:int; view:view_i; index:int | Load signed-64 element |
| view_store_i | op,view,index,src | view:view_i; index:int; src:int | Store signed-64 element |
| view_load_b | op,dst,view,index | dst:bool; view:view_b; index:int | Load canonical boolean |
| view_store_b | op,view,index,src | view:view_b; index:int; src:bool | Store canonical boolean |
| region_reset | op,region | region:region | Invalidate all views and reset cursor |
| region_close | op,region | region:region | Close region and invalidate capabilities |

The capacity operand should ultimately be an integer register rather than an unbounded JSON literal. This is an open choice pending schema review. Counts and indices are signed-64 values and MUST be nonnegative at execution.

There is no capability equality, arithmetic, pointer cast, raw byte load/store, or capability-returning instruction. A zero-count view is valid but cannot be indexed.

## 6. Transition semantics

### 6.1 Region creation

Creation checks, in order: capacity validity; region-table availability; checked aggregate-capacity addition; aggregate limit; backing admission. Only after every check succeeds does it create a region and initialise the destination capability register.

A failed creation leaves the region table, aggregate counter and destination register unchanged. The reference evaluator must support deterministic admission-failure injection. A native backend may additionally encounter physical allocation failure, which must map to the same observable allocation_failed outcome.

### 6.2 Reservation

For element size s, alignment a, count n and current cursor u:
1. Require n >= 0.
2. Compute bytes = n*s with checked arithmetic.
3. Compute start = u + ((a - (u mod a)) mod a), with checked arithmetic.
4. Compute end = start + bytes with checked arithmetic.
5. Require end <= capacity.
6. Only then commit used = end and write the view capability.

Alignment padding is charged. Failed reservation leaves both cursor and destination unchanged. The initial alignments are exactly 1 and 8. All intermediate arithmetic uses a specified unsigned byte-count domain, never host signed overflow.

### 6.3 Load and store

For index i, first require 0 <= i < view.count. Calculate relative offset i*s and absolute offset view.offset+relative with checked arithmetic. Then validate capability identity/generation, open state, owner, layout and full interval containment.

i64 loads/stores encode exactly eight little-endian bytes using two's-complement interpretation. Boolean loads accept only 0 or 1; any other byte is scratch_corrupt_bool. Stores write exactly 0 or 1. A load changes its destination only after successful validation and decoding. A store is one atomic abstract transition; partial byte updates are unobservable.

### 6.4 Reset, close and linearity

Reset increments the generation with checked arithmetic, sets used to zero and invalidates all old views. The region register named by reset is refreshed to the new generation. The initial profile prohibits capability copies, so no other register can retain a valid old region handle.

Close marks the region closed, invalidates all capabilities and releases its logical capacity from aggregate accounting. Double close and stale use trap deterministically. Frame exit closes every remaining region owned by that frame.

A region capability is linear: it cannot be copied, passed, returned or overwritten while live. Static validation must enforce one live region register per created region and explicit close on every reachable normal return. Frame-exit cleanup is the safety backstop for traps and termination.

## 7. Traps and error precedence

Proposed dynamic traps:
- allocation_failed;
- region_limit_exceeded;
- region_closed;
- stale_region_capability;
- wrong_region_owner;
- scratch_exhausted;
- scratch_range_error;
- scratch_arithmetic_overflow;
- scratch_type_mismatch;
- scratch_corrupt_bool.

Malformed schemas, unknown opcodes, static type mismatches, copied linear capabilities, invalid control flow and malformed limits remain validation errors, not runtime traps.

Recommended dynamic check order: validated register/index access; initialised-register read; capability identity/generation; open state; owner; view layout; element index; checked offset arithmetic; storage access. This order must be frozen before v0.2 acceptance. Failed operations never partially mutate state.

## 8. Static validation

The v0.2 validator must reject:
- v0.2 tags/opcodes in v0.1 programs;
- unknown v0.2 tags/opcodes;
- wrong register types or invalid indices;
- capability use before definite initialization;
- capability arguments, returns or generic moves;
- statically provable use after close/reset;
- normal return paths with a live region;
- control-flow paths that fall off a function;
- branch joins where incoming region states disagree.

Region lifecycle is a control-flow dataflow problem. At every CFG join, the region state must agree across incoming paths. If the validator cannot establish one valid state within a fixed analysis budget, it rejects the program. Runtime generation, owner and open-state checks remain mandatory.

The first validator should conservatively reject loops containing region lifecycle operations unless a bounded finite-state fixpoint proves their behaviour.

## 9. Formal invariants

- M1 Capacity: each open region satisfies 0 <= used <= capacity.
- M2 Aggregate: sum of open-region capacities <= maxRegionBytes.
- M3 Table: open-region count <= maxRegions.
- M4 Identity: live identities are unique.
- M5 Ownership: every open region has one live owner frame.
- M6 View validity: every accepted access matches identity, generation, state, owner, layout and interval.
- M7 Reservation atomicity: failed reserve leaves cursor and destination unchanged.
- M8 Creation atomicity: failed creation leaves table, accounting and destination unchanged.
- M9 Alignment: each view offset satisfies its layout alignment.
- M10 Non-overlap: reservations in one generation have disjoint nonempty intervals.
- M11 Reset invalidation: reset invalidates every view from the prior generation.
- M12 Close invalidation: close invalidates all capabilities for that generation.
- M13 Scalar fidelity: i64 round-trips exactly; bool remains canonical.
- M14 Frame cleanup: terminated frames leave no open owned regions.
- M15 No hidden growth: reserve, view access, reset and close allocate no memory.
- M16 Linearity: no two live region registers designate the same region generation.

Proof sequence: checked alignment/extent arithmetic; creation and reservation preservation; view containment and non-overlap; generation invalidation; frame cleanup; scalar round trips; reference-evaluator refinement; native instruction simulation. Error transitions must be included. Abstract proofs do not prove physical allocator admission.

## 10. Conformance and adversarial tests

Required vectors include:
- zero, one, exact-capacity and one-byte-over regions;
- region-table and aggregate-capacity exact limits and one-over;
- alignment padding at capacity boundaries;
- multiplication, alignment and end-offset overflow;
- failed create/reserve state snapshots proving atomicity;
- zero-count views and attempted access;
- negative, count-equal and maximum indices;
- i64 minimum, maximum, -1, 0 and 1 round trips;
- bool round trips and injected noncanonical bytes;
- stale view after reset, stale region capability, use after close and double close;
- wrong owner and frame-exit cleanup on normal return and trap;
- copied capability, call escape and return escape rejected statically;
- inconsistent branch-join states rejected;
- deterministic allocation failure at every admission point.

Use an independent arbitrary-precision oracle for byte arithmetic and encoding. Generate bounded random operation traces and compare every observable transition, including failed-operation atomicity. Serialize failing seeds and traces. Run identical vectors against the reference evaluator and each native backend.

## 11. Implementation sequence

| Work item | Deliverable | Gate |
|---|---|---|
| CCAM-MEM-01 | Freeze value/layout/region semantics and error precedence | M-SPEC |
| CCAM-MEM-02 | Extend reference machine state and Capstan evaluator | M-REF |
| CCAM-MEM-03 | Add v0.2 schema and CFG/linear-capability validator | M-VALID |
| CCAM-MEM-04 | Differential and adversarial conformance corpus | M-CONF |
| CCAM-MEM-05 | Lean transition model and preservation proofs | M-PROOF |
| CCAM-MEM-06 | Native backend lowering with bounded admission | M-NATIVE |
| CCAM-MEM-07 | Keel maximum-mesh workspace consumer | M-KEEL |

No item is complete by publication of this proposal. The next coding milestone is a Capstan reference-transition prototype while leaving the v0.1 evaluator unchanged.

## 12. Open decisions

1. Capacity operand: immediate literal or integer register. Recommendation: integer register, read once before admission.
2. Allocation failure: deterministic injected admission result in the reference evaluator, plus native allocation failure mapped to the same outcome.
3. Reset: refresh the named region register and invalidate every old view; capability copying remains forbidden.
4. Loop analysis: bounded CFG fixpoint; reject ambiguity or budget exhaustion.
5. Byte encoding: little-endian two's-complement as abstract CCAM semantics, independent of host layout.

These are review decisions, not silently ratified language semantics.

## 13. Executable prototype boundary (2026-11-25)

The Capstan-native artifacts now include three deliberately separate layers:

- `verification/ccam_memory_reservation.cap`: checked reservation arithmetic.
- `verification/ccam_memory_region_model.cap`: single-region ownership and lifecycle transitions.
- `verification/ccam_memory_store_model.cap`: bounded multi-region table and explicit byte-vector reference storage.

The current store model fixes prototype limits at eight table slots and 4096
aggregate logical bytes. It reuses closed table slots, preserves monotonically
increasing region identities, checks aggregate capacity before admission, and
performs deterministic injected admission failure at every byte-vector
initialisation boundary (including before the first byte and after the final
byte) before changing the table, identity source, or accounting. Closing
wipes the complete backing byte vector before releasing the original capacity
from the aggregate ledger. Reset increments generation and clears the backing
bytes while invalidating all prior views.

Scalar storage is implemented in the prototype, not merely described:
i64 is encoded and decoded as eight little-endian two's-complement bytes;
boolean stores write exactly 0 or 1 and loads trap on any other byte. The
independent Python oracle compares generated signed-64 vectors and every
resulting byte against Python arbitrary-precision integer encoding.

These artifacts do **not** complete CCAM-MEM-02 or any later gate. They are
Capstan reference models, not the normative v0.2 machine, a production
allocator, a physical-allocation guarantee, or an opaque capability system.
The current fault injection tests every modeled byte-vector admission boundary;
it does not intercept a host allocator failure inside Capstan's own list runtime.
An isolated Capstan-native CFG lifecycle validator prototype now checks
region-register use, overwrite, close, normal-return leaks and exact join-state
equality, with a bounded worklist and conservative rejection of lifecycle-
changing loops. It is tested by the standard runner but is not yet connected to
CCAM decoding, the v0.2 opcode/type schema or evaluator. It now tracks bounded view registers and their owning region/generation: view
creation requires a live region, view use/drop requires a live matching
owner-generation, and region reset/close invalidates every derived view in the
abstract state. Region-register reuse advances the abstract generation rather
than resetting it, preventing generation ABA in this model. Branch joins compare
view liveness, owner and generation as part of the complete state. It conservatively permits at most one live view per region until mutability and
disjoint-range proofs exist, and explicitly rejects view-copy, view-escape and
call instructions rather than assuming they are safe. It does not yet model
interprocedural summaries or implement frame-unwind cleanup. The
normative v0.2 schema/evaluator, complete linear-capability integration,
frame-unwind cleanup, formal proofs and native backend lowering remain
outstanding. CCAM v0.1 files and semantics are unchanged.
