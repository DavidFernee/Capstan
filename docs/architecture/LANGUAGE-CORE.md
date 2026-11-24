# Capstan Core Language Semantics

**Status:** normative proposal for review  
**Version:** Core v0.1  
**Owner:** Language Semantics workstream  
**Scope:** the scalar, control-flow and direct-call subset represented by CCAM v0.1

This document defines the source-independent semantic contract for the initial Capstan core. It is intended to be adopted by the CCAM specification and implemented by the Capstan-native evaluator. It does not claim to specify all of Capstan v0.1: heap objects, strings, collections, taint, secrets, grants, IO, concurrency and cryptographic services require later semantic extensions.

## 1. Conformance vocabulary

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

A conforming implementation preserves the observable behaviour defined here for every well-typed, structurally valid core program. An implementation MUST NOT use host-language undefined behaviour, unspecified evaluation order, integer overflow, or invalid memory access to implement a Capstan operation.

A compile-time rejection is distinct from a runtime trap. A runtime trap is an observable terminal outcome and MUST occur before any later instruction or effect.

## 2. Core values and types

The initial core value domain is the disjoint sum:

`Value = Int64(n) | Bool(b)`

where `-2^63 <= n <= 2^63-1` and `b ∈ {false, true}`.

The corresponding types are `int` and `bool`. They are disjoint: a boolean is never an integer, and no implicit conversion exists between them.

The source-level core subset consists of:
- integer and boolean literals;
- local variable reads and initialising declarations;
- assignment to local variables;
- integer arithmetic (`+`, `-`, `*`, `/`, `%`) and integer comparisons (`==`, `!=`, `<`, `<=`, `>`, `>=`);
- boolean negation (`!`), short-circuit conjunction/disjunction (`&&`, `||`), and boolean equality/inequality (`==`, `!=`);
- conditional and unconditional control flow;
- direct function calls and returns;
- explicit traps in the machine-level representation.

The source compiler MUST reject a core expression whose operands or result do not match the operation's declared types. The machine MUST independently validate the instruction program's structural type constraints.


### 2.1 Core typing judgement

Let `Σ` be the complete function-signature environment, where
`Σ(f) = (T1, ..., Tn) -> R`, each parameter type `Ti` is `int` or `bool`,
and the result type `R` is `int`, `bool` or `void`. Let `Γ` map the
currently in-scope, initialised local names to `int` or `bool`. Function
signatures are collected before checking bodies, so direct recursion is
well-defined. Parameter names and local names must be unique within their
scope. A local enters `Γ` only after its initialiser has type-checked; this
matches the source rule that every variable is initialised at declaration.

The judgement `Γ;Σ ⊢ e : T` is syntax-directed and has exactly these core
operator signatures:

| Expression form | Required operand types | Result type |
|---|---|---|
| integer literal | signed-64 representable literal | `int` |
| `true`, `false` | none | `bool` |
| local `x` | `x:T ∈ Γ` | `T` |
| `+ - * / %` | `int, int` | `int` |
| `< <= > >=` | `int, int` | `bool` |
| `== !=` | two operands of the same type, either `int` or `bool` | `bool` |
| `!` | `bool` | `bool` |
| `&& ||` | `bool, bool` | `bool` |
| `f(e1, ..., en)` | `Σ(f)=(T1,...,Tn)->R` and each `Γ;Σ ⊢ ei:Ti` | `R`, provided `R != void` |

A void-returning call is permitted only as a statement; it is not an expression
and cannot be used as an operand, initialiser, argument value or return value.
No implicit conversions, integer/boolean interchange, or coercions from
`void` exist.

The statement judgement is checked against the enclosing function result type:

| Statement form | Typing requirement |
|---|---|
| `int x = e;` / `bool x = e;` | `e` has exactly the declared type; then add `x:T` to the block environment. |
| `x = e;` | `x:T ∈ Γ` and `e:T`. |
| scalar `x op= e;` | `x:int ∈ Γ` and `e:int`; `op` is one of `+ - * / %`. |
| `if (e) s1 [else s2]` | `e:bool`; check each present branch under the incoming environment. |
| `while (e) s` | `e:bool`; check `e` as `bool` and the body under the incoming environment. |
| `for (init; cond; step) s` | check `init` in a loop-local scope; `cond:bool`; check `step` and the body in that scope; loop-local declarations do not escape. |
| `f(args);` | `f` exists in `Σ`; argument count and types match its signature. A non-void result may be discarded. |
| `return e;` | the enclosing function returns `T != void` and `e:T`. |
| `return;` | the enclosing function returns `void`. |
| `break;`, `continue;` | occur only within a loop. |

Block-local declarations do not escape their block. A `for` initializer's
scope includes its condition, body and step but ends after the loop. Every
variable read must refer to a name in `Γ`; because declarations require
initialisers, an uninitialised local is a source typing error. A non-void function MUST have no reachable normal-completion path that falls
through without returning a value of its declared type. A path may instead
terminate in a defined trap or diverge in a non-terminating loop. A void
function may return void or fall through to its implicit void completion. The CCAM register model is more
defensive: non-parameter registers start uninitialised and a read of one traps,
so malformed or incorrectly lowered programs cannot turn this source guarantee
into an unchecked host-language read.

## 3. Evaluation and sequencing

### 3.1 General rule

Evaluation is strictly left-to-right. Whenever an expression contains multiple subexpressions, each is evaluated completely, in source order, before the next begins. A trap during one subexpression prevents evaluation of every later subexpression.

Function-call arguments are evaluated from left to right before the callee begins. The callee observes the resulting argument values, not unevaluated caller expressions.

### 3.2 Boolean operators

`&&` and `||` are short-circuiting:
- `a && b`: evaluate `a`; if false, return false without evaluating `b`; otherwise evaluate and return `b`.
- `a || b`: evaluate `a`; if true, return true without evaluating `b`; otherwise evaluate and return `b`.

The left operand is always evaluated first. The right operand is evaluated only when required by the rule above.

### 3.3 Assignment

For simple local assignment `x = e`, evaluate `e` completely, then replace the value of `x`.

Compound assignment is defined by sequencing, not by textual substitution into an implementation-language expression. For an assignable location `L` and operation `op`, `L op= e` means:
1. evaluate and retain the location designator exactly once; an indexed location retains the container identity and evaluated index, not an identity for the element currently stored there;
2. read and retain the old value at that location;
3. evaluate `e`;
4. apply `op` to the retained old value and the new RHS value;
5. establish that the retained location remains valid in the post-RHS state (including object liveness and current logical bounds), by a dynamic recheck or a sound proof that the RHS cannot invalidate it; then write the result.

A trap in steps 1–4 prevents the write. After the RHS, the write targets the current slot at the retained index if that index remains within the container's current logical length; an insertion/removal before that index may therefore change which element occupies the slot. If the RHS invalidates the location—for example, by shrinking the list so the retained index is no longer valid—the write traps and performs no store. A bounds proof established before the RHS alone does not justify an unchecked post-RHS store. No step may be reordered across another observable step. The aggregate transition is reserved until aggregate locations are added to the machine, but every future aggregate extension MUST preserve this sequencing and revalidation rule.

## 4. Integer semantics

Integers are signed 64-bit two's-complement values. Let `MIN = -2^63` and `MAX = 2^63 - 1`.

For checked addition, subtraction and multiplication, calculate the mathematical integer result first. If it is outside [MIN, MAX], execution traps with `integer_overflow`; otherwise the exact result is returned. Unary integer negation is defined as checked subtraction from zero: `-a` returns the mathematical `0 - a` when representable and traps with `integer_overflow` for `a == MIN`.

Division and remainder use truncation toward zero. For nonzero divisor `b`, define the mathematical quotient `q = trunc(a / b)` and remainder `r = a - q*b`. Therefore `|r| < |b|`, and a nonzero remainder has the sign of `a`.

- If `b == 0`, division and remainder trap with `division_by_zero`.
- `MIN / -1` traps with `integer_overflow`, because the quotient is not representable as `int`.
- `MIN % -1` returns `0`. The mathematical remainder is representable even though the corresponding quotient is not. Implementations MUST special-case this pair before using a host operation that could overflow or be undefined.

This last rule preserves the existing Capstan runtime behaviour. It corrects the conflicting CCAM v0.1 draft, which currently specifies an overflow trap for both division and remainder. The correction MUST be reflected in CCAM conformance vectors and in every evaluator/backend. A future incompatible change requires an explicit language/machine version change.

Bitwise operations, shifts, wrapping arithmetic, strings and aggregate operations are outside this minimal scalar core and must be specified in their own extension clauses before being admitted to the machine.

## 5. Function and control-flow semantics

A function invocation creates a fresh frame. Its parameter registers are initialised from the already-evaluated argument values. Other local registers begin uninitialised. A function cannot read an uninitialised local.

A call transfers control to the callee's first instruction only after the call instruction has passed structural validation and all argument values have been read and checked. A non-void return supplies exactly one value of the declared return type. A void return supplies no value. Returning from the entry function halts the machine.

The Capstan source entry point remains `int main()` or `void main()`; a CCAM program used as a complete source-program image MUST have a zero-argument entry function returning `int` or `void`. Internal CCAM functions MAY return `bool` as well as `int` or `void`.


### 5.1 Structured control flow

- An `if` evaluates its boolean condition once, then executes exactly the selected branch (or no branch when false and no `else` is present).
- A `while` evaluates its condition before each iteration. A false result exits; a true result executes the body and then reevaluates the condition. `continue` resumes at the condition; `break` exits the innermost enclosing loop.
- A `for (init; cond; step)` executes `init` once, then repeats: evaluate `cond`; if false, exit; otherwise execute the body; on normal body completion or `continue`, execute `step`; then reevaluate `cond`. `break` exits without executing `step`.
- A `return` terminates the current function immediately. No later statement in that invocation is evaluated. A successful call resumes the caller only after the callee has returned; a trap terminates the entire machine execution.

These rules are source-level sequencing requirements. Lowering may replace structured control flow with branches and jumps, but MUST preserve the condition, body, step, break and continue order exactly.

All branches select a validated instruction index within the current function. Starting at instruction 0, every reachable nonterminal instruction MUST have an in-function successor; a reachable infinite loop is permitted. A function MUST NOT have a reachable path that falls through beyond its instruction sequence. Unreachable instructions are still structurally validated.

## 6. Structural validation and dynamic traps

The machine MUST validate a complete program before executing its first instruction. Structural validation MUST reject:
- duplicate or empty function names;
- a missing or invalid entry function;
- unknown type tags or invalid return types;
- parameter counts larger than the register vector;
- invalid register indices, instruction operands or branch targets;
- statically mismatched operand, destination, parameter or return types;
- calls to unknown functions, wrong arity, or incompatible return destinations;
- a return instruction incompatible with its enclosing function;
- any control-flow path reachable from instruction 0 that can fall off the end of a function; unreachable instructions still receive schema/index/type validation but do not independently cause a fall-through error;
- malformed explicit trap reason strings (the reason is 1–64 ASCII characters matching `[a-z][a-z0-9_]{0,63}`).

Structural validation MUST be deterministic and MUST NOT execute program instructions.

Dynamic checks remain mandatory for properties depending on machine state, including register initialisation, configured step limits and call-depth limits. A dynamic failure produces a defined trap outcome. Structural invalidity is a validation error, not a runtime trap.

Where an instruction reads multiple operands, it reads them in the specified left-to-right order. If a dynamic read check fails, later operands are not read.

## 7. Machine limits and accounting

The initial CCAM machine has two deterministic limits: maximum instruction steps and maximum call depth. The configuration requires `maxDepth` in `1..2^63-1` and `maxSteps` in `0..2^63-1`. They are execution-configuration parameters, not fields in the CCAM program JSON; any transport must preserve exact integer values (and, if JSON is used, reject booleans, fractions and out-of-range values).

- The entry frame counts as depth 1.
- A `call` instruction consumes one instruction step. It traps with `call_depth_exceeded` rather than pushing a frame if the push would exceed the configured maximum.
- A `ret` or `ret_void` instruction consumes one instruction step.
- Every other executed instruction consumes exactly one instruction step, including an explicit `trap`.
- A step limit of N permits at most N instructions to execute. If the machine has already executed N instructions and another instruction is required, it traps with `step_limit_exceeded` before executing that instruction.
- Structural validation is outside the execution-step budget. Implementations SHOULD expose a separate validation/resource limit for untrusted program descriptions; that limit is not part of the v0.1 execution semantics unless configured as an explicit machine parameter.

For a fixed validated program, arguments and machine limits, execution has one deterministic transition sequence and one terminal outcome.

## 8. Trap outcomes

A dynamic trap is terminal. The observable machine result is:

`Halt(value)`, `HaltVoid`, or `Trap(code, function, pc, detail)`. `detail` is absent for ordinary machine traps and contains the validated reason string only for `explicit_trap`.

The initial stable trap codes are:
- `integer_overflow`
- `division_by_zero`
- `uninitialised_register`
- `invalid_register` (defence-in-depth; structurally invalid indices should be rejected before execution)
- `register_type_mismatch` (defence-in-depth; structurally invalid typed programs should be rejected before execution)
- `step_limit_exceeded`
- `call_depth_exceeded`
- `explicit_trap` (with a separately validated application reason matching `[a-z][a-z0-9_]{0,63}`)

The machine MUST NOT expose host exceptions, signals, undefined behaviour or process crashes as substitutes for these outcomes. A malformed program description is reported as a validation failure and is not converted into a dynamic trap.

## 9. Required conformance properties

Every implementation of this core MUST test:
1. all checked arithmetic boundaries, including `MIN / -1` and `MIN % -1`;
2. division and remainder by zero;
3. operand-read and call-argument order;
4. short-circuit suppression of a trapping or effectful RHS;
5. uninitialised register reads;
6. entry and nested call/return behaviour;
7. step and call-depth boundaries, including exact-limit success and one-over-limit traps;
8. each structural validation rejection listed above;
9. identical outcomes across the Capstan evaluator, any proof model, and every native backend.

## 10. Extension discipline

A feature outside this core MUST NOT be treated as having machine semantics merely because the source compiler currently accepts it. Each extension must define:
- its value and type representation;
- its evaluation and effect order;
- its dynamic checks and trap outcomes;
- resource bounds and accounting;
- its interaction with existing safety invariants;
- executable conformance vectors;
- proof obligations and a refinement relation to lower-level execution.

Heap references, aliasing, object identity, collection mutation, garbage collection, taint, secrets, grants, IO and concurrency are explicitly deferred to their own semantic extensions.
