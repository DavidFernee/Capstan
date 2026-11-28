"""Exercise the opt-in aggregate CLI; explicitly probe the complete production compiler.

The driver is C-hosted. This test is not S1 evidence.
"""
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

SOURCE_FILES = (
    "compiler/ast.cap", "compiler/lexer.cap", "compiler/parser.cap",
    "compiler/checker.cap", "compiler/ranges.cap", "compiler/codegen.cap",
    "compiler/main.cap",
)

def run(root, cli, output, *files):
    return subprocess.run(
        [str(cli), "native", "--direct", "--direct-aggregate",
         "--root", str(root), "-o", str(output), *files],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300,
    )

def main():
    repo = Path(sys.argv[1]).resolve()
    cli = repo / "bin/capstan"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "fixture.cap"
        helper = root / "helper.cap"
        out = root / "program"
        helper.write_text("struct Item { int value; }\nint get(Item x) { return x.value; }\n")
        source.write_text('import "helper.cap";\nint main() { Item x = new Item{value: 42}; return get(x); }\n')
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode == 0, p.stdout.decode(errors="replace")
        raw = out.read_bytes()
        assert raw.startswith(b"\x7fELF") and os.access(out, os.X_OK)
        q = subprocess.run([str(out)], capture_output=True, timeout=5)
        assert (q.returncode, q.stdout, q.stderr) == (0, struct.pack("<q",42), b"")
        original = raw
        source.write_text("int main() { return true; }\n")
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode != 0 and out.read_bytes() == original, p.stdout
        source.write_text("int main() { return 1; }\n")
        p = run(root, cli, out, "../fixture.cap")
        assert p.returncode != 0 and out.read_bytes() == original, p.stdout

        # Exercise the production layouts and functions with all six Diag fields observable.
        ast = (repo / "compiler/ast.cap").read_text()
        declarations = ast[ast.index("struct Diag {"):ast.index("void error_at(")]
        source.write_text(declarations + """
int main() {
    Ctx c = new Ctx{files: new List<string>(), sources: new List<Tainted>(), diags: new List<Diag>(), release: false, strict: true, keep_checks: false};
    report(c, 2, 42, true, "FIRST", "message");
    report_at(c, 3, 7, 9, false, "SECOND", "another");
    if (c.diags.len() != 2) { return 1; }
    Diag a = c.diags[0];
    Diag b = c.diags[1];
    if (a.file != 2 || a.line != 42 || a.col != 0 || !a.error || a.code != "FIRST" || a.msg != "message") { return 2; }
    if (b.file != 3 || b.line != 7 || b.col != 9 || b.error || b.code != "SECOND" || b.msg != "another") { return 3; }
    return 42;
}
""")
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode == 0, p.stdout.decode(errors="replace")
        q = subprocess.run([str(out)], capture_output=True, timeout=5)
        assert (q.returncode, q.stdout, q.stderr) == (0, struct.pack("<q", 42), b""), q

        # Production source_excerpt is the next real compiler admission
        # boundary. Read the exact function and record declarations, not
        # a hand-written equivalent. This deliberately scoped probe is
        # supplementary; the full compiler probe below remains mandatory.
        excerpt = ast[ast.index("LogText? source_excerpt("):ast.index("int error_count(")]
        assert excerpt.count("LogText? source_excerpt(") == 1
        source.write_text(declarations + excerpt + r"""
int main() {
    Ctx c = new Ctx{files: new List<string>(), sources: new List<Tainted>(), diags: new List<Diag>(), release: false, strict: true, keep_checks: false};
    c.files.push("input.cap");
    c.sources.push(taint("first\n" + char_str(27) + "[31msecond\n"));
    Diag first = new Diag{file: 0, line: 1, col: 3, error: true, code: "FIRST", msg: "first"};
    Diag hostile = new Diag{file: 0, line: 2, col: 5, error: true, code: "SECOND", msg: "second"};
    Diag missing = new Diag{file: 0, line: 4, col: 1, error: true, code: "MISSING", msg: "missing"};
    Diag outside = new Diag{file: 1, line: 1, col: 1, error: true, code: "FILE", msg: "missing file"};
    Diag zero = new Diag{file: 0, line: 0, col: 1, error: true, code: "ZERO", msg: "invalid line"};
    if (let x = source_excerpt(c, first)) { LogText again = escape_log(x); } else { return 11; }
    if (let x = source_excerpt(c, hostile)) { LogText again = escape_log(x); } else { return 12; }
    if (let x = source_excerpt(c, missing)) { return 13; }
    if (let x = source_excerpt(c, outside)) { return 14; }
    if (let x = source_excerpt(c, zero)) { return 15; }
    return 42;
}
""")
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode == 0, ("production source_excerpt admission", p.stdout.decode(errors="replace"))
        q = subprocess.run([str(out)], capture_output=True, timeout=5)
        assert (q.returncode, q.stdout, q.stderr) == (0, struct.pack("<q", 42), b""), ("production source_excerpt execution", q)
        print("Production source_excerpt candidate: exact source admitted and present/absent paths executed")
        # The current result ABI exposes only an integer. This probe does
        # not observe the returned log bytes; the isolated native leaf
        # differential tests cover those transforms separately.

        # Exercise exact production print_diags and source_excerpt together.
        # Candidate result ABI appends the existing binary return word after
        # the emitted text; compare the whole stream, including hostile input.
        printer = ast[ast.index("int error_count("):ast.index("// ---- constructors")]
        source.write_text(declarations + excerpt + printer + r"""
int main() {
    Ctx c = new Ctx{files: new List<string>(), sources: new List<Tainted>(), diags: new List<Diag>(), release: false, strict: true, keep_checks: false};
    c.files.push("input.cap");
    c.sources.push(taint("first\n" + char_str(27) + "[31msecond\n"));
    report_at(c, 0, 1, 3, true, "FIRST", "message");
    report_at(c, 0, 2, 5, false, "", "another");
    print_diags(c);
    return 42;
}
""")
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode == 0, ("production print_diags admission", p.stdout.decode(errors="replace"))
        q = subprocess.run([str(out)], capture_output=True, timeout=5)
        expected = (b"input.cap:1:3: error[FIRST]: message\n"
                    b"    first\n      ^\n"
                    b"input.cap:2:5: warning: another\n"
                    b"    \\x1b[31msecond\n        ^\n")
        assert (q.returncode, q.stdout, q.stderr) == (0, expected + struct.pack("<q", 42), b""), ("production print_diags", q)
        print("Production print_diags candidate: exact source emitted expected diagnostic bytes")

        # Compile the entire production AST module, unchanged, with only
        # a test entry appended. No declaration pruning or replacement.
        source.write_text(ast + r"""
int main() {
    CompileBudget budget = new_compile_budget();
    Node node = mk_node_s(N_INT, "n", 0, 1);
    Node parent = mk_node(N_BLOCK, 0, 1);
    parent.kids.push(node);
    List<Node> roots = new List<Node>(); roots.push(parent);
    if (!charge_ast_nodes(budget, roots) || budget.ast_nodes != 2) { return 1; }
    Type a = mk_wrap(TY_LIST, mk_type(TY_INT));
    Type b = mk_wrap(TY_LIST, mk_type(TY_INT));
    if (!type_eq(a, b) || type_str(a) != "List<int>") { return 2; }
    if (!assignable(mk_type(TY_NONE), mk_wrap(TY_OPT, mk_type(TY_INT)))) { return 3; }
    if (lower("AbC") != "abc" || !contains("abc", "bc")) { return 4; }
    if (edit_distance("a", "b") != 1) { return 5; }
    List<string> candidates = new List<string>(); candidates.push("cat");
    if (suggest("car", candidates) != " (did you mean 'cat'?)") { return 6; }
    return 42;
}
""")
        p = run(root, cli, out, "fixture.cap")
        assert p.returncode == 0, ("complete production ast.cap admission", p.stdout.decode(errors="replace"))
        q = subprocess.run([str(out)], capture_output=True, timeout=5)
        assert (q.returncode, q.stdout, q.stderr) == (0, struct.pack("<q", 42), b""), ("complete production ast.cap execution", q)
        print("Complete production ast.cap candidate: all declarations admitted and constructor/type/collection helpers executed")

        # The complete checked compiler is the actual target. Do not prune
        # declarations, rename functions, or substitute a synthetic subset.
        probe = root / "compiler-probe"
        p = run(repo, cli, probe, *SOURCE_FILES)
        print(p.stdout.decode(errors="replace"))
        if p.returncode != 0:
            assert not probe.exists(), "rejection must not publish executable"
            assert b"candidate aggregate backend rejected complete checked module" in p.stdout, p.stdout
            print("Complete compiler candidate admission: BLOCKED (see diagnostic above)")
        else:
            # A produced ELF is still not acceptance: verify actual compiler CLI.
            q = subprocess.run([str(probe), "--version"], capture_output=True, timeout=5)
            assert q.returncode == 0 and q.stdout.startswith(b"Capstan "), (q.returncode, q.stdout, q.stderr)
            print("Complete compiler candidate emitted and version executed; C-hosted driver is NOT S1")
    print("Aggregate native CLI fixture and fail-closed workspace checks passed")

if __name__ == "__main__":
    main()
