# A01 — Native backend traceability (RTM-003)

Pinned main 2409357ea777a3875bc608106fce5e42eb233656. Static audit only. Backend verification/ccam_native_x64.cap blob e3eee99; architecture CCAM-NATIVE-BACKEND.md f70ef34; historical research/native-bootstrap/NATIVE-RESULT-ABI.md 8f3be66. Active #552/#555 work must be reconciled before implementation; #533 is merged.

| ID | Requirement | Existing evidence | Acceptance gap |
|---|---|---|---|
| R07.01 | Validate before emission | ccam_x64_emit_linux_elf | Prove accepted profile and rejection before output |
| R07.02 | Bound code expansion | 8192 instructions, 65536 registers; expansion test | Bound emitted bytes, intermediate storage and compilation work |
| R07.03 | Disjoint aligned stack slots | ccam_x64_slot, ccam_x64_init_slot | Prove offsets, alignment, initialization flag isolation |
| R07.04 | Exact read-before-write traps | ccam_x64_check_initialized | All instruction variants, competing fault cases |
| R07.05 | Arithmetic instruction selection | ccam_x64_emit_instruction; overflow, remainder tests | Universal machine simulation, not assembly text matching |
| R07.06 | Branch target integrity | ccam_x64_instruction_label; loop test | Every relocation/branch resolves to intended instruction boundary |
| R07.07 | ABI preservation | ccam_x64_emit_function; six integer argument ceiling | Argument order, return values, callee saves and alignment |
| R07.08 | Dedicated bounded stack | mmap PROT_NONE, guard page, bounded depth | Prove total mapped size including guard and actual stack use |
| R07.09 | Platform failure distinction | stack allocation trap label | Separate host failure from machine traps, exact record |
| R07.10 | Exact result transport | legacy exit status; candidate fd3 record | Injective typed outcomes including Bool or explicit canonical mapping |
| R07.11 | Strict bounded result parser | candidate 48-byte header and 1136-byte maximum | Reject malformed, stale, partial, extra records; bind function index/name |
| R07.12 | Bounded result writes | candidate bounded short-write/EINTR policy | Explicit attempt budget and launcher timeout for blocked syscall |
| R07.13 | Output byte preservation | output literal emission; NUL/UTF8 and budget tests | Exact trace and partial-write semantics; output independent of result |
| R07.14 | Object and relocation correctness | GNU as/ld baseline | Direct encoder/ELF evidence and checked relocation overflow |
| R07.15 | Executable permission integrity | GNU-stack note, historical no PT_INTERP checks | Verify W^X, entry mapping, segment ranges, no undefined dependencies |
| R07.16 | Deterministic artifact generation | deterministic label helpers | Identical bytes from pinned inputs; toolchain manifest |
| R07.17 | Workspace import confinement | architecture openat2 contract | Audit current driver; adversarial syscall and file identity tests |
| R07.18 | Final executable refinement | no theorem identified in pinned backend docs | Independent checker or proof covering actual bytes, loader and ABI |

## Findings

N-01: Backend architecture documentation describes BSS stack and no output; pinned implementation emits mmap-backed guarded stack and output tests. Reconcile the direct-result transport and legacy backend documentation in #552 before treating it as design authority.
N-02: Historical result ABI specifies unsigned 0xffffffff no-location sentinel in header but describes zero sentinels in outcome prose. Resolve explicitly; reject noncanonical alternatives. Its candidate kinds omit Bool; determine canonical entry contract before adoption, not silently coerce.
N-03: Specifying bounded retry attempts is necessary but does not bound elapsed blocking syscall time. Launcher must enforce an explicit timeout and classify termination without fabricating a machine result.
N-04: GNU assembler/linker and host loader remain part of the artifact assurance boundary even when generated executable has no C runtime; direct ELF generation requires independent byte-level checking, not merely replacing tools.
N-05: Stack budget must distinguish usable stack, mapping and guard page; prove exact charging and checked arithmetic, including boundary rounding. This is an acceptance obligation rather than a reproduced overflow.

## Acceptance corpus

For every admitted scalar instruction: same validated CCAM, reference outcome, native outcome, exact value/trap/location/steps and output trace. Include invalid input (no executable), fuel zero, call depth one, MIN/MAX, 0/256, negative result, void, malformed result records, closed fd, timeout, stack-map failure, branch displacement boundaries, invalid ELF ranges and reproducible artifacts. Separate compile rejection, machine outcome and platform failure. Record exact commit and toolchain digests. No tests or fresh CI executed in this tranche. All 18 rows remain unaccepted.
