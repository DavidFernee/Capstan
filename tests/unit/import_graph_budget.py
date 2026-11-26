#!/usr/bin/env python3
"""Exact and adversarial aggregate-budget tests for compiler import graphs."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

COMPILER = pathlib.Path(sys.argv[1]).resolve()


def run(root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(COMPILER), "check", str(root)],
        cwd=root.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
    )


def expect_success(root: pathlib.Path, label: str) -> None:
    result = run(root)
    if result.returncode != 0:
        raise SystemExit(f"{label}: expected success; exit={result.returncode}\n{result.stdout[-4000:]}")


def expect_failure(root: pathlib.Path, needle: str, label: str) -> None:
    result = run(root)
    if result.returncode == 0 or needle not in result.stdout:
        raise SystemExit(f"{label}: expected {needle!r}; exit={result.returncode}\n{result.stdout[-4000:]}")


def expect_reaches_parser(root: pathlib.Path, needle: str, label: str) -> None:
    result = run(root)
    if result.returncode == 0 or needle in result.stdout:
        raise SystemExit(f"{label}: expected a parser diagnostic, not {needle!r}; exit={result.returncode}\n{result.stdout[-4000:]}")


def write_chain(directory: pathlib.Path, imported_files: int) -> pathlib.Path:
    directory.mkdir()
    (directory / "main.cap").write_text('import "f0.cap";\n')
    for i in range(imported_files):
        body = f'import "f{i + 1}.cap";\n' if i + 1 < imported_files else "void main() {}\n"
        (directory / f"f{i}.cap").write_text(body)
    return directory / "main.cap"


def padded(prefix: str, size: int) -> str:
    marker = "//"
    return prefix + marker + ("x" * (size - len(prefix) - len(marker) - 1)) + "\n"


with tempfile.TemporaryDirectory(prefix="capstan-import-budget-") as td:
    base = pathlib.Path(td)

    # Root plus 255 imports is exactly 256 distinct files.
    expect_success(write_chain(base / "file-count-exact", 255), "exact file-count budget")
    expect_failure(write_chain(base / "file-count-over", 256), "file-count limit", "file-count budget")

    # A single source is limited to 16 MiB, independently of the graph total.
    graph = base / "source-file-exact"
    graph.mkdir()
    (graph / "main.cap").write_text(padded("void main() {}\n", 16 * 1024 * 1024))
    expect_success(graph / "main.cap", "exact per-file source-byte budget")

    graph = base / "source-file-over"
    graph.mkdir()
    (graph / "main.cap").write_text(padded("void main() {}\n", 16 * 1024 * 1024 + 1))
    expect_failure(graph / "main.cap", "over 16 MiB", "per-file source-byte budget")

    # Each file is below 16 MiB; exactly 32 MiB is accepted, one byte more is not.
    mib = 1024 * 1024
    graph = base / "source-bytes-exact"
    graph.mkdir()
    (graph / "main.cap").write_text(padded('import "f0.cap";\n', 11 * mib))
    (graph / "f0.cap").write_text(padded('import "f1.cap";\n', 11 * mib))
    (graph / "f1.cap").write_text(padded("void main() {}\n", 10 * mib))
    expect_success(graph / "main.cap", "exact aggregate source-byte budget")

    graph = base / "source-bytes-over"
    graph.mkdir()
    (graph / "main.cap").write_text(padded('import "f0.cap";\n', 11 * mib))
    (graph / "f0.cap").write_text(padded('import "f1.cap";\n', 11 * mib))
    (graph / "f1.cap").write_text(padded("void main() {}\n", 10 * mib + 1))
    expect_failure(graph / "main.cap", "source budget", "aggregate source-byte budget")

    # EOF is not a token: 500,000 tokens reach the parser, 500,001 are refused.
    graph = base / "tokens-exact"
    graph.mkdir()
    (graph / "main.cap").write_text(";" * 500_000)
    expect_reaches_parser(graph / "main.cap", "total token budget", "exact token budget")

    graph = base / "tokens-over"
    graph.mkdir()
    (graph / "main.cap").write_text(";" * 500_001)
    expect_failure(graph / "main.cap", "total token budget", "aggregate token budget")

    # A constant contributes its declaration and literal expression nodes.
    graph = base / "ast-exact"
    graph.mkdir()
    declarations = "".join(f"const int value{i} = 0;\n" for i in range(75_000))
    (graph / "main.cap").write_text(declarations)
    expect_success(graph / "main.cap", "exact AST-node budget")

    graph = base / "ast-over"
    graph.mkdir()
    declarations = "".join(f"const int value{i} = 0;\n" for i in range(75_001))
    (graph / "main.cap").write_text(declarations)
    expect_failure(graph / "main.cap", "AST-node limit", "aggregate AST-node budget")

print("compiler import graph: exact and over-limit file, byte, token and AST budgets")
