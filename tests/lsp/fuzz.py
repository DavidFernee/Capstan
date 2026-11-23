#!/usr/bin/env python3
"""Robustness fuzzing for capstan-lsp.

    python3 -I tests/lsp/fuzz.py build/capstan-lsp SESSIONS SEED

Each session starts a server, initializes it and sends a random stream. Half the
sessions keep the framing intact and fuzz everything inside it: random JSON values,
random requests and notifications with random parameters, corrupted JSON bodies, and
documents (mutated programs from the repository, with random encodings and random
incremental edits) that go through the compiler's lexer, parser and checker. Those
sessions must still answer a final shutdown request and exit with code 0. The other
half also corrupt the framing itself: flipped, inserted and deleted bytes, wrong
Content-Lengths, random bytes and headers. There the server must exit as soon as its
input closes.

Always: no crash, no runtime stop, nothing on standard error, no hang (every session
has a deadline), and every byte the server writes is a well-framed JSON message in
valid UTF-8 with no raw control characters or line separators. A failing session's
input is saved in tests/lsp/failures/.
"""
# spec: tools.lsp
import json, os, random, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from client import Server, frame, read_frames, FramingError  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
METHODS = ["initialize", "initialized", "shutdown", "textDocument/didOpen", "textDocument/didChange",
           "textDocument/didClose", "textDocument/didSave", "textDocument/hover", "textDocument/definition",
           "$/cancelRequest", "$/setTrace", "workspace/didChangeConfiguration", "", "é", "x" * 300]
KEYS = ["jsonrpc", "id", "method", "params", "textDocument", "uri", "text", "version", "contentChanges",
        "range", "start", "end", "line", "character", "capabilities", "general", "positionEncodings",
        "initializationOptions", "strict", "release", "rootUri", "workspaceFolders", "result", "error"]
STATS = {"messages": 0, "checked": 0, "bytes": 0}
URIS = ["file:///f/a.cap", "file:///f/lib/util.cap", "file:///f/b.cap", "untitled:1", "", "file:///f/%zz.cap"]


def sources():
    files = []
    for d in ("tests/accept", "tests/reject", "tests/diagnostics", "tests/runtime", "examples"):
        for f in sorted(os.listdir(os.path.join(ROOT, d))):
            if f.endswith(".cap"):
                with open(os.path.join(ROOT, d, f), "rb") as fh:
                    files.append(fh.read())
    return files


def mutate_bytes(rng, data, n=None):
    data = bytearray(data)
    for _ in range(n if n is not None else rng.randint(1, 6)):
        op = rng.randrange(5)
        i = rng.randint(0, len(data))
        if op == 0 and data:
            data[min(i, len(data) - 1)] = rng.randrange(256)
        elif op == 1:
            data[i:i] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 8)))
        elif op == 2:
            del data[i:i + rng.randint(1, 40)]
        elif op == 3:
            j = rng.randint(0, len(data))
            data[i:i] = data[j:j + rng.randint(1, 60)]
        else:
            data[i:i] = rng.choice([b"{", b"}", b"(", b")", b'"', b"\n", b"\\", b"$\"{", b"/*", b"Tainted ", b"import \"x.cap\";"])
    return bytes(data)


def rand_json(rng, depth=0):
    r = rng.randrange(9 if depth < 5 else 6)
    if r == 0:
        return None
    if r == 1:
        return rng.choice([True, False])
    if r == 2:
        return rng.choice([0, -1, 1, 2**31, 2**63, -2**63 - 1, 10**30, 1.5, -0.0, 1e300])
    if r in (3, 4, 5):
        return rng.choice(["", "x", "\u0000", "\ud800", "\U0001F600", "file:///f/a.cap", "utf-8", "2.0"]
                          + METHODS + KEYS)
    if r == 6:
        return [rand_json(rng, depth + 1) for _ in range(rng.randint(0, 4))]
    return {rng.choice(KEYS): rand_json(rng, depth + 1) for _ in range(rng.randint(0, 5))}


def rand_pos(rng):
    return {"line": rng.choice([0, 1, 2, 5, 100, -1, 2**40]), "character": rng.choice([0, 1, 3, 9, 1000, -3])}


def doc_message(rng, srcs, version):
    text = rng.choice(srcs)
    if rng.random() < 0.8:
        text = mutate_bytes(rng, text)
    t = text.decode("utf-8", "surrogateescape")
    uri = rng.choice(URIS)
    kind = rng.randrange(3)
    if kind == 0:
        params = {"textDocument": {"uri": uri, "languageId": "capstan", "version": version, "text": t}}
        method = "textDocument/didOpen"
    elif kind == 1:
        change = {"text": t[:rng.randint(0, len(t))]}
        if rng.random() < 0.6:
            change["range"] = {"start": rand_pos(rng), "end": rand_pos(rng)}
        params = {"textDocument": {"uri": uri, "version": version}, "contentChanges": [change] * rng.randint(0, 3)}
        method = "textDocument/didChange"
    else:
        params = {"textDocument": {"uri": uri}}
        method = "textDocument/didClose"
    msg = {"jsonrpc": "2.0", "method": method, "params": params}
    ensure_ascii = rng.random() < 0.5
    body = json.dumps(msg, ensure_ascii=ensure_ascii)
    return body.encode("utf-8", "surrogatepass")


def body_message(rng, srcs, n, allow_exit):
    r = rng.randrange(6)
    if r == 0:
        return doc_message(rng, srcs, n)
    if r == 1:
        return json.dumps(rand_json(rng)).encode()
    if r == 2:
        methods = METHODS + (["exit"] if allow_exit else [])
        m = {"jsonrpc": "2.0", "method": rng.choice(methods)}
        if rng.random() < 0.7:
            m["id"] = rng.choice([n, str(n), None, 1.5, [n]])
        if rng.random() < 0.8:
            m["params"] = rand_json(rng)
        return json.dumps(m).encode()
    if r == 3:
        good = doc_message(rng, srcs, n) if rng.random() < 0.5 else json.dumps({"jsonrpc": "2.0", "id": n, "method": "shutdown"}).encode()
        bad = mutate_bytes(rng, good)
        return bad if allow_exit or b'"exit"' not in bad else good
    if r == 4:
        return b"[" * rng.randint(1, 3000) + b"]" * rng.randint(0, 3000)
    return bytes(rng.randrange(256) for _ in range(rng.randint(0, 200)))


def framing_chaos(rng, srcs, n):
    r = rng.randrange(6)
    msg = frame(body_message(rng, srcs, n, True))
    if r == 0:
        return mutate_bytes(rng, msg)
    if r == 1:
        return bytes(rng.randrange(256) for _ in range(rng.randint(0, 3000)))
    if r == 2:
        return msg[:rng.randint(0, len(msg))]
    if r == 3:
        return b"Content-Length: %d\r\n\r\n" % rng.choice([0, 1, 7, 2**31, 10**30, -1]) + msg
    if r == 4:
        return b"".join(rng.choice([b"Content-Length: 3", b"X: y", b"", b":", b"Content-Length:", b"\xff\xfe"]) + rng.choice([b"\r\n", b"\n", b"\r"])
                        for _ in range(rng.randint(1, 50)))
    return msg


def run_session(exe, rng, srcs, chaos):
    s = Server(exe)
    sent = bytearray()

    def send(raw):
        sent.extend(raw)
        try:
            s.send(raw)
        except BrokenPipeError:
            return False
        return True

    init = {"processId": None, "rootUri": "file:///f", "capabilities": rng.choice([{}, {"general": {"positionEncodings": ["utf-8"]}}])}
    if rng.random() < 0.3:
        init["initializationOptions"] = {"strict": True, "release": rng.random() < 0.5}
    send(frame({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": init}))
    problem = None
    for n in range(1, rng.randint(2, 60)):
        raw = framing_chaos(rng, srcs, n) if chaos and rng.random() < 0.5 else frame(body_message(rng, srcs, n, chaos))
        if not send(raw):
            break
    if not chaos:
        send(frame({"jsonrpc": "2.0", "id": "final", "method": "shutdown"}))
        try:
            s.recv_until(lambda m: m.get("id") == "final", timeout=30)
            send(frame({"jsonrpc": "2.0", "method": "exit"}))
        except (TimeoutError, EOFError) as e:
            problem = "final shutdown not answered: %s" % e
    start = time.time()
    try:
        code = s.close(timeout=30)
    except TimeoutError as e:
        return str(e), sent
    took = time.time() - start
    err = s.p.stderr.read()
    if problem:
        return problem, sent
    if code not in (0, 1) or (not chaos and code != 0):
        return "exit code %d (stderr: %r)" % (code, err[:300]), sent
    if err:
        return "stderr: %r" % err[:300], sent
    if took > 20:
        return "took %.1fs to exit after its input closed" % took, sent
    try:
        out = read_frames(bytes(s.raw))
    except (FramingError, ValueError) as e:
        return "malformed output: %s" % e, sent
    STATS["messages"] += len(out)
    STATS["checked"] += sum(1 for m in out if m.get("method") == "textDocument/publishDiagnostics" and m["params"]["diagnostics"])
    STATS["bytes"] += len(sent)
    return None, sent


def main():
    exe, count, seed = os.path.abspath(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    rng = random.Random(seed)
    srcs = sources()
    fails = 0
    for i in range(count):
        chaos = i % 2 == 1
        why, sent = run_session(exe, rng, srcs, chaos)
        if why:
            fails += 1
            d = os.path.join(ROOT, "tests", "lsp", "failures")
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, "seed%d_session%d.bin" % (seed, i))
            with open(path, "wb") as fh:
                fh.write(sent)
            print("  session %d (%s): %s; input saved in %s" % (i, "framing" if chaos else "json", why, os.path.relpath(path, ROOT)))
    if fails:
        print("%d of %d fuzzed language server sessions failed (seed %d)" % (fails, count, seed))
        return 1
    print("language server fuzz: %d sessions (half with corrupted framing), %d KB sent, %d replies, %d documents with diagnostics: no crash, no hang (seed %d)"
          % (count, STATS["bytes"] // 1024, STATS["messages"], STATS["checked"], seed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
