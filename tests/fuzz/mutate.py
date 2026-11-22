#!/usr/bin/env python3
"""
Robustness fuzzer: takes every Capstan program in the repository, corrupts it
at random (deleting, duplicating, swapping and inserting tokens; flipping
bytes), and feeds the result to the compiler.

The compiler must:
  - never crash, hang, or stop on one of its own runtime checks (only exit 0 or 1)
  - whenever it accepts a program, produce C that the C compiler accepts

usage: mutate.py [iterations] [seed]
"""
import glob, os, random, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("CC", "cc")
VOCAB = ["{", "}", "(", ")", ";", ",", ".", "?", "<", ">", "=", "==", "+", "-", "*", "/", "%", "!", "&&",
         "if", "else", "while", "for", "return", "break", "let", "new", "none", "true", "policy", "protected",
         "authorize", "struct", "int", "string", "Tainted", "Secret", "List<int>", "Map<string>", "Grant<P>",
         "x", "main", '"s"', "'c'", "0", "9223372036854775808", "\\", '"', "/*", "*/", "//", "\n", "\x00", "\xff"]
TOKEN = re.compile(rb'"(?:[^"\\\n]|\\.)*"|//[^\n]*|/\*|\*/|[A-Za-z_][A-Za-z0-9_]*|\d+|\S|\s+')


def mutate(src, r):
    toks = TOKEN.findall(src)
    for _ in range(r.randint(1, 4)):
        if not toks:
            break
        k = r.randrange(6)
        i = r.randrange(len(toks))
        if k == 0:
            del toks[i:i + r.randint(1, 8)]
        elif k == 1:
            j = r.randrange(len(toks))
            toks[i:i] = toks[j:j + r.randint(1, 12)]
        elif k == 2:
            j = r.randrange(len(toks))
            toks[i], toks[j] = toks[j], toks[i]
        elif k == 3:
            toks.insert(i, r.choice(VOCAB).encode("latin-1"))
        elif k == 4:
            t = bytearray(toks[i])
            if t:
                t[r.randrange(len(t))] = r.randrange(256)
            toks[i] = bytes(t)
        else:
            toks[i] = r.choice(VOCAB).encode("latin-1")
    return b"".join(toks)


def main():
    iters = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    r = random.Random(seed)
    corpus = [open(p, "rb").read() for p in sorted(glob.glob(os.path.join(ROOT, "**/*.cap"), recursive=True))
              if "/fuzz/" not in p]
    capstanc = os.path.join(ROOT, "build/capstanc")
    accepted = rejected = 0
    with tempfile.TemporaryDirectory() as d:
        cap, c = os.path.join(d, "m.cap"), os.path.join(d, "m.c")
        for i in range(iters):
            src = mutate(r.choice(corpus), r)
            open(cap, "wb").write(src)
            mode = r.choice(["build", "test", "check"])
            try:
                p = subprocess.run([capstanc, mode, "-o", c, cap], capture_output=True, timeout=20)
            except subprocess.TimeoutExpired:
                p = None
            problem = None
            if p is None:
                problem = "compiler hung"
            elif p.returncode not in (0, 1):
                problem = f"compiler exited {p.returncode}: {p.stderr.decode(errors='replace')[-400:]}"
            elif p.returncode == 0 and mode != "check":
                accepted += 1
                b = subprocess.run([CC, "-std=gnu11", "-fsyntax-only", "-w", "-I" + os.path.join(ROOT, "runtime"), c],
                                   capture_output=True, timeout=60)
                if b.returncode != 0:
                    problem = "accepted program produced invalid C:\n" + b.stderr.decode(errors="replace")[:1500]
            elif p.returncode == 1:
                rejected += 1
            else:
                accepted += 1
            if problem:
                os.makedirs(os.path.join(ROOT, "tests/fuzz/failures"), exist_ok=True)
                path = os.path.join(ROOT, f"tests/fuzz/failures/mut_{seed}_{i}.cap")
                open(path, "wb").write(src)
                print(f"FAIL iteration {i} ({mode}) saved to {path}\n{problem}")
                sys.exit(1)
    print(f"mutation fuzz: {iters} corrupted programs, no crashes or hangs "
          f"({rejected} rejected with diagnostics, {accepted} accepted and produced valid C)")


if __name__ == "__main__":
    main()
