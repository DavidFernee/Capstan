# G1 decision and acceptance ledger

Inputs #575–580; CAP-006. Candidate disposition, not approval. G0 HOLD. Existing scalar rules retained; extension proposals cannot silently change v0.1.

| ID | Proposed disposition | Producer / consumer | Acceptance evidence |
|---|---|---|---|
| X01 | Retain exact mathematical JSON integer admission; source lexical grammar distinct; config explicitly specify same policy | CCAM / Frontend, Formal | decimal exponent, negative zero, MIN/MAX, fractional rejection; bounded exact parser proof |
| X02 | Retain dynamic initialization and fuel before dispatch; malformed input rejected before execution | Frontend, CCAM / Native, Formal | zero fuel competing faults, unreachable malformed instruction; step simulation |
| X03 | Retain existing wire profile; reserve platform kind until registry and canonical fields approved | CCAM / Native, launcher | byte-exact records and malformed mutations; no fabricated trap |
| X04 | Defer physical admission outcome mapping to versioned extension; deterministic quota separate | Runtime / CCAM, Native | injected failures vs quota; unchanged logical state |
| X05 | Retain source location sequencing; managed mode requires rooted receiver and post-RHS revalidation | Frontend / Runtime, Native | shrink/replacement RHS, safepoint liveness proof |
| X06 | Separate handle/grant/host capability namespaces; descendant revocation proposed only | Security, Runtime / CCAM | cross-kind forgery denial, monotonic attenuation, retirement |
| X07 | Private launcher result authority; no ordinary source effect on result descriptor | Native / Security, Runtime | denied descriptor mutation and malformed transport tests |
| X08 | Controlled wipe and reset non-disclosure; exclude external kill and uncontrolled host copies | Runtime / Security, Native | reuse, spill and cleanup corpus; wipe refinement |
| X09 | Immutable authenticated checked snapshot or revalidation; no annotation authority | Frontend / CCAM, Security | mutated typed tree, stale binding, contextual sink negatives |
| X10 | Distinct admission, fuel, runtime work and physical budgets; wall deadline external | CCAM, Runtime / Native, Formal | limit exact/one-over, competing fault traces |
| X11 | Defer noninterference claim until attacker observer and permitted declassification approved | Security / Formal, Native | relational proof and explicit public trace/termination scope |
| X12 | Bind exact version and artifact digests through compilation; source maps authenticated separately | Frontend, CCAM / Native, Formal | mismatched digest/profile rejection; reproducible binding |

All decisions pending producer/consumer acknowledgement. For each record reviewer identity, exact baseline, clause diff, accepted profile, vector identifiers, proof boundary and disposition. No CI result constitutes semantic approval. Existing interfaces I06/I07 remain later freeze obligations, not silently accepted by this ledger. No tests or independent review performed. Do not label G1 accepted until prerequisite G0 and approved interface freeze evidence exist.
