#!/usr/bin/env bash
# Capstan test suite.
#
#   tests/run.sh          standard run (a few minutes)
#   tests/run.sh --full   adds long fuzzing campaigns and the benchmark gate
#
# Sections:
#   spec         every area of docs/SPEC.md is covered by tagged tests
#   unit         runtime unit tests (published crypto vectors, collections, validators, GC)
#   reject       vulnerable programs that must not compile, each with its CWE
#   diagnostics  ordinary errors with their exact messages
#   recovery     every independent syntax error in a file is reported in one run
#   runtime      programs that must stop safely with the named CWE
#   ranges       checks the range analysis proves unnecessary: exact counts, and the same
#                output with --keep-checks
#   conformance  programs with expected output, checked three ways:
#                exact output, agreement with the independent stage-0 implementation,
#                and warning-free generated C (-Wall -Wextra -Werror)
#   portability  every conformance program and safety stop at -O0, -O2 and -O3, with each
#                C compiler available, behaves identically
#   crypto       lib/crypto.cap (SHA-256, HMAC, PBKDF2 in Capstan) against hashlib, the
#                published vectors and the runtime's C implementation, native and stage 0
#   gc           bounded memory under churn, integrity when collecting on every allocation
#   limits       pathological input (deep nesting) gives diagnostics, not crashes
#   cwe atlas    an attempt to write every code-level CWE in Capstan, with its verdict
#   fuzz         differential fuzzing (random programs) and mutation fuzzing (corrupted programs)
#   sanitizers   compiler and programs under AddressSanitizer + UndefinedBehaviorSanitizer
#   bootstrap    self-hosting fixpoint, the compiler's own --strict check, alternate C compiler
#   examples     example programs pass --release checks and their own tests
#   fmt          the formatter: expected layout, idempotence, house style, whitespace and corruption fuzzing
#   supply chain SBOM generation, the reproducibility report, the release verifier against good
#                and tampered releases, and the workflow hardening rules (tests/supply/)
#   lsp          the language server: the compiler's exact diagnostics for every test program, the
#                protocol and its errors, sanitizers, and fuzzing of JSON and framing
#   coverage     (--full) line coverage of compiler, formatter and runtime, with floors
#   mutation     (--full) injected compiler bugs must be caught by the suite
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
SRC=$(ls "$ROOT"/compiler/{ast,lexer,parser,checker,ranges,codegen,main}.cap)
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  pass  %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s: %s\n' "$1" "$2"; }
section() { echo; echo "== $1"; }

[[ -x "$C" ]] || make -s -C "$ROOT" bootstrap

section "agent instructions: AGENTS.md (Codex) and CLAUDE.md (Claude) are identical"
if cmp -s "$ROOT/AGENTS.md" "$ROOT/CLAUDE.md"; then ok "AGENTS.md and CLAUDE.md match"; else bad "AGENTS.md and CLAUDE.md differ; change both together" "$(diff "$ROOT/AGENTS.md" "$ROOT/CLAUDE.md" | head -20)"; fi

section "K0: complete CVE population, race patterns and kernel-specific memory projections"
if out="$($PY "$ROOT/tests/k0/check.py" 2>&1)"; then ok "$out"; else bad "K0 study checks" "$out"; fi

section "spec coverage: every language area has tests"
if out="$($PY "$ROOT/tests/spec_coverage.py" 2>&1)"; then ok "$(tail -1 <<<"$out")"; else bad "spec coverage" "$out"; fi

section "Capstan-native verification: CCAM arithmetic, typed registers and single-frame evaluator"
if out="$( "$ROOT/bin/capstan" test "$ROOT/verification/ccam_core.cap" 2>&1)"; then
  ok "CCAM checked arithmetic, typed registers and single-frame evaluator tests"
else
  bad "CCAM Capstan arithmetic, register validation and evaluator" "$out"
fi

section "Capstan-native verification: CCAM multi-function calls and frames"
if out="$( "$ROOT/bin/capstan" test "$ROOT/verification/ccam_calls.cap" 2>&1)"; then
  ok "CCAM function validation, argument transfer, call depth and atomic returns"
else
  bad "CCAM multi-function evaluator" "$out"
fi

section "Capstan-native verification: bounded concurrency reference machine"
if out="$( "$ROOT/bin/capstan" test "$ROOT/verification/concurrency_model.cap" 2>&1)"; then
  ok "bounded task/channel transitions, ownership, cancellation, scope and resource invariants"
else
  bad "bounded concurrency reference machine" "$out"
fi

section "Capstan-native verification: Halyard single-owner resource admission"
if out="$( "$ROOT/bin/capstan" test "$ROOT/verification/halyard_resource_actor.cap" 2>&1)"; then
  ok "bounded FIFO admission, serial resource accounting, failure atomicity and one-shot release"
else
  bad "Halyard resource actor model" "$out"
fi

section "Capstan-native verification: finite protocol automata"
if out="$( "$ROOT/bin/capstan" test "$ROOT/verification/protocol_automata.cap" 2>&1)"; then
  ok "finite protocol validation, deterministic transitions, reachability and acyclicity"
else
  bad "finite protocol automata" "$out"
fi

section "Capstan-native verification: concurrency protocol refinement"
if out="$( "$ROOT/bin/capstan" test "$ROOT/verification/concurrency_protocol_refinement.cap" 2>&1)"; then
  ok "normal task/channel message transitions refine protocol ownership and resource contracts"
else
  bad "concurrency protocol refinement" "$out"
fi

section "Capstan-native verification: checked source to CCAM lowering"
if out="$( "$ROOT/bin/capstan" test "$ROOT/compiler/ast.cap" "$ROOT/compiler/lexer.cap" "$ROOT/compiler/parser.cap" "$ROOT/compiler/checker.cap" "$ROOT/verification/ccam_lowering.cap" 2>&1)"; then
  ok "checked scalar source lowers to validated CCAM and executes in the Capstan evaluator"
else
  bad "CCAM source-to-IR lowering" "$out"
fi

section "Capstan-native verification: freestanding Linux x86-64 native backend"
if out="$( "$ROOT/bin/capstan" test "$ROOT/compiler/ast.cap" "$ROOT/compiler/lexer.cap" "$ROOT/compiler/parser.cap" "$ROOT/compiler/checker.cap" "$ROOT/verification/ccam_native_x64.cap" 2>&1)"; then
  ok "CCAM emits freestanding x86-64 assembly without C runtime references"
  if [[ "$(uname -s)" == "Linux" && "$(uname -m)" == "x86_64" ]]; then
    native_run() {
      local name="$1" expected="$2"
      if as --64 "$ROOT/build/$name.s" -o "$tmp/$name.o" &&
         ld -o "$tmp/$name" "$tmp/$name.o"; then
        if readelf -l "$tmp/$name" | grep -q "INTERP"; then
          bad "freestanding $name runtime audit" "ELF unexpectedly has an interpreter"
        elif [[ -n "$(nm -u "$tmp/$name")" ]]; then
          bad "freestanding $name runtime audit" "ELF has undefined external symbols"
        else
          "$tmp/$name"
          local status=$?
          if [[ $status -eq $expected ]]; then
            ok "freestanding $name exits $expected with no interpreter or undefined symbols"
          else
            bad "freestanding $name exit status" "expected $expected, got $status"
          fi
        fi
      else
        bad "freestanding $name assembly/link" "GNU as or ld rejected generated assembly"
      fi
    }
    native_run ccam-native-x64 42
    native_run ccam-native-x64-loop 42
    native_run ccam-native-x64-recursion 42
    native_run ccam-native-x64-overflow 70
    native_run ccam-native-x64-divzero 71
    native_run ccam-native-x64-div-overflow 70
    native_run ccam-native-x64-rem-min 0
    native_run ccam-native-x64-step-limit 73
    native_run ccam-native-x64-depth-limit 74
    native_run ccam-native-x64-uninitialised 75
  else
    ok "Linux x86-64 execution test skipped on non-Linux/non-x86-64 host"
  fi
else
  bad "CCAM native x86-64 backend" "$out"
fi

section "unit"
for opt in 0 2 3; do
  if "$CC" "-O$opt" -std=gnu11 -w -I"$ROOT/runtime" "$ROOT/tests/unit/test_runtime.c" -o "$tmp/unit_o$opt" &&
      out="$("$tmp/unit_o$opt")"; then
    ok "runtime unit tests at -O$opt ($out)"
  else
    bad "runtime unit tests at -O$opt" "$out"
  fi
done
if out="$($PY "$ROOT/tests/unit/escape_roundtrip.py" 2>&1)"; then ok "$out"; else bad "escape round trip" "$out"; fi
if out="$($PY "$ROOT/tests/unit/ranges_props.py" 2>&1)"; then ok "$out"; else bad "range properties" "$out"; fi
if out="$($PY "$ROOT/tests/unit/codegen_literal_order.py" "$C" "$tmp" 2>&1)"; then ok "$out"; else bad "literal operand sequencing" "$out"; fi
if out="$($PY "$ROOT/tests/unit/escape_log_agree.py" 2>&1)"; then ok "$out"; else bad "escape_log agreement" "$out"; fi
if out="$($PY "$ROOT/tests/unit/siphash_agree.py" 2>&1)"; then ok "$out"; else bad "siphash" "$out"; fi
if out="$($PY "$ROOT/tests/unit/escape_json_agree.py" 2>&1)"; then ok "$out"; else bad "escape_json agreement" "$out"; fi
if out="$($PY "$ROOT/tests/unit/lint_table.py" 2>&1)"; then ok "$out"; else bad "lint table" "$out"; fi
if out="$($PY "$ROOT/tests/unit/grant_reference.py" 2>&1)"; then ok "$out"; else bad "grant reference semantics" "$out"; fi
if out="$($PY "$ROOT/tests/unit/assurance_freshness.py" 2>&1)"; then ok "$out"; else bad "assurance evidence freshness" "$out"; fi

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

section "recovery: every independent syntax error reported in one run"
for f in "$ROOT"/tests/recovery/*.cap; do
  n="recovery/$(basename "$f")"
  sed -n 's|^// error: ||p' "$f" >"$tmp/want"
  out="$("$C" check "$f" 2>&1)"; code=$?
  grep -o '^[^ ]*:[0-9]*:[0-9]*: error: .*' <<<"$out" | sed 's|^.*\.cap:||; s|error: ||' >"$tmp/got"
  if [[ $code -ne 1 ]]; then bad "$n" "compiler exited $code"
  elif diff -q "$tmp/want" "$tmp/got" >/dev/null; then ok "$n  ($(wc -l <"$tmp/want" | tr -d ' ') errors)"
  else bad "$n" "errors differ: $(diff "$tmp/want" "$tmp/got" | head -3 | tr '\n' ' ')"; fi
done
# A file with very many errors stops after 50 syntax errors (bounded output, CWE-400).
for i in $(seq 1 80); do echo "int f$i() { return ; ; }"; done | sed 's/return ;/return +;/' >"$tmp/many.cap"
got=$("$C" check "$tmp/many.cap" 2>&1 | grep -c ': error: ')
if [[ $got -eq 50 ]]; then ok "recovery: 80 broken functions give exactly 50 errors"; else bad "recovery: error limit" "got $got errors"; fi
{ echo "int main() {"; for i in $(seq 1 80); do echo "  int x$i = +;"; done; echo "  return 0;"; echo "}"; } >"$tmp/many2.cap"
got=$("$C" check "$tmp/many2.cap" 2>&1 | grep -c ': error: ')
if [[ $got -eq 50 ]]; then ok "recovery: 80 broken statements in one block give exactly 50 errors"; else bad "recovery: error limit in a block" "got $got errors"; fi
{ echo "int main() { return"; for i in $(seq 1 1100); do printf '('; done; echo " 1; }"; echo "int f() { return +; }"; } >"$tmp/deep.cap"
got=$("$C" check "$tmp/deep.cap" 2>&1 | grep -c ': error: ')
if [[ $got -eq 1 ]]; then ok "recovery: too-deep nesting stops parsing with one error"; else bad "recovery: nesting is fatal" "got $got errors"; fi

section "runtime: safe stops (generated C warning-free; these programs recurse or loop on purpose)"
for f in "$ROOT"/tests/runtime/*.cap; do
  n="runtime/$(basename "$f")"
  want="$(sed -n 's|^// expect-runtime: ||p' "$f" | head -1)"
  envs="$(sed -n 's|^// env: ||p' "$f" | head -1)"
  if ! "$C" build -o "$tmp/r.c" "$f" >"$tmp/log" 2>&1; then bad "$n" "did not compile: $(head -1 "$tmp/log")"; continue; fi
  "$CC" $WFLAGS -Wno-infinite-recursion -Wno-for-loop-analysis "$tmp/r.c" -o "$tmp/r" 2>"$tmp/cc" || { bad "$n" "generated C has warnings or does not compile: $(head -2 "$tmp/cc")"; continue; }
  err="$(env $envs "$tmp/r" 2>&1 >/dev/null)"; code=$?
  if [[ $code -eq 101 ]] && grep -qF -- "$want" <<<"$err"; then ok "$n  ($want)"; else bad "$n" "exit $code: $err"; fi
done

section "ranges: run-time checks proved unnecessary"
for f in $(grep -l '^// expect-proved: ' "$ROOT"/tests/*/*.cap); do
  n="${f#$ROOT/tests/}"; want="$(sed -n 's|^// expect-proved: ||p' "$f" | head -1)"
  "$C" build -o "$tmp/rg.c" "$f" >/dev/null 2>&1 && "$C" build --keep-checks -o "$tmp/rk.c" "$f" >/dev/null 2>&1 || { bad "$n" "did not compile"; continue; }
  got=$(grep -o 'cap_[a-z_]*_proved(' "$tmp/rg.c" | wc -l | tr -d ' '); kept=$(grep -o 'cap_[a-z_]*_proved(' "$tmp/rk.c" | wc -l | tr -d ' ')
  "$CC" $CFLAGS "$tmp/rg.c" -o "$tmp/rg" && "$CC" $CFLAGS "$tmp/rk.c" -o "$tmp/rk"
  if [[ "$got" == "$want" && "$kept" == 0 ]] && cmp -s <("$tmp/rg" 2>&1; echo "exit $?") <("$tmp/rk" 2>&1; echo "exit $?"); then ok "$n  ($got checks proved; same result with --keep-checks)"
  else bad "$n" "proved $got, expected $want; --keep-checks still proved $kept"; fi
done
"$C" build -o "$tmp/self_rg.c" $SRC && proved=$(grep -o 'cap_[a-z_]*_proved(' "$tmp/self_rg.c" | wc -l | tr -d ' ')
total=$(grep -oE 'cap_(add|sub|mul|div|mod|neg|list_get|list_set|blist_get|blist_set|str_at)(_proved)?\(' "$tmp/self_rg.c" | wc -l | tr -d ' ')
ok "the compiler's own code: $proved of $total checks proved unnecessary"

section "conformance: output, stage-0 agreement, warning-free C"
for f in "$ROOT"/tests/accept/*.cap "$ROOT"/tests/gc/*.cap; do
  n="${f#$ROOT/tests/}"
  aflags="$(sed -n 's|^// flags: ||p' "$f" | head -1)"
  if ! "$C" build -o "$tmp/a.c" $aflags "$f" >"$tmp/log" 2>&1; then bad "$n" "$(head -3 "$tmp/log")"; continue; fi
  if ! "$CC" $WFLAGS "$tmp/a.c" -o "$tmp/a" 2>"$tmp/cc"; then bad "$n" "generated C has warnings: $(head -3 "$tmp/cc")"; continue; fi
  "$tmp/a" >"$tmp/native" 2>/dev/null
  if ! diff -u "${f%.cap}.out" "$tmp/native" >"$tmp/diff"; then bad "$n" "output differs"; cat "$tmp/diff"; continue; fi
  $PY "$ROOT/bootstrap/capstan0.py" "$tmp/s0.py" "$f" && $PY "$tmp/s0.py" >"$tmp/s0" 2>/dev/null
  if [[ "$n" == accept/untrusted.cap ]] || cmp -s "$tmp/native" "$tmp/s0"; then ok "$n"; else bad "$n" "stage 0 disagrees"; diff "$tmp/native" "$tmp/s0" | head; fi
done

section "portability: optimisation levels and C compilers"
COMPILERS="$CC"; for alt in gcc clang; do command -v $alt >/dev/null && [[ "$(readlink -f "$(command -v $alt)")" != "$(readlink -f "$(command -v $CC)")" ]] && COMPILERS="$COMPILERS $alt"; done
pfail=0; pn=0
for f in "$ROOT"/tests/accept/*.cap "$ROOT"/tests/gc/integrity.cap "$ROOT"/tests/runtime/*.cap; do
  "$C" build -o "$tmp/p.c" "$f" >/dev/null 2>&1 || continue
  envs="$(sed -n 's|^// env: ||p' "$f" | head -1)"; ref=""
  for cc in $COMPILERS; do for o in -O0 -O2 -O3; do
    if ! $cc $o -std=gnu11 -w -I"$ROOT/runtime" "$tmp/p.c" -o "$tmp/p" 2>/dev/null; then bad "${f#$ROOT/tests/}" "$cc $o: C compile failed"; pfail=1; continue; fi
    got="$(env $envs "$tmp/p" 2>&1; echo "exit $?")"
    if [[ -z "$ref" ]]; then ref="$got"; elif [[ "$got" != "$ref" ]]; then bad "${f#$ROOT/tests/}" "$cc $o behaves differently"; pfail=1; fi
  done; done
  pn=$((pn+1))
done
(( pfail )) || ok "$pn programs behave identically at -O0, -O2 and -O3 with: $COMPILERS"

section "io: standard input and files, native and stage 0"
for f in "$ROOT"/tests/io/*.cap; do
  n="io/$(basename "$f")"; in="${f%.cap}.in"; d1="$(mktemp -d)"; d2="$(mktemp -d)"
  if ! "$C" build -o "$tmp/io.c" "$f" >"$tmp/log" 2>&1 || ! "$CC" $WFLAGS "$tmp/io.c" -o "$tmp/io" 2>>"$tmp/log"; then bad "$n" "$(head -3 "$tmp/log")"; continue; fi
  "$tmp/io" "$d1" <"$in" >"$tmp/io.native" 2>&1; c1=$?
  $PY "$ROOT/bootstrap/capstan0.py" "$tmp/io0.py" "$f" && $PY "$tmp/io0.py" "$d2" <"$in" >"$tmp/io.s0" 2>&1; c2=$?
  if [[ $c1 -ne 0 ]] || ! diff -u "${f%.cap}.out" "$tmp/io.native" >"$tmp/diff"; then bad "$n" "exit $c1"; cat "$tmp/diff"
  elif [[ $c2 -ne 0 ]] || ! cmp -s "$tmp/io.native" "$tmp/io.s0"; then bad "$n" "stage 0 disagrees"; diff "$tmp/io.native" "$tmp/io.s0" | head
  else ok "$n (expected output; stage 0 agrees)"; fi
  rm -rf "$d1" "$d2"
done
if out="$($PY "$ROOT/tests/unit/stdio_interactive.py" "$C" "$CC" $WFLAGS 2>&1)"; then ok "$out"; else bad "io: conversation over a pipe" "$out"; fi
if out="$($PY "$ROOT/tests/unit/read_file_bounds.py" "$C" "$CC" $WFLAGS 2>&1)"; then ok "$out"; else bad "io: read_file bounds" "$out"; fi
if out="$($PY "$ROOT/tests/unit/read_line_eof.py" "$C" "$CC" $WFLAGS 2>&1)"; then ok "$out"; else bad "io: read_line exact-limit EOF" "$out"; fi

section "crypto: lib/crypto.cap against hashlib, the published vectors and the runtime"
if out="$($PY "$ROOT/tests/crypto/check.py" "$C" "$CC" $WFLAGS 2>&1)"; then ok "$out"; else bad "crypto" "$out"; fi

section "shroud: the GUI library against exact areas, fontTools, Python's UTF-8 decoder, zlib and golden frames"
if out="$($PY "$ROOT/tests/shroud/check.py" "$C" "$CC" $WFLAGS 2>&1)"; then
  ok "$(head -1 <<<"$out")"; tail -n +2 <<<"$out" | sed 's/^/      /'
else bad "shroud" "$out"; fi
if out="$($PY "$ROOT/tests/shroud/check_frame_budget.py" "$C" "$CC" $WFLAGS 2>&1)"; then ok "$out"; else bad "shroud frame text budget" "$out"; fi
if out="$($PY "$ROOT/tests/shroud/check_frame_line_budget.py" "$C" "$CC" $WFLAGS 2>&1)"; then ok "$out"; else bad "shroud frame line budget" "$out"; fi
printf 'int main(void) { return 0; }\n' > "$tmp/san.c"
if "$CC" $SAN "$tmp/san.c" -o "$tmp/san" 2>/dev/null; then
  if out="$($PY "$ROOT/tests/shroud/check.py" "$C" "$CC" $SAN 2>&1)"; then ok "shroud under ASan+UBSan, damaged fonts included: no reports"; else bad "shroud (sanitizers)" "$out"; fi
  if out="$($PY "$ROOT/tests/shroud/check_frame_budget.py" "$C" "$CC" $SAN 2>&1)"; then ok "shroud frame text budget under ASan+UBSan: $out"; else bad "shroud frame text budget (sanitizers)" "$out"; fi
  if out="$($PY "$ROOT/tests/shroud/check_frame_line_budget.py" "$C" "$CC" $SAN 2>&1)"; then ok "shroud frame line budget under ASan+UBSan: $out"; else bad "shroud frame line budget (sanitizers)" "$out"; fi
else
  echo "  skip  sanitizers not available for $CC"
fi


section "halyard: Capstan-native Media Core, Shanty and Deadeye"
for media_file in "$ROOT/lib/halyard/core.cap" "$ROOT/lib/halyard/shanty.cap" "$ROOT/lib/halyard/deadeye.cap"; do
  media_name="${media_file#$ROOT/}"
  if out="$( "$ROOT/bin/capstan" test "$media_file" 2>&1)"; then
    ok "$media_name ($out)"
  else
    bad "$media_name" "$out"
  fi
done


section "gc"
"$C" build -o "$tmp/churn.c" "$ROOT/tests/gc/churn.cap" >/dev/null && "$CC" $CFLAGS "$tmp/churn.c" -o "$tmp/churn"
stats="$(CAPSTAN_GC_STATS=1 "$tmp/churn" 2>&1 >/dev/null)"
peak=$(sed -n 's/.*peak_heap=\([0-9]*\).*/\1/p' <<<"$stats"); total=$(sed -n 's/.*total_allocated=\([0-9]*\).*/\1/p' <<<"$stats")
if [[ -n "$peak" ]] && (( peak < 64 * 1024 * 1024 && total > 500 * 1024 * 1024 )); then ok "churn: $((total/1048576)) MB allocated, peak heap $((peak/1048576)) MB"
else bad "churn" "$stats"; fi
"$C" build -o "$tmp/integ.c" "$ROOT/tests/gc/integrity.cap" >/dev/null && "$CC" $CFLAGS "$tmp/integ.c" -o "$tmp/integ"
if CAPSTAN_GC_STRESS=1 "$tmp/integ" | diff -q - "$ROOT/tests/gc/integrity.out" >/dev/null; then ok "integrity with a collection on every allocation"; else bad "integrity" "values changed under GC stress"; fi
"$C" build -o "$tmp/grant_roots.c" "$ROOT/tests/gc/grant_roots.cap" >/dev/null && "$CC" $CFLAGS "$tmp/grant_roots.c" -o "$tmp/grant_roots"
if CAPSTAN_GC_STRESS=1 "$tmp/grant_roots" | diff -q - "$ROOT/tests/gc/grant_roots.out" >/dev/null; then ok "grant and policy arguments remain rooted under GC stress"; else bad "grant GC roots" "grant or policy arguments did not survive collection"; fi
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
  "$C" build -o "$tmp/fmtsan.c" "$ROOT/tools/fmt.cap" >/dev/null 2>&1 && "$CC" $SAN "$tmp/fmtsan.c" -o "$tmp/fmtsan" && cp "$ROOT/tests/fmt/layout.cap" $SRC "$tmp/" 2>/dev/null
  if CAPSTAN_GC_STRESS=200 "$tmp/fmtsan" "$tmp/layout.cap" "$tmp"/{ast,lexer,parser,checker,ranges,codegen,main}.cap && cmp -s "$tmp/layout.cap" "$ROOT/tests/fmt/layout.fmt"; then ok "formatter clean under ASan+UBSan with GC stress"; else bad "sanitized formatter" "failed"; fi
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

section "fmt"
F="$ROOT/build/capstanfmt"
if "$C" build -o "$tmp/fmt.c" "$ROOT/tools/fmt.cap" >"$tmp/log" 2>&1 && "$CC" $WFLAGS "$tmp/fmt.c" -o "$F" 2>>"$tmp/log"; then
  if [[ "$(grep -c 'warning\[' "$tmp/log")" == 1 ]] && grep -q 'warning\[AUDIT\]' "$tmp/log"; then ok "formatter builds warning-free C; its single trust() is reported as AUDIT"
  else bad "fmt build" "expected exactly one AUDIT warning: $(head -3 "$tmp/log")"; fi
else bad "fmt build" "$(head -3 "$tmp/log")"; fi
for f in "$ROOT"/tests/fmt/*.cap; do
  n="fmt/$(basename "$f")"; cp "$f" "$tmp/f.cap"
  if "$F" "$tmp/f.cap" && diff -u "${f%.cap}.fmt" "$tmp/f.cap" >"$tmp/diff"; then
    if "$F" --check "$tmp/f.cap" >/dev/null; then ok "$n (expected layout, idempotent)"; else bad "$n" "not idempotent"; fi
  else bad "$n" "layout differs"; cat "$tmp/diff"; fi
done
# Every source file in the repository follows the house style, except the diagnostics
# and recovery tests (their columns and lexical errors are what they test), formatter inputs and
# files marked `// fmt: off` (a lexical test that needs tabs and CRLF).
STYLED=$(cd "$ROOT" && grep -L '^// fmt: off' compiler/*.cap tools/*.cap lib/*.cap lib/shroud/*.cap examples/*.cap examples/shroud/*.cap bench/*.cap tests/{accept,reject,runtime,gc,io,crypto,shroud}/*.cap 2>/dev/null)
if out="$(cd "$ROOT" && "$F" --check $STYLED)"; then
  ok "$(wc -w <<<"$STYLED") repository sources are formatted"
else
  # Show the formatter rewrite so house-style failures are actionable in CI.
  while IFS= read -r f; do
    [[ -f "$f" ]] || continue
    cp "$f" "$tmp/house-style.before"
    if "$F" "$tmp/house-style.before" >/dev/null 2>&1; then
      if ! cmp -s "$f" "$tmp/house-style.before"; then
        diff -u --label "$f" --label "$f (formatter output)" "$f" "$tmp/house-style.before" || true
      fi
    fi
  done <<< "$out"
  bad "house style" "run bin/capstan fmt on: $out"
fi
cp "$ROOT/tests/fmt/layout.cap" "$tmp/bad.cap"; printf 'int main() { return 0 @ 1; }\n' > "$tmp/lexerr.cap"; cp "$tmp/lexerr.cap" "$tmp/lexerr.keep"
"$F" --check "$tmp/bad.cap" >/dev/null; c1=$?; "$F" "$tmp/lexerr.cap" >/dev/null; c2=$?
if [[ $c1 -eq 1 && $c2 -eq 2 ]] && cmp -s "$tmp/lexerr.cap" "$tmp/lexerr.keep" && cmp -s "$tmp/bad.cap" "$ROOT/tests/fmt/layout.cap"; then ok "--check changes nothing and exits 1; unscannable files are refused and left alone"
else bad "fmt modes" "check exit $c1, refuse exit $c2"; fi
FMT_N=3; COR_N=2; (( FULL )) && { FMT_N=30; COR_N=20; }
if out="$(cd "$ROOT" && $PY tests/fmt/perturb.py "$F" $FMT_N "${FUZZ_SEED:-$RANDOM}" $STYLED 2>&1)"; then ok "$out"; else bad "fmt whitespace fuzz" "$out"; fi
if out="$(cd "$ROOT" && $PY tests/fmt/perturb.py --corrupt "$F" $COR_N "${FUZZ_SEED:-$RANDOM}" $STYLED 2>&1)"; then ok "$out"; else bad "fmt corruption fuzz" "$out"; fi

section "supply chain: SBOM, reproducibility report, release verifier, workflow hardening"
if out="$("$ROOT/tests/supply/test_supply.sh" 2>&1)"; then ok "$(tail -1 <<<"$out")"; grep '^  pass' <<<"$out" | sed 's/^  pass  /      /'
else bad "supply chain" "$(grep -A3 'FAIL' <<<"$out" | head -8)"; fi

section "CWE red-team atlas"
if out="$(CAPSTANC="$C" CC="$CC" $PY "$ROOT/tests/cwe/atlas.py" --write-doc 2>&1)"; then
  if git -C "$ROOT" diff --quiet -- docs/CWE-ATLAS.md; then
    ok "$out; generated atlas is current"
  else
    bad "CWE atlas documentation drift" "$(git -C "$ROOT" diff -- docs/CWE-ATLAS.md | head -40)"
  fi
else
  bad "CWE red-team atlas" "$out"
fi

section "lsp"
L="$ROOT/build/capstan-lsp"
LSP_SRC="$(ls "$ROOT"/compiler/{ast,lexer,parser,checker,ranges,codegen}.cap) $ROOT/tools/lsp.cap"
if "$C" build -o "$tmp/lsp.c" $LSP_SRC >"$tmp/log" 2>&1 && "$CC" $WFLAGS "$tmp/lsp.c" -o "$L" 2>>"$tmp/log"; then
  if [[ ! -s "$tmp/log" ]]; then ok "language server builds with no warnings and no trust(); warning-free C"; else bad "lsp build" "$(head -3 "$tmp/log")"; fi
else bad "lsp build" "$(head -3 "$tmp/log")"; fi
if out="$($PY "$ROOT/tests/lsp/sessions.py" "$L" 2>&1)"; then ok "$out"; else bad "lsp sessions" "$out"; fi
LSP_N=40; (( FULL )) && LSP_N=1000
if out="$($PY "$ROOT/tests/lsp/fuzz.py" "$L" $LSP_N "${FUZZ_SEED:-$RANDOM}" 2>&1)"; then ok "$out"; else bad "lsp fuzz" "$out"; fi
if "$CC" $SAN "$tmp/lsp.c" -o "$tmp/lspsan" 2>/dev/null; then
  out2=""
  if out="$(CAPSTAN_GC_STRESS=200 $PY "$ROOT/tests/lsp/sessions.py" "$tmp/lspsan" 2>&1)" && out2="$(CAPSTAN_GC_STRESS=200 $PY "$ROOT/tests/lsp/fuzz.py" "$tmp/lspsan" 20 "${FUZZ_SEED:-$RANDOM}" 2>&1)"; then
    ok "language server clean under ASan+UBSan with GC stress (sessions and fuzzing)"
  else bad "sanitized language server" "$out $out2"; fi
else
  echo "  skip  sanitizers not available for $CC"
fi

if (( FULL )); then
  section "coverage"
  if [[ "$(uname)" != Linux ]] || ! command -v gcov >/dev/null || ! command -v gcc >/dev/null; then echo "  skip  coverage and compiler mutation run on Linux with gcc and gcov"
  elif out="$($PY "$ROOT/tests/coverage.py" --check 2>&1)"; then ok "$(tail -1 <<<"$out")"; echo "$out" | grep '%' | sed 's/^/      /'; else bad "coverage" "$(tail -3 <<<"$out")"; fi

  section "compiler mutation"
  if [[ "$(uname)" != Linux ]]; then echo "  skip  (Linux only)"
  elif out="$($PY "$ROOT/tests/mutate_compiler.py" "${MUTANTS:-24}" "${FUZZ_SEED:-$RANDOM}" compiler/ranges.cap compiler/checker.cap compiler/lexer.cap compiler/parser.cap compiler/codegen.cap 2>&1)"; then ok "$(tail -1 <<<"$out")"
  else bad "compiler mutation" "$(grep SURVIVED <<<"$out" | head -5; tail -1 <<<"$out")"; fi

  section "bench"
  if out="$("$ROOT/bench/run.sh" 2>&1)"; then ok "benchmarks within limit"; echo "$out" | sed 's/^/        /'; else bad "bench" "$out"; fi
fi

echo
echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]
