# G0 atomic parent traceability audit

2026-11-27. Proposed mappings to CAP-001 MASTER-REQUIREMENTS.md. All 48 local IDs individually mapped; first parent primary, additional parents cross-cutting. Existing matrix acceptance obligations retained verbatim by reference; no implementation acceptance inferred. Normative section precision and exact source/test/proof bindings still outstanding. G0 HOLD.

## GC

Authority candidate: RTM-005; NATIVE-CAPSTAN-GC.md.

| Local ID | CAP-001 parents | Evidence disposition |
|---|---|---|
| GC01 | R04 | Existing matrix obligation retained; exact implementation binding pending |
| GC02 | R04, R07 | Existing matrix obligation retained; exact implementation binding pending |
| GC03 | R04, R06 | Existing matrix obligation retained; exact implementation binding pending |
| GC04 | R04, R07 | Existing matrix obligation retained; exact implementation binding pending |
| GC05 | R04, R05 | Existing matrix obligation retained; exact implementation binding pending |
| GC06 | R04 | Existing matrix obligation retained; exact implementation binding pending |
| GC07 | R04, R05 | Existing matrix obligation retained; exact implementation binding pending |
| GC08 | R04 | Existing matrix obligation retained; exact implementation binding pending |
| GC09 | R04 | Existing matrix obligation retained; exact implementation binding pending |
| GC10 | R04 | Existing matrix obligation retained; exact implementation binding pending |
| GC11 | R04, R05 | Existing matrix obligation retained; exact implementation binding pending |
| GC12 | R05, R04 | Existing matrix obligation retained; exact implementation binding pending |
| GC13 | R05 | Existing matrix obligation retained; exact implementation binding pending |
| GC14 | R04, R07 | Existing matrix obligation retained; exact implementation binding pending |
| GC15 | R06, R04 | Existing matrix obligation retained; exact implementation binding pending |
| GC16 | R05 | Existing matrix obligation retained; exact implementation binding pending |
| GC17 | R04, R06 | Existing matrix obligation retained; exact implementation binding pending |
| GC18 | R09, R04 | Existing matrix obligation retained; exact implementation binding pending |

## BS

Authority candidate: RTM-006; NATIVE-BOOTSTRAP-PLAN.md; RFC G-16.

| Local ID | CAP-001 parents | Evidence disposition |
|---|---|---|
| BS01 | R09, R01 | Existing matrix obligation retained; exact implementation binding pending |
| BS02 | R09, R11 | Existing matrix obligation retained; exact implementation binding pending |
| BS03 | R02, R09 | Existing matrix obligation retained; exact implementation binding pending |
| BS04 | R09, R11 | Existing matrix obligation retained; exact implementation binding pending |
| BS05 | R03, R07, R09 | Existing matrix obligation retained; exact implementation binding pending |
| BS06 | R09, R01 | Existing matrix obligation retained; exact implementation binding pending |
| BS07 | R09, R10 | Existing matrix obligation retained; exact implementation binding pending |
| BS08 | R10, R11 | Existing matrix obligation retained; exact implementation binding pending |
| BS09 | R09, R11 | Existing matrix obligation retained; exact implementation binding pending |
| BS10 | R09 | Existing matrix obligation retained; exact implementation binding pending |
| BS11 | R11, R10 | Existing matrix obligation retained; exact implementation binding pending |
| BS12 | R11, R10, R09 | Existing matrix obligation retained; exact implementation binding pending |

## OPT

Authority candidate: RTM-007; RFC sections 3–6, G-12/G-18.

| Local ID | CAP-001 parents | Evidence disposition |
|---|---|---|
| OPT01 | R08, R02 | Existing matrix obligation retained; exact implementation binding pending |
| OPT02 | R08, R11 | Existing matrix obligation retained; exact implementation binding pending |
| OPT03 | R08, R03 | Existing matrix obligation retained; exact implementation binding pending |
| OPT04 | R08, R01, R06 | Existing matrix obligation retained; exact implementation binding pending |
| OPT05 | R08, R04 | Existing matrix obligation retained; exact implementation binding pending |
| OPT06 | R08, R04, R06 | Existing matrix obligation retained; exact implementation binding pending |
| OPT07 | R08, R07, R04 | Existing matrix obligation retained; exact implementation binding pending |
| OPT08 | R08, R05 | Existing matrix obligation retained; exact implementation binding pending |
| OPT09 | R08, R11 | Existing matrix obligation retained; exact implementation binding pending |
| OPT10 | R11, R08 | Existing matrix obligation retained; exact implementation binding pending |
| OPT11 | R06, R08 | Existing matrix obligation retained; exact implementation binding pending |
| OPT12 | R08, R10, R11 | Existing matrix obligation retained; exact implementation binding pending |

## Inventory reconciliation

Scalar 17, aggregate 18, native 18, frontend 18 already use parent-prefixed identifiers. GC 18, bootstrap 12, optimisation 12 now have explicit candidate links (48). Total 113. Review cross-cutting links for completeness; do not count links as additional requirements. Twelve supplemental security/performance/governance candidates remain separately dispositioned. RTM-006/007 exist; pending means acceptance pending, not missing artifacts.
