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
/* One integer helper with up to six integer arguments. */
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
    cmpq $6, scalar_local_count(%rip)
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
    cmp %r13, %rsi
    jae invalid
    cmpb $105, (%rsi)
    je parse_if
    lea return_prefix(%rip), %r14
    call match_prefix
    call emit_expression
    jmp finish_main
finish_scalar_helper:
    movb $0, scalar_helper_active(%rip)
    movl $0x00c48348, (%rbx)       /* add rsp,imm8 */
    mov scalar_local_count(%rip), %rax
    shl $3, %eax
    mov %al, 3(%rbx)
    movb $0xc3, 4(%rbx)            /* ret */
    add $5, %rbx
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
    pushq scalar_local_count(%rip)  /* preserve arity, hide helper parameters */
    movq $0, scalar_local_count(%rip)
    mov (%rsp), %rax
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
    lea argument_pop(%rip), %rax
scalar_restore_argument:
    dec %rcx
    movzwl (%rax,%rcx,2), %edx
    mov %dx, (%rbx)
    add $2, %rbx
    test %rcx, %rcx
    jnz scalar_restore_argument
    movb $0xe8, (%rbx)             /* call helper */
    add $5, %rbx
    lea result_code+5(%rip), %rax
    sub %rbx, %rax
    mov %eax, -4(%rbx)
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
    mov layout_count(%rip), %rax
    lea (%rax,%rax,2), %rcx
    lea layouts(%rip), %rax
    lea (%rax,%rcx,8), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid                    /* only self-recursive List<ThisLayout> */
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
    call select_record_layout
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
    lea record_main_prefix(%rip), %r14
    call match_prefix
    call select_record_layout
    lea record_local_prefix(%rip), %r14
    call match_prefix
    call match_record_name
record_open_initializer:
    lea open_brace(%rip), %r14
    call match_prefix
    mov record_fields_base(%rip), %r12
    mov record_count(%rip), %rbp
record_initializer:
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
    cmpq $3, 16(%r12)
    je record_string
    cmpq $4, 16(%r12)
    je record_empty_list
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
record_empty_list:
    lea list_value_open(%rip), %r14
    call match_prefix
    call match_record_name
    lea list_value_close(%rip), %r14
    call match_prefix
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
    cmpq $0, helper_name+8(%rip)
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
    cmpq $0, helper_name+8(%rip)
    jne record_finish_helper
    lea record_close_initializer(%rip), %r14
    call match_prefix
    jmp record_return
record_finish_helper:
    lea helper_end(%rip), %r14
    call match_prefix
    movb $0xc3, (%rbx)             /* ret */
    inc %rbx
    lea result_code+5(%rip), %rax
    mov %rbx, %rcx
    sub %rax, %rcx
    mov %ecx, -4(%rax)
    pushq record_fields_base(%rip)
    pushq record_count(%rip)
    call parse_layouts
    popq record_count(%rip)
    popq record_fields_base(%rip)
    lea record_main_prefix(%rip), %r14
    call match_prefix
    call match_record_name
    lea helper_local_prefix(%rip), %r14
    call match_prefix
    call parse_record_identifier
    lea helper_name(%rip), %rax
    mov $1, %r10d
    call find_name
    test %rax, %rax
    jz invalid
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
record_return:
    lea record_return_prefix(%rip), %r14
    call match_prefix
    call parse_record_identifier
    mov record_fields_base(%rip), %rax
    mov record_count(%rip), %r10
    call find_name
    test %rax, %rax
    jz invalid
    mov 16(%rax), %r12              /* field kind */
    cmp $2, %r12
    je invalid                     /* main returns int */
    mov record_fields_base(%rip), %rcx
    sub %rcx, %rax
    xor %edx, %edx
    mov $24, %ecx
    div %rcx                       /* layout entry index */
    mov record_count(%rip), %rcx
    dec %rcx
    sub %rax, %rcx                 /* reverse index of pushed field */
    movl $0x24848b48, (%rbx)         /* mov rax,[rsp+disp32] */
    shl $3, %ecx
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

select_record_layout:
    call parse_record_identifier
    lea layouts(%rip), %rax
    mov layout_count(%rip), %r10
    call find_name
    test %rax, %rax
    jz invalid
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
record_main_prefix: .asciz "\001int main\001(\001)\001{\001"
record_local_prefix: .asciz " item\001=\001new "
required_trivia: .asciz " "
helper_prefix: .asciz "\001(\001)\001{\001return new "
helper_end: .asciz "\001}\001;\001}"
helper_local_prefix: .asciz " item\001=\001"
helper_call_end: .asciz "\001(\001)\001;"
record_close_initializer: .asciz "\001}\001;"
record_return_prefix: .asciz "\001return item\001.\001"
string_escapes:
    .byte 110,10, 116,9, 114,13, 48,0, 92,92, 34,34, 39,39
string_escapes_end:
string_quote: .asciz "\""
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
    .space 256 * 19 + 1536 + (result_tail_end-result_tail)

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
.lcomm scalar_local_count,8
.lcomm scalar_locals,16 * 24
.lcomm constant_count,8
.lcomm constants,256 * 24
.lcomm record_name,24
.lcomm helper_name,24
.lcomm record_count,8
.lcomm layout_count,8
.lcomm layouts,32 * 24
.lcomm record_fields_base,8
.lcomm record_fields,32 * 32 * 24
.section .note.GNU-stack,"",@progbits
