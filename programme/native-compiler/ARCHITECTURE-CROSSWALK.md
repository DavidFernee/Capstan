# Architecture crosswalk
This crosswalk maps the [implementation gap ledger](../../docs/architecture/NATIVE-COMPILER-IMPLEMENTATION-GAP-LEDGER.md) for the [architecture RFC](../../docs/architecture/NATIVE-COMPILER-ARCHITECTURE-RFC.md) integrated in #542. The language specification and normative CCAM govern semantics. [CAP-003](WORK-BREAKDOWN.md) assigns work packages, and the [consolidated acceptance register](G0-CONSOLIDATED-ACCEPTANCE.md) records gate status.

| RFC gap | Work packages | Gate | Traceability |
|---|---|---|---|
| G-01 architecture | A01 | G0/G1 | crosswalk |
| G-02 source preservation | B01 C02 | G1/G2 | RTM-004 |
| G-03 evaluator refinement | C01 D01 E01 | G2/G4/G7 | RTM-001/002 |
| G-04 proof profile | B02 C01 | G1/G2 | RTM-001 |
| G-05 strict decoder | B02 C01 | G2 | RTM-001 |
| G-06 calls | B02 C01 | G2 | RTM-001 |
| G-07 aggregate | B04 D01 D03 | G4 | RTM-002 |
| G-08 root ABI | B03 B04 D02 | G1/G4 | RTM-002/005 |
| G-09 native coverage | C03 D03 F01 | G3/G4/G6 | RTM-003/004 |
| G-10 object writer | C04 | G3/G6 | RTM-003 |
| G-11 ABI | B03 C03 | G1/G3 | RTM-003 |
| G-12 optimisation | E02 | G5 | RTM-007 |
| G-13 resources | B04 D02 D03 | G4/G7 | RTM-002/003/005 |
| G-14 security | B05 D04 | G4/G7 | RTM-004; R06.01–R06.06 |
| G-15 precise roots | D02 D03 E01 | G4/G7 | RTM-005 |
| G-16 bootstrap | F01 F02 | G6 | RTM-006 |
| G-17 performance portability | F03 | G7 | R10.01–R10.03 |
| G-18 evidence manifest | E01 E02 F03 | G5/G7 | RTM-007; R11.01–R11.03 |
| G-19 terminal ABI | B03 C03 | G1/G3 | RTM-001/003 |

G-19 is an early interface dependency. B03 owns the result sentinel, entry domain, transport behaviour and consumer review under the [candidate result contract](G1-B03-RESULT-CONTRACT.md).

| Traceability record | Ledger gaps linked above |
|---|---|
| [RTM-001 Scalar](A01-SCALAR-TRACEABILITY.md) | G-03, G-04, G-05, G-06, G-19 |
| [RTM-002 Aggregate](A01-AGGREGATE-TRACEABILITY.md) | G-03, G-07, G-08, G-13 |
| [RTM-003 Native](A01-NATIVE-TRACEABILITY.md) | G-09, G-10, G-11, G-13, G-19 |
| [RTM-004 Frontend](A01-FRONTEND-TRACEABILITY.md) | G-02, G-09, G-14 |
| [RTM-005 GC](A01-GC-TRACEABILITY.md) | G-08, G-13, G-15 |
| [RTM-006 Bootstrap](A01-BOOTSTRAP-TRACEABILITY.md) | G-16 |
| [RTM-007 Optimisation](A01-OPTIMISATION-TRACEABILITY.md) | G-12, G-18 |
| [Supplemental requirements](G0-SUPPLEMENTAL-DISPOSITION.md) | G-14, G-17, G-18 |

The gate column identifies the programme checkpoints for each gap. The
supplemental dispositions also apply the evidence-review and claim-scope
requirements R11.02 and R11.03 to G0.
