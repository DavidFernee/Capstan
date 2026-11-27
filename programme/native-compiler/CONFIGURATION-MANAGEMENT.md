# CAP-005 — Configuration management

Follow AGENTS.md and coordination issue #25. Read main and claims before work, claim one package or subtask, use isolated branch and PR, identify agent in comments and commit trailers. Reconcile current main and exact-head CI before merge; never bypass checks. Only merge with applicable user authorisation. Release claim on merge or abandonment.

Package states: candidate, designed, in development, implemented, tested, verified (when applicable), integrated, accepted. Record proof/test status separately; no inference from merge alone. Change requests affecting semantics, ABI or invariants require impact analysis, versioning, migration and revised evidence. Integration authority coordinates shared files; avoid duplicate PRs (#542/#544 are a known example). Review weekly: blockers, claims, evidence, risk, schedule and next tasks.

Worker mapping proposal: native compiler -> frontend/native/bootstrap; CCAM/media -> CCAM and runtime interfaces; formal assurance -> Lean and validators; security engineering -> threat models and security refinement; integration/issues -> inventory, claims, CI and release. Runtime and optimisation need explicit subtask ownership. Existing schedules are unchanged by this document.
