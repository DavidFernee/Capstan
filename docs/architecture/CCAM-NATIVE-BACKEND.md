# CCAM Native Backend: Linux x86-64

**Status:** experimental freestanding backend integrated in PR #212; the user-facing native CLI remains under review in PR #228  
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

The prototype maps dynamic trap classes to distinct process exit statuses: integer overflow (70), division by zero (71), explicit trap (72), step limit (73), call-depth limit (74), and uninitialised register (75). It does not yet preserve structured trap locations/details or expose a stable public trap ABI. Unsupported instructions, argument counts, entry signatures, and invalid machine limits are rejected by the emitter before assembly is returned. The native backend also applies stricter expansion ceilings of 8,192 total instructions and 65,536 aggregate registers before validation or assembly allocation; these are backend resource limits, not changes to the CCAM language limits.

## 4. Validation and testing

The emitter first calls the multi-function CCAM validator. Tests generate assembly from checked Capstan source for a direct `add(19, 23)` call and verify that the output contains a freestanding `_start`, direct function calls, syscall exit, and configured resource limits, with no C include or Capstan runtime reference.

On Linux x86-64, the integration test assembles with `as --64`, links directly with `ld`, and executes the resulting ELF. The expected process exit status is 42. Additional freestanding execution vectors cover a loop/conditional, bounded recursion on the dedicated stack, addition and signed-division overflow, division by zero, step limit, call-depth limit, and an uninitialised-register read. Each ELF is checked to have no `PT_INTERP` program header and no undefined external symbols before execution. The tests do not use a C compiler or C runtime to build or run the target programs. Other CI platforms currently check code generation only; the Linux ELF artifact is not portable to macOS or Windows.

## 5. Explicit gaps

This is not yet a production backend. It does not support strings, output, heap objects, aggregates, globals, foreign calls, more than six integer-class arguments, Windows ABI, macOS Mach-O, AArch64, or a complete runtime. Trap details are reduced to exit statuses. There is no Lean theorem proving that emitted machine code simulates CCAM, and no differential conformance suite yet compares every supported CCAM instruction against the native executable.

Next work:

1. execute the same conformance vectors through the Capstan evaluator and native ELF, comparing values and trap outcomes;
2. add a formal semantics for the emitted subset and prove instruction-selection / calling-convention simulation;
3. add AArch64 Linux and macOS targets, then Windows x86-64 with a separately specified ABI;
4. implement the minimum native runtime and output syscall interface for a C-free Hello World;
5. wire a target-selecting native build command into the compiler CLI and keep generated-C as an explicit compatibility backend only;
6. replace the C-dependent bootstrap and runtime, then demonstrate a reproducible self-hosting chain with no C compiler/runtime in the trusted path.
