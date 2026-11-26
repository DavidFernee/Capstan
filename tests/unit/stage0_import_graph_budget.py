#!/usr/bin/env python3
"""Stage-0 conformance tests for bounded compiler import graphs."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

BOOTSTRAP = pathlib.Path(sys.argv[1]).resolve()


def run(root: pathlib.Path, label: str) -> subprocess.CompletedProcess[str]:
    output = root.parent / (label + ".py")
    return subprocess.run(
        [sys.executable, "-I", str(BOOTSTRAP), str(output), str(root)],
        cwd=root.parent,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=180,
        check=False,
    )


def expect_success(root: pathlib.Path, label: str) -> None:
    result = run(root, label)
    if result.returncode != 0:
        raise SystemExit(f"{label}: expected success; exit={result.returncode}\n{result.stdout[-4000:]}")


def expect_failure(root: pathlib.Path, needle: str, label: str) -> None:
    result = run(root, label)
    if result.returncode == 0 or needle not in result.stdout:
        raise SystemExit(f"{label}: expected {needle!r}; exit={result.returncode}\n{result.stdout[-4000:]}")


def expect_reaches_parser(root: pathlib.Path, needle: str, label: str) -> None:
    result = run(root, label)
    if result.returncode == 0 or needle in result.stdout:
        raise SystemExit(f"{label}: expected parser diagnostic, not {needle!r}; exit={result.returncode}\n{result.stdout[-4000:]}")


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


with tempfile.TemporaryDirectory(prefix="capstan-stage0-import-budget-") as td:
    base = pathlib.Path(td)

    expect_success(write_chain(base / "file-count-exact", 255), "stage0-file-count-exact")
    expect_failure(
        write_chain(base / "file-count-over", 256),
        "file-count limit (256)",
        "stage0-file-count-over",
    )

    mib = 1024 * 1024
    graph = base / "source-file-exact"
    graph.mkdir()
    (graph / "main.cap").write_text(padded("void main() {}\n", 16 * mib))
    expect_success(graph / "main.cap", "stage0-per-file-exact")

    graph = base / "source-file-over"
    graph.mkdir()
    (graph / "main.cap").write_text(padded("void main() {}\n", 16 * mib + 1))
    expect_failure(graph / "main.cap", "per-file byte limit", "stage0-per-file-over")

    graph = base / "source-bytes-exact"
    graph.mkdir()
    (graph / "main.cap").write_text(padded('import "f0.cap";\n', 11 * mib))
    (graph / "f0.cap").write_text(padded('import "f1.cap";\n', 11 * mib))
    (graph / "f1.cap").write_text(padded("void main() {}\n", 10 * mib))
    expect_success(graph / "main.cap", "stage0-source-bytes-exact")

    graph = base / "source-bytes-over"
    graph.mkdir()
    (graph / "main.cap").write_text(padded('import "f0.cap";\n', 11 * mib))
    (graph / "f0.cap").write_text(padded('import "f1.cap";\n', 11 * mib))
    (graph / "f1.cap").write_text(padded("void main() {}\n", 10 * mib + 1))
    expect_failure(graph / "main.cap", "source exceeds remaining import-graph byte budget", "stage0-source-bytes-over")

    graph = base / "tokens-exact"
    graph.mkdir()
    (graph / "main.cap").write_text(";" * 500_000)
    expect_reaches_parser(graph / "main.cap", "total token budget", "stage0-exact-token-budget")

    graph = base / "tokens-over"
    graph.mkdir()
    (graph / "main.cap").write_text(";" * 500_001)
    expect_failure(graph / "main.cap", "total token budget", "stage0-token-budget-over")

    graph = base / "ast-exact"
    graph.mkdir()
    declarations = "".join(f"const int value{i} = 0;\n" for i in range(50_000))
    (graph / "main.cap").write_text(declarations)
    expect_success(graph / "main.cap", "stage0-exact-AST-budget")

    graph = base / "ast-over"
    graph.mkdir()
    declarations = "".join(f"const int value{i} = 0;\n" for i in range(50_001))
    (graph / "main.cap").write_text(declarations + ";")
    expect_failure(graph / "main.cap", "AST-node limit", "stage0-AST-budget-over")

print("stage 0 import graph: exact and over-limit file, byte, token and AST budgets")
