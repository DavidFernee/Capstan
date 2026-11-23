# Capstan design map

## 1. Purpose

Capstan's goal: **with familiar C/Java syntax, make every common vulnerability class
either impossible to express or a compile error, and say plainly what remains.**

The long-term aim is **Capstan all the way down**: the compiler, standard library and
runtime written in Capstan, compiling to machine code with no C anywhere, every line
subject to Capstan's guarantees, including the runtime. Only the
operating system underneath remains outside Capstan.

## 2. Design principles

1. **Unsafe is unrepresentable.** Prefer removing the dangerous construct (null,
   pointers, shells, format strings, weak crypto) over warning about it.
2. **Errors name the weakness.** Every safety diagnostic carries its CWE number,
   so findings map directly onto security standards, audits and ISM controls.
3. **The compiler is deterministic.** The same source always gives the same verdict.
   AI review is advisory, or a separately recorded and cached gate, never part of type checking.
4. **Escape hatches are explicit, rare and auditable.** `trust("why")` always needs a written
   justification and appears in audit output. There is no unsafe code: nothing, the runtime included, runs unchecked.
5. **Friction only where risk is.** Mandatory tests apply to policies and other
   security-critical code, not to everything.
6. **Agility without code changes.** Security primitives are abstract (`hash`,
   `hash_password`), their outputs are self-describing, and upgrading the language
   version upgrades the algorithms.
7. **Dogfooding.** The compiler is written in Capstan and must pass `--strict`.
8. **Honest claims.** The coverage document states what is not prevented.
9. **Trust as little as possible.** Every line of C, every external tool and every
   escape hatch is a liability to be reduced, and the remainder is documented as the
   trusted base.
10. **Every security check, every release.** No release ships without the full suite,
    the CWE atlas, fuzzing and sanitisers passing on every supported platform.

## 3. Architecture

```
            source (.cap)
                 │
   lexer ── parser ── checker ──────────── codegen ── C ── GCC/Clang ── native
                         │  types, taint,                    ▲
                         │  grants, policies,                │ capstan_rt.h
                         │  CWE diagnostics                  │ (checks, crypto,
                         ▼                                   │  collections)
                 diagnostics ──► CLI today ──► LSP server ──► editors / Capstan IDE
                                                   ▲
                                      Capstan Review (Claude), advisory layer
```

## 4. Roadmap

Each version must keep the self-hosting fixpoint, the full test suite and the
compiler's own `--strict` check passing, and the repository formatted with `capstan fmt`.

### v0.1 — Self-hosting safe language *(done)*
Structs, optionals, lists, maps, checked integers, taint tracking, secrets,
policies and grants with object binding, mandatory denial tests, agile hashing
(SHA-256 and PBKDF2), 46 vulnerability tests (39 rejected at compile time, 7 stopped at run time), and a compiler that compiles itself.

### v0.2 — Memory management and test suite *(done)*
Mark-sweep garbage collector with interior-pointer support and pointer-free
allocation for strings. Stack overflow guard (CWE-674) and a nesting limit in the
compiler. `#line` mapping from generated C back to Capstan source, for debuggers,
sanitizers and coverage. A commercial-grade test suite: published crypto vectors,
conformance against a second implementation, differential and mutation fuzzing,
sanitizers, GC stress, pathological limits and a benchmark gate (see TESTING.md).

### v0.3 — Everyday language *(done)*
Enums with payloads and exhaustive `match`, `else if` chains, `x++`, string interpolation that
preserves taint (`$"Hello {name}"`), struct methods, `List.pop/insert/remove_at/sort`, `Map.remove`,
`import "module"` with one file per module, packed `List<bool>`, and diagnostics with columns,
source excerpts and "did you mean" suggestions. Also the CWE red-team atlas and 20 gap closures
(`Html`/`LogText`, `sensitive struct`, secret wiping, heap limit, new lints).

`capstan fmt`, the formatter, completes the version. It is written in Capstan (`tools/fmt.cap`),
changes whitespace only and checks its own output token for token before writing. Writing a
source file back is its one `trust()`, so its build shows one AUDIT warning: the first in-tree use
of the escape hatch, and the first entry the v0.10 audit command will list. The repository is
formatted, and the suite enforces it and fuzzes the formatter (see TESTING.md).

Carried forward, because neither blocks everyday use:
- `public`/`private` visibility for module members (v0.5, alongside interfaces)
- parser error recovery, so one run reports more than one syntax error (with the LSP server, Phase A)

### v0.4 — Performance *(in progress)*
Done:
- packed `List<bool>`, one byte per element
- **range analysis** (`compiler/ranges.cap`): overflow, division and bounds checks are left out
  where the compiler proves they cannot fail (`i += 1` under `i < xs.len()`, `xs[i]` in a loop
  that cannot shrink any list, `n - 1` after `if (n < 2) { return n; }`), and kept everywhere
  else. It proves 186 of the compiler's own 855 checks unnecessary. Facts are only kept for
  variables that cannot change, so the argument for soundness is short (see the file header
  and CWE-COVERAGE.md). `--keep-checks` turns it off for assurance work.
- unboxed optionals where an `int?` is unwrapped at once (`if (let v = m.get(k))`, `xs.pop()`)
- benchmark gate in the nightly CI run

Remaining:
- packed, type-specialised lists for other element types, and unboxed `int?` in variables and fields
- facts across function calls (bounds on parameters from every call site): what the `calls`
  benchmark still pays for
- generational collection; returning empty pages to the operating system
- benchmarks within 20% of C (now: alloc is; arrays about 1.4×, calls 1.7×, strings 1.9×)

### v0.5 — Abstraction
- user generics with interfaces (`interface Comparable<T>`)
- `public`/`private` visibility for module members
- closures that capture by value (no dangling references)
- error handling: `Result<T, E>` with `?` propagation (no exceptions)

### v0.6 — Safe systems access
- capability-based I/O: `main(Capabilities caps)`. Code can only touch files,
  directories, network hosts and environment variables it was handed
  (addresses CWE-22, CWE-918, and supply-chain blast radius)
- `Path` type with traversal-safe joining
- real `run()` (posix_spawn, never a shell) and SQL drivers with prepared statements
- resource limits: size-bounded input types, mandatory timeouts, linear-time regex (CWE-400)
- secure random API (`random_bytes`, `random_int`)
- authenticated encryption `seal()` / `open()` with algorithm tags; key rotation support

### v0.7 — Concurrency
- tasks and channels; data shared only by moving ownership or through typed locks
  (data races become compile errors)
- the kernel-ready forms of these are designed in section 7, K1.2 to K1.5: data guarded by its
  lock, RCU as a type, execution contexts, lock ordering and structured concurrency
- `async` I/O for servers

### v0.8 — Policies, proven
- `assert never ...` policy properties checked by an SMT solver, with counter-examples
- `sensitive struct`: every access is protected by default (closes the CWE-862 "forgot to mark it" gap)
- policy coverage report in CI
- mutation testing for policies: the compiler weakens a rule and checks that a test fails

### v0.9 — Web
- typed HTML templates (`Html` type; XSS becomes a type error)
- web framework with CSRF tokens, secure cookies, session expiry and auth flows built in
- typed decoders for JSON and forms that produce `Tainted` fields

### v0.10 — Interop and packages
- foreign code (existing C libraries) runs isolated, never in-process unchecked: in a separate process or a WebAssembly sandbox, behind a typed, checked interface whose inputs and outputs are `Tainted`
- package manager: signed packages, lockfiles, capability manifests per dependency
- audit command: lists every `trust()`, isolated foreign component and suppressed warning in a project

### v1.0 — Stable
- language and standard library stability guarantee
- complete specification; optional formal verification of the checker's core rules
- WebAssembly backend alongside C

## 5. Tooling and IDE

### Phase A — Language server (next, alongside v0.4)
An LSP server written in Capstan, reusing the compiler front end:
- prerequisite: parser error recovery, so an editor sees every error in a file at once
- red and yellow underlines with CWE codes, linking to the CWE description
- hover types (`Tainted`, `Grant<ReadRecord>`), go to definition, find references, rename
- quick fixes: "wrap in `escape_log()`", "unwrap with `if (let ...)`",
  "generate a denial test for this policy"
- format on save through `capstan fmt` (done as a command-line tool)
- works in VS Code, JetBrains, Neovim, Zed and others from day one

### Phase B — Capstan IDE (with v0.6)
A dedicated IDE built on the same server (for example a VS Code-based distribution):
- **security view**: every policy, which functions it protects, test status, and trust sites
- **taint view**: where untrusted input enters and every validator it passes through
- one-click `--release` build showing exactly what blocks it
- debugger with grant and taint inspection

### Phase C — Capstan Review, powered by Claude
An advisory AI layer on top of the deterministic compiler:
- reviews changed code and underlines questionable logic the type system can't see:
  - policies that contradict documentation (the ML check against requirements)
  - business-logic flaws and suspicious `trust()` justifications
- each finding cites the code and, when relevant, the requirements passage
- **Gate mode (opt-in):** "do not build if Review reports any issue". To keep builds
  reproducible, verdicts are cached against the file contents and recorded with the
  build. The same code always gets the same answer until it changes or you re-run Review.
- Model: Claude through the Anthropic API. The Mythos tier isn't generally available;
  Claude Fable 5.2 is the publicly available model in that tier and needs evaluating for this
  use, since it has extra cybersecurity safeguards. The feature shouldn't carry Anthropic's
  model names as its brand.
- Privacy: code is sent to the API. Offer an organisation-level switch and a clear
  data notice, which matters for government and PROTECTED workloads.

## 6. Trusted base reduction: Capstan all the way down

Today a Capstan program depends on three things that are not Capstan: the runtime
(about 1,500 lines of C), the C standard library, and the C compiler. Code written in
Capstan cannot corrupt memory; code in that foundation can. Each step below moves code
into Capstan, where its bugs become safe stops instead of exploitable corruption, or
removes a dependency altogether.

| Stage | Work | Security gain |
|---|---|---|
| T1 (with v0.5) | **Standard library in Capstan:** validators, escapers, collection helpers (sort, join, search) | Text-processing code inherits Capstan's guarantees |
| T2 (with v0.5) | **Bitwise operators and explicitly wrapping arithmetic** (`&`, `\|`, `^`, shifts, `wrapping_add`); ordinary `+` stays overflow-checked, and a shift by a negative amount or by the type's width or more stops safely | Prerequisite for writing crypto and parsers safely |
| T3 (with v0.6) | **Crypto in Capstan:** SHA-256, HMAC, PBKDF2, then authenticated encryption, checked against the same published vectors | Crypto implementation bugs cannot corrupt memory. A FIPS 140-3 validated-module option remains for certified deployments |
| T4 (with v0.6) | **Formatting and parsing in Capstan:** number to text and back, replacing `sprintf`, `snprintf` and `strtol`; differentially tested against libc on millions of random inputs | Removes the libc functions where memory-corruption bugs have historically clustered |
| T5 (with v0.6) | **Network parsing in Capstan from the start:** addresses, URLs, HTTP, name resolution. Never borrowed from libc | The highest-risk input handling is memory-safe by construction (compare glibc CVE-2015-0235, CVE-2015-7547) |
| T6 (v0.7) | **Thin system-call layer:** the program talks to the kernel through a small audited layer (open, read, write, exit, memory mapping, signals) instead of the C library, as Go does on Linux | libc leaves the trusted base |
| T7 (v0.8) | **Verified low-level Capstan:** the few raw operations the runtime needs (read or write raw memory, convert an address, call the kernel) are allowed only when the compiler proves their preconditions with an automated solver, as SPARK Ada does for run-time errors and Verus does for low-level Rust. Unprovable code does not compile. There is no `unsafe` escape hatch | Capstan's guarantees hold in the runtime too, established by proof instead of run-time checks |
| T8 (v0.9) | **Runtime in verified Capstan:** garbage collector, allocator and safety primitives, every raw operation proved; the C remaining is only the program entry point, until the native backend removes it | No unchecked code in the runtime |
| T9 (v0.9) | **Verified C compilation option:** generated C builds with CompCert (formally verified), for high-assurance users | The C compiler leaves the trusted base (CompCert needs a commercial licence outside research) |
| T10 (v1.0) | **WebAssembly backend:** Capstan emits WebAssembly directly, no C | First backend with no C at all; sandboxed execution contains even compiler bugs |
| T11 (after v1.0) | **Native backend:** Capstan emits x86-64 and ARM64 directly. Designed for verification (small, simple, with translation validation) rather than peak speed; the C path remains for performance builds | Capstan all the way down |
| T12 (after v1.0) | **Full functional verification:** the type and safety checker proved to enforce Capstan's rules, and the runtime proved to meet its specification (not only free of memory errors) | Proof, not just testing, for everything Capstan relies on |

**No unsafe component.** Capstan's guarantees apply at all times, to all code, including
the runtime and the standard library. Ordinary code is protected by the type system and run-time
checks; the runtime's low-level operations are protected by machine-checked proof. Code that cannot be proved safe does not
compile, so there is no code anywhere that runs unchecked. What remains to be trusted is the
irreducible minimum for any system: the proof checker, the specifications (a proof shows code
meets its specification, not that the specification is right), the operating-system kernel and
the hardware, the same residue that seL4 and CompCert rest on.

**Testing the runtime as hard as it is proved.** Proof and testing complement each other:
- **checked build:** in test runs, every raw operation in the runtime is also checked at run time
  against the allocator's own record of which memory exists and who owns it, and the whole suite
  (conformance, CWE atlas, differential and mutation fuzzing, collector stress) runs on that build
- **reference models:** the collector and allocator run side by side with a deliberately simple,
  obviously correct model on millions of random allocation patterns and must agree
- **direct fuzzing** of every runtime entry point
- **CWE atlas for the runtime:** attacks aimed at low-level code, each of which the prover or the
  checked build must catch

**Defence in depth.** Even proved code runs on real hardware with real compilers until the native
backend is complete, so the runtime is also hardened against exploitation: guard pages around heap
regions, randomised heap layout, poisoning of freed memory, and the C compilers' exploit mitigations
(control-flow integrity, stack protectors, position-independent code) while C is still in the build.

At every stage the existing tests (conformance, CWE atlas, differential and mutation
fuzzing, sanitisers, published vectors) must pass unchanged. Each replaced component is
also tested against the one it replaces: Capstan's number formatting must match libc's
byte for byte, its SHA-256 must match the current implementation, and so on.

**The end state: no C.** After stage T11, nothing in Capstan or in a Capstan program is written
in C: not the compiler, the standard library, the runtime, the system-call layer or the program's
start-up code. What remains belongs to the platform, not to Capstan:

| Platform | Capstan and its programs | Still underneath (see section 7 for removing the kernel too) |
|---|---|---|
| Linux | no C at all: programs call the kernel directly through its stable system-call interface | the kernel |
| macOS, Windows | no C in Capstan or its programs | the kernel, plus the vendor's system libraries: both platforms require programs to reach the kernel through them (Go had to make the same change on macOS). Everything those calls return is treated as untrusted input |
| seL4 (formally verified kernel) | no C at all | a kernel with a machine-checked proof of correctness: the highest-assurance target, suited to defence use |

**Bootstrapping without C.** Once the native backend exists, each Capstan release is built by the
previous one. The Python stage 0 and the C route are kept, but not depended on: they are the
independent toolchains that diverse double-compiling compares against, so a tampered compiler
binary would be detected.

**Defending the compiler itself.** Ken Thompson showed that a compiler can be tampered
with to insert flaws that appear nowhere in its source. Capstan uses David A. Wheeler's
diverse double-compiling defence: the compiler must reproduce itself byte for byte when
built with GCC, with Clang, and from the independent Python stage 0. Each new backend
joins that comparison.

## 7. Capstan in the kernel

The operating-system kernel is the last large body of C beneath a Capstan program. The Linux
kernel is about 40 million lines and now fixes close to 2,000 CVEs per release, most of them
memory corruption. This track measures how much of that Capstan would prevent, then tests the
answer on real kernel code, and finally removes the kernel from the trusted base altogether.

### K0: measure first (can start now, no kernel code)
Take the Linux kernel CVEs from a recent period, classify each by CWE from its fix, and run every
class through the CWE atlas. Publish the result: the share Capstan's rules would have prevented at
compile time, the share stopped safely at run time, the share that are logic errors no language
catches, and the share outside Capstan's current reach. Re-run the study each year as the CVE
stream and Capstan both change. This is also direct evidence for government and defence buyers.

**Status: first study done (2025 CVEs).** [K0-KERNEL-CVES.md](K0-KERNEL-CVES.md), generated by
`tools/k0/study.py`: of 2,702 kernel CVEs published in 2025, about 71% of those that could be
classified are weaknesses Capstan prevents today (51% at compile time, 20% stopped safely at run
time), 21% are outside its current reach (mostly concurrency and resource lifetime, the target of
K1) and 8% are logic errors. The K1 design below is aimed at that remainder; the study projects
that, built as designed, it would raise the prevented share to about 89%. Next: independent
relabelling of the check samples, and the 2026 re-run.

### K1: kernel-mode prerequisites
Kernel code cannot use a collector that pauses at arbitrary moments or rely on an operating system
beneath it. Before any kernel work, Capstan needs:
- **a freestanding mode:** no operating system, no allocator unless one is provided, explicit stack limits
- **error results that must be handled:** no ignored return codes (already a Capstan direction)

The rest of K1 is designed against the K0 result. Of the 2025 kernel CVEs that could be
classified, 29% are not prevented by Capstan today: 21% outside its reach, 8% logic errors. Each
item below names the classes it targets and the outcome it is meant to produce; `tools/k0/study.py`
projects the effect on the same CVEs, so the claim can be checked when the feature exists. None of
them adds an `unsafe` escape: where the compiler cannot prove a rule, the code does not compile.

**K1.1 Ownership and linear resources** *(memory leaks, resource and reference-count leaks:
~6% of classified CVEs)*
- Kernel mode replaces the collector with ownership: every allocation has one owner, freed when the
  owner goes out of scope; borrowing is checked so no reference outlives its object. Use-after-free
  and double free stay impossible, as they are under the collector.
- **Linear resources.** A reference count taken, a device enabled, a DMA mapping or an IRQ
  requested is a value of a `linear` type: it must be released exactly once on every path, including
  every error path. `Ref<T> r = get(obj);` with no matching `put(r)` is `error[CWE-772]`; a second
  `put(r)` is `error[CWE-1341]`. The kernel's `goto err_*` unwind ladders become automatic, in reverse
  order of acquisition.
- **Shared ownership** (`Rc<T>`, `Arc<T>`) for objects that really are shared, with weak
  references for back-pointers so cycles do not leak.

**K1.2 Data guarded by its lock** *(data races, improper locking: ~8%)*
- Shared mutable data is declared with the lock that protects it: `Locked<Stats, Spin> stats;`.
  The data can only be reached through the guard that `lock()` returns, and the guard releases the
  lock when it goes out of scope, on every path. Missing locks, missing unlocks and unbalanced
  lock/unlock are compile errors (`CWE-667`).
- Values cross between threads only if their type is safe to share (immutable, atomic, or behind a
  lock); otherwise moving or sharing them is `error[CWE-362]`. This is Rust's `Send`/`Sync`, extended
  to the kernel's own primitives: per-CPU data, sequence locks and atomics with explicit ordering.
- **RCU as a type.** `Rcu<T>` can be read only inside an `rcu_read { }` block, and a reference read
  there cannot escape the block; updates go through `rcu_assign` and objects are freed only after a
  grace period, by the compiler-inserted `call_rcu`. Accessing RCU data outside a read section, the
  most common locking CVE in the 2025 set, does not compile.
- **Shared memory with user space or devices** is a distinct type, `Volatile<T>`: every read is a
  single fetch into a local (the kernel's `READ_ONCE()`), so a value cannot change between its check
  and its use (`CWE-367`).

**K1.3 Execution contexts** *(sleeping in atomic context, interrupt-unsafe locking)*
- Every function has a context, inferred where possible and declared at boundaries: `process`,
  `atomic` (spinlock held, preemption off), `softirq`, `hardirq`, `nmi`. A function that may sleep
  cannot be called in an atomic context, and a lock taken in interrupt context must be taken with
  interrupts disabled everywhere else. Both are compile errors, not lockdep warnings at run time.

**K1.4 Lock ordering** *(deadlocks: ~4%)*
- Locks are declared in levels (`lock_order inode_lock < page_lock < stats_lock`); the compiler
  rejects acquiring a lock while holding one of an equal or higher level, which rules out
  self-deadlock (AA) and ABBA cycles. Waiting for work, a completion or a timer counts as acquiring
  the locks that work takes, so `flush_work()` under a lock the work needs is rejected (`CWE-833`).
- Lock orders that depend on run-time data (two objects of the same type) use an ordered
  acquisition primitive (`lock_both(a, b)` by address), and the checked build verifies the remaining
  dynamic orders and stops safely before a cycle completes.

**K1.5 Lifetimes of callbacks** *(teardown races: work, timers and interrupts outliving their
device; the largest source of race-caused use-after-free)*
- **Structured concurrency.** A work item, timer, interrupt handler or kernel thread is registered
  through an owner (`dev.spawn(...)`, `dev.request_irq(...)`), and the owner cannot be destroyed
  until all of them are cancelled and finished: the compiler inserts the cancellation, in order, at
  the end of the owner's lifetime. Module unload with work pending becomes impossible to write.
- **Typestate for drivers.** A device moves through declared states (`probed`, `open`, `suspended`,
  `removed`); operations exist only in the states that allow them, so using a device after
  `remove()` or before probe completes is a type error (`CWE-841`, `CWE-672`).

**K1.6 Hardware and memory reinterpretation** *(type confusion, shifts)*
- **Typed views.** Device memory, network packets and on-disk structures are reached through
  `view<T>(bytes)`, which the compiler allows only when `T` is plain data and the size and
  alignment are proved; the result of a view of untrusted bytes is `Tainted`. `container_of` becomes
  a checked downcast. This replaces casts without reintroducing type confusion (`CWE-843`).
- **Checked shifts** (with T2): a shift by a negative amount or by at least the type's width stops
  safely, as overflow does; `wrapping_shl` is explicit (`CWE-1335`).

**K1.7 Entry points declare their authorisation** *(missing permission checks)*
- Every system call, ioctl, netlink handler and sysfs or procfs write is an entry point, and an entry
  point must name its policy (`protected(CapNetAdmin)`, `protected(OwnerOf)`) or be explicitly
  `public`. A privileged operation reached from an entry point without a grant does not compile.
  This closes the atlas's CWE-862 and CWE-306 gaps for kernel code, where entry points are known.

**K1.8 Speculation hardening** *(Spectre variant 1)*
- Capstan already knows which indices are `Tainted`. An array access with an index derived from
  untrusted input is compiled with the bounds check *and* index masking (the kernel's
  `array_index_nospec()`), automatically. Other speculation attacks remain the processor's to fix.

**K1.9 Narrowing the logic errors** *(hangs and infinite loops, insufficient validation: ~8%)*
No language decides intent, but two features turn common kernel logic errors into checkable ones:
- **Bounded loops.** In `atomic` and interrupt contexts, and wherever the loop's bound comes from
  untrusted data (a disk image, a packet, a device), a loop must declare its bound
  (`for (...) bounded(MAX_EXTENTS)`) or a decreasing measure the compiler proves; reaching the bound
  returns an error instead of hanging. Most 2025 hangs were loops over corrupt on-disk or device data.
- **Declared formats and refinement types.** On-disk and wire structures are described once
  (`format Ext4Extent { u16 len in 1..32768; u32 start; ... }`), and the compiler generates the
  parser: a value of the type exists only if every declared constraint held. Integer ranges
  (`int{0..MAX_PORTS}`) travel with the value. What remains a logic error is a wrong constraint,
  not a forgotten one.

**What stays out of reach:** logic errors in what the code is meant to do, hardware and firmware
faults, and processor side channels beyond variant 1. K0 reports them separately every year.

### K2: port real subsystems and count what disappears
Using kernel-mode Capstan, rewrite a small number of the Linux subsystems with the most CVEs, as
loadable modules: for example a network protocol parser, a USB or Bluetooth driver, and a
file-system metadata parser. For each, replay the known CVE reproducers and run the kernel's own
fuzzer (syzkaller) against the C original and the Capstan version side by side, and report which
vulnerabilities no longer exist, which became safe stops, and which remain. The kernel itself is C,
so these modules sit on the platform as any program does; everything the C kernel passes them is
treated as untrusted input.

### K3: a Capstan microkernel
Rather than rewriting all of Linux, write a small kernel in Capstan, in the spirit of seL4 (formally
verified) and Redox (written in Rust): isolation, scheduling, memory management and message passing
in the kernel; drivers, file systems and network stacks as isolated Capstan services. With its
correctness proved, it completes the stack: Capstan all the way down, kernel included, with nothing
in C. This is a long-term goal after v1.0.

## 8. Security programme

Standing commitments, every release:

- **Full verification on every platform:** `tests/run.sh --full`, including the CWE atlas,
  long fuzzing campaigns, sanitisers and benchmarks, on every supported OS and compiler.
  No release is published otherwise.
- **CWE tracking:** when MITRE publishes a new CWE version or Top 25 list, new code-level
  entries are added to the atlas with an attack attempt and a verdict before the next release.
- **Gap burn-down:** every remaining gap in the atlas has an owner milestone; a release
  may not add a new gap without recording it.
- **Vulnerability reporting:** a published disclosure policy (`SECURITY.md`), private
  reporting, advisories for every confirmed issue, and a regression test for every fix.
- **Supply chain:** signed releases, SBOMs (CycloneDX or SPDX), SLSA build provenance,
  reproducible builds (already verified by the self-hosting fixpoint), and minimal
  dependencies.
- **Dependency watch:** monitor advisories for the C compilers and C library while they
  remain in the trusted base.
- **Independent review:** an external security audit before v1.0, and again whenever
  the trusted base changes substantially.
- **Threat model:** a maintained document stating what Capstan defends against, what it
  assumes, and what is out of scope ([assurance/THREAT-MODEL.md](assurance/THREAT-MODEL.md)).

## 9. Government and defence use

Capstan's first audience is government and defence software, where vulnerability
classes are costly and assurance must be demonstrated. Work needed for that audience
(the assurance pack so far is in [assurance/](assurance/README.md)):

- **Memory-safe language guidance.** The Five Eyes cyber agencies, including ASD's
  ACSC, recommend that organisations move to memory-safe languages. Capstan should
  publish a short statement mapping its guarantees to that guidance
  ([assurance/MEMORY-SAFETY.md](assurance/MEMORY-SAFETY.md)).
- **Approved cryptography.** Align the defaults behind `hash()`, `hash_password()` and
  the future `seal()` with ASD's approved cryptographic algorithms and NSA's
  CNSA 2.0 suite (for example SHA-384 and AES-256 for higher classifications).
  Algorithm tagging makes that a version change, not a code change.
- **Validated cryptographic modules.** Self-implemented cryptography can't be
  FIPS 140-3 validated without its own certification. Offer a build option that
  routes every primitive through a validated module (for example the OpenSSL 3 FIPS
  provider or AWS-LC FIPS), keeping the built-in implementation for other uses.
- **Secure development evidence.** Map the toolchain and tests to the ISM's software
  development controls and NIST SP 800-218 (SSDF)
  ([assurance/ISM-MAPPING.md](assurance/ISM-MAPPING.md)). Publish SBOMs (CycloneDX or SPDX),
  signed releases and SLSA build provenance. The self-hosting fixpoint already gives
  reproducible compiler builds.
- **Export controls.** Capstan includes cryptographic source code. Before public release,
  confirm the position under Australia's Defence Trade Controls Act and Defence and
  Strategic Goods List (Category 5 Part 2), and under the US EAR for US-based contributors
  and mirrors. Published open-source cryptography often qualifies for exemptions, but
  this needs confirming, ideally with Defence Export Controls.
- **Assurance.** For use in evaluated products or safety-related systems: a compiler
  qualification kit (requirements-based tests traced to the specification), coverage
  reports from the `#line` mapping, and a path to formal verification of the checker's
  core rules (v1.0).
- **Air-gapped operation.** The compiler, runtime and tests need no network access.
  Capstan Review (AI) must stay optional and off by default for classified work.

## 10. Quality bar

- every safety rule has at least one rejecting test, and every runtime check a stopping test
- every diagnostic the checker can emit is triggered by a test; line coverage of the compiler,
  formatter and runtime is measured (`tests/coverage.py`, `docs/COVERAGE.md`) and may not fall
  below the floors in `tests/coverage_floors.txt`
- mutation testing of the compiler (`tests/mutate_compiler.py`): injected compiler bugs must be
  caught by the suite; every surviving mutant becomes a test or is shown to be equivalent
- every conformance program and safety stop behaves identically at `-O0`, `-O2` and `-O3` with
  GCC and Clang
- the range analysis's interval arithmetic is property-tested against exact arithmetic on every
  combination of edge values
- the compiler passes its own `--strict` check
- every source file in the repository is formatted (`capstan fmt --check`)
- the bootstrap fixpoint is verified in CI
- sanitiser runs (ASan/UBSan) of the compiler, formatter and examples in CI, and of a third of
  the differentially fuzzed programs (so undefined behaviour is caught even when output matches)
- differential and mutation fuzzing on every change; long campaigns nightly

## 11. Known risks

| Risk | Mitigation |
|---|---|
| Trusted base bugs (runtime, C library, C compiler) | the trusted base reduction plan (section 6): proof for the runtime, no unchecked code; meanwhile fuzzing, sanitisers and diverse double-compiling |
| Proofs rest on specifications that could be wrong | specifications are reviewed, kept small, and tested: the checked build and reference models test the same properties the proofs establish |
| Rewritten components less battle-tested than the originals | write them in Capstan so their bugs cannot corrupt memory; differential testing against the component replaced |
| Heuristic checks (CWE-798 names) give false confidence | label them Partial; prefer type-based rules over name heuristics |
| Friction drives developers to `trust()` | quick fixes and good validators; audit reports make overuse visible |
| AI review non-determinism | advisory by default; cached and recorded verdicts in gate mode |
| Scope | ship each version usable on its own; never break self-hosting |
| Kernel work outgrows the project | measure first (K0); port only a few high-CVE subsystems (K2); a microkernel rather than a Linux rewrite (K3) |
