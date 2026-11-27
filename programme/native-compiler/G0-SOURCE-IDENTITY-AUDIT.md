# G0 source identity audit

Exact inspected commit: 7be0a4a6ee02b9eb76bb06a5505cb6d9b277e6b6. This is a static textual-reference audit, not declaration authenticity, execution or proof correspondence. First occurrence line can be a use/comment rather than definition. Missing names require reconciliation, not an inference of absent implementation.

| Path | Git blob | Referenced names and first matching lines |
|---|---|---|
| verification/ccam_core.cap | 5ce0daf5cdfebd886aaaf8a097ec53a48775e6c8 | ccam_validate_single_frame: L1399; ccam_add: L16; ccam_sub: L26; ccam_mul: L36; ccam_div: L61; ccam_rem: L71; ccam_register_read_int: L208; ccam_register_read_bool: L222; ccam_register_write_int: L236; ccam_register_write_bool: L249 |
| verification/ccam_calls.cap | 0f6d64132415186398f09f43f305b743f8d3a2df | File identity only |
| verification/ccam_heap.cap | d72d00ba2ffdffc74f79d5a4b381c2f1187c6c77 | ccam_heap_object_index: L180; ccam_heap_value_has_type: L174; ccam_heap_create_bounded: L130 |
| verification/ccam_aggregate_machine.cap | c359b6efad1a0b7fb702139875b9093d2a13a26f | ccam_aggregate_write: L159; ccam_aggregate_read: L134; ccam_aggregate_begin_step: L112; ccam_aggregate_alloc_record: L194 |
| verification/ccam_native_x64.cap | e3eee998b9c82c9c28810bf9e672d8589f880c1f | ccam_x64_emit_linux_elf: L365; ccam_x64_slot: L19; ccam_x64_init_slot: L23; ccam_x64_check_initialized: L27; ccam_x64_emit_instruction: L110; ccam_x64_instruction_label: L48; ccam_x64_emit_function: L327 |
| verification/ccam_lowering.cap | db91956debb38de7acb2766ebf25e7f589fcd7e0 | ccam_lower_checked_program: L791; ccam_lower_emit: L209; ccam_lower_short_circuit: L430; ccam_lower_call_expression: L355 |
| compiler/lexer.cap | 6bc9bf8c12b4b9bcf8928b45d302f8e8453a02eb | lex_run: L239; lex_hex: L268; lex_string: L116; add_tok: L89 |
| compiler/parser.cap | b656da773f2aa118b0fd2eeeb537a8a4614cad1e | parse_binary: L248; parse_unary: L252; parse_type: L168; recover_statement: L85; recover_declaration: L112 |
| compiler/ast.cap | 596dac3f21d25b404ae2c3e900b09da611488542 | CompileBudget: L19; MAX_SOURCE_BYTES: L11; MAX_TOTAL_SOURCE_BYTES: L13; MAX_IMPORT_FILES: L12; charge_ast_nodes: L117; type_eq: L282; assignable: L312; is_contextual_text: L327 |
| compiler/checker.cap | 3a7b109196e350397238b9e6aa723345566e5365 | declare: L89; push_scope: L43; pop_scope: L57; check_expr: L347; check_type: L138; contains_grant: L168; html_context: L589 |
| formal/CCAMHeap.lean | 31d55db2d98708d2eb5174453abd28b5256237fa | rejected_allocation_preserves_state: L94; allocation_success_facts: L124; allocate_success_preserves_heapInvariant: L187; allocation_charges_exactly: L210; allocation_preserves_work_bound: L266; stale_handle_rejected_after_recycle: L323; cross_region_handle_rejected: L350; revoked_capability_invalid: L426 |
| verification/lean/CapstanVerification/CollectorSemantics.lean | e2ca2eaff29a379e09e10941d9abd877e7fb2c7a | HeapMarkerComplete: L36; gcSweep_preserves_reachable: L49; gcSweep_retained_edge_target: L115; gcSweep_preserves_roots: L60; gcSweep_then_allocate_preserves_reachable: L135 |
| runtime/capstan_gc.h | dee014e7a47c82d9a3ad9e163ade35f03b4e0ca1 | cap_gc_meta: L165; cap_gc_checked_add: L79; cap_gc_checked_mul: L85; cap_gc_account_release: L446; cap_gc_wipe: L183 |
| tests/run.sh | d361d71290db59c55f575d2d00545ebc999bd792 | File identity only |

## Result

14 files retrieved, 70 textual name matches, 0 unmatched. Exact semantic declarations, tests, transitive imports, new direct ELF artifacts and formal refinement remain open. G0 HOLD.
