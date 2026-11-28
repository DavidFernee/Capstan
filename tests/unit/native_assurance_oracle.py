"""Independent native/CCAM arithmetic oracle; requires Linux x86-64."""
import itertools
import subprocess
import sys
import tempfile
from pathlib import Path

from native_direct_elf import decode_record, run_case, RECORD_TRAPS

MIN = -(1 << 63)
MAX = (1 << 63) - 1
VALUES = (MIN, -3, -1, 0, 1, 3, MAX)


def outcome(op, a, b, fuel):
    # Fuel precedes dispatch; arithmetic traps consume the third step.
    if fuel < 3:
        return "step_limit_exceeded", 0, fuel, fuel
    if op in (6, 7) and b == 0:
        return "division_by_zero", 0, 3, 2
    if op == 3:
        value = a + b
    elif op == 4:
        value = a - b
    elif op == 5:
        value = a * b
    else:
        quotient = abs(a) // abs(b)
        if (a < 0) != (b < 0):
            quotient = -quotient
        value = quotient if op == 6 else a - quotient * b
    if not MIN <= value <= MAX:
        return "integer_overflow", 0, 3, 2
    if fuel == 3:
        return "step_limit_exceeded", 0, 3, 3
    return "", value, 4, 0


def main():
    root = Path(__file__).resolve().parents[2]
    capstan = root / "bin/capstan"
    with tempfile.TemporaryDirectory(prefix="native-assurance-") as tmp:
        directory = Path(tmp)
        generator = directory / "generate"
        subprocess.run([capstan, "build", "--strict",
                        root / "verification/ccam_direct_elf.cap",
                        root / "tests/unit/native_assurance_vectors.cap",
                        "-o", generator], check=True, timeout=120)
        manifest = subprocess.run([generator, directory], check=True,
                                  capture_output=True, text=True, timeout=180)
        rows = manifest.stdout.splitlines()
        cases = list(itertools.product(range(3, 8), VALUES, VALUES, range(5)))
        if len(rows) != len(cases):
            raise AssertionError(("incomplete manifest", len(rows), len(cases)))
        for i, (row, case) in enumerate(zip(rows, cases)):
            ident, trap, value, steps, function, pc, detail = row.split("\t")
            expected_trap, expected_value, expected_steps, expected_pc = outcome(*case)
            assert int(ident) == i, row
            assert (trap, int(value), int(steps), detail) == (
                expected_trap, expected_value, expected_steps, ""), (case, row)
            if trap:
                assert function == "main" and int(pc) == expected_pc, (case, row)
                expected_record = (2, RECORD_TRAPS[trap], 0, expected_steps,
                                   0, expected_pc, b"main", b"")
            else:
                expected_record = (0, 0, expected_value, expected_steps,
                                   0xFFFFFFFF, 0xFFFFFFFF, b"", b"")
            image = directory / f"case-{i}"
            image.chmod(0o700)
            status, record = run_case(image, directory / "result")
            assert decode_record(record, status) == expected_record, (case, row, record)
        assert len(list(directory.glob("case-*"))) == len(cases)
        print(f"native/evaluator/independent arithmetic oracle: {len(cases)} cases")


if __name__ == "__main__":
    if not sys.platform.startswith("linux"):
        raise SystemExit("Linux x86-64 required")
    import platform
    if platform.machine() != "x86_64":
        raise SystemExit("Linux x86-64 required")
    main()
