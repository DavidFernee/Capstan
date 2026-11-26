#!/usr/bin/env python3
"""Language server sessions: capstan-lsp must agree with the compiler and follow the protocol.

  python3 -I tests/lsp/sessions.py build/capstan-lsp

1. Agreement: every program in tests/reject, tests/diagnostics and tests/accept is opened
   in the server, and the published diagnostics must be exactly those `capstanc` reports
   for it (line, column, severity, code, message; the CWE code linked to cwe.mitre.org),
   including the test's own `// expect:` text, then cleared again when it is closed.
2. Protocol: lifecycle (requests before initialize, a second initialize, shutdown, exit
   codes), full and incremental document sync, UTF-16 and UTF-8 positions, imports,
   --strict and --release through initializationOptions, and JSON-RPC errors for
   malformed JSON, invalid requests, unknown methods, bad framing and oversized messages,
   each followed by a request that must still be answered.
"""
# spec: tools.lsp
import json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Server  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPSTANC = os.path.join(ROOT, "build", "capstanc")
LINE = re.compile(r"^(.+?):(\d+)(?::(\d+))?: (error|warning)(?:\[([^\]]*)\])?: (.*)$")
failures = []
checks = 0


def check(cond, what):
    global checks
    checks += 1
    if not cond:
        failures.append(what)
    return cond


def uri_of(path):
    return "file://" + os.path.abspath(path)


def utf16_len(b):
    return len(b.decode("utf-8", "replace").encode("utf-16-le")) // 2


def expected_diags(path, flags):
    """What capstanc reports for a file: build mode, less 'no main' (the server checks libraries too)."""
    rel = os.path.relpath(path, ROOT)
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run([CAPSTANC, "build", "-o", os.path.join(d, "x.c")] + flags + [rel],
                             cwd=ROOT, capture_output=True, text=True).stdout
    diags = []
    for line in out.splitlines():
        m = LINE.match(line)
        if not m:
            continue
        f, ln, col, sev, code, msg = m.groups()
        if msg == "program has no main() function":
            continue
        diags.append({"file": f, "line": int(ln), "col": int(col or 0), "error": sev == "error",
                      "code": code or "", "msg": msg})
    return rel, diags


def lsp_code(d):
    if d["code"]:
        return d["code"]
    m = re.search(r"\[(CWE-\d+)\]$", d["msg"])
    return m.group(1) if m else ""


def compare(path, flags, got, src_lines):
    rel, want = expected_diags(path, flags)
    imports = {}
    for i, text in enumerate(src_lines):
        m = re.match(r'\s*import\s+"([^"]*)"', text.decode("utf-8", "replace"))
        if m:
            imports[os.path.normpath(os.path.join(os.path.dirname(rel), m.group(1)))] = (i, text.index(b"import"))
    exp = []
    for d in want:
        msg = d["msg"]
        if d["file"] == rel:
            line = max(d["line"], 1) - 1
            col = d["col"]
        else:   # shown on the import that brought the file in
            where = d["file"] + (":%d" % d["line"] if d["line"] else "") + (":%d" % d["col"] if d["col"] else "")
            msg = "in %s: %s" % (where, msg)
            line, c0 = imports.get(os.path.normpath(d["file"]), (0, 0))
            col = c0 + 1
        text = src_lines[line] if line < len(src_lines) else b""
        if col > 0:
            ch = utf16_len(text[:col - 1])
        else:
            ch = utf16_len(text[:len(text) - len(text.lstrip(b" \t"))])
        code = lsp_code(d)
        href = "https://cwe.mitre.org/data/definitions/%s.html" % code[4:] if re.fullmatch(r"CWE-\d+", code) else None
        exp.append((line, ch, 1 if d["error"] else 2, code, href, msg))
    have = []
    for g in got:
        have.append((g["range"]["start"]["line"], g["range"]["start"]["character"], g["severity"], g.get("code", ""),
                     g.get("codeDescription", {}).get("href"), g["message"]))
        if g["range"]["end"]["line"] != g["range"]["start"]["line"] or g["range"]["end"]["character"] < g["range"]["start"]["character"]:
            check(False, "%s: bad range %r" % (rel, g["range"]))
        if g.get("source") != "capstan":
            check(False, "%s: source is %r" % (rel, g.get("source")))
    if not check(have == exp, "%s: diagnostics differ from capstanc\n      server:   %r\n      capstanc: %r" % (rel, have, exp)):
        return False
    expect = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("// expect: "):
                expect = line[len("// expect: "):].strip()
                break
    if expect and expect != "program has no main() function":     # the server also checks libraries
        texts = []
        for (line, ch, sev, code, _, msg) in have:
            col = len(src_lines[line][:ch].decode("utf-8", "replace").encode()) + 1 if line < len(src_lines) else 1
            label = ("error" if sev == 1 else "warning") + ("[%s]" % code if code else "")
            texts.append("%d:%d: %s: %s" % (line + 1, col, label, msg))
        check(any(expect in t for t in texts), "%s: expected '%s' among %r" % (rel, expect, texts))
    return True


def session(exe, options=None, utf8=False):
    s = Server(exe, cwd=ROOT)
    caps = {"general": {"positionEncodings": ["utf-8", "utf-16"]}} if utf8 else {}
    params = {"processId": None, "rootUri": uri_of(ROOT), "capabilities": caps}
    if options is not None:
        params["initializationOptions"] = options
    s.request(1, "initialize", params)
    r = s.recv()
    check(r.get("id") == 1 and "capabilities" in r.get("result", {}), "initialize reply: %r" % r)
    s.notify("initialized", {})
    return s, r


def finish(s, name, id=999):
    s.request(id, "shutdown")
    r, _ = s.recv_until(lambda m: m.get("id") == id)
    check(r.get("result", 1) is None, "%s: shutdown reply %r" % (name, r))
    s.notify("exit")
    code = s.close()
    check(code == 0, "%s: exit after shutdown gave %s" % (name, code))
    err = s.p.stderr.read()
    check(not err, "%s: stderr: %r" % (name, err[:300]))


def publish_for(s, uri):
    m, _ = s.recv_until(lambda m: m.get("method") == "textDocument/publishDiagnostics" and m["params"]["uri"] == uri)
    return m["params"]


def agreement(exe):
    files = []
    for d in ("reject", "diagnostics", "accept"):
        files += sorted(os.path.join(ROOT, "tests", d, f) for f in os.listdir(os.path.join(ROOT, "tests", d)) if f.endswith(".cap"))
    groups = {}
    for f in files:
        flags = ""
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("// flags: "):
                    flags = line[len("// flags: "):].strip()
                    break
        groups.setdefault(flags, []).append(f)
    agreed = 0
    for flags, group in sorted(groups.items()):
        fl = flags.split()
        s, _ = session(exe, {"strict": "--strict" in fl, "release": "--release" in fl})
        for n, f in enumerate(group):
            with open(f, "rb") as fh:
                data = fh.read()
            uri = uri_of(f)
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue    # LSP carries text as Unicode; such a file cannot be opened in an editor as is
            s.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": "capstan", "version": n, "text": text}})
            p = publish_for(s, uri)
            check(p.get("version") == n, "%s: version %r" % (f, p.get("version")))
            if compare(f, fl, p["diagnostics"], data.split(b"\n")):
                agreed += 1
            s.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
            p = publish_for(s, uri)
            check(p["diagnostics"] == [], "%s: diagnostics not cleared on close" % f)
        finish(s, "agreement " + flags)
    return agreed, len(files)


def expect_error(s, id, code, name, after=None):
    """The next reply for id must be an error with code; then a request must still be answered."""
    m, _ = s.recv_until(lambda m: "id" in m and m["id"] == id and "method" not in m)
    check(m.get("error", {}).get("code") == code, "%s: expected error %s, got %r" % (name, code, m))
    return m


def alive(s, name, id):
    s.request(id, "capstan/unknown")
    m, _ = s.recv_until(lambda m: m.get("id") == id)
    check(m.get("error", {}).get("code") == -32601, "%s: server did not answer afterwards: %r" % (name, m))


def protocol(exe):
    uri = "file:///virtual/main.cap"

    # Lifecycle before initialize.
    s = Server(exe)
    s.request("a", "textDocument/hover", {})
    expect_error(s, "a", -32002, "request before initialize")
    s.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "version": 1, "text": "int main() { return x; }"}})
    s.request(1, "initialize", {"capabilities": {}})
    m = s.recv()
    check(m.get("id") == 1 and m["result"]["capabilities"]["positionEncoding"] == "utf-16" and m["result"]["capabilities"]["textDocumentSync"]["change"] == 1,
          "notification before initialize must be dropped, then initialize answered: %r" % m)
    s.request(2, "initialize", {"capabilities": {}})
    expect_error(s, 2, -32600, "second initialize")
    s.request(3, "shutdown")
    m = s.recv()
    check(m == {"jsonrpc": "2.0", "id": 3, "result": None}, "shutdown: %r" % m)
    s.request(4, "shutdown")
    expect_error(s, 4, -32600, "request after shutdown")
    s.notify("exit")
    check(s.close() == 0, "exit after shutdown must give 0")

    s = Server(exe)
    s.request(1, "initialize", {"capabilities": {}})
    s.recv()
    s.notify("exit")
    check(s.close() == 1, "exit without shutdown must give 1")
    s = Server(exe)
    check(s.close() == 1, "end of input without shutdown must give 1")

    # Document sync, versions, closing.
    s, _ = session(exe)
    s.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "languageId": "capstan", "version": 1,
                                                       "text": "int main() {\n    return x;\n}\n"}})
    p = publish_for(s, uri)
    check(len(p["diagnostics"]) == 1 and p["diagnostics"][0]["message"].startswith("unknown variable 'x'")
          and p["diagnostics"][0]["range"] == {"start": {"line": 1, "character": 11}, "end": {"line": 1, "character": 12}},
          "didOpen diagnostics: %r" % p)
    s.notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": 2},
                                        "contentChanges": [{"text": "int main() {\n    return 0;\n}\n"}]})
    p = publish_for(s, uri)
    check(p == {"uri": uri, "version": 2, "diagnostics": []}, "full change clears diagnostics: %r" % p)
    s.notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": 3}, "contentChanges": [
        {"range": {"start": {"line": 1, "character": 11}, "end": {"line": 1, "character": 12}}, "text": "count"}]})
    p = publish_for(s, uri)
    check(p["version"] == 3 and [d["message"] for d in p["diagnostics"]] == ["unknown variable 'count'"],
          "incremental change: %r" % p)
    s.notify("textDocument/didChange", {"textDocument": {"uri": "file:///not/open.cap", "version": 1}, "contentChanges": [{"text": ""}]})
    m = s.recv()
    check(m.get("method") == "window/logMessage", "change to a closed document is logged: %r" % m)
    s.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
    p = publish_for(s, uri)
    check(p["diagnostics"] == [], "close clears diagnostics")

    # The golden file: exact ranges, severities, codes and links for tests/lsp/diagnostics.cap.
    golden = os.path.join(ROOT, "tests", "lsp", "diagnostics.cap")
    with open(golden, encoding="utf-8") as fh:
        s.notify("textDocument/didOpen", {"textDocument": {"uri": uri_of(golden), "version": 1, "text": fh.read()}})
    with open(golden[:-4] + ".json", encoding="utf-8") as fh:
        want = json.load(fh)
    got = publish_for(s, uri_of(golden))["diagnostics"]
    check(got == want, "tests/lsp/diagnostics.cap: published %s" % json.dumps(got, ensure_ascii=False))

    # Positions: UTF-16 code units by default, bytes when the client offers utf-8.
    line = 'int main() { string s = "é\U0001F600"; return s + 1; }'
    for utf8 in (False, True):
        s2, r = session(exe, utf8=utf8)
        check(r["result"]["capabilities"]["positionEncoding"] == ("utf-8" if utf8 else "utf-16"), "encoding negotiation")
        s2.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "version": 1, "text": line + "\n"}})
        d = publish_for(s2, uri)["diagnostics"]
        prefix = line[:line.index("s + 1") + 2]
        want = len(prefix.encode("utf-8")) if utf8 else len(prefix.encode("utf-16-le")) // 2
        check(len(d) == 1 and d[0]["range"]["start"]["character"] == want, "positions (utf8=%s): %r, want %d" % (utf8, d, want))
        finish(s2, "positions")

    # JSON escapes: a document sent with every non-ASCII character escaped is the same document.
    s3, _ = session(exe)
    body = json.dumps({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {
        "uri": "file:///virtual/ümläut.cap", "version": 7, "text": line + "\n"}}}, ensure_ascii=True).encode()
    s3.send(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    p = publish_for(s3, "file:///virtual/ümläut.cap")
    check(p["version"] == 7 and len(p["diagnostics"]) == 1 and p["diagnostics"][0]["range"]["start"]["character"] == len(prefix.encode("utf-16-le")) // 2,
          "\\u escapes and surrogate pairs decode to the same text: %r" % p)
    finish(s3, "escapes")

    # Imports: from open documents, and from disk inside the workspace.
    s, _ = session(exe)
    lib = "file:///virtual/lib/util.cap"
    s.notify("textDocument/didOpen", {"textDocument": {"uri": lib, "version": 1, "text": "int twice(int x) { return x * 2; }\n"}})
    publish_for(s, lib)
    s.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "version": 1,
                                                       "text": 'import "lib/util.cap";\nint main() { return twice(2); }\n'}})
    check(publish_for(s, uri)["diagnostics"] == [], "import of an open document")
    s.notify("textDocument/didChange", {"textDocument": {"uri": lib, "version": 2}, "contentChanges": [{"text": "int twice(int x) { return y; }\n"}]})
    publish_for(s, lib)
    s.notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": 2}, "contentChanges": [{"text": '// uses twice()\n  import "lib/util.cap";\n'}]})
    d = publish_for(s, uri)["diagnostics"]
    check(len(d) == 1 and d[0]["message"].startswith("in lib/util.cap:1:27: unknown variable 'y'") and d[0]["range"]["start"] == {"line": 1, "character": 2},
          "an error in an imported file is shown on its import: %r" % d)
    s.notify("textDocument/didChange", {"textDocument": {"uri": uri, "version": 3}, "contentChanges": [{"text": 'import "nowhere.cap";\n'}]})
    d = publish_for(s, uri)["diagnostics"]
    check(len(d) == 1 and d[0]["message"] == "cannot read imported file 'nowhere.cap' (missing, unreadable, a directory, or over 16 MiB)", "missing import: %r" % d)
    finish(s, "imports")

    # --strict and --release through initializationOptions.
    src = "int main() { int unused = 1; return 0; }\n"
    for opts, sev in ((None, 2), ({"strict": True}, 1)):
        s, _ = session(exe, opts)
        s.notify("textDocument/didOpen", {"textDocument": {"uri": uri, "version": 1, "text": src}})
        d = publish_for(s, uri)["diagnostics"]
        check([(x["code"], x["severity"]) for x in d] == [("CWE-563", sev)], "strict=%r: %r" % (opts, d))
        finish(s, "strict")

    # Malformed messages: each gets the JSON-RPC error, and the server keeps working.
    s, _ = session(exe)
    n = 100
    bad_bodies = [
        (b"{bad json", -32700, "invalid JSON"),
        (b"", -32700, "empty body"),
        (b"[1, 2]", -32600, "an array"),
        (b'"text"', -32600, "a string"),
        (b'{"jsonrpc": "2.0", "id": 1, "method": "x"} trailing', -32700, "data after the value"),
        (b'{"jsonrpc": "2.0", "id": {"a": 1}, "method": "x"}', -32600, "an object id"),
        (b'{"jsonrpc": "2.0", "id": 1.5, "method": "x"}', -32600, "a fractional id"),
        (b'{"jsonrpc": "2.0", "method": "x", "id": "\xff"}', -32700, "invalid UTF-8"),
        (b'{"jsonrpc": "2.0", "method": "x", "id": "a\x01"}', -32700, "a raw control character"),
        (b'{"jsonrpc": "2.0", "method": "x", "id": "\\x"}', -32700, "an invalid escape"),
        (b"[" * 100000 + b"]" * 100000, -32700, "deep nesting"),
        (b'{"jsonrpc": "2.0", "method": "x", "id": 1e999999999999999999}', None, None),
    ]
    # The JSON parser bounds aggregate values, members, elements, string bytes,
    # escape-fragment amplification and number-token length independently.
    value_fanout = b"[" + b",".join(
        b"[" + b",".join([b"null"] * 16) + b"]" for _ in range(4096)
    ) + b"]"
    too_many_members = b"{" + b",".join(
        b'"k%d":null' % i for i in range(4097)
    ) + b"}"
    too_many_elements = b"[" + b",".join([b"null"] * 16385) + b"]"
    long_string = b'{"s":"' + b"a" * (8 * 1024 * 1024 + 1) + b'"}'
    escape_fragments = b'"' + b"\\n" * 131073 + b'"'
    aggregate_strings = b"[" + b",".join(
        b'"' + b"a" * (7 * 1024 * 1024) + b'"' for _ in range(2)
    ) + b"]"
    exact_nested = b"[" + b",".join([b"null"] * 15) + b"]"
    exact_values = b"[" + b",".join([exact_nested] * 4095 + [b"null"] * 15) + b"]"
    exact_members = b"{" + b",".join(b'"k%d":null' % i for i in range(4096)) + b"}"
    exact_elements = b"[" + b",".join([b"null"] * 16384) + b"]"
    exact_string = b'"' + b"a" * (8 * 1024 * 1024) + b'"'
    exact_aggregate_strings = b'["' + b"a" * (6 * 1024 * 1024) + b'","' + b"a" * (6 * 1024 * 1024) + b'"]'
    exact_fragments = b'"' + b"\\n" * 131069 + b"\\uD83D\\uDE00" + b'"'
    exact_number = b"1" * 128
    aggregate_parts = b"[" + b",".join([exact_fragments] * 3) + b"]"
    bad_bodies.extend([
        (exact_values, -32600, "exact JSON value budget"),
        (exact_members, -32600, "exact JSON object member budget"),
        (exact_elements, -32600, "exact JSON array element budget"),
        (exact_string, -32600, "exact JSON per-string byte budget"),
        (exact_aggregate_strings, -32600, "exact JSON aggregate string byte budget"),
        (exact_fragments, -32600, "exact JSON string fragment budget"),
        (exact_number, -32600, "exact JSON number token budget"),
        (b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"method":"x"}', -32700, "duplicate object key"),
        (value_fanout, -32700, "aggregate JSON value budget"),
        (too_many_members, -32700, "JSON object member budget"),
        (too_many_elements, -32700, "JSON array element budget"),
        (long_string, -32700, "JSON per-string byte budget"),
        (escape_fragments, -32700, "JSON string fragment budget"),
        (aggregate_strings, -32700, "JSON aggregate string byte budget"),
        (aggregate_parts, -32700, "JSON aggregate string fragment budget"),
        (b"1" * 129, -32700, "JSON number token byte budget"),
    ])
    for body, code, name in bad_bodies:
        s.send(b"Content-Length: %d\r\n\r\n" % len(body) + body)
        if code is None:
            m, _ = s.recv_until(lambda m: "error" in m)
            check(m["error"]["code"] == -32600, "a huge exponent id is not an integer: %r" % m)
        else:
            m = s.recv()
            check(m.get("id") is None and m.get("error", {}).get("code") == code, "%s: %r" % (name, m))
        n += 1
        alive(s, name, n)
    for msg, code, name in [
        ({"id": 5, "method": "shutdown"}, -32600, "missing jsonrpc"),
        ({"jsonrpc": "1.0", "id": 6, "method": "shutdown"}, -32600, "wrong jsonrpc"),
        ({"jsonrpc": "2.0", "id": 7, "method": 42}, -32600, "a numeric method"),
        ({"jsonrpc": "2.0", "id": 8, "method": "shutdown", "params": 3}, -32602, "scalar params"),
        ({"jsonrpc": "2.0", "id": 9}, -32600, "no method"),
        ({"jsonrpc": "2.0", "id": "str-id", "method": "workspace/symbol", "params": {}}, -32601, "an unknown method"),
    ]:
        s.send(msg)
        m = expect_error(s, msg["id"], code, name)
        n += 1
        alive(s, name, n)
    # Notifications and responses that need no reply produce none.
    s.notify("$/cancelRequest", {"id": 1})
    s.notify("workspace/didChangeConfiguration", {"settings": {}})
    s.send({"jsonrpc": "2.0", "id": 77, "result": None})
    s.send({"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {"textDocument": {"uri": 3}}})
    m = s.recv()
    check(m.get("method") == "window/logMessage", "malformed didOpen is logged: %r" % m)
    n += 1
    alive(s, "silent notifications", n)
    check(s.q.empty(), "notifications and client responses must not be answered")

    # Framing.
    framing = [
        (b"Content-Type: application/json\r\n\r\n", "no Content-Length"),
        (b"Content-Length: abc\r\n\r\n", "a non-numeric length"),
        (b"Content-Length: -5\r\n\r\n", "a negative length"),
        (b"Content-Length: 99999999999999999999999\r\n\r\n", "a length that does not fit"),
        (b"garbage\r\n\r\n", "a garbage header"),
        (b"x" * 200000 + b"\r\n\r\n", "a 200 KB header line"),
        (b"Content-Length: 2\r\nContent-Length: 2\r\n\r\n{}", "two lengths"),
        (b"".join(b"X-%d: y\r\n" % i for i in range(50)) + b"\r\n", "too many headers"),
    ]
    for raw, name in framing:
        s.send(raw)
        m = s.recv()
        check(m.get("id") is None and m.get("error", {}).get("code") == -32700, "%s: %r" % (name, m))
        # Some of these are followed by a second error as the server resynchronises.
        n += 1
        s.request(n, "capstan/unknown")
        m, _ = s.recv_until(lambda m: m.get("id") == n)
        check(m["error"]["code"] == -32601, "%s: no recovery" % name)
    # A body without a header, then a message: the server resynchronises at its Content-Length.
    body = json.dumps({"jsonrpc": "2.0", "id": 500, "method": "capstan/unknown"}).encode()
    s.send(body + b"Content-Length: %d\r\n\r\n" % len(body) + body)
    m = s.recv()
    check(m.get("error", {}).get("code") == -32700, "headerless body is reported: %r" % m)
    m = s.recv()
    check(m.get("id") == 500, "resynchronised at the next Content-Length: %r" % m)
    # Headers with extra whitespace and a Content-Type are accepted; bare \n line ends too.
    s.send(b"Content-Length:   %d  \nContent-Type: application/vscode-jsonrpc; charset=utf-8\n\n" % len(body) + body)
    m = s.recv()
    check(m.get("id") == 500, "lenient header: %r" % m)
    s.send(b"Content-Type: application/vscode-jsonrpc; charset=utf-8\r\nContent-Length: %d\r\n\r\n" % len(body) + body)
    m = s.recv()
    check(m.get("id") == 500, "Content-Type before Content-Length: %r" % m)
    # An oversized message is skipped without being stored.
    big = 16 * 1024 * 1024 + 1
    s.send(b"Content-Length: %d\r\n\r\n" % big + b" " * big)
    m = s.recv(timeout=60)
    check(m.get("error", {}).get("code") == -32600 and "CWE-400" in m["error"]["message"], "oversized message: %r" % m)
    n += 1
    alive(s, "oversized message", n)
    finish(s, "malformed")


def main():
    exe = os.path.abspath(sys.argv[1])
    agreed, total = agreement(exe)
    protocol(exe)
    if failures:
        for f in failures[:30]:
            print("  " + f)
        print("%d of %d language server checks failed" % (len(failures), checks))
        return 1
    print("language server: %d of %d programs give exactly the compiler's diagnostics; %d checks pass"
          % (agreed, total, checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
