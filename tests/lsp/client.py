"""A minimal LSP client for testing capstan-lsp: framing, a reader thread, timeouts."""
import json, queue, subprocess, threading, time


def frame(body):
    if not isinstance(body, bytes):
        body = json.dumps(body, ensure_ascii=False).encode()
    return b"Content-Length: %d\r\n\r\n" % len(body) + body


class FramingError(Exception):
    pass


def read_frames(data):
    """Split server output into messages; raises FramingError on bad output."""
    out, i = [], 0
    while i < len(data):
        end = data.find(b"\r\n\r\n", i)
        if end < 0:
            raise FramingError("unterminated header at byte %d: %r" % (i, data[i:i + 80]))
        head = data[i:end].decode("ascii")
        if not head.startswith("Content-Length: ") or "\r\n" in head:
            raise FramingError("unexpected header %r" % head)
        n = int(head[len("Content-Length: "):])
        body = data[end + 4:end + 4 + n]
        if len(body) != n:
            raise FramingError("truncated body")
        if any(b < 32 or b == 127 for b in body):
            raise FramingError("body contains a raw control character")
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            raise FramingError("body is not valid UTF-8")
        if "\u2028" in text or "\u2029" in text:
            raise FramingError("body contains a raw line separator")
        out.append(json.loads(body.decode("utf-8")))
        i = end + 4 + n
    return out


class Server:
    def __init__(self, exe, cwd=None):
        self.p = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        self.q = queue.Queue()
        self.raw = bytearray()
        self.error = None
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        buf = b""
        try:
            while True:
                chunk = self.p.stdout.read1(65536)
                if not chunk:
                    break
                self.raw += chunk
                buf += chunk
                while True:
                    end = buf.find(b"\r\n\r\n")
                    if end < 0:
                        break
                    head = buf[:end].decode("ascii", "replace")
                    if not head.startswith("Content-Length: "):
                        raise FramingError("unexpected header %r" % head)
                    n = int(head[len("Content-Length: "):])
                    if len(buf) < end + 4 + n:
                        break
                    body = buf[end + 4:end + 4 + n]
                    buf = buf[end + 4 + n:]
                    self.q.put(json.loads(body.decode("utf-8")))
        except Exception as e:      # reported by recv()
            self.error = e
        self.q.put(None)

    def send(self, msg):
        self.p.stdin.write(frame(msg) if not isinstance(msg, (bytes, bytearray)) else msg)
        self.p.stdin.flush()

    def request(self, id, method, params=None):
        m = {"jsonrpc": "2.0", "id": id, "method": method}
        if params is not None:
            m["params"] = params
        self.send(m)

    def notify(self, method, params=None):
        m = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            m["params"] = params
        self.send(m)

    def recv(self, timeout=10):
        try:
            m = self.q.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError("no message from the server within %ss" % timeout)
        if m is None:
            raise EOFError("server closed its output" + (": %s" % self.error if self.error else ""))
        return m

    def recv_until(self, pred, timeout=10):
        deadline = time.time() + timeout
        seen = []
        while True:
            m = self.recv(max(0.01, deadline - time.time()))
            if pred(m):
                return m, seen
            seen.append(m)

    def close(self, timeout=10):
        try:
            self.p.stdin.close()
        except BrokenPipeError:
            pass
        try:
            return self.p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait()
            raise TimeoutError("server did not exit within %ss after its input closed" % timeout)
