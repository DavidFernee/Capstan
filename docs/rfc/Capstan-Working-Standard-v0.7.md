# Capstan 1.0 — Independent standards series
Revision 0.7 • 27 November 2026 • Working drafts, not adopted standards

All uppercase MUST/MUST NOT requirements are proposed normative obligations. This is a complete first-pass series, not a claim of current implementation conformance. Concrete syntax, ABI inventories and machine proofs remain to be ratified against a pinned repository revision. One security profile applies to all conforming programs. No unsafe source escape exists.

## RFC 0001 — Foundational requirements

CAP-REV6-001: Conformance claims MUST identify unsupported tasks and distinguish normative requirements, bounded model evidence, mathematical proofs and implementation evidence.

CAP-ADV5-002 (proposed normative correction): Report raw and assurance-matched baselines separately.


CAP-CMP-001 (proposed comparative amendment): Define Pareto comparison only over declared workloads and equivalent security properties; never trade mandatory invariants for speed. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-CORE-001: Every accepted program MUST obey the static and dynamic rules of this series. Invalid operations MUST be rejected before prohibited effects occur; permitted failure MUST have specified semantics. Unsupported mandatory features prevent full conformance, rather than creating a weaker profile. The language standard, implementation and assurance claims are separate versioned objects. External components are explicitly modelled trusted boundaries, not exceptions available to source programs. Acceptance: negative tests for each invariant and a revision-bound conformance report.

CAP-CORE-002 (mandatory corrective amendment): Define conformance over a closed, versioned set of requirements and environment assumptions. Unknown mandatory requirement or extension MUST fail closed; no implementation-defined security weakening. Distinguish safety (finite bad prefixes) from liveness and probabilistic claims. Claims MUST name observation, adversary and failure model.

CAP-CORE-003 (research-informed mandatory amendment): Define admissible contexts independently of the property being proved; require a nonempty environment witness and explicit attacker powers. Reject circular assumptions that presuppose the guarantee. Acceptance obligation: Construct a hostile context and a valid execution witness. Research mapping: R1,R2.

## RFC 0002 — Lexical structure and grammar

CAP-ADV5-003 (proposed normative correction): Charge expansion and reject before emission.


CAP-CMP-002 (proposed comparative amendment): Bound hygienic macro expansion and generated imports; preserve source maps without trusting them. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-GRAM-001: A normative grammar MUST specify encoding, Unicode version, identifier equivalence, token priority, comments, literals, precedence, associativity and full-input consumption. Malformed encoding, ambiguous parses and trailing tokens MUST be rejected. Source size, nesting, token count and literal expansion MUST be bounded before allocation. A proposed abstract grammar is Program ::= Declaration*; Declaration ::= TypeDecl | FunctionDecl | PolicyDecl; Statement ::= Binding | Assignment | Conditional | Loop | Return | ExpressionStatement. These are abstract categories, not approved concrete syntax. The concrete grammar must be extracted and reconciled with the existing parser before ratification. Acceptance: parser differential tests, malformed encoding and limit±1 vectors, unique AST for each accepted input.

CAP-GRAM-002 (mandatory corrective amendment): Pin normalization and identifier comparison at every module boundary; reject normalization collisions and ambiguous import resolution. Diagnostics MUST escape control characters. Canonical serialization MUST be injective over security-relevant AST distinctions; parser recovery MUST never authorize execution. Bound compiler work before lexing and during error recovery.

CAP-GRAM-003 (research-informed mandatory amendment): Require one canonical byte-to-AST relation shared by build, IDE and policy inspection; bind original bytes and canonical AST to evidence. Reject ambiguous normalization and generated-source bypass. Acceptance obligation: Compare parser and tooling AST on malformed and equivalent encodings. Research mapping: R2.

## RFC 0003 — Type system and static semantics

CAP-ADV5-004 (proposed normative correction): Fail closed on timeout.


CAP-CMP-003 (proposed comparative amendment): Require decidable inference fragment and explicit annotations outside it; no partial acceptance. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-TYP-001: Define judgement Γ; A ⊢ e : T ! E, with type context Γ, authority A and effects E. Assignment, argument passing and return require compatible types; conversions must be explicit or proven lossless. Nullable values require refinement before dereference; grants and secrets cannot be forged by casts or deserialisation. Subtyping MUST preserve authority, lifetime and information-flow restrictions. Prove preservation under reduction and progress to a value, permitted trap or specified external wait. Acceptance: rejected ill-typed ASTs and mechanised typing/substitution lemmas; no unchecked coercion.

CAP-TYP-002 (mandatory corrective amendment): Authority, secret and ownership labels MUST survive generics, containers, closures, reflection, serialization and separate compilation. Module signatures MUST be checked against actual definitions. Type inference MUST terminate within explicit budgets; exhaustion rejects without accepting partial derivations. Prove substitution, weakening only for unrestricted values, and no authority amplification.

CAP-TYP-003 (research-informed mandatory amendment): Define structural information-flow judgments over fields, variants and abstract module interfaces; check implicit control flow and existential packaging; conservative fallback on undecidable obligations. Acceptance obligation: Prove substitution and abstraction preserve labels; test secret-dependent variant selection. Research mapping: R3.

## RFC 0004 — Operational semantics

CAP-ADV5-025 (proposed normative correction): Quiesce or version authority and preserve commitment semantics.


CAP-CMP-004 (proposed comparative amendment): Define observable equivalence for staged evaluation and live upgrades; reject unsupported migrations. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-SEM-001: Define configuration (program, control, store, authority, budget, trace). Each transition is a specified internal step, external event, terminal value or trap. Evaluation order, overflow, allocation failure, cancellation and effect commitment MUST be explicit. Determinism is conditional on a fixed external event/scheduling trace; concurrent semantics may admit multiple traces. No undefined behaviour in the program model. Acceptance: executable reference semantics, step vectors and simulation of concrete implementation.

CAP-SEM-002 (mandatory corrective amendment): Define observations as externally committed effects, results, traps and logical charges; confidentiality adds separately declared timing and other channels. Specify maximal traces including divergence and external wait; do not equate deadlock with success. Each effect has a linearization point and explicit partial completion contract. Failure handling MUST NOT bypass security checks.

CAP-SEM-003 (research-informed mandatory amendment): Mechanically check invariant satisfiability, transition overlap, coverage and reachable dead ends; distinguish permitted nondeterminism from conflicting obligations. Require witnesses for each permitted outcome. Acceptance obligation: Check overlapping guards and unreachable success conditions. Research mapping: R2.

## RFC 0005 — Memory, ownership and lifetime

CAP-REV6-005: Finite generation counters MUST NOT wrap into a previously valid identity. Retire the identity at exhaustion or establish a proof that no stale reference can survive reuse.

CAP-ADV5-005 (proposed normative correction): Prove lane bounds or mask with verified semantics.


CAP-CMP-005 (proposed comparative amendment): Specify safe layout, alignment and pinned-buffer ownership; verify vector tail accesses. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-MEM-001: Every access MUST refer to a live object and valid range, with permitted mutability and authority. References cannot be manufactured from arbitrary integers. Alias rules MUST prevent conflicting unsynchronised access; reclamation must not invalidate reachable references. Allocation, collection, finalisation and failure transitions preserve root and capacity invariants. The standard permits GC or other implementations only if observable semantics agree. Acceptance: lifetime proof, concrete allocator refinement, use-after-free and overflow adversarial tests.

CAP-MEM-002 (mandatory corrective amendment): Check offset and length without overflow, including zero-sized and one-past references; bind references to object identity and generation. Account for allocator metadata, fragmentation, GC work and pinned foreign buffers. Finalizers MUST NOT resurrect revoked authority. Secret-bearing storage follows RFC 0014 independently of GC reachability.

CAP-MEM-003 (research-informed mandatory amendment): Protect object provenance, memory mappings and executable pages against admissible foreign contexts; enforce isolation or reject linkage. Model DMA and shared buffers as explicit environmental authority. Acceptance obligation: Attempt cross-module writes and stale DMA accesses in platform model. Research mapping: R1,R7.

## RFC 0006 — Bounded external input

CAP-ADV5-006 (proposed normative correction): Reserve end-to-end capacity and bound outstanding work.


CAP-CMP-006 (proposed comparative amendment): Provide bounded streaming and backpressure with cumulative budget inheritance. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-INP-001: Every external read MUST have explicit byte/item, allocation, cumulative work and applicable wait/cancellation limits. A limit supplied by untrusted data is constrained by an independently authorised ceiling. Validate lengths before arithmetic, allocation or copy. Bounds are inherited across nested decoding, decompression and retries; rejection cannot reset cumulative work. Hosts unable to enforce required wait bounds MUST reject the operation or expose a separately specified nonblocking interface. Acceptance: zero, exact, excess, truncation, slow input, compressed expansion and nested-budget tests.

CAP-INP-002 (mandatory corrective amendment): Every admitted operation MUST reserve parent capacity before accepting input; nested limits cannot mint budget. Bound protocol headers, metadata, encoding expansion, retries and cancellation cleanup. EOF and partial frame are distinct outcomes. Deadlines use an explicitly trusted monotonic clock; if uninterruptible host work cannot be isolated and bounded at the promised boundary, the operation is unavailable.

CAP-INP-003 (research-informed mandatory amendment): Include input rejection, wait and resource exhaustion in observation model; secret-dependent limits require authorized release or oblivious handling. Bound cancellation at declared interface, not by assumed host cooperation. Acceptance obligation: Compare traces for paired secret inputs and stalled host. Research mapping: R5,R8.

## RFC 0007 — Information flow and injection resistance

CAP-ADV5-007 (proposed normative correction): Preserve policy-filtered relational semantics.


CAP-CMP-007 (proposed comparative amendment): Require structured query and process interfaces; bound regex/search and forbid unsafe fallback. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-INJ-001: Untrusted data MUST NOT become grammar, executable structure or authority in a privileged interpreter except through an explicitly typed, authorised construction whose semantics are specified. Data parameters and syntax nodes are distinct types; escaping alone is insufficient without a proved encoding/decoding contract for the target interpreter. For a fixed authorised syntax skeleton S, varying untrusted data d must not alter S after target decoding (except explicitly authorised structural choices). Model source-to-sink paths, second-order injection and downstream reparsing. Confidentiality uses a separate observation model, with explicit authorised declassification. Acceptance: sink inventory, structural noninterference theorem and cross-interpreter adversarial vectors.

CAP-INJ-002 (mandatory corrective amendment): Define interpreter identity/version, grammar and canonical decoding pipeline per sink. Prove for fixed policy and authorized skeleton that all admissible payloads yield the same privileged structural projection, including error and fallback paths; authorized structure choices are explicit capabilities with bounded grammar. A parameter can still select unauthorized resources; separately enforce RFC 0008. Unknown interpreter contracts MUST NOT be used as privileged sinks. Stored taint persists across storage and transport. Confidentiality requires termination/trace-sensitive noninterference or explicitly disclosed weaker observation model and authorized release.

CAP-INJ-003 (research-informed mandatory amendment): Define total outcome over all bounded inputs including rejection; accepted structural projections remain fixed; rejection must grant no unauthorized effect and obey confidentiality model. Bind canonical interpreter version and configuration. Acceptance obligation: Test accepted/rejected pairs, fallback parser and stored payload. Research mapping: R3,R1.

## RFC 0008 — Capabilities and authorisation

CAP-REV6-008: Authorisation MUST bind principal, object identity, operation and epoch at the effect commitment point. Epoch exhaustion MUST fail closed; reuse requires proof that stale grants cannot survive.

CAP-ADV5-008 (proposed normative correction): Use explicit idempotency protocol or prohibit retry.


CAP-CMP-008 (proposed comparative amendment): Enforce linear asset conservation and explicit transaction commitment; external effects are not rollbackable. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-AUT-001: Authority is explicitly granted, scoped, non-forgeable and checked at use. Delegation cannot increase authority; grants bind subject, object, operation and validity epoch. Revocation and check/use races require atomic validation at effect commitment or a specified lease. No ambient authority in ordinary program code. Acceptance: forgery, stale grants, confused deputy, delegation and concurrent revocation tests; authority conservation proof.

CAP-AUT-002 (mandatory corrective amendment): Bind grants to stable object identity, audience, action, context and non-reused generation; prevent replay across processes and tenants. Delegation is monotone in authority and expiry. Revocation prevents new commitments after its linearization; already committed effects cannot be undone. Leases explicitly delay revocation effectiveness, are bounded and cannot renew without fresh authorization. Do not trust path strings as object identity; use checked handles. Audit records MUST NOT leak secrets.

CAP-AUT-003 (research-informed mandatory amendment): Define contextual authority conservation across callbacks, dynamic dispatch and component linking; prevent authority amplification via reentrancy. Revocation semantics use monotone epochs and explicit lease linearization. Acceptance obligation: Explore reentrant deputy and concurrent revoke/commit. Research mapping: R1,R4.

## RFC 0009 — Arithmetic and failure

CAP-ADV5-023 (proposed normative correction): Bound precision before allocation and charge work.


CAP-ADV5-009 (proposed normative correction): Specify exact comparison or authorized rounding rule.


CAP-CMP-009 (proposed comparative amendment): Specify decimal rounding, numeric accuracy envelopes and reproducible floating modes without security weakening. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-ARI-001: Integer widths, signedness, conversion, overflow, division, shifts and floating-point behaviour MUST be specified. Invalid arithmetic traps or returns an explicitly typed failure; no implicit wrap unless a separately defined modular operation is used. Security checks cannot themselves overflow. Observable failures preserve invariants; external effects already committed are not falsely described as rolled back. Acceptance: boundary vectors for every operator and target, including NaN and signed zero where supported.

CAP-ARI-002 (mandatory corrective amendment): Define evaluation order for failing operands, division minimum/-1, shift count bounds, narrowing, literal conversion and floating comparison. Security decisions MUST NOT rely on NaN-sensitive unchecked comparisons. Specify rounding and permitted floating variation; prohibit transformations that change guards. Failure handlers retain resource charges and authority restrictions.

CAP-ARI-003 (research-informed mandatory amendment): Specify target lowering for flags, shifts, floating exceptions and data-dependent latency wherever observable; do not infer constant-time from arithmetic correctness. Acceptance obligation: Compare target traces on boundary operands and secret-dependent latency. Research mapping: R5,R8.

## RFC 0010 — Concurrency and temporal safety

CAP-ADV5-010 (proposed normative correction): Charge cumulative parent budget.


CAP-CMP-010 (proposed comparative amendment): Require structured supervision, bounded restarts and mailbox admission; declare scheduler assumptions. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-CON-001: Task lifetimes, ownership transfer, channel capacity, memory ordering and cancellation are normative. Data races are prohibited; shared mutation requires specified synchronisation. Cancellation cannot leak authority or live resources. Deadlock freedom and fairness are not implied by memory safety; any liveness claim requires explicit scheduler and environment assumptions. Acceptance: bounded interleaving exploration, cancellation at each transition and refinement to actual runtime.

CAP-CON-002 (mandatory corrective amendment): Define happens-before and atomic operation order, ownership of queued messages and cancellation/close races. Each resource transfer has exactly one owner before and after a linearization point. Join and cleanup are bounded or report outstanding isolated work without returning its reservation. Fairness and deadlock claims require explicit scheduler assumptions; no implicit promise of termination.

CAP-CON-003 (research-informed mandatory amendment): Separate safety under every admissible interleaving from determinacy for deterministic fragments and liveness under explicit fairness assumptions. Capability-based synchronization must conserve authority and resource reservations across fences. Acceptance obligation: Enumerate bounded interleavings including unfair paths and cancellation. Research mapping: R4.

## RFC 0011 — CCAM abstract machine

CAP-ADV5-011 (proposed normative correction): Reject unsupported execution.


CAP-CMP-011 (proposed comparative amendment): Version portable CCAM feature negotiation; reject unavailable mandatory operations. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-CCAM-001: Versioned typed instruction schema, validation, evaluation order, checked operations, explicit traps and resource charges are normative. Decode and validate bounded input before execution; invalid control flow, types and operands are rejected. Native backends preserve reference outcomes and observable traces. Derived IR requires a validator and refinement argument. Acceptance: shared vectors include trap details, PC trace and instruction accounting; concrete evaluator simulation against formal machine. Exact opcode inventory remains a ratification dependency.

CAP-CCAM-002 (mandatory corrective amendment): Canonical decoder MUST reject duplicate fields, unknown mandatory opcodes, invalid unreachable code and noncanonical representations. Validation certificate binds exact immutable bytes, schema, limits and target; mutation invalidates certificate. Specify entry/exit and frame invariants, indirect targets and trap priority. Decoder/validator work is budgeted separately from execution. Native admission cannot rely on untrusted certificate assertions.

CAP-CCAM-003 (research-informed mandatory amendment): Bind certificate to module interfaces, linkage, loader policy and leakage/cost model as well as immutable code. Revalidate after transformation; enforce control-flow and memory isolation at native admission. Acceptance obligation: Reject certificate replay under altered loader configuration. Research mapping: R1,R6.

## RFC 0012 — Native toolchain and bootstrap

CAP-ADV5-012 (proposed normative correction): Bind transitive inputs and toolchain versions.


CAP-CMP-012 (proposed comparative amendment): Benchmark incremental native builds and reproducibility with identical manifests; no foreign production helpers. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-BST-001: Final reference toolchain source MUST be Capstan throughout compiler, runtime, standard library, assembler/object writer, linker, build/package/test/fuzz/benchmark/release tools. No external C compiler, assembler/linker delegation or foreign-language implementation helpers in the supported path. OS/hardware and external orchestration remain declared boundaries. A previously built Capstan binary S0 builds S1, S1 builds S2, S2 builds S3 from a pinned manifest; compare complete S2/S3 artifacts and test each stage. Reproducibility alone does not rule out trusting-trust attacks; require independent provenance/diverse verification. Acceptance: clean isolated build with forbidden dependencies absent, artifact comparison and provenance audit.

CAP-BST-002 (mandatory corrective amendment): Pin source and build manifest, stage identity, environment, target and entire artifact inventory. Reject undeclared build inputs and dynamic tool discovery. S0 provenance MUST be independently verified; diverse double compilation or equivalent argument states compiler compatibility and trust assumptions. External proof-checking research tools may provide independent evidence but MUST NOT be required in the final supported Capstan build/test path. Self-hosting does not prove absence of malicious behavior.

CAP-BST-003 (research-informed mandatory amendment): Separate independent verification evidence from final supported build path; record verifier provenance and shared dependencies. Bootstrap diversity must not rely exclusively on the artifact being assessed. Acceptance obligation: Audit dependency graph for circular trust and reproducibility inputs. Research mapping: R6.

## RFC 0013 — Compiler correctness

CAP-ADV5-024 (proposed normative correction): Bind target, model and assumption versions.


CAP-ADV5-013 (proposed normative correction): Prove substitution and effect preservation.


CAP-CMP-013 (proposed comparative amendment): Require proof-preserving specialization, vectorization and separate compilation; verify discarded checks. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-COR-001: For accepted source P and admissible environment E, target traces refine permitted source traces, preserving security-relevant effects, traps and resource obligations. Optimisation requires a sound side condition for every removed check. A compiler error is permitted only within specified diagnostic/resource rules and cannot masquerade as successful compilation. Proof relates actual compiler, decoder, lowering, backend and runtime revisions; a model-only theorem is insufficient. Acceptance: per-pass simulation, differential execution, negative optimisation controls and proof checker audit.

CAP-COR-002 (mandatory corrective amendment): Refinement MUST cover maximal traces and exclude target stuck states, invented effects and silent divergence when source must terminate under stated assumptions. Preserve rejection of invalid source and fail-closed compilation; translation validation may substitute for a compiler proof only with proved validator soundness and fail-closed execution. Logical charges independent of optimization preserve specified budget failures; separately certify physical resource bounds. Include linker, loader, runtime and separate compilation assumptions.

CAP-COR-003 (research-informed mandatory amendment): For each claimed property class K, require for every admissible target context a source-context witness or another sound robust-preservation argument; for hyperproperties preserve joint observations, not just individual traces. Include linker/loader and binary-level validation with independently checked soundness. Acceptance obligation: Attempt hostile context, paired-trace and incorrect relocation counterexamples. Research mapping: R1,R6.

## RFC 0014 — Cryptography and secrets

CAP-ADV5-014 (proposed normative correction): Use public synthetic inputs and leakage-safe reporting.


CAP-CMP-014 (proposed comparative amendment): Prevent benchmark-driven disabling of masking; use explicit leakage and key lifecycle contracts. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-CRY-001: Cryptography APIs MUST specify allowed algorithms, key sizes, nonce requirements, randomness source, authentication and failure behaviour. No plaintext release before authentication. Secrets cannot flow to ordinary logging or serialization without authorised declassification. Zeroisation and timing guarantees require explicit memory and hardware models; GC copies and compiler transformations must be addressed. Algorithm transition is versioned; strength is not asserted indefinitely. Acceptance: known-answer vectors, nonce misuse, authentication failure and leakage assessment.

CAP-CRY-002 (mandatory corrective amendment): Bind authentication to protocol context and algorithm/version; reject downgrade, replay where freshness is required, and entropy failure. Nonce uniqueness obligations survive restart, rollback and concurrent writers. Secret storage MUST prevent unapproved copies and clear owned buffers on every exit; OS paging, caches, hardware leakage and external copies require explicit assumptions or mitigation. Constant-time claims specify instruction/memory observation and target. Cryptographic guarantees are probabilistic, not absolute.

CAP-CRY-003 (research-informed mandatory amendment): Define target-specific leakage traces including relevant transient events, register transitions and randomness. Require per-pass leakage preservation for claimed cryptographic property, or validated binary-level equivalent; algorithmic correctness alone insufficient. Acceptance obligation: Check paired traces and correlated randomness across optimization passes. Research mapping: R5,R8.

## RFC 0015 — Resource accounting

CAP-REV6-015: Admission MUST atomically reserve operation and cleanup capacity across every dimension; transfers MUST conserve reservations. Arithmetic MUST be checked before mutation.

CAP-ADV5-021 (proposed normative correction): Keep reservation until isolation established; declare availability loss.


CAP-ADV5-015 (proposed normative correction): Retain reservations until verified completion.


CAP-CMP-015 (proposed comparative amendment): Measure physical cost independently of logical charges; include compilation, GC, queues and accelerator work. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-RES-001: Distinguish cumulative work W from live resources L. Every charge c is nonnegative and admitted only if c ≤ B-W or c ≤ B-L, as applicable, using checked arithmetic. Release decreases L exactly once and never W. Child reservations and concurrent admission conserve aggregate capacity. Budget exhaustion precedes the prohibited effect. Host work requires bounded APIs or documented isolation. Acceptance: overflow, double release, cancellation, aliasing and concurrent admission tests; inductive conservation proof.

CAP-RES-002 (mandatory corrective amendment): Use vector budgets for work, live bytes, handles, tasks, output and waits; reserve atomically across dimensions or reject without partial admission. Parent-child reservations conserve capacity; persistent output and external work remain charged until transferred or ended. Every externally driven loop charges positive work; bound validation, bookkeeping and cleanup with pre-reserved capacity. Physical CPU/time guarantees require measured or proved cost bounds and host assumptions, not merely logical fuel.

CAP-RES-003 (research-informed mandatory amendment): Use explicit physical resource assumptions, including scheduler and shared accelerator contention; meter analysis itself and require bounded certificate checking. No confidentiality inference from equal logical charges. Acceptance obligation: Compare equal-fuel jobs with distinct observed timing and budget exhaustion. Research mapping: R4,R8.

## RFC 0016 — Platform interfaces

CAP-ADV5-016 (proposed normative correction): Initialize or exclude padding at boundary.


CAP-CMP-016 (proposed comparative amendment): Specify safe ABI layout and typed handles; deny unsupported platform operations rather than emulate insecurely. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-PLT-001: Each supported platform MUST publish ABI, syscall inventory, descriptor lifetimes, error mapping, limits and trust assumptions. Host responses are untrusted structured inputs; validate before effects or copies. Ordinary application code cannot bypass checks through raw pointers, arbitrary syscalls or foreign calls. Narrow implementation-owned adapters are trusted components, not source-language escape hatches. Acceptance: mock-host fault injection and real-platform tests, including partial operations, interrupts and hostile lengths.

CAP-PLT-002 (mandatory corrective amendment): Each adapter MUST have typed capability-scoped entry points, explicit ABI marshalling, checked lengths, bounded handle counts and partial-effect semantics. Treat hostile host data separately from malicious kernel behavior; the latter is outside guarantees unless isolated by a stronger verified boundary. Prevent descriptor reuse and path TOCTOU via stable handles. No dynamic native loading or arbitrary foreign calls by ordinary programs. Unsupported platform operations fail closed.

CAP-PLT-003 (research-informed mandatory amendment): Version CPU/GPU, firmware, microcode, loader and observation models; require platform-specific leakage and isolation evidence. Disable operation or withhold affected conformance claim on unmet assumptions, not weaken the language profile. Acceptance obligation: Change platform measurement and verify claim invalidation. Research mapping: R7,R8.

## RFC 0017 — Vulnerability-class exclusion

CAP-ADV5-017 (proposed normative correction): Publish per-metric results and mandatory floors.


CAP-CMP-017 (proposed comparative amendment): Maintain a claim registry with baseline versions, metrics, environments, losses and counterexamples. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-CWE-001: Each claim names weakness definition/version, scope, attacker model, invariant, theorem, implementation correspondence, tests and residual boundaries. Evidence classes are distinct: specified, tested, model-proved, implementation-proved. A CWE identifier alone is not an exclusion proof. Unknown vulnerabilities and application-policy errors remain possible. Acceptance: independent audit of each claimed exclusion and counterexample search, with stale evidence invalidating claims.

CAP-CWE-002 (mandatory corrective amendment): Quantify exclusion over accepted programs, supported environments and weakness predicate; distinguish prevention, detection, containment and residual risk. Require counterexample attempts and independent review; never infer coverage from a CWE family label. Evidence invalidation propagates transitively on changes to assumptions or dependencies. Publish known counterexamples and withdraw affected claims promptly.

CAP-CWE-003 (research-informed mandatory amendment): Require independently reviewed theorem-to-claim mapping, nonvacuity witness, threat model, counterexample regressions and dependency invalidation. Scope vulnerability exclusions to actual modeled mechanisms. Acceptance obligation: Mutate theorem premise and evidence dependency; reject vacuous claim. Research mapping: R2,R6.

## RFC 0018 — Conformance and certification

CAP-REV6-018: Bounded model evidence MUST publish state domains, transition relation, checked properties and counterexamples. A tautological assertion or absence of a counterexample within a finite domain MUST NOT be classified as implementation verification.

CAP-ADV5-022 (proposed normative correction): Limit tuning access and rotate independently curated tests.


CAP-ADV5-018 (proposed normative correction): Hold out independently maintained workloads.


CAP-ADV5-001 (proposed normative correction): Include full admission and startup; report steady state separately.


CAP-CMP-018 (proposed comparative amendment): Require reproducible benchmark protocols, confidence intervals and independent reruns; no certification based on aggregate scores. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-CNF-001: Full language conformance requires all adopted mandatory requirements. Assurance evidence tiers describe strength of evidence, never weaker language profiles. Release manifest binds requirement IDs to exact source, target, toolchain, proof artifacts and test results. Missing or stale mandatory evidence blocks the corresponding certification. Independent verifier must reproduce results; deviations are published. Acceptance: manifest validator rejects missing, mismatched and expired evidence.

CAP-CNF-002 (mandatory corrective amendment): Define signed manifest schema with requirement ID, semantic version, source/target digests, proof assumptions, checker version, test corpus and evidence dependency graph. Reject missing, cyclic, unverifiable or revoked evidence; avoid self-attestation as independent review. Conformance and formal certification are separate labels with exact scope. No grandfathering of withdrawn security claims; deviations cannot be called full conformance.

CAP-CNF-003 (research-informed mandatory amendment): Reject unapproved axioms, admitted lemmas and unverifiable evidence; inventory trusted checker, model and binary identity. Distinguish bounded exploration from proof and require independent replay. Acceptance obligation: Inject admitted lemma, stale binary digest and missing assumption. Research mapping: R2,R6.

## RFC 0019 — Supply chain and reproducibility

CAP-ADV5-019 (proposed normative correction): Verify provenance and isolate execution.


CAP-CMP-019 (proposed comparative amendment): Pin dependencies and benchmark corpora; audit telemetry and cache provenance. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-SUP-001: Pin inputs, dependencies and build environment; identify artifacts by digest, publish provenance and SBOM, sign release manifests with revocable keys. Reproducible builds require independent comparison and declared nondeterminism. Compromise response includes revocation, notification and rebuilt artifacts. A signature attests provenance, not code safety. Acceptance: tampered artifact, substituted dependency, revoked key and independent build tests.

CAP-SUP-002 (mandatory corrective amendment): Use threshold-controlled release authorization, pinned trust roots, rollback protection and a signed freshness/revocation policy. Verify metadata and artifacts before execution; constrain archive paths and unpacking resources. Reproducibility comparison includes all shipped executable artifacts and declared normalization. Define recovery when signing keys or build infrastructure are compromised; offline verification must disclose freshness limits.

CAP-SUP-003 (research-informed mandatory amendment): Bind release and evidence manifests to target policy and monotonically versioned assumptions; freshness failure cannot silently authorize new execution requiring current certification. Acceptance obligation: Replay valid old evidence under revoked target policy. Research mapping: R6,R7.

## RFC 0020 — Governance and evolution

CAP-REV6-020: Draft submission MUST distinguish unratified proposals from adopted standards; unresolved obligations MUST remain in the review register.

CAP-ADV5-020 (proposed normative correction): Version protocols before execution and require independent review.


CAP-CMP-020 (proposed comparative amendment): Require public trade-off register, independent challenge process and research-driven amendments. Acceptance: demonstrate the corresponding obligation under the comparative protocol below.

CAP-GOV-001: Independent open standards process under prospective Foundation stewardship. Public proposals, recorded rationale, conflict disclosures, review periods, resolution of objections and appeal process are required. Adopted requirements have stable IDs and versioned changes. Security invariants cannot be weakened merely for convenience; corrections to erroneous or unrealizable requirements require public rationale, threat analysis and migration plan. Emergency security amendments receive retrospective review. Until a Foundation exists, interim maintainers publish decisions without claiming legal Foundation status. Acceptance: public decision register, independent review and documented ratification rules; voting/quorum rules require stakeholder adoption.

CAP-GOV-002 (mandatory corrective amendment): Propose public minimum 30-day ordinary review, conflict disclosure, recorded technical objections and independent appeal; emergency changes may use expedited review with public rationale and subsequent ordinary review. No individual may both propose and solely approve a security claim. Ratification requires published quorum and voting rules adopted by stakeholders; until then all texts remain drafts. Security invariant corrections require proof impact analysis and explicit transition version; no hidden compatibility bypass.

CAP-GOV-003 (research-informed mandatory amendment): Record research maturity, applicability, alternatives and proof impact; require independent review of normative changes and new threat assumptions. No research result automatically establishes Capstan conformance. Acceptance obligation: Review a proposal that narrows attacker scope solely to pass a proof. Research mapping: R2,R6.

# Adversarial cross-series design review

| Severity | Design flaw / tension | Corrective requirement incorporated above | Remaining gate |
|---|---|---|---|
| Critical | Model proof mistaken for implementation proof | RFC 13/17 require refinement and exact revisions | Whole compiler/runtime proof |
| Critical | Unsafe host boundary defeats single profile | RFC 16 prohibits ordinary bypass, audits adapters | ABI inventory and isolation proof |
| Critical | Injection through second interpreter or stored data | RFC 7 specifies downstream decoding and structural integrity | Sink-specific formal contracts |
| High | Bounded bytes do not bound CPU, decompression or waits | RFC 6/15 separate cumulative work and waits | Runtime enforcement including blocking I/O |
| High | Revocation races with effect commitment | RFC 8 demands atomic check or lease | Concurrent grant semantics |
| High | Bootstrap fixed point can reproduce compromised compiler | RFC 12/19 require independent provenance | Diverse verification protocol |
| High | Optimisation erases traps or budget charges | RFC 4/13 preserve security-relevant traces | Cost model and per-pass proofs |
| High | Secret zeroisation conflicts with GC and optimiser | RFC 14 limits claim to explicit models | Concrete secret runtime proof |
| High | Concurrency conflicts with unconditional determinism | RFC 4/10 trace-relative semantics | Formal scheduler model |
| High | Budget releases enable repeated work or double release | RFC 15 separates live/cumulative accounting | Concurrent ledger refinement |
| High | Concrete grammar/types may differ from implementation | RFC 2/3 mark reconciliation gates | Pinned parser and typing audit |
| Medium | Foundation governance could freeze erroneous rules | RFC 20 permits justified corrections | Ratified constitution and appeals |
| Medium | Evidence tiers mistaken for unsafe profiles | RFC 18 explicitly separates them | Manifest schema and release policy |
| Medium | Platform and crypto promises age | RFC 14/16/19 version targets and algorithms | Maintenance schedule and deprecation policy |

## Review verdict
No claim of flaw-free design or final standard is justified. Draft-level corrections are integrated; implementation and mathematical validation remain open. In particular, concrete grammar, full typing rules, operational transition rules, CCAM opcode inventory, platform ABI and mechanised proofs are not complete here. Before ratification, reconcile every requirement with pinned source, produce executable conformance vectors, complete formal definitions and proofs, obtain independent review and resolve all critical/high findings. Existing repository write authorisation was denied; this document is a local draft, not a merged repository change.


# Iterative review — revision 0.3

Review method: desk review of each amended RFC against its neighboring contracts, then adversarial counterexample walkthroughs and a final consistency pass. This is not exhaustive model checking or an independent audit.

| Pass | Finding / counterexample | Amendment | Draft disposition |
|---|---|---|---|
| 1 | Original fourteen risks remain underspecified at failure boundaries | All original requirements preserved; see amendments 004–020 | Addressed normatively; evidence outstanding |
| 2 | Unicode alias or import collision changes meaning | 0002/0003 | Addressed |
| 2 | Generic container erases secret or grant labels | 0003/0007 | Addressed |
| 2 | Parser recovery accepts invalid suffix | 0002/0013 | Addressed |
| 2 | Recycled handle makes stale grant valid | 0005/0008/0016 | Addressed |
| 2 | Partial I/O commits before later trap | 0004/0009/0016 | Addressed |
| 2 | Parameterized query still selects another tenant | 0007/0008 | Addressed |
| 2 | Validator certificate reused after byte mutation | 0011 | Addressed |
| 2 | Compiler silently diverges while source terminates | 0013 | Addressed |
| 2 | Nonce repeats after restart or rollback | 0014 | Addressed |
| 2 | Multi-budget admission partially succeeds | 0015 | Addressed |
| 2 | Signed old release bypasses current policy | 0019 | Addressed |
| 2 | Evidence dependency changes without invalidation | 0017/0018 | Addressed |
| 2 | Governance capture through sole reviewer | 0020 | Addressed as proposal |
| 3 | Cleanup consumes exhausted budget | 0010/0015 reserve cleanup capacity | Addressed |
| 3 | Lease revocation contradicts immediate revocation | 0008 explicitly defines effective revocation | Addressed |
| 3 | Optimization changes fuel even when results agree | 0013 separates logical charges from physical bounds | Addressed |
| 3 | Isolation returns while host operation still consumes resources | 0006/0010/0015 retain reservation | Addressed |
| 3 | External proof checker conflicts with native build requirement | 0012 separates independent research evidence from supported build | Addressed |
| 3 | Finite trace refinement hides divergence | 0004/0013 maximal traces | Addressed |
| 3 | Offline verifier cannot know latest revocation | 0019 freshness disclosure | Addressed |
| 4 | Cross-check authority/lifetime, trace/cost, parser/validator, proof/claims, governance/release | No additional distinct finding identified in this bounded desk pass | Provisional stopping point |

## Residual gates (not closed)
Concrete grammar and complete type rules; executable semantics and opcode catalogue; formal observation/adversary models per sink; cost models and bounded host cancellation; actual ABI inventories; mechanised proofs and implementation correspondence; independent bootstrap verification; certification manifest implementation; independent adversarial review; governance ratification. These are substantive open design and evidence obligations, not merely editorial work. No claim of zero remaining actual risk. No repository changes or tests performed in this revision.

# Revision 0.4 — research register (27 November 2026)
Targeted literature scan, primarily abstracts and programme records; not a systematic review or full-paper replication. All amendments are proposed Capstan requirements, not results established by cited research.

- R1: Endangered by the Language But Saved by the Compiler, POPL 2026. https://people.mpi-sws.org/~mueck/downloads/paper-popl26.pdf
- R2: Detecting Inconsistencies in Arm CCA's Formally Verified Specification, ASPLOS 2026. https://doi.org/10.1145/3779212.3790152
- R3: Structural Information Flow: A Fresh Look at Types for Non-interference, OOPSLA 2025. https://doi.org/10.1145/3764116
- R4: Let It Flow: A Formally Verified Compilation Framework for Asynchronous Dataflow, PLDI 2026. https://doi.org/10.1145/3808263
- R5: Secure Compilation of Probabilistic Side-Channel Countermeasures, October 2026 preprint. https://eprint.iacr.org/2026/2510
- R6: AlphaProof Code: Verifying Signal's Security at the Machine-Code Level, November 2026 technical report. https://google-deepmind.github.io/code-verification/
- R7: Towards Robust Secure Compilation in Presence of Speculative Execution, PriSC 2026 workshop contribution. https://perso.telecom-paristech.fr/brandner/paper/prisc26-clement.pdf
- R8: USENIX Security 2026 accepted papers, including UncoreBleed, M-Step and TIMESLICE-SANDWICH work. https://www.usenix.org/conference/usenixsecurity26/cycle1-accepted-papers

## Pass 5 — research-derived counterexamples
| RFC | Finding | Resolution | Evidence status |
|---|---|---|---|
| 0001 | Threat model drift and vacuous guarantees | See new -003 amendment | Open: Construct a hostile context and a valid execution witness. |
| 0002 | Parser differential via normalization or tooling | See new -003 amendment | Open: Compare parser and tooling AST on malformed and equivalent encodings. |
| 0003 | Structural labels lost at abstraction boundaries | See new -003 amendment | Open: Prove substitution and abstraction preserve labels; test secret-dependent variant selection. |
| 0004 | Inconsistent or vacuous transition rules | See new -003 amendment | Open: Check overlapping guards and unreachable success conditions. |
| 0005 | Hostile native code invalidates source safety | See new -003 amendment | Open: Attempt cross-module writes and stale DMA accesses in platform model. |
| 0006 | Budget or deadline side channel | See new -003 amendment | Open: Compare traces for paired secret inputs and stalled host. |
| 0007 | Noninterference vacuous on rejected payloads | See new -003 amendment | Open: Test accepted/rejected pairs, fallback parser and stored payload. |
| 0008 | Cross-module authority laundering | See new -003 amendment | Open: Explore reentrant deputy and concurrent revoke/commit. |
| 0009 | Target arithmetic leakage or undefined flags | See new -003 amendment | Open: Compare target traces on boundary operands and secret-dependent latency. |
| 0010 | Determinacy proof assumes scheduler fairness | See new -003 amendment | Open: Enumerate bounded interleavings including unfair paths and cancellation. |
| 0011 | Validation does not protect native execution | See new -003 amendment | Open: Reject certificate replay under altered loader configuration. |
| 0012 | Independent evidence conflicts with Capstan-only production | See new -003 amendment | Open: Audit dependency graph for circular trust and reproducibility inputs. |
| 0013 | Closed-world correctness misses adversarial linking | See new -003 amendment | Open: Attempt hostile context, paired-trace and incorrect relocation counterexamples. |
| 0014 | Optimization breaks masking or transient confidentiality | See new -003 amendment | Open: Check paired traces and correlated randomness across optimization passes. |
| 0015 | Logical fuel conceals physical/shared resource leakage | See new -003 amendment | Open: Compare equal-fuel jobs with distinct observed timing and budget exhaustion. |
| 0016 | Hardware isolation assumptions become obsolete | See new -003 amendment | Open: Change platform measurement and verify claim invalidation. |
| 0017 | Evidence theorem proves wrong property | See new -003 amendment | Open: Mutate theorem premise and evidence dependency; reject vacuous claim. |
| 0018 | Proof checker or AI-generated assumptions conceal gaps | See new -003 amendment | Open: Inject admitted lemma, stale binary digest and missing assumption. |
| 0019 | Rollback of evidence or verifier configuration | See new -003 amendment | Open: Replay valid old evidence under revoked target policy. |
| 0020 | Research-driven amendments silently weaken invariants | See new -003 amendment | Open: Review a proposal that narrows attacker scope solely to pass a proof. |

## Pass 6 — secondary interactions
The following additional corrections are normative and supplement the -003 requirements.

1. CAP-COR-004 / CAP-CORE-004: Context back-translation must not grant the source witness additional authority unavailable to the original admissible context; independently define context relation and observation mapping. A safety witness is not sufficient for a relational confidentiality theorem.
2. CAP-CRY-004 / CAP-RES-004: Randomness consumption, rejection sampling and padding must be included in resource and leakage analysis; an exhausted padding budget cannot release an unprotected result. Reserve worst-case capacity or use a specified safe failure with permitted observation.
3. CAP-CON-004 / CAP-AUT-004: An authority-bearing queued message must be checked at the specified commitment point and cannot regain authority via cancellation, retry or replay. Preserve ownership and reservation independently of grant validity.
4. CAP-CONF-004 / CAP-SUP-004: Evidence revocation is not retroactive proof of exploitation. Distinguish invalidated certification from unsafe execution; define fresh admission policy and bounded revocation distribution for managed deployments. Offline systems explicitly state maximum evidence age and fail closed when required freshness cannot be established.
5. CAP-BST-004 / CAP-GOV-004: Independent external proof tooling is allowed for research and external certification, not as a concealed mandatory foreign-language production toolchain dependency. Publish proof checker assumptions and avoid claiming the entire evidence ecosystem is Capstan-native.

## Pass 7 — targeted consistency walkthrough
Checked context quantification versus authority, logical versus physical charges, cryptographic failure versus leakage, revocation versus queued ownership, and independent proof evidence versus native-toolchain scope. No additional distinct counterexample identified in this limited walkthrough after the five amendments above. This is a desk-review stopping point, not an exhaustive search or a proof.

## Release disposition
Twenty research-informed amendments and five interaction corrections added. All 25 have draft-level requirements, but all associated proof/test obligations remain open. The prior 33 findings are retained, not independently revalidated. No compiler or theorem prover executed; no repository writes performed. Remaining blockers include complete grammar and semantics, formal context/observation relations, platform models, implementation-linked proofs and independent ratification.


# Revision 0.5 — comparative design programme

Scope: representative language families, not an exhaustive census of all languages or versions. Comparisons below are design targets, not measured rankings. No external source or benchmark was consulted in this revision.

| Baselines | Strength to preserve | Proposed Capstan response | Evidence gate |
|---|---|---|---|
| C, C++, Zig, D, Odin | native control, layout, ABI, predictable cost | explicit safe layout and verified check elision; no raw pointer escape | native kernels, size, latency, memory |
| Rust, Ada/SPARK, ATS, Cyclone | ownership, contracts, dependent resource reasoning | compositional lifetime and authority proofs with ergonomic inference | allocator and ownership counterexamples; annotation burden |
| Haskell, OCaml, F#, Standard ML, Elm | algebraic types, inference, exhaustive matching | principal types where decidable, explicit fallback, exhaustive matches | type inference and refactoring corpus |
| Lean, Coq/Rocq, Agda, Idris, F*, Dafny, Why3 | proofs, dependent types, verification automation | proof erasure only under verified refinement; bounded proof checking | proof replay, trust inventory, proof effort |
| Java, C#, Kotlin, Scala, Swift | managed runtimes, tooling, libraries | safe generic libraries and stable ABI contracts; predictable GC budgets | startup, GC tails, IDE latency |
| Python, Ruby, JavaScript, TypeScript, Lua, PHP | rapid development, scripting, ecosystem | concise safe APIs, bounded dynamic values, fast iteration | task completion time, diagnostics, compatibility |
| Go, Erlang, Elixir, Pony, Newspeak | concurrency, actors, fault isolation | structured tasks, bounded mailboxes and non-amplifying supervision | cancellation, throughput, fault recovery |
| Julia, MATLAB, R, Fortran, Chapel, X10 | numerics, array programming, HPC | typed shapes, explicit numerical error and safe parallel kernels | BLAS-like workloads, accuracy, scaling |
| CUDA C++, OpenCL C, WGSL, GLSL, HLSL | accelerator execution and shaders | validated kernels and isolation with explicit device assumptions | GPU throughput, transfer overhead, invalid dispatch |
| SQL, Datalog, Prolog, miniKanren | declarative queries and logic | typed query ASTs and bounded search with explicit completeness limits | query plans, hostile inputs, search exhaustion |
| Scheme, Common Lisp, Racket, Clojure, MetaOCaml | macros and metaprogramming | hygienic staged typed generation under compiler budgets | capture, phase confusion, expansion cost |
| Smalltalk, Eiffel, Simula, Objective-C | objects, contracts, live tooling | checked dispatch and substitutable contracts; isolated live reload | contract inheritance, stale code, update latency |
| APL, J, K, BQN, Forth, Factor | compact array and stack abstractions | typed combinators and shape/stack verification | expressiveness, stack safety, code size |
| COBOL, ABAP, PL/I, RPG, Visual Basic | business data and decimal semantics | exact decimal arithmetic and schema evolution | accounting correctness, migration fidelity |
| Bash, PowerShell, Tcl, awk, Perl | automation and text processing | structured process arguments, bounded streams and safe pattern engines | pipeline workloads, regex exhaustion |
| WebAssembly, LLVM IR, JVM bytecode, CLR IL | portable validated execution and optimization | canonical CCAM and verified backend contracts | validation, startup, cross-target equivalence |
| Solidity, Move, Michelson, Scilla | asset conservation and transaction semantics | linear resources and explicit transactional effects | reentrancy, rollback, conservation |
| Scratch, Blockly, Logo, Pascal, BASIC | learnability and education | accessible diagnostics and progressive teaching without weaker safety | novice task completion and error recovery |
| Verilog, VHDL, SystemVerilog, Chisel | hardware description and timing | do not claim hardware synthesis support; model interfaces and timing separately | only compare supported hardware-facing tasks |
| SPSS, SAS, Stata, Mathematica, Maple | statistics and symbolic computation | reproducible numeric and symbolic libraries with bounded algorithms | statistical accuracy and symbolic resource limits |

## Adversarial review register — pass A (comparative counterexamples)

| Finding | Required correction | RFC |
|---|---|---|
| Benchmark excludes validation cost | Include full admission and startup; report steady state separately | 0018 |
| Unsafe baseline wins by omitting checks | Report raw and assurance-matched baselines separately | 0001 |
| Unbounded macro recursion | Charge expansion and reject before emission | 0002 |
| Inference timeout accepts partial type | Fail closed on timeout | 0003 |
| SIMD tail reads past end | Prove lane bounds or mask with verified semantics | 0005 |
| Backpressure queue shifts exhaustion upstream | Reserve end-to-end capacity and bound outstanding work | 0006 |
| Query optimizer changes authorization scope | Preserve policy-filtered relational semantics | 0007 |
| Transaction retries duplicate external effects | Use explicit idempotency protocol or prohibit retry | 0008 |
| Decimal rounding changes policy threshold | Specify exact comparison or authorized rounding rule | 0009 |
| Supervisor restarts mint work budget | Charge cumulative parent budget | 0010 |
| Portable fallback weakens mandatory semantics | Reject unsupported execution | 0011 |
| Incremental cache reuses proof for changed dependency | Bind transitive inputs and toolchain versions | 0012 |
| Specialization drops security label | Prove substitution and effect preservation | 0013 |
| Timing benchmark reveals secrets | Use public synthetic inputs and leakage-safe reporting | 0014 |
| GPU asynchronous work escapes budget | Retain reservations until verified completion | 0015 |
| ABI padding leaks prior data | Initialize or exclude padding at boundary | 0016 |
| Aggregate score hides severe regression | Publish per-metric results and mandatory floors | 0017 |
| Benchmark tuner overfits public corpus | Hold out independently maintained workloads | 0018 |
| Benchmark dependency is compromised | Verify provenance and isolate execution | 0019 |
| Foundation changes metric to favor Capstan | Version protocols before execution and require independent review | 0020 |

## Pass B — amendment interaction counterexamples

| Finding | Required correction | RFC |
|---|---|---|
| Budgeted cleanup still waits for device reset | Keep reservation until isolation established; declare availability loss | 0015 |
| Holdout results leak via repeated submissions | Limit tuning access and rotate independently curated tests | 0018 |
| Exact decimal arithmetic exhausts memory | Bound precision before allocation and charge work | 0009 |
| Proof cache key omits platform assumptions | Bind target, model and assumption versions | 0013 |
| Live upgrade races with in-flight grants | Quiesce or version authority and preserve commitment semantics | 0004 |

## Pass C — targeted recheck
Check the 25 counterexamples against their newly inserted requirements. Each has a matching normative correction; this is a traceability check, not a proof that the correction is sufficient or that no new risks exist. Open design questions include the feasible overhead of robust compilation, exact inference fragment, platform isolation and resource-bound completeness. No executable adversarial model was run.

## Comparative protocol
Pin each language implementation, version, flags, platform, workload, input and assurance configuration. Require equivalent output and numerical accuracy; record failures and unsupported tasks explicitly. Measure median and tail latency, throughput, peak memory, binary size, cold/incremental build time, energy where measured, proof effort, diagnostic quality and accessibility. Use repeated trials and publish uncertainty, raw data and negative outcomes. Evaluate expressiveness with representative tasks and independent human studies; ecosystem breadth is a separate metric. Never infer universal superiority from a finite corpus. No benchmark results are asserted here.

## Revision 0.6 — bounded executable review

New counterexample: finite generation or authority epoch wrap can revalidate stale references or grants (ABA). Corrected by CAP-REV6-005 and CAP-REV6-008. Remaining risk: exhaustion can cause availability loss, which must be explicit and accounted for; no identity reuse is permitted without proof.

The companion Python model checks elementary finite admission arithmetic and retirement; the authority predicate check is definitional, not an independent transition-system proof. It exercises no production code. Python is external research tooling only, not part of the Capstan-native production toolchain.

```text
Budget states checked: 875
Authority states checked: 288
ABA counterexample: width 1 reuse count 2
ABA counterexample: width 2 reuse count 4
ABA counterexample: width 3 reuse count 8
ABA counterexample: width 4 reuse count 16
Non-wrapping generation states checked: 152
```

Review remains open: concurrency interleavings, crash recovery, compiler refinement and platform leakage are not explored by these checks. Prior findings are retained without independent revalidation. No universal superiority or absence-of-risk claim is justified.

## Revision 0.7 — implementation gates and executable transition review

Normative amendments to RFCs 0004, 0008, 0010 and 0015: queued operations MUST revalidate object identity, authority epoch, principal and operation atomically at the external effect commitment point. Revocation and commitment MUST share a specified linearization order. Reservation ownership transfers exactly once; cancellation or completion releases or consumes it exactly once. Admission and commitment are distinct. The finite reference model checks a single object and single queued request with three units of budget and epochs 0–2; it is not a production implementation.

Normative amendments to RFCs 0004, 0016 and 0019: replay-resistant effects MUST bind a stable operation identifier to the canonical request and authority scope; where exactly-once commitment is claimed, the deduplication record and external effect MUST commit atomically in the same failure domain, or an independently verified endpoint protocol MUST provide equivalent semantics. Otherwise expose an explicit uncertain outcome and prohibit automatic non-idempotent retries. Deduplication retention MUST cover the permitted retry horizon and identifiers MUST NOT be silently reused. The finite crash model assumes atomic durability, one request and at most two effects; it does not prove distributed exactly-once delivery.

### Engineering sequence and acceptance gates

| RFC | Concrete implementation deliverable | Required evidence before ratification |
|---|---|---|
| 0001 | Versioned conformance schema | Satisfiability witnesses and requirement audit |
| 0002 | Byte-level grammar and reference parser | Parser equivalence and malformed-input vectors |
| 0003 | Syntax-directed typing and effect rules | Mechanised substitution, preservation and progress |
| 0004 | Reference small-step interpreter | Transition coverage and trace refinement |
| 0005 | Object identity and lifetime ledger | Allocator refinement and stale-handle tests |
| 0006 | Bounded input syntax and adapters | Boundary, cancellation and partial-input tests |
| 0007 | Typed interpreter adapters | Noninterference and persistent taint proof |
| 0008 | Authority ledger with commit-time checks | Revocation races and authority conservation |
| 0009 | Exact numeric semantics and trap table | Boundary and target equivalence tests |
| 0010 | Scheduler, message and cancellation semantics | Interleaving exploration and race-freedom proof |
| 0011 | Versioned CCAM schema and validator | Decoder totality and evaluator correspondence |
| 0012 | Native bootstrap manifest and build graph | Full reproducible Capstan-only staged rebuild |
| 0013 | Pass-by-pass refinement and binary validation | Robust security preservation proof |
| 0014 | Secret lifecycle and primitive interfaces | Leakage model and cryptographic evidence |
| 0015 | Multidimensional reservation ledger | Conservation, exhaustion and cleanup proof |
| 0016 | Target ABI and host capability inventory | Host contract tests and isolation evidence |
| 0017 | Claim-to-theorem registry | Independent scope and counterexample audit |
| 0018 | Evidence checker and conformance harness | Freshness, tamper and negative tests |
| 0019 | Signed release and recovery protocol | Reproducibility and rollback resistance |
| 0020 | Foundation charter and amendment process | Independent review and ratification records |

These gates are open unless exact-revision evidence is supplied. No theorem prover, compiler benchmark or independent reviewer was available for this revision. The Python review is external research tooling only. The concrete grammar, typing rules, full machine instruction inventory and platform ABI remain incomplete. Do not treat this document as a ratified or implementation-complete standard.
commit revalidation=False: 60 states, 128 edges, 27 violating edges
shortest witness: ['enqueue', 'revoke', 'commit']
commit revalidation=True: 60 states, 101 edges, 0 violating edges
shortest witness: none
atomic durable dedup=False: 5 states, 11 edges, 5 violating edges
atomic durable dedup=True: 3 states, 7 edges, 0 violating edges