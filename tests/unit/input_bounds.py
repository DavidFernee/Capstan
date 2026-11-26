#!/usr/bin/env python3
"""Mandatory input-bound contracts, checked natively and under stage 0.

Covers exact argument count/per-value/aggregate limits, one-over rejection,
line payload bounds, and bounded secret environment reads.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROGRAM = """int main() {
    List<string> values = args(2, 4, 6);
    if (let line = read_line(4)) { println(int_to_str(line.len())); }
    else { println("none"); }
    if (let secret = secret_env("CAPSTAN_BOUNDED_SECRET", 4)) { println("secret"); }
    else { println("no secret"); }
    println(int_to_str(values.len()));
    return 0;
}
"""
WANT = b"4\nsecret\n2\n"


def run_case(command, data, env, accepted, label):
    try:
        result = subprocess.run(command, input=data, capture_output=True, env=env, timeout=30)
    except subprocess.TimeoutExpired:
        raise AssertionError(f"{label}: process hung")
    if accepted:
        if result.returncode != 0 or result.stdout != WANT:
            raise AssertionError(f"{label}: exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}")
    elif result.returncode != 101 or b"CWE-789" not in result.stderr:
        raise AssertionError(f"{label}: expected bounded-input trap, exit={result.returncode}, stderr={result.stderr!r}")


def main():
    capstanc, cc, *flags = sys.argv[1:]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "input_bounds.cap"
        generated = root / "input_bounds.c"
        executable = root / "input_bounds"
        stage0 = root / "input_bounds.py"
        source.write_text(PROGRAM, encoding="utf-8")
        subprocess.run([capstanc, "build", "-o", str(generated), str(source)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([cc, *flags, str(generated), "-o", str(executable)], check=True)
        subprocess.run([sys.executable, "-I", str(Path(capstanc).resolve().parents[1] / "bootstrap/capstan0.py"), str(stage0), str(source)], check=True)
        env = os.environ.copy()
        env["CAPSTAN_BOUNDED_SECRET"] = "ABCD"
        engines = [("native", [str(executable)]), ("stage 0", [sys.executable, "-I", str(stage0)])]
        cases = [
            ("exact all bounds", ["ABCD", "XY"], b"1234\n", "ABCD", True),
            ("argument count +1", ["A", "B", "C"], b"1234\n", "ABCD", False),
            ("per-argument bytes +1", ["12345"], b"1234\n", "ABCD", False),
            ("aggregate argument bytes +1", ["ABCD", "XYZ"], b"1234\n", "ABCD", False),
            ("line bytes +1", [], b"12345\n", "ABCD", False),
            ("secret bytes +1", [], b"1234\n", "ABCDE", False),
        ]
        for engine, base in engines:
            for label, argv, stdin, secret, accepted in cases:
                case_env = env.copy()
                case_env["CAPSTAN_BOUNDED_SECRET"] = secret
                run_case(base + argv, stdin, case_env, accepted, f"{engine}: {label}")
    print("explicit input bounds: exact limits accepted; count, per-value, aggregate, line and secret overflows rejected natively and under stage 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
