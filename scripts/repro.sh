#!/usr/bin/env bash
# Reproducibility report for a built tree. Usage: scripts/repro.sh OUT.txt  (after `make`)
#
# The compiler is bootstrapped twice: stage 1 (the compiler running under the Python stage 0)
# compiles the compiler to build/stage2.c, and the native compiler built from that compiles it
# again to build/stage3.c. The two must be identical byte for byte (the fixpoint). The generated
# C depends only on the sources, not on the platform or the C compiler, so every platform must
# report the same checksums; scripts/verify-release.sh compares them, and with --rebuild compares
# them with a fresh build of the source archive.
#
# Writes "key: value" lines and fails unless the fixpoint holds.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
out="${1:?usage: repro.sh OUT.txt}"
CC="${CC:-cc}"
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
for f in build/stage2.c build/stage3.c build/capstanc; do
  [[ -f "$ROOT/$f" ]] || { echo "repro: $f is missing; run make first" >&2; exit 1; }
done
s2="$(sha256 "$ROOT/build/stage2.c")"
s3="$(sha256 "$ROOT/build/stage3.c")"
if cmp -s "$ROOT/build/stage2.c" "$ROOT/build/stage3.c"; then fixpoint=reached; else fixpoint=FAILED; fi
commit="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
{
  echo "# Capstan reproducibility report (scripts/repro.sh)"
  echo "compiler: $("$ROOT/build/capstanc" version)"
  echo "commit: $commit"
  echo "platform: $(uname -srm)"
  echo "cc: $("$CC" --version 2>&1 | head -1)"
  echo "python: $(python3 --version 2>&1)"
  echo "fixpoint: $fixpoint"
  echo "sha256 build/stage2.c: $s2"
  echo "sha256 build/stage3.c: $s3"
  for f in "$ROOT"/runtime/*.h "$ROOT"/bootstrap/capstan0.py; do
    echo "sha256 ${f#"$ROOT"/}: $(sha256 "$f")"
  done
} > "$out"
cat "$out"
[[ "$fixpoint" == reached ]] || { echo "repro: build/stage2.c and build/stage3.c differ" >&2; exit 1; }
