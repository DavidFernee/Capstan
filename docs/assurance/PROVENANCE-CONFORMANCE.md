# Provenance Semantics — Current Conformance Assessment

**Assessment date:** 2026-11-24  
**Purpose:** Evidence companion to PROVENANCE-SEMANTICS.md  
**Status:** Independent source-level assessment; not a runtime test report. The audit was revalidated against main at `bc0a283df5a964e7340cd48ec8ce4a1e8fb3acde`; the provenance-flow implementation remains unchanged in the reviewed region.

## 1. Scope and evidence discipline

This document compares the proposed provenance semantics with the current implementation on main.

Primary source snapshots inspected:

| File | Revision |
|---|---|
| compiler/checker.cap | 9c515141bea8279f4a14a15bb6e387b8eee4a2ce |
| compiler/parser.cap | 121fda06ac28119ebdbf80f793e42633681fe6b3 |
| docs/CWE-COVERAGE.md | 8c01d778788330dd1cf12c1d7b6fd7918e079b0f |
| tests/cwe/atlas.py | e4273a8b6430ca89640eb67a52386ae6a72eb376 |

Line numbers below refer to these exact file snapshots. A later revision may move them.

This is source inspection. Candidate programs described here have not been compiled or executed as part of this assessment. “Gap” means the inspected transfer logic does not implement the required rule, and the candidate illustrates the expected consequence. It is not a claim that an executable exploit has been demonstrated.

The assessment intentionally distinguishes:
- **Covered case:** a specific existing regression demonstrates the intended rejection.
- **Source-level gap:** the transfer logic lacks the required propagation.
- **Not established:** the source or tests inspected do not justify a conformance claim.

## 2. Current analysis architecture

The current analysis is a variable-name-based may-analysis, not the abstract-value and heap analysis specified in the companion semantics.

Evidence:

- FlowSummary stores returns_derived, param_to_return, and param_to_sink only (checker.cap:1801–1805).
- Flow stores derived variable names in Map<int> vars (1803–1811).
- derived() recognises selected AST forms: tainted .at(), marked variables, unary operations, marked field/index bases, selected map .get(), int_to_str(), string concatenation, selected collection reads, arithmetic, wrapping operations, and function summaries (1821–1852).
- base_marked() recursively reduces a field/index expression to its root variable name (1854–1858); it does not resolve object identity or aliases.
- flow_walk() marks only int and string local declarations and assignments (1891–1893).
- Aggregate writes mark a root variable name; push, insert, and set inspect only the final argument (1907–1913).
- Optional unwrapping is handled for a direct N_IF expression (1915), but a stored optional local is not modelled as a payload-bearing abstract value.
- Interprocedural summaries seed only parameters whose declared type is TY_INT (1956–1970).
- Ordinary function summaries are iterated to a fixed point with a 50-round fail-closed limit (1981–2009). Intraprocedural analysis has a 100-round fail-closed limit (1924–1944).
- The final body pass analyses both functions and policies with an empty seed; there is no policy-parameter summary phase (2011–2016).

The fixed-point failure behaviour is a positive design property: an exhausted analysis does not silently accept a partial result. The redesign should preserve this property while replacing the coarse domain.

## 3. Finding-to-rule conformance matrix

The following entries map the independent TYPE findings to the rules required by the proposed specification.

| Finding | Missing or incomplete rule | Source-level evidence | Assessment |
|---|---|---|---|
| TYPE-01 | Context-specific encoder result types and sink contracts | Encoder checker returns generic TY_STR for escape_c, escape_csv, and escape_json; only HTML and log have distinct result types (checker around 1055–1057) | Gap |
| TYPE-02 | Aggregate parameter paths in summaries | Only TY_INT parameters are seeded (1956–1970) | Gap |
| TYPE-03 | Alias-aware abstract heap | base_marked resolves only syntactic root variable name (1850–1859) | Gap |
| TYPE-04 | Interprocedural heap-write effects | Summary has no heap-effect component (1801–1805); caller summary application only handles return dependencies (1839–1845) | Gap |
| TYPE-05 | Provenance through generic text conversion | derived() has int_to_str but no to_text transfer (1821–1852) | Gap |
| TYPE-06 | Provenance through collection-consuming join | Checker types join but derived() has no join rule (checker 1029–1036; 1821–1852) | Gap |
| TYPE-07 | Provenance through tainted length | No .len() transfer in derived() (1821–1852) | Gap |
| TYPE-08 | Comparison-result provenance | No comparison or Boolean-result transfer in derived() (1821–1852) | Gap |
| TYPE-09 | Provenance for Boolean and other local types | Local marking is restricted to TY_INT and TY_STR (1891–1893) | Gap |
| TYPE-10 | Map key and key-set provenance | set marks from final argument only; keys() has no transfer (1907–1909; 1821–1852) | Gap |
| TYPE-11 | Scalar string and other non-integer parameter summaries | Summary seeds only TY_INT (1960–1968) | Gap |
| TYPE-12 | Map membership/removal result provenance | No has or remove transfer in derived() (1821–1852) | Gap |
| TYPE-13 | Optional values as payload-bearing locals | Direct optional binding is marked at N_IF; declarations only mark int/string (1915; 1891–1893) | Gap |
| TYPE-14 | Struct constructor field provenance | Aggregate mutation is recognised for assignment; no constructor transfer in flow_walk (1887–1921) | Gap |
| TYPE-15 | Collection shape/length provenance | No collection .len() transfer or shape domain (1821–1852) | Gap |
| TYPE-16 | Receiver and struct-parameter summary dependencies | Only int parameters are seeded, so struct receiver paths are not analysed as parameter sources (1960–1968) | Gap |
| TYPE-17 | Enum payload construction and match binding | Parser/checker construct and type enum payloads, but flow analysis has no enum payload or match-binding transfer (parser enum construction; checker match handling; flow 1887–1921) | Gap |
| TYPE-18 | Map value provenance on trusted-key lookup | get special case tests derived key; it does not consult map value provenance (1825; 1829) | Gap |
| TYPE-20 | Policy parameter summaries and authorize-site instantiation | Summary fixpoint includes only N_FN; final policy analysis uses empty seed (1987–2000; 2011–2016) | Gap |
| TYPE-21 | Policy purity/effect checking | Policy bodies receive no effect summary or transitive purity check in this analysis; separate checker review found in_policy is set/reset but not used to gate effects | Gap |

TYPE-19 is withdrawn as a false positive and is not part of this matrix.

## 4. Existing regression coverage: what it proves and what it does not

The CWE atlas contains positive evidence for selected laundering patterns:

- Direct byte-by-byte reconstruction with char_str and helper-mediated byte extraction (tests/cwe/atlas.py:73–83, with reject cases at 206–209).
- Derived bytes stored in a list and later reconstructed (210–212).
- Derived byte assigned into a struct field after construction (213–214).
- A control-flow-only reconstruction case is recorded as logic, not as a compiler rejection (215–216).
- A trusted lookup table indexed by untrusted bytes is expected to be rejected (597–600).

The CWE coverage document states that byte reconstruction is rejected through helper functions and parameters, lists, maps, struct fields, bit masks, and wrapping arithmetic, while pure branch-only information is not tracked (docs/CWE-COVERAGE.md:91–96).

These are useful regression guarantees. They do not demonstrate complete coverage of every aggregate shape or every parameter type. In particular, the atlas cases cited above do not establish alias propagation, map key/value separation, constructor-initialised struct fields, enum payload bindings, stored optionals, general string-parameter summaries, or policy parameter propagation.

The documentation claim should therefore be read as a claim about the tested and implemented cases, not as proof of a complete general-purpose heap provenance analysis. The proposed semantics deliberately make the broader target explicit.

## 5. Recommended first implementation slice

The highest-leverage first slice is a value-level provenance domain for scalar values, before introducing a general heap.

It should include:

1. Provenance on every scalar abstract value, including bool.
2. Transfer for comparisons, Boolean operators, to_text, int_to_str, char_str, join, and .len().
3. Local assignment and reassignment as value updates rather than permanent variable-name marking.
4. A complete builtin transfer table with conservative fallback.
5. Negative and positive regressions for every transfer, including alpha-renaming and temporary-local metamorphic variants.

This slice closes several direct gaps without prematurely choosing heap precision. It must not be presented as solving aliasing, aggregate mutation, map key/value effects, optional payloads, enum bindings, or interprocedural heap effects; those remain later stages.

## 6. Review gates before implementation

The following design choices must be resolved by the language and security owners:

- Does default provenance rejection include length, collection shape, and membership disclosures, or are these allowed unless they reach a narrower reconstruction sink?
- Is a value's dependency relation tracked only by source identity, or also by structured input paths and dependency kind?
- Which nominal context types are introduced, and how are context guarantees preserved or invalidated by concatenation?
- Are user-defined validators trusted by declaration, verified by a restricted effect/contract system, or treated as ordinary functions?
- Are policies required to be pure, and are transitive calls checked for effects?
- What is the precise conservative fallback for an unsupported builtin or opaque external function?

Until these decisions are settled, implementation should retain the current fail-closed principle and avoid weakening existing rejection cases.

## 7. Verification status

- Repository changes in this assessment: none.
- Compiler or runtime builds run by this assessment: none.
- Candidate examples compiled or executed: none.
- Evidence type: source inspection and comparison with existing test source.
- Required next evidence: executable regressions, full project test campaign, sanitizer/fuzz campaigns as applicable, and formal proof of the transfer/summarisation soundness claims.
