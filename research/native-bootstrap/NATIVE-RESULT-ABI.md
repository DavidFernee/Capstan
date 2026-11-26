# Candidate native terminal-result ABI (N0 design record)

**Status:** proposal for review; not normative CCAM semantics and not implemented.
**Baseline:** `main` at `189f19dd2a39c169e033691856d675b070fb2864`.
**Coordination:** issue #370.

## 1. Problem statement

The current x86-64 backend maps an entry `int64` return to Linux `exit(2)`. Linux exposes only the low eight bits as the process status. This is not an injective encoding of the CCAM `Halt(Int64)` outcome. The current emitter also collapses several distinct CCAM traps to process statuses and loses explicit-trap detail and function/PC context.

The canonical CCAM model already distinguishes:
- `Halt(value)` and `HaltVoid`;
- `Trap(code, function, pc, detail)`, with explicit trap reason in `detail`;
- malformed-program validation failure before execution;
- bounded step and call-depth traps.

The native process interface must preserve these distinctions rather than inventing a second machine semantics.

## 2. Candidate transport

Reserve Linux file descriptor **3** as a result capability. The launcher must explicitly pass a fresh, writable, bounded regular file or memfd at fd 3. The native program writes exactly one record and exits with process status 0 only after the complete record has been written.

- stdout and stderr remain separate and are not used as the machine result channel.
- fd 3 is mandatory; no fallback to stdout, process exit status, a path lookup, environment variable or implicit file.
- The launcher must create/truncate the result sink for each invocation, cap it at 1,136 bytes, and reject absent, truncated, overlong or malformed records.
- A regular file/memfd is required in the first profile, avoiding SIGPIPE semantics and concurrent-writer ambiguity. A later streaming profile would need its own signal and atomicity contract.
- The program uses Linux `write(2)` directly. It retries `EINTR`, continues after positive short writes, and treats zero progress or any other error as transport failure. No unbounded retry is permitted.
- On transport failure the program exits with a reserved process-level status (proposed 76) and does not fall back to an alternate channel. The launcher rejects any partial record.
- The executable performs no path lookup or open operation for this channel; fd 3 is an explicit capability supplied by its caller.

This is a Linux x86-64 platform boundary, not part of architecture-neutral CCAM semantics.

## 3. Candidate version-1 record

All integers are little-endian. The record is a 48-byte fixed header followed by bounded name and detail byte strings.

| Offset | Width | Field | Meaning |
|---:|---:|---|---|
| 0 | 8 | magic | Exact bytes `CCAMRES\0` |
| 8 | 2 | version | 1 |
| 10 | 2 | kind | 0=int return, 1=void return, 2=CCAM trap, 3=platform failure |
| 12 | 4 | code | Stable code table below; zero when not applicable |
| 16 | 8 | value | Signed two's-complement int64; meaningful only for kind 0, otherwise zero |
| 24 | 8 | steps | Number of CCAM instructions executed, including an instruction that traps |
| 32 | 4 | function_index | Index in validated function table; `0xffffffff` if no machine location |
| 36 | 4 | pc | Instruction index; `0xffffffff` if no machine location |
| 40 | 4 | function_name_len | 0..1024 bytes |
| 44 | 4 | detail_len | 0..64 bytes |
| 48 | variable | function_name | Exact canonical function-name bytes; empty if no machine location |
| 48+name_len | variable | detail | Explicit-trap reason bytes only in the initial profile |

Maximum record size is 48 + 1,024 + 64 = **1,136 bytes**. The producer uses a statically bounded buffer; it does not allocate based on an untrusted length. The consumer requires exact total length and rejects unknown versions, kinds, codes, inconsistent lengths, nonzero reserved/unused fields, and malformed name/detail encodings.

Function index is included as a stable machine location, while the function-name bytes preserve the CCAM observable trap field directly. The two must agree with the validated program metadata supplied to the compiler. The exact byte encoding of function names must follow the canonical CCAM name representation; this proposal does not silently impose a new Unicode or identifier grammar.

### 3.1 Outcome kinds

- **0 — integer return:** `code=0`, full signed-64 `value`, zero function/PC sentinels, empty name and detail.
- **1 — void return:** `code=0`, `value=0`, zero function/PC sentinels, empty name and detail.
- **2 — CCAM trap:** `value=0`, nonzero machine trap code, function index/name and PC populated. `detail` is populated only for `explicit_trap`, preserving its validated reason exactly.
- **3 — platform failure:** `value=0`, a separately namespaced platform code, and no function/PC/name/detail unless a future specification defines a meaningful machine location. Native stack mapping/allocation failure belongs here, not in a CCAM trap code.

The process exit status is not the returned value and is not the machine trap code. Status 0 means the complete terminal record was transported. Status 76 is reserved for inability to transport it. Other process termination (signal, timeout, launcher kill) is an abnormal platform termination and the launcher must not fabricate a CCAM result.

### 3.2 Initial CCAM trap code assignments

The numeric assignments below are a proposed wire mapping, not a change to the canonical string names:

| Code | Canonical trap |
|---:|---|
| 1 | `integer_overflow` |
| 2 | `division_by_zero` |
| 3 | `uninitialised_register` |
| 4 | `invalid_register` |
| 5 | `register_type_mismatch` |
| 6 | `step_limit_exceeded` |
| 7 | `call_depth_exceeded` |
| 8 | `explicit_trap` |
| 9 | `invalid_program_counter` |
| 10 | `invalid_instruction` |

Unknown codes are rejected by the consumer. Validation errors are not runtime traps: whole-program validation must complete before executable generation, and malformed input must fail closed before native execution.

Platform error codes must use a disjoint namespace/table and must not be mapped to CCAM trap codes. The initial platform table should include at least native stack mapping/allocation failure and any explicitly specified host resource failure.

## 4. Semantic mapping obligations

An implementation must demonstrate a total mapping from each canonical terminal outcome to exactly one record:

| CCAM/reference outcome | Candidate native record |
|---|---|
| `Halt(Int64(v))` | kind 0, exact signed-64 (v) |
| `HaltVoid` | kind 1 |
| `Trap(code, fn, pc, detail)` | kind 2, exact code/function/PC/detail projection |
| Failure to establish required native stack | kind 3, platform stack error |
| Invalid program/schema | no executable; compile/validation diagnostic, not a record |

The `steps` field must preserve the canonical transition accounting: dynamic traps consume the step of the instruction that trapped; a step-limit trap occurs before the next instruction and does not consume an additional step. Call-depth failure must preserve the canonical preflight behavior and caller location.

The function index/name pair, PC, detail, and step count are not optional debugging metadata: they are part of the observation needed to compare the native result with the reference machine.

## 5. Resource and security contract

- Maximum record length: 1,136 bytes.
- Fixed producer buffer; no length-derived allocation.
- Exactly one logical record per invocation.
- Bounded write loop with explicit short-write and `EINTR` handling.
- No retry loop without a finite byte/progress bound.
- No alternate output channel or silent truncation.
- fd 3 is an explicit caller-provided capability; the executable does not open paths or discover ambient output destinations.
- The launcher validates exact file length, magic, version, code, lengths, reserved values and outcome-field consistency before accepting a result.
- Failure to write is a platform failure, never a fabricated CCAM trap or value.
- The result ABI does not itself establish compiler correctness, native-code refinement or trustworthiness of the producer.

## 6. Alternatives considered

1. **Keep process exit status:** rejected for arbitrary CCAM int64 results and structured trap observations; it is inherently lossy.
2. **Write a textual JSON result to stdout:** rejected for the first native profile because it introduces escaping, text encoding, parser ambiguity, unbounded output risk and conflict with ordinary program stdout. It may be a host-facing presentation format layered above the fixed binary record.
3. **Write a fixed binary record to stdout:** technically viable, but couples machine results to application output and makes composition harder. A dedicated inherited fd is a clearer capability boundary.
4. **Use a temporary path opened by the executable:** rejected because it introduces path resolution, ambient filesystem authority, race/symlink concerns and additional OS dependencies.

## 7. Open decisions before implementation

- Confirm whether fd 3 should be the standard Linux x86-64 result capability, or whether the project prefers a different launcher-managed descriptor.
- Confirm the exact canonical byte representation of function names.
- Confirm whether function index is zero-based in the normative function table (the proposal assumes zero-based).
- Finalise platform failure codes and whether any host resource failures can occur after execution begins.
- Decide whether the compiler embeds the function name bytes in the generated image or references an immutable metadata section.
- Specify the process/launcher contract for the bounded regular file or memfd and its ownership/lifetime.

## 8. Acceptance gates

Before implementation:
- CCAM architecture owner approves the observation mapping and versioning.
- Formal/reference semantics owner confirms every outcome field and step-accounting rule.
- Linux ABI reviewer confirms syscall/error handling and fd capability behavior.
- Integration worker confirms no conflict with in-flight CCAM changes.

Implementation acceptance:
- Exhaustive mapping tests for all terminal outcome kinds and trap codes.
- Signed-64 boundary vectors: `INT64_MIN`, `INT64_MAX`, -1, 0, 1, 255, 256 and values with high bits set.
- Explicit trap detail round-trip at lengths 1 and 64.
- Function-name boundary and location correspondence tests.
- Short-write, `EINTR`, zero-progress, full-sink and transport-failure tests.
- Exact record length, malformed header, unknown code, oversized lengths and truncation rejection tests.
- Differential comparison against the canonical CCAM machine for value, outcome, code, function, PC, detail and step count.
- ELF checks remain separate: no interpreter, dynamic section, undefined symbols or relocations; W^X load segments; non-executable stack.
- No generated C, C compiler/linker driver, Capstan C runtime or Python production dependency.

This design is a candidate interface only. No CCAM semantics, native emitter, runtime, shared compiler or build files were modified to implement it.
