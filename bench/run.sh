#!/usr/bin/env bash
# Capstan vs hand-written C. Fails if any benchmark is slower than MAX_RATIO.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CC="${CC:-cc}"; MAX_RATIO="${MAX_RATIO:-5.0}"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
best() { python3 -I -c 'import subprocess, sys, time
b = 1e9
for _ in range(3):
    s = time.perf_counter(); subprocess.run([sys.argv[1]], stdout=subprocess.DEVNULL, check=True); b = min(b, time.perf_counter() - s)
print(int(b * 1000))' "$1"; }
printf '%-10s %10s %10s %8s\n' benchmark "C (ms)" "Capstan" ratio
status=0
for f in "$ROOT"/bench/*.cap; do
  n="$(basename "$f" .cap)"
  "$ROOT/build/capstanc" build -o "$tmp/$n.c" "$f" >/dev/null
  "$CC" -O2 -std=gnu11 -w -I"$ROOT/runtime" "$tmp/$n.c" -o "$tmp/$n.cap.bin"
  "$CC" -O2 -w "$ROOT/bench/$n.c" -o "$tmp/$n.c.bin"
  [[ "$("$tmp/$n.cap.bin")" == "$("$tmp/$n.c.bin")" ]] || { echo "$n: outputs differ"; status=1; continue; }
  c=$(best "$tmp/$n.c.bin"); k=$(best "$tmp/$n.cap.bin")
  r=$(awk -v a="$k" -v b="$c" 'BEGIN { printf "%.2f", (b > 0 ? a / b : 1) }')
  printf '%-10s %10s %10s %7sx\n' "$n" "$c" "$k" "$r"
  awk -v r="$r" -v m="$MAX_RATIO" 'BEGIN { exit !(r > m) }' && { echo "  regression: above ${MAX_RATIO}x"; status=1; }
done
exit $status
