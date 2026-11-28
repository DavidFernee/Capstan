"""Run the borrowed-FD input leaf from a Capstan-emitted binary on Linux x86-64."""
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

SIZE = 16 + 16 + 4096 * 16
MASK = (1 << 64) - 1


def image(leaf, fd, limit, capacity):
    # Sentinel arena and observation frame; no libc or interpreter in child.
    code = bytearray.fromhex('4881ec') + struct.pack('<I', SIZE + 24)
    code.extend(bytes.fromhex('4989e74889e748b8a5a5a5a5a5a5a5a5b9') + struct.pack('<I', SIZE // 8) + bytes.fromhex('fcf348ab4d89fc'))

    def mov(reg, value):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', value & MASK))

    for reg, value in ((13, 16), (14, capacity), (0, fd), (8, limit)):
        mov(reg, value)
    code.append(0xe8)
    call = len(code)
    code.extend(bytes(4))
    for opcode, offset in (('498987', SIZE), ('498997', SIZE + 8), ('4d89af', SIZE + 16)):
        code.extend(bytes.fromhex(opcode) + struct.pack('<I', offset))
    # Write observation with short-write loop (stdout is a pipe).
    mov(0, 1); mov(7, 1); mov(2, SIZE + 24)
    code.extend(bytes.fromhex('4c89fe0f054885c07e1a4801c64829c27407b801000000ebea31ffb83c0000000f050f0bbf01000000b83c0000000f050f0b'))
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
    assert len(leaf) == 278
    sentinel = b'\xa5' * SIZE
    count = 0
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'reader'
        source = Path(directory) / 'input'

        def check(fd, limit, capacity, expected, inherited=()):
            nonlocal count
            executable.write_bytes(image(leaf, fd, limit, capacity))
            os.chmod(executable, 0o700)
            p = subprocess.run([executable], pass_fds=inherited, capture_output=True, timeout=5)
            assert p.returncode == 0 and not p.stderr and len(p.stdout) == SIZE + 24, (fd, limit, capacity, p.returncode, len(p.stdout))
            memory, state = p.stdout[:SIZE], struct.unpack_from('<QQQ', p.stdout, SIZE)
            if expected is None:
                assert state == (0, 1, 16) and memory == sentinel, (limit, capacity, state)
            else:
                object_bytes = struct.pack('<QQ', 2045, len(expected)) + b''.join(struct.pack('<QQ', b, 1) for b in expected)
                end = 16 + len(object_bytes)
                assert state == (16, 0, end) and memory == sentinel[:16] + object_bytes + sentinel[end:], (limit, capacity, state)
            count += 1

        for data in (b'', b'\x00', b'a\x00\xffb', bytes(range(256)), b'x'*4095, b'y'*4096, b'z'*4097):
            source.write_bytes(data)
            with source.open('rb') as stream:
                fd = stream.fileno()
                stream.seek(3)
                for limit in sorted({0, 1, 4096, min(len(data),4096), max(0,min(len(data)-1,4096))}):
                    expected = data if len(data) <= limit else None
                    check(fd, limit, SIZE, expected, (fd,))
                    assert stream.tell() == 3
                if len(data) <= 4096:
                    need = 32 + 16*len(data)
                    check(fd, len(data), need, data, (fd,))
                    check(fd, len(data), need-1, None, (fd,))
                check(fd, 4097, SIZE, None, (fd,))
                check(fd, -1, SIZE, None, (fd,))
                assert stream.tell() == 3
        for fd in (-1, 2147483648, 123456):
            check(fd, 4096, SIZE, None)
        fd = os.open(directory, os.O_RDONLY)
        try:
            check(fd, 4096, SIZE, None, (fd,))
        finally:
            os.close(fd)
        r, w = os.pipe()
        try:
            os.write(w, b'test')
            check(r, 4096, SIZE, None, (r,))
            assert os.read(r, 4) == b'test'
        finally:
            os.close(r)
            os.close(w)
        fd = os.open(source, os.O_WRONLY)
        try:
            check(fd, 4096, SIZE, None, (fd,))
        finally:
            os.close(fd)
    print(f'{count} borrowed-FD native input cases passed')


if __name__ == '__main__':
    main()
