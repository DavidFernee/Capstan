"""Targeted behavioral mutations of verification implementations.
A failed build, timeout, signal or infrastructure error is not a killed mutant.
Each baseline must pass; each exact anchored mutation must compile and trigger
a test assertion. The checkout is never modified.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MUTATIONS = [
    ("add-boundary", "ccam_core.cap",
     "b > 0 && a > CCAM_I64_MAX - b",
     "b > 0 && a >= CCAM_I64_MAX - b",
     "ccam_assurance_arithmetic_tests.cap"),
    ("sub-boundary", "ccam_core.cap",
     "b < 0 && a > CCAM_I64_MAX + b",
     "b < 0 && a >= CCAM_I64_MAX + b",
     "ccam_assurance_arithmetic_tests.cap"),
    ("fuel-off-by-one", "ccam_core.cap",
     "if (state.steps >= state.max_steps) {",
     "if (state.steps > state.max_steps) {",
     "ccam_assurance_transition_tests.cap"),
    ("output-boundary", "ccam_core.cap",
     "instruction.byte_data.len() >\n                state.max_output_bytes - state.output_bytes.len()",
     "instruction.byte_data.len() >=\n                state.max_output_bytes - state.output_bytes.len()",
     "ccam_assurance_transition_tests.cap"),
    ("capability-rights", "schooner_capability.cap",
     "(handle.rights & required_rights) != required_rights",
     "(handle.rights & required_rights) == 0",
     "schooner_assurance_capability_tests.cap"),
    ("capability-epoch", "schooner_capability.cap",
     "handle.revocation_epoch != state.revocation_epoch",
     "false",
     "schooner_assurance_capability_tests.cap"),
    ("channel-wake", "concurrency_generated_capacity_graph.cap",
     "next.producer_status = CSG_RUNNABLE;",
     "next.producer_status = CSG_BLOCKED;",
     "concurrency_assurance_capacity_tests.cap"),
]


def run(argv, timeout):
    return subprocess.run(argv, capture_output=True, text=True, timeout=timeout)


def compile_and_run(directory, suite):
    generated = directory / "test.c"
    exe = directory / "test"
    generated.unlink(missing_ok=True)
    exe.unlink(missing_ok=True)
    compiled = run([ROOT / "build/capstanc", "test", "-o", generated,
                    directory / suite], 180)
    if compiled.returncode != 0:
        raise RuntimeError(("test compilation failed", suite, compiled.stdout, compiled.stderr))
    linked = run([os.environ.get("CC", "cc"), "-O2", "-std=gnu11", "-w",
                  "-I", ROOT / "runtime", generated, "-o", exe], 180)
    if linked.returncode != 0:
        raise RuntimeError(("host compilation failed", suite, linked.stderr))
    return run([exe], 180)


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix="capstan-security-mutants-") as tmp:
        directory = Path(tmp) / "verification"
        shutil.copytree(ROOT / "verification", directory)
        for suite in sorted({item[4] for item in MUTATIONS}):
            baseline = compile_and_run(directory, suite)
            if baseline.returncode != 0:
                raise RuntimeError(("baseline failed", suite, baseline.stdout, baseline.stderr))
        for name, file, old, new, suite in MUTATIONS:
            target = directory / file
            source = target.read_text()
            if source.count(old) != 1:
                raise RuntimeError(("mutation anchor is not unique", name, source.count(old)))
            try:
                target.write_text(source.replace(old, new, 1))
                observed = compile_and_run(directory, suite)
            finally:
                target.write_text(source)
            killed = observed.returncode == 101 and "assertion failed" in observed.stderr
            results.append({"id": name, "target": file, "suite": suite,
                            "killed": killed, "returncode": observed.returncode})
            print(json.dumps(results[-1]), flush=True)
    if len(results) != len(MUTATIONS) or not all(row["killed"] for row in results):
        raise SystemExit("targeted mutation campaign incomplete or surviving mutant")
    print(f"all {len(results)} targeted behavioral mutants detected")


if __name__ == "__main__":
    main()
