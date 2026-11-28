"""Independent headless Anchor A0 rendering and accessibility smoke check."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[2]
SHROUD = ("geom", "color", "path", "raster", "png", "ttf", "text",
          "theme", "view", "layout", "paint", "a11y", "ui")


def png_check(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    chunks = []
    while pos < len(data):
        assert pos + 12 <= len(data)
        length, kind = struct.unpack_from(">I4s", data, pos)
        end = pos + 12 + length
        assert end <= len(data)
        body = data[pos + 8:end - 4]
        crc = struct.unpack_from(">I", data, end - 4)[0]
        assert zlib.crc32(kind + body) == crc
        chunks.append((kind, body))
        pos = end
    assert chunks[0][0] == b"IHDR" and chunks[-1] == (b"IEND", b"")
    assert struct.unpack_from(">II", chunks[0][1]) == (1100, 720)
    pixels = zlib.decompress(b"".join(body for kind, body in chunks if kind == b"IDAT"))
    assert pixels
    return hashlib.sha256(data).hexdigest()


def names(node):
    yield node["name"]
    for child in node.get("children", []):
        yield from names(child)


def main():
    with tempfile.TemporaryDirectory(prefix="anchor-assurance-") as tmp:
        directory = Path(tmp)
        executable = directory / "anchor"
        subprocess.run([ROOT / "bin/capstan", "build",
                        *(ROOT / f"lib/shroud/{name}.cap" for name in SHROUD),
                        ROOT / "examples/anchor/main.cap", "-o", executable],
                       cwd=ROOT, check=True, timeout=180)
        snapshots = []
        for n in range(2):
            out = directory / str(n)
            out.mkdir()
            subprocess.run([executable, out], cwd=ROOT, check=True, timeout=60)
            light = png_check(out / "anchor.png")
            dark = png_check(out / "anchor-dark.png")
            assert light != dark
            raw = (out / "anchor-a11y.json").read_bytes()
            labels = set(names(json.loads(raw)))
            assert "ANCHOR" in labels
            assert "No assurance verdict available" in labels
            assert "No live compiler connection in A0." in labels
            snapshots.append((light, dark, hashlib.sha256(raw).hexdigest()))
        assert snapshots[0] == snapshots[1], "nondeterministic headless rendering"
        print("Anchor A0: deterministic light/dark PNG and accessibility disclaimer verified")


if __name__ == "__main__":
    main()
