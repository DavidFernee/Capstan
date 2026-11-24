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
| Compound assignment | Explicit old-value read, RHS evaluation, computation and write | The old value and target address are retained before a mutating RHS; a potentially invalidated index is rechecked at write time, while a proved setter is permitted only when the range analysis establishes that the RHS region cannot shrink the list; see PR #97 |
| `sql_query` / `run` | Special lowering builds a runtime argument list | Argument zero is statically required by the checker to be a string literal, so its later textual placement cannot reorder a source side effect; remaining arguments are appended sequentially |

## 3. The `hoist()` classification invariant

The optimisation does not materialise every operand unconditionally. It classifies integer/string/boolean/none literals and variable references as simple; field, index, call and method expressions are complex.

This is sound only under the following current-language assumptions:

1. A local scalar binding is not addressable or captured by a callee. Function arguments are passed by value, so a call cannot reassign the caller's local scalar.
2. A local reference-valued binding contributes its pointer/reference value. A callee may mutate the referenced object, but cannot change the caller's local binding itself through that by-value argument.
3. Global names resolved as variables are constants registered in the checker; there are no mutable global variable bindings.
4. Field, index, call and method expressions are classified complex and materialised when paired with another complex operand.
5. **Unresolved exception:** the current `is_simple()` also classifies string literals as simple, but `CAP_LIT` lazily allocates via `malloc` on first evaluation. That is an effect with a possible allocation-failure outcome. Issue #106 tracks whether literal materialisation is part of the observable resource-order contract and the required codegen/allocation-failure regression. Until resolved, the C backend's ordering claim is not complete for string-literal initialisation.

If any future language feature invalidates one of these assumptions—mutable globals, by-reference scalar parameters, captured mutable locals, overloaded variable reads, or effectful getters—the simple/complex classification must be revisited before that feature is enabled. The current string-literal exception is already known and unresolved. The safe fallback is to materialise every operand in source order or eliminate runtime effects from literal construction.

This is an explicit compiler proof obligation, not an intrinsic property of C.

## 4. Regression evidence

`tests/accept/operand_evaluation_order.cap` checks both:
- a field read used as the left operand of an expression whose right operand mutates the same object;
- a field read used as the first argument of a call whose second argument mutates the same object.

The expected output is `11` and `1001`. These values distinguish left-to-right evaluation from a lowering that executes the mutating call before reading the field.

`tests/accept/compound_assignment_sequence.cap` separately checks field, string-field and indexed-list compound assignments with mutating RHS functions. `tests/accept/compound_assignment_lvalue_once.cap` checks that a side-effectful field receiver, indexed-list base and index expression are each evaluated exactly once before the RHS. `tests/runtime/compound_assignment_invalidated_index.cap` checks that an RHS which shrinks the list causes a controlled bounds trap at the final write rather than an unchecked stale-index store.

The fixtures are conformance tests. They do not prove all generated expressions correct, establish that the C compiler behaves identically on every target, or replace a formal source-to-CCAM/native correctness argument.

## 5. Required future work

- Keep a syntax-node classification test whenever new expression forms are introduced.
- Add tests for every new multi-operand lowering path, especially effectful builtins and collection methods.
- Prefer a typed effect classification over syntax-only `is_simple()` when the language gains richer aliasing, closures or by-reference features.
- Make left-to-right sequencing explicit in CCAM semantics and in the native backend; do not inherit C's unspecified evaluation order.
- Include trap order and resource accounting in differential tests, not only final values.
