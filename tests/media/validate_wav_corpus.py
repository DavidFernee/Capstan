#!/usr/bin/env python3
"""Independent, stdlib-only oracle for the synthetic RIFF/WAVE corpus."""
import json
import struct
import sys
from pathlib import Path

def decode(blob):
    if len(blob) < 12: return {"error":"truncated_riff_header"}
    if blob[:4] != b"RIFF": return {"error":"not_riff"}
    if blob[8:12] != b"WAVE": return {"error":"not_wave"}
    declared = struct.unpack_from("<I", blob, 4)[0]
    if declared < 4: return {"error":"invalid_riff_size"}
    if declared - 4 != len(blob) - 12: return {"error":"riff_size_mismatch"}
    pos, fmt, data, chunks = 12, None, None, 0
    while pos < len(blob):
        if chunks >= 1024: return {"error":"chunk_limit"}
        if len(blob)-pos < 8: return {"error":"truncated_chunk_header"}
        tag, size = blob[pos:pos+4], struct.unpack_from("<I",blob,pos+4)[0]
        pos += 8
        pad = size & 1
        if size > len(blob)-pos or pad > len(blob)-pos-size:
            return {"error":"truncated_chunk"}
        payload = blob[pos:pos+size]
        if tag == b"fmt ":
            if fmt is not None: return {"error":"duplicate_fmt"}
            if size < 16: return {"error":"short_fmt"}
            code,ch,rate,byte_rate,align,bits = struct.unpack_from("<HHIIHH",payload)
            if code != 1: return {"error":"unsupported_format"}
            if not 1 <= ch <= 8: return {"error":"invalid_channels"}
            if not 1 <= rate <= 384000: return {"error":"invalid_sample_rate"}
            if bits not in (8,16,24,32): return {"error":"unsupported_bit_depth"}
            expected_align = ch*(bits//8)
            if align != expected_align or byte_rate != rate*expected_align:
                return {"error":"invalid_pcm_alignment"}
            fmt=(ch,rate,byte_rate,align,bits)
        elif tag == b"data":
            if fmt is None: return {"error":"fmt_required_before_data"}
            if data is not None: return {"error":"duplicate_data"}
            if size % fmt[3]: return {"error":"invalid_data_alignment"}
            data=payload
        pos += size + pad
        chunks += 1
    if fmt is None: return {"error":"missing_fmt"}
    if data is None: return {"error":"missing_data"}
    ch,rate,byte_rate,align,bits=fmt
    width=bits//8
    samples=[]
    for i in range(0,len(data),width):
        raw=int.from_bytes(data[i:i+width],"little",signed=(bits!=8))
        samples.append(raw-128 if bits==8 else raw)
    return {"sample_rate":rate,"channels":ch,"bits_per_sample":bits,
            "block_align":align,"byte_rate":byte_rate,"samples":samples}

def validate(corpus):
    errors=[]
    if not isinstance(corpus,dict) or corpus.get("corpus_version")!="1.0.0":
        return ["corpus: expected object with corpus_version 1.0.0"]
    cases=corpus.get("cases")
    if not isinstance(cases,list) or not cases: return ["cases: expected non-empty array"]
    seen=set()
    for i,case in enumerate(cases):
        p=f"cases[{i}]"
        if not isinstance(case,dict): errors.append(f"{p}: expected object"); continue
        ident=case.get("id")
        if not isinstance(ident,str) or not ident: errors.append(f"{p}.id: expected non-empty string")
        elif ident in seen: errors.append(f"{p}.id: duplicate id")
        else: seen.add(ident)
        try: raw=bytes.fromhex(case["wav_hex"])
        except (KeyError,TypeError,ValueError): errors.append(f"{p}.wav_hex: invalid hex fixture"); continue
        actual=decode(raw)
        if actual != case.get("expected"):
            errors.append(f"{p} ({ident}): oracle result differs from expected vector: {actual!r}")
    return sorted(errors)

def main(argv):
    if len(argv)!=2:
        print(f"usage: {Path(argv[0]).name} CORPUS.json",file=sys.stderr); return 2
    try: corpus=json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError) as exc:
        print(f"corpus input error: {exc}",file=sys.stderr); return 2
    errors=validate(corpus)
    if errors:
        print("\\n".join(errors),file=sys.stderr); return 1
    print(f"valid WAV corpus: {len(corpus['cases'])} fixtures")
    return 0

if __name__=="__main__": raise SystemExit(main(sys.argv))
