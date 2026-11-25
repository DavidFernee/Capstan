/*
 * Helm initial x86-64 higher-half ELF layout for Limine.
 * No dynamic loader, relocations, interpreter, or runtime is permitted.
 */
OUTPUT_FORMAT(elf64-x86-64)
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

KERNEL_VMA = 0xffffffff80000000;

PHDRS
{
    text   PT_LOAD FLAGS(5); /* PF_R | PF_X */
    rodata PT_LOAD FLAGS(4); /* PF_R */
    data   PT_LOAD FLAGS(6); /* PF_R | PF_W */
}

SECTIONS
{
    . = KERNEL_VMA;

    .text ALIGN(0x1000) :
    {
        KEEP(*(.text.boot))
        *(.text .text.*)
    } :text

    .rodata ALIGN(0x1000) :
    {
        *(.rodata .rodata.*)
    } :rodata

    .data ALIGN(0x1000) :
    {
        *(.data .data.*)
    } :data

    .bss ALIGN(0x1000) (NOLOAD) :
    {
        *(COMMON)
        *(.bss .bss.*)
    } :data

    /DISCARD/ :
    {
        *(.comment)
        *(.eh_frame .eh_frame.*)
        *(.note .note.*)
        *(.interp)
        *(.dynamic .dynsym .dynstr)
        *(.rela .rela.* .rel .rel.*)
        *(.got .got.* .plt .plt.*)
    }
}
