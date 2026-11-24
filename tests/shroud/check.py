#!/usr/bin/env python3
"""Shroud, the Capstan GUI library, checked against independent references.

    check.py CAPSTANC CC [CFLAGS...]          run every check
    check.py CAPSTANC CC [CFLAGS...] --update-golden

Run from anywhere; paths are relative to the repository root.

1. behaviour   tests/shroud/behaviour.cap: layout, input, focus, editing, guards,
               accessibility, themes (its own assertions)
2. raster      random polygons filled by the rasteriser, against their exact area
               coverage of every pixel, computed here by polygon clipping
3. fonts       every mapped character of the bundled fonts: glyph index, advance and
               outline bounds against fontTools (recorded in fonts.expected, and
               recomputed whenever fontTools is installed)
4. utf-8       random and edge-case byte strings against Python's decoder
               (errors="replace" follows the same maximal-subpart rule)
5. png         the encoder's output decoded by zlib and compared pixel by pixel
6. font fuzz   damaged fonts (bit flips, truncation, hostile offsets and counts):
               each is refused or drawn, and the program never stops or crashes
7. golden      the example gallery renders to the recorded SHA-256 of every frame.
               Rendering is integer arithmetic only, so this holds on every platform.
"""
import hashlib, os, random, re, struct, subprocess, sys, tempfile, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = sorted(os.path.join("lib/shroud", f) for f in os.listdir(os.path.join(ROOT, "lib/shroud")) if f.endswith(".cap"))
FONTS = ["lib/shroud/fonts/DejaVuSans-Latin.ttf", "lib/shroud/fonts/DejaVuSans-Bold-Latin.ttf"]
GOLDEN = os.path.join(ROOT, "tests/shroud/golden.txt")


def build(capstanc, cc, cflags, tmp, main, name):
    c = os.path.join(tmp, name + ".c")
    exe = os.path.join(tmp, name)
    r = subprocess.run([capstanc, "build", "--strict", "-o", c] + LIB + [main], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"{name}: does not compile:\n{r.stdout}{r.stderr}")
    r = subprocess.run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), c, "-o", exe], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"{name}: C compiler failed:\n{r.stderr}")
    return exe


def run(exe, *args, check=True):
    r = subprocess.run([exe] + list(args), cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"{os.path.basename(exe)} {' '.join(args[:1])}: exit {r.returncode}\n{r.stdout}{r.stderr}")
    return r


# ---- exact coverage ------------------------------------------------------------------

def clip(poly, x0, y0, x1, y1):
    """Sutherland-Hodgman clipping of a (possibly concave, simple) polygon to a box.
    The area of the result is the exact area of the intersection."""
    def side(pts, inside, cut):
        out = []
        for i, p in enumerate(pts):
            q = pts[i - 1]
            if inside(p):
                if not inside(q):
                    out.append(cut(q, p))
                out.append(p)
            elif inside(q):
                out.append(cut(q, p))
        return out

    def at_x(x):
        return lambda a, b: (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def at_y(y):
        return lambda a, b: (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)

    pts = poly
    for inside, cut in ((lambda p: p[0] >= x0, at_x(x0)), (lambda p: p[0] <= x1, at_x(x1)),
                        (lambda p: p[1] >= y0, at_y(y0)), (lambda p: p[1] <= y1, at_y(y1))):
        if not pts:
            return 0.0
        pts = side(pts, inside, cut)
    a = 0.0
    for i in range(len(pts)):
        a += pts[i - 1][0] * pts[i][1] - pts[i][0] * pts[i - 1][1]
    return abs(a) / 2


def star(rng):
    import math
    # One vertex in each of n equal sectors around the centre: no gap between
    # neighbours reaches half a turn, so the polygon is simple (it does not cross
    # itself) and its exact coverage is its clipped area.
    n = rng.randint(4, 14)
    cx, cy = rng.uniform(4, 28), rng.uniform(4, 28)
    angles = [2 * math.pi * (i + rng.uniform(0.05, 0.95)) / n for i in range(n)]
    pts = []
    for a in angles:
        r = rng.uniform(1, 20)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    # Snap to the rasteriser's 1/256-pixel grid, which is what it is given.
    return [(round(x * 256) / 256, round(y * 256) / 256) for x, y in pts]


def check_raster(exe, tmp):
    rng = random.Random(20261124)
    polys = [star(rng) for _ in range(150)]
    for _ in range(50):
        polys.append([(round(rng.uniform(-4, 36) * 256) / 256, round(rng.uniform(-4, 36) * 256) / 256) for _ in range(3)])
    polys.append([(0.5, 0.5), (31.5, 0.5), (31.5, 31.5), (0.5, 31.5)])
    polys.append([(10.25, 3.75), (11.0, 30.0), (10.75, 3.0)])         # a sliver
    path = os.path.join(tmp, "polys.txt")
    with open(path, "w") as f:
        for p in polys:
            f.write(f"{len(p)} " + " ".join(f"{round(x * 256)} {round(y * 256)}" for x, y in p) + "\n")
    lines = run(exe, "raster", path).stdout.split("\n")
    worst, total, count = 0, 0.0, 0
    for k, p in enumerate(polys):
        got = [int(v) for v in lines[k].split()]
        for y in range(32):
            for x in range(32):
                want = clip(p, x, y, x + 1, y + 1) * 255
                d = abs(got[y * 32 + x] - want)
                worst = max(worst, d)
                total += d
                count += 1
    mean = total / count
    # 16 sub-scanlines bound the vertical error by 1/32 of a pixel per edge.
    if worst > 17 or mean > 0.25:
        sys.exit(f"raster: coverage differs from the exact area: worst {worst:.1f}/255, mean {mean:.3f}")
    return f"{len(polys)} polygons, {count} pixels, worst {worst:.1f}/255, mean {mean:.3f}"


EXPECTED_FONTS = os.path.join(ROOT, "tests/shroud/fonts.expected")


def font_reference():
    """What fontTools says about every mapped character of the bundled fonts, in the
    form `vectors font` prints. Needs fontTools; the result is recorded in
    tests/shroud/fonts.expected so the suite runs without it."""
    from fontTools.ttLib import TTFont
    out = []
    for path in FONTS:
        f = TTFont(os.path.join(ROOT, path))
        glyf = f["glyf"]
        order = f.getGlyphOrder()
        cmap = f.getBestCmap()
        out.append(f"== {path}")
        out.append(f"font {f['head'].unitsPerEm} {f['hhea'].ascent} {f['hhea'].descent} {f['maxp'].numGlyphs}")
        for cp in sorted(cmap):
            gid = order.index(cmap[cp])
            if cp >= 0x10000 or gid == 0:
                continue
            coords, ends, _ = glyf[cmap[cp]].getCoordinates(glyf)
            # A contour of one point (an anchor) draws nothing, and Shroud drops it.
            keep, start = [], 0
            for e in ends:
                if e > start:
                    keep.extend(coords[start:e + 1])
                start = e + 1
            if keep:
                xs = [c[0] for c in keep]
                ys = [c[1] for c in keep]
                box = f"{min(xs)} {min(ys)} {max(xs)} {max(ys)}"
            else:
                box = "empty"
            out.append(f"{cp} {gid} {f['hmtx'][cmap[cp]][0]} true {box}")
    return "\n".join(out) + "\n"


def check_fonts(exe):
    got = []
    for path in FONTS:
        got.append(f"== {path}")
        got.extend(run(exe, "font", path).stdout.strip().split("\n"))
    got = "\n".join(got) + "\n"
    want = open(EXPECTED_FONTS).read()
    try:
        fresh = font_reference()
    except ImportError:
        fresh = None
    if fresh is not None and fresh != want:
        sys.exit("fonts: tests/shroud/fonts.expected is out of date with fontTools; regenerate it with --update-golden")
    if got != want:
        a, b = got.split("\n"), want.split("\n")
        for i in range(min(len(a), len(b))):
            if a[i] != b[i]:
                sys.exit(f"fonts: Shroud says [{a[i]}], fontTools says [{b[i]}]")
        sys.exit("fonts: a different number of characters")
    n = sum(1 for line in want.split("\n") if line and line[0].isdigit())
    how = "fontTools, run now" if fresh is not None else "fontTools, as recorded"
    return f"{n} characters in {len(FONTS)} fonts: glyphs, advances and outlines agree with {how}"


def check_utf8(exe, tmp):
    rng = random.Random(7)
    cases = [b"", b"plain", "héllo wörld €".encode(), "\U0001F600".encode(),
             b"\xc0\xaf", b"\xe0\x80\xaf", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"\xf8\x88\x80\x80\x80",
             b"\xe2\x82", b"\xe2\x82A", b"\xf0\x9f\x98", b"\x80\xbf", b"\xfe\xff", b"\xc2", b"A\xc3"]
    alphabet = [0x41, 0x7F, 0x80, 0xBF, 0xC0, 0xC2, 0xDF, 0xE0, 0xED, 0xEF, 0xF0, 0xF4, 0xF5, 0xFF, 0x9F, 0xA0, 0x8F, 0x90]
    for _ in range(3000):
        cases.append(bytes(rng.choice(alphabet) if rng.random() < 0.7 else rng.randrange(256) for _ in range(rng.randint(0, 12))))
    path = os.path.join(tmp, "utf8.txt")
    with open(path, "w") as f:
        for c in cases:
            f.write(c.hex() + "\n")
    lines = run(exe, "utf8", path).stdout.split("\n")
    for i, c in enumerate(cases):
        want = " ".join(str(ord(ch)) for ch in c.decode("utf-8", errors="replace"))
        if lines[i] != want:
            sys.exit(f"utf-8: {c.hex()}: Shroud gives [{lines[i]}], Python gives [{want}]")
    return f"{len(cases)} byte strings decode as Python decodes them"


def check_png(exe, tmp):
    out = os.path.join(tmp, "scene.png")
    dump = os.path.join(tmp, "scene.txt")
    run(exe, "png", out, dump)
    data = open(out, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit("png: bad signature")
    pos, idat, size = 8, b"", None
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        crc = struct.unpack(">I", data[pos + 8 + n:pos + 12 + n])[0]
        if zlib.crc32(kind + body) != crc:
            sys.exit(f"png: bad CRC in {kind}")
        if kind == b"IHDR":
            size = struct.unpack(">II", body[:8])
        if kind == b"IDAT":
            idat += body
        pos += 12 + n
    w, h = size
    raw = zlib.decompress(idat)
    want = [int(v) for v in open(dump).read().split()]
    for y in range(h):
        row = raw[y * (1 + 4 * w):(y + 1) * (1 + 4 * w)]
        if row[0] != 0:
            sys.exit("png: unexpected filter")
        for x in range(w):
            r, g, b, a = row[1 + 4 * x:5 + 4 * x]
            if (a << 24 | r << 16 | g << 8 | b) != want[y * w + x]:
                sys.exit(f"png: pixel ({x}, {y}) differs")
    return f"{w}x{h} image: chunks, CRCs, zlib stream and every pixel check"


def mutants(font, rng, count):
    """Damaged copies of a font: random bytes, truncation, and hostile table fields."""
    out = []
    n_tables = struct.unpack(">H", font[4:6])[0]
    records = [font[12 + 16 * i:28 + 16 * i] for i in range(n_tables)]
    tables = {r[:4]: struct.unpack(">II", r[8:16]) for r in records}
    for i in range(count):
        b = bytearray(font)
        kind = i % 6
        if kind == 0:
            for _ in range(rng.randint(1, 40)):
                b[rng.randrange(len(b))] = rng.randrange(256)
        elif kind == 1:
            b = b[:rng.randrange(len(b))]
        elif kind == 2:
            # Point a table record's offset or length somewhere hostile.
            r = 12 + 16 * rng.randrange(n_tables) + rng.choice([8, 12])
            b[r:r + 4] = struct.pack(">I", rng.choice([0, 0xFFFFFFFF, 0x7FFFFFFF, len(b), len(b) - 1, rng.randrange(1 << 32)]))
        elif kind == 3:
            # Damage the glyph data: contour counts, end points, flags, composite records.
            off, length = tables[b"glyf"]
            for _ in range(rng.randint(1, 30)):
                p = off + rng.randrange(length)
                b[p:p + 2] = struct.pack(">H", rng.choice([0, 1, 0x7FFF, 0x8000, 0xFFFF, rng.randrange(65536)]))
        elif kind == 4:
            # Damage loca and cmap: glyph offsets and segment tables.
            for tag in (b"loca", b"cmap", b"hhea", b"maxp", b"head"):
                off, length = tables[tag]
                for _ in range(rng.randint(0, 6)):
                    p = off + rng.randrange(max(1, length - 1))
                    b[p:p + 2] = struct.pack(">H", rng.choice([0, 0xFFFF, 0x8000, rng.randrange(65536)]))
        else:
            # A composite glyph that includes itself, and deep nesting.
            off, length = tables[b"glyf"]
            p = off + rng.randrange(length - 12)
            b[p:p + 2] = b"\xff\xff"
            b[p + 10:p + 14] = struct.pack(">HH", 0x0022, rng.randrange(400))
        out.append(bytes(b))
    return out


def check_fuzz(exe, tmp):
    rng = random.Random(1337)
    paths = []
    for font in FONTS:
        data = open(os.path.join(ROOT, font), "rb").read()
        for k, m in enumerate(mutants(data, rng, 150)):
            p = os.path.join(tmp, f"m{len(paths)}.ttf")
            open(p, "wb").write(m)
            paths.append(p)
    for extra, content in (("empty", b""), ("tiny", b"\x00\x01\x00\x00"), ("random", bytes(rng.randrange(256) for _ in range(5000)))):
        p = os.path.join(tmp, extra + ".ttf")
        open(p, "wb").write(content)
        paths.append(p)
    r = run(exe, "fuzz", *paths, check=False)
    if r.returncode != 0 or not r.stdout.startswith("fuzz"):
        sys.exit(f"font fuzz: the program stopped (exit {r.returncode}):\n{r.stdout[-2000:]}{r.stderr[-2000:]}")
    return f"{len(paths)} damaged fonts: {r.stdout.strip()[5:]}, no stops"




def check_single_line_budget(capstanc, cc, cflags, tmp):
    exe = build(capstanc, cc, cflags, tmp, "tests/shroud/single_line_budget.cap", "single-line-budget")
    source = os.path.join(tmp, "alternating-controls.txt")
    with open(source, "wb") as f:
        f.write(b"A\n" * 32768)
    env = os.environ.copy()
    env["CAPSTAN_GC_STATS"] = "1"
    r = subprocess.run([exe, source], cwd=ROOT, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        sys.exit(f"single-line budget: exit {r.returncode}:\n{r.stdout}{r.stderr}")
    if r.stdout != "32768\n65\n65\n":
        sys.exit(f"single-line budget: incorrect retained bytes: {r.stdout!r}")
    match = re.search(r"total_allocated=(\d+)", r.stderr)
    if not match:
        sys.exit(f"single-line budget: GC allocation counter missing: {r.stderr!r}")
    allocated = int(match.group(1))
    # 32,768 alternating retained spans must be assembled in one join, not
    # by repeatedly copying the growing prefix (which allocates ~512 MiB).
    if allocated > 16 * 1024 * 1024:
        sys.exit(f"single-line budget: allocation amplification: {allocated} bytes")
    return f"65,536-byte alternating input -> 32,768 retained bytes; total Capstan allocation {allocated} bytes"


def check_pixmap_limits(capstanc, cc, cflags, tmp):
    exe = build(capstanc, cc, cflags, tmp, "tests/shroud/limits.cap", "pixmap-limits")
    ok = run(exe)
    if ok.stdout.strip() != "resource limits: 29 assertions and glyph cache exercised":
        sys.exit(f"pixmap limits: unexpected output: {ok.stdout!r}")
    rejected_exe = build(capstanc, cc, cflags, tmp, "tests/shroud/limits_reject.cap", "pixmap-reject")
    rejected = run(rejected_exe, check=False)
    if rejected.returncode != 101 or "pixmap size out of range" not in rejected.stdout:
        sys.exit(f"pixmap limits: oversized constructor request was not rejected: exit {rejected.returncode}\\n{rejected.stdout}{rejected.stderr}")
    return "29 resource-budget assertions including recursive composite budget; glyph cache exercised; oversized pixmap rejected before allocation"



def check_golden(capstanc, cc, cflags, tmp, update):
    exe = build(capstanc, cc, cflags, tmp, "examples/shroud/gallery.cap", "gallery")
    out = os.path.join(tmp, "frames")
    os.makedirs(out, exist_ok=True)
    run(exe, out)
    got = {}
    for name in sorted(os.listdir(out)):
        got[name] = hashlib.sha256(open(os.path.join(out, name), "rb").read()).hexdigest()
    if update:
        with open(GOLDEN, "w") as f:
            f.write("# SHA-256 of every file examples/shroud/gallery.cap writes. Regenerate with\n")
            f.write("# tests/shroud/check.py CAPSTANC CC --update-golden after an intended change.\n")
            for name, h in got.items():
                f.write(f"{h}  {name}\n")
        return f"recorded {len(got)} files"
    want = {}
    for line in open(GOLDEN):
        if line.strip() and not line.startswith("#"):
            h, name = line.split()
            want[name] = h
    if got != want:
        diff = sorted(n for n in set(got) | set(want) if got.get(n) != want.get(n))
        sys.exit(f"golden: these frames changed: {', '.join(diff)} (run with --update-golden if intended)")
    return f"{len(got)} frames and accessibility trees identical to the recorded ones"


def main():
    args = [a for a in sys.argv[1:] if a != "--update-golden"]
    update = "--update-golden" in sys.argv
    if len(args) < 2:
        sys.exit(__doc__)
    capstanc = os.path.abspath(args[0]) if os.path.exists(args[0]) else args[0]
    cc, cflags = args[1], args[2:]
    if not any(f.startswith("-O") for f in cflags):
        cflags = ["-O2"] + cflags
    with tempfile.TemporaryDirectory() as tmp:
        report = []
        beh = build(capstanc, cc, cflags, tmp, "tests/shroud/behaviour.cap", "behaviour")
        r = run(beh, check=False)
        if r.returncode != 0:
            sys.exit(f"behaviour:\n{r.stdout}{r.stderr}")
        report.append("behaviour: " + r.stdout.strip().split("\n")[-1])
        vec = build(capstanc, cc, cflags, tmp, "tests/shroud/vectors.cap", "vectors")
        report.append("raster: " + check_raster(vec, tmp))
        if update:
            with open(EXPECTED_FONTS, "w") as f:
                f.write(font_reference())
        report.append("fonts: " + check_fonts(vec))
        report.append("utf-8: " + check_utf8(vec, tmp))
        report.append("png: " + check_png(vec, tmp))
        report.append("font fuzz: " + check_fuzz(vec, tmp))
        report.append("pixmap limits: " + check_pixmap_limits(capstanc, cc, cflags, tmp))
        report.append("single-line filtering: " + check_single_line_budget(capstanc, cc, cflags, tmp))
        report.append("golden: " + check_golden(capstanc, cc, cflags, tmp, update))
        print("\n".join(report))


if __name__ == "__main__":
    main()
