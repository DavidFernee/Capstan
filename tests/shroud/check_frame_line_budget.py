#!/usr/bin/env python3
"""Strict-build and exercise Shroud's aggregate rendered-line budget."""

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = sorted(
    os.path.join("lib", "shroud", name)
    for name in os.listdir(os.path.join(ROOT, "lib", "shroud"))
    if name.endswith(".cap")
)


def run(argv, expected=0, env=None):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, env=env)
    if result.returncode != expected:
        raise SystemExit(
            f"expected exit {expected}, got {result.returncode}: {' '.join(argv)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def build(capstanc, cc, cflags, source, output):
    c_source = output + ".c"
    run([capstanc, "build", "--strict", "-o", c_source] + LIB + [source])
    run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), c_source, "-o", output])


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: check_frame_line_budget.py CAPSTANC CC [CFLAGS...]")
    capstanc = os.path.abspath(sys.argv[1]) if os.path.exists(sys.argv[1]) else sys.argv[1]
    cc = sys.argv[2]
    cflags = sys.argv[3:]
    if not any(flag.startswith("-O") for flag in cflags):
        cflags = ["-O2"] + cflags

    unit = os.path.join(ROOT, "tests", "shroud", "frame_line_budget.cap")
    reject = os.path.join(ROOT, "tests", "shroud", "frame_line_budget_reject.cap")
    with tempfile.TemporaryDirectory(prefix="capstan-frame-lines-") as tmp:
        unit_exe = os.path.join(tmp, "frame_line_budget")
        build(capstanc, cc, cflags, unit, unit_exe)
        env = os.environ.copy()
        env["CAPSTAN_GC_STATS"] = "1"
        payload_path = os.path.join(ROOT, "tests", "shroud", ".frame_line_payload.tmp")
        try:
            with open(payload_path, "wb") as payload:
                payload.write(b"x" * 1048576)
            unit_result = run([unit_exe], env=env)
        finally:
            if os.path.exists(payload_path):
                os.unlink(payload_path)
        if "frame line budget: 6 assertions" not in unit_result.stdout:
            raise SystemExit(f"frame line budget unit assertions missing:\n{unit_result.stdout}")

        reject_exe = os.path.join(tmp, "frame_line_budget_reject")
        build(capstanc, cc, cflags, reject, reject_exe)
        result = run([reject_exe], expected=101)
        if "shroud: frame text line budget exceeded" not in result.stdout:
            raise SystemExit(f"aggregate line-budget diagnostic missing:\n{result.stdout}")

    peak = re.search(r"peak_heap=(\d+)", unit_result.stderr + unit_result.stdout)
    if not peak:
        raise SystemExit("frame line budget: CAPSTAN_GC_STATS did not report peak_heap")
    heap_note = f"; peak Capstan GC heap {int(peak.group(1)) / (1024 * 1024):.1f} MiB"
    print("frame line budget: 6 unit assertions; explicit/soft wrap, full-size untrusted input and multi-view "
          "boundaries; one-line-over tree rejected" + heap_note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
