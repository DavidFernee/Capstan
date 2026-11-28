"""Test the actual indexed-arena leaf bytes on Linux x86-64 via a test-only ABI adapter."""
import ctypes as c
import mmap
import struct
import sys
from pathlib import Path

class Result(c.Structure):
    _fields_=[('value',c.c_uint64),('status',c.c_uint64)]

WRAP=bytes.fromhex('415441554156534989fb4989f44889d34c8b2b4989ce4c89c74c89ce488b4424284c8b44243041ffd34c892b5b415e415d415cc3')

def main():
    leaf=Path(sys.argv[1]).read_bytes()
    assert len(leaf)==350
    mem=mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE)
    mem.write(WRAP+leaf)
    p=c.addressof(c.c_char.from_buffer(mem))
    libc=c.CDLL(None,use_errno=True)
    libc.mprotect.argtypes=[c.c_void_p,c.c_size_t,c.c_int]
    assert libc.mprotect(p,4096,mmap.PROT_READ|mmap.PROT_EXEC)==0
    fn=c.CFUNCTYPE(Result,*([c.c_uint64]*8))(p)
    n=0
    def invoke(a, bits, used, cap, arg, count=0, guard=False, bitlen=None, base=None, bitbase=None):
        nonlocal n
        n+=1
        return fn(p+len(WRAP)+(138 if guard else 0),c.addressof(a) if base is None else base,c.addressof(used),cap,c.addressof(bits) if bitbase is None else bitbase,len(bits) if bitlen is None else bitlen,arg,count)
    for cap in (1024, 65536, 67108864):
        a=(c.c_ubyte*cap)(); bits=(c.c_ubyte*(cap//128))(); used=c.c_uint64(0)
        # fill large extents, then exactly exhaust the last remainder
        starts=[]
        while used.value<cap:
            old=used.value; count=min(4096,(cap-old)//16-1)
            res=invoke(a,bits,used,cap,1,count)
            assert (res.value,res.status,used.value)==(old,0,old+16+16*count)
            starts.append(old)
            assert struct.unpack_from('<QQ',a,old)==(1,count)
            assert not any(a[old+16:used.value])
            assert bits[old//128] & (1<<(old//16%8))
            if count:
                res=invoke(a,bits,used,cap,old+16,guard=True); assert res.status==1
        for off in starts:
            res=invoke(a,bits,used,cap,off,guard=True); assert (res.value,res.status)==(off,0)
        assert sum(b.bit_count() for b in bits)==len(starts)
        before=bytes(bits); res=invoke(a,bits,used,cap,1); assert res.status==1 and used.value==cap and bytes(bits)==before
        for off in (1,cap,cap+16,(1<<64)-1): assert invoke(a,bits,used,cap,off,guard=True).status==1
    a=(c.c_ubyte*1024)(); bits=(c.c_ubyte*8)(); used=c.c_uint64(0)
    def reject(arg=1,count=0,cap=1024,**kw):
        before=(bytes(a),bytes(bits),used.value)
        r=invoke(a,bits,used,cap,arg,count,**kw)
        assert r.status==1 and before==(bytes(a),bytes(bits),used.value)
    for arg,count in ((0,0),(4097,0),(1,4097),(1,64),(1,(1<<64)-1)):
        reject(arg,count)
    for cap in (0,1008,67109888): reject(cap=cap)
    reject(bitlen=7); reject(bitlen=9); reject(base=0); reject(base=c.addressof(a)+1)
    reject(bitbase=0); reject(bitbase=c.addressof(a)); reject(bitbase=c.addressof(bits)+1)
    reject(base=(1<<64)-16); reject(bitbase=(1<<64)-8)
    bits[0]=1; reject(); bits[0]=0
    used.value=1; reject(); used.value=0
    r=invoke(a,bits,used,1024,4096,2); assert (r.value,r.status)==(0,0)
    # Forged interior header must not become a valid object start.
    struct.pack_into('<QQ',a,16,1,0)
    reject(16,guard=True)
    # Guard validates the indexed object's header and extent.
    struct.pack_into('<Q',a,0,0); reject(0,guard=True)
    struct.pack_into('<QQ',a,0,1,4096); reject(0,guard=True)
    struct.pack_into('<QQ',a,0,1,2); assert invoke(a,bits,used,1024,0,guard=True).status==0
    print(f'{n} indexed arena native allocation/membership cases passed')

if __name__=='__main__': main()
