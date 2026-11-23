#!/usr/bin/env python3
"""Table-driven tests for the checker's pattern-based rules.

Each row is a small program and the verdict it must get: a diagnostic code that
must appear (with --strict, so warnings count), or None for a program that must
compile cleanly under --strict --release. Rows come in pairs where it matters:
the thing a rule must catch, and a near miss it must not flag.

    lint_table.py            uses build/capstanc (or $CAPSTANC)
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPSTANC = os.environ.get("CAPSTANC", os.path.join(ROOT, "build/capstanc"))


def lit(s):
    return f'int main() {{ println("{s}".slice(0, 0)); return 0; }}'


ROWS = []
# CWE-798: string literals in known credential formats, one row per format, plus near misses.
# Each sample is assembled from a prefix and a body here, so that this file never contains a
# string in a credential format (secret scanners would rightly refuse it); the program under
# test still receives the whole literal.
BODY = "Xq7" * 9                                   # 27 characters of filler, no real key
SAMPLES = [("sk_" + "live_", BODY), ("rk_" + "live_", BODY), ("AK" + "IA", "Q" * 16), ("AS" + "IA", "Q7" * 8),
           ("gh" + "p_", BODY), ("gh" + "o_", BODY), ("gh" + "s_", BODY), ("github" + "_pat_", BODY),
           ("xo" + "xb-", BODY), ("xo" + "xp-", BODY), ("xo" + "xa-", BODY), ("AI" + "za", "Q" * 35),
           ("-----BEGIN RSA PRIV" + "ATE KEY-----", "")]
for prefix, body in SAMPLES:
    ROWS.append((f"credential format {prefix}", lit(prefix + body), "CWE-798"))
NEAR = [("sk_" + "live_", ""), ("AK" + "IA", "q" * 16), ("AK" + "IA", "Q" * 15), ("AK" + "IA", "Q" * 17), ("gh" + "p_", "short"),
        ("AI" + "za", "Q" * 8), ("xo" + "x-", BODY), ("-----BEGIN PUBLIC KEY-----", ""), ("sk_" + "test_", BODY)]
for prefix, body in NEAR:
    ROWS.append((f"not a credential: {prefix}{body[:6]}", lit(prefix + body), None))

# CWE-547: security decisions on magic numbers, for every security-sounding name and comparison.
for name in ["role", "level", "permission", "privilege", "clearance", "access", "rank"]:
    for op in ["==", "!=", "<", "<=", ">", ">="]:
        ROWS.append((f"magic number: {name} {op} 3",
                     f"int main() {{ int user_{name} = 1; if (user_{name} {op} 3) {{ println(\"x\"); }} return 0; }}", "CWE-547"))
ROWS.append(("magic number on the left", "int main() { int level = 1; if (3 == level) { println(\"x\"); } return 0; }", "CWE-547"))
ROWS.append(("0 and 1 are not magic", "int main() { int level = 1; if (level == 1 || level == 0) { println(\"x\"); } return 0; }", None))
ROWS.append(("not a security name", "int main() { int count = 1; if (count == 3) { println(\"x\"); } return 0; }", None))

# CWE-546: comments about unfinished security work.
for marker in ["TODO", "FIXME", "XXX", "HACK", "todo", "Fixme"]:
    for topic in ["password", "auth", "security", "secret", "bypass", "remove before release"]:
        ROWS.append((f"comment: {marker} {topic}", f"// {marker}: {topic} check\nint main() {{ return 0; }}", "CWE-546"))
ROWS.append(("comment: backdoor", "/* debug backdoor */\nint main() { return 0; }", "CWE-546"))
ROWS.append(("comment: TODO about something else", "// TODO: tidy up the output format\nint main() { return 0; }", None))
ROWS.append(("comment: security note without a marker", "// passwords are hashed with PBKDF2\nint main() { return 0; }", None))

# CWE-20: untrusted bytes stay untrusted through every arithmetic and bitwise operator.
for expr in ["b + 0", "b - 0", "b * 1", "b / 1", "b % 256", "b & 255", "b | 0", "b ^ 0", "b << 0", "b >> 0", "b >>> 0",
             "~(~b)", "wrapping_add(b, 0)", "wrapping_sub(b, 0)", "wrapping_mul(b, 1)", "wrapping_shl(b, 0)"]:
    ROWS.append((f"laundering through {expr}",
                 f"int main() {{ if (let t = read_line()) {{ int b = t.at(0); println(char_str({expr})); }} return 0; }}", "CWE-20"))
ROWS.append(("trusted bytes through the same operators",
             "int main() { int b = 72; println(char_str((b + 0) & 255) + char_str(wrapping_add(b, 1))); return 0; }", None))

# CWE-480: bitwise operators on booleans, each pointing to the logical operator meant.
for op, meant in [("&", "&&"), ("|", "||"), ("^", "!=")]:
    ROWS.append((f"bitwise {op} on bool", f"bool f(bool a, bool b) {{ return a {op} b; }}\nint main() {{ return 0; }}", "CWE-480"))
ROWS.append(("bitwise ~ on bool", "bool f(bool a) { return ~a == 0; }\nint main() { return 0; }", "CWE-480"))

# Warnings with no other test.
ROWS.append(("CWE-390 empty else", "int main() { int x = 1; if (x > 0) { println(\"a\"); } else {} return 0; }", "CWE-390"))
ROWS.append(("CWE-1164 self-assignment", "int main() { int x = 1; x = x; println(int_to_str(x)); return 0; }", "CWE-1164"))
ROWS.append(("CWE-1164 self-assignment of a field",
             "struct P { int x; }\nint main() { P p = new P{x: 1}; p.x = p.x; println(int_to_str(p.x)); return 0; }", "CWE-1164"))
ROWS.append(("not a self-assignment", "int main() { int x = 1; int y = 2; x = y; println(int_to_str(x + y)); return 0; }", None))
ROWS.append(("CWE-252 ignored write_file", 'int main() { write_file("out.txt", "x"); return 0; }', "CWE-252"))
ROWS.append(("checked write_file", 'int main() { if (!write_file("out.txt", "x")) { return 1; } return 0; }', None))

# CWE-208: comparing credential-named values, and comparisons that are fine.
ROWS.append(("CWE-208 token compare", "bool same(string token, string other) { return token == other; }\nint main() { return 0; }", "CWE-208"))
ROWS.append(("call results compared", 'string a() { return "x"; }\nstring b() { return "y"; }\nint main() { if (a() == b()) { println("same"); } return 0; }', None))
ROWS.append(("token count compared", "int main() { int token_count = 2; if (token_count == 2) { println(\"two\"); } return 0; }", None))


def main():
    work = tempfile.mkdtemp()
    cap, out = os.path.join(work, "t.cap"), os.path.join(work, "t.c")
    fails = []
    for name, src, want in ROWS:
        open(cap, "w").write(src + "\n")
        try:
            r = subprocess.run([CAPSTANC, "check", "--strict", "--release", cap], capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            fails.append(f"{name}: compiler hung")
            continue
        text = r.stdout.decode(errors="replace")
        if want is None and r.returncode != 0:
            fails.append(f"{name}: must be accepted, got: {text.splitlines()[0] if text else r.returncode}")
        elif want is not None and (r.returncode != 1 or f"[{want}]" not in text):
            fails.append(f"{name}: expected {want}, got exit {r.returncode}: {text.splitlines()[0] if text else ''}")
    for f in fails:
        print("  " + f)
    print(f"lint table: {len(ROWS) - len(fails)} of {len(ROWS)} rows give the expected verdict")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
