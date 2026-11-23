#!/usr/bin/env python3
"""
Differential fuzzer: generates random well-typed Capstan programs and runs each
one two independent ways:

  1. the native self-hosted compiler  -> C -> GCC/Clang -> native binary
  2. the stage-0 bootstrap translator -> Python

Both must print the same output and finish with the same exit code. That
includes the same safety stop (exit 101) on overflow, bad indexes, division by
zero, and so on.
The programs deliberately hit edge cases: values near the 64-bit limits,
negative indexes, empty slices, and map keys that are present or absent.

They also exercise what the compiler's range analysis reasons about, because
stage 0 has no range analysis and keeps every check: guards and early returns
before arithmetic, loops that run up to the 64-bit limits, and index loops whose
list shrinks in the body, in the condition or through a call. If the analysis
ever dropped a check that could fire, the two runs would disagree.

Every third program is also built with AddressSanitizer and UBSan (including
signed-overflow detection) and must behave identically. That catches an
unchecked operation that misbehaves even when the output happens to match:
signed overflow in C is undefined, and an out-of-bounds read may return a
plausible value.

usage: gen.py [count] [seed]
"""
import os, random, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("CC", "cc")
CAPSTANC = os.environ.get("CAPSTANC", os.path.join(ROOT, "build/capstanc"))   # another compiler, e.g. a mutant
BIG = [0, 1, 2, 3, 7, 10, 255, 1000, 65536, 2147483647, 4611686018427387904, 9223372036854775807]


class Gen:
    def __init__(self, rng):
        self.r = rng
        self.n = 0
        self.funcs = []          # (name, arity)

    def fresh(self, p="v"):
        self.n += 1
        return f"{p}{self.n}"

    def lit(self):
        r = self.r
        v = r.choice(BIG) if r.random() < 0.3 else r.randint(0, 50)
        return str(v) if r.random() < 0.8 else f"(0 - {v})"

    def int_expr(self, sc, d):
        r = self.r
        if d <= 0 or r.random() < 0.25:
            return r.choice(sc["ints"]) if sc["ints"] and r.random() < 0.6 else self.lit()
        k = r.randrange(10)
        if k <= 3:
            op = r.choice(["+", "-", "*", "/", "%", "+", "-"])
            rhs = self.int_expr(sc, d - 1)
            if op in "/%" and rhs == "0":
                rhs = "(0 + 0)"          # a literal zero divisor is rejected at compile time
            return f"({self.int_expr(sc, d - 1)} {op} {rhs})"
        if k == 4 and self.funcs:
            name, ar = r.choice(self.funcs)
            return f"{name}({', '.join(self.int_expr(sc, d - 1) for _ in range(ar))})"
        if k == 5 and sc["lists"]:
            xs = r.choice(sc["lists"])
            if r.random() < 0.85:
                return f"{xs}[safe_index({self.int_expr(sc, d - 1)}, {xs}.len())]"
            return f"{xs}[{self.int_expr(sc, d - 1)}]"
        if k == 6 and sc["strs"]:
            s = r.choice(sc["strs"])
            return f"{s}.len()" if r.random() < 0.5 else f"{s}.at(safe_index({self.int_expr(sc, d - 1)}, {s}.len()))"
        if k == 7:
            return f"(-{self.int_expr(sc, d - 1)})"
        if k == 8 and sc["lists"]:
            return f"{r.choice(sc['lists'])}.len()"
        return self.int_expr(sc, d - 1)

    def cond(self, sc, d):
        r = self.r
        k = r.randrange(5)
        if k <= 2 or d <= 0:
            return f"({self.int_expr(sc, 1)} {r.choice(['<', '<=', '>', '>=', '==', '!='])} {self.int_expr(sc, 1)})"
        if k == 3:
            return f"({self.cond(sc, d - 1)} {r.choice(['&&', '||'])} {self.cond(sc, d - 1)})"
        return f"(!{self.cond(sc, d - 1)})"

    def str_expr(self, sc, d):
        r = self.r
        k = r.randrange(5)
        if k == 0 and sc["strs"]:
            return r.choice(sc["strs"])
        if k == 1:
            return f"int_to_str({self.int_expr(sc, d)})"
        if k == 2 and sc["strs"]:
            s = r.choice(sc["strs"])
            return f"{s}.slice(0, safe_index({self.int_expr(sc, 1)}, {s}.len() + 1))"
        if k == 3 and sc["strs"]:
            return f"({r.choice(sc['strs'])} + \"{r.choice(['', 'x', '-', 'ab'])}\")"
        return '"' + r.choice(["alpha", "", "Grace", "a b", "0"]) + '"'

    def block(self, sc, d, ind, budget):
        out = []
        for _ in range(self.r.randint(1, budget)):
            out += self.stmt(sc, d, ind)
        return out

    def stmt(self, sc, d, ind):
        r, p = self.r, "    " * ind
        k = r.randrange(15)
        if k <= 1:
            v = self.fresh()
            line = f"{p}int {v} = {self.int_expr(sc, 3)};"
            sc["ints"].append(v)
            return [line]
        if k == 2 and sc["ints"]:
            v = r.choice(sc["mut"]) if sc["mut"] else None
            if v:
                return [f"{p}{v} {r.choice(['=', '+=', '-='])} {self.int_expr(sc, 2)};"]
        if k == 3:
            return [f"{p}println({self.str_expr(sc, 2)});"]
        if k == 4:
            return [f"{p}println(int_to_str({self.int_expr(sc, 3)}));"]
        if k == 5 and sc["lists"]:
            return [f"{p}{r.choice(sc['lists'])}.push({self.int_expr(sc, 2)});"]
        if k == 6 and sc["lists"]:
            xs = r.choice(sc["lists"])
            return [f"{p}if ({xs}.len() > 0) {{ {xs}[safe_index({self.int_expr(sc, 1)}, {xs}.len())] = {self.int_expr(sc, 2)}; }}"]
        if k == 7 and d > 0:
            inner = dict(sc, ints=list(sc["ints"]), strs=list(sc["strs"]))
            body = self.block(inner, d - 1, ind + 1, 3)
            inner2 = dict(sc, ints=list(sc["ints"]), strs=list(sc["strs"]))
            els = self.block(inner2, d - 1, ind + 1, 2)
            return [f"{p}if {self.cond(sc, 2)} {{"] + body + [f"{p}}} else {{"] + els + [f"{p}}}"]
        if k == 8 and d > 0:
            i = self.fresh("i")
            inner = dict(sc, ints=list(sc["ints"]) + [i], strs=list(sc["strs"]))
            body = self.block(inner, d - 1, ind + 1, 3)
            return [f"{p}for (int {i} = 0; {i} < {r.randint(0, 6)}; {i} += 1) {{"] + body + [f"{p}}}"]
        if k == 9 and sc["maps"]:
            m = sc["maps"][0]
            return [f'{p}{m}.set("k" + int_to_str({self.int_expr(sc, 1)} % 5), {self.int_expr(sc, 2)});']
        if k == 10 and sc["maps"]:
            m, v = sc["maps"][0], self.fresh("m")
            return [f'{p}if (let {v} = {m}.get("k" + int_to_str({self.int_expr(sc, 1)} % 5))) {{ println("hit " + int_to_str({v})); }} else {{ println("miss"); }}']
        if k == 12 and d > 0:
            # a loop at the edge of the 64-bit range, up or down
            i, a, b, step = self.fresh("i"), r.randint(0, 4), r.randint(0, 4), r.randint(1, 3)
            inner = dict(sc, ints=list(sc["ints"]) + [i], strs=list(sc["strs"]))
            body = self.block(inner, 0, ind + 1, 2) + [f"{p}    println(int_to_str({i} % 10));"]
            if r.random() < 0.5:
                head = f"for (int {i} = (9223372036854775807 - {a}); {i} {r.choice(['<', '<='])} (9223372036854775807 - {b}); {i} += {step})"
            else:
                head = f"for (int {i} = (0 - 9223372036854775807 + {a}); {i} {r.choice(['>', '>='])} (0 - 9223372036854775807 - 1 + {b}); {i} -= {step})"
            return [f"{p}{head} {{"] + body + [f"{p}}}"]
        if k == 13 and sc["lists"]:
            # an index loop; the list may shrink in the body, the condition or a call
            xs, j = r.choice(sc["lists"]), self.fresh("j")
            cond = f"{j} < {xs}.len()"
            if r.random() < 0.2:
                cond += f" && pop_ok({xs})"
            shrink = r.choice(["", "", f"{xs}.pop();", f"shrink({xs});", f"if (let {self.fresh('q')} = {xs}.pop()) {{ println(\"popped\"); }}", f"{xs}.clear();"])
            if shrink == f"{xs}.pop();":
                shrink = f"if ({xs}.len() > 5) {{ {xs}.remove_at(0); }}"
            lines = [f"{p}for (int {j} = {r.choice(['0', '0', '1'])}; {cond}; {j} += 1) {{",
                     f"{p}    println(int_to_str({xs}[{j}] % 1000));"]
            if shrink:
                lines.append(f"{p}    {shrink}")
                lines.append(f"{p}    println(int_to_str({xs}[{j}] % 1000));")
            return lines + [f"{p}}}"]
        if k == 14:
            # a guard on a variable that never changes, then arithmetic it might justify
            fixed = [v for v in sc["ints"] if v not in sc["mut"]]
            if fixed:
                v = r.choice(fixed)
                op, lit = r.choice(["<", "<=", ">", ">=", "==", "!="]), self.lit()
                aop = r.choice(["+", "-", "*", "/", "%"])
                k1, k2 = self.lit(), self.lit()
                if aop in "/%":
                    k1, k2 = (x if x != "0" else "(0 + 0)" for x in (k1, k2))
                return [f"{p}if ({v} {op} {lit}) {{ println(int_to_str({v} {aop} {k1})); }} else {{ println(int_to_str({v} {aop} {k2})); }}"]
        if k == 11:
            v = self.fresh("s")
            line = f"{p}string {v} = {self.str_expr(sc, 2)};"
            sc["strs"].append(v)
            return [line]
        return [f"{p}println(\"tick\");"]

    def function(self, idx):
        ar = self.r.randint(1, 3)
        params = [self.fresh("p") for _ in range(ar)]
        sc = {"ints": list(params), "mut": [], "strs": [], "lists": [], "maps": []}
        body = []
        for q in params:
            if self.r.random() < 0.5:     # an early return the range analysis learns from
                body.append(f"    if ({q} {self.r.choice(['<', '<=', '>', '>='])} {self.lit()}) {{ return {self.int_expr(sc, 2)}; }}")
        body += self.block(sc, 1, 1, 4)
        ret = self.int_expr(sc, 3)
        name = f"f{idx}"
        src = [f"int {name}({', '.join('int ' + q for q in params)}) {{"] + body + [f"    return {ret};", "}"]
        self.funcs.append((name, ar))
        return src

    def program(self):
        out = [
            "// generated by tests/fuzz/gen.py",
            "int safe_index(int i, int n) {",
            "    if (n <= 0) { return 0; }",
            "    int m = i % n;",
            "    if (m < 0) { return m + n; }",
            "    return m;",
            "}",
            "void shrink(List<int> ys) {",
            "    if (ys.len() > 0) { ys.remove_at(0); }",
            "}",
            "bool pop_ok(List<int> ys) {",
            "    if (let _q = ys.pop()) { return true; }",
            "    return false;",
            "}",
        ]
        for i in range(self.r.randint(0, 3)):
            out += self.function(i)
        sc = {"ints": ["acc"], "mut": ["acc"], "strs": ["label"], "lists": ["xs"], "maps": ["m"]}
        out += ["int main() {", "    int acc = 1;", '    string label = "start";',
                "    List<int> xs = new List<int>();", "    xs.push(3); xs.push(0 - 4); xs.push(9);",
                "    Map<int> m = new Map<int>();"]
        out += self.block(sc, 2, 1, 12)
        out += ['    println("acc " + int_to_str(acc) + " " + label + " " + int_to_str(xs.len()));', "    return 0;", "}"]
        return "\n".join(out) + "\n"


class Ran:
    def __init__(self, returncode, stdout, stderr):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _limit_output():
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))   # a runaway writer gets SIGXFSZ


def run(cmd, input=None, timeout=30, env=None, cwd=None):
    """Run cmd with its output going to files capped at 64 MB, so a runaway program
    (a mutant's, say) cannot exhaust this process's memory. None on timeout."""
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            p = subprocess.run(cmd, input=input, stdout=out, stderr=err, timeout=timeout, env=env, cwd=cwd,
                               preexec_fn=_limit_output)
        except subprocess.TimeoutExpired:
            return None
        out.seek(0)
        err.seek(0)
        return Ran(p.returncode, out.read(8 << 20), err.read(1 << 20))


def _run_or_raise(cmd, **kw):
    r = run(cmd, **kw)
    if r is None:
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout", 30))
    return r


SAN = ["-O1", "-g", "-fsanitize=address,undefined", "-fsanitize=signed-integer-overflow,shift,bounds",
       "-fno-sanitize-recover=all", "-fno-omit-frame-pointer"]
SAN_ENV = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:detect_stack_use_after_return=0", UBSAN_OPTIONS="print_stacktrace=1")
_san_ok = None


def sanitizers_available(d):
    global _san_ok
    if _san_ok is None:
        probe = os.path.join(d, "probe.c")
        open(probe, "w").write("int main(void) { return 0; }\n")
        _san_ok = _run_or_raise([CC] + SAN + [probe, "-o", os.path.join(d, "probe")]).returncode == 0
    return _san_ok


def check(src, d, sanitize=False):
    cap = os.path.join(d, "p.cap")
    open(cap, "w").write(src)
    c = _run_or_raise([CAPSTANC, "build", "-o", os.path.join(d, "p.c"), cap])
    if c.returncode != 0:
        return "native compiler rejected a well-typed program:\n" + c.stdout.decode(errors="replace")
    b = _run_or_raise([CC, "-std=gnu11", "-O1", "-w", "-I" + os.path.join(ROOT, "runtime"), os.path.join(d, "p.c"), "-o", os.path.join(d, "p")])
    if b.returncode != 0:
        return "generated C did not compile:\n" + b.stderr.decode(errors="replace")[:2000]
    t = _run_or_raise([sys.executable, "-I", os.path.join(ROOT, "bootstrap/capstan0.py"), os.path.join(d, "p0.py"), cap])
    if t.returncode != 0:
        return "stage 0 failed to translate:\n" + t.stderr.decode(errors="replace")
    n = _run_or_raise([os.path.join(d, "p")])
    py = _run_or_raise([sys.executable, "-I", os.path.join(d, "p0.py")])
    if n.returncode not in (0, 101):
        return f"native program crashed (exit {n.returncode})"
    if (n.stdout, n.returncode) != (py.stdout, py.returncode):
        return (f"native and stage 0 disagree: exit {n.returncode} vs {py.returncode}\n--- native\n"
                + n.stdout.decode(errors="replace")[-1500:] + "\n--- stage0\n" + py.stdout.decode(errors="replace")[-1500:]
                + "\n" + py.stderr.decode(errors="replace")[-500:])
    if sanitize and sanitizers_available(d):
        s = _run_or_raise([CC, "-std=gnu11", "-w", "-I" + os.path.join(ROOT, "runtime")] + SAN + [os.path.join(d, "p.c"), "-o", os.path.join(d, "ps")])
        if s.returncode != 0:
            return "generated C did not compile with sanitizers:\n" + s.stderr.decode(errors="replace")[:2000]
        ns = run([os.path.join(d, "ps")], timeout=120, env=SAN_ENV)
        if ns is None:
            return "sanitized build timed out"
        if (ns.stdout, ns.returncode) != (n.stdout, n.returncode):
            return (f"sanitized build differs (exit {ns.returncode} vs {n.returncode}): undefined behaviour or a bad access in generated code\n"
                    + ns.stderr.decode(errors="replace")[-2500:])
    return None


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    stops = 0
    for i in range(count):
        src = Gen(random.Random(seed * 100003 + i)).program()
        with tempfile.TemporaryDirectory() as d:
            err = check(src, d, sanitize=(i % 3 == 0))
            if err is None and os.path.exists(os.path.join(d, "p")):
                if _run_or_raise([os.path.join(d, "p")]).returncode == 101:
                    stops += 1
        if err:
            keep = os.environ.get("FUZZ_FAILURES", os.path.join(ROOT, "tests/fuzz/failures"))
            os.makedirs(keep, exist_ok=True)
            path = os.path.join(keep, f"gen_{seed}_{i}.cap")
            open(path, "w").write(src)
            print(f"FAIL program {i} (seed {seed}) saved to {path}\n{err}")
            sys.exit(1)
    san = f", {(count + 2) // 3} also clean under ASan+UBSan" if _san_ok else ""
    print(f"differential fuzz: {count} random programs agree (native vs stage 0){san}; {stops} stopped safely at run time")


if __name__ == "__main__":
    main()
