#!/usr/bin/env python3
"""Line coverage of the compiler, the formatter and the runtime.

    coverage.py [--check]

Builds instrumented copies (gcc --coverage), runs the suite's workloads through
them and reads the results back with gcov. The generated C carries #line
directives, so coverage is reported against the Capstan source lines themselves.

  compiler   build/stage3.c, run on every test program, every example, its own sources,
             the CWE atlas and short differential and mutation fuzzing campaigns
  formatter  build/fmt.c, run on the formatter tests and the repository's sources
  runtime    runtime/*.h, through the runtime unit tests and every program that runs

Writes docs/COVERAGE.md (per-file totals and the lines no test reaches). With
--check, fails if any file falls below its floor in tests/coverage_floors.txt.
"""
import glob, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GCC = os.environ.get("COVERAGE_CC", "gcc")
GCOV = os.environ.get("GCOV", "gcov")
RT = os.path.join(ROOT, "runtime")
FLAGS = ["-O0", "--coverage", "-std=gnu11", "-w", "-I" + RT]
SRC = [os.path.join(ROOT, f"compiler/{n}.cap") for n in ("ast", "lexer", "parser", "checker", "ranges", "codegen", "main")]


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, timeout=300, **kw)


def tests(*dirs):
    return sorted(p for d in dirs for p in glob.glob(os.path.join(ROOT, d, "*.cap")))


def gcov_lines(objdir, counts):
    """Merge gcov's per-line counts for every .gcda in objdir into counts[file][line]."""
    for gcda in sorted(glob.glob(os.path.join(objdir, "*.gcda"))):
        res = run([GCOV, "--stdout", "-o", objdir, gcda], cwd=ROOT)
        src = None
        for line in res.stdout.decode(errors="replace").splitlines():
            m = re.match(r"\s*([^:]+):\s*(\d+):(.*)$", line)
            if not m:
                continue
            count, num = m.group(1).strip(), int(m.group(2))
            if num == 0:
                if m.group(3).startswith("Source:"):
                    src = os.path.relpath(os.path.join(ROOT, m.group(3)[7:].strip()), ROOT)
                continue
            if count == "-" or src is None:
                continue
            hit = count not in ("#####", "=====")
            per = counts.setdefault(src, {})
            per[num] = per.get(num, False) or hit
        os.remove(gcda)


def compiler(work, counts):
    d = os.path.join(work, "compiler")
    os.makedirs(d)
    shutil.copy(os.path.join(ROOT, "build/stage3.c"), d)
    exe = os.path.join(d, "capstanc")
    r = run([GCC] + FLAGS + [os.path.join(d, "stage3.c"), "-o", exe])
    if r.returncode:
        sys.exit("instrumented compiler did not build:\n" + r.stderr.decode()[:2000])
    out = os.path.join(work, "out.c")
    jobs = []
    for f in tests("tests/accept", "tests/gc", "tests/runtime", "tests/reject", "tests/diagnostics", "examples", "bench", "tests/fmt", "tools"):
        flags = re.findall(r"^// flags: (.*)$", open(f, encoding="latin-1").read(), re.M)
        extra = flags[0].split() if flags else []
        jobs += [["build", "-o", out] + extra + [f], ["check", "--strict", "--release", f], ["test", "-o", out, f]]
    jobs += [["build", "-o", out] + SRC, ["check", "--strict", "--release"] + SRC, ["build", "--keep-checks", "-o", out] + SRC,
             ["build", "-o", out] + SRC[:-1] + [os.path.join(ROOT, "tests/unit/ranges_props.cap")],
             [], ["version"], ["bogus"], ["build"], ["build", "-o"], ["check", os.path.join(work, "missing.cap")]]
    for j in jobs:
        run([exe] + j, cwd=ROOT)
    env = dict(os.environ, CAPSTANC=exe, FUZZ_FAILURES=os.path.join(work, "fuzz-failures"))
    deep = os.path.join(work, "deep.cap")
    open(deep, "w").write("int main() { return " + "(" * 2000 + "1" + ")" * 2000 + "; }\n")
    run([exe, "check", deep])
    for script, args in (("tests/cwe/atlas.py", []), ("tests/fuzz/gen.py", ["40", "7"]), ("tests/fuzz/mutate.py", ["600", "7"]),
                         ("tests/unit/lint_table.py", []), ("tests/unit/ranges_props.py", [])):
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, script)] + args, capture_output=True, timeout=3000, env=env, cwd=ROOT)
    gcov_lines(d, counts)


def formatter(work, counts):
    d = os.path.join(work, "fmt")
    os.makedirs(d)
    if not os.path.exists(os.path.join(ROOT, "build/fmt.c")):
        run(["make", "-s", "-C", ROOT, "fmt"])
    shutil.copy(os.path.join(ROOT, "build/fmt.c"), d)
    exe = os.path.join(d, "capstanfmt")
    if run([GCC] + FLAGS + [os.path.join(d, "fmt.c"), "-o", exe]).returncode:
        sys.exit("instrumented formatter did not build")
    scratch = os.path.join(work, "fmt-inputs")
    os.makedirs(scratch)
    files = tests("tests/fmt", "tests/accept", "tests/reject", "tests/diagnostics", "compiler", "tools")
    for i, f in enumerate(files):
        shutil.copy(f, os.path.join(scratch, f"{i}.cap"))
    copies = sorted(glob.glob(os.path.join(scratch, "*.cap")))
    run([exe, "--check"] + copies)
    run([exe] + copies)
    for j in ([], ["--help"], [os.path.join(work, "missing.cap")]):
        run([exe] + j)
    run([sys.executable, "-I", os.path.join(ROOT, "tests/fmt/perturb.py"), exe, "2", "1"] + tests("compiler"), cwd=ROOT)
    run([sys.executable, "-I", os.path.join(ROOT, "tests/fmt/perturb.py"), "--corrupt", exe, "3", "1"] + tests("tests/accept"), cwd=ROOT)
    gcov_lines(d, counts)


def runtime(work, counts):
    d = os.path.join(work, "rt")
    os.makedirs(d)
    capstanc = os.path.join(ROOT, "build/capstanc")
    progs = [(f, "build") for f in tests("tests/accept", "tests/gc", "tests/runtime", "tests/io")] + [(f, "test") for f in tests("examples")]
    for i, (f, mode) in enumerate(progs):
        c = os.path.join(d, f"p{i}.c")
        if run([capstanc, mode, "-o", c, f]).returncode:
            continue
        exe = os.path.join(d, f"p{i}")
        if run([GCC] + FLAGS + [c, "-o", exe], cwd=d).returncode:
            continue
        env = dict(os.environ, CAPSTAN_GC_STATS="1")
        for kv in re.findall(r"^// env: (.*)$", open(f, encoding="latin-1").read(), re.M):
            for pair in kv.split():
                k, _, v = pair.partition("=")
                env[k] = v
        stdin = open(f[:-4] + ".in", "rb").read() if os.path.exists(f[:-4] + ".in") else b"line one\nline two\n"
        args = [tempfile.mkdtemp(dir=d)] if "/tests/io/" in f else []
        if i == 0:
            env["CAPSTAN_MAX_HEAP"] = "1G"
        try:
            subprocess.run([exe] + args, capture_output=True, timeout=120, env=env, input=stdin)
            if "tests/gc/" not in f and "// env:" not in open(f, encoding="latin-1").read():   # collector stress (too slow for the big ones at -O0)
                subprocess.run([exe], capture_output=True, timeout=120, env=dict(env, CAPSTAN_GC_STRESS="7"))
        except subprocess.TimeoutExpired:
            print(f"  note: {os.path.relpath(f, ROOT)} timed out under coverage")
    unit = os.path.join(d, "unit")
    if not run([GCC] + FLAGS + [os.path.join(ROOT, "tests/unit/test_runtime.c"), "-o", unit], cwd=d).returncode:
        run([unit], cwd=d)
    gcov_lines(d, counts)


def ranges_of(nums):
    out, start, prev = [], None, None
    for n in nums:
        if start is None:
            start = prev = n
        elif n == prev + 1:
            prev = n
        else:
            out.append(f"{start}" if start == prev else f"{start}–{prev}")
            start = prev = n
    if start is not None:
        out.append(f"{start}" if start == prev else f"{start}–{prev}")
    return out


def main():
    check = "--check" in sys.argv
    work = tempfile.mkdtemp()
    groups = {}
    for name, fn in (("compiler", compiler), ("formatter", formatter), ("runtime", runtime)):
        counts = {}
        fn(work, counts)
        groups[name] = counts
    want = {"compiler": "compiler/", "formatter": "tools/", "runtime": "runtime/"}
    lines = ["# Coverage", "", "Generated by `tests/coverage.py`: line coverage of the compiler, the formatter and the",
             "runtime under the test suite's workloads (see [TESTING.md](TESTING.md)). Lines are Capstan source",
             "lines for the compiler and formatter, through the generated C's `#line` mapping.", "",
             "| File | Lines | Covered | Coverage |", "|---|---|---|---|"]
    detail, summary = [], {}
    for name, counts in groups.items():
        for src in sorted(counts):
            if not src.startswith(want[name]):
                continue
            per = counts[src]
            total, hit = len(per), sum(per.values())
            pct = 100.0 * hit / total if total else 100.0
            summary[src] = pct
            lines.append(f"| `{src}` | {total} | {hit} | {pct:.1f}% |")
            missed = ranges_of(sorted(n for n, h in per.items() if not h))
            if missed:
                detail.append(f"- `{src}`: " + ", ".join(missed))
    lines += ["", "## Lines no test reaches", ""] + detail
    open(os.path.join(ROOT, "docs/COVERAGE.md"), "w").write("\n".join(lines) + "\n")
    shutil.rmtree(work, ignore_errors=True)
    for src, pct in summary.items():
        print(f"  {src:28s} {pct:5.1f}%")
    if check:
        floors = {}
        for line in open(os.path.join(ROOT, "tests/coverage_floors.txt")):
            line = line.split("#")[0].split()
            if len(line) == 2:
                floors[line[0]] = float(line[1])
        low = [f"{s} {summary.get(s, 0):.1f}% < floor {f}%" for s, f in floors.items() if summary.get(s, 0) < f]
        if low:
            print("coverage below floor: " + "; ".join(low))
            return 1
    total = len(summary)
    print(f"coverage: {total} files measured; report in docs/COVERAGE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
