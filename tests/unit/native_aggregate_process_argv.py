"""Exercise exact Capstan-emitted argv leaf with actual Linux kernel argv."""
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def image(leaf):
    # Freestanding observation trampoline: mmap private RW arena, preserve
    # initial RSP, call leaf, write offset/status/cursor and committed bytes.
    # No foreign compiler or runtime executes in the test ELF.
    prefix = bytes.fromhex(
        '4989e731ffbe00001000ba0300000041ba2200000049c7c0ffffffff4531c9'
        'b8090000000f054989c44531ed49c7c6000010004c89f8e83300000041555250'
        'b801000000bf010000004889e6ba180000000f05b801000000bf010000004c89e6'
        '4c89ea0f05b83c00000031ff0f05')
    code = prefix + leaf
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x4000b0,
                         64, 0, 0, 64, 56, 2, 0, 0, 0)
    size = 176 + len(code)
    segment = struct.pack('<IIQQQQQQ', 1, 5, 0, 0x400000, 0x400000, size, size, 4096)
    stack = struct.pack('<IIQQQQQQ', 0x6474e551, 6, 0, 0, 0, 0, 0, 16)
    return header + segment + stack + code


def main():
    leaf = Path(sys.argv[1]).read_bytes()
    assert len(leaf) == 353
    cases = [([], True), ([b''], True), ([b'a', b'abc', b'\xff'], True),
             ([b'x'*4096], True), ([b'x'*4097], False), ([b'']*256, True),
             ([b'']*257, False), ([b'x'*4096]*20, False)]
    rng = random.Random(42)
    for _ in range(60):
        cases.append(([bytes(rng.randrange(1, 256) for _ in range(rng.randrange(100)))
                       for _ in range(rng.randrange(20))], True))
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'argv'
        executable.write_bytes(image(leaf))
        os.chmod(executable, 0o700)
        for args, ok in cases:
            run = subprocess.run([executable, *args], capture_output=True, timeout=5)
            assert run.returncode == 0 and not run.stderr
            off, status, used = struct.unpack_from('<QQQ', run.stdout)
            data = run.stdout[24:]
            assert off == 0 and status == int(not ok) and len(data) == used
            if not ok:
                assert used == 0
                continue
            assert struct.unpack_from('<QQQQ', data) == (4093, 257, len(args), 1)
            pos = 4128
            for i, arg in enumerate(args):
                assert struct.unpack_from('<QQ', data, 32+i*16) == (pos, 1)
                assert struct.unpack_from('<QQ', data, pos) == (4096, len(arg))
                assert all(struct.unpack_from('<QQ', data, pos+16+j*16) == (v, 1)
                           for j, v in enumerate(arg))
                pos += 16 + 16*len(arg)
            assert data[32+16*len(args):4128] == bytes(4096-16*len(args))
            assert pos == used
    print(f'{len(cases)} native process argv cases passed')


if __name__ == '__main__':
    main()
