# C-free type-safety assurance

**Programme:** issue [#80](https://github.com/DavidFernee/Capstan/issues/80)  
**Implementation work:** issue [#451](https://github.com/DavidFernee/Capstan/issues/451)  
**Status:** proposed assurance profile; existing CCAM scalar model is machine-checked, but end-to-end implementation correspondence is not established.

## Claim boundary

See the [execution assurance architecture](EXECUTION-ASSURANCE-ARCHITECTURE.md) and its [machine-readable boundary register](execution-boundaries.json) for the end-to-end path, current implementation dispositions and explicit unproved links. The register is schema-validated and checked in CI; a model-level theorem cannot be promoted to implementation proof without an explicit refinement flag and review.


The intended proof path is:

```text
Capstan source
  -> parser and source checker
  -> checked scalar source core
  -> source-to-CCAM lowering
  -> complete CCAM validation
  -> CCAM abstract execution
  -> native backend
```

The proof target is the C-free pipeline. Generated C, the host C compiler and the legacy C runtime are not part of the proof chain. The legacy backend may remain a temporary differential comparator, but its output is not semantic authority.

Initial profile: signed 64-bit integers, booleans, scalar locals, supported scalar expressions, structured control flow, direct calls and returns. Strings, heap values, collections, optionals, user-defined aggregate types, taint, secrets, HTML/JSON/log contexts, grants, IO, concurrency and FFI remain outside the profile until represented in CCAM and covered by their own proof obligations.

## Existing formal evidence

| Layer | Existing evidence | What it establishes | What remains unproved |
|---|---|---|---|
| CCAM value/register model | `verification/lean/CapstanVerification/Core.lean` | Disjoint int/bool values, signed-64 range, typed register invariant, checked operations, preservation lemmas for scalar writes/operations | Correspondence to executable Capstan list/object semantics and full machine execution |
| Single-frame machine | `Machine.lean`, `Progress.lean` | Intrinsically typed instruction operands, typed machine states, one-step outcomes, deterministic functional semantics, scalar register invariant preservation | Multi-function call frames, full normative CCAM, and concrete evaluator simulation |
| Raw instruction validator | `Validator.lean`, `ProgramValidator.lean` | Natural indices converted to `Fin`; successful scalar instruction construction carries exact register types and bounded targets; conservative final-terminal proof profile | JSON decoding, complete whole-program schema, normative reachability validator, concrete validator equivalence |
| Native register bridge | `NativeRegisterBridge.lean`, `NativeRegisterFileBridge.lean`, `InitialStateBridge.lean` | Mathematical correspondence for register tags, values, bounded list reads/writes, typed register-file relations, pairwise initial native/abstract register construction from one validated scalar type vector, and conversion into the reusable `NativeRuntimeRegisterFileRelation`; the finite indexed model's empty runtime register vector is related to the abstract initial list | Proof that actual Capstan list/object operations and full native evaluator implement this model; connection from the list-level initialisation relation to the concrete evaluator's constructor and the complete machine state |
| Source-to-CCAM lowering | `verification/ccam_lowering.cap`, `docs/architecture/COMPILER-CCAM-LOWERING.md` | Executable lowering exists for a restricted checked scalar subset and rejects unsupported constructs | A formal source typing judgement, lowering simulation theorem and production CLI integration |
| Multi-function CCAM | `verification/ccam_calls.cap`, `verification/ccam_core.cap`; new `verification/lean/CapstanVerification/MultiFunction.lean` | Executable bounded call-frame evaluator exists; Lean proves exact parameter-to-leading-register transfer, uninitialised locals, typed callee register-file construction, exact return/destination type contracts, and preservation of the caller register invariant when a correctly typed return value is committed to its destination | Full multi-frame small-step semantics, validator soundness, caller/callee state simulation and concrete evaluator correspondence. New lemmas are pending exact-head CI |
| Native backend | `verification/ccam_native_x64.cap`, `docs/architecture/CCAM-NATIVE-BACKEND.md` | Experimental freestanding Linux x86-64 backend exists | End-to-end CCAM-to-machine-code refinement and supported-target conformance |

These are deliberately separate evidence layers. A theorem over `Fin`-indexed Lean instructions does not prove the Capstan parser, checker, validator, lowerer, evaluator or native backend correct.

## Required proof ladder

### CF-TS1 — CCAM scalar machine invariant

Retain the intrinsically typed representation as the semantic core. Prove for every successful machine transition that the resulting register file remains well-typed; every failure is a specified trap and leaves no partially committed destination write. Cover every instruction constructor, not only arithmetic. Prove return payloads satisfy the declared function result type.

### CF-TS2 — Complete validated program

Replace the current proof-profile gap with a model of the multi-function CCAM program: unique function names, entry validity, complete closed instruction schemas, register and branch bounds, exact call signatures, return contracts, reachable control-flow safety and bounded resource fields. Prove that successful validation constructs only intrinsically well-typed programs. Model JSON decoding and duplicate-key rejection separately; do not conflate an in-memory validator with a safe decoder.

### CF-TS3 — Call-frame preservation

Model function signatures, typed arguments, frame-local register files, caller continuations and return destinations. The initial model now proves argument transfer, local-register initialisation, typed frame construction, return-value and destination contracts, and preservation of the caller's register invariant when the returned value is written. The next proof step is a full heterogeneous multi-frame small-step semantics matching the concrete push/call/pop protocol. Prove call-depth/step exhaustion traps before an invalid state transition.

### CF-TS4 — Source checker and lowering

Define the formal typing judgement for the actual C-free scalar source subset, including lexical environments and function signatures. Prove accepted expressions have unique types. Prove the executable lowerer's emitted CCAM instructions preserve source evaluation order, short-circuit behaviour, checked arithmetic, branch/loop semantics, call signatures and return types. Unsupported syntax must fail closed.

### CF-TS5 — Native refinement

Relate validated CCAM states and outcomes to native machine states and observable outcomes. Cover all emitted opcodes, register allocation/spills, arithmetic overflow, control flow, calls/returns, traps, stack limits and ABI transitions. Make OS and hardware assumptions explicit.

### CF-TS6 — Trust and reproducibility

Pin the source revision, Lean toolchain, dependencies and build flags. Run the Lean build with warnings as errors, independent proof replay and axiom audit. Tie every implementation correspondence result to exact source hashes. Add negative controls that must fail, plus adversarial malformed-program, boundary, differential and fuzz corpora.

## Immediate engineering order

1. Extend `MultiFunction.lean` from the proved call-entry/return contracts to a complete typed multi-frame transition model matching `ccam_calls.cap`.
2. Strengthen the formal program validator to cover function tables and cross-function call signatures; preserve the conservative single-frame validator as a named proof profile rather than calling it the normative validator.
3. Connect the existing `ccam_lowering.cap` test corpus to generated CCAM conformance vectors, then prove the source-to-CCAM relation for the supported subset.
4. Complete the initial-state bridge by connecting the Lean register constructors to the concrete evaluator's actual register-list constructor, then prove whole-state initial correspondence (PC, counters, return contract and frame stack).
5. Extend concrete refinement from register-file operations to the full Capstan CCAM evaluator.
6. Add the native backend as a subsequent refinement layer, not as an independent semantics.

## Release and marketing claim policy

Until CF-TS4 and CF-TS5 are discharged, do not claim that the production C-free compiler is formally type-safe. The accurate statement is that Capstan has a machine-checked, restricted scalar CCAM model with typed-state preservation properties, while source-checker, full-program validator, lowering, concrete evaluator and native-backend correspondence remain open.

Do not use the old generated-C compiler as a proof foundation. Its only permitted role in this workstream is temporary differential testing while the C-free path matures.