# CCAM JSON decoder — bounded input and validation contract

**Status:** implementation contract proposal; not yet implemented or normative CCAM v0.1  
**Depends on:** CCAM.md, ccam-v0.1.schema.json and verification/ccam_calls.cap

This contract closes the gap between the published JSON schema and the current in-memory evaluator. A schema describes shapes; it does not establish safe parsing, duplicate-key handling, exact-number conversion, allocation bounds or validation order.

## 1. Required invariants

Before an evaluator receives a program, the decoder MUST establish:

1. The input is valid UTF-8 JSON under RFC 8259 and the stricter CCAM rules below.
2. Every object has unique keys after JSON escape decoding. Thus "entry" and "\\u0065ntry" are duplicates.
3. Integer fields are parsed from their original decimal token, never through binary floating point or a lossy host JSON number.
4. Every object is closed: required fields occur exactly once; unknown fields are rejected; null is accepted only where explicitly specified.
5. Scalars, strings, containers, nesting and aggregate program resources are bounded before allocation or indexing depends on them.
6. Cross-field and whole-program invariants are checked before frames, register files, call-site tables or executable state are constructed.
7. Rejection is a validation error, never a runtime trap; rejected input never starts execution.

The decoder remains in the trusted computing base until its implementation is verified or replaced by a verified implementation. JSON Schema validation alone is insufficient.

## 2. Parsing architecture

Use a two-stage, iterative pipeline:

    bounded input bytes
      -> UTF-8 / JSON lexical scanner
      -> bounded token tape (token kinds and source spans)
      -> structural and schema validation
      -> cross-field and whole-program validation
      -> immutable typed CCAM program
      -> evaluator

The scanner MUST use an explicit container stack, not host recursion proportional to untrusted nesting. Tokens retain source byte spans. Numeric tokens retain their original lexemes until the schema validator selects the expected numeric type. Strings retain bounded decoded bytes, or bounded references into a decoder-owned arena.

Detect duplicate keys while scanning each object. Compare decoded key bytes exactly. A hash may accelerate lookup but MUST NOT establish equality. The duplicate-key set is bounded by the object-member limit and discarded when the object closes.

Do not first parse into a generic host JSON object: common parsers discard duplicate-key evidence, round large integers, allocate from untrusted lengths or impose undocumented depth limits. Do not build a generic tree and assume a later schema pass can recover discarded information.

## 3. Lexical and scalar rules

### UTF-8 and strings

- Reject invalid UTF-8, overlong encodings, encoded surrogate values and code points above U+10FFFF.
- Decode JSON escapes exactly. A high-surrogate escape MUST be followed immediately by a low-surrogate escape; lone surrogates are invalid.
- Compare keys after escape decoding, by exact UTF-8 byte sequence. Do not normalise Unicode or case-fold.
- Preserve decoded string bytes; never silently replace malformed sequences.
- Enforce decoded byte limits while decoding, before appending to the string arena.
- Function names additionally reject empty strings and embedded U+0000, and remain unique by exact scalar-value sequence.
- Explicit trap reasons retain the ASCII grammar in normative CCAM.

A JSON string containing U+0000 is valid JSON, but is not a valid function name. The schema-specific validator applies that distinction.

### Numbers

The scanner recognises the complete JSON number grammar and preserves the original token span. It rejects leading plus signs, illegal leading zeroes, missing fraction digits and missing exponent digits.

A CCAM integer field accepts only an integer token with neither fraction nor exponent. Therefore 1.0 and 1e0 are rejected even though mathematically integral. Boolean and null tokens are never integers.

Parse signed 64-bit values directly from decimal digits using negative accumulation, or an equivalent proved checked algorithm. Check each digit before multiplication/subtraction so MIN is representable without first constructing its unrepresentable positive magnitude. Reject overflow before updating the accumulator. Non-negative indices reject a leading minus and are bounded by 2^63-1. No integer conversion passes through floating point.

## 4. Proposed initial admission ceilings

These are proposed starting limits, not yet normative. Any change must update specification, tests and aggregate accounting together.

| Resource | Maximum |
|---|---:|
| Encoded document | 16 MiB |
| Container nesting depth | 64 |
| Decoded bytes in one JSON string | 1 MiB |
| Object members | 16 |
| Elements in one JSON array | 1,048,576 |
| Total tokens | 1,048,576 |
| Functions | 4,096 |
| Function-name bytes | 1,024 |
| Aggregate function-name bytes | 256 KiB |
| Total registers | 262,144 |
| Total call arguments | 262,144 |
| Total instructions | 1,048,576 |

Check every capacity addition with overflow-safe arithmetic before buffer growth. Capacity growth MUST remain under the corresponding ceiling. Do not reserve an untrusted declared array size; grow only as validated elements are consumed.

Limit failures use stable bounded categories such as document_limit_exceeded, nesting_limit_exceeded, string_limit_exceeded, token_limit_exceeded and aggregate_instruction_limit_exceeded. Diagnostics MUST NOT echo unbounded attacker-controlled strings.

## 5. Validation order

The required observable order is:

1. Check encoded document size.
2. Scan UTF-8, JSON grammar, nesting and lexical resource limits; detect duplicate keys.
3. Validate the top-level exact field set.
4. Validate every function object's exact field set and scalar/array element types.
5. Validate function names, uniqueness, register tags, parameter counts, return types and instruction shapes.
6. Parse numeric operands exactly and range-check before conversion to indices.
7. Validate entry existence and entry signature.
8. Validate register indices and types, branch/jump targets, call names, arity, argument types, return types and destination compatibility.
9. Validate reachable control flow and reject reachable fall-through.
10. Enforce aggregate resource limits and construct the immutable typed program.
11. Only then construct evaluator frames and register files.

Passes may be fused only if this rejection order is preserved and no unchecked value influences allocation or indexing. Validation error selection must be deterministic and tested.

## 6. Schema-specific requirements

The published ccam-v0.1.schema.json remains authoritative for closed object shapes. The decoder additionally enforces duplicate-key rejection at every depth; exact signed-64 and index parsing; Unicode scalar validity; function-name NUL rejection; field-specific nullability (only call dst accepts null); aggregate limits; and all cross-field/control-flow constraints in CCAM.md.

A schema library is suitable only if it preserves duplicate keys and exact numeric lexemes and documents bounded allocation behaviour.

## 7. Adversarial test matrix

**Numbers:** MIN, MAX, zero, negative zero; one below MIN and one above MAX; maximum index and one above; very long digit strings; 1.0, 1e0, -0.0, +1, 01, --1, truncated exponents; true, false and null in integer fields.

**Objects and strings:** duplicate literal keys; duplicate keys using equivalent escapes; duplicates at every object depth; unknown, missing and wrongly typed fields; escaped quotes, backslashes and control bytes; valid surrogate pairs; lone surrogates; malformed, overlong and truncated UTF-8; embedded NUL in names and permitted values; canonically equivalent but byte-distinct Unicode names (which remain distinct; no normalisation).

**Bounds:** document, depth, string, token, member, array, function, instruction, register and argument limits at and above their boundaries; capacity arithmetic overflow; deeply nested input without host-stack growth; repeated duplicate keys and hash-collision candidates; malformed input at the final byte of a maximum-sized document.

**Isolation:** every invalid document is rejected before entry-frame construction; failure exposes no partial program; validation errors never become runtime traps; accepted documents yield the same typed program under harmless whitespace and object-member reordering.

Each vector asserts its error category and that evaluation did not begin. Fuzz the scanner independently and fuzz complete documents around token boundaries, escaping, duplicate keys, numeric limits and aggregate counters.

## 8. Proof obligations

1. Prove decimal parsing accepts exactly the signed-64 integer-token grammar and returns the mathematical value.
2. Prove scanner transitions preserve token-span, string-arena and container-stack bounds.
3. Prove duplicate-key detection is complete for decoded-key equality; hashes are only indexes.
4. Prove structural validation produces schema-conforming typed values.
5. Prove whole-program validation establishes the premises of the multi-function machine model.
6. Prove rejected input cannot reach evaluator construction and accepted input maps to the formal validated-program predicate.
7. Separately establish refinement from the Capstan implementation to the formal model. A Lean parser model alone does not prove the Capstan parser.

The trusted-base inventory must include the compiler used to build the decoder, byte/string primitives, allocator, proof kernel and any remaining host interfaces.

## 9. Exit gate

This work is complete only when one exact revision contains a Capstan-native bounded scanner and decoder, duplicate-key and exact-integer rejection, closed schema and whole-program validation, adversarial/fuzz tests, an immutable typed output, formal results with explicit assumptions, and implementation-to-model correspondence evidence.

Until then, external CCAM JSON decoding is NOT IMPLEMENTED. The current in-memory evaluator must not be described as accepting arbitrary external CCAM JSON documents.
