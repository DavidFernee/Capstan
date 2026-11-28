"""Run every registered suite; incomplete evidence is never a pass."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(__file__).with_name("systematic_suites.json")


def validate_manifest(groups):
    if not isinstance(groups, dict) or not groups:
        raise ValueError("empty manifest")
    seen = set()
    for group, commands in groups.items():
        if not group.isascii() or not group.isalpha() or not isinstance(commands, list) or not commands:
            raise ValueError("invalid or empty group")
        for argv in commands:
            if not isinstance(argv, list) or not all(isinstance(a, str) and a for a in argv):
                raise ValueError("invalid command")
            if len(argv) < 2 or argv[0] not in ("bin/capstan", "python3"):
                raise ValueError("unsupported runner")
            if argv[0] == "bin/capstan" and (len(argv) < 3 or argv[1] != "test"):
                raise ValueError("unsupported Capstan invocation")
            paths = argv[2:] if argv[0] == "bin/capstan" else argv[1:]
            if any(Path(p).is_absolute() or ".." in Path(p).parts or p.startswith("-") for p in paths):
                raise ValueError("invalid suite path")
            key = tuple(argv)
            if key in seen:
                raise ValueError("duplicate suite")
            seen.add(key)
    return groups


def execute(commands, directory, cwd, timeout=600):
    directory.mkdir(parents=True, exist_ok=False)
    rows = []
    for i, argv in enumerate(commands):
        log = directory / f"{i:03d}.log"
        start = time.monotonic()
        status = None
        error = ""
        with log.open("wb") as out:
            try:
                result = subprocess.run(argv, cwd=cwd, stdout=out,
                                        stderr=subprocess.STDOUT, timeout=timeout)
                status = result.returncode
            except subprocess.TimeoutExpired:
                error = "timeout"
            except OSError as exc:
                error = type(exc).__name__
        rows.append({"argv": argv, "returncode": status, "error": error,
                     "elapsed_seconds": round(time.monotonic() - start, 3),
                     "log": log.name, "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
        print(json.dumps(rows[-1]), flush=True)
    return rows


def complete(commands, rows):
    return bool(commands) and len(rows) == len(commands) and all(
        row["argv"] == argv and type(row["returncode"]) is int
        and row["returncode"] == 0 and row["error"] == ""
        for argv, row in zip(commands, rows))


def main():
    group = sys.argv[1]
    groups = validate_manifest(json.loads(MANIFEST.read_text()))
    commands = groups[group]
    directory = ROOT / "build" / "systematic-evidence" / group
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    revision = git("rev-parse", "HEAD")
    tree = git("rev-parse", "HEAD^{tree}")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked tree is dirty before campaign")
    rows = execute(commands, directory, ROOT)
    passed = complete(commands, rows) and not git("status", "--porcelain", "--untracked-files=no")
    evidence = {"schema": 1, "revision": revision, "tree": tree, "group": group,
                "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
                "expected_count": len(commands), "results": rows, "passed": passed}
    (directory / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
