#!/usr/bin/env python3
"""Property tests for the range analysis's interval arithmetic.

Builds tests/unit/ranges_props.cap together with the compiler's own sources,
runs it, and checks every answer it prints against exact (big-integer)
arithmetic:

  F  mul_fits, add_over, sub_over and the saturating operations, for every pair
     of edge values: must be exactly right.
  B  bin_safe and bin_range for every pair of intervals over the edge values and
     each of + - * / %:
       - soundness: when bin_safe says an operation needs no check, it must be
         impossible for it to overflow or divide by zero anywhere in the intervals;
       - precision: for + - * it must also say so whenever that is true;
       - bin_range must contain every result the operation can produce at the
         intervals' corners and sample points.
  C  bound(): after learning "x op v" for x in one interval and v in another, the
     new interval for x must contain every x for which the comparison can hold.
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("CC", "cc")
MIN, MAX = -2**63, 2**63 - 1
SRC_DIR = os.environ.get("CAPSTAN_SRC", os.path.join(ROOT, "compiler"))   # another compiler's sources, e.g. a mutant
SRC = [os.path.join(SRC_DIR, f"{n}.cap") for n in ("ast", "lexer", "parser", "checker", "ranges", "codegen")]


def fits(v):
    return MIN <= v <= MAX


def clamp(v):
    return max(MIN, min(MAX, v))


def cdiv(a, b):                       # C: truncates toward zero
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def cmod(a, b):
    if a == MIN and b == -1:          # the runtime defines this as 0
        return 0
    return a - b * cdiv(a, b)


def points(lo, hi):
    cand = {lo, hi, lo + 1, hi - 1, 0, 1, -1, 2, -2, (lo + hi) // 2}
    return [p for p in cand if lo <= p <= hi]


def exact(op, x, y):
    """The value op produces at run time, or None if the check stops the program."""
    if op == "+":
        v = x + y
    elif op == "-":
        v = x - y
    elif op == "*":
        v = x * y
    elif op == "/":
        if y == 0:
            return None
        v = cdiv(x, y)
    else:
        if y == 0:
            return None
        return cmod(x, y)
    return v if fits(v) else None


def truly_safe(op, alo, ahi, blo, bhi):
    corners = [(x, y) for x in (alo, ahi) for y in (blo, bhi)]
    if op in "+-*":
        return all(fits({"+": x + y, "-": x - y, "*": x * y}[op]) for x, y in corners)
    if blo <= 0 <= bhi:
        return False
    return not (alo == MIN and blo <= -1 <= bhi)


def holds(op, x, v):
    return {"<": x < v, "<=": x <= v, ">": x > v, ">=": x >= v, "==": x == v}[op]


def main():
    work = tempfile.mkdtemp()
    c = os.path.join(work, "props.c")
    built = subprocess.run([os.path.join(ROOT, "build/capstanc"), "build", "-o", c]
                           + SRC + [os.path.join(ROOT, "tests/unit/ranges_props.cap")],
                           capture_output=True, text=True)
    if built.returncode != 0:
        print("driver did not compile:\n" + built.stdout[-2000:])
        return 1
    exe = os.path.join(work, "props")
    if subprocess.run([CC, "-O2", "-std=gnu11", "-w", "-I" + os.path.join(ROOT, "runtime"), c, "-o", exe]).returncode != 0:
        print("driver C did not compile")
        return 1
    out = subprocess.run([exe], capture_output=True, text=True, timeout=600)
    if out.returncode != 0:
        print(f"driver exited {out.returncode}: {out.stderr[-500:]}")
        return 1
    errors, counts = [], {"F": 0, "B": 0, "C": 0}
    proved = possible = 0
    for line in out.stdout.splitlines():
        f = line.split()
        counts[f[0]] += 1
        if f[0] == "F":
            x, y = int(f[1]), int(f[2])
            want = [int(fits(x * y)), int(not fits(x + y)), int(not fits(x - y)), clamp(x + y), clamp(x - y), clamp(x * y)]
            got = [int(v) for v in f[3:]]
            if got != want:
                errors.append(f"{line}  (expected {want})")
        elif f[0] == "B":
            op = f[1]
            alo, ahi, blo, bhi, safe, rlo, rhi = (int(v) for v in f[2:])
            truth = truly_safe(op, alo, ahi, blo, bhi)
            if safe and not truth:
                errors.append(f"UNSOUND bin_safe: {line}")
            if op in "+-*" and truth and not safe:
                errors.append(f"imprecise bin_safe: {line}")
            possible += truth
            proved += safe
            for x in points(alo, ahi):
                for y in points(blo, bhi):
                    v = exact(op, x, y)
                    if v is not None and not rlo <= v <= rhi:
                        errors.append(f"UNSOUND bin_range: {line}  ({x} {op} {y} = {v})")
        else:
            op = f[1]
            clo, chi, vlo, vhi, glo, ghi = (int(v) for v in f[2:])
            for x in points(clo, chi):
                for v in points(vlo, vhi):
                    if holds(op, x, v) and not glo <= x <= ghi:
                        errors.append(f"UNSOUND bound: {line}  (x = {x}, v = {v})")
    if errors:
        for e in errors[:20]:
            print("  " + e)
        print(f"{len(errors)} property violations")
        return 1
    print(f"range properties: {counts['F']} bound operations exact, {counts['B']} interval operations sound "
          f"({proved} of {possible} provably safe ones proved), {counts['C']} comparison facts sound")
    return 0


if __name__ == "__main__":
    sys.exit(main())
