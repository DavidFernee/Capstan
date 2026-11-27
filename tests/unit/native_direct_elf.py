"""Run the CLI's direct ELF products on the Linux x86-64 kernel."""

import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def run_case(executable, sink):
    with sink.open("wb") as stream:
        result = subprocess.run(
            ["bash", "-c", 'exec "$1" 3>&1', "direct-elf", executable],
            stdout=stream,
            check=False,
            timeout=5,
        )
    return result.returncode, sink.read_bytes()


def main(capstan):
    cases = [
        ("return (-9223372036854775807 - 1);", 0, -(1 << 63)),
        ("return 9223372036854775807;", 0, (1 << 63) - 1),
        ("return -1000000000000 / 3 * 4 + -13 % 5 - 7;", 0, -1333333333342),
        ("return (-9223372036854775807 - 1) % -1;", 0, 0),
        ("return 9223372036854775807 + 1;", 70, None),
        ("return (-9223372036854775807 - 1) - 1;", 70, None),
        ("return 3037000500 * 3037000500;", 70, None),
        ("return (-9223372036854775807 - 1) / -1;", 70, None),
        ("int divisor = 0; return 7 / divisor;", 71, None),
        ("int divisor = 0; return -7 % divisor;", 71, None),
        (
            "int x = 42; if (!(x == 42)) { int divisor = 0; x = x / divisor; } "
            "else { x = x * 1000; } if (x < 42001) { x += 17; } return x;",
            0,
            42017,
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="capstan-direct-elf-") as directory:
        root = Path(directory)
        source = root / "main.cap"
        executable = root / "program"
        sink = root / "result"
        env = dict(os.environ, AS="/nonexistent/as", LD="/nonexistent/ld")
        command = [
            capstan, "native", "--direct", "--strict", "--root", root,
            source.name, "-o", executable,
        ]
        for body, status, value in cases:
            source.write_text(f"int main() {{ {body} }}\n", encoding="ascii")
            subprocess.run(command, env=env, check=True, timeout=60)
            actual_status, record = run_case(executable, sink)
            expected_record = b"" if value is None else struct.pack("<q", value)
            assert (actual_status, record) == (status, expected_record), (body, actual_status, record)

        image = executable.read_bytes()
        assert image[:7] == b"\x7fELF\x02\x01\x01"
        assert struct.unpack_from("<HH", image, 16) == (2, 62)  # ET_EXEC, EM_X86_64
        assert struct.unpack_from("<Q", image, 24) == (0x4000B0,)
        assert struct.unpack_from("<Q", image, 32) == (64,)
        assert struct.unpack_from("<HH", image, 54) == (56, 2)
        assert struct.unpack_from("<II", image, 64) == (1, 5)  # RX PT_LOAD
        assert struct.unpack_from("<II", image, 120) == (0x6474E551, 6)  # RW PT_GNU_STACK
        subprocess.run(command, env=env, check=True, timeout=60)
        assert executable.read_bytes() == image

        missing_fd = subprocess.run(
            ["bash", "-c", 'exec "$1" 3>&-', "direct-elf", executable],
            check=False,
            timeout=5,
        )
        assert missing_fd.returncode == 77
        full_fd = subprocess.run(
            ["bash", "-c", 'exec "$1" 3>/dev/full', "direct-elf", executable],
            check=False,
            timeout=5,
        )
        assert full_fd.returncode == 77

        # Match the reference machine's two-instruction CONST_I/RET vector.
        source.write_text("int main() { return 42; }\n", encoding="ascii")
        for limit in range(3):
            subprocess.run(command + ["--direct-steps", str(limit)], env=env, check=True, timeout=60)
            wanted = (0, struct.pack("<q", 42)) if limit == 2 else (73, b"")
            assert run_case(executable, sink) == wanted

        source.write_text(
            "int main() { int n = 1; while (n < 4) { n += 1; } return n; }\n",
            encoding="ascii",
        )
        subprocess.run(command, env=env, check=True, timeout=60)
        assert run_case(executable, sink) == (0, struct.pack("<q", 4))
        source.write_text("int main() { while (true) {} }\n", encoding="ascii")
        subprocess.run(command + ["--direct-steps", "20"], env=env, check=True, timeout=60)
        assert run_case(executable, sink) == (73, b"")

        image = executable.read_bytes()
        rejection = subprocess.run(
            command + ["--direct-steps", "10000001"], env=env,
            capture_output=True, text=True, timeout=60,
        )
        assert rejection.returncode == 2, rejection
        assert "step budget outside" in rejection.stdout, rejection
        assert executable.read_bytes() == image  # A failed compilation did not replace the artifact.
        assert not list(root.glob("program.*"))  # A failed compilation did not leave a staging file.
    print(f"{len(cases)} direct execution cases plus ELF, determinism, and failure-path checks passed")


if __name__ == "__main__":
    main(str(Path(sys.argv[1]).resolve()))
