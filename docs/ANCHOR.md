# Anchor: IDE architecture and first milestone

**Status:** proposal and S0-compatible prototype  
**Target:** Capstan v0.6  
**Implementation branch:** `feature/anchor`

Anchor is the integrated development environment for Capstan. It is a client of the
existing compiler, language server and Shroud library; it is not a second compiler,
a second source of diagnostics, or an assurance authority.

## 1. Current facts and boundaries

The repository currently provides:

- a self-hosting Capstan 0.4.0 compiler with `check`, `build` and `test` commands;
- `capstan fmt` and a bounded LSP server (`capstan lsp`);
- LSP initialize/shutdown/exit, open/change/close document notifications and
  `publishDiagnostics`, including compiler line/column, severity, diagnostic code
  (including CWE codes), and a CWE description URL;
- Shroud S0: a headless, deterministic renderer, widgets, input handling, keyboard
  navigation, accessibility tree and PNG output.

There is no native Shroud window embedder, full text editor, syntax-highlighting API,
debugger protocol, package manager, or generic typed Shroud message API in this
baseline. Compiler v0.5/v0.6 roadmap items are not current interfaces. Anchor must
show these as unavailable/planned, not simulate them as working features.

The compiler CLI currently accepts source paths and supports:
- `capstan check [--strict] [--release] file.cap...`
- `capstan build file.cap... -o program [--strict] [--release]`
- `capstan test file.cap...`
- `capstan fmt file.cap... [--check]`
- `capstan lsp`

The LSP's documented initialization options include `strict` and `release`.
Its current server implementation is a useful diagnostics source, not yet a complete
IDE language-intelligence service.

## 2. Architectural shape

Keep the application split into independently testable services:

1. **Workspace model** — canonical workspace root, project metadata, open documents,
   dirty buffers and selected build profile. Treat every project file as untrusted.
2. **Document service** — bounded UTF-8 reads, buffer versions, file identity,
   dirty-state tracking and atomic save. Reject symlinks/path escapes where the host
   implementation permits reliable checks; never resolve an import outside the
   workspace merely because a project requests it.
3. **Language service adapter** — one supervised `capstan lsp` child per workspace
   (or a later shared server), JSON-RPC framing, request correlation, cancellation,
   restart policy and bounded queues. Diagnostics are displayed as received; Anchor
   does not reconstruct or reinterpret compiler verdicts.
4. **Command service** — explicit allowlisted Capstan operations, argument vectors
   rather than shell strings, fixed working directory, bounded output/time and
   visible command provenance. No project-defined build hooks in MVP.
5. **Shroud presentation** — pure view construction from application state and
   message-driven updates. Keep UI independent of process, filesystem and LSP code.
6. **Evidence model** — read-only presentation of machine-readable assurance records
   and their provenance/freshness. The compiler's diagnostics and external assurance
   evidence are different data classes and must never be conflated.

Suggested dependency direction:

```
Host adapter (later) ── input / pixels / accessibility
                         │
Anchor application ── model / commands / workspace policy
       │                 │
       ├── document service
       ├── compiler process adapter ── capstan CLI
       ├── language service adapter ── capstan lsp
       └── evidence reader ── assurance records
                         │
                    Shroud S0 views
```

The first implementation keeps host interaction scripted/headless because Shroud S0
has no native embedder. Do not introduce a second GUI toolkit just to conceal that gap.

## 3. User interface and interaction model

The eventual desktop shell has five stable regions:

- **Activity/navigation rail:** workspace, search, source control, build, tests,
  security and documentation.
- **Workspace explorer:** project files and explicitly trusted toolchain/configuration
  metadata. No automatic execution from opening a project.
- **Editor group:** tabs, source editing, diagnostics, navigation and formatting.
- **Bottom panel:** build/test output, compiler diagnostics and task status.
- **Security/evidence inspector:** static enforcement, runtime checks, project
  assurance claims, evidence age, dependency trust and capability requirements.

MVP interaction sequence:

1. Open a directory explicitly; show its canonical path and trust state.
2. List only bounded, regular files within the selected root.
3. Open a `.cap` file as untrusted source text.
4. Start the configured compiler's LSP process without a shell; publish diagnostics.
5. Run check/build/test/format only after an explicit user action.
6. Show the exact command, compiler identity/version, profile, exit status and output.
7. Present security information with provenance and a clear distinction between
   compiler-enforced facts, runtime checks, recorded evidence and unknowns.

The S0 prototype is only a static workbench composition. Navigation entries are
plain labels, not inert buttons; no input host or message loop is connected. It is not
yet an editor, workspace browser or process controller.

## 4. Shroud integration contract

Anchor targets the public S0 surface in `lib/shroud/*.cap`:

- compose `View` values using `column`, `row`, `box`, `text`, `button`,
  `text_field`, `scroll`, `divider` and modifiers;
- build the interface from an application model;
- receive `Msg` values from `Ui.handle(Event)` and update the model outside widgets;
- render via `Ui.render(View, monotonic_time_ms)`, present `Ui.pixmap` through a
  future host adapter, and expose `a11y_tree` / `a11y_problems`;
- pass all user-entered text as `Tainted`; validate before it becomes trusted data;
- give stable `key()` identities to dynamic controls and use `guarded()` for
  security-sensitive actions.

**Clock and confirmation boundary (after Shroud PR #54):** guarded-action timing is
anchored to the timestamp supplied to `Ui.render()`, not to an activating event's
timestamp. The future host adapter MUST source that render timestamp from a trusted,
monotonic platform clock; Anchor must not substitute wall-clock time, project data or
event timestamps. This closes the specific future-event-timestamp bypass, but does not
authenticate physical input, prove that a frame was presented or establish that a
person saw a control. A `.danger()` style/guard is not an informed-consent confirmation
dialog. Irreversible operations still require an explicit application confirmation
flow that identifies the action and target.

**Merged Shroud integration fixes (24 November 2026):**

The following changes have landed in `main` and are part of the current S0 baseline:
- PR #57: duplicate explicit view-key identity is rejected safely; Anchor must still
  provide unique stable keys and must not rely on duplicate-key state retention.
- PR #58: visual deceptive-character sanitisation is applied to accessibility names
  and non-password text-field values. Anchor must preserve the distinction between
  sanitised presentation and original untrusted source text.
- PR #63: disabled interactive widgets block pointer-through without receiving focus
  or messages. This is a UI interaction invariant, not an application authorization
  boundary.
- PR #65: text-field caret hit testing is linear while preserving malformed UTF-8 and
  secure-field semantics. It does not provide the missing multiline editor.

These PRs are merged. Do not describe them as pending or condition Anchor integration
on their future availability.

The separate S1 native-host contract remains a proposal, not a shipped API:
`docs/SHROUD-HOST.md` describes responsibilities and security properties but its
`HostWindow`, `FrameLease` and `HostEvent` names are conceptual. Anchor must not
implement against those names or introduce a private host API. The prerequisites and
missing S0 transitions are recorded in that contract.

S0 constraints are explicit: string action names and int/Tainted payloads; no generic
`View<M>`; no native window, clipboard, IME, multi-line editor, tabs, split panes,
virtualized tree or image widget. Anchor must not fork or patch Shroud internals to
work around these limitations.

Coordination contract: Shroud changes that alter public view, message, event, font,
pixmap or accessibility APIs require a handoff and a versioned integration note before
Anchor depends on them. Anchor-only adapters belong outside `lib/shroud/`.

## 5. Compiler and LSP integration

### Diagnostics

Use the compiler's LSP `textDocument/publishDiagnostics` messages as the authoritative
diagnostic stream. Preserve URI, document version, source, severity, code, range,
message and `codeDescription.href`. Stale diagnostics for an older buffer version
must not overwrite newer diagnostics. CWE links are references to weakness definitions,
not proof that the IDE has independently validated a security property.

### Commands

The MVP supports only the existing wrapper commands: check, build, test, fmt and LSP.
Resolve the compiler executable from an explicitly configured toolchain path or the
bundled installation; do not search PATH and silently choose an arbitrary compiler.
Capture and display its version and executable identity.

Use a process API with an argument vector, never a shell command string. A future
Capstan `run()` capability API is not a substitute for host-side process isolation.

**A1 runtime prerequisite:** inspection of the current `runtime/capstan_rt.h` found no
child-process creation, wait, cancellation or process-group API. Therefore the LSP and
command supervisors cannot yet be implemented against the current public runtime
surface. They require an agreed Capstan-native, capability-scoped process API or a
Shroud/platform host contract. Anchor MUST NOT fill this gap with `system()`,
`popen()`, shell interpolation or a private C shim.

### Navigation and editing

The current LSP does not advertise go-to-definition, references, rename, completion,
hover, semantic tokens or formatting requests. Until those are implemented and
specified, Anchor may provide local file navigation and explicit formatter invocation,
but must not claim language-aware refactoring or semantic highlighting.

A first editor can use plain text and compiler diagnostics. Syntax colouring can begin
with a small lexer-backed presentation only after a stable token API is agreed with
the compiler contributor; a regex highlighter must not be marketed as compiler-accurate.

## 6. Security architecture

Threats include malicious workspace metadata, path traversal and symlink races,
hostile source and import graphs, resource exhaustion, compromised dependencies,
build-script execution, terminal injection, environment leakage, credential disclosure,
and malicious plugins.

MVP policy:

- **No implicit trust:** opening a folder does not run code, scripts, tasks, plugins,
  formatters or dependency installers.
- **No shell:** launch only fixed executable paths with structured argv; never
  interpolate workspace data into shell syntax.
- **No project hooks:** ignore build scripts and task definitions until a separately
  reviewed, capability-scoped execution design exists.
- **Bounded parsing:** cap workspace file count, individual file size, total indexed
  bytes, directory depth, LSP frame size, diagnostics, process output and execution
  time. Handle malformed UTF-8 and malformed project metadata without crashing.
- **Filesystem confinement:** canonicalize the root; reject absolute and parent paths;
  account for symlinks and time-of-check/time-of-use races. A string-prefix path check
  is not confinement.
- **Environment hygiene:** pass a minimal explicit environment; do not copy secrets
  from the user's shell into compiler/build child processes by default. Never log
  environment values, credentials or source contents to telemetry.
- **Terminal safety:** output is data, not executable markup. Escape control and
  bidirectional characters; no automatic link execution or command substitution.
- **Plugin boundary:** no in-process arbitrary plugin code in MVP. Future extensions
  require a separate process, narrow RPC, explicit permissions and resource limits.
- **Dependency trust:** display provenance only when backed by verified signatures,
  attestations and lock data. No package install or update until package-manager
  interfaces and trust policy exist.
- **Secrets:** detect likely credential material in UI output and redact by default;
  never display password-field values. Avoid persistence of tokens in project settings.
- **Workspace state:** project metadata is declarative data with a versioned schema,
  strict size limits and no executable expressions.

## 7. Security properties and evidence presentation

Every displayed item carries a status and source:

| Class | Meaning | Display rule |
|---|---|---|
| Static compiler rejection | Compiler rejects a source construction | Cite the exact diagnostic and compiler version; do not generalise beyond its scope |
| Runtime guard | Generated/runtime check may stop execution | Identify the checked condition and applicable runtime/toolchain |
| Assurance claim | A project-level claim in the assurance register | Show scope, owner, revision and status from the record |
| Evidence | Test, review, CI result, attestation or report | Show artifact identity, commit, timestamp and verification result |
| Dependency trust | Package provenance, signature, advisory status | Unknown unless a verified package record supports it |
| Capability requirement | Authority needed for an operation | Unknown/not available until capability interfaces exist |

Freshness is a comparison, not a green badge: evidence is current only if its recorded
source revision and covered inputs match the inspected project/toolchain state and the
verification procedure succeeds. Missing provenance, changed inputs, expired evidence
or an unavailable verifier means stale or unknown, never proven.

Do not infer that a project is secure because it has no diagnostics. A clean compiler
run proves only that this compiler version accepted this source under these flags.

## 8. Minimal viable IDE milestones

**A0 — Contract and headless shell (this PR):**
- architecture and threat model;
- Shroud S0 workbench example;
- build instructions and known limitations;
- no compiler, runtime or Shroud internals changed.

**A1 — Host and process foundations (split into independent gates):**

- **A1-P — Process service:** capability-scoped compiler/LSP child supervision and explicit CLI operations. See [ANCHOR-PROCESS-SUPERVISION.md](ANCHOR-PROCESS-SUPERVISION.md).
- **A1-H — Shroud native host:** native window, Wayland protocol, input, frame presentation and lifecycle, following [SHROUD-HOST.md](SHROUD-HOST.md) and [SHROUD-LINUX-WAYLAND-PREREQUISITES.md](proposals/SHROUD-LINUX-WAYLAND-PREREQUISITES.md).
- **A1-I — Anchor integration:** connect the independently gated host and process services. See [ANCHOR-A1-WORKSTREAMS.md](ANCHOR-A1-WORKSTREAMS.md).

The split is intentional: Shroud's Wayland host does not need to spawn a compositor/helper process, and Anchor's process supervisor can be tested headlessly. Neither track may bypass the reviewed Capstan capability-I/O and platform contracts.

**A2 — Workspace and editing:**
- confined project tree, tabs, single-line input only where appropriate;
- real multi-line editor contract and syntax token API agreed with compiler team;
- save/reload, dirty buffers and external-change handling.

**A3 — Development workflow:**
- compiler diagnostics, check/build/test/format;
- local symbol/file navigation where supported;
- reproducible build record and toolchain identity.

**A4 — Visual development and live preview:**
- Shroud component palette, hierarchy/tree, design canvas and properties inspector;
- responsive and theme previews, accessibility inspection and interactive preview;
- source-aware, bidirectional transformations between a constrained visual subset and
  Capstan source; source remains authoritative and round-trip edits preserve unrelated
  comments, formatting and code;
- no separate proprietary visual document as a competing source of truth.

**A5 — Security assurance and trusted component catalogue:**
- assurance-register reader, evidence provenance/freshness and static/runtime property
  catalogue;
- curated, versioned catalogue of reusable Capstan components, including authentication
  and authorisation building blocks;
- component assurance records, dependency closure, signatures, reproducible build
  identity, security review, tests/fuzzing and vulnerability/advisory status;
- project-level verification of selected component versions and configurations;
- no “secure” or “verified” label without scoped, current, independently checkable evidence.

**Later — Advanced development workflow:**
Debugging, semantic refactoring, package management, isolated extensions, documentation
browser, semantic tokens and advanced code navigation require stable underlying APIs.

## 9. Acceptance criteria for A0

- Anchor builds against the current Shroud S0 public surface without Shroud/compiler/
  runtime source modifications.
- The example renders deterministically in light and dark themes.
- Accessibility tree generation succeeds and the Shroud accessibility checker reports
  no problems for the prototype.
- The docs clearly label absent interfaces and planned work.
- No assurance claim is shown as proven without verifiable evidence.


## 10. WYSIWYG Shroud designer

The visual designer is a first-class Anchor workflow, not a separate application or a
replacement for Capstan source. It is built entirely in Capstan and rendered by Shroud.
The initial design surface is intentionally limited to a declarative subset of Shroud
views whose structure and properties can be represented and edited without executing
arbitrary project code.

The designer should provide:
- a searchable component palette;
- a hierarchical component tree with selection, reordering and nesting;
- a canvas with selection outlines, resize/layout handles and interactive preview;
- a properties inspector for layout, typography, colour, state and accessibility;
- viewport and breakpoint previews, light/dark themes and reusable design tokens;
- accessibility checks and visual regression/diff support;
- selection-to-source mapping in both directions.

**Source authority and round-trip safety:** Capstan source remains authoritative.
Visual edits must be expressed as source-aware transformations over compiler-recognised
syntax, not by serialising an unrelated visual model over the user's file. Code edits
must refresh the visual projection. A selection in either view must map to the same
component/source range. Transformations must preserve comments, formatting and
unrelated expressions; if a transformation cannot be made safely, the designer must
refuse the edit and explain why rather than silently rewriting or dropping code.

This requires a compiler-supported parse/source-map/transformation contract and Shroud
component metadata. Neither exists as a complete current interface; A4 is therefore a
design target, not a claim about current functionality. The designer must never execute
untrusted project code merely to draw the canvas. Preview execution, if later required,
must use a separate constrained process with explicit capabilities and resource limits.

## 11. Curated security-reviewed component catalogue

See [ANCHOR-COMPONENT-CATALOGUE.md](ANCHOR-COMPONENT-CATALOGUE.md) for the proposed record model, verification procedure, offline/revocation semantics, capability policy, authentication review profiles and acceptance gates.


Anchor should make secure implementation the easiest path by offering prebuilt,
reusable Capstan components for security-sensitive tasks. Initial candidate families
include authentication (passkeys/WebAuthn, OIDC/OAuth client integration, MFA, session
lifecycle and password verification), authorisation (role/attribute-based policy
building blocks), secure credential and secret handling, cryptographic protocols,
input/serialization validation, secure network clients and audit logging.

The catalogue is not an untrusted plugin marketplace. Components are reviewed and
published through a controlled release process, with source available and pinned,
versioned dependencies. The package manager, signature verification and capability
interfaces are prerequisites; none should be implied to exist in the current baseline.

Each catalogue entry must carry a machine-readable assurance record containing at least:
- exact component version, source revision, package identity and transitive dependency
  closure;
- maintainer and reviewer identities, review date, review scope and threat model;
- supported protocols/algorithms and explicit configuration assumptions;
- test, conformance, fuzz, static-analysis and (where applicable) formal-verification
  results, each tied to exact source and tool versions;
- SBOM, reproducible-build result, signed release and provenance/attestation references;
- known limitations, security advisories, affected-version ranges and remediation status;
- capability requirements, data-handling behaviour and upgrade/compatibility notes.

**Assurance is scoped, not absolute.** Avoid a binary “secure” badge. Distinguish at
least: unreviewed; reviewed; tests passing; provenance verified; independently
audited; formally verified for a stated property. A component can satisfy several
dimensions independently. Show the exact claims and evidence, not a single composite
score. Expired, withdrawn, vulnerable, unverifiable or configuration-mismatched
components must be visibly downgraded; absence of known advisories is not proof of
safety.

For authentication, Anchor should favour standard, interoperable protocols and
well-maintained implementations over bespoke cryptography or home-grown protocol
design. The catalogue must distinguish an authentication *mechanism* from an
application's complete identity and access-management policy. Correctness depends on
deployment, relying-party configuration, recovery flows, session handling, rate limits,
origin validation, key storage and operational procedures. Templates should expose
security-relevant choices, provide safe defaults, and explain any residual application
responsibilities.

The developer workflow should allow a component to be inspected, added at an exact
version, locked, updated deliberately and verified offline from cached signed material.
No dependency installation or update occurs merely by opening a workspace. A project's
selected components and assurance records become part of its reproducible build and
security evidence. Anchor must never silently upgrade a security-sensitive dependency.


### Catalogue contract and developer workflow

The catalogue should be split into four independently verifiable artifacts:

1. **Catalogue entry:** human-readable description, ownership, supported Capstan
   versions, API surface, configuration schema and security-relevant defaults.
2. **Immutable package:** exact source revision and content digest, with a complete,
   pinned transitive dependency graph. A mutable tag or branch is never a dependency
   identity.
3. **Assurance bundle:** signed metadata linking review reports, tests, fuzz campaigns,
   formal claims, SBOM, build provenance and advisories to that exact package graph.
4. **Project lock record:** the exact selected package versions, digests, dependency
   closure, required capabilities and assurance-bundle identities used by the build.

A proposed component manifest should declare at least: package identity/version;
public API and compatibility range; source digest; dependency constraints; required
capabilities; data classifications and taint behaviour; secret inputs/outputs and
lifecycle; supported protocols/algorithms; configuration schema and safe defaults;
resource limits; threat model; maintainer/reviewer; and links to machine-readable
assurance and advisory records. The manifest is a declarative, size-bounded data format,
not executable project configuration.

The intended user flow is:

1. Search or browse the curated catalogue and compare supported use cases, assumptions,
   required capabilities and assurance evidence.
2. Inspect source, API, configuration defaults, dependency closure and known limitations.
3. Add one exact version; Anchor writes a lock record and shows every requested capability.
4. Verify package digests, signatures and provenance, then validate assurance evidence
   against the selected source and dependency graph.
5. Compile and test the project; record the compiler/toolchain identity and the component
   lock/evidence identities in the build record.
6. Review updates as explicit changes. Security advisories may trigger an alert and
   explain affected versions, but must not silently rewrite the lockfile or upgrade code.

The verification display must be multidimensional rather than a single score. At minimum,
show source identity, signature/provenance validity, test status, audit status, formal
properties (with their exact statement and scope), current advisories, configuration
conformance and capability review separately. A successful test campaign is evidence
about tested behaviour, not proof of absence of vulnerabilities. A signature establishes
publisher identity/integrity under a trust policy, not code safety. Formal verification
of one property does not establish that the whole component is secure.

### Initial authentication component families

The first catalogue candidates should be deliberately narrow, protocol-based building
blocks rather than a generic “login” black box:

- **Passkeys/WebAuthn relying-party integration:** challenge generation and validation,
  origin/RP-ID checks, credential lifecycle and counter/backup-state handling where
  applicable.
- **OIDC relying-party client:** issuer and audience validation, nonce/state/PKCE
  handling, redirect URI policy, token validation and key rotation.
- **MFA orchestration:** factor enrolment, step-up policy, recovery and rate limiting,
  with explicit treatment of weaker fallback channels.
- **Password verification:** standard password-hashing schemes and parameters, bounded
  work factors, constant-time verification where required, and secure secret handling.
- **Session lifecycle:** opaque session identifiers, rotation, expiry, revocation,
  CSRF protections and secure cookie policy where applicable.
- **Authorisation policy components:** deny-by-default policy evaluation, explicit
  resource/action/subject inputs, auditable decisions and tests for privilege boundaries.

These components must not hide deployment-critical choices. The application remains
responsible for identity proofing, account recovery policy, tenant isolation, authorization
rules, operational monitoring and incident response unless a component's reviewed
contract explicitly covers them. No catalogue entry should encourage bespoke cryptography
or custom protocol implementations.

**Current readiness warning:** the repository's existing crypto standard-library API
has a separate security review in progress (draft PR #56) that identified concrete
input-bound, resource-exhaustion and secret-lifecycle concerns. Those APIs and any
components depending on them must remain unverified until the review is resolved and
the exact implementation passes its required tests and independent checks. This is an
example of why catalogue status must be evidence-driven rather than aspirational.
