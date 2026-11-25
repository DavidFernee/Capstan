# Bosun construction-safety and corruption contract

**Status:** normative acceptance contract; compiler and storage implementation work required  
**Date:** 2026-11-26  
**Applies to:** every Bosun API, page, index, transaction, WAL, recovery, query and maintenance path  
**Implementation language:** Capstan only

## 1. Security objective

Bosun's safe API must make every invalid state and every invalid operation unconstructible or unexpressible by a well-typed safe Capstan program. This is a construction requirement, not a requirement to add checks around publicly mutable records.

The guarantee has two deliberately separate parts:

1. **Construction safety:** safe clients cannot forge handles, duplicate or prematurely destroy ownership, mutate representation, skip lifecycle transitions, exceed admitted resource budgets, or invoke an operation in the wrong state.
2. **Corruption containment:** bytes and state arriving from outside the trusted in-memory abstraction (disk, device, OS, DMA, recovery input, imported backup, or a detected runtime/hardware fault) are untrusted. They are decoded into validated private values before use. A detected integrity or invariant failure stops the affected operation and prevents corrupted state from becoming observable or durable.

No software design can honestly promise that arbitrary physical faults, malicious hardware, compiler miscompilation, or defects in the declared trusted computing base are impossible. These are explicit assumptions and residual risks, not reasons to weaken the safe API. Bosun must detect and contain faults within its specified fault model.

## 2. Non-negotiable representation rules

- Storage, region, page, transaction, cursor, snapshot, lock, buffer, WAL and capability representations are opaque outside their defining module.
- No safe client may construct a representation with a struct literal, copy its internal fields, mutate its counters, or fabricate a handle from integers.
- Identity and authority are unforgeable capabilities, not caller-supplied owner integers.
- Mutable storage has one statically tracked owner or a typed synchronisation discipline. Immutable reads may be shared only through a type whose lifetime and backing stability are enforced.
- Resource reservations are linear/affine values. A reservation is consumed exactly once by commit, abort or drop cleanup; it cannot be copied, forgotten, or released twice.
- Handles carry compiler-enforced lifetimes and state. A stale handle, wrong-owner handle, closed handle or handle from an earlier generation cannot be used in a safe program.
- State transitions consume the old typestate and produce the new typestate. There is no public setter for state flags or counters.
- Constructors validate all external parameters and acquire all required resources before publishing a value. Failure leaves the prior abstract state unchanged.
- Allocation, I/O and persistence operations are explicitly fallible. No safe constructor may expose a partially initialized object or rely on an unreportable allocation failure.
- Integer arithmetic used for sizes, offsets, counters, lengths and identifiers is checked before effects. Bounds are proved or checked before indexing, allocation, pointer derivation or mutation.

These rules require compiler-enforced visibility/opaque types, affine ownership, borrowing/lifetimes, typestate, capability non-forgeability, checked arithmetic and recoverable resource acquisition. Documentation conventions and naming are not substitutes.

## 3. Storage invariants

For each storage instance, the implementation must preserve, by construction:

- admitted capacity equals the sum of capacities of all live regions;
- reserved bytes equal the sum of used extents of all live regions;
- every region has exactly one storage owner and a valid lifecycle state;
- every byte extent lies wholly within one admitted region and is disjoint from every other live reservation unless a separately specified shared immutable representation applies;
- no reference can outlive its region generation, owner, backing allocation or permitted borrow;
- reset/reuse cannot resurrect an old reference (generation wrap must be impossible or use a non-repeating identity);
- every byte is in the range 0..255; typed encodings have one canonical representation;
- capacity, allocation count, nesting depth and all derived totals remain within declared limits;
- failed admission, reservation, write, reset or release has no externally observable partial effect.

Cached counters are not authorities. Either derive them from canonical state or maintain them behind a representation whose transitions are proved to preserve the equations. A validator that discovers corrupted public counters is defence in depth, not construction safety.

## 4. Persistent-data and recovery invariants

All persisted bytes are untrusted on every open and recovery, including bytes written by a previous Bosun version. Before interpretation, validate framing, version, lengths, arithmetic, page identity, generation, checksums/authentication where applicable, record tags, canonical encodings, references and cross-record invariants.

- No unchecked length controls allocation, slicing, indexing or iteration.
- No page, index entry, WAL record or checkpoint is partially published as valid.
- A checksum failure, malformed encoding, impossible transition, duplicate identity, broken reference or inconsistent LSN relation cannot be silently repaired by guessing.
- Recovery is deterministic, bounded, restartable and idempotent. Each crash point has a defined allowed recovered state.
- A detected corrupt record is never treated as a valid default value and never reaches query execution.
- Commit acknowledgement follows the specified persistence boundary; recovery cannot expose a partial transaction.
- Format migration is explicit and versioned. Unknown mandatory features fail closed.

Checksums detect accidental corruption; they do not authenticate hostile modification. If the threat model includes an attacker able to rewrite storage, use authenticated integrity with key lifecycle and rollback policy specified. Neither mechanism substitutes for structural validation.

## 5. Operation protocol

Every mutating operation follows a transactional internal protocol:

1. Validate the opaque handle, typestate, capability, lifetime and budget.
2. Validate all input values and all arithmetic without mutation.
3. Acquire the complete bounded resource reservation.
4. Construct the complete next representation in private temporary state.
5. Validate the next-state invariant or discharge its preservation proof.
6. Publish through one specified linearisation point.
7. Consume/release resources exactly once.

If any step before publication fails, the old abstract state remains unchanged. If publication or persistence can fail, its protocol must define rollback or an explicit recoverable state; no ordinary error return may conceal a half-transition.

## 6. Compiler acceptance gates

Bosun must not expose a production-safe API until the Capstan compiler can demonstrate, with positive and negative compiler tests:

1. Opaque module-private representations; reject external construction, field access and mutation.
2. Affine/linear handles and reservations; reject copying, double consumption, leaks and invalid drops.
3. Borrowing and lifetime rules; reject use-after-reset/close, escaped references and mutation while incompatible borrows exist.
4. Typestate transitions; reject commit-before-prepare, use-after-commit/abort, stale cursor/snapshot and wrong-phase WAL operations.
5. Capability typing and attenuation; reject forged, duplicated or escalated authority.
6. Checked arithmetic and bounded resource effects; reject overflow and unbudgeted allocation/work before effects.
7. Fallible allocation and I/O with failure-atomic constructors and transitions.
8. A soundness argument for the admitted core, plus refinement evidence connecting the compiler's accepted program to the runtime and backend semantics.

A library-level convention, private naming prefix, validator, test suite or code review cannot satisfy these gates.

## 7. Corruption and fault model gates

For every external boundary, specify and test malformed, truncated, duplicated, reordered, stale, oversized and adversarial inputs. Inject faults at every persistence boundary, including short writes, flush failures, torn pages, disk-full, process termination and repeated crash during recovery.

For in-memory corruption, define the faults in scope (including invalid tags, counters, lengths, indices, references and payload bytes), the detection point, fail-closed result and whether the process must terminate. Use independent state reconstruction where practical; do not trust the same cached metadata in both checker and implementation.

Hardware faults, arbitrary memory scribbles, compromised compiler/runtime, and malicious devices require an explicit residual-risk statement and appropriate platform mitigations. Never describe detection tests as proof that arbitrary corruption is impossible.

## 8. Current BL1 status and release block

The current BL1 storage prototype is intentionally **not** a safe API:

- its structs and lists are publicly mutable and forgeable;
- owner identities are ordinary integers;
- references are ordinary constructible values;
- there is no compiler-enforced affine ownership, borrow/lifetime or typestate;
- allocation failure is not recoverable through the current runtime API;
- it has no persistent page format, WAL, recovery, transaction executor or durability boundary.

Its runtime checks and independent flat-vector oracle are useful prototype evidence only. They do not make invalid states unrepresentable, and they do not establish corruption impossibility.

**Release rule:** do not promote BL1 to a production or security boundary, and do not build transaction execution on top of it, until the compiler acceptance gates in section 6 are met and the storage representation is replaced by opaque, ownership-safe types. Persistent storage remains blocked until section 4 and the crash/recovery gates in section 7 are implemented and validated.

## 9. Required evidence per release

Every claim is tied to an exact commit and records: threat model; invariant; compiler rejection tests; positive conformance tests; property/differential/mutation tests; formal theorem and assumptions (if claimed); implementation refinement evidence; platform and trusted-computing-base assumptions; fault-injection results; unresolved limitations.

A green test suite is necessary but not sufficient. A proof of an abstract model is not a proof of the implementation without a sound refinement link. Any known counterexample to a claimed invariant blocks release until resolved or the claim is narrowed.
