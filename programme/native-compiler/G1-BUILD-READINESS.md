# G1 build readiness and evidence plan
Status: candidate; G0 acceptance prerequisite remains. This record does not amend normative semantics or certify implementation. Use CAP-003/004/006 and G1 B01–B04 candidates; B05 and cross-interface decision work claimed separately on #25.

## Build admission and sequencing
Freeze I02 with CCAM/Formal/Native first, jointly reconcile I01 and I03, then I04 and I05. Review I06 and I07 with Native/Formal before the dependent C04/E01/E02/F03 work; identify exact version and explicit exclusion of any deferred profile. Every interface requires schema, pre/postconditions, failure priority, bounded resource ledger, security metadata, vectors, proof relation and producer/consumer approval. No candidate decision silently overrides an existing normative contract.

| Boundary | Build evidence to prepare | Blocking design decision |
|---|---|---|
| I01 | Checked source and canonical CCAM fixtures; binding, evaluation order, trap/source-map and rejection cases | immutable checked boundary, source/import and nesting limits |
| I02 | Decoder/evaluator corpus including exact decimal/exponent integrality, decoded duplicate keys, unreachable malformed instructions and quota boundaries | numeric admission, deterministic diagnostics, aggregate limits |
| I03 | Same-CCAM full terminal tuple differential; malformed record and short-write fault injection | sentinel, entry domain, transport deadline, platform code registry |
| I04 | Profile-specific state snapshots for stale handles, quota exhaustion, generation ceilings and root/mark failures | profile version, fault precedence, concrete resource ceilings |
| I05 | Authority-negative matrix covering forged, stale, attenuated and revoked grants and host failures | reviewed effects and host contract; no ambient authority |
| I06 | ELF header/segment/relocation mutation corpus, deterministic object bytes and W^X checks | supported target, relocation domain, loader assumptions |
| I07 | Certificate mutation, input/output identity, unknown/timeout rejection and counterexample retention | validator trust basis, exact artifact and budget binding |

## Execution recipe and recording
1. After G0 approval select immutable candidate commit and record checkout SHA/tree, clean status, tracked dependency manifest, runner images, tool versions and artifact SHA-256; use G0 provenance controls only once integrated.
2. Run repository-prescribed matrix: make and bash tests/run.sh on Ubuntu GCC, Ubuntu Clang and macOS Clang; inspect current workflow definitions before execution. Collect formal-verification and CodeQL outcomes and native ELF harness where applicable. Do not infer success from a prior commit.
3. For each interface identify existing fixture paths and theorem declarations at that commit, tag vectors as existing/missing, and record command, profile, expected/actual, assumptions, owner and result. Missing fixtures become downstream implementation tasks unless required to resolve G1 design ambiguity.
4. Preserve baseline regression outcomes separately from new-profile experiments. Reject unsupported operations before publication; never substitute the legacy C backend without explicit profile selection.
5. Any failed check blocks integration; successful checks support build health but do not approve semantic contracts. G1 acceptance records all interface dispositions, normative amendment versions, producer/consumer review and G0 acceptance identity. Later gates still require concrete conformance/refinement.

No build executed in this preparation pass. No new normative decision, fixture implementation, approval or independent reproduction claimed. Coordinate with current B05, cross-interface and scalar-vector owners on #25 rather than duplicating their work.
