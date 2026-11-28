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
import sys

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
    ("gc-stale-generation",
     "gc_handle_model.cap",
     "if (slot.generation != handle.generation) {",
     "if (slot.generation < handle.generation) {",
     "gc_assurance_handle_tests.cap"),
    ("memory-stale-generation",
     "ccam_memory_store_model.cap",
     "if (view.generation != region.generation) {",
     "if (view.generation > region.generation) {",
     "ccam_assurance_memory_tests.cap"),
    ("memory-final-allocation-fault",
     "ccam_memory_store_model.cap",
     "if (fail_after_bytes == capacity && capacity > 0) {",
     "if (fail_after_bytes == capacity && capacity > 1) {",
     "ccam_assurance_memory_tests.cap"),
    ("halyard-exact-capacity",
     "halyard_resource_vector_actor.cap",
     "retained <= before.capacity_retained - before.used_retained",
     "retained < before.capacity_retained - before.used_retained",
     "halyard_assurance_resource_tests.cap"),
    ("wal-flush-regression",
     "bosuns_locker_protocol.cap",
     "argument < next.durable_lsn || argument > next.next_lsn",
     "argument > next.next_lsn",
     "bosun_assurance_storage_tests.cap"),
    ("wal-premature-page",
     "bosuns_locker_protocol.cap",
     "argument > next.durable_lsn) {",
     "argument > next.durable_lsn + 1) {",
     "bosun_assurance_storage_tests.cap"),
    ("wal-premature-ack",
     "bosuns_locker_protocol.cap",
     "next.durable_lsn < next.commit_lsn) {",
     "next.durable_lsn < next.commit_lsn - 1) {",
     "bosun_assurance_storage_tests.cap"),
    ("helm-carry-boundary",
     "helm_boot_memory_model.cap",
     "if (low_sum >= HBM_U32_BASE) {",
     "if (low_sum > HBM_U32_BASE) {",
     "helm_assurance_memory_tests.cap"),
    ("helm-overflow-boundary",
     "helm_boot_memory_model.cap",
     "if (high_sum >= HBM_U32_BASE) {",
     "if (high_sum > HBM_U32_BASE) {",
     "helm_assurance_memory_tests.cap"),
    ("branch-target-zero-rejected",
     "ccam_core.cap",
     "target >= 0 && target < instructions.len()",
     "target > 0 && target < instructions.len()",
     "ccam_assurance_malformed_tests.cap"),
    ("trap-reason-max-length",
     "ccam_core.cap",
     "if (n == 0 || n > 64) {",
     "if (n == 0 || n >= 64) {",
     "ccam_assurance_malformed_tests.cap"),
    ("gc-handle-foreign-heap",
     "gc_handle_model.cap",
     "handle.heap_token != heap.heap_token",
     "handle.heap_token == heap.heap_token",
     "gc_assurance_handle_tests.cap"),
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


# Partition by stable identifier; each experiment belongs to exactly one group.
GROUPS = {
    "scalar": {"add-boundary", "sub-boundary", "fuel-off-by-one", "output-boundary",
               "branch-target-zero-rejected", "trap-reason-max-length"},
    "authority": {"capability-rights", "capability-epoch", "channel-wake",
                  "gc-stale-generation", "gc-handle-foreign-heap"},
    "resources": {"memory-stale-generation", "memory-final-allocation-fault",
                  "halyard-exact-capacity", "helm-carry-boundary", "helm-overflow-boundary"},
    "persistence": {"wal-flush-regression", "wal-premature-page", "wal-premature-ack"},
}


def validate_inventory():
    ids = [item[0] for item in MUTATIONS]
    assigned = [ident for group in GROUPS.values() for ident in group]
    if len(ids) != len(set(ids)) or sorted(ids) != sorted(assigned):
        raise ValueError("mutation inventory missing, duplicated or unassigned IDs")


def classify(observed):
    if observed.returncode == 101 and "assertion failed" in observed.stderr:
        return "assertion_detected"
    if observed.returncode == 0:
        return "survived"
    return "unexpected_execution_failure"


def main():
    validate_inventory()
    if len(sys.argv) != 2 or sys.argv[1] not in GROUPS:
        raise SystemExit("select one mutation group: " + ", ".join(GROUPS))
    selected = [item for item in MUTATIONS if item[0] in GROUPS[sys.argv[1]]]
    results = []
    with tempfile.TemporaryDirectory(prefix="capstan-security-mutants-") as tmp:
        directory = Path(tmp) / "verification"
        shutil.copytree(ROOT / "verification", directory)
        baselines = {}
        for suite in sorted({item[4] for item in selected}):
            try:
                baseline = compile_and_run(directory, suite)
                baselines[suite] = baseline.returncode == 0
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                baselines[suite] = False
                print(json.dumps({"baseline": suite, "error": str(exc)[:2000]}), flush=True)
        for name, file, old, new, suite in selected:
            target = directory / file
            source = target.read_text()
            status = "baseline_failed"
            returncode = None
            detail = ""
            if baselines[suite]:
                if source.count(old) != 1:
                    status = "invalid_anchor"
                else:
                    try:
                        target.write_text(source.replace(old, new, 1))
                        observed = compile_and_run(directory, suite)
                        returncode = observed.returncode
                        status = classify(observed)
                    except subprocess.TimeoutExpired:
                        status = "timeout"
                    except (RuntimeError, OSError) as exc:
                        status = "infrastructure_or_build_failure"
                        detail = str(exc)[:2000]
                    finally:
                        target.write_text(source)
            results.append({"id": name, "target": file, "suite": suite,
                            "status": status, "returncode": returncode,
                            "detail": detail})
            print(json.dumps(results[-1]), flush=True)
    if len(results) != len(selected) or not all(
            row["status"] == "assertion_detected" for row in results):
        raise SystemExit("targeted mutation campaign incomplete or surviving mutant")
    print(f"all {len(results)} targeted behavioral mutants detected")


if __name__ == "__main__":
    main()
