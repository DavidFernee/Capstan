"""Execute actual indexed lifecycle and allocator leaf bytes (Linux x86-64)."""
import ctypes as c
import mmap
import sys
from pathlib import Path

WRAP = bytes.fromhex('534154415541564989fb4889f34889d04989c84c8b234c8b6b084c8b7310488b7b18488b732041ffd34c89234c896b084c89731048897b1848897320415e415d415c5bc3')

class Result(c.Structure):
    _fields_ = [('value', c.c_uint64), ('status', c.c_uint64)]


def main():
    life = Path(sys.argv[1]).read_bytes()
    alloc = Path(sys.argv[2]).read_bytes()
    assert len(life) == 265 and len(alloc) == 350
    code = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE)
    code.write(WRAP + life + alloc)
    p = c.addressof(c.c_char.from_buffer(code))
    libc = c.CDLL(None, use_errno=True)
    libc.mprotect.argtypes = [c.c_void_p, c.c_size_t, c.c_int]
    assert libc.mprotect(p, 4096, mmap.PROT_READ | mmap.PROT_EXEC) == 0
    fn = c.CFUNCTYPE(Result, c.c_uint64, c.c_void_p, c.c_uint64, c.c_uint64)(p)
    s = (c.c_uint64 * 5)()
    n = 0
    def call(off, value=0, count=0):
        nonlocal n
        n += 1
        return fn(p + len(WRAP) + off, s, value, count)
    def reject(off, value=0):
        before = tuple(s)
        r = call(off, value)
        assert r.status == 1 and r.value == 0 and tuple(s) == before
    for cap in (0, 1, 1023, 1025, 67109888, 2**64-1): reject(0, cap)
    reject(144)
    for i in range(5):
        s[i] = 1
        reject(0, 1024)
        s[i] = 0
    for cap in (1024, 4096, 65536, 1048576, 67108864):
        r = call(0, cap)
        assert r.status == 0 and tuple(s) == (r.value, 0, cap, r.value+cap, cap//128)
        assert s[0] % 4096 == 0
        base = s[0]
        assert c.string_at(s[3],s[4]) == b'\0'*s[4]
        reject(0, cap)
        for i in (0,1,2,3,4):
            old = s[i]; s[i] += 1; reject(144); s[i] = old
        for count in (0,1,3,7):
            old = s[1]; r = call(265, 1, count)
            assert r.status == 0 and r.value == old and s[1] == old+16+16*count
            assert call(265+138,old).status == 0
            if count: assert call(265+138,old+16).status == 1
        r = call(144)
        assert (r.value,r.status,tuple(s)) == (0,0,(0,0,0,0,0))
        libc.mincore.argtypes = [c.c_void_p,c.c_size_t,c.c_void_p]
        vec = c.c_ubyte()
        for addr in (base,base+((cap+cap//128-1)//4096)*4096):
            c.set_errno(0)
            assert libc.mincore(addr,4096,c.byref(vec)) == -1 and c.get_errno() == 12
        reject(144)
    print(f'{n} indexed lifecycle/allocator native checks passed')

if __name__ == '__main__': main()
