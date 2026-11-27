# A01 — Native allocator and collector traceability (RTM-005)

Pinned main 3187b3adc3d9b2f5476c2d25ed410da1ec1c88ce. Static inspection only. These are refinements of RTM-002 managed-heap requirements, not independent claims of coverage. Native collector is a design target; C compatibility implementation is not native acceptance evidence.

| ID | Requirement | Existing evidence | Acceptance obligation |
|---|---|---|---|
| GC01 | Complete live roots | Native GC design §3 | Compiler liveness theorem including outgoing args and helper temporaries |
| GC02 | Typed root maps | GC-R0 proposal | Closed versioned encoding, bounds and exact slot classification |
| GC03 | Frame publication and unwind | GC-R0 proposal | Publish after initialization, withdraw exactly once on every controlled exit |
| GC04 | Safepoint discipline | GC-R0 proposal | Spill before publication, reload after collection, forbid unsafepointed collection |
| GC05 | Heap identity and generation | Native design §4; abstract heap proofs | Non-recycled identity issuance and exhaustion; concrete stale-handle rejection |
| GC06 | Immutable layouts | Native design §4 | Descriptor provenance, checked offsets, pointer-free secret/atomic objects |
| GC07 | Marker completeness | CollectorSemantics.lean HeapMarkerComplete | Complete concrete bounded worklist algorithm; graph oracle |
| GC08 | Sweep safety | gcSweep_preserves_reachable | Discharge completeness premise and concrete refinement |
| GC09 | Retained edge integrity | gcSweep_retained_edge_target | Layout-to-graph correspondence and malformed-edge failure |
| GC10 | Slot partition | Native design §9; historical #309 | Concrete exactly-one-owner and free-list equivalence |
| GC11 | Failure-atomic allocation | Native design §6; legacy cap_gc_meta | Fault injection at every reservation/publication boundary |
| GC12 | Metadata independence | Separate metadata arena proposal | Bound all metadata, no managed allocation recursion |
| GC13 | Physical memory accounting | Legacy cap_gc_checked_add/mul, cap_gc_account_release | Distinguish payload, reserved, committed, metadata and temporary storage |
| GC14 | Platform page transitions | Native design §7 | Syscall adapter refinement; failure and partial-success semantics |
| GC15 | Secret wipe before reuse | Legacy cap_gc_wipe; native §8 | Native code store preservation, out-of-line metadata and failure quarantine |
| GC16 | Bounded tracing and pause work | Native §5 bounded worklist | Cost bound on roots, slots, edges, worklist and sweep; explicit host timing assumptions |
| GC17 | Single-thread isolation | Native §3/9 | Reject reentry, concurrent mutation and signal-time allocation |
| GC18 | C-free migration | Native §1/12 | Actual compiler workload, native stress corpus, dependency audit and reproducible artifact |

## Findings

GC-F01: CollectorSemantics.lean proves sweep safety conditional on marker completeness. A compiler root-completeness proof and concrete marking refinement are separate mandatory obligations.
GC-F02: GC-R0 leaves physical root-map encoding open. Freeze interface I04 jointly with backend owners; do not promote a collector that only tests synthetic root lists.
GC-F03: A bounded worklist alone does not bound total pause work: bound descriptor edges, repeated root visits and sparse slot scanning; distinguish deterministic work from elapsed host time.
GC-F04: Heap identity uniqueness is assumed in the design and needs an issuance/exhaustion model. Finite generation exhaustion must retire a slot or reject before mutation, never wrap.
GC-F05: Secret wiping via GC is not timely destruction. Specify explicit secret consumption separately; native optimiser must preserve wiping before reuse. Do not promise physical remanence guarantees.
GC-F06: Define sweep failure policy for partial OS release/wipe failures: either verified transactional transition or terminal quarantine preserving ownership and preventing mutator resumption with inconsistent state. Abstract sweep model alone does not implement rollback.

## Evidence

docs/architecture/NATIVE-CAPSTAN-GC.md (7ee4cbc), runtime/capstan_gc.h (04b2498), verification/lean/CapstanVerification/CollectorSemantics.lean (e2ca2ea). Named theorem declarations include gcSweep_preserves_roots, gcSweep_preserves_reachable_edges, gcSweep_no_new_objects and gcSweep_then_allocate_preserves_reachable. No Lean execution here. Coordinate #137/#541 and existing allocator/collector proof work before changing implementation. Required corpus: empty/cyclic/shared graph, last live register and helper temporary, stale/foreign handle, corrupted descriptor/frame chain, exact work and metadata limits, page failure, generation exhaustion, secret wipe and native optimizer checks. All 18 obligations unaccepted. G4 remains open.
