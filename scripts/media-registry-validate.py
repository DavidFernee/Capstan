#!/usr/bin/env python3
"""Dependency-free, fail-closed validator for the Capstan media registry."""
import json
import re
import sys
from pathlib import Path

TOP = {"schema_version", "registry_version", "records"}
FIELDS = {"id","version","container","codec","profile","level","operation","ancillary_formats",
          "bit_depth","chroma","channel_layout","platforms","implementation","source_revision",
          "licence_review","patent_review","corpus_revision","test_status","fuzz_status",
          "assurance_level","known_limitations"}
SEMVER = re.compile(r"^[0-9]+\\.[0-9]+\\.[0-9]+$")
IDENT = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")
REV = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
ENUMS = {
 "operation":{"decode","encode","demux","mux"},
 "licence_review":{"not-reviewed","reviewed-clear","restricted","unknown"},
 "patent_review":{"not-reviewed","reviewed-clear","restricted","unknown"},
 "test_status":{"not-present","present-not-run","passed","failed","inconclusive"},
 "fuzz_status":{"not-run","running","passed","failed","inconclusive"},
 "assurance_level":{"unassessed","prototype","reviewed","release-assured"},
}

def validate_registry(value):
    errors = []
    if not isinstance(value, dict):
        return ["$: expected object"]
    errors += [f"$: unknown property {k!r}" for k in sorted(set(value)-TOP)]
    errors += [f"$: missing property {k!r}" for k in sorted(TOP-set(value))]
    if value.get("schema_version") != "1.0.0":
        errors.append("$.schema_version: must equal '1.0.0'")
    if not isinstance(value.get("registry_version"), str) or not SEMVER.fullmatch(value["registry_version"]):
        errors.append("$.registry_version: expected numeric major.minor.patch")
    records = value.get("records")
    if not isinstance(records, list):
        return sorted(errors + ["$.records: expected array"])
    ids, tuples = set(), set()
    for i, r in enumerate(records):
        p = f"$.records[{i}]"
        if not isinstance(r, dict):
            errors.append(f"{p}: expected object")
            continue
        errors += [f"{p}: unknown property {k!r}" for k in sorted(set(r)-FIELDS)]
        errors += [f"{p}: missing property {k!r}" for k in sorted(FIELDS-set(r))]
        for k in ("id","version","container","codec","profile","implementation","corpus_revision"):
            if not isinstance(r.get(k), str) or not r[k].strip():
                errors.append(f"{p}.{k}: expected non-empty string")
        ident = r.get("id")
        if isinstance(ident, str):
            if not IDENT.fullmatch(ident): errors.append(f"{p}.id: invalid stable identifier")
            if ident in ids: errors.append(f"{p}.id: duplicate identifier {ident!r}")
            ids.add(ident)
        if isinstance(r.get("version"), str) and not SEMVER.fullmatch(r["version"]):
            errors.append(f"{p}.version: expected numeric major.minor.patch")
        for k, allowed in ENUMS.items():
            if r.get(k) not in allowed: errors.append(f"{p}.{k}: unknown value")
        if not isinstance(r.get("source_revision"), str) or not REV.fullmatch(r["source_revision"]):
            errors.append(f"{p}.source_revision: expected 40- or 64-character lowercase Git object id")
        for k in ("level","chroma","channel_layout"):
            if r.get(k) is not None and not isinstance(r.get(k), str):
                errors.append(f"{p}.{k}: expected string or null")
        depth = r.get("bit_depth")
        if depth is not None and (type(depth) is not int or not 1 <= depth <= 128):
            errors.append(f"{p}.bit_depth: expected integer 1..128 or null")
        for k, nonempty in (("platforms",True),("ancillary_formats",False),("known_limitations",False)):
            a = r.get(k)
            if not isinstance(a, list) or (nonempty and not a):
                errors.append(f"{p}.{k}: expected {'non-empty ' if nonempty else ''}array")
            elif any(not isinstance(x,str) or not x.strip() for x in a):
                errors.append(f"{p}.{k}: items must be non-empty strings")
            elif len(a) != len(set(a)):
                errors.append(f"{p}.{k}: duplicate entries are not permitted")
        # Duplicate exact operation/profile tuples are conflicts, even under distinct IDs.
        key = tuple(r.get(k) for k in ("container","codec","profile","level","operation",
                                       "bit_depth","chroma","channel_layout"))
        if key in tuples: errors.append(f"{p}: duplicate/conflicting registration tuple")
        tuples.add(key)
    return sorted(errors)

def main(argv):
    if len(argv) != 2:
        print(f"usage: {Path(argv[0]).name} REGISTRY.json", file=sys.stderr)
        return 2
    try:
        value = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"registry input error: {exc}", file=sys.stderr)
        return 2
    errors = validate_registry(value)
    if errors:
        print("\\n".join(errors), file=sys.stderr)
        return 1
    print(f"valid media registry: {len(value['records'])} record(s), schema 1.0.0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
