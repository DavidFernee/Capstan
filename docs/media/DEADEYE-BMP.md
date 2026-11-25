# Deadeye strict BMP ingest vertical slice

**Implementation:** `lib/halyard/deadeye.cap`  
**Dependency:** `lib/halyard/core.cap`  
**Status:** first Capstan-native still-image parser prototype; not release-ready.

## Why BMP first

The Shroud source audit found `lib/shroud/png.cap` implements PNG encoding only. It writes 8-bit RGBA PNG with stored-DEFLATE blocks, CRC-32 and Adler-32. There is no PNG decoder to reuse. Shroud's independent test harness decodes encoder output with Python zlib; that remains an isolated test oracle, not an implementation dependency. The encoder also materialises multiple image-sized lists and a byte-string representation, so Halyard does not copy that memory architecture.

Deadeye starts with a deliberately narrow uncompressed BMP profile. This avoids making a DEFLATE inflater and PNG filter pipeline part of the first hostile-input parser. PNG can be added later as a first-party Capstan implementation with its own resource and conformance gates.

## Supported BMP profile

The first decoder accepts only:
- the 14-byte BMP file header and 40-byte Windows BITMAPINFOHEADER;
- BI_RGB compression (value zero);
- 24-bit BGR and 32-bit BGRx pixels;
- positive width and nonzero signed height, with bottom-up and top-down row order;
- a canonical pixel-data offset of 54 bytes, no palette or metadata gap;
- zero reserved file-header fields, one plane, no palette declarations;
- at most 8,192 pixels on either side, 2,097,152 pixels total and 16 MiB input;
- exact file-size and image-size consistency (zero image-size is accepted for BI_RGB).

Rows are DWORD-aligned; 24-bit row padding is skipped. Pixels are emitted as row-major RGBA8. The fourth byte of 32-bit BI_RGB is reserved in this profile and is ignored; output alpha is always 255. No colour profile, gamma, palette, alpha-mask, bitfield, RLE or OS/2 header semantics are inferred.

The parser rejects other DIB sizes, compression modes, bit depths, offsets, palettes, dimensions, inconsistent lengths, truncated data and trailing bytes.

## Capstan implementation and tests

All decoder, conversion, helper and regression logic is authored in Capstan in
`lib/halyard/deadeye.cap`. The module imports sibling `core.cap`; it does not use
parent-directory imports, foreign-language shims, third-party image code or generated-C
media implementation.

Six colocated Capstan test declarations cover:
- bottom-up 24-bit decode with row padding and exact pixel orientation;
- top-down 32-bit decode and opaque alpha handling;
- malformed signatures and file-size mismatch;
- unsupported DIB header, compression and bit depth;
- invalid dimensions and noncanonical pixel offset;
- image-size mismatch and mutated-source rejection.

Run the module tests by invoking Capstan test mode on `lib/halyard/deadeye.cap`.
Exact-head execution is still required; no test-pass or conformance claim is made until observed.

The parser consumes its source. On failure it returns no partial wave/frame value, but the source cursor remains at the point where the error was detected; callers should discard that source rather than retry from an assumed initial position.

## Explicit non-goals and release blockers

- BMP palettes, bitfields, RLE, OS/2, V4/V5, embedded profiles and arbitrary offsets.
- PNG/JPEG/WebP/AVIF/TIFF/OpenEXR and all compressed image/video formats.
- Streaming decode, zero-copy frame views or GPU/hardware paths.
- Aggregate-ledger reservations for pixel input, temporary copies and RGBA output.
- Opaque frame/source state, lifetime-bound ownership, cancellation and full colour-management semantics.
- Adversarial corpus, fuzzing, differential tests, independent review and exact-head CI.
