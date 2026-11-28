"""Compare emitted join bytes with reference assembly and independent arena oracle."""
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
    return struct.pack('<QQ',tag,len(data))+b''.join(struct.pack('<QQ',v,1) for v in data)

def lst(tag, offsets):
    return struct.pack('<QQQQ',tag,257,len(offsets),1)+b''.join(struct.pack('<QQ',v,1) for v in offsets)+bytes(16*(256-len(offsets)))

def main():
    raw=Path(sys.argv[1]).read_bytes()
    assert len(raw)==728 and hashlib.sha256(raw).hexdigest()=='494ec8f54f730d27a41a8fd6f1b8f79c10c9fe09b87acaee54f7dd359851ef0c'
    asm=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).resolve().parents[2]/'research/native-bootstrap/join-leaf.S'
    with tempfile.TemporaryDirectory() as tmp:
        o,b=Path(tmp)/'join.o',Path(tmp)/'join.bin'
        subprocess.run(['as','--64',str(asm),'-o',str(o)],check=True)
        subprocess.run(['objcopy','-O','binary','-j','.text',str(o),str(b)],check=True)
        assert b.read_bytes()==raw
    mem=mmap.mmap(-1,4096,prot=mmap.PROT_READ|mmap.PROT_WRITE)
    mem.write(raw)
    addr=c.addressof(c.c_char.from_buffer(mem))
    libc=c.CDLL(None)
    libc.mprotect.argtypes=[c.c_void_p,c.c_size_t,c.c_int]
    assert libc.mprotect(addr,4096,mmap.PROT_READ|mmap.PROT_EXEC)==0
    fn=c.CFUNCTYPE(Result,c.c_void_p,c.POINTER(c.c_uint64),*([c.c_uint64]*4))(addr)
    arena=(c.c_ubyte*262144)()
    cases=0
    def check(parts,sep,mode,*,wrong_list=False,wrong_part=False,wrong_sep=False,delta=None,corrupt=None,off=None):
        nonlocal cases
        tag=2045 if mode==1 else 4096
        data=obj(2045 if wrong_sep else 4096,sep)
        offsets=[]
        for i,part in enumerate(parts):
            offsets.append(len(data))
            data+=obj((4096 if tag==2045 else 2045) if wrong_part and i==0 else tag,part)
        receiver=len(data)
        data+=lst((4093 if mode==1 else 1024) if wrong_list else (1024 if mode==1 else 4093),offsets)
        if corrupt:
            data=bytearray(data)
            where,value=corrupt(receiver,offsets)
            struct.pack_into('<Q',data,where,value)
            data=bytes(data)
        expected=sep.join(parts)
        used=c.c_uint64(len(data)); cap=len(arena)
        valid=mode in (0,1) and not wrong_list and not (wrong_part and parts) and not wrong_sep and corrupt is None and off is None and len(expected)<=4096
        if delta is not None:
            cap=len(data)+16+16*len(expected)+delta
            valid=valid and delta>=0
        c.memset(arena,0xa5,len(arena)); c.memmove(arena,data,len(data)); before=bytes(arena)
        r=fn(arena,c.byref(used),cap,receiver if off is None else off,0,mode)
        if valid:
            new=obj(tag,expected)
            assert (r.value,r.status,used.value)==(len(data),0,len(data)+len(new)),(mode,len(parts),r.value,r.status)
            assert bytes(arena)==before[:len(data)]+new+before[len(data)+len(new):]
        else:
            assert (r.value,r.status,used.value)==(0,1,len(data)) and bytes(arena)==before,(mode,len(parts),r.value,r.status)
        cases+=1
    rng=random.Random(674)
    for _ in range(1000):
        parts=[rng.randbytes(rng.randrange(48)) for _ in range(rng.randrange(12))]
        sep=rng.randbytes(rng.randrange(8)); mode=rng.randrange(2)
        check(parts,sep,mode); check(parts,sep,mode,delta=0); check(parts,sep,mode,delta=-1)
    for mode in (0,1):
        for parts,sep in (([],b'x'),([b''],b''),([b'x']*256,b'-'),([b'a'*4096],b''),([b'a'*4096,b'b'],b''),([b'']*2,b'z'*4096)):
            check(parts,sep,mode)
        check([b'a'],b'-',mode,wrong_list=True)
        check([b'a'],b'-',mode,wrong_part=True)
        check([],b'-',mode,wrong_sep=True)
        for off in (1,16,-1): check([b'a'],b'-',mode,off=off)
        for corrupt in (lambda r,o:(r+8,256),lambda r,o:(r+16,257),lambda r,o:(r+24,0),lambda r,o:(r+40,0),lambda r,o:(r+32,16),lambda r,o:(o[0]+16,256),lambda r,o:(o[0]+24,0)):
            check([b'a'],b'-',mode,corrupt=corrupt)
    check([],b'',2)
    print(f'{cases} native join differential and boundary cases passed')
if __name__=='__main__': main()
