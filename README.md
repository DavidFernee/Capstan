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
| `printf(…)`, `strcpy(…)`, `free(…)` | `error[CWE-134/120/415]` these don't exist |
| `println(api_key)`, `token == given` | `error[CWE-532]`, `error[CWE-208]` use `secret_eq()` |
| calling a protected function without a grant | `error[CWE-862]` |
| storing or returning a grant | `error[CWE-613]` |
| `policy P(...) { return true; }` | `error[CWE-862]` permits everything; mark it `public` |
| a policy deciding on `Tainted` data | `error[CWE-807]` |
| a policy that ignores the object | `warning[CWE-639]` (error with `--strict`) |
| a policy with no denial test | `warning[CAP-TEST]` (error with `--release`) |

At run time: out-of-bounds reads and writes (CWE-125/787), integer overflow
(CWE-190/191), division by zero (CWE-369), and a grant replayed against a
different object (CWE-639) stop the program with exit code 101.

See [docs/CWE-COVERAGE.md](docs/CWE-COVERAGE.md) for the full mapping,
including what Capstan does **not** prevent.

## Documentation

- [docs/SPEC.md](docs/SPEC.md): the language reference for v0.1
- [docs/CWE-COVERAGE.md](docs/CWE-COVERAGE.md): which weaknesses are prevented, and how
- [docs/DESIGN-MAP.md](docs/DESIGN-MAP.md): design principles and roadmap, from language features to the IDE

## Status

v0.1.0 is a working, self-hosting core language. It is **not yet production-ready**:
there is no garbage collector yet (memory is never freed), `sql_query()` and
`run()` are demonstration sinks that print rather than execute, and there are
no modules, generics or concurrency. See the design map.

## Performance

Capstan compiles to C, which GCC or Clang optimises to native code. On a loop-
and recursion-heavy benchmark, v0.1 runs about 1.6–2× slower than hand-written
C, with every bounds and overflow check active. Closing that gap is on the
roadmap (check elimination, unboxed generics).
