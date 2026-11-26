#!/usr/bin/env python3
"""Byte-boundary behaviour of read_file(path, max), natively and under stage 0.

    read_file_bounds.py CAPSTANC CC [CFLAGS...]

Covers FIFOs with no writer and with an idle live writer, /dev/zero,
exact/over-limit regular files, directories and invalid limits. Non-regular
sources must be rejected before reading: a byte ceiling is not a deadline.
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROGRAM = """void show(string label, Tainted? t) {
    if (let s = t) { println(label + ": " + int_to_str(s.len()) + " bytes"); } else { println(label + ": none"); }
}
int main() {
    List<string> a = args(1, 4096, 4096);
    string d = a[0];
    show("fifo", read_file(d + "/fifo", 1048576));
    show("zero", read_file("/dev/zero", 100000));
    show("exact", read_file(d + "/ten", 10));
    show("over", read_file(d + "/ten", 9));
    show("empty limit", read_file(d + "/empty", 0));
    show("explicit limit", read_file(d + "/ten", 1048576));
    show("directory", read_file(d, 1048576));
    show("bad limit", read_file(d + "/ten", -1));
    return 0;
}
"""
WANT = """fifo: none
zero: none
exact: 10 bytes
over: none
empty limit: 0 bytes
explicit limit: 10 bytes
directory: none
"""


def main():
    capstanc, cc, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
    with tempfile.TemporaryDirectory() as d:
        fifo = os.path.join(d, "fifo")
        os.mkfifo(fifo)
        with open(os.path.join(d, "ten"), "wb") as f:
            f.write(b"0123456789")
        open(os.path.join(d, "empty"), "wb").close()
        cap = os.path.join(d, "rf.cap")
        with open(cap, "w") as f:
            f.write(PROGRAM)
        subprocess.run([capstanc, "build", "-o", cap[:-4] + ".c", cap], check=True, stdout=subprocess.DEVNULL)
        subprocess.run([cc] + flags + [cap[:-4] + ".c", "-o", cap[:-4]], check=True)
        subprocess.run([sys.executable, "-I", os.path.join(ROOT, "bootstrap/capstan0.py"), cap[:-4] + ".py", cap], check=True)
        for label, cmd in (("native", [cap[:-4], d]), ("stage 0", [sys.executable, "-I", cap[:-4] + ".py", d])):
            for idle_writer in (False, True):
                # O_RDWR keeps a FIFO writer present but idle. This used to hang
                # when the native runtime cleared O_NONBLOCK before calling fread().
                keeper = os.open(fifo, os.O_RDWR | os.O_NONBLOCK) if idle_writer else None
                try:
                    try:
                        p = subprocess.run(cmd, capture_output=True, timeout=5)
                    except subprocess.TimeoutExpired:
                        print(f"FAIL {label}: read_file blocked on a FIFO (idle_writer={idle_writer})")
                        return 1
                finally:
                    if keeper is not None:
                        os.close(keeper)
                if p.stdout.decode() != WANT or p.returncode != 101 or b"CWE-789" not in p.stderr:
                    print(f"FAIL {label}: exit {p.returncode}\n{p.stdout.decode()}{p.stderr.decode()}")
                    return 1
        try:
            p = subprocess.run([capstanc, "check", "/dev/zero"], capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            print("FAIL compiler hung reading /dev/zero")
            return 1
        if p.returncode != 1:
            print(f"FAIL compiler on /dev/zero: exit {p.returncode}")
            return 1
    print("read_file rejects non-regular sources before reading; idle FIFO, byte limits and directories tested natively and under stage 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
