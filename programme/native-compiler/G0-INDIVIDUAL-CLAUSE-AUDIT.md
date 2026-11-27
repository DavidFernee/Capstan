# G0 individual clause traceability audit

Candidate architecture links, not normative approval. A = NATIVE-COMPILER-ARCHITECTURE-RFC.md blob 91c804c63b0cef4cc68315ac396dd4ff5ac3df7c; C = CCAM.md blob ff0d483d4e4bc38778b0d60d21ea706693e748b0; G = NATIVE-CAPSTAN-GC.md blob 7ee4cbc2145d9eb881fe0651e263a8f160c18c41. Numbers are sections. Architecture-level coverage is not a substitute for detailed language clauses or approval of proposed profile semantics. Existing evidence and obligations reproduced as inventory, not reverified.

## SCALAR

Source matrix blob: 0fbe62cced3da36ecc13b9141648715b386de209.

| ID and requirement | Architecture clauses | Existing matrix evidence / open obligation |
|---|---|---|
| R02.01 — Exact signed-64 JSON decoding, reject duplicate/unknown fields | C2,2.1,3.1; A3.3 | CCAM JSON decoder contract; in-memory validator is insufficient; No decoder refinement identified; Raw adversarial corpus and closed decoder proof |
| R02.02 — Typed register indices and instruction schemas | C2,3.1 | ccam_validate_single_frame; ccam_core_tests.cap; ProgramValidator.lean; SF-P restricted admission; Prove concrete admission correspondence, then normative completeness |
| R02.03 — Reachable fall-through rejected; unreachable final nonterminal allowed | C3.1 | ccam_validate_single_frame; SF-P final-slot rule is deliberately stronger; Reachability invariant and differential accept/reject vectors |
| R02.04 — Canonical named calls and signatures | C2.1,3.1; A3.3 | ccam_calls.cap side table; #547 work, not accepted; Exact external-to-internal mapping and validation |
| R03.01 — Addition overflow | C4 | ccam_add; ccam_core.cap tests; native overflow vector; SFVectors.lean sfP_run_SF002; Concrete/native correspondence for all operands |
| R03.02 — Subtraction/multiplication overflow | C4 | ccam_sub, ccam_mul; core arithmetic tests; Core.lean model, concrete refinement open; Boundary and operand precedence evidence |
| R03.03 — MIN/-1 division traps | C4 | ccam_div; native div-overflow vector; SFVectors.lean sfP_run_SF003; Exact native terminal record and refinement |
| R03.04 — MIN%-1 returns zero | C4 | ccam_rem; native rem-min vector; SFVectors.lean sfP_run_SF004; Exact result comparison, not exit-status-only |
| R03.05 — Zero divisor traps | C4 | ccam_div, ccam_rem; native divzero vector; SFVectors.lean sfP_run_SF005 covers division; Both operations, exact trap and step count |
| R03.06 — Exact integer terminal result | C6; A10.1 | #552 direct fd-3 result/CCAMRES v1 candidate; SFVectors.lean sfP_run_SF001 models 42; Distinguish 0/256, MIN/MAX, void, transport failure |
| R03.07 — Uninitialised read and typed destination checks | C2,8 | ccam_register_read_int/bool and write_int/bool; native uninitialised vector; RuntimeBridge.lean representation relation per contract; Concrete read/write simulation and failure atomicity |
| R03.08 — Left-to-right call reads; depth check afterward | C5,7 | ccam_calls.cap; ccam_initial_state_tests.cap; #549 ordered reads, #547 prerequisite; Prove implementation correspondence and exact competing-trap vectors |
| R03.09 — Atomic return pop/write | C5 | ccam_calls.cap; #527 active; Preflight invalid destination; unchanged stack and destination on failure |
| R03.10 — Explicit trap reason preserved | C3.1,6 | CCAM.md; native trap exits insufficient; SF-P excludes entire explicit trap opcode; Bounded reason and exact code/function/PC/detail record |
| R05.01 — Step counted on instruction trap; exhaustion before next instruction | C5; A8 | ccam_core.cap; native step-limit vector; budgetedMachineStep_consumes_one; budgetedMachineStep_exhausted_before_instruction (model only); Concrete step/trace equivalence at 0, N-1, N and N+1 |
| R05.02 — Call depth includes entry frame | C5 | ccam_calls.cap; native depth-limit vector; Multi-frame work #547; Exact boundary and failure state correspondence |
| R01.01 — Checked scalar source lowered deterministically | A3.2,4 | ccam_lowering.cap; tests/run.sh frontend invocation; #451 open; Accepted subset theorem and source/CCAM differential corpus |

## AGGREGATE

Source matrix blob: a73bc319ec5bb6e03b798a9bc59ca27a699ec972.

| ID and requirement | Architecture clauses | Existing matrix evidence / open obligation |
|---|---|---|
| R04.01 Opaque reference provenance | A7.1 | A; ccam_heap_object_index; ccam_aggregate_write; cross-arena/opaque probes in tests/run.sh; Concrete opacity and native handle refinement |
| R04.02 Nominal descriptor and field types | A7.1,7.3 | A; ccam_heap_value_has_type, field_get/set; Immutable canonical descriptor authority; typed native correspondence |
| R04.03 Field initialization and mutability | A7.2,7.3 | A; field_initialised, field_mutable; heap record tests; Preservation across every aggregate transition |
| R04.04 Array index within logical length | A7,8 | A; array_get/set/append/len; array tests; Exact bounds and capacity preservation |
| R04.05 Immutable byte values | A3.3,7 | A; bytes_concat, byte_get, bytes_slice; NUL and concatenation tests; Byte-exact native semantics and bounded charges |
| R04.06 Reference-bearing register admission | A3.3,7.1 | A; ccam_aggregate_write/read; Canonical schema and call-frame integration |
| R04.07 Failure-atomic allocations | A8 | A; allocation_check; exact budget tests; Model-to-concrete simulation; allocator failure injection |
| R05.03 Byte/object/work/temp quotas | A8 | A; ccam_heap_create_bounded; Actual native memory/temporary overhead bound, not logical charges alone |
| R05.04 Aggregate step ordering | A8; C5 | A; ccam_aggregate_begin_step; alloc_record checks destination before begin_step; Define invalid operand vs fuel priority consistently with admitted instruction semantics; test competing faults |
| R04.08 Frame-exclusive capability authority | A7.2,9 | R; CCAM-MEMORY-SECURITY-CONTRACT.md; CFG transfer and runtime owner refinement |
| R04.09 Generation exhaustion, reset and close | A7.1,9 | R; proposed checked non-wrapping generations; Concrete generation boundary and stale-view tests |
| R04.10 No capability duplication or escape | A7.2,9 | R; contract restrictions on moves, fields, calls; Validator and source-lowering enforcement |
| R04.11 Exact join and bounded analysis | A4,8,9 | R; proposed exact capability-state join; Loop convergence/budget rejection and soundness |
| R04.12 Complete backing wipe on unwind | A7.2,9 | R; proposed every-frame exit contract; Normal return/trap/cancellation/limit tests and native wipe preservation |
| R04.13 Checked layout arithmetic | A7.1,8 | R; proposed interval/layout invariants; Overflow, alignment and end bounds proof |
| R04.14 Collection root completeness | A7.3 | G; native GC design, not arena semantics; Root map + safepoint completeness and compiler/runtime relation |
| R04.15 Stale reference rejection after reuse | A7.1 | G; CCAMHeap.lean stale_handle_rejected_after_recycle (abstract model); Concrete generation/slot exhaustion and reuse refinement |
| R05.05 Bounded collection and allocation failure | A7.3,8 | G; proposed native runtime; Worst-case resource contract and failure atomicity |

## NATIVE

Source matrix blob: 5665858ae9608954117d8722cb83779037410f6a.

| ID and requirement | Architecture clauses | Existing matrix evidence / open obligation |
|---|---|---|
| R07.01 — Validate before emission | A3.3,3.5,4 | ccam_x64_emit_linux_elf; Prove accepted profile and rejection before output |
| R07.02 — Bound code expansion | A8 | 8192 instructions, 65536 registers; expansion test; Bound emitted bytes, intermediate storage and compilation work |
| R07.03 — Disjoint aligned stack slots | A3.6,10 | ccam_x64_slot, ccam_x64_init_slot; Prove offsets, alignment, initialization flag isolation |
| R07.04 — Exact read-before-write traps | C2,7; A4 | ccam_x64_check_initialized; All instruction variants, competing fault cases |
| R07.05 — Arithmetic instruction selection | C4; A4 | ccam_x64_emit_instruction; overflow, remainder tests; Universal machine simulation, not assembly text matching |
| R07.06 — Branch target integrity | A3.6,10 | ccam_x64_instruction_label; loop test; Every relocation/branch resolves to intended instruction boundary |
| R07.07 — ABI preservation | A3.6,10 | ccam_x64_emit_function; six integer argument ceiling; Argument order, return values, callee saves and alignment |
| R07.08 — Dedicated bounded stack | A8,10 | mmap PROT_NONE, guard page, bounded depth; Prove total mapped size including guard and actual stack use |
| R07.09 — Platform failure distinction | A8,10.1 | stack allocation trap label; Separate host failure from machine traps, exact record |
| R07.10 — Exact result transport | C6; A10.1 | legacy exit status; candidate fd3 record; Injective typed outcomes including Bool or explicit canonical mapping |
| R07.11 — Strict bounded result parser | A10.1 | candidate 48-byte header and 1136-byte maximum; Reject malformed, stale, partial, extra records; bind function index/name |
| R07.12 — Bounded result writes | A8,10.1 | candidate bounded short-write/EINTR policy; Explicit attempt budget and launcher timeout for blocked syscall |
| R07.13 — Output byte preservation | A5,8 | output literal emission; NUL/UTF8 and budget tests; Exact trace and partial-write semantics; output independent of result |
| R07.14 — Object and relocation correctness | A3.6,10 | GNU as/ld baseline; Direct encoder/ELF evidence and checked relocation overflow |
| R07.15 — Executable permission integrity | A3.6,10 | GNU-stack note, historical no PT_INTERP checks; Verify W^X, entry mapping, segment ranges, no undefined dependencies |
| R07.16 — Deterministic artifact generation | A12,13,15 | deterministic label helpers; Identical bytes from pinned inputs; toolchain manifest |
| R07.17 — Workspace import confinement | A9,10 | architecture openat2 contract; Audit current driver; adversarial syscall and file identity tests |
| R07.18 — Final executable refinement | A4,11 | no theorem identified in pinned backend docs; Independent checker or proof covering actual bytes, loader and ABI |

## FRONTEND

Source matrix blob: 6e03ceec2ba7a6016a00ed97d376a9fb51c326fb.

| ID and requirement | Architecture clauses | Existing matrix evidence / open obligation |
|---|---|---|
| R01.02 — Bounded source and import graph | A3.1,8 | ast.cap CompileBudget; MAX_SOURCE_BYTES, MAX_TOTAL_SOURCE_BYTES, MAX_IMPORT_FILES; Admission before allocation; all entry points and native loader limits |
| R01.03 — Exact tokenization of untrusted input | A3.1,4 | lexer.cap Lexer, lex_run, lex_hex; Grammar correspondence, malformed byte corpus |
| R01.04 — Literal semantics independent of target | A3.1,4 | lex_string, escape_c representation; ccam_decode_escaped_literal; Canonical byte values independent of C escaping; round-trip and malformed tests |
| R01.05 — Bounded token and interpolation work | A8 | add_tok, shared CompileBudget; Cost bound including nested lexers and intermediate buffers |
| R01.06 — Parser grammar and precedence | A3.1,4 | parse_binary, parse_unary, parse_type; Grammar acceptance equivalence and associativity corpus |
| R01.07 — Parser totality and recovery | A8 | enter, leave, recover_statement, recover_declaration; MAX_NESTING=1000, MAX_SYNTAX_ERRORS=50; Progress measure, physical stack safety, EOF/token invariant |
| R01.08 — AST shape and provenance | A3.1,3.2 | Node constructors, charge_ast_nodes; Closed shape validation, source spans, reject partial trees |
| R01.09 — Binding and scopes | A3.2,9 | checker declare, push_scope, pop_scope; lowerer locals map; Stable binding identity and shadowing policy preserved |
| R01.10 — Type preservation | A3.2,4,11 | checker check_expr, check_type, ast type_eq, assignable; Checked-tree authenticity, soundness and lowering relation |
| R01.11 — Capability authority | A9 | checker contains_grant, policy tables, privileged; Explicit effect/capability judgement and no erasure in lowering |
| R01.12 — Contextual text and taint | A9 | checker html_context, ast is_contextual_text; Native output sinks preserve contextual trust distinctions |
| R01.13 — Mandatory bounded input | A8 | #444 active; shared compile limits not language-wide input syntax; Grammar, checker, runtime and negative conformance |
| R01.14 — Deterministic lowering | A3.2,4 | ccam_lower_checked_program, ccam_lower_emit; Same checked source produces canonical CCAM and evidence |
| R01.15 — Control flow and evaluation order | A4,5 | ccam_lower_short_circuit, loop patching; regression tests; Side effects, trap precedence and nested loop simulation |
| R01.16 — Typed calls and returns | C2.1,5; A4 | ccam_lower_call_expression; recursion, void and Bool tests; Source signature and CCAM frame correspondence |
| R01.17 — Unsupported constructs fail closed | A3.2 | scalar lowerer subset rejection test; Exhaustive node/type dispatch coverage; no silent fallback |
| R01.18 — Production aggregate workload | A7,13 | #481, AST List/Map/optional/string dependencies; Execute actual lexer/parser/checker through managed CCAM |
| R01.19 — Diagnostics separate from executable output | A3.2,4 | Ctx, report_at, parser failed/fatal fields; No artifact on error; deterministic bounded diagnostic output |

## GC

Source matrix blob: fc5fd8b50c1393e45c733230c72d40e7f2975882.

| ID and requirement | Architecture clauses | Existing matrix evidence / open obligation |
|---|---|---|
| GC01 — Complete live roots | G3; A7.3 | Native GC design §3; Compiler liveness theorem including outgoing args and helper temporaries |
| GC02 — Typed root maps | G3; A7.3 | GC-R0 proposal; Closed versioned encoding, bounds and exact slot classification |
| GC03 — Frame publication and unwind | G3; A7.3 | GC-R0 proposal; Publish after initialization, withdraw exactly once on every controlled exit |
| GC04 — Safepoint discipline | G3; A7.3 | GC-R0 proposal; Spill before publication, reload after collection, forbid unsafepointed collection |
| GC05 — Heap identity and generation | G4; A7.1 | Native design §4; abstract heap proofs; Non-recycled identity issuance and exhaustion; concrete stale-handle rejection |
| GC06 — Immutable layouts | G4; A7.1 | Native design §4; Descriptor provenance, checked offsets, pointer-free secret/atomic objects |
| GC07 — Marker completeness | G5; A7.3 | CollectorSemantics.lean HeapMarkerComplete; Complete concrete bounded worklist algorithm; graph oracle |
| GC08 — Sweep safety | G5,9; A7.3 | gcSweep_preserves_reachable; Discharge completeness premise and concrete refinement |
| GC09 — Retained edge integrity | G9; A7.3 | gcSweep_retained_edge_target; Layout-to-graph correspondence and malformed-edge failure |
| GC10 — Slot partition | G9 | Native design §9; historical #309; Concrete exactly-one-owner and free-list equivalence |
| GC11 — Failure-atomic allocation | G6; A8 | Native design §6; legacy cap_gc_meta; Fault injection at every reservation/publication boundary |
| GC12 — Metadata independence | G6; A8 | Separate metadata arena proposal; Bound all metadata, no managed allocation recursion |
| GC13 — Physical memory accounting | G6,7; A8 | Legacy cap_gc_checked_add/mul, cap_gc_account_release; Distinguish payload, reserved, committed, metadata and temporary storage |
| GC14 — Platform page transitions | G7; A10 | Native design §7; Syscall adapter refinement; failure and partial-success semantics |
| GC15 — Secret wipe before reuse | G8; A9 | Legacy cap_gc_wipe; native §8; Native code store preservation, out-of-line metadata and failure quarantine |
| GC16 — Bounded tracing and pause work | G5; A8 | Native §5 bounded worklist; Cost bound on roots, slots, edges, worklist and sweep; explicit host timing assumptions |
| GC17 — Single-thread isolation | G3,9; A14 | Native §3/9; Reject reentry, concurrent mutation and signal-time allocation |
| GC18 — C-free migration | G1,11,12; A13 | Native §1/12; Actual compiler workload, native stress corpus, dependency audit and reproducible artifact |

## BOOTSTRAP

Source matrix blob: 9ee8478ac77ba27e1987d862f2fb97863ce24ca2.

| ID and requirement | Architecture clauses | Existing matrix evidence / open obligation |
|---|---|---|
| BS01 — Freeze source subset | A3.2,13 | Transitive compiler workload inventory and negative syntax cases |
| BS02 — Independent seed | A13 | Source, pinned toolchain, dependency/FFI audit |
| BS03 — Seed admission | A3.3,8,13 | Bounded strict source and canonical CCAM validation |
| BS04 — S1 artifact | A13 | Build seed to native Capstan compiler; manifest and digest |
| BS05 — Native execution | A5,10,13 | Complete scalar outcomes vs reference, no C runtime |
| BS06 — Workload closure | A13 | Actual lexer/parser/checker/lowerer/emitter compiled natively |
| BS07 — S2 rebuild | A13 | S1 compiles identical compiler source, S2 executes corpus |
| BS08 — Reproducibility | A13,15 | Independent clean builds identical under pinned inputs |
| BS09 — Diverse double compilation | A13 | Independent trusted compiler path and documented DDC comparison assumptions |
| BS10 — Production dependency closure | A10,13 | Build and run without seed, C, Python or external assembler/linker for strict target |
| BS11 — Provenance | A12,13 | Source, transitive imports, tools, configuration, binary hashes |
| BS12 — S3 release | A12,13,16 | Signed artifacts, assurance manifests, platform boundary and rollback policy |

## OPTIMISATION

Source matrix blob: fea3284bf9d1cff162481e046197eed82a5a90d4.

| ID and requirement | Architecture clauses | Existing matrix evidence / open obligation |
|---|---|---|
| OPT01 — Canonical CCAM authority | A3.3,3.4 | Derived IR only when justified; closed verifier and roundtrip |
| OPT02 — Pass registry | A6.2 | Version, preconditions, observables, resource policy |
| OPT03 — Arithmetic rewrites | C4; A5,6.1 | Checked overflow/trap equivalence, boundary oracle |
| OPT04 — CFG transformations | A3.4,5,6 | Reachability, effect order and termination relation |
| OPT05 — Bounds elimination | A6.1,6.2 | Independently checked proof of bound at use |
| OPT06 — Memory optimisations | A6.1,7,9 | Alias, lifetime, capability and secret preservation |
| OPT07 — Allocation/spills | A3.6,5 | Nonoverlap, spill scheduling, ABI and executable pressure tests |
| OPT08 — Resource equivalence | A6.2,8 | Preserve semantic charges or formally approved relation |
| OPT09 — Translation validation | A6.2,11 | Fail closed on unknown, timeout, mismatch; no unverified output |
| OPT10 — Artifact binding | A6.2,12 | Canonical bounded trace, exact source/target/pass/binary digests |
| OPT11 — Relational security | A5,9 | Separate attacker model; spills and speculative observables |
| OPT12 — Adversarial evaluation | A6.2,15 | Pass-directed fuzz, mutation tests, benchmarks and independent reviewer |

## Disposition

113 rows mapped. Aggregate profile-specific clauses and frontend language specification must be refined and approved; explicit wire ABI remains proposed. Exact implementation source/test/theorem identities and transitive inventory not independently verified. No tests executed. G0 HOLD.
