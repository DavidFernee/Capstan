"""Execute the candidate taint validation leaf on Linux x86-64."""
import ctypes as c
import mmap
import random
import re
import struct
import sys
from pathlib import Path

WRAP = bytes.fromhex('534154415541564989fb4989f44889d34c8b2b4989ce4c89c04d89c841ffd34c892b415e415d415c5bc3')
MASK = (1 << 64) - 1
class Result(c.Structure):
    _fields_ = [('value', c.c_uint64), ('status', c.c_uint64)]

def escape(data):
    return b''.join(b'\\'+bytes([b]) if b in (34,63,92) else bytes([b]) if 32<=b<127 else ('\\%03o'%b).encode() for b in data)

def main():
    leaf = Path(sys.argv[1]).read_bytes()
    assert len(leaf)==1059
    mem = mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE)
    mem.write(WRAP+leaf)
    p=c.addressof(c.c_char.from_buffer(mem))
    libc=c.CDLL(None,use_errno=True)
    libc.mprotect.argtypes=[c.c_void_p,c.c_size_t,c.c_int]
    assert libc.mprotect(p,4096,mmap.PROT_READ|mmap.PROT_EXEC)==0
    fn=c.CFUNCTYPE(Result,*([c.c_uint64]*6))(p)
    arena=(c.c_ubyte*262144)()
    n=0
    def obj(tag,data):
        return struct.pack('<QQ',tag,len(data))+b''.join(struct.pack('<QQ',b,1) for b in data)
    def check(data,mode,*,tag=None,offset=0,corrupt=None,cap_delta=None):
        nonlocal n
        if tag is None: tag=4096 if mode==3 else 2045
        start=obj(tag,data)
        if corrupt is not None:
            start=bytearray(start); struct.pack_into('<Q',start,*corrupt); start=bytes(start)
        used=c.c_uint64(len(start)); capacity=len(arena)
        expected=None; result=used.value
        if tag==(4096 if mode==3 else 2045) and offset==0 and corrupt is None:
            if mode==0:
                v=0; present=0
                if re.fullmatch(rb'-?[0-9]+',data):
                    # No arbitrary-size conversion: mirror bounded arithmetic.
                    neg=data.startswith(b'-')
                    for b in data[int(neg):]:
                        v=v*10+(-1 if neg else 1)*(b-48)
                        if not -(1<<63)<=v<(1<<63): break
                    else: present=1
                expected=struct.pack('<QQQQ',1021,1,v&MASK if present else 0,present)
            elif mode==1:
                if len(data)<=255 and re.fullmatch(rb'[A-Za-z_][A-Za-z_0-9]*',data):
                    string=obj(4096,data); result+=len(string)
                    expected=string+struct.pack('<QQQQ',1023,1,used.value,1)
                else: expected=struct.pack('<QQQQ',1023,1,0,0)
            elif mode==2:
                escaped=escape(data)
                if len(escaped)<=4096: expected=obj(4096,escaped)
            elif mode==3: expected=obj(2045,data)
        if cap_delta is not None:
            assert expected is not None
            capacity=used.value+len(expected)+cap_delta
            if cap_delta<0: expected=None
        c.memset(arena,0xa5,len(arena)); c.memmove(arena,start,len(start))
        before=bytes(arena); old=used.value
        r=fn(p+len(WRAP),c.addressof(arena),c.addressof(used),capacity,offset,mode)
        if expected is None:
            assert (r.value,r.status,used.value)==(0,1,old) and bytes(arena)==before,(data[:40],mode,r.value,r.status)
        else:
            end=old+len(expected)
            assert (r.value,r.status,used.value)==(result,0,end),(data[:40],mode,r.value,r.status,used.value)
            assert bytes(arena)==before[:old]+expected+before[end:],(data[:40],mode)
        n+=1
    rng=random.Random(921)
    values=[b'',b'-',b'+1',b'-0',b'00',b'1\x002',b' 1',b'1\n',b'9223372036854775807',b'9223372036854775808',b'-9223372036854775808',b'-9223372036854775809',b'0'*4096,b'9'*4096,b'-'+b'0'*4095,b'a',b'_a9',b'1a',b'abc'*85,b'a'*256,b'\xff',bytes(range(256)),b'\x00'*1024,b'\x00'*1025,b'A'*4096]
    for data in values:
        for mode in range(4): check(data,mode)
    for i in range(256):
        for mode in (0,1,2): check(bytes([i]),mode)
        check(b'a'+bytes([i]),1)
    for _ in range(300):
        data=bytes(rng.randrange(256) for _ in range(rng.randrange(64)))
        for mode in range(4): check(data,mode)
    for _ in range(250):
        v=rng.randrange(-(1<<64),1<<64)
        check(str(v).encode(),0)
    for mode in range(4):
        for data in (b'abc',b'42',b''):
            check(data,mode,cap_delta=0); check(data,mode,cap_delta=-1)
        check(b'a',mode,tag=2045 if mode==3 else 4096)
        check(b'a',mode,offset=16)
        check(b'a',mode,corrupt=(24,0)); check(b'a',mode,corrupt=(16,256))
    check(b'a',4)
    print(f'{n} taint validation native execution cases passed')

if __name__=='__main__': main()
