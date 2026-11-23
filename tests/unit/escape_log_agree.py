#!/usr/bin/env python3
"""escape_log() in the C runtime and in stage 0 must agree byte for byte: on every
1-byte input, every 2-byte input starting at 0x80 or above, and random fragments
built from the bytes that matter for UTF-8 validity (lead bytes, boundary
continuation bytes, ASCII)."""
import os, random, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("CC", "cc")
src = open(os.path.join(ROOT, "bootstrap/capstan0.py")).read()
ns = {}
exec(src[src.index("def _utf8_seq"):src.index("def b_trust")], ns)
work = tempfile.mkdtemp()
c = os.path.join(work, "el.c")
open(c, "w").write('#include "capstan_rt.h"\nstatic const char *f[] = {"x"};\n'
                   "int main(void) { cap_gc_init(); cap_files = f; unsigned char b[8]; int n;\n"
                   "  while ((n = getchar()) != EOF) { for (int i = 0; i < n; i++) b[i] = (unsigned char)getchar();\n"
                   "    CapStr *e = cap_escape_log(cap_str_new((char *)b, n)); fwrite(e->data, 1, (size_t)e->len, stdout); putchar('\\n'); }\n"
                   "  return 0; }\n")
exe = os.path.join(work, "el")
subprocess.run([CC, "-O2", "-std=gnu11", "-w", "-I" + os.path.join(ROOT, "runtime"), c, "-o", exe], check=True)
r = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
inputs = [bytes([a]) for a in range(256)] + [bytes([a, b]) for a in range(0x80, 256) for b in range(256)]
pool = [0xC2, 0xDF, 0xE0, 0xE1, 0xE2, 0xED, 0xEF, 0xF0, 0xF4, 0xF5, 0x80, 0x8F, 0x90, 0x9F, 0xA0, 0xBF, 0xC0, 0x28, 0x41, 0x0A]
inputs += [bytes(r.choice(pool) for _ in range(r.randint(1, 6))) for _ in range(40000)]
out = subprocess.run([exe], input=b"".join(bytes([len(x)]) + x for x in inputs), capture_output=True).stdout.split(b"\n")
bad = [(x, g) for x, g in zip(inputs, out) if ns["b_escape_log"](x.decode("latin-1")).encode("latin-1") != g]
for x, g in bad[:5]:
    print(f"  {x!r}: C gives {g!r}, stage 0 gives {ns['b_escape_log'](x.decode('latin-1')).encode('latin-1')!r}")
print(f"escape_log: C runtime and stage 0 agree on {len(inputs) - len(bad)} of {len(inputs)} inputs")
sys.exit(1 if bad else 0)
