# A01 — Frontend traceability (RTM-004)

Pinned baseline 3187b3adc3d9b2f5476c2d25ed410da1ec1c88ce. Static inspection only. All requirements unaccepted; active #539/#444/#481 work must be reconciled before new implementation.

| ID | Requirement | Concrete evidence | Acceptance gap |
|---|---|---|---|
| R01.02 | Bounded source and import graph | ast.cap CompileBudget; MAX_SOURCE_BYTES, MAX_TOTAL_SOURCE_BYTES, MAX_IMPORT_FILES | Admission before allocation; all entry points and native loader limits |
| R01.03 | Exact tokenization of untrusted input | lexer.cap Lexer, lex_run, lex_hex | Grammar correspondence, malformed byte corpus |
| R01.04 | Literal semantics independent of target | lex_string, escape_c representation; ccam_decode_escaped_literal | Canonical byte values independent of C escaping; round-trip and malformed tests |
| R01.05 | Bounded token and interpolation work | add_tok, shared CompileBudget | Cost bound including nested lexers and intermediate buffers |
| R01.06 | Parser grammar and precedence | parse_binary, parse_unary, parse_type | Grammar acceptance equivalence and associativity corpus |
| R01.07 | Parser totality and recovery | enter, leave, recover_statement, recover_declaration; MAX_NESTING=1000, MAX_SYNTAX_ERRORS=50 | Progress measure, physical stack safety, EOF/token invariant |
| R01.08 | AST shape and provenance | Node constructors, charge_ast_nodes | Closed shape validation, source spans, reject partial trees |
| R01.09 | Binding and scopes | checker declare, push_scope, pop_scope; lowerer locals map | Stable binding identity and shadowing policy preserved |
| R01.10 | Type preservation | checker check_expr, check_type, ast type_eq, assignable | Checked-tree authenticity, soundness and lowering relation |
| R01.11 | Capability authority | checker contains_grant, policy tables, privileged | Explicit effect/capability judgement and no erasure in lowering |
| R01.12 | Contextual text and taint | checker html_context, ast is_contextual_text | Native output sinks preserve contextual trust distinctions |
| R01.13 | Mandatory bounded input | #444 active; shared compile limits not language-wide input syntax | Grammar, checker, runtime and negative conformance |
| R01.14 | Deterministic lowering | ccam_lower_checked_program, ccam_lower_emit | Same checked source produces canonical CCAM and evidence |
| R01.15 | Control flow and evaluation order | ccam_lower_short_circuit, loop patching; regression tests | Side effects, trap precedence and nested loop simulation |
| R01.16 | Typed calls and returns | ccam_lower_call_expression; recursion, void and Bool tests | Source signature and CCAM frame correspondence |
| R01.17 | Unsupported constructs fail closed | scalar lowerer subset rejection test | Exhaustive node/type dispatch coverage; no silent fallback |
| R01.18 | Production aggregate workload | #481, AST List/Map/optional/string dependencies | Execute actual lexer/parser/checker through managed CCAM |
| R01.19 | Diagnostics separate from executable output | Ctx, report_at, parser failed/fatal fields | No artifact on error; deterministic bounded diagnostic output |

## Findings

F-004: Lexer and AST carry C-escaped literal representations. Native lowerer explicitly decodes them and has octet round-trip tests; this is a transitional coupling, not evidence of a defect. Introduce target-neutral canonical literal representation through a controlled interface change rather than deleting compatibility code prematurely.
F-005: Mutable Node.ty is optional; checker typed() writes it and ty_of() returns TY_ERR when absent. Establish an authenticated checked-program boundary or revalidate semantic invariants before lowering. No bypass is demonstrated by this observation.
F-006: Parser depth bound is not a physical stack proof. Establish token-list EOF invariant for cur(), progress for recovery, and worst-case stack charge for nested recursive calls before claiming robust hostile-input handling.
F-007: ast.cap aggregate source ceiling is 32 MiB while native backend architecture describes 64 MiB. Determine whether these are intentionally separate admission layers; reconcile actual loader and compiler enforcement rather than silently choose either.
F-008: Existing scalar lowering tests show useful coverage but do not establish production aggregate workload closure or preservation of taint/effects. Build a grammar-node/type/effect coverage ledger tied to actual compiler sources.

## Pinned artifacts

compiler/lexer.cap 6bc9bf8; compiler/parser.cap b656da7; compiler/ast.cap 7202b16; compiler/checker.cap 9b485cf; verification/ccam_lowering.cap db91956. Existing test declarations inspected, not executed. No new theorem or correctness claim. Keep #451 open until source and native refinement accepted. Next: runtime/GC traceability then bootstrap and optimisation, followed by live main reconciliation.
