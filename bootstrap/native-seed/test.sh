#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ "$(uname -sm)" == "Linux x86_64" ]]
scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
mkdir "$scratch/empty"
for run in first second; do
    as --64 seed.S -o "$scratch/$run.o"
    ld -static -nostdlib -s "$scratch/$run.o" -o "$scratch/$run"
done
cmp "$scratch/first" "$scratch/second"

check_static() {
    local headers
    headers="$(readelf -lW "$1")"
    [[ "$headers" != *INTERP* && "$headers" != *DYNAMIC* ]]
}
check_static "$scratch/first"
compile() {
    env -i PATH="$scratch/empty" "$scratch/first"
}
for n in 0 -1 256 9223372036854775807 -9223372036854775808; do
    printf 'int main() { return %s; }\n' "$n" | compile > "$scratch/program"
    printf 'int main() { return %s; }\n' "$n" | compile > "$scratch/repeated"
    cmp "$scratch/program" "$scratch/repeated"
    chmod +x "$scratch/program"
    check_static "$scratch/program"
    env -i PATH="$scratch/empty" "$scratch/program" 3>"$scratch/result"
    [[ "$(wc -c < "$scratch/result")" == 8 ]]
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$n" ]]
done

printf '/* lead */ int/**/main ( ) { // body\nreturn/* value */256; } // end' |
    compile > "$scratch/trivia"
chmod +x "$scratch/trivia"
env -i PATH="$scratch/empty" "$scratch/trivia" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 256 ]]

reject() {
    local code=0
    compile > "$scratch/rejected" 2>"$scratch/offset" || code=$?
    [[ "$code" == 2 && ! -s "$scratch/rejected" && "$(cat "$scratch/offset")" =~ ^[0-9]+$ ]]
}
for source in \
    '' 'int main() { return -; }' 'int main() { return 9223372036854775808; }' \
    'int main() { return -9223372036854775809; }' 'int main() { return 42; } trailing' \
    'int main() { return 1 + 2 * 3; }' 'int main() { return 1--2; }' 'int main() { return 42;' \
    'intmain(){return 42;}' 'int main(){return42;}' 'int main(){return 42;}/*'; do
    printf '%s' "$source" | reject
done
printf 'int main() { return 42; }\0' | reject
printf '/* \0 */ int main(){return 42;}' | reject
source='int main() { return 42; }'
input_limit=1048576
printf '%s%*s' "$source" "$((input_limit - ${#source}))" '' | compile > "$scratch/limit"
[[ -s "$scratch/limit" ]]
printf '%s%*s' "$source" "$((input_limit + 1 - ${#source}))" '' > "$scratch/too-long"
status=0
compile < "$scratch/too-long" > "$scratch/rejected" || status=$?
[[ "$status" == 3 && ! -s "$scratch/rejected" ]]

for expression in '40 + 2' '44 - 2' '40 - -2' '60 - 20 - 3 + 5'; do
    printf 'int main() { return %s; }' "$expression" | compile > "$scratch/program"
    chmod +x "$scratch/program"
    env -i PATH="$scratch/empty" "$scratch/program" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
done
for expression in '9223372036854775807 + 1' '-9223372036854775808 - 1' '0 - -9223372036854775808' '9223372036854775807 + 1 - 1'; do
    printf 'int main() { return %s; }' "$expression" | compile > "$scratch/overflow"
    chmod +x "$scratch/overflow"
    status=0
    env -i PATH="$scratch/empty" "$scratch/overflow" 3>"$scratch/result" || status=$?
    [[ "$status" == 70 && ! -s "$scratch/result" ]]
done

chain=0
for ((i = 0; i < 256; i++)); do chain+=" + 1"; done
printf 'int main() { return %s; }' "$chain" | compile > "$scratch/chain"
chmod +x "$scratch/chain"
env -i PATH="$scratch/empty" "$scratch/chain" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 256 ]]
printf 'int main() { return %s + 1; }' "$chain" | reject

printf 'const int BASE = 40; const int STEP_2 = -2; int main(){return BASE - STEP_2;}' |
    compile > "$scratch/constants"
chmod +x "$scratch/constants"
env -i PATH="$scratch/empty" "$scratch/constants" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
for case_source in \
    'const int X = 1; const int X = 2; int main(){return X;}' \
    'const int X = 1; int main(){return XX;}' \
    'const int X = 1 + 2; int main(){return X;}' \
    'const int int = 1; int main(){return int;}'; do
    printf '%s' "$case_source" | reject
done

# Exercise the real first compiler record layout, with a small entry fixture.
{
    sed -n '1,/^CompileBudget new_compile_budget()/p' ../../compiler/ast.cap | sed '$d'
    printf 'int main(){ CompileBudget item = new CompileBudget{source_bytes: 4, tokens: 7, ast_nodes: 150000, files: 2, exhausted: false}; return item.ast_nodes; }\n'
} | compile > "$scratch/record"
chmod +x "$scratch/record"
check_static "$scratch/record"
env -i PATH="$scratch/empty" "$scratch/record" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 150000 ]]
for case_source in \
    'struct Cell { int field; int field; } int main(){return 0;}' \
    'struct Cell { int field; } int main(){ Cell item = new Cell{field: true}; return item.field; }' \
    'struct Cell { bool field; } int main(){ Cell item = new Cell{field: true}; return item.field; }' \
    'struct Cell { int a; int b; } int main(){ Cell item = new Cell{b: 2, a: 1}; return item.b; }' \
    'struct Cell { int field; } int main(){ Cell item = new Other{field: 42}; return item.field; }'; do
    printf '%s' "$case_source" | reject
done

# Compile the original helper as a callable function, then exercise a
# nonzero return in every integer slot with a separate typed layout.
{
    sed -n '1,/^bool charge_ast_nodes(/p' ../../compiler/ast.cap | sed '$d'
    printf 'int main(){ CompileBudget item = new_compile_budget(); return item.ast_nodes; }\n'
} | compile > "$scratch/helper"
chmod +x "$scratch/helper"
check_static "$scratch/helper"
env -i PATH="$scratch/empty" "$scratch/helper" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 0 ]]
for field in first last; do
    printf 'struct Cell { int first; bool ready; int last; } const int BASE = 41; Cell make(){ return new Cell{first: BASE, ready: true, last: 42}; } const int UNUSED = 43; int main(){ Cell item = make(); return item.%s; }' "$field" |
        compile > "$scratch/helper"
    chmod +x "$scratch/helper"
    env -i PATH="$scratch/empty" "$scratch/helper" 3>"$scratch/result"
    expected=41
    [[ "$field" != last ]] || expected=42
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
printf 'struct Cell { int n; } Cell make(){ return new Cell{n: 42}; } int main(){ Cell item = other(); return item.n; }' |
    reject

printf 'const int X = 1; struct Cell { int n; } Cell make(){ return new Cell{n: X}; } const int X = 2; int main(){ Cell item = make(); return item.n; }' |
    reject

printf 'struct A { int n; } struct B { bool flag; int n; } int main(){ B item = new B{flag: true, n: 42}; return item.n; }' |
    compile > "$scratch/layouts"
chmod +x "$scratch/layouts"
env -i PATH="$scratch/empty" "$scratch/layouts" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
for case_source in \
    'struct A { int n; } struct A { int m; } int main(){return 0;}' \
    'struct A { List<Missing> items; } int main(){return 0;}' \
    'struct A { string name; } int main(){ A item = new A{name: true}; return item.name; }'; do
    printf '%s' "$case_source" | reject
done

for field in name args; do
    printf 'struct Type { int k; string name; List<Type> args; } Type make(){ return new Type{k: 1, name: "example", args: new List<Type>()}; } int main(){ Type item = make(); return item.%s.len(); }' "$field" |
        compile > "$scratch/type"
    chmod +x "$scratch/type"
    check_static "$scratch/type"
    env -i PATH="$scratch/empty" "$scratch/type" 3>"$scratch/result"
    expected=7
    [[ "$field" != args ]] || expected=0
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
printf 'struct Type { List<Type> args; } int main(){ Type item = new Type{args: new List<Other>()}; return item.args.len(); }' |
    reject
printf 'struct Type { string name; } int main(){ Type item = new Type{name: "%64s"}; return item.name.len(); }' '' |
    reject

for index in 0 LAST -1 3 9223372036854775807; do
    printf 'const int LAST = 2; struct Token { string text; } Token make(){ return new Token{text: "AbZ"}; } int main(){ Token item = make(); return item.text.at(%s); }' "$index" |
        compile > "$scratch/byte"
    chmod +x "$scratch/byte"
    status=0
    env -i PATH="$scratch/empty" "$scratch/byte" 3>"$scratch/result" || status=$?
    case "$index" in
        0) [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 65 ]];;
        LAST) [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 90 ]];;
        *) [[ "$status" == 75 && ! -s "$scratch/result" ]];;
    esac
done
printf 'struct Type { List<Type> args; } int main(){ Type item = new Type{args: new List<Type>()}; return item.args.at(0); }' |
    reject

escaped="$(cat <<'CAPSTAN'
struct Token { string text; } int main(){ Token item = new Token{text: "A\n\t\r\0\\\"\'Z"}; return item.text
CAPSTAN
)"
expected_bytes=(65 10 9 13 0 92 34 39 90)
for index in "${!expected_bytes[@]}"; do
    printf '%s.at(%s); }' "$escaped" "$index" | compile > "$scratch/escaped"
    chmod +x "$scratch/escaped"
    env -i PATH="$scratch/empty" "$scratch/escaped" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "${expected_bytes[index]}" ]]
done
printf '%s.len(); }' "$escaped" | compile > "$scratch/escaped"
env -i PATH="$scratch/empty" "$scratch/escaped" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 9 ]]
printf '%s' 'struct Token { string text; } int main(){ Token item = new Token{text: "\q"}; return item.text.len(); }' |
    reject
printf '%s' 'struct Token { string text; } int main(){ Token item = new Token{text: "end\' |
    reject

for endpoints in '0, END' '1, 3' '4, 4' '3, 1' '-1, 2' '0, -1' '-2, -1' '0, 5'; do
    printf 'const int END = 4; struct Token { string text; } int main(){ Token item = new Token{text: "abcd"}; return item.text.slice(%s).len(); }' "$endpoints" |
        compile > "$scratch/slice"
    chmod +x "$scratch/slice"
    status=0
    env -i PATH="$scratch/empty" "$scratch/slice" 3>"$scratch/result" || status=$?
    case "$endpoints" in
        '0, END') [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 4 ]];;
        '1, 3') [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 2 ]];;
        '4, 4') [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 0 ]];;
        *) [[ "$status" == 75 && ! -s "$scratch/result" ]];;
    esac
done

for access in 'slice(1, 3).at(0)' 'slice(1, 3).at(1)' 'slice(1, 3).at(2)' 'slice(1, 3).at(-1)' 'slice(2, 2).at(0)' 'slice(0, 5).at(0)'; do
    printf 'struct Token { string text; } int main(){ Token item = new Token{text: "abcd"}; return item.text.%s; }' "$access" |
        compile > "$scratch/slice-byte"
    chmod +x "$scratch/slice-byte"
    status=0
    env -i PATH="$scratch/empty" "$scratch/slice-byte" 3>"$scratch/result" || status=$?
    case "$access" in
        'slice(1, 3).at(0)') [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 98 ]];;
        'slice(1, 3).at(1)') [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 99 ]];;
        *) [[ "$status" == 75 && ! -s "$scratch/result" ]];;
    esac
done

for literal in "'A'" "'\n'" "'\0'" "'\''"; do
    printf 'const int BYTE = %s; int main(){ return BYTE + %s; }' "$literal" "$literal" |
        compile > "$scratch/char"
    chmod +x "$scratch/char"
    env -i PATH="$scratch/empty" "$scratch/char" 3>"$scratch/result"
    case "$literal" in
        "'A'") expected=130;;
        "'\n'") expected=20;;
        "'\0'") expected=0;;
        *) expected=78;;
    esac
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
for literal in "''" "'ab'" "'\q'" "'a"; do
    printf 'int main(){ return %s; }' "$literal" | reject
done

for literal in 0x0 0xD8 0x000000000000000000000000000000aB 0x8000000000000000 0xffffFFFFFFFFffff; do
    printf 'const int MASK = %s; int main(){ return MASK; }' "$literal" | compile > "$scratch/hex"
    chmod +x "$scratch/hex"
    env -i PATH="$scratch/empty" "$scratch/hex" 3>"$scratch/result"
    case "$literal" in
        0x0) expected=0;;
        0xD8) expected=216;;
        0x000000000000000000000000000000aB) expected=171;;
        0x8000000000000000) expected=-9223372036854775808;;
        *) expected=-1;;
    esac
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
for literal in 0x 0xG 0xAfoo 0x10000000000000000 -0x1; do
    printf 'int main(){ return %s; }' "$literal" | reject
done

for comparison in 'MIN < MAX' 'MAX < MIN' 'MIN < MIN' 'MIN == MIN' 'MIN == MAX' \
    'MIN <= MIN' 'MAX <= MIN' 'MAX > MIN' 'MIN > MIN' 'MAX >= MAX' 'MIN >= MAX' 'MIN != MAX' 'MIN != MIN'; do
    printf 'const int MIN = 0x8000000000000000; const int MAX = 9223372036854775807; int main(){ if (%s) { return 42; } return 17; }' "$comparison" |
        compile > "$scratch/branch"
    chmod +x "$scratch/branch"
    check_static "$scratch/branch"
    env -i PATH="$scratch/empty" "$scratch/branch" 3>"$scratch/result"
    case "$comparison" in
        'MIN < MAX'|'MIN == MIN'|'MIN <= MIN'|'MAX > MIN'|'MAX >= MAX'|'MIN != MAX') expected=42;;
        *) expected=17;;
    esac
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
for comparison in '1 = 2' '1 ! 2' '1 <> 2' '1 =='; do
    printf 'int main(){ if (%s) { return 42; } return 17; }' "$comparison" | reject
done

for operator in '<' '=='; do
    for overflowing_arm in true false; do
        true_result='40 + 2'
        false_result='40 + 2'
        if [[ "$overflowing_arm" == true ]]; then
            true_result='9223372036854775807 + 1'
        else
            false_result='9223372036854775807 + 1'
        fi
        printf 'int main(){ if (1 %s 2) { return %s; } return %s; }' "$operator" "$true_result" "$false_result" |
            compile > "$scratch/branch-arithmetic"
        chmod +x "$scratch/branch-arithmetic"
        status=0
        env -i PATH="$scratch/empty" "$scratch/branch-arithmetic" 3>"$scratch/result" || status=$?
        if [[ "$operator:$overflowing_arm" == '<:true' || "$operator:$overflowing_arm" == '==:false' ]]; then
            [[ "$status" == 70 && ! -s "$scratch/result" ]]
        else
            [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
        fi
    done
done
printf 'int main(){ if (1 < 2) { return %s; } return 1 + 2; }' "$chain" | reject

for body in 'int _value = 40 + 2; return _value;' \
    'int _value = 17; _value = _value + 4; return _value + _value;' \
    'int _value = 8; _value = 29 - _value; return _value + _value;'; do
    printf 'int main(){ %s }' "$body" | compile > "$scratch/local"
    chmod +x "$scratch/local"
    env -i PATH="$scratch/empty" "$scratch/local" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
done
for body in 'int _value = _value; return _value;' 'int _value = 1; _other = 2; return _value;' \
    'int _value = 1; return _other;' 'int _VALUE = 1; return _VALUE;'; do
    printf 'const int _VALUE = 42; int main(){ %s }' "$body" | reject
done
printf '%s' 'int main(){ int _value = 9223372036854775807 + 1; return 42; }' |
    compile > "$scratch/local"
env_status=0
env -i PATH="$scratch/empty" "$scratch/local" 3>"$scratch/result" || env_status=$?
[[ "$env_status" == 70 && ! -s "$scratch/result" ]]

for specification in '0|42|_n + 1|0|42' '42|42|_n + 1|0|42' \
    '0|1000000|_n + 1|0|1000000' '0|1000001|_n + 1|73|' \
    '0|1|_n|73|' '0|1|9223372036854775807 + 1|70|'; do
    IFS='|' read -r initial limit update expected_status expected_value <<< "$specification"
    printf 'int main(){ int _n = %s; while (_n < %s) { _n = %s; } return _n; }'         "$initial" "$limit" "$update" | compile > "$scratch/loop"
    chmod +x "$scratch/loop"
    status=0
    env -i PATH="$scratch/empty" "$scratch/loop" 3>"$scratch/result" || status=$?
    [[ "$status" == "$expected_status" ]]
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected_value" ]]
done
printf '%s' 'int main(){ int _n = 10; _n = _n + 1; _n = _n + 2; return _n; }' |
    compile > "$scratch/loop"
env -i PATH="$scratch/empty" "$scratch/loop" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 13 ]]

for comparison in '_n == 21' '20 < _n' '_n == _n'; do
    printf 'int main(){ int _n = 0; while (_n < 21) { _n = _n + 1; } if (%s) { return _n + _n; } return 17; }' "$comparison" |
        compile > "$scratch/local-branch"
    chmod +x "$scratch/local-branch"
    env -i PATH="$scratch/empty" "$scratch/local-branch" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
done
printf '%s' 'int main(){ int _n = 0; _n = 42; if (_n < 40) { return 9223372036854775807 + 1; } return _n; }' |
    compile > "$scratch/local-branch"
env -i PATH="$scratch/empty" "$scratch/local-branch" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf 'int main(){ int _n = %s; if (_n == 0) { return 1 + 2; } return _n; }' "$chain" |
    reject

printf '%s' 'int main(){ int _n = 1; int _step = _n + 2; _n = 0; while (_n < 42) { _n = _n + _step; } if (_step < _n) { return _n; } return _step; }' |
    compile > "$scratch/locals"
chmod +x "$scratch/locals"
env -i PATH="$scratch/empty" "$scratch/locals" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
declarations=''
for ((i = 1; i <= 16; i++)); do declarations+="int _v$i = $i; "; done
printf 'int main(){ %s return _v1 + _v16; }' "$declarations" | compile > "$scratch/locals"
env -i PATH="$scratch/empty" "$scratch/locals" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 17 ]]
printf 'int main(){ %s int _v17 = 17; return _v17; }' "$declarations" | reject
printf '%s' 'int main(){ int _a = 1; int _a = 2; return _a; }' | reject
printf '%s' 'int main(){ int _a = _b; int _b = 42; return _a; }' | reject

printf '%s' 'int main(){ int _n = 0; int _bound = 84; while (_n < _bound) { _n = _n + 1; _bound = _bound - 1; } return _n; }' |
    compile > "$scratch/mutable-bound"
chmod +x "$scratch/mutable-bound"
env -i PATH="$scratch/empty" "$scratch/mutable-bound" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
updates=''
for ((i = 0; i < 32; i++)); do updates+='_n = _n + 1; '; done
printf 'int main(){ int _n = 10; while (_n < 11) { %s } return _n; }' "$updates" |
    compile > "$scratch/mutable-bound"
env -i PATH="$scratch/empty" "$scratch/mutable-bound" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf 'int main(){ int _n = 10; while (_n < 11) { %s _n = 42; } return _n; }' "$updates" | reject

for argument in VALUE 9223372036854775807; do
    printf 'const int VALUE = 21; int _double(int _n){ return _n + _n; } int main(){ return _double(%s); }' "$argument" |
        compile > "$scratch/parameter"
    chmod +x "$scratch/parameter"
    check_static "$scratch/parameter"
    status=0
    env -i PATH="$scratch/empty" "$scratch/parameter" 3>"$scratch/result" || status=$?
    if [[ "$argument" == VALUE ]]; then
        [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
    else
        [[ "$status" == 70 && ! -s "$scratch/result" ]]
    fi
done
for call in '_double()' '_double(1, 2)' '_other(21)' '_double(_n)'; do
    printf 'int _double(int _n){ return _n + _n; } int main(){ return %s; }' "$call" | reject
done

for helper in \
    'int _sub(int _a, int _b){ return _a - _b; } int main(){ return _sub(50, 8); }' \
    'int _six(int _a, int _b, int _c, int _d, int _e, int _f){ return _a - _b - _c - _d - _e - _f; } int main(){ return _six(100, 20, 3, 4, 5, 26); }'; do
    printf '%s' "$helper" | compile > "$scratch/arguments"
    chmod +x "$scratch/arguments"
    env -i PATH="$scratch/empty" "$scratch/arguments" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
done
for helper in \
    'int _sub(int _a, int _a){ return _a; } int main(){ return _sub(50, 8); }' \
    'int _sub(int _a, int _b){ return _a - _b; } int main(){ return _sub(42); }' \
    'int _many(int _a, int _b, int _c, int _d, int _e, int _f, int _g){ return _g; } int main(){ return _many(1, 2, 3, 4, 5, 6); }'; do
    printf '%s' "$helper" | reject
done

# Exercise both alignment cases and every register/stack argument position.
for arity in 7 8 15 16 17; do
    params=() args=()
    for ((i=1; i<=arity; i++)); do params+=("int _p$i"); args+=("$i + 20"); done
    for ((i=1; i<=arity; i++)); do
        fixture="$(IFS=,; printf 'int _pick(%s){ return _p%d; } int main(){ return _pick(%s); }' "${params[*]}" "$i" "${args[*]}")"
        if ((arity > 16)); then printf '%s' "$fixture" | reject; break; fi
        printf '%s' "$fixture" | compile > "$scratch/stack-arguments"
        chmod +x "$scratch/stack-arguments"
        env -i PATH="$scratch/empty" "$scratch/stack-arguments" 3>"$scratch/result"
        [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$((i+20))" ]]
    done
done

printf '%s' 'int _sub(int _left, int _right){ return _left - _right; } int main(){ return _sub(45 + 5, 10 - 2); }' |
    compile > "$scratch/expression-arguments"
chmod +x "$scratch/expression-arguments"
env -i PATH="$scratch/empty" "$scratch/expression-arguments" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'int _first(int _left, int _right){ return _left; } int main(){ return _first(42, 9223372036854775807 + 1); }' |
    compile > "$scratch/expression-arguments"
status=0
env -i PATH="$scratch/empty" "$scratch/expression-arguments" 3>"$scratch/result" || status=$?
[[ "$status" == 70 && ! -s "$scratch/result" ]]
printf 'int _same(int _n){ return _n + 0; } int main(){ return _same(%s); }' "$chain" |
    reject

for arguments in '19 + 1, 22' '22, 19 + 1' '21, 21' '0x7fffffffffffffff, 1'; do
    printf 'int _choose(int _a, int _b){ if (_a < _b) { return _a + _b; } return _b + _a; } int main(){ return _choose(%s); }' "$arguments" |
        compile > "$scratch/helper-branch"
    chmod +x "$scratch/helper-branch"
    status=0
    env -i PATH="$scratch/empty" "$scratch/helper-branch" 3>"$scratch/result" || status=$?
    if [[ "$arguments" == '0x7fffffffffffffff, 1' ]]; then
        [[ "$status" == 70 && ! -s "$scratch/result" ]]
    else
        [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
    fi
done
printf '%s' 'int _choose(int _n){ if (_n == 42) { return _n; } return 9223372036854775807 + 1; } int main(){ return _choose(42); }' |
    compile > "$scratch/helper-branch"
env -i PATH="$scratch/empty" "$scratch/helper-branch" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]

printf '%s' 'int _count(int _limit, int _step){ int _n = 0; while (_n < _limit) { _n = _n + _step; } if (_n == _limit) { return _n; } return 0; } int main(){ return _count(40 + 2, 3); }' |
    compile > "$scratch/helper-loop"
chmod +x "$scratch/helper-loop"
env -i PATH="$scratch/empty" "$scratch/helper-loop" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'int _step(int _n){ _n = _n + 1; return _n; } int main(){ return _step(41); }' |
    compile > "$scratch/helper-loop"
env -i PATH="$scratch/empty" "$scratch/helper-loop" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'int _same(int _n){ int _old = _n; while (_n < 1) { _n = _old; } return _n; } int main(){ return _same(0); }' |
    compile > "$scratch/helper-loop"
status=0
env -i PATH="$scratch/empty" "$scratch/helper-loop" 3>"$scratch/result" || status=$?
[[ "$status" == 73 && ! -s "$scratch/result" ]]
printf '%s' 'int _foo(int _n){ int _x = _n; return _x; } int main(){ return _foo(_x); }' |
    reject

{
    sed -n '1,/^CompileBudget new_compile_budget()/p' ../../compiler/ast.cap | sed '$d'
    printf '%s\n' 'int _nodes(CompileBudget item){ return item.ast_nodes; }'
    printf '%s\n' 'int main(){ CompileBudget item = new CompileBudget{source_bytes: 4, tokens: 7, ast_nodes: 42, files: 2, exhausted: false}; return _nodes(item); }'
} | compile > "$scratch/record-argument"
chmod +x "$scratch/record-argument"
check_static "$scratch/record-argument"
env -i PATH="$scratch/empty" "$scratch/record-argument" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'struct Cell { int a; int b; } int _read(Cell item){ return item.a; } int main(){ Cell item = new Cell{a: 42, b: 17}; return _read(item); }' |
    compile > "$scratch/record-argument"
env -i PATH="$scratch/empty" "$scratch/record-argument" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'struct Cell { int a; } struct Other { int b; } int _read(Cell item){ return item.a; } int main(){ Other item = new Other{b: 42}; return _read(item); }' |
    reject

for field in a b; do
    printf 'struct Cell { int a; int b; } int _update(Cell item){ item.a = 40; item.a += 2; return item.%s; } int main(){ Cell item = new Cell{a: 0, b: 17}; return _update(item); }' "$field" |
        compile > "$scratch/record-update"
    chmod +x "$scratch/record-update"
    env -i PATH="$scratch/empty" "$scratch/record-update" 3>"$scratch/result"
    expected=42
    [[ "$field" != b ]] || expected=17
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
printf '%s' 'struct Cell { int a; } int _inc(Cell item){ item.a += 1; return item.a; } int main(){ Cell item = new Cell{a: 9223372036854775807}; return _inc(item); }' |
    compile > "$scratch/record-update"
status=0
env -i PATH="$scratch/empty" "$scratch/record-update" 3>"$scratch/result" || status=$?
[[ "$status" == 70 && ! -s "$scratch/result" ]]
printf '%s' 'struct Cell { bool flag; int a; } int _inc(Cell item){ item.flag += 1; return item.a; } int main(){ Cell item = new Cell{flag: true, a: 42}; return _inc(item); }' |
    reject

for count in 0 16 17; do
    pushes=''
    for ((i = 0; i < count; i++)); do pushes+='item.values.push(42); '; done
    printf 'struct Work { int marker; List<int> values; } int _fill(Work item){ %s return item.values.len(); } int main(){ Work item = new Work{marker: 7, values: new List<int>()}; return _fill(item); }' "$pushes" |
        compile > "$scratch/list"
    chmod +x "$scratch/list"
    status=0
    env -i PATH="$scratch/empty" "$scratch/list" 3>"$scratch/result" || status=$?
    if [[ "$count" == 17 ]]; then
        [[ "$status" == 75 && ! -s "$scratch/result" ]]
    else
        [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$count" ]]
    fi
done
printf '%s' 'struct Work { List<int> values; } Work _make(){ return new Work{values: new List<int>()}; } int main(){ Work item = _make(); return item.values.len(); }' |
    reject

for index in 0 1 2 -1; do
    printf 'struct Work { List<int> values; } int _read(Work item){ item.values.push(17); item.values.push(42); return item.values[%s]; } int main(){ Work item = new Work{values: new List<int>()}; return _read(item); }' "$index" |
        compile > "$scratch/list-index"
    chmod +x "$scratch/list-index"
    status=0
    env -i PATH="$scratch/empty" "$scratch/list-index" 3>"$scratch/result" || status=$?
    case "$index" in
        0) [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 17 ]];;
        1) [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]];;
        *) [[ "$status" == 75 && ! -s "$scratch/result" ]];;
    esac
done

for access in 'kids[0].k' 'kids[1].k' 'kids[-1].k' 'kids.len()'; do
    printf 'struct Node { int k; List<Node> kids; } int _walk(Node item){ item.kids.push(item); item.k += 2; return item.%s; } int main(){ Node item = new Node{k: 40, kids: new List<Node>()}; return _walk(item); }' "$access" |
        compile > "$scratch/record-list"
    chmod +x "$scratch/record-list"
    status=0
    env -i PATH="$scratch/empty" "$scratch/record-list" 3>"$scratch/result" || status=$?
    case "$access" in
        'kids[0].k') [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]];;
        'kids.len()') [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 1 ]];;
        *) [[ "$status" == 75 && ! -s "$scratch/result" ]];;
    esac
done
printf '%s' 'struct Node { int k; List<Node> kids; } int _walk(Node item){ item.kids.push(42); return item.k; } int main(){ Node item = new Node{k: 40, kids: new List<Node>()}; return _walk(item); }' |
    reject

for index in 0 1 -1; do
    printf 'struct Node { int k; List<Node> src; List<Node> dst; } int _copy(Node item){ item.src.push(item); item.dst.push(item.src[%s]); item.k += 2; return item.dst[0].k; } int main(){ Node item = new Node{k: 40, src: new List<Node>(), dst: new List<Node>()}; return _copy(item); }' "$index" |
        compile > "$scratch/list-copy"
    chmod +x "$scratch/list-copy"
    status=0
    env -i PATH="$scratch/empty" "$scratch/list-copy" 3>"$scratch/result" || status=$?
    if [[ "$index" == 0 ]]; then
        [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
    else
        [[ "$status" == 75 && ! -s "$scratch/result" ]]
    fi
done
printf '%s' 'struct Node { int k; List<Node> kids; } int _copy(Node item){ item.kids.push(item); item.kids.push(item.kids[0]); return item.kids.len(); } int main(){ Node item = new Node{k: 42, kids: new List<Node>()}; return _copy(item); }' |
    compile > "$scratch/list-copy"
env -i PATH="$scratch/empty" "$scratch/list-copy" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 2 ]]

for index in 0 1 2; do
    printf 'struct Node { int k; List<Node> kids; } int _walk(Node item, Node peer){ item.kids.push(item); item.kids.push(peer); item.k += 2; return item.kids[%s].k; } int main(){ Node item = new Node{k: 15, kids: new List<Node>()}; Node peer = new Node{k: 42, kids: new List<Node>()}; return _walk(item, peer); }' "$index" |
        compile > "$scratch/peer"
    chmod +x "$scratch/peer"
    status=0
    env -i PATH="$scratch/empty" "$scratch/peer" 3>"$scratch/result" || status=$?
    case "$index" in
        0) [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 17 ]];;
        1) [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]];;
        *) [[ "$status" == 75 && ! -s "$scratch/result" ]];;
    esac
done
printf '%s' 'struct Node { int k; List<Node> kids; } int _walk(Node item){ item.kids.push(peer); return item.k; } int main(){ Node item = new Node{k: 42, kids: new List<Node>()}; return _walk(item); }' |
    reject

for order in empty item-first peer-first; do
    pushes=''
    expected=7
    case "$order" in
        item-first) pushes='item.kids.push(item); item.kids.push(peer);'; expected=42;;
        peer-first) pushes='item.kids.push(peer); item.kids.push(item);'; expected=17;;
    esac
    printf 'struct Node { int k; List<Node> kids; } int _pop(Node item, Node peer){ %s if (let child = item.kids.pop()) { return child.k; } return 7; } int main(){ Node item = new Node{k: 17, kids: new List<Node>()}; Node peer = new Node{k: 42, kids: new List<Node>()}; return _pop(item, peer); }' "$pushes" |
        compile > "$scratch/pop"
    chmod +x "$scratch/pop"
    env -i PATH="$scratch/empty" "$scratch/pop" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
printf '%s' 'struct Node { int k; List<Node> kids; } int _pop(Node item){ if (let child = item.kids.pop()) { return child.missing; } return 7; } int main(){ Node item = new Node{k: 17, kids: new List<Node>()}; return _pop(item); }' |
    reject

printf '%s' 'struct Node { int k; List<Node> kids; } int _walk(Node item, Node peer){ item.kids.pop(); item.kids.push(item); item.kids.push(peer); item.kids.pop(); return item.kids[0].k; } int main(){ Node item = new Node{k: 42, kids: new List<Node>()}; Node peer = new Node{k: 17, kids: new List<Node>()}; return _walk(item, peer); }' |
    compile > "$scratch/discard-pop"
chmod +x "$scratch/discard-pop"
env -i PATH="$scratch/empty" "$scratch/discard-pop" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'struct Node { int k; List<Node> kids; } int _walk(Node item){ item.kids.push(item); item.kids.pop(); item.kids.pop(); return item.kids.len(); } int main(){ Node item = new Node{k: 42, kids: new List<Node>()}; return _walk(item); }' |
    compile > "$scratch/discard-pop"
env -i PATH="$scratch/empty" "$scratch/discard-pop" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 0 ]]

for mode in drain empty stuck; do
    pushes='item.kids.push(item); item.kids.push(item);'
    body='item.k += 1; item.kids.pop();'
    expected=42
    case "$mode" in
        empty) pushes=''; expected=40;;
        stuck) body='item.kids.push(item); item.kids.pop();';;
    esac
    printf 'struct Node { int k; List<Node> kids; } int _walk(Node item){ %s while (item.kids.len() > 0) { %s } return item.k; } int main(){ Node item = new Node{k: 40, kids: new List<Node>()}; return _walk(item); }' "$pushes" "$body" |
        compile > "$scratch/record-loop"
    chmod +x "$scratch/record-loop"
    status=0
    env -i PATH="$scratch/empty" "$scratch/record-loop" 3>"$scratch/result" || status=$?
    if [[ "$mode" == stuck ]]; then
        [[ "$status" == 73 && ! -s "$scratch/result" ]]
    else
        [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
    fi
done
printf '%s' 'struct Node { int k; List<Node> kids; } int _walk(Node item){ while (item.kids.len() > 0) { return item.k; } return item.k; } int main(){ Node item = new Node{k: 40, kids: new List<Node>()}; return _walk(item); }' |
    reject

walk_prefix='struct Node { int k; int total; List<Node> kids; List<Node> spare; }'
walk_suffix='int main(){ Node item = new Node{k: 17, total: 0, kids: new List<Node>(), spare: new List<Node>()}; Node peer = new Node{k: 25, total: 0, kids: new List<Node>(), spare: new List<Node>()}; return _walk(item, peer); }'
printf '%s %s %s' "$walk_prefix" 'int _walk(Node item, Node peer){ item.kids.push(item); item.kids.push(peer); while (item.kids.len() > 0) { Node node = item.kids[item.kids.len() - 1]; item.kids.pop(); item.total += node.k; } return item.total; }' "$walk_suffix" |
    compile > "$scratch/worklist-fields"
chmod +x "$scratch/worklist-fields"
env -i PATH="$scratch/empty" "$scratch/worklist-fields" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s %s %s' "$walk_prefix" 'int _walk(Node item, Node peer){ while (item.kids.len() > 0) { Node node = item.kids[item.spare.len() - 1]; item.kids.pop(); } return item.total; }' "$walk_suffix" |
    reject
printf '%s %s %s' "$walk_prefix" 'int _walk(Node item, Node peer){ while (item.kids.len() > 0) { Node node = item.kids[item.kids.len() - 1]; item.kids.pop(); } item.total = node.k; return item.total; }' "$walk_suffix" |
    reject

for start in 39 40 41 42; do
    printf 'const int LIMIT = 42; struct Node { int count; List<Node> kids; } int _charge(Node item){ item.kids.push(item); item.kids.push(item); while (item.kids.len() > 0) { if (item.count >= LIMIT) { return -1; } item.count += 1; item.kids.pop(); } return item.count; } int main(){ Node item = new Node{count: %s, kids: new List<Node>()}; return _charge(item); }' "$start" |
        compile > "$scratch/worklist-budget"
    chmod +x "$scratch/worklist-budget"
    env -i PATH="$scratch/empty" "$scratch/worklist-budget" 3>"$scratch/result"
    if (( start <= 40 )); then expected=$((start + 2)); else expected=-1; fi
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done

for index in 0 1; do
    printf 'struct Node { int k; List<Node> pending; List<Node> kids; } int _walk(Node item, Node peer){ item.pending.push(item); item.kids.push(peer); while (item.pending.len() > 0) { Node node = item.pending[item.pending.len() - 1]; item.pending.pop(); item.kids.push(node.kids[%s]); } return item.kids[1].k; } int main(){ Node item = new Node{k: 17, pending: new List<Node>(), kids: new List<Node>()}; Node peer = new Node{k: 42, pending: new List<Node>(), kids: new List<Node>()}; return _walk(item, peer); }' "$index" |
        compile > "$scratch/node-child"
    chmod +x "$scratch/node-child"
    status=0
    env -i PATH="$scratch/empty" "$scratch/node-child" 3>"$scratch/result" || status=$?
    if [[ "$index" == 0 ]]; then
        [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
    else
        [[ "$status" == 75 && ! -s "$scratch/result" ]]
    fi
done

for destination in out kids; do
    printf 'struct Node { int k; List<Node> pending; List<Node> kids; List<Node> out; } int _walk(Node item, Node peer){ item.pending.push(item); item.kids.push(item); item.kids.push(peer); while (item.pending.len() > 0) { Node node = item.pending[item.pending.len() - 1]; item.pending.pop(); for (int i = 0; i < node.kids.len(); i += 1) { item.%s.push(node.kids[i]); } } return item.out[1].k; } int main(){ Node item = new Node{k: 17, pending: new List<Node>(), kids: new List<Node>(), out: new List<Node>()}; Node peer = new Node{k: 42, pending: new List<Node>(), kids: new List<Node>(), out: new List<Node>()}; return _walk(item, peer); }' "$destination" |
        compile > "$scratch/children"
    chmod +x "$scratch/children"
    status=0
    env -i PATH="$scratch/empty" "$scratch/children" 3>"$scratch/result" || status=$?
    if [[ "$destination" == out ]]; then
        [[ "$status" == 0 && "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
    else
        [[ "$status" == 75 && ! -s "$scratch/result" ]]
    fi
done

printf '%s' 'struct Node { int count; List<Node> kids; } int _walk(Node item, Node peer){ List<Node> pending = new List<Node>(); item.kids.push(peer); pending.push(item); while (pending.len() > 0) { Node node = pending[pending.len() - 1]; pending.pop(); item.count += 1; for (int i = 0; i < node.kids.len(); i += 1) { pending.push(node.kids[i]); } } return item.count; } int main(){ Node item = new Node{count: 40, kids: new List<Node>()}; Node peer = new Node{count: 17, kids: new List<Node>()}; return _walk(item, peer); }' |
    compile > "$scratch/local-worklist"
chmod +x "$scratch/local-worklist"
env -i PATH="$scratch/empty" "$scratch/local-worklist" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'struct Node { int count; } int _walk(Node item){ List<Node> pending = new List<Node>(); while (pending.len() > 0) { pending.pop(); } return item.count; } int main(){ Node item = new Node{count: 42}; return _walk(item); }' |
    compile > "$scratch/local-worklist"
env -i PATH="$scratch/empty" "$scratch/local-worklist" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'struct Node { int count; } int _walk(Node item){ pending.push(item); return item.count; } int main(){ Node item = new Node{count: 42}; return _walk(item); }' |
    reject

for mode in empty seeded; do
    initialization=''
    expected=40
    if [[ "$mode" == seeded ]]; then
        initialization='item.kids.push(item); item.kids.push(item);'
        expected=42
    fi
    printf 'struct Node { int count; List<Node> kids; } int _walk(Node item, List<Node> roots){ List<Node> pending = new List<Node>(); %s for (int i = 0; i < roots.len(); i += 1) { pending.push(roots[i]); } while (pending.len() > 0) { pending.pop(); item.count += 1; } return item.count; } int main(){ Node item = new Node{count: 40, kids: new List<Node>()}; return _walk(item, item.kids); }' "$initialization" |
        compile > "$scratch/roots"
    chmod +x "$scratch/roots"
    env -i PATH="$scratch/empty" "$scratch/roots" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
printf '%s' 'struct Node { int count; List<Node> kids; } int _walk(Node item, List<Node> roots){ return item.count; } int main(){ Node item = new Node{count: 42, kids: new List<Node>()}; return _walk(item, item.count); }' |
    reject

for start in 40 42; do
    printf 'const int LIMIT = 42; struct Node { int count; List<Node> kids; } bool _charge(Node item, List<Node> roots){ List<Node> pending = new List<Node>(); item.kids.push(item); for (int i = 0; i < roots.len(); i += 1) { pending.push(roots[i]); } while (pending.len() > 0) { if (item.count >= LIMIT) { return false; } item.count += 1; pending.pop(); } return true; } int main(){ Node item = new Node{count: %s, kids: new List<Node>()}; if (_charge(item, item.kids)) { return 42; } return 17; }' "$start" |
        compile > "$scratch/bool-helper"
    chmod +x "$scratch/bool-helper"
    env -i PATH="$scratch/empty" "$scratch/bool-helper" 3>"$scratch/result"
    expected=42
    [[ "$start" != 42 ]] || expected=17
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
printf '%s' 'struct Node { int count; } bool _charge(Node item){ return 1; } int main(){ Node item = new Node{count: 42}; if (_charge(item)) { return 42; } return 17; }' |
    reject

for start in 40 42; do
    printf 'const int LIMIT = 42; struct Node { int count; bool exhausted; List<Node> kids; } bool _charge(Node item){ item.kids.push(item); while (item.kids.len() > 0) { if (item.count >= LIMIT) { item.exhausted = true; return false; } item.count += 1; item.kids.pop(); } return true; } int main(){ Node item = new Node{count: %s, exhausted: false, kids: new List<Node>()}; if (_charge(item)) { return 42; } return 17; }' "$start" |
        compile > "$scratch/bool-guard"
    chmod +x "$scratch/bool-guard"
    env -i PATH="$scratch/empty" "$scratch/bool-guard" 3>"$scratch/result"
    expected=42
    [[ "$start" != 42 ]] || expected=17
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done
printf '%s' 'struct Node { int count; } bool _charge(Node item){ if (item.count >= 42) { item.count = true; return false; } return true; } int main(){ Node item = new Node{count: 42}; if (_charge(item)) { return 42; } return 17; }' |
    reject

{
    sed -n '1,/^bool charge_ast_nodes(/p' ../../compiler/ast.cap | sed '/^CompileBudget new_compile_budget()/,/^}/d; $d'
    printf '%s\n' 'bool _charge(CompileBudget item, List<Node> roots){ List<Node> pending = new List<Node>(); for (int i = 0; i < roots.len(); i += 1) { pending.push(roots[i]); } while (pending.len() > 0) { Node node = pending[pending.len() - 1]; pending.pop(); if (item.ast_nodes >= MAX_TOTAL_AST_NODES) { item.exhausted = true; return false; } item.ast_nodes += 1; for (int i = 0; i < node.kids.len(); i += 1) { pending.push(node.kids[i]); } } return true; }'
    printf '%s\n' 'int main(){ CompileBudget item = new CompileBudget{source_bytes: 0, tokens: 0, ast_nodes: MAX_TOTAL_AST_NODES, files: 0, exhausted: false}; if (_charge(item, new List<Node>())) { return 42; } return 17; }'
} | compile > "$scratch/distinct-root"
chmod +x "$scratch/distinct-root"
env -i PATH="$scratch/empty" "$scratch/distinct-root" 3>"$scratch/result"
[[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 42 ]]
printf '%s' 'struct Budget { int count; } struct Node { int k; List<Node> kids; } bool _charge(Budget item, List<Node> roots){ return true; } int main(){ Budget item = new Budget{count: 42}; if (_charge(item, new List<Budget>())) { return 42; } return 17; }' |
    reject
printf '%s' 'struct Ref { int n; } struct Holder { Ref? optional; } int main(){ Holder item = new Holder{optional: true}; return item.optional.len(); }' |
    reject

printf '%s' 'struct Budget { int count; } struct Node { int k; List<Node> kids; } bool _charge(Budget item, List<Node> roots){ List<Node> pending = new List<Node>(); pending.push(item); return true; } int main(){ Budget item = new Budget{count: 42}; if (_charge(item, new List<Node>())) { return 42; } return 17; }' |
    reject

for budget in fresh 149999 150000; do
    {
        sed '/^void report(/,$d' ../../compiler/ast.cap
        if [[ "$budget" == fresh ]]; then
            printf '%s' 'int main(){ CompileBudget item = new_compile_budget(); '
        else
            printf 'int main(){ CompileBudget item = new CompileBudget{source_bytes: 0, tokens: 0, ast_nodes: %s, files: 0, exhausted: false}; ' "$budget"
        fi
        printf '%s\n' 'Node peer = new Node{k: N_NONE, s: "", s2: "", s3: "", n: 0, binding_id: 0, line: 0, col: 0, file: 0, kids: new List<Node>(), ty: none}; List<Node> roots = new List<Node>(); roots.push(peer); if (charge_ast_nodes(item, roots)) { return 42; } return 17; }'
    } | compile > "$scratch/nonempty-distinct-roots"
    chmod +x "$scratch/nonempty-distinct-roots"
    env -i PATH="$scratch/empty" "$scratch/nonempty-distinct-roots" 3>"$scratch/result"
    expected=42
    [[ "$budget" != 150000 ]] || expected=17
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == "$expected" ]]
done

# Reject two helpers sharing a name, and a constructor of the wrong nominal type.
printf '%s' 'struct A { int k; } A make(){ return new A{k: 42}; } bool make(A item){ return true; } int main(){ A item = make(); if (make(item)) { return 1; } return 0; }' | reject
printf '%s' 'struct A { int k; } struct B { int k; } A make(){ return new A{k: 42}; } bool check(B item){ return true; } int main(){ B item = make(); if (check(item)) { return 1; } return 0; }' | reject

# Build the production Ctx layout and read each list through a typed parameter.
for field in files sources diags; do
    {
        sed -n '/^struct Diag {/,/^void report(/{ /^void report(/!p; }' ../../compiler/ast.cap
        printf 'int _size(Ctx value){ return value.%s.len(); } ' "$field"
        printf '%s' 'int main(){ Ctx item = new Ctx{files: new List<string>(), sources: new List<Tainted>(), diags: new List<Diag>(), release: false, strict: false, keep_checks: false}; return _size(item); }'
    } | compile > "$scratch/context"
    chmod +x "$scratch/context"
    env -i PATH="$scratch/empty" "$scratch/context" 3>"$scratch/result"
    [[ "$(od -An -td8 "$scratch/result" | tr -d '[:space:]')" == 0 ]]
done

printf '%s' 'struct Tainted { int k; } int main(){ Tainted item = new Tainted{k: 2}; return item.k; }' | reject
for element_pair in 'string Tainted' 'Tainted string' 'Diag Token' 'Diag Missing'; do
    read -r declared supplied <<< "$element_pair"
    printf 'struct Diag { int k; } struct Token { int k; } struct Ctx { List<%s> values; } int main(){ Ctx item = new Ctx{values: new List<%s>()}; return item.values.len(); }' "$declared" "$supplied" | reject
done
printf '%s' 'struct Ctx { List<Tainted> values; } int _read(Ctx item){ return item.values[0]; } int main(){ Ctx item = new Ctx{values: new List<Tainted>()}; return _read(item); }' | reject

# Distinguish a broken input channel from a malformed source, and check
# that transport failures cannot be mistaken for a successful compile/run.
status=0
compile <&- > "$scratch/broken-input" || status=$?
[[ "$status" == 1 && ! -s "$scratch/broken-input" ]]
status=0
printf '%s' "$source" | compile > /dev/full || status=$?
[[ "$status" == 1 ]]
status=0
env -i PATH="$scratch/empty" "$scratch/program" 3>&- || status=$?
[[ "$status" == 1 ]]

as --64 charge-ast-nodes.S -o "$scratch/charge.o"
as --64 charge-ast-nodes-test.S -o "$scratch/charge-test.o"
ld -static -nostdlib -s "$scratch/charge-test.o" "$scratch/charge.o" -o "$scratch/charge-test"
check_static "$scratch/charge-test"
env -i PATH="$scratch/empty" "$scratch/charge-test" > "$scratch/charge-results"
[[ "$(wc -c < "$scratch/charge-results")" == 72 ]]

sha256sum "$scratch/first"
printf 'Native seed and ELF fixtures passed.\n'
