# Capstan Language Compatibility and Semantic Coverage

**Status:** initial mapping; not a conformance claim  
**Baseline:** `docs/SPEC.md` and current compiler/runtime on main at the start of this workstream  
**Purpose:** prevent the initial CCAM subset from being mistaken for the complete Capstan language.

## 1. Coverage rule

The initial CCAM v0.1 value model contains only signed-64 integers and booleans, with typed local registers, direct calls, control flow and traps. It is not yet a complete execution semantics for the existing Capstan language.

A feature being accepted by the existing compiler does not mean it is supported by CCAM. Until its value representation, effects, transition rules, traps, resource limits and conformance tests are specified, it is outside the C-free machine's supported subset.

## 2. Initial core mapping

| Existing source feature | Existing contract / implementation fact | Initial CCAM status | Required semantic work |
|---|---|---|---|
| `int` | Signed 64-bit, checked ordinary arithmetic and unary negation | Supported | Align remainder exceptional pair; lower negation through checked subtraction; prove arithmetic |
| `bool` | Distinct boolean type | Supported | Preserve type separation |
| Local variables and parameters | Initialised declarations; function parameters | Supported in register model | Define source-to-register lowering |
| Direct functions | Typed arguments and returns | Supported in narrow form | Define full structural validation and frame rules |
| `if`, loops, `break`, `continue` | Structured source control flow | Supported after lowering | Prove control-flow translation |
| `&&`, `||` | C backend emits short-circuit operators | Not yet an explicit CCAM instruction | Lower to branches; test suppressed RHS |
| Unary/binary arithmetic and comparisons | Includes checked arithmetic and bitwise/shift operations | Partial | Specify all operator rules and trap boundaries |
| `wrapping_*` builtins | Explicit modulo-2^64 operations | Excluded | Add distinct wrapping instructions/semantics |
| Structs and methods | Reference types, mutable fields, identity | Excluded | Heap, layout, aliasing and lifetime model |

**CCAM register-file qualification:** `verification/ccam_core.cap` currently uses mutable `CCAMRegister` values obtained from a `List<CCAMRegister>`, including local copies followed by field mutation. That implementation therefore depends on reference identity and aliasing behaviour which this table explicitly classifies as excluded from the supported language subset. The register-file regression tests exercise the current implementation, but they do not establish a language-level reference-semantics guarantee. The Lean heap bridge is a proposed semantic model; it remains unconnected to a proved Capstan evaluation rule until struct allocation, field access/update, list storage and aliasing are specified and verified.
| Enums and payloads | Tagged variants, exhaustive match | Excluded | Tagged value layout and safe payload access |
| Optionals | `T?`, `none`, explicit unwrap/control flow | Excluded | Option representation and unwrap semantics |
| Lists and maps | Mutable collections; checked indexing; insertion-order maps | Excluded | Aggregate state, bounds, mutation order, hashing/resource semantics |
| Strings and interpolation | Immutable byte sequences; current C backend lazily materialises each literal through `CAP_LIT`/`malloc` on first use, which may fail; merged PR #109 now sequences that first-use materialisation before later effectful operands | Excluded | Byte-string value model, static-vs-dynamic literal storage, allocation/resource semantics, UTF-8 and effects |
| `Tainted`, `Html`, `LogText` | Distinct information-flow/context types | Excluded | Typed information-flow semantics and sink contracts |
| `Secret` | Restricted credential type and secret runtime allocation | Excluded | Non-disclosure, comparison, copies and zeroisation model |
| Policies and `Grant<P>` | Policy checks, role binding, revalidation | Excluded | Grant values, identity binding, lifetime and protected-call transitions |
| IO and process/SQL APIs | Runtime builtins with external effects | Excluded | Capability model, effect system, deterministic failure and resource contracts |
| GC and heap limits | Runtime-managed memory and resource cap | Excluded | Allocation graph, roots, collector and heap-accounting semantics |
| Closures/generics/Result | Planned language extensions | Not in current v0.1 core | Specify before implementation and add proof obligations |
| Concurrency | Planned | Not in current core | Ownership, synchronisation and happens-before model |

## 3. Compatibility decisions recorded

### 3.1 Remainder exceptional pair

The existing runtime defines `INT64_MIN % -1` as zero, while the original CCAM v0.1 draft said remainder traps with `integer_overflow`. The normative core proposal preserves the existing source behaviour: `MIN / -1` traps, `MIN % -1` returns zero. The current range analysis has an explicit exclusion for the exceptional pair before selecting the proven C remainder helper; retain and test that precondition. PR #124 adds an optimizer-path fixture expecting one proven operation (the unary negation in `-1`) and requiring the remainder itself to remain checked. PR #132 has merged these changes into the #81 foundation branch at `99828f0bbd31455e92c97316f075d49eefefb564`: `CCAM.md`, the Capstan-native `ccam_rem` substrate, sign/boundary tests, closed JSON schemas and typed-register validation. All four exact-head CI jobs passed. PR #81's post-integration CI is queued; the correction is on the foundation branch but not yet on `main`.

### 3.2 Compound assignment order

The source reference promises left-to-right evaluation. The original field and indexed compound-assignment paths nested the old-value read and RHS inside a generated C call expression, where argument evaluation order is unspecified. PR #124 adds `compound_field_receiver_identity.cap` to distinguish field-target object identity from direct indexed-element slot semantics: the field write remains on the retained receiver after the RHS replaces its former list slot. PR #93's initial fixture confirmed a GCC-vs-reference mismatch at `-O0`, `-O2` and `-O3` in CI. PR #97 has merged to `main` as `30958c0b1e069225debbc743b97cab1665ec2562`, explicitly sequencing location evaluation, old-value read, RHS, computation and write for local, field, indexed and text compound assignment; it also retains the invalidated-index runtime regression. PR #102 was closed without merging because its side-effectful field-receiver fixture was invalid under the then-current checker grammar. Draft PR #123 now proposes a narrow checker extension admitting effectful field receivers and tests exactly-once evaluation; indexed targets remain restricted to simple paths. The range analysis uses `seq_ok` / `may_shrink` guards to suppress list-length facts across potentially shrinking regions; this is fail-closed but not a formal proof of classifier completeness.

### 3.3 `read_line()` bound

The runtime caps the payload at 1,048,576 bytes, excluding the terminating newline. Exactly 1 MiB is accepted (including EOF immediately after that payload); the next non-newline byte traps with CWE-789. PR #124 adds the existing bound and over-limit outcome to the `docs/SPEC.md` row. The runtime unit suite tests exactly 1 MiB followed by newline and max-plus-one rejection. PR #124 adds `tests/unit/read_line_eof.py`, which exercises the public native API with exactly 1 MiB followed immediately by EOF; its exact-head CI is queued. Treat the limit as a compatibility fact, not as a new CCAM feature.


## 3.4 Reference identity and mutable objects — proposed formal semantics

The existing source language treats structs as reference types with mutable fields; `docs/SPEC.md` also states that structs and collections are bound by identity in policy grants. That behaviour must be specified independently of CCAM's initial scalar/register subset. The general reference model permits multiple references to the same object: the no-alias condition used by the CCAM register-file bridge is a stronger, constructor-specific invariant, not a global language rule.

The first formal semantics increment defines an object identity as an opaque reference value and a heap as the authoritative mapping from identities to object records. Copying a reference copies its identity; it does not clone the object. Dereferencing an absent identity is invalid. A field mutation is modelled as an update to the heap cell named by the retained reference, leaving every other heap cell unchanged.

Allocation uses a monotonically increasing identity frontier. Its freshness guarantee is conditional on a heap invariant: every identity at or beyond the frontier is unallocated. The allocator theorem establishes preservation of that invariant in the mathematical model; it is not yet evidence about the executable runtime allocator.

The Lean module `CapstanVerification.ReferenceSemantics` currently models these laws using the CCAM register record as a first object payload. It proves identity-preserving reference copies, allocation at the frontier, preservation of other heap cells, the allocation-frontier invariant, write/readback, alias visibility, and generic object modification visible through copied aliases. The model is polymorphic in object payload; CCAM registers are one specialization. This is a proof model, not a proof of compiler or runtime implementation.

**Current implementation facts relevant to that correspondence:** `compiler/codegen.cap` represents a struct type as a typed C pointer (`S_Name*`), lowers `new S{...}` to `cap_alloc(sizeof(S_Name))` followed by field initialisation, and emits struct fields using their corresponding generated C types. `runtime/capstan_rt.h` routes pointer-containing allocations through the collector. `runtime/capstan_gc.h` describes a non-moving conservative mark-sweep collector: it scans the machine stack, callee-saved registers, registered globals and object contents; it reuses freed small-object slots/pages and separately releases large objects. These are implementation facts, not proofs that every live Capstan reference is retained or that allocation/initialisation is failure-atomic.

The formal `ObjectId` is therefore an abstract allocation-incarnation identity, not a raw C address. Physical addresses can be reused after collection. The implementation refinement must show that no still-usable language reference can denote a reclaimed incarnation, and that address reuse cannot make an invalid/stale reference denote a different live object. The GC's conservative roots and object graph are consequently part of the trusted implementation boundary until formally related to the language heap model.

**Generational-handle alternative:** `CapstanVerification.GenerationalHandles` models a handle as a region, slot and allocation generation. Resolution requires the caller's expected region and checks slot generation too, preventing cross-region resolution. This aligns with the region-scoped identity contract in PR #262. The Lean model proves that releasing a slot invalidates its old handle and that reusing the same slot under a different generation cannot resurrect it. This is a candidate for the C-free runtime's explicit-root heap; it is not the current C backend representation. `boundedNextGeneration` now formalises strict generation growth below a configured maximum and refusal at the limit. The concrete slot-table retirement state machine remains unimplemented.

**Abstract collector proof increment:** `CapstanVerification.CollectorSemantics` models reachability from explicit roots through object fields and a sweep operation driven by a Boolean mark set. It proves that a complete marker preserves all reachable objects, root objects, and reachable edge targets; that sweep invents no objects; and that collection preserves the monotone allocation frontier. The marker may conservatively retain unreachable objects. This is the required abstract sweep theorem, conditional on marker completeness—not a proof that the current conservative C collector computes a complete mark set.

The implementation correspondence remains open and must establish, separately:
1. the source type checker and compiler preserve reference identity through assignment, argument passing, return, and collection storage;
2. runtime allocation returns fresh identities and handles exhaustion/failure without publishing a partially initialized object;
3. field reads and writes dereference the same heap object, including through copied aliases;
4. object lifetime, reachability, collection, and stale-reference prevention are defined (including whether generations are required to prevent identity reuse);
5. lowering and backend execution preserve these rules under optimisation and concurrency.

Until these obligations are discharged, reference-containing types remain outside the formally verified C-free subset. The current CCAM register tests are regression evidence only; they do not promote structs or mutable references into the supported CCAM v0.1 feature set.

## 4. Compatibility policy

- Existing observable behaviour is preserved by default when migrating the C-free implementation.
- A defect in the current implementation is not automatically promoted into normative language semantics; it must be classified as either a deviation from an existing specification or an explicit language change.
- An implementation detail that affects observable results, traps, resource exhaustion or side-effect order is not merely an implementation detail.
- Any incompatible change requires a versioned specification decision, migration note and updated conformance tests.
- The C backend may be used as a differential comparator, but disagreement is resolved against the normative source specification plus an explicit compatibility decision—not by assuming the C output is correct.

## 5. Acceptance gate for feature migration

A source feature enters the supported C-free subset only when all of the following exist:
1. normative type/value representation;
2. evaluation and effect-order rules;
3. transition and trap semantics;
4. explicit resource bounds and accounting;
5. Capstan-native evaluator implementation;
6. positive, negative and adversarial conformance tests;
7. proof obligations and evidence status;
8. source lowering and native-backend preservation evidence.

Features should be migrated in dependency order. The scalar core does not confer blanket safety on features that remain outside it.
