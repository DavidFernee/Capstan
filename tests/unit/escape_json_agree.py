#!/usr/bin/env python3
"""escape_json() is correct and the C runtime and stage 0 agree byte for byte.

On every 1-byte input, every 2-byte input starting at 0x80 or above, random UTF-8
fragments and random valid text: both give the same bytes; the result in quotes is
always valid JSON (Python's strict json parser); for valid UTF-8 input it decodes
back to exactly the input; and it never contains a raw control, '<', '>', '&',
U+2028 or U+2029 (so it is also safe inside an HTML <script> block)."""
import json, os, random, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("CC", "cc")
src = open(os.path.join(ROOT, "bootstrap/capstan0.py")).read()
ns = {}
exec(src[src.index("def _utf8_seq"):src.index("def b_trust")], ns)
work = tempfile.mkdtemp()
c = os.path.join(work, "ej.c")
open(c, "w").write('#include "capstan_rt.h"\nstatic const char *f[] = {"x"};\n'
                   "int main(void) { cap_gc_init(); cap_files = f; unsigned char b[64]; int n;\n"
                   "  while ((n = getchar()) != EOF) { for (int i = 0; i < n; i++) b[i] = (unsigned char)getchar();\n"
                   "    CapStr *e = cap_escape_json(cap_str_new((char *)b, n)); fwrite(e->data, 1, (size_t)e->len, stdout); putchar('\\n'); }\n"
                   "  return 0; }\n")
exe = os.path.join(work, "ej")
subprocess.run([CC, "-O2", "-std=gnu11", "-w", "-I" + os.path.join(ROOT, "runtime"), c, "-o", exe], check=True)
r = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
inputs = [bytes([a]) for a in range(256)] + [bytes([a, b]) for a in range(0x80, 256) for b in range(256)]
pool = [0xC2, 0xDF, 0xE0, 0xE1, 0xE2, 0xED, 0xEF, 0xF0, 0xF4, 0xF5, 0x80, 0x8F, 0x90, 0x9F, 0xA0, 0xBF, 0xC0, 0x22, 0x5C, 0x3C, 0x0A, 0x7F]
inputs += [bytes(r.choice(pool) for _ in range(r.randint(1, 6))) for _ in range(40000)]
chars = ['"', "\\", "<", ">", "&", "\n", "\x00", "\x7f", "é", "€", "😀", " ", " ", "﻿", "a", " "]
inputs += ["".join(r.choice(chars) for _ in range(r.randint(1, 12))).encode("utf-8") for _ in range(5000)]
out = subprocess.run([exe], input=b"".join(bytes([len(x)]) + x for x in inputs), capture_output=True).stdout.split(b"\n")
problems = []
for x, g in zip(inputs, out):
    s0 = ns["b_escape_json"](x.decode("latin-1")).encode("latin-1")
    if s0 != g:
        problems.append(f"{x!r}: C gives {g!r}, stage 0 gives {s0!r}")
        continue
    try:
        back = json.loads(b'"' + g + b'"')
    except ValueError as e:
        problems.append(f"{x!r}: {g!r} is not valid JSON ({e})")
        continue
    try:
        text = x.decode("utf-8")
        if back != text:
            problems.append(f"{x!r}: decodes to {back!r}")
    except UnicodeDecodeError:
        pass
    t = g.decode("utf-8")
    if any(ch in t for ch in "<>&  \x7f") or any(ord(ch) < 32 for ch in t):
        problems.append(f"{x!r}: raw unsafe character in {g!r}")
for p in problems[:5]:
    print("  " + p)
print(f"escape_json: C runtime and stage 0 agree, output valid JSON that round-trips, on {len(inputs) - len(problems)} of {len(inputs)} inputs")
sys.exit(1 if problems else 0)
