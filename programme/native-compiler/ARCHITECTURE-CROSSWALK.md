# Architecture crosswalk
Reviewed RFC #542 head aa19a6dd7961baa91ef68f67317a2c0bf497c777. #544 closed unmerged; unique content comparison remains pending. #545 supplementary. Existing language specification and normative CCAM govern semantics; RFC governs architecture upon approval; programme governs work and evidence.

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
| G-12 optimisation | E02 | G5 | RTM-007 pending |
| G-13 resources | B04 D02 D03 | G4/G7 | RTM-002/003/005 |
| G-14 security | B05 D04 | G4/G7 | RTM-004; dedicated security evidence required |
| G-15 precise roots | D02 D03 E01 | G4/G7 | RTM-005 |
| G-16 bootstrap | F01 F02 | G6 | RTM-006 pending |
| G-17 performance portability | F03 | G7 | benchmark plan pending |
| G-18 evidence manifest | E01 E02 F03 | G5/G7 | RTM-007 pending |
| G-19 terminal ABI | B03 C03 | G1/G3 | RTM-001/003 |

G-19 is an early interface dependency, not merely release evidence. #540 reports experimental CCAMRES scalar records and 12 differential cases; PR-reported evidence only. B03 owns wire sentinel, entry type, retry and consumer review. #535/#549 candidate formal evidence is not completed concrete refinement. Retain existing worker ownership. All gaps unaccepted; exact-head CI queued/pending for #542/#545/#548.
