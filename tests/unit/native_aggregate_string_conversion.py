"""Run Capstan-emitted conversion leaf in isolated freestanding ELF processes."""
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def image(leaf, value, mode, cap):
    # 512-byte sentinel backing plus 24-byte observation frame.
    code = bytearray.fromhex('4881ec180200004989e74889e748b8a5a5a5a5a5a5a5a5b940000000fcf348ab4d89fc')
    def mov(reg, x):
        code.extend((0x48 + reg // 8, 0xb8 + reg % 8))
        code.extend(struct.pack('<Q', x & ((1 << 64) - 1)))
    for reg, x in ((13, 16), (14, cap), (0, value), (8, mode)):
        mov(reg, x)
    code.append(0xe8)
    call = len(code)
    code.extend(bytes(4))
    # Observation after backing: result, status, committed cursor.
    code.extend(bytes.fromhex('49898700020000498997080200004d89af10020000'))
    mov(0, 1); mov(7, 1); mov(2, 536)
    code.extend(bytes.fromhex('4c89fe0f0531ffb83c0000000f050f0b'))
    struct.pack_into('<i', code, call, len(code) - call - 4)
    code.extend(leaf)
    ident = b'\x7fELF\x02\x01\x01' + bytes(9)
    header = struct.pack('<16sHHIQQQIHHHHHH', ident, 2, 62, 1, 0x4000b0,64,0,0,64,56,2,0,0,0)
    size = 176 + len(code)
    segment = struct.pack('<IIQQQQQQ',1,5,0,0x400000,0x400000,size,size,4096)
    stack = struct.pack('<IIQQQQQQ',0x6474e551,6,0,0,0,0,0,16)
    return header + segment + stack + code


def main():
    leaf = Path(sys.argv[1]).read_bytes()
    assert len(leaf) == 262
    cases = [(v,0,str(v).encode()) for v in (0,1,-1,9,10,-10,99,100,2**63-1,-2**63)]
    cases += [(v,1,bytes([v])) for v in (0,1,127,128,255)]
    cases += [(0,2,b'false'),(1,2,b'true')]
    cases += [(v,m,None) for v,m in ((-1,1),(256,1),(2,2),(-1,2),(0,3))]
    rng = random.Random(0)
    for _ in range(100):
        v = rng.randrange(-2**63,2**63)
        cases.append((v,0,str(v).encode()))
    count = 0
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / 'conversion'
        for value, mode, expected in cases:
            caps = [512] if expected is None else [512,32+16*len(expected),31+16*len(expected)]
            for cap in caps:
                executable.write_bytes(image(leaf,value,mode,cap))
                os.chmod(executable,0o700)
                result = subprocess.run([executable],capture_output=True,timeout=5)
                assert result.returncode == 0 and not result.stderr and len(result.stdout) == 536, (value,mode,cap,result)
                data = result.stdout[:512]
                state = struct.unpack_from('<QQQ',result.stdout,512)
                if expected is None or cap < 32+16*len(expected):
                    assert state == (0,1,16) and data == b'\xa5'*512, (value,mode,cap,state)
                else:
                    end = 32+16*len(expected)
                    assert state == (16,0,end) and data[:16] == b'\xa5'*16 and data[end:] == b'\xa5'*(512-end)
                    assert struct.unpack_from('<QQ',data,16) == (4096,len(expected))
                    assert all(struct.unpack_from('<QQ',data,32+16*i) == (v,1) for i,v in enumerate(expected))
                count += 1
    print(f'{count} native string conversion cases passed')


if __name__ == '__main__':
    main()
