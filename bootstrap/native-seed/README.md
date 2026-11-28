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

A scalar program can declare one integer helper with one to sixteen integer
parameters. The helper supports the scalar local, assignment, loop, and
conditional return forms described above. Parameters count toward its 16
stack slots and may be read or assigned within the helper. The helper and parameter names
begin with underscores. The entry evaluates the matching number of checked argument
expressions left to right, then returns the helper result. The caller and
helper share a 256-operator compilation budget. The native call uses the System V
AMD64 integer argument registers for the first six values and passes the remaining
arguments on the aligned stack. The helper spills
each argument into a distinct stack slot and returns the value in RAX.

## Record fixture profile

The seed can admit up to 32 ordinary struct layouts, each with up to 32
distinct fields. It recognizes `int`, `bool`, `string`, and self-recursive
`List<ThisLayout>` field declarations, as well as optional references to a previously declared
layout. Optional references accept the empty `none` initializer. String initializers accept printable ASCII and the seven single-byte
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

A separate record profile admits an integer helper with one record parameter
named `item`. The helper returns one integer field. The caller constructs the
record and passes its stack address as an internal argument. The seed checks
that the caller's layout matches the parameter layout and that the selected
field has integer type. The helper can perform up to 32 integer field
assignments or checked `+=` updates before returning. Overflow branches
before the field store. The helper cannot return the reference.

A caller-constructed record can also hold an empty `List<int>` with
capacity for 16 integers in separate stack backing. Its helper can append
values and return the length or a checked indexed element. The list length
is published after its new element is stored. A full list or an invalid
index exits with status 75. A caller-constructed self-recursive record list uses the same backing. A
helper can append its own record parameter `item`, read the list length, or
read an integer field through an indexed reference. A helper may receive a
second parameter named `peer` of the same layout, separately constructed
in the caller. It can append either parameter to the list in `item`. It can
also append a
reference read from an indexed element of another field of the same list
type, including the destination list itself. The source index is checked
before the destination is changed. The reference aliases
the caller-owned record and cannot escape. A helper may finish with `if (let child = item.list.pop()) { return child.field; }
return fallback;`. It removes the most recently appended reference, clears its
slot, and reads an integer field on the nonempty path. Empty lists return
the fallback without reading any element. A helper can also discard the
result with an `item.list.pop();` statement. Both forms share the same
length update and slot clearing. A record helper can include one
`while (item.list.len() > 0)` loop containing the supported field and
list statements. The emitted loop rereads the length and spends from a
one-million-iteration budget only when entering the body. Within the loop,
a local named `node` can bind the last record reference using the same
list for both indexing and length. The helper may read an integer field
through that local for an assignment, including after popping the list slot.
The helper can also append `node.list[index]` to a list on `item` after
checking the source index and the destination capacity. The local remains
scoped to the loop body. A bounded inner `for` loop may stream all
references from a saved node’s child list to a list on `item`. It reloads
the source length and checks destination capacity on each iteration. An `if (item.field >= limit)
{ return value; }` statement can exit early from the helper. The field
is checked as an integer and the limit and result may be integer literals
or constants. Record-returning helpers still
produce only immutable empty self-recursive lists.

## Toolchain and trust boundary

Assembly is a candidate alternative to the proposed Rust seed. GNU Binutils is available in the local environment, and the seed's static linker inputs consist of one object assembled from `seed.S`. This keeps the seed independent of Capstan's existing compiler, generated C, Python and libc. The tradeoff is a Linux x86-64-specific parser and ELF emitter that require assembly review. The assembler, linker, kernel and CPU remain trusted for this experiment. This choice has not been accepted as the programme's S0 toolchain.

Run `bash bootstrap/native-seed/test.sh` on Linux x86-64. The local audit used GNU assembler and linker 2.44. Two builds in one environment produced identical stripped seed binaries with SHA-256 `afe373779dbae2d1ce5433d02f2b4801ba09c5335c894387724a183aa2875cad`. The test checks for absence of dynamic loading headers, runs the seed and emitted programs with empty tool paths, compares repeat outputs, and exercises signed extrema, input length boundaries and malformed source. This is same-environment evidence.

The candidate does not yet produce S1, consume a source manifest, compile the checked compiler workload, or establish canonical CCAM outcome correspondence. S2 compiler-on-compiler equivalence and S3 production dependency and diverse-seed evidence are still pending.

The record helper can declare one local `List<Layout> pending` before its
loop, with independent stack backing provided by the caller. The same
bounded append, discard-pop, length-test, and last-element checks apply.
The inner child loop can append to this local worklist. The list is visible
only in the helper, and its references remain tied to the caller frame.
A helper can alternatively receive a second parameter `List<Layout> roots`
from a matching list field of `item`. It can seed `pending` by appending
the indexed roots in order, checking capacity at each append. A record
helper may instead return Boolean literals, including from an early budget
guard. Such a guard can set a declared Boolean field before it returns.
In that profile `main` branches on the helper’s result. The root list may
have a different declared element layout from the first record parameter.
The caller can pass an empty typed list or a singleton list containing a
separately constructed `Node peer`. The seed resolves worklist fields
against the element layout and rejects appending the budget record to the
node worklist. The fixture uses the actual `CompileBudget` and `Node` layouts
and compiles the unmodified `charge_ast_nodes` function extracted from
`compiler/ast.cap`. It exercises success and exhaustion with one root. The
fixture omits the preceding record-returning helper because this seed
profile admits one callable helper per source stream.

## Native AST traversal primitive

`charge-ast-nodes.S` implements the worklist algorithm for a runtime-owned
node table, root array, and scratch buffer. It charges nodes once per visit,
checks IDs and scratch capacity, and marks exhaustion at the source
compiler’s 150,000-node limit. The runtime owns pointer provenance and
backing extents. The standalone test runs with an empty tool path and covers
shared children, a cycle at the budget boundary, invalid roots, oversized
child counts, and empty roots at the limit. Source lowering does not yet call
this primitive.

`bash bootstrap/native-seed/check-charge-ast-nodes.sh` compares the
native return flag, charged count, and exhaustion flag directly against
the actual `charge_ast_nodes` in `compiler/ast.cap` for the shared-child,
cycle, and empty-root cases. The comparison builds the reference using
the existing C-hosted Capstan compiler. The freestanding native test
still runs independently with an empty tool path.

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
