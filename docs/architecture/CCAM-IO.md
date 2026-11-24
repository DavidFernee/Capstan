# CCAM v0.2 output extension — design contract

**Status:** proposal for review; does not amend normative CCAM v0.1  
**Depends on:** CCAM v0.1, checked source-to-CCAM lowering, native backend  
**Initial use case:** compile `print("Hello, World!\\n")` to a freestanding native executable

## 1. Purpose and compatibility

CCAM v0.1 deliberately excludes strings and IO. This document specifies the smallest additive extension needed for deterministic, bounded literal output. It is a proposed CCAM v0.2 extension, not an assertion that the v0.1 machine or the current native prototype already supports IO.

The extension must preserve the following boundaries:

- v0.1 programs remain valid and retain their existing semantics;
- the first increment supports only statically known UTF-8 byte sequences;
- it does not introduce a string register type, heap, allocator, general file API, or ambient path authority;
- output order is instruction order and output bytes are exact;
- output volume is bounded before execution;
- the native OS write adapter is an explicit trusted boundary, not part of a CCAM proof unless separately modelled.

## 2. Abstract output trace

Extend the machine configuration with an append-only byte sequence `stdout_bytes`, initially empty, and an execution limit `maxOutputBytes`.

The abstract output trace is not a Capstan heap string. It is a sequence of octets observable by the embedding environment after or during execution. It is deliberately byte-oriented so embedded NUL and all valid UTF-8 encodings are unambiguous.

`maxOutputBytes` is a non-negative exact integer. Before constructing the execution state, the implementation MUST reject a negative value or a value above its implementation-defined admission ceiling. The initial implementation ceiling should be 1,048,576 bytes. The implementation MUST check the addition without overflow.

## 3. New instruction

Add one instruction to the v0.2 extension:

| Instruction | Exact fields | Semantics |
|---|---|---|
| `emit_utf8` | `op:string, data:string` | Encode `data` as UTF-8 and append those bytes to `stdout_bytes`. |

The `data` value MUST contain only Unicode scalar values. Unpaired UTF-16 surrogate code points and malformed input encodings are invalid. Encoding MUST be canonical UTF-8 (shortest form); no normalisation, case folding, newline conversion, or locale transformation is performed. Embedded U+0000 is permitted and emits byte 0x00.

Before changing machine state, execution MUST determine the encoded byte length and check:

`stdout_bytes.length + encoded_length <= maxOutputBytes`

If the check fails, execution traps with `output_limit` and leaves `stdout_bytes` unchanged. If it succeeds, the complete byte sequence is appended atomically to the abstract trace. The instruction consumes exactly one CCAM step, regardless of its byte length. An empty string is valid, appends no bytes, and still consumes one step.

The instruction is an effect barrier: a compiler or optimiser MUST NOT remove, reorder, merge across, or duplicate it unless a refinement proof establishes identical output traces and trap behaviour.

## 4. Validation and resource rules

The closed instruction schema MUST admit exactly `{ "op": "emit_utf8", "data": <string> }` for this opcode and reject missing, extra, duplicate, or wrongly typed fields.

Validation MUST reject malformed Unicode scalar sequences before execution. The decoder must enforce an encoded literal size limit before allocating a decoded representation. The aggregate encoded output literals in one program MUST be bounded; the initial admission ceiling is 1 MiB. The evaluator's `maxOutputBytes` MUST be no greater than that ceiling in the first implementation.

The validator MUST account for the literal byte length when applying program resource limits. No untrusted length may be used for allocation or indexing before overflow-safe bounds checks.

## 5. Source lowering

The first source-level bridge may lower only a direct call whose callee is the standard `print` builtin and whose sole argument is a string literal:

- `print("Hello, World!\\n")` emits one `emit_utf8` instruction;
- `println("Hello, World!")` may be supported as a distinct source builtin and lowered to the literal bytes followed by U+000A, but only if the checker already defines that builtin's exact semantics;
- interpolated strings, concatenation, local string variables, tainted strings, and arbitrary string expressions MUST be rejected by this initial lowerer rather than evaluated or coerced implicitly.

The lowerer MUST preserve source order relative to calls, traps, and other effects. A successful source check is necessary but not sufficient: the lowerer must independently verify the AST shape and literal bounds.

## 6. Native output adapter

The Linux x86-64 prototype may implement the abstract trace by embedding each literal in read-only data and issuing `write(1, ptr, remaining)` via the Linux `syscall` ABI.

The adapter MUST:

1. preserve the exact literal bytes, including NUL and non-ASCII UTF-8;
2. advance the pointer after a positive partial write;
3. retry when the syscall is interrupted (`-EINTR`);
4. treat a zero-byte write with remaining bytes, or any other negative result, as an OS output failure;
5. never spin on a zero-byte write;
6. keep all literal offsets and lengths within the emitted read-only data section.

The CCAM abstract machine specifies the output trace, not Linux file-descriptor behaviour. A native write failure is therefore a platform-adapter failure, reported through a documented process exit status distinct from CCAM trap statuses. A partial prefix may already have reached the host before such a failure; the adapter MUST NOT claim rollback or atomicity at the OS boundary.

The first target remains Linux x86-64 only. Other OS targets require separate ABI adapters and tests; they must not inherit Linux syscall numbers or assumptions.

## 7. Required conformance tests

Before this extension is accepted, add Capstan-native evaluator and validator tests for:

- empty output;
- ASCII output and exact byte order;
- multibyte UTF-8 (for example, `é` and a supplementary-plane scalar);
- embedded NUL;
- concatenation of multiple output instructions in source order;
- exact output-budget boundary and one-byte-over rejection;
- no output mutation when an output-limit trap occurs;
- malformed scalar/UTF-8 rejection;
- step accounting for empty and non-empty output;
- output instruction preservation across lowering and any optimisation.

Add Linux x86-64 execution tests that compare captured stdout byte-for-byte, exercise a partial-write test adapter where practical, and verify that write failure cannot cause an infinite loop. The native tests must assemble and link without a C compiler or C runtime.

## 8. Proof and assurance obligations

The formal model must extend the machine state with the output trace and output budget. Prove that:

- a successful `emit_utf8` appends exactly the canonical UTF-8 encoding of its literal;
- a rejected output-limit instruction leaves the trace unchanged;
- the trace length never exceeds `maxOutputBytes`;
- instruction-step accounting remains exact;
- effect ordering is preserved by source lowering.

The native backend refinement must relate emitted bytes and instruction order to the abstract output trace. Linux syscall handling, partial writes, EINTR and file-descriptor semantics remain explicit assumptions or separately verified adapter properties.

No claim of complete string support, dynamic IO, portable IO, runtime equivalence, or C-free self-hosting follows from this proposal.

## 9. Acceptance gate

Do not mark CCAM v0.2 output integrated until the schema, Capstan evaluator, validator, source lowerer, Linux native adapter, exact-byte tests, formal model and assurance matrix agree. The existing v0.1 contract remains unchanged until a reviewed version transition is accepted.
