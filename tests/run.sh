#!/usr/bin/env bash
# Capstan test suite.
#
#   tests/run.sh          standard run (a few minutes)
#   tests/run.sh --full   adds long fuzzing campaigns and the benchmark gate
#
# Sections:
#   unit         runtime unit tests (published crypto vectors, collections, validators, GC)
#   reject       vulnerable programs that must not compile, each with its CWE
#   diagnostics  ordinary errors with their exact messages
#   runtime      programs that must stop safely with the named CWE
#   conformance  programs with expected output, checked three ways:
#                exact output, agreement with the independent stage-0 implementation,
#                and warning-free generated C (-Wall -Wextra -Werror)
#   gc           bounded memory under churn, integrity when collecting on every allocation
#   limits       pathological input (deep nesting) gives diagnostics, not crashes
#   cwe atlas    an attempt to write every code-level CWE in Capstan, with its verdict
#   fuzz         differential fuzzing (random programs) and mutation fuzzing (corrupted programs)
#   sanitizers   compiler and programs under AddressSanitizer + UndefinedBehaviorSanitizer
#   bootstrap    self-hosting fixpoint, the compiler's own --strict check, alternate C compiler
#   examples     example programs pass --release checks and their own tests
#   bench        (--full) speed against hand-written C, with a regression limit
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
C="$ROOT/build/capstanc"
CC="${CC:-cc}"
FULL=0; [[ "${1:-}" == "--full" ]] && FULL=1
CFLAGS="-O2 -std=gnu11 -w -I$ROOT/runtime"
WFLAGS="-O2 -std=gnu11 -Wall -Wextra -Werror -Wno-unused-function -Wno-unused-parameter -Wno-unused-variable -Wno-unused-but-set-variable -I$ROOT/runtime"
[[ "$($CC --version 2>&1)" == *clang* ]] && WFLAGS="$WFLAGS -Wno-parentheses-equality -Wno-gnu-statement-expression -Wno-gnu-auto-type"
SAN="-O1 -g -std=gnu11 -w -fsanitize=address,undefined -fno-sanitize-recover=all -I$ROOT/runtime"
export ASAN_OPTIONS=detect_leaks=0:detect_stack_use_after_return=0
PY="python3 -I"
SRC=$(ls "$ROOT"/compiler/{ast,lexer,parser,checker,codegen,main}.cap)
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  pass  %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s: %s\n' "$1" "$2"; }
section() { echo; echo "== $1"; }

[[ -x "$C" ]] || make -s -C "$ROOT" bootstrap

section "unit"
if "$CC" $CFLAGS "$ROOT/tests/unit/test_runtime.c" -o "$tmp/unit" && out="$("$tmp/unit")"; then ok "$out"; else bad "runtime unit tests" "$out"; fi
if out="$($PY "$ROOT/tests/unit/escape_roundtrip.py" 2>&1)"; then ok "$out"; else bad "escape round trip" "$out"; fi

expect_reject() {   # dir label
  for f in "$ROOT"/tests/$1/*.cap; do
    local n="$1/$(basename "$f")" want flags out code
    want="$(sed -n 's|^// expect: ||p' "$f" | head -1)"
    flags="$(sed -n 's|^// flags: ||p' "$f" | head -1)"
    out="$("$C" build -o "$tmp/x.c" $flags "$f" 2>&1)"; code=$?
    if [[ $code -eq 0 ]]; then bad "$n" "compiled, expected: $want"
    elif [[ $code -ne 1 ]]; then bad "$n" "compiler exited $code"
    elif grep -qF -- "$want" <<<"$out"; then ok "$n  ($want)"
    else bad "$n" "expected '$want', got: $(head -1 <<<"$out")"; fi
  done
}
section "reject: vulnerabilities rejected at compile time"; expect_reject reject
section "diagnostics: ordinary errors"; expect_reject diagnostics

section "runtime: safe stops"
for f in "$ROOT"/tests/runtime/*.cap; do
  n="runtime/$(basename "$f")"
  want="$(sed -n 's|^// expect-runtime: ||p' "$f" | head -1)"
  if ! "$C" build -o "$tmp/r.c" "$f" >"$tmp/log" 2>&1; then bad "$n" "did not compile: $(head -1 "$tmp/log")"; continue; fi
  "$CC" $CFLAGS "$tmp/r.c" -o "$tmp/r" || { bad "$n" "C compile failed"; continue; }
  err="$("$tmp/r" 2>&1 >/dev/null)"; code=$?
  if [[ $code -eq 101 ]] && grep -qF -- "$want" <<<"$err"; then ok "$n  ($want)"; else bad "$n" "exit $code: $err"; fi
done

section "conformance: output, stage-0 agreement, warning-free C"
for f in "$ROOT"/tests/accept/*.cap "$ROOT"/tests/gc/*.cap; do
  n="${f#$ROOT/tests/}"
  if ! "$C" build -o "$tmp/a.c" "$f" >"$tmp/log" 2>&1; then bad "$n" "$(head -3 "$tmp/log")"; continue; fi
  if ! "$CC" $WFLAGS "$tmp/a.c" -o "$tmp/a" 2>"$tmp/cc"; then bad "$n" "generated C has warnings: $(head -3 "$tmp/cc")"; continue; fi
  "$tmp/a" >"$tmp/native" 2>/dev/null
  if ! diff -u "${f%.cap}.out" "$tmp/native" >"$tmp/diff"; then bad "$n" "output differs"; cat "$tmp/diff"; continue; fi
  $PY "$ROOT/bootstrap/capstan0.py" "$tmp/s0.py" "$f" && $PY "$tmp/s0.py" >"$tmp/s0" 2>/dev/null
  if [[ "$n" == accept/untrusted.cap ]] || cmp -s "$tmp/native" "$tmp/s0"; then ok "$n"; else bad "$n" "stage 0 disagrees"; diff "$tmp/native" "$tmp/s0" | head; fi
done

section "gc"
"$C" build -o "$tmp/churn.c" "$ROOT/tests/gc/churn.cap" >/dev/null && "$CC" $CFLAGS "$tmp/churn.c" -o "$tmp/churn"
stats="$(CAPSTAN_GC_STATS=1 "$tmp/churn" 2>&1 >/dev/null)"
peak=$(sed -n 's/.*peak_heap=\([0-9]*\).*/\1/p' <<<"$stats"); total=$(sed -n 's/.*total_allocated=\([0-9]*\).*/\1/p' <<<"$stats")
if [[ -n "$peak" ]] && (( peak < 64 * 1024 * 1024 && total > 500 * 1024 * 1024 )); then ok "churn: $((total/1048576)) MB allocated, peak heap $((peak/1048576)) MB"
else bad "churn" "$stats"; fi
"$C" build -o "$tmp/integ.c" "$ROOT/tests/gc/integrity.cap" >/dev/null && "$CC" $CFLAGS "$tmp/integ.c" -o "$tmp/integ"
if CAPSTAN_GC_STRESS=1 "$tmp/integ" | diff -q - "$ROOT/tests/gc/integrity.out" >/dev/null; then ok "integrity with a collection on every allocation"; else bad "integrity" "values changed under GC stress"; fi
if CAPSTAN_GC_STRESS=1000 "$C" build -o "$tmp/gcself.c" $SRC && "$C" build -o "$tmp/self.c" $SRC && cmp -s "$tmp/gcself.c" "$tmp/self.c"; then ok "compiler output identical under GC stress"; else bad "gc self-compile" "output differs"; fi

section "limits"
$PY -c "n=100000; open('$tmp/deep.cap','w').write('int main() { return ' + '('*n + '1' + ')'*n + '; }\n')"
$PY -c "n=100000; open('$tmp/blocks.cap','w').write('int main() { ' + 'if (true) { '*n + '}'*n + ' return 0; }\n')"
$PY -c "open('$tmp/long.cap','w').write('int main() { return ' + ' + '.join(['1']*50000) + '; }\n')"
for t in deep blocks long; do
  out="$("$C" check "$tmp/$t.cap" 2>&1)"; code=$?
  if [[ $code -eq 1 ]] && grep -q "CWE-674" <<<"$out"; then ok "$t nesting gives a diagnostic"; else bad "$t nesting" "exit $code"; fi
done
$PY -c "open('$tmp/wide.cap','w').write('int main() {\n' + ''.join('    int _v%d = %d;\n' % (i, i) for i in range(20000)) + '    return _v19999 - 19999;\n}\n')"
if "$C" build -o "$tmp/wide.c" "$tmp/wide.cap" && "$CC" -O0 -std=gnu11 -w -I"$ROOT/runtime" "$tmp/wide.c" -o "$tmp/wide" && "$tmp/wide"; then ok "20,000-statement function"; else bad "wide" "failed"; fi

section "cwe atlas: red-team attempt for every code-level CWE"
if out="$($PY "$ROOT/tests/cwe/atlas.py" 2>&1)"; then ok "$(tail -1 <<<"$out")"; else bad "cwe atlas" "$out"; fi

section "fuzz"
DIFF_N=60; MUT_N=3000; (( FULL )) && { DIFF_N=1000; MUT_N=50000; }
if out="$($PY "$ROOT/tests/fuzz/gen.py" $DIFF_N "${FUZZ_SEED:-$RANDOM}" 2>&1)"; then ok "$out"; else bad "differential fuzz" "$out"; fi
if out="$($PY "$ROOT/tests/fuzz/mutate.py" $MUT_N "${FUZZ_SEED:-$RANDOM}" 2>&1)"; then ok "$out"; else bad "mutation fuzz" "$out"; fi

section "sanitizers"
"$C" build -o "$tmp/ref.c" $SRC    # reference output for this checkout's paths
if "$CC" $SAN "$ROOT/build/stage3.c" -o "$tmp/san" 2>/dev/null; then
  if CAPSTAN_GC_STRESS=3000 "$tmp/san" build -o "$tmp/san.c" $SRC && cmp -s "$tmp/san.c" "$tmp/ref.c"; then ok "compiler under ASan+UBSan (with GC stress) reproduces itself"; else bad "sanitized compiler" "failed"; fi
  "$CC" $SAN "$ROOT/tests/unit/test_runtime.c" -o "$tmp/unit_san" && "$tmp/unit_san" >/dev/null && ok "runtime unit tests under ASan+UBSan" || bad "unit sanitized" "failed"
  sanfail=0
  for f in "$ROOT"/tests/accept/*.cap "$ROOT"/examples/*.cap "$ROOT"/tests/gc/integrity.cap; do
    "$C" build -o "$tmp/s.c" "$f" >/dev/null 2>&1 && "$CC" $SAN "$tmp/s.c" -o "$tmp/s" && CAPSTAN_GC_STRESS=50 "$tmp/s" >/dev/null 2>"$tmp/serr" || { sanfail=1; bad "sanitized $(basename "$f")" "$(tail -3 "$tmp/serr")"; }
  done
  (( sanfail )) || ok "all conformance programs and examples clean under ASan+UBSan with GC stress"
else
  echo "  skip  sanitizers not available for $CC"
fi

section "bootstrap"
if "$C" build -o "$tmp/self.c" $SRC && "$CC" $CFLAGS "$tmp/self.c" -o "$tmp/self" && "$tmp/self" build -o "$tmp/self2.c" $SRC && cmp -s "$tmp/self.c" "$tmp/self2.c"; then ok "compiler reproduces itself byte for byte"; else bad "fixpoint" "self-compilation differs"; fi
if "$C" check --strict --release $SRC >"$tmp/log" 2>&1; then ok "compiler passes its own --strict --release checks"; else bad "strict" "$(head -3 "$tmp/log")"; fi
if "$CC" $WFLAGS "$ROOT/build/stage3.c" -o "$tmp/werror" 2>"$tmp/cc"; then ok "compiler's generated C is warning-free"; else bad "compiler -Werror" "$(head -3 "$tmp/cc")"; fi
for alt in clang gcc; do
  command -v $alt >/dev/null && [[ "$($alt --version 2>&1)" != "$($CC --version 2>&1)" ]] || continue
  if $alt $CFLAGS "$ROOT/build/stage3.c" -o "$tmp/alt" && "$tmp/alt" build -o "$tmp/alt.c" $SRC && cmp -s "$tmp/alt.c" "$tmp/ref.c"; then ok "compiler built with $alt reproduces itself"; else bad "$alt" "differs"; fi
done
rm -f "$tmp/s0.py"; $PY "$ROOT/bootstrap/capstan0.py" "$tmp/s1.py" $SRC && $PY "$tmp/s1.py" build -o "$tmp/s1.c" $SRC && cmp -s "$tmp/s1.c" "$tmp/ref.c" \
  && ok "stage 0 still bootstraps to the identical compiler" || bad "stage 0 bootstrap" "differs"

section "examples"
for f in "$ROOT"/examples/*.cap; do
  n="examples/$(basename "$f")"
  if "$C" check --release "$f" >"$tmp/log" 2>&1 && "$C" test -o "$tmp/t.c" "$f" >>"$tmp/log" 2>&1 \
     && "$CC" $CFLAGS "$tmp/t.c" -o "$tmp/t" && "$tmp/t" >>"$tmp/log" 2>&1; then ok "$n (release check + its tests)"
  else bad "$n" "$(tail -3 "$tmp/log")"; fi
done
cat > "$tmp/failing.cap" <<'CAP'
test "passes" { assert(1 + 1 == 2); }
test "fails" { assert(1 + 1 == 3); }
test "still runs after a failure" { assert(true); }
CAP
"$C" test -o "$tmp/f.c" "$tmp/failing.cap" >/dev/null && "$CC" $CFLAGS "$tmp/f.c" -o "$tmp/f"
out="$("$tmp/f" 2>/dev/null)"; code=$?
if [[ $code -eq 1 ]] && grep -q "FAIL  fails" <<<"$out" && grep -q "pass  still runs" <<<"$out" && grep -q "3 test(s), 1 failed" <<<"$out"; then ok "test runner reports failures and keeps going"
else bad "test runner" "exit $code: $out"; fi

if (( FULL )); then
  section "bench"
  if out="$("$ROOT/bench/run.sh" 2>&1)"; then ok "benchmarks within limit"; echo "$out" | sed 's/^/        /'; else bad "bench" "$out"; fi
fi

echo
echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]
