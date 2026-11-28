.text
.global capstan_log_escape
.type capstan_log_escape,@function
# rdi input, rsi size, rdx output, rcx capacity. rax length or -1.
capstan_log_escape:
    cmp $4096,%rsi
    ja .Lreject
    cmp $4096,%rcx
    ja .Lreject
    test %rsi,%rsi
    jz .Lempty
    test %rdi,%rdi
    jz .Lreject
    test %rdx,%rdx
    jz .Lreject
    push %rbx
    push %r12
    push %r13
    push %r14
    push %r15
    sub $4096,%rsp
    mov %rdi,%r12
    mov %rsi,%r13
    mov %rdx,%r14
    mov %rcx,%r15
    xor %ebx,%ebx
    xor %r8d,%r8d
.Lnext:
    cmp %r13,%r8
    jae .Lpublish
    movzbl (%r12,%r8),%r9d
    mov $1,%r10d
    cmp $32,%r9d
    jb .Lescape
    cmp $127,%r9d
    jb .Lcopy
    cmp $0xc2,%r9d
    jb .Lescape
    cmp $0xdf,%r9d
    jbe .Ltwo
    cmp $0xef,%r9d
    jbe .Lthree
    cmp $0xf4,%r9d
    ja .Lescape
    mov $4,%r10d
    mov %r9d,%eax
    and $7,%eax
    jmp .Ldecode
.Lthree:
    mov $3,%r10d
    mov %r9d,%eax
    and $15,%eax
    jmp .Ldecode
.Ltwo:
    mov $2,%r10d
    mov %r9d,%eax
    and $31,%eax
.Ldecode:
    lea (%r8,%r10),%r11
    cmp %r13,%r11
    ja .Linvalid
    mov $1,%ecx
.Lcont:
    lea (%r8,%rcx),%r11
    movzbl (%r12,%r11),%r11d
    cmp $0x80,%r11d
    jb .Linvalid
    cmp $0xbf,%r11d
    ja .Linvalid
    shl $6,%eax
    and $63,%r11d
    or %r11d,%eax
    inc %ecx
    cmp %r10d,%ecx
    jb .Lcont
    cmp $2,%r10d
    je .Lvalid
    cmp $3,%r10d
    jne .Lfourcheck
    cmp $0x800,%eax
    jb .Linvalid
    cmp $0xd800,%eax
    jb .Lvalid
    cmp $0xdfff,%eax
    jbe .Linvalid
    jmp .Lvalid
.Lfourcheck:
    cmp $0x10000,%eax
    jb .Linvalid
    cmp $0x10ffff,%eax
    ja .Linvalid
.Lvalid:
    cmp $0x9f,%eax
    jbe .Lescape
    cmp $0x61c,%eax
    je .Lescape
    cmp $0x200e,%eax
    je .Lescape
    cmp $0x200f,%eax
    je .Lescape
    cmp $0xfeff,%eax
    je .Lescape
    cmp $0x2028,%eax
    jb .Lcopy
    cmp $0x202e,%eax
    jbe .Lescape
    cmp $0x2066,%eax
    jb .Lcopy
    cmp $0x2069,%eax
    jbe .Lescape
.Lcopy:
    lea (%rbx,%r10),%rax
    cmp %r15,%rax
    ja .Lfail
    xor %ecx,%ecx
.Lcopyloop:
    movb (%r12,%r8),%al
    movb %al,(%rsp,%rbx)
    inc %r8
    inc %rbx
    inc %ecx
    cmp %r10d,%ecx
    jb .Lcopyloop
    jmp .Lnext
.Linvalid:
    mov $1,%r10d
.Lescape:
    lea (%rbx,%r10,4),%rax
    cmp %r15,%rax
    ja .Lfail
    xor %ecx,%ecx
.Lhexloop:
    movzbl (%r12,%r8),%eax
    movb $92,(%rsp,%rbx)
    movb $120,1(%rsp,%rbx)
    mov %eax,%r11d
    shr $4,%eax
    and $15,%r11d
    add $48,%eax
    cmp $57,%eax
    jbe .Lhigh
    add $39,%eax
.Lhigh:
    add $48,%r11d
    cmp $57,%r11d
    jbe .Llow
    add $39,%r11d
.Llow:
    mov %al,2(%rsp,%rbx)
    mov %r11b,3(%rsp,%rbx)
    add $4,%rbx
    inc %r8
    inc %ecx
    cmp %r10d,%ecx
    jb .Lhexloop
    jmp .Lnext
.Lpublish:
    xor %ecx,%ecx
.Lpublishloop:
    cmp %rbx,%rcx
    jae .Lsuccess
    movb (%rsp,%rcx),%al
    movb %al,(%r14,%rcx)
    inc %rcx
    jmp .Lpublishloop
.Lsuccess:
    mov %rbx,%rax
    jmp .Ldone
.Lfail:
    mov $-1,%rax
.Ldone:
    add $4096,%rsp
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %rbx
    ret
.Lempty:
    xor %eax,%eax
    ret
.Lreject:
    mov $-1,%rax
    ret
.size capstan_log_escape, .-capstan_log_escape
.section .note.GNU-stack,"",@progbits
