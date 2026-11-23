#!/usr/bin/env python3
"""Whitespace and corruption fuzzing for capstan fmt.

    perturb.py FMT VARIANTS SEED file.cap...
    perturb.py --corrupt FMT VARIANTS SEED file.cap...

Each file must already be formatted. For every file, VARIANTS copies are made
with their whitespace scrambled (indentation, spacing between tokens, tabs,
trailing whitespace, carriage returns, extra blank lines) without changing any
token. Formatting a copy must give back the original byte for byte.

With --corrupt, copies get random byte edits instead. The formatter must then
either format the copy (and leave it formatted) or refuse it with exit code 2;
it must never crash, stop on a runtime check or hang."""
import os, random, re, subprocess, sys, tempfile

TWO = ["&&", "||", "==", "!=", "<=", ">=", "+=", "-=", "++", "--", "<<"]
ONE = "{}()[];,.:?<>=+-*/%!&|^~"
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9][A-Za-z0-9_]*")   # numbers include 0xFF


def tokens(src):
    """(kind, text, newlines_before, gap_before) with kind in w s o l b."""
    out, i, nl, gap = [], 0, 0, 0
    n = len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            nl, gap, i = nl + 1, 0, i + 1
            continue
        if c in " \t\r":
            gap, i = gap + 1, i + 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            text, kind = src[i:j].rstrip(" \t\r"), "l"
        elif src.startswith("/*", i):
            j = src.index("*/", i + 2) + 2
            text, kind = src[i:j], "b"
        elif c == '"':
            j = i + 1
            while src[j] != '"':
                j += 2 if src[j] == "\\" else 1
            text, kind = src[i:j + 1], "s"
        elif src.startswith('$"', i):
            j = i + 2
            while src[j] != '"':
                if src[j] == "\\" or src[j:j + 2] in ("{{", "}}"):
                    j += 2
                elif src[j] == "{":
                    depth, j = 1, j + 1
                    while depth:
                        if src[j] == '"':
                            j += 1
                            while src[j] != '"':
                                j += 2 if src[j] == "\\" else 1
                        depth += {"{": 1, "}": -1}.get(src[j], 0)
                        j += 1
                else:
                    j += 1
            text, kind = src[i:j + 1], "s"
        elif c == "'":
            j = i + (4 if src[i + 1] == "\\" else 3)
            text, kind = src[i:j], "s"
        elif WORD.match(src, i):
            text, kind = WORD.match(src, i).group(0), "w"
        elif src[i:i + 2] in TWO:
            text, kind = src[i:i + 2], "o"
        elif c in ONE:
            text, kind = c, "o"
        else:
            raise ValueError(f"unexpected byte {c!r}")
        out.append((kind, text, nl, gap))
        i += len(text) if kind != "l" else (src.find("\n", i) if src.find("\n", i) >= 0 else n) - i
        nl, gap = 0, 0
    return out


def glues(a, b):
    x, y = a[-1], b[0]
    if (x.isalnum() or x == "_") and (y.isalnum() or y == "_"):
        return True
    return x + y in TWO or x + y in ("//", "/*")


def ws(r, lo, hi):
    return "".join(r.choice(" \t") for _ in range(r.randint(lo, hi)))


def scramble(src, r):
    toks = tokens(src)
    out = [ws(r, 0, 1) + "\n" * r.randint(0, 2)]
    for i, (kind, text, nl, gap) in enumerate(toks):
        if i and nl:
            out.append(r.choice(["", " ", "\t", "\r", "  \r"]))
            out.append("\n" if nl == 1 else "\n" + "".join(ws(r, 0, 2) + "\n" for _ in range(r.randint(1, 3))))
            out.append(ws(r, 0, 12))
        elif i:
            prev = toks[i - 1]
            if kind == "l":
                out.append(" " * gap)                       # trailing-comment gaps are kept
            elif kind == "b" or prev[0] == "b":
                out.append(ws(r, 1, 3) if gap else "")
            elif text == ">" and prev[1] == ">" and gap == 0:
                out.append("")                              # >> and >>> are adjacent '>' tokens
            elif glues(prev[1], text):
                out.append(ws(r, 1, 3))
            else:
                out.append(r.choice(["", "", " ", "  ", "\t"]))
        out.append(text)
    out.append(ws(r, 0, 2) + "\n" * r.randint(0, 3))
    return "".join(out)


def corrupt(src, r):
    b = bytearray(src.encode("latin-1"))
    for _ in range(r.randint(1, 6)):
        op, at = r.randint(0, 2), r.randrange(len(b) + 1)
        if op == 0 and b:
            del b[min(at, len(b) - 1)]
        elif op == 1:
            b.insert(at, r.choice(b'{}()[]"\'$/*\n\t <>-+!;,.:?' + bytes([r.randrange(256)])))
        elif b:
            b[min(at, len(b) - 1)] = r.randrange(256)
    return b.decode("latin-1")


def corruption(fmt, variants, seed, files):
    r = random.Random(seed)
    work = tempfile.mkdtemp()
    n = 0
    for path in files:
        src = open(path, encoding="latin-1", newline="").read()
        for _ in range(variants):
            name = os.path.join(work, "c.cap")
            open(name, "w", encoding="latin-1", newline="").write(corrupt(src, r))
            keep = open(name, encoding="latin-1", newline="").read()
            try:
                res = subprocess.run([fmt, name], capture_output=True, text=True, timeout=20)
                again = subprocess.run([fmt, "--check", name], capture_output=True, text=True, timeout=20) if res.returncode == 0 else res
            except subprocess.TimeoutExpired:
                res = again = None
            ok = res is not None and (res.returncode == 2 or (res.returncode == 0 and again.returncode == 0))
            if not ok:
                d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failures")
                os.makedirs(d, exist_ok=True)
                out = os.path.join(d, f"corrupt-{seed}-{n}.cap")
                open(out, "w", encoding="latin-1", newline="").write(keep)
                what = "hung" if res is None else f"exit {res.returncode}: {(res.stdout + res.stderr)[:200]}"
                print(f"  formatter failed on a corrupted copy of {path} ({what}); kept as {os.path.relpath(out)}")
                return 1
            n += 1
    print(f"corruption fuzz: {n} corrupted copies formatted or refused cleanly (seed {seed})")
    return 0


def main():
    if sys.argv[1] == "--corrupt":
        return corruption(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5:])
    fmt, variants, seed, files = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
    r = random.Random(seed)
    work = tempfile.mkdtemp()
    cases = []
    for path in files:
        src = open(path, encoding="latin-1", newline="").read()
        for v in range(variants):
            name = os.path.join(work, f"{len(cases)}.cap")
            open(name, "w", encoding="latin-1", newline="").write(scramble(src, r))
            cases.append((path, name))
    res = subprocess.run([fmt] + [c[1] for c in cases], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"capstanfmt exited {res.returncode} (seed {seed}): {res.stdout[:400]}")
        return 1
    bad = []
    for path, name in cases:
        if open(name, encoding="latin-1", newline="").read() != open(path, encoding="latin-1", newline="").read():
            bad.append((path, name))
    if bad:
        keep = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failures")
        os.makedirs(keep, exist_ok=True)
        for path, name in bad[:5]:
            print(f"  not restored: {path} (seed {seed}, kept as tests/fmt/failures/{os.path.basename(name)})")
            os.replace(name, os.path.join(keep, os.path.basename(name)))
        return 1
    print(f"whitespace fuzz: {len(cases)} scrambled copies of {len(files)} files restored exactly (seed {seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
