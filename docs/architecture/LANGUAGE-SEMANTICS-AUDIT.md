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

**Status:** high-confidence semantic/code-generation defect candidate, requiring a focused executable regression against the current compiler. The normative IR must lower this as explicit sequencing: evaluate and retain the target location/index, read the old value, evaluate the RHS, compute, then write. Do not encode this as one expression with multiple effectful C arguments.

### 2.3 `read_line()` resource bound is not normative in the reference

The runtime defines `CAP_READ_LINE_MAX = 1 << 20` and traps when a line exceeds 1 MiB. The runtime comment documents this limit. The `read_line()` row in `docs/SPEC.md` documents byte preservation and EOF behaviour but does not state the 1 MiB bound or its failure mode.

**Required specification update:** the limit is 1,048,576 payload bytes, excluding the terminating newline. Exactly 1 MiB is accepted; the next non-newline byte causes a controlled runtime trap (CWE-789). EOF after exactly 1 MiB is accepted. Add boundary tests for max bytes with newline, max bytes at EOF, and max-plus-one payload bytes. This is a compatibility contract, not merely an implementation tuning parameter.

### 2.4 Proven remainder helper needs an explicit overflow guard

The runtime's ordinary `cap_mod` handles `INT64_MIN % -1` explicitly. The corresponding `cap_mod_proved` helper currently evaluates C's `a % b` directly. In C, signed division and remainder are undefined when the quotient is not representable, including `INT64_MIN % -1`.

**Status:** the helper body is unsafe if called outside its precondition, but source inspection of `compiler/ranges.cap::bin_safe` shows an explicit `no_min_by_minus_one` guard: the proven form is not selected when the dividend interval includes `INT64_MIN` and the divisor interval includes `-1`. The draft PR adds `tests/accept/remainder_min_minus_one.cap` with `// expect-proved: 0` to assert that this exceptional pair stays on the checked path. CI has not yet completed on the latest head, and this is not a formal proof of range-analysis soundness. Retain the guard and helper precondition; a proof-based fast path must never license undefined behaviour in the implementation language.

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

This is an initial audit, not a complete language specification or a claim that the compiler is safe. No compiler or runtime implementation files were changed. PR #93 adds executable conformance fixtures for field/list compound-assignment sequencing and signed remainder boundaries, including an optimizer-path assertion. They have not been run locally; CI is pending on the latest PR head. The compound-assignment source defect is strongly indicated by the generated expression structure but should be treated as confirmed only after the fixture demonstrates a mismatch on a supported compiler. The proven remainder helper's exceptional case is excluded by the current range predicate, subject to the new regression and later formal proof.
