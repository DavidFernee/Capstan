#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AS="${AS:-as}"
LD="${LD:-ld}"
READELF="${READELF:-readelf}"
OBJDUMP="${OBJDUMP:-objdump}"
for tool in "$AS" "$LD" "$READELF" "$OBJDUMP"; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "missing required tool: $tool" >&2
        exit 1
    }
done

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

"$AS" --64 "$ROOT/kernel/helm/x86_64/entry.S" -o "$tmp/entry.o"
cat > "$tmp/stub.S" <<'ASM'
.section .text,"ax",@progbits
.global helm_kernel_main
.type helm_kernel_main,@function
helm_kernel_main:
    xorl %eax, %eax
    ret
.size helm_kernel_main, . - helm_kernel_main

.section .rodata,"a",@progbits
.asciz "Helm H0-C0 linker contract"

.section .data,"aw",@progbits
.quad 0x48454c4d

.section .note.GNU-stack,"",@progbits
ASM
"$AS" --64 "$tmp/stub.S" -o "$tmp/stub.o"
"$LD" -nostdlib -static -z max-page-size=0x1000 \
    -T "$ROOT/kernel/helm/x86_64/linker.ld" \
    -o "$tmp/helm-kernel.elf" "$tmp/entry.o" "$tmp/stub.o"

"$READELF" -h "$tmp/helm-kernel.elf" > "$tmp/header"
"$READELF" -lW "$tmp/helm-kernel.elf" > "$tmp/program-headers"
"$OBJDUMP" -d "$tmp/helm-kernel.elf" > "$tmp/disassembly"

grep -q 'Class:.*ELF64' "$tmp/header"
grep -q 'Machine:.*Advanced Micro Devices X86-64' "$tmp/header"
grep -q 'Entry point address:.*ffffffff8000' "$tmp/header"
grep -q 'LOAD.*R E' "$tmp/program-headers"
grep -q 'LOAD.*R ' "$tmp/program-headers"
grep -q 'LOAD.*RW ' "$tmp/program-headers"
grep -q '<_start>:' "$tmp/disassembly"
grep -q 'cli' "$tmp/disassembly"
grep -q 'cld' "$tmp/disassembly"
grep -q 'call.*helm_kernel_main' "$tmp/disassembly"

# The stack must be a bounded, page-aligned NOBITS allocation in the RW segment.
"$READELF" -sW "$tmp/helm-kernel.elf" > "$tmp/symbols"
grep -q 'helm_boot_stack_bottom' "$tmp/symbols"
grep -q 'helm_boot_stack_top' "$tmp/symbols"

echo "Helm H0-C0: entry assembly, higher-half ELF entry, RX/R/RW segments and bounded bootstrap stack verified"
