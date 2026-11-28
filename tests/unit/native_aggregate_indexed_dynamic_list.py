"""Exercise actual indexed dynamic scalar lists and native lifecycle on Linux x86-64."""
import ctypes as c
import mmap
import sys
from pathlib import Path

WRAP = bytes.fromhex('534154415541564989fb4889f34889d04d89ca4d89c14989c84c8b234c8b6b084c8b7310488b7b18488b732041ffd34c89234c896b084c89731048897b1848897320415e415d415c5bc3')

class Result(c.Structure):
    _fields_ = [('value', c.c_uint64), ('status', c.c_uint64)]

def main():
    life = Path(sys.argv[1]).read_bytes()
    leaf = Path(sys.argv[2]).read_bytes()
    assert len(life) == 265 and len(leaf) == 1153
    mem = mmap.mmap(-1, 4096, prot=mmap.PROT_READ | mmap.PROT_WRITE)
    mem.write(WRAP + life + leaf)
    p = c.addressof(c.c_char.from_buffer(mem))
    libc = c.CDLL(None)
    libc.mprotect.argtypes = [c.c_void_p, c.c_size_t, c.c_int]
    assert libc.mprotect(p, 4096, mmap.PROT_READ | mmap.PROT_EXEC) == 0
    fn = c.CFUNCTYPE(Result, c.c_uint64, c.c_void_p, *([c.c_uint64]*4))(p)
    s = (c.c_uint64*5)()
    n = 0

    def call(off, a=0, b=0, d=0, e=0):
        nonlocal n
        n += 1
        return fn(p+len(WRAP)+off,s,a,b,d,e)

    def check(h, mode, i=0, v=0, result=0, status=0):
        old = s[1]
        before = (c.string_at(s[0],old), c.string_at(s[3],s[4])) if status else None
        r = call(265,h,mode,i,v)
        assert (r.value,r.status) == (result,status), (h,mode,i,v,r.value,r.status,result,status)
        if status:
            assert s[1] == old and before == (c.string_at(s[0],old), c.string_at(s[3],s[4]))
        return r.value

    assert call(0,1048576).status == 0
    for mode in (0,1):
        h = check(0,mode,result=s[1])
        check(h,2); check(h,6); check(h,3,status=1)
        for i in range(4096):
            v = i if mode == 0 else i%2
            check(h,5,v=v); check(h,3,i,result=v)
        check(h,2,result=4096); check(h,5,status=1); check(h,3,4096,status=1)
        check(h,4,2,v=1); check(h,3,2,result=1)
        if mode: check(h,4,2,v=2,status=1)
        for i in range(4096): check(h,6)
        check(h,2); check(h,6); check(h,5,v=1); check(h,3,result=1)
    assert call(144).status == 0
    assert call(0,1024).status == 0
    h = check(0,0,result=0)
    for i in range(16): check(h,5,v=i)
    check(h,5,v=20,status=1); check(h,2,result=16); check(h,3,15,result=15)
    assert call(144).status == 0
    print(f'{n} indexed dynamic list/lifecycle operations passed')

if __name__ == '__main__': main()
