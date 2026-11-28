"""Check exact composed LogText leaf bytes and execute independent arena oracle."""
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

def obj(tag, data):
    return struct.pack('<QQ', tag, len(data)) + b''.join(struct.pack('<QQ', x, 1) for x in data)

def esc(data):
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if 32 <= b < 127:
            out.append(b)
            i += 1
            continue
        n = 2 if 194 <= b <= 223 else 3 if 224 <= b <= 239 else 4 if 240 <= b <= 244 else 1
        try:
            cp = ord(data[i:i+n].decode('utf8')) if n > 1 else None
        except (UnicodeDecodeError, TypeError):
            cp = None
        if cp is None:
            n = 1
        hostile = (cp is None or 128 <= cp <= 159 or cp in (1564, 8206, 8207, 65279)
                   or 8232 <= cp <= 8238 or 8294 <= cp <= 8297)
        out.extend(b''.join(b'\\x%02x' % v for v in data[i:i+n]) if hostile else data[i:i+n])
        i += n
    return bytes(out)

def main():
    bridge = Path(sys.argv[1]).read_bytes()
    assert len(bridge) == 1263
    assert hashlib.sha256(bridge).hexdigest() == '64267c0dcafe3e3d82aa0291706abadd9cdc8e445e31c99f5490510b29627da0'
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory() as tmp:
        o, b = Path(tmp) / 'bridge.o', Path(tmp) / 'bridge.bin'
        subprocess.run(['as', '--64', str(root / 'research/native-bootstrap/log-bridge-leaf.S'), '-o', str(o)], check=True)
        subprocess.run(['objcopy', '-O', 'binary', '-j', '.text', str(o), str(b)], check=True)
        assert b.read_bytes() == bridge[:674]
    assert bridge[674:] == (Path(sys.argv[1]).parent / 'ccam-native-log-escape.bin').read_bytes()
    mem = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE)
    mem.write(bridge)
    addr = c.addressof(c.c_char.from_buffer(mem))
    libc = c.CDLL(None)
    libc.mprotect.argtypes = [c.c_void_p, c.c_size_t, c.c_int]
    assert libc.mprotect(addr, 4096, mmap.PROT_READ | mmap.PROT_EXEC) == 0
    fn = c.CFUNCTYPE(Result, c.c_void_p, c.POINTER(c.c_uint64), *([c.c_uint64]*4))(addr)
    arena = (c.c_ubyte * 200000)()
    cases = 0

    def check(a, b, tag1, tag2, mode, delta=None, corrupt=None, offset=None):
        nonlocal cases
        first = obj(tag1, a)
        initial = first + obj(tag2, b)
        used = c.c_uint64(len(initial))
        cap = len(arena)
        valid = (tag1 in (2045, 2046, 4096) and
                 (mode == 0 or (mode == 1 and tag1 in (2046, 4096) and tag2 in (2046, 4096)
                                and 2046 in (tag1, tag2))) and corrupt is None and offset is None)
        want = esc(a) if mode == 0 else a + b
        valid = valid and len(want) <= 4096
        if delta is not None:
            cap = len(initial) + 16 + 16 * len(want) + delta
            valid = valid and delta >= 0
        data = bytearray(initial)
        if corrupt:
            struct.pack_into('<Q', data, *corrupt)
        c.memset(arena, 0xa5, len(arena))
        c.memmove(arena, bytes(data), len(data))
        before = bytes(arena)
        result = fn(arena, c.byref(used), cap, 0 if offset is None else offset, len(first), mode)
        if valid:
            new = obj(2046, want)
            assert (result.value, result.status, used.value) == (len(initial), 0, len(initial)+len(new))
            assert bytes(arena) == before[:len(initial)] + new + before[len(initial)+len(new):]
        else:
            assert (result.value, result.status, used.value) == (0, 1, len(initial)) and bytes(arena) == before
        cases += 1

    rng = random.Random(674)
    for _ in range(1500):
        a = rng.randbytes(rng.randrange(60))
        b = rng.randbytes(rng.randrange(60))
        t1 = rng.choice([2045, 2046, 4096, 1])
        t2 = rng.choice([2045, 2046, 4096, 1])
        mode = rng.randrange(2)
        check(a, b, t1, t2, mode)
        check(a, b, t1, t2, mode, -1)
    for a in (b'', b'A'*4096, b'\x00'*1024, b'\x00'*1025, b'\xe2\x80\xae', b'\xf4\x8f\xbf\xbf'):
        check(a, b'', 2045, 4096, 0)
    for off in (1, 16, 32, -1):
        check(b'abc', b'', 2045, 4096, 0, offset=off)
    for corrupt in ((0, 0), (8, 4097), (16, 256), (24, 0), (48, 256)):
        check(b'abc', b'', 2045, 4096, 0, corrupt=corrupt)
    print(f'{cases} LogText bridge differential and boundary cases passed')

if __name__ == '__main__':
    main()
