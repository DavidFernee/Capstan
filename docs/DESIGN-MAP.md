# Capstan design map

> **Architecture revision — 2026-11-25**
>
> This map is the repository's top-level architecture index and decision record. It
> distinguishes the integrated implementation from active proposals and target-state
> requirements. Subsystem specifications remain authoritative for their detailed
> contracts; this map records how they fit together and the gates between them.
>
> **Status vocabulary**
>
> - **Integrated** — present on the default branch and covered by the repository's tests.
> - **Validated** — integrated and supported by the stated test/conformance evidence.
> - **Formally verified** — the exact stated property is established by a machine-checked
>   theorem whose assumptions and implementation correspondence are disclosed.
> - **In progress** — implementation or documentation exists on a working branch or in
>   an incomplete mainline workstream; this is not a release claim.
> - **Specified** — a reviewed or proposed contract exists; implementation is not implied.
> - **Target** — an architectural objective with acceptance gates still outstanding.
>
> A pull request, proof fragment, prototype, benchmark, design note or successful
> self-hosting fixpoint is not by itself evidence that a capability is integrated,
> complete, secure or formally verified. All status statements are relative to the
> named branch and revision date. When in doubt, the default branch and exact-head CI
> determine the integrated state.
>
> ## Architecture decisions and current status
>
> ### System decomposition
>
> Capstan is a family of cooperating components with deliberately separate trust and
> semantic responsibilities:
>
> 1. **Language and compiler** — source syntax, name/type checking, security diagnostics,
>    source tooling and lowering. The compiler is the authority for language acceptance;
>    clients must not reimplement its rules.
> 2. **CCAM** — the canonical typed core representation and reference abstract machine
>    for the C-free execution programme. Its normative specification defines values,
>    evaluation order, checked arithmetic, traps, control flow and deterministic resource
>    accounting. A derived optimisation IR is permitted only with a validator and a
>    refinement path back to CCAM.
> 3. **CCAM validator and evaluator** — accept only bounded, structurally valid programs;
>    execute the specified abstract machine with explicit step and call-depth limits.
>    Decoder, schema, aggregate-allocation and validation-order guarantees are part of
>    the contract, not incidental implementation details.
> 4. **Native backends and platform adapters** — consume validated CCAM, preserve its
>    observable outcomes and resource limits, and isolate target ABI/syscall/vendor
>    interfaces behind narrow, documented boundaries.
> 5. **Runtime and standard library** — allocation, collection, strings, crypto, secrets,
>    grants, I/O and other services. These remain separate assurance targets; a C-free
>    instruction backend does not make the runtime C-free or verified.
> 6. **Bootstrap and build system** — establish how compiler stages are built, compared
>    and trusted. Self-hosting and reproducibility are useful evidence, not proofs of
>    compiler correctness or freedom from a trusting-trust attack.
> 7. **Shroud** — an independently reusable, cross-platform GUI toolkit implemented in
>    Capstan, with platform hosts kept narrow and auditable.
> 8. **Keel** — the proposed Capstan-native 3D rendering, simulation and interactive-world
>    engine. It owns spatial, scene, geometry, asset, rendering and simulation semantics;
>    its K0 architecture is specified in `docs/KEEL.md`. Keel may consume Shroud's stable
>    public host/presentation interfaces, but must remain usable headlessly.
> 9. **Keel Science** — a proposed downstream scientific-computing library for quantities,
>    units, coordinate frames, uncertainty, provenance, digital twins and biomedical/
>    imaging research. It consumes Keel and Capstan contracts; it is not part of the engine
>    core and must not become a dependency of Keel. Its K0 proposal is `docs/KEEL-SCIENCE.md`.
>10. **Anchor** — the Capstan IDE built in Capstan on Shroud. It consumes compiler and
>    language-server services; it is not a second compiler or security-policy engine.
>    Keel Studio may later be a separate Shroud-based application, not an Anchor dependency.
>11. **Assurance and supply chain** — tests, fuzzing, sanitizers, proofs, SBOMs, provenance,
>    signatures, vulnerability response and the explicit trusted-computing-base inventory.
>
> The dependency direction is intentional: compiler semantics and CCAM contracts are
> below execution and tooling; Shroud is below Anchor and may provide Keel host/presentation
> adapters; Keel Science is above Keel and consumes its public spatial/scene contracts;
> Keel does not depend on Keel Science, and neither engine nor science library makes Shroud
> depend on 3D semantics. Anchor consumes compiler services and may host later Keel tooling
> as an application. No cycle is permitted (in particular, the compiler must not depend on
> Anchor, Shroud, Keel or Keel Science).
>
> ### Present execution path versus target
>
> The integrated default-branch compiler path remains the C-generating pipeline:
>
> ```
> Capstan source -> lexer/parser/checker -> C code generation
>               -> host C compiler/linker -> executable
>               -> C runtime / conservative collector / OS interfaces
> ```
>
> The C-free path is a separate, staged programme, not the present production default:
>
> ```
> Capstan source -> checked source subset -> CCAM lowering
>               -> bounded CCAM validation -> CCAM evaluator / reference semantics
>               -> native backend -> target executable
>                                      |
>                                      +-> narrow platform/OS adapter
> ```
>
> The current work demonstrates components and restricted vertical slices; it does not
> yet establish an end-to-end C-free compiler, standard library and runtime on all target
> platforms. In particular, a freestanding Linux x86-64 executable generated from a
> restricted CCAM program is not the same claim as a C-free compiler bootstrap or a
> general-purpose C-free runtime. Keep those claims separate in status reports.
>
> ### Semantic authority and correctness obligations
>
> CCAM is the canonical semantic boundary for the C-free path. Its normative contract
> must settle, version and test at least:
>
> - scalar and aggregate value representation, types and register initialization;
> - left-to-right evaluation and exact error/trap precedence;
> - checked integer operations, signed division/remainder edge cases and branch rules;
> - function signatures, calls, returns, frame construction and failure atomicity;
> - explicit traps and observable effects;
> - step, depth, stack, memory, instruction, function, argument and aggregate input limits;
> - deterministic behaviour when a limit is reached.
>
> The implementation layers have distinct obligations:
>
> - **Source lowering:** preserve source evaluation order, lvalue identity, effects, security
>   qualifiers and trap-before-effect behaviour.
> - **Validation:** reject malformed encodings and invalid typed/control-flow structures
>   before unsafe allocation or execution; bound total work and memory, not just individual
>   arrays. A decoder must specify duplicate-key, unknown-field, integer-range and size
>   handling where a serialized format is used.
> - **Evaluator:** refine the CCAM abstract machine, including call/return, trap ordering
>   and exact shared resource accounting.
> - **Native backend:** preserve values, traps, effects and resource bounds. Architecture
>   tests must execute generated binaries, not merely inspect assembly text.
> - **Runtime/platform adapters:** specify ownership, allocation, GC, I/O, entropy,
>   cryptography, secret lifecycle, process creation and OS error mapping separately.
>
> A proof of a model fragment does not prove the Capstan evaluator, validator, lowerer,
> backend, runtime or hardware. Each correspondence link must be stated and evidenced.
> The C backend remains a useful differential comparator but is not the normative oracle;
> independent CCAM semantics and conformance vectors are.
>
> ### Formal assurance model
>
> Assurance claims must identify both the property and the artefact to which it applies.
> The evidence ladder is:
>
> 1. normative specification and explicit assumptions;
> 2. deterministic examples and positive/negative conformance tests;
> 3. property-based, differential, mutation and adversarial fuzz testing;
> 4. sanitizer, resource-exhaustion and platform execution testing;
> 5. machine-checked theorems over a named formal model;
> 6. a proved or validated correspondence between model and implementation;
> 7. independent review/reproduction of the result.
>
> These are complementary, not interchangeable. A theorem about a mathematical model
> must not be reported as a theorem about implementation code until the refinement link
> is established. Every proof report records toolchain version, exact commit, theorem
> scope, imports/axioms, assumptions, unproved obligations and implementation boundary.
> No admitted theorem, `sorry`, `admit`, custom axiom or hidden trust assumption may be
> presented as a completed proof.
>
> ### C-free engineering sequence
>
> The work is ordered by semantic dependency, not by optimistic release dates:
>
> 1. Stabilise and version the CCAM semantics and resource contract.
> 2. Complete bounded validation and its malformed-input/aggregate-budget tests.
> 3. Complete multi-function execution and call/return invariants.
> 4. Complete source-to-CCAM lowering with evaluation-order and effect-sensitive tests.
> 5. Establish an end-to-end native Linux x86-64 vertical slice, including executable
>    output, traps and bounded stack behaviour.
> 6. Connect evaluator and lowering to formal models with explicit simulation/refinement
>    obligations; prove only properties actually established.
> 7. Define and execute the S0→S1→S2→S3 bootstrap, retaining diverse independent seeds as
>    comparison tools rather than final runtime dependencies.
> 8. Port through separate architecture/OS adapter work to Linux ARM64, macOS and Windows
>    x86-64/ARM64. Do not infer platform support from host-independent CCAM conformance.
> 9. Migrate runtime and standard-library responsibilities incrementally, each behind
>    compatibility tests and a reviewed trust-boundary contract.
> 10. Retire the C path only after the replacement meets conformance, security, bootstrap,
>     portability, performance and assurance acceptance gates.
>
> The order may overlap across isolated workstreams, but no dependent change may silently
> assume an unmerged semantic or validator contract. The C-backed baseline remains
> available as a compatibility and differential oracle until the retirement gate passes.
>
> ### Platform and portability policy
>
> Separate three claims: (a) CCAM semantics are host-independent; (b) a backend/adapter
> exists for a particular ISA/ABI/OS; (c) the complete compiler/runtime/toolchain is
> supported on that platform. Each requires its own evidence. The eventual target matrix
> is Linux, macOS and Windows on x86-64 and ARM64, but it is a target matrix, not a claim
> of current support.
>
> Linux may use a narrow, documented syscall interface. macOS and Windows may require
> vendor system libraries or platform services; "C-free" means no C implementation or
> generated-C dependency in Capstan's own compiler/runtime path, not that vendor OS
> internals are written in Capstan. Treat every OS result as untrusted input. Pin ABI
> contracts and test platform-specific error, path, entropy, memory and process semantics.
>
> ### Bootstrap and diverse compilation
>
> Distinguish self-hosting, fixed-point reproducibility, bootstrapping, diverse double
> compilation and compiler correctness. The current C/Python seed path remains part of
> today's trust inventory. The intended native bootstrap removes those as runtime/build
> dependencies only when a reproducible stage chain has been demonstrated. Retaining an
> independent seed compiler as an audit comparator is compatible with a C-free final
> build, provided it is not a dependency of that final build. A fixpoint alone cannot
> exclude a common-mode or trusting-trust defect.
>
> ### Shroud and Anchor boundary
>
> Shroud is a toolkit product with its own API, platform-host contract, resource budgets,
> text/input/accessibility model, rendering conformance suite and release gates. Anchor
> is one Shroud application and the reference Capstan IDE. Shroud must not absorb compiler
> semantics; Anchor must not duplicate them.
>
> Anchor's trust model is fail-closed and evidence-aware: opening a workspace never runs
> project code; build/test/format actions are explicit and use fixed executables plus
> argument vectors (never shell interpolation); workspace and symlink traversal are
> confined; subprocess output and execution are bounded and cancellable; plugins are
> excluded until separately specified isolation/capability controls exist. Compiler
> diagnostics are authoritative for language errors. The UI must distinguish compile-time
> enforcement, runtime checks, tested claims, formal results, assumptions, and unknown
> evidence. Missing, stale or unverifiable evidence is **unknown**, never a green result.
> Component catalogue entries are pinned, attributable and scoped; "verified secure" is
> never an unqualified or permanent label.
>
> ### Supply-chain and remediation policy
>
> SBOM, provenance, signature and advisory data are evidence inputs, not a guarantee that
> a dependency is benign. Vulnerability reachability claims require reproducible evidence
> and must not be inferred from an incomplete call graph. Offline environments consume
> signed, versioned database snapshots.
>
> Deterministic local quick fixes may be offered, but compiler/toolchain changes, trust-root
> changes, capability increases, dependency changes with security impact and any action
> that executes project code require explicit review/approval under organisation policy.
> Do not make automatic adoption of new compiler/toolchain releases the default. Every
> remediation is attributable, reviewable, test-gated and reversible; AI review remains
> advisory unless a separately governed, reproducible gate is explicitly enabled.
>
> ### Release and architecture acceptance gates
>
> A release claim is made per capability and platform. Before a C-free 1.0 claim, require:
>
> - complete, versioned language and CCAM specifications with conformance vectors;
> - source-lowering, validator, evaluator and backend correctness evidence at declared
>   assurance levels;
> - no generated C, C compiler, libc or C runtime dependency in the claimed build/run path;
> - a documented bootstrap chain and reproducible outputs, with independent comparison;
> - runtime and standard-library inventory with explicit residual trusted base;
> - bounded resource behaviour, adversarial malformed-input tests and secret-lifecycle tests;
> - supported-platform CI and executable tests for each claimed ISA/ABI/OS combination;
> - full security suite, fuzzing, sanitizers, supply-chain attestations and external review
>   appropriate to the release claim;
> - no open critical/high security defect without an explicit, approved disposition.
>
> The language's stable 1.0 release and the C-free toolchain milestone are related but
> distinct decisions. A stable language may retain a compatibility backend; a C-free
> prototype does not by itself justify language stability or a complete assurance claim.
>
> ### Architecture risks requiring continuous tracking
>
> - Semantic drift between source, CCAM, evaluator and native backend.
> - Resource limits enforced locally but not in aggregate, or with different meanings
>   across interpreter and native execution.
> - Proof/model mismatch and unsupported claims based on isolated theorem fragments.
> - Runtime/GC/secret-wiping assumptions outside the current formal model.
> - Platform adapter and ABI differences hidden behind apparently portable source.
> - Bootstrap common-mode failures and compromised build infrastructure.
> - Workspace escape, command injection, stale evidence and dependency compromise in IDEs.
> - Scope coupling between language releases, C-free engineering, Shroud and Anchor.
>
> The remainder of this document retains the detailed language, kernel, security, Shroud
> and Anchor programme specifications. Where older roadmap text conflicts with this
> architecture revision, this revision's status definitions, dependency order and
> acceptance gates take precedence; the detailed subsystem documents govern their
> respective technical contracts.
>
> ---
>
## 1. Purpose

Capstan's goal: **with familiar C/Java syntax, make every common vulnerability class
either impossible to express or a compile error, and say plainly what remains.**

The long-term aim is **Capstan all the way down**: the compiler, standard library and
runtime written in Capstan, compiling to machine code with no C anywhere, every line
subject to Capstan's guarantees, including the runtime. Only the
operating system underneath remains outside Capstan.

## 2. Design principles

1. **Unsafe is unrepresentable.** Prefer removing the dangerous construct (null,
   pointers, shells, format strings, weak crypto) over warning about it.
2. **Errors name the weakness.** Every safety diagnostic carries its CWE number,
   so findings map directly onto security standards, audits and ISM controls.
3. **The compiler is deterministic.** The same source always gives the same verdict.
   AI review is advisory, or a separately recorded and cached gate, never part of type checking.
4. **Escape hatches are explicit, rare and auditable.** `trust("why")` always needs a written
   justification and appears in audit output. There is no unsafe code: nothing, the runtime included, runs unchecked.
5. **Friction only where risk is.** Mandatory tests apply to policies and other
   security-critical code, not to everything.
6. **Agility without code changes.** Security primitives are abstract (`hash`,
   `hash_password`), their outputs are self-describing, and upgrading the language
   version upgrades the algorithms.
7. **Dogfooding.** The compiler is written in Capstan and must pass `--strict`.
8. **Honest claims.** The coverage document states what is not prevented.
9. **Trust as little as possible.** Every line of C, every external tool and every
   escape hatch is a liability to be reduced, and the remainder is documented as the
   trusted base.
10. **Every security check, every release.** No release ships without the full suite,
    the CWE atlas, fuzzing and sanitisers passing on every supported platform.

## 3. Architecture

### 3.1 Current integrated execution path

```
Capstan source (.cap)
        │
        ▼
Lexer / parser / checker ──► diagnostics / CLI / LSP
        │
        ▼
Capstan code generation ──► generated C ──► GCC or Clang ──► native executable
                                      │
                                      └── C runtime and conservative GC
```

This is the architecture integrated on `main` at the time of this map. The compiler is
self-hosting, but stage 0 (Python), the generated C, the C compiler, libc, runtime/GC,
build scripts and host platform remain within the relevant trusted base. The exact
scope is recorded in [THREAT-MODEL.md](assurance/THREAT-MODEL.md).

### 3.2 C-free target architecture — in progress, not yet the default

```
Capstan source ──► source validation / lowering ──► validated CCAM
                                                    │
                               normative semantics / abstract machine
                                                    │
                              Lean model and machine-checked fragments
                                                    │
                         future native code generation and runtime
```

CCAM is being established as the canonical typed core representation. Lean currently
checks selected value, register, arithmetic and finite-machine properties; it does not
prove the Capstan compiler, source lowering, complete runtime, GC or generated native
code correct. The intended future implementation path is C-free, but the target is not
an implemented or verified end-to-end execution pipeline. See the active C-free
architecture and semantics work for the precise scope and dependencies.

## 4. Delivery status and roadmap

This section separates implementation status from proposals. A PR, design document,
workflow or proof fragment is not by itself evidence that a feature has shipped or that
an assurance claim is established.

### Completed and integrated baseline

The v0.1–v0.3 milestones below describe the historical integrated language baseline.
The v0.4 performance work is mixed: range analysis, packed booleans, unboxed optionals,
benchmark CI and empty-page reclamation are present; the remaining items stay explicitly
listed as incomplete. The current compiler still emits C.

### Active programme: C-free architecture and formal assurance

The C-free programme is tracked separately from the versioned feature roadmap. The
normative bootstrap and release contract is in [C-FREE-BOOTSTRAP.md](C-FREE-BOOTSTRAP.md).
It distinguishes self-hosting from genuinely C-free native self-hosting, defines the
S0→S1→S2→S3 bootstrap, and states platform and assurance gates. It is a target contract,
not evidence that the implementation is complete.

**Current CCAM status (main, 2026-11-25):** the v0.1 specification is normative; the
Capstan-native single-frame evaluator (PR #142), typed in-memory single-frame validator
(PR #163), bounded multi-function evaluator (PR #207), and checked scalar source lowering
(PR #210) are integrated. The implementation is explicitly **not yet a conforming CCAM
v0.1 machine**. Whole-program closed-schema decoding, duplicate-key rejection, complete
multi-function validation, shared conformance vectors, evaluator/model refinement and
native correspondence remain open. The freestanding Linux x86-64 backend work is active
in PR #212; it is not a production backend or proof of end-to-end C-free execution.
The detailed contract and limitations in [CCAM.md](architecture/CCAM.md) govern.

The active dependencies are:

- **CCAM semantics and conformance:** preserve the normative specification; close
  discrepancies through versioned decisions and shared positive/negative vectors.
  Do not silently change instruction semantics to accommodate an implementation.
- **Validation and decoding:** complete bounded raw-input decoding, exact integer
  parsing, duplicate-key rejection, closed schemas, whole-program validation and
  aggregate input/allocation budgets before execution.
- **Multi-function execution:** replace transitional side-table call representation
  with the normative named-call model; establish call/return, failure-atomicity and
  shared-budget invariants.
- **Source lowering:** preserve source evaluation order, lvalue identity, effects,
  security qualifiers and trap-before-effect behaviour across the complete supported
  subset.
- **Formal correspondence:** connect named Lean properties to executable evaluator,
  validator, lowering and backend boundaries. A model theorem alone is not an
  implementation theorem.
- **Native execution:** establish executable Linux x86-64 conformance, including traps,
  calls, resource limits and failure behaviour, before expanding the supported subset.
- **Bootstrap/runtime:** keep native execution, C-free compiler bootstrap, runtime and
  standard-library migration as separate milestones with separate trust inventories.

### Unified guarantee model

The research and implementation programmes converge on one compositional model. A
program component has a contract over:

1. **Values and types:** representation, invariants, ownership and valid state transitions.
2. **Effects and authority:** the operations it may perform, capabilities required, and
   how authority is attenuated across calls, modules and host boundaries.
3. **Information flow:** provenance and permitted transformations of tainted and secret data.
4. **Resources:** deterministic fuel, call depth, stack, live/aggregate memory, allocation,
   handles, tasks, messages, I/O and output, with explicit units and exhaustion behaviour.
5. **Logical properties:** preconditions, postconditions, protocol invariants and policy claims.
6. **Evidence:** the specification/version, checks, certificates, tests and refinement evidence
   supporting each claim.

These dimensions must compose across function and module boundaries. Unknown, unbounded,
unanalysed or unsupported behaviour must remain explicit; it must not be silently treated
as safe. Static rejection, runtime enforcement, testing, model proof and implementation
refinement are distinct evidence categories. The first research target is deliberately
small: a bounded CCAM subset with shared deterministic fuel and stack limits, one narrow
capability policy, and an independently checkable evidence artefact.

### Concurrency and resource-safety programme

Concurrency is an active research and design stream, not an integrated language guarantee.
PR #239 specifies a proposed race-free structured-concurrency core; PR #254 is an active
Capstan-native bounded task/channel reference-machine prototype; PR #248 integrates
concurrency into the research programme. The corresponding issues #229 and #249 remain
the implementation/specification work queue. None of these open PRs establishes a shipped
concurrency feature or a formal implementation guarantee.

The first concurrency slice should prefer structured task lifetimes, ownership transfer,
bounded channels, explicit cancellation and deterministic scheduling. It must define
failure propagation, task completion, channel closure, queue limits and aggregate resource
accounting. Race freedom is not deadlock freedom; structured concurrency is not a proof
of progress. Locks, atomics and more general shared-memory concurrency follow only after
the minimal model and its invariants are stable.

### Dependency and integration rule

The dependency order is: architecture and claim inventory → normative CCAM semantics and
resource units → bounded decoder/validator and conformance vectors → multi-function
execution and source lowering → unified contract/evidence model → concurrency and
capability vertical slices → implementation-linked proofs and independent checking →
native execution → bootstrap/runtime migration. Literature reviews, Shroud work and
isolated tests may proceed in parallel. No dependent implementation or proof may assume
an unmerged contract, and shared semantic files have one integration owner.

### Active implementation and remediation work

Runtime allocation/collector safety, compiler evaluation sequencing, and Shroud resource
budgets are separate workstreams. They remain subject to exact-head CI, subsystem-owner
review, independent adversarial testing where security-sensitive, and post-merge
integration tests. Their presence in an open PR is not a completed milestone.

### Proposed and long-term research

The versioned v0.5–v1.0 roadmap below remains a proposal unless a capability is
implemented, tested and integrated. Concurrency is now an active research/design stream
(see the programme above), but the versioned language feature remains proposed until its
semantics, implementation and acceptance evidence are integrated. Kernel work,
generational GC, web, package management, SMT policy proofs and optional backends each
retain separate design and acceptance gates; none is implied by the C-free programme.

Each version must keep the self-hosting fixpoint, the full test suite and the
compiler's own `--strict` check passing, and the repository formatted with `capstan fmt`.

### v0.1 — Self-hosting safe language *(done)*
Structs, optionals, lists, maps, checked integers, taint tracking, secrets,
policies and grants with object binding, mandatory denial tests, agile hashing
(SHA-256 and PBKDF2), 46 vulnerability tests (39 rejected at compile time, 7 stopped at run time), and a compiler that compiles itself.

### v0.2 — Memory management and test suite *(done)*
Mark-sweep garbage collector with interior-pointer support and pointer-free
allocation for strings. Stack overflow guard (CWE-674) and a nesting limit in the
compiler. `#line` mapping from generated C back to Capstan source, for debuggers,
sanitizers and coverage. A commercial-grade test suite: published crypto vectors,
conformance against a second implementation, differential and mutation fuzzing,
sanitizers, GC stress, pathological limits and a benchmark gate (see TESTING.md).

### v0.3 — Everyday language *(done)*
Enums with payloads and exhaustive `match`, `else if` chains, `x++`, string interpolation that
preserves taint (`$"Hello {name}"`), struct methods, `List.pop/insert/remove_at/sort`, `Map.remove`,
`import "module"` with one file per module, packed `List<bool>`, and diagnostics with columns,
source excerpts and "did you mean" suggestions. Also the CWE red-team atlas and 20 gap closures
(`Html`/`LogText`, `sensitive struct`, secret wiping, heap limit, new lints).

`capstan fmt`, the formatter, completes the version. It is written in Capstan (`tools/fmt.cap`),
changes whitespace only and checks its own output token for token before writing. Writing a
source file back is its one `trust()`, so its build shows one AUDIT warning: the first in-tree use
of the escape hatch, and the first entry the v0.10 audit command will list. The repository is
formatted, and the suite enforces it and fuzzes the formatter (see TESTING.md).

Carried forward, because neither blocks everyday use:
- `public`/`private` visibility for module members (v0.5, alongside interfaces)
- parser error recovery *(integrated: the parser resumes at the next statement or declaration and reports up to 50 syntax errors per run; tests/recovery)*

### v0.4 — Performance *(in progress)*
Done:
- packed `List<bool>`, one byte per element
- **range analysis** (`compiler/ranges.cap`): overflow, division and bounds checks are left out
  where the compiler proves they cannot fail (`i += 1` under `i < xs.len()`, `xs[i]` in a loop
  that cannot shrink any list, `n - 1` after `if (n < 2) { return n; }`), and kept everywhere
  else. Facts are only kept for variables that cannot change, so the argument for soundness is
  short (see the file header and CWE-COVERAGE.md). It proves 227 of the compiler's own checks
  unnecessary; `--keep-checks` turns it off for assurance work. The interprocedural analysis
  uses an iterated, widened fixpoint over call sites, including recursion.
- unboxed optionals where an `int?` is unwrapped at once (`if (let v = m.get(k))`, `xs.pop()`)
- benchmark gate in the nightly CI run
- empty-page reclamation: pages left empty by collection are returned to the OS beyond a reserve
  sized for the next allocation threshold, and are reused before new memory is requested

Remaining:
- packed, type-specialised lists for element types other than `bool`, and unboxed `int?` in
  variables and fields
- generational collection (not implemented): the runtime currently performs full mark-sweep
  collections. The proposed design below is a plan, not a description of working collector
  behaviour. In particular, there are no minor collections, generation bits, card table, write
  barriers or `CAPSTAN_GC_VERIFY` mode yet.
  *Proposed design:* for a non-moving collector:
  - *two generations by mark bits:* objects that survive a collection keep their mark ("sticky"
    marks) and are old; a minor collection marks from roots and old objects that may point to
    young ones, and sweeps only young objects. Every few minor collections, or when the old
    generation has grown by half, a full collection runs as today
  - *a write barrier:* every store of a pointer into a heap object (a struct field, list or map
    element, or grant arguments) marks the owning object's card dirty. Generated stores and
    runtime collection operations must both participate. Pointer-free (atomic) and secret pages
    need no barrier
  - *verification:* a test mode runs a full mark after every minor collection and fails if the
    minor collector would free anything reached by the full mark. The complete test suite,
    fuzzers and bootstrap should run in this mode before generational collection is trusted
  - expected effect: most collections mark only allocations since the last full collection, so
    collection time should fall substantially; this remains a hypothesis until measured
- benchmarks within 20% of C (now: alloc is; arrays about 1.3×, calls 1.8×, strings 1.2× since
  `int_to_str` stopped using `snprintf`, which was 38% of its time)

### v0.5 — Abstraction
- user generics with interfaces (`interface Comparable<T>`)
- `public`/`private` visibility for module members
- closures that capture by value (no dangling references)
- error handling: `Result<T, E>` with `?` propagation (no exceptions)

### v0.6 — Safe systems access
- capability-based I/O: `main(Capabilities caps)`. Code can only touch files,
  directories, network hosts and environment variables it was handed
  (addresses CWE-22, CWE-918, and supply-chain blast radius)
- `Path` type with traversal-safe joining
- real `run()` (posix_spawn, never a shell) and SQL drivers with prepared statements
- resource limits: size-bounded input types, mandatory timeouts, linear-time regex (CWE-400)
- secure random API (`random_bytes`, `random_int`)
- authenticated encryption `seal()` / `open()` with algorithm tags; key rotation support

### v0.7 — Concurrency *(proposed; research and reference prototypes active)*
- structured task lifetimes, ownership transfer and bounded channels as the first
  implementable concurrency subset; race freedom, cancellation, failure propagation,
  completion and progress are separate properties with separate evidence gates
- typed locks and more general shared mutable state only after the minimal task/channel
  semantics and invariants are stable
- kernel-oriented forms remain a separate design stream (section 7, K1.2–K1.5)
- `async` I/O follows the capability and resource contracts; no concurrency guarantee
  is implied by the current language/runtime

### v0.8 — Policies, proven
- `assert never ...` policy properties checked by an SMT solver, with counter-examples
- `sensitive struct`: every access is protected by default (closes the CWE-862 "forgot to mark it" gap)
- policy coverage report in CI
- mutation testing for policies: the compiler weakens a rule and checks that a test fails

### v0.9 — Web
- typed HTML templates (`Html` type; XSS becomes a type error)
- web framework with CSRF tokens, secure cookies, session expiry and auth flows built in
- typed decoders for JSON and forms that produce `Tainted` fields

### v0.10 — Interop and packages
- foreign code (existing C libraries) runs isolated, never in-process unchecked: in a separate process or a WebAssembly sandbox, behind a typed, checked interface whose inputs and outputs are `Tainted`
- package manager: signed packages, lockfiles, capability manifests per dependency; the IDE's
  live SBOM, vulnerability checks and default remediation build on these (section 5)
- audit command: lists every `trust()`, isolated foreign component and suppressed warning in a project

### v1.0 — Stable (release proposal; acceptance gates apply)
- language and standard library stability guarantee with a complete normative specification
- mandatory, explicitly scoped assurance case for the checker and runtime; formal results are reported by theorem scope and implementation correspondence, not as an optional marketing label
- backend support is selected and accepted independently; WebAssembly and native targets are not assumed complete merely by being listed here

## 5. Tooling and IDE

### Phase A — Language server (integrated baseline; remaining features tracked below)
An LSP server written in Capstan, reusing the compiler front end:
- parser error recovery is integrated; the server reuses compiler diagnostics. Do not describe this prerequisite as outstanding.
- red and yellow underlines with CWE codes, linking to the CWE description
  (done: `capstan lsp`, `tools/lsp.cap`, gives exactly the compiler's diagnostics)
- hover types (`Tainted`, `Grant<ReadRecord>`), go to definition, find references, rename
- quick fixes: "wrap in `escape_log()`", "unwrap with `if (let ...)`",
  "generate a denial test for this policy"
- format on save through `capstan fmt` (done as a command-line tool)
- works in VS Code, JetBrains, Neovim, Zed and others from day one
  (the server speaks standard LSP over stdio; editor extensions are not packaged yet)

### Phase B — Capstan IDE (with v0.6)
A dedicated IDE built on the same server (for example a VS Code-based distribution):
- **security view**: every policy, which functions it protects, test status, and trust sites
- **taint view**: where untrusted input enters and every validator it passes through
- one-click `--release` build showing exactly what blocks it
- debugger with grant and taint inspection

### Supply chain in the IDE (with Phase B and v0.10 packages)
The IDE keeps every project's software bill of materials live, checks it against every
vulnerability source continuously, and fixes what it finds by default.

**A live SBOM.** The IDE maintains the project's SBOM (CycloneDX and SPDX, as releases already
use) as the code changes, not only at release:
- every dependency, with its version, licence, signature, provenance and declared capabilities
- the toolchain too: the Capstan compiler and runtime, the C compiler and C library while they
  remain in the trusted base (section 6), and the build tools, since these are where a supply-chain
  attack would hide
- the history of every change to it, with the reason (upgrade, remediation, new dependency)
- exported on demand and attached to every build, so what shipped is always known

**Every vulnerability source, checked continuously.** On project open, on every dependency change,
and whenever a source publishes:
- OSV (which gathers the GitHub Advisory Database and the ecosystem databases), the NVD, CISA's
  Known Exploited Vulnerabilities catalogue, EPSS exploitation scores, vendor and distribution
  advisories, and Capstan's own advisories, including any Capstan Challenge findings
- **reachability:** the compiler knows the call graph, so each advisory is marked as reachable or
  not from the project's code; unreachable ones are recorded in the SBOM as VEX "not affected"
  statements with the evidence, rather than raised as noise
- **privacy:** lookups run against a local mirror of the databases, so the project's dependency list
  never leaves the machine. Air-gapped and classified environments import signed database snapshots
  instead (section 9)

**Fixed by default.** When an update, an advisory or a warning has a fix, the IDE applies it
without being asked, unless the user has chosen to see warnings before remediation:
- the setting is per user, per project and per organisation; security-sensitive, dependency, compiler/toolchain, trust-root or capability changes require explicit approval
- **what is remediated:** dependency updates that fix an advisory; new versions of dependencies
  and of the toolchain; compiler warnings that have a deterministic quick fix (wrap in
  `escape_log()`, add `"--"`, unwrap an optional). Capstan Review's AI findings are never applied
  automatically, since they are advice, not proof
- **how:** each remediation is one change set with its reason, the advisory it fixes, and the SBOM
  difference; it is shown in a remediation log and can be undone in one step
- **when it cannot be fixed** (no fixed version yet, or the fix fails the gates below), the finding
  stays as a warning with the advisory, its reachability and the options, and a release build is
  blocked if it is a known exploited vulnerability that is reachable

**Safeguards on automatic updates.** A new version is also how supply-chain attacks arrive (a
compromised maintainer account, a backdoored release such as xz in 2024), so updating automatically
must never mean trusting automatically. An update is applied without asking only if it passes every gate:
1. **signed, with build provenance** that matches the package's declared source repository
2. **no new capabilities:** the package's capability manifest (v0.10) grants nothing it did not
   before, and it adds no `trust()`, foreign code or suppressed warning (the audit command). Any
   increase is always shown to the user first, whatever the setting
3. **a cooling-off period** (default seven days) before a new release is adopted, so the ecosystem
   has time to catch a malicious one; waived only when the update fixes a known exploited,
   reachable vulnerability
4. **the project's own tests pass**, including its CWE checks and policy denial tests, and
   `--release` still builds
5. **a compatible version** by the package's declared compatibility; a breaking upgrade is prepared
   on a branch and shown, never applied silently

**Reported, not hidden.** A summary after each session lists what was updated and why, what was
held back and why, and what the user should look at. Organisations get the same as a report for
their whole portfolio, which also serves as evidence for the ISM's software controls and the SSDF
(see `docs/assurance/ISM-MAPPING.md`).

### Phase C — Capstan Review, powered by Claude
An advisory AI layer on top of the deterministic compiler:
- reviews changed code and underlines questionable logic the type system can't see:
  - policies that contradict documentation (the ML check against requirements)
  - business-logic flaws and suspicious `trust()` justifications
- each finding cites the code and, when relevant, the requirements passage
- **Gate mode (opt-in):** "do not build if Review reports any issue". To keep builds
  reproducible, verdicts are cached against the file contents and recorded with the
  build. The same code always gets the same answer until it changes or you re-run Review.
- Model: Claude through the Anthropic API. The Mythos tier isn't generally available;
  Claude Fable 5.2 is the publicly available model in that tier and needs evaluating for this
  use, since it has extra cybersecurity safeguards. The feature shouldn't carry Anthropic's
  model names as its brand.
- Privacy: code is sent to the API. Offer an organisation-level switch and a clear
  data notice, which matters for government and PROTECTED workloads.

## 6. Trusted base reduction: Capstan all the way down

Today a Capstan program depends on three things that are not Capstan: the runtime
(about 1,500 lines of C), the C standard library, and the C compiler. Code written in
Capstan cannot corrupt memory; code in that foundation can. Each step below moves code
into Capstan, where its bugs become safe stops instead of exploitable corruption, or
removes a dependency altogether.

| Stage | Work | Security gain |
|---|---|---|
| T1 (with v0.5) | **Standard library in Capstan:** validators, escapers, collection helpers (sort, join, search) | Text-processing code inherits Capstan's guarantees |
| T2 (with v0.5) *(done)* | **Bitwise operators and explicitly wrapping arithmetic** (`&`, `\|`, `^`, `~`, `<<`, `>>`, `>>>`, `wrapping_add/sub/mul/shl`, hexadecimal literals); ordinary `+` and `<<` stay overflow-checked, shift counts are checked (CWE-1335), and bitwise operators need parentheses when mixed with others (CWE-783); a shift by a negative amount or by the type's width or more is a compile error when the count is a literal and stops safely otherwise | Prerequisite for writing crypto and parsers safely |
| T3 (with v0.6) *(started)* | **Crypto in Capstan:** SHA-256, HMAC, PBKDF2, then authenticated encryption, checked against the same published vectors. *Progress:* SHA-256, HMAC-SHA256 and PBKDF2-HMAC-SHA256 are written in Capstan (`lib/crypto.cap`) and agree with hashlib, the FIPS 180-4 examples and the runtime's C code (`tests/crypto/`); PBKDF2 at 600,000 iterations runs as fast as the C version. Next: a standard-library mechanism (T1) so `hash()` and `hash_password()` call them, then retire the C | Crypto implementation bugs cannot corrupt memory. A FIPS 140-3 validated-module option remains for certified deployments |
| T4 (with v0.6) | **Formatting and parsing in Capstan:** number to text and back, replacing `sprintf`, `snprintf` and `strtol`; differentially tested against libc on millions of random inputs | Removes the libc functions where memory-corruption bugs have historically clustered |
| T5 (with v0.6) | **Network parsing in Capstan from the start:** addresses, URLs, HTTP, name resolution. Never borrowed from libc | The highest-risk input handling is memory-safe by construction (compare glibc CVE-2015-0235, CVE-2015-7547) |
| T6 (v0.7) | **Thin system-call layer:** the program talks to the kernel through a small audited layer (open, read, write, exit, memory mapping, signals) instead of the C library, as Go does on Linux | libc leaves the trusted base |
| T7 (v0.8) | **Verified low-level Capstan:** the few raw operations the runtime needs (read or write raw memory, convert an address, call the kernel) are allowed only when the compiler proves their preconditions with an automated solver, as SPARK Ada does for run-time errors and Verus does for low-level Rust. Unprovable code does not compile. There is no `unsafe` escape hatch | Capstan's guarantees hold in the runtime too, established by proof instead of run-time checks |
| T8 (v0.9) | **Runtime in verified Capstan:** garbage collector, allocator and safety primitives, every raw operation proved; the C remaining is only the program entry point, until the native backend removes it | No unchecked code in the runtime |
| T9 (v0.9) | **Verified C compilation option:** generated C builds with CompCert (formally verified), for high-assurance users | The C compiler leaves the trusted base (CompCert needs a commercial licence outside research) |
| T10 (independent backend track) | **WebAssembly backend:** direct WebAssembly emission, if selected after a separate ABI/runtime and assurance design | A C-free target for the specified subset; not proof of a C-free compiler or runtime |
| T11 (active C-free engineering track; not a release-date promise) | **Native backend:** incrementally emit target machine code from validated CCAM, beginning with a restricted Linux x86-64 slice; extend to other ISAs/OSes only after per-target gates | C-free execution for the explicitly supported subset; full Capstan all-the-way-down remains a later milestone |
| T12 (after v1.0) | **Full functional verification:** the type and safety checker proved to enforce Capstan's rules, and the runtime proved to meet its specification (not only free of memory errors) | Proof, not just testing, for everything Capstan relies on |

**Target assurance boundary (not a present-state claim).** The long-term design aims to apply Capstan's guarantees to the runtime and standard library as well as ordinary programs. That state has not yet been established for every component. Until each low-level operation has a proved or otherwise explicitly justified contract, the runtime, compiler, generated C, C compiler, linker, OS interfaces and hardware remain in the applicable trusted base. The proof checker, specifications and hardware also remain assumptions even in a highly assured end state.

**Testing the runtime as hard as it is proved.** Proof and testing complement each other:
- **checked build:** in test runs, every raw operation in the runtime is also checked at run time
  against the allocator's own record of which memory exists and who owns it, and the whole suite
  (conformance, CWE atlas, differential and mutation fuzzing, collector stress) runs on that build
- **reference models:** the collector and allocator run side by side with a deliberately simple,
  obviously correct model on millions of random allocation patterns and must agree
- **direct fuzzing** of every runtime entry point
- **CWE atlas for the runtime:** attacks aimed at low-level code, each of which the prover or the
  checked build must catch

**Defence in depth.** Even proved code runs on real hardware with real compilers until the native
backend is complete, so the runtime is also hardened against exploitation: guard pages around heap
regions, randomised heap layout, poisoning of freed memory, and the C compilers' exploit mitigations
(control-flow integrity, stack protectors, position-independent code) while C is still in the build.

At every stage the existing tests (conformance, CWE atlas, differential and mutation
fuzzing, sanitisers, published vectors) must pass unchanged. Each replaced component is
also tested against the one it replaces: Capstan's number formatting must match libc's
byte for byte, its SHA-256 must match the current implementation, and so on.

**The end state: no C.** After stage T11, nothing in Capstan or in a Capstan program is written
in C: not the compiler, the standard library, the runtime, the system-call layer or the program's
start-up code. What remains belongs to the platform, not to Capstan:

| Platform | Capstan and its programs | Still underneath (see section 7 for removing the kernel too) |
|---|---|---|
| Linux | no C at all: programs call the kernel directly through its stable system-call interface | the kernel |
| macOS, Windows | no C in Capstan or its programs | the kernel, plus the vendor's system libraries: both platforms require programs to reach the kernel through them (Go had to make the same change on macOS). Everything those calls return is treated as untrusted input |
| seL4 (formally verified kernel) | no C at all | a kernel with a machine-checked proof of correctness: the highest-assurance target, suited to defence use |

**Bootstrapping without C.** Once the native backend exists, each Capstan release is built by the
previous one. The Python stage 0 and the C route are kept, but not depended on: they are the
independent toolchains that diverse double-compiling compares against, so a tampered compiler
binary would be detected.

**Defending the compiler itself.** Ken Thompson showed that a compiler can be tampered
with to insert flaws that appear nowhere in its source. Capstan uses David A. Wheeler's
diverse double-compiling defence: the compiler must reproduce itself byte for byte when
built with GCC, with Clang, and from the independent Python stage 0. Each new backend
joins that comparison.

## 7. Capstan in the kernel

The operating-system kernel is the last large body of C beneath a Capstan program. The Linux
kernel is about 40 million lines and now fixes close to 2,000 CVEs per release, a large share of
them memory-safety bugs (K0 measures exactly how many). This track measures how much of that Capstan would prevent, then tests the
answer on real kernel code, and finally removes the kernel from the trusted base altogether.

### K0: measure first (can start now, no kernel code)
Take the Linux kernel CVEs from a recent period, classify each by CWE from its fix, and run every
class through the CWE atlas. Publish the result: the share Capstan's rules would have prevented at
compile time, the share stopped safely at run time, the share that are logic errors no language
catches, and the share outside Capstan's current reach. Re-run the study each year as the CVE
stream and Capstan both change. This is also direct evidence for government and defence buyers.
Since the kernel's CVE authority assigns a CVE to almost every fix, many are not exploitable; the
study classifies by weakness rather than counting CVEs, and states its sample and method so the
result can be reproduced.

**Status: first study done (2025 CVEs).** [K0-KERNEL-CVES.md](K0-KERNEL-CVES.md), generated by
`tools/k0/study.py`. All 2,702 kernel CVEs published in 2025 were classified: 2,114 automatically
from their fix descriptions, 588 by reading them. Of the 2,698 whose weakness is known:

| | Today | With K1.1 to K1.9 | With K1.10 proofs |
|---|---|---|---|
| Prevented or proved absent | 60.6% | 79.1% | 98.7% |

Every memory-safety bug in the set (52% of all CVEs) is prevented today. What no design removes is
1.3%: hardware and firmware faults, build configuration errors, and processor speculation flaws
beyond variant 1. Next: independent relabelling of the review and check samples, reading the fix
diffs for the four undeterminable CVEs, and the 2026 re-run.

### K1: kernel-mode prerequisites
Kernel code cannot use a collector that pauses at arbitrary moments or rely on an operating system
beneath it. Before any kernel work, Capstan needs:
- **a freestanding mode:** no operating system, no allocator unless one is provided, explicit stack limits
- **error results that must be handled:** no ignored return codes (already a Capstan direction)

The rest of K1 is designed against the K0 result. Of the 2025 kernel CVEs, 39% are not prevented by
Capstan today: 21% outside its reach, 19% logic errors. Each
item below names the classes it targets and the outcome it is meant to produce; `tools/k0/study.py`
projects the effect on the same CVEs, so the claim can be checked when the feature exists. None of
them adds an `unsafe` escape: where the compiler cannot prove a rule, the code does not compile.

**K1.1 Ownership and linear resources** *(memory leaks, resource and reference-count leaks:
~6% of classified CVEs)*
- Kernel mode replaces the collector with ownership: every allocation has one owner, freed when the
  owner goes out of scope; borrowing is checked so no reference outlives its object. Use-after-free
  and double free stay impossible, as they are under the collector.
- **Linear resources.** A reference count taken, a device enabled, a DMA mapping or an IRQ
  requested is a value of a `linear` type: it must be released exactly once on every path, including
  every error path. `Ref<T> r = get(obj);` with no matching `put(r)` is `error[CWE-772]`; a second
  `put(r)` is `error[CWE-1341]`. The kernel's `goto err_*` unwind ladders become automatic, in reverse
  order of acquisition.
- **Shared ownership** (`Rc<T>`, `Arc<T>`) for objects that really are shared, with weak
  references for back-pointers so cycles do not leak.

**K1.2 Data guarded by its lock** *(data races, improper locking: ~5%)*
- Shared mutable data is declared with the lock that protects it: `Locked<Stats, Spin> stats;`.
  The data can only be reached through the guard that `lock()` returns, and the guard releases the
  lock when it goes out of scope, on every path. Missing locks, missing unlocks and unbalanced
  lock/unlock are compile errors (`CWE-667`).
- Values cross between threads only if their type is safe to share (immutable, atomic, or behind a
  lock); otherwise moving or sharing them is `error[CWE-362]`. This is Rust's `Send`/`Sync`, extended
  to the kernel's own primitives: per-CPU data, sequence locks and atomics with explicit ordering.
- **RCU as a type.** `Rcu<T>` can be read only inside an `rcu_read { }` block, and a reference read
  there cannot escape the block; updates go through `rcu_assign` and objects are freed only after a
  grace period, by the compiler-inserted `call_rcu`. Accessing RCU data outside a read section, the
  most common locking CVE in the 2025 set, does not compile.
- **Shared memory with user space or devices** is a distinct type, `Volatile<T>`: every read is a
  single fetch into a local (the kernel's `READ_ONCE()`), so a value cannot change between its check
  and its use (`CWE-367`).

**K1.3 Execution contexts** *(sleeping in atomic context, interrupt-unsafe locking)*
- Every function has a context, inferred where possible and declared at boundaries: `process`,
  `atomic` (spinlock held, preemption off), `softirq`, `hardirq`, `nmi`. A function that may sleep
  cannot be called in an atomic context, and a lock taken in interrupt context must be taken with
  interrupts disabled everywhere else. Both are compile errors, not lockdep warnings at run time.

**K1.4 Lock ordering** *(deadlocks: ~3.5%)*
- Locks are declared in levels (`lock_order inode_lock < page_lock < stats_lock`); the compiler
  rejects acquiring a lock while holding one of an equal or higher level, which rules out
  self-deadlock (AA) and ABBA cycles. Waiting for work, a completion or a timer counts as acquiring
  the locks that work takes, so `flush_work()` under a lock the work needs is rejected (`CWE-833`).
- Lock orders that depend on run-time data (two objects of the same type) use an ordered
  acquisition primitive (`lock_both(a, b)` by address), and the checked build verifies the remaining
  dynamic orders and stops safely before a cycle completes.

**K1.5 Lifetimes of callbacks** *(teardown races: work, timers and interrupts outliving their
device; the largest source of race-caused use-after-free)*
- **Structured concurrency.** A work item, timer, interrupt handler or kernel thread is registered
  through an owner (`dev.spawn(...)`, `dev.request_irq(...)`), and the owner cannot be destroyed
  until all of them are cancelled and finished: the compiler inserts the cancellation, in order, at
  the end of the owner's lifetime. Module unload with work pending becomes impossible to write.
- **Typestate for drivers.** A device moves through declared states (`probed`, `open`, `suspended`,
  `removed`); operations exist only in the states that allow them, so using a device after
  `remove()` or before probe completes is a type error (`CWE-841`, `CWE-672`).

**K1.6 Hardware and memory reinterpretation** *(type confusion, shifts)*
- **Typed views.** Device memory, network packets and on-disk structures are reached through
  `view<T>(bytes)`, which the compiler allows only when `T` is plain data and the size and
  alignment are proved; the result of a view of untrusted bytes is `Tainted`. `container_of` becomes
  a checked downcast. This replaces casts without reintroducing type confusion (`CWE-843`).
- **Checked shifts** *(done, T2)*: a shift by a negative amount or by at least the type's width is a
  compile error when the count is a literal and stops safely otherwise, as overflow does;
  `wrapping_shl` is explicit (`CWE-1335`). K0 now counts the 2025 shift CVE as stopped safely.

**K1.7 Entry points declare their authorisation** *(missing permission checks)*
- Every system call, ioctl, netlink handler and sysfs or procfs write is an entry point, and an entry
  point must name its policy (`protected(CapNetAdmin)`, `protected(OwnerOf)`) or be explicitly
  `public`. A privileged operation reached from an entry point without a grant does not compile.
  This closes the atlas's CWE-862 and CWE-306 gaps for kernel code, where entry points are known.

**K1.8 Speculation hardening** *(speculative execution)*
Spectre-class attacks exploit the processor running ahead of a check. A language cannot fix the
processor, but it can make every known software mitigation automatic, and it can make the most
damaging leak, of secrets, impossible to write:
- **Variant 1 (bounds-check bypass).** Capstan knows which indices are `Tainted`. An access with an
  index derived from untrusted input is compiled with the bounds check *and* index masking (the
  kernel's `array_index_nospec()`); loads whose address depends on such a value use speculative load
  hardening. Code with no tainted indices pays nothing.
- **Speculatively constant-time secrets.** A `Secret` value may not decide a branch, a memory
  address, a loop bound or a variable-time instruction (division, some multiplications), and this is
  checked on speculative paths too, as in the Jasmin language. A secret cannot leak through the cache
  or through timing, whatever the processor speculates. This also enforces constant-time comparison
  (`CWE-208`), which Capstan already requires through `secret_eq()`.
- **Variant 2, branch history and return stack (BHI, Retbleed).** The compiler emits the countermeasure
  each target processor needs (retpolines, return thunks, branch-history clearing at privilege
  boundaries) from a maintained table, so no driver can forget one. Indirect calls are rare by
  construction: where the set of implementations is known, interface calls compile to direct calls,
  and the remaining indirect calls are checked by type-based control-flow integrity.
- **Crossing security domains.** Where K1.10 declares a domain boundary (user to kernel, guest to
  host, tenant to tenant), the compiler emits the processor's barrier (IBPB, buffer clearing) at the
  switch. The K3 microkernel places each service in its own address space, which limits what any
  remaining leak can reach.
- **The limit.** Flaws in the processor beyond these, and future variants, can only be mitigated, by
  the processor vendor's barriers. K0 reports them separately every year.

**K1.9 Narrowing the logic errors** *(hangs and infinite loops, insufficient validation)*
No language decides intent, but two features turn common kernel logic errors into checkable ones:
- **Bounded loops.** In `atomic` and interrupt contexts, and wherever the loop's bound comes from
  untrusted data (a disk image, a packet, a device), a loop must declare its bound
  (`for (...) bounded(MAX_EXTENTS)`) or a decreasing measure the compiler proves; reaching the bound
  returns an error instead of hanging. Most 2025 hangs were loops over corrupt on-disk or device data.
- **Declared formats and refinement types.** On-disk and wire structures are described once
  (`format Ext4Extent { u16 len in 1..32768; u32 start; ... }`), and the compiler generates the
  parser: a value of the type exists only if every declared constraint held. Integer ranges
  (`int{0..MAX_PORTS}`) travel with the value. What remains a logic error is a wrong constraint,
  not a forgotten one.

**K1.10 Proof against a specification** *(the logic errors K1.1 to K1.9 leave: ~20% of 2025 CVEs)*
A logic error is code that does exactly what it says, where what it says is wrong. No rule about how
code is written can catch it; only a statement of what the code is *for* can. K1.10 lets that statement
be written in Capstan, next to the code, and has the compiler prove the code meets it, as seL4 did for
an entire kernel. The proof replaces "we tested it" with "it cannot do otherwise".
- **Contracts.** Functions declare what they require and guarantee (`requires`, `ensures`); types
  and modules declare invariants that hold whenever they are visible; loops carry invariants and a
  decreasing measure. Specification-only (ghost) code and state describe abstract models without
  costing anything at run time. The automated solver already planned for T7 proves them; a module
  marked `proved` does not compile until every obligation is discharged.
- **Invariants owned by locks.** Each `Locked<T>` (K1.2) may state the invariant its data satisfies
  whenever the lock is free. The compiler proves every critical section restores it, which turns the
  ordering races K1.2 cannot see (check under one lock, act under another) into proof failures. This
  is the separation-logic method of VeriFast and Iris, built into the type system.
- **Protocols.** Wire protocols, driver lifecycles and multi-step operations are declared as state
  machines with guarded transitions; the code is proved to follow them, and the protocol itself is
  model-checked for deadlock and for the properties it declares (`assert never two owners`).
- **Termination.** In kernel mode every function either terminates, proved by its measures, or is
  declared `diverges` (an event loop). Waiting on hardware takes a `Deadline`, so a device that never
  answers produces an error, not a hang.
- **Validation from the standard.** K1.9's declared formats carry their constraints from the published
  standard (the USB descriptor, the 802.11 element, the ext4 on-disk layout), written once in a shared,
  reviewed library rather than re-derived in each driver. A parser is proved to accept exactly the
  values the format allows.
- **Isolation as non-interference.** Security domains (namespaces, tenants, guests, user and kernel)
  are labels on types. The compiler proves no information flows from one domain to another except
  through a declared, audited channel, so a namespace leak or a missing permission check becomes a
  type error. This covers the 2025 cases of state leaking across network namespaces and of
  permission checks applied to the wrong identity.
- **Refinement for the core.** For the kernel's core (entry points, scheduler, memory manager,
  message passing) an abstract specification is written first and the code is proved to refine it:
  every behaviour of the code is a behaviour the specification allows. This is the seL4 standard, and
  the route to K3.
- **Proof levels, reported.** Each module states its level: `checked` (Capstan's rules only),
  `contracts` (entry points and parsers proved), or `refined` (full functional proof). Every build
  reports the level of every module, as it reports every `trust()`, so a reviewer sees exactly which
  code carries which guarantee.
- **The proof checker is small and independent.** The solver must return a certificate that a small,
  separately written checker verifies, so a solver bug cannot admit a false proof. The checker joins
  the trusted base reduced in section 6 and proved in T12.
- **Specifications are tested too.** A proof is only as good as its specification. Specifications are
  reviewed like code, kept small, and mutation-tested: the compiler weakens a specification and a test
  or a dependent proof must fail (as v0.8 does for policies).

**The guarantee, stated precisely.** When K1 is complete, a Capstan module at the `refined` level
cannot contain a memory-safety error, a data race, a deadlock, a resource leak, an injection, a missing
authorisation check, a secret leak through timing or speculation, or a behaviour its specification
forbids. Each of those claims rests on a proof checked by the small independent checker, not on
testing. What remains possible, and is named in every K0 report:
- **an error in the specification itself**: kept small, reviewed and mutation-tested, but not provable;
- **the platform**: processor and firmware flaws, including speculation beyond what K1.8 covers;
- **the trusted base**: the proof checker, the code generator and the hardware model, reduced by
  section 6 and proved by T12;
- **code below `refined`**: protected by Capstan's rules and by K1.1 to K1.9, but not by functional proof.

Against the 2025 kernel CVEs, K0 projects that K1.1 to K1.9 would prevent 79% and K1.10 the logic
errors in specified code, a ceiling of 98.7%. The 1.3% left are hardware faults, build configuration
errors and processor flaws: none of them is a mistake in the source code.

### K2: port real subsystems and count what disappears
Using kernel-mode Capstan, rewrite a small number of the Linux subsystems with the most CVEs, as
loadable modules: for example a network protocol parser, a USB or Bluetooth driver, and a
file-system metadata parser. For each, replay the known CVE reproducers and run the kernel's own
fuzzer (syzkaller) against the C original and the Capstan version side by side, and report which
vulnerabilities no longer exist, which became safe stops, and which remain. The kernel itself is C,
so these modules sit on the platform as any program does; everything the C kernel passes them is
treated as untrusted input. This is the one place a Capstan program calls C in-process, which v0.10
otherwise forbids for foreign code: here the C is the platform, not a library. The calls go through
a generated, typed binding layer (as Rust for Linux does) whose declarations are a documented
trusted assumption, listed by the audit command, and every result crosses it as `Tainted` input.

### K3: a Capstan microkernel
Rather than rewriting all of Linux, write a small kernel in Capstan, in the spirit of seL4 (formally
verified) and Redox (written in Rust): isolation, scheduling, memory management and message passing
in the kernel; drivers, file systems and network stacks as isolated Capstan services. With its
correctness proved, it completes the stack: Capstan all the way down, kernel included, with nothing
in C. This is a long-term goal after v1.0.

## 8. Security programme

Standing commitments, every release:

- **Full verification on every platform:** `tests/run.sh --full`, including the CWE atlas,
  long fuzzing campaigns, sanitisers and benchmarks, on every supported OS and compiler.
  No release is published otherwise.
- **CWE tracking:** when MITRE publishes a new CWE version or Top 25 list, new code-level
  entries are added to the atlas with an attack attempt and a verdict before the next release.
- **Gap burn-down:** every remaining gap in the atlas has an owner milestone; a release
  may not add a new gap without recording it.
- **Vulnerability reporting:** a published disclosure policy (`SECURITY.md`), private
  reporting, advisories for every confirmed issue, and a regression test for every fix.
- **Supply chain:** signed releases, SBOMs (CycloneDX or SPDX), SLSA build provenance,
  reproducible builds (already verified by the self-hosting fixpoint), and minimal
  dependencies.
  *Progress (0.4.0):* in place in `release.yml`: keyless Sigstore signatures for every
  file, CycloneDX and SPDX SBOMs validated against their schemas, SLSA provenance through
  GitHub artifact attestations, per-platform reproducibility reports whose checksums must
  agree and which the source archive must rebuild to, and `scripts/verify-release.sh` for
  users; every action pinned by commit, least-privilege jobs. Not yet: an independent
  rebuild outside GitHub, and SLSA Build Level 3 (an isolated, non-forgeable builder).
- **Dependency watch:** monitor advisories for the C compilers and C library while they
  remain in the trusted base.
- **Independent review:** an external security audit before v1.0, and again whenever
  the trusted base changes substantially.
- **Threat model:** a maintained document stating what Capstan defends against, what it
  assumes, and what is out of scope ([assurance/THREAT-MODEL.md](assurance/THREAT-MODEL.md)).
- **The Capstan Challenge** *(subject to funding for a foundation to administer the language)*: a
  yearly prize for anyone who writes a vulnerability Capstan claims is impossible, in four tiers: a wrong atlas verdict, a broken safe stop, a working exploit, and
  (with K1.10) a broken proof. Draft rules: [CHALLENGE.md](CHALLENGE.md).
  *Stages:* now, findings through `SECURITY.md` are credited in the challenge's hall of fame;
  once a foundation is established and funded to administer Capstan, cash prizes open when the
  pool is held in full, an independent appeals panel is
  named and the rules have had legal review; after K1.10, the proof tier carries the largest
  prize. Each year closes with a public report alongside K0.

## 9. Government and defence use

Capstan's first audience is government and defence software, where vulnerability
classes are costly and assurance must be demonstrated. Work needed for that audience
(the assurance pack so far is in [assurance/](assurance/README.md)):

- **Memory-safe language guidance.** The Five Eyes cyber agencies, including ASD's
  ACSC, recommend that organisations move to memory-safe languages. Capstan should
  publish a short statement mapping its guarantees to that guidance
  ([assurance/MEMORY-SAFETY.md](assurance/MEMORY-SAFETY.md)).
- **Approved cryptography.** Align the defaults behind `hash()`, `hash_password()` and
  the future `seal()` with ASD's approved cryptographic algorithms and NSA's
  CNSA 2.0 suite (for example SHA-384 and AES-256 for higher classifications).
  Algorithm tagging makes that a version change, not a code change.
- **Validated cryptographic modules.** Self-implemented cryptography can't be
  FIPS 140-3 validated without its own certification. Offer a build option that
  routes every primitive through a validated module (for example the OpenSSL 3 FIPS
  provider or AWS-LC FIPS), keeping the built-in implementation for other uses.
- **Secure development evidence.** Map the toolchain and tests to the ISM's software
  development controls and NIST SP 800-218 (SSDF)
  ([assurance/ISM-MAPPING.md](assurance/ISM-MAPPING.md)). Publish SBOMs (CycloneDX or SPDX),
  signed releases and SLSA build provenance. The self-hosting fixpoint already gives
  reproducible compiler builds.
- **Export controls.** Capstan includes cryptographic source code. Before public release,
  confirm the position under Australia's Defence Trade Controls Act and Defence and
  Strategic Goods List (Category 5 Part 2), and under the US EAR for US-based contributors
  and mirrors. Published open-source cryptography often qualifies for exemptions, but
  this needs confirming, ideally with Defence Export Controls.
- **Assurance.** For use in evaluated products or safety-related systems: a compiler
  qualification kit (requirements-based tests traced to the specification), coverage
  reports from the `#line` mapping, and a path to formal verification of the checker's
  core rules (v1.0).
- **Air-gapped operation.** The compiler, runtime and tests need no network access.
  Capstan Review (AI) must stay optional and off by default for classified work.

## 10. Quality bar

- every safety rule has at least one rejecting test, and every runtime check a stopping test
- every diagnostic the checker can emit is triggered by a test; line coverage of the compiler,
  formatter and runtime is measured (`tests/coverage.py`, `docs/COVERAGE.md`) and may not fall
  below the floors in `tests/coverage_floors.txt`
- mutation testing of the compiler (`tests/mutate_compiler.py`): injected compiler bugs must be
  caught by the suite; every surviving mutant becomes a test or is shown to be equivalent
- every conformance program and safety stop behaves identically at `-O0`, `-O2` and `-O3` with
  GCC and Clang
- the range analysis's interval arithmetic is property-tested against exact arithmetic on every
  combination of edge values
- the compiler passes its own `--strict` check
- every source file in the repository is formatted (`capstan fmt --check`)
- the bootstrap fixpoint is verified in CI
- sanitiser runs (ASan/UBSan) of the compiler, formatter and examples in CI, and of a third of
  the differentially fuzzed programs (so undefined behaviour is caught even when output matches)
- differential and mutation fuzzing on every change; long campaigns nightly

## 11. Known risks

| Risk | Mitigation |
|---|---|
| Trusted base bugs (runtime, C library, C compiler) | the trusted base reduction plan (section 6): proof for the runtime, no unchecked code; meanwhile fuzzing, sanitisers and diverse double-compiling |
| Proofs rest on specifications that could be wrong | specifications are reviewed, kept small, and tested: the checked build and reference models test the same properties the proofs establish |
| Rewritten components less battle-tested than the originals | write them in Capstan so their bugs cannot corrupt memory; differential testing against the component replaced |
| Heuristic checks (CWE-798 names) give false confidence | label them Partial; prefer type-based rules over name heuristics |
| Friction drives developers to `trust()` | quick fixes and good validators; audit reports make overuse visible |
| AI review non-determinism | advisory by default; cached and recorded verdicts in gate mode |
| Scope | ship each version usable on its own; never break self-hosting |
| Kernel work outgrows the project | measure first (K0); port only a few high-CVE subsystems (K2); a microkernel rather than a Linux rewrite (K3) |

## 12. Shroud: cross-platform GUI

Shroud is the GUI library: one Capstan codebase for Windows, macOS and Linux, and later iOS,
Android and the web. Its aim is to equal or better WinUI 3, SwiftUI, Qt and Flutter. Like Flutter,
it draws every pixel itself and asks each operating system only for a window, input and an
accessibility bridge. Fonts, text, layout, drawing and input are therefore Capstan code with
Capstan's guarantees, and rendering is integer-only, so a frame is identical on every platform.
Text typed by a user arrives as `Tainted`, deceptive characters in untrusted text are shown
rather than obeyed (CWE-451), dangerous buttons are guarded against clickjacking (CWE-1021), and
accessibility and WCAG contrast are checked by the library and its tests.

The full design, the comparison with WinUI 3, SwiftUI, Qt and Flutter, and the roadmap are in
[SHROUD.md](SHROUD.md). Stages, with the language versions they need:

| Stage | Work | Needs |
|---|---|---|
| S0 *(done)* | rasteriser, TrueType parser, text, layout, 16 widgets, input and focus, accessibility tree and checks, themes, headless driver, golden-frame tests (`lib/shroud/`) | v0.4 |
| S1 | platform embedders: Wayland first (a wire protocol, so pure Capstan), then Windows and macOS through one audited module each; damage tracking, multiple windows, clipboard | v0.6 capability I/O, T6 |
| S2 | OpenType shaping, bidi, line breaking, CFF and variable fonts, colour emoji, input methods, multi-line and rich-text editing | T1 |
| S3 | GPU backend checked against the software rasteriser, image decoders in Capstan, effects, animation | v0.6 |
| S4 | widget breadth: virtualised lists, tables, trees, menus, dialogs, pickers, navigation | |
| S5 | typed messages (`View<M>`), closures, async effects | v0.5, v0.7 |
| S6 | live preview in the IDE, inspector, hot reload, visual designer | IDE Phase B |
| S7 | WCAG 2.2 AA, EN 301 549 and Section 508 conformance; localisation; protective markings, capture-proof secret windows, `SecureField` yielding `Secret` | v0.8 |
| S8 | iOS, Android, and the web through the WebAssembly backend | T10 |

## 13. Anchor: Capstan IDE

Anchor is the integrated development environment built on Shroud and the existing Capstan
compiler tooling. It is a client of the compiler and language server, not a second
implementation of language semantics or a source of security verdicts. Its architecture,
threat model, Shroud integration contract and milestones are in [ANCHOR.md](ANCHOR.md).

| Milestone | Work | Needs |
|---|---|---|
| A0 *(prototype)* | Architecture, threat model, Shroud S0 workbench composition, honest status/evidence model | Shroud S0, current CLI and LSP |
| A1 | Integrate Shroud-owned native host/embedder; supervised LSP and compiler process adapters, bounded output and cancellation | Versioned Shroud S1 host contract; Capstan-native capability-scoped process API (not present in current runtime) |
| A2 | Confined workspace model, multi-line editor, compiler-backed token/highlighting contract, save/reload | Shroud S2; compiler token API agreement |
| A3 | Diagnostics, explicit check/build/test/format commands, reproducible build identity and local navigation | Existing compiler CLI/LSP; future LSP navigation requests |
| A4 | WYSIWYG Shroud designer, live preview, component tree/properties inspector, source-aware bidirectional editing | Shroud visual designer APIs; compiler parse/source-map/transformation contract |
| A5 | Assurance evidence inspector and curated security-reviewed component catalogue (authentication, authorisation, crypto, secrets, validation, secure networking) | Package manager, signatures, SBOM/provenance, assurance records and verifiers; v0.6 capability interfaces |
| Later | Debugger, semantic refactoring, isolated extensions, documentation browser, advanced code navigation | Stable underlying compiler/runtime/package/debug APIs |

The visual designer is built in Capstan using Shroud. Capstan source remains authoritative;
visual edits must use source-aware transformations and preserve unrelated comments,
formatting and code. No current compiler API is assumed to provide this yet.

The component catalogue is curated, not an arbitrary plugin marketplace. Its proposed
record model, assurance dimensions, offline/revocation semantics, capability policy and
acceptance gates are specified in [ANCHOR-COMPONENT-CATALOGUE.md](ANCHOR-COMPONENT-CATALOGUE.md).
Every entry is version-pinned and accompanied by scoped evidence. Authentication components
should use established protocols and safe defaults, not bespoke cryptography. “Verified
secure” is never an unqualified or permanent claim. Automatic remediation must follow the
supply-chain gates in section 5: changes are reviewable, attributable and reversible; no
capability or trust-root increase is applied automatically.

Anchor's security UI must distinguish compiler rejections, runtime checks, assurance
claims, evidence and dependency trust. A clean compile is not a project security proof;
missing, stale or unverifiable evidence is unknown, never green. Workspace opening must
not execute project code. Build commands use explicit executables and argument vectors,
never shell interpolation. Project hooks and in-process plugins are out of scope until
a separately reviewed capability and isolation design exists.


## Keel architecture addendum (2026-11-25)

Keel is the proposed 3D rendering, simulation and interactive-world engine for scene
representation, geometry, visibility, materials, rendering, simulation, physics,
animation, world streaming and asset ingestion. Its main proposal is
[KEEL.md](KEEL.md); detailed resource, numeric, scene and backend contracts are in
[KEEL-ARCHITECTURE.md](KEEL-ARCHITECTURE.md).

Dependency rules:

- Keel may consume Shroud's stable public host, lifecycle, input and presentation
  interfaces; it must remain usable headlessly.
- Shroud must not depend on Keel or import scene, mesh, simulation or renderer semantics.
- Capstan remains the authority for language semantics, compiler acceptance, runtime and
  capability security.
- Anchor may host Keel Studio tooling as an application, but is not a dependency of either
  library.
- Shared abstractions are extracted only after stable contracts and concrete consumers
  justify them.

K0 remains specification and research preparation. The scene graph, spatial core, CPU
reference renderer and asset pipeline are future phase deliverables, not integrated
capabilities. GPU drivers, OS graphics services and hardware remain explicit external
trust boundaries.


### Halyard: Capstan's media architecture

10. **Halyard** — Capstan's media architecture, comprising Capstan Media Core, Shanty and Deadeye. **Capstan Media Core** supplies shared, versioned media primitives: bounded byte streams and sinks, explicit ownership, checked size arithmetic, aggregate resource reservations, rational clocks/timebases, timestamps, format registry, structured errors, cancellation and codec-worker contracts.
11. **Shanty** — independent audio engine for ingest, decode/encode, playback/capture, mixing, resampling, synthesis, spatialisation and processing.
12. **Deadeye** — independent video/image engine for ingest, demux/decode, encode, frame scheduling, presentation, composition, colour management, effects and streaming.

The governing architecture map is [docs/media/HALYARD.md](media/HALYARD.md); detailed component design, design charter, format catalogue and mandatory security policy are maintained alongside it.

Core is below both engines and must not depend on either. Shanty and Deadeye share Core contracts but retain domain-specific schedulers and APIs. Shroud core remains media-independent; an optional, separately versioned Halyard–Shroud adapter consumes media presentation surfaces/events together with Shroud rendering/input APIs. Neither media engine depends on Shroud. Keel consumes media APIs when orchestrating graphs and does not duplicate codec semantics. Anchor remains a Shroud application.

The architecture, threat model, format taxonomy and stage gates are specified in [media/ARCHITECTURE.md](media/ARCHITECTURE.md) and [media/FORMAT-CATALOGUE.md](media/FORMAT-CATALOGUE.md). At this revision these are specifications and targets, not evidence of implemented codecs, playback, recording, platform adapters or formal verification. The initial vertical slices are deliberately modest: bounded WAV/PCM offline processing for Shanty, and a bounded still-image/frame pipeline for Deadeye. Shroud's PNG output path must not be mistaken for a general image decoder.

Media security is an assurance workstream in its own right: aggregate resource accounting, checked offsets/dimensions/strides/timebases, bounded queues, capability-minimal codec workers, output revalidation, adversarial corpora, fuzzing and explicit model-to-implementation proof boundaries. The current C runtime remains in the trusted computing base; Capstan source alone does not make media code end-to-end memory-safe.

| Gate | Scope | Exit evidence |
|---|---|---|
| MC0 | Architecture, threat model, format and licence policy | Reviewed contracts, dependency graph, resource ledger and research hypotheses |
| MC1 | Core streams, ownership, clocks and budgets | Conformance vectors, overflow and atomic-reservation tests, adversarial cases |
| SH0 | WAV/PCM offline slice | Differential sample vectors, malformed RIFF corpus, deterministic output |
| DE0 | Image/frame slice | Selected decoder, bounded dimensions/strides, pixel oracle and malformed corpus |
| MC2 | Codec worker boundary | Capability-minimal protocol, quotas, crash/timeout tests and output validation |
| SH1/DE1 | Device playback and presentation | Platform adapter and callback/clock evidence |
| MC3 | Synchronised media graph | A/V clock, VFR, drift, seek, discontinuity and backpressure tests |
| MC4–MC6 | Compatibility, assurance, performance and scientific media | Exact feature matrix, reproducible benchmarks, fuzz/proof evidence and specialist corpus |

The ambition is broad practical historical and modern format compatibility, not an unqualified promise to support undocumented, proprietary, encrypted or DRM-restricted formats. Container, codec, profile, operation direction and assurance status are reported separately.


Media security assurance is mandatory for Shanty, Deadeye and Media Core. The vulnerability accounting, root-cause taxonomy, safe reproducer protocol, SBOM/advisory reconciliation and release-blocking gates are specified in [media/SECURITY-ASSURANCE.md](media/SECURITY-ASSURANCE.md) and tracked in [#292](https://github.com/DavidFernee/Capstan/issues/292). No media release may treat a clean scanner or absence of assigned CVEs as evidence that the attack surface is safe.

## Bosun's Locker database programme

Bosun's Locker is the Capstan-native transactional database and storage engine. Its
architecture and research programme are specified in
[`docs/database/BOSUNS-LOCKER-ARCHITECTURE.md`](database/BOSUNS-LOCKER-ARCHITECTURE.md),
with the candidate transaction-history contract in
[`docs/database/TRANSACTION-HISTORY-SEMANTICS.md`](database/TRANSACTION-HISTORY-SEMANTICS.md).
The initial target is single-node strict serializability and durable commit. The selected
concurrency-control algorithm and physical index/storage layout remain open pending
formal analysis and reproducible benchmarks. These documents are proposals, not claims
of an implemented or verified database.
