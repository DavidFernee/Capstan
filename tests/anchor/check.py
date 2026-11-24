#!/usr/bin/env python3
"""Build and smoke-test Anchor's headless Shroud S0 prototype.

Run after `make bootstrap`:
    python3 tests/anchor/check.py
"""
import json
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPILER = ROOT / "build" / "capstanc"
SHROUD = [
    "lib/shroud/geom.cap", "lib/shroud/color.cap", "lib/shroud/path.cap",
    "lib/shroud/raster.cap", "lib/shroud/png.cap", "lib/shroud/ttf.cap",
    "lib/shroud/text.cap", "lib/shroud/theme.cap", "lib/shroud/view.cap",
    "lib/shroud/layout.cap", "lib/shroud/paint.cap", "lib/shroud/a11y.cap",
    "lib/shroud/ui.cap", "examples/anchor/main.cap",
]


def run(argv, *, cwd=ROOT):
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=True)


def main():
    if not COMPILER.is_file():
        raise SystemExit("build the compiler first: make bootstrap")
    with tempfile.TemporaryDirectory(prefix="capstan-anchor-") as tmp:
        c_file = os.path.join(tmp, "anchor.c")
        exe = os.path.join(tmp, "anchor")
        run([str(COMPILER), "build", "-o", c_file, *SHROUD])
        run([os.environ.get("CC", "cc"), "-O2", "-std=gnu11",
             f"-I{ROOT / 'runtime'}", c_file, "-o", exe])
        rendered = run([exe, tmp])
        if "accessibility:" in rendered.stdout:
            raise AssertionError("Shroud reported accessibility problems: " + rendered.stdout)
        png = pathlib.Path(tmp, "anchor.png").read_bytes()
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise AssertionError("Anchor did not produce a PNG")
        if png[16:24] != (1100).to_bytes(4, "big") + (720).to_bytes(4, "big"):
            raise AssertionError("unexpected Anchor frame dimensions")
        tree = json.loads(pathlib.Path(tmp, "anchor-a11y.json").read_text())
        if not isinstance(tree, dict):
            raise AssertionError("accessibility tree is not a JSON object")
        print("Anchor A0: build, render and accessibility smoke test passed")


if __name__ == "__main__":
    main()
