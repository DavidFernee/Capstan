#!/usr/bin/env python3
"""The read_line() maximum payload is accepted when EOF follows without a newline.

    read_line_eof.py CAPSTANC CC [CFLAGS...]

The runtime unit suite covers the exact limit with a newline and max+1 rejection.
This public-API test covers the distinct exact-limit-at-EOF boundary.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

MAX = 1 << 20
PROGRAM = """int main() {
    if (let line = read_line()) {
        println(int_to_str(line.len()));
    } else {
        println("none");
    }
    return 0;
}
"""


def main():
    capstanc, cc, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        source = root / "read_line_eof.cap"
        generated = root / "read_line_eof.c"
        executable = root / "read_line_eof"
        source.write_text(PROGRAM, encoding="utf-8")
        subprocess.run(
            [capstanc, "build", "-o", str(generated), str(source)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run([cc, *flags, str(generated), "-o", str(executable)], check=True)
        try:
            result = subprocess.run(
                [str(executable)],
                input=b"Q" * MAX,
                capture_output=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            print("FAIL read_line() hung at the exact payload limit")
            return 1
        if result.returncode != 0 or result.stdout != b"1048576\n":
            print(
                "FAIL exact-limit EOF boundary: "
                f"exit={result.returncode}, stdout={result.stdout!r}, "
                f"stderr={result.stderr.decode(errors='replace')}"
            )
            return 1
    print("read_line accepts exactly 1 MiB followed immediately by EOF")
    return 0


if __name__ == "__main__":
    sys.exit(main())
