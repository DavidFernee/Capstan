# Compiler Evaluation-Order Assurance

**Status:** source-level audit and regression boundary, not a proof of compiler correctness  
**Applies to:** the v0.6 generated-C backend  
**Normative rule:** Capstan evaluates expression operands and call arguments from left to right.

## 1. Why this boundary matters

C does not generally specify the order in which function arguments are evaluated. A generated call such as:

```c
cap_add(read_field(object), call_that_mutates_object(), loc)
```

is therefore not a valid implementation of Capstan's left-to-right rule. The compiler must sequence observable operand evaluations before placing their resulting values in a C call.

The backend uses GNU C statement expressions and temporaries for this purpose. That is a compatibility mechanism for v0.6, not part of the C-free architecture.

The mainline now contains the explicit compound-assignment sequencing implementation and field/string/list regressions (#97), the lazy-string-literal correction (#109), support for side-effectful compound-field receivers with exactly-once evaluation (#123), and literal-first `sql_query` / `run` argument sequencing (#133). PR #124 carries the proposed normative source-level core and typed-IR contract; this document records the current v0.6 backend evidence without depending on that proposal being merged.

## 2. Current lowering strategy

| Source construct | Lowering strategy | Assurance condition |
|---|---|---|
| Binary operators and comparisons | `operands()` followed by `hoist()` | When two or more operands are classified complex, all complex operands are assigned to temporaries in source order before the final C expression/call |
| Direct calls and ordinary builtins | Same `operands()` / `hoist()` path | Same condition; the function designator is statically resolved |
| Methods | Receiver and arguments are collected in source order, then passed through `hoist()` | Same condition |
| Short-circuit `&&` / `||` | C short-circuit operators | C guarantees left operand evaluation first and conditional right operand evaluation |
| Field/index assignment | Explicit receiver/index/value temporaries where required | The lvalue address components are evaluated before the assigned value when their evaluation can be observable |
| Struct/enum construction | Sequential statement-expression assignments | Initialisers are emitted in source order |
| Authorisation arguments | Sequential typed temporaries | Policy arguments are evaluated in source order before policy evaluation |
| Compound assignment | Explicit old-value read, RHS evaluation, computation and write | The old value and target address are retained before a mutating RHS. Compound field receivers may be effectful but are evaluated exactly once before the old-value read and RHS; `tests/accept/compound_assignment_lvalue_once.cap` verifies this. In the current implementation, range analysis does not generate list-length facts (`seq_ok` remains false), so indexed-list reads and writes use checked helpers; the merged PR #97 regression verifies that an RHS which removes the indexed element traps at the final write. Any future list-bounds check elision requires a complete alias/effect proof, not merely the presence of the currently unused `may_shrink` helpers. |
| `sql_query` / `run` | Special lowering materialises the literal first argument and each remaining source argument into temporaries from left to right before allocating and populating the runtime argument list | The generated-C regression in `tests/unit/codegen_literal_order.py` covers both builtins; the correction is merged in PR #133 |

## 3. The `hoist()` classification invariant

The optimisation does not materialise every operand unconditionally. It classifies integer/boolean/none literals and variable references as simple; string literals, field, index, call and method expressions are complex. String literals are complex because `CAP_LIT` performs lazy allocation in the current runtime; the sequencing correction is now in main via merged PR #109.

This is sound only under the following current-language assumptions:

1. A local scalar binding is not addressable or captured by a callee. Function arguments are passed by value, so a call cannot reassign the caller's local scalar.
2. A local reference-valued binding contributes its pointer/reference value. A callee may mutate the referenced object, but cannot change the caller's local binding itself through that by-value argument.
3. Global names resolved as variables are constants registered in the checker; there are no mutable global variable bindings.
4. Field, index, call, method and string-literal expressions are classified complex and materialised in source order when paired with another complex operand. String literals require this treatment because `CAP_LIT` lazily allocates via `malloc` and can fail.

If any future language feature invalidates one of these assumptions—mutable globals, by-reference scalar parameters, captured mutable locals, overloaded variable reads, or effectful getters—the simple/complex classification must be revisited before that feature is enabled. String-literal sequencing is fixed in main; the safe fallback for any future effectful expression is to materialise every operand in source order or eliminate runtime effects from its construction.

This is an explicit compiler proof obligation, not an intrinsic property of C.

## 4. Regression evidence

`tests/accept/operand_evaluation_order.cap` checks both:
- a field read used as the left operand of an expression whose right operand mutates the same object;
- a field read used as the first argument of a call whose second argument mutates the same object.

The expected output is `11` and `1001`. These values distinguish left-to-right evaluation from a lowering that executes the mutating call before reading the field.

`tests/accept/compound_assignment_sequence.cap` separately checks field, string-field and indexed-list compound assignments with mutating RHS functions. `tests/accept/compound_assignment_lvalue_once.cap` checks that an effectful field receiver is evaluated exactly once. The current checker still restricts indexed compound-assignment targets to simple-indexed elements, so effectful index/base expressions are not currently source-representable; the indexed-list old-value and post-RHS validity paths are covered by the implementation and regression tests merged in PR #97. PR #124 separately specifies the normative source-level contract.

The fixtures are conformance tests. They do not prove all generated expressions correct, establish that the C compiler behaves identically on every target, or replace a formal source-to-CCAM/native correctness argument. The `sql_query` / `run` special-call exception is now corrected and covered separately by merged PR #133; the fixture in this PR focuses on ordinary operand sequencing.

## 5. Required future work

- Keep a syntax-node classification test whenever new expression forms are introduced.
- Keep the literal-first `sql_query` / `run` regression in `tests/unit/codegen_literal_order.py` as part of the standard unit suite.
- Add tests for every new multi-operand lowering path, especially effectful builtins and collection methods.
- Prefer a typed effect classification over syntax-only `is_simple()` when the language gains richer aliasing, closures or by-reference features.
- Make left-to-right sequencing explicit in CCAM semantics and in the native backend; do not inherit C's unspecified evaluation order.
- Include trap order and resource accounting in differential tests, not only final values.
