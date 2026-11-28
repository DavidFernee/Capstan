"""Bounded source-rewrite pilots for memory checks and WAL ordering.

Instrumentation is isolated from the original source. Each whole guard anchor
must occur exactly once. An atom is evaluated in its original short-circuit
position and recorded as true/false; 2 means not evaluated.
"""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import json

from systematic_runner import capstan_summary_valid

ROOT = Path(__file__).resolve().parents[2]

MEMORY = [
    ("!ccam_mem_manager_valid(manager)", [ "!ccam_mem_manager_valid(manager)" ]),
    ("slot < 0", ["slot < 0"]),
    ("view.generation != region.generation", ["view.generation != region.generation"]),
    ("!region.open", ["!region.open"]),
    ("caller_frame != region.owner_frame ||\n        view.owner_frame != region.owner_frame",
     ["caller_frame != region.owner_frame", "view.owner_frame != region.owner_frame"]),
    ("!((view.element_size == 1 && view.alignment == 1) ||\n          (view.element_size == 8 && view.alignment == 8))",
     ["view.element_size == 1", "view.alignment == 1", "view.element_size == 8", "view.alignment == 8"]),
    ("index < 0 || index >= view.count", ["index < 0", "index >= view.count"]),
    ("!relative.ok", ["!relative.ok"]),
    ("!absolute.ok", ["!absolute.ok"]),
    ("!end.ok", ["!end.ok"]),
    ("view.offset < 0 || end.value > region.used ||\n        end.value > region.capacity || end.value > region.bytes.len()",
     ["view.offset < 0", "end.value > region.used", "end.value > region.capacity", "end.value > region.bytes.len()"]),
    ("view.offset % view.alignment != 0", ["view.offset % view.alignment != 0"]),
]

WAL = [
    ("argument < next.durable_lsn || argument > next.next_lsn",
     ["argument < next.durable_lsn", "argument > next.next_lsn"]),
    ("argument <= 0 || argument > next.next_lsn ||\n            argument > next.durable_lsn",
     ["argument <= 0", "argument > next.next_lsn", "argument > next.durable_lsn"]),
    ("argument < next.page_lsn", ["argument < next.page_lsn"]),
    ("next.commit_lsn <= 0 ||\n            next.durable_lsn < next.commit_lsn",
     ["next.commit_lsn <= 0", "next.durable_lsn < next.commit_lsn"]),
]


def instrument(source, prefix, signature_end, clone, guards):
    start = source.index(prefix)
    end = source.index("\n}\n", start) + 3
    function = source[start:end]
    signature = function[:function.index(" {")]
    if not signature.endswith(signature_end):
        raise ValueError("unexpected function signature")
    name = prefix.split()[1].split("(")[0]
    updated = signature.replace(name, clone, 1)[:-1] + ", List<int> trace)"
    function = updated + function[len(signature):]
    ordinal = 0
    for guard, conditions in guards:
        anchor = "if (" + guard + ")"
        if function.count(anchor) != 1:
            raise ValueError("missing or ambiguous guard: " + guard)
        replacement = guard
        for condition in conditions:
            if replacement.count(condition) != 1:
                raise ValueError("missing or ambiguous atom: " + condition)
            replacement = replacement.replace(
                condition, f"assurance_trace_atom(trace, {ordinal}, ({condition}))", 1)
            ordinal += 1
        function = function.replace(anchor, "if (" + replacement + ")", 1)
    return function, ordinal


COMMON = """
bool assurance_trace_atom(List<int> trace, int index, bool value) {
    assert(trace[index] == 2);
    if (value) { trace[index] = 1; } else { trace[index] = 0; }
    return value;
}
void assurance_trace_report(List<int> trace) {
    List<string> values = new List<string>();
    for (int i = 0; i < trace.len(); i += 1) { values.push(int_to_str(trace[i])); }
    println("ASSURANCE_TRACE " + join(values, ""));
}
List<int> assurance_trace_empty(int count) {
    List<int> trace = new List<int>();
    for (int i = 0; i < count; i += 1) { trace.push(2); }
    return trace;
}
"""

MEM_HARNESS = """
test "memory instrumentation preserves access disposition and validation precedence" {
    for (int count = 1; count <= 8; count += 1) {
        for (int caller = 0; caller <= 2; caller += 1) {
            for (int generation = 0; generation <= 2; generation += 1) {
                for (int index = -1; index <= count; index += 1) {
                    for (int fault = 0; fault < 5; fault += 1) {
                        CCAMMemManager manager = ccam_mem_manager(1, 8);
                        CCAMMemCreateResult created = ccam_mem_create(manager, 1, 8, -1);
                        assert(created.ok);
                        CCAMMemResult reserved = ccam_mem_reserve(manager, created.identity, 1, count, 1, 1);
                        assert(reserved.ok);
                        CCAMMemView view = reserved.view;
                        view.generation = generation;
                        if (fault == 1) { view.identity += 1; }
                        if (fault == 2) { view.owner_frame += 1; }
                        if (fault == 3) { view.alignment = 2; }
                        if (fault == 4) { view.offset = -1; }
                        List<int> trace = assurance_trace_empty(20);
                        string baseline = ccam_mem_check(manager, view, caller, index);
                        string observed = assurance_traced_memory(manager, view, caller, index, trace);
                        assert(baseline == observed);
                        assurance_trace_report(trace);
                        assert(trace[0] == 0);
                        if (fault == 1) {
                            assert(trace[1] == 1);
                            for (int t = 2; t < 20; t += 1) { assert(trace[t] == 2); }
                        } else if (generation != 1) {
                            assert(trace[1] == 0 && trace[2] == 1);
                            for (int t = 3; t < 20; t += 1) { assert(trace[t] == 2); }
                        } else if (caller != 1) {
                            assert(trace[4] == 1 && trace[5] == 2);
                            for (int t = 6; t < 20; t += 1) { assert(trace[t] == 2); }
                        }
                        assert(manager.live_regions == 1 && manager.live_capacity == 8);
                        for (int b = 0; b < 8; b += 1) { assert(manager.regions[0].bytes[b] == 0); }
                    }
                }
            }
        }
    }
}
"""

WAL_HARNESS = """
bool assurance_storage_same(BLStorageState a, BLStorageState b) {
    return a.next_lsn == b.next_lsn && a.durable_lsn == b.durable_lsn &&
        a.page_lsn == b.page_lsn && a.page_persisted == b.page_persisted &&
        a.commit_lsn == b.commit_lsn && a.acknowledged == b.acknowledged;
}
test "WAL instrumentation preserves ordering decisions and transition state" {
    for (int written = 0; written <= 4; written += 1) {
        for (int durable = 0; durable <= written; durable += 1) {
            for (int page = 0; page <= durable; page += 1) {
                for (int committed = 0; committed < 2; committed += 1) {
                    BLStorageState state = bl_storage_initial();
                    state.next_lsn = written; state.durable_lsn = durable;
                    state.page_lsn = page; state.page_persisted = page > 0;
                    if (committed == 1) { state.commit_lsn = written; }
                    assert(bl_storage_invariant(state));
                    for (int mode = 0; mode < 3; mode += 1) {
                        int action = BL_STORAGE_FLUSH_LOG;
                        if (mode == 1) { action = BL_STORAGE_FLUSH_PAGE; }
                        if (mode == 2) { action = BL_STORAGE_ACK_COMMIT; }
                        for (int argument = -1; argument <= 5; argument += 1) {
                            List<int> trace = assurance_trace_empty(8);
                            BLStorageState original = bl_storage_copy_state(state);
                            BLStorageTransition baseline = bl_storage_step(state, action, argument);
                            BLStorageTransition actual = assurance_traced_storage(state, action, argument, trace);
                            assert(actual.accepted == baseline.accepted && actual.error == baseline.error);
                            assert(assurance_storage_same(actual.state, baseline.state));
                            assert(assurance_storage_same(state, original));
                            assurance_trace_report(trace);
                            if (mode == 0 && argument < durable) {
                                assert(trace[0] == 1 && trace[1] == 2);
                            }
                            if (mode == 1 && argument <= 0) {
                                assert(trace[2] == 1 && trace[3] == 2 && trace[4] == 2 && trace[5] == 2);
                            }
                            if (mode == 2 && state.commit_lsn == 0) {
                                assert(trace[6] == 1 && trace[7] == 2);
                            }
                        }
                    }
                }
            }
        }
    }
}
"""


def validate_trace_output(output, width, expected_rows):
    rows = []
    for line in output.splitlines():
        if line.startswith(b"ASSURANCE_TRACE "):
            values = line[len(b"ASSURANCE_TRACE "):]
            if len(values) != width or any(value not in b"012" for value in values):
                raise ValueError("invalid condition observation")
            rows.append(values)
    if len(rows) != expected_rows or not capstan_summary_valid(output):
        raise ValueError("missing or incomplete execution evidence")
    return [{"atom": i, "false": sum(row[i] == 48 for row in rows),
             "true": sum(row[i] == 49 for row in rows),
             "not_evaluated": sum(row[i] == 50 for row in rows)}
            for i in range(width)]


def main():
    profiles = [
        ("ccam_memory_store_model.cap", "string ccam_mem_check(", "\n)",
         "assurance_traced_memory", MEMORY, 20, 2340, MEM_HARNESS),
        ("bosuns_locker_protocol.cap", "BLStorageTransition bl_storage_step(",
         "int argument)", "assurance_traced_storage", WAL, 8, 1470, WAL_HARNESS),
    ]
    for file, prefix, suffix, clone, guards, width, expected_rows, harness in profiles:
        source = ROOT / "verification" / file
        raw = source.read_bytes()
        rewritten, count = instrument(raw.decode("utf-8"), prefix, suffix, clone, guards)
        if count != width:
            raise ValueError("unexpected condition inventory")
        with tempfile.TemporaryDirectory(prefix="capstan-trace-") as tmp:
            fixture = Path(tmp) / "instrumented.cap"
            fixture.write_text(COMMON + rewritten + "\n" + harness, encoding="utf-8")
            print(f"{file}: source_sha256={hashlib.sha256(raw).hexdigest()} atoms={count}", flush=True)
            result = subprocess.run([ROOT / "bin/capstan", "test", source, fixture],
                                    cwd=ROOT, capture_output=True, timeout=180)
            # Preserve actual observed masks in the enclosing suite log even on failure.
            print(result.stdout.decode("utf-8", errors="replace"), end="", flush=True)
            print(result.stderr.decode("utf-8", errors="replace"), end="", flush=True)
            result.check_returncode()
            summary = validate_trace_output(result.stdout, width, expected_rows)
            print(json.dumps({"source": file, "rows": expected_rows, "conditions": summary}),
                  flush=True)


if __name__ == "__main__":
    main()
