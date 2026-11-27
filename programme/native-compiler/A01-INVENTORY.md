# A01 — Initial implementation and work allocation inventory

Snapshot: main 3187b3adc3d9b2f5476c2d25ed410da1ec1c88ce; open PR/issue search 2026-11-27. Partial inventory, not gate G0 acceptance. File presence and comments were inspected; no new execution or proof claim.

| Package | Evidence or active work | Remaining acceptance gap |
|---|---|---|
| A01 | #548, #467, #80 | Complete exact-commit inventory and reconcile #542 |
| B01/C02 | verification/ccam_lowering.cap (db91956), #539, #444 | Accepted-subset coverage and source refinement |
| B02 | verification/ccam_calls.cap (4296e7c), CCAM.md | Canonical named call decoder mapping and complete validator evidence |
| B03/C03 | CCAM-NATIVE-BACKEND.md (f70ef34), #540, #545 | Review versioned result transport and exact native differential evidence |
| B04/D01 | #538 merged; #458, #550 | Normative memory contract, integration and failure atomicity |
| B05/D04 | #325, #536, #473 | Effect/capability and blocking I/O contracts, relational refinement |
| C01 | #243, #235, #527, #547, #549 | Whole-machine proof and concrete evaluator correspondence |
| C04 | #540, #533, #521 | Direct ELF coverage, relocations and exact encoder validation |
| D02 | NATIVE-CAPSTAN-GC.md (7ee4cbc), #137, #541 merged | Native GC integration, root completeness and proof audit |
| D03 | #538 merged; #458 | Managed native execution end-to-end |
| E01 | #451, #547 | Source/CCAM/native theorem or independently sound validator |
| E02 | #528, #521 | Pass-direction corpus, trace/certifier, independent validation |
| F01 | #481, compiler/codegen.cap (a43b616) | Actual compiler workload closure; existing codegen emits C |
| F02 | NATIVE-BOOTSTRAP-PLAN.md (f27bba2) | Revalidate historical audit; reproduce S0–S3 |
| F03 | #428, #261, #252, #543 | Exact artifact evidence and release acceptance |

## First operational tranche

Do not duplicate active PRs. Integration role reconciles #542, #548 and #545, then maps pending #540/#533/#521/#528 to C03/C04/E02. Formal role reviews #547/#549/#527 against C01 before opening separate proof work. CCAM/runtime role consumes merged #538 plus #550 and #458 evidence before claiming aggregate integration. Frontend role checks #539 and #481 against C02/F01. Security role establishes issue #473 acceptance criteria and maps #536 to B05/D04.

Next unclaimed tasks must be selected on issue #25 after checking ownership, not automatically assigned by this document.

## Evidence limitations

Open search returned 18 PRs and 47 issues at observation time (search snapshot, not exhaustive historical inventory). Mainline file observations are pinned; active PR status can change. Existing documentation includes historical statements, and neither file presence nor coordination handoffs establish CI or proof success. #548 initial head had CI, CodeQL and formal-verification queued. Recheck exact new head. No estimates reduced until actual acceptance evidence is mapped.

## G0 residual checklist

- Enumerate compiler/runtime source modules and dependency graph.
- Map every atomic normative requirement to a source path, test/proof ID and exact commit.
- Establish reproducible baseline build and CI evidence.
- Reconcile overlapping architecture documents with one accepted authority.
- Review package ownership, capacity and schedule with integration authority.
