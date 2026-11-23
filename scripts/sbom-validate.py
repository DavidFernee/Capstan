#!/usr/bin/env python3
"""Validate Capstan's SBOMs against the official CycloneDX 1.6 and SPDX 2.3 JSON schemas.

    python3 -I scripts/sbom-validate.py [--schemas DIR] [--cyclonedx FILE] [--spdx FILE]

The schemas are fetched from fixed commits of the CycloneDX and SPDX specification repositories
and checked against the SHA-256 values below before use, or read from DIR (same checks) for
offline use. Needs the `jsonschema` package (scripts/sbom-schema-requirements.txt, hash-pinned);
only CI and release jobs run this, never the compiler or the test suite.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.request

CDX = "https://raw.githubusercontent.com/CycloneDX/specification/e833d732337dd33aceb45ff1991f896796f1e5e7/schema/"  # tag 1.6.2
SPDX = "https://raw.githubusercontent.com/spdx/spdx-spec/6f2cb47d13db19b12c23885573b22ef32ec1ada5/schemas/"  # tag v2.3.1
SCHEMAS = {
    # file name: (URL, SHA-256, $id it is registered under)
    "bom-1.6.schema.json": (CDX + "bom-1.6.schema.json",
                            "18f57f7482593bad9f21b4feed09084640cbeff419d62ad5090c5ceccca5b37d",
                            "http://cyclonedx.org/schema/bom-1.6.schema.json"),
    "spdx.schema.json": (CDX + "spdx.schema.json",
                         "c41917196639055e9f9670811bac23ef777732144f3ff5a2f39686f61580dbe6",
                         "http://cyclonedx.org/schema/spdx.schema.json"),
    "jsf-0.82.schema.json": (CDX + "jsf-0.82.schema.json",
                             "8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae",
                             "http://cyclonedx.org/schema/jsf-0.82.schema.json"),
    "spdx-2.3.schema.json": (SPDX + "spdx-schema.json",
                             "4126dc29f15e92feec92e9622f4939131ad58b125d6f578aa93e980a6e6f3212",
                             "http://spdx.org/rdf/terms/2.3"),
}


def load(name, cache):
    url, want, _ = SCHEMAS[name]
    if cache and os.path.exists(os.path.join(cache, name)):
        with open(os.path.join(cache, name), "rb") as f:
            data = f.read()
    else:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read()
    got = hashlib.sha256(data).hexdigest()
    if got != want:
        sys.exit(f"sbom-validate: {name} has SHA-256 {got}, expected {want}; refusing to use it")
    if cache:
        os.makedirs(cache, exist_ok=True)
        with open(os.path.join(cache, name), "wb") as f:
            f.write(data)
    return json.loads(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--schemas", help="directory to cache schemas in, or read them from")
    ap.add_argument("--cyclonedx")
    ap.add_argument("--spdx")
    a = ap.parse_args()
    if not (a.cyclonedx or a.spdx):
        ap.error("give --cyclonedx and/or --spdx")
    import jsonschema
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7, DRAFT201909

    docs = {n: load(n, a.schemas) for n in SCHEMAS}
    registry = Registry()
    for name, doc in docs.items():
        spec = DRAFT201909 if name.startswith("spdx-2") else DRAFT7
        res = Resource.from_contents(doc, default_specification=spec)
        # Registered under its $id: the CycloneDX schema's relative $refs resolve against it.
        registry = registry.with_resource(SCHEMAS[name][2], res)
    failed = False
    for path, name, cls in ((a.cyclonedx, "bom-1.6.schema.json", jsonschema.Draft7Validator),
                            (a.spdx, "spdx-2.3.schema.json", jsonschema.Draft201909Validator)):
        if not path:
            continue
        with open(path, encoding="utf-8") as f:
            inst = json.load(f)
        v = cls(docs[name], registry=registry, format_checker=cls.FORMAT_CHECKER)
        errors = sorted(v.iter_errors(inst), key=lambda e: list(e.absolute_path))
        for e in errors[:20]:
            print(f"  {path}: /{'/'.join(map(str, e.absolute_path))}: {e.message[:300]}")
        if errors:
            failed = True
            print(f"sbom-validate: {path}: {len(errors)} schema error(s) against {name}")
        else:
            print(f"sbom-validate: {path} is valid against {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
