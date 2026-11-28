.text
.global capstan_tainted_slice
.type capstan_tainted_slice,@function
# SysV: arena, committed*, capacity, source offset, start, end.
# Return (offset,status) in RAX,RDX. Valid mapped backing, cursor and stack
# are caller obligations. No mutation until all checks complete.
capstan_tainted_slice:
    test %rdi,%rdi
    jz .Lreject
    test $7,%rdi
    jnz .Lreject
    test %rsi,%rsi
    jz .Lreject
    test $7,%rsi
    jnz .Lreject
    cmp $1048576,%rdx
    ja .Lreject
    mov %rdi,%rax
    add %rdx,%rax
    jc .Lreject
    mov (%rsi),%r10
    cmp %rdx,%r10
    ja .Lreject
    test $15,%r10
    jnz .Lreject
    cmp %r10,%rcx
    jae .Lreject
    test $15,%rcx
    jnz .Lreject
    xor %eax,%eax
.Lscan:
    mov %r10,%r11
    sub %rax,%r11
    cmp $16,%r11
    jb .Lreject
    cmpq $1,(%rdi,%rax)
    jb .Lreject
    cmpq $4096,(%rdi,%rax)
    ja .Lreject
    mov 8(%rdi,%rax),%r11
    cmp $4096,%r11
    ja .Lreject
    shl $4,%r11
    add $16,%r11
    add %rax,%r11
    cmp %r10,%r11
    ja .Lreject
    cmp %rcx,%rax
    je .Lfound
    cmp %rcx,%r11
    ja .Lreject
    mov %r11,%rax
    jmp .Lscan
.Lfound:
    cmpq $2045,(%rdi,%rcx)
    jne .Lreject
    mov 8(%rdi,%rcx),%r11
    cmp %r9,%r8
    ja .Lreject
    cmp %r11,%r9
    ja .Lreject
    # All source byte pairs must be canonical, including outside slice.
    lea 16(%rdi,%rcx),%rax
    test %r11,%r11
    jz .Lextent
.Lvalidate:
    cmpq $255,(%rax)
    ja .Lreject
    cmpq $1,8(%rax)
    jne .Lreject
    add $16,%rax
    dec %r11
    jnz .Lvalidate
.Lextent:
    sub %r8,%r9
    mov %r9,%r11
    shl $4,%r11
    add $16,%r11
    mov %rdx,%rax
    sub %r10,%rax
    cmp %rax,%r11
    ja .Lreject
    # No remaining rejection; write distinct new object, publish last.
    lea (%rdi,%r10),%rdx
    movq $2045,(%rdx)
    mov %r9,8(%rdx)
    shl $4,%r8
    lea 16(%rdi,%rcx),%rax
    add %r8,%rax
    add $16,%rdx
    test %r9,%r9
    jz .Lpublish
.Lcopy:
    mov (%rax),%rcx
    mov %rcx,(%rdx)
    movq $1,8(%rdx)
    add $16,%rax
    add $16,%rdx
    dec %r9
    jnz .Lcopy
.Lpublish:
    add %r10,%r11
    mov %r11,(%rsi)
    mov %r10,%rax
    xor %edx,%edx
    ret
.Lreject:
    xor %eax,%eax
    mov $1,%edx
    ret
.size capstan_tainted_slice, .-capstan_tainted_slice
.section .note.GNU-stack,"",@progbits
