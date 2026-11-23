#!/usr/bin/env python3
"""Mutation testing of the compiler: does the test suite notice a compiler bug?

    mutate_compiler.py COUNT SEED [file.cap[:FROM-TO] ...]
    mutate_compiler.py --replay REPORT      re-run the survivors listed in an earlier report

Makes COUNT mutants of the compiler, each with one small change of the kind a
programmer might make by mistake (a flipped comparison, && for ||, an inverted
boolean, an off-by-one, a deleted diagnostic or guard). Each mutant is built
and run against the suite's behavioural oracles until one fails ("killed"):

  1. every reject and diagnostics test must still fail with its expected message, and every
     recovery test must report exactly its syntax errors;
  2. every runtime test must still stop with its CWE;
  3. every conformance and io program must still give its expected output;
  4. the range-analysis counts must still hold;
  5. the compiler's own sources must still pass --strict --release (no false warnings);
  6. the lint table, the examples (--release and their tests), the interval property
     tests (built from the mutant's own sources) and the CWE atlas must still pass;
  7. a short differential fuzzing campaign against stage 0 must still agree.

A mutant that survives all of them points at behaviour no test pins down. The
report lists every survivor with its change, so it can be turned into a test or
recognised as equivalent (a change that cannot alter behaviour). Mutants that do
not compile are discarded and replaced.

Defaults to mutating compiler/ranges.cap and compiler/checker.cap.
"""
import glob, os, random, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CC = os.environ.get("CC", "cc")
NAMES = ("ast", "lexer", "parser", "checker", "ranges", "codegen", "main")
RT = os.path.join(ROOT, "runtime")
CF = ["-O1", "-std=gnu11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-Wno-unused-parameter", "-Wno-unused-variable",
      "-Wno-unused-but-set-variable", "-Wno-infinite-recursion", "-Wno-for-loop-analysis", "-I" + RT]   # as in tests/run.sh

# (pattern, replacement) pairs applied at one match each.
OPERATORS = [
    (r"(?<![<>=!])<(?![<=])(?=\s)", "<="), (r"<=", "<"), (r"(?<![<>=!-])>(?![>=])(?=\s)", ">="), (r">=", ">"),
    (r"==", "!="), (r"!=", "=="), (r"&&", "||"), (r"\|\|", "&&"),
    (r"\btrue\b", "false"), (r"\bfalse\b", "true"),
    (r"(?<=[\s(])!(?=[a-z(])", ""),
    (r"\+ 1\b", "- 1"), (r"- 1\b", "+ 1"), (r"\+=", "-="),
    (r"return true;", "return false;"), (r"return false;", "return true;"),
]
LINE_DELETIONS = [r"^\s*(error_at|warn_at|report_at|report)\(", r"^\s*if \(.*\) \{ return [^}]*; \}$", r"^\s*(mark|learn|forget|rg_declare|bound)\("]


def sites(text):
    """Every possible single mutation of a file: (kind, start, end, replacement, description)."""
    out = []
    lines = text.split("\n")
    offsets, pos = [], 0
    for l in lines:
        offsets.append(pos)
        pos += len(l) + 1
    for n, line in enumerate(lines):
        code = line.split("//")[0]
        if not code.strip() or code.lstrip().startswith(("struct ", "const ", "import ")):
            continue
        # skip string literals: only mutate outside quotes
        quoted = [m.span() for m in re.finditer(r'"(?:\\.|[^"\\])*"', code)]
        for pat, rep in OPERATORS:
            for m in re.finditer(pat, code):
                if any(a <= m.start() < b for a, b in quoted):
                    continue
                out.append((offsets[n] + m.start(), offsets[n] + m.end(), rep, f"line {n + 1} col {m.start() + 1}: '{m.group(0)}' -> '{rep}'"))
        for pat in LINE_DELETIONS:
            if re.search(pat, code) and code.rstrip().endswith((";", "}")) and code.count("{") == code.count("}"):
                out.append((offsets[n], offsets[n] + len(line), "", f"line {n + 1}: deleted '{line.strip()[:70]}'"))
    return out


class Ran:
    def __init__(self, returncode, stdout, stderr):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def _limit_output():
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 << 20, 64 << 20))   # a runaway writer gets SIGXFSZ


def run(cmd, input=None, timeout=60, env=None, cwd=None):
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


def expect(path, key):
    m = re.search(rf"^// {key}: (.*)$", open(path, encoding="latin-1").read(), re.M)
    return m.group(1).strip() if m else None


def oracles(mc, d):
    """Run the oracles with mutant compiler mc; return why it was killed, or None."""
    out = os.path.join(d, "o.c")
    exe = os.path.join(d, "o")
    for f in sorted(glob.glob(os.path.join(ROOT, "tests/reject/*.cap")) + glob.glob(os.path.join(ROOT, "tests/diagnostics/*.cap"))):
        flags = (expect(f, "flags") or "").split()
        r = run([mc, "build", "-o", out] + flags + [f])
        if r is None or r.returncode != 1 or expect(f, "expect") not in r.stdout.decode(errors="replace"):
            return f"{os.path.relpath(f, ROOT)} no longer rejected as expected"
    for f in sorted(glob.glob(os.path.join(ROOT, "tests/recovery/*.cap"))):
        want = re.findall(r"^// error: (.*)$", open(f, encoding="latin-1").read(), re.M)
        r = run([mc, "check", f])
        got = re.findall(r"^\S*\.cap:(\d+:\d+): error: (.*)$", r.stdout.decode(errors="replace"), re.M) if r else None
        if r is None or r.returncode != 1 or [f"{a}: {m}" for a, m in got] != want:
            return f"{os.path.relpath(f, ROOT)} reports different syntax errors"
    many = os.path.join(d, "many.cap")
    with open(many, "w") as fh:
        fh.write("".join(f"int f{i}() {{ return +; ; }}\n" for i in range(80)))
    r = run([mc, "check", many])
    if r is None or r.stdout.decode(errors="replace").count(": error: ") != 50:
        return "a file with 80 syntax errors no longer reports exactly 50"
    with open(many, "w") as fh:
        fh.write("int main() {\n" + "".join(f"  int x{i} = +;\n" for i in range(80)) + "  return 0;\n}\n")
    r = run([mc, "check", many])
    if r is None or r.stdout.decode(errors="replace").count(": error: ") != 50:
        return "a block with 80 syntax errors no longer reports exactly 50"
    with open(many, "w") as fh:
        fh.write("int main() { return " + "(" * 1100 + " 1; }\nint f() { return +; }\n")
    r = run([mc, "check", many])
    if r is None or r.stdout.decode(errors="replace").count(": error: ") != 1:
        return "too-deep nesting no longer stops parsing with one error"
    for f in sorted(glob.glob(os.path.join(ROOT, "tests/runtime/*.cap"))):
        r = run([mc, "build", "-o", out, f])
        if r is None or r.returncode != 0 or run([CC] + CF + [out, "-o", exe]).returncode != 0:
            return f"{os.path.relpath(f, ROOT)} no longer compiles"
        env = dict(os.environ)
        for kv in (expect(f, "env") or "").split():
            k, _, v = kv.partition("=")
            env[k] = v
        p = run([exe], env=env)
        if p is None or p.returncode != 101 or expect(f, "expect-runtime") not in p.stderr.decode(errors="replace"):
            return f"{os.path.relpath(f, ROOT)} no longer stops with {expect(f, 'expect-runtime')}"
    for f in sorted(glob.glob(os.path.join(ROOT, "tests/accept/*.cap")) + glob.glob(os.path.join(ROOT, "tests/io/*.cap"))):
        r = run([mc, "build", "-o", out] + (expect(f, "flags") or "").split() + [f])
        if r is None or r.returncode != 0 or run([CC] + CF + [out, "-o", exe]).returncode != 0:
            return f"{os.path.relpath(f, ROOT)} no longer compiles"
        io = "/tests/io/" in f
        stdin = open(f[:-4] + ".in", "rb").read() if io else b""
        scratch = tempfile.mkdtemp(dir=d)
        p = run([exe] + ([scratch] if io else []), input=stdin)
        if p is None or p.stdout != open(f[:-4] + ".out", "rb").read():
            return f"{os.path.relpath(f, ROOT)} output changed"
        want = expect(f, "expect-proved")
        if want is not None and len(re.findall(r"cap_[a-z_]*_proved\(", open(out).read())) != int(want):
            return f"{os.path.relpath(f, ROOT)} proves a different number of checks"
    src = [os.path.join(ROOT, f"compiler/{n}.cap") for n in NAMES]
    r = run([mc, "check", "--strict", "--release"] + src)
    if r is None or r.returncode != 0:
        return "the compiler's own sources no longer pass --strict --release"
    for f in sorted(glob.glob(os.path.join(ROOT, "examples/*.cap"))):
        r = run([mc, "check", "--release", f])
        t = run([mc, "test", "-o", out, f])
        if r is None or t is None or r.returncode or t.returncode or run([CC] + CF + [out, "-o", exe]).returncode:
            return f"{os.path.relpath(f, ROOT)} no longer passes --release"
        p = run([exe])
        if p is None or p.returncode != 0:
            return f"{os.path.relpath(f, ROOT)} tests fail"
    env = dict(os.environ, CAPSTANC=mc, CAPSTAN_SRC=os.path.join(d, "compiler"), FUZZ_FAILURES=os.path.join(d, "fuzz-failures"))
    for script, what in (("tests/unit/lint_table.py", "the lint table"), ("tests/unit/ranges_props.py", "the interval property tests"),
                         ("tests/cwe/atlas.py", "the CWE atlas")):
        p = run([sys.executable, "-I", os.path.join(ROOT, script)], env=env, timeout=1200)
        if p is None or p.returncode != 0:
            return f"{what} failed"
    p = run([sys.executable, "-I", os.path.join(ROOT, "tests/fuzz/gen.py"), "30", "11"], env=env, timeout=900)
    if p is None or p.returncode != 0:
        return "differential fuzzing found a disagreement"
    return None


def build_mutant(src_texts, target, mutation, d):
    start, end, rep, _ = mutation
    srcdir = os.path.join(d, "compiler")
    os.makedirs(srcdir, exist_ok=True)
    for n, text in src_texts.items():
        if n == target:
            text = text[:start] + rep + text[end:]
        open(os.path.join(srcdir, n + ".cap"), "w").write(text)
    c = os.path.join(d, "mutant.c")
    r = run([os.path.join(ROOT, "build/capstanc"), "build", "-o", c] + [os.path.join(srcdir, n + ".cap") for n in NAMES], cwd=d)
    if r is None or r.returncode != 0:
        return None
    exe = os.path.join(d, "capstanc")
    if run([CC, "-O1", "-std=gnu11", "-w", "-I" + RT, c, "-o", exe], timeout=600).returncode != 0:
        return None
    return exe


def replay(log):
    """Mutants named by SURVIVED lines of an earlier report, to check they are now killed."""
    texts = {n: open(os.path.join(ROOT, f"compiler/{n}.cap")).read() for n in NAMES}
    wanted = []
    for line in open(log):
        m = re.search(r"SURVIVED (\w+)\.cap (line \d+(?: col \d+)?: .*)$", line.rstrip())
        if m:
            wanted.append((m.group(1), m.group(2)))
    items = []
    for target, desc in wanted:
        strip = re.sub(r" col \d+", "", desc)
        hits = [s for s in sites(texts[target]) if s[3] == desc or re.sub(r" col \d+", "", s[3]) == strip and " col " not in desc]
        items += [(target, h) for h in hits]
    return texts, items


def main():
    # A mutant may loop while allocating; cap every compiler and program it builds
    # well below the machine's memory so that only the mutant fails.
    os.environ.setdefault("CAPSTAN_MAX_HEAP", "1G")
    if sys.argv[1] == "--replay":
        texts, pool = replay(sys.argv[2])
        count, seed = len(pool), 0
        return campaign(texts, pool, count, seed)
    count, seed = int(sys.argv[1]), int(sys.argv[2])
    targets = sys.argv[3:] or ["compiler/ranges.cap", "compiler/checker.cap"]
    texts = {n: open(os.path.join(ROOT, f"compiler/{n}.cap")).read() for n in NAMES}
    r = random.Random(seed)
    pool = []
    for t in targets:        # file.cap, or file.cap:FROM-TO to mutate only those lines
        path, _, span = t.partition(":")
        name = os.path.basename(path)[:-4]
        lo, _, hi = span.partition("-")
        for site in sites(texts[name]):
            line = int(re.match(r"line (\d+)", site[3]).group(1))
            if not span or int(lo) <= line <= int(hi or lo):
                pool.append((name, site))
    r.shuffle(pool)
    return campaign(texts, pool, count, seed)


def campaign(texts, pool, count, seed):
    work = tempfile.mkdtemp()
    results, i = [], 0

    def one(item):
        target, mutation = item
        d = tempfile.mkdtemp(dir=work)
        mc = build_mutant(texts, target, mutation, d)
        if mc is None:
            shutil.rmtree(d, ignore_errors=True)
            return None
        why = oracles(mc, d)
        shutil.rmtree(d, ignore_errors=True)
        return (target, mutation[3], why)

    jobs = int(os.environ.get("JOBS", "2"))
    with ThreadPoolExecutor(jobs) as ex:
        while len(results) < count and i < len(pool):
            batch = pool[i:i + jobs * 2]
            i += len(batch)
            for res in ex.map(one, batch):
                if res is not None and len(results) < count:
                    results.append(res)
                    status = "killed  " if res[2] else "SURVIVED"
                    print(f"  {status} {res[0]}.cap {res[1]}" + (f"  ({res[2]})" if res[2] else ""), flush=True)
    killed = sum(1 for _, _, why in results if why)
    print(f"compiler mutation testing: {killed} of {len(results)} mutants killed ({100.0 * killed / max(1, len(results)):.0f}%), seed {seed}")
    shutil.rmtree(work, ignore_errors=True)
    return 0 if killed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
