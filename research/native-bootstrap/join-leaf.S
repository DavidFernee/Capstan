.text
.global capstan_join
.type capstan_join,@function
# SysV base,cursor*,capacity,list offset,separator offset,mode(0 string,1 tainted).
# Return offset/status. Exclusive mapped arena, disjoint cursor, valid stack.
capstan_join:
    test %rdi,%rdi
    jz .Learly
    test $7,%rdi
    jnz .Learly
    test %rsi,%rsi
    jz .Learly
    test $7,%rsi
    jnz .Learly
    cmp $1048576,%rdx
    ja .Learly
    mov %rdi,%rax
    add %rdx,%rax
    jc .Learly
    cmp $1,%r9
    ja .Learly
    push %rbx
    push %rbp
    push %r12
    push %r13
    push %r14
    push %r15
    sub $4144,%rsp
    mov %rdi,%r12
    mov (%rsi),%r13
    mov %rsi,%r14
    mov %rdx,%r15
    mov %r8,4096(%rsp)
    movq $4096,4104(%rsp)
    mov $4093,%edx
    test %r9,%r9
    jz .Llist
    movq $2045,4104(%rsp)
    mov $1024,%edx
.Llist:
    cmp %r15,%r13
    ja .Lfail
    test $15,%r13
    jnz .Lfail
    mov %rcx,%rax
    call .Lmember
    test %rax,%rax
    jz .Lfail
    cmp %rdx,(%rax)
    jne .Lfail
    cmpq $257,8(%rax)
    jne .Lfail
    cmpq $1,24(%rax)
    jne .Lfail
    cmpq $256,16(%rax)
    ja .Lfail
    mov %rax,%rbx
    mov 4096(%rsp),%rax
    mov $4096,%edx
    call .Lbytes
    test %rax,%rax
    jz .Lfail
    mov %rax,4096(%rsp)
    xor %ebp,%ebp
    movq $0,4112(%rsp)
.Lpart:
    mov 4112(%rsp),%r8
    cmp 16(%rbx),%r8
    jae .Lpublish
    test %r8,%r8
    jz .Lvalue
    mov 4096(%rsp),%rax
    call .Lappend
    test %edx,%edx
    jnz .Lfail
.Lvalue:
    mov 4112(%rsp),%r8
    shl $4,%r8
    lea 32(%rbx,%r8),%r10
    cmpq $1,8(%r10)
    jne .Lfail
    mov (%r10),%rax
    mov 4104(%rsp),%rdx
    call .Lbytes
    test %rax,%rax
    jz .Lfail
    call .Lappend
    test %edx,%edx
    jnz .Lfail
    incq 4112(%rsp)
    jmp .Lpart
.Lpublish:
    mov %rbp,%r11
    shl $4,%r11
    add $16,%r11
    mov %r15,%rax
    sub %r13,%rax
    cmp %rax,%r11
    ja .Lfail
    lea (%r12,%r13),%r10
    mov 4104(%rsp),%rax
    mov %rax,(%r10)
    mov %rbp,8(%r10)
    add $16,%r10
    xor %ecx,%ecx
.Lwrite:
    cmp %rbp,%rcx
    jae .Lcommit
    movzbl (%rsp,%rcx),%eax
    mov %rax,(%r10)
    movq $1,8(%r10)
    add $16,%r10
    inc %rcx
    jmp .Lwrite
.Lcommit:
    mov %r13,%rax
    add %r13,%r11
    mov %r11,(%r14)
    xor %edx,%edx
    jmp .Ldone
.Lfail:
    xor %eax,%eax
    mov $1,%edx
.Ldone:
    add $4144,%rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbp
    pop %rbx
    ret
.Learly:
    xor %eax,%eax
    mov $1,%edx
    ret
# Member RAX offset -> pointer or zero. Preserves RDX expected tag.
.Lmember:
    cmp %r13,%rax
    jae .Lbad
    test $15,%rax
    jnz .Lbad
    xor %r10d,%r10d
.Lscan:
    mov %r13,%r11
    sub %r10,%r11
    cmp $16,%r11
    jb .Lbad
    cmpq $1,(%r12,%r10)
    jb .Lbad
    cmpq $4096,(%r12,%r10)
    ja .Lbad
    mov 8(%r12,%r10),%rcx
    cmp $4096,%rcx
    ja .Lbad
    shl $4,%rcx
    add $16,%rcx
    cmp %r11,%rcx
    ja .Lbad
    cmp %rax,%r10
    je .Lfound
    add %rcx,%r10
    cmp %rax,%r10
    ja .Lbad
    jmp .Lscan
.Lfound:
    lea (%r12,%r10),%rax
    ret
.Lbad:
    xor %eax,%eax
    ret
.Lbytes:
    call .Lmember
    test %rax,%rax
    jz .Lbad
    cmp %rdx,(%rax)
    jne .Lbad
    mov 8(%rax),%rcx
    lea 16(%rax),%r10
.Lvalidate:
    test %rcx,%rcx
    jz .Lvalid
    cmpq $255,(%r10)
    ja .Lbad
    cmpq $1,8(%r10)
    jne .Lbad
    add $16,%r10
    dec %rcx
    jmp .Lvalidate
.Lvalid:
    ret
# Append prevalidated bytes into stack scratch, not the arena.
# Return EDX status. RSP+8 is caller scratch, RBP current output size.
.Lappend:
    mov 8(%rax),%rcx
    lea (%rbp,%rcx),%r11
    cmp $4096,%r11
    ja .Lappend_bad
    lea 16(%rax),%r10
.Lcopy:
    test %rcx,%rcx
    jz .Lappend_ok
    mov (%r10),%rax
    mov %al,8(%rsp,%rbp)
    add $16,%r10
    inc %rbp
    dec %rcx
    jmp .Lcopy
.Lappend_ok:
    xor %edx,%edx
    ret
.Lappend_bad:
    mov $1,%edx
    ret
.size capstan_join, .-capstan_join
.section .note.GNU-stack,"",@progbits
