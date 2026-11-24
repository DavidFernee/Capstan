# Compiler Contract: Lowering the Checked Source Core to CCAM

**Status:** target compiler contract; dependent on review of the language-semantics and CCAM contracts. PR #167 implements an initial, deliberately narrower scalar lowering stage; it is not yet conformant to the complete subset specified here.  
**Owner:** Compiler Architecture workstream  
**Related:** `LANGUAGE-CORE.md`, `TYPED-IR.md`, `CCAM.md`, `COMPILER-PIPELINE-AUDIT.md`

This document specifies the compiler-owned lowering boundary for the first C-free vertical slice. It does not define a second IR or restate the abstract machine's instruction semantics. CCAM remains the canonical typed core IR and execution semantics.

## 1. Pipeline boundary

The initial C-free path is:

```
source
  -> lexer / parser
  -> existing checker (accepted scalar subset only)
  -> deterministic source-to-CCAM lowering
  -> complete CCAM structural validation
  -> Capstan-native CCAM evaluator
```

The native machine-code backend is a subsequent consumer of the same validated CCAM program. It must not bypass CCAM validation or assign independent meanings to source constructs.

The existing generated-C path remains a separate compatibility path while the C-free implementation is developed. It may be used as a differential comparator, but a disagreement is resolved against normative source semantics and CCAM—not by assuming generated C is correct.

The current AST is mutable and carries optional `Type` annotations. It is not itself the normative typed IR. Lowering must consume only a successfully checked tree and must independently check the subset/type preconditions it relies upon.

## 2. Initial supported source subset

The first lowering implementation should support only constructs expressible by CCAM v0.1:

- `int` and `bool` values;
- integer and boolean literals;
- initialised local declarations and local-variable reads/writes;
- checked integer addition, subtraction, multiplication, division and remainder;
- integer equality and signed less-than;
- boolean negation;
- derived integer comparisons (`!=`, `<=`, `>`, `>=`);
- short-circuit `&&` and `||`;
- blocks, `if` / `else`, `while`, and `for`;
- `break`, `continue`, direct calls and returns;
- `int main()` and `void main()` as entry functions.

The exact accepted subset must be checked against the final normative core and the source checker. The presence of a source AST node or the fact that the existing C backend handles it does not make it supported by the C-free compiler.

The first implementation must reject unsupported constructs with a structured compiler diagnostic. It must never emit a placeholder instruction, silently coerce a value, or fall back to generated C.

### 2.1 Current staged implementation (PR #167)

PR #167 implements an initial vertical slice that is narrower than the target list above. It currently supports integer/boolean literals and locals, local initialization and assignment, checked integer arithmetic, integer comparisons and their derived forms, boolean negation, short-circuit `&&` / `||`, direct function calls, returns, and `if` / `else`. It parses and checks actual source before lowering, validates the resulting in-memory CCAM function table, and executes it with the Capstan-native evaluator. The current tests invoke this API directly; it is not yet wired into `compiler/main.cap`, the compiler CLI, or the production build/run path, which still uses generated C.

The current implementation supports `while`, `for`, `break`, and `continue` with explicit loop-target fixups; it also rejects local shadowing rather than risking a name-to-register aliasing error. The remaining supported-subset list above is the intended target contract, not a claim that PR #167 implements every listed construct.

Explicitly excluded until separately specified and implemented: strings, structs, enums, optionals, lists, maps, heap references, methods, closures, taint, secrets, grants, IO, policies, cryptographic operations, FFI and concurrency. Bitwise operations, shifts, wrapping arithmetic, boolean equality and indirect calls are also excluded from this initial slice.

## 2.1 Aggregate assignment is a later semantic extension

The scalar v0.1 lowering subset does not include structs, lists, maps or heap locations, so it does not lower aggregate compound assignment.

When aggregate locations are admitted, the compiler MUST preserve the complete sequencing contract:

1. evaluate and retain the location designator exactly once;
2. read and retain the old value;
3. evaluate the RHS completely;
4. compute the new value;
5. establish that the retained location is still live and valid in the post-RHS state (including current logical collection bounds);
6. write only after that validation succeeds.

For an indexed collection target, a bounds check performed before the RHS is not sufficient if the RHS may shrink the collection through an alias. The compiler may omit a post-RHS check only when a sound effect/range analysis proves that no operation in the RHS can invalidate the retained location. The proof must include direct calls, methods, aliases and all future effect forms. A stale location must produce the specified controlled trap and must never reach an unchecked store.

This is a semantic requirement, not a code-generation optimisation detail. The v0.6 C-backend implementation and its field/string/list sequencing plus post-RHS invalidated-index regressions are merged in PR #97. The independent operand-order assurance fixture and audit are in PR #128; the normative source-language contract remains under review in PR #124. None of these makes aggregate assignment part of the initial CCAM scalar subset.

## 3. Lowering state and deterministic allocation

For each function, the lowering context contains:

- the checked source function and its declared signature;
- an ordered vector of CCAM register types;
- a lexical mapping from source local names to fixed register indices;
- an append-only instruction buffer;
- a monotonically increasing temporary-register allocator;
- loop targets for `break` and `continue`;
- pending branch/jump fixups;
- source-location metadata for emitted instructions;
- explicit limits for registers and emitted instructions.

Allocate parameter registers first, in source declaration order. Allocate local registers in declaration order. Allocate expression temporaries in deterministic emission order. Do not reuse registers in the first implementation: simple monotonic allocation makes initialisation and lifetime reasoning easier. Register reuse is a later optimisation and must preserve the same CCAM outcomes.

Every allocated register has exactly one declared CCAM type (`int` or `bool`). A source local is mapped to one fixed register for its lexical lifetime. Shadowing is already rejected by the current checker; if that policy changes, the lowering map must become scope-aware rather than silently aliasing names.

Register and instruction limits are checked before extending their respective vectors. Exceeding a compiler resource bound is a compile failure, not integer wraparound, partial output or an allocation attempt based on unchecked arithmetic.

## 4. Expression lowering

An expression-lowering operation returns a pair:

```
(value_register, value_type)
```

It emits all instructions required to compute that value before returning. The result register is initialised on every successful path through the emitted fragment. A failed expression aborts lowering and produces no executable program.

### 4.1 Literals and local variables

- Integer literal: allocate an `int` register and emit `const_i`.
- Boolean literal: allocate a `bool` register and emit `const_b`.
- Local read: resolve the name to its fixed register, emit a `move` into a fresh temporary, and return the snapshot register/type. This preserves left-to-right value evaluation if a later operand or call has effects. The source checker must already have established declaration and type correctness.
- Local declaration: lower the initializer completely, allocate the declared local register and emit `move` into it.
- Local assignment: lower the RHS completely, then emit `move` into the target local register.

The compiler must check literal range and declared/result type before emitting the instruction. A boolean must never be represented as an integer register.

### 4.2 Unary operators

Boolean negation emits `not_b` into a fresh boolean register.

Integer negation is lowered without adding a new CCAM opcode: emit `const_i 0`, then `sub_i result, zero, operand`. This uses checked subtraction and therefore preserves the specified overflow behaviour. The minimum signed integer literal requires the source parser's established special handling; the lowering must not attempt to negate an out-of-range positive literal as an implementation shortcut.

### 4.3 Binary arithmetic and comparisons

For every non-short-circuit binary expression:

1. lower the left operand completely;
2. lower the right operand completely;
3. verify their types against the operator;
4. emit the corresponding CCAM instruction into a fresh result register.

This ordering ensures that a trap in the left expression prevents evaluation of the right expression. The arithmetic instruction itself then performs its specified left-to-right register reads and atomic transition.

Direct mappings:

| Source operator | CCAM instruction |
|---|---|
| `+` | `add_i` |
| `-` | `sub_i` |
| `*` | `mul_i` |
| `/` | `div_i` |
| `%` | `rem_i` |
| `==` on int | `eq_i` |
| `<` on int | `lt_i` |

Derived comparisons use only typed boolean operations and integer comparisons:

- `a != b`: `eq_i` followed by `not_b`;
- `a > b`: `lt_i` with operands `b, a`;
- `a <= b`: `lt_i` with operands `b, a`, then `not_b`;
- `a >= b`: `lt_i` with operands `a, b`, then `not_b`.

No derived form may introduce an unchecked arithmetic operation. Boolean equality and inequality are excluded until the machine contract admits them or defines an approved lowering.

### 4.4 Short-circuit boolean operators

Do not lower `&&` or `||` as eager binary instructions. CCAM has no such opcode, and the RHS must not execute when short-circuited.

For `a && b`:

1. lower `a`;
2. emit a conditional branch to either the RHS block or the false-result block;
3. in the RHS block, lower `b` and move it to a result register;
4. in the false-result block, write `false` to that same result register;
5. join at the instruction following both blocks.

For `a || b`, use the same structure with the true-result block writing `true`.

The result register is declared `bool` and is initialised on every path reaching the join. Branch targets are patched only after block positions are known, then checked by the complete CCAM validator. Tests must demonstrate that a trapping or effectful RHS is suppressed when required.

## 5. Statement and control-flow lowering

Use instruction indices as basic-block positions. Emit explicit `jump` and `branch` instructions; do not rely on implicit fall-through past a function's end.

- **Block:** lower statements in source order. Stop lowering unreachable statements after a terminal return/trap where the source checker permits this; do not emit invalid fall-through.
- **If/else:** lower the condition, emit a branch to then/else blocks, and emit explicit jumps to a common continuation where needed.
- **While:** record the condition instruction index; lower the condition and branch to body/exit; push loop targets (continue = condition, break = exit); lower the body; emit a jump to condition; patch exit and all pending breaks.
- **For:** lower the initializer once; record the condition index; lower condition and branch to body/exit; lower body with continue targeting the step block; lower step; jump to condition; patch exit and breaks.
- **Break/continue:** valid only within a loop (already checked by the front end); emit a jump fixup to the innermost loop's corresponding target.
- **Return:** lower the return expression completely, then emit `ret`; emit `ret_void` for a void return. The enclosing function signature must agree.
- **Function call:** lower arguments completely from left to right, then emit one `call` with their resulting registers in source order. Allocate a result register for `int` or `bool` return; use null destination only for a void return. The callee's signature is checked against the call before emission.

Every completed function must have valid branch targets and no reachable path that falls off the instruction sequence. A final validator checks this independently of the lowering algorithm. PR #167 implements if/else and short-circuit branches, plus loop-target stacks and break/continue fixups for the supported while/for subset.

## 6. Locations and source diagnostics

The current AST records file, line and column, but not a full source span. Initially attach the best available source location to each emitted instruction. Do not fabricate end offsets.

A later lexer/parser extension should preserve start/end byte offsets and file identity through AST construction. CCAM metadata should then carry stable source spans so validation diagnostics and runtime traps can point to the originating source operation. Source metadata is diagnostic-only and must not alter execution semantics.

## 7. Validation and fail-closed behaviour

The compiler must not execute or emit native code from partially validated CCAM.

The pipeline is:

1. parse source;
2. type/safety-check source;
3. reject source constructs outside the declared C-free subset;
4. lower deterministically;
5. validate the complete immutable CCAM program;
6. execute only the validated program in the reference evaluator, or pass it to a backend that independently consumes the same validated representation.

The validator—not the lowering implementation—must reject malformed function tables, unknown type tags/opcodes, invalid field shapes, out-of-range registers/targets, type mismatches, invalid call signatures, invalid return conventions, malformed trap reasons and reachable fall-through. Validator totality and bounded resource use are separate proof/test obligations.

A validation failure is not a runtime trap. No program instruction may execute before whole-program validation succeeds.

## 8. Optimisation policy for the first implementation

The first lowering implementation should be deliberately unoptimised. Do not introduce range-check elimination, dead-code elimination, register reuse, instruction scheduling, block reordering or peephole rewrites until:

- the evaluator and conformance vectors exist;
- source-to-CCAM differential tests cover the supported subset;
- trap ordering and short-circuit behaviour are tested;
- each optimisation has a stated preservation argument and adversarial regression suite.

A later optimisation IR is permitted only as a derived representation translated back to CCAM, with validation, refinement/simulation evidence and differential tests. It must preserve values, trap kinds and order, observable effects, required resource accounting and source-location attribution.

## 9. Required compiler conformance tests

### Positive source programs

- literal return from `int main()`;
- `void main()` and void calls;
- parameter passing and nested direct calls;
- checked arithmetic within range;
- integer comparison and each derived comparison;
- local assignment and nested scopes;
- `if/else`, while, for, break and continue;
- exact left-to-right call-argument evaluation;
- short-circuit false-`&&` and true-`||` suppressing a RHS trap;
- source locations retained for each emitted instruction.

### Negative source programs

- unsupported string, aggregate, optional, enum, policy, grant or IO operation;
- unknown local or function;
- wrong argument count/type;
- wrong return type;
- invalid entry signature;
- boolean supplied to an integer operation or vice versa;
- out-of-range integer literal;
- unsupported boolean equality, bitwise, shift or wrapping operation.

### Machine-level adversarial programs

- unknown opcode and unknown type tag;
- missing/extra instruction fields and invalid null destinations;
- negative and oversized register indices;
- invalid branch targets and reachable fall-through;
- duplicate/empty function names;
- wrong call arity, argument types and return destination;
- return mismatch and malformed explicit trap reason;
- register reads before initialisation;
- exact and one-over step/call-depth limits;
- malformed large program descriptions and validator resource exhaustion.

All tests should compare the compiler-produced CCAM program with the Capstan-native evaluator's outcomes. When the native backend exists, run the same vectors against evaluator and native executable. Compare halt/trap outcome, return value, trap location, and observable output—not merely exit status.

## 10. Implementation order

1. Freeze the reviewed core/CCAM contract and exact opcode schemas.
2. Add a total, bounded CCAM structural validator.
3. Complete the Capstan-native evaluator and machine-level conformance suite.
4. Implement deterministic function/register allocation and literals/locals.
5. Add arithmetic, comparisons, direct calls and returns.
6. Add branch-based control flow and short-circuit lowering.
7. Add negative subset diagnostics and source-location mapping.
8. Establish source-to-CCAM differential tests.
9. Only then begin a minimal native backend.

This order deliberately places semantic validation and an executable oracle before native instruction selection. It is the shortest route to a trustworthy C-free vertical slice, not an attempt to implement the whole language in one pass.
