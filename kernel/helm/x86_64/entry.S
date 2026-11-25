/*
 * Helm H0-C0 entry adapter.
 *
 * Limine enters in 64-bit supervisor mode with interrupts disabled. This stub
 * deliberately consumes no bootloader register arguments. It switches to a
 * kernel-owned, statically bounded bootstrap stack before calling Capstan-
 * generated helm_kernel_main.
 *
 * This is not yet an exception-safe kernel: the IDT is undefined at handoff.
 * Keep IF clear until a kernel-owned IDT and exception path are installed.
 */

.section .text.boot,"ax",@progbits
.code64
.global _start
.type _start, @function
_start:
    cli
    cld

    /* Limine sets the third base-tag word to zero only when revision 6 was honoured. */
    cmpq $0, helm_limine_base_revision_tag+16(%rip)
    jne .Lhelm_entry_halt

    /* Use a private 64 KiB bootstrap stack; maintain SysV call alignment. */
    leaq helm_boot_stack_top(%rip), %rsp
    andq $-16, %rsp
    xorq %rbp, %rbp

    call helm_kernel_main

.Lhelm_entry_halt:
    cli
    hlt
    jmp .Lhelm_entry_halt
.size _start, . - _start

.section .bss.boot_stack,"aw",@nobits
.balign 4096
.global helm_boot_stack_bottom
helm_boot_stack_bottom:
    .skip 65536
.global helm_boot_stack_top
helm_boot_stack_top:

/* Request current Limine base revision 6. Entry fails closed if unsupported. */
.section .limine_requests,"a",@progbits
.balign 8
.global helm_limine_base_revision_tag
helm_limine_base_revision_tag:
    .quad 0xf9562b2d5c95a6c8
    .quad 0x6a7b384944536bdc
    .quad 6
