# G1 cross-interface review

Candidate inputs #575–579; not yet integrated or accepted. G0 HOLD. Cross-contract findings and proposed dispositions:

| ID | Interfaces | Finding and required disposition |
|---|---|---|
| X01 | B01/B02 | Source decimal grammar and external JSON mathematical integer grammar intentionally differ; configuration transport must explicitly adopt same exact integer rule or declare separate profile. Test 1.0, 1e0, MIN, negative zero at both boundaries. |
| X02 | B01/B02/B04 | Source definite initialization differs from dynamic CCAM register initialization; no removal of dynamic checks without sound proof. Structural invalidity precedes execution; fuel precedes dispatch and ordered operand reads. |
| X03 | B02/B03 | Nonlocated platform error must not masquerade as located machine trap; freeze registered platform codes, sentinel and observed steps before enabling platform record kind. |
| X04 | B03/B04/B05 | Physical backing failure is not deterministic logical quota exhaustion. Existing scratch proposal maps both to allocation_failed; require versioned clarification or fixed admission oracle. Launcher deadline is external, not fuel. |
| X05 | B01/B04 | Retained aggregate reference across RHS must be rooted, then location revalidated before write; scalar subset rejects aggregates. |
| X06 | B04/B05 | Memory handles, host capabilities and policy grants have distinct identity namespaces and lifetime rules. Revocation cannot imply collection; cleanup cannot grant authority. |
| X07 | B03/B05 | Result fd is private launcher authority; ordinary source effects must not write terminal transport. Bound actual writes via host policy and reject trailing bytes. |
| X08 | B04/B05 | Secret wipe scopes must include managed copies and spills, not host copies outside control. Reset cannot expose prior region contents. |
| X09 | B01/B05 | Checked snapshot binds provenance and effect judgments; untrusted annotations cannot promote context or grant. Lowering must preserve sink and policy decisions. |
| X10 | all | Separate source admission, machine steps, runtime work/bytes and wall time; no interchangeable budgets. |
| X11 | B03/B05 | Public terminal trap, steps and lengths can themselves leak secrets; relational theorem requires explicit declassification and observer policy, not merely equal-length comparison. |
| X12 | all | Bind version, source, checked snapshot, validated CCAM and native artifact; source maps nonsemantic but authenticated for attribution. No unsupported profile fallback. |

## Freeze checklist
Resolve X01–X12 with named producer and consumer acknowledgement, record normative clause/version changes and executable vectors; ensure all proposed interfaces have bounded admission, failure ordering, complete outcome and explicit proof boundary. Record deferred extensions as rejected, not implemented. CI is necessary, not approval of prose. No independent review or test execution claimed. G1 remains unaccepted pending G0 and evidence.
