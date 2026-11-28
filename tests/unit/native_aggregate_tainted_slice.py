"""Native tainted slice: execute exact emitted bytes, check arena and cursor."""
import ctypes as c
import hashlib
import mmap
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

class Result(c.Structure):
    _fields_ = [('value', c.c_uint64), ('status', c.c_uint64)]


def obj(data, tag=2045):
    return struct.pack('<QQ', tag, len(data)) + b''.join(struct.pack('<QQ', x, 1) for x in data)


def main():
    raw = Path(sys.argv[1]).read_bytes()
    assert len(raw) == 396
    assert hashlib.sha256(raw).hexdigest() == 'bff28dfa4b66bb608234ac9751e21b47ad40e88351a5e32213bce82f5c08de57'
    asm = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[2] / 'research/native-bootstrap/tainted-slice-leaf.S'
    with tempfile.TemporaryDirectory() as tmp:
        o, b = Path(tmp) / 'slice.o', Path(tmp) / 'slice.bin'
        subprocess.run(['as', '--64', str(asm), '-o', str(o)], check=True)
        subprocess.run(['objcopy', '-O', 'binary', '-j', '.text', str(o), str(b)], check=True)
        assert b.read_bytes() == raw
    mem = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE)
    mem.write(raw)
    addr = c.addressof(c.c_char.from_buffer(mem))
    libc = c.CDLL(None, use_errno=True)
    libc.mprotect.argtypes = [c.c_void_p, c.c_size_t, c.c_int]
    assert libc.mprotect(addr, 4096, mmap.PROT_READ | mmap.PROT_EXEC) == 0
    fn = c.CFUNCTYPE(Result, c.c_void_p, c.POINTER(c.c_uint64), *([c.c_uint64]*4))(addr)
    arena = (c.c_ubyte * 262144)()
    n = 0

    def check(data, start, end, *, prefix=b'', tag=2045, corrupt=None, delta=None, offset=None, used_override=None, capacity_override=None):
        nonlocal n
        source = prefix + obj(data, tag)
        if corrupt is not None:
            source = bytearray(source)
            struct.pack_into('<Q', source, *corrupt)
            source = bytes(source)
        used = c.c_uint64(len(source) if used_override is None else used_override)
        at = len(prefix) if offset is None else offset
        capacity = len(arena) if capacity_override is None else capacity_override
        if delta is not None:
            capacity = len(source) + len(obj(data[start:end])) + delta
        c.memset(arena, 0xa5, len(arena))
        c.memmove(arena, source, len(source))
        before = bytes(arena)
        old = used.value
        valid = (tag == 2045 and corrupt is None and at == len(prefix) and
                 old == len(source) and 0 <= start <= end <= len(data) and
                 old + len(obj(data[start:end])) <= capacity <= len(arena))
        r = fn(arena, c.byref(used), capacity, at, start, end)
        if valid:
            expected = obj(data[start:end])
            assert (r.value, r.status, used.value) == (old, 0, old + len(expected))
            assert bytes(arena) == before[:old] + expected + before[old+len(expected):]
        else:
            assert (r.value, r.status, used.value) == (0, 1, old), (start, end, tag, at, capacity)
            assert bytes(arena) == before
        n += 1

    for data in (b'', b'a', bytes(range(32)), b'\xff\x00\x1b', b'abc'):
        for s in range(-1, len(data)+2):
            for e in range(-1, len(data)+2):
                check(data, s, e)
    for x in range(256):
        check(bytes([x]), 0, 1, prefix=obj(b'other', 4096))
    rng = random.Random(674)
    for _ in range(1500):
        data = rng.randbytes(rng.randrange(128))
        s = rng.randrange(len(data)+1)
        e = rng.randrange(s, len(data)+1)
        check(data, s, e, prefix=obj(b'') + obj(b'X', 4096))
        check(data, s, e, delta=0)
        check(data, s, e, delta=-1)
    for data in (bytes(range(256))*16, b'', b'abc'):
        check(data, 0, len(data))
        check(data, len(data), len(data))
        check(data, 0, len(data), delta=-1)
    for tag in (4096, 1024, 1):
        check(b'abc', 0, 1, tag=tag)
    for off in (1, 16, 32, 64, -1):
        check(b'abc', 0, 1, offset=off)
    for corrupt in ((0, 0), (8, 4097), (8, 999), (16, 256), (24, 0), (48, 256), (56, 2)):
        check(b'abc', 0, 1, corrupt=corrupt)
    for used in (0, 15, 63, 79, 1048577):
        check(b'abc', 0, 1, used_override=used)
    for capacity in (0, 63, 1048577):
        check(b'abc', 0, 1, capacity_override=capacity)
    print(f'{n} tainted slice native differential and boundary cases passed')

if __name__ == '__main__':
    main()
