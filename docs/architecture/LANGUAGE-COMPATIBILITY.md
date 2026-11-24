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
| `int` | Signed 64-bit, checked ordinary arithmetic | Supported | Align remainder exceptional pair; prove arithmetic |
| `bool` | Distinct boolean type | Supported | Preserve type separation |
| Local variables and parameters | Initialised declarations; function parameters | Supported in register model | Define source-to-register lowering |
| Direct functions | Typed arguments and returns | Supported in narrow form | Define full structural validation and frame rules |
| `if`, loops, `break`, `continue` | Structured source control flow | Supported after lowering | Prove control-flow translation |
| `&&`, `||` | C backend emits short-circuit operators | Not yet an explicit CCAM instruction | Lower to branches; test suppressed RHS |
| Unary/binary arithmetic and comparisons | Includes checked arithmetic and bitwise/shift operations | Partial | Specify all operator rules and trap boundaries |
| `wrapping_*` builtins | Explicit modulo-2^64 operations | Excluded | Add distinct wrapping instructions/semantics |
| Structs and methods | Reference types, mutable fields, identity | Excluded | Heap, layout, aliasing and lifetime model |
| Enums and payloads | Tagged variants, exhaustive match | Excluded | Tagged value layout and safe payload access |
| Optionals | `T?`, `none`, explicit unwrap/control flow | Excluded | Option representation and unwrap semantics |
| Lists and maps | Mutable collections; checked indexing; insertion-order maps | Excluded | Aggregate state, bounds, mutation order, hashing/resource semantics |
| Strings and interpolation | Immutable byte sequences; taint-aware concatenation | Excluded | Byte-string value model, allocation, UTF-8 and effects |
| `Tainted`, `Html`, `LogText` | Distinct information-flow/context types | Excluded | Typed information-flow semantics and sink contracts |
| `Secret` | Restricted credential type and secret runtime allocation | Excluded | Non-disclosure, comparison, copies and zeroisation model |
| Policies and `Grant<P>` | Policy checks, role binding, revalidation | Excluded | Grant values, identity binding, lifetime and protected-call transitions |
| IO and process/SQL APIs | Runtime builtins with external effects | Excluded | Capability model, effect system, deterministic failure and resource contracts |
| GC and heap limits | Runtime-managed memory and resource cap | Excluded | Allocation graph, roots, collector and heap-accounting semantics |
| Closures/generics/Result | Planned language extensions | Not in current v0.1 core | Specify before implementation and add proof obligations |
| Concurrency | Planned | Not in current core | Ownership, synchronisation and happens-before model |

## 3. Compatibility decisions recorded

### 3.1 Remainder exceptional pair

The existing runtime defines `INT64_MIN % -1` as zero, while the CCAM v0.1 draft says remainder traps with `integer_overflow`. The normative core proposal preserves the existing source behaviour: `MIN / -1` traps, `MIN % -1` returns zero. The current range analysis has an explicit exclusion for the exceptional pair before selecting the proven C remainder helper; retain and test that precondition. The CCAM arithmetic implementation and tests must be updated before it is used as a reference oracle.

### 3.2 Compound assignment order

The source reference promises left-to-right evaluation. The code generator's indexed compound-assignment path nests the old-value read and RHS inside a generated C call expression, where argument evaluation order is unspecified. This requires an executable reproducer and a lowering fix. The C backend is not allowed to redefine the source rule.

### 3.3 `read_line()` bound

The runtime caps a line at 1 MiB; the current reference row documents byte preservation and EOF but omits the bound and over-limit outcome. Treat the limit as a compatibility fact requiring explicit documentation and boundary tests, not as a new CCAM feature.

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
