"""Execute the bounded native log byte leaf and compare with independent UTF-8 oracle."""
import ctypes as c
import hashlib
import mmap
import random
import subprocess
import sys
import tempfile
from pathlib import Path


def escape(data):
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if 32 <= b < 127:
            out.append(b)
            i += 1
            continue
        n = 2 if 0xc2 <= b <= 0xdf else 3 if 0xe0 <= b <= 0xef else 4 if 0xf0 <= b <= 0xf4 else 0
        cp = None
        if n and i + n <= len(data):
            try:
                cp = ord(data[i:i+n].decode('utf-8', 'strict'))
            except (UnicodeDecodeError, TypeError):
                pass
        if cp is None:
            n = 1
        hostile = (cp is None or 0x80 <= cp <= 0x9f or
                   cp in (0x61c, 0x200e, 0x200f, 0xfeff) or
                   0x2028 <= cp <= 0x202e or 0x2066 <= cp <= 0x2069)
        if hostile:
            out.extend(b''.join(b'\\x%02x' % v for v in data[i:i+n]))
        else:
            out.extend(data[i:i+n])
        i += n
    return bytes(out)


def main():
    raw = Path(sys.argv[1]).read_bytes()
    assert len(raw) == 589
    assert hashlib.sha256(raw).hexdigest() == 'ccb9a463c0dda6e259b0cf595db0fd00f5f9433032a46b517113cbf2d5f30c98'
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory() as tmp:
        obj = Path(tmp) / 'escape.o'
        binary = Path(tmp) / 'escape.bin'
        subprocess.run(['as', '--64', str(root / 'research/native-bootstrap/escape-log-leaf.S'), '-o', str(obj)], check=True)
        subprocess.run(['objcopy', '-O', 'binary', '-j', '.text', str(obj), str(binary)], check=True)
        assert binary.read_bytes() == raw, 'assembly and Capstan emitter disagree'
    mem = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE)
    mem.write(raw)
    p = c.addressof(c.c_char.from_buffer(mem))
    libc = c.CDLL(None, use_errno=True)
    libc.mprotect.argtypes = [c.c_void_p, c.c_size_t, c.c_int]
    libc.mprotect.restype = c.c_int
    assert libc.mprotect(p, 4096, mmap.PROT_READ | mmap.PROT_EXEC) == 0
    fn = c.CFUNCTYPE(c.c_int64, c.c_void_p, c.c_uint64, c.c_void_p, c.c_uint64)(p)
    n = 0

    def check(data, cap=4096):
        nonlocal n
        inp = c.create_string_buffer(data)
        out = (c.c_ubyte * 4128)()
        c.memset(out, 0xa5, len(out))
        before = bytes(out)
        expected = escape(data)
        ret = fn(inp, len(data), c.byref(out, 16), cap)
        if len(data) > 4096 or cap > 4096 or len(expected) > cap:
            assert ret == -1 and bytes(out) == before, (data[:16], cap, ret)
        else:
            assert ret == len(expected) and bytes(out) == before[:16] + expected + before[16+ret:], (data[:16], cap, ret)
        assert inp.raw == data + b'\0'
        n += 1

    for b in range(256):
        check(bytes([b]))
    for a in range(128, 256):
        for b in range(256):
            check(bytes([a, b]))
    rng = random.Random(921)
    pool = [0xc2, 0xdf, 0xe0, 0xe1, 0xe2, 0xed, 0xef, 0xf0, 0xf4, 0xf5, 0x80, 0x8f, 0x90, 0x9f, 0xa0, 0xbf, 0xc0, 0x28, 0x41, 0xa]
    for _ in range(10000):
        check(bytes(rng.choice(pool) for _ in range(rng.randint(0, 12))))
    for cp in (0x7f, 0x80, 0x9f, 0xa0, 0x61c, 0x200d, 0x200e, 0x200f, 0x2027, 0x2028, 0x202e, 0x202f, 0x2065, 0x2066, 0x2069, 0x206a, 0xfeff, 0x10000, 0x10ffff):
        data = chr(cp).encode()
        check(data)
        check(data, len(escape(data)))
        check(data, len(escape(data))-1)
    for data in (b'', b'A'*4096, b'A'*4097, b'\0'*1024, b'\0'*1025, b'abc\x1b', b'\xf4\x8f\xbf\xbf'):
        check(data)
        check(data, 0)
        check(data, 4097)
    assert fn(None, 1, None, 4096) == -1 and fn(None, 0, None, 0) == 0
    print(f'{n} differential and boundary cases passed')


if __name__ == '__main__':
    main()
