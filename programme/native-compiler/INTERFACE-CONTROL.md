# CAP-006 — Interface control register

Proposed freeze gates, not normative replacements. Each interface requires version, owner, input/output schema, pre/postconditions, invalid-input behaviour, resource charge, security metadata, conformance vectors and proof relation.

| ICD | Boundary | Owner | Freeze before |
|---|---|---|---|
| I01 | Checked source -> CCAM | Frontend/CCAM | C02 |
| I02 | Canonical decoder -> validator/evaluator | CCAM | C01,C03 |
| I03 | CCAM -> scalar native and terminal result | Native/CCAM | C03,C04 |
| I04 | Runtime objects, references, roots, allocation | Runtime/CCAM | D01,D02,D03 |
| I05 | Effects, authority, host calls | Security/Runtime | D04 |
| I06 | Machine code, relocations, object/load | Native | C04,E01 |
| I07 | Optimisation/certificate and exact artifact binding | Formal/Native | E02,F03 |

I03 must distinguish signed-64 and void outcomes, trap identity/location/detail/steps, and platform failures; coordinate active #540 rather than invent wire format. I04 must state generation exhaustion, root publication and failure atomicity. I07 must state validator timeout policy and trust assumptions. Interface changes require review from both producers and consumers.
