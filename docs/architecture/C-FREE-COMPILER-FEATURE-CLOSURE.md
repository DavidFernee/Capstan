# C-Free Compiler: Heap and Aggregate Feature Closure

**Status:** engineering proposal; not normative CCAM semantics  
**Baseline:** `main` at `d635940c209d28b569f4776b3e443ab9632bf7f1` (2026-11-25)  
**Authority:** `docs/DESIGN-MAP.md`, `docs/C-FREE-BOOTSTRAP.md`, `docs/architecture/CCAM.md`  
**Research coordination:** #219–#227, especially resource analysis #221, capability/effect analysis #222 and compositional calculus #227  
**Implementation dependencies:** #163, #207, #210 merged; native backend #212 and CLI #213 under review

## 1. The next real compiler milestone

The scalar CCAM/native path is a useful first executable slice, but it cannot compile Capstan's compiler. The compiler is not a scalar program: it uses records, generic lists and maps, mutable aggregate state, strings, source buffers, token/AST collections, type graphs, flow summaries and file/process interfaces.

The next C-free compiler milestone is therefore a **bounded, typed aggregate-memory profile** sufficient to represent the compiler's own data structures. Another arithmetic opcode does not move us materially closer to self-hosting.

This proposal investigates a process-lifetime region/arena as the first memory profile for the compiler executable:

- objects are allocated monotonically and live until process termination;
- no individual free or garbage collector is required in this initial compiler profile;
- each allocation is charged to explicit byte and object budgets;
- references are abstract handles, never exposed native pointers;
- records and arrays carry immutable runtime layout/type descriptors;
- all field/index operations are checked and typed;
- strings are immutable byte sequences, with source-level semantics defined separately;
- output and host IO remain explicit effects.

A one-shot compiler process is a suitable first client: its tokens, AST, type and flow objects become unreachable together when compilation exits. This is not a proposal to replace the existing v0.6 collector for ordinary long-running programs.

### 1.1 First aggregate execution bridge

The experimental `verification/ccam_aggregate_machine.cap` now composes the opaque process-lifetime heap with typed integer, boolean and reference registers. It provides Capstan reference transitions for record/array/byte allocation, record field access, array append/read, arena provenance checks and pre-dispatch step limits. Its exact scope and limitations are recorded in [CCAM Aggregate Register/Heap Execution Bridge](CCAM-AGGREGATE-MACHINE-BRIDGE.md).

This is an integration milestone only. It is not yet part of the canonical CCAM instruction schema, multi-frame evaluator, native backend or Lean refinement chain, and it does not yet execute the production lexer/parser through aggregate CCAM. Those remain explicit gates for #458/#481.

## 2. Why the compiler cannot self-compile today

At the inspected revision, the C-free path has a Capstan-native single-frame evaluator and validator (#142/#163), bounded multi-function calls (#207), checked scalar source-to-CCAM lowering (#210), and a freestanding Linux x86-64 backend/CLI under review (#212/#213).

Normative CCAM v0.1 has only `Int64 | Bool` values. It explicitly excludes strings, heap objects, collections, GC, taint, secrets, grants, IO and concurrency. The native backend consumes this scalar machine and cannot represent the compiler's own state.

The following is a compiler-source feature closure, not a claim that these features are supported by CCAM:

| Compiler component | Observed source dependencies | C-free requirement |
|---|---|---|
| `compiler/ast.cap` | `Type`, `Node`, `Diag`, `Ctx` records; `List<T>`; strings | Record allocation/field access, mutable arrays/lists, string representation |
| `compiler/lexer.cap` | `Token`, `Lexer`; token/keyword lists; string scanning/slicing; nested `Map<List<int>>` | Records, arrays, maps or a library over arrays, byte/string operations |
| `compiler/parser.cap` | Recursive-descent parser state; token and AST lists; mutable node construction | Record mutation, list growth/indexing, bounded recursion/stack |
| `compiler/checker.cap` | `Checker`, `Flow`, `FlowSummary`; many `Map<T>`/`List<T>`; taint/secret/grant/policy distinctions | Typed aggregate graph, generic collections, strings and security metadata |
| `compiler/ranges.cap` | Interval/snapshot records; maps of facts and lists of interval vectors | Nested aggregates, copy/update semantics and deterministic iteration |
| `compiler/codegen.cap` | Generator records; mutable string/list builders; AST/type/map traversals | Aggregate operations plus replacement of C-emitting code generation |
| `compiler/main.cap` | Argument list, source loading, import queue, maps, diagnostics and output writes | Process arguments and explicit bounded filesystem IO |

The C generator in `compiler/codegen.cap` must itself be replaced by a Capstan-native CCAM/native-code producer. Compiling the existing C generator to a native executable would still leave generated C in the compiler pipeline and would not meet the bootstrap contract.

## 3. Candidate abstract memory model

This is a separately versioned extension profile, not a modification to CCAM v0.1.

### 3.1 Values and handles

Extend the abstract value domain with opaque object references:

`Value ::= Int64(n) | Bool(b) | Ref(objectId)`

An `objectId` is a non-zero abstract identifier allocated by the machine. It is not a byte offset, native pointer, file descriptor or user-forgeable integer. Reference registers have statically declared reference types; every operation also checks the referenced object's descriptor.

The program carries a closed, immutable layout table. A descriptor identifies a record layout (ordered field types and mutability), a homogeneous array element type, or an immutable byte payload. Layout identifiers are validated before execution and cannot be modified by program instructions.

### 3.2 Heap objects

The abstract heap is a finite partial map from object identifiers to:

- `Record(descriptor, fields, initialisedFields)`;
- `Array(elementType, capacity, length, cells, initialisedCells)`;
- `Bytes(length, immutableBytes)`.

A field read traps if the field is uninitialised. A field write checks descriptor, field index, mutability and exact source type before atomically updating the field and initialisation bit.

An array has fixed capacity and a logical length. An index is valid only when non-negative and strictly below logical length. Reads/writes check element type; writes update atomically. Capacity beyond logical length is not addressable through ordinary array operations.

No raw pointer arithmetic, pointer casts, arbitrary loads/stores or foreign memory access are introduced by this profile.

### 3.3 Monotonic region allocation

Each execution has one allocation region. Allocation chooses the next deterministic object identifier and charges the complete footprint, including header/descriptor and alignment overhead, to the region budget.

The machine has explicit `maxHeapBytes` and `maxHeapObjects` limits. They are validated before execution and capped by implementation admission ceilings. Allocation must perform overflow-safe size calculation and check both budgets before changing state. Failure traps with `heap_limit` and leaves the heap, next identifier and both counters unchanged.

There is no individual free, reuse or moving collection in this profile. The region is reclaimed when the process exits. This makes object identity stable and gives the initial native implementation a simple allocation discipline. It does **not** establish a general memory bound for other runtime profiles or for OS memory outside the region.

Keep separate accounting for abstract charged heap bytes, host virtual-memory reservation/commitment, native stack, executable image, read-only constants and OS-owned resources. A configured heap limit is not a claim that total process RSS is bounded by the same number.

## 4. Candidate instruction families

Exact schemas, operand typing and trap precedence must be frozen only after review.

| Family | Candidate operations | Required semantics |
|---|---|---|
| Allocation | `alloc_record`, `alloc_array`, `alloc_bytes` | Deterministic ID; checked size arithmetic; atomic budget admission; explicit initialisation policy |
| Records | `field_get`, `field_set` | Descriptor/index checks; exact field type; mutability; uninitialised-read trap |
| Arrays | `array_len`, `array_get`, `array_set` | Logical-length bounds; element type; initialisation; no unchecked index |
| References | `ref_eq` | Identity equality only; no pointer ordering or integer conversion |
| Byte substrate | `bytes_len`, `byte_get`, bounded slice/copy | Checked offsets/lengths; immutable string literals; source-level Unicode semantics remain separate |
| Effects | proposed byte-oriented `emit_bytes` output instruction (the earlier `emit_utf8` proposal in #190 needs reconciliation with `docs/SPEC.md`) | Exact exact byte output trace and budget for `print(string)`/`println(string)`; no hidden IO in allocation/string operations |

Lists and maps should initially be Capstan library abstractions over records and arrays, not additional primitive machine objects. A first map may use a bounded linear representation; hashing and resizing can follow as library/performance work. This keeps the semantic machine small and lets the type system define collection interfaces.

The byte substrate must not silently decide whether source-level `string.len()`, indexing or slicing count bytes, Unicode scalar values or grapheme clusters. Reconcile those semantics with `docs/architecture/LANGUAGE-CORE.md` before implementation.

## 5. Runtime and backend obligations

The Linux x86-64 prototype may reserve a bounded region through its documented OS memory adapter. Native code must use abstract object handles or a validated handle table; it must never treat arbitrary source integers as native pointers.

Required checks:

1. handle is allocated and belongs to the current machine;
2. descriptor matches the operation;
3. field/index is within the declared layout/logical length;
4. value has the exact required type;
5. byte-size, offset and alignment calculations cannot overflow;
6. allocation budgets are checked before mutation;
7. traps occur before partial object/field/array updates;
8. each abstract instruction consumes exactly one CCAM step.

Heap semantics are host-independent. AArch64, macOS and Windows backends must implement the same abstract object behaviour through their own adapters; Linux syscall details must not leak into CCAM.

## 6. Compiler-specific memory profile

The first intended client is the command-line compiler, not the full application runtime. A compiler process has a natural whole-process lifetime: tokens, AST nodes, types, scopes, flow summaries, strings, maps and generated output can live in one bounded region and be reclaimed together at exit.

This avoids requiring tracing GC in the first C-free compiler executable while retaining explicit memory accounting and deterministic OOM behaviour. It must not silently change public language memory semantics. The LSP, Shroud and long-running applications still require a separately specified lifetime/reclamation model.

The native compiler must ultimately provide bounded argument/source loading, UTF-8 handling consistent with the language contract, record/list/map/string operations for the actual compiler source tree, deterministic diagnostics, CCAM lowering and validation, native code emission, and explicit file/process effects through a narrow OS adapter.

## 7. Formal and research obligations

Extend the existing Lean machine in layers, not directly from scalar registers to an unstructured byte heap:

1. Define abstract object/region state and its well-formedness invariant.
2. Prove allocation creates exactly one fresh, correctly typed object within both budgets, or traps without state change.
3. Prove field/array operations preserve heap well-formedness and cannot access outside the declared object/layout.
4. Prove references cannot be forged from integers or cross machine instances.
5. Define observable trace and resource accounting for allocation, mutation and output.
6. Prove the Capstan-native validator accepts only programs satisfying extended static object/type invariants.
7. Establish evaluator refinement to the Lean transition relation.
8. Establish native backend refinement for each implemented operation.

The register representation work (#205/#216) is a prerequisite for connecting concrete register values to the formal model; it is not itself a heap-safety or backend theorem. ECE reconciliation (#219) must keep proof-producing compiler obligations distinct from independent certificate-checker obligations.

The research agenda requires semantic guarantees, authority/effects and resource contracts to remain distinct judgments with explicit composition rules unless the literature review supports a stronger unification:
- heap-byte and object-count budgets are resource contracts;
- filesystem/process access are effects and authority;
- type/layout preservation and memory safety are semantic properties;
- certificates and proofs are evidence about those properties.

Compare this proposal against region/arena systems, ownership/borrowing, resource-aware types and proof-carrying resource bounds. This is an engineering proposal until the surveys establish what, if anything, is novel.

## 8. Dependency-ordered implementation plan

| Increment | Deliverable | Exit criterion |
|---|---|---|
| M0 | Freeze value, object, descriptor and region-budget semantics | Reviewed extension contract; no v0.1 semantic drift |
| M1 | Lean object/region model and allocation/field/array lemmas | Exact-head Lean build/checker replay; assumptions recorded |
| M2 | Capstan-native validator/evaluator for allocation and aggregates | Positive, malformed, aliasing, OOM and exact-boundary tests |
| M3 | Source lowering for records, arrays and references | Differential source/evaluator vectors; unsupported constructs fail closed |
| M4 | Linux x86-64 backend for the same operations | Executed ELF vectors; no C compiler/libc in target build/run |
| M5 | Capstan library `List<T>`, `Map<K,V>` and string substrate | Compiler data structures represented without C runtime calls |
| M6 | Compiler region profile and explicit IO adapter | Driver reads source and emits native output without C/Python |
| M7 | Compiler source-closure build | All compiler modules compile; unsupported source constructs are zero |
| M8 | S0→S1→S2→S3 bootstrap | Full compiler fixed-point comparison and independent clean rebuild |

Do not treat the current scalar native CLI as a self-hosting compiler. It cannot represent the compiler's records, strings, lists or maps. Do not begin by deleting or weakening the current C backend.

## 9. Decisions deliberately left open

- One process-wide arena or multiple named regions.
- Exact object/descriptor encoding and nominal versus structural layouts.
- Whether byte strings and Unicode strings are distinct at the machine boundary.
- Fixed-capacity/logical-length arrays versus immutable fixed-length cells.
- Maps as library code over arrays versus a later primitive.
- Relationship between compiler arena and existing conservative GC.
- How allocation cost composes with fuel/step costs and call summaries.
- Which handle-table and OS-memory-adapter components belong in the trusted base.
- Portable object format versus per-target assembler/linker adapters for the first bootstrap.

These choices require evidence from compiler source closure, resource/capability surveys, formal bridge and native backend. This document does not change normative CCAM v0.1 and does not claim an implemented heap, C-free compiler or completed proof.


## 10. Opaque process-arena references (experimental implementation)

The experimental process-lifetime heap now uses two module-private opaque reference types:
- `CCAMHeapIdentity` is a fresh reference-identity object allocated for each arena instance.
- `CCAMHeapRef` contains that identity and an object index; importing modules can neither construct nor inspect the representation.

The heap factory no longer accepts a caller-selected identity token. Allocation returns an authentic `CCAMHeapRef`, and every field, array, byte-string and reference-value operation accepts that opaque value. Resolution uses Capstan's identity-bound grant mechanism to require that the reference's opaque identity is the arena's identity before using the object index. A cross-arena substitution is rejected as CWE-639; it is not converted into an ordinary invalid-index result. Distinct arenas with identical limits and identical first object indices therefore remain disjoint; copying an arena handle preserves its identity because Capstan structs are reference-bound. Scalar heap values use an absent optional reference, so they do not allocate dummy identity objects.

This is still an experimental Capstan-level model, not a connected CCAM evaluator/native implementation or a formal heap theorem. The compiler integration milestone remains tracked separately in #481; the integer-handle flaw is tracked by #480.
