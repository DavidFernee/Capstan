"""Exercise the opt-in aggregate CLI; explicitly probe the complete production compiler.

The driver is C-hosted. This test is not S1 evidence.
"""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

SOURCE_FILES = (
    "compiler/ast.cap", "compiler/lexer.cap", "compiler/parser.cap",
    "compiler/checker.cap", "compiler/ranges.cap", "compiler/codegen.cap",
    "compiler/main.cap",
)

def run(root, cli, output, *files):
    return subprocess.run(
        [str(cli), "native", "--direct", "--direct-aggregate",
         "--root", str(root), "-o", str(output), *files],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300,
    )

def main():
    repo = Path(sys.argv[1]).resolve()
    cli = repo / "bin/capstan"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "fixture.cap"
        helper = root / "helper.cap"
        out = root / "program"
        helper.write_text("struct Item { int value; }\nint get(Item x) { return x.value; }\n")
        source.write_text('import "helper.cap";\nint main() { Item x = new Item{value: 42}; return get(x); }\n')
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode == 0, p.stdout.decode(errors="replace")
        raw = out.read_bytes()
        assert raw.startswith(b"\x7fELF") and os.access(out, os.X_OK)
        q = subprocess.run([str(out)], capture_output=True, timeout=5)
        assert (q.returncode, q.stdout, q.stderr) == (0, struct.pack("<q",42), b"")
        original = raw
        source.write_text("int main() { return true; }\n")
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode != 0 and out.read_bytes() == original, p.stdout
        source.write_text("int main() { return 1; }\n")
        p = run(root, cli, out, "../fixture.cap")
        assert p.returncode != 0 and out.read_bytes() == original, p.stdout

        # The complete checked compiler is the actual target. Do not prune
        # declarations, rename functions, or substitute a synthetic subset.
        probe = root / "compiler-probe"
        p = run(repo, cli, probe, *SOURCE_FILES)
        print(p.stdout.decode(errors="replace"))
        if p.returncode != 0:
            assert not probe.exists(), "rejection must not publish executable"
            assert b"candidate aggregate backend rejected complete checked module" in p.stdout, p.stdout
            print("Complete compiler candidate admission: BLOCKED (see diagnostic above)")
        else:
            # A produced ELF is still not acceptance: verify actual compiler CLI.
            q = subprocess.run([str(probe), "--version"], capture_output=True, timeout=5)
            assert q.returncode == 0 and q.stdout.startswith(b"Capstan "), (q.returncode, q.stdout, q.stderr)
            print("Complete compiler candidate emitted and version executed; C-hosted driver is NOT S1")
    print("Aggregate native CLI fixture and fail-closed workspace checks passed")

if __name__ == "__main__":
    main()
