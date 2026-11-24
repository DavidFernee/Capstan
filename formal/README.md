# Capstan formal verification

**Status: programme foundation; no runtime theorem is yet machine-checked.**

This directory is the authoritative home for machine-checked specifications, proof
sources, pinned proof-tool dependencies, and reproducible proof commands. A document
describing a proof obligation is not evidence that the obligation has been discharged.

## Scope and trust boundary

The first target is the single-threaded, non-moving, conservative mark-and-sweep
collector in `runtime/capstan_gc.h`. The formal model must represent the implementation,
including process-fatal allocation failures and operating-system operation results.
It must not silently replace those behaviours with idealised successful operations.

The initial scope is deliberately narrower than a complete proof of Capstan memory
safety:

1. checked size arithmetic and metadata capacity growth;
2. small-page and slot state transitions;
3. free-list ownership, uniqueness and completeness;
4. large-object ordering, range membership and lifecycle;
5. heap-accounting transitions;
6. secret-slot erasure ordering and metadata separation;
7. marking and sweep preservation, conditional on a stated root/scanning contract.

The current collector scans registered roots, a `setjmp` register spill, and the current
thread's stack conservatively. The proof must state the assumptions needed for that
root-discovery mechanism. It must not claim to prove compiler liveness, ABI behaviour,
or completeness of conservative root discovery merely by proving an abstract graph
traversal.

## Directory map

- `SPECIFICATION.md`: concrete abstract state and transition-system contract.
- `OBLIGATIONS.md`: proof-obligation inventory and acceptance criteria.
- `toolchain/README.md`: proof-tool selection record and reproducibility requirements.
- `CapstanFormal.lean`: initial Lean model and arithmetic/page-release theorems.
- `implementation/`: implementation-facing contracts and refinement evidence.
- `proofs/`: additional discharged theorem sources and generated proof reports.

The first Lean model is now present. Its theorems remain unverified until the pinned CI
job completes; do not promote their status without a reproducible checker run.

## Evidence rules

Every discharged result must identify:

- the exact source revision and implementation files covered;
- the proposition and its formal statement;
- the proof source and pinned toolchain/dependency versions;
- the clean-checkout command and successful CI run;
- assumptions, axioms, imported theories and trusted components;
- the refinement argument connecting the formal state to the C implementation;
- known exclusions and any counterexample/regression tests.

Proof status is one of `not_started`, `in_progress`, `proved_model_only`,
`proved_implementation`, `blocked`, or `not_applicable`. In particular,
`proved_model_only` must never be reported as proof of the C implementation.

## Non-goals for the first milestone

No concurrency, generational collection, finalisation, deterministic secret-destruction
deadline, or process-wide RSS bound is claimed. No proof will assume that conservative
false positives cannot occur. GC-time reclamation is not deterministic resource cleanup.

See [the assurance report](../docs/assurance/FORMAL-VERIFICATION.md) and
[the obligation matrix](OBLIGATIONS.md).
