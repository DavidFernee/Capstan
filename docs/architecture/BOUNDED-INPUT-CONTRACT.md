# Mandatory bounded-input contract

**Status:** normative source-level requirement for direct input builtins; parser-specific compositional budgets remain a separate implementation obligation.  
**Related issue:** [#444](https://github.com/DavidFernee/Capstan/issues/444)

## 1. Rule

Every direct source-level operation that obtains bytes, strings, arguments or environment values from outside the current computation MUST state a finite bound in its call syntax. There is no unbounded/default overload.

The bound is part of the source program's contract, not inferred from the process heap ceiling. The compiler rejects calls that omit a required bound. The generated runtime checks the supplied value before consuming or allocating input. Stage 0 must implement the same observable acceptance and failure behaviour.

All bounds are nonnegative signed-64 integer expressions in the current language. Runtime hard ceilings are documented per API; a requested bound outside the supported range traps with CWE-789. A bound may be smaller than the hard ceiling and is enforced independently for that call.

## 2. Direct input API

| Source form | Explicit unit(s) | Current hard ceiling | Over-limit behaviour |
|---|---|---|---|
| `args(max_count, max_arg_bytes, max_total_bytes)` | number of arguments; bytes in each argument; aggregate argument bytes | 4096; 1 MiB; 16 MiB | Trap with CWE-789. Count and every argument length are preflighted before the result list or managed strings are allocated. |
| `read_file(path, max_bytes)` | bytes read from the opened file/stream | 1 GiB | Returns `none` for content exceeding the caller's bound; invalid bound traps. Reads are streamed rather than trusting a reported file size. **This is a byte bound, not a deadline; a live FIFO/device/network filesystem may block while waiting for data.** |
| `read_line(max_bytes)` | payload bytes, excluding newline | 1 MiB | Trap with CWE-789 before appending the first byte beyond the caller's bound. Exactly the bound is accepted with newline or EOF. |
| `read_bytes(count)` | bytes requested from standard input | 1 GiB | Reads at most the explicit count; EOF may return fewer bytes. Invalid count traps. |
| `secret_env("NAME", max_bytes)` | bytes in the environment value | 1 MiB | Trap with CWE-789 before allocating the managed Secret. Variable names remain string literals without embedded NUL. |
| `workspace_read_file(root, relative, max_bytes)` | bytes read from the confined regular file | 1 GiB | Returns `none` for over-limit content; invalid bound traps. This remains a native-driver host operation, not a general unforgeable directory type. |



Byte limits do not establish a wall-clock bound. In particular, the current `read_file` implementation opens with `O_NONBLOCK` but then clears that flag before reading; a FIFO with a writer that remains open and idle can therefore block indefinitely. The existing FIFO regression covers only the no-writer case and must not be described as proving non-blocking behaviour. A deadline/cancellation contract for live streams is still open under issue #444.

Input-derived values retain their existing trust/provenance rules. In particular, file, line and byte-stream results remain `Tainted`; an explicit size bound does not validate their contents.

## 3. Compiler and runtime obligations

For each direct input call:

1. The checker enforces the exact arity and integer type of every bound argument.
2. Code generation evaluates arguments left-to-right and passes the caller's bound and source location to the runtime.
3. The runtime validates the bound against its documented domain before reading or allocating.
4. Aggregate limits are checked with subtraction-based or checked-add arithmetic before allocation; no attacker-controlled length is used for allocation, indexing or pointer arithmetic before validation.
5. Over-limit outcomes are deterministic and preserve the API's documented failure semantics.
6. Stage 0 mirrors native behaviour for the same source program and input.
7. Tests cover the exact bound, one unit over, zero, invalid negative/maximum values, EOF and failure atomicity where applicable.

A runtime bounds check may be elided only when the compiler proves that it cannot fail. Otherwise the check remains mandatory. `--keep-checks` is diagnostic/testing instrumentation, not a safety opt-out.

## 4. Parser and decoder composition

A bound on the raw input bytes is necessary but not sufficient for a parser that expands, duplicates or indexes decoded data. Every parser/decoder must separately identify and enforce the dimensions it consumes, including where applicable:

- maximum input bytes;
- maximum records, tokens, fields and collection elements;
- maximum nesting depth;
- maximum bytes per string/key/value;
- maximum aggregate decoded bytes and retained output;
- maximum work/fuel for scanning, validation, normalization and conversion.

Each individual bound and each aggregate bound must be checked before the corresponding allocation or access. Derived sizes and offsets use checked arithmetic. Cumulative work/decoded-byte charges are monotonic across nested calls; they are not reset when a child parser returns. Live temporary storage uses a separate peak/lease budget and is released only through a verified lifecycle transition. Failure must not publish a partially decoded result.

The compiler source/import graph now has a shared aggregate profile across the Capstan CLI, the experimental native driver and the LSP front end: 256 distinct source files; 16 MiB per file; 32 MiB total source bytes; 500,000 lexer tokens (excluding EOF sentinels); and 200,000 AST nodes. The same limits are enforced by the stage-0 bootstrap before it emits Python. The LSP also caps all open document text at 256 MiB. Exact and one-over tests cover file count, source bytes, token count and AST nodes in the compiler and stage 0; the Linux native-driver test exercises the same import-graph limits. These limits apply to compiler source graphs, not arbitrary application parsers.

The Capstan LSP JSON-RPC decoder is one concrete implementation of these compositional limits. Its current limits are: 16 MiB framed message bytes; nesting depth 64; 65,536 JSON values; 4,096 members per object; 16,384 elements per array; 8 MiB per raw string; 12 MiB aggregate raw string bytes; 262,144 fragments per string; 524,288 aggregate string fragments; and 128 bytes per number token. Duplicate object keys are rejected. Exact-limit and one-over-limit protocol cases are exercised in `tests/lsp/sessions.py`. These values and tests establish only the LSP parser's stated profile; they are not defaults for other JSON, media, image, font or database decoders.

A raw-byte bound MUST NOT be presented as a proof of bounded parser work, decoded size, nesting, or live memory. Parser APIs that do not expose a suitable limit contract remain subject to explicit audit and migration; this document does not claim that every existing parser already satisfies this section.

## 5. Assurance boundary

The direct builtin signatures in section 2 are the first implementation increment for issue #444. The compiler/runtime/bootstrap wiring and direct API adversarial tests are being integrated in [PR #456](https://github.com/DavidFernee/Capstan/pull/456).

Still required before issue #444 can close:

- inventory every parser and decoder, including JSON, protocol framing, image/font/media formats and compiler source loading;
- define and implement parser-specific limits for count, nesting, decoded aggregate size and cumulative work;
- verify those limits across every backend and stage-0/native differential path;
- complete adversarial exact/one-over/overflow tests and update the CWE/assurance evidence ledger.

No process-wide heap cap, fixed undocumented default, or input-size inference from available memory substitutes for an explicit per-boundary contract.
