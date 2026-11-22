#!/usr/bin/env python3
"""Every byte value placed raw in a Capstan string literal must come out of the
compiled program unchanged (lexer -> escape_c -> C compiler -> runtime)."""
import os, subprocess, sys, tempfile
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
raw = bytes(b for b in range(256) if b not in (10, 34, 92))          # newline, quote, backslash
src = b'int main() { print("' + raw + b'\\n\\"\\\\"); return 0; }\n'
expect = raw + b'\n"\\'
with tempfile.TemporaryDirectory() as d:
    cap, c, exe = (os.path.join(d, n) for n in ("bytes.cap", "bytes.c", "bytes"))
    open(cap, "wb").write(src)
    subprocess.run([os.path.join(root, "build/capstanc"), "build", "-o", c, cap], check=True)
    subprocess.run([os.environ.get("CC", "cc"), "-std=gnu11", "-w", "-I" + os.path.join(root, "runtime"), c, "-o", exe], check=True)
    out = subprocess.run([exe], capture_output=True, check=True).stdout
    # stage 0 must agree byte for byte
    py = os.path.join(d, "bytes.py")
    subprocess.run([sys.executable, os.path.join(root, "bootstrap/capstan0.py"), py, cap], check=True)
    out0 = subprocess.run([sys.executable, py], capture_output=True, check=True).stdout
if out != expect or out0 != expect:
    bad = [i for i, (a, b) in enumerate(zip(out, expect)) if a != b][:5]
    sys.exit(f"escape round trip FAILED (native ok={out == expect}, stage0 ok={out0 == expect}) first diffs at {bad}")
print(f"escape round trip: all {len(expect)} bytes preserved (native and stage 0)")
