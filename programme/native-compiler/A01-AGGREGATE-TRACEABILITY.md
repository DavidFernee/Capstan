# A01 — Aggregate and runtime traceability (RTM-002)

Pinned main: 3187b3adc3d9b2f5476c2d25ed410da1ec1c88ce. Static audit, no execution evidence. Distinguish process-lifetime compiler arena (A), proposed frame-owned region/view profile (R), and future collecting runtime (G). Do not infer one profile's guarantees from another.

| Requirement | Profile | Implementation / evidence | Acceptance gap |
|---|---|---|---|
| R04.01 Opaque reference provenance | A | ccam_heap_object_index; ccam_aggregate_write; cross-arena/opaque probes in tests/run.sh | Concrete opacity and native handle refinement |
| R04.02 Nominal descriptor and field types | A | ccam_heap_value_has_type, field_get/set | Immutable canonical descriptor authority; typed native correspondence |
| R04.03 Field initialization and mutability | A | field_initialised, field_mutable; heap record tests | Preservation across every aggregate transition |
| R04.04 Array index within logical length | A | array_get/set/append/len; array tests | Exact bounds and capacity preservation |
| R04.05 Immutable byte values | A | bytes_concat, byte_get, bytes_slice; NUL and concatenation tests | Byte-exact native semantics and bounded charges |
| R04.06 Reference-bearing register admission | A | ccam_aggregate_write/read | Canonical schema and call-frame integration |
| R04.07 Failure-atomic allocations | A | allocation_check; exact budget tests | Model-to-concrete simulation; allocator failure injection |
| R05.03 Byte/object/work/temp quotas | A | ccam_heap_create_bounded | Actual native memory/temporary overhead bound, not logical charges alone |
| R05.04 Aggregate step ordering | A | ccam_aggregate_begin_step; alloc_record checks destination before begin_step | Define invalid operand vs fuel priority consistently with admitted instruction semantics; test competing faults |
| R04.08 Frame-exclusive capability authority | R | CCAM-MEMORY-SECURITY-CONTRACT.md | CFG transfer and runtime owner refinement |
| R04.09 Generation exhaustion, reset and close | R | proposed checked non-wrapping generations | Concrete generation boundary and stale-view tests |
| R04.10 No capability duplication or escape | R | contract restrictions on moves, fields, calls | Validator and source-lowering enforcement |
| R04.11 Exact join and bounded analysis | R | proposed exact capability-state join | Loop convergence/budget rejection and soundness |
| R04.12 Complete backing wipe on unwind | R | proposed every-frame exit contract | Normal return/trap/cancellation/limit tests and native wipe preservation |
| R04.13 Checked layout arithmetic | R | proposed interval/layout invariants | Overflow, alignment and end bounds proof |
| R04.14 Collection root completeness | G | native GC design, not arena semantics | Root map + safepoint completeness and compiler/runtime relation |
| R04.15 Stale reference rejection after reuse | G | CCAMHeap.lean stale_handle_rejected_after_recycle (abstract model) | Concrete generation/slot exhaustion and reuse refinement |
| R05.05 Bounded collection and allocation failure | G | proposed native runtime | Worst-case resource contract and failure atomicity |

## Formal evidence inventory

formal/CCAMHeap.lean blob 31d55db: rejected_allocation_preserves_state, allocation_success_facts, allocate_success_preserves_heapInvariant, allocation_charges_exactly, allocation_preserves_work_bound, stale_handle_rejected_after_recycle, cross_region_handle_rejected, revoked_capability_invalid. These are abstract model declarations, not a verified execution of the current Capstan heap. The initial capability token model explicitly does not establish opacity or non-forgeability. Nat counters do not by themselves prove finite machine counter arithmetic.

## Architectural findings and work allocation

- M-01: Compiler arena has no individual free or GC; frame-owned RegionCap/ViewCap rules intentionally prohibit live capabilities across calls. Do not use either as evidence of a production collecting heap. Establish separate profile identifiers and cross-profile interface rules.
- M-02: Aggregate bridge does not yet establish canonical instruction, call-frame or native integration at the pinned revision. #538 is merged; coordinate remaining #458/#481/#550 work before starting new code.
- M-03: Aggregate allocation checks destination before step admission in ccam_aggregate_alloc_record. For malformed direct API inputs this can change failure precedence; this is a contract reconciliation question, not a demonstrated normative machine violation. Specify admission versus dispatch and test zero fuel with invalid destination.
- M-04: Logical byte charges and temporary peak accounting need explicit physical runtime correspondence; host allocation overhead and collector storage are not demonstrated bounded by those logical counters.
- M-05: Frame wiping and whole-program termination semantics must distinguish controlled unwind from uncatchable external termination; do not claim guarantees outside the stated storage/threat model.

## Pinned artifacts

- verification/ccam_aggregate_machine.cap: c359b6e
- verification/ccam_heap.cap: fb1afbfd
- formal/CCAMHeap.lean: 31d55db
- docs/architecture/CCAM-MEMORY-SECURITY-CONTRACT.md: 9c8da56
- docs/architecture/CCAM-AGGREGATE-MACHINE-BRIDGE.md: 2d26da4

All 18 requirements remain unaccepted. G0/G4 remain open. Next: check active PR heads, reconcile profile contracts and create shared competing-fault and lifecycle acceptance vectors only after ownership checks.
