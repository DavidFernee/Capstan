#!/usr/bin/env python3
"""
Capstan CWE red-team atlas.

For each code-level weakness in the CWE list, this file holds the most natural
attempt to write that weakness in Capstan, including deliberate workarounds,
and the outcome Capstan must produce. Running it re-checks every verdict
against the current compiler and regenerates docs/CWE-ATLAS.md.

Verdicts:
  reject   the attempt does not compile; the diagnostic must contain `expect`
  runtime  the attempt compiles but stops safely (exit 101) with `expect`
  neutral  the attempt compiles and runs, but the attack has no effect;
           output must contain `expect`
  absent   the construct the weakness needs does not exist in Capstan;
           the attempt (written as a C/Java programmer would) must fail to compile
  audited  possible only through trust(); the build reports an AUDIT warning
  logic    a logic or design decision that no language can tell from intent;
           the attempt compiles
  gap      THE WEAKNESS CAN BE WRITTEN: the attempt compiles. If a later version
           closes the gap, this check fails, so the entry must be reclassified
  na       not applicable to program code in Capstan (hardware, process, or a
           facility Capstan does not have yet); no attempt

usage: atlas.py [--write-doc]
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CC = os.environ.get("CC", "cc")
MAIN = "\nint main() { return 0; }\n"

E = []


def add(cwe, name, verdict, code=None, expect=None, note=""):
    E.append(dict(cwe=cwe, name=name, verdict=verdict, code=code, expect=expect, note=note))


# Reusable attempt shapes for constructs Capstan does not have.
PTR = "int main() { int x = 1; int* p = &x; *p = 2; return x; }"
PTR_ARITH = "int main() { List<int> xs = new List<int>(); int* p = xs; p = p + 10; return *p; }"
CAST = "int main() { int big = 300; byte b = (byte) big; return b; }"
UNSIGNED = "int main() { unsigned int u = 0 - 1; return 0; }"
SHIFT = "int main() { int x = 1 << 70; return x; }"
FLOAT = "int main() { double d = 0.1 + 0.2; if (d == 0.3) { return 1; } return 0; }"
SWITCH = "int main() { int x = 1; switch (x) { case 1: x = 2; case 2: x = 3; } return x; }"
THREAD = "int counter = 0;\nvoid work() { counter = counter + 1; }\nint main() { spawn work(); spawn work(); return counter; }"
EXCEPT = "int main() { try { throw new Error(); } catch (Exception e) { } return 0; }"
FREE = "int main() { string s = \"x\"; free(s); free(s); return 0; }"
MALLOC = "int main() { string s = malloc(16); return 0; }"
EVAL = "int main() { eval(\"1 + 1\"); return 0; }"
REFLECT = "int main() { string cls = \"User\"; Object o = Class.forName(cls).newInstance(); return 0; }"
DESER = "int main() { Object o = deserialize(read_line()); return 0; }"
XML = "int main() { Xml doc = parse_xml(taint(\"<!DOCTYPE x [<!ENTITY e SYSTEM 'file:///etc/passwd'>]>\")); return 0; }"
NET = "int main() { string body = http_get(\"http://169.254.169.254/latest/meta-data/\"); return 0; }"
SOCKET = "int main() { Socket s = connect(\"example.com\", 80); return 0; }"
REGEX = "int main() { bool m = regex_match(\"(a+)+$\", taint(\"aaaaaaaaaaaaaaaaaaaaaaaaaaaa!\")); return 0; }"
RANDOM = "int main() { int token = rand(); return token; }"
ENCRYPT = "int main() { string c = encrypt_cbc(\"key\", \"iv\", \"data\"); return 0; }"
TLS = "int main() { Tls t = tls_connect(\"bank.example\", false); return 0; }"
SIGNAL = "void on_term() { }\nint main() { signal(15, on_term); return 0; }"
SETENV = "int main() { setenv(\"PATH\", trust(taint(\"/tmp\"), \"x\")); return 0; }"
LOADLIB = "int main() { load_library(trust(taint(\"evil.so\"), \"x\")); return 0; }"
CHMOD = "int main() { chmod(\"secrets.txt\", 511); return 0; }"
GOTO = "int main() { goto end; end: return 0; }"
SIZEOF = "int main() { string s = \"abc\"; int n = sizeof(s); return n; }"
NULLLIT = "int main() { string s = null; return 0; }"
ASSIGN_IN_COND = "int main() { int x = 0; if (x = 1) { return 1; } return 0; }"
UNINIT = "int main() { int total; return total; }"
GLOBAL_MUT = "int hits = 0;\nint main() { hits = hits + 1; return hits; }"
INCLUDE = "#include \"untrusted.h\"\nint main() { return 0; }"
LAUNDER = '''string launder(Tainted t) {
    string out = "";
    for (int i = 0; i < t.len(); i += 1) { out += char_str(t.at(i)); }
    return out;
}
'''
LAUNDER_HELPER = '''int byte_at(Tainted t, int i) { return t.at(i); }
string launder(Tainted t) {
    string out = "";
    for (int i = 0; i < t.len(); i += 1) { out += char_str(byte_at(t, i)); }
    return out;
}
'''
SENS = '''sensitive struct User { int id; int role; }
sensitive struct Record { int owner; string body; }
'''
USERS = '''struct User { int id; int role; }
struct Record { int owner; string body; }
'''

# ---------------------------------------------------------------- memory safety
add(119, "Improper restriction of operations within memory buffer bounds", "runtime",
    "int main() { List<int> buf = new List<int>(); buf.push(1); int i = 8; buf[i] = 7; return 0; }", "CWE-787")
add(120, "Buffer copy without checking size of input (classic overflow)", "reject",
    "int main() { strcpy(\"dst\", \"a much longer source string\"); return 0; }", "CWE-120")
add(121, "Stack-based buffer overflow", "absent", "int main() { char buf[8]; buf[20] = 'x'; return 0; }")
add(122, "Heap-based buffer overflow", "runtime",
    "int main() { List<int> h = new List<int>(); for (int i = 0; i < 4; i += 1) { h.push(i); } h[4] = 1; return 0; }", "CWE-787")
add(123, "Write-what-where condition", "absent", PTR)
add(124, "Buffer underwrite", "runtime",
    "int main() { List<int> b = new List<int>(); b.push(1); int i = 0 - 1; b[i] = 9; return 0; }", "CWE-787")
add(125, "Out-of-bounds read", "runtime",
    "int main() { string s = \"abc\"; int i = 3; return s.at(i); }", "CWE-125")
add(126, "Buffer over-read", "runtime",
    "int main() { string s = \"secret\"; string leak = s.slice(0, 64); return 0; }", "CWE-125")
add(127, "Buffer under-read", "runtime",
    "int main() { List<int> b = new List<int>(); b.push(1); int i = 0 - 2; return b[i]; }", "CWE-125")
add(129, "Improper validation of array index", "runtime",
    "int lookup(List<int> t, int i) { return t[i]; }\nint main() { List<int> t = new List<int>(); t.push(5); return lookup(t, 1000000); }", "CWE-125")
add(131, "Incorrect calculation of buffer size", "absent", MALLOC)
add(134, "Use of externally-controlled format string", "reject",
    "int main() { Tainted fmt = taint(\"%s%s%n\"); printf(fmt); return 0; }", "CWE-134")
add(170, "Improper null termination", "neutral",
    'int main() { string s = "ab\\0cd"; println(int_to_str(s.len())); return 0; }', "5",
    "Strings carry their length; an embedded zero byte does not truncate them.")
add(188, "Reliance on data/memory layout", "absent", PTR_ARITH)
add(401, "Missing release of memory after effective lifetime (leak)", "neutral",
    'struct Big { List<int> data; }\nint main() { for (int i = 0; i < 2000; i += 1) { Big b = new Big{data: new List<int>()}; for (int j = 0; j < 1000; j += 1) { b.data.push(j); } } println("bounded"); return 0; }',
    "bounded", "Unreachable memory is collected. Memory still reachable from live data (a growing global list) is retained by design.")
add(415, "Double free", "reject", FREE, "CWE-415")
add(416, "Use after free", "reject", FREE, "CWE-415", "There is no free(); memory is reclaimed only when unreachable.")
add(457, "Use of uninitialized variable", "reject", UNINIT, "CWE-457")
add(466, "Return of pointer value outside of expected range", "absent", PTR)
add(467, "Use of sizeof() on a pointer type", "absent", SIZEOF)
add(468, "Incorrect pointer scaling", "absent", PTR_ARITH)
add(469, "Use of pointer subtraction to determine size", "absent", PTR_ARITH)
add(476, "NULL pointer dereference", "reject",
    "struct A { string owner; }\nA? find(int id) { return none; }\nint main() { A? a = find(1); println(a.owner); return 0; }", "CWE-476")
add(587, "Assignment of a fixed address to a pointer", "absent", "int main() { int* p = 0xdeadbeef; return 0; }")
add(590, "Free of memory not on the heap", "reject", FREE, "CWE-415")
add(761, "Free of pointer not at start of buffer", "reject", FREE, "CWE-415")
add(762, "Mismatched memory management routines", "reject", MALLOC, "CWE-415")
add(763, "Release of invalid pointer or reference", "reject", FREE, "CWE-415")
add(786, "Access of memory location before start of buffer", "runtime",
    "int main() { string s = \"abc\"; return s.at(0 - 1); }", "CWE-125")
add(787, "Out-of-bounds write", "runtime",
    "int main() { List<int> b = new List<int>(); b[0] = 1; return 0; }", "CWE-787")
add(788, "Access of memory location after end of buffer", "runtime",
    "int main() { List<string> b = new List<string>(); b.push(\"x\"); println(b[1]); return 0; }", "CWE-125")
add(805, "Buffer access with incorrect length value", "runtime",
    "int main() { string s = \"short\"; int claimed = 100; string t = s.slice(0, claimed); return 0; }", "CWE-125")
add(806, "Buffer access using size of source buffer", "runtime",
    "int main() { string src = \"a longer source\"; string dst = \"tiny\"; string x = dst.slice(0, src.len()); return 0; }", "CWE-125")
add(824, "Access of uninitialized pointer", "reject",
    "struct Node { int v; }\nint main() { Node n; return n.v; }", "CWE-457")
add(825, "Expired pointer dereference", "absent", PTR)
add(908, "Use of uninitialized resource", "reject",
    "struct Conn { string host; int port; }\nint main() { Conn c = new Conn{port: 443}; println(c.host); return 0; }", "CWE-908")
add(909, "Missing initialization of resource", "reject",
    "struct Config { bool tls; string host; }\nint main() { Config c = new Config{host: \"x\"}; return 0; }", "CWE-908")

# ---------------------------------------------------------------- numbers
add(128, "Wrap-around error", "runtime",
    "int main() { int balance = 9223372036854775807; balance += 1; return 0; }", "CWE-190")
add(190, "Integer overflow or wraparound", "runtime",
    "int total(int qty, int price) { return qty * price; }\nint main() { return total(4611686018427387904, 4); }", "CWE-190")
add(191, "Integer underflow", "runtime",
    "int main() { int stock = 0 - 9223372036854775807; stock -= 5; return 0; }", "CWE-191")
add(192, "Integer coercion error", "absent", CAST)
add(194, "Unexpected sign extension", "absent", CAST)
add(195, "Signed to unsigned conversion error", "absent", UNSIGNED)
add(196, "Unsigned to signed conversion error", "absent", UNSIGNED)
add(197, "Numeric truncation error", "absent", CAST)
add(369, "Divide by zero", "runtime",
    "int avg(int sum, int n) { return sum / n; }\nint main() { return avg(10, 0); }", "CWE-369")
add(681, "Incorrect conversion between numeric types", "absent", CAST)
add(682, "Incorrect calculation", "logic", "int discount(int price) { return price - price / 10 * 100; }" + MAIN, note="A wrong formula is a specification error. Overflow from it is still caught.")
add(704, "Incorrect type conversion or cast", "runtime",
    "int main() { int code = 300; string s = char_str(code); return 0; }", "CWE-704")
add(1335, "Incorrect bitwise shift of integer", "reject", SHIFT, "CWE-1335",
    note="A literal shift count outside 0..63 does not compile.")
add(1335, "Incorrect bitwise shift of integer (computed count)", "runtime",
    "int count() { return 70; }\nint main() { return 1 << count(); }", "CWE-1335")
add(190, "Integer overflow (bits shifted out by <<)", "runtime",
    "int main() { int x = 3; int n = 62; return x << n; }", "CWE-190",
    note="<< is checked like multiplication; wrapping_shl() is the explicit modular form.")
add(783, "Operator precedence logic error (bitwise)", "reject",
    "bool even(int flags) { return flags & 1 == 0; }" + MAIN, "CWE-783",
    note="A bitwise operator may not be mixed with another operator without parentheses.")
add(480, "Use of incorrect operator (bitwise on booleans)", "reject",
    "bool both(bool a, bool b) { return a & b; }" + MAIN, "CWE-480")
add(20, "Laundering untrusted bytes through a bit mask", "reject",
    "int main() { if (let t = read_line()) { println(char_str(t.at(0) & 0x7F)); } return 0; }", "CWE-20")
add(1339, "Insufficient precision or accuracy of a real number", "absent", FLOAT)
add(1077, "Floating point comparison with incorrect operator", "absent", FLOAT)

# ---------------------------------------------------------------- injection
add(20, "Improper input validation", "reject",
    "int main() { if (let line = read_line()) { string name = line; } return 0; }", "CWE-20")
add(74, "Injection (generic)", "reject",
    "void sink(string cmd) { }\nint main() { Tainted t = taint(\"; rm -rf /\"); sink(t); return 0; }", "CWE-20")
add(77, "Command injection", "reject",
    "int main() { Tainted f = taint(\"x; reboot\"); run(\"tar -czf \" + f); return 0; }", "CWE-78")
add(78, "OS command injection", "reject",
    "int main() { system(\"ping 127.0.0.1\"); return 0; }", "CWE-78")
add(78, "OS command injection (via run with untrusted argument)", "neutral",
    'int main() { run("ping", "--", taint("127.0.0.1; cat /etc/shadow")); return 0; }', "argv[2]=127.0.0.1; cat /etc/shadow",
    "No shell exists: the whole value stays one argument.")
add(79, "Cross-site scripting", "reject",
    "string page(string body) { return \"<p>\" + body + \"</p>\"; }\nint main() { Tainted c = taint(\"<script>x()</script>\"); string h = page(c); return 0; }", "CWE-20")
add(79, "Cross-site scripting (via the wrong escaper)", "reject",
    'string page(string body) { return "<p>" + body + "</p>"; }\nint main() { println(page(escape_log(taint("<script>steal()</script>")))); return 0; }', "CWE-116",
    "escape_log() returns LogText and escape_html() returns Html; neither can pass as a plain string.")
add(79, "Cross-site scripting (via byte-by-byte laundering)", "reject",
    LAUNDER + 'int main() { println("<p>" + launder(taint("<script>x()</script>")) + "</p>"); return 0; }', "CWE-20")
add(79, "Cross-site scripting (laundering through a helper function)", "reject",
    LAUNDER_HELPER + 'int main() { println("<p>" + launder(taint("<script>x()</script>")) + "</p>"); return 0; }', "CWE-20")
add(20, "Laundering untrusted bytes through a list", "reject",
    'string launder(Tainted t) { List<int> b = new List<int>(); for (int i = 0; i < t.len(); i += 1) { b.push(t.at(i)); } string out = ""; for (int j = 0; j < b.len(); j += 1) { out += char_str(b[j]); } return out; }' + MAIN, "CWE-20",
    "Collections and structs that hold bytes of untrusted input are tracked too.")
add(20, "Laundering untrusted bytes through a struct field", "reject",
    'struct Box { int b; }\nstring launder(Tainted t) { Box x = new Box{b: 0}; x.b = t.at(0); return char_str(x.b); }' + MAIN, "CWE-20")
add(20, "Laundering untrusted bytes through control flow", "logic",
    'string launder(Tainted t) { string out = ""; for (int i = 0; i < t.len(); i += 1) { if (t.at(i) == 60) { out += "<"; } else { out += "a"; } } return out; }' + MAIN,
    note="Building output by branching on each input byte is exactly how a validator is written (the compiler's own lexer works this way). Which branches are safe is the programmer's decision.")
add(80, "Basic XSS (improper neutralization of script tags)", "neutral",
    'int main() { println("<p>" + escape_html(taint("<script>x()</script>")) + "</p>"); return 0; }', "&lt;script&gt;")
add(88, "Argument injection", "reject",
    'int main() { run("git", "clone", taint("--upload-pack=touch /tmp/pwned")); return 0; }', "CWE-88")
add(89, "SQL injection", "reject",
    "void find(Tainted name) { sql_query(\"SELECT * FROM users WHERE name = '\" + name + \"'\"); }" + MAIN, "CWE-89")
add(89, "SQL injection (query held in a variable)", "reject",
    "int main() { string q = \"DROP TABLE users\"; sql_query(q); return 0; }", "CWE-89")
add(89, "SQL injection (attempt through a bound parameter)", "neutral",
    "int main() { sql_query(\"SELECT * FROM users WHERE name = ?\", taint(\"x' OR '1'='1\")); return 0; }", "$1=x' OR '1'='1")
add(90, "LDAP injection", "na", note="No LDAP facility.")
add(91, "XML injection", "absent", XML)
add(93, "CRLF injection", "reject",
    'int main() { println("Location: " + taint("/home\\r\nSet-Cookie: admin=1")); return 0; }', "CWE-117")
add(94, "Code injection", "absent", EVAL)
add(95, "Eval injection", "reject", EVAL, "CWE-95")
add(96, "Static code injection", "absent", INCLUDE)
add(97, "Server-side includes injection", "na", note="No web server facility.")
add(98, "PHP remote file inclusion", "absent", INCLUDE)
add(99, "Resource injection", "reject",
    "int main() { if (let p = read_line()) { if (let data = read_file(p)) { } } return 0; }", "CWE-20")
add(113, "HTTP response splitting", "na", note="No HTTP facility yet; header output would follow the CWE-93 rule.")
add(116, "Improper encoding or escaping of output", "reject",
    'int main() { string csv = escape_html(taint("=cmd|\' /C calc\'!A0")) + ",1"; bool ok = write_file("out.csv", csv); return 0; }', "CWE-116",
    "Escaped text is typed by its context (Html, LogText) and cannot pass as a plain string.")
add(116, "Improper encoding: HTML-escaped text written into a CSV file", "gap",
    'int main() { Html cell = escape_html(taint("=cmd|\' /C calc\'!A0")) + ",1"; bool ok = write_file("out.csv", cell); return 0; }',
    note="write_file() accepts Html because web pages are files too, and the compiler cannot know the file's format. Typed file writers (CSV, HTML, JSON) are on the roadmap.")
add(117, "Improper output neutralization for logs", "reject",
    'int main() { println("login failed: " + taint("bob\nINFO admin ok")); return 0; }', "CWE-117")
add(117, "Log injection (attempt after escape_log)", "neutral",
    'int main() { println("login failed: " + escape_log(taint("bob\nINFO admin ok"))); return 0; }', "bob\\x0aINFO")
add(643, "XPath injection", "na", note="No XPath facility.")
add(652, "XQuery injection", "na", note="No XQuery facility.")
add(611, "XML external entity reference (XXE)", "absent", XML)
add(776, "XML entity expansion (billion laughs)", "absent", XML)
add(917, "Expression language injection", "absent", EVAL)
add(1236, "CSV formula injection", "reject",
    'int main() { Tainted cell = taint("=HYPERLINK(\"http://evil\")"); bool ok = write_file("export.csv", "name\n" + cell); return 0; }', "escape_csv",
    "Untrusted text cannot be written to a file unchanged.")
add(1236, "CSV formula injection (attempt after escape_csv)", "neutral",
    'int main() { println(escape_csv(taint("=HYPERLINK(1)"))); return 0; }', "\"'=HYPERLINK(1)\"")
add(1333, "Inefficient regular expression complexity (ReDoS)", "absent", REGEX)
add(185, "Incorrect regular expression", "absent", REGEX)

# ---------------------------------------------------------------- files and paths
add(22, "Path traversal", "reject",
    "int main() { Tainted name = taint(\"../../etc/passwd\"); if (let f = read_file(name)) { } return 0; }", "CWE-20")
add(22, "Path traversal (via an audited trust())", "audited",
    'int main() { Tainted name = taint("../../etc/passwd"); if (let f = read_file(trust(name, "file name from form"))) { } return 0; }',
    note="Possible only through trust(), which needs a written justification and is reported in every build. validate_path() is the safe route.")
add(22, "Path traversal (attempt through validate_path)", "neutral",
    'int main() { if (let p = validate_path(taint("../../etc/passwd"))) { println("accepted"); } else { println("rejected"); } return 0; }', "rejected")
add(23, "Relative path traversal", "reject",
    "int main() { string base = \"/srv/files/\"; Tainted n = taint(\"../secret\"); bool ok = write_file(base + n, \"x\"); return 0; }", "CWE-20")
add(36, "Absolute path traversal", "reject",
    "int main() { Tainted n = taint(\"/etc/shadow\"); if (let f = read_file(n)) { } return 0; }", "CWE-20")
add(59, "Improper link resolution before file access (link following)", "na",
    note="File access follows symbolic links; capability-based file access (v0.6) will address it.")
add(73, "External control of file name or path", "reject",
    "int main() { if (let p = read_line()) { bool ok = write_file(p, \"data\"); } return 0; }", "CWE-20")
add(434, "Unrestricted upload of file with dangerous type", "na", note="No upload facility.")
add(538, "Insertion of sensitive information into externally-accessible file", "reject",
    'int main() { if (let key = secret_env("API_KEY")) { bool ok = write_file("public/config.txt", key); } return 0; }', "CWE-532")
add(552, "Files or directories accessible to external parties", "na", note="Deployment concern.")
add(732, "Incorrect permission assignment for critical resource", "absent", CHMOD)
add(276, "Incorrect default permissions", "na", note="Files are created with the process umask; a file API with explicit permissions is planned with capabilities.")
add(377, "Insecure temporary file", "na", note="No temporary-file API.")
add(367, "Time-of-check time-of-use race", "absent",
    "int main() { if (file_exists(\"x\")) { if (let d = read_file(\"x\")) { } } return 0; }",
    note="There is no separate existence check; read_file() returns the contents or none in one step.")

# ---------------------------------------------------------------- environment and execution
add(15, "External control of system or configuration setting", "absent", SETENV)
add(114, "Process control", "absent", LOADLIB)
add(426, "Untrusted search path", "absent", LOADLIB)
add(427, "Uncontrolled search path element", "absent", SETENV)
add(470, "Use of externally-controlled input to select classes or code (unsafe reflection)", "absent", REFLECT)
add(502, "Deserialization of untrusted data", "absent", DESER)
add(915, "Improperly controlled modification of dynamically-determined object attributes", "absent", REFLECT)
add(242, "Use of inherently dangerous function", "reject", "int main() { gets(\"buf\"); return 0; }", "CWE-120")
add(676, "Use of potentially dangerous function", "reject", "int main() { strcat(\"a\", \"b\"); return 0; }", "CWE-120")
add(477, "Use of obsolete function", "reject", "int main() { string h = md5(\"x\"); return 0; }", "CWE-327")
add(829, "Inclusion of functionality from untrusted control sphere", "absent", INCLUDE)
add(494, "Download of code without integrity check", "absent", NET)
add(250, "Execution with unnecessary privileges", "na", note="Deployment concern; capability-based I/O (v0.6) limits what code can touch.")

# ---------------------------------------------------------------- cryptography and randomness
add(256, "Plaintext storage of a password", "reject",
    'int main() { if (let pw = read_line()) { bool ok = write_file("users.db", "alice:" + pw); } return 0; }', "CWE-20")
add(257, "Storing passwords in a recoverable format", "reject",
    'int main() { if (let pw = read_line()) { bool ok = write_file("users.db", escape_html(pw)); } return 0; }', "CWE-256")
add(259, "Use of hard-coded password", "reject", "int main() { string admin_password = \"letmein\"; return 0; }", "CWE-798")
add(798, "Use of hard-coded credentials", "reject",
    "struct Client { string api_key; }\nint main() { Client c = new Client{api_key: \"sk_live_42\"}; return 0; }", "CWE-798")
add(798, "Hard-coded credential in a recognised format, under an innocuous name", "reject",
    'int main() { string cfg = "sk_live_51HxQ2eKzABCDEFG"; return 0; }', "CWE-798",
    "Literals in known credential formats (payment, cloud, source-hosting and chat tokens; private keys) are rejected wherever they appear.")
add(798, "Hard-coded password-like literal under an innocuous name", "gap",
    'int main() { string cfg = "Winter2026!"; sql_query("UPDATE settings SET v = ?", cfg); return 0; }',
    note="A short password-like literal under an ordinary name is indistinguishable from other text.")
add(321, "Use of hard-coded cryptographic key", "reject", "int main() { string signing_secret = \"0123456789abcdef\"; return 0; }", "CWE-798")
add(311, "Missing encryption of sensitive data", "na", note="No encryption API yet (seal()/open() planned for v0.6).")
add(312, "Cleartext storage of sensitive information", "reject",
    'int main() { if (let k = secret_env("DB_KEY")) { bool ok = write_file("cache.txt", k); } return 0; }', "CWE-532")
add(319, "Cleartext transmission of sensitive information", "absent", NET)
add(326, "Inadequate encryption strength", "absent", ENCRYPT)
add(327, "Use of a broken or risky cryptographic algorithm", "reject", "int main() { string h = sha1(\"x\"); return 0; }", "CWE-327")
add(328, "Use of weak hash", "reject", "int main() { string h = md5(\"x\"); return 0; }", "CWE-327")
add(329, "Generation of predictable IV with CBC mode", "absent", ENCRYPT)
add(323, "Reusing a nonce, key pair in encryption", "absent", ENCRYPT)
add(324, "Use of a key past its expiration date", "absent", ENCRYPT)
add(325, "Missing cryptographic step", "absent", ENCRYPT)
add(780, "Use of RSA algorithm without OAEP", "absent", ENCRYPT)
add(347, "Improper verification of cryptographic signature", "absent", ENCRYPT)
add(295, "Improper certificate validation", "absent", TLS)
add(297, "Improper validation of certificate with host mismatch", "absent", TLS)
add(330, "Use of insufficiently random values", "reject", RANDOM, "CWE-338")
add(331, "Insufficient entropy", "reject", RANDOM, "CWE-338")
add(335, "Incorrect usage of seeds in PRNG", "absent", "int main() { srand(42); return 0; }")
add(338, "Use of cryptographically weak PRNG", "reject", RANDOM, "CWE-338")
add(916, "Use of password hash with insufficient computational effort", "reject",
    "int main() { if (let pw = read_line()) { string stored = hash(pw); } return 0; }", "CWE-916")
add(916, "Weak password hash (password in an innocuously named variable)", "gap",
    "int main() { if (let x = read_line()) { string stored = hash(x); } return 0; }",
    note="Detection is name-based. Typing passwords as Secret at input would make this a type error (roadmap).")
add(916, "Weak password hash (password passed through a method call)", "gap",
    "int main() { if (let password = read_line()) { string stored = hash(password.slice(0, password.len())); } return 0; }",
    note="The password-name heuristic stops at N_METHOD nodes, so wrapping a password in a string method may evade the name-based CWE-916 check. Provisional until compiler CI confirms this expression is accepted.")
add(916, "Weak password hash (password passed through a helper call)", "gap",
    "Tainted identity(Tainted value) { return value; }\nint main() { if (let password = read_line()) { string stored = hash(identity(password)); } return 0; }",
    note="The password-name heuristic stops at N_CALL nodes, so a helper that preserves Tainted can hide a password-like variable from the name-based CWE-916 check. Provisional until compiler CI confirms this expression is accepted.")
add(759, "Use of a one-way hash without a salt", "reject",
    "string store(Tainted password) { return hash(password); }" + MAIN, "CWE-916")
add(760, "Use of a one-way hash with a predictable salt", "reject",
    "string store(Tainted password) { return hash(\"salt\" + password); }" + MAIN, "CWE-916")
add(208, "Observable timing discrepancy", "reject",
    "bool ok(Secret a, Secret b) { return a == b; }" + MAIN, "CWE-208")
add(208, "Timing discrepancy (token compared as a plain string)", "reject",
    "bool valid(Tainted given_token, string stored_token) { return given_token == stored_token; }" + MAIN, "CWE-208")
add(203, "Observable discrepancy (e.g. username enumeration)", "logic",
    'string login(bool user_exists, bool pw_ok) { if (!user_exists) { return "no such user"; } if (!pw_ok) { return "wrong password"; } return "ok"; }' + MAIN,
    note="What a response reveals is a design decision.")
add(385, "Covert timing channel", "na", note="Below the language.")

# ---------------------------------------------------------------- authentication and authorisation
add(862, "Missing authorization", "reject",
    USERS + "policy Read(User u, Record r) { return u.id == r.owner; }\nprotected(Read) string body(Grant<Read> g, Record r) { return r.body; }\nint main() { Record r = new Record{owner: 1, body: \"x\"}; println(body(r)); return 0; }\ntest \"d\" { assert_denied Read(new User{id: 2, role: 0}, new Record{owner: 1, body: \"\"}); }",
    "CWE-862")
add(862, "Missing authorization (record read with no grant)", "reject",
    SENS + "string read_any(Record r) { return r.body; }" + MAIN, "CWE-862",
    "Fields of a sensitive struct can only be read in protected functions, policies and tests.")
add(862, "Missing authorization (data type not declared sensitive)", "gap",
    USERS + "string read_any(Record r) { return r.body; }" + MAIN,
    note="Protection starts when the type is declared sensitive. It is declared once per type, not per function, but it can still be forgotten.")
add(285, "Improper authorization", "reject",
    USERS + "policy Read(User u, Record r) { return true; }" + MAIN, "CWE-862")
add(284, "Improper access control", "reject",
    USERS + "policy Admin(User u) { return u.role == 9; }\nvoid wipe(Grant<Admin> g) { }" + MAIN + "test \"d\" { assert_denied Admin(new User{id: 1, role: 0}); }", "CWE-862")
add(863, "Incorrect authorization", "logic",
    USERS + "policy Read(User u, Record r) { return u.id == r.owner || u.role > 0; }" + MAIN + "test \"d\" { assert_denied Read(new User{id: 2, role: 0}, new Record{owner: 1, body: \"\"}); }",
    note="A consistent but wrong policy is a requirements error. Denial tests, policy assertions (roadmap) and review are the defences.")
add(639, "Authorization bypass through user-controlled key (IDOR)", "runtime",
    USERS + "policy Read(User u, Record r) { return u.id == r.owner; }\nprotected(Read) string body(Grant<Read> g, Record r) { return r.body; }\nint main() { User me = new User{id: 1, role: 0}; Record mine = new Record{owner: 1, body: \"a\"}; Record theirs = new Record{owner: 2, body: \"b\"}; if (let g = authorize Read(me, mine)) { println(body(g, theirs)); } return 0; }\ntest \"d\" { assert_denied Read(new User{id: 2, role: 0}, new Record{owner: 1, body: \"\"}); }",
    "CWE-639")
add(639, "IDOR (policy that ignores the object)", "reject",
    USERS + "policy Read(User u, Record r) { return u.role == 2; }" + MAIN + "test \"d\" { assert_denied Read(new User{id: 2, role: 0}, new Record{owner: 1, body: \"\"}); }",
    "CWE-639", "Reported as a warning; an error with --strict (tested that way).")
add(613, "Insufficient session expiration (grant kept beyond its request)", "reject",
    USERS + "policy Admin(User u) { return u.role == 9; }\nstruct Session { Grant<Admin> g; }" + MAIN + "test \"d\" { assert_denied Admin(new User{id: 1, role: 0}); }", "CWE-613")
add(807, "Reliance on untrusted inputs in a security decision", "reject",
    "policy Admin(Tainted role_header) { return role_header == \"admin\"; }" + MAIN + "test \"d\" { assert_denied Admin(taint(\"x\")); }", "CWE-807")
add(302, "Authentication bypass by assumed-immutable data", "reject",
    "policy Admin(Tainted cookie_is_admin) { return cookie_is_admin == \"1\"; }" + MAIN + "test \"d\" { assert_denied Admin(taint(\"0\")); }", "CWE-807")
add(565, "Reliance on cookies without validation", "reject",
    "policy Owner(Tainted cookie_user_id) { return cookie_user_id == \"7\"; }" + MAIN + "test \"d\" { assert_denied Owner(taint(\"8\")); }", "CWE-807")
add(602, "Client-side enforcement of server-side security", "na", note="Architecture concern.")
add(287, "Improper authentication", "logic",
    'bool authenticate(Tainted user, Tainted pw) { return user == "admin"; }' + MAIN,
    note="Authentication logic is a design decision; a session and authentication framework is on the roadmap.")
add(306, "Missing authentication for critical function", "gap",
    "void delete_all_records() { }" + MAIN, note="An operation that touches no sensitive data value cannot be recognised as critical; it must be declared protected.")
add(307, "Improper restriction of excessive authentication attempts", "logic",
    'bool try_login(Tainted pw) { return verify_password(pw, "cap1$pbkdf2-sha256$600000$00$00"); }' + MAIN, note="Rate limiting is a design decision (the slow password hash already limits guessing speed).")
add(308, "Use of single-factor authentication", "na", note="Design concern.")
add(521, "Weak password requirements", "logic", "bool acceptable(Tainted pw) { return pw.len() >= 1; }" + MAIN, note="Password rules are policy.")
add(522, "Insufficiently protected credentials", "reject",
    'int main() { if (let token = secret_env("TOKEN")) { println("token loaded: " + token); } return 0; }', "CWE-200")
add(620, "Unverified password change", "logic",
    'string change(Tainted new_pw) { return hash_password(new_pw); }' + MAIN, note="Workflow design.")
add(640, "Weak password recovery mechanism", "na", note="Design concern.")
add(384, "Session fixation", "na", note="No session facility.")
add(352, "Cross-site request forgery", "na", note="No web facility yet (CSRF tokens planned in the web framework).")
add(1021, "Improper restriction of rendered UI layers (clickjacking)", "na", note="No web facility.")
add(290, "Authentication bypass by spoofing", "na", note="Network concern.")
add(294, "Authentication bypass by capture-replay", "na", note="Network concern.")
add(288, "Authentication bypass using an alternate path", "reject",
    SENS + "policy Read(User u, Record r) { return u.id == r.owner; }\nprotected(Read) string body(Grant<Read> g, Record r) { return r.body; }\nstring export_all(Record r) { return r.body; }" + MAIN + "test \"d\" { assert_denied Read(new User{id: 2, role: 0}, new Record{owner: 1, body: \"\"}); }",
    "CWE-862", "Every path to sensitive data needs a grant, so a second unprotected path does not compile.")
add(425, "Direct request (forced browsing)", "na", note="No web facility.")
add(269, "Improper privilege management", "reject",
    SENS + "void promote(User u) { u.role = 9; }" + MAIN, "CWE-862", "Changing a sensitive record also needs a grant.")
add(266, "Incorrect privilege assignment", "logic",
    USERS + "User new_user(int id) { return new User{id: id, role: 9}; }" + MAIN, note="Default roles are policy.")

# ---------------------------------------------------------------- information exposure
add(200, "Exposure of sensitive information", "reject",
    'int main() { if (let k = secret_env("KEY")) { string s = "k=" + k; } return 0; }', "CWE-200")
add(209, "Error message containing sensitive information", "reject",
    'int main() { if (let k = secret_env("DB_PASSWORD")) { println("connection failed with " + k); } return 0; }', "CWE-200")
add(210, "Self-generated error message with sensitive information", "neutral",
    'int main() { List<string> l = new List<string>(); println(l[3]); return 0; }', "",
    "Runtime stops report the file, line and check, never data values. The test expects the stop's stderr to be data-free.")
add(215, "Insertion of sensitive information into debugging code", "reject",
    'int main() { if (let k = secret_env("KEY")) { println(k); } return 0; }', "CWE-532")
add(532, "Insertion of sensitive information into log file", "reject",
    'int main() { if (let k = secret_env("KEY")) { println(k); } return 0; }', "CWE-532")
add(359, "Exposure of private personal information", "reject",
    "sensitive struct Patient { string name; string diagnosis; }\nint main() { Patient p = new Patient{name: \"A\", diagnosis: \"x\"}; println(p.diagnosis); return 0; }",
    "CWE-862", "Personal data declared sensitive can only be read under a grant.")
add(497, "Exposure of sensitive system information", "na", note="No system-information API.")
add(214, "Invocation of process using visible sensitive information", "neutral",
    'int main() { if (let k = secret_env("KEY")) { run("tool", "--"); } return 0; }', "[run] tool",
    "Secrets cannot be passed to run(); a separate test proves that (CWE-532).")
add(214, "Sensitive information on a command line", "reject",
    'int main() { if (let k = secret_env("KEY")) { run("tool", "--", k); } return 0; }', "CWE-532")
add(226, "Sensitive information in resource not removed before reuse", "neutral",
    'int main() { println("ok"); return 0; }', "ok",
    "Memory is zeroed when the collector reuses it and when it is allocated. Freed but not yet reused memory is not wiped; see CWE-244.")
add(244, "Improper clearing of heap memory before release (heap inspection)", "neutral",
    'int main() { if (let k = secret_env("KEY")) { } println("ok"); return 0; }', "ok",
    "Secrets live in their own memory class and are zeroed when collected; tests/unit proves it. Password-hashing scratch buffers are wiped too.")
add(316, "Cleartext storage of sensitive information in memory", "na", note="As CWE-244.")

# ---------------------------------------------------------------- error handling
add(248, "Uncaught exception", "absent", EXCEPT)
add(252, "Unchecked return value", "reject",
    "int main() { write_file(\"out.txt\", \"data\"); return 0; }", "CWE-252", "Warning; an error with --strict (tested that way).")
add(253, "Incorrect check of function return value", "reject",
    "int main() { int ok = write_file(\"x\", \"y\"); return 0; }", "type mismatch")
add(390, "Detection of error condition without action", "reject",
    "int main() { if (let d = read_file(\"config\")) { println(\"loaded\"); } else { } return 0; }", "CWE-390",
    "An empty else is a warning; an error with --strict (tested that way).")
add(391, "Unchecked error condition", "reject",
    "int main() { Tainted? d = read_file(\"config\"); println(int_to_str(d.len())); return 0; }", "CWE-476")
add(396, "Declaration of catch for generic exception", "absent", EXCEPT)
add(397, "Declaration of throws for generic exception", "absent", EXCEPT)
add(617, "Reachable assertion", "reject",
    "int main() { if (let line = read_line()) { assert(line.len() < 10); } return 0; }", "CWE-617",
    "assert() outside tests is a warning; an error with --strict (tested that way).")
add(636, "Not failing securely (failing open)", "reject",
    USERS + "policy Read(User u, Record r) { if (u.id == r.owner) { return true; } }" + MAIN, "default deny")
add(754, "Improper check for unusual or exceptional conditions", "reject",
    "int main() { Map<int> m = new Map<int>(); int v = m.get(\"k\"); return v; }", "CWE-476")
add(755, "Improper handling of exceptional conditions", "reject",
    "int main() { Tainted? f = read_file(\"x\"); Tainted t = f; return 0; }", "CWE-476")

# ---------------------------------------------------------------- concurrency
add(362, "Concurrent execution using shared resource with improper synchronization (race)", "absent", THREAD)
add(364, "Signal handler race condition", "absent", SIGNAL)
add(366, "Race condition within a thread", "absent", THREAD)
add(543, "Use of singleton pattern without synchronization", "absent", THREAD)
add(567, "Unsynchronized access to shared data", "absent", THREAD)
add(667, "Improper locking", "absent", THREAD)
add(833, "Deadlock", "absent", THREAD)
add(820, "Missing synchronization", "absent", THREAD)
add(821, "Incorrect synchronization", "absent", THREAD)
add(1265, "Unintended reentrant invocation of non-reentrant code", "absent", SIGNAL)

# ---------------------------------------------------------------- resources and denial of service
add(400, "Uncontrolled resource consumption", "runtime",
    'int main() { if (let n = validate_int(taint("100000000"))) { List<string> xs = new List<string>(); for (int i = 0; i < n; i += 1) { xs.push("row " + int_to_str(i)); } } return 0; }', "CWE-400",
    "The heap limit (CAPSTAN_MAX_HEAP; 64 MB in this test) stops runaway allocation safely. validate_range() bounds input values.")
add(770, "Allocation of resources without limits or throttling", "runtime",
    'int main() { List<string> all = new List<string>(); while (true) { all.push("request " + int_to_str(all.len())); } return 0; }', "CWE-400")
add(789, "Memory allocation with excessive size value", "runtime",
    'int main() { string s = "x"; for (int i = 0; i < 40; i += 1) { s = s + s; } return 0; }', "CWE-400")
add(834, "Excessive iteration", "logic",
    "int main() { for (int i = 0; i < 9223372036854775807; i += 1) { if (i == 3) { return 0; } } return 0; }",
    note="Loop bounds are a design decision.")
add(835, "Loop with unreachable exit condition (infinite loop)", "logic",
    "void spin() { int i = 0; while (i < 10) { i = i * 1; } }" + MAIN, note="Whether a loop terminates is undecidable in general (the halting problem).")
add(606, "Unchecked input for loop condition", "runtime",
    'int main() { if (let n = validate_int(taint("90000000"))) { List<int> xs = new List<int>(); for (int i = 0; i < n; i += 1) { xs.push(i); } } return 0; }', "CWE-400")
add(674, "Uncontrolled recursion", "runtime",
    "int down(int n) { return down(n + 1) + 1; }\nint main() { return down(0); }", "CWE-674")
add(407, "Inefficient algorithmic complexity", "logic",
    "int slow(int n) { if (n < 2) { return n; } return slow(n - 1) + slow(n - 2); }" + MAIN, note="Algorithm choice is a design decision.")
add(405, "Asymmetric resource consumption (amplification)", "na", note="Network concern.")
add(404, "Improper resource shutdown or release", "absent",
    "int main() { File f = open(\"x\"); return 0; }", note="Files are read and written whole; there are no handles to leak.")
add(772, "Missing release of resource after effective lifetime", "absent", "int main() { File f = open(\"x\"); return 0; }")
add(775, "Missing release of file descriptor or handle", "absent", "int main() { int fd = fopen(\"x\"); return 0; }")
add(459, "Incomplete cleanup", "absent", "int main() { File f = open(\"x\"); return 0; }")

# ---------------------------------------------------------------- code quality and logic
add(480, "Use of incorrect operator", "logic", "bool is_big(int n) { return n > 9; }" + MAIN, note="Which operator was meant is the programmer\'s intent.")
add(481, "Assigning instead of comparing", "absent", ASSIGN_IN_COND)
add(482, "Comparing instead of assigning", "reject", "int main() { int x = 0; x == 1; return x; }", "expression result is unused")
add(483, "Incorrect block delimitation", "absent",
    "int main() { int x = 0; if (x > 1) x = 2; x = 3; return x; }", note="Braces are mandatory.")
add(484, "Omitted break statement in switch", "absent", SWITCH,
    note="match has no fall-through between cases.")
add(478, "Missing default case in multiple condition expression", "reject",
    "enum Access { Read, Write, Admin }\nbool ok(Access a) { match (a) { case Read { return true; } case Write { return false; } } return false; }" + MAIN, "CWE-478",
    "match must handle every variant or have an else branch.")
add(561, "Dead code", "reject",
    "int f() { return 1; int unreachable = 2; }" + MAIN, "CWE-561", "Warning; an error with --strict (tested that way).")
add(563, "Assignment to variable without use", "reject",
    "int main() { int unused = 42; return 0; }", "CWE-563", "Warning; an error with --strict (tested that way).")
add(570, "Expression is always false", "reject",
    "int main() { if (false) { return 1; } return 0; }", "CWE-570", "Warning; an error with --strict (tested that way).")
add(571, "Expression is always true", "reject",
    "int main() { int x = 1; if (true) { x = 2; } return x; }", "CWE-571", "Warning; an error with --strict (tested that way).")
add(595, "Comparison of object references instead of object contents", "reject",
    "struct P { int x; }\nint main() { P a = new P{x: 1}; P b = new P{x: 1}; bool same = a == b; return 0; }", "cannot compare")
add(597, "Use of wrong operator in string comparison", "neutral",
    'int main() { string a = "ab"; string b = "a" + "b"; if (a == b) { println("equal by content"); } return 0; }', "equal by content",
    "== on strings compares contents, not references.")
add(697, "Incorrect comparison", "logic",
    'bool same_user(string a, string b) { return a.len() == b.len(); }' + MAIN, note="Comparison logic is intent.")
add(1023, "Incomplete comparison with missing factors", "logic", USERS + "bool same(User a, User b) { return a.id == b.id; }" + MAIN, note="As CWE-697.")
add(783, "Operator precedence logic error", "reject",
    "bool allowed(bool admin, bool owner, bool locked) { return admin || owner && !locked; }" + MAIN, "CWE-783",
    "Mixing && inside || without parentheses is a warning; an error with --strict (tested that way).")
add(843, "Access of resource using incompatible type (type confusion)", "absent", CAST)
add(670, "Always-incorrect control flow implementation", "logic", "int f(int x) { while (x > 0) { return 1; } return 0; }" + MAIN, note="Control-flow intent.")
add(489, "Active debug code", "reject",
    'const bool DEBUG = true;\nint main() { if (DEBUG) { println("debug mode"); } return 0; }', "CWE-489",
    "A debug switch left on is an error in --release builds (tested that way).")
add(546, "Suspicious comment", "reject", "// TODO: remove this backdoor before release" + MAIN, "CWE-546",
    "A warning; an error with --strict (tested that way).")
add(547, "Use of hard-coded, security-relevant constants", "reject",
    "bool is_admin(int role) { return role == 7; }" + MAIN, "CWE-547", "A warning; an error with --strict (tested that way).")
add(1164, "Irrelevant code", "reject",
    "int main() { int x = 1; x = x; return x; }", "CWE-1164", "Warning; an error with --strict (tested that way).")
add(912, "Hidden functionality", "logic",
    'bool login(Tainted user, Tainted pw) { if (user == "maintenance") { return true; } return verify_password(pw, "cap1$pbkdf2-sha256$600000$00$00"); }' + MAIN,
    note="A deliberate backdoor written as ordinary logic is indistinguishable from intended logic. Code review and Capstan Review (AI) are the defences.")
add(506, "Embedded malicious code", "na", note="Supply-chain concern; signed packages are planned.")
add(1104, "Use of unmaintained third-party components", "na", note="No package system yet.")
add(693, "Protection mechanism failure", "audited",
    'int main() { string s = trust(taint("x"), "temporary"); return 0; }', note="trust() is audited: it needs a justification and is reported in every build.")

# ---------------------------------------------------------------- data handling
add(1284, "Improper validation of specified quantity in input", "logic",
    "int main() { if (let l = read_line()) { if (let qty = validate_int(l)) { int total = qty * 10; } } return 0; }",
    note="Which range is valid is business knowledge; validate_range(t, min, max) makes enforcing it one call. Overflow is still caught.")
add(1287, "Improper validation of specified type in input", "neutral",
    'int main() { if (let n = validate_int(taint("12abc"))) { println("accepted"); } else { println("rejected"); } return 0; }', "rejected")
add(172, "Encoding error", "na", note="Strings are bytes; encodings are not interpreted.")
add(176, "Improper handling of Unicode encoding", "neutral",
    'int main() { if (let id = validate_ident(taint("adm\\0in"))) { println("accepted"); } else { println("rejected"); } return 0; }', "rejected")
add(178, "Improper handling of case sensitivity", "logic",
    'bool blocked(Tainted name) { return name == "admin"; }' + MAIN, note="Whether 'Admin' and 'admin' are the same name is a design decision.")
add(180, "Incorrect behaviour order: validate before canonicalize", "na", note="No canonicalisation API.")
add(345, "Insufficient verification of data authenticity", "na", note="No signature API yet.")
add(353, "Missing support for integrity check", "neutral",
    'int main() { string tag = hash("payload"); if (hash_verify("payload", tag)) { println("verified"); } return 0; }', "verified",
    "hash() and hash_verify() are available. Integrity is opt-in.")
add(841, "Improper enforcement of behavioral workflow", "logic",
    "void ship(int order) { }\nvoid pay(int order) { }" + MAIN, note="Workflow order is a design decision; typestate checking is a possible future feature.")
add(837, "Improper enforcement of a single, unique action", "logic", "void redeem(int voucher) { }" + MAIN, note="Business rule.")
add(799, "Improper control of interaction frequency", "logic", "void send_code(Tainted phone) { }" + MAIN, note="Rate limiting is a design decision.")
add(601, "URL redirection to untrusted site (open redirect)", "na", note="No web facility.")
add(918, "Server-side request forgery", "absent", NET)
add(1188, "Insecure default initialization of resource", "reject",
    "struct Config { bool tls; }\nint main() { Config c = new Config{}; return 0; }", "CWE-908",
    "There are no implicit defaults; every field must be given.")
add(1321, "Prototype pollution", "absent", REFLECT)
add(1341, "Multiple releases of same resource", "reject", FREE, "CWE-415")
add(1325, "Improperly controlled sequential memory allocation", "neutral",
    'int main() { List<string> xs = new List<string>(); for (int i = 0; i < 100000; i += 1) { xs.push("v" + int_to_str(i)); } println("done"); return 0; }', "done",
    "Collections grow geometrically with checked sizes.")
add(1386, "Insecure operation on Windows junction / mount point", "na", note="Platform file-system concern.")
add(1390, "Weak authentication", "na", note="Design concern.")
add(1391, "Use of weak credentials", "reject", "int main() { string root_password = \"admin\"; return 0; }", "CWE-798")
add(1392, "Use of default credentials", "reject", "int main() { string default_password = \"changeme\"; return 0; }", "CWE-798")
add(1393, "Use of default password", "reject", "int main() { string password = \"password\"; return 0; }", "CWE-798")
add(1394, "Use of default cryptographic key", "reject", "int main() { string private_key = \"-----BEGIN KEY-----\"; return 0; }", "CWE-798")


# Scalar metadata and conversion provenance must survive local variables and helper calls.
add(20, "Improper input validation (laundering through Tainted length)", "reject",
    "int length_of(Tainted input) { return input.len(); }\n"
    "int main() { if (let input = read_line()) { int n = length_of(input); char_str(n); } return 0; }",
    "CWE-20", "Length is derived metadata; helper summaries must preserve the Tainted parameter dependency.")

add(20, "Improper input validation (laundering through Boolean comparison)", "gap",
    "int main() { if (let input = read_line()) { bool matched = input.at(0) == 65; string output = to_text(matched); bool ok = write_file(\"out.txt\", output); } return 0; }",
    note="The current byte-reconstruction sink is not a general information-flow sink. Boolean comparison provenance is now tracked through locals, but the compiler does not yet define a policy for every control-flow observation.")

# ---------------------------------------------------------------- harness

# ---- found in the November 2026 attack review --------------------------------------------------
TABLE = "List<string> table = new List<string>(); for (int c = 0; c < 256; c += 1) { table.push(char_str(c)); } "
add(20, "Improper input validation (laundering through a lookup table)", "reject",
    "int main() { if (let t = read_line()) { " + TABLE + "string out = \"\"; for (int i = 0; i < t.len(); i += 1) { out = out + table[t.at(i)]; } sql_query(\"SELECT ?\", out); } return 0; }", "CWE-20",
    "Bytes of untrusted input are tainted integers: selecting trusted text with them (list index, slice, map key) is rejected.")
add(78, "OS command injection (through a shell named as the program)", "reject",
    'int main() { if (let t = read_line()) { run("sh", "-c", "--", t); } return 0; }', "CWE-78",
    "Shells, interpreters and launchers (sh, env, python, xargs and others) take only literal arguments.")
add(88, "Argument injection (computed argument read as an option)", "reject",
    'int main() { if (let t = read_line()) { if (let n = validate_int(t)) { run("head", "-n", int_to_str(n), "log"); } } return 0; }', "CWE-88",
    "Every computed argument must follow a literal \"--\"; validate_path() also refuses a leading '-'.")
add(79, "Cross-site scripting (escaped text in an unquoted attribute)", "reject",
    'int main() { if (let t = read_line()) { bool ok = write_file("p.html", "<img src=" + escape_html(t) + ">"); } return 0; }', "CWE-79")
add(79, "Cross-site scripting (escaped text in a URL attribute)", "reject",
    'int main() { if (let t = read_line()) { bool ok = write_file("p.html", "<a href=\"" + escape_html(t) + "\">x</a>"); } return 0; }', "CWE-79")
add(79, "Cross-site scripting (escaped text in a script block)", "reject",
    'int main() { if (let t = read_line()) { bool ok = write_file("p.html", "<script>var n = \'" + escape_html(t) + "\';</script>"); } return 0; }', "CWE-79")
add(79, "Cross-site scripting (Html assembled across separate statements)", "gap",
    'int main() { if (let t = read_line()) { Html v = escape_html(t); Html page = "<img src=" + v + ">"; bool ok = write_file("p.html", page); } return 0; }',
    note="The context of escaped text is checked only where escape_html() is called in the same expression as the literal HTML around it. Contextual HTML templates, which track context across statements, are on the roadmap.")
add(1007, "Insufficient visual distinction of homoglyphs and invisible characters (Trojan Source)", "reject",
    "int main() { bool admin = false; /* \u202e } \u2066if (admin)\u2069 \u2066 */ return 0; }", "CWE-1007",
    "Bidirectional controls and zero-width characters are rejected anywhere in source (CVE-2021-42574).")
add(532, "Insertion of sensitive information into output (hash of a secret)", "reject",
    'int main() { if (let s = secret_env("PIN")) { println(hash(s)); } return 0; }', "CWE-532",
    "A fast hash of a short secret is reversed by trying every value.")
add(367, "Time-of-check time-of-use (grant used after the checked data changed)", "runtime",
    "struct User { int id; }\nsensitive struct Doc { int owner; string body; }\npolicy CanRead(User u, Doc d, int to) { return u.id == d.owner && to >= 0; }\n"
    "protected(CanRead) string read_doc(Grant<CanRead> g, Doc d) { return d.body; }\n"
    "protected(CanRead) void transfer(Grant<CanRead> g, Doc d, int to) { d.owner = to; }\n"
    "test \"deny\" { assert_denied CanRead(new User{id: 1}, new Doc{owner: 2, body: \"x\"}, 2); }\n"
    "int main() { User me = new User{id: 1}; Doc d = new Doc{owner: 1, body: \"p\"}; if (let g = authorize CanRead(me, d, 2)) { transfer(g, d, 2); println(read_doc(g, d)); } return 0; }",
    "CWE-367", "Each protected call evaluates the policy again on the grant's arguments.")


STRICT_NOTE = "--strict"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, timeout=60, **kw)


def check(e, d):
    code = e["code"]
    if code is None:
        return None
    if "int main(" not in code and "void main(" not in code:
        code += MAIN
    cap, c, exe = (os.path.join(d, n) for n in ("a.cap", "a.c", "a"))
    open(cap, "w").write(code)
    flags = ["--strict"] if STRICT_NOTE in e["note"] else []
    if "--release" in e["note"]:
        flags.append("--release")
    comp = run([os.environ.get("CAPSTANC", os.path.join(ROOT, "build/capstanc")), "build", "-o", c] + flags + [cap])
    out = comp.stdout.decode(errors="replace")
    v = e["verdict"]
    if v == "absent":
        return None if comp.returncode == 1 else f"construct unexpectedly compiles (exit {comp.returncode})"
    if v == "reject":
        if comp.returncode != 1:
            return f"expected rejection containing {e['expect']!r}, but it compiled"
        return None if e["expect"] in out else f"rejected, but without {e['expect']!r}: {out.strip()[:200]}"
    if comp.returncode != 0:
        return f"expected to compile ({v}) but: {out.strip()[:300]}"
    if v in ("gap", "logic"):
        return None
    if v == "audited":
        return None if "AUDIT" in out else "expected an AUDIT warning"
    b = run([CC, "-std=gnu11", "-O1", "-w", "-I" + os.path.join(ROOT, "runtime"), c, "-o", exe])
    if b.returncode != 0:
        return "generated C did not compile"
    try:
        r = subprocess.run([exe], capture_output=True, timeout=60, env=dict(os.environ, CAPSTAN_MAX_HEAP="64M", KEY="k", API_KEY="k", TOKEN="t", DB_KEY="k", DB_PASSWORD="p"))
    except subprocess.TimeoutExpired:
        return "program did not finish"
    so, se = r.stdout.decode(errors="replace"), r.stderr.decode(errors="replace")
    if v == "runtime":
        return None if r.returncode == 101 and e["expect"] in se else f"expected safe stop {e['expect']}, got exit {r.returncode}: {se.strip()[:200]}"
    if v == "neutral":
        if e["cwe"] == 210:
            return None if r.returncode == 101 and "list index" in se and "[" in se and "=" not in se.split("prevented")[0].split("check failed:")[-1] else f"unexpected: {se}"
        if e["cwe"] == 789:
            return None if r.returncode in (101, 102) else f"expected a clean stop, got {r.returncode}"
        return None if r.returncode == 0 and e["expect"] in so else f"expected output containing {e['expect']!r}, got exit {r.returncode}: {so.strip()[:200]} {se.strip()[:200]}"
    return f"unknown verdict {v}"


LABEL = {
    "reject": "Prevented: rejected at compile time",
    "runtime": "Prevented: stopped safely at run time",
    "neutral": "Prevented: attempt compiles but has no effect",
    "absent": "Inexpressible: the construct does not exist",
    "gap": "**Gap: can be written**",
    "audited": "Possible only through an audited escape hatch",
    "logic": "Logic or design decision: beyond any language",
    "na": "Not applicable (yet)",
}


def write_doc(results):
    by = {}
    for e in E:
        by.setdefault(e["verdict"], []).append(e)
    ids = sorted({e["cwe"] for e in E})
    worst = {}
    order = ["gap", "logic", "audited", "na", "neutral", "runtime", "reject", "absent"]
    for e in E:
        cur = worst.get(e["cwe"])
        if cur is None or order.index(e["verdict"]) < order.index(cur):
            worst[e["cwe"]] = e["verdict"]
    lines = [
        "# CWE atlas: red-teaming Capstan",
        "",
        "For each code-level weakness in the CWE list, the atlas holds the most natural attempt to write it",
        "in Capstan, plus deliberate workarounds (laundering untrusted input, hiding credentials under",
        "innocuous names, using the wrong escaper). Every verdict is an executable test in",
        "`tests/cwe/atlas.py`, re-checked by the test suite against the current compiler.",
        "",
        "The rest of the CWE list (hardware design, organisational and process weaknesses, and",
        "categories and views) is outside scope: it describes things program code cannot express.",
        "Attempts are written from the CWE descriptions; this atlas is not an official MITRE mapping.",
        "",
        f"**{len(ids)} weaknesses, {len(E)} attempts.** Counting each weakness once, by its weakest attempt:",
        "",
        "| Outcome | Weaknesses |",
        "|---|---|",
    ]
    for v in ["reject", "runtime", "neutral", "absent", "audited", "logic", "gap", "na"]:
        lines.append(f"| {LABEL[v]} | {sum(1 for c in ids if worst[c] == v)} |")
    lines += ["", "## Gaps: weaknesses that can still be written", "",
              "These are honest limits of the current version. Each is a test, so when a future version",
              "closes a gap the test fails and the entry is reclassified.", "",
              "| CWE | Weakness | What was written | Why it compiles, and the plan |", "|---|---|---|---|"]
    for e in E:
        if e["verdict"] == "gap":
            first = e["code"].strip().splitlines()
            snippet = next((l for l in first if l.strip() and not l.startswith("struct") and "int main() { return 0; }" not in l), first[0])
            snippet = snippet.replace("|", "\\|")
            if len(snippet) > 90:
                snippet = snippet[:87] + "..."
            lines.append(f"| [{e['cwe']}](https://cwe.mitre.org/data/definitions/{e['cwe']}.html) | {e['name']} | `{snippet}` | {e['note']} |")
    lines += ["", "## Beyond any language: logic and design decisions", "",
              "These weaknesses can be written in Capstan because they are not mistakes in *how* code is written but",
              "in *what* it was meant to do: a wrong formula, a missing business rule, a policy that is consistent but",
              "wrong. No compiler can tell them from intended behaviour. Each attempt still compiles here, as a test.", "",
              "| CWE | Weakness | Why | ", "|---|---|---|"]
    for e in E:
        if e["verdict"] == "logic":
            lines.append(f"| [{e['cwe']}](https://cwe.mitre.org/data/definitions/{e['cwe']}.html) | {e['name']} | {e['note']} |")
    lines += ["", "## Full atlas", "", "| CWE | Weakness | Outcome | Detail |", "|---|---|---|---|"]
    for e in sorted(E, key=lambda x: (x["cwe"], x["verdict"])):
        detail = e["note"]
        if e["verdict"] in ("reject", "runtime") and e["expect"]:
            detail = (f"`{e['expect']}`. " + detail).strip()
        lines.append(f"| [{e['cwe']}](https://cwe.mitre.org/data/definitions/{e['cwe']}.html) | {e['name']} | {LABEL[e['verdict']]} | {detail} |")
    lines.append("")
    open(os.path.join(ROOT, "docs/CWE-ATLAS.md"), "w").write("\n".join(lines))


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        for e in E:
            err = check(e, d)
            if err:
                failures += 1
                print(f"  FAIL  CWE-{e['cwe']} {e['name']} [{e['verdict']}]: {err}")
    ids = {e["cwe"] for e in E}
    gaps = sorted({e["cwe"] for e in E if e["verdict"] == "gap"})
    if "--write-doc" in sys.argv:
        write_doc(None)
    logic = sorted({e["cwe"] for e in E if e["verdict"] == "logic"})
    print(f"CWE atlas: {len(E)} attempts across {len(ids)} weaknesses, {failures} verdict(s) wrong; "
          f"{len(gaps)} gaps, {len(logic)} logic/design weaknesses beyond any language")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
