"""Run emitted scalar-record leaves in standalone Linux x86-64 ELF images."""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MASK = (1 << 64) - 1
SENTINEL = 0x1122334455667788
VALUE = 0xfedcba9876543210


def image(leaves, case):
    code = bytearray(b'\x48\x81\xec\x80\x00\x00\x00\x49\x89\xe7')
    failures, calls = [], []

    def mov(reg, value):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', value & MASK))

    def jne():
        code.extend(b'\x0f\x85')
        failures.append(len(code))
        code.extend(bytes(4))

    def check(reg, value):
        mov(3, value)
        code.extend((0x48 + reg // 8, 0x39, 0xd8 + reg % 8))
        jne()

    def memory(offset, value, write=False):
        mov(3, value)
        code.extend((0x49, 0x89 if write else 0x39, 0x5f, offset))
        if not write:
            jne()

    def call(name, args):
        for reg, value in args:
            mov(reg, value)
        code.append(0xe8)
        calls.append((len(code), name))
        code.extend(bytes(4))

    def allocate(desc, count):
        call('alloc', ((0, desc), (6, count)))

    def access(name, offset, desc, count, index):
        call(name, ((0, offset), (6, desc), (7, count), (8, index), (9, VALUE)))

    def result(ok, value, used, capacity):
        check(2, int(not ok))
        check(0, value)
        check(13, used)
        check(14, capacity)
        code.extend(b'\x4d\x39\xfc')
        jne()

    for offset in range(0, 128, 8):
        memory(offset, SENTINEL, True)
    code.extend(b'\x4d\x89\xfc')
    if case[0] == 'reject-alloc':
        _, desc, count, used, capacity = case
        mov(13, used)
        mov(14, capacity)
        allocate(desc, count)
        result(False, 0, used, capacity)
        for offset in range(0, 128, 8):
            memory(offset, SENTINEL)
    elif case[0] == 'roundtrip':
        mov(13, 0)
        mov(14, 80)
        allocate(7, 2)
        result(True, 0, 48, 80)
        for offset, value in enumerate((7, 2, 0, 0, 0, 0)):
            memory(offset * 8, value)
        allocate(9, 1)
        result(True, 48, 80, 80)
        access('load', 0, 7, 2, 1)
        result(False, 0, 80, 80)
        access('store', 0, 7, 2, 1)
        result(True, 0, 80, 80)
        access('load', 0, 7, 2, 1)
        result(True, VALUE, 80, 80)
        access('load', 48, 9, 1, 0)
        result(False, 0, 80, 80)
        for offset, value in enumerate((7, 2, 0, 0, VALUE, 1, 9, 1, 0, 0)):
            memory(offset * 8, value)
        allocate(1, 0)
        result(False, 0, 80, 80)
        memory(80, SENTINEL)
    else:
        _, name, offset, desc, count, index, flag = case
        mov(13, 0)
        mov(14, 64)
        allocate(7, 2)
        result(True, 0, 48, 64)
        memory(24, flag, True)
        access(name, offset, desc, count, index)
        result(False, 0, 48, 64)
        for pos, value in enumerate((7, 2, 0, flag, 0, 0, SENTINEL)):
            memory(pos * 8, value)
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
    assert len(data) == 493
    leaves = dict(zip(('alloc', 'load', 'store'), (data[:137], data[137:308], data[308:])))
    cases = [('roundtrip',)]
    cases += [('reject-alloc', *c) for c in [(0, 1, 0, 64), (4097, 1, 0, 64),
              (-1, 1, 0, 64), (1, -1, 0, 64), (1, 4097, 0, 64),
              (1, 4, 0, 64), (1, 0, 1, 64), (1, 0, 72, 64),
              (1, 0, -8, 64), (1, 0, 0, -1), (1, 0, 0, 67108865)]]
    for name in ('load', 'store'):
        cases += [('reject-access', name, *c) for c in [(0, 8, 2, 0, 1),
                  (0, 7, 1, 0, 1), (0, 7, 2, 2, 1), (0, 7, 2, -1, 1),
                  (1, 7, 2, 0, 1), (-8, 7, 2, 0, 1), (48, 7, 2, 0, 1),
                  (0, 7, 2, 0, 2)]]
    cases.append(('reject-access', 'load', 0, 7, 2, 0, 0))
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'record'
        for case in cases:
            executable.write_bytes(image(leaves, case))
            os.chmod(executable, 0o700)
            result = subprocess.run([executable], capture_output=True, timeout=5)
            assert result.returncode == 0 and not result.stdout and not result.stderr, (case, result)
    print(f'{len(cases)} native scalar-record cases passed')


if __name__ == '__main__':
    main()
