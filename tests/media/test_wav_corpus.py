#!/usr/bin/env python3
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("wav_oracle",ROOT/"tests/media/validate_wav_corpus.py")
oracle=importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
CORPUS=json.loads((ROOT/"tests/media/fixtures/wav-pcm-corpus.json").read_text(encoding="utf-8"))

class WavCorpusTests(unittest.TestCase):
    def test_all_fixture_bytes_match_independent_oracle(self):
        self.assertEqual(oracle.validate(CORPUS),[])
    def test_required_sample_widths_present(self):
        valid=[c for c in CORPUS["cases"] if "samples" in c["expected"]]
        self.assertEqual({c["expected"]["bits_per_sample"] for c in valid},{8,16,24,32})
    def test_mono_and_multichannel_present(self):
        valid=[c for c in CORPUS["cases"] if "samples" in c["expected"]]
        self.assertIn(1,{c["expected"]["channels"] for c in valid})
        self.assertTrue(any(c["expected"]["channels"]>1 for c in valid))
    def test_negative_cases_present(self):
        errors={c["expected"].get("error") for c in CORPUS["cases"] if "error" in c["expected"]}
        self.assertTrue({"invalid_pcm_alignment","truncated_chunk","fmt_required_before_data","invalid_data_alignment"} <= errors)
    def test_duplicate_ids_rejected(self):
        value=copy.deepcopy(CORPUS); value["cases"].append(copy.deepcopy(value["cases"][0]))
        self.assertTrue(any("duplicate id" in e for e in oracle.validate(value)))
    def test_mutated_expected_sample_rejected(self):
        value=copy.deepcopy(CORPUS); value["cases"][0]["expected"]["samples"][0]=0
        self.assertTrue(any("differs from expected vector" in e for e in oracle.validate(value)))

if __name__=="__main__": unittest.main()
