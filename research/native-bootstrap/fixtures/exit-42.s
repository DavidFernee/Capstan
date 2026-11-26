# Minimal Linux x86-64 syscall-only executable used to exercise check-elf.sh.
# No libc, dynamic loader, relocations or external symbols.
.section .text
.globl _start
.type _start,@function
_start:
    mov $60, %rax
    mov $42, %rdi
    syscall
.size _start, .-_start

.section .note.GNU-stack,"",@progbits
