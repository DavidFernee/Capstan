.text
.global capstan_log_bridge
.type capstan_log_bridge,@function
# SysV base,cursor*,capacity,left,right,mode(0 escape,1 concat)
# returns offset/status. Exclusive valid backing and disjoint cursor required.
capstan_log_bridge:
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
    sub $8224,%rsp
    mov %rdi,%r12
    mov (%rsi),%r13
    mov %rsi,%r14
    mov %rdx,%r15
    mov %r9,%rbp
    mov %r8,8192(%rsp)
    cmp %r15,%r13
    ja .Lfail
    test $15,%r13
    jnz .Lfail
    mov %rcx,%rax
    call .Lobject
    test %rax,%rax
    jz .Lfail
    mov (%rax),%rbx
    mov 8(%rax),%rcx
    mov %rcx,8200(%rsp)
    lea 16(%rax),%r10
    xor %r11d,%r11d
.Lfirst:
    cmp %rcx,%r11
    jae .Lmode
    mov (%r10),%rax
    mov %al,(%rsp,%r11)
    add $16,%r10
    inc %r11
    jmp .Lfirst
.Lmode:
    test %rbp,%rbp
    jnz .Lconcat
    mov %rsp,%rdi
    mov 8200(%rsp),%rsi
    lea 4096(%rsp),%rdx
    mov $4096,%ecx
    call .Lescape_raw
    test %rax,%rax
    js .Lfail
    mov %rax,%rbx
    lea 4096(%rsp),%r8
    jmp .Lpublish_check
.Lconcat:
    cmp $2045,%rbx
    je .Lfail
    mov 8192(%rsp),%rax
    call .Lobject
    test %rax,%rax
    jz .Lfail
    cmpq $2045,(%rax)
    je .Lfail
    cmp $2046,%rbx
    je .Lconcat_kind
    cmpq $2046,(%rax)
    jne .Lfail
.Lconcat_kind:
    mov 8200(%rsp),%r11
    mov 8(%rax),%rcx
    lea (%r11,%rcx),%rbx
    cmp $4096,%rbx
    ja .Lfail
    lea 16(%rax),%r10
.Lsecond:
    test %rcx,%rcx
    jz .Lconcat_ready
    mov (%r10),%rax
    mov %al,(%rsp,%r11)
    add $16,%r10
    inc %r11
    dec %rcx
    jmp .Lsecond
.Lconcat_ready:
    mov %rsp,%r8
.Lpublish_check:
    mov %rbx,%r11
    shl $4,%r11
    add $16,%r11
    mov %r15,%rax
    sub %r13,%rax
    cmp %rax,%r11
    ja .Lfail
    lea (%r12,%r13),%r10
    movq $2046,(%r10)
    mov %rbx,8(%r10)
    add $16,%r10
    xor %ecx,%ecx
.Lwrite:
    cmp %rbx,%rcx
    jae .Lcommit
    movzbl (%r8,%rcx),%eax
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
    add $8224,%rsp
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
# Membership and all byte pairs; exact eligible tags. Return pointer or zero.
.Lobject:
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
    cmpq $4096,(%rax)
    je .Lvalidate
    cmpq $2045,(%rax)
    je .Lvalidate
    cmpq $2046,(%rax)
    jne .Lbad
.Lvalidate:
    mov 8(%rax),%rcx
    lea 16(%rax),%r10
.Lpair:
    test %rcx,%rcx
    jz .Lreturn
    cmpq $255,(%r10)
    ja .Lbad
    cmpq $1,8(%r10)
    jne .Lbad
    add $16,%r10
    dec %rcx
    jmp .Lpair
.Lreturn:
    ret
.Lbad:
    xor %eax,%eax
    ret
.size capstan_log_bridge, .-capstan_log_bridge
# Existing 589-byte raw escape leaf appended exactly here by emitter.
.Lescape_raw:
.section .note.GNU-stack,"",@progbits
