#!/usr/bin/env python3
"""Fail-closed pin for the Capstan injection-checker modelled source.

This is a source-identity/coverage precondition, not a semantic refinement proof.
It prevents a checker edit from silently retaining a stale Lean model. A future
AST bridge must replace this pin with a parser-backed translation validator.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "compiler" / "checker.cap"
MODEL = ROOT / "verification" / "lean" / "CapstanVerification" / "InjectionChecker.lean"
SINK_MODEL = ROOT / "verification" / "lean" / "CapstanVerification" / "InjectionSinks.lean"
BASELINE = ROOT / "verification" / "lean" / "fixtures" / "injection_checker_laundering_source.cap"
SOURCE_MARKER = "// ---- laundering analysis (CWE-20)"

REQUIRED_SOURCE_FRAGMENTS = (
    "bool derived(Flow f, Node e)",
    "bool base_marked(Flow f, Node e)",
    "void flow_walk(Flow f, Node n)",
    'e.k == N_METHOD && e.s == "at"',
    'e.k == N_CALL && e.s == "int_to_str"',
    'e.k == N_BIN && e.s == "+" && ty_of(e).k == TY_STR',
    'e.s == "wrapping_add" || e.s == "wrapping_sub"',
    'n.k == N_CALL && n.s == "char_str"',
    'n.k == N_INDEX && texty_type(ty_of(n))',
    'rounds < 100',
    'rounds < 50',
)

REQUIRED_MODEL_FRAGMENTS = (
    "def checkerDerived",
    "def checkerBaseMarked",
    "def checkerWrite",
    "def checkerSummaryReturn",
    "def checkerSummarySink",
    "def checkerOptionalBranch",
    "theorem checkerDerived_agrees_on_supported",
    "theorem comparison_result_not_derived",
    "theorem struct_constructor_not_derived",
)

REQUIRED_SINK_MODEL_FRAGMENTS = (
    "def checkerRejectsSink",
    "theorem char_string_derived_is_rejected",
    "theorem text_index_derived_selector_is_rejected",
    "theorem optional_text_map_get_derived_key_is_rejected",
    "theorem trusted_slice_derived_selector_is_rejected",
)


def fail(message: str) -> None:
    print(f"injection checker source bridge: FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    if not SOURCE.is_file() or not MODEL.is_file() or not SINK_MODEL.is_file():
        fail("run from a complete Capstan checkout; required source/model file missing")

    source = SOURCE.read_text(encoding="utf-8")
    model = MODEL.read_text(encoding="utf-8")
    sink_model = SINK_MODEL.read_text(encoding="utf-8")
    baseline = BASELINE.read_text(encoding="utf-8")
    if SOURCE_MARKER not in source:
        fail("checker laundering-analysis section marker is missing")
    section = source[source.index(SOURCE_MARKER):]
    if section != baseline:
        fail(
            "compiler/checker.cap laundering-analysis section differs from "
            "the reviewed source fixture; inspect transfer/sink/fixpoint changes "
            "and update the model and fixture together"
        )
    missing_source = [fragment for fragment in REQUIRED_SOURCE_FRAGMENTS if fragment not in source]
    missing_model = [fragment for fragment in REQUIRED_MODEL_FRAGMENTS if fragment not in model]
    missing_sink_model = [fragment for fragment in REQUIRED_SINK_MODEL_FRAGMENTS if fragment not in sink_model]
    if missing_source:
        fail("expected checker transfer/sink/fixpoint fragment missing: " + repr(missing_source))
    if missing_model:
        fail("expected Lean model declaration missing: " + repr(missing_model))
    if missing_sink_model:
        fail("expected Lean protected-sink theorem missing: " + repr(missing_sink_model))

    print(
        "injection checker source bridge: PASS "
        "(checker laundering-analysis section matches fixture; transfer and sink model declarations present)"
    )
    print(
        "LIMIT: source identity and declaration-presence checks only; "
        "no AST translation or semantic refinement theorem is established."
    )


if __name__ == "__main__":
    main()
