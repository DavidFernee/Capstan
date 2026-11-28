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
        'opt-scalar': 7, 'opt-record': 42, 'opt-string': 3, 'opt-absent': 42,
        'opt-unwrap-none': None, 'opt-mismatch': None,
        'map-int': 42, 'map-ref': 42, 'map-string-bool': 3,
        'map-full': 42, 'map-over': None,
        'map-snapshot': 33, 'map-remove': 42, 'map-empty-keys': 1,
        'module-constants': 42, 'module-41': 42, 'module-256': 42,
        'module-300': 42,
        'constant-min': -(1 << 63), 'constant-ops': 42,
        'taint-list': 101, 'taint-empty': 0, 'taint-slice-oob': None,
        'taint-negative': None, 'taint-list-oob': None, 'taint-field': 65,
        'log-present': 42, 'log-absent': 0,
        'join': 65,
        'validation': 42, 'validation-absent': 42, 'validation-escape': 94,
        'taint-build': 454, 'taint-char-negative': None, 'taint-char-over': None,
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
    executable = directory / 'ccam-native-record-stdout.elf'
    os.chmod(executable, 0o700)
    run = subprocess.run([executable.resolve()], capture_output=True, timeout=5)
    assert (run.returncode, run.stdout, run.stderr) == (0, b'prefix:\\x1b\n' + struct.pack('<q', 42), b''), run
    with open('/dev/full', 'wb') as full:
        run = subprocess.run([executable.resolve()], stdout=full, stderr=subprocess.PIPE, timeout=5)
    assert (run.returncode, run.stderr) == (1, b''), run
    cases = [
        ('argv', [], 0), ('argv', [b'abc'], 10003),
        ('argv', [b'', b'x'], 20000),
        ('argv', [b'x' * 4096], 14096),
        ('argv', [b'x' * 4097], None),
        ('argv', [b''] * 256, 2560000),
        ('argv', [b''] * 257, None),
        ('argv', [b'x' * 4096] * 20, None),
        ('bytes', [b'', b'\xff'], 255),
    ]
    for name, args, value in cases:
        executable = directory / f'ccam-native-record-process-{name}.elf'
        data = executable.read_bytes()
        assert data[:7] == b'\x7fELF\x02\x01\x01'
        assert struct.unpack_from('<II', data, 120) == (0x6474e551, 6)
        os.chmod(executable, 0o700)
        run = subprocess.run([executable.resolve(), *args], capture_output=True, timeout=5)
        if value is None:
            assert (run.returncode, run.stdout, run.stderr) == (1, b'', b''), (name, run)
        else:
            assert (run.returncode, run.stdout, run.stderr) == (0, struct.pack('<q', value), b''), (name, run)
    print(f'{len(expected)} direct native record/backend ELF cases and {len(cases)} process entry cases passed')


if __name__ == '__main__':
    main()
