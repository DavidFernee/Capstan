#!/usr/bin/env python3
"""Adversarial boundary tests for explicit argv, environment and line bounds."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROGRAM = """int main() {
    List<string> argv = args(2, 4, 6);
    if (let secret = secret_env("CAPSTAN_BOUND_INPUT_SECRET", 4)) {
        if (!secret_eq(secret, "abcd")) { return 11; }
    } else { return 12; }
    if (let line = read_line(3)) {
        println(int_to_str(line.len()));
    } else {
        println("none");
    }
    println(int_to_str(argv.len()));
    return 0;
}
"""


def run(executable, argv, secret, stdin):
    env = os.environ.copy()
    env["CAPSTAN_BOUND_INPUT_SECRET"] = secret
    return subprocess.run(
        [str(executable), *argv], input=stdin, capture_output=True,
        timeout=30, env=env,
    )


def main():
    capstanc, cc, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
    with tempfile.TemporaryDirectory(prefix="capstan-input-bounds-") as d:
        root = Path(d)
        source, generated, executable = (
            root / "input_bounds.cap", root / "input_bounds.c", root / "input_bounds"
        )
        source.write_text(PROGRAM, encoding="utf-8")
        subprocess.run(
            [capstanc, "build", "--strict", "-o", str(generated), str(source)],
            check=True, stdout=subprocess.DEVNULL,
        )
        subprocess.run([cc, *flags, str(generated), "-o", str(executable)], check=True)

        exact = run(executable, ["abcd", "xy"], "abcd", b"abc")
        if exact.returncode != 0 or exact.stdout != b"3\\n2\\n":
            raise SystemExit(f"exact bounds failed: exit={exact.returncode}, out={exact.stdout!r}, err={exact.stderr!r}")

        cases = [
            ("argument count", ["a", "b", "c"], "abcd", b"x"),
            ("per-argument bytes", ["abcde"], "abcd", b"x"),
            ("aggregate argument bytes", ["abcd", "xyz"], "abcd", b"x"),
            ("environment bytes", ["a"], "abcde", b"x"),
            ("line bytes", ["a"], "abcd", b"abcd\\n"),
        ]
        for label, argv, secret, stdin in cases:
            result = run(executable, argv, secret, stdin)
            if result.returncode == 0:
                raise SystemExit(f"{label} over-limit input was accepted")
    print("explicit input bounds: exact limits accepted; count, per-field and aggregate overflows rejected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
