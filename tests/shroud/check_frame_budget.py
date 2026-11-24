#!/usr/bin/env python3
"""Standalone regression for Shroud's cumulative per-frame text budget.

Usage:
    python3 tests/shroud/check_frame_budget.py CAPSTANC CC [CFLAGS...]
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = sorted(
    os.path.join("lib/shroud", name)
    for name in os.listdir(os.path.join(ROOT, "lib/shroud"))
    if name.endswith(".cap")
)


def run(argv, *, expected=0):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != expected:
        raise SystemExit(
            f"frame budget: {argv[0]!r} exited {result.returncode}, expected {expected}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def build(capstanc, cc, cflags, tmp, source, name):
    c_source = os.path.join(tmp, name + ".c")
    exe = os.path.join(tmp, name)
    run([capstanc, "build", "--strict", "-o", c_source] + LIB + [source])
    run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), c_source, "-o", exe])
    return exe


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    capstanc = os.path.abspath(sys.argv[1]) if os.path.exists(sys.argv[1]) else sys.argv[1]
    cc = sys.argv[2]
    cflags = sys.argv[3:]
    if not any(flag.startswith("-O") for flag in cflags):
        cflags = ["-O2"] + cflags
    with tempfile.TemporaryDirectory() as tmp:
        unit = build(capstanc, cc, cflags, tmp, "tests/shroud/frame_budget.cap", "frame-budget")
        result = run([unit])
        if "frame text budget: 11 assertions" not in result.stdout:
            raise SystemExit(f"frame budget: unexpected unit output {result.stdout!r}")
        reject = build(capstanc, cc, cflags, tmp, "tests/shroud/frame_budget_reject.cap", "frame-budget-reject")
        result = run([reject], expected=101)
        if "shroud: frame view or text budget exceeded" not in result.stdout:
            raise SystemExit(f"frame budget: missing preflight diagnostic: {result.stdout!r}")
    print("frame budget: 11 unit assertions; aggregate over-budget tree rejected before layout")


if __name__ == "__main__":
    main()
