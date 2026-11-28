"""Diverse host-toolchain fixpoint and exact fixture conformance.

This is the existing C-backed bootstrap, not evidence of C-free S1.
Every selected fixture runs at three optimisation levels, and failures,
missing expectations, build errors and timeouts are fatal.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SRC = [f"compiler/{n}.cap" for n in
       ("ast", "lexer", "parser", "checker", "ranges", "codegen", "main")]
FIXTURES = [
    "accept/basics", "accept/compound_assignment_order",
    "accept/operand_evaluation_order", "accept/short_circuit",
    "accept/remainder_min_minus_one", "accept/provenance_binding_identity",
    "accept/collections", "gc/integrity", "gc/grant_roots",
    "runtime/integer_overflow", "runtime/integer_underflow",
    "runtime/remainder_by_zero", "runtime/runtime_division_by_zero",
    "runtime/negative_index", "runtime/out_of_bounds_read",
    "runtime/out_of_bounds_write", "runtime/range_divide_minus_one",
    "runtime/grant_for_other_object", "runtime/grant_after_change",
]


def run(argv, cwd=ROOT, **kwargs):
    return subprocess.run(argv, cwd=cwd, capture_output=True, timeout=180, **kwargs)


def require(argv, cwd=ROOT, **kwargs):
    result = run(argv, cwd, **kwargs)
    if result.returncode != 0:
        raise RuntimeError(f"{argv}: exit {result.returncode}: {result.stderr[-2000:]!r}")
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture_expected(path):
    if path.parent.name == "runtime":
        matches = re.findall(r"^// expect-runtime: (.+)$", path.read_text(), re.M)
        if len(matches) != 1:
            raise ValueError(f"missing or ambiguous runtime expectation: {path}")
        return 101, matches[0].encode()
    return 0, path.with_suffix(".out").read_bytes()


def check_outcome(observed, status, expected):
    if observed.returncode != status:
        raise ValueError(f"unexpected process exit {observed.returncode}, expected {status}")
    if status == 0 and observed.stdout != expected:
        raise ValueError("positive fixture output mismatch")
    if status == 101 and expected not in observed.stderr:
        raise ValueError("wrong security diagnostic")


def main():
    cc = os.environ.get("CC", "cc")
    revision = require(["git", "rev-parse", "HEAD"]).stdout.decode().strip()
    tree = require(["git", "rev-parse", "HEAD^{tree}"]).stdout.decode().strip()
    if require(["git", "status", "--porcelain", "--untracked-files=no"]).stdout:
        raise ValueError("dirty source tree")
    report = {"scope": "C-backed bootstrap, not C-free S1",
              "revision": revision, "tree": tree,
              "platform": platform.platform(), "machine": platform.machine(),
              "toolchain": require([cc, "--version"]).stdout.decode(errors="replace"),
              "fixpoints": [], "fixtures": [], "passed": False}
    directory = ROOT / "build" / "portable-assurance"
    directory.mkdir(parents=True, exist_ok=False)
    evidence = directory / "evidence.json"
    def checkpoint():
        temporary = evidence.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(evidence)
    checkpoint()
    reference = ROOT / "build/stage3.c"
    if (ROOT / "build/stage2.c").read_bytes() != reference.read_bytes():
        raise ValueError("bootstrap baseline mismatch")
    with tempfile.TemporaryDirectory(prefix="capstan-portability-") as tmp:
        work = Path(tmp)
        flags = ["-std=gnu11", "-w", "-I", str(ROOT / "runtime")]
        for opt in ("-O0", "-O2", "-O3"):
            compiler = work / "compiler"
            generated = work / "compiler.c"
            require([cc, opt, *flags, reference, "-o", compiler])
            require([compiler, "build", "-o", generated, *SRC])
            if generated.read_bytes() != reference.read_bytes():
                raise ValueError(f"bootstrap differs under {cc} {opt}")
            report["fixpoints"].append({"optimisation": opt, "sha256": digest(generated)})
            checkpoint()
            for name in FIXTURES:
                source = ROOT / "tests" / (name + ".cap")
                status, expected = fixture_expected(source)
                env = dict(os.environ)
                for pair in re.findall(r"^// env: (.+)$", source.read_text(), re.M):
                    for item in pair.split():
                        key, sep, value = item.partition("=")
                        if not sep:
                            raise ValueError("invalid fixture environment")
                        env[key] = value
                capflags = re.findall(r"^// flags: (.+)$", source.read_text(), re.M)
                c = work / "fixture.c"
                exe = work / "fixture"
                c.unlink(missing_ok=True)
                exe.unlink(missing_ok=True)
                require([compiler, "build", "-o", c, *(capflags[0].split() if capflags else []), source])
                require([cc, opt, *flags, c, "-o", exe])
                observed = run([exe], env=env)
                row = {"name": name, "optimisation": opt,
                                           "exit": observed.returncode,
                                           "stdout_sha256": hashlib.sha256(observed.stdout).hexdigest(),
                                           "expected_sha256": hashlib.sha256(expected).hexdigest(),
                                           "stderr_sha256": hashlib.sha256(observed.stderr).hexdigest(),
                                           "generated_c_sha256": digest(c), "passed": False}
                report["fixtures"].append(row)
                checkpoint()
                check_outcome(observed, status, expected)
                row["passed"] = True
                checkpoint()
    if len(report["fixpoints"]) != 3 or len(report["fixtures"]) != 3 * len(FIXTURES):
        raise ValueError("incomplete campaign")
    if require(["git", "status", "--porcelain", "--untracked-files=no"]).stdout:
        raise ValueError("source tree changed during campaign")
    report["passed"] = True
    checkpoint()
    print(f"three C-backed fixpoints and {len(report['fixtures'])} fixture executions passed")


if __name__ == "__main__":
    main()
