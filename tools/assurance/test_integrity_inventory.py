"""Conservative test-evidence inventory; review flags are not semantic proofs."""
import argparse
import json
import re
import subprocess
import sys

BYPASS = re.compile(
    rb"\b(?:continue-on-error|allow_failure|skipTest|pytest\.mark\.(?:skip|xfail)"
    rb"|unittest\.skip|GITHUB_STEP_SUMMARY)\b|\|\|\s*true\b"
    rb"|\b(?:sorry|admit|axiom)\b|\bif:\s*(?:false|\$\{\{\s*false)"
    rb"|\bassert\s*\(\s*true\s*\)|\bassert\s+True\b", re.I)

def git(*args):
    return subprocess.check_output(["git", "--literal-pathspecs", *args])

def protected(path):
    parts = path.lower().split("/")
    return (parts[0] in {"tests", "verification", ".github", "proofs", "formal", "scripts"}
            or any(any(s in p for s in ("test", "fuzz", "mutation", "assurance"))
                   for p in parts)
            or path.lower().endswith(".lean"))

def inventory(rev):
    paths = git("ls-tree", "-r", "--name-only", "-z", rev).split(b"\0")
    return sorted(p.decode("utf-8", "surrogateescape") for p in paths
                  if p and protected(p.decode("utf-8", "surrogateescape")))

def audit(base, head):
    base, head = [git("rev-parse", "--verify", "--end-of-options", r + "^{commit}").decode().strip()
                  for r in (base, head)]
    raw = git("diff", "--no-renames", "--no-ext-diff", "--no-textconv", "--numstat", "-z", base, head, "--")
    changes = []
    for entry in raw.split(b"\0"):
        if not entry:
            continue
        added, deleted, name = entry.split(b"\t", 2)
        path = name.decode("utf-8", errors="surrogateescape")
        if not protected(path):
            continue
        reasons = []
        if deleted != b"0":
            reasons.append("deleted-lines-or-binary-change")
        patch = git("diff", "--no-renames", "--no-ext-diff", "--no-textconv",
                    "--unified=0", base, head, "--", path)
        if any(line.startswith((b"old mode ", b"new mode ")) for line in patch.splitlines()):
            reasons.append("mode-change")
        if any(BYPASS.search(line[1:]) for line in patch.splitlines()
               if line.startswith(b"+") and not line.startswith(b"+++ ")):
            reasons.append("possible-bypass-added")
        changes.append({"path": path, "added": int(added) if added.isdigit() else None,
                        "deleted": int(deleted) if deleted.isdigit() else None,
                        "reasons": reasons, "review_required": bool(reasons)})
    before, after = inventory(base), inventory(head)
    removed = sorted(set(before) - set(after))
    return {"base": base, "head": head, "changes": changes,
            "protected_paths_before": len(before), "protected_paths_after": len(after),
            "removed_paths": removed,
            "review_required": bool(removed) or any(c["review_required"] for c in changes)}

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
