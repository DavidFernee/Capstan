"""Execute native tainted-list leaf; compare complete arena against model."""
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


def list_obj(items):
    assert len(items) <= 256
    return struct.pack('<QQQQ', 1024, 257, len(items), 1) + b''.join(
        struct.pack('<QQ', x & ((1 << 64)-1), 1) for x in items) + bytes(16 * (256-len(items)))


def main():
    raw = Path(sys.argv[1]).read_bytes()
    assert len(raw) == 555
    assert hashlib.sha256(raw).hexdigest() == '64d204f4fb328011c8f0f0f77c11ee7eaadbb74400c7e012e14ebf336fc03292'
    asm = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[2] / 'research/native-bootstrap/tainted-list-leaf.S'
    with tempfile.TemporaryDirectory() as tmp:
        o, b = Path(tmp) / 'list.o', Path(tmp) / 'list.bin'
        subprocess.run(['as', '--64', str(asm), '-o', str(o)], check=True)
        subprocess.run(['objcopy', '-O', 'binary', '-j', '.text', str(o), str(b)], check=True)
        assert b.read_bytes() == raw
    mem = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE)
    mem.write(raw)
    addr = c.addressof(c.c_char.from_buffer(mem))
    libc = c.CDLL(None, use_errno=True)
    libc.mprotect.argtypes = [c.c_void_p, c.c_size_t, c.c_int]
    libc.mprotect.restype = c.c_int
    assert libc.mprotect(addr, 4096, mmap.PROT_READ | mmap.PROT_EXEC) == 0
    fn = c.CFUNCTYPE(Result, c.c_void_p, *([c.c_uint64]*5))(addr)
    first = obj(b'abc')
    second = obj(b'\xff\x00\x1b')
    trusted = obj(b'trusted', 4096)
    prefix = first + second + trusted
    receiver = len(prefix)
    good = [0, len(first)]
    bad = [len(first)+len(second), 16, receiver, -1, 1, receiver+16]
    arena = (c.c_ubyte * 16384)()
    cases = 0

    def check(items, mode, index=0, payload=0, *, corrupt=None, recv=None, extent=None, reject=False):
        nonlocal cases
        data = bytearray(prefix + list_obj(items))
        if corrupt is not None:
            struct.pack_into('<Q', data, *corrupt)
        used = len(data) if extent is None else extent
        offset = receiver if recv is None else recv
        c.memset(arena, 0xa5, len(arena))
        c.memmove(arena, bytes(data), len(data))
        before = bytes(arena)
        expected = list(items)
        result = 0
        valid = not reject and 0 <= mode <= 4
        if valid:
            if mode == 0:
                result = len(items)
            elif mode == 1:
                valid = 0 <= index < len(items) and items[index] in good
                if valid:
                    result = items[index]
            elif mode == 2:
                valid = 0 <= index < len(items) and items[index] in good and payload in good
                if valid:
                    expected[index] = payload
            elif mode == 3:
                valid = len(items) < 256 and payload in good
                if valid:
                    expected.append(payload)
            elif mode == 4:
                valid = not items or items[-1] in good
                if valid and items:
                    expected.pop()
        r = fn(arena, used, offset, mode, index, payload)
        if valid:
            assert (r.value, r.status) == (result, 0), (items[:5], mode, index, payload, r.value, r.status)
            want = before if mode in (0, 1) else prefix + list_obj(expected) + before[len(data):]
            assert bytes(arena) == want, (mode, index, payload)
        else:
            assert (r.value, r.status) == (0, 1) and bytes(arena) == before, (mode, index, payload, corrupt, recv, extent)
        cases += 1

    for items in ([], [0], good, [0]*255, [0]*256):
        for mode in range(-1, 6):
            for index in (-1, 0, len(items)-1, len(items), 256):
                for payload in good + bad:
                    check(items, mode, index, payload)
    rng = random.Random(674)
    for _ in range(3000):
        items = [rng.choice(good) for _ in range(rng.randrange(257))]
        check(items, rng.randrange(5), rng.randrange(-1, len(items)+1), rng.choice(good+bad))
    for mode in range(5):
        for corrupt in ((receiver, 4093), (receiver+8, 256), (receiver+16, 257), (receiver+24, 0)):
            check([0], mode, corrupt=corrupt, reject=True)
        for off in (0, 16, receiver+16, receiver+32, -1):
            check([0], mode, recv=off, reject=True)
        for size in (0, 15, receiver+16, receiver+32, 1048577):
            check([0], mode, extent=size, reject=True)
    for mode in (1, 2, 4):
        for corrupt in ((receiver+40, 0), (receiver+32, 16), (16, 256), (24, 0), (48, 256)):
            check([0], mode, corrupt=corrupt, reject=True)
    for corrupt in ((receiver+32, 1), (receiver+40, 1), (16, 256), (24, 0)):
        check([], 3, corrupt=corrupt, reject=True)
    for payload in bad:
        check([payload], 1)
        check([payload], 2, payload=0)
        check([payload], 4)
    assert fn(None, 0, 0, 0, 0, 0).status == 1
    print(f'{cases} tainted list differential and boundary cases passed')


if __name__ == '__main__':
    main()
