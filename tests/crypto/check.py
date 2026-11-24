#!/usr/bin/env python3
"""lib/crypto.cap agrees with Python's hashlib, natively and under stage 0.

    check.py CAPSTANC CC [CFLAGS...]

tests/crypto/vectors.cap prints SHA-256, HMAC-SHA256 and PBKDF2-HMAC-SHA256 results
for the FIPS 180-4 examples and for inputs from a generator (xorshift64*) that this
script repeats, and checks each SHA-256 against the runtime's C hash() itself. Every
line must equal hashlib's answer; the native build also runs the one-million-'a'
vector and checks the runtime's hash_password() at full cost, too slow for stage 0.
"""
import hashlib, hmac, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
M64 = (1 << 64) - 1


class Gen:
    def __init__(self, s):
        self.s = s

    def next(self):
        x = self.s
        x ^= x >> 12
        x = (x ^ (x << 25)) & M64
        x ^= x >> 27
        self.s = x
        return ((x * 2685821657736338717) & M64) >> 33 & 0x7FFFFFFF

    def bytes(self, n):
        return bytes(self.next() & 0xFF for _ in range(n))


def expected(long_vectors):
    sha = lambda b: hashlib.sha256(b).hexdigest()
    out = ["sha256-empty " + sha(b""), "sha256-abc " + sha(b"abc"),
           "sha256-448 " + sha(b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"),
           "sha256-896 " + sha(b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu")]
    if long_vectors:
        out.append("hash_password agrees")
        out.append("sha256-million-a " + sha(b"a" * 1000000))
    g = Gen(88172645463325252)
    for n in range(201):
        out.append(f"sha256-{n} " + sha(g.bytes(n)))
    for _ in range(20):
        n = 200 + g.next() % 3000
        out.append(f"sha256-long-{n} " + sha(g.bytes(n)))
    for _ in range(40):
        kn = g.next() % 150
        key = g.bytes(kn)
        msg = g.bytes(g.next() % 300)
        out.append(f"hmac-{kn} " + hmac.new(key, msg, "sha256").hexdigest())
    for _ in range(12):
        pw = g.bytes(g.next() % 80)
        salt = g.bytes(g.next() % 40)
        it = 1 + g.next() % 20
        dk = 1 + g.next() % 100
        out.append(f"pbkdf2-{it}-{dk} " + hashlib.pbkdf2_hmac("sha256", pw, salt, it, dk).hex())
    out.append("pbkdf2-bounds ok")
    out.append("pbkdf2-empty " + hashlib.pbkdf2_hmac("sha256", b"", b"", 1, 32).hex())
    return out


def main():
    capstanc, cc, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
    lib, prog = os.path.join(ROOT, "lib/crypto.cap"), os.path.join(ROOT, "tests/crypto/vectors.cap")
    with tempfile.TemporaryDirectory() as d:
        c, exe, py = os.path.join(d, "v.c"), os.path.join(d, "v"), os.path.join(d, "v.py")
        built = subprocess.run([capstanc, "build", "--strict", "-o", c, lib, prog], capture_output=True, text=True)
        if built.returncode != 0:
            print("FAIL lib/crypto.cap does not compile with --strict:\n" + built.stdout[-2000:])
            return 1
        subprocess.run([cc] + flags + [c, "-o", exe], check=True)
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "bootstrap/capstan0.py"), py, lib, prog], check=True)
        for label, cmd, long_vectors in (("native", [exe, "long"], True), ("stage 0", [sys.executable, "-I", py], False)):
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
            got, want = p.stdout.splitlines(), expected(long_vectors)
            if p.returncode != 0 or got != want:
                bad = next((f"{w!r} but got {g!r}" for g, w in zip(got, want) if g != w), f"{len(got)} lines, expected {len(want)}")
                print(f"FAIL {label}: exit {p.returncode}: expected {bad}\n{p.stderr[-500:]}")
                return 1
    n = len(expected(True))
    print(f"lib/crypto.cap: SHA-256, HMAC-SHA256 and PBKDF2 agree with hashlib on {n - 1} results natively and {n - 2} under stage 0, and with the runtime's hash() and hash_password()")
    return 0


if __name__ == "__main__":
    sys.exit(main())
