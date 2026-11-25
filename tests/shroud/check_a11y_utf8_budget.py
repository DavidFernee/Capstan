#!/usr/bin/env python3
"""Large-input allocation regression for Shroud's accessibility UTF-8 encoder.

Usage: python3 tests/shroud/check_a11y_utf8_budget.py CAPSTANC CC [CFLAGS...]
The test constrains and reports the Capstan managed heap, not process RSS.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = sorted(
    os.path.join("lib/shroud", name)
    for name in os.listdir(os.path.join(ROOT, "lib/shroud"))
    if name.endswith(".cap")
)


def run(argv, *, env=None, expected=0):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, env=env)
    if result.returncode != expected:
        raise SystemExit(
            f"a11y UTF-8 budget: {argv[0]!r} exited {result.returncode}, expected {expected}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    capstanc = os.path.abspath(sys.argv[1]) if os.path.exists(sys.argv[1]) else sys.argv[1]
    cc = sys.argv[2]
    cflags = sys.argv[3:]
    if not any(flag.startswith("-O") for flag in cflags):
        cflags = ["-O2"] + cflags

    source = """
int main() {
    List<int> cps = new List<int>();
    for (int i = 0; i < MAX_TEXT_BYTES; i += 1) { cps.push(0x41); }
    string encoded = utf8_from_codepoints(cps);
    if (encoded.len() != MAX_TEXT_BYTES) { return 1; }
    if (encoded.at(0) != 0x41 || encoded.at(MAX_TEXT_BYTES - 1) != 0x41) { return 2; }
    println("a11y UTF-8 budget: 1 MiB ASCII encoded exactly");
    return 0;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        cap = os.path.join(tmp, "a11y-utf8-budget.cap")
        c_source = os.path.join(tmp, "a11y-utf8-budget.c")
        exe = os.path.join(tmp, "a11y-utf8-budget")
        with open(cap, "w", encoding="utf-8") as stream:
            stream.write(source)
        run([capstanc, "build", "--strict", "-o", c_source] + LIB + [cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), c_source, "-o", exe])

        env = os.environ.copy()
        env["CAPSTAN_MAX_HEAP"] = "64M"
        env["CAPSTAN_GC_STATS"] = "1"
        result = run([exe], env=env)
        if "1 MiB ASCII encoded exactly" not in result.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing result confirmation: {result.stdout!r}")
        match = re.search(r"peak_heap=(\d+)", result.stderr)
        if not match:
            raise SystemExit(f"a11y UTF-8 budget: collector peak heap not reported: {result.stderr!r}")
        peak = int(match.group(1))
        limit = 64 * 1024 * 1024
        if peak > limit:
            raise SystemExit(f"a11y UTF-8 budget: peak managed heap {peak} exceeds {limit}")

        over_source = """
int main() {
    List<int> cps = new List<int>();
    for (int i = 0; i < 262145; i += 1) { cps.push(0x1F600); }
    utf8_from_codepoints(cps);
    println("unexpectedly accepted oversized accessibility text");
    return 1;
}
"""
        over_cap = os.path.join(tmp, "a11y-utf8-over.cap")
        over_c = os.path.join(tmp, "a11y-utf8-over.c")
        over_exe = os.path.join(tmp, "a11y-utf8-over")
        with open(over_cap, "w", encoding="utf-8") as stream:
            stream.write(over_source)
        run([capstanc, "build", "--strict", "-o", over_c] + LIB + [over_cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), over_c, "-o", over_exe])
        rejected = run([over_exe], env=env, expected=101)
        if "shroud: accessibility UTF-8 byte limit exceeded" not in rejected.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing over-limit diagnostic: {rejected.stdout!r}")
    print(f"a11y UTF-8 budget: 1 MiB encoded; peak Capstan managed heap {peak} bytes (64 MiB cap); oversized multi-byte output rejected")


if __name__ == "__main__":
    main()
