#!/usr/bin/env python3
"""Integration tests for source-file-private struct fields."""
import pathlib
import subprocess
import sys
import tempfile

capstan, cc, root = sys.argv[1:4]
fixture = pathlib.Path(root) / "tests" / "unit" / "private_fields"

def run(args):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

with tempfile.TemporaryDirectory(prefix="capstan-private-fields-") as td:
    generated = pathlib.Path(td) / "program.c"
    binary = pathlib.Path(td) / "program"

    accepted = run([capstan, "build", "-o", str(generated), str(fixture / "accept.cap")])
    if accepted.returncode != 0:
        raise SystemExit("private-field factory program did not compile:\n" + accepted.stdout)

    compiled = run([cc, "-O2", "-std=gnu11", "-w", "-I" + str(pathlib.Path(root) / "runtime"),
                    str(generated), "-o", str(binary)])
    if compiled.returncode != 0:
        raise SystemExit("generated private-field test C did not compile:\n" + compiled.stdout)

    executed = run([str(binary)])
    if executed.returncode != 0 or executed.stdout != "7\nvalid\n":
        raise SystemExit("private-field factory program behaved incorrectly: "
                         f"exit={executed.returncode}, output={executed.stdout!r}")

    expected = {
        "read.cap": "private field 'secret' of Vault is accessible only within its defining module",
        "write.cap": "private field 'secret' of Vault is accessible only within its defining module",
        "construct.cap": "private field 'secret' of Vault may be initialised only within its defining module",
        "omit.cap": "field 'secret' of Vault is not initialised",
        "private_method.cap": "private currently applies only to struct fields, not methods",
    }
    for name, diagnostic in expected.items():
        rejected = run([capstan, "build", "-o", str(generated), str(fixture / name)])
        if rejected.returncode != 1 or diagnostic not in rejected.stdout:
            raise SystemExit(f"{name} was not rejected as specified "
                             f"(exit={rejected.returncode}):\n{rejected.stdout}")

print("private fields: factory access, external read/write/construction rejection, and syntax guard")
