# CCAM Native Backend: Linux x86-64

**Status:** experimental freestanding Linux x86-64 backend; executable tests and native CLI integration are present, but full CCAM conformance, lossless terminal-result transport and compiler/refinement assurance remain open  
**Input:** validated multi-function CCAM v0.1 scalar subset  
**Target:** freestanding Linux x86-64 ELF, System V AMD64 calling convention, GNU assembler syntax

## 1. Workspace loader security boundary

The driver bounds the import queue to 256 paths and aggregate source bytes to 64 MiB, in addition to the per-file compiler source limit. The CLI selects a canonical workspace root and converts initial source paths to relative paths beneath it. The driver opens that root once and retains the directory descriptor while loading the complete import graph.

Each source is opened with Linux `openat2` relative to the pinned root descriptor using `RESOLVE_BENEATH | RESOLVE_NO_SYMLINKS | RESOLVE_NO_MAGICLINKS | RESOLVE_NO_XDEV`. Only singly linked regular files are accepted; hard-linked aliases are rejected. The read is bounded, the opened inode is pinned by its descriptor, and metadata is checked again after the read. Root-path or file-path symlinks, magic links, dot-segment traversal, mount crossings, non-regular files and kernels without `openat2` fail closed. There is no check-then-open fallback.

The root descriptor is an integer process capability used only by the trusted native driver; it is not an unforgeable language-level sandbox type. General `read_file` and `write_file` remain ambient APIs. This loader hardens the native compiler's source-import boundary, but it does not by itself sandbox arbitrary Capstan programs or establish a process-wide filesystem policy.

## 1. Contract

The native backend is a consumer of validated CCAM, not a second source-language compiler. It must not reinterpret source AST nodes or bypass structural validation. The pipeline is:

```
Capstan source
  -> lexer / parser / checker
  -> checked scalar AST
  -> deterministic CCAM lowering
  -> multi-function CCAM validation
  -> native x86-64 assembly
  -> GNU as
  -> GNU ld
  -> freestanding ELF executable
```

The assembler and linker are used as object-format tools. No C source is emitted, no C compiler is invoked for the target program, and no libc or Capstan C runtime is linked into the target executable. The compiler that produces the assembly remains bootstrapped through the repository's existing C-dependent build and runtime; that is a separate bootstrap trust boundary and means the compiler toolchain is not yet end-to-end C-free.

## 2. Supported instruction subset

The prototype emits:

- integer and boolean constants, typed moves;
- checked signed-64 add, subtract and multiply;
- checked signed-64 divide and remainder, including zero and MIN/-1 cases;
- integer equality and signed less-than comparisons;
- boolean negation;
- conditional and unconditional branches;
- direct calls and typed integer/boolean/void returns;
- explicit trap exits.

Each CCAM virtual register is assigned an eight-byte value slot and an eight-byte initialized flag in its function frame. Flags are cleared on frame entry, set on parameter transfer and every write, and checked before every read so the evaluator's uninitialised-register trap is preserved. Parameters and up to six call arguments use the System V integer argument registers. Caller values remain in stack slots across calls. The frame size is rounded to a 16-byte multiple to preserve call-site stack alignment.

## 3. Dynamic limits and traps

The emitted program maintains process-global step and call-depth counters and switches to a dedicated, 16-byte-aligned BSS stack sized conservatively from the largest function frame and configured maximum depth. This prevents the host process's default stack limit from silently changing CCAM call-depth behaviour. The backend caps this stack allocation at 32 MiB. It checks the step budget before dispatching each CCAM instruction and checks call depth before entering a callee. The initial frame counts as depth one, matching the reference evaluator.

The prototype maps dynamic trap classes to distinct process exit statuses: integer overflow (70), division by zero (71), explicit trap (72), step limit (73), call-depth limit (74), and uninitialised register (75). It does not yet preserve structured trap locations/details or expose a stable public trap ABI. More importantly, an `int main` result is transported through Linux process exit status, which exposes only the low eight bits; this is not a lossless encoding of CCAM `Halt(Int64)`. A separate bounded terminal-result channel is required before native execution can claim full CCAM outcome equivalence. Unsupported instructions, argument counts, entry signatures, and invalid machine limits are rejected by the emitter before assembly is returned. The native backend also applies stricter expansion ceilings of 8,192 total instructions and 65,536 aggregate registers before validation or assembly allocation; these are backend resource limits, not changes to the CCAM language limits.

## 4. Validation and testing

The emitter first calls the multi-function CCAM validator. Tests generate assembly from checked Capstan source for a direct `add(19, 23)` call and inspect the freestanding `_start`, direct function calls, syscall use and configured resource limits, with no C include or Capstan runtime reference.

On Linux x86-64, the integration test assembles with `as --64`, links directly with `ld`, and executes the resulting ELF. The current executable corpus covers a loop/conditional, bounded recursion on the dedicated stack, arithmetic and division traps, step limit, call-depth limit, uninitialised-register reads, Hello World output, exact NUL/UTF-8 output bytes, output-budget rejection and broken-pipe failure. Each ELF is checked to have no `PT_INTERP` program header and no undefined external symbols before execution. These tests establish useful execution evidence for the prototype, not complete CCAM outcome equivalence: the process exit status is lossy for full-width returns, trap identity/details are incomplete, and the output adapter has platform-specific failure behaviour. The tests do not use a C compiler or C runtime to build or run target programs. Other CI platforms currently check code generation only; the Linux ELF artifact is not portable to macOS or Windows.

## 5. Explicit gaps

This is not yet a production backend. It does not support strings, output, heap objects, aggregates, globals, foreign calls, more than six integer-class arguments, Windows ABI, macOS Mach-O, AArch64, or a complete runtime. Trap details are reduced to exit statuses. There is no Lean theorem proving that emitted machine code simulates CCAM, and no differential conformance suite yet compares every supported CCAM instruction against the native executable.

Next work:

1. execute the same conformance vectors through the Capstan evaluator and native ELF, comparing values and trap outcomes;
2. add a formal semantics for the emitted subset and prove instruction-selection / calling-convention simulation;
3. add AArch64 Linux and macOS targets, then Windows x86-64 with a separately specified ABI;
4. implement the minimum native runtime and output syscall interface for a C-free Hello World;
5. wire a target-selecting native build command into the compiler CLI and keep generated-C as an explicit compatibility backend only;
6. replace the C-dependent bootstrap and runtime, then demonstrate a reproducible self-hosting chain with no C compiler/runtime in the trusted path.

## Direct ELF prototype

On Linux x86-64, `capstan native --direct --root . main.cap -o program` uses the
same workspace loader, source checker and CCAM lowering as the assembler-backed
command. The backend validates the CCAM and writes a static ELF image directly.
The image has one read/execute load segment and an explicit non-executable stack.
The driver still builds through the C-backed toolchain. Generation and execution
of the target ELF require neither an assembler nor a linker.

The profile admits one parameterless, integer-returning function with at most
252 CCAM instructions and 256 typed registers. Constants, moves, signed checked
arithmetic, comparisons, boolean negation, branches, loops and returns are
supported. An instruction can load a register only when every incoming path
has initialized it. Calls and byte output are outside this profile. Each instruction charges
one step before dispatch, including jumps, returns and explicit traps. An
exhausted budget exits before the next instruction's effects. The default is
1,000,000 steps. Pass `--direct-steps N` to set a budget from 0 through
10,000,000. Image size is separately limited by the static instruction count.

Run the executable with a fresh writable regular file on descriptor 3.

```sh
./program 3>result.bin
od -An -td8 result.bin
```

Exit status 0 carries exactly eight little-endian bytes containing the signed
return value. Status 70 denotes integer overflow, 71 division or remainder by
zero, 72 an explicit CCAM trap, and 73 instruction budget exhaustion. Status 77 means the result write failed or
was short. Discard the file on any nonzero status. Use a regular file as the
result sink. The prototype uses a single write and does not retry interruptions.
Trap detail, instruction count, and location are outside this transport profile.

The standard test runner executes this profile on Linux x86-64 with assembler
and linker paths set to nonexistent files. It checks full-width signed results,
arithmetic traps, branch joins, bounded loops, exact reference step limits,
malformed CCAM, byte-identical rebuilds and
output failure paths. Native-code refinement and C-free self-hosting remain
open.

### Scalar terminal outcome baseline

The direct backend's current result transport is an experimental projection of
the validated single-entry CCAM machine. This table records the implemented
boundary for the native architecture RFC's T3 work.

| Reference terminal outcome | Linux exit status | Bytes written to fd 3 |
| --- | ---: | --- |
| Integer return | 0 | Exactly eight signed little-endian bytes |
| `integer_overflow` | 70 | None |
| `division_by_zero` | 71 | None |
| `explicit_trap` | 72 | None |
| `step_limit_exceeded` | 73 | None |
| Result write fails or is short | 77 | Discard any partial bytes |

Status 77 is a platform transport failure. Compilation and validation failures
produce no replacement executable. For traps, the reference machine carries
the function, instruction PC, detail string and charged step count. The
current transport carries the trap class only. Resource exhaustion is checked
before dispatch at the pending PC. An arithmetic or explicit trap reached by
dispatch consumes that instruction's step.

The Linux tests emit an executable and run the reference evaluator from the
same typed CCAM fixture and step budget. They compare the implemented
projection, including zero bytes for each trap, and assert expected reference
PCs, step counts and details separately. The result record proposal in
[Native Result ABI](../../research/native-bootstrap/NATIVE-RESULT-ABI.md)
would need versioning, a byte-level consumer and end-to-end checks for the
additional observable fields before adoption.

### Experimental versioned terminal record

Use `capstan native --direct --direct-record --root . main.cap -o program`
to opt in to the scalar subset of the proposed CCAMRES v1 format. Pass a
fresh writable regular file on descriptor 3. The raw-result mode remains
the default.

The record starts with the 48-byte little-endian header described in
[Native Result ABI](../../research/native-bootstrap/NATIVE-RESULT-ABI.md).
An integer return carries its signed 64-bit value and charged step count
with both location fields set to `0xffffffff`. A trap carries its code,
charged steps, function index zero, current CCAM PC, and function name.
Explicit traps append the exact detail bytes. The invariant is one record
of 48 through 1,136 bytes, with the declared name and detail lengths.
The PC identifies the pending instruction for fuel exhaustion and the
dispatched instruction for every other supported trap.

Process status 0 confirms the complete record was written, including
records that describe CCAM traps. Status 76 reports a failed or short
write. Discard any bytes when status is nonzero. This prototype uses
one write to the caller's regular file, so interrupted and short writes
fail rather than retrying. The proposed bounded retry protocol and
production record consumer remain open.
