"""Run the CLI's direct ELF products on the Linux x86-64 kernel."""

import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


def valid_direct_image(image):
    """Strict current direct ET_EXEC profile, not an instruction safety proof."""
    if not 177 <= len(image) <= 1048576 + 176:
        return False
    ident, kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = struct.unpack_from("<16sHHIQQQIHHHHHH", image)
    if ident != b"\x7fELF\x02\x01\x01" + bytes(9):
        return False
    if (kind, machine, version, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr) != (2, 62, 1, 64, 0, 0, 64, 56, 2, 0, 0, 0):
        return False
    if not 0x4000B0 <= entry < 0x400000 + len(image):
        return False
    if struct.unpack_from("<IIQQQQQQ", image, 64) != (1, 5, 0, 0x400000, 0x400000, len(image), len(image), 4096):
        return False
    return struct.unpack_from("<IIQQQQQQ", image, 120) == (0x6474E551, 6, 0, 0, 0, 0, 0, 16)


def check_image_mutations(image):
    assert valid_direct_image(image)
    for offset in (0, 4, 5, 16, 18, 20, 32, 40, 48, 52, 54, 56, 58, 60, 62, 64, 68, 72, 80, 88, 96, 104, 112, 120, 124, 128, 136, 144, 152, 160, 168):
        mutated = bytearray(image)
        mutated[offset] ^= 1
        assert not valid_direct_image(mutated), offset
    for entry in (0x400000, 0x4000AF, 0x400000 + len(image), (1 << 64) - 1):
        mutated = bytearray(image)
        struct.pack_into("<Q", mutated, 24, entry)
        assert not valid_direct_image(mutated), entry
    assert not valid_direct_image(image[:175])
    assert not valid_direct_image(image[:-1])
    assert not valid_direct_image(image + b"\0")


def run_case(executable, sink):
    assert valid_direct_image(executable.read_bytes()), executable
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


def decode_record(record, status=0):
    """Validate the experimental single-function record, not a production ABI."""
    if status != 0 or not RESULT_HEADER.size <= len(record) <= 1136:
        raise ValueError("invalid termination or record size")
    magic, version, kind, code, value, steps, function, pc, name_len, detail_len = (
        RESULT_HEADER.unpack_from(record)
    )
    if (magic != b"CCAMRES\0" or version != 1 or name_len > 1024
            or detail_len > 64 or len(record) != RESULT_HEADER.size + name_len + detail_len):
        raise ValueError("invalid record framing")
    name_end = RESULT_HEADER.size + name_len
    name = record[RESULT_HEADER.size:name_end]
    detail = record[name_end:]
    if kind == 0:
        if (code, function, pc, name_len, detail_len) != (0, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0):
            raise ValueError("invalid return fields")
    elif kind == 2:
        if (code not in RECORD_TRAPS.values() or value != 0 or function != 0
                or pc >= 252 or not name or (code != 8 and detail)):
            raise ValueError("invalid trap fields")
    else:
        raise ValueError("unsupported outcome kind")
    return kind, code, value, steps, function, pc, name, detail


def check_record_mutations():
    good = RESULT_HEADER.pack(b"CCAMRES\0", 1, 0, 0, 42, 2,
                              0xFFFFFFFF, 0xFFFFFFFF, 0, 0)
    assert decode_record(good)[2] == 42

    def reject(record, status=0):
        try:
            decode_record(record, status)
        except ValueError:
            return
        raise AssertionError("accepted invalid terminal record")

    for offset in (0, 8, 10, 12, 32, 36, 40, 44):
        mutated = bytearray(good)
        mutated[offset] ^= 1
        reject(mutated)
    for length in range(len(good)):
        reject(good[:length])
    reject(good + b"\0")
    reject(bytes(1137))
    for status in (76, 77, -9, -11):
        reject(good, status)
    trap = RESULT_HEADER.pack(b"CCAMRES\0", 1, 2, 8, 0, 1, 0, 0, 4, 1) + b"mainx"
    assert decode_record(trap)[-2:] == (b"main", b"x")
    for offset in (12, 16, 32):
        mutated = bytearray(trap)
        mutated[offset] ^= 1
        reject(mutated)
    mutated = bytearray(trap)
    struct.pack_into("<I", mutated, 36, 252)
    reject(mutated)
    mutated = bytearray(trap)
    struct.pack_into("<I", mutated, 12, 1)
    reject(mutated)  # non-explicit trap cannot carry detail
    reject(trap[:-1])


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
        assert decode_record(record, status) == expected_record, (row, record)
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
    check_record_mutations()
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
            "bool t = true; bool f = false; "
            "if (t == t && f == f && !(t == f) && !(f == t) "
            "&& t != f && f != t && !(t != t) && !(f != f)) { return 42; } "
            "return 0;",
            0,
            42,
        ),
        ("int divisor = 0; if (false == (7 / divisor == 0)) { return 1; } return 0;", 71, None),
        (
            "int sum = 0; "
            "if (sum == 0) { int value = 10; value += 2; sum = value; } "
            "else { bool value = sum < 0; if (value) { sum = 100; } } "
            "for (int value = 0; value < 3; value++) { sum += value; } "
            "int value = 27; return sum + value;",
            0,
            42,
        ),
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
        check_image_mutations(image)
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
