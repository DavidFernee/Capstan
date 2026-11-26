#!/usr/bin/env python3
"""A Capstan program can hold a conversation over a pipe (as a language server does):

    stdio_interactive.py CAPSTANC CC [CFLAGS...]

The program reads a length line and then exactly that many bytes with read_bytes(),
answers, and calls flush(). The driver sends one frame at a time and waits for each
answer before sending the next, natively and under stage 0. The same program without
flush() must NOT answer before its input ends (a control showing the test can fail).
"""
import os, select, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROGRAM = """int main() {
    while (true) {
        if (let header = read_line()) {
            if (let n = validate_range(header, 0, 100000)) {
                if (let body = read_bytes(n)) {
                    println($"got {body.len()} bytes: " + escape_log(body));
                    FLUSH
                }
            }
        } else {
            break;
        }
    }
    return 0;
}
"""
FRAMES = [b"hello", b"two\nlines", b"\x00\xff\x7f", b"x" * 70000]


def answer(proc, timeout):
    """One line from proc's stdout, or None if none arrives in time."""
    line = b""
    while not line.endswith(b"\n"):
        r, _, _ = select.select([proc.stdout], [], [], timeout)
        if not r:
            return None
        b = os.read(proc.stdout.fileno(), 1)
        if not b:
            return None
        line += b
    return line


def converse(cmd, timeout):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    got = []
    try:
        for body in FRAMES:
            proc.stdin.write(str(len(body)).encode() + b"\n" + body)
            proc.stdin.flush()
            a = answer(proc, timeout)
            if a is None:
                return None
            got.append(a)
        proc.stdin.close()
        if proc.wait(timeout=30) != 0:
            return None
        return got
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def build(d, capstanc, cc, flags, src, name):
    cap = os.path.join(d, name + ".cap")
    with open(cap, "w") as f:
        f.write(src)
    subprocess.run([capstanc, "build", "-o", cap[:-4] + ".c", cap], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([cc] + flags + [cap[:-4] + ".c", "-o", cap[:-4]], check=True)
    subprocess.run([sys.executable, "-I", os.path.join(ROOT, "bootstrap/capstan0.py"), cap[:-4] + ".py", cap], check=True)
    return [cap[:-4]], [sys.executable, "-I", cap[:-4] + ".py"]


def main():
    capstanc, cc, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
    with tempfile.TemporaryDirectory() as d:
        native, stage0 = build(d, capstanc, cc, flags, PROGRAM.replace("FLUSH", "flush();"), "talk")
        want = [b"got %d bytes: " % len(b) for b in FRAMES]
        for label, cmd in (("native", native), ("stage 0", stage0)):
            got = converse(cmd, 10)
            if got is None or [g[:len(w)] for g, w in zip(got, want)] != want:
                print(f"FAIL {label}: no answer to a frame before the next was sent: {got}")
                return 1
        quiet, _ = build(d, capstanc, cc, flags, PROGRAM.replace("FLUSH", ""), "quiet")
        if converse(quiet, 1) is not None:
            print("FAIL control: a program without flush() answered at once, so this test cannot tell")
            return 1
    print(f"{len(FRAMES)} framed exchanges over a pipe, natively and under stage 0; without flush() no answer comes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
