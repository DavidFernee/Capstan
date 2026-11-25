#!/bin/sh
# Research-only Linux x86-64 harness for Capstan-emitted GNU assembly.
# This is not a production build integration and deliberately avoids a C compiler driver.
set -eu

usage() {
    echo "usage: $0 INPUT.s EXPECTED_EXIT_STATUS" >&2
    exit 64
}

[ "$#" -eq 2 ] || usage
assembly=$1
expected=$2

case "$expected" in
    ''|*[!0-9]*) usage ;;
esac
[ "$expected" -le 255 ] || usage
[ -f "$assembly" ] || { echo "assembly input does not exist" >&2; exit 66; }

[ "$(uname -s)" = Linux ] || { echo "requires Linux" >&2; exit 69; }
[ "$(uname -m)" = x86_64 ] || { echo "requires x86_64" >&2; exit 69; }

for tool in as ld readelf nm sha256sum; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "missing required tool: $tool" >&2
        exit 69
    }
done

work=$(mktemp -d "${TMPDIR:-/tmp}/capstan-native.XXXXXXXX")
trap 'rm -rf "$work"' EXIT HUP INT TERM
object=$work/program.o
executable=$work/program

echo "== toolchain =="
as --version | sed -n '1p'
ld --version | sed -n '1p'
readelf --version | sed -n '1p'

echo "== assemble (GNU as, no compiler driver) =="
as --64 -o "$object" "$assembly"

echo "== link (freestanding static ELF, no standard libraries) =="
ld -m elf_x86_64 -static -nostdlib --no-dynamic-linker -e _start -o "$executable" "$object"

echo "== ELF header =="
readelf -h "$executable"
readelf -h "$executable" | grep -Eq 'Class:[[:space:]]+ELF64' || {
    echo "not ELF64" >&2; exit 1;
}
readelf -h "$executable" | grep -Eq 'Machine:[[:space:]]+Advanced Micro Devices X86-64' || {
    echo "not x86-64" >&2; exit 1;
}
readelf -h "$executable" | grep -Eq 'Type:[[:space:]]+EXEC' || {
    echo "expected fixed-address ET_EXEC output" >&2; exit 1;
}

echo "== program headers =="
readelf -l "$executable"
if readelf -l "$executable" | grep -q 'INTERP'; then
    echo "unexpected ELF interpreter" >&2
    exit 1
fi

echo "== dynamic section =="
if readelf -d "$executable" >"$work/dynamic.txt" 2>&1; then
    cat "$work/dynamic.txt"
    echo "unexpected dynamic section" >&2
    exit 1
else
    cat "$work/dynamic.txt"
    grep -q 'no dynamic section' "$work/dynamic.txt" || {
        echo "could not establish absence of dynamic section" >&2
        exit 1
    }
fi

echo "== undefined symbols =="
undefined=$(nm -u "$executable")
[ -z "$undefined" ] || {
    printf '%s\n' "$undefined" >&2
    echo "unexpected undefined external symbols" >&2
    exit 1
}
echo "none"

echo "== relocations =="
readelf -r "$executable"
if readelf -r "$executable" | grep -q 'Relocation section'; then
    echo "unexpected remaining relocations" >&2
    exit 1
fi

echo "== execute =="
set +e
"$executable"
actual=$?
set -e
echo "exit status: $actual (expected $expected)"
[ "$actual" -eq "$expected" ] || exit 1

echo "== artifact identity =="
sha256sum "$assembly" "$object" "$executable"
echo "PASS: freestanding Linux x86-64 ELF checks"
