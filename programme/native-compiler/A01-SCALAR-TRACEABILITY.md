# A01 — Scalar requirements traceability, increment 1

Pinned main: 3187b3adc3d9b2f5476c2d25ed410da1ec1c88ce. Static evidence inventory only; no tests executed in this increment. Requirement identifiers below are local children of CAP-001. Normative authority: docs/architecture/CCAM.md (blob ff0d483). Test runner: tests/run.sh (f465e8b). Concrete core: verification/ccam_core.cap (5ce0daf).

| ID | Requirement | Concrete implementation / test entry | Formal evidence or gap | Acceptance obligation |
|---|---|---|---|---|
| R02.01 | Exact signed-64 JSON decoding, reject duplicate/unknown fields | CCAM JSON decoder contract; in-memory validator is insufficient | No decoder refinement identified | Raw adversarial corpus and closed decoder proof |
| R02.02 | Typed register indices and instruction schemas | ccam_validate_single_frame; ccam_core_tests.cap | ProgramValidator.lean; SF-P restricted admission | Prove concrete admission correspondence, then normative completeness |
| R02.03 | Reachable fall-through rejected; unreachable final nonterminal allowed | ccam_validate_single_frame | SF-P final-slot rule is deliberately stronger | Reachability invariant and differential accept/reject vectors |
| R02.04 | Canonical named calls and signatures | ccam_calls.cap side table | #547 work, not accepted | Exact external-to-internal mapping and validation |
| R03.01 | Addition overflow | ccam_add; ccam_core.cap tests; native overflow vector | SFVectors.lean sfP_run_SF002 | Concrete/native correspondence for all operands |
| R03.02 | Subtraction/multiplication overflow | ccam_sub, ccam_mul; core arithmetic tests | Core.lean model, concrete refinement open | Boundary and operand precedence evidence |
| R03.03 | MIN/-1 division traps | ccam_div; native div-overflow vector | SFVectors.lean sfP_run_SF003 | Exact native terminal record and refinement |
| R03.04 | MIN%-1 returns zero | ccam_rem; native rem-min vector | SFVectors.lean sfP_run_SF004 | Exact result comparison, not exit-status-only |
| R03.05 | Zero divisor traps | ccam_div, ccam_rem; native divzero vector | SFVectors.lean sfP_run_SF005 covers division | Both operations, exact trap and step count |
| R03.06 | Exact integer terminal result | #552 direct fd-3 result/CCAMRES v1 candidate | SFVectors.lean sfP_run_SF001 models 42 | Distinguish 0/256, MIN/MAX, void, transport failure |
| R03.07 | Uninitialised read and typed destination checks | ccam_register_read_int/bool and write_int/bool; native uninitialised vector | RuntimeBridge.lean representation relation per contract | Concrete read/write simulation and failure atomicity |
| R03.08 | Left-to-right call reads; depth check afterward | ccam_calls.cap; ccam_initial_state_tests.cap | #549 ordered reads, #547 prerequisite | Prove implementation correspondence and exact competing-trap vectors |
| R03.09 | Atomic return pop/write | ccam_calls.cap | #527 active | Preflight invalid destination; unchanged stack and destination on failure |
| R03.10 | Explicit trap reason preserved | CCAM.md; native trap exits insufficient | SF-P excludes entire explicit trap opcode | Bounded reason and exact code/function/PC/detail record |
| R05.01 | Step counted on instruction trap; exhaustion before next instruction | ccam_core.cap; native step-limit vector | budgetedMachineStep_consumes_one; budgetedMachineStep_exhausted_before_instruction (model only) | Concrete step/trace equivalence at 0, N-1, N and N+1 |
| R05.02 | Call depth includes entry frame | ccam_calls.cap; native depth-limit vector | Multi-frame work #547 | Exact boundary and failure state correspondence |
| R01.01 | Checked scalar source lowered deterministically | ccam_lowering.cap; tests/run.sh frontend invocation | #451 open | Accepted subset theorem and source/CCAM differential corpus |

## Evidence classification

All rows remain unaccepted. Named Lean vector theorems were read in SFVectors.lean (14812895); they establish propositions about model execution, not implementation correctness. The existing concrete refinement contract (a8e8028) pins an older concrete core blob b29b619, not the current 5ce0daf; refresh the proof input inventory before making implementation-linked claims. Its opcode correspondence table must be read together with the later SF-P scope restrictions: explicit trap is excluded, and the stricter terminality rule is not normative CCAM.

Existing runner invokes schema validation, generated Lean vector check, concrete vector runner and native executable tests. Presence of commands is not a successful run. Legacy exit-status vectors are insufficient for full-width terminal observation; #552 adds experimental fd-3 raw-result and CCAMRES v1 modes, with stable ABI and full outcome refinement still open. Consume #552 evidence rather than duplicate its implementation.

## Acceptance sequencing

Use #542 as the governing architecture candidate; then freeze I02/I03 and review #552. Extend shared corpus with exact terminal outcome and competing-trap negatives. Formal work must pin toolchain, imports, machine profile and implementation revision. Integration must record exact-head CI and release evidence separately from model theorem statements.
