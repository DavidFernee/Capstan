#!/usr/bin/env python3
"""Assert generated C sequences lazy literals and literal-first special calls left-to-right."""
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
    sql_query("select ?", make());
    run("echo", "--", make());
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


def check_special_order(label, source_arg_ends, call_name, required_pushes):
    if source_arg_ends != sorted(source_arg_ends):
        print(f"{label} source arguments are not ordered")
        raise SystemExit(1)
    list_match = re.search(
        r'CapList\s*\*\w+\s*=\s*cap_list_new\(\)',
        c[source_arg_ends[-1]:],
    )
    if not list_match:
        print(f"{label} argument list is allocated before source argument evaluation")
        raise SystemExit(1)
    list_start = source_arg_ends[-1] + list_match.start()
    after_list = list_start + list_match.end()
    call_pos = c.find(call_name, after_list)
    if call_pos < 0:
        print(f"{label} runtime helper call is missing after argument-list allocation")
        raise SystemExit(1)
    pushes = c[after_list:call_pos].count("cap_list_push(")
    if pushes < required_pushes:
        print(f"{label} does not append every evaluated argument after list allocation")
        raise SystemExit(1)


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

query = re.search(r'CAP_LIT\("select \\?\?",\s*8\)', c)
query_arg = re.search(r'__auto_type\s+\w+\s*=\s*fn_make\(\)', c[query.end():]) if query else None
if not query:
    print("sql_query literal is missing from generated C")
    pos = c.find("cap_sql_query(")
    if pos >= 0:
        print(c[max(0, pos - 900):pos + 300])
    raise SystemExit(1)
if not query_arg:
    print("sql_query later argument is not materialised in a temporary after the query literal")
    pos = c.find("cap_sql_query(")
    if pos >= 0:
        print(c[max(0, pos - 1200):pos + 300])
    raise SystemExit(1)
query_arg_end = query.end() + query_arg.end()
check_special_order("sql_query", [query.end(), query_arg_end], "cap_sql_query(", 1)

program = re.search(r'CAP_LIT\("echo",\s*4\)', c)
dash = re.search(r'CAP_LIT\("--",\s*2\)', c[program.end():]) if program else None
if not program or not dash:
    print("run literal program or -- marker is missing from generated C")
    raise SystemExit(1)
dash_end = program.end() + dash.end()
run_arg = re.search(r'__auto_type\s+\w+\s*=\s*fn_make\(\)', c[dash_end:])
if not run_arg:
    print("run later argument is missing from generated C")
    raise SystemExit(1)
run_arg_end = dash_end + run_arg.end()
check_special_order("run", [program.end(), dash_end, run_arg_end], "cap_run(", 2)
print("lazy string literals and special literal-first calls are materialised in source order")
