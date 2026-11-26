# Security proof-obligation matrix

> **Status:** obligation definitions are established; no end-to-end source-to-runtime security theorem is claimed. Tests and CWE-atlas outcomes are empirical evidence, not proofs.

This matrix turns the security claims in the [vulnerability-prevention programme](../docs/assurance/VULNERABILITY-PREVENTION-PROGRAMME.md) into propositions that can be modelled, proved and connected to the implementation. It is deliberately separate from the allocator/collector matrix in OBLIGATIONS.md.

## Evidence levels

- **Tested:** an executable positive/negative fixture exercises the stated case.
- **Model-only:** a proof assistant checks an abstract model, but no concrete compiler/runtime correspondence has been established.
- **Implementation-proved:** the exact implementation is connected to the model by a checked refinement or equivalent proof.
- **Open:** the proposition, model, or implementation bridge is incomplete.

A test can support a claim without proving it. A model-only theorem cannot be promoted to an implementation guarantee by documentation alone.

## Obligations

| ID | Property to establish | Model-level proposition | Required implementation bridge | Current evidence / status |
|---|---|---|---|---|
| SEC-MEM-01 | List and string reads never perform an out-of-bounds memory access. | For every index operation, either the index is in the logical collection range and the returned value equals the indexed element, or execution takes the specified safe-stop path before dereferencing storage. | Prove lowering of checked index operations to runtime guards; prove range-check elimination preserves the guard condition; connect logical lengths to allocated capacities. | Tested: tests/runtime/out_of_bounds_read.cap and tests/cwe/atlas.py; range proof tests exist. Formal source-to-runtime refinement open. |
| SEC-MEM-02 | List and string writes never modify memory outside the allocated object. | Every successful write has an in-range index and changes only the corresponding logical element; every invalid write terminates before the store. | Prove generated-C/native store lowering and capacity/length invariants. | Tested: tests/runtime/out_of_bounds_write.cap; implementation proof open. |
| SEC-ARITH-01 | Checked arithmetic is exact when representable and fail-stops otherwise. | Addition, subtraction, multiplication and negation either produce the mathematical result within the signed machine range or take the specified fatal transition. | Prove C helper refinement and that compiler lowering cannot bypass checked helpers. | Addition has model-only Lean results in OBLIGATIONS.md; multiplication and concrete C refinement remain open. |
| SEC-TAINT-01 | Untrusted provenance cannot silently become trusted data. | Taint propagates through concatenation, interpolation, helper calls and supported aggregates/lookups; only specified validators, context escapers or audited declassification operations may change the provenance label. | Prove checker transfer functions sound with respect to language evaluation and all builtin/library sink signatures. | Tested: tests/accept/untrusted.cap, reject fixtures and CWE atlas. Control-flow validation is intentionally a declassification boundary and requires a separate validator-correctness argument. |
| SEC-OUT-01 | Context-encoded output cannot cross into an incompatible sink. | Html, LogText and CsvText are preserved by allowed composition; incompatible concatenation, assignment and sink use are rejected; generic write_file does not accept these context types. | Prove type-checker soundness for contextual types and correspondence of each typed sink to its declared output operation. | Tested: tests/accept/contextual_output_sinks.cap and tests/reject/*_sink.cap; JSON remains a plain string fragment and is explicitly outside this obligation until its serializer migration. |
| SEC-LOG-01 | Terminal/log output neutralises the specified hostile byte and Unicode set. | escape_log maps line controls, C1 and bidi controls to inert text; escape_json also escapes C1/bidi controls before its string fragment can reach terminal output. | Prove UTF-8 decoding/encoding and escaping loops preserve valid content while eliminating the specified hostile code points. | Tested: JSON and log escaper fixtures plus CWE-117 atlas cases. Formal runtime proof open. |
| SEC-CSV-01 | CSV field encoding neutralises the enumerated formula leaders in emitted bytes. | For the tested ASCII leaders, tab/CR/LF, leading ASCII spaces and four full-width leaders, the encoded field begins with the apostrophe prefix and preserves CSV quoting. | Prove the byte-level encoder and sink preserve the exact bytes. Separately test target spreadsheet clients, including save/reopen behaviour. | Tested: 304-attempt CWE atlas and contextual-sink runtime fixture. Not a universal spreadsheet guarantee; client-specific behaviour remains an explicit limitation. |
| SEC-AUTH-01 | A protected operation cannot be invoked without a valid grant for the required policy and object. | A grant is issued only when the policy holds, is bound to the authorised object, cannot be forged or widened, and cannot outlive its permitted scope. | Prove checker rules, grant construction, runtime validation and object-identity binding preserve the model. | Tested: tests/runtime/grant_*.cap and policy fixtures. Formal proof and implementation correspondence open. |
| SEC-SECRET-01 | Secret values cannot be disclosed through ordinary output and are erased according to a precise lifecycle contract. | Secret values cannot flow to print/log/file sinks; the model must state whether erasure is deterministic at scope exit, collection, reuse or release. | Prove all copies, registers, buffers, allocator metadata and runtime transitions satisfy the chosen erasure contract. | Print/log rejection is tested. Current GC-time wipe is non-deterministic; deterministic destruction and a complete copy/register story are not established. |
| SEC-CCAM-01 | Security-relevant source semantics survive lowering. | Source-level bounds checks, checked arithmetic, taint labels, context types and grants retain their meaning in CCAM and all executable backends. | End-to-end refinement from source semantics through typed IR/CCAM to generated C/native execution, including compiler self-hosting. | Open. Selected CCAM and Lean fragments do not yet establish whole-compiler refinement. |
| SEC-CVE-01 | Each CVE case preserves the security-relevant root cause in its Capstan analogue. | The analogue retains attacker capability, vulnerable operation, preconditions and security effect; cases with missing facilities are classified as capability-absent/out-of-scope, not prevented. | Reproducible fixtures, positive controls, pinned toolchain and independent review of semantic mapping. | Protocol and first Heartbleed parser-kernel fixture exist; exact-head CI and independent case review pending. |

## Promotion rules

1. A row may move from **Open** to **Tested** only when positive controls and adversarial negative fixtures are checked into the repository and run by the standard test entry point.
2. A row may move to **Model-only** only with a pinned proof-assistant version, clean reproducible build, explicit assumptions and recorded theorem names.
3. A row may move to **Implementation-proved** only when the exact compiler/runtime revision is connected to the model by a checked refinement or an independently reviewed equivalent argument.
4. Any unchecked builtin, FFI boundary, generated-C operation, allocator assumption or host dependency must appear in the trusted-base inventory.
5. A change to the covered semantics or implementation invalidates promotion until the affected proof obligations are rerun or re-established.

## Immediate proof increments

1. Prove list-index semantics and the safe-stop transition for a finite abstract list model; then connect the model to the concrete list runtime.
2. Prove the taint transfer rules for concatenation, function calls and aggregate storage; isolate validators as explicit, separately justified declassification functions.
3. Prove context-type preservation and sink admissibility, starting with HTML/log/CSV and leaving JSON explicitly separate until its serializers migrate.
4. Extend checked-arithmetic model proofs to subtraction, multiplication and negation; then prove C helper correspondence.
5. Define the grant state machine and prove object binding, non-forgeability and scope expiration before attempting compiler/runtime refinement.
