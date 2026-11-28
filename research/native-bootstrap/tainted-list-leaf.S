.text
.global capstan_tainted_list
.type capstan_tainted_list,@function
# SysV: base, used extent, receiver offset, mode, index, payload offset.
# Return value/status in RAX/RDX. Caller owns live exclusive backing.
capstan_tainted_list:
    test %rdi,%rdi
    jz .Learly
    test $7,%rdi
    jnz .Learly
    cmp $1048576,%rsi
    ja .Learly
    test $15,%rsi
    jnz .Learly
    mov %rdi,%rax
    add %rsi,%rax
    jc .Learly
    cmp $4,%rcx
    ja .Learly
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    mov %rdi,%r12
    mov %rsi,%r13
    mov %rcx,%r15
    mov %r8,%rbx
    mov %rdx,%rax
    call .Lmember
    test %rax,%rax
    jz .Lfail
    mov %rax,%r14
    cmpq $1024,(%r14)
    jne .Lfail
    cmpq $257,8(%r14)
    jne .Lfail
    cmpq $1,24(%r14)
    jne .Lfail
    mov 16(%r14),%r8
    cmp $256,%r8
    ja .Lfail
    test %r15,%r15
    jz .Llen
    cmp $3,%r15
    je .Lpush
    cmp $4,%r15
    jne .Lindex
    test %r8,%r8
    jz .Lzero
    lea -1(%r8),%rbx
.Lindex:
    cmp %r8,%rbx
    jae .Lfail
    shl $4,%rbx
    lea 32(%r14,%rbx),%rbx
    cmpq $1,8(%rbx)
    jne .Lfail
    mov (%rbx),%rax
    call .Ltainted
    test %rax,%rax
    jz .Lfail
    cmp $1,%r15
    je .Lget
    cmp $4,%r15
    je .Lpop
    mov %r9,%rax
    call .Ltainted
    test %rax,%rax
    jz .Lfail
    mov %r9,(%rbx)
    jmp .Lzero
.Lpush:
    cmp $256,%r8
    jae .Lfail
    mov %r8,%rbx
    shl $4,%rbx
    lea 32(%r14,%rbx),%rbx
    cmpq $0,(%rbx)
    jne .Lfail
    cmpq $0,8(%rbx)
    jne .Lfail
    mov %r9,%rax
    call .Ltainted
    test %rax,%rax
    jz .Lfail
    mov %r9,(%rbx)
    movq $1,8(%rbx)
    incq 16(%r14)
    jmp .Lzero
.Lpop:
    movq $0,(%rbx)
    movq $0,8(%rbx)
    decq 16(%r14)
    jmp .Lzero
.Lget:
    mov (%rbx),%rax
    jmp .Lok
.Llen:
    mov %r8,%rax
    jmp .Lok
.Lzero:
    xor %eax,%eax
.Lok:
    xor %edx,%edx
    jmp .Ldone
.Lfail:
    xor %eax,%eax
    mov $1,%edx
.Ldone:
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret
.Learly:
    xor %eax,%eax
    mov $1,%edx
    ret
# Input offset RAX; return pointer or zero. Preserve r8/r9/rbx/r12-r15.
.Lmember:
    cmp %r13,%rax
    jae .Lnotfound
    test $15,%rax
    jnz .Lnotfound
    xor %r10d,%r10d
.Lscan:
    mov %r13,%r11
    sub %r10,%r11
    cmp $16,%r11
    jb .Lnotfound
    cmpq $1,(%r12,%r10)
    jb .Lnotfound
    cmpq $4096,(%r12,%r10)
    ja .Lnotfound
    mov 8(%r12,%r10),%rcx
    cmp $4096,%rcx
    ja .Lnotfound
    shl $4,%rcx
    add $16,%rcx
    cmp %r11,%rcx
    ja .Lnotfound
    cmp %rax,%r10
    je .Lfound
    add %rcx,%r10
    cmp %rax,%r10
    ja .Lnotfound
    jmp .Lscan
.Lfound:
    lea (%r12,%r10),%rax
    ret
.Lnotfound:
    xor %eax,%eax
    ret
# Validate exact taint tag and every canonical byte/readiness pair.
.Ltainted:
    call .Lmember
    test %rax,%rax
    jz .Lnotfound
    cmpq $2045,(%rax)
    jne .Lnotfound
    mov 8(%rax),%rcx
    lea 16(%rax),%r10
    test %rcx,%rcx
    jz .Lvalid
.Lbytes:
    cmpq $255,(%r10)
    ja .Lnotfound
    cmpq $1,8(%r10)
    jne .Lnotfound
    add $16,%r10
    dec %rcx
    jnz .Lbytes
.Lvalid:
    ret
.size capstan_tainted_list, .-capstan_tainted_list
.section .note.GNU-stack,"",@progbits
