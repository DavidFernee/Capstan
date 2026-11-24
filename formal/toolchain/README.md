# Proof-toolchain selection record

**Decision:** not yet selected.  
**Reason:** the programme needs both a faithful abstract transition model and a credible
bridge to the existing GNU C runtime. Selecting a prover before testing that bridge risks
producing attractive but disconnected proofs.

## Candidates to evaluate

### Coq + VST / CompCert

Potentially the strongest route for C-level separation-logic proofs and a mechanised
connection to a defined C subset. Evaluate the cost of modelling the actual runtime's
GNU extensions, libc calls, pointer arithmetic, conservative scanning and platform APIs.
A proof over CompCert C is not automatically a proof of arbitrary GCC/Clang output or
system-call behaviour.

### Frama-C / ACSL / WP

Potentially a pragmatic route for contracts and verification of isolated C helpers and
transition functions. Evaluate supported C dialect/features, the WP memory model,
available provers, proof reproducibility, and the trusted boundary for SMT solvers.
Do not treat an SMT result as kernel-checked unless the selected configuration provides
that guarantee.

### Lean 4

Potentially effective for a clean, executable abstract state machine, arithmetic
lemmas and reachability proofs. By itself it does not establish that the C implementation
refines that model. A separate C verification bridge is mandatory.

### Isabelle/HOL

A further candidate for mature theorem-proving support and code-level reasoning. Assess
the same refinement and C-semantics questions rather than choosing on theorem-prover
features alone.

## Evaluation gates

1. Prove checked addition and multiplication over the target machine domain.
2. Model a page with a small fixed number of slots and prove slot partition/free-list
   invariants inductively.
3. Model page-release success and failure and prove exact accounting deltas.
4. Demonstrate a tractable path from at least one actual C helper to its formal contract.
5. Pin tool versions and dependencies; build from a clean checkout in CI.
6. Document the kernel, external provers, axioms, imported libraries and all assumptions.

The selected stack may be layered: one tool for the abstract model and another for C
refinement. Tool diversity is acceptable only if the semantic boundary between them is
explicit and independently reviewable.
