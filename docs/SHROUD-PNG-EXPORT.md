# Shroud PNG export: limits, allocation accounting and remaining work

Status: current implementation and measured evidence. This document describes the
bounded PNG path; it does **not** claim a process-wide memory bound or streaming.

## 1. Supported format

Shroud writes non-interlaced PNG with:
- 8-bit RGBA colour (colour type 6);
- filter type 0 on every scanline;
- zlib-wrapped DEFLATE stored blocks (no compression);
- one IDAT chunk, followed by IEND.

The stored-block stream is deliberately simple and deterministic. Each block
contains at most 65,535 raw bytes. Adler-32 is calculated while scanline bytes
are emitted; CRC-32 covers the completed IDAT chunk. The encoder writes those
bytes directly into the final PNG list rather than retaining separate
full-image raw-scanline and zlib lists.

## 2. Dimension and raw-byte budget

`MAX_PNG_RAW_BYTES` is 2,097,152 (2 MiB), including one filter byte per row.
The preflight uses division before multiplication:

```
row_bytes = 1 + 4 * width
height <= MAX_PNG_RAW_BYTES / row_bytes
```

Width and height must each be in 1..16,384. This prevents arithmetic overflow
and rejects oversized images before allocating the PNG output list or opening
the destination path.

The 2 MiB budget deliberately accommodates the existing 560×520 reference
gallery: `(1 + 4*560) * 520 = 1,165,320` filtered bytes. The largest tested
accepted case is 1023×512:

| Case | Filtered bytes | Result |
|---|---:|---|
| 560×520 gallery | 1,165,320 | accepted |
| 1023×512 | 2,095,616 | accepted |
| 1024×512 | 2,097,664 | rejected |

The 1023×512 case is 1,536 bytes below the 2 MiB ceiling. Its filtered stream
uses 32 stored DEFLATE blocks. The 1024×512 case exceeds the ceiling by 512
bytes and is rejected before PNG output allocation. Rejection returns an empty
encoded list / `false` from `png_write`; it does not create a destination file.

## 3. Allocation model

The current runtime `write_file` interface accepts a string, not a byte slice
or stream. The encoder therefore still has to materialise:
1. the final PNG as `List<int>`;
2. bounded 4 KiB string chunks;
3. the final joined output string.

The conversion reuses a cached table of the 256 possible one-byte strings and
one 4 KiB `parts` list across all batches. Each batch overwrites that fixed list
with byte-string references (clearing unused tail entries), joins it to one
chunk string, and then joins the chunk strings once. It does not allocate a new
CapStr object for every output byte or a fresh growing parts list for every batch.

The runtime's `CapList` stores 8-byte `CapVal` entries and doubles capacity
from an initial capacity of 8. For the 1023×512 maximum accepted test case:

- PNG file length: 2,095,839 bytes.
- Final output-list capacity: 2,097,152 entries = 16 MiB.
- Sum of the output-list backing-array allocations during geometric growth:
  4,194,296 entries = 32 MiB minus 64 bytes, before collection.
- Pixmap pixel count: 523,776.
- Final Pixmap-list capacity: 1,048,576 entries = 8 MiB.
- Sum of Pixmap-list backing-array allocations during geometric growth:
  2,097,144 entries = 16 MiB minus 64 bytes, before collection.
- Chunk strings plus final joined string: approximately 4 MiB, plus small
  CapStr headers.
- The cached byte-string table, 4 KiB parts list, chunk-reference list, CRC
  table and IHDR list add only tens of KiB.

The resulting conservative *cumulative allocation* envelope for constructing
the Pixmap and encoding one maximum-sized image is approximately 52 MiB before
GC/allocator metadata and unrelated application state. This is not the same as
simultaneously live bytes: earlier geometrically grown list buffers become
garbage and may be reclaimed. Conversely, GC timing, retained Pixmaps, other
views, fonts and application state can increase the observed process heap.
The 2 MiB raw-byte ceiling is therefore emphatically **not** a 2 MiB heap or
RSS ceiling.

### Measured CI high-water marks

The standalone verifier runs three actual exports (128×128, 560×520 and
1023×512), independently decodes them, and records `CAPSTAN_GC_STATS` peak
heap for the combined test process. After reusing one bounded 4 KiB parts list
across conversion chunks, exact-head CI run `45350392496` on commit
`c1d6386a9d96b4dcecf67bd7394251ffa875fdf8` passed all four jobs:

| Runner | Normal peak GC heap | ASan+UBSan peak GC heap |
|---|---:|---:|
| macOS / Clang | 43.0 MiB | 47.0 MiB |
| Ubuntu / Clang | 43.0 MiB | 47.0 MiB |
| Ubuntu / GCC | 47.1 MiB | 56.9 MiB |

These are measured Capstan GC heap high-water marks for the combined test
workload, not resident-set-size measurements, not a worst-case bound for a
whole application, and not evidence that all allocator/OS memory is included.
The values are consistent with the allocation derivation above; the GCC
sanitizer run is the highest observed heap at 56.9 MiB.

## 4. Verification

`tests/shroud/png_budget.cap` and
`tests/shroud/check_png_budget.py` are invoked by `tests/run.sh` in both the
ordinary Shroud run and the ASan+UBSan run.

The Python verifier independently checks:
- PNG signature, chunk order, lengths and every chunk CRC;
- stored-DEFLATE block type, LEN/NLEN, block boundaries and final-block marker;
- zlib decompression and Adler-32;
- every decoded RGBA pixel and row filter for 128×128, 560×520 and 1023×512;
- exact byte preservation for all values 0x00..0xFF through `bytes_text()`;
- absence of a destination file after an over-budget `png_write`.

The existing gallery golden test also verifies that all eight rendered frames
and accessibility trees remain byte-for-byte identical to the recorded
baselines on the tested platforms.

## 5. Known limitations and required next step

- Exports above 2 MiB of filtered scanline data are intentionally rejected.
  This excludes common larger desktop and 4K screenshots. The ceiling is a
  temporary safety bound, not the desired product capability.
- The final PNG byte list and final joined string coexist. The measured
  allocation envelope is not a process-wide resource guarantee.
- Budget rejection occurs before opening the destination path. An I/O failure
  during the current string-based `write_file` call can still leave a partial
  file; the runtime API has no atomic temporary-file/commit contract.
- The current writer does not stream to a bounded sink.

The correct long-term design is a runtime-owned binary writer with bounded
chunk writes, explicit open/write/finish/abort semantics, short-write and error
handling, a caller-visible total-byte budget, and atomic destination commit
(or documented cleanup semantics). Shroud can then emit PNG signature, chunk
headers, zlib blocks, scanline bytes and checksums incrementally without a
full output `List<int>` or joined string. This interface must be designed with
the runtime/capability-I/O owner; Shroud must not invent a second file-I/O path.
