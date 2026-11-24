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

The specification states strict left-to-right expression evaluation (`expr.order`). The original field and indexed compound-assignment lowering nested the old-value read and RHS inside a generated C call expression. C does not specify function-argument evaluation order, so a RHS mutating the same aggregate could produce compiler-dependent results.

**Status:** confirmed cross-compiler defect, now fixed on `main`. PR #97 merged as `30958c0b1e069225debbc743b97cab1665ec2562`; it explicitly sequences local, field, indexed and text compound assignment, and retains a runtime regression for an indexed location invalidated by RHS mutation. The original portability matrix reproduced the defect under GCC `-O0`, `-O2` and `-O3`. The source checker on the audit baseline accepted only local variables, simple field paths and simply-indexed elements as compound-assignment targets. Draft PR #123 now proposes admitting effectful field receivers and adds an exactly-once regression; indexed targets remain restricted to simple paths. The normative lowering now distinguishes target identity: a field target evaluates and retains its receiver object once, then writes that same object's field after the RHS; a direct indexed-element target retains container/index and revalidates current bounds after the RHS. `tests/accept/compound_field_receiver_identity.cap` verifies that replacing `xs[0]` during the RHS does not retarget `xs[0].field` to the replacement object.

### 2.3 `read_line()` resource bound is not normative in the reference

The runtime defines `CAP_READ_LINE_MAX = 1 << 20` and traps when a line exceeds 1 MiB. The runtime comment documents this limit. At the audit baseline, the `read_line()` row in `docs/SPEC.md` documented byte preservation and EOF behaviour but omitted the 1 MiB bound and its failure mode; PR #93 now corrects that omission.

**Specification update and boundary evidence:** the `docs/SPEC.md` row in PR #124 records the limit: 1,048,576 payload bytes, excluding the terminating newline. Exactly 1 MiB is accepted; the next non-newline byte causes a controlled runtime trap (CWE-789). Existing runtime unit tests cover max bytes with newline and max-plus-one payload bytes. PR #124 adds `tests/unit/read_line_eof.py` to cover exactly 1 MiB followed immediately by EOF through the public native API. PR #124's exact-head CI is queued; do not claim the new test passed until that run completes. This is a compatibility contract, not merely an implementation tuning parameter.

### 2.4 Proven remainder helper needs an explicit overflow guard

The runtime's ordinary `cap_mod` handles `INT64_MIN % -1` explicitly. The corresponding `cap_mod_proved` helper currently evaluates C's `a % b` directly. In C, signed division and remainder are undefined when the quotient is not representable, including `INT64_MIN % -1`.

**Status:** the helper body is unsafe if called outside its precondition, but source inspection of `compiler/ranges.cap::bin_safe` shows an explicit `no_min_by_minus_one` guard. The dedicated fixture expects one proven operation (the unary negation forming `-1`) and therefore fails if the remainder itself is lowered to `cap_mod_proved`. The first CI run exposed that the initial expected count of zero was wrong because the unary negation is legitimately proven; the fixture was corrected to one. The corrected assertion still requires a rerun. This is not a formal proof of range-analysis soundness. Retain the guard and helper precondition; a proof-based fast path must never license undefined behaviour in the implementation language.


### 2.5 Compound indexed assignment and post-RHS validity

The compound-assignment correction merged in PR #97 retains the list and index, reads the old element, evaluates the RHS, then writes. It selects the same `_proved` suffix for the old-value read and final write when `index_safe` is true.

A bounds fact established before the RHS is not by itself sufficient for the final write: the RHS may shrink the list. Source inspection shows `seq_ok` is initialised to `false` in `ranges.cap`, then set by `codegen.cap::gen_guarded` only when the condition/body/step contain no operation classified by `may_shrink`; `gen_block` also uses `rest_may_shrink` when carrying facts past exiting branches. `may_shrink` conservatively classifies list `pop`/`remove_at`/`clear`, struct/enum methods, user-function calls and authorisation/test operations. This is an intended fail-closed effect guard, not a formal proof of completeness. The invalidation fixture exercises the checked runtime write path because its RHS calls user code that may shrink the list. The classifier and region transitions must be updated whenever a new mutating operation or effectful feature is added.

PR #97 merged `tests/runtime/compound_assignment_invalidated_index.cap`: after `i < xs.len()` establishes an index condition, the compound-assignment RHS removes the element. The final store must trap with CWE-787 because the retained index is no longer within the current logical length. Because this RHS contains a user-function call, the region guard disables the list-length fact and keeps the final store checked; this test verifies dynamic post-RHS validation. It is not evidence that every future mutating operation is already classified by `may_shrink`.


### 2.6 String-literal materialisation is an effect in the current backend

The runtime `CAP_LIT` macro lazily initialises a static pointer by calling `cap_str_perm`, which uses `malloc` and can terminate through the OOM path. Therefore the first evaluation of a string literal is not a pure C constant in the current backend. Treating `N_STR` as a simple operand allowed C argument evaluation order to move that allocation after a later effectful call, contrary to source left-to-right evaluation. PR #109 has now merged to `main` as commit `4e6b4e08ab710fc4e5dde82d3416b16e130b8d2f` after its exact-head four-job CI passed. It removes `N_STR` from the simple-operand class and adds generated-C regressions for call arguments and concatenation operands. The current C backend therefore sequences lazy literal materialisation explicitly. The C-free architecture must still decide whether literals are immutable static data (with an explicit resource-compatibility decision) or effectful initialisation operations; it must not silently inherit the current C macro.


### 2.7 Stage-0 `read_line()` parity gap

The native runtime rejects a line whose payload exceeds 1,048,576 bytes, but the temporary `bootstrap/capstan0.py::b_read_line()` currently delegates to unbounded `sys.stdin.buffer.readline()`. This makes Stage 0 disagree with the native runtime at the over-limit boundary and means it cannot be treated as a differential oracle for this behaviour until aligned. PR #124 adds a native public-API regression for exactly 1 MiB followed immediately by EOF; the C runtime unit suite already covers exactly 1 MiB followed by newline and max-plus-one rejection. The bootstrap implementation is non-normative and must not redefine the language contract.

## 3. Normative semantic requirements for the C-free core

1. **Deterministic sequencing:** all observable subexpressions have a specified order. The IR must make effectful ordering explicit.
2. **Defined integer semantics:** signed 64-bit operations specify exact result or trap conditions; no host-language undefined behaviour is permitted.
3. **Defined traps:** each trap has a stable semantic category and occurs at the specified operation, before subsequent effects.
4. **Aggregate operations:** index evaluation, bounds checks, reads, writes, and RHS evaluation have an explicit order.
5. **Resource semantics:** externally influenced input sizes and allocation limits are part of the contract where they affect program behaviour.
6. **Backend independence:** the semantics must be stated over Capstan values and machine state, not C expressions, C ABI details, or compiler-specific statement expressions.

## 4. Required next verification

- Keep the merged indexed compound-assignment mutation regression in the conformance suite and ensure the exact-head compiler matrix remains green.
- Exercise both ordinary and range-proven remainder paths at `INT64_MIN, -1`; PR #124 adds the checked-helper optimizer assertion. A new `tests/runtime/remainder_by_zero.cap` fixture also covers `%` by a variable zero divisor at run time.
- Run the PR #124 `read_line()` exact-limit-at-EOF regression; the newline and max-plus-one cases are already covered by runtime unit tests.
- Audit constructor arguments and aggregate literals for analogous sequencing hazards; PR #109 already fixed the first-use string-literal operand-order case.
- Merge/reconcile PR #132's CCAM arithmetic correction before treating CCAM's remainder rule as aligned with the source core.

## 5. Scope and confidence

This is an initial audit, not a complete language specification or a claim that the compiler is safe. No compiler or runtime implementation files are changed by this semantics PR. The original compound-assignment cross-compiler mismatch was fixed by merged PR #97; string-literal operand ordering was fixed by merged PR #109. PR #124 carries the normative source-level semantics, signed-remainder boundary and zero-divisor fixtures, an optimizer-path assertion, short-circuit fixtures and the `read_line()` EOF-boundary test. Its exact-head CI is queued. The corrected remainder optimizer assertion expects exactly one proof for unary `-1`, while requiring the MIN/-1 remainder to retain its checked helper. Dependent PR #132 updates CCAM semantics and the Capstan-native remainder substrate; its exact-head CI is still running.
