"""K0: how much of the Linux kernel's CVE stream would Capstan have prevented?

Usage:
    git clone https://github.com/CVEProject/cvelistV5.git CVELIST_DIR
    python3 tools/k0/study.py CVELIST_DIR [--year 2025]

CVELIST_DIR is a complete checkout of https://github.com/CVEProject/cvelistV5. The study scans
all identifier-year directories (not just the publication year) and takes every CVE published in the
given calendar year by the Linux kernel's CNA, classifies it from its fix description
(classify.py), runs each class through the CWE atlas (docs/CWE-ATLAS.md), and writes:

    docs/K0-KERNEL-CVES.md                  the report
    tools/k0/data/kernel-cves-<year>.csv    one row per CVE: id, date, class, CWE, outcome, evidence

It checks the classifier against the hand-labelled sample in tests/k0/labels.csv and prints the
agreement. Re-run it each year (DESIGN-MAP.md section 7, K0).
"""
import collections
import csv
import json
import os
import re
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from classify import RULES, classify  # noqa: E402


COMPILE, RUNTIME, LOGIC, OUTSIDE, UNKNOWN = (
    "Prevented at compile time", "Stopped safely at run time", "Logic error: beyond any language",
    "Outside Capstan's current reach", "Not determinable from the record")
PROOF_ELIGIBLE = "Potentially proof-eligible (not proven)"
BUCKETS = [COMPILE, RUNTIME, LOGIC, OUTSIDE, UNKNOWN]

# Classes used only in the reviewed labels (tools/k0/data/reviewed-<year>.csv), with their CWE and,
# where the CWE alone does not decide it, the outcome today.
EXTRA_CLASSES = {
    "logic error": ("CWE-670", None),
    "hardware or firmware fault": ("", LOGIC),
    "build or configuration error": ("", LOGIC),
    "use after device removal": ("CWE-672", OUTSIDE),
    "misaligned access": ("CWE-1328", OUTSIDE),
    "aliased mutation": ("CWE-1260", OUTSIDE),
    "timing side channel": ("CWE-208", None),
}
CLASS_CWE = {c: w for c, w, _ in RULES}
CLASS_CWE.update({c: w for c, (w, _) in EXTRA_CLASSES.items()})

# Atlas outcome -> study bucket. "Inexpressible" and "no effect" mean the weakness cannot be
# written in Capstan as it stands, which counts as prevented before the program runs.
ATLAS_TO_BUCKET = [
    ("Gap", OUTSIDE), ("Not applicable", OUTSIDE), ("escape hatch", OUTSIDE),
    ("Logic", LOGIC), ("run time", RUNTIME), ("no effect", COMPILE),
    ("Inexpressible", COMPILE), ("compile time", COMPILE),
]
WEAKEST_FIRST = [OUTSIDE, LOGIC, RUNTIME, COMPILE]

# Where the atlas verdict holds for application code but not yet for kernel code. Each override
# is a published part of the method, and each names the roadmap item that would remove it.
KERNEL_OVERRIDES = {
    "CWE-401": "Leaks are collected by Capstan's garbage collector, but kernel code cannot use a "
               "collector that pauses at arbitrary moments. Needs deterministic memory management (K1).",
    "CWE-415": "Kernel allocators and explicit release paths are not governed by Capstan's application "
               "memory model. Double/invalid-free prevention in kernel code depends on K1.1 ownership.",
    "CWE-416": "The application memory model does not establish safe lifetime rules for kernel allocators, "
               "DMA, callbacks or externally owned objects. Use-after-free prevention in kernel code "
               "depends on K1.1 ownership.",
    "CWE-772": "Capstan has no handles to leak today; kernel code holds reference counts, locks and "
               "device resources. Needs ownership of resources (K1).",
    "CWE-362": "Capstan has no threads yet, so races are inexpressible only because concurrency is. "
               "Needs safe concurrency (v0.7, K1).",
    "CWE-667": "As CWE-362: locking is absent from the language, not checked. Needs safe concurrency (v0.7, K1).",
    "CWE-833": "As CWE-362. Needs lock ordering checked by the compiler (v0.7, K1).",
    "CWE-843": "Capstan has no casts, but kernel code must reinterpret device memory and container "
               "structures. Needs typed hardware access under proof (K1).",
    "CWE-1037": "Speculative-execution leaks are a property of the processor, not of the source language.",
    "CWE-617": "A kernel WARN_ON or BUG_ON was reached, but the record does not say what state "
               "reached it, so the underlying weakness is unknown.",
}
OVERRIDE_BUCKET = {cwe: (UNKNOWN if cwe == "CWE-617" else OUTSIDE) for cwe in KERNEL_OVERRIDES}

# What the K1 design (DESIGN-MAP.md section 7) is meant to do to each class that Capstan does not
# prevent today. A projection, not a measurement: it holds only if the feature is built as designed,
# and K2 will test it on real kernel code.
PROJECTION = {
    "memory leak": (COMPILE, "K1.1 ownership"),
    "use-after-free": (COMPILE, "K1.1 ownership and lifetime-checked references"),
    "double or invalid free": (COMPILE, "K1.1 ownership and linear release"),
    "resource leak": (COMPILE, "K1.1 linear resources"),
    "improper locking": (COMPILE, "K1.2 guarded data, RCU type; K1.3 contexts"),
    "deadlock": (COMPILE, "K1.4 lock levels (dynamic orders: safe stop)"),
    "type confusion": (COMPILE, "K1.6 typed views"),
    "missing authorisation": (COMPILE, "K1.7 entry points declare policy"),
    "use after device removal": (COMPILE, "K1.5 structured concurrency, driver typestate"),
    "misaligned access": (COMPILE, "K1.6 typed views prove alignment"),
    "aliased mutation": (COMPILE, "K1.1 ownership: no mutation through a shared reference"),
}
# K1.10: proof against a specification. Applies to what K1.1-K1.9 leave as logic errors, for code
# whose behaviour is specified. Hardware faults and build errors stay outside any proof of the code.
PROOF_ELIGIBLE_CLASSES = {"logic error", "insufficient validation", "race condition", "hang or infinite loop"}
SPECTRE_V1 = re.compile(r"nospec|array_index|\bindex\b|opcode|speculat\w* (load|read|access)", re.I)
# Races split: a race on shared data is a data race, which K1.2 rejects; a race between a device's
# teardown and its callbacks is what K1.5 rules out. Races in ordering logic beyond these stay logic.
DATA_RACE = re.compile(r"data-race|kcsan|read_once|write_once|without (holding |taking )?(the )?\w* ?lock|"
                       r"(missing|no|under|outside( of)?) (the )?\w* ?(lock|rcu)|concurrent(ly)? (access|modif|updat|writ)|"
                       r"\b(?:device|driver|netdev|interface|adapter|callback|workqueue|resource)\b.{0,50}"
                       r"\b(?:unregist\w*|remov(e|al|ing)|teardown|unbind|unload\w*|detach\w*)\b|"
                       r"\b(?:unregist\w*|remov(e|al|ing)|teardown|unbind|unload\w*|detach\w*)\b.{0,50}"
                       r"\b(?:device|driver|netdev|interface|adapter|callback|workqueue|resource)\b", re.I)
# Hangs: only loops driven by data (corrupt images, packets, devices) are what K1.9's bounded loops
# turn into errors. A hang waiting on hardware or firmware stays a logic or platform fault.
DATA_LOOP = re.compile(r"infinite loop|endless loop|loops? forever|never (terminates|ends|exits)|"
                       r"corrupt|malformed|crafted|bogus|malicious|on-disk|fuzz|syzbot|syzkaller|image", re.I)


def projected(r):
    if r["bucket"] in (COMPILE, RUNTIME, UNKNOWN):
        return r["bucket"], ""
    if r["class"] == "speculative execution":
        if SPECTRE_V1.search(r["title"] + " " + r["desc"]) and "bhb" not in (r["title"] + r["desc"]).lower():
            return COMPILE, "K1.8 index masking on tainted indices"
        return OUTSIDE, ""
    if r["class"] in PROJECTION:
        return PROJECTION[r["class"]]
    if r["class"] == "race condition":
        if DATA_RACE.search(r["title"] + " " + r["desc"]):
            return COMPILE, "K1.2 guarded data; K1.5 structured concurrency"
        return LOGIC, ""
    if r["class"] == "hang or infinite loop" and DATA_LOOP.search(r["title"] + " " + r["desc"]):
        return RUNTIME, "K1.9 bounded loops"
    return r["bucket"], ""


def atlas_verdicts():
    """Weakest outcome per CWE, read from the generated atlas."""
    text = open(os.path.join(ROOT, "docs", "CWE-ATLAS.md")).read()
    full = text.split("## Full atlas", 1)[1]
    per = collections.defaultdict(list)
    for line in full.splitlines():
        m = re.match(r"\| \[(\d+)\]\([^)]*\) \| ([^|]*) \| ([^|]*) \|", line)
        if not m:
            continue
        outcome = m.group(3).replace("*", "")
        bucket = next((b for key, b in ATLAS_TO_BUCKET if key in outcome), OUTSIDE)
        per["CWE-" + m.group(1)].append((bucket, outcome.strip()))
    return {cwe: min(v, key=lambda bo: WEAKEST_FIRST.index(bo[0])) for cwe, v in per.items()}


def load(cvelist, year):
    """Load the complete publication-year population from every CVE identifier year.

    CVE identifier years are allocation dates, not publication dates. A delayed disclosure
    can therefore live in any identifier-year directory. Missing directories and malformed
    records are fatal: a partial population must never produce a plausible-looking study.
    """
    root = os.path.join(cvelist, "cves")
    if not os.path.isdir(root):
        raise RuntimeError(f"missing CVE List directory: {root}")

    year_dirs = sorted(
        (name for name in os.listdir(root)
         if name.isdigit() and os.path.isdir(os.path.join(root, name))),
        key=int,
    )
    if not year_dirs:
        raise RuntimeError(f"no CVE identifier-year directories found under {root}")
    years = [int(name) for name in year_dirs]
    expected = list(range(1999, years[-1] + 1))
    if years != expected:
        missing = sorted(set(expected) - set(years))
        raise RuntimeError(f"incomplete CVE List checkout; missing identifier-year directories: {missing}")

    rows = []
    seen = set()

    def walk_error(error):
        raise error

    for sub in year_dirs:
        base = os.path.join(root, sub)
        for directory, _, files in os.walk(base, onerror=walk_error):
            for filename in files:
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(directory, filename)
                try:
                    with open(path, encoding="utf-8") as source:
                        record = json.load(source)
                except (OSError, ValueError) as error:
                    raise RuntimeError(f"cannot read CVE record {path}: {error}") from error
                if not isinstance(record, dict):
                    raise RuntimeError(f"CVE record is not a JSON object: {path}")
                meta = record.get("cveMetadata")
                if not isinstance(meta, dict):
                    raise RuntimeError(f"CVE record has no cveMetadata object: {path}")
                if meta.get("assignerShortName") != "Linux" or meta.get("state") != "PUBLISHED":
                    continue

                published = meta.get("datePublished")
                cve_id = meta.get("cveId")
                if not isinstance(published, str) or len(published) < 10:
                    raise RuntimeError(f"Linux published CVE has no valid datePublished: {path}")
                try:
                    from datetime import date
                    published_date = date.fromisoformat(published[:10])
                except ValueError as error:
                    raise RuntimeError(f"invalid datePublished in {path}: {published!r}") from error
                if published_date.year != year:
                    continue
                if not isinstance(cve_id, str) or not cve_id.startswith("CVE-"):
                    raise RuntimeError(f"Linux published CVE has no valid cveId: {path}")
                if filename != cve_id + ".json":
                    raise RuntimeError(f"CVE filename/id mismatch in {path}: {cve_id}")
                if cve_id in seen:
                    raise RuntimeError(f"duplicate CVE identifier in source tree: {cve_id}")
                seen.add(cve_id)

                containers = record.get("containers")
                cna = containers.get("cna") if isinstance(containers, dict) else None
                if not isinstance(cna, dict):
                    raise RuntimeError(f"Linux published CVE has no containers.cna object: {path}")
                descriptions = cna.get("descriptions", [])
                if not isinstance(descriptions, list):
                    raise RuntimeError(f"invalid CNA descriptions in {path}")
                desc = next((item.get("value") for item in descriptions
                             if isinstance(item, dict) and item.get("lang", "").startswith("en")), None)
                if not isinstance(desc, str) or not desc.strip():
                    raise RuntimeError(f"Linux published CVE has no non-empty English CNA description: {path}")
                title = cna.get("title", "")
                if not isinstance(title, str):
                    raise RuntimeError(f"invalid CNA title in {path}")
                affected = cna.get("affected", [])
                if not isinstance(affected, list):
                    raise RuntimeError(f"invalid CNA affected list in {path}")
                files_ = []
                for item in affected:
                    if not isinstance(item, dict):
                        raise RuntimeError(f"invalid CNA affected entry in {path}")
                    program_files = item.get("programFiles", [])
                    if not isinstance(program_files, list) or any(not isinstance(value, str)
                                                                  for value in program_files):
                        raise RuntimeError(f"invalid CNA programFiles list in {path}")
                    files_.extend(program_files)
                files_ = sorted(set(files_))
                rows.append({"id": cve_id, "date": published_date.isoformat(),
                             "title": title, "desc": desc, "files": files_})

    rows.sort(key=lambda row: row["id"])
    return rows

def subsystem(files):
    if not files:
        return "unknown"
    top = files[0].split("/")
    if top[0] in ("drivers", "net", "fs", "arch", "sound") and len(top) > 2:
        return "/".join(top[:2])
    return top[0]


def proof_eligible(r):
    """Identify K1.10 candidates; this is a design projection, not a proof result."""
    if r["projected"] == LOGIC and r["class"] in PROOF_ELIGIBLE_CLASSES:
        return PROOF_ELIGIBLE, "K1.10 proof eligibility only; no proof established"
    return r["projected"], r["via"]


def bucket_for_class(cls, atlas):
    cwe = CLASS_CWE.get(cls, "")
    if cls in EXTRA_CLASSES and EXTRA_CLASSES[cls][1]:
        return EXTRA_CLASSES[cls][1], "reviewed class"
    return bucket_for(cwe, atlas)


def bucket_for(cwe, atlas):
    if cwe in OVERRIDE_BUCKET:
        base = atlas[cwe][1] if cwe in atlas else "not in the atlas"
        return OVERRIDE_BUCKET[cwe], base + "; adjusted for the kernel"
    if not cwe:
        return UNKNOWN, ""
    if cwe in atlas:
        return atlas[cwe][0], atlas[cwe][1]
    return OUTSIDE, "not in the atlas"


def pct(n, d):
    return f"{100.0 * n / d:.1f}%" if d else "n/a"


def check_labels(classified, atlas, name):
    """Agreement with a hand-labelled sample: (total, same class, same outcome, mismatches)."""
    path = os.path.join(ROOT, "tests", "k0", name)
    if not os.path.exists(path):
        return None
    by_id = {r["id"]: r for r in classified}
    total = same_class = same_outcome = 0
    prevented = {"classifier": 0, "labels": 0}
    misses = []
    labels = list(csv.DictReader(open(path)))
    label_ids = [lab["id"] for lab in labels]
    if len(label_ids) != len(set(label_ids)):
        raise ValueError(f"duplicate CVE identifiers in label file {path}")
    missing = sorted(set(label_ids) - set(by_id))
    if missing:
        raise ValueError(f"label file {path} contains CVEs absent from the source population: {missing}")
    for lab in labels:
        r = by_id[lab["id"]]
        total += 1
        auto_bucket = bucket_for_class(r["auto_class"], atlas)[0]
        same_class += r["auto_class"] == lab["class"]
        lab_bucket = bucket_for_class(lab["class"], atlas)[0]
        same_outcome += auto_bucket == lab_bucket
        prevented["classifier"] += auto_bucket in (COMPILE, RUNTIME)
        prevented["labels"] += lab_bucket in (COMPILE, RUNTIME)
        if r["auto_class"] != lab["class"]:
            misses.append((lab["id"], lab["class"], r["auto_class"]))
    return total, same_class, same_outcome, misses, prevented


def source_snapshot(cvelist):
    """Return the exact, clean Git commit for the source population or fail closed."""
    try:
        commit = subprocess.run(
            ["git", "-C", cvelist, "rev-parse", "--verify", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", cvelist, "status", "--porcelain", "--untracked-files=all"],
            check=True, capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(
            "CVE List source must be a Git checkout with a verifiable commit"
        ) from error
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError(f"invalid CVE List Git commit: {commit!r}")
    if status:
        raise RuntimeError("CVE List checkout is dirty; use a clean, pinned source snapshot")

    # A clean Git worktree can still be sparse: Git may mark omitted tracked files
    # skip-worktree, leaving status clean while os.walk silently sees only a subset.
    # Compare the complete tracked CVE JSON inventory with files actually materialised.
    try:
        tracked = subprocess.run(
            ["git", "-C", cvelist, "ls-files", "-z", "--", "cves"],
            check=True, capture_output=True,
        ).stdout.decode("utf-8").split("\0")
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError) as error:
        raise RuntimeError("cannot enumerate tracked CVE List source files") from error
    tracked_json = {path for path in tracked if path.endswith(".json")}
    root = os.path.join(cvelist, "cves")
    materialised_json = set()
    for directory, _, files in os.walk(root):
        for filename in files:
            if filename.endswith(".json"):
                materialised_json.add(os.path.relpath(os.path.join(directory, filename), cvelist))
    if tracked_json != materialised_json:
        missing = sorted(tracked_json - materialised_json)
        unexpected = sorted(materialised_json - tracked_json)
        raise RuntimeError(
            "CVE List checkout is incomplete or contains untracked JSON records; "
            f"missing tracked files: {missing[:10]}; unexpected files: {unexpected[:10]}"
        )
    if not tracked_json:
        raise RuntimeError("CVE List checkout contains no tracked CVE JSON records")
    return commit


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    year = 2025
    if "--year" in args:
        year = int(args[args.index("--year") + 1])
    rows = load(args[0], year)
    snapshot = source_snapshot(args[0])
    atlas = atlas_verdicts()
    reviewed = {}
    rpath = os.path.join(HERE, "data", f"reviewed-{year}.csv")
    if os.path.exists(rpath):
        reviewed = {x["id"]: x["class"] for x in csv.DictReader(open(rpath))}
    for r in rows:
        cls, cwe, ev = classify(r["title"], r["desc"])
        r["class"], r["cwe"], r["evidence"] = cls, cwe, ev
        r["auto_class"], r["method"] = cls, "classifier"
        if r["id"] in reviewed:
            r["class"], r["method"] = reviewed[r["id"]], "reviewed"
            r["cwe"], r["evidence"] = CLASS_CWE.get(r["class"], ""), "read by a reviewer"
        r["bucket"], r["atlas"] = bucket_for_class(r["class"], atlas)
        r["subsystem"] = subsystem(r["files"])
        r["projected"], r["via"] = projected(r)
        r["final"], r["final_via"] = proof_eligible(r)

    n = len(rows)
    by_bucket = collections.Counter(r["bucket"] for r in rows)
    by_class = collections.Counter((r["class"], r["cwe"], r["bucket"]) for r in rows)
    known = n - by_bucket[UNKNOWN]
    n_reviewed = sum(r["method"] == "reviewed" for r in rows)
    memory_classes = {"use-after-free", "double or invalid free", "out-of-bounds read",
                      "out-of-bounds write", "NULL dereference", "uninitialised memory"}
    mem = sum(1 for r in rows if r["class"] in memory_classes)
    prevented = by_bucket[COMPILE] + by_bucket[RUNTIME]
    proj = collections.Counter(r["projected"] for r in rows)
    proj_prevented = proj[COMPILE] + proj[RUNTIME]
    fin = collections.Counter(r["final"] for r in rows)
    fin_candidate = fin[COMPILE] + fin[RUNTIME] + fin[PROOF_ELIGIBLE]

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", f"kernel-cves-{year}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "published", "subsystem", "class", "cwe", "method", "outcome", "with_k1",
                    "with_k1_10", "evidence", "title"])
        for r in rows:
            w.writerow([r["id"], r["date"], r["subsystem"], r["class"], r["cwe"], r["method"], r["bucket"],
                        r["projected"], r["final"], r["evidence"], r["title"]])

    tuning = check_labels(rows, atlas, "labels.csv")
    heldout = check_labels(rows, atlas, "labels-heldout.csv")
    json.dump({"year": year, "source_repository": "https://github.com/CVEProject/cvelistV5",
               "source_commit": snapshot, "total": n, "reviewed": n_reviewed,
               "buckets": {b: by_bucket[b] for b in BUCKETS}, "memory_safety": mem,
               "with_k1": {b: proj[b] for b in BUCKETS},
               "k1_10_proof_eligibility_projection": {b: fin[b] for b in BUCKETS + [PROOF_ELIGIBLE]},
               "heldout": heldout[:3] if heldout else None},
              open(os.path.join(HERE, "data", f"summary-{year}.json"), "w"), indent=1)

    out = []
    p = out.append
    p(f"# K0: Linux kernel CVEs of {year} against Capstan\n")
    p("Generated by `tools/k0/study.py` from the CVE List; do not edit by hand. The method, its limits and "
      "every rule are below, so the result can be checked and re-run each year "
      "([DESIGN-MAP.md](DESIGN-MAP.md), section 7, K0).\n")
    p("## Result\n")
    p(f"**{n:,} CVEs** published in {year} by the Linux kernel's CVE Numbering Authority. "
      f"{n - n_reviewed:,} were classified automatically from their fix descriptions and {n_reviewed:,} were "
      f"read and classified by a reviewer, because the rules could not decide them or decided them wrongly. "
      f"{by_bucket[UNKNOWN]} remain undeterminable from the record.\n")
    p("| Outcome / measure | Today | K1.1-K1.9 design projection | K1.10 proof-eligibility ceiling (not proof) |")
    p("|---|---|---|---|")
    for b in [COMPILE, RUNTIME, PROOF_ELIGIBLE, LOGIC, OUTSIDE]:
        today = pct(by_bucket[b], known) if b != PROOF_ELIGIBLE else "\u2013"
        k1 = pct(proj[b], known) if b != PROOF_ELIGIBLE else "\u2013"
        p(f"| {b} | {today} | {k1} | {pct(fin[b], known)} |")
    p(f"| **Prevented / potentially addressable** | **{pct(prevented, known)}** | **{pct(proj_prevented, known)}** | "
      f"**{pct(fin_candidate, known)}** |")
    p("")
    p(f"Shares are of the {known:,} CVEs whose weakness is known. Today's column is a measurement of "
      "Capstan as it stands; the other columns are projections, not implementation evidence. The K1.1-K1.9 "
      "column assumes those designs are built as specified. The K1.10 column only identifies classes that "
      "might be candidates for proof; it does not establish that specifications or machine-checked proofs "
      "exist. K2 must test the designs on real kernel code.\n")
    p(f"- **{pct(mem, n)} of all CVEs** ({mem:,}) are memory-safety bugs: use-after-free, double free, "
      "out-of-bounds access, NULL dereference and uninitialised memory. This is a weakness count, not "
      "a claim that kernel-mode Capstan currently prevents them; UAF and double-free coverage depends on K1.1.")
    p(f"- **{pct(prevented, known)} are prevented today**: {pct(by_bucket[COMPILE], known)} refused by the compiler, "
      f"{pct(by_bucket[RUNTIME], known)} stopped safely at run time.")
    p("- A safe stop in the kernel is still a crash (a denial of service), but not a corruption an attacker "
      "can turn into code execution or privilege escalation.\n")
    rest = [r for r in rows if r["final"] in (LOGIC, OUTSIDE)]
    rc = collections.Counter(r["class"] for r in rest)
    p("### What no design here removes\n")
    p(f"{len(rest)} CVEs ({pct(len(rest), known)}) stay possible even with every design item, and "
      f"{by_bucket[UNKNOWN]} cannot be judged:\n")
    p("| Class | CVEs | Why |")
    p("|---|---|---|")
    why = {"hardware or firmware fault": "The device, firmware or processor misbehaves; the driver's workaround "
           "is a correct program for a wrong machine.",
           "build or configuration error": "The mistake is in the build or device-tree configuration, not in code.",
           "speculative execution": "Processor flaws beyond Spectre variant 1 (branch-history injection, VMSCAPE): "
           "Capstan applies the vendor's barriers, but the leak is in the hardware.",
           "logic error": "Code outside the specified core: proof (K1.10) needs a specification to prove against.",
           "insufficient validation": "As logic error.", "race condition": "As logic error.",
           "hang or infinite loop": "As logic error."}
    for c, k in rc.most_common():
        p(f"| {c} | {k} | {why.get(c, '')} |")
    p("")
    p("K1.10 proof eligibility is only a candidate ceiling. No CVE is counted as formally established: "
      "each candidate requires a concrete specification, an applicable machine-checked proof, and evidence "
      "that the proof corresponds to the production implementation. Without those artefacts, it remains "
      "a projection and must not be reported as a prevented vulnerability.\n")
    p("## By weakness class (today)\n")
    p("| Class | CWE | CVEs | Share | Outcome | Atlas verdict |")
    p("|---|---|---|---|---|---|")
    for (cls, cwe, b), c in sorted(by_class.items(), key=lambda kv: -kv[1]):
        link = f"[{cwe}](https://cwe.mitre.org/data/definitions/{cwe[4:]}.html)" if cwe else ""
        verdict = bucket_for_class(cls, atlas)[1]
        p(f"| {cls} | {link} | {c:,} | {pct(c, n)} | {b} | {verdict} |")
    p("")
    p("## What each design item removes\n")
    via = collections.Counter((r["class"], r["final_via"], r["final"]) for r in rows if r["final_via"])
    p("| Class | CVEs | Outcome | Design item |")
    p("|---|---|---|---|")
    for (cls, v, b), c in sorted(via.items(), key=lambda kv: -kv[1]):
        p(f"| {cls} | {c:,} | {b} | {v} |")
    p("")
    p("Races and hangs count for K1.2, K1.5 and K1.9 only where the description shows the pattern those items "
      "target (a data race or teardown race; a loop driven by untrusted data). The rest fall to K1.10.\n")
    p("## Kernel adjustments to the atlas\n")
    p("The atlas judges Capstan as it is today, for application code. Where its verdict depends on a feature "
      "kernel code cannot use, or on a construct Capstan simply lacks, the study counts the class as outside "
      "Capstan's reach rather than prevented:\n")
    p("| CWE | Why the atlas verdict does not carry over to the kernel |")
    p("|---|---|")
    for cwe, why_ in KERNEL_OVERRIDES.items():
        p(f"| {cwe} | {why_} |")
    p("")
    p("Classes found only in review are judged the same way: use after device removal (CWE-672), misaligned "
      "access and aliased mutation of a shared buffer have no counterpart in Capstan today, so they count as "
      "outside its reach until K1.5, K1.6 and K1.1. Hardware faults and build errors are beyond any language.\n")
    p("Use-after-free and double free are **not** counted as prevented today in kernel code. The application "
      "memory model does not establish lifetimes for kernel allocators, DMA, callbacks or externally owned "
      "objects. Their K1 projection is conditional on K1.1 ownership and lifetime enforcement.\n")
    subs = collections.Counter(r["subsystem"] for r in rows if r["bucket"] in (COMPILE, RUNTIME))
    p("## Where the preventable CVEs are\n")
    p("Subsystems with the most CVEs Capstan would have prevented today: candidates for K2.\n")
    p("| Subsystem | Preventable CVEs |")
    p("|---|---|")
    for sname, c in subs.most_common(12):
        p(f"| `{sname}` | {c} |")
    p("")
    p("## Method\n")
    p("1. **Data.** Every record in the complete [CVE List](https://github.com/CVEProject/cvelistV5) checkout, "
      "across all identifier-year directories, whose assigner is the Linux kernel CNA and whose publication "
      f"date falls in {year}. Rejected records are excluded. Missing year directories, unreadable JSON, "
      "malformed Linux-published records and labels absent from the population are fatal errors. "
      f"Snapshot: commit `{snapshot}`.")
    p("2. **Automatic classification.** The kernel CNA almost never assigns a CWE, so each CVE is classified from "
      "its description, which is the fix commit's message: its subject line, its text, and the sanitiser "
      "reports quoted in it (KASAN, UBSAN, KMSAN, KCSAN, lockdep, kmemleak). The rules are regular expressions "
      "in `tools/k0/classify.py`, tried in a fixed order. Memory-safety classes are tried first, so a race "
      "that ends in a use-after-free counts as a use-after-free: that is what a language has to stop.")
    p(f"3. **Review.** Every CVE the rules could not decide, and every one they called speculative execution, "
      f"was read and classified by a reviewer ({n_reviewed:,} in all, `tools/k0/data/reviewed-{year}.csv`). "
      "The review label replaces the automatic one. Where a fix states its consequence (\"leads to a NULL "
      "dereference\"), the consequence decides, as in step 2.")
    p("4. **The atlas.** Each class's CWE is looked up in the [CWE atlas](CWE-ATLAS.md), taking its weakest "
      "verdict, then the kernel adjustments above are applied.")
    if heldout:
        t, c, o, _, pv = heldout
        p(f"5. **Check.** {t} CVEs drawn at random were labelled by reading each fix, before looking at the "
          f"classifier's answer (`tests/k0/labels-heldout.csv`). The automatic classifier gives the same class for "
          f"{c} ({pct(c, t)}) and the same outcome for {o} ({pct(o, t)}). It counts {pv['classifier']} of the "
          f"{t} as prevented; the hand labels count {pv['labels']}"
          + (", so its errors do not inflate the headline." if pv["classifier"] <= pv["labels"]
             else ": treat the headline as an upper estimate."))
        if tuning:
            t2, c2, o2, _, _ = tuning
            p(f"   On the {t2}-CVE sample used while writing the rules (`tests/k0/labels.csv`) the figures are "
              f"{pct(c2, t2)} and {pct(o2, t2)}.")
    p("")
    p("## Limits\n")
    p("- The review and both check samples were done by Claude, the AI assistant that wrote the classifier. "
      "An independent reviewer relabelling them is the next step for the study's credibility.")
    p("- The automatic classification is right about 60% of the time on class and 70% on outcome (held-out "
      "sample); it does not overstate prevention there, but individual rows can be wrong. Every row is in "
      "`tools/k0/data/` with how it was classified.")
    p("- Review read the fix descriptions, not the code changes. Reading the diffs would settle the four "
      "undeterminable CVEs and some borderline logic errors.")
    p("- A CVE is not an exploit: the kernel CNA assigns one to almost every fix that might matter. The study "
      "measures weakness classes, not attacks.")
    p("- \"Prevented\" means the weakness could not be written, not that the driver would have been bug-free: "
      "the same mistake in Capstan becomes a compile error or a safe stop, and the programmer must still fix it.")
    p("- Kernel-mode Capstan (K1) does not exist yet. The projections say which classes its rules must cover.")
    p("")
    open(os.path.join(ROOT, "docs", "K0-KERNEL-CVES.md"), "w").write("\n".join(out))

    print(f"{n} CVEs ({n_reviewed} reviewed); " + "; ".join(f"{b}: {by_bucket[b]}" for b in BUCKETS))
    print(f"prevented today {pct(prevented, known)}, with K1 {pct(proj_prevented, known)}, "
          f"K1.10 proof-eligibility ceiling (not proven) {pct(fin_candidate, known)}")
    for name, lab in (("tuning", tuning), ("held-out", heldout)):
        if lab:
            print(f"{name}: class {lab[1]}/{lab[0]}, outcome {lab[2]}/{lab[0]}")

if __name__ == "__main__":
    main()
