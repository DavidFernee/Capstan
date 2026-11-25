#!/usr/bin/env python3
"""Shroud per-value UTF-8 byte-limit boundary and fail-closed regressions.

Usage: python3 tests/shroud/check_text_byte_limit.py CAPSTANC CC [CFLAGS...]
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = sorted(
    os.path.join("lib/shroud", name)
    for name in os.listdir(os.path.join(ROOT, "lib/shroud"))
    if name.endswith(".cap")
)


def run(argv, *, expected=0):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != expected:
        raise SystemExit(
            f"text byte limit: {argv[0]!r} exited {result.returncode}, expected {expected}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    capstanc = os.path.abspath(sys.argv[1]) if os.path.exists(sys.argv[1]) else sys.argv[1]
    cc = sys.argv[2]
    cflags = sys.argv[3:]
    if not any(flag.startswith("-O") for flag in cflags):
        cflags = ["-O2"] + cflags

    repeat = """
string repeat_ascii(int n) {
    List<string> parts = new List<string>();
    for (int i = 0; i < n; i += 1) { parts.push("x"); }
    return join(parts, "");
}
"""
    exact = repeat + """
int main() {
    string s = repeat_ascii(MAX_TEXT_BYTES);
    if (string_bytes(s).len() != MAX_TEXT_BYTES) { return 1; }
    Tainted t = taint(s);
    if (tainted_bytes(t).len() != MAX_TEXT_BYTES) { return 2; }
    println("text byte limit: exact boundary accepted for trusted and Tainted input");
    return 0;
}
"""
    rejected = {
        "trusted": repeat + """
int main() {
    string s = repeat_ascii(MAX_TEXT_BYTES + 1);
    string_bytes(s);
    println("unexpectedly accepted oversized trusted text");
    return 1;
}
""",
        "tainted": repeat + """
int main() {
    Tainted s = taint(repeat_ascii(MAX_TEXT_BYTES + 1));
    tainted_bytes(s);
    println("unexpectedly accepted oversized untrusted text");
    return 1;
}
""",
    }

    with tempfile.TemporaryDirectory() as tmp:
        def build(source, name):
            cap = os.path.join(tmp, name + ".cap")
            c_source = os.path.join(tmp, name + ".c")
            exe = os.path.join(tmp, name)
            with open(cap, "w", encoding="utf-8") as stream:
                stream.write(source)
            run([capstanc, "build", "--strict", "-o", c_source] + LIB + [cap])
            run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), c_source, "-o", exe])
            return exe

        exe = build(exact, "text-byte-limit-exact")
        result = run([exe])
        if "exact boundary accepted" not in result.stdout:
            raise SystemExit(f"text byte limit: missing exact-boundary confirmation: {result.stdout!r}")

        for name, source in rejected.items():
            exe = build(source, "text-byte-limit-" + name)
            result = run([exe], expected=101)
            expected = (
                "shroud: text byte limit exceeded"
                if name == "trusted"
                else "shroud: untrusted text byte limit exceeded"
            )
            if expected not in result.stdout:
                raise SystemExit(f"text byte limit: {name} rejection diagnostic missing: {result.stdout!r}")

    print("text byte limit: exact boundary accepted; limit+1 rejected for trusted and Tainted input")


if __name__ == "__main__":
    main()
