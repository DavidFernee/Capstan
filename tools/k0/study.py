"""K0: how much of the Linux kernel's CVE stream would Capstan have prevented?

Usage:
    python3 tools/k0/study.py CVELIST_DIR [--year 2025]

CVELIST_DIR is a checkout of https://github.com/CVEProject/cvelistV5 (a sparse checkout of the
cves/<year> and cves/<year-1> folders is enough). The study takes every CVE published in the
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from classify import RULES, classify  # noqa: E402

COMPILE, RUNTIME, LOGIC, OUTSIDE, UNKNOWN = (
    "Prevented at compile time", "Stopped safely at run time", "Logic error: beyond any language",
    "Outside Capstan's current reach", "Not determinable from the record")
BUCKETS = [COMPILE, RUNTIME, LOGIC, OUTSIDE, UNKNOWN]

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
    "resource leak": (COMPILE, "K1.1 linear resources"),
    "improper locking": (COMPILE, "K1.2 guarded data, RCU type; K1.3 contexts"),
    "deadlock": (COMPILE, "K1.4 lock levels (dynamic orders: safe stop)"),
    "type confusion": (COMPILE, "K1.6 typed views"),
    "missing authorisation": (COMPILE, "K1.7 entry points declare policy"),
}
# Races split: a race on shared data is a data race, which K1.2 rejects; a race between a device's
# teardown and its callbacks is what K1.5 rules out. Races in ordering logic beyond these stay logic.
DATA_RACE = re.compile(r"data-race|kcsan|read_once|write_once|without (holding |taking )?(the )?\\w* ?lock|"
                       r"(missing|no|under|outside( of)?) (the )?\\w* ?(lock|rcu)|concurrent(ly)? (access|modif|updat|writ)|"
                       r"\\b(unregist\\w*|remov(e|al|ing)|teardown|unbind|unload\\w*|detach\\w*)\\b", re.I)
# Hangs: only loops driven by data (corrupt images, packets, devices) are what K1.9's bounded loops
# turn into errors. A hang waiting on hardware or firmware stays a logic or platform fault.
DATA_LOOP = re.compile(r"infinite loop|endless loop|loops? forever|never (terminates|ends|exits)|"
                       r"corrupt|malformed|crafted|bogus|malicious|on-disk|fuzz|syzbot|syzkaller|image", re.I)


def projected(r):
    if r["bucket"] in (COMPILE, RUNTIME, UNKNOWN):
        return r["bucket"], ""
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
    rows = []
    for sub in (str(year - 1), str(year)):
        base = os.path.join(cvelist, "cves", sub)
        for d, _, files in os.walk(base):
            for f in files:
                if not f.endswith(".json"):
                    continue
                try:
                    j = json.load(open(os.path.join(d, f)))
                except (OSError, ValueError):
                    continue
                if not isinstance(j, dict):
                    continue
                meta = j.get("cveMetadata", {})
                if meta.get("assignerShortName") != "Linux" or meta.get("state") != "PUBLISHED":
                    continue
                if not meta.get("datePublished", "").startswith(str(year)):
                    continue
                cna = j["containers"]["cna"]
                desc = next((x["value"] for x in cna.get("descriptions", [])
                             if x.get("lang", "").startswith("en")), "")
                files_ = sorted({p for a in cna.get("affected", []) for p in a.get("programFiles", [])})
                rows.append({"id": meta["cveId"], "date": meta["datePublished"][:10],
                             "title": cna.get("title", ""), "desc": desc, "files": files_})
    rows.sort(key=lambda r: r["id"])
    return rows


def subsystem(files):
    if not files:
        return "unknown"
    top = files[0].split("/")
    if top[0] in ("drivers", "net", "fs", "arch", "sound") and len(top) > 2:
        return "/".join(top[:2])
    return top[0]


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
    cwe_of = {c: w for c, w, _ in RULES}
    by_id = {r["id"]: r for r in classified}
    total = same_class = same_outcome = 0
    prevented = {"classifier": 0, "labels": 0}
    misses = []
    for lab in csv.DictReader(open(path)):
        r = by_id.get(lab["id"])
        if not r:
            continue
        total += 1
        same_class += r["class"] == lab["class"]
        lab_bucket = bucket_for(cwe_of.get(lab["class"], ""), atlas)[0]
        same_outcome += r["bucket"] == lab_bucket
        prevented["classifier"] += r["bucket"] in (COMPILE, RUNTIME)
        prevented["labels"] += lab_bucket in (COMPILE, RUNTIME)
        if r["class"] != lab["class"]:
            misses.append((lab["id"], lab["class"], r["class"]))
    return total, same_class, same_outcome, misses, prevented


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    year = 2025
    if "--year" in args:
        year = int(args[args.index("--year") + 1])
    rows = load(args[0], year)
    try:
        snapshot = open(os.path.join(args[0], ".git", "HEAD")).read().strip()
        if snapshot.startswith("ref:"):
            snapshot = open(os.path.join(args[0], ".git", snapshot[5:])).read().strip()
    except OSError:
        snapshot = "unknown"
    atlas = atlas_verdicts()
    for r in rows:
        cls, cwe, ev = classify(r["title"], r["desc"])
        r["class"], r["cwe"], r["evidence"] = cls, cwe, ev
        r["bucket"], r["atlas"] = bucket_for(cwe, atlas)
        r["subsystem"] = subsystem(r["files"])
        r["projected"], r["via"] = projected(r)

    n = len(rows)
    by_bucket = collections.Counter(r["bucket"] for r in rows)
    by_class = collections.Counter((r["class"], r["cwe"], r["bucket"]) for r in rows)
    known = n - by_bucket[UNKNOWN]
    memory_classes = {"use-after-free", "double or invalid free", "out-of-bounds read",
                      "out-of-bounds write", "NULL dereference", "uninitialised memory"}
    mem = sum(1 for r in rows if r["class"] in memory_classes)

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", f"kernel-cves-{year}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "published", "subsystem", "class", "cwe", "outcome", "with_k1", "evidence", "title"])
        for r in rows:
            w.writerow([r["id"], r["date"], r["subsystem"], r["class"], r["cwe"], r["bucket"],
                        r["projected"], r["evidence"], r["title"]])

    proj = collections.Counter(r["projected"] for r in rows)
    proj_prevented = proj[COMPILE] + proj[RUNTIME]
    tuning = check_labels(rows, atlas, "labels.csv")
    heldout = check_labels(rows, atlas, "labels-heldout.csv")
    json.dump({"year": year, "total": n, "buckets": {b: by_bucket[b] for b in BUCKETS},
               "memory_safety": mem,
               "projected": {b: proj[b] for b in BUCKETS}, "heldout": heldout[:3] if heldout else None},
              open(os.path.join(HERE, "data", f"summary-{year}.json"), "w"), indent=1)

    out = []
    p = out.append
    p(f"# K0: Linux kernel CVEs of {year} against Capstan\n")
    p("Generated by `tools/k0/study.py` from the CVE List; do not edit by hand. The method, its limits and "
      "every rule are below, so the result can be checked and re-run each year "
      "([DESIGN-MAP.md](DESIGN-MAP.md), section 7, K0).\n")
    p("## Result\n")
    p(f"**{n:,} CVEs** published in {year} by the Linux kernel's CVE Numbering Authority.\n")
    p("| Outcome had the code been written in Capstan | CVEs | Share of all | Share of those classified |")
    p("|---|---|---|---|")
    for b in BUCKETS:
        share_known = pct(by_bucket[b], known) if b != UNKNOWN else ""
        p(f"| {b} | {by_bucket[b]:,} | {pct(by_bucket[b], n)} | {share_known} |")
    prevented = by_bucket[COMPILE] + by_bucket[RUNTIME]
    p("")
    p(f"- **{pct(prevented, known)} of the classified CVEs** ({prevented:,}) are weaknesses Capstan prevents today: "
      f"{pct(by_bucket[COMPILE], known)} refused by the compiler, {pct(by_bucket[RUNTIME], known)} stopped safely at run time.")
    p(f"- **{pct(mem, n)} of all CVEs** ({mem:,}) are memory-safety bugs: use-after-free, double free, "
      "out-of-bounds access, NULL dereference and uninitialised memory.")
    p(f"- **{pct(by_bucket[OUTSIDE], known)}** are outside Capstan's current reach, mostly concurrency and "
      "resource lifetime: the kernel-mode prerequisites in K1 are aimed at exactly these.")
    p(f"- **{pct(by_bucket[LOGIC], known)}** are logic errors that no programming language prevents.")
    p("")
    p("A safe stop in the kernel is still a crash (a denial of service), but not a corruption an attacker "
      "can turn into code execution or privilege escalation.\n")
    p("## By weakness class\n")
    p("| Class | CWE | CVEs | Share | Outcome | Atlas verdict |")
    p("|---|---|---|---|---|---|")
    for (cls, cwe, b), c in sorted(by_class.items(), key=lambda kv: -kv[1]):
        link = f"[{cwe}](https://cwe.mitre.org/data/definitions/{cwe[4:]}.html)" if cwe else ""
        verdict = bucket_for(cwe, atlas)[1]
        p(f"| {cls} | {link} | {c:,} | {pct(c, n)} | {b} | {verdict} |")
    p("")
    p("## Kernel adjustments to the atlas\n")
    p("The atlas judges Capstan as it is today, for application code. Where its verdict depends on a feature "
      "kernel code cannot use, or on a construct Capstan simply lacks, the study counts the class as outside "
      "Capstan's reach rather than prevented:\n")
    p("| CWE | Why the atlas verdict does not carry over to the kernel |")
    p("|---|---|")
    for cwe, why in KERNEL_OVERRIDES.items():
        p(f"| {cwe} | {why} |")
    p("")
    p("Use-after-free and double free are counted as prevented: Capstan has no `free()`, and the "
      "deterministic memory management planned for kernel code (K1) must keep that guarantee, as Rust's "
      "ownership does. Some of these use-after-frees begin as races (a work item running after its device "
      "is gone); the memory error is prevented, the race itself may remain a logic error.\n")
    p("## With the K1 design\n")
    p("The K1 items in [DESIGN-MAP.md](DESIGN-MAP.md) (section 7) are designed against the classes above that "
      "Capstan does not yet prevent. If they are built as designed, the same CVEs would come out as follows. "
      "This is a projection, not a measurement; K2 tests it on real kernel code.\n")
    p("| Outcome | Today | With K1 |")
    p("|---|---|---|")
    for b in BUCKETS[:4]:
        p(f"| {b} | {pct(by_bucket[b], known)} | {pct(proj[b], known)} |")
    p(f"| **Prevented** | **{pct(prevented, known)}** | **{pct(proj_prevented, known)}** |")
    p("")
    via = collections.Counter((r["class"], r["via"], r["projected"]) for r in rows if r["via"])
    p("| Class | CVEs | With K1 | Design item |")
    p("|---|---|---|---|")
    for (cls, v, b), c in sorted(via.items(), key=lambda kv: -kv[1]):
        p(f"| {cls} | {c:,} | {b} | {v} |")
    p("")
    p("Still not prevented after K1: races in ordering logic that are not data races or teardown races, "
      "insufficient validation (K1.9's declared formats make validation the default, but a wrong constraint "
      "is still a logic error), speculative execution beyond variant 1, and the CVEs whose records do not "
      "say what went wrong.\n")
    subs = collections.Counter(r["subsystem"] for r in rows if r["bucket"] in (COMPILE, RUNTIME))
    p("## Where the preventable CVEs are\n")
    p("Subsystems with the most CVEs Capstan would have prevented: candidates for K2.\n")
    p("| Subsystem | Preventable CVEs |")
    p("|---|---|")
    for s, c in subs.most_common(12):
        p(f"| `{s}` | {c} |")
    p("")
    p("## Method\n")
    p("1. **Data.** Every record in the [CVE List](https://github.com/CVEProject/cvelistV5) whose assigner is the "
      f"Linux kernel CNA and whose publication date falls in {year}. Rejected records are excluded. "
      f"Snapshot: commit `{snapshot[:12]}`.")
    p("2. **Classification.** The kernel CNA almost never assigns a CWE, so each CVE is classified from its "
      "description, which is the fix commit's message: its subject line, its text, and the sanitiser "
      "reports quoted in it (KASAN, UBSAN, KMSAN, KCSAN, lockdep, kmemleak). The rules are regular expressions "
      "in `tools/k0/classify.py`, tried in a fixed order. Memory-safety classes are tried first, so a race "
      "that ends in a use-after-free counts as a use-after-free: that is what a language has to stop.")
    p("3. **The atlas.** Each class's CWE is looked up in the [CWE atlas](CWE-ATLAS.md), taking its weakest "
      "verdict, then the kernel adjustments above are applied.")
    if heldout:
        t, c, o, _, pv = heldout
        p(f"4. **Check.** {t} CVEs drawn at random were labelled by reading each fix, before looking at the "
          f"classifier's answer (`tests/k0/labels-heldout.csv`). The classifier gives the same class for "
          f"{c} ({pct(c, t)}) and the same outcome for {o} ({pct(o, t)}). It counts {pv['classifier']} of the "
          f"{t} as prevented; the hand labels count {pv['labels']}"
          + (", so its errors do not inflate the headline." if pv["classifier"] <= pv["labels"]
             else ": treat the headline as an upper estimate."))
        if tuning:
            t2, c2, o2, _, _ = tuning
            p(f"   On the {t2}-CVE sample used while writing the rules (`tests/k0/labels.csv`) the figures are "
              f"{pct(c2, t2)} and {pct(o2, t2)}. Both samples were labelled by the AI assistant that wrote "
              "the classifier; independent relabelling is the next step.")
    p("")
    p("## Limits\n")
    p("- Classification is automatic. A description can mention a class it does not fix, and many state the "
      "symptom rather than the cause. The per-CVE table (`tools/k0/data/`) lets anyone check a row.")
    p("- A CVE is not an exploit: the kernel CNA assigns one to almost every fix that might matter. The study "
      "measures weakness classes, not attacks.")
    p("- \"Prevented\" means the weakness could not be written, not that the driver would have been bug-free: "
      "the same mistake in Capstan becomes a compile error or a safe stop, and the programmer must still fix it.")
    p("- Kernel-mode Capstan (K1) does not exist yet. These are the classes its rules must cover, measured "
      "against the language as it stands.")
    p("")
    open(os.path.join(ROOT, "docs", "K0-KERNEL-CVES.md"), "w").write("\n".join(out))

    print(f"{n} CVEs; " + "; ".join(f"{b}: {by_bucket[b]}" for b in BUCKETS))
    print(f"prevented today {pct(prevented, known)}, with K1 {pct(proj_prevented, known)}")
    for name, lab in (("tuning", tuning), ("held-out", heldout)):
        if lab:
            print(f"{name}: class {lab[1]}/{lab[0]}, outcome {lab[2]}/{lab[0]}")
            for m in lab[3]:
                print("  mismatch", *m)


if __name__ == "__main__":
    main()
