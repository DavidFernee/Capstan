"""Execute the native scalar-list leaf from emitted bytes in standalone ELF files."""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

WORDS = 516
SIZE = WORDS * 8
MASK = (1 << 64) - 1


def image(leaf, state, tag, mode, index, value):
    code = bytearray.fromhex('4881ec') + struct.pack('<I', SIZE + 16)
    code.extend(bytes.fromhex('4989e74889e731c0b9') + struct.pack('<I', WORDS) + bytes.fromhex('fcf348ab4d89fc'))

    def mov(reg, word):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', word & MASK))

    for i, word in enumerate(state):
        if word:
            mov(3, word)
            code.extend(bytes.fromhex('49899f') + struct.pack('<I', i * 8))
    for reg, word in ((0, 0), (6, tag), (7, mode), (8, index), (9, value)):
        mov(reg, word)
    code.append(0xe8)
    call = len(code)
    code.extend(bytes(4))
    code.extend(bytes.fromhex('498987') + struct.pack('<I', SIZE))
    code.extend(bytes.fromhex('498997') + struct.pack('<I', SIZE + 8))
    mov(0, 1); mov(7, 1); mov(2, SIZE + 16)
    code.extend(bytes.fromhex('4c89fe0f0531ffb83c0000000f050f0b'))
    struct.pack_into('<i', code, call, len(code) - call - 4)
    code.extend(leaf)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x4000b0, 64, 0, 0, 64, 56, 2, 0, 0, 0)
    size = 176 + len(code)
    segment = struct.pack('<IIQQQQQQ', 1, 5, 0, 0x400000, 0x400000, size, size, 4096)
    stack = struct.pack('<IIQQQQQQ', 0x6474e551, 6, 0, 0, 0, 0, 0, 16)
    return header + segment + stack + code


def main():
    leaf = Path(sys.argv[1]).read_bytes()
    assert len(leaf) == 306
    count = 0
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'list'
        for tag in (4094, 4095):
            state = [tag, 257, 0, 1] + [0] * 512

            def check(mode, index=0, value=0, result=0, status=0, expected_tag=tag):
                nonlocal count
                before = state.copy()
                executable.write_bytes(image(leaf, before, expected_tag, mode, index, value))
                os.chmod(executable, 0o700)
                run = subprocess.run([executable], capture_output=True, timeout=5)
                assert (run.returncode, run.stderr, len(run.stdout)) == (0, b'', SIZE + 16), (mode, index, run)
                actual = list(struct.unpack('<' + 'Q' * (WORDS + 2), run.stdout))
                assert actual[-2:] == [result, status], (mode, index, actual[-2:])
                if not status:
                    if mode == 3:
                        i = state[2]; state[4 + 2*i:6 + 2*i] = [value, 1]; state[2] += 1
                    elif mode == 2:
                        state[4 + 2*index] = value
                    elif mode == 4 and state[2]:
                        state[2] -= 1; i = state[2]; state[4 + 2*i:6 + 2*i] = [0, 0]
                assert actual[:-2] == state, (mode, index, value, status)
                count += 1

            check(0); check(4); check(1, status=1); check(2, status=1)
            check(0, status=1, expected_tag=4095 if tag == 4094 else 4094)
            check(5, status=1)
            for i in range(256):
                value = i*123456789 if tag == 4094 else i%2
                check(3, value=value); check(1, index=i, result=value)
            check(0, result=256); check(3, status=1); check(1, index=256, status=1)
            check(1, index=MASK, status=1); check(2, index=42, value=1); check(1, index=42, result=1)
            if tag == 4095:
                check(2, index=42, value=2, status=1)
                state[88] = 2; check(1, index=42, status=1); state[88] = 1
            for _ in range(256):
                check(4)
            check(0); check(4)
            state[1] = 256; check(0, status=1); state[1] = 257
            state[2] = 257; check(0, status=1); state[2] = 0
            state[3] = 0; check(0, status=1)
    print(f'{count} native scalar list leaf cases passed')


if __name__ == '__main__':
    main()
