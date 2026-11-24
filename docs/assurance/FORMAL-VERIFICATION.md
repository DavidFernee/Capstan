# Machine-checked runtime verification

**Status:** initial abstract-model theorems are machine-checked; no C implementation theorem has been machine-checked.  
**Implementation baseline inspected:** `e54edb6bbccab24acab9f2d002a98a09e56c443f`.

## Purpose

This programme reduces the trusted runtime base by specifying and proving allocator and
garbage-collector properties, then connecting those properties to the concrete C
implementation. It is intentionally separate from ordinary regression testing:
passing tests provide execution evidence, not mathematical proof.

The initial Lean model revision passed checked-add soundness, completeness and exactness,
plus target page-release failure preservation, exact successful accounting decrement and
idempotence. The current revision also models checked-add overflow as an explicit fatal outcome and
proves it in exact-head CI run 45360322725.
These are abstract-model theorems only; they do not yet verify the C code. Exact toolchain
inputs and run evidence are in the [proof-run ledger](../../formal/PROOF-RUNS.md).

The normative starting points are:

- [formal specification](../../formal/SPECIFICATION.md)
- [proof-obligation matrix](../../formal/OBLIGATIONS.md)
- [toolchain selection record](../../formal/toolchain/README.md)

## Current implementation facts and blockers

The current runtime is a single-threaded, non-moving, conservative mark-and-sweep
collector implemented in `runtime/capstan_gc.h`. Small allocations use 64 KiB pages,
fourteen size classes and allocation/mark bitmaps. Large allocations are individually
tracked in a base-address-sorted array. The three allocation kinds are pointer-bearing,
pointer-free atomic, and pointer-free secret.

The first implementation-level blockers are concrete:

1. `cap_gc_release` ignores the return value from `madvise`, then marks the page
   released and decrements `cap_gc.heap`. The accounting theorem cannot be discharged
   against this transition as written.
2. Small secret slots are wiped during sweep, but the allocator writes an intrusive
   free-list pointer into the beginning of the slot. This does not satisfy a full-slot
   erased-free-state invariant.
3. Allocation and metadata OOM paths are currently fail-stop. The model must preserve
   terminal outcomes and must not claim recoverable failure atomicity.
4. The collector scans every machine word in a pointer-bearing allocation, not just a
   container's logical live range. A pointer left in a vacated list/map backing slot can
   therefore remain a conservative edge and delay collection of its referent. Logical
   removal must not be modelled as physical edge removal unless the backing word is
   cleared or overwritten. This is a retention/lifetime precision issue; it does not
   justify reclaiming objects that remain discoverable.
5. The collector's root set depends on registered globals, a `setjmp` register spill,
   current-thread stack discovery, compiler behaviour and ABI assumptions. An abstract
   graph-reachability theorem does not prove those concrete roots complete.
6. libc, the C compiler, platform memory APIs and the current C runtime remain in the
   trusted computing base until their relevant contracts/refinement obligations are
   separately discharged.

The separate runtime-hardening workstream is addressing some implementation defects.
Formal work will not silently duplicate or conflict with that implementation branch.
See [issue #137](https://github.com/DavidFernee/Capstan/issues/137) for coordination.

## Verification layers

| Layer | Target | What a successful result means |
|---|---|---|
| 1. Arithmetic | Checked add/multiply, capacity growth, bounded indices | The specified arithmetic helper is correct over its declared machine domain. |
| 2. Abstract allocator | Page/slot states, free lists, page table, large-object table, accounting | The abstract transition system preserves its invariants. |
| 3. Abstract collector | Root graph, mark stack, mark/sweep | Reachable model objects are not reclaimed, under explicit root/scanning premises. |
| 4. C implementation | ACSL/WP, VST/CompCert or another suitable checked bridge | Concrete functions satisfy contracts in the selected C semantics. |
| 5. Refinement | Concrete metadata and transitions mapped to abstract state | The model theorem applies to the implementation within the stated compiler, ABI and OS boundary. |

A result at one layer must not be described as a result at a later layer. In particular,
a model-only proof is not proof of the C runtime.

## Evidence and reporting policy

Every proof result must name the theorem, proof source, exact implementation revision,
toolchain versions, clean-checkout command, CI run, assumptions, axioms and trusted
components. Failed or stale proof runs remain visible. Changes to covered implementation
code invalidate the corresponding evidence until it is rerun and reviewed.

No assurance claim is promoted merely because a proof file exists or a CI job was
configured. The proof must actually be checked, and the refinement boundary must be
documented. The initial abstract-model result is checked; no C implementation result is
claimed.

## Explicit exclusions

The initial programme does not establish concurrent collection, multi-threaded root
completeness, generational barriers, deterministic finalisation, a deadline for secret
reclamation, system-wide secret erasure, or a process-wide memory/RSS ceiling. These
require separate specifications and evidence.
