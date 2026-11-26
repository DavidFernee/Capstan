#!/usr/bin/env python3
"""Regression test for the machine-readable CWE attempt-record CLI."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "tests", "cwe", "attempt_records.py")


def main():
    result = subprocess.run(
        [sys.executable, SCRIPT, "--json"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise SystemExit(result.stderr.decode("utf-8", "replace"))
    if not result.stdout.endswith(b"\n"):
        raise SystemExit("JSON output must end with one real line-feed")
    if result.stdout.endswith(b"\\n"):
        raise SystemExit("JSON output must not end with a literal backslash-n")
    records = json.loads(result.stdout)
    if not isinstance(records, list) or not records:
        raise SystemExit("expected a non-empty JSON array of attempt records")
    print("CWE attempt-record JSON: %d records, valid JSON, newline-terminated" % len(records))


if __name__ == "__main__":
    main()
