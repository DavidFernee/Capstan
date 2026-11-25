# Actual compiler bootstrap feasibility — dependency gap assessment

**Status:** B2 initial feasibility assessment; not an implementation or proof.
**Baseline:** `main` at `189f19dd2a39c169e033691856d675b070fb2864`.
**Work branch:** `research/native-compiler-bootstrap`.
**Related architecture contract:** [NATIVE-BOOTSTRAP-PLAN.md](../../docs/architecture/NATIVE-BOOTSTRAP-PLAN.md).

## Executive assessment

The integrated native CCAM path is a credible scalar execution experiment, but it is not presently capable of compiling the actual Capstan compiler. The gap is structural, not a matter of adding a few opcodes.

The existing lowering/backend profile is essentially signed-64 integer and boolean code with local registers, direct calls, branches, loops, checked arithmetic and traps. The compiler implementation itself is a substantially richer Capstan program: it constructs and traverses recursive AST/type/diagnostic graphs; uses strings, lists, maps and optional values; performs recursive parsing and type checking; maintains nested symbol tables; analyses ranges over collections; reads source files and imports; emits diagnostics; and exposes formatter, CLI and language-server tools. The legacy code generator is specifically a C code generator and calls a large Capstan C runtime API.

**Conclusion:** a C-Free S1 compiler is not feasible using the currently integrated scalar CCAM profile alone. It becomes feasible in principle after a bounded native memory/object model, strings, generic collections, optionals, module loading, and a broader source-to-CCAM lowering/backend have been specified and implemented. The C code generator must be replaced by native code generation, not carried forward as an alternate path.

## 1. Dependency-by-dependency assessment

| Compiler component | Concrete use in current source | Present native support | Minimum S1 requirement | Classification / blocker |
|---|---|---|---|---|
| AST and shared types (`compiler/ast.cap`) | Recursive `Node` and `Type` values; `List<Node>`, `List<Type>`; optional type annotations; source file/string references; diagnostics and context | No heap-backed object graph, string or list lowering | Stable object layouts; bounded arena/heap; recursive references; typed list operations; optional representation; source-span and diagnostic values | Production compiler dependency; blocked by runtime/object model |
| Lexer (`compiler/lexer.cap`) | Tainted source bytes, positions, token strings, token lists, keyword/operator tables, escaped string literals | Scalar values only; no strings or collections | Bounded byte/string view and owned string; token vector; byte indexing/slicing; UTF-8 policy; deterministic source spans and lexical errors | Production compiler dependency; blocked by strings/collections |
| Parser (`compiler/parser.cap`) | Recursive descent; AST construction; lists of tokens/nodes/parameters/fields; nested expressions/statements; error recovery and nesting cap | Direct recursion and scalar calls exist, but no AST allocation/list operations | Bounded parser recursion; append/index/slice for vectors; AST arena with stable references; explicit parser stack budget; bounded recovery/diagnostics | Production compiler dependency; blocked by heap/collections |
| Type checker (`compiler/checker.cap`) | Maps for functions, structs, policies, enums, constants, types, scopes and usage counts; nested scope stacks; AST traversal and semantic checks | No maps, strings or object graph | Deterministic bounded hash map or ordered map; collision and capacity contract; stable keys; typed scopes; all existing language type/safety rules | Production compiler dependency; major blocker |
| Range analysis (`compiler/ranges.cap`) | Interval values; maps of variable facts; lists of call-site parameter ranges; fixed-point iterations with a round bound; collection-length and alias-sensitive facts | No map/list/heap semantics | Map/list operations plus exact signed interval semantics; preserve conservative fallback when analysis cannot converge; prove optimization soundness independently | Production optimisation pass; can initially disable and retain runtime checks, subject to tests |
| Source-to-CCAM (`verification/ccam_lowering.cap`) | Converts a checked AST into scalar CCAM functions and registers | Exists for restricted int/bool subset | Extend lowering only after each data type and operation has a canonical CCAM representation; preserve evaluation order, traps, taint and checks | Bootstrap research / test-only today |
| CCAM decoding and validation | Current evaluator consumes in-memory Capstan structures; normative external interchange requires strict decoding | In-memory validator exists; external stable JSON boundary is not integrated | Canonical versioned format; strict decoder; duplicate-key rejection; exact int64 parsing; closed schemas; bounded byte/depth/token/array limits; whole-program validation | Required compiler boundary; PR #315 dependency after Linux CI/interface stabilisation |
| Native backend (`verification/ccam_native_x64.cap`) | Emits a narrow freestanding x86-64 assembly subset | Assembly text emitter exists | Full lowering coverage for compiler-required operations; defined result/trap protocol; ABI and stack proofs/tests; data/object representation; relocations and constants; executable driver | Bootstrap research only; insufficient for compiler source |
| Existing code generator (`compiler/codegen.cap`) | Emits GNU C expressions, declarations, labels, runtime helper calls, C ABI types and C test harness code | C-only by design | Replace with native object/ELF backend over validated CCAM; do not port C text emission into the new pipeline | Production today; must be retired, not adapted as a native stage |
| CLI and import loader (`compiler/main.cap`) | Parses command arguments; resolves relative imports; reads source files; diagnostics; writes output | No filesystem/process capability interface in native CCAM | Explicit filesystem capabilities; path normalization; bounded import graph/count/depth/bytes; atomic output; deterministic CLI and diagnostics | Production compiler dependency; OS boundary required |
| Runtime and standard library | Strings, lists, maps, optional/boxed values, taint/secret values, formatting, IO, crypto, policy/grants, allocation and panic handling | Legacy C runtime and conservative GC | Concrete native allocator/object model; ownership/lifetime; string encoding; list/map semantics; error/exception/trap ABI; stdlib APIs; explicit OS/crypto providers | Production today; largest research and assurance blocker |
| Formatter (`tools/fmt.cap`) | Token-preserving formatting, string/token/list manipulation, source read/write | Source lexer may be reused only after port | Lexer, strings/vectors, bounded file capabilities, token-preserving rewrite and idempotence corpus | Production tool; depends on compiler frontend and IO |
| Language server (`tools/lsp.cap`) | JSON-RPC framing, bounded JSON parser/serializer, document store, incremental text changes, diagnostics, stdin/stdout | No general IO/JSON/string/list/map runtime | Bounded streaming IO, JSON value model/strict decoder and encoder, document map, text edit semantics, cancellation and protocol state machine | Production tool; can be a later stage, but not omitted from a full-toolchain claim |
| Build and bootstrap | `Makefile` uses `bootstrap/capstan0.py`, Python-hosted compiler, generated C, `CC`, `runtime/capstan_rt.h` | Not C-Free | S0/S1/S2 build driver and provenance; direct assembler/linker invocation; production build with Python and C toolchains absent | Current production/bootstrap dependency |
| Tests and release | `tests/run.sh` invokes Python stage-0, C compiler, C runtime, native tests and release scripts | Native tests run within legacy harness | Native test runner; deterministic vectors; independent ELF execution; artifact inspection; SBOM and provenance; CI lane not requiring Python/C for production build | Test-only / release infrastructure remains transitional |

## 2. Required runtime semantics before compiler self-hosting

The compiler source makes heap-backed data structures unavoidable. These semantics must be specified before an implementation is selected.

### 2.1 Object and memory model

Minimum requirements:
- Explicit object kinds and layouts for strings, vectors/lists, maps, AST nodes, type nodes, diagnostics, optionals and compiler contexts.
- A documented pointer/reference representation and nullability model.
- Stable object identity or a proven relocation/handle strategy; AST references must remain valid as collections grow.
- Checked allocation sizes, capacity growth, alignment and integer conversions.
- A hard per-compilation memory budget and deterministic allocation failure.
- Ownership and lifetime rules, including whether values are immutable, uniquely owned, shared or reference-counted.
- No raw pointer exposure through safe Capstan interfaces.
- Failure atomicity: failed vector/map growth must not corrupt the prior value or leak partially initialised objects.
- Defined secret zeroisation if compiler/runtime objects can contain secret values; no claim that ordinary GC guarantees this.

A region/arena allocator is a plausible first compiler-specific strategy because AST and many compiler objects share a compilation lifetime. It is not yet an approved implementation: nested lifetimes, long-lived interned strings, LSP documents, and cross-document reuse require separate treatment. Do not infer that PRs #246/#262/#255 supply this concrete implementation.

### 2.2 Strings and bytes

Specify:
- Whether `string` is UTF-8, arbitrary bytes, or a validated text type; current lexer/runtime operations are byte-oriented in several places.
- Length units (bytes versus Unicode scalar values) for indexing, slicing, columns and protocol offsets.
- Immutable string ownership, concatenation and interning.
- Checked conversion to syscall lengths and host sizes.
- Embedded NUL handling and filesystem path restrictions.
- Bounded builder/formatter APIs and exact failure behavior.

### 2.3 Collections

At minimum, `List<T>` needs bounded construction, length, indexed read/write, append, insert, remove, pop, clear, iteration and deterministic capacity growth. `Map<K,V>` needs bounded construction, lookup, insert/update, removal, key enumeration and a defined iteration-order contract. Generic type representation and runtime type safety must not depend on unchecked casts.

The checker and range analysis use nested maps and lists of maps/lists; this is not just a runtime library convenience. It is a compiler bootstrap prerequisite.

### 2.4 Runtime and platform capabilities

The compiler driver and LSP need file reads/writes, arguments, stdin/stdout, process exit and possibly directory/import resolution. These must be exposed as explicit capabilities with path confinement, byte quotas, short-read/write handling, cancellation and deterministic error mapping. No implicit environment, current-directory, process, network or filesystem authority should leak into safe language code.

The production compiler does not necessarily need the entire application runtime (database, crypto, secret handling, grants/policies, HTML/CSV/JSON escaping) to bootstrap itself. But the final product runtime and full compiler/toolchain cannot be declared complete until each supported language/runtime API has a native implementation or is explicitly outside the supported profile.

## 3. What can be reused and what must be replaced

**Reusable as semantic references or source material (not automatically as production implementation):**
- The lexer, parser, checker and AST source as the language behavior specification and migration starting point.
- Range analysis as an optional optimisation pass; initial S1 can conservatively retain checks and disable range-based check elimination.
- CCAM v0.1 semantics, in-memory evaluator, multi-function validator and scalar lowering as the first execution profile, subject to conformance and refinement evidence.
- Existing tests and negative/security corpus as differential vectors; their current harness remains Python/C dependent.
- Formatter and LSP protocol specifications and tests.

**Must be replaced for C-Free production:**
- `compiler/codegen.cap` C text emission.
- Python bootstrap `bootstrap/capstan0.py` and generated Python compiler stage.
- Generated-C compilation and `CC`/GCC/Clang driver use.
- `runtime/capstan_rt.h` and `runtime/capstan_gc.h` as required runtime components.
- Any production dependence on the conservative collector or libc helper implementation.

**Must not be silently cloned:**
- The CCAM external JSON decoder while PR #315 is unsettled.
- The region heap/ownership implementation while PRs #246/#262/#255 and refinement work remain unresolved.
- The experimental CCAM byte-output work in PR #304.

## 4. Feasible now / blocked / research required

| Work item | Assessment | Reason |
|---|---|---|
| Audit and document scalar CCAM subset | Feasible now | Integrated source and tests are available |
| Existing scalar native vertical slice | Demonstrated by baseline Ubuntu/GCC CI | Ten Capstan-generated programs were assembled, linked and executed directly; stronger ELF inspection remains pending |
| Native scalar executable tests for small process statuses and current trap codes | Demonstrated in baseline CI | Ten native programs pass; current exit-status interface is only an 8-bit projection and does not establish arbitrary int64 results |
| Full signed-64 result and structured trap equivalence | Blocked by backend result protocol | Exit status is only eight bits; trap detail is discarded |
| Strict external CCAM interchange | Blocked by integration | Wait for PR #315 Linux CI and stable interface |
| Compiler AST, lexer and parser on native runtime | Requires new runtime work | Strings, vectors, AST allocation and stable references absent |
| Native checker and range analysis | Requires new runtime work | Generic maps/lists, optionals, recursive object graphs absent |
| Actual compiler native code generation | Requires substantial backend work | Existing emitter covers scalar subset only; C codegen is not reusable |
| Full CLI, formatter and LSP | Requires platform/stdlib work | File IO, args, streaming stdin/out and JSON protocol not present |
| S0 independent seed | Feasible as a separate design/build task | Must implement only a bounded compiler subset and be audited independently |
| S1 self-hosting compiler | Not feasible on current integrated native subset | Runtime and source lowering gaps above |
| S2/S3 | Blocked on S1 | No meaningful self-hosting/reproducibility claim before native compiler exists |

## 5. Proposed implementation and assurance order

1. **Freeze the scalar execution contract.** Resolve full-width result reporting and structured trap reporting; preserve exact instruction-count and call-depth semantics. Keep the existing C compiler path untouched.
2. **Obtain real ELF evidence.** Run the Capstan-native test generator and ELF harness in a Linux x86-64 environment. Test 64-bit boundaries, all trap classes, loops, calls, recursion, step/depth limits, stack guard and malformed machine input. Record exact source/toolchain/artifact hashes.
3. **Stabilise the CCAM external boundary.** Consume PR #315 only after its Linux failures and interface are resolved. Do not invent a second JSON decoder.
4. **Specify native object model and bounded memory.** Select arena/region/reference strategy only after ownership, stable references, growth and failure atomicity have explicit semantics. Link the implementation to the model before claiming refinement.
5. **Implement strings and generic collections.** Test capacity arithmetic, allocation failure atomicity, aliasing, stale references, iteration, collision handling and memory quotas.
6. **Extend CCAM semantics and backend in vertical slices.** First strings/bytes and immutable vectors; then mutable lists/maps and AST objects; then optionals/structs/enums; then taint/secret and policy/grant types as required. Each slice needs a canonical encoding, validator rules, evaluator semantics, lowering and native correspondence. Do not add a feature solely to make a demo compile.
7. **Port the actual compiler frontend.** Compile AST/types, lexer, parser and diagnostics with S1. Keep the source frontend as the language authority; compare all diagnostics and accepted/rejected source against the legacy compiler corpus.
8. **Port checker and compiler analyses.** Add maps/scopes and checker semantics. Initially disable range-based check removal (or retain all runtime checks) until the native analysis is separately validated; later port the bounded range analysis with a soundness argument.
9. **Replace the C code generator.** Generate validated CCAM/native objects directly. The backend must preserve all checked semantics and emit the documented ELF/ABI contract.
10. **Port CLI/import IO, formatter and LSP.** Introduce capability-scoped file and stream APIs; add bounded JSON-RPC and document-store support; test each without C runtime or Python.
11. **Build S0/S1, then S2/S3.** S0 builds the first native compiler; S1 builds itself; S2 diverse-seed and reproducibility evidence follow only after source/CCAM/backend correctness gates pass.

## 6. Required proof and test obligations

Keep these evidence categories separate:

- **Specification:** language, CCAM, object layout, memory, ABI, IO and failure contracts.
- **Conformance:** exact positive/negative vectors and differential comparisons.
- **Implementation refinement:** theorem or independently reviewed correspondence from concrete runtime/backend to formal semantics; tests alone do not qualify.
- **Resource assurance:** checked bounds for memory, stack, source size, compiler work, imports, diagnostics, output and runtime steps.
- **Security assurance:** malformed input, mutation/fuzz, alias/lifetime, OOM/failure-atomicity, capability confinement and binary inspection.
- **Bootstrap assurance:** independent seed audit, diverse bootstrap comparison, independent reproducible builds and production dependency closure.

A successful self-hosting fixpoint, identical output, or passing test suite is useful evidence but does not establish compiler correctness or exclude a trusting-trust attack.

## 7. Scope and coordination

This is an assessment only. It does not modify `compiler/*`, `runtime/*`, existing CCAM modules, `Makefile`, `bin/capstan` or `tests/run.sh`. No unmerged PR implementation is treated as available. Dependencies and coordination requests are reported through issue #370. Any future shared-interface proposal must wait until the integration worker stabilises the relevant mainline files.
