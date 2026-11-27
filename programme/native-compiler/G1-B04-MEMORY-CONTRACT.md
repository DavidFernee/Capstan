# G1 B04 / I04 — memory and resource contract candidate

Sources: CCAM-MEMORY-EXTENSION.md §§1–10, NATIVE-CAPSTAN-GC.md §§3–7, RTM-002. G0 HOLD; proposed decisions, not normative amendments.

## Profile separation
A: process-lifetime compiler arena; R: frame-exclusive scratch regions; G: precise collecting heap. No implicit conversion, shared handle namespace or inherited proof claim. v0.1 rejects extension opcodes; versioned envelope required for R/G. Native physical addresses are not source-visible.

## Competing faults and atomicity
Proposal: structural admission before execution; admitted instruction checks fuel before dispatch, charges exactly one step, reads operands left-to-right, checks identity/generation, open state, owner, layout, index, checked arithmetic, storage access. This resolves §6.3 index-first versus §7 capability-first ordering in scratch proposal. Malformed direct API input is admission failure, not a machine trap. Failed dispatched operation preserves payload, destination, ownership and allocation counters except charged step and terminal state. Cleanup is separately specified, not a hidden instruction. Physical admission failure maps to platform failure unless deterministic admission oracle is explicitly part of the machine profile; do not identify arbitrary host OOM with deterministic quota exhaustion.

## Region lifecycle
Propose register operands for capacity/count (typed int, checked nonnegative); schema change requires versioned approval. No generation wrap or identity reuse: reject reset before mutation at generation ceiling; retire exhausted slots, reserve cleanup ability even at exhaustion. Normal exit requires explicit close; controlled traps unwind owned regions exactly once. Specify reset zero-initialization before exposing new reservations, including bool canonicality and stale-data non-disclosure. Secret wipe guarantee scoped to controlled execution and declared backing, not external kill or physical remanence. Zero-length views cannot be indexed. Exact join or bounded analysis rejection.

## Resource ledger
Separate logical payload, object/region count, metadata, temporary peak, native mapping/guard overhead, and work budgets. Charge checked arithmetic before allocation; no hidden metadata recursion. Physical adapter failure cannot publish partial allocation. Do not claim RSS bound from logical byte counters. Sweep only after complete validated root chain and bounded transitive marking; no partial reclaim on invalid metadata or worklist exhaustion. Compiler publishes live roots before safepoint, reloads after; single-thread only, no asynchronous callbacks. Handle identity includes nonrecycled heap incarnation, slot, generation; retire exhausted slots.

## Acceptance vectors
Zero fuel plus stale capability; stale plus invalid index; wrong owner plus layout mismatch; generation ceiling reset/close; zero-count access; reset followed by read of newly reserved storage; metadata exhaustion before publication; allocation failure at each preflight; exact quota and one-over; root-chain cycle, invalid map, missing live root, mark-work exhaustion; normal and trap cleanup; secret wipe before reuse. Snapshot state and compare against profile-specific reference, including exact step count. Proof obligations: checked finite arithmetic, typed containment, no alias/escape, failure atomicity, root completeness, concrete refinement. No tests or proofs executed here.

Review by Runtime, CCAM, Frontend, Native, Security and Formal owners before I04 freeze; resource ceilings and concrete layout still require approval.
