"""Instrument an isolated copy of the actual capability-resolution predicate.

This is a source-rewrite pilot, not compiler-wide MC/DC instrumentation.
The original implementation is compiled alongside the transformed copy.
Exact anchors prevent silently instrumenting a different source decision.
"""
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "verification/schooner_capability.cap"

DECISIONS = [
    ["state.revoked", "required_rights <= 0", "!scm_valid_rights(required_rights)"],
    ["handle.object_id != state.object_id",
     "handle.object_generation != state.object_generation",
     "handle.revocation_epoch != state.revocation_epoch"],
    ["!scm_valid_rights(handle.rights)",
     "(handle.rights & required_rights) != required_rights"],
    ["handle.slot == 0"],
    ["state.root_live", "handle.slot_generation == state.root_generation",
     "handle.rights == state.root_rights"],
    ["handle.slot == 1"],
    ["state.child_live", "handle.slot_generation == state.child_generation",
     "handle.rights == state.child_rights"],
]


def instrument(source):
    start = source.index("bool scm_resolves(")
    end = source.index("\n}\n", start) + 3
    fn = source[start:end]
    signature = "bool scm_resolves(SCMState state, SCMHandle handle, int required_rights)"
    if fn.count(signature) != 1:
        raise ValueError("resolution signature changed")
    fn = fn.replace(signature, signature.replace("scm_resolves", "assurance_traced_resolves")
                    .replace("int required_rights)", "int required_rights, List<int> trace)"))
    ordinal = 0
    for conditions in DECISIONS:
        for condition in conditions:
            if fn.count(condition) != 1:
                raise ValueError("missing or ambiguous condition: " + condition)
            fn = fn.replace(condition,
                            f"assurance_trace_atom(trace, {ordinal}, ({condition}))", 1)
            ordinal += 1
    if ordinal != 16:
        raise ValueError("condition inventory changed")
    return fn


HARNESS = """
bool assurance_trace_atom(List<int> trace, int index, bool value) {
    if (value) { trace[index] = 1; } else { trace[index] = 0; }
    return value;
}

test "instrumented actual capability predicate preserves result and short-circuit masks" {
    for (int rights = 1; rights <= 7; rights += 1) {
        for (int required = 0; required <= 8; required += 1) {
            for (int fault = -1; fault < 10; fault += 1) {
                SCMTransition root = scm_issue_root(scm_initial(), rights);
                assert(root.ok);
                SCMState state = root.state;
                SCMHandle h = root.handle;
                if (fault == 0) { state.revoked = true; }
                if (fault == 1) { h.object_id += 1; }
                if (fault == 2) { h.object_generation += 1; }
                if (fault == 3) { h.revocation_epoch += 1; }
                if (fault == 4) { h.rights = 0; }
                if (fault == 5) { h.slot = 2; }
                if (fault == 6) { state.root_live = false; }
                if (fault == 7) { h.slot_generation += 1; }
                if (fault == 8) { h.rights = 7; }
                if (fault == 9) { h.slot = 1; }
                List<int> trace = new List<int>();
                for (int i = 0; i < 16; i += 1) { trace.push(2); }
                bool expected = scm_resolves(state,h,required);
                bool observed = assurance_traced_resolves(state,h,required,trace);
                assert(observed == expected);
                assert(trace[0] == (state.revoked ? 1 : 0));
                if (state.revoked) {
                    for (int i = 1; i < 16; i += 1) { assert(trace[i] == 2); }
                }
                if (!state.revoked && required == 0) {
                    assert(trace[1] == 1);
                    for (int i = 2; i < 16; i += 1) { assert(trace[i] == 2); }
                }
            }
        }
    }
}
"""


def main():
    raw = SOURCE.read_bytes()
    transformed = instrument(raw.decode("utf-8"))
    with tempfile.TemporaryDirectory(prefix="capstan-source-observation-") as tmp:
        fixture = Path(tmp) / "instrumented.cap"
        fixture.write_text(HARNESS.replace(
            "assert(trace[0] == (state.revoked ? 1 : 0));",
            "if (state.revoked) { assert(trace[0] == 1); } else { assert(trace[0] == 0); }")
            + "\n" + transformed, encoding="utf-8")
        print("source_sha256=" + hashlib.sha256(raw).hexdigest(), flush=True)
        subprocess.run([ROOT / "bin/capstan", "test", SOURCE, fixture],
                       cwd=ROOT, check=True, timeout=180)


if __name__ == "__main__":
    main()
