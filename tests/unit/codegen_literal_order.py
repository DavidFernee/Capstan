#!/usr/bin/env python3
"""Assert generated C sequences lazy string-literal materialisation left-to-right."""
from pathlib import Path
import re
import subprocess
import sys

compiler = Path(sys.argv[1])
work = Path(sys.argv[2]) / "literal-order"
work.mkdir(parents=True, exist_ok=True)
source = work / "literal_order.cap"
generated = work / "literal_order.c"

source.write_text(
    """string make() {
    return "later";
}

string combine(string first, string second) {
    return first + second;
}

int main() {
    println(combine("first", make()));
    println("left" + make());
    return 0;
}
""",
    encoding="utf-8",
)

result = subprocess.run(
    [str(compiler), "build", "-o", str(generated), str(source)],
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
if result.returncode != 0:
    print("compiler failed:", result.stdout.strip())
    raise SystemExit(1)

c = generated.read_text(encoding="utf-8")
call = re.compile(
    r'__auto_type\s+(\w+)\s*=\s*CAP_LIT\("first",\s*5\);\s*'
    r'__auto_type\s+(\w+)\s*=\s*fn_make\(\);\s*'
    r'fn_combine\(\1,\s*\2\)',
    re.S,
)
binary = re.compile(
    r'__auto_type\s+(\w+)\s*=\s*CAP_LIT\("left",\s*4\);\s*'
    r'__auto_type\s+(\w+)\s*=\s*fn_make\(\);\s*'
    r'cap_str_concat\(\1,\s*\2,',
    re.S,
)
if not call.search(c):
    print("call arguments do not materialise the first string literal before fn_make()")
    raise SystemExit(1)
if not binary.search(c):
    print("binary operands do not materialise the left string literal before fn_make()")
    raise SystemExit(1)
print("lazy string literals are materialised before later effectful operands")
