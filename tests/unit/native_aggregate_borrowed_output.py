"""Execute the borrowed regular-file output leaf from emitted bytes in freestanding ELF."""
import os
import resource
import signal
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MASK = (1 << 64) - 1


def image(leaf, state, fd, limit, offset, committed):
    size = len(state)
    code = bytearray.fromhex('4881ec') + struct.pack('<I', size + 24)
    code.extend(bytes.fromhex('4989e74889e7488d35'))
    data_disp = len(code); code.extend(bytes(4))
    code.extend(bytes.fromhex('b9') + struct.pack('<I', size//8) + bytes.fromhex('fcf348a54d89fc'))

    def mov(reg, value):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', value & MASK))

    for reg, value in ((13, committed), (14, size), (0, offset), (8, fd), (9, limit)):
        mov(reg, value)
    code.append(0xe8); call = len(code); code.extend(bytes(4))
    for opcode, pos in (('498987', size), ('498997', size+8), ('4d89af', size+16)):
        code.extend(bytes.fromhex(opcode) + struct.pack('<I', pos))
    mov(0, 1); mov(7, 1); mov(2, size + 24)
    code.extend(bytes.fromhex('4c89fe0f054885c07e1a4801c64829c27407b801000000ebea31ffb83c0000000f050f0bbf01000000b83c0000000f050f0b'))
    struct.pack_into('<i', code, call, len(code)-call-4)
    code.extend(leaf)
    struct.pack_into('<i', code, data_disp, len(code)-data_disp-4)
    code.extend(state)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x4000b0,64,0,0,64,56,2,0,0,0)
    end = 176+len(code)
    segment = struct.pack('<IIQQQQQQ',1,5,0,0x400000,0x400000,end,end,4096)
    stack = struct.pack('<IIQQQQQQ',0x6474e551,6,0,0,0,0,0,16)
    return header+segment+stack+code


def main():
    leaf = Path(sys.argv[1]).read_bytes()
    assert len(leaf) == 494
    count = 0
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory)/'writer'
        dest = Path(directory)/'output'
        initial = b'Z'*5000

        def check(fd, data, limit, expected, status, *, tag=4096, offset=0, ready=1, bad_byte=False, inherited=(), file_limit=None):
            nonlocal count
            state = struct.pack('<QQ',tag,len(data)) + b''.join(struct.pack('<QQ', 256 if bad_byte and i==0 else v, ready) for i,v in enumerate(data))
            used = len(state)
            state += b'\xa5'*32
            executable.write_bytes(image(leaf,state,fd,limit,offset,used)); os.chmod(executable,0o700)
            def restrict():
                signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
                resource.setrlimit(resource.RLIMIT_FSIZE,(file_limit,file_limit))
            p = subprocess.run([executable],pass_fds=inherited,capture_output=True,timeout=5,preexec_fn=restrict if file_limit is not None else None)
            assert p.returncode==0 and not p.stderr and len(p.stdout)==len(state)+24, (p.returncode,p.stderr,len(p.stdout))
            assert p.stdout[:len(state)]==state
            assert struct.unpack_from('<QQQ',p.stdout,len(state))==(expected,status,used), (limit,tag,offset,struct.unpack_from('<QQQ',p.stdout,len(state)))
            count+=1

        for data in (b'',b'\0',b'a\0\xffb',bytes(range(256)),b'x'*4095,b'y'*4096):
            for limit in sorted({0,1,4096,len(data),max(0,len(data)-1),4097,-1}):
                dest.write_bytes(initial)
                with dest.open('r+b') as f:
                    f.seek(7); fd=f.fileno(); ok=0<=limit<=4096 and len(data)<=limit
                    check(fd,data,limit,len(data) if ok else 0,0 if ok else 1,inherited=(fd,))
                    assert f.tell()==7
                assert dest.read_bytes()==(data+initial[len(data):] if ok else initial)
        for kwargs in ({'tag':2045},{'offset':8},{'ready':0},{'bad_byte':True}):
            dest.write_bytes(initial)
            with dest.open('r+b') as f:
                check(f.fileno(),b'abc',4096,0,1,inherited=(f.fileno(),),**kwargs)
            assert dest.read_bytes()==initial
        for flags in (os.O_RDONLY,os.O_WRONLY|os.O_APPEND,os.O_WRONLY|os.O_NONBLOCK,os.O_PATH):
            dest.write_bytes(initial); fd=os.open(dest,flags)
            try: check(fd,b'abc',4096,0,1,inherited=(fd,))
            finally: os.close(fd)
            assert dest.read_bytes()==initial
        for fd in (-1,2147483648,123456): check(fd,b'abc',4096,0,1)
        fd=os.open(directory,os.O_RDONLY)
        try: check(fd,b'abc',4096,0,1,inherited=(fd,))
        finally: os.close(fd)
        r,w=os.pipe()
        try: check(w,b'abc',4096,0,1,inherited=(w,))
        finally: os.close(w)
        assert os.read(r,1)==b''; os.close(r)
        dest.write_bytes(b'')
        with dest.open('r+b') as f:
            check(f.fileno(),b'abcdefgh',4096,3,1,inherited=(f.fileno(),),file_limit=3)
            assert f.tell()==0
        assert dest.read_bytes()==b'abc'
    print(f'{count} native borrowed-FD output cases passed')


if __name__=='__main__': main()
