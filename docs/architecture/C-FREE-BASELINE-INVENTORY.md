# C-free programme: current execution-path inventory

**Status:** first-pass source inventory; not a completeness audit  
**Baseline:** `main` at the revisions listed below (2026-11-26)  
**Parent:** issue #80  
**Purpose:** make the current C/Python/platform dependencies and their assurance consequences explicit before selecting the replacement native boundary.

## 1. Scope and method

This note inventories the current bootstrap/build path, the C constructs emitted by the Capstan code generator, and the principal runtime/collector interfaces visible in the current source. It is a source-level inventory, not proof that every conditional path, generated symbol, transitive library dependency, or release workflow has been enumerated.

Inspected files:

| File | Revision |
|---|---|
| `compiler/codegen.cap` | `4e24b9bb276d7210af50d05658393ecf68f16c6f` |
| `runtime/capstan_rt.h` | `0210ea0cdaaeab52ef8f1614bc788bd224ec5403` |
| `runtime/capstan_gc.h` | `04b24986acec804853c33ee32dd20fa795643e29` |
| `Makefile` | `a49187062b36a1f46edee073d01a21ca63e0d235` |
| `README.md` | `4b0fd3b75efc855afad4fb1c5029fb3c1154cbda` |

The architectural intent and previous bootstrap observations are in [C-FREE-EXECUTION.md](C-FREE-EXECUTION.md). This document adds a more concrete code-generator/runtime boundary map; it does not replace that proposal.

## 2. Current build and bootstrap chain

The Makefile currently defines this dependency chain:

1. `bootstrap/capstan0.py` translates the Capstan compiler sources into `build/stage1.py`.
2. Python 3 executes stage 1; stage 1 compiles the compiler sources to `build/stage2.c`.
3. `$(CC)` (default `cc`) compiles stage 2 C, including `runtime/capstan_rt.h`, into `build/capstanc2`.
4. The native stage-2 compiler emits `build/stage3.c`.
5. `cmp` requires stage 2 and stage 3 generated C to be byte-identical; the C compiler then builds `build/capstanc`.
6. The formatter and language server are separately emitted as C and compiled with the same C toolchain/runtime header.

The default `all` target includes bootstrap, formatter and LSP. The `test` target runs `tests/run.sh` after building those executables.

**What the fixpoint establishes:** stage 2 and stage 3 emit identical C for the compiler source at that revision.

**What it does not establish:** correctness of stage 0, semantic correctness of generated C, correctness of the C compiler/linker, correctness of the C runtime/collector, or equivalence with an independent language semantics.

Current build-time dependencies directly visible in the Makefile include Python 3, a C compiler supporting the selected GNU C dialect/extensions, a POSIX-like shell/test environment, and the host C/POSIX headers and libraries used by the runtime. This list is not yet a complete platform/dependency inventory.

## 3. C language and compiler-extension surface

The code generator emits C source directly. The following constructs/extensions are visible in its generation templates and runtime contract:

- C scalar and pointer representations: `int64_t`, `bool`, `void`, typed pointers, `NULL`, `true`, `false`, `INT64_MIN`, and `INT64_C(...)`.
- GNU statement expressions `({ ... })`, used to sequence effectful operands and construct temporary values.
- GNU `__auto_type`, used for generated temporaries.
- Compiler builtins/attributes in the runtime: `__builtin_expect`, `__attribute__((noreturn, cold, noinline))`, and compiler-specific no-sanitize attributes.
- Generated global and local declarations, structure/enum representations, field access, casts, assignments, conditionals, loops, calls, returns and switch-like dispatch.
- Runtime macros and generated metadata for source locations, string literals, global roots and test mode.

The Makefile selects `-std=gnu11`, not strictly conforming ISO C11. The emitted program is therefore coupled to a GCC/Clang-compatible GNU C environment unless and until this surface is changed.

The generator explicitly hoists multiple effectful operands into temporaries to preserve Capstan's left-to-right evaluation order where C leaves operand/argument order unspecified. This is a semantic obligation for any replacement backend, not merely a code-generation style preference.

## 4. Generated runtime symbol inventory

The following names occur in `compiler/codegen.cap` as emitted runtime interfaces, macros, or generated-name prefixes. The list is derived from source-token scanning and is a navigation inventory; it is not a claim that every name is emitted by every program.

**Memory, values and initialisation:** `CAP_LIT`, `cap_alloc`, `cap_box_int`, `cap_vi`, `cap_vp`, `cap_init_globals`, `cap_gc_init`, `cap_gc_root`.

**Arithmetic and checked operations:** `cap_add`, `cap_sub`, `cap_mul`, `cap_div`, `cap_mod`, `cap_neg`, `cap_shl`, `cap_sar`, `cap_shr`, `cap_wrapping_add`, `cap_wrapping_sub`, `cap_wrapping_mul`, `cap_wrapping_shl`, and corresponding proved-operation variants where present.

**Strings and text:** `cap_str_at`, `cap_str_at_proved`, `cap_str_concat`, `cap_str_eq`, `cap_str_slice`, `cap_char_str`, `cap_int_to_str`, `cap_join`, `cap_taint_char`.

**Collections:** list operations (`cap_list_*`), packed-boolean-list operations (`cap_blist_*`), and map operations (`cap_map_*`).

**Authority:** `cap_grant_new`, `cap_grant_bind`, `cap_grant_check`, `cap_grant_policy_check`, `cap_grant_recheck`, plus generated policy-specific recheck names (`cap_recheck_*`).

**Security, crypto and validation:** `cap_hash`, `cap_hash_password`, `cap_hash_verify`, `cap_verify_password`, `cap_needs_rehash`, `cap_secret_eq`, `cap_escape_*`, `cap_validate_*`.

**IO, process and workspace-facing operations:** `cap_print`, `cap_println`, `cap_flush`, `cap_exit`, `cap_read_line`, `cap_read_bytes`, `cap_read_file`, `cap_read_file_max`, `cap_write_file`, `cap_workspace_open`, `cap_workspace_read_file`, `cap_workspace_close`, and argument/global metadata names.

The exact declaration, implementation and ownership of each generated symbol must be reconciled against the complete runtime and library source before this becomes a normative ABI inventory. In particular, collection and security operations also depend on internal helpers not emitted directly by the generator.

## 5. Runtime and platform boundary

`runtime/capstan_rt.h` is the generated program's principal runtime interface. It includes standard C headers for integer types, booleans, errno, limits, stdio, allocation, strings and non-local jumps; filesystem/process headers including `sys/stat.h`, `fcntl.h` and `unistd.h`; and `capstan_gc.h`.

Linux-specific code conditionally uses `sys/syscall.h` and an explicitly declared `openat2` ABI structure/constants. Workspace confinement therefore has a Linux kernel ABI dependency in addition to the general C/POSIX runtime boundary.

**Post-baseline integration note (PR #413):** the native CLI now has a Capstan-source driver in
`tools/native_driver.cap`. The driver is still compiled by the existing C-emitting compiler
and host C toolchain; it is not a C-free bootstrap stage. Its import loader uses the workspace
descriptor API with descriptor-relative `openat2` resolution, rejecting symlinks, magic links,
mount crossings, hard-linked files, oversized inputs and detected mutation during reads.
Unsupported kernel support fails closed. This improves source-path confinement for the native
CLI but does not make the integer file descriptor an unforgeable language capability, prove
the C runtime, or establish a Lean-to-runtime refinement theorem. This is a post-baseline
delta and is not silently folded into the pinned source revisions above.

The runtime uses process termination for failed runtime guards, with a test-mode `setjmp`/ `longjmp` path. It also owns IO, hashing/password operations, workspace access, grants, string operations and collection adapters. These operations are not all language semantics: each needs classification as (a) semantic rule, (b) Capstan runtime service, or (c) host/OS capability boundary.

`runtime/capstan_gc.h` adds dependencies on C allocation/integer facilities, pthreads, signals, process/stack facilities, and memory mapping (`sys/mman.h`). The collector discovers stack bounds and scans the stack/register spill area conservatively; it manages pages, size classes, large-object metadata, heap accounting, collection, and secret wiping. These mechanisms are part of the present trusted execution base and are target/ABI sensitive.

## 6. Preliminary trusted-base classification

| Component | Current role | C-free migration implication |
|---|---|---|
| `bootstrap/capstan0.py` | Unchecked stage-0 translator | Bootstrap trust and independent reproducibility must be addressed; self-hosting alone is insufficient. |
| Capstan compiler sources | Parse/check/lower and emit C | Must gain a specified typed IR and direct target path; generated-C semantics cannot be silently assumed. |
| GCC/Clang and linker | Translate generated C to executable | Retired from the ordinary target build/run path only after replacement conformance gates pass. |
| `capstan_rt.h` | Runtime checks, IO, authority, crypto, workspace and value helpers | Split semantic services from audited host ABI operations; define explicit ownership and failure contracts. |
| `capstan_gc.h` | Allocation, conservative collection, roots, accounting and secret wiping | Requires a target-specific memory/root model and implementation-linked assurance. |
| C/POSIX/Linux ABI | Process, file, memory, stack and platform services | Remains an explicit external boundary unless replaced by a separately specified host interface. |
| Python 3 / shell test environment | Bootstrap and test orchestration | Build/test dependencies must be distinguished from shipped-program runtime dependencies. |

## 7. Required next inventory passes

This note deliberately does not close Stage A. The following passes remain:

1. **Complete symbol reconciliation:** enumerate every emitted runtime symbol and generated data layout, then link it to its declaration, implementation, tests, and proposed semantic/host owner.
2. **Runtime source inventory:** cover all runtime headers and implementation units, including crypto, file/process/SQL, workspace, allocator/GC, secret storage and platform-specific code.
3. **Build/release inventory:** inspect all CI, fuzz, sanitizer, benchmark, packaging and release workflows for C/Python/shell/toolchain assumptions.
4. **Guarantee map:** trace each claimed semantic/security property from specification to checker, generated check, runtime, OS/library and test/proof evidence.
5. **Target/ABI matrix:** record supported and tested OS/architecture/compiler combinations and the exact assumptions made by stack scanning, calling convention, syscalls and memory mapping.
6. **Independent review:** have the inventory checked against the full source tree before choosing a native target or estimating replacement scope.

No native target, ABI, allocator, GC strategy or proof assistant is selected by this inventory. No C-free, compiler-correctness or implementation-verification claim is made.
