.section .text
.global _start
_start:
    lea roots(%rip), %rcx
    mov $2, %r8d
    call run_fixture
    cmp $1, %eax
    jne failed
    cmpq $4, budget(%rip)
    jne failed
    call write_result

    movq $149999, budget(%rip)
    lea cycle_root(%rip), %rcx
    mov $1, %r8d
    call run_fixture
    test %eax, %eax
    jne failed
    cmpq $150000, budget(%rip)
    jne failed
    cmpq $1, budget+8(%rip)
    jne failed
    call write_result

    movq $0, budget(%rip)
    movq $0, budget+8(%rip)
    lea bad_root(%rip), %rcx
    mov $1, %r8d
    call run_fixture
    cmp $-1, %rax
    jne failed
    cmpq $0, budget(%rip)
    jne failed

    lea oversized_root(%rip), %rcx
    mov $1, %r8d
    call run_fixture
    cmp $-1, %rax
    jne failed
    cmpq $1, budget(%rip)
    jne failed

    movq $150000, budget(%rip)
    xor %r8d, %r8d
    call run_fixture
    cmp $1, %eax
    jne failed
    cmpq $0, budget+8(%rip)
    jne failed
    call write_result
    xor %edi, %edi
    jmp terminate
failed:
    mov $1, %edi
terminate:
    mov $60, %eax
    syscall
    ud2
write_result:
    lea observation(%rip), %rsi
    mov %rax, (%rsi)
    mov budget(%rip), %rax
    mov %rax, 8(%rsi)
    mov budget+8(%rip), %rax
    mov %rax, 16(%rsi)
    mov $24, %edx
    mov $1, %edi
    mov $1, %eax
    syscall
    cmp $24, %rax
    jne failed
    ret
run_fixture:
    sub $8, %rsp
    lea budget(%rip), %rdi
    lea nodes(%rip), %rsi
    mov $5, %edx
    lea scratch(%rip), %r9
    call seed_charge_ast_nodes
    add $8, %rsp
    ret

.section .rodata
roots: .quad 0, 1
cycle_root: .quad 3
bad_root: .quad 5
oversized_root: .quad 4
root_children: .quad 1, 2
cycle_children: .quad 3
nodes:
    .quad root_children, 2
    .quad 0, 0
    .quad 0, 0
    .quad cycle_children, 1
    .quad 0, 150001

.section .bss
.lcomm budget,16
.lcomm observation,24
.lcomm scratch,150000 * 8
.section .note.GNU-stack,"",@progbits
