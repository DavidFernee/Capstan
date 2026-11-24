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


## Initial evidence-based assessment (2026-11-24)

The official Frama-C documentation describes ACSL as a C contract language and WP as a
weakest-precondition engine for proving those contracts. WP can discharge obligations
with its internal Qed prover, external SMT solvers, or interactive proof assistants
including Coq. This makes it a plausible implementation-facing route for small,
well-isolated C functions; it does not make an unannotated whole-runtime proof automatic.

- Frama-C WP: https://frama-c.com/fc-plugins/wp.html
- ACSL: https://frama-c.com/html/acsl.html
- WP manual: https://frama-c.com/download/frama-c-wp-manual.pdf

The Verified Software Toolchain (VST) offers a more foundational separation-logic route
for C, with Coq and CompCert in its toolchain. Its official installation notes identify
a CompCert licensing distinction for the `clightgen` path. More importantly for this
project, Capstan's runtime currently uses GNU/POSIX facilities and compiler/platform
extensions; the entire header is not assumed to be directly translatable into the
CompCert-supported C subset.

- VST: https://vst.cs.princeton.edu/
- VST installation/licensing notes: https://vst.cs.princeton.edu/download/

Lean's small kernel checks theorem proof terms, and its documentation describes
independently implemented external kernels, including Nanoda. This is attractive for
the pure state machine, arithmetic and graph-reachability layer. Lean alone does not
connect the abstract state to C memory or prove the C implementation refines it.

- Lean reference: https://lean-lang.org/doc/reference/latest/
- Lean external kernels: https://lean-lang.org/doc/reference/latest/External-Kernels/
- Lean proof validation: https://lean-lang.org/doc/reference/latest/ValidatingProofs/

### Provisional architecture to pilot

The evidence supports a **layered pilot**, not yet a final toolchain commitment:

1. **Lean 4** for the abstract allocator/collector transition system, finite-state
   invariants, checked arithmetic and reachability/sweep theorems. Require a pinned
   Lean release, no `sorry`, audit theorem axioms, and evaluate independent kernel
   rechecking (Nanoda) for released proof artifacts.
2. **Frama-C + ACSL/WP** for isolated concrete C helpers and transition functions,
   beginning with checked arithmetic and page-release accounting. Use a pinned
   Frama-C release and explicitly record the exact WP memory model and solver. Prefer
   Coq-backed interactive discharge for difficult obligations where practical; never
   label an SMT discharge as kernel-checked without identifying the actual prover and
   trust path.
3. **Explicit refinement relation** between the Lean abstract state and the ACSL
   contracts. The mapping must be reviewed and itself supported by proof or precise
   implementation invariants; shared names or similar comments do not establish it.

VST/CompCert remains a candidate for a future isolated C core if the relevant code can
be expressed in its supported C subset and the licensing/build constraints are resolved.
It is not the assumed route for the present full runtime.

### Pilot acceptance gate

Before pinning this as the project stack, demonstrate all of the following in a small
reviewable PR:

- Lean proves bounded addition/multiplication and a small page-slot transition invariant.
- The Lean project builds from a clean checkout with a fixed toolchain and locked
  dependencies; theorem axiom reports are retained.
- Frama-C parses an isolated production C helper with ACSL contracts and proves its
  postcondition on all inputs satisfying the precondition.
- A deliberately incorrect helper causes the proof job to fail (negative control).
- CI records tool versions, commands, prover identities, logs and exit status.
- The relationship between the Lean theorem and the verified C helper is written down.

Until that pilot succeeds, this remains a reasoned candidate architecture, not a selected
or operational proof toolchain.
