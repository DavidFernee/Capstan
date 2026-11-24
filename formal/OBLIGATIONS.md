# Allocator and collector proof-obligation matrix

**Baseline:** `e54edb6bbccab24acab9f2d002a98a09e56c443f`  
**Status:** all obligations are open; this is an inventory, not proof evidence.

| ID | Property | Required evidence | Current status / blocker |
|---|---|---|---|
| ARITH-01 | Checked addition returns the exact sum iff it fits; otherwise it takes the specified fatal path. | Machine proof of helper plus C refinement. | Not started. |
| ARITH-02 | Checked multiplication returns the exact product iff it fits; otherwise fatal. | Machine proof plus C refinement. | Not started. |
| ARITH-03 | Capacity growth terminates, is at least required, and its byte size fits. | Machine proof over all machine-sized inputs plus C refinement. | Not started. |
| PAGE-01 | Page records and page-table entries are unique and consistent. | Model invariant and implementation correspondence. | Not started. |
| PAGE-02 | Page-table probing terminates within capacity under occupancy and power-of-two assumptions. | Machine proof; explicit occupancy invariant. | Not started. |
| SLOT-01 | Every slot is in exactly one allocated/free/spare state. | Inductive state invariant. | Not started. |
| FREE-01 | Every free-list link points to a valid slot in the matching kind/class. | Inductive invariant and concrete memory-layout relation. | Not started; links are currently in-band. |
| FREE-02 | No reusable slot appears more than once; every reusable active slot appears exactly once. | Uniqueness and completeness proofs. | Not started. |
| LARGE-01 | Large-object records are sorted, unique and non-overlapping. | Insertion/sort/search proofs and pointer-range bounds. | Not started. |
| MARK-01 | Mark-stack depth is bounded and work items refer to allocated objects. | Push/drain transition proofs. | Not started. |
| GC-01 | Marking reaches every object reachable from the abstract roots. | Inductive graph-reachability theorem. | Not started; root completeness is a premise. |
| GC-02 | Sweep never reclaims an object marked reachable. | Theorem from GC-01 plus sweep invariant. | Not started. |\n| GC-03 | Abstract scanning matches physical bytes scanned by C, including stale pointer words in vacated container capacity. | Representation contract plus container mutation correspondence. | Not started; logical removal does not itself clear conservative scan words. |
| ACCOUNT-01 | Heap accounting equals retained page backing plus registered large-object bytes. | Transition proof with explicit OS outcomes. | Blocked by unchecked `madvise` result in baseline C. |
| ACCOUNT-02 | Each successful acquire/release changes accounting exactly once; failed release does not. | Transition proof, exact-delta implementation test, C refinement. | Blocked by baseline release implementation. |
| SECRET-01 | Secret payload is wiped before reuse or release. | Wipe primitive review, state proof, direct byte-observation tests. | Not satisfied by baseline small-slot in-band free-list link. |
| SECRET-02 | Secret free-slot metadata is out of line and does not repopulate payload bytes. | Implementation change and representation proof. | Awaiting runtime hardening work. |
| FAIL-01 | Every allocation failure follows the documented terminal/failure-atomic transition. | Enumerated failure sites, injected tests, state proof. | Not started; OOM is currently fail-stop. |
| REFINE-01 | Concrete C operations simulate the abstract transition system. | ACSL/Frama-C, VST/CompCert, or equivalent checked bridge. | Not started; toolchain selection pending. |
| ROOT-01 | Concrete root scan covers the supported execution roots. | Platform/ABI-specific proof or explicitly bounded assumption plus tests. | Not started; not derivable from abstract graph proof. |

## Promotion criteria

- `not_started` -> `in_progress`: source and exact proposition are under active development.
- `in_progress` -> `proved_model_only`: proof assistant checks the model theorem from a clean,
  pinned environment; the result is explicitly labelled model-only.
- `proved_model_only` -> `proved_implementation`: concrete representation/refinement obligations
  are discharged and the exact implementation revision is identified.
- A failed build, missing assumption, changed covered implementation, or unreviewed axiom
  prevents promotion.
- Tests, fuzzing, static analysis and code review are useful complementary evidence, never
  substitutes for a theorem.
