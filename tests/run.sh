#!/usr/bin/env bash
# Capstan test suite.
#   tests/reject/   programs that must NOT compile; first line names the expected diagnostic
#   tests/runtime/  programs that compile but must stop safely with the named CWE
#   tests/accept/   programs that must compile and print exactly the .out file
#   examples/       must pass their own tests and a --release check
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
C="$ROOT/build/capstanc"
CC="${CC:-cc}"
CFLAGS="-O2 -std=gnu11 -w -I$ROOT/runtime"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  pass  %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s: %s\n' "$1" "$2"; }

echo "== must be rejected at compile time"
for f in "$ROOT"/tests/reject/*.cap; do
  n="reject/$(basename "$f")"
  want="$(sed -n 's|^// expect: ||p' "$f" | head -1)"
  flags="$(sed -n 's|^// flags: ||p' "$f" | head -1)"
  out="$("$C" build -o "$tmp/x.c" $flags "$f" 2>&1)"; code=$?
  if [[ $code -eq 0 ]]; then bad "$n" "compiled, expected $want"
  elif grep -qF -- "$want" <<<"$out"; then ok "$n  ($want)"
  else bad "$n" "expected $want, got: $(head -1 <<<"$out")"; fi
done

echo "== must stop safely at run time"
for f in "$ROOT"/tests/runtime/*.cap; do
  n="runtime/$(basename "$f")"
  want="$(sed -n 's|^// expect-runtime: ||p' "$f" | head -1)"
  if ! "$C" build -o "$tmp/r.c" "$f" >"$tmp/log" 2>&1; then bad "$n" "did not compile: $(head -1 "$tmp/log")"; continue; fi
  "$CC" $CFLAGS "$tmp/r.c" -o "$tmp/r" || { bad "$n" "C compile failed"; continue; }
  err="$("$tmp/r" 2>&1 >/dev/null)"; code=$?
  if [[ $code -eq 101 ]] && grep -qF -- "$want" <<<"$err"; then ok "$n  ($want)"
  else bad "$n" "exit $code, stderr: $err"; fi
done

echo "== must compile and produce the expected output"
for f in "$ROOT"/tests/accept/*.cap; do
  n="accept/$(basename "$f")"
  if ! "$C" build -o "$tmp/a.c" "$f" >"$tmp/log" 2>&1; then bad "$n" "$(head -3 "$tmp/log")"; continue; fi
  "$CC" $CFLAGS "$tmp/a.c" -o "$tmp/a" || { bad "$n" "C compile failed"; continue; }
  if diff -u "${f%.cap}.out" <("$tmp/a") >"$tmp/diff"; then ok "$n"; else bad "$n" "output differs"; cat "$tmp/diff"; fi
done

echo "== examples"
for f in "$ROOT"/examples/*.cap; do
  n="examples/$(basename "$f")"
  if "$C" check --release "$f" >"$tmp/log" 2>&1 && "$C" test -o "$tmp/t.c" "$f" >>"$tmp/log" 2>&1 \
     && "$CC" $CFLAGS "$tmp/t.c" -o "$tmp/t" && "$tmp/t" >>"$tmp/log" 2>&1; then ok "$n (release check + tests)"
  else bad "$n" "$(tail -3 "$tmp/log")"; fi
done

echo "== self-hosting fixpoint"
SRC=$(ls "$ROOT"/compiler/{ast,lexer,parser,checker,codegen,main}.cap)
if "$C" build -o "$tmp/self.c" $SRC && "$CC" $CFLAGS "$tmp/self.c" -o "$tmp/self" \
   && "$tmp/self" build -o "$tmp/self2.c" $SRC && cmp -s "$tmp/self.c" "$tmp/self2.c"; then ok "compiler reproduces itself"
else bad "fixpoint" "self-compilation differs"; fi
"$C" check --strict $SRC >"$tmp/log" 2>&1 && ok "compiler passes its own --strict checks" || bad "strict" "$(head -3 "$tmp/log")"

echo
echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]
