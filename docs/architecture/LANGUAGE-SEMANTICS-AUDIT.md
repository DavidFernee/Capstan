# Language semantics audit (initial)

**Status:** initial source audit; not yet a normative specification  
**Baseline:** `main` at `e1b9a023d275516ebc352a24293d532011961988` (2026-11-24)  
**Workstream:** `language/semantics-core`

This document records observable language rules and semantic risks found during the first pass over `docs/SPEC.md`, the checker, C code generator, and runtime. It deliberately distinguishes confirmed source facts from questions that require executable regression tests. The generated-C backend is evidence about current behaviour, not the semantic authority for the C-free architecture.

## 1. Architectural boundary

The current compiler pipeline is lexer → parser → AST → checker → C code generator. Type annotations are attached to the AST and consumed by code generation; there is not yet a separate, normative typed IR with an independently defined execution semantics.

The C-free architecture should define source meaning independently of this pipeline. In particular:
- source evaluation order must be explicit and must not inherit C's unspecified expression/argument evaluation order;
- every potentially trapping operation must have a defined precondition and observable trap;
- aggregate access, mutation, calls, and allocation must be represented as ordered effects;
- the typed IR must preserve source-observable behaviour, not merely type-check or produce equivalent results for pure expressions.

## 2. Confirmed compatibility facts and gaps

### 2.1 Remainder at the signed minimum

The runtime helper `cap_mod(a, b)` traps when `b == 0`, but returns zero for `INT64_MIN % -1`. This is the existing language behaviour in the ordinary runtime path. Division by zero and the signed division overflow case are handled separately.

**Compatibility decision required:** the CCAM v0.1 draft currently specifies a trap for `INT64_MIN rem -1`. That is a semantic incompatibility. Unless David explicitly approves a language-version change, preserve the existing observable rule: remainder by zero traps; `INT64_MIN % -1 == 0`. Ensure the abstract machine and all execution backends implement this without relying on host-language undefined behaviour.

### 2.2 Compound assignment and evaluation sequencing

The specification states strict left-to-right expression evaluation (`expr.order`). In `compiler/codegen.cap`, compound assignment to an indexed target is emitted as a nested C expression: the list update receives the list, index, and a computed value containing a list read and the RHS. For example, the shape generated for an expression equivalent to `xs[0] += mutate(xs)` can place the old-value read and RHS call in separate C function arguments.

C does not specify the evaluation order of function arguments. If the RHS mutates the same aggregate, the generated program can observe an order different from the source language's stated left-to-right rule.

**Status:** confirmed cross-compiler behaviour defect. The focused fixture in PR #93 passes the expected-output/conformance check under the reference compiler, but the portability matrix on CI run `45342627667` reports GCC `-O0`, `-O2` and `-O3` produce a different result for the field/list mutation cases. The source generator forms `cap_add(old_target_read, rhs_call, ...)` inside an assignment/update expression without explicit sequencing. The normative lowering must evaluate and retain the target location/index, read the old value, evaluate the RHS, compute, then write. Do not encode this as one expression with multiple effectful C arguments. Draft PR #97 implements this sequence for local, field, indexed and text compound assignment; its exact-head CI passed all four jobs. PR #102 adds broader operand-order coverage and carries the invalidated-index runtime regression; its corrected exact-head CI is pending. A proposed side-effectful lvalue-once fixture was removed because the current checker rejects call-expression receivers as compound-assignment targets. Neither PR has been merged, so the fix is not yet part of `main`.

### 2.3 `read_line()` resource bound is not normative in the reference

The runtime defines `CAP_READ_LINE_MAX = 1 << 20` and traps when a line exceeds 1 MiB. The runtime comment documents this limit. The `read_line()` row in `docs/SPEC.md` documents byte preservation and EOF behaviour but does not state the 1 MiB bound or its failure mode.

**Required specification update:** PR #93 now adds the limit to `docs/SPEC.md`: 1,048,576 payload bytes, excluding the terminating newline. Exactly 1 MiB is accepted; the next non-newline byte causes a controlled runtime trap (CWE-789). The runtime unit tests cover max bytes with newline and max-plus-one payload bytes. PR #93 adds `tests/unit/read_line_eof.py` to cover exactly 1 MiB followed immediately by EOF through the public native API; its CI is pending. This is a compatibility contract, not merely an implementation tuning parameter.

### 2.4 Proven remainder helper needs an explicit overflow guard

The runtime's ordinary `cap_mod` handles `INT64_MIN % -1` explicitly. The corresponding `cap_mod_proved` helper currently evaluates C's `a % b` directly. In C, signed division and remainder are undefined when the quotient is not representable, including `INT64_MIN % -1`.

**Status:** the helper body is unsafe if called outside its precondition, but source inspection of `compiler/ranges.cap::bin_safe` shows an explicit `no_min_by_minus_one` guard. The dedicated fixture expects one proven operation (the unary negation forming `-1`) and therefore fails if the remainder itself is lowered to `cap_mod_proved`. The first CI run exposed that the initial expected count of zero was wrong because the unary negation is legitimately proven; the fixture was corrected to one. The corrected assertion still requires a rerun. This is not a formal proof of range-analysis soundness. Retain the guard and helper precondition; a proof-based fast path must never license undefined behaviour in the implementation language.


### 2.5 Compound indexed assignment and post-RHS validity

The compound-assignment correction in draft PR #97 retains the list and index, reads the old element, evaluates the RHS, then writes. It selects the same `_proved` suffix for the old-value read and final write when `index_safe` is true.

A bounds fact established before the RHS is not by itself sufficient for the final write: the RHS may shrink the list. Source inspection shows `seq_ok` is initialised to `false` in `ranges.cap`, then set by `codegen.cap::gen_guarded` only when the condition/body/step contain no operation classified by `may_shrink`; `gen_block` also uses `rest_may_shrink` when carrying facts past exiting branches. `may_shrink` conservatively classifies list `pop`/`remove_at`/`clear`, struct/enum methods, user-function calls and authorisation/test operations. This is an intended fail-closed effect guard, not a formal proof of completeness. The invalidation fixture exercises the checked runtime write path because its RHS calls user code that may shrink the list. The classifier and region transitions must be updated whenever a new mutating operation or effectful feature is added.

PR #93 adds `tests/runtime/compound_assignment_invalidated_index.cap`: after `i < xs.len()` establishes an index condition, the compound-assignment RHS removes the element. The final store must trap with CWE-787 because the retained index is no longer within the current logical length. Because this RHS contains a user-function call, the region guard should disable the list-length fact and keep the final store checked; this test verifies that dynamic post-RHS validation. It is not evidence that every future mutating operation is already classified by `may_shrink`.


### 2.6 String-literal materialisation is an effect in the current backend

The runtime `CAP_LIT` macro lazily initialises a static pointer by calling `cap_str_perm`, which uses `malloc` and can terminate through the OOM path. Therefore the first evaluation of a string literal is not a pure C constant in the current backend. Treating `N_STR` as a simple operand allowed C argument evaluation order to move that allocation after a later effectful call, contrary to source left-to-right evaluation. Draft PR #109 removes `N_STR` from the simple-operand class and adds generated-C regressions for call arguments and concatenation operands. Its exact head `a3b56e997e1e867fb5320db84ad754856adb16ac` passes all four required CI jobs, but it remains unmerged; the correction is therefore not yet integrated into `main`. The C-free architecture should decide whether literals are immutable static data (with an explicit resource-compatibility decision) or effectful initialisation operations; it must not silently inherit the current C macro.


### 2.7 Stage-0 `read_line()` parity gap

The native runtime rejects a line whose payload exceeds 1,048,576 bytes, but the temporary `bootstrap/capstan0.py::b_read_line()` currently delegates to unbounded `sys.stdin.buffer.readline()`. This makes Stage 0 disagree with the native runtime at the over-limit boundary and means it cannot be treated as a differential oracle for this behaviour until aligned. PR #93 adds a native public-API regression for exactly 1 MiB followed immediately by EOF; the C runtime unit suite already covers exactly 1 MiB followed by newline and max-plus-one rejection. The bootstrap implementation is non-normative and must not redefine the language contract.

## 3. Normative semantic requirements for the C-free core

1. **Deterministic sequencing:** all observable subexpressions have a specified order. The IR must make effectful ordering explicit.
2. **Defined integer semantics:** signed 64-bit operations specify exact result or trap conditions; no host-language undefined behaviour is permitted.
3. **Defined traps:** each trap has a stable semantic category and occurs at the specified operation, before subsequent effects.
4. **Aggregate operations:** index evaluation, bounds checks, reads, writes, and RHS evaluation have an explicit order.
5. **Resource semantics:** externally influenced input sizes and allocation limits are part of the contract where they affect program behaviour.
6. **Backend independence:** the semantics must be stated over Capstan values and machine state, not C expressions, C ABI details, or compiler-specific statement expressions.

## 4. Required next verification

- Add an executable regression for indexed compound assignment whose RHS mutates the same list; assert the result dictated by left-to-right semantics.
- Exercise both ordinary and range-proven remainder paths at `INT64_MIN, -1`.
- Test `read_line()` at 1 MiB and one byte over, including newline and EOF boundary cases.
- Audit compound assignment to fields, constructors, call arguments, and aggregate literals for the same sequencing hazard.
- Reconcile CCAM's arithmetic rules with the compatibility decision above before treating CCAM as the reference semantics.

## 5. Scope and confidence

This is an initial audit, not a complete language specification or a claim that the compiler is safe. No compiler or runtime implementation files were changed. PR #93 adds executable conformance fixtures for field/list compound-assignment sequencing and signed remainder boundaries, including an optimizer-path assertion. CI confirmed the compound-assignment cross-compiler mismatch (GCC `-O0/-O2/-O3`). Draft PR #97 now implements explicit sequencing and has passed its exact-head GCC, Clang, macOS and supply-chain jobs, but it remains unmerged. PR #102 adds broader operand-order coverage; its corrected exact-head CI is pending. The corrected remainder optimizer assertion expects exactly one proof for unary `-1`, while requiring the MIN/-1 remainder to retain its checked helper; the current PR #93 exact-head CI is also pending. Dependent PR #100 updates CCAM semantics and the Capstan-native remainder substrate; its exact-head CI is running.
