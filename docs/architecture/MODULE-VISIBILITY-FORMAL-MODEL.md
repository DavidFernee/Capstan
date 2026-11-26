# Module visibility judgement: formal policy slice

This change adds a small Lean 4.19 model of the policy for the `private`
struct-field and `opaque struct` features.

It formalises:
- field read, write and literal-initialisation decisions;
- private fields being inaccessible outside their defining source module;
- every field of an opaque type being inaccessible outside that module;
- public, non-opaque fields retaining cross-module access;
- opaque values being constructible only inside their defining module.

## Evidence boundary

This is a formalisation of the intended policy, **not a proof of the compiler
implementation**. The judgement currently takes module and declaration
identity as already-resolved inputs. It does not prove that the import loader
assigns correct source-file identities, that AST nodes preserve them, or that
every parser/checker path calls an equivalent predicate. It does not prove
diagnostic non-disclosure or soundness of generated C.

The next proof gate is an implementation bridge: identify the exact checker
predicate and AST fields, then prove or mechanically test that each production
decision is equivalent to this judgement. Until that bridge exists, PR #360
remains an implementation with regression tests and an independently checked
policy model, not a formally verified compiler feature.

## Proposed correspondence to the current compiler slice

The implementation proposed in PR #360 has a direct, reviewable mapping to the
abstract inputs of this judgement:

| Formal input | PR #360 compiler representation |
|---|---|
| `ownerModule` | `c.structs.get(sname).file`, the defining struct AST node's source-file index |
| `currentModule` for field reads | `N_GETF` expression node's `e.file` |
| `currentModule` for field writes | `check_stmt` checks an `N_ASSIGN` target through `check_expr`, so the target `N_GETF` node's `e.file` is consulted |
| `currentModule` for field initialisation | `N_INIT` node's `init.file` |
| `currentModule` for opaque construction | `N_NEW` expression node's `e.file` |
| `fieldIsHidden` | `field_is_private`: field marker `fd.s2 == "private"` or containing struct marker `st.s3 == "opaque"` |

The import loader in `compiler/main.cap` assigns each loaded path an integer
index, passes it into `lex`, and stores it in `Ctx.files`; lexer/parser nodes
retain the token's file index. The checker resolves the field through the
containing struct's declaration before applying the module comparison.

This table is a source-level correspondence argument, **not a machine-checked
refinement theorem**. The Lean model intentionally treats the field
declaration as already resolved. Remaining proof obligations include unique
and stable type/declaration resolution, source-index integrity through every
AST construction/transformation, completeness of all access paths, and
agreement with generated code. The production checker must be connected to
this judgement before claiming formal verification.
