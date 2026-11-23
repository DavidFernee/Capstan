# CWE coverage

How Capstan v0.1 handles each entry in the 2024 CWE Top 25, plus other weaknesses
it addresses. Statuses:

- **Prevented**: cannot be written, or is always stopped safely at run time.
- **Partial**: substantially harder to get wrong, with the gap stated.
- **Not yet**: outside v0.1's reach; the roadmap item is named.

Every claim here is backed by a test in `tests/`. For an attempt-by-attempt
red-team of about 250 code-level CWEs, including the gaps that remain, see
[CWE-ATLAS.md](CWE-ATLAS.md).

## The 2024 CWE Top 25

| # | CWE | Weakness | Status | How |
|---|---|---|---|---|
| 1 | 79 | Cross-site scripting | **Prevented** for HTML built from `Html` values | Untrusted input must go through `escape_html()`, whose `Html` result can't be confused with other text. *Gap:* typed HTML templates and an HTML-only output sink are on the roadmap |
| 2 | 787 | Out-of-bounds write | **Prevented** | No pointers; every list write is bounds-checked, except where the compiler proves the index in range (see *Checks proved unnecessary* below) |
| 3 | 89 | SQL injection | **Prevented** | Query text must be a string literal; values are bound parameters |
| 4 | 352 | CSRF | Not yet | A framework concern (roadmap: web framework with built-in tokens) |
| 5 | 22 | Path traversal | **Prevented** (except through audited `trust()`) | File paths must be `string`; `validate_path()` rejects `..` and absolute paths; imports are checked the same way |
| 6 | 125 | Out-of-bounds read | **Prevented** | Bounds-checked strings and lists (checks are left out only where proved unnecessary) |
| 7 | 78 | OS command injection | **Prevented** | No shell exists; `run()` takes a literal program and separate arguments |
| 8 | 416 | Use after free | **Prevented** | Garbage-collected memory; programs cannot free memory themselves |
| 9 | 862 | Missing authorisation | **Prevented** for `protected` functions and `sensitive` data | Protected functions require a `Grant`, which only `authorize` can create; fields of a `sensitive struct` can only be touched under a grant. *Gap:* the type must be declared sensitive (once per type) |
| 10 | 434 | Unrestricted file upload | Not yet | Roadmap: typed upload handling in the web framework |
| 11 | 94 | Code injection | **Prevented** | No `eval`. The compiler itself only emits source text through `escape_c()` |
| 12 | 20 | Improper input validation | **Prevented** as a type error | Input sources return `Tainted`. Leaving it requires a validator or an audited `trust()` |
| 13 | 77 | Command injection | **Prevented** | As CWE-78 |
| 14 | 287 | Improper authentication | Partial | `Secret`, `secret_eq()` and `hash_password()` make the parts safe. *Gap:* no built-in session/auth framework |
| 15 | 269 | Improper privilege management | Partial | Policies and grants. *Gap:* policy meaning is the developer's |
| 16 | 502 | Deserialisation of untrusted data | **Prevented** (by absence) | No object deserialisation. Roadmap: typed decoders that return `Tainted` fields |
| 17 | 200 | Exposure of sensitive information | Partial | `Secret` can't be printed, logged, concatenated, written or read; `sensitive struct` data needs a grant. *Gap:* the type must be declared sensitive |
| 18 | 863 | Incorrect authorisation | Partial | Policy analysis (trivially-true, ignored parameters, string roles, tainted inputs) and mandatory denial tests. *Gap:* the policy's meaning |
| 19 | 918 | Server-side request forgery | Not yet | v0.1 has no networking. Roadmap: capability-based network access |
| 20 | 119 | Buffer bounds | **Prevented** | As 787/125 |
| 21 | 476 | Null dereference | **Prevented** | No null; optionals must be unwrapped |
| 22 | 798 | Hard-coded credentials | Partial | Secrets only come from `secret_env()`, and literals assigned to credential-named variables or fields are rejected. *Gap:* a literal under an innocuous name isn't detected |
| 23 | 190 | Integer overflow | **Prevented** | All arithmetic is checked, except where the compiler proves the result fits; overflowing literals don't compile |
| 24 | 400 | Uncontrolled resource consumption | Partial | A heap limit stops runaway allocation safely; `validate_range()` bounds input. *Gap:* CPU time and loop bounds |
| 25 | 306 | Missing authentication for a critical function | Partial | As CWE-862 |

## Other weaknesses addressed

| CWE | Weakness | How |
|---|---|---|
| 116 | Wrong output encoding | Escaped text is typed by context (`Html`, `LogText`) and can't pass as a plain string |
| 244 | Secrets left in freed memory | Secrets are zeroed when collected |
| 256 / 257 | Passwords stored readably | Untrusted input can't be written to files unescaped; password-named data can't be written at all |
| 390 / 546 / 547 / 617 / 783 / 489 | Ignored errors, suspicious comments, magic security numbers, reachable asserts, precedence slips, debug switches | Warnings (errors with `--strict`; debug switches are errors in `--release`) |
| 478 | Missing case | `match` must handle every variant |
| 1236 | CSV formula injection | `escape_csv()`; untrusted text can't be written to files unescaped |
| 88 | Argument injection | Untrusted arguments to `run()` must come after a literal `"--"`, so they can't be read as options |
| 117 | Log injection | `Tainted` can't be printed without `escape_log()`, which neutralises line breaks and control bytes, and also C1 controls, bidirectional overrides, Unicode line separators and invalid UTF-8 |
| 1335 | Incorrect bitwise shift | Shift counts must be 0..63: a literal outside is a compile error, a computed one stops the program; `<<` that loses bits stops with CWE-190 |
| 783 | Operator precedence (bitwise) | Bitwise and shift operators cannot be mixed with other operators without parentheses |
| 480 | Incorrect operator (bitwise on booleans) | `&`, `\|`, `^`, `~` on `bool` are compile errors that name `&&`, `\|\|`, `!=`, `!` |
| 150 | Escape sequences in output | As 117: terminal control sequences, including 8-bit CSI (0x9B and U+009B), are escaped |
| 158 | NUL byte in a path | `read_file()` and `write_file()` refuse a path containing a NUL byte, which C would truncate to name a different file |
| 120 | Classic buffer overflow | `strcpy`/`memcpy`/`gets` don't exist |
| 134 | Format string | No format strings |
| 191 | Integer underflow | Checked arithmetic |
| 208 | Timing side channel on secret comparison | `==` on `Secret` is an error, as is `==` on strings named like tokens or passwords; `secret_eq()` is constant-time |
| 252 | Unchecked return value | Warning when `write_file()`'s result is ignored |
| 327 / 328 | Weak cryptography | No weak primitives. `hash()` and `hash_password()` tag their outputs with the algorithm, so a new language version can change defaults while still verifying old values; `needs_rehash()` flags them for upgrade |
| 561 / 563 / 570 / 571 / 1164 | Dead code, unused variables, constant conditions, self-assignment | Warnings (errors with `--strict`) |
| 916 / 759 / 760 | Fast or unsalted password hashing | `hash()` on a password-named value is an error; use `hash_password()` |
| 338 | Weak random numbers | `rand()` doesn't exist (secure random API on the roadmap) |
| 369 | Division by zero | Literal zero rejected at compile time; checked at run time |
| 415 | Double free | No manual memory management |
| 674 | Uncontrolled recursion | Runaway recursion stops safely; the compiler limits source nesting instead of overflowing its own stack |
| 457 / 908 | Uninitialised variables and fields | Declarations need an initialiser; `new` needs every field |
| 532 | Secrets in logs | `Secret` can't be printed or written |
| 613 | Grants outliving their request | Grants can't be stored, returned or put in collections |
| 639 | Insecure direct object reference | Grants are bound to the objects they were issued for; policies ignoring the object are flagged |
| 807 | Security decision on untrusted input | Policies cannot take `Tainted` parameters |

## What Capstan cannot prevent

- **The meaning of a policy.** Capstan proves that a check happened and flags
  suspicious policies, but it can't know that your organisation meant
  "clinicians on the care team" rather than "all clinicians".
- **Business-logic flaws**: a refund claimable twice, a race between checking and
  debiting at the database.
- **Bugs in the trusted base**: the compiler, the runtime (including the garbage
  collector), and the C compiler. The test suite fuzzes, stress-tests and sanitises
  them, but testing can't prove their absence.
- **Deployment and configuration**: open storage buckets, weak TLS settings.
- **Hardware side channels** below the language.
- **Laundering through data structures or control flow.** Rebuilding text from
  the bytes of untrusted input with `char_str()` is rejected, including through
  helper functions and parameters, lists, maps and struct fields, and bit masks
  and wrapping arithmetic. Information carried only by branching on each byte is
  not tracked: that is how a validator is written, so which branches are safe is
  the programmer's decision. The atlas records it.

## Checks proved unnecessary

Since v0.4 the compiler's range analysis (`compiler/ranges.cap`) leaves out an
overflow, division or bounds check when it can prove the check cannot fail: for
example `i += 1` in `for (int i = 0; i < xs.len(); i += 1)`, the read `xs[i]` in
that loop when nothing in it can shrink a list, or `n - 1` after
`if (n < 2) { return n; }`. Every check it cannot prove is kept, so no program
behaves differently; only the cost of checks that can never fire goes away.

- Facts are recorded only for variables that cannot change in the region concerned,
  and a list-length fact only where no list can shrink (no `pop`, `remove_at`, `clear`
  or call to user code, which might shrink another name for the same list).
- Lengths are bounded by the runtime's 2^48-byte heap cap, and bound arithmetic
  saturates, so the analysis cannot itself overflow.
- `capstanc --keep-checks` (and `capstan build/run --keep-checks`) keeps every check,
  for anyone who would rather not rely on the analysis.
- Tested by: runtime stops that must still happen (`tests/runtime/range_*.cap`), an
  exact count of what is proved (`tests/accept/ranges_proved.cap`), identical results
  with `--keep-checks`, and differential fuzzing against stage 0, which has no range
  analysis, with programs built to tempt it (guards, loops at the 64-bit limits, lists
  shrinking in loop bodies, conditions and calls).

