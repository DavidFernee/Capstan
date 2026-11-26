#!/usr/bin/env python3
"""Adversarial input-boundary tests for native and stage-0 execution.

Covers exact and one-over argv count, per-argument bytes, aggregate bytes,
environment bytes and line payload bytes. Both engines must agree.
"""
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


def run(command, argv, secret, stdin):
    env = os.environ.copy()
    env["CAPSTAN_BOUND_INPUT_SECRET"] = secret
    return subprocess.run(
        [*command, *argv], input=stdin, capture_output=True,
        timeout=30, env=env,
    )


def check_engine(label, command):
    exact = run(command, ["abcd", "xy"], "abcd", b"abc")
    if exact.returncode != 0 or exact.stdout != b"3\\n2\\n":
        raise AssertionError(
            f"{label}: exact limits failed: exit={exact.returncode}, "
            f"out={exact.stdout!r}, err={exact.stderr!r}"
        )

    cases = [
        ("argument count", ["a", "b", "c"], "abcd", b"x"),
        ("per-argument bytes", ["abcde"], "abcd", b"x"),
        ("aggregate argument bytes", ["abcd", "xyz"], "abcd", b"x"),
        ("environment bytes", ["a"], "abcde", b"x"),
        ("line bytes", ["a"], "abcd", b"abcd\\n"),
    ]
    for name, argv, secret, stdin in cases:
        result = run(command, argv, secret, stdin)
        if result.returncode != 101 or b"CWE-789" not in result.stderr:
            raise AssertionError(
                f"{label}: {name} was not rejected with CWE-789: "
                f"exit={result.returncode}, out={result.stdout!r}, "
                f"err={result.stderr!r}"
            )


def main():
    capstanc, cc, *flags = sys.argv[1:]
    root = Path(tempfile.mkdtemp(prefix="capstan-input-bounds-"))
    try:
        source = root / "input_bounds.cap"
        generated = root / "input_bounds.c"
        executable = root / "input_bounds"
        stage0 = root / "input_bounds.py"
        source.write_text(PROGRAM, encoding="utf-8")

        subprocess.run(
            [capstanc, "build", "--strict", "-o", str(generated), str(source)],
            check=True, stdout=subprocess.DEVNULL,
        )
        subprocess.run([cc, *flags, str(generated), "-o", str(executable)], check=True)

        bootstrap = Path(capstanc).resolve().parents[1] / "bootstrap/capstan0.py"
        subprocess.run(
            [sys.executable, "-I", str(bootstrap), str(stage0), str(source)],
            check=True,
        )

        check_engine("native", [str(executable)])
        check_engine("stage 0", [sys.executable, "-I", str(stage0)])
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)

    print(
        "explicit input bounds: exact limits accepted; count, per-argument, "
        "aggregate, line and secret overflows rejected natively and under stage 0"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
