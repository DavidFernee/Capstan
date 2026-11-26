# RFC formalisation bridge — v0.7 reconciliation (draft)

**Status:** review draft, not adopted syntax or machine-checked proof. **Repository baseline:** `main` tree `d5efd7a8488261914cf191c39c22ba26fa43aaa1` (2026-11-26 UTC). The live repository is concurrently changing; re-pin all evidence before ratification.

## Precedence and compatibility

The imported RFC 0001–0020 working draft supplements rather than supersedes the extant `docs/SPEC.md`, `docs/architecture/LANGUAGE-CORE.md`, `docs/architecture/CCAM.md`, `docs/architecture/ccam-v0.1.schema.json`, `formal/` and `docs/assurance/`. Their current implemented fragments and versioned contracts are the baseline for reconciliation. Conflicts remain open until explicit versioned decisions and tests; the RFCs do not authorize speculative source incompatibilities.

Important reconciliations:

1. Current source identifiers are ASCII `[A-Za-z_][A-Za-z0-9_]*`; RFC 0002's Unicode normalization requirement is a future extension question, not permission to silently permit Unicode identifiers. Unicode in string data is separate.
2. Source `int` is signed 64-bit with checked overflow. In particular `MIN % -1 = 0` whereas `MIN / -1` traps: retain this already-documented source/CCAM agreement (RFC 0009).
3. The source-language reference currently includes `Tainted`, `Secret`, `Html`, `LogText`, `Grant<P>`, structs, collections and optionals. Scalar core types and typing tables in `LANGUAGE-CORE.md` are a deliberately restricted subset, not a full type-system proof (RFC 0003).
4. CCAM v0.1 has a closed, typed JSON design, a Capstan-native in-memory single-frame evaluator and partial validator, and experimental multi-function/backend work. Complete canonical JSON decoding, full instruction validation and source-to-native refinement are not established by this document (RFC 0011/0013).
5. Core evaluation is strictly left-to-right; a trap prevents later operand evaluation. The CCAM step counter charges the instruction that traps. Source bounds and global runtime budgets must be reconciled with *separate* validation and execution budgets (RFC 0004/0015).
6. The baseline default executable remains C-backed; the production all-Capstan toolchain is an explicit future acceptance gate (RFC 0012). External Lean/Python verification tools remain independent research/certification tooling rather than production toolchain components.
7. The existing `docs/research/COMPARATIVE-EVALUATION-PROTOCOL.md` is the comparison protocol foundation; RFC 0018 must not invent benchmark wins.

## Initial formal scalar core: scope-limited, mathematical specification

This defines a *proposed* executable-paper fragment sufficient for the first refinement obligations, not the full Capstan grammar or a new normative syntax. For accepted scalar source:

```ebnf
CoreType  ::= "int" | "bool"
Expr      ::= Int64Literal | "true" | "false" | Identifier
            | "-" Expr | "!" Expr
            | Expr ("+"|"-"|"*"|"/"|"%"|"=="|"!="|"<"|"<="|">"|">="|"&&"|"||") Expr
            | Identifier "(" [Expr ("," Expr)*] ")"
Stmt      ::= CoreType Identifier "=" Expr ";"
            | Identifier "=" Expr ";"
            | "return" [Expr] ";"
            | "if" "(" Expr ")" Block ["else" Block]
            | "while" "(" Expr ")" Block
            | Block | Expr ";"
Block     ::= "{" Stmt* "}"
```

The EBNF above describes *abstract precedence-free constructors*. It is **not** a complete concrete grammar: tokens, precedence, comments, full-input parsing, imports, declarations, policies, effects, lifetime and error recovery remain governed by existing implementation/reference and require machine-differential reconciliation. Do not use this EBNF to build a permissive parser.

Let `Γ` map initialized local variables to types, `Σ` function names to signatures, and `T` range over `int | bool`. Initial syntax-directed rules:

```text
(T-Int)    n ∈ Int64                      ─────────────── Γ;Σ ⊢ n : int
(T-Bool)   b ∈ Bool                       ─────────────── Γ;Σ ⊢ b : bool
(T-Var)    Γ(x) = T                       ─────────────── Γ;Σ ⊢ x : T
(T-Arith)  Γ;Σ ⊢ e1 : int  Γ;Σ ⊢ e2 : int ─────────────── Γ;Σ ⊢ e1 op e2 : int
           op ∈ {+,-,*,/,%}
(T-Cmp)    Γ;Σ ⊢ e1 : int  Γ;Σ ⊢ e2 : int ─────────────── Γ;Σ ⊢ e1 cmp e2 : bool
(T-BoolOp) Γ;Σ ⊢ e1 : bool Γ;Σ ⊢ e2 : bool ────────────── Γ;Σ ⊢ e1 bop e2 : bool
(T-Call)   Σ(f)=(T1,..,Tn)→T; ∀i Γ;Σ⊢ei:Ti ─────────── Γ;Σ ⊢ f(e1,..,en):T
```

`op` and `cmp` are not overloaded in this fragment; type-compatible equality admits equal `bool` operands as the current core reference does. A void call is permitted as a statement only. No integer/boolean implicit coercion exists. Extended judgment `Γ;A;Σ ⊢ e:T ! E` for effects and capabilities is an **open proof obligation**, not derivable from the scalar rules alone.

Define evaluation configurations `⟨control, store, frames, fuel, trace⟩` where `trace` collects security-relevant terminal results, traps, committed effects and logical charges. A transition must either (i) take one internal deterministic step relative to externally supplied events, (ii) terminate, (iii) emit a specified trap, or (iv) enter a separately defined external-wait state. Unknown behavior is rejection/stuck-model defect, never permission to execute. **Detailed transition rules for all constructors remain open**.

Representative proposed arithmetic rules for already evaluated values `a,b:Int64`:

- `a+b`, `a-b`, `a*b`: produce exact mathematical result if representable; otherwise `Trap(integer_overflow)`.
- `a/b`: `Trap(division_by_zero)` if `b=0`; `Trap(integer_overflow)` if `a=MIN ∧ b=-1`; otherwise signed quotient truncated toward zero.
- `a%b`: `Trap(division_by_zero)` if `b=0`; `0` if `a=MIN ∧ b=-1`; otherwise remainder with dividend's sign.
- Short-circuit `&&` and `||` do not evaluate the right operand when the left value decides the result. All other binary expression operands evaluate left-to-right and abort before evaluating the right when the left traps.
- Any host-lowered operation that could invoke undefined behavior must use a checked implementation.

### Required proof statements (not yet theorems)

**Preservation:** If `Γ;Σ ⊢ e:T` and `⟨e,σ⟩→⟨e',σ'⟩`, then there exists a well-typed successor configuration (including appropriately updated store typing), or a specified trap with no forbidden effect.

**Progress or explicit wait:** A closed well-typed configuration is a value, permits a step, emits a permitted trap, or is in a specifically modelled external wait. This must not misclassify deadlock, unbounded waiting, undefined host actions or disallowed effects as progress.

**Robust refinement:** With a **nonempty** independently defined admissible target-context relation, every target observation (including maximal traces, divergence, committed effects and logical resource charges) must be allowed by a related source execution; hyperproperty claims need relational trace preservation. Linker, loader, OS and hostile foreign contexts are explicit assumptions.

**Authority invariant:** Every effect commitment has a linearization point at which its principal, stable object identity, operation and nonreused epoch are authorized. Queued work cannot rely solely on admission-time checks. Revocation, cancellation, deduplication and retry must preserve ownership and reservation conservation.

**Budget invariant:** For each resource dimension `d`, `0≤spent_d + reserved_d + free_d = capacity_d` (with per-resource semantics for cumulative vs live ledgers). Admission atomically reserves across dimensions; releases must not decrease cumulative spent work.

### Concrete required checker/refinement work

| Stage | Proof/replay target | Required negative control |
|---|---|---|
| Byte stream → lexer/parser → AST | one canonical parse, bounded work, full-input consumption | malformed UTF-8/control chars, trailing tokens, normalization collision on proposed extensions |
| Checker → typed AST | substitution/preservation, grant/provenance labels | type cast, taint through container/closure, invalid grants |
| Typed AST → CCAM | forward simulation and rejection preservation | reordered trapping operands, wrong remainder case |
| CCAM JSON → validated CCAM | decoder totality, unique canonical representation, complete schema | duplicate keys, unknown opcodes, unreachable malformed instructions |
| CCAM → evaluator | step-level simulation, exact trap and fuel order | stale certificate, out-of-range branch, call/return mismatch |
| CCAM → native binary | simulation including memory, authority, traps and cost | incorrect relocations, elided check, hostile linked code |
| Native runtime/OS | adapter contract and explicit TCB | stale file descriptors, blocking I/O, partial commit, crash/retry |
| Evidence → CWE claims | theorem/assumption linkage with dependency invalidation | vacuous premise, stale source hash, admitted axiom |

A sound proof over a *reference model* is not a proof of executable compiler/runtime correspondence. Each claimed theorem needs its real checked source, toolchain pin, trusted axioms inventory, clean replay and exact source/target artifacts.

## Critical open acceptance gates

- Ratify the concrete grammar from `compiler/lexer.cap`/`compiler/parser.cap` and existing `docs/SPEC.md`; do not silently add Unicode identifiers.
- Complete effect/grant/taint/secret/ownership typing rules and mechanized substitution and preservation.
- Specify executable operational semantics for full declarations, calls, heap, I/O, concurrency and cancellation.
- Complete CCAM opcode/decoder inventory and map exact native evaluator/backend, including v0.2 or later features **only after versioning**.
- Establish target ABI/platform assumptions, robust secure compilation and physical-cost/leakage bounds.
- Require an independent review and governance ratification process before a 1.0 conformance claim.

## Bounded-model test evidence and limitations

The supplied Python model, which is *external research tooling*, was executed locally with `python docs/rfc/models/revocation-crash-model.py` using its own assertions. It enumerates (a) one live/revoked object, one queued request, three units budget, epochs 0–2, and (b) one crash/retry operation with at most two effects. Output is archived in `docs/rfc/models/revocation-crash-results.txt`. The fixed models yield zero violating *explored* edges, while unsafe controls yield explicit witnesses. This is not evidence of complete concurrent Capstan implementation correctness, durable atomicity in a real datastore, or the absence of vulnerabilities beyond the enumerated states.

## Academic and comparative input status

The imported v0.7 draft cites 2025–2026 research on structural information flow, secure compilation, model/specification inconsistency, dataflow, machine-code verification, and speculative/physical leakage. Those references are **research leads**, not independently reproduced proofs for Capstan. The repository's `docs/research/` survey series and `COMPARATIVE-EVALUATION-PROTOCOL.md` supply the baseline protocol. Before asserting new research-informed normative changes, verify publication metadata/full-text assumptions and independently challenge the applicability. Measure only version-pinned, assurance-matched workloads with per-metric negative results, and do not infer universal programming-language superiority.
