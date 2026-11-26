#!/usr/bin/env python3
"""read_file(, 1048576) cannot be made to hang or exhaust memory, natively and under stage 0:

    read_file_bounds.py CAPSTANC CC [CFLAGS...]

A FIFO with no writer reads as empty instead of blocking; /dev/zero and a file over
the limit give none; a file exactly at the limit is read whole; a directory gives
none; a limit outside 0..2^30 stops the program (CWE-789). The compiler, given an
endless or blocking source file, reports an error promptly instead of hanging.
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROGRAM = """void show(string label, Tainted? t) {
    if (let s = t) { println(label + ": " + int_to_str(s.len()) + " bytes"); } else { println(label + ": none"); }
}
int main() {
    List<string> a = args(4096, 1048576, 16777216);
    string d = a[0];
    show("fifo", read_file(d + "/fifo", 1048576));
    show("zero", read_file("/dev/zero", 100000));
    show("exact", read_file(d + "/ten", 10));
    show("over", read_file(d + "/ten", 9));
    show("empty limit", read_file(d + "/empty", 0));
    show("default", read_file(d + "/ten", 1048576));
    show("directory", read_file(d, 1048576));
    show("bad limit", read_file(d + "/ten", -1));
    return 0;
}
"""
WANT = """fifo: 0 bytes
zero: none
exact: 10 bytes
over: none
empty limit: 0 bytes
default: 10 bytes
directory: none
"""


def main():
    capstanc, cc, flags = sys.argv[1], sys.argv[2], sys.argv[3:]
    with tempfile.TemporaryDirectory() as d:
        os.mkfifo(os.path.join(d, "fifo"))
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
            try:
                p = subprocess.run(cmd, capture_output=True, timeout=60)
            except subprocess.TimeoutExpired:
                print(f"FAIL {label}: read_file hung")
                return 1
            if p.stdout.decode() != WANT or p.returncode != 101 or b"CWE-789" not in p.stderr:
                print(f"FAIL {label}: exit {p.returncode}\n{p.stdout.decode()}{p.stderr.decode()}")
                return 1
        for src in ("/dev/zero", os.path.join(d, "fifo")):
            try:
                p = subprocess.run([capstanc, "check", src], capture_output=True, timeout=60)
            except subprocess.TimeoutExpired:
                print(f"FAIL compiler hung reading {src}")
                return 1
            out = p.stdout.decode(errors="replace")
            if src == "/dev/zero" and (p.returncode != 1 or "over 16 MiB" not in out):
                print(f"FAIL compiler on {src}: exit {p.returncode}: {out[:200]}")
                return 1
            if src != "/dev/zero" and p.returncode not in (0, 1):
                print(f"FAIL compiler on an empty FIFO: exit {p.returncode}: {out[:200]}")
                return 1
    print("read_file is bounded: FIFO, /dev/zero, limits and directories, natively and under stage 0; the compiler refuses endless sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
