# Capstan

**A programming language with C/Java-style syntax in which the most common classes of security vulnerability cannot be written.**

```java
policy ReadRecord(User u, Record r) {
    if (u.role == ROLE_CLINICIAN && u.id == r.treating_clinician) { return true; }
    return u.role == ROLE_PATIENT && u.id == r.patient_id;
}

protected(ReadRecord) string read_notes(Grant<ReadRecord> g, Record r) {
    return r.notes;
}

void show(User u, Record r) {
    if (let g = authorize ReadRecord(u, r)) {
        println(read_notes(g, r));       // compiles: we hold a grant for r
    }
    println(read_notes(r));              // error[CWE-862]: read_notes() is protected
}
```

Capstan's compiler rejects programs containing SQL injection, command injection,
null dereference, hard-coded credentials, weak cryptography, missing
authorisation and more, with an error that names the CWE weakness it prevented.
What can only be decided at run time (an index computed from input, an
overflowing sum) is checked at run time and stops the program safely.

The name: a capstan is the drum a ship's crew turns to haul up an anchor far
heavier than they could lift by hand. Like the compiler, it gets its leverage
by turning on itself.

## A self-hosting compiler

The Capstan compiler is written in Capstan, and it compiles itself. It's a nod
to Rear Admiral Grace Hopper, whose A-0 started the idea that programs could
write programs.

```
bootstrap/capstan0.py   stage 0: a small, unchecked Python translator, used once
        │ translates compiler/*.cap
        ▼
build/stage1.py         stage 1: the real compiler, running under Python
        │ compiles compiler/*.cap
        ▼
build/stage2.c → capstanc2   stage 2: native compiler
        │ compiles compiler/*.cap again
        ▼
build/stage3.c          must be byte-for-byte identical to stage2.c (the fixpoint)
```

The compiler also passes its own checks: it reads source files as `Tainted`, and
text from a source file reaches the generated C only through `validate_ident()`,
`validate_int()` and `escape_c()`.

## Quick start

Requirements: a C compiler (GCC or Clang) and Python 3 (only for the one-time bootstrap).

```sh
make                                          # bootstrap; verifies the fixpoint
bin/capstan run  examples/patient_records.cap
bin/capstan test examples/patient_records.cap
bin/capstan check --release examples/patient_records.cap
bin/capstan fmt   examples/patient_records.cap   # format in place (--check to verify only)
tests/run.sh                                  # the full suite
```

## What the compiler refuses

| You write | Capstan says |
|---|---|
| `sql_query("SELECT … '" + name + "'")` | `error[CWE-89]` query text must be a literal; pass values as parameters |
| `run("convert " + file)` / `system(…)` | `error[CWE-78]` no shell; program name must be a literal |
| `string s = read_line_value;` | `error[CWE-20]` untrusted input used as a trusted string |
| `println(user_input)` | `error[CWE-117]` wrap it in `escape_log()` |
| `account.owner` where `account` may be none | `error[CWE-476]` unwrap it with `if (let …)` |
| `int total;` | `error[CWE-457]` must be initialised |
| `new Config{port: 80}` missing a field | `error[CWE-908]` field not initialised |
| `string db_password = "hunter2";` | `error[CWE-798]` use `secret_env("NAME")` |
| `md5(…)`, `sha1(…)` | `error[CWE-327]` use `hash()` / `hash_password()` |
| `flags & 1 == 0` | `error[CWE-783]` bitwise operators need parentheses when mixed with others |
| `1 << 64`, `admin & owner` on bools | `error[CWE-1335]`, `error[CWE-480]` |
| `printf(…)`, `strcpy(…)`, `free(…)` | `error[CWE-134/120/415]` these don't exist |
| `println(api_key)`, `token == given` | `error[CWE-532]`, `error[CWE-208]` use `secret_eq()` |
| calling a protected function without a grant | `error[CWE-862]` |
| storing or returning a grant | `error[CWE-613]` |
| `policy P(...) { return true; }` | `error[CWE-862]` permits everything; mark it `public` |
| a policy deciding on `Tainted` data | `error[CWE-807]` |
| a policy that ignores the object | `warning[CWE-639]` (error with `--strict`) |
| a policy with no denial test | `warning[CAP-TEST]` (error with `--release`) |

At run time: out-of-bounds reads and writes (CWE-125/787), integer overflow
(CWE-190/191), division by zero (CWE-369), a shift count outside 0..63 (CWE-1335), runaway recursion (CWE-674), and a
grant replayed against a different object (CWE-639) stop the program with
exit code 101.

See [docs/CWE-COVERAGE.md](docs/CWE-COVERAGE.md) for the full mapping,
including what Capstan does **not** prevent.

## Documentation

- [docs/SPEC.md](docs/SPEC.md): the language reference for v0.1
- [docs/CWE-COVERAGE.md](docs/CWE-COVERAGE.md): which weaknesses are prevented, and how
- [docs/DESIGN-MAP.md](docs/DESIGN-MAP.md): design principles and roadmap, from language features to the IDE
- [docs/K0-KERNEL-CVES.md](docs/K0-KERNEL-CVES.md): the Linux kernel's 2025 CVEs measured against Capstan (roadmap K0)
- [docs/TESTING.md](docs/TESTING.md): how the language is tested

## Memory

Capstan has automatic memory management: a mark-sweep garbage collector built
into the runtime (`runtime/capstan_gc.h`). Programs never free memory
themselves, so use-after-free and double-free can't occur. Under a churn test
that allocates more than 600 MB, the heap peaks at about 13 MB.

## Testing

The suite (`tests/run.sh`) includes:
- runtime unit tests against published cryptographic test vectors, and every validator and escaper
  against its specification
- 68 vulnerable programs that must be rejected, and 76 diagnostics tests
- safe-stop tests and conformance tests checked against an independent second implementation
- collector stress tests, pathological-input limits and sanitizer runs
- differential and mutation fuzzing, and self-hosting reproducibility checks
- formatter tests: expected layout, house style across the repository, whitespace and corruption fuzzing
- every program at -O0, -O2 and -O3 with GCC and Clang; fuzzed programs under ASan and UBSan
- measured test quality: line coverage of the compiler (about 98–100% per file) with enforced
  floors, and mutation testing of the compiler: injected compiler bugs must be caught

See [docs/TESTING.md](docs/TESTING.md).

## Status

Capstan (0.4.0, unreleased) is a working, self-hosting language with garbage
collection, enums, modules, struct methods, a formatter and range analysis. It is **not yet production-ready**: `sql_query()` and
`run()` are demonstration sinks that print rather than execute, and there are no
generics or concurrency yet. See the [design map](docs/DESIGN-MAP.md).

## Performance

Capstan compiles to C, which GCC or Clang optimises to native code. Against
equivalent hand-written C (`bench/run.sh`, all safety checks on):

| Benchmark | What it stresses | Capstan vs C |
|---|---|---|
| alloc | building and discarding trees | about **0.75×** (faster than malloc/free) |
| arrays | sieve over a 5-million-element `List<bool>` | about 1.4× |
| calls | 33 million recursive calls | about 1.7× |
| strings | string building and map updates | about 1.9× |

The compiler's range analysis leaves out overflow and bounds checks it can prove
will never fail, and keeps all the others (`--keep-checks` keeps them all).
`bench/fib.cap` shows how far that can go: once `n - 1` and `n - 2` are proved safe,
the C compiler restructures naive Fibonacci entirely and it runs about 20× faster than
the hand-written C, which says more about optimisers than about call overhead.

## Licence

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
