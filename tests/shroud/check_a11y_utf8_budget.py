#!/usr/bin/env python3
"""Large-input allocation regression for Shroud's accessibility UTF-8 encoder.

Usage: python3 tests/shroud/check_a11y_utf8_budget.py CAPSTANC CC [CFLAGS...]
The test constrains and reports the Capstan managed heap, not process RSS.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIB = sorted(
    os.path.join("lib/shroud", name)
    for name in os.listdir(os.path.join(ROOT, "lib/shroud"))
    if name.endswith(".cap")
)


def run(argv, *, env=None, expected=0):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, env=env)
    if result.returncode != expected:
        raise SystemExit(
            f"a11y UTF-8 budget: {argv[0]!r} exited {result.returncode}, expected {expected}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    capstanc = os.path.abspath(sys.argv[1]) if os.path.exists(sys.argv[1]) else sys.argv[1]
    cc = sys.argv[2]
    cflags = sys.argv[3:]
    if not any(flag.startswith("-O") for flag in cflags):
        cflags = ["-O2"] + cflags

    source = """
int main() {
    List<int> cps = new List<int>();
    for (int i = 0; i < MAX_TEXT_BYTES; i += 1) { cps.push(0x41); }
    Tainted encoded = utf8_from_codepoints(cps);
    if (encoded.len() != MAX_TEXT_BYTES) { return 1; }
    if (encoded.at(0) != 0x41 || encoded.at(MAX_TEXT_BYTES - 1) != 0x41) { return 2; }
    println("a11y UTF-8 budget: 1 MiB ASCII encoded exactly");
    return 0;
}
"""
    with tempfile.TemporaryDirectory() as tmp:
        cap = os.path.join(tmp, "a11y-utf8-budget.cap")
        c_source = os.path.join(tmp, "a11y-utf8-budget.c")
        exe = os.path.join(tmp, "a11y-utf8-budget")
        with open(cap, "w", encoding="utf-8") as stream:
            stream.write(source)
        run([capstanc, "build", "--strict", "-o", c_source] + LIB + [cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), c_source, "-o", exe])

        env = os.environ.copy()
        env["CAPSTAN_MAX_HEAP"] = "64M"
        env["CAPSTAN_GC_STATS"] = "1"
        result = run([exe], env=env)
        if "1 MiB ASCII encoded exactly" not in result.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing result confirmation: {result.stdout!r}")
        match = re.search(r"peak_heap=(\d+)", result.stderr)
        if not match:
            raise SystemExit(f"a11y UTF-8 budget: collector peak heap not reported: {result.stderr!r}")
        peak = int(match.group(1))
        limit = 64 * 1024 * 1024
        if peak > limit:
            raise SystemExit(f"a11y UTF-8 budget: peak managed heap {peak} exceeds {limit}")

        over_source = """
int main() {
    List<int> cps = new List<int>();
    for (int i = 0; i < 262145; i += 1) { cps.push(0x1F600); }
    utf8_from_codepoints(cps);
    println("unexpectedly accepted oversized accessibility text");
    return 1;
}
"""
        over_cap = os.path.join(tmp, "a11y-utf8-over.cap")
        over_c = os.path.join(tmp, "a11y-utf8-over.c")
        over_exe = os.path.join(tmp, "a11y-utf8-over")
        with open(over_cap, "w", encoding="utf-8") as stream:
            stream.write(over_source)
        run([capstanc, "build", "--strict", "-o", over_c] + LIB + [over_cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), over_c, "-o", over_exe])
        rejected = run([over_exe], env=env, expected=101)
        if "shroud: accessibility UTF-8 byte limit exceeded" not in rejected.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing over-limit diagnostic: {rejected.stdout!r}")

        invalid_source = """
int main() {
    List<int> cps = new List<int>();
    cps.push(0xD800);
    utf8_from_codepoints(cps);
    println("unexpectedly accepted surrogate code point");
    return 1;
}
"""
        invalid_cap = os.path.join(tmp, "a11y-utf8-invalid.cap")
        invalid_c = os.path.join(tmp, "a11y-utf8-invalid.c")
        invalid_exe = os.path.join(tmp, "a11y-utf8-invalid")
        with open(invalid_cap, "w", encoding="utf-8") as stream:
            stream.write(invalid_source)
        run([capstanc, "build", "--strict", "-o", invalid_c] + LIB + [invalid_cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), invalid_c, "-o", invalid_exe])
        invalid = run([invalid_exe], env=env, expected=101)
        if "shroud: invalid Unicode scalar in accessibility text" not in invalid.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing invalid-scalar diagnostic: {invalid.stdout!r}")

        json_budget_source = """
int main() {
    List<string> chars = new List<string>();
    for (int i = 0; i < 4096; i += 1) { chars.push("A"); }
    string chunk = join(chars, "");
    List<string> chunks = new List<string>();
    for (int i = 0; i < 1500; i += 1) { chunks.push(chunk); }
    Tainted large = taint(join(chunks, ""));
    A11yNode n = new A11yNode{
        id: "node", role: "text", name: large, value: taint(""),
        states: new List<string>(), bounds: rect(0, 0, 1, 1),
        kids: new List<A11yNode>()
    };
    a11y_json(n);
    println("unexpectedly accepted oversized accessibility JSON");
    return 1;
}
"""
        json_cap = os.path.join(tmp, "a11y-json-over.cap")
        json_c = os.path.join(tmp, "a11y-json-over.c")
        json_exe = os.path.join(tmp, "a11y-json-over")
        with open(json_cap, "w", encoding="utf-8") as stream:
            stream.write(json_budget_source)
        run([capstanc, "build", "--strict", "-o", json_c] + LIB + [json_cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), json_c, "-o", json_exe])
        json_rejected = run([json_exe], env=env, expected=101)
        if "shroud: accessibility JSON node/depth/byte budget exceeded" not in json_rejected.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing JSON output-budget diagnostic: {json_rejected.stdout!r}")

        depth_source = """
int main() {
    A11yNode n = new A11yNode{
        id: "leaf", role: "text", name: taint("leaf"), value: taint(""),
        states: new List<string>(), bounds: rect(0, 0, 1, 1),
        kids: new List<A11yNode>()
    };
    for (int i = 0; i <= MAX_DEPTH; i += 1) {
        List<A11yNode> kids = new List<A11yNode>();
        kids.push(n);
        n = new A11yNode{
            id: "parent", role: "group", name: taint(""), value: taint(""),
            states: new List<string>(), bounds: rect(0, 0, 1, 1), kids: kids
        };
    }
    a11y_json(n);
    println("unexpectedly accepted excessive accessibility JSON depth");
    return 1;
}
"""
        depth_cap = os.path.join(tmp, "a11y-json-depth.cap")
        depth_c = os.path.join(tmp, "a11y-json-depth.c")
        depth_exe = os.path.join(tmp, "a11y-json-depth")
        with open(depth_cap, "w", encoding="utf-8") as stream:
            stream.write(depth_source)
        run([capstanc, "build", "--strict", "-o", depth_c] + LIB + [depth_cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), depth_c, "-o", depth_exe])
        depth_rejected = run([depth_exe], env=env, expected=101)
        if "shroud: accessibility JSON node/depth/byte budget exceeded" not in depth_rejected.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing JSON depth diagnostic: {depth_rejected.stdout!r}")

        json_stress_source = """
int main() {
    List<string> chars = new List<string>();
    for (int i = 0; i < 4096; i += 1) { chars.push(char_str(1)); }
    string chunk = join(chars, "");
    List<string> chunks = new List<string>();
    for (int i = 0; i < 256; i += 1) { chunks.push(chunk); }
    Tainted large = taint(join(chunks, ""));
    A11yNode n = new A11yNode{
        id: "node", role: "text", name: large, value: taint(""),
        states: new List<string>(), bounds: rect(0, 0, 1, 1),
        kids: new List<A11yNode>()
    };
    string json = a11y_json(n);
    if (json.len() < MAX_TEXT_BYTES * 6) { return 1; }
    println("a11y JSON stress: 1 MiB controls escaped");
    return 0;
}
"""
        stress_cap = os.path.join(tmp, "a11y-json-stress.cap")
        stress_c = os.path.join(tmp, "a11y-json-stress.c")
        stress_exe = os.path.join(tmp, "a11y-json-stress")
        with open(stress_cap, "w", encoding="utf-8") as stream:
            stream.write(json_stress_source)
        run([capstanc, "build", "--strict", "-o", stress_c] + LIB + [stress_cap])
        run([cc] + cflags + ["-I", os.path.join(ROOT, "runtime"), stress_c, "-o", stress_exe])
        stress = run([stress_exe], env=env)
        if "1 MiB controls escaped" not in stress.stdout:
            raise SystemExit(f"a11y UTF-8 budget: missing JSON stress confirmation: {stress.stdout!r}")
        stress_match = re.search(r"peak_heap=(\d+)", stress.stderr)
        if not stress_match:
            raise SystemExit(f"a11y UTF-8 budget: JSON stress peak heap not reported: {stress.stderr!r}")
        stress_peak = int(stress_match.group(1))
        if stress_peak > limit:
            raise SystemExit(f"a11y UTF-8 budget: JSON stress peak managed heap {stress_peak} exceeds {limit}")
    print(f"a11y UTF-8 budget: 1 MiB encoded; encoder peak {peak} bytes; 1 MiB control JSON peak {stress_peak} bytes (64 MiB managed-heap cap); invalid scalar, oversized UTF-8/JSON and excessive depth rejected")


if __name__ == "__main__":
    main()
