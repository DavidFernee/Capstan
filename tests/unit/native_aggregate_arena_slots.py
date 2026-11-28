"""Execute Capstan-emitted checked word loads/stores in freestanding ELF."""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MASK = (1 << 64) - 1
INITIAL = (0x1122334455667788, 0x8877665544332211, 0x0102030405060708, 0xfedcba9876543210)
VALUE = 0xdeadbeef12345678


def image(leaf, store, base_mode, used, capacity, offset, success):
    code = bytearray(b'\x48\x83\xec\x20\x49\x89\xe7')  # sub rsp,32; mov r15,rsp
    branches = []

    def mov(reg, val):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', val & MASK))

    def jne():
        code.extend(b'\x0f\x85')
        branches.append(len(code))
        code.extend(bytes(4))

    def check(reg, val):
        mov(3, val)
        code.extend((0x48 + reg // 8, 0x39, 0xd8 + reg % 8))
        jne()

    for i, val in enumerate(INITIAL):
        mov(3, val)
        code.extend((0x49, 0x89, 0x5f, i * 8))
    if base_mode == 'valid':
        code.extend(b'\x4d\x89\xfc')
    elif base_mode == 'misaligned':
        code.extend(b'\x4d\x89\xfc\x49\x83\xc4\x01')
    elif base_mode == 'wrap':
        mov(12, MASK - 7)
    elif base_mode == 'zero':
        mov(12, 0)
    else:
        raise AssertionError(base_mode)
    for reg, val in ((13, used), (14, capacity), (0, offset), (6, VALUE)):
        mov(reg, val)
    code.append(0xe8)
    call = len(code)
    code.extend(bytes(4))
    check(0, INITIAL[offset // 8] if success and not store else 0)
    check(2, 0 if success else 1)
    check(13, used)
    check(14, capacity)
    check(6, VALUE)
    for i, val in enumerate(INITIAL):
        mov(3, VALUE if success and store and i == offset // 8 else val)
        code.extend((0x49, 0x39, 0x5f, i * 8))
        jne()
    code.extend(b'\x31\xff\xb8\x3c\x00\x00\x00\x0f\x05\x0f\x0b')
    fail = len(code)
    code.extend(b'\xbf\x01\x00\x00\x00\xb8\x3c\x00\x00\x00\x0f\x05\x0f\x0b')
    target = len(code)
    code.extend(leaf)
    struct.pack_into('<i', code, call, target - call - 4)
    for field in branches:
        struct.pack_into('<i', code, field, fail - field - 4)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x4000b0, 64,
                         0, 0, 64, 56, 2, 0, 0, 0)
    length = 176 + len(code)
    segment = struct.pack('<IIQQQQQQ', 1, 5, 0, 0x400000, 0x400000, length, length, 4096)
    stack = struct.pack('<IIQQQQQQ', 0x6474e551, 6, 0, 0, 0, 0, 0, 16)
    return header + segment + stack + code


def main():
    data = Path(sys.argv[1]).read_bytes()
    assert len(data) == 166
    cases = [
        ('valid', 16, 32, 0, True), ('valid', 16, 32, 8, True),
        ('valid', 16, 32, 16, False), ('valid', 15, 32, 8, False),
        ('valid', 16, 32, 1, False), ('valid', 16, 32, -8, False),
        ('valid', 33, 32, 0, False), ('valid', -1, 32, 0, False),
        ('valid', 0, -1, 0, False), ('wrap', 8, 16, 0, False),
        ('zero', 8, 16, 0, False), ('misaligned', 16, 32, 0, False),
    ]
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'slots'
        for store, leaf in [(False, data[:82]), (True, data[82:])]:
            for case in cases:
                executable.write_bytes(image(leaf, store, *case))
                os.chmod(executable, 0o700)
                result = subprocess.run([executable], capture_output=True, timeout=5)
                assert result.returncode == 0 and not result.stdout and not result.stderr, (store, case, result)
    print('24 native slot cases passed')


if __name__ == '__main__':
    main()
