# RTM-006 — Bootstrap acceptance
Authority: NATIVE-BOOTSTRAP-PLAN.md (historical audit refreshed by PR status, not proof), RFC #542 G-16. All gates open. S0 independent Rust candidate is bootstrap-only, not production dependency; selection remains proposed.
| ID | Obligation | Required evidence |
|---|---|---|
| BS01 | Freeze source subset | Transitive compiler workload inventory and negative syntax cases |
| BS02 | Independent seed | Source, pinned toolchain, dependency/FFI audit |
| BS03 | Seed admission | Bounded strict source and canonical CCAM validation |
| BS04 | S1 artifact | Build seed to native Capstan compiler; manifest and digest |
| BS05 | Native execution | Complete scalar outcomes vs reference, no C runtime |
| BS06 | Workload closure | Actual lexer/parser/checker/lowerer/emitter compiled natively |
| BS07 | S2 rebuild | S1 compiles identical compiler source, S2 executes corpus |
| BS08 | Reproducibility | Independent clean builds identical under pinned inputs |
| BS09 | Diverse double compilation | Independent trusted compiler path and documented DDC comparison assumptions |
| BS10 | Production dependency closure | Build and run without seed, C, Python or external assembler/linker for strict target |
| BS11 | Provenance | Source, transitive imports, tools, configuration, binary hashes |
| BS12 | S3 release | Signed artifacts, assurance manifests, platform boundary and rollback policy |
#540 direct ELF remains candidate and host driver builds through C. It is not S1. Do not infer source trust from reproducibility. Historical plan permits assembler/linker; strict production target requires direct Capstan-native object generation per #542, with explicit platform boundary. No execution performed.
