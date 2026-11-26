#!/usr/bin/env python3
"""Validate claim-scoped assurance records and enforce promotion requirements.

Freshness is computed against the checked-out HEAD using Git history. Proposed and
withdrawn claims remain visible with stale-record diagnostics. Active and qualified
claims are release-gated on fresh review, passed exact-commit evidence and independent
review evidence; a green test alone cannot promote a claim.
"""
import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def inside_repo(path):
    if (not isinstance(path, str) or not path or path.startswith("/")
            or "\\" in path or re.match(r"^[A-Za-z]:", path)):
        return False
    parts = path.split("/")
    return all(p not in ("", ".", "..") for p in parts)


def resolves_inside_repo(path):
    """Resolve a validated repository-relative path without following it outside ROOT.

    realpath may produce a path on another filesystem/drive (notably through a
    symlink on Windows); commonpath raises ValueError for different roots. Both
    cases are a failed containment check, never an uncaught validator exception.
    """
    if not inside_repo(path):
        return False
    root_real = os.path.normcase(os.path.realpath(ROOT))
    full = os.path.normcase(os.path.realpath(os.path.join(ROOT, path)))
    try:
        return os.path.commonpath((root_real, full)) == root_real
    except ValueError:
        return False


def requires_freshness(state):
    """Only claims presented as live assurance must have current evidence."""
    return state in ("active", "qualified")


def promotion_errors(claim):
    """Return missing evidence required before a claim can be presented as live.

    A live claim needs at least one passed, exact-commit verification and a passed
    independent review tied to the same reviewed source revision. This checks the
    presence and identity of evidence records; it does not judge their substance.
    """
    if not requires_freshness(claim.get("state")):
        return []
    cid = claim.get("id", "<missing>")
    evidence = claim.get("evidence", [])
    passed = [item for item in evidence if item.get("result") == "passed"]
    errors = []
    if not passed:
        errors.append(
            "%s: live claim requires at least one passed evidence record" % cid)
    review_revision = claim.get("review", {}).get("reviewed_commit", "")
    independent = [
        item for item in passed
        if item.get("kind") == "independent-review"
        and item.get("revision") == review_revision
        and item.get("verification", {}).get("commit") == review_revision
    ]
    if not independent:
        errors.append(
            "%s: live claim requires passed independent-review evidence "
            "at the reviewed commit" % cid)
    return errors



def boundary_policy_errors(boundaries):
    """Reject duplicate boundary IDs and unsupported proof/refinement combinations."""
    errors = []
    seen = set()
    for boundary in boundaries.get("boundaries", []):
        bid = boundary.get("id", "<missing>")
        if bid in seen:
            errors.append("duplicate boundary identifier %s" % bid)
        seen.add(bid)
        if boundary.get("formal") == "proved" and not boundary.get("implementation_refinement"):
            errors.append("%s: formal=proved requires implementation_refinement=true" % bid)
        if boundary.get("implementation_refinement") and boundary.get("formal") != "proved":
            errors.append("%s: implementation_refinement=true requires formal=proved" % bid)
    return errors


def git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False)


def changed_paths(revision, paths):
    """Return paths changed from revision to HEAD, or raise on invalid history."""
    ancestor = git("merge-base", "--is-ancestor", revision, "HEAD")
    if ancestor.returncode != 0:
        raise ValueError("revision is not an ancestor of HEAD: " + revision)
    # Treat manifest entries as literal repository paths, not Git pathspec syntax.
    pathspecs = [":(literal)" + path for path in paths]
    result = git("diff", "--name-only", "--no-renames", revision, "HEAD", "--", *pathspecs)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "git diff failed")
    return [p for p in result.stdout.splitlines() if p]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default="docs/assurance/assurance.schema.json")
    ap.add_argument("--manifest", default="docs/assurance/claims.json")
    ap.add_argument("--boundaries", default="docs/assurance/execution-boundaries.json")
    ap.add_argument("--boundary-schema", default="docs/assurance/execution-boundaries.schema.json")
    ap.add_argument("--require-fresh", action="store_true",
                    help=("fail if active or qualified claims lack fresh review, "
                          "passed exact-commit evidence, or independent review"))
    args = ap.parse_args()
    try:
        import jsonschema
    except ImportError:
        sys.exit("assurance-validate: install the hash-pinned jsonschema requirements used by CI")

    def load(path):
        full = os.path.join(ROOT, path)
        with open(full, encoding="utf-8") as f:
            return json.load(f)

    try:
        schema = load(args.schema)
        manifest = load(args.manifest)
        boundary_schema = load(args.boundary_schema)
        boundaries = load(args.boundaries)
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator.check_schema(boundary_schema)
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(validator.iter_errors(manifest),
                        key=lambda e: (list(map(str, e.absolute_path)), e.message))
        boundary_validator = jsonschema.Draft202012Validator(
            boundary_schema, format_checker=jsonschema.FormatChecker())
        boundary_errors = sorted(
            boundary_validator.iter_errors(boundaries),
            key=lambda e: (list(map(str, e.absolute_path)), e.message))
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as e:
        sys.exit("assurance-validate: " + str(e))

    failed = False
    for e in errors:
        where = "/" + "/".join(map(str, e.absolute_path))
        print("  claims schema: %s: %s" % (where, e.message))
        failed = True
    for e in boundary_errors:
        where = "/" + "/".join(map(str, e.absolute_path))
        print("  boundaries schema: %s: %s" % (where, e.message))
        failed = True

    # Never inspect nested manifest fields after schema failure. Malformed
    # structures must fail closed with diagnostics, not raise AttributeError
    # while freshness checks assume the schema's object/list shapes.
    if errors or boundary_errors:
        return 1

    head = git("rev-parse", "HEAD")
    if head.returncode != 0:
        sys.exit("assurance-validate: must run inside a Git checkout")
    head_sha = head.stdout.strip()
    snapshot = manifest.get("snapshot", {}).get("commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", snapshot):
        print("  snapshot: missing full commit SHA")
        failed = True
    else:
        try:
            changed_paths(snapshot, [])
        except ValueError as e:
            print("  snapshot: %s" % e)
            failed = True

    # Validate the architecture register independently from the claim register.
    # A formal proof over a model is not an implementation proof unless the
    # boundary explicitly records a reviewed refinement link.
    boundary_paths = set()
    for path in boundaries.get("production_path", []) + boundaries.get("target_path", []):
        boundary_paths.add(path)
    for error in boundary_policy_errors(boundaries):
        print("  boundary: " + error)
        failed = True
    for boundary in boundaries.get("boundaries", []):
        boundary_paths.update(boundary.get("artifacts", []))
    for path in sorted(boundary_paths):
        if not inside_repo(path):
            print("  boundary: unsafe repository path %r" % path)
            failed = True
        elif not resolves_inside_repo(path):
            print("  boundary: path resolves outside repository or across filesystem roots: %s" % path)
            failed = True
        elif not os.path.isfile(os.path.realpath(os.path.join(ROOT, path))):
            print("  boundary: artifact does not exist: %s" % path)
            failed = True
    baseline = boundaries.get("baseline_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        print("  boundary: missing full baseline commit SHA")
        failed = True
    else:
        try:
            changed_paths(baseline, [])
        except ValueError as e:
            print("  boundary: baseline is not in current history: %s" % e)
            failed = True

    ids = set()
    stale_count = 0
    gated_stale_count = 0
    promotion_failure_count = 0

    def record_stale(claim, description):
        nonlocal stale_count, gated_stale_count
        stale_count += 1
        if requires_freshness(claim.get("state")):
            gated_stale_count += 1
        print("  STALE %s %s" % (claim.get("id", "<missing>"), description))

    for claim in manifest.get("claims", []):
        cid = claim.get("id", "<missing>")
        if cid in ids:
            print("  claim: duplicate identifier %s" % cid)
            failed = True
        ids.add(cid)
        if args.require_fresh:
            for error in promotion_errors(claim):
                print("  PROMOTION BLOCKED " + error)
                promotion_failure_count += 1
        coverage = claim.get("covers", [])
        for path in coverage:
            if not inside_repo(path):
                print("  %s: unsafe covered path %r" % (cid, path))
                failed = True
                continue
            full = os.path.realpath(os.path.join(ROOT, path))
            if not resolves_inside_repo(path):
                print("  %s: covered path resolves outside repository or across filesystem roots: %s" % (cid, path))
                failed = True
            elif not os.path.exists(full):
                print("  %s: covered path does not exist: %s" % (cid, path))
                failed = True
        review_revision = claim.get("review", {}).get("reviewed_commit", "")
        if re.fullmatch(r"[0-9a-f]{40}", review_revision) and coverage:
            try:
                changed = changed_paths(review_revision, coverage)
                if changed:
                    record_stale(claim, "review: covered implementation changed since %s: %s" %
                                 (review_revision, ", ".join(changed)))
            except ValueError as e:
                record_stale(claim, "review: %s" % e)
        for ei, evidence in enumerate(claim.get("evidence", [])):
            artifacts = evidence.get("artifacts", [])
            safe_artifacts = True
            for path in artifacts:
                if not inside_repo(path):
                    print("  %s evidence[%d]: unsafe repository path %r" % (cid, ei, path))
                    failed = True
                    safe_artifacts = False
                    continue
                full = os.path.realpath(os.path.join(ROOT, path))
                if not resolves_inside_repo(path):
                    print("  %s evidence[%d]: artifact resolves outside repository or across filesystem roots: %s" % (cid, ei, path))
                    failed = True
                    safe_artifacts = False
                    continue
                if not os.path.isfile(full):
                    print("  %s evidence[%d]: artifact does not exist: %s" % (cid, ei, path))
                    failed = True
                    safe_artifacts = False
            revision = evidence.get("revision", "")
            if re.fullmatch(r"[0-9a-f]{40}", revision) and safe_artifacts:
                paths = list(dict.fromkeys(artifacts + coverage))
                try:
                    changed = changed_paths(revision, paths)
                    if changed:
                        record_stale(
                            claim, "evidence[%d] (%s): changed since %s: %s" %
                            (ei, evidence.get("kind", "unknown"), revision, ", ".join(changed)))
                except ValueError as e:
                    record_stale(claim, "evidence[%d]: %s" % (ei, e))
            verification = evidence.get("verification")
            if evidence.get("result") == "passed" and verification:
                if not re.fullmatch(r"[0-9a-f]{40}", verification.get("commit", "")):
                    print("  %s evidence[%d]: passed evidence lacks a full commit SHA" % (cid, ei))
                    failed = True
                if verification.get("commit") != revision:
                    print("  %s evidence[%d]: verification commit differs from evidence revision" % (cid, ei))
                    failed = True
                if not verification.get("run_url", "").startswith("https://github.com/"):
                    print("  %s evidence[%d]: passed evidence needs a GitHub run/review URL" % (cid, ei))
                    failed = True

    if args.require_fresh and (gated_stale_count or promotion_failure_count):
        print("assurance-validate: %d stale record(s) and %d promotion failure(s) on active/qualified claims" %
              (gated_stale_count, promotion_failure_count))
        failed = True
    if failed:
        return 1
    print("assurance-validate: %d claim(s), %d execution boundary(s), both schemas valid, evidence paths resolve; HEAD %s; %d stale record(s), %d on active/qualified claims; %d promotion failure(s)" %
          (len(manifest.get("claims", [])), len(boundaries.get("boundaries", [])),
           head_sha, stale_count, gated_stale_count, promotion_failure_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
