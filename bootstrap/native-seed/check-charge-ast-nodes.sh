#!/usr/bin/env bash
# Compare the freestanding assembly primitive with the actual Capstan source.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"
seed_dir=bootstrap/native-seed
compiler="${1:-$root/bin/capstan}"
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir "$scratch/empty"

as --64 "$seed_dir/charge-ast-nodes.S" -o "$scratch/charge.o"
as --64 "$seed_dir/charge-ast-nodes-test.S" -o "$scratch/charge-test.o"
ld -static -nostdlib -s "$scratch/charge-test.o" "$scratch/charge.o" -o "$scratch/native"
env -i PATH="$scratch/empty" "$scratch/native" > "$scratch/observations"
[[ "$(wc -c < "$scratch/observations")" == 72 ]]
od -An -v -td8 -w24 "$scratch/observations" | awk '{print $1, $2, $3}' > "$scratch/native.txt"

"$compiler" build compiler/ast.cap "$seed_dir/charge-ast-nodes-reference.cap" -o "$scratch/reference"
"$scratch/reference" > "$scratch/reference.txt"
diff -u "$scratch/reference.txt" "$scratch/native.txt"
cat "$scratch/native.txt"
