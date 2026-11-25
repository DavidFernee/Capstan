# Allocator and collector abstract specification

**Status:** initial normative target contract; selected arithmetic and page-release fragments are represented in the separate Lean model, but this specification is not yet fully mechanised and no C refinement is proved.  
**Implementation baseline:** `bc0a283df5a964e7340cd48ec8ce4a1e8fb3acde`.  
**Primary implementation:** `runtime/capstan_gc.h`.

This specification records the state that a formal model must represent. It is not a
claim that the current C implementation satisfies every invariant below.

## 1. Machine domains and constants

The model must parameterise the machine word width, `size_t` maximum, pointer width,
page size, class-size table, and allocation-kind count. It must not assume that the host
used to run a proof has the same word width as every supported target.

The implementation currently has 64 KiB pages, fourteen small-object size classes
(16 through 2048 bytes), and three allocation kinds: pointer-bearing, pointer-free
atomic, and pointer-free secret. Objects larger than the largest small-object class
are tracked individually.

All arithmetic in the model is mathematical integer arithmetic accompanied by explicit
machine-range preconditions and checked-operation results. Modulo-`size_t` arithmetic
must never be substituted for checked arithmetic.

## 2. Abstract state

A collector state contains at least:

- page records: stable page identity, base address, object size/class, slot count,
  allocation bitmap, mark bitmap, allocation kind, spare flag and released flag;
- slot payload state, including whether the payload is zero and whether allocator
  metadata is stored in the payload;
- the per-kind/per-class free-list sequences;
- page-table mapping and capacity;
- spare-page sequence and page-array membership;
- sorted large-object records, including base, size, kind and mark state;
- registered root slots and the abstract pointer graph they expose;
- mark work stack and its capacity;
- managed-heap accounting, live-byte count, and saturating statistics;
- external operation outcomes for backing allocation, page advice/release and free.

Page and object identities in the mathematical model are not raw C pointers. A separate
representation relation must connect identities to concrete addresses and byte ranges.

## 3. Slot states

Every slot has exactly one logical state:

- `AllocatedUnmarked`: allocated and not yet marked in the current collection;
- `AllocatedMarked`: allocated and marked in the current collection;
- `FreeListed`: unallocated and represented exactly once in its matching free list;
- `SecretErasedFree`: secret payload has been completely erased and the slot is
  represented by out-of-line allocator metadata;
- `PageSpare`: its page is empty and the page is present exactly once in the spare list.

The model must distinguish page-level spare/released state from slot-level state.
An empty page's slots are not simultaneously entries in active per-class free lists.
The current implementation uses in-band free-list links for ordinary small-object kinds.
Secret-kind pages instead use an out-of-line `free_slots` index array; page formatting
wipes the page before populating that array, and sweep wipes an allocated secret slot
before publishing its index as free. This is a material implementation improvement over
the historical in-band secret-list design. The proof obligation is now to establish the
wipe-before-publication/reuse ordering, array bounds and representation correspondence;
source inspection alone is not a machine-checked erasure theorem.

## 4. Transition system

Every operation is a transition with explicit preconditions, postconditions and failure
outcomes. At minimum model:

- checked addition, multiplication, and capacity growth; checked arithmetic overflow has a terminal fatal outcome and never returns a wrapped value;
- page acquisition, metadata construction and page-table insertion;
- slot allocation and free-list removal;
- root registration;
- mark candidate recognition for small and large objects;
- mark-stack push, scan and drain;
- collection entry, mark phase, small-object sweep and large-object sweep;
- page movement to spare storage;
- page backing release/advice and later recommit/reuse;
- process-fatal metadata/object/page allocation failures;
- secret wipe, free-list publication and large-object release.

A transition that calls an OS primitive must consume an explicit result. A successful
result and a failed result are distinct transitions. State and accounting may change
only as specified for that result. In particular, page accounting must not treat a
failed `madvise` as a successful release.

### Allocation and metadata failures

The present runtime's `cap_gc_meta` and backing allocation paths terminate on
allocation failure. The abstract semantics therefore model a terminal
`OutOfMemory` outcome for these paths, not a recoverable return to the caller.
If recoverable allocation is introduced, it requires a new transition contract and
failure-atomicity proof; it must not be inferred from this model.

### OS page advice

At historical baseline `bc0a283df5a964e7340cd48ec8ce4a1e8fb3acde`, `cap_gc_release`
ignored the return value of `madvise`, then set `released` and subtracted one page from
`cap_gc.heap`. That defect has since been corrected in the inspected mainline snapshot
`9674d810c0f16c415b1c90ace9a4b5ac89cf2138`: `cap_gc_release` records the advice result
and `cap_gc_account_release` leaves the page accounted and retryable when advice fails.
This code-level correction removes the original blocker but does not itself prove the C
implementation refines the Lean release model. The intended contract remains:

- on successful advice, the page may transition to `ReleasedSpare` and accounting
  decreases by exactly one page;
- on failed advice, the page remains accounted as retained and the released flag
  remains false; the implementation must take a documented fail-stop or retry path.

The formal model must not prove the intended contract against the present code without
an implementation correction and a refinement check.

## 5. Core invariants

The target invariant set is:

1. **Slot partition:** every slot in every formatted page is in exactly one logical
   slot state.
2. **Page ownership:** every managed page has exactly one page record and one page-table
   mapping for its page number.
3. **Free-list soundness:** every free-list element is an aligned slot in a page with
   matching kind and size class, and is not allocated or marked.
4. **Free-list uniqueness:** no slot occurs more than once in any free list or across
   incompatible free lists.
5. **Free-list completeness:** every reusable slot in an active page occurs exactly
   once in its matching free list.
6. **Spare-page separation:** every spare page occurs exactly once in the spare list
   and contributes no slot to an active free list.
7. **Page-table validity:** capacity is a nonzero power of two when populated; entries
   are unique; probing terminates within capacity under the occupancy invariant.
8. **Large-object validity:** records are strictly ordered by base, ranges do not
   overlap, and every registered allocation occurs exactly once.
9. **Mark validity:** only allocated slots/large objects can be marked; marks are reset
   at the collection boundary.
10. **Mark-stack validity:** stack depth never exceeds capacity and each work item
    describes a valid allocated object range.
11. **Accounting:** managed-heap bytes equal retained page backing plus sizes of
    registered large allocations, under the exact platform operation semantics.
12. **Arithmetic safety:** all allocation sizes, capacities, indices, offsets and
    accounting updates are within their machine domains and do not wrap.
13. **Secret lifecycle:** a secret payload is not made reusable or released until the
    required complete, non-elidable wipe has occurred; allocator metadata does not
    overwrite the erased payload.
14. **Reachability preservation:** no object reachable from the model's valid root
    set through pointer-bearing objects is reclaimed by sweep.

These are target invariants, not statements of current implementation conformance.

## 6. Reachability theorem boundary

The abstract marking theorem can state: if the initial root set contains every live
program reference under the chosen abstract pointer semantics, and scanning every
pointer-bearing object enumerates every outgoing reference, then after mark-stack
drain every object reachable from those roots is marked; sweep therefore does not
reclaim a reachable object.

That theorem does not establish that the concrete C runtime discovers every machine
root. The concrete refinement obligation must separately account for:

- registered global-root slot correctness and lifetime;
- stack bounds and stack direction for each supported platform;
- callee-saved register spilling and compiler/ABI behaviour around `setjmp`;
- aligned machine-word scanning and permitted pointer representations;
- generated C object layout and all pointer-bearing stores;
- the C abstract machine and compiler transformations;
- OS and libc contracts for allocation and page operations.

Any unproved premise remains an explicit assumption in the assurance report.

### Physical scanning and stale container slots

The concrete scanner reads every machine word in the allocated byte range of a
pointer-bearing object; it does not know a list/map's logical length or which backing
slots the language-level container considers vacant. A pointer left in a vacated backing
slot can therefore remain a conservative edge and retain its referent. The abstract
model must distinguish logical container membership from physical payload words scanned
by the collector. A removal operation eliminates a graph edge for collection purposes
only when the corresponding physical word is cleared or overwritten (subject to the
actual representation and aliasing rules). This is a retention/lifetime precision issue,
not permission to reclaim an object that remains physically discoverable.

The concrete implementation workstream has identified stale-slot hygiene in list/map
mutation paths as a separate remediation target. The formal model must not assume that
logical deletion automatically clears scanned bytes.

## 7. Secret-erasure boundary

The collector's secret allocation kind is pointer-free and is wiped only when an
unreachable object is collected. The model must not equate unreachability with prompt
destruction. It must distinguish:

- wiping the payload bytes of a particular allocation;
- preventing allocator metadata from reintroducing nonzero bytes into the freed slot;
- copies elsewhere in registers, stack, ordinary heap, files, kernel buffers, swap,
  snapshots, crash dumps or hardware caches.

The first two can be implementation properties. The third is outside the collector's
control unless separately designed and proved. No system-wide erasure claim follows.

## 8. Refinement requirement

A model theorem is promoted to an implementation theorem only with a checked or
reviewable refinement argument mapping each concrete C state and operation to the
abstract state and transition. The relation must cover:

- concrete metadata arrays, bitmaps, intrusive free-list links and pointer arithmetic;
- allocation and release ordering, including all error branches;
- memory ownership and aliasing of C objects;
- the exact compiler/ABI and platform assumptions relied upon.

A diagram, test suite, matching function names, or informal statement of correspondence
is not by itself a refinement proof.

## Current implementation delta against the historical baseline

The formal specification baseline above is historical. A source inspection of mainline
commit `9674d810c0f16c415b1c90ace9a4b5ac89cf2138` confirms two relevant runtime changes:

- Page release now consumes the `madvise` result; failed advice leaves the page unreleased
  and accounted, while successful advice updates the release flag and heap counter.
- Secret small-object pages use out-of-line `free_slots` indices; formatting wipes the
  page, and sweep wipes an allocated secret payload before publishing its slot index.

These observations update the implementation-risk assessment, not the proof status.
The C operations still require a formal representation relation, transition refinement,
and tests/assurance for volatile wiping, OS semantics and metadata invariants.
