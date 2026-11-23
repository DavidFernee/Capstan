# Capstan and memory-safe language guidance

This statement maps Capstan's guarantees to the memory-safety guidance published by the Five Eyes
cyber security agencies, including the Australian Signals Directorate's Australian Cyber Security
Centre (ASD's ACSC). It describes Capstan 0.4.0 (unreleased) as it is in this repository. Each claim
names the test or document that demonstrates it; where something is not yet done, it says so.

## The guidance

| Publication | Agencies | Date |
|---|---|---|
| [Software Memory Safety](https://media.defense.gov/2022/Nov/10/2003112742/-1/-1/0/CSI_SOFTWARE_MEMORY_SAFETY.PDF) (Cybersecurity Information Sheet) | NSA | 10 November 2022 |
| [The Case for Memory Safe Roadmaps](https://media.defense.gov/2023/Dec/06/2003352724/-1/-1/0/THE-CASE-FOR-MEMORY-SAFE-ROADMAPS-TLP-CLEAR.PDF) | CISA, NSA, FBI, ASD's ACSC, Canadian Centre for Cyber Security, NCSC-UK, NCSC-NZ, CERT NZ | 6 December 2023 ([ASD's ACSC notice](https://www.cyber.gov.au/about-us/view-all-content/news-and-media/case-for-memory-safe-roadmaps), 7 December 2023) |
| [Exploring Memory Safety in Critical Open Source Projects](https://www.cyber.gov.au/business-government/secure-design/secure-by-design/exploring-memory-safety-in-critical-open-source-projects) | CISA, FBI, ASD's ACSC, Canadian Centre for Cyber Security | 26 June 2024 (ASD's ACSC, 27 June 2024) |
| [Memory Safe Languages: Reducing Vulnerabilities in Modern Software Development](https://www.cisa.gov/resources-tools/resources/memory-safe-languages-reducing-vulnerabilities-modern-software-development) (Cybersecurity Information Sheet) | NSA, CISA | 24 June 2025 |
| [Information Security Manual](https://www.cyber.gov.au/ism/guidelines-for-software-development), Guidelines for software development, ISM-2041 | ASD | September 2026 edition |

The common message: memory-safety bugs (out-of-bounds access, use after free, double free,
uninitialised memory) are a large share of serious vulnerabilities; memory-safe languages are the
most complete mitigation; memory-safe languages still carry risk where they allow unsafe code,
call C or C++ libraries, or depend on components written in memory-unsafe languages; and
organisations should publish roadmaps for removing memory-unsafe code. ISM-2041 asks that
memory-safe languages are used, or, less preferably, memory-safe practices.

## What Capstan guarantees today

Code written in Capstan cannot express the memory-safety weaknesses below. The table uses the
CWE classes that The Case for Memory Safe Roadmaps names (it groups them under CWE-1399,
Comprehensive Categorization: Memory Safety), plus the related classes in the 2025 NSA and CISA
sheet.

| Weakness | How Capstan prevents it | Evidence |
|---|---|---|
| Out-of-bounds read and write (CWE-125, CWE-787, CWE-119) | No pointers or pointer arithmetic. Every string and list access is bounds-checked and stops the program safely (exit code 101) when out of range. The range analysis leaves out a check only where it proves the index in range; `--keep-checks` keeps every check | `tests/runtime/out_of_bounds_read.cap`, `out_of_bounds_write.cap`, `negative_index.cap`, `range_*.cap`; [CWE-COVERAGE.md](../CWE-COVERAGE.md), "Checks proved unnecessary" |
| Classic buffer overflow (CWE-120) | `strcpy`, `memcpy` and `gets` do not exist | `tests/reject/buffer_overflow_strcpy.cap` |
| Use after free, double free (CWE-416, CWE-415) | Memory is managed by a garbage collector; programs cannot free memory | `tests/reject/double_free.cap`; `tests/gc/` (collector stress, churn) |
| Uninitialised variables and fields (CWE-457, CWE-908) | Every declaration needs an initialiser and `new` needs every field | `tests/reject/uninitialised_variable.cap`, `uninitialised_field.cap` |
| Null dereference (CWE-476) | No null; optional values must be unwrapped with `if (let ...)` | `tests/reject/null_dereference.cap`, `null_method.cap`, `optional_*.cap` |
| Integer overflow and underflow leading to memory errors (CWE-190, CWE-191) | All arithmetic is checked; overflow stops the program safely | `tests/runtime/integer_overflow.cap`, `integer_underflow.cap` |
| Format strings (CWE-134) | There are no format strings | `tests/reject/format_string.cap` |
| Stack exhaustion (CWE-674) | Runaway recursion stops safely through a stack guard | `tests/runtime/stack_overflow.cap` |
| Data races (CWE-362) | Capstan has no threads or shared memory yet, so a data race cannot be written. Safe concurrency is planned for v0.7 | [DESIGN-MAP.md](../DESIGN-MAP.md), section 4, v0.7 |

The CWE atlas ([CWE-ATLAS.md](../CWE-ATLAS.md)) attempts each of about 250 code-level weaknesses and
re-checks every verdict on each test run (`tests/cwe/atlas.py`). None of its five remaining gaps is a
memory-safety weakness.

**No unsafe subset.** The guidance warns that memory-safe languages lose their guarantee where
developers use unsafe features (for example Rust's `unsafe`). Capstan has no unsafe code construct.
Its one escape hatch, `trust("why")`, marks untrusted text as trusted; it cannot create a pointer,
skip a bounds check or free memory, it needs a written justification, and every build reports it as
an `AUDIT` warning (`tests/reject/trust_without_reason.cap`; [DESIGN-MAP.md](../DESIGN-MAP.md),
principle 4).

**No foreign calls.** The guidance notes that guarantees are qualified where data crosses into C or
C++ libraries. Capstan programs cannot call foreign code today. When interop arrives (v0.10), foreign
code is to run isolated, in a separate process or a WebAssembly sandbox, with its results typed as
`Tainted` ([DESIGN-MAP.md](../DESIGN-MAP.md), section 4, v0.10).

## What is not yet memory-safe

Capstan's guarantees hold for code written in Capstan. They rest on components that are not:

- **The runtime is C.** About 1,400 lines (`runtime/capstan_rt.h`, `runtime/capstan_gc.h`) provide the
  checks, collections, cryptography and the garbage collector. A bug there can corrupt memory.
- **The C standard library is trusted.** The runtime calls libc for I/O, memory and number formatting.
- **The C compiler is trusted.** Capstan compiles to C, and GCC or Clang compiles that C.
- **The garbage collector scans conservatively.** It is non-moving and scans the stack and object
  contents conservatively, so a value that looks like a pointer can keep memory alive. This can retain
  memory; it cannot free live memory.

How these are tested meanwhile: the runtime unit tests against published vectors, the whole runtime,
compiler and formatter under AddressSanitizer and UndefinedBehaviorSanitizer, collector stress,
differential fuzzing against the independent stage-0 implementation, and identical results at
`-O0`, `-O2` and `-O3` with GCC and Clang ([TESTING.md](../TESTING.md)). Testing reduces this risk; it
does not remove it.

Not yet done:

- Generated programs are compiled without explicitly enabling the C compilers' exploit mitigations
  (stack protector, control-flow integrity, position-independent executables, `_FORTIFY_SOURCE`):
  `bin/capstan` uses `-O2 -std=gnu11 -w`. Whatever the platform's compiler enables by default applies.
  Planned under "Defence in depth" in [DESIGN-MAP.md](../DESIGN-MAP.md), section 6.
- Hardware memory protection (CHERI, Arm Memory Tagging Extension), which the 2023 guidance mentions,
  is not used.

## Capstan's memory-safe roadmap

The Case for Memory Safe Roadmaps asks manufacturers to publish a roadmap with dated phases, a plan
for external dependencies, transparency and CWE reporting. Capstan's equivalents:

| Roadmap element in the guidance | Capstan |
|---|---|
| Phases with outcomes | Trusted base reduction, stages T1 to T12 ([DESIGN-MAP.md](../DESIGN-MAP.md), section 6), each tied to a version. Calendar dates are not set |
| Date after which new code is in a memory-safe language | Already true for the compiler and formatter, which are written in Capstan and pass the compiler's own `--strict --release` checks (`tests/run.sh`, bootstrap section). The runtime moves to verified Capstan at T7 and T8 (v0.8, v0.9) |
| Prioritise security-critical code (parsing, networking, cryptography) | Cryptography (T3), number formatting and parsing (T4) and network parsing (T5) are the first runtime components planned to move into Capstan |
| External dependency plan | libc leaves the trusted base at T6 (a thin system-call layer); the C compiler becomes optional with CompCert (T9), then unnecessary with the WebAssembly (T10) and native (T11) backends |
| Run old and new side by side | Each replaced component is tested against the one it replaces (section 6); stage 0 is already used this way for code generation |
| Interim mitigations for unsafe code | Fuzzing, sanitisers and coverage of the runtime: done. Compiler exploit mitigations and a hardened allocator: not yet |
| Transparency | This document, [CWE-COVERAGE.md](../CWE-COVERAGE.md), [CWE-ATLAS.md](../CWE-ATLAS.md) and the changelog are updated each release |
| CWE for every CVE | Every safety diagnostic names its CWE. [SECURITY.md](../../SECURITY.md) commits to an advisory for every confirmed issue; no advisory has yet been issued |

## Summary

Capstan meets the central recommendation, use a memory-safe language, for code written in Capstan,
with no unsafe subset and no foreign calls. It does not yet meet it for its own foundation: the
runtime, the C library and the C compiler are memory-unsafe and trusted, as
[THREAT-MODEL.md](THREAT-MODEL.md) records. The plan to remove them is published, and is not finished.
