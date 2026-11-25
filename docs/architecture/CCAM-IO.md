# CCAM v0.2 output extension — byte-oriented design contract

**Status:** byte-output evaluator, formal output-transition model and Linux x86-64 native adapter are integrated on the `ccam/byte-output-evaluator-rebased-20261125` working branch through PRs #304, #306 and #307. PR #304 remains unmerged to `main`; the extension is experimental and does not amend normative CCAM v0.1.  
**Depends on:** CCAM v0.1, checked source-to-CCAM lowering, native backend  
**Initial use case:** compile `print("Hello, World!\\n")` to a freestanding native executable

## 1. Purpose and compatibility

Capstan `string` is a byte sequence, not a Unicode-scalar or grapheme sequence. Its length, indexing and slicing are byte-oriented. This extension therefore specifies byte output, not an implicit UTF-8 conversion.

The extension is append-only and preserves v0.1 semantics:

- v0.1 programs remain valid and retain their existing semantics;
- the first increment supports statically known string-literal bytes only;
- it introduces no string register type, heap, allocator, general file API, or ambient path authority;
- output order is instruction order and bytes are preserved exactly;
- output volume is bounded before execution;
- the native OS write adapter is an explicit trusted boundary.

Text APIs that require valid UTF-8 must validate it explicitly at their boundary. The output instruction itself does not validate, normalise, transcode, replace, or reinterpret bytes.

## 2. Abstract output trace

Extend the machine configuration with an append-only byte sequence `stdout_bytes`, initially empty, and an execution limit `maxOutputBytes`.

The trace is a sequence of octets observable by the embedding environment. Embedded NUL and arbitrary byte values are permitted. This is deliberately not a Capstan heap string and does not imply that the trace is valid UTF-8.

`maxOutputBytes` is a non-negative exact integer. Before constructing execution state, the implementation MUST reject a negative value or a value above its implementation-defined admission ceiling. The initial implementation ceiling is 1,048,576 bytes. All additions and conversions used for capacity checks MUST be overflow-safe.

## 3. New instruction

Add one instruction to the v0.2 extension:

| Instruction | Exact fields | Semantics |
|---|---|---|
| `emit_bytes` | `op:CCAM_OP_EMIT_BYTES, byte_data:List<int>` | Append the exact bytes of `byte_data` to `stdout_bytes`. |

The current Capstan-native representation stores the payload as `List<int>`, with each element validated to be in the inclusive range 0..255. Its byte length is `byte_data.len()`; no Unicode interpretation is performed. The future JSON wire representation is exactly `{ "op": "emit_bytes", "data": <string> }`; its serialized decoder is a separate bounded-validation workstream and is not part of the current in-memory instruction representation.

Before changing machine state, execution MUST check:

`stdout_bytes.length + byte_data.len() <= maxOutputBytes`

If the check fails, execution traps with `output_limit` and leaves `stdout_bytes` unchanged. If it succeeds, the complete byte sequence is appended to the abstract trace. The instruction consumes exactly one CCAM step, regardless of byte length. Empty data is valid, appends no bytes, and still consumes one step.

The instruction is an effect barrier: a compiler or optimiser MUST NOT remove, reorder, merge across, or duplicate it unless a refinement proof establishes identical output traces and trap behaviour.

## 4. Validation and resource rules

The typed in-memory validator MUST admit `CCAM_OP_EMIT_BYTES` only with a byte payload whose elements are all in 0..255. The current implementation validates the `List<int>` representation. When the JSON wire representation is enabled, its closed schema MUST admit exactly `{ "op": "emit_bytes", "data": <string> }` and reject missing, extra, duplicate or wrongly typed fields. The serialized decoder remains a separate integration gate and MUST NOT be claimed complete until its tests pass.

The decoder must enforce an encoded literal size limit before allocating a decoded representation. Aggregate output literal bytes in one program MUST be bounded; the initial admission ceiling is 1 MiB. The evaluator's `maxOutputBytes` MUST be no greater than that ceiling in the first implementation.

The validator MUST account for literal byte length when applying program resource limits. No untrusted length may be used for allocation or indexing before overflow-safe bounds checks. The validator MUST preserve embedded NUL and every other byte exactly.

## 5. Source lowering

The first source-level bridge may lower only direct calls to the existing `print` and `println` builtins whose sole argument is a string literal:

- `print("Hello, World!")` emits one `emit_bytes` instruction containing the literal's decoded bytes;
- `println("Hello, World!")` emits the literal bytes followed by exactly one LF byte (0x0A), matching the existing builtin contract;
- interpolated strings, concatenation, local string variables, tainted strings, secret values, and arbitrary string expressions MUST be rejected by this initial lowerer.

The current lexer decodes supported escapes such as `\\0` into bytes, then stores `escape_c(decoded)` in the token and AST string field; the AST's integer length records the decoded byte count. That escaped representation is suitable for generated-C literals but is not itself the original byte sequence.

The current implementation uses a shared, bounded decoder for the canonical `escape_c()` representation and produces a `List<int>` of exact source bytes. The AST's escaped field is therefore not treated as raw bytes and is not UTF-8 encoded a second time. Retaining decoded bytes separately in the AST remains a valid future alternative, but the present lowerer uses the shared decoder. Tests cover quotes, backslashes, octal bytes, NUL, empty strings and multibyte source bytes; broader lexer escape round-trip coverage remains part of conformance work.

The existing lowerer resolves direct calls through its user-function table. It must explicitly recognise the existing `print` and `println` builtins before user-function lookup, then independently verify the one-literal-argument AST shape and output byte budget. It MUST preserve source order relative to calls, traps, and other effects.

## 6. Native output adapter

The Linux x86-64 prototype may implement the abstract trace by embedding each literal byte sequence in read-only data and issuing `write(1, ptr, remaining)` via the Linux syscall ABI.

The adapter MUST:

1. preserve exact bytes, including NUL and non-ASCII byte sequences;
2. advance the pointer after a positive partial write;
3. retry when interrupted (`-EINTR`), with a finite consecutive-interruption retry bound;
4. treat a zero-byte write with remaining bytes, or any other negative result, as an OS output failure;
5. never spin on a zero-byte write or retry interruption without a bound;
6. keep all literal offsets and lengths within the emitted read-only data section;
7. account for each successfully written prefix against the output budget;
8. ignore `SIGPIPE` so a closed stdout pipe is observed as `EPIPE` and follows the output-failure path.

The current prototype uses a 64-consecutive-`EINTR` retry bound. It installs `SIG_IGN` for `SIGPIPE` with the Linux x86-64 `rt_sigaction` syscall before entering the program. Its process statuses are 76 for the CCAM output-limit trap, 77 for an output syscall failure, and 78 if signal setup fails. These values are platform-adapter statuses, not CCAM trap encodings.

The CCAM abstract machine specifies the output trace, not Linux file-descriptor behaviour. A native write failure is therefore a platform-adapter failure. A partial prefix may already have reached the host before such a failure; the adapter MUST NOT claim rollback or atomicity at the OS boundary.

The first target remains Linux x86-64 only. Other OS targets require separate ABI adapters and tests; they must not inherit Linux syscall numbers or assumptions.

## 7. Required conformance tests

Add Capstan-native evaluator and validator tests for:

- empty output;
- ASCII output and exact byte order;
- multibyte UTF-8 source text preserved as its original UTF-8 bytes (without machine-level decoding);
- embedded NUL;
- concatenation of multiple output instructions in source order;
- exact output-budget boundary and one-byte-over rejection;
- no output mutation when an output-limit trap occurs;
- empty and non-empty instruction step accounting;
- preservation of output instructions across lowering and optimisation;
- fail-closed rejection of unsupported source expressions and non-literal arguments.

Add Linux x86-64 execution tests that compare captured stdout byte-for-byte, exercise a partial-write test adapter where practical, and verify that write failure cannot cause an infinite loop. The native tests must assemble and link without a C compiler or C runtime.

## 8. Proof and assurance obligations

The formal model must extend the machine state with the output trace and output budget. Prove that:

- a successful `emit_bytes` appends exactly its input byte sequence;
- a rejected output-limit instruction leaves the trace unchanged;
- trace length never exceeds `maxOutputBytes`;
- instruction-step accounting remains exact;
- source lowering preserves byte identity and effect ordering.

The native backend refinement must relate emitted bytes and instruction order to the abstract output trace. Linux syscall handling, partial writes, EINTR and file-descriptor semantics remain explicit assumptions or separately verified adapter properties.

No claim of Unicode text semantics, general string support, dynamic IO, portable IO, runtime equivalence, or C-free self-hosting follows from this proposal.

## 9. Acceptance gate

Do not mark the v0.2 byte-output extension integrated until the schema, Capstan evaluator, validator, source lowerer, Linux native adapter, exact-byte tests, formal model and assurance matrix agree. The existing v0.1 contract remains unchanged until a reviewed version transition is accepted.
