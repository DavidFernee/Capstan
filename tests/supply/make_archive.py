#!/usr/bin/env python3
"""Make a release-style source archive (capstan-X.Y.Z/...) of the working tree, for the tests.

    python3 -I tests/supply/make_archive.py OUT.tar.gz VERSION

Like `git archive --prefix=capstan-X.Y.Z/`, but of the files as they are now (tracked and
untracked, not ignored), so the tests see uncommitted changes. Deterministic.
"""
import gzip
import io
import os
import subprocess
import sys
import tarfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def files():
    try:
        out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", "-c", "-o", "--exclude-standard"],
                             check=True, capture_output=True).stdout.decode()
        names = [n for n in out.split("\0") if n]
    except (OSError, subprocess.CalledProcessError):
        names = []
        for d, subdirs, fs in os.walk(ROOT):
            subdirs[:] = [s for s in subdirs if s not in (".git", "build", "__pycache__")]
            names += [os.path.relpath(os.path.join(d, f), ROOT) for f in fs]
    return sorted(n for n in set(names) if os.path.isfile(os.path.join(ROOT, n)) and not os.path.islink(os.path.join(ROOT, n)))


def main(out, version):
    prefix = "capstan-" + version
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        dirs = sorted({os.path.dirname(n) for n in files()} - {""})
        seen = set()
        for d in dirs:
            parts = d.split("/")
            for k in range(1, len(parts) + 1):
                p = "/".join(parts[:k])
                if p not in seen:
                    seen.add(p)
                    ti = tarfile.TarInfo(prefix + "/" + p)
                    ti.type, ti.mode, ti.mtime = tarfile.DIRTYPE, 0o755, 0
                    tar.addfile(ti)
        for n in files():
            with open(os.path.join(ROOT, n), "rb") as f:
                data = f.read()
            ti = tarfile.TarInfo(prefix + "/" + n)
            ti.size, ti.mtime = len(data), 0
            ti.mode = 0o755 if os.access(os.path.join(ROOT, n), os.X_OK) else 0o644
            tar.addfile(ti, io.BytesIO(data))
    with open(out, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as gz:
        gz.write(buf.getvalue())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
