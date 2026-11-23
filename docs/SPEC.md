# Capstan v0.1 language reference

## Lexical structure

- Comments: `// line` and `/* block */`.
- Identifiers: `[A-Za-z_][A-Za-z0-9_]*`.
- Integer literals: decimal, must fit in a signed 64-bit integer (otherwise a compile error);
  or hexadecimal, `0x` followed by up to 16 significant hex digits, which use all 64 bits as in
  Java (`0xFFFFFFFFFFFFFFFF` is `-1`, `0x8000000000000000` is the smallest int).
- Character literals: `'a'`, `'\n'`, `'\''`; they are `int` values 0–255.
- String literals: `"..."` with escapes `\n \t \r \0 \\ \" \'`. Strings are byte sequences.
- Keywords: `struct const if else while for return break continue true false none new let protected policy public test authorize assert_denied assert_granted`.

## Types

| Type | Meaning |
|---|---|
| `int` | signed 64-bit integer; all arithmetic is overflow-checked |
| `bool` | `true` / `false` |
| `string` | immutable, trusted byte string |
| `Tainted` | immutable byte string from an untrusted source |
| `Secret` | a credential; cannot be printed, concatenated, compared with `==` or read |
| `Html` | text escaped for HTML (from `escape_html()`); joins only with `Html` and trusted `string`, never passes as a plain `string` |
| `LogText` | text escaped for logs and terminals (from `escape_log()`): printable ASCII and valid UTF-8 text are kept; control bytes, invalid UTF-8, C1 controls, bidirectional controls, line and paragraph separators and the byte-order mark become `\xNN`. Same rules as `Html` |
| `S` | a `struct` (reference type) |
| `List<T>` | growable, bounds-checked list |
| `Map<T>` | map from `string` keys to `T`, iterated in insertion order |
| `Grant<P>` | proof that policy `P` approved a request |
| `T?` | optional: a `T` or `none` |
| `void` | function return type only |

There is no null. Only `T?` can hold `none`, and an optional must be unwrapped with
`if (let x = value) { ... } else { ... }` before use. A `T` converts implicitly to `T?`.
List and map elements cannot be optional, and optionals cannot nest.

## Declarations

```java
struct Point { int x; int y; Point? next; }
const int LIMIT = 100;
int add(int a, int b) { return a + b; }
policy CanEdit(User u, Doc d) { return u.id == d.owner; }
public policy Anyone(User u) { return true; }
protected(CanEdit) void edit(Grant<CanEdit> g, Doc d) { ... }
test "owners can edit" { assert_granted CanEdit(owner, doc); }
```

- `sensitive struct Record { ... }`: fields of a sensitive struct can only be read or changed
  in protected functions, policies and tests, so every path to the data needs a grant (CWE-862).
  Values can be created and passed around anywhere.
- `enum Shape { Circle(int r), Empty }`; values are written `Shape.Circle(3)` and `Shape.Empty`.
  `match (s) { case Circle(r) { ... } case Empty { ... } }` must handle every variant or end with
  `else { ... }` (CWE-478). Enums without values can be compared with `==`.
- Methods are declared inside a struct and called as `value.method(args)`; the receiver is available as `self`.
  Methods get no extra access: on a sensitive struct they still need a grant to read fields.
- `import "lib/util.cap";` loads a file once, relative to the importing file; no `..` or absolute paths.
- Every variable must be initialised where it is declared.
- Every field must be given a value in `new S{field: value, ...}`.
- A variable may not shadow a variable or constant from an enclosing scope.
- A non-void function must return on every path.
- The program entry point is `int main()` or `void main()`.

## Statements

`T name = expr;`, `target = expr;`, `target += expr;`, `target -= expr;`, `if (cond) {...} else {...}`,
`if (let x = opt) {...} else {...}`, `while (cond) {...}`, `for (init; cond; step) {...}`,
`return expr;`, `break;`, `continue;`, and expression statements (calls only).
Braces are required around every body.

## Expressions

Precedence from low to high: `||`, `&&`, `== !=`, `< <= > >=`, `+ -`, `* / %`, unary `! - ~`,
then postfix `.field`, `.method(args)`, `[index]`.

Bitwise operators `&`, `|`, `^` and shifts `<<`, `>>`, `>>>` **may not be combined with any other
operator without parentheses** (CWE-783): `(x & 1) == 0`, never `x & 1 == 0`, which C reads as
`x & (1 == 0)`. A chain of one of `&`, `|`, `^` needs none (`a | b | c`); shifts are always grouped
explicitly. Their meaning therefore never depends on precedence.

- `&`, `|`, `^` and `~` work on `int` as 64-bit two's complement. On `bool` they are an error
  (CWE-480): use `&&`, `||`, `!=` and `!`.
- `a << n` requires `0 <= n <= 63` (CWE-1335) and is checked like multiplication: if a bit would
  be lost, the program stops (CWE-190). `a >> n` shifts right keeping the sign; `a >>> n` shifts
  right filling with zeros. Both require `0 <= n <= 63`. A literal count outside 0..63 is a
  compile error; a computed one stops the program.
- `wrapping_add(a, b)`, `wrapping_sub(a, b)`, `wrapping_mul(a, b)` and `wrapping_shl(a, n)` compute
  modulo 2^64, for hashing and cryptography. Ordinary `+`, `-`, `*` and `<<` stay checked.
- `>>` and `>>>` are written as adjacent `>` characters, so `Map<List<int>>` still closes two
  type arguments.

- `$"Hello {name}, {count} new"` is an interpolated string: it means `"Hello " + to_text(name) + ", " + to_text(count) + " new"`,
  so every rule for `+` applies (interpolating `Tainted` yields `Tainted`, interpolating into `Html` stays `Html`, a `Secret`
  cannot be interpolated). `int` and `bool` are converted to text; `{{` and `}}` are literal braces.
- `+` adds `int`s or concatenates strings. If either string operand is `Tainted`, the result is `Tainted`.
- `==` and `!=` compare `int`, `bool` and strings. Structs and optionals cannot be compared.
- `/` truncates toward zero. Division by zero stops the program (CWE-369).
- **Evaluation is strictly left to right**, including function arguments.

### Methods

| Receiver | Methods |
|---|---|
| `string`, `Tainted` | `len()`, `at(i)` → byte as `int`, `slice(a, b)` → same type |
| `List<T>` | `len()`, `push(v)`, indexing `xs[i]`, `xs[i] = v` |
| `Map<T>` | `get(k)` → `T?`, `set(k, v)`, `has(k)`, `keys()` → `List<string>` |

## Built-in functions

| Function | Notes |
|---|---|
| `print(s)`, `println(s)` | `string` only. `Tainted` → CWE-117, `Secret` → CWE-532 |
| `int_to_str(i)`, `char_str(c)` | |
| `args()` → `List<string>` | command-line arguments (supplied by the operator) |
| `read_file(path)` → `Tainted?`, `read_line()` → `Tainted?` | untrusted input sources. `read_file` reads to the end of the file (pipes and `/proc` files included) and gives `none` for a directory, an unreadable file, or a path containing a NUL byte (CWE-158). `read_line` gives one line without its `\n`, every byte kept (NUL included), or `none` at end of input |
| `read_bytes(n)` → `Tainted?`, `flush()` | `read_bytes` reads exactly `n` bytes of standard input (fewer only if the input ends first), every byte kept, or gives `none` at end of input; `read_bytes(0)` is `""`. `n` outside 0..2^30 stops the program (CWE-789); memory grows with the bytes read, not with `n`. `flush()` writes out everything printed so far, for programs that converse over a pipe (a language server, say) |
| `write_file(path, data)` → `bool` | data must be `string`, `Html` or `LogText`: untrusted input must be escaped or validated first; password-named data is rejected (CWE-256); ignoring the result is warning CWE-252; a path containing a NUL byte gives `false` |
| `join(list, sep)`, `exit(code)`, `assert(cond)` | |
| `validate_ident(t)` → `string?`, `validate_int(t)` → `int?` | validators: the safe ways out of `Tainted` |
| `escape_html(t)` → `Html`, `escape_log(t)` → `LogText`, `escape_c(t)` → `string` | escapers |
| `trust(t, "justification")` → `string` | explicit escape hatch; always reported as an AUDIT warning |
| `validate_path(t)` → `string?` | a relative path with no `.` or `..` segments (CWE-22) |
| `validate_range(t, min, max)` → `int?` | an integer within bounds (CWE-1284) |
| `escape_csv(t)` → `string` | one quoted CSV field, with leading `= + - @` neutralised (CWE-1236) |
| `taint(s)` → `Tainted` | marks a value as untrusted (useful in tests) |
| `wrapping_add(a, b)`, `wrapping_sub(a, b)`, `wrapping_mul(a, b)` → `int` | arithmetic modulo 2^64; never stops |
| `wrapping_shl(a, n)` → `int` | `a << n` modulo 2^64; `n` must be 0..63 (CWE-1335) |
| `sql_query("literal", params...)` | query text must be a literal; values are bound parameters |
| `run("program", args...)` | program must be a literal; no shell; arguments are passed separately; untrusted arguments must follow a literal `"--"` (CWE-88) |
| `secret_env("NAME")` → `Secret?`, `secret_eq(secret, other)` | constant-time comparison |
| `hash(x)`, `hash_verify(x, h)` | integrity hashing; output tagged `cap1$sha256$…`; not for passwords (CWE-916) |
| `hash_password(p)`, `verify_password(p, h)`, `needs_rehash(h)` | PBKDF2-SHA256 with 600,000 iterations; output carries its algorithm and cost |

In v0.1, `sql_query` and `run` are demonstration sinks: they print what they would execute.

## Authorisation

- `policy P(params) { ... }` returns `bool` and must return on every path.
- `authorize P(args)` evaluates the policy and returns `Grant<P>?`.
- A `Grant<P>` can only come from `authorize`. It can't be constructed, stored in
  a field, collection or constant, or returned from a function.
- `protected(P)` functions must take `Grant<P>` as their first parameter. Only
  protected functions may take grants, and calling one without a grant is CWE-862.
- A grant is bound to the struct objects it was issued for. If a protected function
  is passed a different object of a type the policy checked, the program stops with CWE-639.
- Policy analysis:
  - `return true;` without `public` is an error (CWE-862).
  - `Tainted` parameters are an error (CWE-807).
  - An ignored parameter is a warning (CWE-639).
  - Comparing against a string literal is a warning (CAP-ROLE).
- Every non-public policy needs a test containing `assert_denied P(...)`. Without one it is a
  warning, and an error under `--release`.

## Memory and limits

- Memory is managed by a garbage collector; there is no way to free memory manually.
  `CAPSTAN_GC_STATS=1` prints collector statistics on exit; `CAPSTAN_GC_STRESS=N` collects every N allocations (for testing).
- Runaway recursion stops the program with CWE-674 rather than crashing.
- The heap is limited by `CAPSTAN_MAX_HEAP` (bytes, with K/M/G suffixes; default three quarters of
  physical memory). Exceeding it stops the program with CWE-400.
- Secrets are kept in their own memory and zeroed when collected (CWE-244).
- String literals in known credential formats (payment, cloud, source-hosting and chat tokens, private keys) are rejected (CWE-798).
- Source nesting (expressions, statements, operator chains) is limited to 1,000 levels;
  deeper input is a compile error (CWE-674).
- After a syntax error the compiler resumes at the next statement or declaration, so one run
  reports every independent syntax error; it stops after 50 (CWE-400). Nesting that is too deep
  ends parsing at once.
- A program stopped by a runtime check exits with code 101.
- The compiler may leave out a check that it proves can never fail (range analysis); this
  never changes what a program does. `--keep-checks` keeps every check.

## Warnings

Warnings are errors under `--strict`. Names starting with `_` are exempt from the unused-variable warning.

| Code | Warning |
|---|---|
| CWE-561 | unreachable statement |
| CWE-563 | local variable never read |
| CWE-570 / CWE-571 | `if` condition is the literal `false` / `true` |
| CWE-1164 | assignment of a value to itself |
| CWE-390 | empty `else` branch (a failure case silently ignored) |
| CWE-546 | comment mentioning a backdoor, or a TODO/FIXME about security |
| CWE-547 | security decision on a magic number (`role == 7`) |
| CWE-617 | `assert()` outside a test |
| CWE-783 | `&&` inside `||` without parentheses |
| CWE-489 | (error in `--release`) a debug switch constant left on |
| CWE-252 | result of `write_file()` ignored |
| CWE-639 | policy ignores one of its parameters |
| CAP-ROLE | policy compares against a string literal |
| CAP-TEST | policy without a denial test (error under `--release`), or test that asserts nothing |
| AUDIT | use of `trust()` |

## Compiler modes

```
capstanc check [--strict] [--release] files...
capstanc build -o out.c [--strict] [--release] files...
capstanc test  -o out.c [--strict] files...
```

`--strict` turns every warning into an error. `--release` makes missing policy tests errors.
`--keep-checks` emits every run-time check, including those the range analysis proves unnecessary.

## Formatter

```
capstan fmt [--check] files...
```

`capstan fmt` rewrites files in the house style; `--check` lists the files that are not
formatted, changes nothing and exits 1 if there are any. Only whitespace changes:

- four spaces of indentation per open block, plus one level for a line that continues an
  unfinished statement or an open `(`, `[` or struct literal;
- one space around binary operators and after `,` and `;`; none inside brackets, generic
  arguments (`List<int>`), struct literals (`new P{x: 1}`), or around `.`, unary operators,
  postfix `++`/`--` and the optional `?`; a space after `if`, `while`, `for`, `match` and `return`;
- line breaks are kept, runs of blank lines become one, trailing whitespace is removed and
  the file ends with one newline;
- comments are unchanged. A trailing `//` comment keeps at least its gap, and trailing
  comments on consecutive lines are aligned with each other.

Before writing, the formatter scans its output again and requires the same tokens with the
same text; otherwise the file is left unchanged. A file that does not scan (an unterminated
string or comment, an unexpected character) is refused with exit code 2.

## Conformance areas

Every area below must be covered by at least one test that declares it with a
`// spec: <area>` line. `tests/spec_coverage.py` enforces this on every test run
and every release, and writes the matrix in [CONFORMANCE.md](CONFORMANCE.md).
When the language gains a feature, add its area here and its tests together.

| Area | Covers |
|---|---|
| `lexical` | comments, literals, escapes, character literals, integer literal range |
| `types.int` | checked 64-bit arithmetic, truncating division, limits |
| `types.bool` | booleans and logical operators |
| `types.string` | immutable byte strings, `len`, `at`, `slice`, concatenation |
| `types.tainted` | untrusted input and where it may flow |
| `types.secret` | secrets and hard-coded credential detection |
| `types.html` | context-typed escaped text (`Html`, `LogText`) |
| `types.optional` | `T?`, `none`, `if (let ...)` |
| `types.list` | lists, indexing, list operations, packed `List<bool>` |
| `types.map` | insertion-ordered maps and their operations |
| `types.struct` | structs as reference types |
| `types.enum` | enums with and without values |
| `decl.function` | functions, returns, scoping, initialisation |
| `decl.const` | constants and their initialisation order |
| `decl.struct` | struct declarations and complete initialisation |
| `decl.sensitive` | sensitive structs |
| `decl.method` | struct methods |
| `decl.import` | modules and import path rules |
| `stmt.control` | `if`, `while`, `for`, `break`, `continue` |
| `stmt.assign` | assignment and compound assignment, `++`, `--` |
| `stmt.match` | `match`, exhaustiveness, bindings |
| `expr.operators` | operators and precedence |
| `expr.order` | strict left-to-right evaluation |
| `expr.interpolation` | `$"..."` interpolated strings |
| `expr.bitwise` | `& \| ^ ~ << >> >>>`, required parentheses, shift counts, hexadecimal literals, wrapping arithmetic |
| `builtins.io` | printing, files, arguments |
| `builtins.validators` | the ways out of `Tainted`, and `trust()` |
| `builtins.escapers` | `escape_html`, `escape_log`, `escape_csv`, `escape_c` |
| `builtins.sinks` | `sql_query` and `run` |
| `builtins.crypto` | hashing and password hashing |
| `safety.banned` | dangerous C idioms and weak primitives that do not exist |
| `auth.policy` | policies and policy analysis |
| `auth.grant` | grants: creation, binding, restrictions |
| `auth.tests` | tests, `assert_denied`, `assert_granted`, mandatory denial tests |
| `memory.gc` | garbage collection |
| `memory.limits` | heap limit and stack-overflow guard |
| `runtime.checks` | safe stops with exit code 101 |
| `compiler.ranges` | checks left out only when proved unnecessary; `--keep-checks` |
| `diag.messages` | error message text, positions, suggestions |
| `diag.recovery` | every independent syntax error reported in one run, at most 50 |
| `warnings` | warnings and their CWE codes |
| `modes` | `--strict` and `--release` |
| `tools.fmt` | `capstan fmt`: layout rules, idempotence, comments, refusing unscannable input |
