# CAP-001 — Requirements and traceability

All statuses initially unverified at this baseline; evidence must bind exact main commit, profile and test/proof identifiers. This does not imply existing code is absent.

| ID | Requirement | WBS | Acceptance evidence |
|---|---|---|---|
| R01 | Source semantic preservation | B01,C02,E01 | Formal relation and accepted-subset lowering checks |
| R02 | Canonical CCAM, strict bounded validation | B02,C01 | Closed decoder corpus and refinement |
| R03 | Exact scalar results and traps | B03,C03 | Full-width values, trap location/detail, fuel, transport failure |
| R04 | Memory and temporal safety | B04,D01,D02,D03 | Reference and root proofs, adversarial lifetime tests |
| R05 | Bounded resource consumption | B04,C03,D02 | Charge semantics and exhaustion vectors |
| R06 | Capability/effect and secrecy preservation | B05,D04 | Authority and relational leakage claims scoped to threat model |
| R07 | Native ABI, object and executable integrity | C04,E01 | Machine simulation or sound validator, ELF and relocation checks |
| R08 | Safe optimisation | E02 | Independent pass validation and directed fuzzing |
| R09 | C-free self-hosting | F01,F02 | Compiler builds itself; audited dependency closure |
| R10 | Release performance and reproducibility | F03 | Pinned workloads, independent rebuild and published budgets |
| R11 | Evidence binding and governance | A01,E02,F03 | Exact artifact hashes, TCB assumptions, traceability |

The inventory package must expand these into atomic requirements and map each to existing RFC clauses, source paths, issue and test/proof IDs before baseline approval.
