#!/usr/bin/env python3
"""Validate claim-scoped assurance records without network access.

Usage:
  python3 scripts/assurance-validate.py [--schema PATH] [--manifest PATH]

The JSON Schema validates structure. This script additionally checks unique claim
identifiers, repository-relative evidence paths, and pinned verification metadata.
It deliberately does not infer that a test passed merely because a fixture exists.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def inside_repo(path):
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    parts = path.split("/")
    return all(p not in ("", ".", "..") for p in parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schema", default="docs/assurance/assurance.schema.json")
    ap.add_argument("--manifest", default="docs/assurance/claims.json")
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
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker())
        errors = sorted(validator.iter_errors(manifest),
                        key=lambda e: (list(map(str, e.absolute_path)), e.message))
    except (OSError, json.JSONDecodeError, jsonschema.SchemaError) as e:
        sys.exit("assurance-validate: " + str(e))

    failed = False
    for e in errors:
        where = "/" + "/".join(map(str, e.absolute_path))
        print("  schema: %s: %s" % (where, e.message))
        failed = True

    ids = set()
    for ci, claim in enumerate(manifest.get("claims", [])):
        cid = claim.get("id", "<missing>")
        if cid in ids:
            print("  claim: duplicate identifier %s" % cid)
            failed = True
        ids.add(cid)
        for ei, evidence in enumerate(claim.get("evidence", [])):
            for path in evidence.get("artifacts", []):
                if not inside_repo(path):
                    print("  %s evidence[%d]: unsafe repository path %r" % (cid, ei, path))
                    failed = True
                    continue
                full = os.path.join(ROOT, path)
                if not os.path.isfile(full):
                    print("  %s evidence[%d]: artifact does not exist: %s" % (cid, ei, path))
                    failed = True
            verification = evidence.get("verification")
            if evidence.get("result") == "passed" and verification:
                if not re.fullmatch(r"[0-9a-f]{40}", verification.get("commit", "")):
                    print("  %s evidence[%d]: passed evidence lacks a full commit SHA" % (cid, ei))
                    failed = True
                if not verification.get("run_url", "").startswith("https://github.com/"):
                    print("  %s evidence[%d]: passed evidence needs a GitHub run/review URL" % (cid, ei))
                    failed = True

    if failed:
        return 1
    print("assurance-validate: %d claim(s), schema valid, all evidence paths resolve" %
          len(manifest.get("claims", [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
