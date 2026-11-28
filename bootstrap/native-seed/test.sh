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
    'int _many(int _a, int _b, int _c, int _d, int _e, int _f, int _g){ return _g; } int main(){ return _many(1, 2, 3, 4, 5, 6, 7); }'; do
    printf '%s' "$helper" | reject
done

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

sha256sum "$scratch/first"
printf 'Native seed and ELF fixtures passed.\n'
