# Anchor: system architecture

**Status:** proposed design specification; not implemented
**Parent:** docs/ANCHOR.md

## Purpose

Anchor is Capstan's integrated development environment and security engineering workbench. It is a client of the compiler, language services, Shroud and assurance infrastructure. It MUST NOT duplicate language semantics, independently issue compiler verdicts, or become an assurance authority.

The product has three modes: professional source development; source-authoritative visual Shroud design; and security engineering with explicit evidence provenance.

## Invariants

- Capstan source is canonical. Syntax trees, indexes, visual projections and caches are derived and revision-bound.
- Compiler and LSP own parsing, typing, diagnostics and semantic facts.
- Opening a workspace never executes project code, hooks, extensions, package scripts or commands.
- UI visibility is not authorization. The service performing an operation enforces policy.
- Malformed, stale, ambiguous or unverifiable inputs fail closed or become explicitly unknown.
- Every parser, queue, process, index, render and evidence operation has hard resource bounds.
- Every assurance result identifies its exact subject, inputs, tool, policy, verifier and freshness.
- Unsupported platform/compiler/runtime APIs are unavailable, not simulated.
- Dependency direction is acyclic: compiler/runtime below tooling; Shroud below Anchor; Anchor consumes both.

## Logical architecture

    Anchor application (Capstan)
      Workspace UX | Editor | Designer | Evidence UX
      Application model, navigation and command policy
      Documents | Language adapter | Build/test | Assurance reader
      Policy, identity, bounded IPC and audit events
          |              |                 |
       Capstan CLI/LSP  Shroud S0/S1   Evidence store/verifiers

This is a logical decomposition, not a claim that every interface exists.

## Subsystem ownership

**Workspace:** canonical root identity, bounded enumeration, declarative project metadata and workspace lifecycle. UI receives workspace-relative handles, not arbitrary paths.

**Documents:** decoding, buffers, versions, dirty state, save/reload and external-change detection. Writes use same-directory temporary files and atomic replacement where supported; conflicts are never silently overwritten.

**Language adapter:** JSON-RPC framing, request IDs, versions, cancellation, bounded queues, process lifecycle and diagnostics association. Compiler responses remain authoritative.

**Build/test:** fixed command allowlist, executable identity, structured arguments, environment allowlist, working directory, timeout, cancellation, output bounds and provenance. No project hooks.

**Designer:** compiler-backed visual projection, source mapping and constrained source transformations. No parallel visual source of truth.

**Assurance:** verifies and presents evidence scope; it does not turn missing evidence into a pass or infer security from a clean compile.

**Shroud presentation:** views, accessibility and interaction only. No filesystem, process, compiler or trust decisions.

## State and concurrency

The application model owns visible state. Every asynchronous result carries workspace identity/generation, document identity/version where relevant, operation ID and toolchain/policy identity. Results from obsolete generations or older document versions are discarded. Cancellation is not complete until the service confirms termination.

## Trust zones

Workspace data, compiler output, build artifacts, external evidence and catalogue metadata are untrusted until validated. A signature establishes identity/provenance under a policy, not benignness. Native host trust is limited to its explicitly stated assurance boundary.

## Cross-cutting contracts

Every service needs a versioned contract for types, ownership, errors, resource limits, cancellation, concurrency, security assumptions and test vectors. No workstream invents a substitute API when a prerequisite is missing.

The process API and Shroud native host remain A1 blockers in docs/ANCHOR.md. Anchor MUST NOT use shell calls, system(), popen() or private C shims.

## Observability

Record operation ID, workspace-relative target, executable identity, redacted arguments, profile, timestamps, exit status and evidence references. Never log source contents, credentials or environment values. Logs are not tamper-proof audit evidence unless separately protected.

## Required architecture decisions

- ADR-A01: Shroud native host ownership and lifecycle.
- ADR-A02: Capstan-native capability-scoped process API.
- ADR-A03: compiler syntax/token/source-map/transformation API.
- ADR-A04: document encoding and atomic-save policy.
- ADR-A05: workspace manifest schema and migration.
- ADR-A06: evidence envelope and verifier interoperability.
- ADR-A07: offline trust snapshots and anti-rollback.

## Acceptance gates

Each subsystem has an owner, contract, threat analysis and resource budget; dependency direction is acyclic; stale results cannot mutate current state; security-critical operations are enforced in services; unsupported features are visibly unavailable; architecture tests reject forbidden dependency directions and shell escape hatches.
