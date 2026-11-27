# CAP-002 — System design description

Pipeline: checked source -> validated CCAM -> optional derived optimiser (validated round-trip to CCAM) -> native target lowering -> object/link -> executable and evidence. CCAM is the canonical typed core, not a competing source-language specification. Linux x86-64 is the initial target; additional targets require independent profiles.

Subsystems: frontend owns syntax, types and deterministic lowering; CCAM owns normative machine transitions; runtime owns memory and resource operations; native owns ABI and machine mapping; formal owns proof relations and sound checker; security owns threat models and relational claims; integration owns baseline and evidence. No independent semantic IR is mandated.

Progressive profiles: scalar evaluator, scalar native, managed native, self-hosted, certified release. Each profile declares covered operations and residual dependencies. The scalar profile may proceed independently of managed memory. Experimental extensions cannot silently change frozen CCAM v0.1.

Architecture decisions follow approved RFCs; resolve #542/#544 before selecting a single governing document. See existing docs/architecture/CCAM.md and TYPED-IR.md. No implementation change in this baseline.
