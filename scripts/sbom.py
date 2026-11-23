#!/usr/bin/env python3
"""Software bill of materials for a Capstan source release, in CycloneDX 1.6 and SPDX 2.3 (JSON).

    python3 -I scripts/sbom.py generate --archive capstan-X.Y.Z.tar.gz --commit SHA \
        --cyclonedx capstan-X.Y.Z.cdx.json --spdx capstan-X.Y.Z.spdx.json
    python3 -I scripts/sbom.py check --archive capstan-X.Y.Z.tar.gz \
        [--cyclonedx capstan-X.Y.Z.cdx.json] [--spdx capstan-X.Y.Z.spdx.json]

`generate` reads the source archive (as made by `git archive --prefix=capstan-X.Y.Z/`) and records:
the archive's own hashes, every file in it with its hashes, the tools needed to build and test it
(a C compiler, make, Python 3 for the stage-0 bootstrap and the tests, bash), and its run-time
dependencies: only the platform C library. There are no third-party libraries, vendored or
fetched, and the SBOM says so (CycloneDX composition "complete").

The output is deterministic: the same archive, commit and timestamp give the same bytes.
The timestamp is --timestamp, else SOURCE_DATE_EPOCH, else the archive's commit time.

`check` recomputes every hash from the archive and fails if either SBOM disagrees with it.

Standard library only, so it can be audited in one sitting and run with `python3 -I`.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tarfile
import uuid

REPO = "DavidFernee/Capstan"
REPO_URL = "https://github.com/" + REPO
TOOL = "capstan-sbom"
TOOL_VERSION = "1"
LICENSE = "Apache-2.0"
# A fixed namespace so the CycloneDX serial number depends only on the archive's digest.
SERIAL_NS = uuid.UUID("6f1c3c2e-5a7e-4d1b-9a43-2b1d0c0a5e11")


class Fail(Exception):
    pass


def digests(data):
    return {
        "SHA-1": hashlib.sha1(data).hexdigest(),
        "SHA-256": hashlib.sha256(data).hexdigest(),
        "SHA-512": hashlib.sha512(data).hexdigest(),
    }


def read_archive(path):
    """Return (archive digests, version, commit, commit time, [(relative path, digests)])."""
    with open(path, "rb") as f:
        blob = f.read()
    files = []
    prefix = None
    with tarfile.open(path, "r:*") as tar:
        commit = tar.pax_headers.get("comment")  # git archive records the commit here
        for m in tar.getmembers():
            top, _, rel = m.name.partition("/")
            if prefix is None:
                prefix = top
            if top != prefix or not re.fullmatch(r"capstan-\d+\.\d+\.\d+", top):
                raise Fail(f"archive member '{m.name}' is not under a single capstan-X.Y.Z/ directory")
            if m.isdir():
                continue
            if not m.isfile():
                raise Fail(f"archive member '{m.name}' is not a regular file or directory")
            parts = rel.split("/")
            if not rel or rel.startswith("/") or ".." in parts or "\\" in rel:
                raise Fail(f"archive member '{m.name}' has an unsafe path")
            files.append((rel, digests(tar.extractfile(m).read()), m.mtime))
    if not files:
        raise Fail("archive contains no files")
    files.sort()
    version = prefix[len("capstan-"):]
    if "compiler/main.cap" not in {r for r, _, _ in files}:
        raise Fail("archive has no compiler/main.cap")
    with tarfile.open(path, "r:*") as tar:
        src = tar.extractfile(prefix + "/compiler/main.cap").read().decode("utf-8")
    m = re.search(r'^const string VERSION = "([^"]*)";', src, re.M)
    if not m or m.group(1) != version:
        raise Fail(f"archive directory says {version}, compiler/main.cap says {m.group(1) if m else 'nothing'}")
    mtime = max(t for _, _, t in files)
    return digests(blob), version, commit, mtime, [(r, d) for r, d, _ in files]


def iso(epoch):
    return datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Build, test and run-time requirements, from the Makefile, bin/capstan, tests/run.sh and the
# runtime headers' #includes. No versions are claimed: the builder supplies these tools, and the
# reproducibility reports attached to each release name the exact ones used to test it.
REQUIREMENTS = [
    # (key, name, kind, CycloneDX type, description)
    ("c-compiler", "C compiler", "build", "application",
     "Any C11 compiler with GNU extensions (-std=gnu11); every release is tested with GCC and Clang. "
     "Compiles the generated C of the compiler and of every Capstan program. Supplied by the builder, not distributed."),
    ("make", "make", "build", "application",
     "Runs the bootstrap in the Makefile. Supplied by the builder, not distributed."),
    ("python3", "Python 3", "build", "application",
     "Runs bootstrap/capstan0.py (stage 0) once to start the bootstrap, and the test suite. "
     "Standard library only. Not needed to run the compiler or the programs it builds."),
    ("bash", "bash", "build", "application",
     "Runs the bin/capstan front end and the test suite. Not needed by compiled programs."),
    ("libc", "C standard library (with POSIX threads)", "runtime", "library",
     "Provided by the platform. The only run-time dependency of the compiler and of the programs it "
     "builds; the Capstan runtime (runtime/*.h) is included in source form in this archive."),
]


def cyclonedx(arch, version, commit, ts, files):
    tag = "v" + version
    root = "pkg:github/%s@%s" % (REPO, tag)
    hashes = lambda d: [{"alg": a, "content": d[a]} for a in ("SHA-1", "SHA-256", "SHA-512")]
    component = {
        "type": "application",
        "bom-ref": root,
        "supplier": {"name": "Capstan project", "url": [REPO_URL]},
        "name": "capstan",
        "version": version,
        "description": "Capstan source release: the self-hosting compiler, its runtime, the stage-0 bootstrap, tools and tests",
        "hashes": hashes(arch),
        "licenses": [{"license": {"id": LICENSE}}],
        "purl": root,
        "externalReferences": [
            {"type": "vcs", "url": REPO_URL + ".git"},
            {"type": "distribution", "url": "%s/releases/download/%s/capstan-%s.tar.gz" % (REPO_URL, tag, version)},
            {"type": "website", "url": REPO_URL},
        ],
        "properties": [{"name": "capstan:git-commit", "value": commit}],
    }
    comps = []
    for rel, d in files:
        comps.append({"type": "file", "bom-ref": "file:" + rel, "name": rel,
                      "hashes": [{"alg": a, "content": d[a]} for a in ("SHA-1", "SHA-256")]})
    deps = []
    for key, name, kind, ctype, desc in REQUIREMENTS:
        comps.append({
            "type": ctype,
            "bom-ref": "requirement:" + key,
            "name": name,
            "description": desc,
            "scope": "required" if kind == "runtime" else "excluded",
            "properties": [{"name": "capstan:dependency-kind", "value": kind}],
        })
        deps.append({"ref": "requirement:" + key, "dependsOn": []})
    deps.insert(0, {"ref": root, "dependsOn": ["requirement:" + r[0] for r in REQUIREMENTS]})
    return {
        "$schema": "http://cyclonedx.org/schema/bom-1.6.schema.json",
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": "urn:uuid:" + str(uuid.uuid5(SERIAL_NS, arch["SHA-256"])),
        "version": 1,
        "metadata": {
            "timestamp": ts,
            "lifecycles": [{"phase": "build"}],
            "tools": {"components": [{"type": "application", "name": TOOL, "version": TOOL_VERSION,
                                      "description": "scripts/sbom.py in the Capstan repository"}]},
            "component": component,
            "properties": [
                {"name": "capstan:third-party-runtime-dependencies", "value": "none"},
                {"name": "capstan:vendored-third-party-code", "value": "none"},
            ],
        },
        "components": comps,
        "dependencies": deps,
        # The dependency list is complete: nothing is left out.
        "compositions": [{"aggregate": "complete", "dependencies": [root]},
                         {"aggregate": "complete", "assemblies": [root]}],
    }


def spdx(arch, version, commit, ts, files):
    tag = "v" + version
    pkg = "SPDXRef-Package-capstan"
    spdx_alg = {"SHA-1": "SHA1", "SHA-256": "SHA256", "SHA-512": "SHA512"}
    out_files, rels = [], [{"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES",
                             "relatedSpdxElement": pkg}]
    sha1s = []
    for i, (rel, d) in enumerate(files, 1):
        fid = "SPDXRef-File-%04d" % i
        sha1s.append(d["SHA-1"])
        out_files.append({"fileName": "./" + rel, "SPDXID": fid,
                          "checksums": [{"algorithm": "SHA1", "checksumValue": d["SHA-1"]},
                                        {"algorithm": "SHA256", "checksumValue": d["SHA-256"]}],
                          "licenseConcluded": "NOASSERTION", "copyrightText": "NOASSERTION"})
        rels.append({"spdxElementId": pkg, "relationshipType": "CONTAINS", "relatedSpdxElement": fid})
    # SPDX 2.3 section 7.9: SHA-1 of the sorted, concatenated SHA-1s of every file.
    verification = hashlib.sha1("".join(sorted(sha1s)).encode("ascii")).hexdigest()
    packages = [{
        "name": "capstan",
        "SPDXID": pkg,
        "versionInfo": version,
        "packageFileName": "capstan-%s.tar.gz" % version,
        "supplier": "Organization: Capstan project",
        "downloadLocation": "git+%s.git@%s" % (REPO_URL, commit),
        "filesAnalyzed": True,
        "packageVerificationCode": {"packageVerificationCodeValue": verification},
        "checksums": [{"algorithm": spdx_alg[a], "checksumValue": arch[a]} for a in ("SHA-1", "SHA-256", "SHA-512")],
        "homepage": REPO_URL,
        "sourceInfo": "git archive of commit %s (tag %s)" % (commit, tag),
        "licenseConcluded": "NOASSERTION",
        "licenseDeclared": LICENSE,
        "copyrightText": "NOASSERTION",
        "summary": "Capstan source release: the self-hosting compiler, its runtime, the stage-0 bootstrap, tools and tests",
        "comment": "No third-party libraries are vendored or fetched. The only run-time dependency is the platform C library.",
        "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl",
                          "referenceLocator": "pkg:github/%s@%s" % (REPO, tag)}],
        "primaryPackagePurpose": "SOURCE",
        "hasFiles": [f["SPDXID"] for f in out_files],
    }]
    for key, name, kind, _, desc in REQUIREMENTS:
        rid = "SPDXRef-Requirement-" + key
        packages.append({"name": name, "SPDXID": rid, "downloadLocation": "NOASSERTION",
                         "filesAnalyzed": False, "licenseConcluded": "NOASSERTION",
                         "licenseDeclared": "NOASSERTION", "copyrightText": "NOASSERTION",
                         "comment": desc,
                         "primaryPackagePurpose": "LIBRARY" if kind == "runtime" else "APPLICATION"})
        if kind == "runtime":
            rels.append({"spdxElementId": rid, "relationshipType": "RUNTIME_DEPENDENCY_OF", "relatedSpdxElement": pkg})
        else:
            rels.append({"spdxElementId": rid, "relationshipType": "BUILD_TOOL_OF", "relatedSpdxElement": pkg})
    rels.append({"spdxElementId": "SPDXRef-Requirement-python3", "relationshipType": "TEST_TOOL_OF", "relatedSpdxElement": pkg})
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "capstan-" + version,
        "documentNamespace": "%s/sbom/capstan-%s-%s" % (REPO_URL, version, arch["SHA-256"]),
        "creationInfo": {"created": ts, "creators": ["Tool: %s-%s" % (TOOL, TOOL_VERSION)]},
        "packages": packages,
        "files": out_files,
        "relationships": rels,
    }


def dump(doc, path):
    data = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(data)


def generate(a):
    if not (a.cyclonedx or a.spdx):
        raise Fail("nothing to write: give --cyclonedx and/or --spdx")
    arch, version, commit, mtime, files = read_archive(a.archive)
    if not re.fullmatch(r"[0-9a-f]{40}", a.commit):
        raise Fail("--commit must be a full 40-character commit id")
    if commit and commit != a.commit:
        raise Fail(f"archive was made from commit {commit}, not {a.commit}")
    epoch = a.timestamp if a.timestamp is not None else os.environ.get("SOURCE_DATE_EPOCH", mtime)
    ts = iso(epoch)
    if a.cyclonedx:
        dump(cyclonedx(arch, version, a.commit, ts, files), a.cyclonedx)
    if a.spdx:
        dump(spdx(arch, version, a.commit, ts, files), a.spdx)
    print(f"sbom: capstan {version}, {len(files)} files, {len(REQUIREMENTS)} requirements, no third-party dependencies")


def check(a):
    arch, version, commit, _, files = read_archive(a.archive)
    want = {rel: d for rel, d in files}
    checked = []
    if a.cyclonedx:
        with open(a.cyclonedx, encoding="utf-8") as f:
            bom = json.load(f)
        if bom.get("bomFormat") != "CycloneDX" or bom.get("specVersion") != "1.6":
            raise Fail("not a CycloneDX 1.6 document")
        c = bom["metadata"]["component"]
        if c.get("version") != version:
            raise Fail(f"CycloneDX describes version {c.get('version')}, archive is {version}")
        got = {h["alg"]: h["content"] for h in c.get("hashes", [])}
        for alg in ("SHA-256", "SHA-512"):
            if got.get(alg) != arch[alg]:
                raise Fail(f"CycloneDX {alg} of the archive does not match")
        listed = {}
        for comp in bom.get("components", []):
            if comp.get("type") == "file":
                listed[comp["name"]] = {h["alg"]: h["content"] for h in comp["hashes"]}
        if set(listed) != set(want):
            raise Fail("CycloneDX file list differs from the archive: %s" % sorted(set(listed) ^ set(want))[:5])
        for rel, d in want.items():
            if listed[rel].get("SHA-256") != d["SHA-256"]:
                raise Fail(f"CycloneDX hash of {rel} does not match")
        checked.append("CycloneDX")
    if a.spdx:
        with open(a.spdx, encoding="utf-8") as f:
            doc = json.load(f)
        if doc.get("spdxVersion") != "SPDX-2.3":
            raise Fail("not an SPDX 2.3 document")
        p = doc["packages"][0]
        if p.get("versionInfo") != version:
            raise Fail(f"SPDX describes version {p.get('versionInfo')}, archive is {version}")
        got = {c["algorithm"]: c["checksumValue"] for c in p.get("checksums", [])}
        if got.get("SHA256") != arch["SHA-256"] or got.get("SHA512") != arch["SHA-512"]:
            raise Fail("SPDX checksum of the archive does not match")
        listed = {}
        for fe in doc.get("files", []):
            listed[fe["fileName"][2:]] = {c["algorithm"]: c["checksumValue"] for c in fe["checksums"]}
        if set(listed) != set(want):
            raise Fail("SPDX file list differs from the archive: %s" % sorted(set(listed) ^ set(want))[:5])
        for rel, d in want.items():
            if listed[rel].get("SHA256") != d["SHA-256"]:
                raise Fail(f"SPDX hash of {rel} does not match")
        verification = hashlib.sha1("".join(sorted(d["SHA-1"] for d in want.values())).encode()).hexdigest()
        if p["packageVerificationCode"]["packageVerificationCodeValue"] != verification:
            raise Fail("SPDX package verification code does not match")
        checked.append("SPDX")
    if not checked:
        raise Fail("nothing to check: give --cyclonedx and/or --spdx")
    print(f"sbom: {' and '.join(checked)} match capstan-{version}.tar.gz ({len(want)} files)")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--archive", required=True)
    g.add_argument("--commit", required=True)
    g.add_argument("--timestamp", type=int, help="seconds since the epoch (default: SOURCE_DATE_EPOCH, else the commit time)")
    g.add_argument("--cyclonedx")
    g.add_argument("--spdx")
    c = sub.add_parser("check")
    c.add_argument("--archive", required=True)
    c.add_argument("--cyclonedx")
    c.add_argument("--spdx")
    a = ap.parse_args(argv)
    try:
        (generate if a.cmd == "generate" else check)(a)
    except (Fail, OSError, KeyError, ValueError, tarfile.TarError) as e:
        print(f"sbom: {e.__class__.__name__ + ': ' if not isinstance(e, Fail) else ''}{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
