# C-Free compiler memory: integration decision

**Status:** integration review and proposed sequencing; not normative CCAM semantics.  
**Baseline:** `main` at `35f7ce57132f235adbb8e60b00a4f27f3a87d9eb` (2026-11-26).  
**Reviewed work:** draft PR #246 (process-lifetime region heap), draft PR #463 (CCAM v0.2 scratch-memory models), issues #451 and #458, and the C-free bootstrap contract.  
**Purpose:** prevent two different memory-lifetime models from being conflated while moving the compiler off the generated-C path.

## 1. Decision

Capstan needs **two distinct bounded memory abstractions**, not one overloaded heap:

1. **Compiler arena:** typed, mutable records and arrays plus immutable byte strings, allocated into a bounded process-lifetime arena. Objects survive function returns and are reclaimed together when the compiler process exits. This is the minimum useful model for tokens, AST nodes, scopes, type graphs, diagnostics and generated output.
2. **Scratch regions:** fixed-capacity byte regions with frame ownership, checked scalar views, generation invalidation and deterministic cleanup on return/trap. These are short-lived workspaces for algorithms and must not be used to store compiler objects that outlive their owner frame.

These profiles have different lifetime and aliasing semantics. They may share low-level checked reservation/accounting primitives only after a common abstract contract is proved. They must not share a single capability type or silently inherit each other's lifetime rules.

Keep normative CCAM v0.1 unchanged. Keep the existing scratch-memory proposal separate from the compiler-arena profile. Do not call either profile a conforming CCAM v0.2 machine until its complete schema, validator, evaluator, native implementation and conformance evidence agree.

## 2. What the current prototypes actually provide

### 2.1 PR #246: process-lifetime object arena

`verification/ccam_heap.cap` is the closer starting point for compiler data structures. It models:
- record layouts with field types, nominal reference target descriptors, mutability and initialisation;
- fixed-capacity arrays with a separate logical length;
- immutable byte-string objects, including embedded NUL;
- monotonically allocated object IDs and heap-instance checks;
- byte, object, work and temporary-peak accounting;
- rejection paths intended to preserve heap state and accounting.

It is explicitly a reference model, not part of the executable CCAM machine, source lowering, native backend or compiler CLI. Its own formal contract identifies two blockers that must remain blockers:

- **Aliasing semantics:** the API mutates `CCAMHeap` fields and nested `List` values. The supported scalar CCAM subset does not establish the struct/reference/collection aliasing semantics this implementation relies on. Either prove the concrete source/runtime semantics and their correspondence, or redesign operations as explicit state-in/state-out transitions over supported values.
- **Reference authenticity (resolved at the Capstan module boundary):** PR #482 replaced caller-selected integer tokens and constructible `(token, id)` pairs with opaque `CCAMHeapIdentity` and `CCAMHeapRef` values. Importers cannot construct or inspect either representation; resolution checks identity before object lookup. This closes the original forgeable-token API defect in the reference model. It does not yet prove that the language/runtime identity primitive is unforgeable under every execution context, nor does it connect references to CCAM registers, a validator, evaluator or native handle table. Those remain integration and formal-correspondence obligations.

Its logical heap charge is not a bound on host allocator overhead, RSS, list capacity, string copies, stack use or total process memory. The work and temporary counters are abstract budgets, not wall-clock or host-allocation proofs.

### 2.2 PR #463: frame-scoped scratch regions

The v0.2 proposal and Capstan prototypes provide a different model:
- fixed-capacity byte storage;
- checked aligned reservations and scalar i64/bool views;
- region identity, generation and owner-frame checks;
- bounded region count and aggregate logical capacity;
- reset/close invalidation and explicit frame-unwind cleanup;
- CFG lifecycle validation that conservatively rejects mismatched ownership states at joins.

This is a scratch-memory profile, not a general object heap. It deliberately excludes records, general references, strings, collections and capability-passing across calls. Its logical capacity limit is not an RSS bound.

There is useful executable integration in the prototype call machine: `CCAMCallMachine` carries a memory manager and frame IDs; the return path unwinds the returning frame's regions, and the trap path unwinds active frames from inner to outer. That is a real integration seam worth retaining. It is still prototype code: it does not establish normative v0.2 conformance, production native behaviour or a proof of implementation refinement.

### 2.3 Why these are not interchangeable

| Property | Compiler arena (#246) | Scratch regions (#463) |
|---|---|---|
| Lifetime | Whole compiler process | Creating call frame |
| Contents | Typed records, arrays, immutable bytes | Fixed byte storage and scalar views |
| Mutation | Typed field/element updates | Bounded byte/scalar stores |
| Reference model | Opaque arena identity plus opaque object references; importers cannot construct or inspect them; resolver checks arena identity | Region/view identity plus generation and owner frame (prototype abstraction) |
| Function return | Objects remain live | Owned regions are invalidated and wiped |
| Primary client | AST, tokens, scopes, types, diagnostics | Temporary algorithm workspaces |
| Reclamation | Whole arena at process exit | Every frame exit / explicit close |
| Needed next | Alias-safe object operations and compiler libraries | Complete call/CFG lifecycle and native implementation |

Using frame-scoped scratch storage for AST nodes would invalidate objects as parser/checker helper functions return. Conversely, retaining all scratch allocations until process exit would defeat the bounded peak/lifetime contract and make cleanup semantics misleading.

## 3. Integration gaps to close

### A. Freeze the profile boundary

- Keep CCAM v0.1 scalar semantics byte-for-byte stable.
- Keep the proposed scratch-region instruction profile distinct and explicitly versioned.
- Specify a separate compiler-arena profile (or a separately named CCAM extension) for typed objects. Do not broaden the scratch profile by implication.
- Define the shared trap vocabulary and deterministic trap precedence only where the two profiles genuinely share operations.

### B. Make object identity real

For the compiler arena, preserve #482's opaque identity/reference API when introducing CCAM register values. The machine must issue and resolve handles; source integers must never be accepted as references. Prove or explicitly bound the identity primitive's issuance and non-reuse assumptions, retain cross-arena rejection, and define stale-handle behaviour. Module/type descriptor identity must be canonical across separately compiled modules, not a local integer convention.

For scratch regions, prove generation advancement cannot wrap or be reused while a stale view can exist. The validator's abstract generation state and runtime table generation must correspond.

### C. Resolve value and aliasing semantics

The language/compiler must define whether aggregate values are references, immutable values or explicit handles; how assignment, parameter passing and return behave; and whether mutation through one alias is visible through another. Until then, a mutable struct/list prototype is not evidence of valid language semantics.

A safer first executable bridge is an explicit machine-owned arena state with operations of the form `(state, request) -> (new_state, result/trap)`. The state is committed only after all type, bounds and resource checks pass. This avoids relying on unproved host-language aliasing while the reference model is being connected to the actual runtime.

### D. Integrate validation before execution

The whole-program validator must check every layout and every aggregate operand, including unreachable instructions. It must establish:
- closed descriptors and canonical nominal type identities;
- register/reference type correctness and definite initialisation;
- object-kind, field and array-element compatibility;
- logical-length bounds, mutability and reference provenance;
- frame ownership and capability escape restrictions for scratch views;
- bounded descriptor/object counts, nesting, work and memory;
- exact trap precedence and failure atomicity.

The scratch CFG validator is a useful component, but it is not the aggregate heap validator and does not prove source-language alias safety.

### E. Establish one observable semantics across implementations

Build one adversarial corpus and run it against:
1. the pure Capstan reference transition model;
2. the complete structural/whole-program validator;
3. the reference CCAM evaluator;
4. the Linux x86-64 native backend.

Compare result values, output bytes, trap code and precedence, state mutation, object/reference validity, and every resource counter. Include exact-limit and one-over cases, allocation failure at every preflight boundary, stale/cross-machine handles, aliasing, wrong descriptors, uninitialised reads, logical-length versus capacity, normal return, trap, cancellation and call-depth exhaustion.

The independent Python byte-store oracle in the scratch prototype is useful as a temporary research oracle, but it cannot be part of the final Capstan-only implementation/test toolchain. Port the authoritative test vectors and oracle to Capstan before declaring the repository's build/test path Capstan-only.

### F. Connect the compiler source, not a toy subset

Track a machine-readable feature-closure matrix for every file in the compiler source list:
- AST and diagnostic records;
- lexer tokens, source slices and keyword maps;
- parser state and recursive construction;
- checker scopes, types, flow summaries and policy metadata;
- range-analysis maps/vectors;
- deterministic diagnostics and output builders;
- imports, argument handling and bounded filesystem IO.

The compiler arena must support the actual operations those modules use. A small successful heap demo is not source closure. Replace `compiler/codegen.cap`'s C-emitting implementation with a deterministic CCAM/native-code producer; compiling the existing C generator to native code would still generate C and fail the objective.

## 4. Recommended implementation order

1. **Contract split:** approve the separate lifetime profiles and their common/non-common invariants. No CCAM v0.1 semantic change.
2. **Arena model hardening:** retain #482's opaque instance-bound references; resolve aliasing, descriptor canonicalisation, accounting and failure atomicity in #246. Prefer explicit state-in/state-out transitions until concrete reference semantics are proved. #482 closes the public integer-token/ID construction flaw, not the evaluator/native capability bridge.
3. **Scratch lifecycle hardening:** complete #463's region/view ownership, generation, CFG join, return/trap/unwind and failure-path tests. Keep its no-escape/no-parameter restrictions until a borrow model exists.
4. **Formal bridge:** prove abstract invariants first, then connect the Lean state to the Capstan implementation's concrete representation. A model-only theorem must not be promoted as implementation refinement.
5. **Evaluator integration:** add versioned typed values and opcodes, whole-program validation and execution. Preserve v0.1 as a separate accepted profile.
6. **Native integration:** implement identical object and scratch semantics in the Linux x86-64 backend using checked runtime-owned handles and explicit OS allocation boundaries. Differentially test every operation.
7. **Compiler libraries:** implement records, arrays, `List<T>`, bounded `Map<K,V>`, immutable bytes/strings and builders in Capstan.
8. **Source closure:** port all compiler modules and replace C-emitting codegen. Report zero unsupported compiler constructs before attempting full self-compilation.
9. **Bootstrap:** remove the Python stage-0 and C compile stages from the release path only after the Capstan-native seed can build S1, S2 and S3 with reproducible artifacts.

## 5. C-free acceptance gates

The repository is not C-free today. The current `Makefile` bootstraps through `bootstrap/capstan0.py`, emits `stage2.c`, compiles it with `$(CC)`, emits `stage3.c`, and compiles again. The compiler CLI's build path also emits C. The C runtime remains part of that toolchain.

The strict end-state gate must be mechanical, not descriptive:

- clean build succeeds with no Python interpreter and no C compiler installed;
- no generated `.c` files appear in the build graph;
- no compiler, launcher, helper or runtime invokes a C toolchain or hides a C implementation behind FFI;
- no Capstan-owned C runtime or unapproved libc dependency is required;
- the complete compiler source list is compiled, with no omitted modules;
- S0→S1→S2→S3 provenance and deterministic artifact comparisons are recorded;
- shared evaluator/native conformance and exact-head assurance gates pass.

A C compiler may remain installed on a developer's machine as an unrelated tool; the test is that the supported Capstan build and execution paths do not invoke or require it.

## 6. Explicit non-claims

This review does not claim that either prototype is a conforming machine, that their current tests prove implementation safety, that the native backend is complete, or that the compiler is self-hosting without C/Python. It recommends a clean separation of memory lifetimes and a dependency-ordered integration plan. All implementation and proof claims remain tied to exact source revisions and passing exact-head evidence.


## 10. Post-merge status (2026-11-26)

PR #482 is merged. It closes #480's public integer-token/object-ID construction flaw in the Capstan heap module: references and arena identities are opaque to importers, and cross-arena resolution is rejected. Exact-head CodeQL, static-analysis, supply-chain, Linux Clang/GCC, macOS Clang, allocator/GC abstract-model and existing language-verification checks passed.

PR #483 is also merged. It adds a Lean protocol model for heterogeneous typed frames, bounded frame pushes and typed non-void/void caller-return commits. It does not establish correspondence with `verification/ccam_calls.cap`.

**#481 / #458 remain open.** The process-lifetime heap remains a Capstan reference model, not an aggregate CCAM profile, validator, evaluator, source lowerer or native backend. The immediate unresolved gate is alias-preserving, failure-atomic aggregate state transitions. Keep compiler-arena objects distinct from #463 frame-scoped scratch regions.

These merged increments narrow the next engineering work; they do not satisfy aggregate-memory integration or the C-free self-hosting acceptance criteria.
