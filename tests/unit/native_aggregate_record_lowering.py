"""Execute images emitted by Capstan, not substitute Python-generated code."""
import os
import struct
import subprocess
import sys
from pathlib import Path


def main():
    directory = Path(sys.argv[1])
    expected = {
        'loop': 23, 'min': -(1 << 63), 'div': -2, 'rem': 0,
        'negative-rem': -1,
        'calls': 235, 'recursion': 120, 'local-record': 63,
        'depth': None, 'callfuel': None,
        'reference': 42, 'reference-recursion': 15,
        'reference-mismatch': None,
        'mixed': 42, 'mixed-replace': 42, 'mixed-valid': 42,
        'mixed-mismatch': None,
        'bytes-index': 128, 'bytes-equal': 42, 'bytes-empty': 0,
        'bytes-oob': None, 'bytes-negative': None,
        'bytes-copy': 50, 'bytes-copy-empty': 3, 'bytes-max': 4096,
        'bytes-over': None, 'bytes-reversed': None, 'bytes-slice-oob': None,
        'bytes-slice-negative': None,
        'text-extrema': 42, 'text-byte-bool': 255,
        'text-byte-over': None, 'text-byte-negative': None,
        'list-int': 42, 'list-bool': 2, 'list-full': 255,
        'list-empty': 0, 'list-over': None, 'list-oob': None, 'list-negative': None,
        'list-string': 108, 'list-reference': 42,
        'list-reference-oob': None, 'list-reference-mismatch': None,
        'fuel': None, 'overflow': None, 'divoverflow': None, 'divzero': None,
    }
    for name, value in expected.items():
        executable = directory / f'ccam-native-record-{name}.elf'
        data = executable.read_bytes()
        assert data[:7] == b'\x7fELF\x02\x01\x01'
        assert struct.unpack_from('<H', data, 56)[0] == 2
        assert struct.unpack_from('<II', data, 120) == (0x6474e551, 6)
        assert struct.unpack_from('<II', data, 64) == (1, 5)
        os.chmod(executable, 0o700)
        run = subprocess.run([executable.resolve()], capture_output=True, timeout=5)
        if value is None:
            assert (run.returncode, run.stdout, run.stderr) == (1, b'', b''), (name, run)
        else:
            assert (run.returncode, run.stdout, run.stderr) == (0, struct.pack('<q', value), b''), (name, run)
    print(f'{len(expected)} direct native record/backend ELF cases passed')


if __name__ == '__main__':
    main()
