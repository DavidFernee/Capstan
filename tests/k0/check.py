#!/usr/bin/env python3
"""Focused regression checks for the K0 population loader and kernel projection."""
import importlib.util
import json
import os
import pathlib
import sys
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "k0"))
spec = importlib.util.spec_from_file_location("k0_study", ROOT / "tools" / "k0" / "study.py")
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def record(cve_id, published, assigner="Linux", state="PUBLISHED"):
    return {
        "cveMetadata": {
            "cveId": cve_id, "datePublished": published,
            "assignerShortName": assigner, "state": state,
        },
        "containers": {"cna": {
            "title": "Kernel test record",
            "descriptions": [{"lang": "en", "value": "A test description"}],
            "affected": [{"programFiles": ["drivers/net/test.c"]}],
        }},
    }


def put(root, identifier_year, cve_id, value):
    directory = root / "cves" / str(identifier_year) / (cve_id.split("-")[2][:-3] + "xxx")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / (cve_id + ".json")).write_text(json.dumps(value), encoding="utf-8")


with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    for y in range(1999, 2026):
        (root / "cves" / str(y)).mkdir(parents=True)
    put(root, 2023, "CVE-2023-54098", record("CVE-2023-54098", "2025-12-24"))
    put(root, 2025, "CVE-2025-10001", record("CVE-2025-10001", "2025-03-01"))
    put(root, 2025, "CVE-2025-0001", record("CVE-2025-0001", "2025-03-02"))
    put(root, 2025, "CVE-2025-10002", record("CVE-2025-10002", "2025-03-01", "Other"))
    rows = study.load(str(root), 2025)
    ids = {row["id"] for row in rows}
    assert ids == {"CVE-2023-54098", "CVE-2025-10001", "CVE-2025-0001"}, ids
    delayed = next(row for row in rows if row["id"] == "CVE-2023-54098")
    assert delayed["date"] == "2025-12-24"

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    for y in range(1999, 2026):
        (root / "cves" / str(y)).mkdir(parents=True)
    (root / "cves" / "archive").mkdir()
    try:
        study.load(str(root), 2025)
    except RuntimeError as error:
        assert "unexpected non-year directories" in str(error)
    else:
        raise AssertionError("non-year CVE directory was silently ignored")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    for y in range(1999, 2026):
        if y != 2024:
            (root / "cves" / str(y)).mkdir(parents=True)
    try:
        study.load(str(root), 2025)
    except RuntimeError as error:
        assert "missing identifier-year directories" in str(error)
    else:
        raise AssertionError("incomplete identifier-year checkout was accepted")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    for y in range(1999, 2026):
        (root / "cves" / str(y)).mkdir(parents=True)
    put(root, 2025, "CVE-2025-10003", {"cveMetadata": {
        "cveId": "CVE-2025-10003", "datePublished": "2025-03-01",
        "assignerShortName": "Linux", "state": "PUBLISHED"}})
    path = root / "cves" / "2025" / "10xxx" / "CVE-2025-10003.json"
    path.write_text("{broken", encoding="utf-8")
    try:
        study.load(str(root), 2025)
    except RuntimeError as error:
        assert "cannot read CVE record" in str(error)
    else:
        raise AssertionError("malformed Linux CVE record was silently skipped")

with tempfile.TemporaryDirectory() as temporary:
    root = pathlib.Path(temporary)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "k0-test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "K0 test"], check=True)
    (root / "snapshot.txt").write_text("pinned source", encoding="utf-8")
    tracked_record = root / "cves" / "1999" / "0xxx" / "CVE-1999-0001.json"
    tracked_record.parent.mkdir(parents=True)
    tracked_record.write_text("{}", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "snapshot.txt", "cves"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)
    commit = study.source_snapshot(str(root))
    assert study.study_snapshot(str(root)) == commit
    assert len(commit) == 40 and all(ch in "0123456789abcdef" for ch in commit)
    # A sparse checkout can hide tracked files from status while leaving the tree clean.
    subprocess.run(["git", "-C", str(root), "update-index", "--skip-worktree",
                    "cves/1999/0xxx/CVE-1999-0001.json"], check=True)
    tracked_record.unlink()
    try:
        study.source_snapshot(str(root))
    except RuntimeError as error:
        assert "incomplete" in str(error)
    else:
        raise AssertionError("sparse CVE source snapshot was accepted")
    tracked_record.write_text("{}", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "update-index", "--no-skip-worktree",
                    "cves/1999/0xxx/CVE-1999-0001.json"], check=True)
    (root / "untracked.json").write_text("{}", encoding="utf-8")
    try:
        study.study_snapshot(str(root))
    except RuntimeError as error:
        assert "dirty" in str(error)
    else:
        raise AssertionError("dirty Capstan study source was accepted")
    try:
        study.source_snapshot(str(root))
    except RuntimeError as error:
        assert "dirty" in str(error)
    else:
        raise AssertionError("dirty CVE source snapshot was accepted")

# Review labels must be unique, belong to the exact source population and use known classes.
with tempfile.TemporaryDirectory() as temporary:
    path = pathlib.Path(temporary) / "reviewed.csv"
    population = [{"id": "CVE-2025-10001"}]
    path.write_text("id,class\\nCVE-2025-10001,use-after-free\\n", encoding="utf-8")
    assert study.load_reviewed(population, str(path)) == {"CVE-2025-10001": "use-after-free"}
    path.write_text("id,class\\nCVE-2025-10001,use-after-free\\nCVE-2025-10001,logic error\\n",
                    encoding="utf-8")
    try:
        study.load_reviewed(population, str(path))
    except RuntimeError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate review labels were accepted")
    path.write_text("id,class\\nCVE-2024-10001,use-after-free\\n", encoding="utf-8")
    try:
        study.load_reviewed(population, str(path))
    except RuntimeError as error:
        assert "absent from the source population" in str(error)
    else:
        raise AssertionError("stale review label was accepted")
    path.write_text("id,class\\nCVE-2025-10001,not-a-real-class\\n", encoding="utf-8")
    try:
        study.load_reviewed(population, str(path))
    except RuntimeError as error:
        assert "unknown review class" in str(error)
    else:
        raise AssertionError("unknown review class was accepted")

# The checked-in tuning and held-out samples cover the 2025 publication population only.
assert study.sample_agreements([], {}, 2024) == (None, None)

# The tuning and held-out label checker must reject duplicate and stale IDs.
original_root = study.ROOT
with tempfile.TemporaryDirectory() as temporary:
    study.ROOT = temporary
    label_dir = pathlib.Path(temporary) / "tests" / "k0"
    label_dir.mkdir(parents=True)
    label_path = label_dir / "labels.csv"
    label_path.write_text("id,class\\nCVE-2025-10001,use-after-free\\n"
                          "CVE-2025-10001,logic error\\n", encoding="utf-8")
    try:
        study.check_labels([], {}, "labels.csv")
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate tuning labels were accepted")
    label_path.write_text("id,class\\nCVE-2024-10001,use-after-free\\n", encoding="utf-8")
    try:
        study.check_labels([], {}, "labels.csv")
    except ValueError as error:
        assert "absent from the source population" in str(error)
    else:
        raise AssertionError("stale tuning label was accepted")
    label_path.write_text("id,class\\nCVE-2025-10001,not-a-real-class\\n", encoding="utf-8")
    try:
        study.check_labels([{"id": "CVE-2025-10001"}], {}, "labels.csv")
    except ValueError as error:
        assert "unknown classes" in str(error)
    else:
        raise AssertionError("unknown tuning class was accepted")
study.ROOT = original_root

# Memory-safety consequences must outrank non-memory causes across title/body fields.
cls, cwe, evidence = study.classify(
    "integer overflow in packet length",
    "The bug permits a use-after-free when the device is removed.",
)
assert cls == "use-after-free", (cls, cwe, evidence)
cls, cwe, evidence = study.classify(
    "integer overflow in packet length",
    "The invalid pointer causes a NULL pointer dereference.",
)
assert cls == "NULL dereference", (cls, cwe, evidence)

for phrase in (
    "device unregistration races with ethtool",
    "race during device removal",
    "driver unload while callback is running",
    "teardown concurrent with callback",
    "KCSAN data-race report",
):
    assert study.DATA_RACE.search(phrase), phrase
for phrase in ("unregistered user account", "removed documentation paragraph"):
    assert not study.DATA_RACE.search(phrase), phrase

for cls in ("use-after-free", "double or invalid free"):
    cwe = study.CLASS_CWE[cls]
    bucket, _ = study.bucket_for(cwe, {})
    assert bucket == study.OUTSIDE, (cls, bucket)
    row = {"bucket": bucket, "class": cls, "title": "", "desc": ""}
    projected, via = study.projected(row)
    assert projected == study.COMPILE and "K1.1" in via, (cls, projected, via)

candidate, via = study.proof_eligible({
    "projected": study.LOGIC, "class": "logic error", "via": "",
})
assert candidate == study.PROOF_ELIGIBLE
assert "no proof established" in via
assert "not proven" in study.PROOF_ELIGIBLE

print("K0 population, snapshot completeness, proof-eligibility, race-pattern and kernel-memory projection checks passed")
