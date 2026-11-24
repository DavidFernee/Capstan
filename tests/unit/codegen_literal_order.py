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


def ordered(label, matches, required_pushes):
    positions = [m.end() for m in matches]
    if any(p <= 0 for p in positions) or positions != sorted(positions):
        print(f"{label} operands or internal allocation are missing/out of order")
        for match in matches:
            if match is not None:
                start = max(0, match.start() - 160)
                end = min(len(c), match.end() + 420)
                print(c[start:end])
        raise SystemExit(1)
    list_pos = c.find("cap_list_new()", positions[-2])
    call_name = "cap_sql_query(" if label == "sql_query" else "cap_run("
    call_pos = c.find(call_name, list_pos)
    if list_pos < 0 or call_pos < 0 or c.find("cap_list_push(", list_pos, call_pos) < 0:
        print(f"{label} does not populate its argument list after source evaluation")
        raise SystemExit(1)
    if c[list_pos:call_pos].count("cap_list_push(") < required_pushes:
        print(f"{label} does not append every evaluated argument")
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

query = re.search(r'CAP_LIT\("select \?",\s*8\)', c)
query_arg = re.search(r'__auto_type\s+\w+\s*=\s*fn_make\(\)', c[query.end():]) if query else None
if not query or not query_arg:
    print("sql_query literal or later argument is missing from generated C")
    raise SystemExit(1)
query_arg_start = query.end() + query_arg.start()
query_arg_end = query.end() + query_arg.end()
query_list = re.search(r'CapList\s*\*\w+\s*=\s*cap_list_new\(\)', c[query_arg_end:])
if not query_list:
    print("sql_query parameter list is not allocated after source arguments")
    raise SystemExit(1)
query_list_start = query_arg_end + query_list.start()
query_call = re.search(r'cap_sql_query\(', c[query_list_start:])
if not query_call:
    print("cap_sql_query call is missing")
    raise SystemExit(1)
ordered(
    "sql_query",
    [query, query_arg, query_list],
    1,
)

program = re.search(r'CAP_LIT\("echo",\s*4\)', c)
dash = re.search(r'CAP_LIT\("--",\s*2\)', c[program.end():]) if program else None
run_arg = re.search(r'__auto_type\s+\w+\s*=\s*fn_make\(\)', c[program.end() + dash.end():]) if program and dash else None
if not program or not dash or not run_arg:
    print("run literal program, -- marker or later argument is missing from generated C")
    raise SystemExit(1)
program_arg = re.search(r'__auto_type\s+\w+\s*=\s*CAP_LIT\("--",\s*2\)', c[program.end():])
dash_end = program.end() + dash.end()
run_arg_abs_end = dash_end + run_arg.end()
run_list = re.search(r'CapList\s*\*\w+\s*=\s*cap_list_new\(\)', c[run_arg_abs_end:])
if not run_list:
    print("run argv list is not allocated after source arguments")
    raise SystemExit(1)
run_list_abs = run_arg_abs_end + run_list.start()
run_call = re.search(r'cap_run\(', c[run_list_abs:])
if not run_call:
    print("cap_run call is missing")
    raise SystemExit(1)
ordered(
    "run",
    [program, program_arg, run_arg, run_list],
    2,
)
print("lazy string literals and special literal-first calls are materialised in source order")
