"""Execute the exact native stdout leaf in freestanding Linux ELF processes."""
import fcntl
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MASK = (1 << 64) - 1


def obj(data, tag=4096):
    return struct.pack('<QQ', tag, len(data)) + b''.join(struct.pack('<QQ', b, 1) for b in data)


def image(leaf, arena, offset, newline, expected_count, used=None, cap=None):
    used = len(arena) if used is None else used
    cap = len(arena) if cap is None else cap
    # RX static arena backing; leaf must not mutate it. Only stack scratch is RW.
    code = bytearray.fromhex('4c8d2500000000')  # lea r12,[rip+disp32]
    def mov(reg, value):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', value & MASK))
    for reg, value in ((13, used), (14, cap), (0, offset), (7, newline)):
        mov(reg, value)
    code.append(0xe8)
    call = len(code)
    code.extend(bytes(4))
    mov(1, expected_count)
    # Wrong returned byte count exits 2; otherwise return leaf status.
    code.extend(bytes.fromhex('4839c8750489d7eb05bf02000000b83c0000000f050f0b'))
    struct.pack_into('<i', code, call, len(code)-call-4)
    code.extend(leaf)
    while len(code) % 8:
        code.append(0)
    struct.pack_into('<i', code, 3, len(code)-7)
    code.extend(arena)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x4000b0, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    size = 176 + len(code)
    segment = struct.pack('<IIQQQQQQ', 1, 5, 0, 0x400000, 0x400000, size, size, 4096)
    stack = struct.pack('<IIQQQQQQ', 0x6474e551, 6, 0, 0, 0, 0, 0, 16)
    return header + segment + stack + code


def main():
    leaf = Path(sys.argv[1]).read_bytes()
    assert len(leaf) == 382
    count = 0
    with tempfile.TemporaryDirectory() as directory:
        exe = Path(directory) / 'stdout'
        def prepare(arena, offset, newline, expected_count, used=None, cap=None):
            exe.write_bytes(image(leaf, arena, offset, newline, expected_count, used, cap))
            os.chmod(exe, 0o700)
        def check(arena, offset, newline, expected=None, used=None, cap=None):
            nonlocal count
            prepare(arena, offset, newline, len(expected) if expected is not None else 0, used, cap)
            run = subprocess.run([exe], capture_output=True, timeout=5)
            assert (run.returncode, run.stdout, run.stderr) == (0 if expected is not None else 1, expected or b'', b''), (offset, newline, run.returncode, run.stdout[:32])
            count += 1
        for data in (b'', b'hello', b'a\0b', bytes(range(256)), b'x'*4096):
            for newline in (0, 1):
                check(obj(data), 0, newline, data + b'\n'*newline)
        rng = random.Random(42)
        for _ in range(50):
            data = rng.randbytes(rng.randrange(4097))
            prefix = obj(b'other', 7)
            check(prefix+obj(data), len(prefix), 1, data+b'\n')
        a = obj(b'abc')
        check(a, 16, 0)
        check(a, len(a), 0)
        check(a, -1, 0)
        check(a, 0, 2)
        check(obj(b'abc', 2045), 0, 0)
        check(a, 0, 0, used=len(a)-16)
        check(a, 0, 0, cap=len(a)-16)
        check(obj(b'x'*4097), 0, 0)
        for pos, word in ((24, 0), (56, 2), (48, 256), (48, MASK)):
            corrupt = bytearray(a)
            struct.pack_into('<Q', corrupt, pos, word)
            check(corrupt, 0, 1)
        # The separately emitted LogText variant changes only the exact
        # class immediate. Neither variant accepts the other class or taint.
        trusted_leaf = leaf
        leaf = Path(sys.argv[1]).with_name('ccam-native-stdout-log.bin').read_bytes()
        assert len(leaf) == 382
        differences = [i for i, (a_byte, b_byte) in enumerate(zip(trusted_leaf, leaf)) if a_byte != b_byte]
        assert differences == [30, 31], differences
        check(obj(b'abc', 2046), 0, 1, b'abc\n')
        check(obj(b'', 2046), 0, 1, b'\n')
        check(obj(b'abc', 4096), 0, 0)
        check(obj(b'abc', 2045), 0, 0)
        leaf = trusted_leaf
        check(obj(b'abc', 2046), 0, 0)
        prepare(a, 0, 0, 0)
        with open('/dev/full', 'wb') as full:
            run = subprocess.run([exe], stdout=full, stderr=subprocess.PIPE, timeout=5)
        assert (run.returncode, run.stderr) == (1, b'')
        count += 1
        # Nonblocking pipe: a partial write followed by EAGAIN is observable.
        rd, wr = os.pipe()
        try:
            capacity = fcntl.fcntl(wr, fcntl.F_GETPIPE_SZ)
            os.set_blocking(wr, False)
            filler = b'z' * (capacity-4096)
            if filler:
                assert os.write(wr, filler) == len(filler)
            prepare(obj(b'x'*4096), 0, 1, 0)
            run = subprocess.run([exe], stdout=wr, stderr=subprocess.PIPE, timeout=5)
            os.close(wr)
            wr = -1
            received = bytearray()
            while True:
                chunk = os.read(rd, 65536)
                if not chunk:
                    break
                received.extend(chunk)
            assert (run.returncode, run.stderr) == (1, b'')
            assert bytes(received) == filler + b'x'*4096
            count += 1
        finally:
            os.close(rd)
            if wr >= 0:
                os.close(wr)
    print(f'{count} native stdout cases passed')


if __name__ == '__main__':
    main()
