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
- unary and binary scalar operations;
- conditional and unconditional control flow;
- direct function calls and returns;
- explicit traps in the machine-level representation.

The source compiler MUST reject a core expression whose operands or result do not match the operation's declared types. The machine MUST independently validate the instruction program's structural type constraints.

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
1. evaluate and retain the location designator exactly once;
2. read and retain the old value at that location;
3. evaluate `e`;
4. apply `op` to the retained old value and the new RHS value;
5. write the result to the retained location.

A trap in steps 1–4 prevents the write. No step may be reordered across another observable step. The aggregate form of this rule is reserved until aggregate locations are added to the machine, but every future aggregate extension MUST preserve this sequencing.

## 4. Integer semantics

Integers are signed 64-bit two's-complement values. Let `MIN = -2^63` and `MAX = 2^63 - 1`.

For checked addition, subtraction and multiplication, calculate the mathematical integer result first. If it is outside [MIN, MAX], execution traps with `integer_overflow`; otherwise the exact result is returned.

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

All branches select a validated instruction index within the current function. A function MUST NOT fall through beyond its instruction sequence.

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
- any control-flow path that can fall off the end of a function;
- malformed explicit trap codes.

Structural validation MUST be deterministic and MUST NOT execute program instructions.

Dynamic checks remain mandatory for properties depending on machine state, including register initialisation, configured step limits and call-depth limits. A dynamic failure produces a defined trap outcome. Structural invalidity is a validation error, not a runtime trap.

Where an instruction reads multiple operands, it reads them in the specified left-to-right order. If a dynamic read check fails, later operands are not read.

## 7. Machine limits and accounting

The initial CCAM machine has two deterministic limits: maximum instruction steps and maximum call depth.

- The entry frame counts as depth 1.
- A `call` instruction consumes one instruction step. It traps with `call_depth_exceeded` rather than pushing a frame if the push would exceed the configured maximum.
- A `ret` or `ret_void` instruction consumes one instruction step.
- Every other executed instruction consumes exactly one instruction step, including an explicit `trap`.
- A step limit of N permits at most N instructions to execute. If the machine has already executed N instructions and another instruction is required, it traps with `step_limit_exceeded` before executing that instruction.
- Structural validation is outside the execution-step budget. Implementations SHOULD expose a separate validation/resource limit for untrusted program descriptions; that limit is not part of the v0.1 execution semantics unless configured as an explicit machine parameter.

For a fixed validated program, arguments and machine limits, execution has one deterministic transition sequence and one terminal outcome.

## 8. Trap outcomes

A dynamic trap is terminal. The observable machine result is:

`Halt(value)` or `Trap(code, function, pc)`.

The initial stable trap codes are:
- `integer_overflow`
- `division_by_zero`
- `uninitialised_register`
- `register_type_mismatch` (defence-in-depth; structurally invalid typed programs should be rejected before execution)
- `step_limit_exceeded`
- `call_depth_exceeded`
- `explicit_trap` (with a separately validated application reason)

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
