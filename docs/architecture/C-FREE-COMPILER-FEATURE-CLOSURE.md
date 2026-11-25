# C-Free Compiler: Heap and Aggregate Feature Closure

**Status:** engineering proposal; not normative CCAM semantics  
**Baseline inspected:** `main` at `d635940c209d28b569f4776b3e443ab9632bf7f1` (2026-11-25)  
**Architecture authority:** `docs/DESIGN-MAP.md`, `docs/C-FREE-BOOTSTRAP.md`, `docs/architecture/CCAM.md`  
**Research coordination:** issues #219–#227; especially resource analysis #221, capability/effect analysis #222 and compositional guarantee calculus #227  
**Related implementation:** merged #163, #207, #210; native backend #212 and CLI #213 are under review

## 1. Decision this proposal is intended to enable

The current scalar CCAM path is a valid first native-code experiment, but it cannot compile Capstan's compiler. The compiler is not a scalar program. It uses records, generic lists and maps, mutable aggregate state, strings, source buffers, token/AST collections, type graphs, flow summaries, and file/process interfaces.

The next C-free compiler milestone is therefore **not another arithmetic opcode**. It is a bounded, typed aggregate-memory profile that can express the data structures used by the compiler, with a native implementation and an explicit proof boundary.

This proposal explores a process-lifetime region/arena as the first memory profile for the compiler executable. It is intentionally narrower than a general-purpose managed heap:

- objects are allocated monotonically and live until process termination;
- there is no individual free and no garbage collector in this profile;
- every allocation is charged to explicit byte and object budgets;
- object references are abstract handles, never exposed native pointers;
- records and arrays carry immutable runtime layout/type descriptors;
- all field/index operations are checked and typed;
- strings are immutable byte sequences whose source-level semantics remain defined by the language specification;
- output and host IO remain explicit effects, not hidden heap operations.

A one-shot compiler process is a good first client: its AST, token, type, and flow-analysis objects all become unreachable together when compilation exits. This is not a proposal to remove or replace the existing v0.6 collector for ordinary long-running programs.

## 2. Why the compiler cannot self-compile today

At the inspected revision, the C-free path has:

- a Capstan-native single-frame evaluator and bounded typed in-memory validator (#142, #163);
- bounded multi-function calls and frames (#207);
- checked scalar source-to-CCAM lowering (#210);
- a freestanding Linux x86-64 backend proposal (#212);
- an experimental native CLI proposal (#213).

The normative CCAM v0.1 value domain is only `Int64 | Bool`. It explicitly excludes strings, heap objects, collections, GC, taint, secrets, grants, IO and concurrency. The native backend consumes this scalar machine and cannot represent the compiler's own state.

The following source inventory is an implementation dependency map, not a claim that these features are already supported by CCAM:

| Compiler component | Observed source-level dependencies | Consequence for C-free compilation |
|---|---|---|
| `compiler/ast.cap` | `Type`, `Node`, `Diag`, `Ctx` records; `List<T>`; strings and string operations | Record allocation/field access, mutable arrays/lists, immutable string representation |
| `compiler/lexer.cap` | `Token`, `Lexer`; token and keyword lists; string scanning/slicing; nested `Map<List<int>>` state | Records, arrays, maps or a library implementation over arrays, byte/string operations |
| `compiler/parser.cap` | Recursive-descent parser state; token and AST lists; mutable node construction | Record mutation, list growth/indexing, bounded recursion/stack |
| `compiler/checker.cap` | `Checker`, `Flow`, `FlowSummary`; many `Map<T>` and `List<T>`; strings; taint/secret/grant/policy type distinctions | Typed aggregate graph, map/list library, string operations, security metadata preservation |
| `compiler/ranges.cap` | Interval and snapshot records; maps of facts and lists of interval vectors | Nested aggregate values, copy/update semantics and deterministic iteration |
| `compiler/codegen.cap` | Generator records; large mutable string/list builders; AST/type/map traversals | Aggregate operations plus a replacement for C-emitting code generation |
| `compiler/main.cap` | Argument list, source-file loading, import queue, maps, diagnostics and output-file writing | Process arguments and explicit bounded filesystem IO |

A complete compiler build also needs a Capstan-native replacement for `compiler/codegen.cap`: the C generator must become a CCAM/native-code producer. Reaching a point where the current C generator is itself compiled natively would still leave a generated-C dependency and would not satisfy the bootstrap contract.

## 3. Proposed abstract memory model

This is a candidate extension profile, not a modification to CCAM v0.1.

### 3.1 Values and references

Extend the abstract value domain with an opaque object handle:

`Value ::= Int64(n) | Bool(b) | Ref(objectId)`

`objectId` is a non-zero abstract identifier allocated by the machine. It is not a byte offset, native pointer, file descriptor, or user-forgeable integer. A reference register has a statically declared reference type; the referenced object's descriptor is checked by every operation that consumes it.

The program carries a closed, immutable type/layout table. A descriptor identifies one of:

- a record layout: ordered field types and mutability flags;
- a homogeneous array element type;
- an immutable byte/string payload.

Type/layout identifiers are validated before execution. Descriptor identity and field/element types cannot be changed by program instructions.

### 3.2 Heap objects

The abstract heap is a finite partial map from object identifiers to:

- `Record(descriptor, fields, initialisedFields)`;
- `Array(elementType, capacity, length, cells, initialisedCells)`;
- `Bytes(length, immutableBytes)`.

A record field read traps if the field has not been initialised. A field write checks the descriptor, field index, mutability and source value type before atomically changing the field and its initialisation bit.

An array has a fixed capacity and a logical length. Indexing is valid only when the index is non-negative and strictly below the logical length. Writes check the element type and update the cell atomically. A capacity slot beyond logical length is not addressable through ordinary array operations.

The first profile does not expose raw pointer arithmetic, pointer casts, arbitrary loads/stores, or foreign memory. Those are separate future contracts, not implied by the existence of references.

### 3.3 Monotonic region allocation

Each execution has one allocation region. Allocation chooses the next deterministic object identifier and charges the complete object footprint, including descriptor/header and alignment overhead, to the region budget.

The machine has explicit `maxHeapBytes` and `maxHeapObjects` limits. Both are non-negative, validated before execution, and capped by implementation admission ceilings. Before allocation, the evaluator must perform overflow-safe size calculation and check both budgets. If either check fails, execution traps with `heap_limit` and leaves the heap, next identifier, byte count and object count unchanged.

There is no individual free, object reuse or moving collection in this profile. The region is reclaimed as a whole when the process exits. This makes object identity stable and gives a simple initial native representation. It does **not** establish a general memory bound for other runtime profiles or for OS memory outside the region.

The implementation must distinguish:
- the abstract charged heap budget;
- the host virtual-memory reservation/commitment;
- native stack, executable image, read-only constants and OS-owned resources.

A configured abstract heap limit is not a claim that total process RSS is bounded by the same number.

## 4. Candidate instruction families

The first extension should be deliberately small. Exact JSON schemas, operand typing and trap precedence must be frozen only after review.

| Family | Candidate operations | Required semantics |
|---|---|---|
| Allocation | `alloc_record`, `alloc_array`, `alloc_bytes` | Deterministic ID; checked size arithmetic; atomic budget admission; zero/initialisation policy explicit |
| Records | `field_get`, `field_set` | Descriptor and field-index checks; exact field type; mutability; uninitialised-read trap |
| Arrays | `array_len`, `array_get`, `array_set` | Logical-length bounds; element type; initialisation; no unchecked index |
| References | `ref_eq` | Identity equality only; no pointer ordering or conversion to integers |
| Byte/string substrate | `bytes_len`, `byte_get`, bounded slice/copy primitives | Byte offsets and lengths checked; immutable string literals; source-level Unicode semantics remain separately specified |
| Effects | proposed `emit_utf8` from the separate output contract | Exact output trace and output budget; no hidden IO in allocation or string operations |

Lists and maps should initially be Capstan library abstractions over records and arrays, not additional primitive machine objects. A first map implementation may use a bounded linear representation; hashing and resizing are later library/performance decisions. This keeps the semantic machine smaller and allows the language's generic/type system to determine the library interface.

The byte/string substrate must not silently decide whether source-level `string.len()`, indexing or slicing count bytes, Unicode scalar values or grapheme clusters. Those semantics must be taken from and reconciled with `docs/architecture/LANGUAGE-CORE.md` before implementation. The native backend must preserve the specified semantics exactly.

## 5. Runtime and backend obligations

The Linux x86-64 prototype may reserve a bounded region using the documented Linux virtual-memory syscall adapter. The native implementation must use abstract object handles or a validated handle table; it must not treat arbitrary source integers as native pointers.

Required checks include:

1. handle is allocated and belongs to the current machine;
2. descriptor matches the operation;
3. field/index is within the declared layout/logical length;
4. value has the exact required type;
5. byte-size, offset and alignment calculations do not overflow;
6. allocation budgets are checked before mutation;
7. traps occur before any partial object/field/array update;
8. step accounting charges each abstract instruction exactly once.

The native backend's current stack, register-slot and syscall code is target-specific. Heap semantics remain host-independent. A later AArch64, macOS or Windows backend must implement the same abstract object behaviour through its own memory adapter; Linux syscall details must not leak into CCAM.

## 6. Compiler self-hosting profile

The first intended client is the command-line compiler, not the full application runtime.

A compiler process has a natural whole-process lifetime. It may allocate tokens, AST nodes, types, scopes, flow summaries, strings, maps and generated output into one bounded region, then terminate. This avoids requiring tracing GC in the initial C-free compiler executable, while retaining explicit memory accounting and deterministic OOM behaviour.

The implementation must not quietly change the public language's memory semantics. This profile is an execution/runtime choice for the compiler process and a possible first supported CCAM resource mode. Long-running programs, Shroud, the LSP and general applications still require a separately specified reclamation/lifetime model.

The native compiler must eventually provide:
- bounded argument and source-file loading;
- UTF-8 source and diagnostic handling consistent with the language contract;
- record/list/map/string operations sufficient for the actual compiler source tree;
- deterministic diagnostics and output;
- CCAM lowering and validation;
- native code emission for the compiler itself;
- explicit file/process effects through a narrow OS adapter.

## 7. Formal and research obligations

The formal work should extend the existing Lean machine in layers, not leap directly from scalar registers to an unstructured byte heap.

Minimum proof sequence:

1. Define the abstract object/region state and well-formedness invariant.
2. Prove allocation either creates exactly one fresh, correctly typed object within both budgets or traps without changing state.
3. Prove field and array operations preserve heap well-formedness and cannot access outside the declared object/layout.
4. Prove reference values cannot be forged from integers and cannot cross machine instances.
5. Define the observable trace and resource accounting for allocation, mutation and output.
6. Prove the Capstan-native validator accepts only programs satisfying the extended static object/type invariants.
7. Establish evaluator refinement to the Lean transition relation.
8. Establish native backend refinement for the implemented instruction subset.

The current register representation work (#205/#216) is a prerequisite for connecting concrete register values to the formal model; it is not itself a heap-safety or backend theorem. The ECE proposal (#214) and its reconciliation issue (#219) should keep proof-producing compiler obligations distinct from independent certificate-checker obligations.

The research agenda requires semantic guarantees, authority/effects and resource contracts to remain distinct judgments with explicit composition rules unless the state-of-the-art review supports a stronger unification. In particular:
- heap-byte and object-count budgets are resource contracts;
- filesystem and process access are effects/authority;
- type/layout preservation and memory safety are semantic properties;
- certificates and proofs are evidence about those properties.

The proposal must be compared against region/arena systems, ownership/borrowing, resource-aware types and proof-carrying resource bounds. It is an engineering proposal until the surveys establish what, if anything, is novel.

## 8. Dependency-ordered implementation plan

| Increment | Deliverable | Exit criterion |
|---|---|---|
| M0 | Freeze value, object, descriptor and region-budget semantics | Reviewed CCAM extension contract; no v0.1 semantic drift |
| M1 | Lean object/region model and allocation/field/array lemmas | Exact-head Lean build and checker replay; assumptions recorded |
| M2 | Capstan-native validator/evaluator for allocation and aggregate operations | Positive, malformed, aliasing, OOM and exact-boundary tests |
| M3 | Source lowering for records, arrays and references | Differential source/evaluator vectors; unsupported constructs fail closed |
| M4 | Linux x86-64 backend for the same operations | Executed ELF vectors; no C compiler/libc in target build/run |
| M5 | Capstan library `List<T>`, `Map<K,V>` and string substrate | Compiler data structures represented without C runtime calls |
| M6 | Compiler-specific region profile and explicit IO adapter | Compiler driver reads source and emits native output without C/Python |
| M7 | Native compiler source-closure build | All compiler modules compile; unsupported source constructs are zero |
| M8 | S0→S1→S2→S3 bootstrap | Full compiler fixed-point comparison, independent clean rebuild and provenance |

Do not start M6 by treating the current scalar native CLI as a self-hosting compiler. It cannot represent the compiler's records, strings, lists or maps. Do not begin by deleting or weakening the current C backend.

## 9. Decisions deliberately left open

- Whether the first profile uses one process-wide arena or multiple named regions.
- Exact object/descriptor encoding and whether layouts are nominal or structural.
- Whether byte strings and Unicode strings are distinct types at the machine boundary.
- Whether arrays expose fixed capacity plus logical length or immutable fixed-length cells only.
- Whether maps are library code over arrays or need a later primitive.
- The exact relationship between the compiler arena and the existing conservative GC.
- How allocation cost composes with fuel/step costs and call summaries.
- Which parts of the handle table and OS memory adapter belong in the trusted computing base.
- Whether a portable object format or per-target assembly/linker adapters are preferable for the first compiler bootstrap.

These choices require evidence from the compiler source closure, the resource/capability surveys, the formal bridge and the native backend. This document does not change normative CCAM v0.1 or claim an implemented heap, a C-free compiler, or a completed proof.
