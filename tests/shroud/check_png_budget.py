#!/usr/bin/env python3
"""Standalone end-to-end regression for Shroud's bounded PNG encoder.

Usage:
    python3 tests/shroud/check_png_budget.py CAPSTANC CC [CFLAGS...]

Builds the Capstan regression program, asks it to write a near-limit PNG, and
independently validates the complete PNG/zlib structure and decoded pixels.
"""
import os
import struct
import subprocess
import sys
import tempfile
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = sorted(
    os.path.join("lib/shroud", name)
    for name in os.listdir(os.path.join(ROOT, "lib/shroud"))
    if name.endswith(".cap")
)


def fail(message):
    raise SystemExit("png budget: " + message)


def run(argv, *, check=True):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)
    if check and result.returncode != 0:
        fail(f"command {argv[0]!r} exited {result.returncode}:\n{result.stdout}{result.stderr}")
    return result


def parse_png(path):
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        fail("invalid PNG signature")
    pos = 8
    chunks = []
    while pos < len(data):
        if len(data) - pos < 12:
            fail("truncated chunk header or trailer")
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        end = pos + 12 + length
        if end > len(data):
            fail(f"truncated {kind!r} chunk")
        body = data[pos + 8:pos + 8 + length]
        crc, = struct.unpack(">I", data[pos + 8 + length:end])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            fail(f"bad CRC in {kind!r}")
        chunks.append((kind, body))
        pos = end
        if kind == b"IEND":
            break
    if pos != len(data):
        fail("trailing bytes after IEND")
    if not chunks or chunks[0][0] != b"IHDR" or chunks[-1] != (b"IEND", b""):
        fail("invalid chunk order or missing IEND")
    if sum(1 for kind, _ in chunks if kind == b"IHDR") != 1:
        fail("expected exactly one IHDR")
    if sum(1 for kind, _ in chunks if kind == b"IEND") != 1:
        fail("expected exactly one IEND")
    idat_positions = [i for i, (kind, _) in enumerate(chunks) if kind == b"IDAT"]
    if not idat_positions:
        fail("missing IDAT")
    if idat_positions != list(range(idat_positions[0], idat_positions[-1] + 1)):
        fail("IDAT chunks are not consecutive")
    ihdr = chunks[0][1]
    if len(ihdr) != 13:
        fail("invalid IHDR length")
    width, height, depth, colour, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if (depth, colour, compression, filtering, interlace) != (8, 6, 0, 0, 0):
        fail("unexpected PNG format; expected non-interlaced 8-bit RGBA")
    idat = b"".join(body for kind, body in chunks if kind == b"IDAT")
    return width, height, idat


def check_stored_deflate(idat, expected_raw_length):
    if len(idat) < 6 or idat[:2] != b"\x78\x01":
        fail("unexpected zlib header")
    deflate = idat[2:-4]
    pos = 0
    total = 0
    blocks = 0
    saw_final = False
    while not saw_final:
        if pos + 5 > len(deflate):
            fail("truncated stored DEFLATE block")
        header = deflate[pos]
        final = header & 1
        block_type = (header >> 1) & 3
        if block_type != 0 or (header & 0xF8) != 0:
            fail("expected byte-aligned stored DEFLATE block")
        length, inverse = struct.unpack("<HH", deflate[pos + 1:pos + 5])
        if (length ^ inverse) != 0xFFFF:
            fail("stored DEFLATE LEN/NLEN mismatch")
        pos += 5
        if pos + length > len(deflate):
            fail("stored DEFLATE block exceeds IDAT")
        pos += length
        total += length
        blocks += 1
        saw_final = bool(final)
    if pos != len(deflate):
        fail("trailing data after final DEFLATE block")
    if total != expected_raw_length:
        fail(f"stored blocks contain {total} bytes, expected {expected_raw_length}")
    if blocks < 2:
        fail("regression did not exercise multiple DEFLATE blocks")
    return blocks


def main():
    if len(sys.argv) < 3:
        fail(__doc__)
    capstanc = os.path.abspath(sys.argv[1]) if os.path.exists(sys.argv[1]) else sys.argv[1]
    cc = sys.argv[2]
    cflags = sys.argv[3:]
    if not any(flag.startswith("-O") for flag in cflags):
        cflags = ["-O2"] + cflags

    with tempfile.TemporaryDirectory() as tmp:
        c_source = os.path.join(tmp, "png_budget.c")
        exe = os.path.join(tmp, "png_budget")
        accepted = os.path.join(tmp, "accepted.png")
        rejected = os.path.join(tmp, "must_not_exist.png")
        binary = os.path.join(tmp, "all_bytes.bin")
        run([capstanc, "build", "--strict", "-o", c_source] + LIB +
            ["tests/shroud/png_budget.cap"])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), c_source, "-o", exe])
        result = run([exe, accepted, rejected, binary])
        if "png budget: 20 assertions" not in result.stdout:
            fail(f"regression program did not report its assertions: {result.stdout!r}")
        if not os.path.isfile(accepted):
            fail("accepted PNG was not written")
        if os.path.exists(rejected):
            fail("over-budget png_write created an output file")
        if open(binary, "rb").read() != bytes(range(256)):
            fail("byte-to-string conversion did not preserve all 256 byte values")

        width, height, idat = parse_png(accepted)
        if (width, height) != (128, 128):
            fail(f"unexpected dimensions {width}x{height}")
        expected_length = (1 + 4 * width) * height
        blocks = check_stored_deflate(idat, expected_length)
        try:
            raw = zlib.decompress(idat)
        except zlib.error as error:
            fail(f"independent zlib decoder rejected IDAT: {error}")
        if len(raw) != expected_length:
            fail(f"decoded {len(raw)} bytes, expected {expected_length}")
        expected_row = b"\x00" + bytes((0x33, 0x66, 0x99, 0xFF)) * width
        for y in range(height):
            row = raw[y * len(expected_row):(y + 1) * len(expected_row)]
            if row != expected_row:
                fail(f"decoded pixels differ on row {y}")
        print(f"png budget: 20 Capstan assertions; {width}x{height} RGBA; "
              f"{blocks} stored DEFLATE blocks; CRC, zlib, Adler and every pixel verified; "
              "over-budget write produced no file")


if __name__ == "__main__":
    main()
