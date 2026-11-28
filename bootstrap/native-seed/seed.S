/* Linux x86-64 independent bootstrap candidate.
 * Input on fd 0: int main() { return <signed decimal> { (+|-) <signed decimal> }; }
 * Output on fd 1: a freestanding ELF that writes the i64 result to fd 3.
 */
.equ SEED_INPUT_LIMIT, 1048576

.global _start
.section .text
_start:
    xor %r12d, %r12d
    lea input(%rip), %rsi
read_input:
    xor %eax, %eax
    xor %edi, %edi
    lea (%rsi,%r12), %rsi
    mov $(SEED_INPUT_LIMIT + 1), %edx
    sub %r12d, %edx
    syscall
    lea input(%rip), %rsi
    test %rax, %rax
    js transport_failed
    jz parse
    add %rax, %r12
    cmp $SEED_INPUT_LIMIT, %r12
    ja input_limit
    jmp read_input

parse:
    lea (%rsi,%r12), %r13
    call parse_constants
    cmp %r13, %rsi
    jae invalid
    cmpb $115, (%rsi)                /* struct */
    je parse_records
    push %rsi
    lea int_prefix(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $95, (%rsi)
    je scalar_helper
    pop %rsi
    jmp parse_main

/* Consume consecutive constant declarations and leave the next token ready. */
parse_constants:
    call skip_trivia
    cmp %r13, %rsi
    jae constants_done
    cmpb $99, (%rsi)                 /* const */
    jne constants_done
    lea const_prefix(%rip), %r14
    call match_prefix
    call parse_identifier
    call find_constant
    test %rax, %rax
    jnz invalid
    mov constant_count(%rip), %rax
    cmp $256, %rax
    jae invalid
    push %rdi
    push %rdx
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $61, (%rsi)
    jne invalid
    inc %rsi
    call skip_trivia
    call parse_literal
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $59, (%rsi)
    jne invalid
    inc %rsi
    pop %rdx
    pop %rdi
    mov constant_count(%rip), %rax
    lea (%rax,%rax,2), %rcx
    lea constants(%rip), %rax
    mov %rdi, (%rax,%rcx,8)
    mov %rdx, 8(%rax,%rcx,8)
    mov %r9, 16(%rax,%rcx,8)
    incq constant_count(%rip)
    jmp parse_constants
constants_done:
    ret
/* One integer helper with up to sixteen integer arguments. */
scalar_helper:
    pop %rax                      /* release the declaration lookahead */
    call parse_record_identifier
    cmp $2, %rdx
    jb invalid
    mov %rdi, helper_name(%rip)
    mov %rdx, helper_name+8(%rip)
    lea scalar_call_open(%rip), %r14
    call match_prefix
scalar_parameter:
    cmpq $16, scalar_local_count(%rip)
    jae invalid
    lea int_prefix(%rip), %r14
    call match_prefix
    call parse_record_identifier
    cmpb $95, (%rdi)
    jne invalid
    cmp $2, %rdx
    jb invalid
    call find_constant
    test %rax, %rax
    jnz invalid
    call find_scalar_local
    test %rax, %rax
    jnz invalid
    mov scalar_local_count(%rip), %rax
    lea (%rax,%rax,2), %rcx
    lea scalar_locals(%rip), %r11
    mov %rdi, (%r11,%rcx,8)
    mov %rdx, 8(%r11,%rcx,8)
    inc %eax
    mov %eax, 16(%r11,%rcx,8)
    mov %rax, scalar_local_count(%rip)
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $44, (%rsi)
    jne scalar_helper_body
    inc %rsi
    call skip_trivia
    jmp scalar_parameter
scalar_helper_body:
    lea scalar_body_open(%rip), %r14
    call match_prefix
    lea result_code(%rip), %rbx
    movb $0xe9, (%rbx)             /* process entry skips the helper */
    add $5, %rbx
    mov scalar_local_count(%rip), %rcx
    mov %rcx, scalar_helper_arity(%rip)
    mov $16, %eax
    sub %ecx, %eax
    shl $3, %eax
    movl $0x00ec8148, (%rbx)       /* reserve non-parameter slots */
    mov %eax, 3(%rbx)
    add $7, %rbx
    /* The incoming return address lies above the reserved locals. Copy the
       stacked arguments from last to first. Each push moves the next source
       and RSP down by eight, so the displacement stays (16 - 6) * 8. */
scalar_copy_stack_parameter:
    cmp $6, %ecx
    jbe scalar_spill_registers
    movl $0x502474ff, (%rbx)       /* push qword [rsp+80] */
    add $4, %rbx
    dec %ecx
    jmp scalar_copy_stack_parameter
scalar_spill_registers:
    lea argument_push(%rip), %rax
scalar_spill_argument:
    dec %rcx
    movzwl (%rax,%rcx,2), %edx
    mov %dx, (%rbx)
    add $2, %rbx
    test %rcx, %rcx
    jnz scalar_spill_argument
    xor %r12d, %r12d
    movb $1, scalar_helper_active(%rip)
    jmp local_body_dispatch
finish_scalar_helper:
    movb $0, scalar_helper_active(%rip)
    movl $0x00c48148, (%rbx)       /* add rsp,128 */
    movl $128, 3(%rbx)
    movb $0xc3, 7(%rbx)            /* ret */
    add $8, %rbx
    lea result_code+5(%rip), %rax
    mov %rbx, %rcx
    sub %rax, %rcx
    mov %ecx, -4(%rax)
    lea record_main_prefix(%rip), %r14
    call match_prefix
    lea return_prefix(%rip), %r14
    call match_prefix
    call parse_record_identifier
    lea helper_name(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid
    lea scalar_call_open(%rip), %r14
    call match_prefix
    pushq scalar_helper_arity(%rip) /* preserve arity, hide helper locals */
    movq $0, scalar_local_count(%rip)
    mov (%rsp), %rax
    cmp $6, %eax
    jbe scalar_argument
    test $1, %al
    jz scalar_argument
    movl $0x08ec8348, (%rbx)       /* alignment pad above all arguments */
    add $4, %rbx
scalar_argument:
    push %rax
    call emit_expression
    movb $0x50, (%rbx)             /* push rax: preserve earlier arguments */
    inc %rbx
    pop %rax
    dec %rax
    jz scalar_call_finish
    push %rax
    lea comma(%rip), %r14
    call match_prefix
    pop %rax
    jmp scalar_argument
scalar_call_finish:
    lea close_paren(%rip), %r14
    call match_prefix
    pop %rcx
    cmp $6, %ecx
    jbe scalar_call_registers
    /* Arguments were evaluated left-to-right and pushed in reverse stack
       order. Reverse the slots, then pop the six register arguments. */
    xor %eax, %eax
    lea -8(,%rcx,8), %edx
scalar_reverse_slots:
    cmp %edx, %eax
    jae scalar_pop_registers_forward
    movl $0x24448b48, (%rbx)       /* mov rax,[rsp+lo] */
    mov %al, 4(%rbx)
    movl $0x24448748, 5(%rbx)      /* xchg rax,[rsp+hi] */
    mov %dl, 9(%rbx)
    movl $0x24448948, 10(%rbx)     /* mov [rsp+lo],rax */
    mov %al, 14(%rbx)
    add $15, %rbx
    add $8, %eax
    sub $8, %edx
    jmp scalar_reverse_slots
scalar_pop_registers_forward:
    lea argument_pop(%rip), %rax
    mov $6, %ecx
scalar_pop_next_register:
    movzwl (%rax), %edx
    mov %dx, (%rbx)
    add $2, %rax
    add $2, %rbx
    dec %ecx
    jnz scalar_pop_next_register
    jmp scalar_emit_call
scalar_call_registers:
    lea argument_pop(%rip), %rax
scalar_restore_argument:
    dec %rcx
    movzwl (%rax,%rcx,2), %edx
    mov %dx, (%rbx)
    add $2, %rbx
    test %rcx, %rcx
    jnz scalar_restore_argument
scalar_emit_call:
    movb $0xe8, (%rbx)             /* call helper */
    add $5, %rbx
    lea result_code+5(%rip), %rax
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    mov scalar_helper_arity(%rip), %eax
    cmp $6, %eax
    jbe finish_main
    sub $5, %eax                   /* round stacked slot count up to even */
    and $-2, %eax
    shl $3, %eax
    movl $0x00c48348, (%rbx)       /* add rsp,stacked bytes + alignment pad */
    mov %al, 3(%rbx)
    add $4, %rbx
    jmp finish_main

parse_main:
    lea main_prefix(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $105, (%rsi)              /* int or if */
    jne scalar_return
    lea 3(%rsi), %rax
    cmp %r13, %rax
    ja invalid
    cmpw $0x6e69, (%rsi)
    jne scalar_if
    cmpb $116, 2(%rsi)
    je parse_local
    jmp scalar_if
scalar_return:
    lea return_prefix(%rip), %r14
    call match_prefix
    jmp parse_expression

scalar_if:
    lea result_code(%rip), %rbx
    xor %r12d, %r12d
    jmp parse_if

/* Reserve sixteen stack slots for the bounded scalar-local profile. */
parse_local:
    lea result_code(%rip), %rbx
    movl $0x00ec8148, (%rbx)      /* sub rsp,128 */
    movl $128, 3(%rbx)
    add $7, %rbx
    xor %r12d, %r12d
local_declaration:
    cmpq $16, scalar_local_count(%rip)
    jae invalid
    lea int_prefix(%rip), %r14
    call match_prefix
    call parse_record_identifier
    cmpb $95, (%rdi)
    jne invalid
    cmp $2, %rdx
    jb invalid
    call find_constant
    test %rax, %rax
    jnz invalid
    call find_scalar_local
    test %rax, %rax
    jnz invalid
    push %rdi
    push %rdx
    lea local_equals(%rip), %r14
    call match_prefix
    call emit_expression
    pop %rdx
    pop %rdi
    mov scalar_local_count(%rip), %rax
    lea (%rax,%rax,2), %rcx
    lea scalar_locals(%rip), %r11
    mov %rdi, (%r11,%rcx,8)
    mov %rdx, 8(%r11,%rcx,8)
    inc %eax
    mov %eax, 16(%r11,%rcx,8)    /* one-based slot ID */
    mov %rax, scalar_local_count(%rip)
    call emit_store_local
local_body_dispatch:
    cmp %r13, %rsi
    jae invalid
    cmpb $105, (%rsi)             /* another int declaration or if */
    jne local_start_statements
    lea 3(%rsi), %rax
    cmp %r13, %rax
    ja invalid
    cmpw $0x6e69, (%rsi)
    jne local_start_statements
    cmpb $116, 2(%rsi)
    je local_declaration
local_start_statements:
    mov $32, %r15d
local_statement:
    cmp %r13, %rsi
    jae invalid
    cmpb $95, (%rsi)
    jne local_control
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    call emit_assignment
    pop %r15
    jmp local_statement
local_control:
    cmpb $119, (%rsi)             /* while */
    je local_while
    jmp local_after_loop
local_return:
    lea return_prefix(%rip), %r14
    call match_prefix
    call emit_expression
    jmp finish_main

find_scalar_local:
    lea scalar_locals(%rip), %rax
    mov scalar_local_count(%rip), %r10
    jmp find_name

match_scalar_local:
    call parse_record_identifier
    call find_scalar_local
    test %rax, %rax
    jz invalid
    mov 16(%rax), %eax
    ret

emit_assignment:
    call match_scalar_local
    push %rax
    lea local_equals(%rip), %r14
    call match_prefix
    call emit_expression
    pop %rax
    jmp emit_store_local

local_while:
    lea while_open(%rip), %r14
    call match_prefix
    call match_scalar_local
    push %rax
    lea while_less(%rip), %r14
    call match_prefix
    call parse_expression_operand
    push %rax
    lea while_body(%rip), %r14
    call match_prefix
    pop %rax
    movw $0xb841, (%rbx)          /* mov r8d,1000000 */
    movl $1000000, 2(%rbx)
    add $6, %rbx
    pop %rdx                      /* comparison's left slot */
    push %rbx                     /* back edge reloads the bound */
    push %rdx
    test %eax, %eax
    jnz while_local_bound
    movw $0xb948, (%rbx)          /* movabs rcx,upper bound */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp while_compare
while_local_bound:
    mov $0x248c8b48, %edx         /* mov rcx,[rsp+disp32] */
    call emit_local_slot
while_compare:
    pop %rax
    movl $0x248c3948, (%rbx)      /* cmp [rsp+disp32],rcx */
    lea -8(,%rax,8), %eax
    mov %eax, 4(%rbx)
    movw $0x8d0f, 8(%rbx)        /* jge past the loop */
    add $14, %rbx
    push %rbx
    movw $0x8545, (%rbx)          /* test r8d,r8d */
    movb $0xc0, 2(%rbx)
    movw $0x840f, 3(%rbx)        /* je iteration_limit_stub */
    lea iteration_limit_stub(%rip), %rax
    add $9, %rbx
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    movw $0xff41, (%rbx)          /* dec r8d */
    movb $0xc8, 2(%rbx)
    add $3, %rbx
    mov $32, %r15d
while_assignment:
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    call emit_assignment
    pop %r15
    cmp %r13, %rsi
    jae invalid
    cmpb $125, (%rsi)
    jne while_assignment
    lea while_close(%rip), %r14
    call match_prefix
    movb $0xe9, (%rbx)            /* jump back to condition */
    add $5, %rbx
    pop %rcx
    pop %rax
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    mov %rbx, %rax
    sub %rcx, %rax
    mov %eax, -4(%rcx)
    jmp local_after_loop
local_after_loop:
    cmp %r13, %rsi
    jae invalid
    cmpb $105, (%rsi)             /* if */
    je parse_if
    jmp local_return

emit_store_local:
    mov $0x24848948, %edx        /* mov [rsp+disp32],rax */
    call emit_local_slot
    lea local_separator(%rip), %r14
    jmp match_prefix

/* EAX is a one-based slot ID. EDX holds opcode, ModRM and SIB bytes. */
emit_local_slot:
    mov %edx, (%rbx)
    lea -8(,%rax,8), %eax
    mov %eax, 4(%rbx)
    add $8, %rbx
    ret

/* Operands can read the initialized integer local or use an immediate. */
parse_if:
    lea if_open(%rip), %r14
    call match_prefix
    call parse_expression_operand
    test %eax, %eax
    jnz if_load_left_local
    movw $0xb948, (%rbx)           /* movabs rcx,left */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp if_operator
if_load_left_local:
    mov $0x248c8b48, %edx         /* mov rcx,[rsp+disp32] */
    call emit_local_slot
if_operator:
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    movzbl (%rsi), %edx
    inc %rsi
    cmp %r13, %rsi
    jae invalid
    cmpb $61, (%rsi)
    je if_two_character_operator
    mov $0x8d, %eax                /* signed jge skips < */
    cmp $60, %edx
    je if_parse_right
    mov $0x8e, %eax                /* signed jle skips > */
    cmp $62, %edx
    jne invalid
    jmp if_parse_right
if_two_character_operator:
    inc %rsi
    mov $0x85, %eax                /* jne skips == */
    cmp $61, %edx
    je if_parse_right
    mov $0x84, %eax                /* je skips != */
    cmp $33, %edx
    je if_parse_right
    mov $0x8f, %eax                /* signed jg skips <= */
    cmp $60, %edx
    je if_parse_right
    mov $0x8c, %eax                /* signed jl skips >= */
    cmp $62, %edx
    jne invalid
if_parse_right:
    push %rax
    call skip_trivia
    call parse_expression_operand
    test %eax, %eax
    jnz if_load_right_local
    movw $0xba48, (%rbx)           /* movabs rdx,right */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp if_compare
if_load_right_local:
    mov $0x24948b48, %edx         /* mov rdx,[rsp+disp32] */
    call emit_local_slot
if_compare:
    lea if_true_prefix(%rip), %r14
    call match_prefix
    pop %rax
    movw $0x3948, (%rbx)          /* cmp rcx,rdx */
    movb $0xd1, 2(%rbx)
    movb $0x0f, 3(%rbx)
    mov %al, 4(%rbx)              /* near Jcc to fallback expression */
    add $9, %rbx
    push %rbx
    call emit_expression
    lea if_false_prefix(%rip), %r14
    call match_prefix
    movb $0xe9, (%rbx)            /* skip fallback on successful true return */
    add $5, %rbx
    pop %rax
    mov %rbx, %rcx
    sub %rax, %rcx
    mov %ecx, -4(%rax)
    push %rbx
    call emit_expression
    pop %rax
    mov %rbx, %rcx
    sub %rax, %rcx
    mov %ecx, -4(%rax)
    jmp finish_main

/* Layout declarations share a bounded name table. An entry selects one
 * layout for construction, directly or through one zero-argument helper. */
parse_records:
    call parse_layouts
    jmp record_main

parse_layouts:
    call parse_constants
    cmp %r13, %rsi
    jae layouts_done
    cmpb $115, (%rsi)
    jne layouts_done
    call parse_record
    jmp parse_layouts
layouts_done:
    ret

parse_record:
    lea struct_prefix(%rip), %r14
    call match_prefix
    call parse_record_identifier
    lea text_list_elements(%rip), %rax
    mov $2, %r10d
    call find_name
    test %rax, %rax
    jnz invalid
    lea layouts(%rip), %rax
    mov layout_count(%rip), %r10
    call find_name
    test %rax, %rax
    jnz invalid
    mov layout_count(%rip), %rax
    cmp $32, %rax
    jae invalid
    lea (%rax,%rax,2), %rcx
    lea layouts(%rip), %r11
    mov %rdi, (%r11,%rcx,8)
    mov %rdx, 8(%r11,%rcx,8)
    imul $768, %rax, %rax          /* 32 field entries of 24 bytes */
    lea record_fields(%rip), %rdx
    add %rdx, %rax
    mov %rax, record_fields_base(%rip)
    movq $0, record_count(%rip)
    lea open_brace(%rip), %r14
    call match_prefix
record_field:
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $125, (%rsi)
    je finish_layout
    mov $1, %ebp
    lea int_prefix(%rip), %r14
    cmpb $115, (%rsi)
    je record_string_type
    cmpb $76, (%rsi)
    je record_list_type
    cmpb $98, (%rsi)
    jne record_int_or_optional
    mov $2, %ebp
    lea bool_prefix(%rip), %r14
    jmp record_field_type
record_int_or_optional:
    cmpb $105, (%rsi)
    je record_field_type
    call parse_record_identifier
    lea layouts(%rip), %rax
    mov layout_count(%rip), %r10
    call find_name
    test %rax, %rax
    jz invalid
    mov $5, %ebp
    lea optional_type_suffix(%rip), %r14
    jmp record_field_type
record_string_type:
    mov $3, %ebp
    lea string_prefix(%rip), %r14
    jmp record_field_type
record_list_type:
    mov $4, %ebp
    lea list_type_open(%rip), %r14
    call match_prefix
    call parse_record_identifier
    cmp $3, %rdx
    jne record_named_list_type
    cmpw $0x6e69, (%rdi)
    jne record_named_list_type
    cmpb $116, 2(%rdi)
    jne record_named_list_type
    mov $6, %ebp
    jmp record_list_type_close
record_named_list_type:
    /* Include the current layout so a recursive worklist keeps kind 4. */
    mov layout_count(%rip), %r10
    inc %r10
    call resolve_list_element
    lea layouts(%rip), %rcx
    imul $24, layout_count(%rip), %rdx
    add %rdx, %rcx
    cmp %rcx, %rax
    je record_list_type_close
    mov %rax, %rbp                /* exact element identity for empty lists */
record_list_type_close:
    lea list_type_close(%rip), %r14
record_field_type:
    call match_prefix
    call parse_record_identifier
    mov record_fields_base(%rip), %rax
    mov record_count(%rip), %r10
    call find_name
    test %rax, %rax
    jnz invalid
    mov record_count(%rip), %rax
    cmp $32, %rax
    jae invalid
    lea (%rax,%rax,2), %rcx
    mov record_fields_base(%rip), %rax
    mov %rdi, (%rax,%rcx,8)
    mov %rdx, 8(%rax,%rcx,8)
    mov %rbp, 16(%rax,%rcx,8)
    incq record_count(%rip)
    lea semicolon(%rip), %r14
    call match_prefix
    jmp record_field

finish_layout:
    mov record_count(%rip), %rdx
    test %rdx, %rdx
    jz invalid
    mov layout_count(%rip), %rax
    lea (%rax,%rax,2), %rcx
    lea layouts(%rip), %rax
    mov %rdx, 16(%rax,%rcx,8)
    incq layout_count(%rip)
    inc %rsi
    ret

record_main:
    lea result_code(%rip), %rbx
    cmp %r13, %rsi
    jae invalid
    cmpb $98, (%rsi)             /* bool */
    je record_bool_helper
    lea 3(%rsi), %rax
    cmp %r13, %rax
    ja invalid
    cmpw $0x6e69, (%rsi)
    jne record_helper
    cmpb $116, 2(%rsi)
    jne record_helper
    cmp %r13, %rax
    jae invalid
    movzbl (%rax), %eax
    mov $1, %r8d
    call identifier_start
    jc record_helper
    sub $48, %eax
    cmp $9, %eax
    ja record_entry
record_helper:
    movb $1, emitting_constructor(%rip)
    call select_record_layout
    mov selected_record_layout(%rip), %rax
    mov %rax, constructor_layout(%rip)
    lea required_trivia(%rip), %r14
    call match_prefix
    call parse_record_identifier
    mov %rdi, helper_name(%rip)
    mov %rdx, helper_name+8(%rip)
    lea helper_prefix(%rip), %r14
    call match_prefix
    call match_record_name
    movb $0xe9, (%rbx)             /* jmp over helper from process entry */
    add $5, %rbx
    jmp record_open_initializer
record_entry:
    push %rsi
    lea int_prefix(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $95, (%rsi)
    je record_read_helper
    pop %rsi
    jmp record_entry_body

record_bool_helper:
    lea bool_prefix(%rip), %r14
    call match_prefix
    movb $1, record_reader_bool(%rip)
    jmp parse_record_reader_name
record_read_helper:
    pop %rax                      /* release declaration lookahead */
parse_record_reader_name:
    call parse_record_identifier
    cmp $2, %rdx
    jb invalid
    lea helper_name(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jnz invalid
    mov %rdi, record_reader_name(%rip)
    mov %rdx, record_reader_name+8(%rip)
    lea scalar_call_open(%rip), %r14
    call match_prefix
    call select_record_layout
    lea required_trivia(%rip), %r14
    call match_prefix
    call parse_record_identifier
    mov %rdi, record_parameter(%rip)
    mov %rdx, record_parameter+8(%rip)
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $44, (%rsi)
    jne record_reader_parameters_done
    lea comma(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $76, (%rsi)
    je record_reader_roots_parameter
    call match_record_name
    lea record_reader_peer_parameter(%rip), %r14
    call match_prefix
    movb $1, record_reader_has_peer(%rip)
    jmp record_reader_parameters_done
record_reader_roots_parameter:
    lea list_type_open(%rip), %r14
    call match_prefix
    call lookup_record_layout
    mov %rax, record_root_layout(%rip)
    cmp selected_record_layout(%rip), %rax
    je record_roots_type_ready
    movb $1, record_distinct_root_layout(%rip)
record_roots_type_ready:
    lea roots_parameter_suffix(%rip), %r14
    call match_prefix
    movb $1, record_reader_has_roots(%rip)
record_reader_parameters_done:
    lea scalar_body_open(%rip), %r14
    call match_prefix
    cmpq $0, constructor_layout(%rip)
    jne record_reader_start
    movb $0xe9, (%rbx)             /* process entry skips helper */
    add $5, %rbx
record_reader_start:
    mov %rbx, reader_entry(%rip)
    mov $32, %r15d
record_reader_statement:
    call record_check_emit_room
    cmp %r13, %rsi
    jae invalid
    cmpb $76, (%rsi)             /* List<Node> pending */
    je record_declare_worklist
    cmpb $112, (%rsi)            /* pending */
    je record_worklist_statement
    cmpb $102, (%rsi)            /* for */
    je record_reader_children
    cmpb $119, (%rsi)             /* while */
    je record_reader_loop
    cmpb $125, (%rsi)
    je record_reader_loop_end
    cmpb $114, (%rsi)             /* return */
    je record_reader_return
    cmpb $105, (%rsi)            /* if */
    jne record_statement_name
    lea 2(%rsi), %rax
    cmp %r13, %rax
    ja invalid
    cmpb $102, 1(%rsi)
    je record_reader_if
record_statement_name:
    push %rsi
    call parse_record_identifier
    lea record_parameter(%rip), %rax
    mov $1, %r10d
    call find_name
    pop %rsi
    test %rax, %rax
    jz record_bind_last_node
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    call resolve_parameter_field
    cmp $6, %r12
    je record_reader_push
    cmp $4, %r12
    je record_reader_push_self
    cmp $1, %r12
    jne invalid
    push %rcx
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    xor %ebp, %ebp
    cmpb $43, (%rsi)
    jne record_reader_assignment_value
    inc %rsi
    cmp %r13, %rsi
    jae invalid
    cmpb $61, (%rsi)
    jne invalid
    mov $1, %ebp
record_reader_assignment_value:
    lea local_equals(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $110, (%rsi)             /* node */
    je record_reader_node_value
    call parse_operand
    movw $0xb848, (%rbx)           /* movabs rax,value */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp record_reader_update_value
record_reader_node_value:
    cmpb $0, record_node_bound(%rip)
    je invalid
    lea node_field_prefix(%rip), %r14
    call match_prefix
    push %rbp
    call resolve_node_field
    pop %rbp
    cmp $1, %r12
    jne invalid
    movw $0x8b49, (%rbx)         /* mov rax,[r9+disp32] */
    movb $0x81, 2(%rbx)
    mov %ecx, 3(%rbx)
    add $7, %rbx
record_reader_update_value:
    pop %rcx
    test %ebp, %ebp
    jz record_reader_store
    movw $0x0348, (%rbx)          /* add rax,[rdi+disp32] */
    movb $0x87, 2(%rbx)
    mov %ecx, 3(%rbx)
    movw $0x800f, 7(%rbx)        /* jo overflow before publishing */
    lea overflow_stub(%rip), %rax
    add $13, %rbx
    sub %rbx, %rax
    mov %eax, -4(%rbx)
record_reader_store:
    movw $0x8948, (%rbx)          /* mov [rdi+disp32],rax */
    movb $0x87, 2(%rbx)
    mov %ecx, 3(%rbx)
    add $7, %rbx
    jmp record_reader_statement_end
record_reader_push:
    push %rcx
    lea list_push_suffix(%rip), %r14
    call match_prefix
    call parse_operand
    lea close_paren(%rip), %r14
    call match_prefix
    pop %rcx
    movw $0xb848, (%rbx)         /* movabs rax,value */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp record_reader_append
record_reader_push_self:
    push %rcx
    lea method_dot(%rip), %r14
    call match_prefix
    lea 2(%rsi), %rax
    cmp %r13, %rax
    ja invalid
    cmpw $0x6f70, (%rsi)          /* po: pop() */
    je record_reader_discard_pop
    movb $0, record_push_node_source(%rip)
    lea list_push_open(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $112, (%rsi)
    je record_reader_push_peer
    cmpb $110, (%rsi)
    je record_reader_push_from_node
    cmpb $0, record_distinct_root_layout(%rip)
    jne invalid
    call match_record_parameter
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $46, (%rsi)
    je record_reader_push_from_list
    lea close_paren(%rip), %r14
    call match_prefix
    pop %rcx
    movw $0x8948, (%rbx)         /* mov rax,rdi: reference to caller record */
    movb $0xf8, 2(%rbx)
    add $3, %rbx
    jmp record_reader_append
record_reader_discard_pop:
    lea list_pop_call(%rip), %r14
    call match_prefix
    pop %rcx
    call emit_record_list_pop
    mov %rbx, %rax
    sub %r11, %rax
    mov %eax, -4(%r11)
    jmp record_reader_statement_end
record_reader_push_peer:
    cmpb $0, record_reader_has_peer(%rip)
    je invalid
    lea peer_argument(%rip), %r14
    call match_prefix
    pop %rcx
    movw $0x8948, (%rbx)         /* mov rax,rsi: second caller-owned record */
    movb $0xf0, 2(%rbx)
    add $3, %rbx
    jmp record_reader_append
record_reader_push_from_node:
    cmpb $0, record_node_bound(%rip)
    je invalid
    cmpb $0, record_distinct_root_layout(%rip)
    je record_node_source_ok
    mov record_count(%rip), %rax
    shl $3, %eax
    cmp %rax, (%rsp)
    jne invalid
record_node_source_ok:
    movb $1, record_push_node_source(%rip)
    lea node_token(%rip), %r14
    call match_prefix
record_reader_push_from_list:
    lea method_dot(%rip), %r14
    call match_prefix
    cmpb $0, record_push_node_source(%rip)
    je record_push_item_field
    call resolve_node_field
    jmp record_push_source_field
record_push_item_field:
    call resolve_record_field
record_push_source_field:
    cmp $4, %r12
    jne invalid
    push %rcx
    lea list_index_open(%rip), %r14
    call match_prefix
    call parse_operand
    lea list_index_close(%rip), %r14
    call match_prefix
    lea close_paren(%rip), %r14
    call match_prefix
    pop %rcx
    movw $0x8b48, (%rbx)          /* mov rax,[rdi+disp32]: item list */
    movb $0x87, 2(%rbx)
    cmpb $0, record_push_node_source(%rip)
    je record_reader_emit_list_offset
    movw $0x8b49, (%rbx)          /* mov rax,[r9+disp32]: saved node list */
    movb $0x81, 2(%rbx)
record_reader_emit_list_offset:
    mov %ecx, 3(%rbx)
    add $7, %rbx
    call emit_indexed_list_load
    pop %rcx
record_reader_append:
    call emit_record_list_append
    jmp record_reader_statement_end

/* Target RAX holds the element. ECX identifies the destination field. */
emit_record_list_append:
    movw $0x8b48, (%rbx)         /* mov rcx,[rdi+disp32] */
    movb $0x8f, 2(%rbx)
    mov %ecx, 3(%rbx)
    movl $0x48118b48, 7(%rbx)    /* mov rdx,[rcx] */
    movw $0xfa83, 11(%rbx)       /* cmp rdx,16 */
    movb $16, 13(%rbx)
    add $14, %rbx
    mov $0x83, %al               /* jae bounds */
    call emit_bounds_branch
    movl $0xd1448948, (%rbx)     /* mov [rcx+rdx*8+8],rax */
    movb $8, 4(%rbx)
    movl $0x48c2ff48, 5(%rbx)    /* inc rdx */
    movw $0x1189, 9(%rbx)        /* mov [rcx],rdx */
    add $11, %rbx
    ret
record_reader_statement_end:
    lea local_separator(%rip), %r14
    call match_prefix
    pop %r15
    jmp record_reader_statement
/* Iterate a saved node's child list and append each reference in order. */
record_reader_children:
    cmpb $0, record_node_bound(%rip)
    je record_reader_copy_roots
    movb $0, record_copy_roots(%rip)
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    lea children_for_prefix(%rip), %r14
    call match_prefix
    call parse_record_identifier
    mov %rdi, child_index_name(%rip)
    mov %rdx, child_index_name+8(%rip)
    lea children_index_initialization(%rip), %r14
    call match_prefix
    call match_child_index
    lea children_comparison(%rip), %r14
    call match_prefix
    call resolve_node_field
    cmp $4, %r12
    jne invalid
    push %rcx                     /* source field */
    lea children_condition_end(%rip), %r14
    call match_prefix
    call match_child_index
    lea children_for_body(%rip), %r14
    call match_prefix
    call resolve_worklist
    cmp $4, %r12
    jne invalid
    cmpb $0, record_distinct_root_layout(%rip)
    je record_child_destination_ok
    mov record_count(%rip), %rax
    shl $3, %eax
    cmp %rax, %rcx
    jne invalid
record_child_destination_ok:
    push %rcx                     /* destination field */
    lea children_push_prefix(%rip), %r14
    call match_prefix
    call resolve_node_field
    cmp $4, %r12
    jne invalid
    cmp %rcx, 8(%rsp)
    jne invalid
    lea list_index_open(%rip), %r14
    call match_prefix
    call match_child_index
    lea children_push_end(%rip), %r14
    call match_prefix
    pop %rdx
    pop %rcx

    jmp record_reader_copy_loop
match_child_index:
    call parse_record_identifier
    lea child_index_name(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid
    ret

record_reader_copy_roots:
    cmpb $0, record_reader_has_roots(%rip)
    je invalid
    cmpb $0, record_pending_declared(%rip)
    je invalid
    cmpq $0, record_loop_header(%rip)
    jne invalid
    cmpb $0, record_copy_roots(%rip)
    jne invalid
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    lea roots_initialization(%rip), %r14
    call match_prefix
    mov record_count(%rip), %rdx
    shl $3, %edx
    movb $1, record_copy_roots(%rip)
record_reader_copy_loop:
    movw $0x3145, (%rbx)          /* xor r11d,r11d */
    movb $0xdb, 2(%rbx)
    add $3, %rbx
    push %rbx
    cmpb $0, record_copy_roots(%rip)
    jne record_copy_roots_pointer
    movw $0x8b49, (%rbx)          /* mov rax,[r9+disp32] */
    movb $0x81, 2(%rbx)
    mov %ecx, 3(%rbx)
    add $7, %rbx
    jmp record_copy_length
record_copy_roots_pointer:
    movw $0x8948, (%rbx)          /* mov rax,rsi */
    movb $0xf0, 2(%rbx)
    add $3, %rbx
record_copy_length:
    movw $0x3b4c, (%rbx)         /* cmp r11,[rax] */
    movb $0x18, 2(%rbx)
    movw $0x830f, 3(%rbx)        /* jae exit */
    add $9, %rbx
    push %rbx
    movw $0x894c, (%rbx)          /* mov rcx,r11 */
    movb $0xd9, 2(%rbx)
    movl $0xc8448b48, 3(%rbx)    /* mov rax,[rax+rcx*8+8] */
    movb $8, 7(%rbx)
    add $8, %rbx
    mov %edx, %ecx
    call emit_record_list_append
    movw $0xff49, (%rbx)           /* inc r11 */
    movb $0xc3, 2(%rbx)
    movb $0xe9, 3(%rbx)            /* jmp condition */
    add $8, %rbx
    pop %rcx
    pop %rax
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    mov %rbx, %rax
    sub %rcx, %rax
    mov %eax, -4(%rcx)
    pop %r15
    jmp record_reader_statement

record_declare_worklist:
    cmpq $0, record_loop_header(%rip)
    jne invalid
    cmpb $0, record_pending_declared(%rip)
    jne invalid
    lea list_type_open(%rip), %r14
    call match_prefix
    call match_node_layout_name
    lea pending_declaration_prefix(%rip), %r14
    call match_prefix
    call match_node_layout_name
    lea list_value_close(%rip), %r14
    call match_prefix
    lea local_separator(%rip), %r14
    push %r15
    call match_prefix
    pop %r15
    movb $1, record_pending_declared(%rip)
    jmp record_reader_statement

record_worklist_statement:
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    call resolve_worklist
    jmp record_reader_push_self

/* The pending slot follows the caller record's declared fields. */
resolve_worklist:
    cmp %r13, %rsi
    jae invalid
    cmpb $112, (%rsi)
    jne resolve_item_worklist
    cmpb $0, record_pending_declared(%rip)
    je invalid
    lea pending_token(%rip), %r14
    call match_prefix
    mov record_count(%rip), %rcx
    shl $3, %ecx
    mov $4, %r12d
    ret
resolve_item_worklist:
    jmp resolve_parameter_field

record_bind_last_node:
    cmpq $0, record_loop_exit(%rip)
    je invalid
    cmpb $0, record_node_bound(%rip)
    jne invalid
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    call match_node_layout_name
    lea last_node_prefix(%rip), %r14
    call match_prefix
    call resolve_worklist
    cmp $4, %r12
    jne invalid
    cmpb $0, record_distinct_root_layout(%rip)
    je record_last_layout_ok
    mov record_count(%rip), %rax
    shl $3, %eax
    cmp %rax, %rcx
    jne invalid
record_last_layout_ok:
    push %rcx
    lea last_node_index(%rip), %r14
    call match_prefix
    call resolve_worklist
    cmp $4, %r12
    jne invalid
    pop %rdx
    cmp %rdx, %rcx
    jne invalid                   /* length must come from the indexed list */
    push %rcx
    lea last_node_index_end(%rip), %r14
    call match_prefix
    pop %rcx
    movw $0x8b48, (%rbx)         /* mov rax,[rdi+disp32] */
    movb $0x87, 2(%rbx)
    mov %ecx, 3(%rbx)
    movl $0x48088b48, 7(%rbx)    /* mov rcx,[rax] */
    movw $0xc985, 11(%rbx)       /* test rcx,rcx */
    add $13, %rbx
    mov $0x84, %al               /* je bounds */
    call emit_bounds_branch
    movl $0x4cc9ff48, (%rbx)     /* dec rcx */
    movl $0x08c84c8b, 4(%rbx)   /* mov r9,[rax+rcx*8+8] */
    add $8, %rbx
    movb $1, record_node_bound(%rip)
    jmp record_reader_statement_end

record_reader_loop:
    cmpq $0, record_loop_header(%rip)
    jne invalid                   /* at most one worklist loop */
    push %r15
    lea record_loop_prefix(%rip), %r14
    call match_prefix
    call resolve_worklist
    cmp $4, %r12
    jne invalid
    push %rcx
    lea record_loop_body(%rip), %r14
    call match_prefix
    pop %rcx
    movw $0xb841, (%rbx)         /* mov r8d,1000000 */
    movl $1000000, 2(%rbx)
    add $6, %rbx
    mov %rbx, record_loop_header(%rip)
    movw $0x8b48, (%rbx)         /* mov rcx,[rdi+disp32] */
    movb $0x8f, 2(%rbx)
    mov %ecx, 3(%rbx)
    movl $0x00398348, 7(%rbx)    /* cmp qword [rcx],0 */
    movw $0x840f, 11(%rbx)      /* je end */
    add $17, %rbx
    mov %rbx, record_loop_exit(%rip)
    movw $0x8545, (%rbx)         /* test r8d,r8d */
    movb $0xc0, 2(%rbx)
    movw $0x840f, 3(%rbx)       /* je iteration_limit_stub */
    lea iteration_limit_stub(%rip), %rax
    add $9, %rbx
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    movw $0xff41, (%rbx)        /* dec r8d */
    movb $0xc8, 2(%rbx)
    add $3, %rbx
    pop %r15
    jmp record_reader_statement
record_reader_loop_end:
    mov record_loop_exit(%rip), %rcx
    test %rcx, %rcx
    jz invalid
    movb $0xe9, (%rbx)
    add $5, %rbx
    mov record_loop_header(%rip), %rax
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    mov %rbx, %rax
    sub %rcx, %rax
    mov %eax, -4(%rcx)
    movq $0, record_loop_exit(%rip)
    movb $0, record_node_bound(%rip)
    inc %rsi
    call skip_trivia
    jmp record_reader_statement
record_reader_return:
    cmpq $0, record_loop_exit(%rip)
    jne invalid
    cmpb $0, record_reader_bool(%rip)
    jne record_reader_return_bool
    lea return_prefix(%rip), %r14
    call match_prefix
    call resolve_parameter_field
    cmp $1, %r12
    je record_reader_load
    cmp $FIRST_NOMINAL_FIELD_KIND, %r12
    jae record_reader_list
    cmp $6, %r12
    je record_reader_list
    cmp $4, %r12
    jne invalid
record_reader_list:
    push %rcx
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $91, (%rsi)
    je record_reader_index
    lea method_dot(%rip), %r14
    call match_prefix
    lea length_suffix(%rip), %r14
    call match_prefix
    pop %rcx
    jmp record_reader_load
record_reader_index:
    cmp $FIRST_NOMINAL_FIELD_KIND, %r12
    jae invalid                    /* no payload access for read-only empty lists */
    lea list_index_open(%rip), %r14
    call match_prefix
    call parse_operand
    lea list_index_close(%rip), %r14
    call match_prefix
    cmp $4, %r12
    je record_reader_index_field
    mov $7, %r12d
    pop %rcx
    jmp record_reader_load
record_reader_index_field:
    push %r9
    lea method_dot(%rip), %r14
    call match_prefix
    call resolve_record_field
    cmp $1, %r12
    jne invalid
    mov %ecx, %ebp               /* field within the selected record */
    mov $8, %r12d
    pop %r9
    pop %rcx
record_reader_load:
    movw $0x8b48, (%rbx)          /* mov rax,[rdi+disp32] */
    movb $0x87, 2(%rbx)
    mov %ecx, 3(%rbx)
    add $7, %rbx
    cmp $7, %r12
    je record_reader_index_load
    cmp $8, %r12
    je record_reader_index_load
    cmp $FIRST_NOMINAL_FIELD_KIND, %r12
    jae record_reader_length_load
    cmp $6, %r12
    je record_reader_length_load
    cmp $4, %r12
    jne record_reader_ret
record_reader_length_load:
    movw $0x8b48, (%rbx)          /* mov rax,[rax] */
    movb $0, 2(%rbx)
    add $3, %rbx
    jmp record_reader_ret
record_reader_index_load:
    call emit_indexed_list_load
    cmp $8, %r12
    jne record_reader_ret
    movw $0x8b48, (%rbx)         /* mov rax,[rax+disp32] */
    movb $0x80, 2(%rbx)
    mov %ebp, 3(%rbx)
    add $7, %rbx
    jmp record_reader_ret

/* Optional pop yields a record only on the nonempty path. */
record_reader_if:
    lea if_open(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $108, (%rsi)             /* let */
    je record_reader_pop
    test %r15d, %r15d
    jz invalid
    dec %r15d
    push %r15
    call resolve_parameter_field
    cmp $1, %r12
    jne invalid
    push %rcx
    lea record_budget_operator(%rip), %r14
    call match_prefix
    call parse_operand
    pop %rcx
    movw $0xb948, (%rbx)          /* movabs rcx,limit */
    mov %r9, 2(%rbx)
    movw $0x3948, 10(%rbx)       /* cmp [rdi+disp32],rcx */
    movb $0x8f, 12(%rbx)
    mov %ecx, 13(%rbx)
    movw $0x8c0f, 17(%rbx)       /* jl skips the early-return body */
    add $23, %rbx
    push %rbx
    lea scalar_body_open(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $114, (%rsi)             /* return or a Boolean field assignment */
    je record_guard_return
    cmpb $0, record_reader_bool(%rip)
    je invalid
    call resolve_parameter_field
    cmp $2, %r12
    jne invalid
    push %rcx
    lea local_equals(%rip), %r14
    call match_prefix
    call parse_record_result_literal
    lea local_separator(%rip), %r14
    call match_prefix
    pop %rcx
    movw $0xc748, (%rbx)          /* mov qword [rdi+disp32],imm32 */
    movb $0x87, 2(%rbx)
    mov %ecx, 3(%rbx)
    mov %r9d, 7(%rbx)
    add $11, %rbx
record_guard_return:
    lea return_prefix(%rip), %r14
    call match_prefix
    call parse_record_result_literal
    lea helper_end_without_initializer(%rip), %r14
    call match_prefix
    movw $0xb848, (%rbx)          /* movabs rax,result */
    mov %r9, 2(%rbx)
    movb $0xc3, 10(%rbx)
    add $11, %rbx
    pop %rax
    mov %rbx, %rcx
    sub %rax, %rcx
    mov %ecx, -4(%rax)
    pop %r15
    jmp record_reader_statement

record_reader_return_bool:
    lea return_prefix(%rip), %r14
    call match_prefix
    call parse_record_result_literal
    movw $0xb848, (%rbx)          /* movabs rax,boolean */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp record_reader_ret

parse_record_result_literal:
    cmpb $0, record_reader_bool(%rip)
    je parse_operand
    cmp %r13, %rsi
    jae invalid
    xor %r9d, %r9d
    lea false_token(%rip), %r14
    cmpb $116, (%rsi)
    jne record_result_match
    mov $1, %r9d
    lea true_token(%rip), %r14
record_result_match:
    jmp match_prefix

record_reader_pop:
    cmpb $0, record_reader_bool(%rip)
    jne invalid
    cmpq $0, record_loop_exit(%rip)
    jne invalid
    lea list_pop_if_prefix(%rip), %r14
    call match_prefix
    call resolve_parameter_field
    cmp $4, %r12
    jne invalid
    push %rcx
    lea list_pop_true_prefix(%rip), %r14
    call match_prefix
    call resolve_record_field
    cmp $1, %r12
    jne invalid
    mov %ecx, %ebp
    pop %rcx
    call emit_record_list_pop
    movw $0x8b48, (%rbx)         /* mov rax,[rax+disp32] */
    movb $0x80, 2(%rbx)
    mov %ebp, 3(%rbx)
    movb $0xc3, 7(%rbx)          /* ret */
    add $8, %rbx
    mov %rbx, %rax
    sub %r11, %rax
    mov %eax, -4(%r11)
    lea if_false_prefix(%rip), %r14
    call match_prefix
    call parse_operand
    movw $0xb848, (%rbx)         /* movabs rax,fallback */
    mov %r9, 2(%rbx)
    add $10, %rbx
record_reader_ret:
    movb $0xc3, (%rbx)
    inc %rbx
    lea result_code+5(%rip), %rax
    mov %rbx, %rcx
    sub %rax, %rcx
    mov %ecx, -4(%rax)
    lea helper_end_without_initializer(%rip), %r14
    call match_prefix

    pushq selected_record_layout(%rip)
    call parse_layouts
    pop %rax
    call select_record_layout_entry
    jmp record_entry_body

/* Each record statement or field emits less than 512 bytes before the next
 * check, including the final call/return sequence. Keep the ELF tail separate. */
record_check_emit_room:
    lea result_code_limit-512(%rip), %rax
    cmp %rax, %rbx
    ja invalid
    ret

/* ECX selects the field. R11 returns the empty-branch relocation base. */
emit_record_list_pop:
    movw $0x8b48, (%rbx)          /* mov rcx,[rdi+disp32] */
    movb $0x8f, 2(%rbx)
    mov %ecx, 3(%rbx)
    movl $0x48118b48, 7(%rbx)     /* mov rdx,[rcx] */
    movw $0xd285, 11(%rbx)       /* test rdx,rdx */
    movw $0x840f, 13(%rbx)       /* je fallback */
    add $19, %rbx
    mov %rbx, %r11
    movl $0x48caff48, (%rbx)     /* dec rdx */
    movw $0x1189, 4(%rbx)        /* mov [rcx],rdx */
    movl $0xd1448b48, 6(%rbx)    /* mov rax,[rcx+rdx*8+8] */
    movb $8, 10(%rbx)
    movl $0xd144c748, 11(%rbx)   /* mov qword [rcx+rdx*8+8],0 */
    movb $8, 15(%rbx)
    movl $0, 16(%rbx)
    add $20, %rbx
    ret

/* Target RAX holds the list pointer. Emit a checked load using R9's index. */
emit_indexed_list_load:
    movw $0xb948, (%rbx)          /* movabs rcx,index */
    mov %r9, 2(%rbx)
    movw $0x3b48, 10(%rbx)       /* cmp rcx,[rax] */
    movb $0x08, 12(%rbx)
    add $13, %rbx
    mov $0x83, %al               /* jae bounds */
    call emit_bounds_branch
    movl $0xc8448b48, (%rbx)     /* mov rax,[rax+rcx*8+8] */
    movb $8, 4(%rbx)
    add $5, %rbx
    ret

record_entry_body:
    lea record_main_prefix(%rip), %r14
    call match_prefix
    cmpq $0, record_reader_name+8(%rip)
    jne record_entry_existing_layout
    call select_record_layout
    jmp record_entry_construct
record_entry_existing_layout:
    call match_record_name
record_entry_construct:
    mov record_fields_base(%rip), %rax
    mov record_count(%rip), %rcx
    cmpb $0, record_pending_declared(%rip)
    jne record_reserve_list_storage
    cmpb $0, record_distinct_root_layout(%rip)
    jne record_reserve_list_storage
record_scan_list_storage:
    cmpq $6, 16(%rax)
    je record_reserve_list_storage
    cmpq $4, 16(%rax)
    je record_reserve_list_storage
    add $24, %rax
    dec %rcx
    jnz record_scan_list_storage
    jmp record_construct_local
record_reserve_list_storage:
    imul $144, record_count(%rip), %eax
    cmpb $0, record_distinct_root_layout(%rip)
    je record_check_peer_backing
    mov record_root_layout(%rip), %rcx
    imul $144, 16(%rcx), %ecx
    add %ecx, %eax
    jmp record_reserve_list_bytes
record_check_peer_backing:
    cmpb $0, record_reader_has_peer(%rip)
    je record_reserve_list_bytes
    add %eax, %eax
record_reserve_list_bytes:
    mov %eax, %ecx
    cmpb $0, record_pending_declared(%rip)
    je record_reserve_backing
    add $144, %eax
record_reserve_backing:
    movl $0x00ec8148, (%rbx)      /* sub rsp,layout slot backing bytes */
    mov %eax, 3(%rbx)
    movw $0x8949, 7(%rbx)        /* mov r10,rsp */
    movb $0xe2, 9(%rbx)
    add $10, %rbx
    cmpb $0, record_pending_declared(%rip)
    je record_construct_local
    movw $0x8d49, (%rbx)         /* lea rax,[r10+disp32]: pending backing */
    movb $0x82, 2(%rbx)
    mov %ecx, 3(%rbx)
    movl $0x0000c748, 7(%rbx)    /* mov qword [rax],0 */
    movl $0, 10(%rbx)
    movl $0x10ec8348, 14(%rbx)   /* sub rsp,16 */
    movl $0x24048948, 18(%rbx)   /* mov [rsp],rax: hidden pending slot */
    add $22, %rbx
record_construct_local:
    lea helper_local_prefix(%rip), %r14
    call match_prefix
    push %rsi
    call parse_record_identifier
    lea helper_name(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    pop %rcx
    jnz record_invoke_constructor
    mov %rcx, %rsi
    lea new_token(%rip), %r14
    call match_prefix
    call match_record_name
record_open_initializer:
    lea open_brace(%rip), %r14
    call match_prefix
    mov record_fields_base(%rip), %r12
    mov record_count(%rip), %rbp
record_initializer:
    call record_check_emit_room
    call skip_trivia
    call parse_record_identifier
    mov %r12, %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid
    lea colon(%rip), %r14
    call match_prefix
    cmpq $1, 16(%r12)
    jne record_bool
    call parse_operand
    jmp record_push
record_bool:
    cmpq $FIRST_NOMINAL_FIELD_KIND, 16(%r12)
    jae record_typed_empty_list
    cmpq $3, 16(%r12)
    je record_string
    cmpq $4, 16(%r12)
    je record_empty_list
    cmpq $6, 16(%r12)
    je record_mutable_list
    cmpq $5, 16(%r12)
    je record_none
    cmpq $2, 16(%r12)
    jne invalid                    /* optional values are outside the profile */
    cmp %r13, %rsi
    jae invalid
    xor %r9d, %r9d
    lea false_token(%rip), %r14
    cmpb $116, (%rsi)
    jne record_bool_token
    mov $1, %r9d
    lea true_token(%rip), %r14
record_bool_token:
    call match_prefix
    jmp record_push
record_none:
    lea none_token(%rip), %r14
    call match_prefix
    xor %r9d, %r9d
    jmp record_push
record_string:
    lea string_quote(%rip), %r14
    call match_prefix
    lea decoded_string(%rip), %rdi
    xor %edx, %edx
record_string_scan:
    cmp %r13, %rsi
    jae invalid
    movzbl (%rsi), %eax
    cmp $34, %al
    je record_string_done
    cmp $92, %al
    je record_string_escape
    cmp $32, %al
    jb invalid
    cmp $126, %al
    ja invalid
    jmp record_string_append
record_string_escape:
    call decode_escape
    jmp record_string_append

decode_escape:
    inc %rsi
    cmp %r13, %rsi
    jae invalid
    movzbl (%rsi), %eax
    lea string_escapes(%rip), %rcx
    lea string_escapes_end(%rip), %r11
record_string_escape_next:
    cmp %r11, %rcx
    jae invalid
    cmp (%rcx), %al
    je record_string_escape_found
    add $2, %rcx
    jmp record_string_escape_next
record_string_escape_found:
    movzbl 1(%rcx), %eax
    ret
record_string_append:
    cmp $63, %rdx
    jae invalid
    mov %al, (%rdi,%rdx)
    inc %rdx
    inc %rsi
    jmp record_string_scan
record_string_done:
    inc %rsi
    jmp record_blob
record_mutable_list:
    cmpb $0, emitting_constructor(%rip)
    jne invalid                   /* caller-owned backing cannot escape a helper */
    lea int_list_constructor(%rip), %r14
    call match_prefix
record_initialize_list_backing:
    mov record_count(%rip), %rax
    sub %rbp, %rax
    cmpb $0, record_constructing_peer(%rip)
    je record_initialize_list_offset
    cmpb $0, record_distinct_root_layout(%rip)
    je record_initialize_same_layout
    mov record_caller_layout(%rip), %rcx
    add 16(%rcx), %rax
    jmp record_initialize_list_offset
record_initialize_same_layout:
    add record_count(%rip), %rax
record_initialize_list_offset:
    imul $144, %eax, %eax
    movw $0x8d49, (%rbx)         /* lea rax,[r10+disp32] */
    movb $0x82, 2(%rbx)
    mov %eax, 3(%rbx)
    movl $0x0000c748, 7(%rbx)    /* mov qword [rax],0 */
    movl $0, 10(%rbx)
    add $14, %rbx
    jmp record_store
record_typed_empty_list:
    lea list_value_open(%rip), %r14
    call match_prefix
    call parse_record_identifier
    mov layout_count(%rip), %r10
    call resolve_list_element
    cmp 16(%r12), %rax
    jne invalid
    lea list_value_close(%rip), %r14
    call match_prefix
    jmp record_immutable_empty
record_empty_list:
    lea list_value_open(%rip), %r14
    call match_prefix
    call match_record_name
    lea list_value_close(%rip), %r14
    call match_prefix
    cmpb $0, emitting_constructor(%rip)
    je record_initialize_list_backing
record_immutable_empty:
    mov %rsi, %rdi
    xor %edx, %edx
record_blob:
    /* LEA RAX,[RIP+5], then JMP over a length word and the immutable bytes. */
    movl $0x05058d48, (%rbx)
    movw $0, 4(%rbx)
    movb $0, 6(%rbx)
    movb $0xe9, 7(%rbx)
    lea 8(%rdx), %eax
    mov %eax, 8(%rbx)
    mov %rdx, 12(%rbx)
    push %rsi
    mov %rdi, %rsi
    lea 20(%rbx), %rdi
    mov %rdx, %rcx
    cld
    rep movsb
    mov %rdi, %rbx
    pop %rsi
    jmp record_store
record_push:
    movw $0xb848, (%rbx)            /* movabs rax, field value */
    mov %r9, 2(%rbx)
    add $10, %rbx
record_store:
    cmpb $0, emitting_constructor(%rip)
    jne record_store_helper
    movb $0x50, (%rbx)              /* push rax */
    inc %rbx
    jmp record_next_initializer
record_store_helper:
    movl $0x24848948, (%rbx)       /* mov [rsp+disp32],rax */
    lea (,%rbp,8), %rax            /* includes the return address */
    mov %eax, 4(%rbx)
    add $8, %rbx
record_next_initializer:
    add $24, %r12
    dec %rbp
    jz record_finish_initializer
    lea comma(%rip), %r14
    call match_prefix
    jmp record_initializer
record_finish_initializer:
    cmpb $0, emitting_constructor(%rip)
    jne record_finish_helper
    lea record_close_initializer(%rip), %r14
    call match_prefix
record_item_ready:
    cmpq $0, record_reader_name+8(%rip)
    je record_return
    cmpb $0, record_distinct_root_layout(%rip)
    jne record_distinct_constructor
    cmpb $0, record_reader_has_peer(%rip)
    je record_call_reader
    cmpb $0, record_constructing_peer(%rip)
    jne record_call_reader
    call skip_trivia
    call match_record_name
    lea record_peer_local_prefix(%rip), %r14
    call match_prefix
    call match_record_name
    movb $1, record_constructing_peer(%rip)
    jmp record_open_initializer
record_distinct_constructor:
    call skip_trivia
    cmpb $0, record_constructing_peer(%rip)
    jne record_finish_root_peer
    cmp %r13, %rsi
    jae invalid
    cmpb $78, (%rsi)              /* separately constructed Node peer */
    jne record_call_reader
    mov selected_record_layout(%rip), %rax
    mov %rax, record_caller_layout(%rip)
    call lookup_record_layout
    cmp record_root_layout(%rip), %rax
    jne invalid
    call select_record_layout_entry
    lea record_peer_local_prefix(%rip), %r14
    call match_prefix
    call match_record_name
    movb $1, record_constructing_peer(%rip)
    jmp record_open_initializer
record_finish_root_peer:
    mov record_caller_layout(%rip), %rax
    call select_record_layout_entry
    lea roots_local_prefix(%rip), %r14
    call match_prefix
    call match_node_layout_name
    lea roots_local_initializer(%rip), %r14
    call match_prefix
    call match_node_layout_name
    lea list_value_close(%rip), %r14
    call match_prefix
    lea roots_local_push(%rip), %r14
    call match_prefix
    jmp record_call_reader

record_call_reader:
    call skip_trivia
    lea return_prefix(%rip), %r14
    cmpb $0, record_reader_bool(%rip)
    je record_reader_call_prefix
    lea if_open(%rip), %r14
record_reader_call_prefix:
    call match_prefix
    call parse_record_identifier
    lea record_reader_name(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid
    cmpb $0, record_reader_has_peer(%rip)
    jne record_call_reader_with_peer
    cmpb $0, record_reader_has_roots(%rip)
    jne record_call_reader_with_roots
    lea record_reader_call(%rip), %r14
    call match_prefix
    jmp record_call_reader_single
record_call_reader_with_roots:
    cmpb $0, record_distinct_root_layout(%rip)
    jne record_call_reader_distinct_roots
    lea roots_call_prefix(%rip), %r14
    call match_prefix
    call resolve_record_field
    cmp $4, %r12
    jne invalid
    push %rcx
    lea close_paren(%rip), %r14
    call match_prefix
    pop %rcx
    movl $0x24b48b48, (%rbx)     /* mov rsi,[rsp+disp32]: roots */
    mov %ecx, 4(%rbx)
    add $8, %rbx
    jmp record_call_reader_single
record_call_reader_distinct_roots:
    cmpb $0, record_constructing_peer(%rip)
    je record_call_reader_empty_roots
    lea nonempty_roots_call(%rip), %r14
    call match_prefix
    movw $0x8948, (%rbx)          /* mov rax,rsp: Node peer */
    movb $0xe0, 2(%rbx)
    movl $0x10ec8348, 3(%rbx)     /* sub rsp,16 */
    movl $0x2404c748, 7(%rbx)     /* mov qword [rsp],1 */
    movl $1, 11(%rbx)
    movl $0x24448948, 15(%rbx)    /* mov [rsp+8],rax */
    movb $8, 19(%rbx)
    movw $0x8948, 20(%rbx)        /* mov rsi,rsp: singleton roots */
    movb $0xe6, 22(%rbx)
    movl $0x24bc8d48, 23(%rbx)    /* lea rdi,[rsp+disp32]: budget */
    mov record_root_layout(%rip), %rax
    mov 16(%rax), %rax
    lea 16(,%rax,8), %ecx
    mov %ecx, 27(%rbx)
    add $31, %rbx
    add record_count(%rip), %rax
    jmp record_reader_check_stack_slots
record_call_reader_empty_roots:
    lea empty_roots_call_prefix(%rip), %r14
    call match_prefix
    call match_node_layout_name
    lea list_value_close(%rip), %r14
    call match_prefix
    lea close_paren(%rip), %r14
    call match_prefix
    movl $0x10ec8348, (%rbx)     /* sub rsp,16: empty roots backing */
    movl $0x2404c748, 4(%rbx)   /* mov qword [rsp],0 */
    movl $0, 8(%rbx)
    movw $0x8948, 12(%rbx)      /* mov rsi,rsp */
    movb $0xe6, 14(%rbx)
    movb $0x48, 15(%rbx)        /* lea rdi,[rsp+16] */
    movl $0x10247c8d, 16(%rbx)
    add $20, %rbx
    jmp record_reader_check_alignment
record_call_reader_single:
    movw $0x8948, (%rbx)          /* mov rdi,rsp: caller-owned record */
    movb $0xe7, 2(%rbx)
    add $3, %rbx
record_reader_check_alignment:
    mov record_count(%rip), %rax
record_reader_check_stack_slots:
    test $1, %al
    jz record_reader_aligned
    movb $1, record_reader_call_pad(%rip)
    movl $0x08ec8348, (%rbx)       /* sub rsp,8 */
    add $4, %rbx
    jmp record_reader_aligned
record_call_reader_with_peer:
    lea record_reader_pair_call(%rip), %r14
    call match_prefix
    movw $0x8948, (%rbx)          /* mov rsi,rsp: peer */
    movb $0xe6, 2(%rbx)
    movl $0x24bc8d48, 3(%rbx)    /* lea rdi,[rsp+disp32]: item */
    mov record_count(%rip), %rax
    shl $3, %eax
    mov %eax, 7(%rbx)
    add $11, %rbx
record_reader_aligned:
    movb $0xe8, (%rbx)
    add $5, %rbx
    mov reader_entry(%rip), %rax
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    cmpb $0, record_reader_call_pad(%rip)
    je record_reader_done
    movl $0x08c48348, (%rbx)       /* add rsp,8 */
    add $4, %rbx
record_reader_done:
    cmpb $0, record_reader_bool(%rip)
    je record_end_return
    lea if_true_prefix(%rip), %r14
    call match_prefix
    call parse_operand
    push %r9
    lea if_false_prefix(%rip), %r14
    call match_prefix
    call parse_operand
    pop %rdx
    movl $0x74c08548, (%rbx)     /* test rax,rax; je false */
    movb $12, 4(%rbx)
    movw $0xb848, 5(%rbx)        /* movabs rax,true result */
    mov %rdx, 7(%rbx)
    movw $0x0aeb, 15(%rbx)       /* jmp over false result */
    movw $0xb848, 17(%rbx)       /* movabs rax,false result */
    mov %r9, 19(%rbx)
    add $27, %rbx
    jmp record_end_return
record_finish_helper:
    lea helper_end(%rip), %r14
    call match_prefix
    movb $0xc3, (%rbx)             /* ret */
    inc %rbx
    lea result_code+5(%rip), %rax
    mov %rbx, %rcx
    sub %rax, %rcx
    mov %ecx, -4(%rax)
    movb $0, emitting_constructor(%rip)
    call parse_layouts
    cmp %r13, %rsi
    jae invalid
    cmpb $98, (%rsi)
    je record_bool_helper
    mov constructor_layout(%rip), %rax
    call select_record_layout_entry
    jmp record_entry_body

record_invoke_constructor:
    mov constructor_layout(%rip), %rax
    cmp selected_record_layout(%rip), %rax
    jne invalid
    /* A constructor's immutable empty list has no caller-owned backing.
       Only pass constructed records to a reader when all fields are immutable. */
    cmpq $0, record_reader_name+8(%rip)
    je record_constructor_call
    mov record_count(%rip), %rcx
    mov record_fields_base(%rip), %rax
record_check_constructor_fields:
    cmpq $4, 16(%rax)
    je invalid
    cmpq $6, 16(%rax)
    je invalid
    add $24, %rax
    dec %rcx
    jnz record_check_constructor_fields
record_constructor_call:
    lea helper_call_end(%rip), %r14
    call match_prefix
    movl $0x00ec8148, (%rbx)       /* sub rsp,imm32 (fourth byte overwritten) */
    mov record_count(%rip), %rax
    shl $3, %eax
    mov %eax, 3(%rbx)
    movb $0xe8, 7(%rbx)            /* call helper */
    add $12, %rbx
    lea result_code+5(%rip), %rax
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    jmp record_item_ready
record_return:
    lea record_return_prefix(%rip), %r14
    call match_prefix
    call resolve_record_field
    cmp $2, %r12
    je invalid                     /* main returns int */
    cmp $5, %r12
    je invalid                     /* optional field has no value lowering */
    movl $0x24848b48, (%rbx)         /* mov rax,[rsp+disp32] */
    mov %ecx, 4(%rbx)
    add $8, %rbx
    cmp $1, %r12
    je record_end_return
    lea method_dot(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $97, (%rsi)
    je record_at
    cmpb $115, (%rsi)
    je record_slice
    lea length_suffix(%rip), %r14
    call match_prefix
    movw $0x8b48, (%rbx)           /* mov rax,[rax] */
    movb $0, 2(%rbx)
    add $3, %rbx
    jmp record_end_return
record_at:
    cmp $3, %r12                   /* only strings expose a byte index */
    jne invalid
    lea byte_at_open(%rip), %r14
    call match_prefix
    call parse_operand
    lea close_paren(%rip), %r14
    call match_prefix
    movw $0xb948, (%rbx)           /* movabs rcx,index */
    mov %r9, 2(%rbx)
    movw $0x3b48, 10(%rbx)        /* cmp rcx,[rax] */
    movb $0x08, 12(%rbx)
    add $13, %rbx
    mov $0x83, %al                /* jae bounds; also rejects negative indices */
    call emit_bounds_branch
    jmp emit_record_byte
record_slice:
    cmp $3, %r12
    jne invalid
    lea slice_open(%rip), %r14
    call match_prefix
    call parse_operand
    push %r9
    lea comma(%rip), %r14
    call match_prefix
    call parse_operand
    lea close_paren(%rip), %r14
    call match_prefix
    pop %rdx

    movw $0xb948, (%rbx)           /* movabs rcx,start */
    mov %rdx, 2(%rbx)
    movw $0xba48, 10(%rbx)        /* movabs rdx,end */
    mov %r9, 12(%rbx)
    movw $0x3948, 20(%rbx)        /* cmp rcx,rdx */
    movb $0xd1, 22(%rbx)
    add $23, %rbx
    mov $0x87, %al                /* ja bounds */
    call emit_bounds_branch
    movw $0x3b48, (%rbx)          /* cmp rdx,[rax] */
    movb $0x10, 2(%rbx)
    add $3, %rbx
    mov $0x87, %al                /* ja bounds */
    call emit_bounds_branch
    movw $0x2948, (%rbx)          /* sub rdx,rcx */
    movb $0xca, 2(%rbx)
    add $3, %rbx
    lea method_dot(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jae invalid
    cmpb $97, (%rsi)
    je record_slice_at
    lea length_suffix(%rip), %r14
    call match_prefix
    movw $0x8948, (%rbx)          /* mov rax,rdx */
    movb $0xd0, 2(%rbx)
    add $3, %rbx
    jmp record_end_return
record_slice_at:
    lea byte_at_open(%rip), %r14
    call match_prefix
    call parse_operand
    lea close_paren(%rip), %r14
    call match_prefix
    movw $0xb849, (%rbx)          /* movabs r8,index */
    mov %r9, 2(%rbx)
    movw $0x3949, 10(%rbx)       /* cmp r8,rdx (slice length) */
    movb $0xd0, 12(%rbx)
    add $13, %rbx
    mov $0x83, %al               /* jae bounds */
    call emit_bounds_branch
    movw $0x014c, (%rbx)         /* add rcx,r8 (slice start + index) */
    movb $0xc1, 2(%rbx)
    add $3, %rbx
emit_record_byte:
    movl $0x0844b60f, (%rbx)      /* movzx eax,byte [rax+rcx+8] */
    movb $8, 4(%rbx)
    add $5, %rbx
record_end_return:
    lea record_end(%rip), %r14
    call match_prefix
    cmp %r13, %rsi
    jne invalid
    jmp emit

emit_bounds_branch:
    movb $0x0f, (%rbx)
    mov %al, 1(%rbx)
    lea bounds_stub(%rip), %rax
    add $6, %rbx
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    ret

/* ECX is byte displacement relative to the lowest record slot. */
resolve_parameter_field:
    call match_record_parameter
    lea method_dot(%rip), %r14
    call match_prefix
    jmp resolve_record_field

match_record_parameter:
    call parse_record_identifier
    lea record_parameter(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid
    ret

resolve_record_field:
    call parse_record_identifier
    mov record_fields_base(%rip), %rax
    mov record_count(%rip), %r10
    call find_name
    test %rax, %rax
    jz invalid
    mov 16(%rax), %r12              /* field kind */
    mov record_fields_base(%rip), %rcx
    sub %rcx, %rax
    xor %edx, %edx
    mov $24, %ecx
    div %rcx                       /* layout entry index */
    mov record_count(%rip), %rcx
    dec %rcx
    sub %rax, %rcx                 /* reverse index of pushed field */
    shl $3, %ecx
    ret

/* Input is a parsed element name and the number of visible layouts.
 * Return the stable name-table entry as its nominal identity. */
resolve_list_element:
    push %r10
    lea text_list_elements(%rip), %rax
    mov $2, %r10d
    call find_name
    pop %r10
    test %rax, %rax
    jnz resolved_list_element
    lea layouts(%rip), %rax
    call find_name
    test %rax, %rax
    jz invalid
resolved_list_element:
    ret

lookup_record_layout:
    call parse_record_identifier
    lea layouts(%rip), %rax
    mov layout_count(%rip), %r10
    call find_name
    test %rax, %rax
    jz invalid
    ret

select_record_layout:
    call lookup_record_layout
select_record_layout_entry:
    mov %rax, selected_record_layout(%rip)
    mov (%rax), %rcx
    mov %rcx, record_name(%rip)
    mov 8(%rax), %rcx
    mov %rcx, record_name+8(%rip)
    mov 16(%rax), %rcx
    mov %rcx, record_count(%rip)
    lea layouts(%rip), %rcx
    sub %rcx, %rax
    shl $5, %rax                   /* each layout entry owns 32 field entries */
    lea record_fields(%rip), %rcx
    add %rcx, %rax
    mov %rax, record_fields_base(%rip)
    ret

match_node_layout_name:
    cmpb $0, record_distinct_root_layout(%rip)
    je match_record_name
    call lookup_record_layout
    cmp record_root_layout(%rip), %rax
    jne invalid
    ret

resolve_node_field:
    cmpb $0, record_distinct_root_layout(%rip)
    je resolve_record_field
    pushq record_fields_base(%rip)
    pushq record_count(%rip)
    mov record_root_layout(%rip), %rax
    mov 16(%rax), %rcx
    mov %rcx, record_count(%rip)
    lea layouts(%rip), %rcx
    sub %rcx, %rax
    shl $5, %rax
    lea record_fields(%rip), %rcx
    add %rcx, %rax
    mov %rax, record_fields_base(%rip)
    call resolve_record_field
    popq record_count(%rip)
    popq record_fields_base(%rip)
    ret

match_record_name:
    call parse_record_identifier
    lea record_name(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid
    ret

match_prefix:
    movzbl (%r14), %eax
    test %al, %al
    jz prefix_done
    cmp $32, %al
    je prefix_required
    cmp $1, %al
    je prefix_optional
    cmp %r13, %rsi
    jae invalid
    cmp (%rsi), %al
    jne invalid
    inc %rsi
    inc %r14
    jmp match_prefix
prefix_required:
    mov %rsi, %r15
    call skip_trivia
    cmp %r15, %rsi
    je invalid
    jmp prefix_advance
prefix_optional:
    call skip_trivia
prefix_advance:
    inc %r14
    jmp match_prefix
prefix_done:
    ret

parse_expression:
    lea result_code(%rip), %rbx
    xor %r12d, %r12d
    call emit_expression
    jmp finish_main

/* RBX is the emission cursor. R12D counts operators across the procedure. */
emit_expression:
    call parse_expression_operand
    test %eax, %eax
    jnz expression_local_first
    movw $0xb848, (%rbx)           /* movabs rax,first operand */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp next_operator
expression_local_first:
    mov $0x24848b48, %edx         /* mov rax,[rsp+disp32] */
    call emit_local_slot
next_operator:
    mov $0x01, %ebp                 /* ADD */
    call skip_trivia
    cmp %r13, %rsi
    jae invalid
    cmpb $43, (%rsi)
    je binary_rhs
    cmpb $45, (%rsi)
    jne finish_expression
    mov $0x29, %ebp                 /* SUB */
    lea 1(%rsi), %rcx
    cmp %r13, %rcx
    jae invalid
    cmpb $45, (%rcx)                 /* Reject a contiguous double minus. */
    je invalid
binary_rhs:
    inc %rsi
    call skip_trivia
    call parse_expression_operand
    cmp $256, %r12d
    jae invalid
    test %eax, %eax
    jnz expression_local_rhs
    movw $0xb948, (%rbx)          /* movabs rcx,operand */
    mov %r9, 2(%rbx)
    add $10, %rbx
    jmp expression_arithmetic
expression_local_rhs:
    mov $0x248c8b48, %edx         /* mov rcx,[rsp+disp32] */
    call emit_local_slot
expression_arithmetic:
    movb $0x48, (%rbx)
    mov %bpl, 1(%rbx)
    movb $0xc8, 2(%rbx)
    movw $0x800f, 3(%rbx)        /* jo overflow (rel32) */
    lea overflow_stub(%rip), %rax
    add $9, %rbx
    sub %rbx, %rax
    mov %eax, -4(%rbx)
    inc %r12d
    jmp next_operator
finish_expression:
    cmpb $59, (%rsi)
    je expression_done
    cmpb $44, (%rsi)
    je expression_done
    cmpb $41, (%rsi)
    jne invalid
expression_done:
    ret
finish_main:
    lea record_end(%rip), %r14
    call match_prefix
    cmpb $0, scalar_helper_active(%rip)
    jne finish_scalar_helper
    cmp %r13, %rsi
    jne invalid
    jmp emit

/* Constant names use an uppercase ASCII identifier subset. */
parse_record_identifier:
    mov $1, %r8d
    jmp identifier_begin
parse_identifier:
    xor %r8d, %r8d
identifier_begin:
    mov %rsi, %rdi
    cmp %r13, %rsi
    jae invalid
    movzbl (%rsi), %eax
    call identifier_start
    jnc invalid
    inc %rsi
identifier_more:
    cmp %r13, %rsi
    jae identifier_done
    movzbl (%rsi), %eax
    call identifier_start
    jc identifier_advance
    sub $48, %eax
    cmp $9, %eax
    ja identifier_done
identifier_advance:
    inc %rsi
    jmp identifier_more
identifier_done:
    mov %rsi, %rdx
    sub %rdi, %rdx
    cmp $63, %rdx
    ja invalid
    ret

identifier_start:
    cmp $95, %al
    je identifier_yes
    mov %al, %cl
    sub $65, %cl
    cmp $25, %cl
    jbe identifier_yes
    test %r8d, %r8d
    jz identifier_no
    sub $32, %cl
    cmp $25, %cl
    jbe identifier_yes
identifier_no:
    clc
    ret
identifier_yes:
    stc
    ret

/* RDI/RDX name span; RAX matching entry or zero. Input storage is immutable. */
find_constant:
    lea constants(%rip), %rax
    mov constant_count(%rip), %r10
find_name:
constant_next:
    test %r10, %r10
    jz constant_missing
    cmp %rdx, 8(%rax)
    jne constant_advance
    mov (%rax), %r11
    xor %ecx, %ecx
constant_compare:
    cmp %rdx, %rcx
    je constant_found
    mov (%r11,%rcx), %r8b
    cmp (%rdi,%rcx), %r8b
    jne constant_advance
    inc %rcx
    jmp constant_compare
constant_advance:
    add $24, %rax
    dec %r10
    jmp constant_next
constant_missing:
    xor %eax, %eax
constant_found:
    ret

/* EAX indicates a local read. R9 carries immediate operands. */
parse_expression_operand:
    cmpq $0, scalar_local_count(%rip)
    je expression_immediate
    cmp %r13, %rsi
    jae invalid
    cmpb $95, (%rsi)
    jne expression_immediate
    push %rsi
    call parse_record_identifier
    call find_scalar_local
    pop %rdx
    test %rax, %rax
    jz expression_retry_constant
    mov 16(%rax), %eax
    ret
expression_retry_constant:
    mov %rdx, %rsi
expression_immediate:
    call parse_operand
    xor %eax, %eax
    ret

parse_operand:
    xor %r8d, %r8d
    cmp %r13, %rsi
    jae invalid
    movzbl (%rsi), %eax
    call identifier_start
    jnc parse_literal
    call parse_identifier
    call find_constant
    test %rax, %rax
    jz invalid
    mov 16(%rax), %r9
    ret

parse_literal:
    cmp %r13, %rsi
    jae invalid
    cmpb $39, (%rsi)
    jne parse_number
    inc %rsi
    cmp %r13, %rsi
    jae invalid
    movzbl (%rsi), %eax
    cmp $92, %al
    je char_escape
    cmp $39, %al
    je invalid
    cmp $32, %al
    jb invalid
    cmp $126, %al
    ja invalid
    jmp char_close
char_escape:
    call decode_escape
char_close:
    inc %rsi
    cmp %r13, %rsi
    jae invalid
    cmpb $39, (%rsi)
    jne invalid
    inc %rsi
    mov %eax, %r9d
    ret

parse_number:
    xor %r8d, %r8d
    cmp %r13, %rsi
    jae invalid
    cmpb $45, (%rsi)
    jne digits_start
    inc %rsi
    mov $1, %r8d
digits_start:
    lea 2(%rsi), %rax
    cmp %r13, %rax
    ja decimal_digits
    cmpw $0x7830, (%rsi)          /* 0x */
    jne decimal_digits
    test %r8d, %r8d
    jnz invalid                   /* unary negation of hex is outside this subset */
    add $2, %rsi
    xor %r9d, %r9d
    xor %r10d, %r10d
hex_digit:
    cmp %r13, %rsi
    jae finish_digits
    movzbl (%rsi), %eax
    sub $48, %eax
    cmp $9, %eax
    jbe hex_accumulate
    movzbl (%rsi), %eax
    or $32, %eax
    sub $97, %eax
    cmp $5, %eax
    ja finish_digits
    add $10, %eax
hex_accumulate:
    mov %r9, %rdx
    shr $60, %rdx
    jnz invalid
    shl $4, %r9
    or %rax, %r9
    inc %rsi
    inc %r10d
    jmp hex_digit
decimal_digits:
    xor %r9d, %r9d
    xor %r10d, %r10d
digit:
    cmp %r13, %rsi
    jae invalid
    movzbl (%rsi), %eax
    sub $48, %eax
    cmp $9, %eax
    ja finish_digits
    movabs $922337203685477580, %rdx
    cmp %rdx, %r9
    ja invalid
    jb accumulate
    lea 7(%r8), %edx
    cmp %edx, %eax
    ja invalid
accumulate:
    imul $10, %r9, %r9
    add %rax, %r9
    inc %rsi
    inc %r10d
    jmp digit
finish_digits:
    test %r10d, %r10d
    jz invalid
    test %r8d, %r8d
    jz return_number
    neg %r9
return_number:
    ret
emit:
    lea result_tail(%rip), %rsi
    mov %rbx, %rdi
    mov $(result_tail_end-result_tail), %ecx
    cld
    rep movsb
    lea image(%rip), %rsi
    mov %rdi, %rdx
    sub %rsi, %rdx
    mov %rdx, result_filesz(%rip)
    mov %rdx, result_memsz(%rip)
    mov $1, %edi
write_image:
    mov $1, %eax
    syscall
    test %rax, %rax
    jle transport_failed
    add %rax, %rsi
    sub %rax, %rdx
    jnz write_image
    xor %edi, %edi
    jmp exit
transport_failed:
    mov $1, %edi
    jmp exit
invalid:
    /* Report the parser cursor as a zero-based byte offset on stderr. */
    mov %rsi, %rax
    lea input(%rip), %rcx
    sub %rcx, %rax
    sub $32, %rsp
    lea 31(%rsp), %rsi
    movb $10, (%rsi)
    mov $10, %ecx
invalid_digit:
    xor %edx, %edx
    div %rcx
    dec %rsi
    add $48, %dl
    mov %dl, (%rsi)
    test %rax, %rax
    jnz invalid_digit
    lea 32(%rsp), %rdx
    sub %rsi, %rdx
    mov $2, %edi
    mov $1, %eax
    syscall
    mov $2, %edi
    jmp exit
input_limit:
    mov $3, %edi
exit:
    mov $60, %eax
    syscall
    ud2

/* Skip ASCII whitespace and comments without reading past the input. */
skip_trivia:
    call is_space
    jc consume_trivia
    lea 1(%rsi), %rcx
    cmp %r13, %rcx
    jae trivia_done
    cmpb $47, (%rsi)
    jne trivia_done
    cmpb $47, 1(%rsi)
    je line_comment_start
    cmpb $42, 1(%rsi)
    jne trivia_done
    add $2, %rsi
block_comment:
    lea 1(%rsi), %rcx
    cmp %r13, %rcx
    jae invalid
    cmpb $42, (%rsi)
    jne block_comment_char
    cmpb $47, 1(%rsi)
    je block_comment_end
block_comment_char:
    call comment_char
    jmp block_comment
block_comment_end:
    add $2, %rsi
    jmp skip_trivia
line_comment_start:
    add $2, %rsi
line_comment:
    cmp %r13, %rsi
    jae trivia_done
    cmpb $10, (%rsi)
    je consume_trivia
    call comment_char
    jmp line_comment
comment_char:
    call is_space
    jc consume_comment_char
    cmpb $32, (%rsi)
    jb invalid
    cmpb $126, (%rsi)
    ja invalid
consume_comment_char:
    inc %rsi
    ret
consume_trivia:
    inc %rsi
    jmp skip_trivia
trivia_done:
    ret
is_space:
    cmp %r13, %rsi
    jae no_space
    movzbl (%rsi), %ecx
    cmp $32, %cl
    je yes_space
    sub $9, %cl
    cmp $4, %cl
    ja no_space
yes_space:
    stc
    ret
no_space:
    clc
    ret

.section .rodata
/* Space requires trivia; byte 1 allows optional trivia. */
struct_prefix: .asciz "struct "
int_prefix: .asciz "int "
bool_prefix: .asciz "bool "
string_prefix: .asciz "string "
list_type_open: .asciz "List\001<\001"
list_type_close: .asciz "\001> "
optional_type_suffix: .asciz "\001?\001"
open_brace: .asciz "\001{\001"
semicolon: .asciz "\001;"
colon: .asciz "\001:\001"
comma: .asciz "\001,\001"
true_token: .asciz "true"
false_token: .asciz "false"
roots_parameter_suffix: .asciz "\001> roots"
roots_initialization: .asciz "for\001(\001int i\001=\0010\001;\001i\001<\001roots\001.\001len\001(\001)\001;\001i\001+=\0011\001)\001{\001pending\001.\001push\001(\001roots\001[\001i\001]\001)\001;\001}\001"
none_token: .asciz "none"
roots_local_prefix: .asciz "List\001<\001"
roots_local_initializer: .asciz "\001> roots\001=\001new List\001<\001"
roots_local_push: .asciz "\001;\001roots\001.\001push\001(\001peer\001)\001;\001"
nonempty_roots_call: .asciz "\001(\001item\001,\001roots\001)"
empty_roots_call_prefix: .asciz "\001(\001item\001,\001new List\001<\001"
roots_call_prefix: .asciz "\001(\001item\001,\001item\001.\001"
record_reader_peer_parameter: .asciz " peer"
record_peer_local_prefix: .asciz " peer\001=\001new "
children_for_prefix: .asciz "for\001(\001int "
children_index_initialization: .asciz "\001=\0010\001;\001"
children_comparison: .asciz "\001<\001node\001.\001"
children_condition_end: .asciz "\001.\001len\001(\001)\001;\001"
children_for_body: .asciz "\001+=\0011\001)\001{\001"
children_push_prefix: .asciz "\001.\001push\001(\001node\001.\001"
children_push_end: .asciz "\001]\001)\001;\001}\001"
node_field_prefix: .asciz "node\001.\001"
last_node_prefix: .asciz " node\001=\001"
last_node_index: .asciz "\001[\001"
last_node_index_end: .asciz "\001.\001len\001(\001)\001-\0011\001]"
record_budget_operator: .asciz "\001>=\001"
record_loop_prefix: .asciz "while\001(\001"
pending_token: .asciz "pending"
pending_declaration_prefix: .asciz "\001> pending\001=\001new List\001<\001"
record_loop_body: .asciz "\001.\001len\001(\001)\001>\0010\001)\001{\001"
record_reader_call: .asciz "\001(\001item\001)"
record_reader_pair_call: .asciz "\001(\001item\001,\001peer\001)"
helper_end_without_initializer: .asciz "\001;\001}\001"
record_main_prefix: .asciz "\001int main\001(\001)\001{\001"
new_token: .asciz "new "
required_trivia: .asciz " "
helper_prefix: .asciz "\001(\001)\001{\001return new "
helper_end: .asciz "\001}\001;\001}"
helper_local_prefix: .asciz " item\001=\001"
helper_call_end: .asciz "\001(\001)\001;"
record_close_initializer: .asciz "\001}\001;"
record_return_prefix: .asciz "\001return item\001.\001"
.set FIRST_NOMINAL_FIELD_KIND, 16
/* Pointer-valued field kinds are disjoint from the small scalar/worklist tags. */
text_list_elements:
    .quad text_string_name,6,0
    .quad text_tainted_name,7,0
text_string_name: .ascii "string"
text_tainted_name: .ascii "Tainted"
string_escapes:
    .byte 110,10, 116,9, 114,13, 48,0, 92,92, 34,34, 39,39
string_escapes_end:
string_quote: .asciz "\""
int_list_constructor: .asciz "new List\001<\001int\001>\001(\001)"
node_token: .asciz "node"
peer_argument: .asciz "peer\001)"
list_push_open: .asciz "push\001(\001"
list_pop_call: .asciz "pop\001(\001)"
list_push_suffix: .asciz "\001.\001push\001(\001"
list_pop_if_prefix: .asciz "let child\001=\001"
list_pop_true_prefix: .asciz "\001.\001pop\001(\001)\001)\001{\001return child\001.\001"
list_index_open: .asciz "[\001"
list_index_close: .asciz "\001]"
list_value_open: .asciz "new List\001<\001"
list_value_close: .asciz "\001>\001(\001)"
method_dot: .asciz "\001.\001"
length_suffix: .asciz "len\001(\001)"
byte_at_open: .asciz "at\001(\001"
slice_open: .asciz "slice\001(\001"
close_paren: .asciz "\001)"
record_end: .asciz "\001;\001}\001"
const_prefix: .asciz "const int "
main_prefix: .asciz "int main\001(\001)\001{\001"
return_prefix: .asciz "return "
/* RDI, RSI, RDX, RCX, R8, R9, in SysV integer argument order. */
argument_push: .word 0x5740,0x5640,0x5240,0x5140,0x5041,0x5141
argument_pop: .word 0x5f40,0x5e40,0x5a40,0x5940,0x5841,0x5941
scalar_body_open: .asciz "\001)\001{\001"
scalar_call_open: .asciz "\001(\001"
local_equals: .asciz "\001=\001"
local_separator: .asciz "\001;\001"
while_open: .asciz "while\001(\001"
while_less: .asciz "\001<\001"
while_body: .asciz "\001)\001{\001"
while_close: .asciz "}\001"
if_open: .asciz "if\001(\001"
if_true_prefix: .asciz "\001)\001{\001return "
if_false_prefix: .asciz "\001;\001}\001return "

.section .data
image:
    .byte 127,69,76,70,2,1,1,0
    .quad 0
    .short 2,62
    .long 1
    .quad 0x400000 + (program-image),64,0
    .long 0
    .short 64,56,2,0,0,0
    .long 1,5
    .quad 0,0x400000,0x400000
result_filesz: .quad 0
result_memsz: .quad 0
    .quad 4096
    .long 0x6474e551,6
    .quad 0,0,0,0,0,16
overflow_stub:
    mov $70, %edi
    mov $60, %eax
    syscall
    ud2
bounds_stub:
    mov $75, %edi
    mov $60, %eax
    syscall
    ud2
iteration_limit_stub:
    mov $73, %edi
    mov $60, %eax
    syscall
    ud2
program:
    .byte 0x48,0xb8                /* movabs rax, imm64 */
result_left:
    .quad 0
result_code:
    .space 256 * 19 + 4096
result_code_limit:
    .space result_tail_end-result_tail

.section .rodata
result_tail:
    push %rax
    mov %rsp, %rsi
    mov $8, %edx
    mov $3, %edi
    mov $1, %eax
    syscall
    xor %edi, %edi
    cmp $8, %rax
    sete %dil
    xor $1, %edi
    mov $60, %eax
    syscall
    ud2
result_tail_end:

.section .bss
.lcomm input,SEED_INPUT_LIMIT + 1
.lcomm decoded_string,63
.lcomm scalar_helper_active,1
.lcomm scalar_helper_arity,8
.lcomm scalar_local_count,8
.lcomm scalar_locals,16 * 24
.lcomm constant_count,8
.lcomm constants,256 * 24
.lcomm record_name,24
.lcomm helper_name,24
.lcomm emitting_constructor,1
.lcomm constructor_layout,8
.lcomm reader_entry,8
.lcomm record_reader_name,24
.lcomm record_parameter,24
.lcomm child_index_name,24
.lcomm record_loop_header,8
.lcomm record_loop_exit,8
.lcomm record_node_bound,1
.lcomm record_pending_declared,1
.lcomm record_push_node_source,1
.lcomm record_reader_has_peer,1
.lcomm record_reader_has_roots,1
.lcomm selected_record_layout,8
.lcomm record_root_layout,8
.lcomm record_distinct_root_layout,1
.lcomm record_caller_layout,8
.lcomm record_reader_call_pad,1
.lcomm record_reader_bool,1
.lcomm record_copy_roots,1
.lcomm record_constructing_peer,1
.lcomm record_count,8
.lcomm layout_count,8
.lcomm layouts,32 * 24
.lcomm record_fields_base,8
.lcomm record_fields,32 * 32 * 24
.section .note.GNU-stack,"",@progbits
