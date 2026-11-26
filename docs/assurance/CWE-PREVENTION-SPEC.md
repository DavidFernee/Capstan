# CWE prevention specification

> Normative evidence format for security claims about the integrated Capstan implementation.
> This specification does not itself assert that any property is implemented or proved.

## 1. Purpose

The CWE atlas is an executable attack corpus. This document defines the minimum evidence needed to turn an atlas verdict into a reproducible engineering claim. The atlas remains the inventory of attacks and current outcomes; this specification governs the quality and wording of claims made from it.

## 2. Required record

Every attempt must be traceable to a record with these fields. A future machine-readable companion should use the same names.

| Field | Requirement |
|---|---|
| id | Stable identifier, preferably CWE-NNNN/slug; do not key only by row number. |
| cwe | CWE identifier and weakness title; identify approximate or project-defined mappings. |
| attempt | Exact source fixture or reproducible generator. |
| preconditions | Attacker control, program state, platform and enabled capabilities required. |
| property | Precise statement of what must not happen or what must happen instead. |
| enforcement | Parser, checker, static analysis, runtime, library contract, or absent construct. |
| outcome | One of the controlled outcomes below. |
| evidence | Test path, expected result, exact command, revision and CI run. |
| positive_control | Nearby legitimate program that must continue to compile/run correctly. |
| bypasses | Aliases, nested expressions, helper boundaries, methods, collections, control-flow joins, escape hatches. |
| assumptions | Compiler/runtime/host/toolchain and developer-declaration assumptions. |
| proof | Theorem and correspondence status, or explicitly none. |
| residual_risk | What remains possible and what this record does not establish. |

A record may group several attempts for one CWE only if each attempt has an independent expected result and is reported separately. Do not collapse distinct bypasses into one successful test.

## 3. Controlled outcome vocabulary

- **Compile-time rejection** — compiler rejects the exact source before execution. Record diagnostic identity and phase.
- **Runtime stop** — program starts, the specified invalid operation is detected, and execution terminates with the documented trap/exit result. This is not compile-time prevention and may still permit denial of service.
- **Neutralised** — program accepts and executes, but the tested attack cannot produce the harmful effect. State exact observable semantics.
- **Inexpressible by absence** — language/API has no construct needed to express the attack. Record the absent capability and confirm no alternate escape hatch supplies it.
- **Audited escape hatch** — attack is possible only after an explicit, reviewable declassification/unsafe operation. Record every audit warning and required justification.
- **Gap / possible** — faithful attack attempt compiles and can produce the harmful effect, or the property is not enforced.
- **Not applicable** — relevant facility or threat is absent from the product; do not count this as prevention.
- **Design limitation** — correctness depends on requirements or business intent the language cannot determine. State the human/process control needed.

The aggregate atlas outcome for a weakness is its weakest applicable attempt. A CWE with one rejected attempt and one successful bypass is a gap, not prevented. Aggregate counts must not imply that each weakness is wholly prevented.

## 4. Test requirements

For each claimed prevention:
1. Include at least one minimal attack fixture.
2. Include positive controls demonstrating legitimate use.
3. Include adversarial variants for aliases, nested expressions, helper calls, methods, collections, struct fields, control-flow joins and serialization boundaries where relevant.
4. Verify expected compiler phase, diagnostic/CWE, runtime exit status and side effects.
5. Run the focused test and standard test runner on the exact commit.
6. Record exact-head CI results; do not infer them from workflow files.
7. Preserve a known-gap fixture until implementation genuinely closes it. Change its expected result in the same reviewed change that adds the mitigation and positive controls.

For runtime stops, assert both exit status and absence of the prohibited side effect. For neutralisation, assert exact output/effect, not merely successful compilation.

## 5. Evidence levels

| Level | Evidence | Claim boundary |
|---|---|---|
| E0 | Proposal or design | Intent only |
| E1 | Current implementation path inspected | Implementation description only |
| E2 | Focused test passes on exact commit | Tested case only |
| E3 | Relevant suite and exact-head CI pass | Validated within stated suite/configuration |
| E4 | Independent reference model, second implementation or adversarial review agrees | Independently cross-checked |
| E5 | Machine-checked theorem with explicit implementation correspondence | Formally verified property under stated assumptions |

Evidence is property-specific. An E5 theorem about a finite CCAM model does not upgrade an E1 C runtime. An E3 atlas suite does not prove all possible source programs safe. A test corpus can discover counterexamples; it cannot establish universal absence by itself.

## 6. Threat-model and trusted-base fields

Every report must identify whether the property depends on parser and type checker correctness; source-to-core lowering and optimisation soundness; generated C or native backend correctness; runtime, allocator/GC, libc and OS behaviour; build/bootstrap tools and compiler provenance; explicit declarations such as sensitive, protected, policy definitions or trust(); and application-specific requirements and deployment configuration.

The current C-backed path must be stated explicitly until a C-free backend and runtime are integrated and independently validated.

## 7. Wording rules

Prefer:
- “The compiler rejects the tested source pattern…”
- “The runtime stops on this invalid index…”
- “The language currently has no pointer arithmetic…”
- “The atlas contains N tested attempts, of which … were classified …”

Avoid:
- “Capstan prevents CWE-X” when only one narrow pattern was tested;
- “memory safe” without naming the source/runtime trust boundary;
- “formally verified” for a model without implementation correspondence;
- counting not-applicable, logic/design, or audited-escape-hatch cases as unconditional prevention;
- treating a CVE analogue as a reproduction without demonstrating semantic equivalence.

## 8. Change control

Changes to an outcome require a source/capability change; a regression test demonstrating the previous bypass is closed; positive controls; atlas, coverage and threat-model updates as appropriate; review for new bypasses/usability hazards; and exact-head CI evidence.

A documentation-only change may correct a claim or classification but must not imply the underlying capability changed.
