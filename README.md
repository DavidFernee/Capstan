# Capstan

<p align="center">
  <img src="brand/capstan.svg" alt="Capstan provisional logo" width="112" />
  &nbsp;&nbsp;&nbsp;
  <img src="brand/shroud.svg" alt="Shroud provisional logo" width="112" />
  &nbsp;&nbsp;&nbsp;
  <img src="brand/anchor.svg" alt="Anchor provisional logo" width="112" />
</p>
<p align="center">
  <sub>Capstan · Shroud · Anchor — provisional identity marks</sub>
</p>

> **Branding status:** These are provisional placeholder marks, not approved final logos. See [brand/README.md](brand/README.md) for the design direction, usage limits and review criteria.


**A security-oriented, self-hosting programming language with C/Java-style syntax.** Capstan uses static checks, runtime guards and explicit trust boundaries to prevent or contain classes of defects; the scope and residual gaps are documented in [CWE coverage](docs/CWE-COVERAGE.md) and the [threat model](docs/assurance/THREAT-MODEL.md). These guarantees apply to the Capstan program model, not automatically to the C runtime, compiler toolchain or host platform.

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

Capstan's compiler has targeted checks for source patterns associated with
weaknesses such as SQL/command injection, nullable-value misuse, hard-coded
credentials, weak cryptography and missing authorisation. These checks reject
specific constructs; they do not prove that every application is free of every
instance of those weaknesses. The CWE label and scope of each check are recorded
in [CWE coverage](docs/CWE-COVERAGE.md). Checked operations whose validity
depends on run-time values (for example, an input-derived index or arithmetic
overflow) stop safely when their specified guard fails.

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

## Architecture status

The released development path remains the C-backed implementation shown by the current build: Capstan source is checked and lowered to generated C, then GCC or Clang produces the native executable. The self-hosting compiler and the C runtime/garbage collector are part of the current trusted computing base. The C-free architecture, CCAM typed core IR and Lean verification work are an active, separate development programme; they are not yet the default compiler or a replacement for the current C backend. See [DESIGN-MAP.md](docs/DESIGN-MAP.md) and the proof-boundary discussion in [THREAT-MODEL.md](docs/assurance/THREAT-MODEL.md).

## Quick start

Requirements: a C compiler (GCC or Clang) and Python 3 (only for the one-time bootstrap).

```sh
make                                          # bootstrap; verifies the fixpoint
bin/capstan run  examples/patient_records.cap
bin/capstan test examples/patient_records.cap
bin/capstan check --release examples/patient_records.cap
bin/capstan fmt   examples/patient_records.cap   # format in place (--check to verify only)
bin/capstan lsp                               # language server for editors (stdin/stdout)
tests/run.sh                                  # the full suite
```

The build and test commands above validate the current C-generated native
execution path. They do not exercise the in-progress C-free/CCAM implementation
as a default backend or establish an end-to-end formal proof.

## Editors

`bin/capstan lsp` is a language server: any editor with an LSP client can start it to
underline what the compiler reports as you type, with each CWE code linked to its
description. For example, in Neovim:

```lua
vim.lsp.start({ name = "capstan", cmd = { "/path/to/capstan/bin/capstan", "lsp" },
                root_dir = vim.fs.root(0, ".git") })
```

See [the specification](docs/SPEC.md#language-server) for what it supports.

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

At run time, the corresponding checked Capstan operations stop with
exit code 101 on out-of-bounds reads/writes (CWE-125/787), integer overflow
(CWE-190/191), division by zero (CWE-369), invalid shift counts (CWE-1335),
runaway recursion (CWE-674), and grant replay against a different object
(CWE-639). These language-level checks do not imply that the C runtime or
external toolchain is memory-safe.

See [docs/CWE-COVERAGE.md](docs/CWE-COVERAGE.md) for the full mapping,
including what Capstan does **not** prevent.

## Documentation

- [docs/SPEC.md](docs/SPEC.md): the language reference for v0.1
- [docs/CWE-COVERAGE.md](docs/CWE-COVERAGE.md): which weaknesses are prevented, and how
- [docs/DESIGN-MAP.md](docs/DESIGN-MAP.md): design principles and roadmap, from language features to the IDE
- [docs/C-FREE-BOOTSTRAP.md](docs/C-FREE-BOOTSTRAP.md): the C-free native self-hosting, bootstrap and Capstan 1.0 acceptance contract
- [docs/K0-KERNEL-CVES.md](docs/K0-KERNEL-CVES.md): the Linux kernel's 2025 CVEs measured against Capstan (roadmap K0)
- [docs/CHALLENGE.md](docs/CHALLENGE.md): draft rules for the Capstan Challenge, a planned yearly prize for writing a vulnerability Capstan says is impossible, subject to funding for a foundation to administer the language
- [docs/SHROUD.md](docs/SHROUD.md): Shroud, the cross-platform GUI library written in Capstan
- [docs/TESTING.md](docs/TESTING.md): how the language is tested
- [docs/assurance/](docs/assurance/README.md): memory-safety statement, threat model, and ISM and SSDF mapping

## Memory

Capstan has automatic memory management: a non-moving, conservative
mark-sweep collector built into the current C runtime
(`runtime/capstan_gc.h`). Capstan source has no general-purpose explicit
`free` operation, removing that class of source-level deallocation mistakes.
This does not establish the absence of memory-safety defects in the C runtime,
generated C, compiler toolchain or foreign interfaces. Conservative retention,
stale pointer-bearing slots and implementation/ABI assumptions remain relevant;
see the [runtime memory and lifetime model](docs/assurance/RUNTIME-MEMORY-MODEL.md)
and [memory-safety assessment](docs/assurance/MEMORY-SAFETY.md).

## Testing

The standard local validation entry point is `tests/run.sh`. It exercises the
current C-backed compiler/runtime path and includes:

- runtime unit tests, cryptographic test vectors, validators and escaping;
- compiler rejection and diagnostic conformance suites;
- runtime safe-stop tests, collector stress and pathological-input limits;
- differential/adversarial fuzzing and self-hosting bootstrap/fixpoint checks;
- formatter and language-server protocol, limit and fuzz tests;
- GCC/Clang optimisation-level checks and ASan/UBSan runs where supported;
- compiler coverage floors and mutation testing in the full validation path.

Test inventories and counts evolve; the test runner's output and the workflow
results for the exact commit are authoritative. A test file or verifier that is
not invoked by `tests/run.sh` is not part of the standard suite. CI currently
validates Linux/GCC, Linux/Clang and macOS/Clang, plus a separate supply-chain
job. These workflow definitions do not imply that a particular local checkout
has been tested, and no result should be carried across commits.

See [docs/TESTING.md](docs/TESTING.md) for the validation model and test
categories.
## Status

Capstan (0.4.0, unreleased) is a working, self-hosting language with garbage
collection, enums, modules, struct methods, a formatter, a language server and range analysis. It is **not yet production-ready**: `sql_query()` and
`run()` are demonstration sinks that print rather than execute, and there are no
generics or concurrency yet. The C backend remains the current execution path. The CCAM/C-free and Lean work is under active development and must not be read as an already integrated native backend or an end-to-end proof. See the [design map](docs/DESIGN-MAP.md) and [assurance boundary](docs/assurance/README.md).

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
