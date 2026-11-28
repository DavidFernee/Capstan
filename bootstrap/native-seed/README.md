# Independent native seed candidate

This Linux x86-64 seed accepts a bounded Capstan source fragment on fd 0 and writes a freestanding ELF on fd 1. It is bootstrap research. S0 acceptance requires the complete source subset and manifest needed to build a native S1 Capstan compiler.

## Profile

The input has the form `int main() { return -42; }`. ASCII whitespace and comments are accepted before the program, around punctuation, and after the closing brace. At least one whitespace byte or comment must separate `int` from `main` and `return` from the literal. Comments use `//` through the next line feed or end of input, or non-nesting `/* ... */`. Comment content is limited to printable ASCII and ASCII whitespace. Decimal integer literals accept an adjacent minus and must fit in a signed 64-bit value. Hexadecimal literals use `0x` with up to 16 significant digits and preserve the full signed 64-bit bit pattern. The current grammar excludes unary negation of a hexadecimal literal. Single-quoted printable ASCII characters and the same seven escapes used by strings produce integer byte values. Up to 256 top-level `const int NAME = literal;` declarations may precede `main`. Names begin with `A`–`Z` or underscore, continue with those characters or digits, and are at most 63 bytes. Duplicate declarations and unresolved references are rejected. A declared constant may replace a literal operand in the return expression. The return expression admits up to 256 binary `+` or `-` operations on such literals, evaluated left to right. The emitted ELF contains one checked machine operation per operator. A negative right operand after binary subtraction requires intervening trivia. Input larger than 1 MiB (1,048,576 bytes) exits with status 3 before writing output. Unsupported syntax, invalid byte sequences and out-of-range literals exit with status 2 before writing output. An input/output syscall failure exits with status 1. Callers discard output on any nonzero status.

The emitted static ELF writes one little-endian signed 64-bit integer to inherited fd 3 and exits successfully only after writing all eight bytes. The emitted arithmetic checks signed overflow at runtime and exits with status 70 without writing a result if it occurs. The seed and target use inherited descriptors and Linux syscalls. The seed performs no path lookup or child process launch.

## Conditional fixture profile

A scalar entry can also contain one `if (left < right) { return yes; } return no;`
or the same form with `<=`, `>`, `>=`, `==`, or `!=`. Each comparison operand is a supported literal or a declared integer
constant. Both return expressions can use checked addition and subtraction,
with a shared limit of 256 operators. The emitted program compares operands
at runtime using signed ordering and evaluates only the selected expression.

## Local integer fixture profile

A scalar entry can declare up to 16 integer locals whose names begin with
an underscore. It can make up to 32 assignments before the optional loop,
then return an arithmetic expression. Each local has its own stack slot.
An optional `while (local < bound)` may follow the assignments. Its body
contains between one and 32 checked assignments to declared locals. The bound
may be a literal, an integer constant, or a local reread before each iteration. The loop checks the condition before spending an iteration
and exits with status 73 if the body would execute more than 1,000,000 times.
The return may be conditional and can read the local on either side of
the comparison and in either return expression. The initializer, assignments,
loop body, and return paths share a 256-operator compilation budget.
Assignment evaluates its right-hand side before updating the
stack slot that holds the local. A local becomes visible after its initializer and
must have a distinct name from the declared integer constants.

## Parameterized integer helper profile

A scalar program can declare one integer helper with one to six integer
parameters and a checked return expression. The helper and parameter names
begin with underscores. The entry passes the matching number of literals or
constants, and returns the helper result. The native call uses the System V
AMD64 integer argument registers in declaration order. The helper spills
each argument into a distinct stack slot and returns the value in RAX.

## Record fixture profile

The seed can admit up to 32 ordinary struct layouts, each with up to 32
distinct fields. It recognizes `int`, `bool`, `string`, and self-recursive
`List<ThisLayout>` field declarations, as well as optional references to a previously declared
layout. Optional reference construction remains outside the seed subset. String initializers accept printable ASCII and the seven single-byte
escapes supported by the existing lexer. The decoded value is limited to
63 bytes, including embedded NUL bytes. List initializers accept
an empty `new List<ThisLayout>()`. Those fields can return their length via
`.len()`. String fields also support `.at(index)` with a signed integer
literal or declared integer constant. The emitted bounds check precedes the
byte load. Negative indices and indices at or beyond the byte length exit with
status 75 and write no result. The seed also accepts
`.slice(start, end).len()` on string fields. Both endpoints may be literals
or declared constants. The emitted code checks `0 <= start <= end <= length`
and returns the difference directly. A slice can also be followed by
`.at(index)`. The emitted code checks the slice and then the index relative
to that slice before reading the original storage. A failed check exits
with status 75.
The emitter stores the length and immutable bytes in the ELF and
keeps an internal reference in the record slot. The entry must construct one local
named `item` with every field initialized in declaration order, then return
one of its integer fields. The construction may instead be in one zero-argument
helper declared between the layout and `main`. Integer constants can also
appear between the layout, helper, and `main`. In that form, `main` reserves
return storage and calls the helper, which writes the result into the caller
frame. An integer initializer can be a literal or a
declared integer constant. A boolean initializer must be `true` or `false`.
The emitted executable stores the fields in separate eight-byte stack
slots and loads the return value from the slot selected during compilation.

## Toolchain and trust boundary

Assembly is a candidate alternative to the proposed Rust seed. GNU Binutils is available in the local environment, and the seed's static linker inputs consist of one object assembled from `seed.S`. This keeps the seed independent of Capstan's existing compiler, generated C, Python and libc. The tradeoff is a Linux x86-64-specific parser and ELF emitter that require assembly review. The assembler, linker, kernel and CPU remain trusted for this experiment. This choice has not been accepted as the programme's S0 toolchain.

Run `bash bootstrap/native-seed/test.sh` on Linux x86-64. The local audit used GNU assembler and linker 2.44. Two builds in one environment produced identical stripped seed binaries with SHA-256 `f58b5920367734955f7a556da00b0689d7bbe1fd2a0a22a573e7c9548b98ee36`. The test checks for absence of dynamic loading headers, runs the seed and emitted programs with empty tool paths, compares repeat outputs, and exercises signed extrema, input length boundaries and malformed source. This is same-environment evidence.

The candidate does not yet produce S1, consume a source manifest, compile the checked compiler workload, or establish canonical CCAM outcome correspondence. S2 compiler-on-compiler equivalence and S3 production dependency and diverse-seed evidence are still pending.

## Pinned workload probe

Run `bash bootstrap/native-seed/check-compiler-workload.sh` to verify the
ordered hashes of the seven existing compiler modules, build the seed and
feed it the complete source bytes. The manifest pins the current compiler
workload for repeatable testing. It does not define the eventual S1 profile
or serve as an input format accepted by the seed.

The ordered stream was 220,188 bytes in the local run. It passed the new
1 MiB size check and was rejected by the seed source profile with status 2.
A separate fixture using the exact initial constant declarations from
`compiler/ast.cap` returned `MAX_TOTAL_AST_NODES` (150,000). A second fixture uses the actual `CompileBudget` struct and returns its
`ast_nodes` field at runtime. The fixture suite also compiles the actual `new_compile_budget()` helper
and executes a native call to it. That fixture includes the real `TY_*`
integer constants following the helper, and the complete `struct Type` layout, including its string and recursive
list field declarations. This fixture constructs and reads `CompileBudget`.
Separate fixtures construct `Type` with a short string and an empty list
and read both lengths through a native helper return. General strings and
mutable lists are outside the profile. The seed reports the parser cursor on source rejection. With the opening
`Node` layout now admitted, the pinned workload stops at the next helper
declaration, `charge_ast_nodes` in `compiler/ast.cap:117`. No S1 artifact was
produced. The larger bounded buffer is a local seed limit, distinct from
the production compiler's source and aggregate import limits.
