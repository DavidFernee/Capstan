#!/usr/bin/env bash
# Probe the seed against the pinned existing compiler workload.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "$root"
seed_dir=bootstrap/native-seed
manifest="$seed_dir/compiler-sources.sha256"

if [[ "$(uname -sm)" != "Linux x86_64" ]]; then
    echo "The current seed targets Linux x86-64." >&2
    exit 2
fi

sources=()
while read -r digest path extra; do
    if [[ ! "$digest" =~ ^[0-9a-f]{64}$ || ! "$path" =~ ^compiler/[a-z]+\.cap$ ||
        -n "$extra" || ! -f "$path" || -L "$path" ]]; then
        echo "Invalid compiler workload manifest entry." >&2
        exit 2
    fi
    for previous in "${sources[@]}"; do
        if [[ "$previous" == "$path" ]]; then
            echo "Duplicate compiler workload module $path." >&2
            exit 2
        fi
    done
    sources+=("$path")
done < "$manifest"
(( ${#sources[@]} > 0 ))
sha256sum -c --strict "$manifest"

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir "$scratch/empty"
as --64 "$seed_dir/seed.S" -o "$scratch/seed.o"
ld -static -nostdlib -s "$scratch/seed.o" -o "$scratch/seed"

# The current seed only has a single byte-stream input. Probe with the ordered
# concatenation of the complete source modules. This is not an import format.
for source in "${sources[@]}"; do
    cat -- "$source"
    printf '\n'
done > "$scratch/workload.cap"

bytes="$(wc -c < "$scratch/workload.cap")"
printf 'Ordered workload: %s modules, %s bytes\n' "${#sources[@]}" "$bytes"
status=0
env -i PATH="$scratch/empty" "$scratch/seed" \
    < "$scratch/workload.cap" > "$scratch/candidate.elf" 2>"$scratch/seed.err" || status=$?
if (( status != 0 )); then
    if [[ -s "$scratch/candidate.elf" ]]; then
        echo "Seed failure produced partial output." >&2
        exit 1
    fi
    if (( status == 3 )); then
        echo "The workload exceeds the seed input limit." >&2
    elif (( status == 2 )); then
        offset="$(cat "$scratch/seed.err")"
        if [[ "$offset" =~ ^[0-9]{1,7}$ ]] && (( offset <= bytes )); then
            printf 'Seed parser stopped at workload byte %s.\n' "$offset" >&2
            for source in "${sources[@]}"; do
                size="$(wc -c < "$source")"
                if (( offset <= size )); then
                    line="$(head -c "$offset" "$source" | wc -l)"
                    printf 'Parser cursor: %s:%s\n' "$source" "$((line + 1))" >&2
                    break
                fi
                offset=$((offset - size - 1))
            done
        fi
    fi
    printf 'Seed rejected the compiler workload with status %s. No S1 artifact.\n' "$status" >&2
    exit 1
fi
if [[ ! -s "$scratch/candidate.elf" ]]; then
    echo "Seed reported success with an empty output." >&2
    exit 1
fi
sha256sum "$scratch/candidate.elf"
echo "Seed produced a candidate artifact. S1 compiler conformance has not been checked."
