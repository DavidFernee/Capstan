"""Execute emitted lifecycle and checked arena leaves in a freestanding ELF."""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MASK = (1 << 64) - 1
MAX = 67108864
VALUE = 0x123456789abcdef0


def image(leaves, case):
    code = bytearray()
    failures = []
    calls = []

    def mov(reg, value):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', value & MASK))

    def jne():
        code.extend(b'\x0f\x85')
        failures.append(len(code))
        code.extend(bytes(4))

    def check(reg, expected):
        mov(3, expected)
        code.extend((0x48 + reg // 8, 0x39, 0xd8 + reg % 8))
        jne()

    def call(name):
        code.append(0xe8)
        calls.append((len(code), name))
        code.extend(bytes(4))

    def state(base, used, cap):
        for reg, value in ((12, base), (13, used), (14, cap)):
            mov(reg, value)

    def verify(base, used, cap):
        for reg, value in ((12, base), (13, used), (14, cap)):
            check(reg, value)

    if case[0] == 'reject-init':
        _, base, used, cap, request = case
        state(base, used, cap)
        mov(0, request)
        call('init')
        check(2, 1)
        check(0, 0)
        verify(base, used, cap)
    elif case[0] == 'reject-release':
        _, base, used, cap = case
        state(base, used, cap)
        call('release')
        check(2, 1)
        check(0, 0)
        verify(base, used, cap)
    else:
        _, cap = case
        state(0, 0, 0)
        mov(0, cap)
        call('init')
        check(2, 0)
        check(13, 0)
        check(14, cap)
        # R15 saves the backing base across the leaf calls.
        code.extend(b'\x4d\x89\xe7\x4d\x85\xff\x0f\x84')
        failures.append(len(code))
        code.extend(bytes(4))
        mov(0, 8)
        call('reserve')
        check(2, 0)
        check(13, 8)
        # Returned pointer equals saved base.
        code.extend(b'\x4c\x39\xf8')
        jne()
        mov(0, 0)
        call('load')
        check(2, 0)
        check(0, 0)  # fresh anonymous mapping is zeroed
        mov(0, 0)
        mov(6, VALUE)
        call('store')
        check(2, 0)
        mov(0, 8)
        mov(6, 9)
        call('store')
        check(2, 1)  # not committed
        mov(0, 0)
        call('load')
        check(2, 0)
        check(0, VALUE)
        mov(0, cap)
        call('init')
        check(2, 1)  # live mapping must not be replaced
        check(13, 8)
        check(14, cap)
        code.extend(b'\x4d\x39\xfc')  # cmp r12,r15
        jne()
        call('release')
        check(2, 0)
        verify(0, 0, 0)
        call('release')
        check(2, 1)
        verify(0, 0, 0)
        # Reinitialisation must be possible after successful release.
        mov(0, cap)
        call('init')
        check(2, 0)
        check(13, 0)
        call('release')
        check(2, 0)
        verify(0, 0, 0)
    code.extend(b'\x31\xff\xb8\x3c\x00\x00\x00\x0f\x05\x0f\x0b')
    fail = len(code)
    code.extend(b'\xbf\x01\x00\x00\x00\xb8\x3c\x00\x00\x00\x0f\x05\x0f\x0b')
    offsets = {}
    for name, leaf in leaves.items():
        offsets[name] = len(code)
        code.extend(leaf)
    for field, name in calls:
        struct.pack_into('<i', code, field, offsets[name] - field - 4)
    for field in failures:
        struct.pack_into('<i', code, field, fail - field - 4)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x4000b0,
                         64, 0, 0, 64, 56, 2, 0, 0, 0)
    length = 176 + len(code)
    segment = struct.pack('<IIQQQQQQ', 1, 5, 0, 0x400000, 0x400000, length, length, 4096)
    stack = struct.pack('<IIQQQQQQ', 0x6474e551, 6, 0, 0, 0, 0, 0, 16)
    return header + segment + stack + code


def main():
    data = Path(sys.argv[1]).read_bytes()
    assert len(data) == 422  # 105 + 84 + 67 + 82 + 84
    leaves = dict(zip(('init', 'release', 'reserve', 'load', 'store'),
                      (data[:105], data[105:189], data[189:256], data[256:338], data[338:])))
    cases = [('roundtrip', 8), ('roundtrip', 4097), ('roundtrip', MAX)]
    cases += [('reject-init', *c) for c in [(0, 0, 0, 0), (0, 0, 0, -1),
              (0, 0, 0, MAX + 1), (4096, 0, 0, 8), (0, 1, 0, 8), (0, 0, 1, 8)]]
    cases += [('reject-release', *c) for c in [(0, 0, 0), (1, 0, 8),
              (4096, -1, 8), (4096, 9, 8), (4096, 0, MAX + 1), (MASK - 4095, 0, 8192)]]
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'lifecycle'
        for case in cases:
            executable.write_bytes(image(leaves, case))
            os.chmod(executable, 0o700)
            result = subprocess.run([executable], capture_output=True, timeout=5)
            assert result.returncode == 0 and not result.stdout and not result.stderr, (case, result)
    print(f'{len(cases)} native arena lifecycle cases passed')


if __name__ == '__main__':
    main()
