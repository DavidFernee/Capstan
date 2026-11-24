#!/usr/bin/env python3
"""Hardening rules for .github/workflows, checked on every run of the suite.

- Every third-party action is pinned by a full 40-hex commit id, with its version in a comment.
- Every workflow sets top-level `permissions: contents: read` and nothing else.
- No `pull_request_target` or `workflow_run` triggers (they run with a privileged token on
  untrusted code).
- No `${{ ... }}` expansion of untrusted event data or secrets inside a `run:` script; values
  reach scripts through `env:` instead.
- Every actions/checkout sets `persist-credentials: false`.
- Write permissions are allowlisted per workflow and job; CodeQL result upload is restricted to its analysis job.

Line-based (no YAML library) so it runs with `python3 -I` anywhere.
Usage: python3 -I tests/supply/workflows.py [DIR]   (default .github/workflows)
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WF = os.path.join(ROOT, ".github", "workflows")
# The only write permissions allowed, as (workflow, job, permission).
ALLOWED_WRITES = {
    ("release.yml", "sign", "id-token"),
    ("release.yml", "sign", "attestations"),
    ("release.yml", "publish", "contents"),
    ("codeql.yml", "analyze", "security-events"),
}
USES = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)(.*)$")
PINNED = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{40}$")
UNTRUSTED = re.compile(r"\$\{\{[^}]*\b(github\.event\.|github\.head_ref|secrets\.|inputs\.)")


def check(name, text, errors):
    lines = text.splitlines()
    def err(i, msg):
        errors.append(f"{name}:{i + 1}: {msg}")
    if any(re.search(r"\b(pull_request_target|workflow_run)\b", l.split("#")[0]) for l in lines):
        err(0, "pull_request_target/workflow_run triggers are not allowed")
    # Top-level permissions: exactly `contents: read`.
    top = [i for i, l in enumerate(lines) if l.rstrip() == "permissions:"]
    if not top:
        err(0, "no top-level 'permissions:' block")
    else:
        body = []
        for l in lines[top[0] + 1:]:
            if not l.startswith("  ") or not l.strip():
                break
            body.append(l.strip())
        if body != ["contents: read"]:
            err(top[0], f"top-level permissions must be exactly 'contents: read', not {body}")
    job, in_run, run_indent = None, False, 0
    for i, l in enumerate(lines):
        s = l.strip()
        indent = len(l) - len(l.lstrip())
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", l)
        if m and indent == 2 and "jobs:" in lines[:i]:
            job = m.group(1)
        if in_run and s and indent <= run_indent:
            in_run = False
        if in_run and UNTRUSTED.search(l):
            err(i, "untrusted data or a secret expanded inside a run script; pass it through env:")
        rm = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", l)
        if rm:
            run_indent = len(rm.group(1))
            in_run = rm.group(2).strip() in ("|", ">", "|-", ">-")
            if not in_run and UNTRUSTED.search(rm.group(2)):
                err(i, "untrusted data or a secret expanded inside a run script; pass it through env:")
        um = USES.match(l)
        if um:
            ref, rest = um.group(1), um.group(2)
            if ref.startswith("./"):
                pass
            elif not PINNED.match(ref):
                err(i, f"action '{ref}' is not pinned by a full commit id")
            elif not re.search(r"#\s*v\d+(\.\d+)*", rest):
                err(i, f"pinned action '{ref}' has no '# vX.Y.Z' version comment")
            if ref.startswith("actions/checkout@"):
                block = []
                for l2 in lines[i + 1:]:
                    if len(l2) - len(l2.lstrip()) <= indent or l2.strip().startswith("- "):
                        break
                    block.append(l2.strip())
                if "persist-credentials: false" not in block:
                    err(i, "actions/checkout without 'persist-credentials: false'")
        pm = re.match(r"^\s+([a-z-]+):\s*write\s*$", l)
        if pm and (name, job, pm.group(1)) not in ALLOWED_WRITES:
            err(i, f"'{pm.group(1)}: write' is not allowed in job '{job}'")


def main(argv):
    wf = argv[0] if argv else WF
    errors, n, pins = [], 0, set()
    for f in sorted(os.listdir(wf)):
        if not f.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(wf, f), encoding="utf-8") as fh:
            text = fh.read()
        check(f, text, errors)
        pins.update(m.group(1) for m in map(USES.match, text.splitlines()) if m)
        n += 1
    for e in errors:
        print(e)
    if errors:
        return 1
    print(f"{n} workflows hardened: {len(pins)} actions pinned by commit, read-only by default, no untrusted expansions")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
