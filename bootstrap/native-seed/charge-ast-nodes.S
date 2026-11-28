/* Candidate native traversal primitive for a validated node table.
 *
 * SysV arguments:
 *   RDI: writable budget { i64 ast_nodes; i64 exhausted }
 *   RSI: node table of { child_ids pointer; i64 child_count }
 *   RDX: number of node entries
 *   RCX: root ID array
 *   R8:  number of root IDs
 *   R9:  writable scratch array of 150000 node IDs
 *
 * Pointers and extents are supplied by the runtime, with scratch disjoint
 * from all other inputs. IDs and logical lengths are checked below.
 * Returns 1 on completion, 0 on node-budget exhaustion, and -1 on
 * invalid metadata or scratch capacity exhaustion. Visits before failure
 * remain charged, as with the source worklist. No recursion or heap calls.
 */
.equ AST_NODE_LIMIT, 150000
.section .text
.global seed_charge_ast_nodes
.type seed_charge_ast_nodes,@function
seed_charge_ast_nodes:
    cmpq $AST_NODE_LIMIT, (%rdi)
    ja charge_invalid
    cmp $AST_NODE_LIMIT, %rdx
    ja charge_invalid
    cmp $AST_NODE_LIMIT, %r8
    ja charge_invalid
    xor %r10d, %r10d
charge_roots:
    cmp %r8, %r10
    je charge_next
    mov (%rcx,%r10,8), %rax
    cmp %rdx, %rax
    jae charge_invalid
    mov %rax, (%r9,%r10,8)
    inc %r10
    jmp charge_roots
charge_next:
    test %r10, %r10
    jz charge_complete
    dec %r10
    mov (%r9,%r10,8), %rax
    cmpq $AST_NODE_LIMIT, (%rdi)
    je charge_exhausted
    incq (%rdi)
    shl $4, %rax
    mov (%rsi,%rax), %rcx         /* child array */
    mov 8(%rsi,%rax), %r8         /* child count */
    mov $AST_NODE_LIMIT, %eax
    sub %r10, %rax
    cmp %rax, %r8
    ja charge_invalid
    xor %r11d, %r11d
charge_children:
    cmp %r8, %r11
    je charge_next
    mov (%rcx,%r11,8), %rax
    cmp %rdx, %rax
    jae charge_invalid
    mov %rax, (%r9,%r10,8)
    inc %r10
    inc %r11
    jmp charge_children
charge_exhausted:
    movq $1, 8(%rdi)
    xor %eax, %eax
    ret
charge_complete:
    mov $1, %eax
    ret
charge_invalid:
    mov $-1, %rax
    ret
.size seed_charge_ast_nodes, .-seed_charge_ast_nodes
.section .note.GNU-stack,"",@progbits
