"""Raw SF-P corpus negative controls; not a production CCAM decoder claim."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "sf_validator", ROOT / "scripts/validate-ccam-sf-vectors.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
BASE = json.loads(VALIDATOR.CORPUS.read_text(encoding="utf-8"))


def encode(data):
    return json.dumps(data, ensure_ascii=True, separators=(",", ":")).encode("ascii")


class RawCorpusControls(unittest.TestCase):
    def check_bytes(self, raw, expected):
        original = VALIDATOR.CORPUS
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_bytes(raw)
            VALIDATOR.CORPUS = path
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
                    status = VALIDATOR.main()
                self.assertEqual(status, expected, stderr.getvalue())
            finally:
                VALIDATOR.CORPUS = original

    def test_baseline(self):
        self.check_bytes(encode(BASE), 0)

    def test_duplicate_keys_and_escaped_aliases(self):
        raw = encode(BASE)
        for needle, replacement in (
            (b'"format":', b'"format":"wrong","format":'),
            (b'"op":"const_i"', b'"op":"const_i","op":"const_i"'),
            (b'"dst":0', b'"dst":0,"dst":0'),
            (b'"dst":0', b'"dst":0,"\\u0064st":0'),
        ):
            self.assertIn(needle, raw)
            with self.subTest(replacement=replacement):
                self.check_bytes(raw.replace(needle, replacement, 1), 1)

    def test_noninteger_and_out_of_range_literal_tokens(self):
        raw = encode(BASE)
        needle = b'"value":19'
        self.assertIn(needle, raw)
        for token in (b"true", b"false", b"null", b'"19"', b"19.0", b"19e0",
                      b"NaN", b"Infinity", b"-Infinity", b"9223372036854775808",
                      b"-9223372036854775809", b"01", b"+19"):
            with self.subTest(token=token):
                self.check_bytes(raw.replace(needle, b'"value":' + token, 1), 1)

    def test_unknown_and_missing_instruction_fields(self):
        for key in ("dst", "value", "op"):
            data = copy.deepcopy(BASE)
            del data["vectors"][0]["instructions"][0][key]
            self.check_bytes(encode(data), 1)
        for key in ("unexpected", "lhs", "reason", "target"):
            data = copy.deepcopy(BASE)
            data["vectors"][0]["instructions"][0][key] = 0
            self.check_bytes(encode(data), 1)

    def test_invalid_register_representations(self):
        for register in (-1, 3, 9223372036854775807, True, None, "0", 0.0):
            data = copy.deepcopy(BASE)
            data["vectors"][0]["instructions"][0]["dst"] = register
            with self.subTest(register=register):
                self.check_bytes(encode(data), 1)

    def test_truncation_and_invalid_utf8(self):
        raw = encode(BASE)
        for length in range(64):
            self.check_bytes(raw[:length], 1)
        for suffix in (b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xf4\x90\x80\x80"):
            self.check_bytes(raw + suffix, 1)
        self.check_bytes(raw + b"{}", 1)
        self.check_bytes(b"[" * 2048 + b"]" * 2048, 1)
        self.check_bytes(b" " * (VALIDATOR.MAX_CORPUS_BYTES + 1), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
