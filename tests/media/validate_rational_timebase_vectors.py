#!/usr/bin/env python3
"""Validate rational-timebase conformance vectors with an independent integer oracle.

This validates the corpus and its expected answers. It does NOT execute the Capstan
runtime and is not implementation-conformance evidence.
"""
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1
ROUNDING = {"exact", "toward_zero", "floor", "ceil", "nearest_even"}


def fail(message):
    raise SystemExit(f"rational-timebase vectors: {message}")


def integer(value, label):
    if not isinstance(value, str) or not value or value.strip() != value:
        fail(f"{label}: expected canonical decimal string")
    if value in {"-0", "+0"} or value.startswith("+"):
        fail(f"{label}: non-canonical integer")
    try:
        number = int(value, 10)
    except ValueError:
        fail(f"{label}: invalid integer")
    if str(number) != value:
        fail(f"{label}: non-canonical integer")
    return number


def bounded_i64(value, label):
    number = integer(value, label)
    if number < I64_MIN or number > I64_MAX:
        fail(f"{label}: outside signed-64 range")
    return number


def timebase(value, label, reduced=True):
    if not isinstance(value, list) or len(value) != 2:
        fail(f"{label}: expected [numerator, denominator]")
    n = bounded_i64(value[0], label + ".numerator")
    d = bounded_i64(value[1], label + ".denominator")
    if n <= 0 or d <= 0:
        return None
    if reduced and math.gcd(n, d) != 1:
        return None
    return Fraction(n, d)


def round_fraction(q, mode):
    if mode == "exact":
        if q.denominator != 1:
            return None
        return q.numerator
    if mode == "toward_zero":
        return abs(q.numerator) // q.denominator * (1 if q >= 0 else -1)
    if mode == "floor":
        return q.numerator // q.denominator
    if mode == "ceil":
        return -((-q.numerator) // q.denominator)
    if mode == "nearest_even":
        sign = 1 if q >= 0 else -1
        magnitude = abs(q)
        whole, rem = divmod(magnitude.numerator, magnitude.denominator)
        twice = rem * 2
        if twice > magnitude.denominator or (
            twice == magnitude.denominator and whole % 2 == 1
        ):
            whole += 1
        return sign * whole
    fail(f"unknown rounding mode {mode!r}")


def validate_rescale(v):
    src = timebase(v["source_tb"], v["id"] + ".source_tb")
    dst = timebase(v["target_tb"], v["id"] + ".target_tb")
    ticks = bounded_i64(v["input_ticks"], v["id"] + ".input_ticks")
    mode = v["rounding"]
    if mode not in ROUNDING:
        fail(f"{v['id']}: invalid rounding mode")
    expected = v["expected"]
    if src is None or dst is None:
        if expected != {"ok": False, "error": "invalid_timebase"}:
            fail(f"{v['id']}: invalid timebase must fail closed")
        return
    result = round_fraction(Fraction(ticks) * src / dst, mode)
    if result is None:
        actual = {"ok": False, "error": "inexact"}
    elif result < I64_MIN or result > I64_MAX:
        actual = {"ok": False, "error": "overflow"}
    else:
        actual = {"ok": True, "ticks": str(result)}
    if actual != expected:
        fail(f"{v['id']}: expected {expected}, oracle produced {actual}")


def validate_wrap(v):
    width = v["width"]
    if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 63:
        if v["expected"].get("error") != "invalid_wrap_width":
            fail(f"{v['id']}: invalid width must be rejected")
        return
    modulus = 1 << width
    anchor = bounded_i64(v["anchor_unwrapped"], v["id"] + ".anchor")
    raw = integer(v["raw"], v["id"] + ".raw")
    window = integer(v["max_abs_delta"], v["id"] + ".window")
    if raw < 0 or raw >= modulus:
        actual = {"ok": False, "error": "raw_counter_out_of_range"}
    else:
        delta = (raw - (anchor % modulus)) % modulus
        if delta * 2 == modulus:
            actual = {"ok": False, "error": "ambiguous_wrap"}
        else:
            signed_delta = delta if delta * 2 < modulus else delta - modulus
            if window < 0 or window * 2 >= modulus or abs(signed_delta) > window:
                actual = {"ok": False, "error": "wrap_out_of_window"}
            else:
                unwrapped = anchor + signed_delta
                if unwrapped < I64_MIN or unwrapped > I64_MAX:
                    actual = {"ok": False, "error": "overflow"}
                else:
                    actual = {"ok": True, "delta": str(signed_delta), "unwrapped": str(unwrapped)}
    if actual != v["expected"]:
        fail(f"{v['id']}: expected {v['expected']}, oracle produced {actual}")


def validate_metadata(v):
    kind = v["kind"]
    if kind == "timebase":
        tb = timebase(v["input"], v["id"] + ".input")
        actual = {"ok": tb is not None}
        if tb is None:
            actual["error"] = "invalid_timebase"
    elif kind == "duration":
        ticks = None if v["ticks"] is None else bounded_i64(v["ticks"], v["id"] + ".ticks")
        invalid = ticks is not None and (ticks < 0 or (ticks == 0 and v["sample_kind"] == "video_frame" and v["known"]))
        actual = {"ok": not invalid}
        if invalid:
            actual["error"] = "invalid_duration"
        else:
            actual["duration"] = None if not v["known"] else str(ticks)
    else:
        fail(f"{v['id']}: unknown metadata vector kind")
    if actual != v["expected"]:
        fail(f"{v['id']}: expected {v['expected']}, got {actual}")


def validate_epochs(v):
    op = v["operation"]
    if op == "compare":
        left, right = v["left"], v["right"]
        if left["stream"] != right["stream"] or left["epoch"] != right["epoch"]:
            actual = {"ok": False, "error": "epoch_mismatch"}
        else:
            lt = bounded_i64(left["ticks"], v["id"] + ".left")
            rt = bounded_i64(right["ticks"], v["id"] + ".right")
            ltb = timebase(left["tb"], v["id"] + ".left.tb")
            rtb = timebase(right["tb"], v["id"] + ".right.tb")
            if ltb is None or rtb is None:
                fail(f"{v['id']}: invalid comparison timebase")
            actual = {"ok": True, "ordering": "equal" if Fraction(lt) * ltb == Fraction(rt) * rtb else ("less" if Fraction(lt) * ltb < Fraction(rt) * rtb else "greater")}
    elif op == "discontinuity":
        if v["policy"] == "reject":
            actual = {"ok": False, "error": "discontinuity_rejected", "epoch_unchanged": True}
        elif v["policy"] == "reset":
            actual = {"ok": True, "epoch": v["new_epoch"], "mapping": None}
        elif v["policy"] == "rebase":
            actual = {"ok": True, "epoch": v["new_epoch"], "mapping": "explicit_anchor_only"}
        else:
            fail(f"{v['id']}: unknown discontinuity policy")
    else:
        fail(f"{v['id']}: unknown epoch operation")
    if actual != v["expected"]:
        fail(f"{v['id']}: expected {v['expected']}, got {actual}")


def validate_seek(v):
    op = v["operation"]
    if op == "seek":
        actual = {"ok": True, "generation": v["new_generation"], "epoch": v["new_epoch"]}
    elif op == "completion":
        stale = v["completion_generation"] != v["active_generation"]
        actual = {"ok": not stale}
        if stale:
            actual.update(error="stale_generation", state_unchanged=True)
    elif op == "presentation_trim":
        present = integer(v["frame_pts"], v["id"] + ".frame_pts") >= integer(v["target_ticks"], v["id"] + ".target_ticks") if v["same_epoch"] else False
        actual = {"present": present}
        if not present:
            actual["reason"] = "before_seek_target" if v["same_epoch"] else "epoch_mismatch"
    else:
        fail(f"{v['id']}: unknown seek operation")
    if actual != v["expected"]:
        fail(f"{v['id']}: expected {v['expected']}, got {actual}")


def validate_clock(v):
    op = v["operation"]
    if op == "project":
        mtb = timebase(v["media_tb"], v["id"] + ".media_tb")
        ctb = timebase(v["clock_tb"], v["id"] + ".clock_tb")
        if mtb is None or ctb is None:
            fail(f"{v['id']}: invalid timebase")
        delta = bounded_i64(v["media_ticks"], v["id"] + ".media_ticks") - bounded_i64(v["media_anchor"], v["id"] + ".media_anchor")
        if delta < I64_MIN or delta > I64_MAX:
            fail("media delta subtraction overflow")
        anchor = bounded_i64(v["clock_anchor"], v["id"] + ".clock_anchor")
        projected = Fraction(anchor) + Fraction(delta) * mtb / ctb
        if projected.denominator != 1 or projected.numerator < I64_MIN or projected.numerator > I64_MAX:
            actual = {"ok": False, "error": "overflow"}
        else:
            actual = {"ok": True, "clock_ticks": str(projected.numerator)}
    elif op == "resync":
        actual = {"ok": True, "generation": v["new_generation"], "prior_mapping_invalidated": True}
    elif op == "external_observation":
        if v["monotonic_required"] and integer(v["new_clock_ticks"], v["id"] + ".new") < integer(v["previous_clock_ticks"], v["id"] + ".previous"):
            actual = {"ok": False, "error": "external_clock_regression", "state_unchanged": True}
        else:
            actual = {"ok": True}
    else:
        fail(f"{v['id']}: unknown external-clock operation")
    if actual != v["expected"]:
        fail(f"{v['id']}: expected {v['expected']}, got {actual}")


def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != "capstan.media.rational-timebase.v1":
        fail("unsupported schema_version")
    seen = set()
    sections = {
        "rescale_vectors": validate_rescale,
        "metadata_vectors": validate_metadata,
        "wrap_vectors": validate_wrap,
        "epoch_vectors": validate_epochs,
        "seek_vectors": validate_seek,
        "external_clock_vectors": validate_clock,
    }
    count = 0
    for section, validator in sections.items():
        vectors = data.get(section)
        if not isinstance(vectors, list) or not vectors:
            fail(f"{section}: expected a non-empty array")
        for vector in vectors:
            ident = vector.get("id")
            if not isinstance(ident, str) or not ident or ident in seen:
                fail(f"{section}: missing or duplicate vector id")
            seen.add(ident)
            validator(vector)
            count += 1
    vfr = data.get("vfr_vectors")
    if not isinstance(vfr, list) or not vfr:
        fail("vfr_vectors: expected a non-empty array")
    for vector in vfr:
        if vector.get("id") in seen:
            fail("duplicate vector id")
        seen.add(vector["id"])
        tb = timebase(vector["tb"], vector["id"] + ".tb")
        if tb is None:
            fail(f"{vector['id']}: invalid timebase")
        previous_pts = None
        for sample in vector["samples"]:
            pts = bounded_i64(sample["pts"], vector["id"] + ".pts")
            bounded_i64(sample["dts"], vector["id"] + ".dts")
            duration = bounded_i64(sample["duration"], vector["id"] + ".duration")
            if duration <= 0:
                fail(f"{vector['id']}: known VFR duration must be positive")
            if previous_pts is not None and pts < previous_pts:
                # PTS order is sample/presentation order in this corpus; DTS may differ.
                fail(f"{vector['id']}: VFR presentation timestamps must not regress")
            previous_pts = pts
        if vector["expected"].get("preserve_each_pts") is not True:
            fail(f"{vector['id']}: must preserve each PTS")
        count += 1
    print(f"validated {count} rational-timebase vectors (independent oracle; runtime not exercised)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: validate_rational_timebase_vectors.py <vectors.json>")
    main(sys.argv[1])
