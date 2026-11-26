#!/usr/bin/env python3
"""
capstan0 -- the stage-0 bootstrap for Capstan.

Grace Hopper's A-0 needed something to start from, and so does every
self-hosting compiler. This file is that starting point: a deliberately
small, unchecked translator from Capstan to Python. It performs *no* safety
analysis. Its only job is to run the real Capstan compiler (compiler/*.cap,
written in Capstan) for the first time. From then on the compiler compiles
itself, and this file can be thrown away.

Usage:  python3 capstan0.py out.py file1.cap [file2.cap ...]
"""
import os, sys

KEYWORDS = {
    "struct", "const", "if", "else", "while", "for", "return", "break", "continue",
    "true", "false", "none", "new", "let", "protected", "policy", "public", "test",
    "authorize", "assert_denied", "assert_granted", "enum", "match", "case", "import", "sensitive",
}
PUNCT = ["&&", "||", "==", "!=", "<=", ">=", "+=", "-=", "++", "--", "<<",
         "{", "}", "(", ")", "[", "]", ";", ",", ".", ":", "?", "<", ">", "=",
         "+", "-", "*", "/", "%", "!", "&", "|", "^", "~"]
TYPE_WORDS = {"int", "bool", "string", "void", "Tainted", "Secret"}
GENERIC_WORDS = {"List", "Map", "Grant"}


class Tok:
    __slots__ = ("kind", "text", "line", "file", "pos")

    def __init__(self, kind, text, line, file, pos=-1):
        self.kind, self.text, self.line, self.file, self.pos = kind, text, line, file, pos

    def __repr__(self):
        return f"{self.file}:{self.line}:{self.kind}:{self.text!r}"


def decode_escapes(raw, where):
    out, i = [], 0
    while i < len(raw):
        c = raw[i]
        if c == "\\":
            i += 1
            e = raw[i]
            out.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'"}.get(e))
            if out[-1] is None:
                raise SystemExit(f"{where}: bad escape \\{e}")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def lex(src, file):
    toks, i, line, n = [], 0, 1, len(src)
    while i < n:
        c = src[i]
        if c == "\n":
            line += 1; i += 1; continue
        if c in " \t\r":
            i += 1; continue
        if src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0:
                raise SystemExit(f"{file}:{line}: unterminated comment")
            line += src.count("\n", i, j)
            i = j + 2
            continue
        if c.isalpha() or c == "_":
            j = i
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            w = src[i:j]
            toks.append(Tok("kw" if w in KEYWORDS else "id", w, line, file))
            i = j; continue
        if src.startswith(("0x", "0X"), i):
            j = i + 2
            while j < n and src[j] in "0123456789abcdefABCDEF":
                j += 1
            if j == i + 2 or (j < n and (src[j].isalnum() or src[j] == "_")) or int(src[i + 2:j], 16) >= 1 << 64:
                raise SystemExit(f"{file}:{line}: malformed hexadecimal literal")
            v = int(src[i + 2:j], 16)
            toks.append(Tok("int", str(v - (1 << 64) if v >= 1 << 63 else v), line, file))
            i = j; continue
        if c.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            toks.append(Tok("int", src[i:j], line, file))
            i = j; continue
        if c == "'":
            j = i + 1
            while j < n and src[j] != "'":
                if src[j] == "\\":
                    j += 1
                j += 1
            ch = decode_escapes(src[i + 1:j].replace("\\'", "'"), f"{file}:{line}")
            if len(ch) != 1:
                raise SystemExit(f"{file}:{line}: bad character literal")
            toks.append(Tok("int", str(ord(ch)), line, file))
            i = j + 1; continue
        if c == "$" and src.startswith('$"', i):
            j, parts, k = i + 2, [], i + 2
            toks.append(Tok("op", "(", line, file)); toks.append(Tok("str", "", line, file))
            while src[j] != '"':
                if src[j] == "\\":
                    j += 2; continue
                if src[j] in "{}" and src[j + 1:j + 2] == src[j]:
                    if j + 1 > k:
                        toks.append(Tok("op", "+", line, file)); toks.append(Tok("str", decode_escapes(src[k:j + 1], file), line, file))
                    j += 2; k = j; continue
                if src[j] == "{":
                    if j > k:
                        toks.append(Tok("op", "+", line, file)); toks.append(Tok("str", decode_escapes(src[k:j], file), line, file))
                    depth, e = 1, j + 1
                    while depth:
                        if src[e] == '"':
                            e += 1
                            while src[e] != '"':
                                e += 2 if src[e] == "\\" else 1
                        elif src[e] == "{": depth += 1
                        elif src[e] == "}": depth -= 1
                        e += 1 if depth else 0
                    toks += [Tok("op", "+", line, file), Tok("id", "to_text", line, file), Tok("op", "(", line, file)]
                    toks += lex(src[j + 1:e], file)[:-1]
                    toks.append(Tok("op", ")", line, file))
                    j = e + 1; k = j; continue
                j += 1
            if j > k:
                toks.append(Tok("op", "+", line, file)); toks.append(Tok("str", decode_escapes(src[k:j], file), line, file))
            toks.append(Tok("op", ")", line, file))
            i = j + 1; continue
        if c == '"':
            j = i + 1
            while j < n and src[j] != '"':
                if src[j] == "\\":
                    j += 1
                if src[j] == "\n":
                    raise SystemExit(f"{file}:{line}: newline in string literal")
                j += 1
            toks.append(Tok("str", decode_escapes(src[i + 1:j], f"{file}:{line}"), line, file))
            i = j + 1; continue
        for p in PUNCT:
            if src.startswith(p, i):
                toks.append(Tok("op", p, line, file, i))
                i += len(p)
                break
        else:
            raise SystemExit(f"{file}:{line}: unexpected character {c!r}")
    toks.append(Tok("eof", "", line, file))
    return toks


class Parser:
    def __init__(self, toks):
        self.t, self.p = toks, 0
        self.tmp = 0
        self.pending = []

    # -- helpers --
    def peek(self, k=0):
        return self.t[min(self.p + k, len(self.t) - 1)]

    def at(self, text, k=0):
        tk = self.peek(k)
        return tk.kind in ("op", "kw") and tk.text == text

    def eat(self, text):
        tk = self.peek()
        if not self.at(text):
            raise SystemExit(f"{tk.file}:{tk.line}: expected {text!r}, found {tk.text!r}")
        self.p += 1
        return tk

    def ident(self):
        tk = self.peek()
        if tk.kind != "id":
            raise SystemExit(f"{tk.file}:{tk.line}: expected identifier, found {tk.text!r}")
        self.p += 1
        return tk.text

    # -- types (stage 0 only needs to skip them) --
    def parse_type(self):
        name = self.ident()
        if name in GENERIC_WORDS:
            self.eat("<"); self.parse_type(); self.eat(">")
        if self.at("?"):
            self.p += 1
        return name

    def is_decl_start(self):
        tk = self.peek()
        if tk.kind != "id":
            return False
        if tk.text in TYPE_WORDS:
            return True
        if tk.text in GENERIC_WORDS and self.at("<", 1):
            return True
        nxt = self.peek(1)
        if nxt.kind == "id":
            return True
        if self.at("?", 1) and self.peek(2).kind == "id":
            return True
        return False

    # -- program --
    def program(self):
        out = []
        while self.peek().kind != "eof":
            out.append(self.decl())
            out += self.pending
            self.pending = []
        return out

    def params(self):
        self.eat("(")
        ps = []
        while not self.at(")"):
            self.parse_type()
            ps.append(self.ident())
            if not self.at(")"):
                self.eat(",")
        self.eat(")")
        return ps

    def decl(self):
        if self.at("import"):
            self.p += 1
            path = self.peek().text
            self.p += 1
            self.eat(";")
            return ("import", path)
        if self.at("enum"):
            self.p += 1
            name = self.ident()
            self.eat("{")
            variants = []
            while not self.at("}"):
                v = self.ident()
                n = 0
                if self.at("("):
                    self.p += 1
                    while not self.at(")"):
                        self.parse_type(); self.ident(); n += 1
                        if not self.at(")"):
                            self.eat(",")
                    self.eat(")")
                variants.append((v, n))
                if not self.at("}"):
                    self.eat(",")
            self.eat("}")
            return ("enum", name, variants)
        if self.at("sensitive"):
            self.p += 1
        if self.at("struct"):
            self.p += 1
            name = self.ident()
            self.eat("{")
            fields = []
            while not self.at("}"):
                self.parse_type()
                fname = self.ident()
                if self.at("("):
                    ps = ["self"] + self.params()
                    self.pending.append(("fn", f"{name}__{fname}", ps, self.block()))
                    continue
                fields.append(fname)
                self.eat(";")
            self.eat("}")
            return ("struct", name, fields)
        if self.at("const"):
            self.p += 1
            self.parse_type()
            name = self.ident()
            self.eat("=")
            e = self.expr()
            self.eat(";")
            return ("const", name, e)
        if self.at("test"):
            self.p += 1
            self.p += 1  # name string
            self.block()
            return ("skip",)
        if self.at("public"):
            self.p += 1
        if self.at("policy"):
            self.p += 1
            name = self.ident()
            ps = self.params()
            return ("fn", "pol_" + name, ps, self.block())
        if self.at("protected"):
            self.p += 1
            self.eat("("); self.ident(); self.eat(")")
        self.parse_type()
        name = self.ident()
        ps = self.params()
        return ("fn", name, ps, self.block())

    # -- statements --
    def block(self):
        self.eat("{")
        body = []
        while not self.at("}"):
            body.append(self.stmt())
        self.eat("}")
        return body

    def stmt(self):
        if self.at("{"):
            return ("block", self.block())
        if self.at("match"):
            self.p += 1
            self.eat("(")
            e = self.expr()
            self.eat(")")
            self.eat("{")
            cases = []
            while not self.at("}"):
                if self.at("else"):
                    self.p += 1
                    cases.append((None, [], self.block()))
                    continue
                self.eat("case")
                v = self.ident()
                binds = []
                if self.at("("):
                    self.p += 1
                    while not self.at(")"):
                        binds.append(self.ident())
                        if not self.at(")"):
                            self.eat(",")
                    self.eat(")")
                cases.append((v, binds, self.block()))
            self.eat("}")
            return ("match", e, cases)
        if self.at("if"):
            self.p += 1
            self.eat("(")
            if self.at("let"):
                self.p += 1
                v = self.ident()
                self.eat("=")
                e = self.expr()
                self.eat(")")
                cond = ("let", v, e)
            else:
                cond = self.expr()
                self.eat(")")
            then = self.block()
            els = None
            if self.at("else"):
                self.p += 1
                els = [self.stmt()] if self.at("if") else self.block()
            return ("if", cond, then, els)
        if self.at("while"):
            self.p += 1
            self.eat("(")
            c = self.expr()
            self.eat(")")
            return ("while", c, self.block())
        if self.at("for"):
            self.p += 1
            self.eat("(")
            init = self.simple_stmt()
            c = self.expr()
            self.eat(";")
            step = self.simple_stmt(end=")")
            return ("for", init, c, step, self.block())
        if self.at("return"):
            self.p += 1
            e = None if self.at(";") else self.expr()
            self.eat(";")
            return ("return", e)
        if self.at("break"):
            self.p += 1; self.eat(";"); return ("break",)
        if self.at("continue"):
            self.p += 1; self.eat(";"); return ("continue",)
        if self.at("assert_denied") or self.at("assert_granted"):
            self.p += 1
            self.ident()
            self.args()
            self.eat(";")
            return ("expr", ("lit", "None"))   # tests are not run by stage 0
        return self.simple_stmt()

    def simple_stmt(self, end=";"):
        if self.is_decl_start():
            self.parse_type()
            name = self.ident()
            self.eat("=")
            e = self.expr()
            self.eat(end)
            return ("decl", name, e)
        e = self.expr()
        if self.at("++") or self.at("--"):
            op = "+=" if self.at("++") else "-="
            self.p += 1
            self.eat(end)
            return ("assign", e, op, ("int", 1))
        if self.at("=") or self.at("+=") or self.at("-="):
            op = self.peek().text
            self.p += 1
            rhs = self.expr()
            self.eat(end)
            return ("assign", e, op, rhs)
        self.eat(end)
        return ("expr", e)

    # -- expressions --
    BIN = [["||"], ["&&"], ["==", "!="], ["<", "<=", ">", ">="], ["|"], ["^"], ["&"], ["<<", ">>", ">>>"],
           ["+", "-"], ["*", "/", "%"]]

    def op_here(self):
        """The operator at the cursor and how many tokens it spans: touching '>' tokens make >> and >>>."""
        t = self.peek()
        if t.kind != "op":
            return None, 0
        if t.text == ">":
            k = 1
            while k < 3 and self.peek(k).text == ">" and self.peek(k).pos == t.pos + k:
                k += 1
            return ">" * k, k
        return t.text, 1

    def expr(self, lvl=0):
        if lvl == len(self.BIN):
            return self.unary()
        e = self.expr(lvl + 1)
        while True:
            op, width = self.op_here()
            if op not in self.BIN[lvl]:
                return e
            self.p += width
            e = ("bin", op, e, self.expr(lvl + 1))

    def unary(self):
        if self.at("!"):
            self.p += 1
            return ("not", self.unary())
        if self.at("-"):
            self.p += 1
            return ("neg", self.unary())
        if self.at("~"):
            self.p += 1
            return ("bnot", self.unary())
        return self.postfix(self.primary())

    def args(self):
        self.eat("(")
        a = []
        while not self.at(")"):
            a.append(self.expr())
            if not self.at(")"):
                self.eat(",")
        self.eat(")")
        return a

    def postfix(self, e):
        while True:
            if self.at("."):
                self.p += 1
                name = self.ident()
                if self.at("("):
                    e = ("method", e, name, self.args())
                else:
                    e = ("field", e, name)
            elif self.at("["):
                self.p += 1
                i = self.expr()
                self.eat("]")
                e = ("index", e, i)
            else:
                return e

    def primary(self):
        tk = self.peek()
        if tk.kind == "int":
            self.p += 1
            return ("int", int(tk.text))
        if tk.kind == "str":
            self.p += 1
            return ("str", tk.text)
        if self.at("true"):
            self.p += 1; return ("lit", "True")
        if self.at("false"):
            self.p += 1; return ("lit", "False")
        if self.at("none"):
            self.p += 1; return ("lit", "None")
        if self.at("("):
            self.p += 1
            e = self.expr()
            self.eat(")")
            return e
        if self.at("new"):
            self.p += 1
            name = self.ident()
            if name in ("List", "Map"):
                self.eat("<"); self.parse_type(); self.eat(">")
                self.eat("("); self.eat(")")
                return ("lit", "[]" if name == "List" else "{}")
            self.eat("{")
            inits = []
            while not self.at("}"):
                f = self.ident()
                self.eat(":")
                inits.append((f, self.expr()))
                if not self.at("}"):
                    self.eat(",")
            self.eat("}")
            return ("new", name, inits)
        if self.at("authorize"):
            self.p += 1
            name = self.ident()
            return ("authorize", name, self.args())
        if tk.kind == "id":
            self.p += 1
            if self.at("("):
                return ("call", tk.text, self.args())
            return ("var", tk.text)
        raise SystemExit(f"{tk.file}:{tk.line}: unexpected {tk.text!r}")


BUILTINS = {
    "print", "println", "int_to_str", "char_str", "read_file", "read_line", "write_file",
    "args", "exit", "join", "assert", "validate_ident", "validate_int", "escape_c",
    "escape_html", "escape_log", "trust", "taint", "sql_query", "run", "secret_env",
    "secret_eq", "hash", "hash_verify", "hash_password", "verify_password", "needs_rehash",
    "escape_csv", "validate_path", "validate_range", "to_text",
    "wrapping_add", "wrapping_sub", "wrapping_mul", "wrapping_shl", "read_bytes", "flush", "escape_json", "taint_char",
}

PRELUDE = r'''
import sys, re, hashlib, os, stat
sys.setrecursionlimit(200000)
I64MIN, I64MAX = -(1 << 63), (1 << 63) - 1
def _panic(msg, cwe):
    sys.stderr.write("runtime check failed: %s [%s prevented]\n" % (msg, cwe)); sys.exit(101)
def _chk(v):
    if v < I64MIN or v > I64MAX: _panic("integer overflow", "CWE-190")
    return v
def _plus(a, b):
    if isinstance(a, str): return a + b
    return _chk(a + b)
def _sub(a, b): return _chk(a - b)
def _mul(a, b): return _chk(a * b)
def _div(a, b):
    if b == 0: _panic("division by zero", "CWE-369")
    q = abs(a) // abs(b)
    return _chk(q if (a >= 0) == (b >= 0) else -q)
def _mod(a, b):
    if b == 0: _panic("division by zero", "CWE-369")
    return a - b * _div(a, b) if not (a == I64MIN and b == -1) else 0
def _neg(a): return _chk(-a)
def _signed(v):
    v &= (1 << 64) - 1
    return v - (1 << 64) if v >= 1 << 63 else v
def _count(n):
    if n < 0 or n > 63: _panic("shift count outside 0..63", "CWE-1335")
    return n
def _shl(a, n): return _chk(a << _count(n))
def _sar(a, n): return a >> _count(n)
def _shr(a, n): return _signed((a & ((1 << 64) - 1)) >> _count(n))
def b_wrapping_add(a, b): return _signed(a + b)
def b_wrapping_sub(a, b): return _signed(a - b)
def b_wrapping_mul(a, b): return _signed(a * b)
def b_wrapping_shl(a, n): return _signed(a << _count(n))
def _at(s, i):
    if i < 0 or i >= len(s): _panic("string index out of bounds", "CWE-125")
    return ord(s[i])
def _slice(s, a, b):
    if a < 0 or b < a or b > len(s): _panic("string slice out of bounds", "CWE-125")
    return s[a:b]
def _idx(l, i):
    if i < 0 or i >= len(l): _panic("list index out of bounds", "CWE-125")
    return l[i]
def _setidx(l, i, v):
    if i < 0 or i >= len(l): _panic("list index out of bounds", "CWE-787")
    l[i] = v
class _Enum:
    __slots__ = ("v", "vals")
    def __init__(self, v, vals): self.v, self.vals = v, vals
    def __eq__(self, o): return self.v == o.v and self.vals == o.vals
    def __ne__(self, o): return not self.__eq__(o)
def _pop(l): return l.pop() if l else None
def _insert(l, i, v):
    if i < 0 or i > len(l): _panic("list insert position out of bounds", "CWE-787")
    l.insert(i, v)
def _remove_at(l, i):
    if i < 0 or i >= len(l): _panic("list index out of bounds", "CWE-125")
    return l.pop(i)
_MISSING = object()
class _Struct:
    __slots__ = ()
def _mcall(recv, name, *args):
    return globals()["fn_" + type(recv).__name__[2:] + "__" + name](recv, *args)
class _Grant:
    def __init__(self, bound): self.bound = bound
def _authorize(pol, args):
    return _Grant(args) if pol(*args) else None
def b_print(s): sys.stdout.buffer.write(s.encode("latin-1"))
def b_println(s): b_print(s + "\n")
def b_int_to_str(i): return str(i)
def b_char_str(c):
    if c < 0 or c > 255: _panic("char_str out of range", "CWE-704")
    return chr(c)
def b_read_file(p, mx):
    if mx < 0 or mx > (1 << 30): _panic("read_file() limit outside 0..2^30", "CWE-789")
    if p == "" or "\0" in p: return None
    try:
        fd = os.open(p, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY | os.O_CLOEXEC)
    except OSError: return None
    try:
        os.set_blocking(fd, True)
        with os.fdopen(fd, "rb") as f:
            if stat.S_ISDIR(os.fstat(f.fileno()).st_mode): return None
            data = f.read(mx + 1)
            return None if len(data) > mx else data.decode("latin-1")
    except OSError: return None
def b_read_line(mx):
    if mx < 0 or mx > (1 << 20): _panic("read_line() limit outside 0..1 MiB", "CWE-789")
    out = bytearray()
    while True:
        ch = sys.stdin.buffer.read(1)
        if not ch: break
        if ch == b"\n": break
        if len(out) >= mx: _panic("read_line() input exceeds explicit byte limit", "CWE-789")
        out.extend(ch)
    return None if not out and not ch else bytes(out).decode("latin-1")
def b_read_bytes(n):
    if n < 0 or n > (1 << 30): _panic("read_bytes() count outside 0..2^30", "CWE-789")
    if n == 0: return ""
    out = b""
    while len(out) < n:
        got = sys.stdin.buffer.read1(min(n - len(out), 65536))
        if not got: break
        out += got
    return None if not out else out.decode("latin-1")
def b_flush(): sys.stdout.flush()
def b_write_file(p, d):
    if p == "" or "\0" in p: return False
    try:
        with open(p, "wb") as f: f.write(d.encode("latin-1"))
        return True
    except OSError: return False
def b_args(max_count, max_arg_bytes, max_total_bytes):
    if not 0 <= max_count <= 4096 or not 0 <= max_arg_bytes <= (1 << 20) or not 0 <= max_total_bytes <= (1 << 24):
        _panic("args() bounds outside supported limits", "CWE-789")
    values = sys.argv[1:]
    if len(values) > max_count: _panic("command-line argument count exceeds explicit bound", "CWE-789")
    total = 0
    for value in values:
        size = len(value.encode("latin-1"))
        if size > max_arg_bytes or size > max_total_bytes - total:
            _panic("command-line argument bytes exceed explicit bound", "CWE-789")
        total += size
    return list(values)
def b_exit(c): sys.stdout.flush(); sys.exit(c)
def b_join(l, sep): return sep.join(l)
def b_assert(c):
    if not c: _panic("assertion failed", "test")
_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
def b_validate_ident(t): return t if 0 < len(t) <= 255 and _ID.match(t) else None
def b_validate_int(t):
    if not re.fullmatch(r"-?[0-9]+", t): return None
    v = int(t)
    return v if I64MIN <= v <= I64MAX else None
def b_escape_c(t):
    o = []
    for ch in t:
        c = ord(ch)
        if ch == "\\": o.append("\\\\")
        elif ch == '"': o.append('\\"')
        elif ch == "?": o.append("\\?")
        elif 32 <= c < 127: o.append(ch)
        else: o.append("\\%03o" % c)
    return "".join(o)
def b_escape_html(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;")
def _utf8_seq(b, i):
    c = b[i]
    if 0xC2 <= c <= 0xDF: n, lo, hi = 2, 0x80, 0xBF
    elif 0xE0 <= c <= 0xEF: n, lo, hi = 3, (0xA0 if c == 0xE0 else 0x80), (0x9F if c == 0xED else 0xBF)
    elif 0xF0 <= c <= 0xF4: n, lo, hi = 4, (0x90 if c == 0xF0 else 0x80), (0x8F if c == 0xF4 else 0xBF)
    else: return 0, 0
    if len(b) - i < n or not lo <= b[i + 1] <= hi or any(not 0x80 <= b[i + k] <= 0xBF for k in range(2, n)): return 0, 0
    return n, ord(bytes(b[i:i + n]).decode("utf-8"))
def _log_hostile(cp):
    return 0x80 <= cp <= 0x9F or cp in (0x061C, 0x200E, 0x200F, 0xFEFF) or 0x2028 <= cp <= 0x202E or 0x2066 <= cp <= 0x2069
def b_escape_log(t):
    b, out, i = t.encode("latin-1"), [], 0
    while i < len(b):
        c = b[i]
        if 32 <= c < 127:
            out.append(chr(c)); i += 1; continue
        n, cp = _utf8_seq(b, i) if c >= 0x80 else (0, 0)
        if n and not _log_hostile(cp):
            out.append(bytes(b[i:i + n]).decode("latin-1")); i += n; continue
        n = n or 1
        out.extend("\\x%02x" % b[i + k] for k in range(n)); i += n
    return "".join(out)
def b_escape_json(t):
    b, out, i = t.encode("latin-1"), [], 0
    simple = {0x22: '\\"', 0x5C: "\\\\", 0x0A: "\\n", 0x09: "\\t", 0x0D: "\\r"}
    while i < len(b):
        c = b[i]
        if c in simple:
            out.append(simple[c]); i += 1; continue
        if c < 32 or c == 127 or c in (0x3C, 0x3E, 0x26):
            out.append("\\u%04x" % c); i += 1; continue
        if c < 128:
            out.append(chr(c)); i += 1; continue
        n, cp = _utf8_seq(b, i)
        if not n:
            out.append("\\ufffd"); i += 1; continue
        out.append("\\u%04x" % cp if cp in (0x2028, 0x2029) else bytes(b[i:i + n]).decode("latin-1")); i += n
    return "".join(out)
def b_taint_char(c):
    if c < 0 or c > 255: _panic("taint_char() byte outside 0..255", "CWE-704")
    return chr(c)
def b_trust(t, why): return t
def b_to_text(x):
    if isinstance(x, bool): return "true" if x else "false"
    return str(x) if isinstance(x, int) else x
def b_escape_csv(t):
    return '"' + ("'" if t[:1] in ("=", "+", "-", "@", "\t", "\r") and t else "") + t.replace('"', '""') + '"'
def b_validate_path(t):
    if not t or len(t) > 4096 or t[0] in ("/", "-"): return None
    for seg in t.split("/"):
        if seg in ("", ".", "..") or not re.fullmatch(r"[A-Za-z0-9_.-]+", seg): return None
    return t
def b_validate_range(t, lo, hi):
    v = b_validate_int(t)
    return v if v is not None and lo <= v <= hi else None
def b_taint(s): return s
def b_sql_query(tmpl, *a): b_println("[sql] " + tmpl + "".join(" $%d=%s" % (i + 1, b_escape_log(x)) for i, x in enumerate(a)))
def b_run(prog, *a): b_println("[run] " + prog + "".join(" argv[%d]=%s" % (i + 1, b_escape_log(x)) for i, x in enumerate(a)))
def b_secret_env(n, mx):
    if mx < 0 or mx > (1 << 20): _panic("secret_env() limit outside 0..1 MiB", "CWE-789")
    value = os.environ.get(n)
    if value is not None and len(value.encode("latin-1")) > mx:
        _panic("secret environment value exceeds explicit byte limit", "CWE-789")
    return value
def b_secret_eq(a, b):
    import hmac; return hmac.compare_digest(a.encode("latin-1"), b.encode("latin-1"))
def b_hash(d): return "cap1$sha256$" + hashlib.sha256(d.encode("latin-1")).hexdigest()
def b_hash_verify(d, t): return t.startswith("cap1$sha256$") and b_secret_eq(b_hash(d), t)
def b_hash_password(p):
    s = os.urandom(16)
    return "cap1$pbkdf2-sha256$600000$%s$%s" % (s.hex(), hashlib.pbkdf2_hmac("sha256", p.encode("latin-1"), s, 600000).hex())
def b_verify_password(p, t):
    parts = t.split("$")
    if len(parts) != 5 or parts[1] != "pbkdf2-sha256": return False
    dk = hashlib.pbkdf2_hmac("sha256", p.encode("latin-1"), bytes.fromhex(parts[3]), int(parts[2])).hex()
    return b_secret_eq(dk, parts[4])
def b_needs_rehash(t): return not t.startswith("cap1$pbkdf2-sha256$600000$")
'''

METHODS = {
    "len": lambda r, a: f"len({r})",
    "at": lambda r, a: f"_at({r}, {a[0]})",
    "slice": lambda r, a: f"_slice({r}, {a[0]}, {a[1]})",
    "push": lambda r, a: f"{r}.append({a[0]})",
    "get": lambda r, a: f"{r}.get({a[0]})",
    "set": lambda r, a: f"{r}.__setitem__({a[0]}, {a[1]})",
    "has": lambda r, a: f"({a[0]} in {r})",
    "keys": lambda r, a: f"list({r}.keys())",
    "pop": lambda r, a: f"_pop({r})",
    "clear": lambda r, a: f"{r}.clear()",
    "insert": lambda r, a: f"_insert({r}, {a[0]}, {a[1]})",
    "remove_at": lambda r, a: f"_remove_at({r}, {a[0]})",
    "sort": lambda r, a: f"{r}.sort()",
    "remove": lambda r, a: f"({r}.pop({a[0]}, _MISSING) is not _MISSING)",
}


class Gen:
    def __init__(self):
        self.enums = set()
        self.methods = set()
        self.out = [PRELUDE]
        self.tmp = 0
        self.loops = []
        self.scopes = [set()]   # names of locals in scope: a local may share an enum's name

    def enum_ref(self, x):
        return x[0] == "var" and x[1] in self.enums and not any(x[1] in s for s in self.scopes)

    def scoped(self, ind, stmts, names=()):
        self.scopes.append(set(names))
        self.body(ind, stmts)
        self.scopes.pop()

    def fresh(self):
        self.tmp += 1
        return f"_t{self.tmp}"

    def e(self, x):
        k = x[0]
        if k == "int":
            return str(x[1])
        if k == "str":
            return ascii(x[1])
        if k == "lit":
            return x[1]
        if k == "var":
            return "u_" + x[1]
        if k == "not":
            return f"(not {self.e(x[1])})"
        if k == "bnot":
            return f"(~{self.e(x[1])})"
        if k == "neg":
            return f"_neg({self.e(x[1])})"
        if k == "bin":
            op, a, b = x[1], self.e(x[2]), self.e(x[3])
            if op == "+": return f"_plus({a}, {b})"
            if op == "-": return f"_sub({a}, {b})"
            if op == "*": return f"_mul({a}, {b})"
            if op == "/": return f"_div({a}, {b})"
            if op == "%": return f"_mod({a}, {b})"
            if op in ("&", "|", "^"): return f"({a} {op} {b})"
            if op == "<<": return f"_shl({a}, {b})"
            if op == ">>": return f"_sar({a}, {b})"
            if op == ">>>": return f"_shr({a}, {b})"
            if op == "&&": return f"({a} and {b})"
            if op == "||": return f"({a} or {b})"
            return f"({a} {op} {b})"
        if k == "field":
            if self.enum_ref(x[1]):
                return f"_Enum({x[2]!r}, [])"
            return f"{self.e(x[1])}.u_{x[2]}"
        if k == "index":
            return f"_idx({self.e(x[1])}, {self.e(x[2])})"
        if k == "method":
            if self.enum_ref(x[1]):
                return f"_Enum({x[2]!r}, [{', '.join(self.e(a) for a in x[3])}])"
            if x[2] in self.methods:
                recv = self.e(x[1])
                user = f"_mcall({recv}, {x[2]!r}{''.join(', ' + self.e(a) for a in x[3])})"
                if x[2] not in METHODS:
                    return user
                t = self.fresh()
                return f"(_mcall({t}, {x[2]!r}{''.join(', ' + self.e(a) for a in x[3])}) if isinstance(({t} := {recv}), _Struct) else {METHODS[x[2]](t, [self.e(a) for a in x[3]])})"
            return METHODS[x[2]](self.e(x[1]), [self.e(a) for a in x[3]])
        if k == "call":
            fn = ("b_" if x[1] in BUILTINS else "fn_") + x[1]
            return f"{fn}({', '.join(self.e(a) for a in x[2])})"
        if k == "new":
            return f"S_{x[1]}({', '.join('u_' + f + '=' + self.e(v) for f, v in x[2])})"
        if k == "authorize":
            return f"_authorize(fn_pol_{x[1]}, [{', '.join(self.e(a) for a in x[2])}])"
        raise SystemExit(f"stage0: cannot translate {k}")

    def emit(self, ind, s):
        self.out.append("    " * ind + s)

    def body(self, ind, stmts):
        if not stmts:
            self.emit(ind, "pass")
        for s in stmts:
            self.stmt(ind, s)

    def stmt(self, ind, s):
        k = s[0]
        if k == "block":
            self.scoped(ind, s[1]) if s[1] else None
        elif k == "decl":
            self.emit(ind, f"u_{s[1]} = {self.e(s[2])}")
            self.scopes[-1].add(s[1])
        elif k == "assign":
            tgt, op, rhs = s[1], s[2], self.e(s[3])
            if op != "=" and tgt[0] == "field":
                # Match the native backend: evaluate the field receiver once,
                # read the old value, then evaluate the RHS and write back.
                receiver = self.fresh()
                old = self.fresh()
                right = self.fresh()
                value = self.fresh()
                self.emit(ind, f"{receiver} = {self.e(tgt[1])}")
                self.emit(ind, f"{old} = {receiver}.u_{tgt[2]}")
                self.emit(ind, f"{right} = {self.e(s[3])}")
                fn = "_plus" if op == "+=" else "_sub"
                self.emit(ind, f"{value} = {fn}({old}, {right})")
                self.emit(ind, f"{receiver}.u_{tgt[2]} = {value}")
                return
            if op != "=":
                rhs = self.e(("bin", op[0], tgt, s[3]))
            if tgt[0] == "index":
                self.emit(ind, f"_setidx({self.e(tgt[1])}, {self.e(tgt[2])}, {rhs})")
            else:
                self.emit(ind, f"{self.e(tgt)} = {rhs}")
        elif k == "expr":
            self.emit(ind, self.e(s[1]))
        elif k == "return":
            self.emit(ind, "return" if s[1] is None else f"return {self.e(s[1])}")
        elif k == "break":
            self.emit(ind, "break")
        elif k == "continue":
            step = self.loops[-1] if self.loops else None
            if step is not None:
                self.stmt(ind, step)
            self.emit(ind, "continue")
        elif k == "if":
            cond = s[1]
            bound = ()
            if isinstance(cond, tuple) and cond[0] == "let":
                t = self.fresh()
                self.emit(ind, f"{t} = {self.e(cond[2])}")
                self.emit(ind, f"if {t} is not None:")
                self.emit(ind + 1, f"u_{cond[1]} = {t}")
                bound = (cond[1],)
            else:
                self.emit(ind, f"if {self.e(cond)}:")
            self.scoped(ind + 1, s[2], bound)
            if s[3] is not None:
                self.emit(ind, "else:")
                self.scoped(ind + 1, s[3])
        elif k == "while":
            self.emit(ind, f"while {self.e(s[1])}:")
            self.loops.append(None)
            self.scoped(ind + 1, s[2])
            self.loops.pop()
        elif k == "for":
            self.scopes.append(set())
            self.stmt(ind, s[1])
            self.emit(ind, f"while {self.e(s[2])}:")
            self.loops.append(s[3])
            self.scoped(ind + 1, s[4])
            self.loops.pop()
            self.stmt(ind + 1, s[3])
            self.scopes.pop()
        elif k == "match":
            t = self.fresh()
            self.emit(ind, f"{t} = {self.e(s[1])}")
            first = True
            for v, binds, body in s[2]:
                if v is None:
                    self.emit(ind, "else:" if not first else "if True:")
                else:
                    self.emit(ind, f"{'if' if first else 'elif'} {t}.v == {v!r}:")
                    for i, b in enumerate(binds):
                        self.emit(ind + 1, f"u_{b} = {t}.vals[{i}]")
                self.scoped(ind + 1, body, binds or ())
                first = False
        else:
            raise SystemExit(f"stage0: cannot translate statement {k}")

    def program(self, decls):
        self.enums = {d[1] for d in decls if d[0] == "enum"}
        self.methods = {d[1].split("__", 1)[1] for d in decls if d[0] == "fn" and "__" in d[1]}
        for d in decls:
            if d[0] == "struct":
                fs = d[2]
                self.emit(0, f"class S_{d[1]}(_Struct):")
                self.emit(1, f"__slots__ = ({', '.join(repr('u_' + f) for f in fs)}{',' if len(fs) == 1 else ''})")
                self.emit(1, f"def __init__(self, {', '.join('u_' + f for f in fs)}):")
                for f in fs:
                    self.emit(2, f"self.u_{f} = u_{f}")
                if not fs:
                    self.emit(2, "pass")
        for d in decls:
            if d[0] == "fn":
                self.emit(0, f"def fn_{d[1]}({', '.join('u_' + p for p in d[2])}):")
                self.scoped(1, d[3], d[2])
        for d in decls:   # after the functions, so constant initialisers may call them
            if d[0] == "const":
                self.emit(0, f"u_{d[1]} = {self.e(d[2])}")
        self.emit(0, "if __name__ == '__main__':")
        self.emit(1, "_r = fn_main()")
        self.emit(1, "sys.stdout.flush()")
        self.emit(1, "sys.exit(_r if isinstance(_r, int) else 0)")
        return "\n".join(self.out) + "\n"


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: capstan0.py out.py file.cap [file.cap ...]")
    decls, queue, loaded = [], list(sys.argv[2:]), set()
    while queue:
        path = queue.pop(0)
        if path in loaded:
            continue
        loaded.add(path)
        with open(path, "rb") as f:
            src = f.read().decode("latin-1")
        for d in Parser(lex(src, path)).program():
            decls.append(d)
            if d[0] == "import":
                queue.append(os.path.join(os.path.dirname(path), d[1]) if os.path.dirname(path) else d[1])
    with open(sys.argv[1], "w", encoding="latin-1") as f:
        f.write(Gen().program(decls))


if __name__ == "__main__":
    main()
