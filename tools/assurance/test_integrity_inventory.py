"""Conservative test-evidence change detector; not a semantic coverage proof."""
import argparse
import json
import subprocess
import sys

def git(*args):
    return subprocess.check_output(["git", *args])

def protected(path):
    parts = path.lower().split("/")
    return (parts[0] in {"tests", "verification", ".github", "proofs", "formal"}
            or any("test" in p or "fuzz" in p or "mutation" in p for p in parts)
            or path.endswith(".lean"))

def audit(base, head):
    base, head = [git("rev-parse", "--verify", r + "^{commit}").decode().strip()
                  for r in (base, head)]
    raw = git("diff", "--no-renames", "--numstat", "-z", base, head, "--")
    changes = []
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        added, deleted, name = entry.split(b"\t", 2)
        path = name.decode("utf-8", errors="surrogateescape")
        if not protected(path):
            continue
        changes.append({"path": path, "added": int(added) if added.isdigit() else None,
                        "deleted": int(deleted) if deleted.isdigit() else None,
                        "review_required": deleted != b"0"})
    return {"base": base, "head": head, "changes": changes,
            "review_required": any(c["review_required"] for c in changes)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    parser.add_argument("head")
    args = parser.parse_args()
    try:
        report = audit(args.base, args.head)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["review_required"] else 0

if __name__ == "__main__":
    sys.exit(main())
