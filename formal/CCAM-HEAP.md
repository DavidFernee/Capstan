# CCAM region heap: semantic contract and proof bridge

**Status:** experimental contract; the Capstan-written prototype is not yet a
refinement of this model and is not part of normative CCAM v0.1.
**Implementation under study:** `verification/ccam_heap.cap` on
`ccam/region-heap-prototype`.
**Formal model:** `formal/CCAMHeap.lean`.

## 1. Scope and non-claims

The prototype models a bounded, process-lifetime region heap. It does not provide
individual deallocation, tracing collection, a process-wide memory bound, or
concurrency safety. It is not yet connected to the source compiler, executable
CCAM machine, or native backend. It is not evidence that the compiler bootstrap
is C-free.

**Language-semantics blocker:** the current heap API takes `CCAMHeap` values and
mutates their fields and contained lists. This relies on struct/reference and
collection aliasing behaviour. The current CCAM supported subset explicitly
excludes structs and mutable collections; the reference-semantics work in #255
is a mathematical model, not yet a compiler/runtime correspondence proof.
Consequently the current `.cap` tests are prototype regression vectors only.
They do not establish that this heap API is a valid implementation in the
supported CCAM subset. Before promotion, either (a) prove the required source
reference/collection semantics and compiler/runtime refinement, or (b) redesign
the API around explicit state-in/state-out transitions using only already
supported value semantics. GC lifetime and stale-reference prevention are
additional obligations.

The current implementation's integer `heap_token` is a region identifier, not
an unforgeable capability. Equality checks prevent accidental cross-region
confusion when callers use issued handles correctly; they do not defend against
a caller able to manufacture or guess tokens. No capability-security claim is
permitted until capability issuance, opacity, attenuation and runtime
representation are specified and enforced.

## 2. Abstract state

A region state contains:
- a region authority token and a unique region identity (issuance and non-forgeability are external obligations);
- an object table with monotonically allocated object identities;
- nominal object descriptors and field/element type descriptors;
- logical bytes charged, logical byte limit, object count and object limit;
- per-operation work/fuel accounting;
- the target's explicit allocation and failure outcomes.

Object identities are meaningful only together with their owning region.
A reference from region A is invalid in region B, even if both regions contain
an object with the same numeric object identity.

## 3. Reference typing

A reference field is not adequately typed by a generic `REF` tag. The final
contract requires a nominal target descriptor (or an explicitly modelled
reference supertype) and checks the descriptor of the resolved target object.
A reference to a different record descriptor, array kind, or byte-buffer kind
must be rejected before mutation. Descriptor identifiers are module-scoped
nominal identities; collisions across modules must be prevented by canonical
link-time identity, not assumed away.

The current prototype checks nominal target descriptors for both record reference
fields and reference-typed array elements. The descriptor namespace is still a local
integer convention; canonical cross-module identity and a compiler-generated descriptor
table remain open. Array reads recheck the stored value against the array descriptor,
and writes/append reject mismatched targets before mutation.

## 4. Resource model

The current `bytes_used` counter is a **logical heap charge**, calculated from
declared headers and slots. It is not a bound on host memory, RSS, allocator
metadata, list capacity, string-copy temporaries, stack use, or the compiler
process itself.

The resource contract separates at least:
- logical region bytes;
- maximum object count and per-object dimensions;
- cumulative abstract work units (currently a conservative prototype counter
  for record/array construction and byte copying, not a machine-instruction
  bound);
- maximum admitted temporary bytes and the largest declared temporary request;
- host/runtime overhead, either bounded by a target-specific representation
  theorem or explicitly outside the guarantee.

The prototype now exposes `ccam_heap_create_bounded` so callers can set
independent work and temporary limits. Allocation admission checks all relevant
budgets before mutation. Record/array construction charges slot work and a
temporary slot estimate; byte allocation charges copy work and temporary bytes;
concatenation preflights cumulative work and a conservative two-buffer
temporary request (joined intermediate plus destination copy) before constructing the
joined string. This is a logical upper estimate; it does not prove the host string
implementation makes exactly two allocations. The older `ccam_heap_create` remains a compatibility wrapper
with generous fixed limits. These are logical accounting units: they do not
yet bound actual host allocator overhead, string representation expansion,
stack use, or wall-clock execution.

All charge arithmetic must be checked before allocation. Unknown cost or
overflow must fail closed. An allocation rejection must preserve the complete
abstract state, including object table, counters, identity supply and fuel
accounting, except for a separately specified diagnostic/failure counter.

## 5. Transition contract

Each operation is specified by preconditions, required authority, a state
transition, a result/trap, and a resource charge.

### Allocate

Preconditions:
- the caller possesses the capability for the target region;
- the heap invariant holds;
- the requested charge is positive and representable;
- object and logical-byte budgets admit the allocation.

Success:
- returns the previous fresh object identity;
- increments object count and identity supply exactly once;
- increments logical bytes by exactly the admitted charge;
- preserves all heap invariants.

Failure:
- returns a specified error;
- leaves heap state unchanged (failure atomicity).

### Field and array access

- Resolve region identity before object identity.
- Check object kind and nominal descriptor before index checks or mutation.
- Check index, initialisation and mutability.
- Check value type and reference target descriptor before committing a write.
- On failure, do not mutate any field, length, capacity, counters or resource ledger.

Trap precedence must be fixed by the normative operation contract and shared by
the executable evaluator, native backend and tests.

### Byte buffers

Byte strings are immutable byte sequences, not implicitly UTF-8 text. Concatenation must check lengths, logical charge, abstract copy work and declared
temporary bytes before creating the joined value. The prototype preflights those
logical dimensions, but still relies on host string concatenation. This is not a
bound on actual allocator calls, string representation expansion or RSS.

## 6. Compositional guarantee record

Every operation must eventually carry this record:

| Dimension | Required declaration |
|---|---|
| Semantics | preconditions, result, state transition and trap precedence |
| Authority | required region capability and effects |
| Types | nominal descriptors and dynamic checks remaining |
| Resources | logical bytes, object count, fuel and temporary bytes |
| Atomicity | exact state preserved on every rejected path |
| Evidence | model theorem, implementation test, refinement obligation and source revision |

Unknown authority, type, resource cost or semantic behaviour is not a weak
warning: it is a failed admission to the guaranteed subset. In particular,
the current work counter is not an instruction/fuel theorem, and the temporary
counter is not a host RSS bound.

## 7. Capability issuance and revocation model

The Lean model includes an issuer ledger with monotonically allocated serials,
an issued-serial list, and a revoked-serial ledger. A grant is model-valid only
when its region matches the issuer, its serial was issued, and its serial has
not been revoked. Issuance lemmas establish that a fresh serial is recorded and
not already revoked. Revocation is now fail-closed: cross-region and unissued
serials return `none` without changing the ledger; valid revocation invalidates
the grant, and repeated revocation is idempotent.

This is an abstract state-machine contract only. It does **not** establish
non-forgeability: Lean's public structure constructors and a runtime's exposed
integer representation are not protected by this model. The model is also not
yet wired into the allocation transition or the `.cap` heap implementation.
Promotion requires a concrete opaque-handle representation, issuer-state
protection, delegation semantics (including attenuation), revocation
propagation, and compiler/runtime refinement. A serial number must never be
treated as a secret or sufficient authority by itself.

## 8. Proof obligations

| ID | Proposition | Current status |
|---|---|---|
| HEAP-MODEL-01 | Rejected allocation preserves the complete abstract state | Lean theorem added; CI verification pending |
| HEAP-MODEL-02 | Successful allocation returns the previous identity counter | Lean theorem added; explicitly a counter result, not proof of a live-object domain; CI verification pending |
| HEAP-MODEL-03 | Successful allocation charges exactly the admitted logical bytes | Lean theorem added; CI verification pending |
| HEAP-MODEL-04 | Successful allocation preserves the logical byte limit | Lean theorem added; CI verification pending |
| HEAP-MODEL-05 | Successful allocation preserves the object-count limit | Lean theorem added; CI verification pending |
| HEAP-MODEL-06 | Successful allocation charges exact abstract work | Lean theorem added; CI verification pending |
| HEAP-MODEL-07 | Successful allocation respects temporary-byte limit | Lean theorem added; CI verification pending |
| HEAP-MODEL-08 | Successful allocation preserves the complete abstract heap invariant | Complete conjunctive Lean theorem added; CI verification pending |
| HEAP-ID-01 | A stale handle cannot resolve to a different object after slot reuse | Generational-handle model and candidate Lean theorem added; CI pending; not current GC behaviour |
| HEAP-ID-02 | A handle cannot resolve through a different slot with a matching generation | Slot-index equality check and candidate Lean theorem added; CI pending |
| HEAP-CAP-01 | Region capabilities cannot be forged, replayed or confused across regions | Abstract issued/revoked serial ledger and invalidation theorem added; non-forgeability, allocation integration, delegation and runtime refinement remain open |
| HEAP-TYPE-01 | Reference values resolve to the nominal target descriptor | Prototype checks record fields and typed reference arrays; cross-module identity/refinement open |
| HEAP-RESOURCE-01 | Logical accounting and operation work compose across calls | Prototype has cumulative bounded work admission for allocation/copy paths; complete operation coverage and machine-cost relation open |
| HEAP-RESOURCE-02 | Host allocations and temporary copies obey a target-specific bound | Prototype bounds declared temporary requests; host representation and allocator refinement open |
| HEAP-ATOMIC-01 | Every concrete rejected mutation preserves all heap state | Tests/model bridge incomplete |
| HEAP-REFINE-01 | Capstan prototype simulates the abstract transition system | Open |
| HEAP-LANG-01 | Heap API mutation patterns are justified by supported CCAM reference/collection semantics | Blocked: structs and mutable collections are excluded from current supported subset; #255 is model-only |

The model also now includes a **generational object-handle target contract**:
a handle carries region, slot and generation; resolution checks all three
components against the selected region, slot index and slot generation. Reusing
a reclaimed slot advances its generation before publishing the replacement
object. Lean theorems state
that a handle from the previous generation is rejected, the new generation
resolves, and a cross-region handle is rejected. This is a design model only:
the current conservative collector uses raw stable addresses, does not perform
generation checks on dereference, and is not refined by this model. A future
runtime must either implement checked handles or prove that its ownership and
lifetime rules make stale dereferences unreachable. Generation wraparound,
slot exhaustion and authority issuance also need explicit contracts.


**Model scope clarification:** `HeapState` currently models allocation counters and
resource ledgers only. It has no live-object set/table, descriptor map or reference
graph. The returned `ObjectId` is therefore the previous identity counter, not a
proof of membership in a concrete allocated-object domain. The generational slot
and capability-ledger models are separate target contracts, not yet composed with
`allocate`. No object existence, descriptor, reference-graph, or concrete heap
mutation guarantee follows from this allocation-counter model.

The Lean model represents authority as an explicit region identity token; it does not model or prove unforgeable capability issuance. The Lean theorems are intended to be model-only. Their current CI status must be checked before treating them as machine-checked results. They do not establish that
`verification/ccam_heap.cap` or a compiled runtime implements these transitions.
Promotion requires a clean pinned proof run, adversarial implementation tests,
an exact representation relation, and a checked refinement argument.

## 9. Research coordination

This contract is subordinate to the programme's shared guarantee calculus and
coordinates with:
- #219/#220: evidence-carrying execution and model-to-implementation evidence;
- #221: compositional resource accounting;
- #222: capabilities, effects and information flow;
- #225: trusted-computing-base inventory;
- #227: compositional guarantee calculus;
- #255: register/object/heap formal bridge;
- #257: research programme consolidation.

The heap is a case study for the unified guarantee calculus, not a parallel
guarantee framework. Its semantic and proof artefacts should be reusable by the
source checker, CCAM validator, evaluator, native backend and bootstrap.
