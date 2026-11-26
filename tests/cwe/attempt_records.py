#!/usr/bin/env python3
"""Emit and validate stable, machine-readable records for the CWE atlas attempts.

The atlas remains the executable source of truth. This adapter deliberately marks
unmapped positive controls, bypass inventories and enforcement points as pending;
it must not manufacture assurance evidence from prose or verdict labels.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ATLAS_PATH = os.path.join(ROOT, "tests", "cwe", "atlas.py")
SCHEMA_PATH = os.path.join(ROOT, "tests", "cwe", "attempt-records.schema.json")


def load_atlas():
    spec = importlib.util.spec_from_file_location("capstan_cwe_atlas", ATLAS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load tests/cwe/atlas.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def records_from_atlas():
    atlas = load_atlas()
    records = []
    seen = set()
    for attempt in atlas.E:
        cwe = int(attempt["cwe"])
        name = attempt["name"]
        code = attempt["code"]
        # Content-derived identity is independent of table order and report order.
        identity = json.dumps(
            [cwe, name, attempt["verdict"], code, attempt["expect"], attempt["note"]],
            ensure_ascii=True, separators=(",", ":"))
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        slug = "".join(ch if ch.isascii() and ch.isalnum() else "-" for ch in name.lower())
        slug = "-".join(part for part in slug.split("-") if part)[:48].rstrip("-")
        record_id = "CWE-%d-%s-%s" % (cwe, slug or "attempt", digest)
        if record_id in seen:
            raise ValueError("duplicate content-derived attempt identifier: " + record_id)
        seen.add(record_id)

        verdict = attempt["verdict"]
        note = attempt["note"].strip()
        assumptions = [
            "The fixture is an abstract Capstan attempt, not a reproduction of a real-world exploit."
        ]
        assumptions.append(note if note else
                          "No per-attempt assumptions have yet been documented.")
        records.append({
            "id": record_id,
            "cwe": cwe,
            "name": name,
            "verdict": verdict,
            "fixture": {"source": "tests/cwe/atlas.py", "code": code},
            "expected_outcome": {"verdict": verdict, "match": attempt["expect"]},
            "positive_control": {
                "status": "not-applicable" if verdict == "na" else "pending",
                "source": None
            },
            "known_bypasses": {"status": "pending", "items": []},
            "enforcement_point": {"status": "pending", "value": None},
            "assumptions": assumptions
        })
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true",
                        help="write the machine-readable records to stdout")
    parser.add_argument("--check", action="store_true",
                        help="validate records against the checked-in JSON Schema")
    args = parser.parse_args()
    try:
        records = records_from_atlas()
        if args.check:
            import jsonschema
            with open(SCHEMA_PATH, encoding="utf-8") as f:
                schema = json.load(f)
            jsonschema.Draft202012Validator.check_schema(schema)
            validator = jsonschema.Draft202012Validator(schema)
            errors = sorted(validator.iter_errors(records),
                            key=lambda e: (list(map(str, e.absolute_path)), e.message))
            if errors:
                for error in errors:
                    where = "/" + "/".join(map(str, error.absolute_path))
                    print("%s: %s" % (where, error.message), file=sys.stderr)
                return 1
            if not os.path.isfile(ATLAS_PATH):
                print("atlas source reference does not exist", file=sys.stderr)
                return 1
        if args.json:
            json.dump(records, sys.stdout, ensure_ascii=False, indent=2)
            sys.stdout.write("\n")
        else:
            pending = sum(
                r["positive_control"]["status"] == "pending"
                or r["known_bypasses"]["status"] == "pending"
                or r["enforcement_point"]["status"] == "pending"
                for r in records
            )
            print("CWE attempt records: %d stable records; %d have evidence fields pending"
                  % (len(records), pending))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, ImportError) as error:
        print("CWE record validation: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
