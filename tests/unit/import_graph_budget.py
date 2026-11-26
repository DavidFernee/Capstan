#!/usr/bin/env python3
"""Adversarial aggregate-budget tests for compiler import graphs."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

COMPILER = pathlib.Path(sys.argv[1]).resolve()


def run_case(root: pathlib.Path, expected: str, label: str) -> None:
    result = subprocess.run(
        [str(COMPILER), "check", str(root)],
        cwd=root.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )
    if result.returncode == 0 or expected not in result.stdout:
        raise SystemExit(
            f"{label}: expected diagnostic containing {expected!r}; "
            f"exit={result.returncode}\n{result.stdout[-4000:]}"
        )


with tempfile.TemporaryDirectory(prefix="capstan-import-budget-") as td:
    base = pathlib.Path(td)

    # 257 distinct files (root plus 256 imports) exceed the graph file ceiling.
    graph = base / "file-count"
    graph.mkdir()
    (graph / "main.cap").write_text('import "f0.cap";\n')
    for i in range(256):
        body = f'import "f{i + 1}.cap";\n' if i < 255 else "void main() {}\n"
        (graph / f"f{i}.cap").write_text(body)
    run_case(graph / "main.cap", "file-count limit", "file-count budget")

    # Every file is below 16 MiB, but their combined source exceeds 32 MiB.
    graph = base / "source-bytes"
    graph.mkdir()
    padding = "//" + ("x" * (11 * 1024 * 1024 - 4)) + "\n"
    (graph / "main.cap").write_text('import "f0.cap";\n' + padding)
    (graph / "f0.cap").write_text('import "f1.cap";\n' + padding)
    (graph / "f1.cap").write_text("void main() {}\n" + padding)
    run_case(graph / "main.cap", "source budget", "aggregate source-byte budget")

    # A token flood is stopped by the lexer before it allocates token 500,001.
    graph = base / "tokens"
    graph.mkdir()
    (graph / "main.cap").write_text(";" * 500_001)
    run_case(graph / "main.cap", "total token budget", "aggregate token budget")

    # Many small declarations stay below the token ceiling but exceed the AST cap.
    graph = base / "ast"
    graph.mkdir()
    declarations = "".join(f"const int value{i} = 0;\n" for i in range(60_000))
    (graph / "main.cap").write_text(declarations)
    run_case(graph / "main.cap", "AST-node limit", "aggregate AST-node budget")

print("compiler import graph: file, source-byte, token and AST budgets reject over-limit graphs")
