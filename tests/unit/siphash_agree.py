#!/usr/bin/env python3
"""The runtime's SipHash (map key hashing, CWE-407) is correct.

Checks the C cap_siphash against the published SipHash-2-4 vectors (Aumasson and
Bernstein, 2012: key 00..0f, the empty message and the message 00..0e), then
against this independent Python implementation for SipHash-2-4 and SipHash-1-3
(what maps use) on every length from 0 to 63 and on random keys and messages.
Also checks that two runs of a program get different map keys, so hash values
cannot be predicted from one run to the next.
"""
import os, random, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("CC", "cc")
M = (1 << 64) - 1


def rotl(x, b):
    return ((x << b) | (x >> (64 - b))) & M


def siphash(msg, k0, k1, c, d):
    v = [0x736f6d6570736575 ^ k0, 0x646f72616e646f6d ^ k1, 0x6c7967656e657261 ^ k0, 0x7465646279746573 ^ k1]

    def rnd():
        v[0] = (v[0] + v[1]) & M; v[1] = rotl(v[1], 13) ^ v[0]; v[0] = rotl(v[0], 32)
        v[2] = (v[2] + v[3]) & M; v[3] = rotl(v[3], 16) ^ v[2]
        v[0] = (v[0] + v[3]) & M; v[3] = rotl(v[3], 21) ^ v[0]
        v[2] = (v[2] + v[1]) & M; v[1] = rotl(v[1], 17) ^ v[2]; v[2] = rotl(v[2], 32)

    full = len(msg) - len(msg) % 8
    for i in range(0, full, 8):
        m = int.from_bytes(msg[i:i + 8], "little")
        v[3] ^= m
        for _ in range(c): rnd()
        v[0] ^= m
    b = (len(msg) << 56) & M | int.from_bytes(msg[full:], "little")
    v[3] ^= b
    for _ in range(c): rnd()
    v[0] ^= b
    v[2] ^= 0xff
    for _ in range(d): rnd()
    return v[0] ^ v[1] ^ v[2] ^ v[3]


PROG = r'''#include "capstan_rt.h"
static const char *f[] = {"x"};
int main(void) {
    cap_gc_init(); cap_files = f;
    unsigned long long k0, k1; int c, d, n;
    unsigned char m[300];
    while (scanf("%llx %llx %d %d %d", &k0, &k1, &c, &d, &n) == 5) {
        for (int i = 0; i < n; i++) { unsigned v; if (scanf("%2x", &v) != 1) return 2; m[i] = (unsigned char)v; }
        printf("%016llx\n", (unsigned long long)cap_siphash(m, (size_t)n, k0, k1, c, d));
    }
    CapMap *map = cap_map_new();
    (void)map;
    fprintf(stderr, "%016llx\n", (unsigned long long)cap_hash_str(cap_str_new("probe", 5)));
    return 0;
}
'''


def main():
    d = tempfile.mkdtemp()
    src, exe = os.path.join(d, "s.c"), os.path.join(d, "s")
    open(src, "w").write(PROG)
    subprocess.run([CC, "-O2", "-std=gnu11", "-w", "-I" + os.path.join(ROOT, "runtime"), src, "-o", exe], check=True)
    r = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    key = bytes(range(16))
    k0, k1 = int.from_bytes(key[:8], "little"), int.from_bytes(key[8:], "little")
    cases = [(k0, k1, 2, 4, b""), (k0, k1, 2, 4, bytes(range(15)))]
    cases += [(k0, k1, c, dd, bytes(range(n))) for n in range(64) for c, dd in ((2, 4), (1, 3))]
    for _ in range(3000):
        cases.append((r.getrandbits(64), r.getrandbits(64), 1, 3, bytes(r.getrandbits(8) for _ in range(r.randint(0, 260)))))
    inp = "".join(f"{a:x} {b:x} {c} {dd} {len(m)} {m.hex()}\n" for a, b, c, dd, m in cases)
    p = subprocess.run([exe], input=inp, capture_output=True, text=True)
    got = [int(x, 16) for x in p.stdout.split()]
    want = [siphash(m, a, b, c, dd) for a, b, c, dd, m in cases]
    published = [0x726fdb47dd0e0e31, 0xa129ca6149be45e5]
    if want[:2] != published or got[:2] != published:
        print(f"FAIL published SipHash-2-4 vectors: C gives {got[:2]}, Python {want[:2]}")
        return 1
    bad = sum(g != w for g, w in zip(got, want)) + abs(len(got) - len(want))
    if bad:
        print(f"FAIL C and Python SipHash disagree on {bad} of {len(want)} inputs")
        return 1
    runs = {subprocess.run([exe], input="", capture_output=True, text=True).stderr.strip() for _ in range(3)}
    if len(runs) != 3:
        print(f"FAIL map hash keys repeat across runs: {runs}")
        return 1
    print(f"SipHash: published vectors, and C and Python agree on {len(want)} inputs; map keys differ on every run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
