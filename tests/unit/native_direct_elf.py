"""Run the CLI's direct ELF products on the Linux x86-64 kernel."""

import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def run_case(executable, sink):
    result = subprocess.run(
        ["bash", "-c", 'exec "$1" 3>"$2"', "direct-elf", executable, sink],
        capture_output=True,
        check=False,
        timeout=5,
    )
    assert result.stdout == result.stderr == b"", result
    return result.returncode, sink.read_bytes()


RESULT_HEADER = struct.Struct("<8sHHIqQIIII")
RECORD_TRAPS = {
    "integer_overflow": 1,
    "division_by_zero": 2,
    "step_limit_exceeded": 6,
    "explicit_trap": 8,
}


def decode_record(record):
    assert RESULT_HEADER.size <= len(record) <= 1136, record
    magic, version, kind, code, value, steps, function, pc, name_len, detail_len = (
        RESULT_HEADER.unpack_from(record)
    )
    assert magic == b"CCAMRES\0" and version == 1, record
    assert name_len <= 1024 and detail_len <= 64, record
    assert len(record) == RESULT_HEADER.size + name_len + detail_len, record
    name_end = RESULT_HEADER.size + name_len
    name = record[RESULT_HEADER.size:name_end]
    detail = record[name_end:]
    return kind, code, value, steps, function, pc, name, detail


def compare_ccam_vectors(capstan, directory):
    repo = Path(__file__).resolve().parents[2]
    generator = directory / "generate-vectors"
    subprocess.run(
        [
            capstan, "build", "--strict",
            repo / "verification/ccam_direct_elf.cap",
            repo / "tests/unit/native_direct_elf_vectors.cap",
            "-o", generator,
        ],
        check=True,
        timeout=60,
    )
    vectors = subprocess.run(
        [generator, directory], capture_output=True, text=True, check=True, timeout=10,
    ).stdout.splitlines()
    expected_trap = {
        "fuel-before-overflow": ("step_limit_exceeded", 2, 2, ""),
        "division-overflow": ("integer_overflow", 3, 2, ""),
        "fuel-before-return": ("step_limit_exceeded", 3, 3, ""),
        "remainder-by-zero": ("division_by_zero", 3, 2, ""),
        "division-by-zero": ("division_by_zero", 3, 2, ""),
        "loop-at-back-edge": ("step_limit_exceeded", 5, 3, ""),
        "loop-at-branch": ("step_limit_exceeded", 6, 2, ""),
        "fuel-before-explicit-trap": ("step_limit_exceeded", 3, 4, ""),
        "explicit-trap": ("explicit_trap", 4, 4, "chosen_stop"),
        "max-record": ("explicit_trap", 4, 4, "t" * 64),
    }
    expected_value = {"min-remainder": 0, "full-width-return": -(1 << 63)}
    native_status = {
        "integer_overflow": 70,
        "division_by_zero": 71,
        "explicit_trap": 72,
        "step_limit_exceeded": 73,
    }
    remaining = expected_trap.keys() | expected_value.keys()
    for row in vectors:
        name, trap, value, steps, function, pc, detail = row.split("\t")
        remaining.remove(name)
        if trap:
            assert (trap, int(steps), int(pc), detail) == expected_trap[name], row
            assert function == ("m" * 1024 if name == "max-record" else "main"), row
            expected = (native_status[trap], b"")
        else:
            assert int(value) == expected_value[name] and int(steps) == 4, row
            expected = (0, struct.pack("<q", int(value)))
        image = directory / name
        image.chmod(0o700)
        assert run_case(image, directory / "oracle-result") == expected, row
        record_image = directory / (name + ".record")
        record_image.chmod(0o700)
        status, record = run_case(record_image, directory / "oracle-record")
        assert status == 0, (row, status, record)
        if trap:
            expected_record = (
                2, RECORD_TRAPS[trap], 0, int(steps), 0, int(pc),
                function.encode("ascii"), detail.encode("ascii"),
            )
        else:
            expected_record = (0, 0, int(value), int(steps), 0xFFFFFFFF, 0xFFFFFFFF, b"", b"")
        assert decode_record(record) == expected_record, (row, record)
    assert not remaining, remaining

    partial = directory / "partial-record"
    short_write = subprocess.run(
        ["bash", "-c", 'ulimit -f 1; exec "$1" 3>"$2"', "short-record",
         directory / "max-record.record", partial],
        capture_output=True,
        timeout=5,
    )
    assert short_write.returncode == 76 and short_write.stdout == short_write.stderr == b"", short_write
    assert 0 < partial.stat().st_size < 1136
    return len(vectors)


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
        source.write_text("int main() { return 42; }\n", encoding="ascii")
        subprocess.run(command + ["--direct-record"], env=env, check=True, timeout=60)
        status, record = run_case(executable, sink)
        assert status == 0 and decode_record(record) == (0, 0, 42, 2, 0xFFFFFFFF, 0xFFFFFFFF, b"", b"")
        for redirection in ('3>&-', '3>/dev/full'):
            broken = subprocess.run(
                ["bash", "-c", 'exec "$1" ' + redirection, "direct-record", executable],
                capture_output=True,
                timeout=5,
            )
            assert broken.returncode == 76 and broken.stdout == broken.stderr == b"", broken
        vector_count = compare_ccam_vectors(capstan, root)
        assert not list(root.glob("program.*"))  # A failed compilation did not leave a staging file.
    print(f"{len(cases)} direct execution cases and {vector_count} same-CCAM reference vectors passed")


if __name__ == "__main__":
    main(str(Path(sys.argv[1]).resolve()))
