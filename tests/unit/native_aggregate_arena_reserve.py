"""Execute Capstan-emitted candidate arena leaf on Linux x86-64.

Python only orchestrates a test fixture. The leaf itself is emitted by
Capstan, with no assembler, linker, C runtime or interpreter in the ELF.
"""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MASK = (1 << 64) - 1
MAX = (1 << 63) - 1


def image(leaf, base, used, capacity, size, success):
    code = bytearray()
    branches = []

    def mov(register, value):
        code.extend((0x48 + register // 8, 0xB8 + register % 8))
        code.extend(struct.pack("<Q", value & MASK))

    def check(register, expected):
        mov(3, expected)
        code.extend((0x48 + register // 8, 0x39, 0xD8 + register % 8))
        code.extend(b"\x0f\x85")
        branches.append(len(code))
        code.extend(bytes(4))

    for register, value in ((12, base), (13, used), (14, capacity), (0, size)):
        mov(register, value)
    code.append(0xE8)
    call = len(code)
    code.extend(bytes(4))
    check(0, base + used if success else 0)
    check(2, 0 if success else 1)
    check(13, used + size if success else used)
    check(12, base)
    check(14, capacity)
    # Exit zero on success, one for a failed observation.
    code.extend(b"\x31\xff\xb8\x3c\x00\x00\x00\x0f\x05\x0f\x0b")
    fail = len(code)
    code.extend(b"\xbf\x01\x00\x00\x00\xb8\x3c\x00\x00\x00\x0f\x05\x0f\x0b")
    target = len(code)
    code.extend(leaf)
    struct.pack_into("<i", code, call, target - call - 4)
    for field in branches:
        struct.pack_into("<i", code, field, fail - field - 4)
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = struct.pack("<16sHHIQQQIHHHHHH", ident, 2, 62, 1, 0x4000B0,
                         64, 0, 0, 64, 56, 2, 0, 0, 0)
    length = 176 + len(code)
    segment = struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0x400000,
                          length, length, 4096)
    stack = struct.pack("<IIQQQQQQ", 0x6474E551, 6, 0, 0, 0, 0, 0, 16)
    return header + segment + stack + code


def main():
    leaf = Path(sys.argv[1]).read_bytes()
    assert len(leaf) == 67
    cases = [
        (4096, 0, 64, 16, True), (4096, 16, 64, 48, True),
        (4096, 64, 64, 0, True), (4096, 64, 64, 1, False),
        (4096, 65, 64, 0, False), (4096, 0, 64, MASK, False),
        (4096, MASK, 64, 0, False), (4096, 0, MASK, 0, False),
        (MASK - 7, 0, 8, 1, False), (0, 0, 64, 1, False),
        (4096, 0, 0, 0, True), (1, 0, MAX, MAX, True),
    ]
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / "arena-reserve"
        for case in cases:
            executable.write_bytes(image(leaf, *case))
            os.chmod(executable, 0o700)
            result = subprocess.run([executable], capture_output=True, timeout=5)
            assert result.returncode == 0 and not result.stdout and not result.stderr, (case, result)
    print("12 native arena reservation cases passed")


if __name__ == "__main__":
    main()
