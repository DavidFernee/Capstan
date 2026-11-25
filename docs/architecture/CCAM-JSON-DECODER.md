# CCAM JSON decoder and validation boundary

**Implementation:** \`verification/ccam_json.cap\`  
**Status:** candidate implementation in PR #312; CI and independent qualification pending  
**Semantic authority:** \`CCAM.md\` and \`ccam-v0.1.schema.json\`

## Input contract

The decoder accepts a tainted JSON byte string and applies limits before constructing the CCAM program:

| Resource | Limit |
|---|---:|
| Input bytes | 8 MiB |
| Nesting depth | 64 |
| JSON value nodes | 1,000,000 |
| Decoded string | 1 MiB |
| Aggregate decoded strings | 4 MiB |
| Functions | 4,096 |
| Registers per function | 4,096 |
| Aggregate registers | 262,144 |
| Aggregate instructions | 65,536 |
| Call arguments | Existing CCAM aggregate limit |
| Output literal bytes | Existing 1 MiB CCAM limit |

The parser preserves number tokens as their original decimal text. Integer fields are converted only by \`validate_int\`; floating-point or exponent-form values cannot be accepted as integer fields through a binary floating-point conversion.

## Syntax and Unicode rules

The parser rejects:
- duplicate object keys, comparing decoded key values (so an escaped spelling cannot evade duplicate detection);
- malformed JSON number grammar, unterminated strings, invalid escapes, trailing commas and trailing non-whitespace data;
- invalid UTF-8, overlong encodings, surrogate encodings, stray continuation bytes and code points above U+10FFFF;
- unpaired UTF-16 surrogate escapes;
- input, nesting, node, string and aggregate-string budget excesses.

Escaped Unicode scalar values are encoded to UTF-8. No normalization or case folding is performed.

## Schema and semantic validation

The decoder requires exact field sets for the program, each function and each instruction. It resolves function names in a separate pass, so forward calls and recursion are representable. It rejects unknown opcodes, unknown register/return types, malformed operand types, invalid indices, missing fields and extra fields.

After decoding, it invokes \`ccam_validate_multi_function\`, which checks the cross-function invariants: unique names, entry signature, register and instruction bounds, call-site correspondence, call arity and argument types, destination/return compatibility, per-function static operand types and reachable control-flow validity.

The public construction path is \`ccam_json_machine_create\`. It does not construct an evaluator machine unless parsing, schema decoding and whole-program validation all succeed.

## Taint boundary

The parser retains tainted text while reading. The implementation's explicit \`trust()\` boundary is confined to values that have passed strict JSON string decoding; all schema strings additionally reject embedded NUL and enforce byte limits; function names pass the function-name constraints, and trap reasons pass the closed ASCII reason grammar. These values are then used only as machine identifiers/reason labels, not as filesystem paths, commands, format strings or executable source.

This boundary requires dedicated security review. The presence of a validation call is not itself a proof of validator soundness.

## Versioning

The v0.1 instruction set is decoded as specified by \`CCAM.md\`. The proposed \`emit_bytes\` instruction is the separately versioned v0.2 extension introduced by the byte-output work; it is not silently added to the normative v0.1 schema. A future versioned envelope should make the selected machine version explicit rather than infer it from the presence of an opcode.

## Remaining assurance obligations

This increment does not establish:
1. a formal proof that every accepted JSON document decodes to a value satisfying the Lean validated-program predicate;
2. a refinement/simulation theorem between this concrete Capstan parser/validator/evaluator and the Lean machine;
3. independent parser fuzzing, coverage-guided mutation, or differential testing against a separately implemented standards parser;
4. platform-specific stack/heap exhaustion qualification for maximum-depth inputs;
5. full conformance of the v0.2 output extension across all target backends.

Do not describe CCAM as fully verified or the C-Free milestone as complete until these obligations and the remaining machine semantics are closed.
