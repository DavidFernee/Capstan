# Deadeye first image decoder: format and provenance audit

**Decision:** retain the strict uncompressed BMP / 40-byte BITMAPINFOHEADER / BI_RGB profile as Deadeye's first still-image decoder prototype. This is a bounded engineering-sequence decision, not a release-support or patent-clearance statement.

**Review date:** 2026-11-26  
**Implementation snapshot:** main at 189f19dd2a39c169e033691856d675b070fb2864

## 1. Exact Shroud capability audit

The relevant implementation is lib/shroud/png.cap. It writes PNG: 8-bit RGBA scanlines, PNG chunks, CRC-32, zlib-wrapped stored-DEFLATE blocks and Adler-32. It contains encoder/output code; it does not parse PNG input, inflate DEFLATE, reverse PNG filters or expose a PNG decoder API. A PNG encoder must not be mistaken for a PNG decoder.

The related tests are tests/shroud/png_budget.cap and tests/shroud/check_png_budget.py. They exercise bounded export and use Python's zlib to independently inspect/decode generated image data as a test oracle. That oracle is not a Capstan decoder and is not linked into Shroud or Halyard. The Shroud golden/behaviour tests are UI/rendering tests, not general PNG ingest tests.

The first Deadeye decoder is in lib/halyard/deadeye.cap, with eight colocated Capstan test declarations documented in docs/media/DEADEYE-BMP.md. Those tests cover bottom-up 24-bit row padding, top-down 32-bit opaque alpha, malformed signatures/lengths, unsupported headers/compression/bit depth, dimensions/offset, mutated sources and logical budget admission. The source documents them as tests present; exact-head execution and independent adversarial corpus coverage remain separate evidence requirements.

## 2. Candidate comparison

| Candidate | Security / implementation complexity | Licensing and provenance | Corpus / semantic considerations | Decision |
|---|---|---|---|---|
| Strict BMP BI_RGB | Small fixed header profile; uncompressed pixels; row padding and orientation arithmetic only. No decompressor, entropy decoder or filter reversal. | Microsoft documents bitmap storage and DIB headers. Library of Congress describes BMP as proprietary but reports no licensing/patent concerns; MDN notes Microsoft patent rights and an Open Specification Promise, and cautions that a promise is not a licence. These sources do not establish a definitive legal clearance for every implementation/use. | Easy to author tiny synthetic fixtures for dimensions, signed height, stride, padding, truncation and exact pixels. Pixel semantics are limited and must be explicit. | **Selected first prototype**, with legal review still a release gate. |
| PNG | Mature and well-specified, but a decoder adds chunk parsing, CRC checks, zlib/DEFLATE, five row filters, colour metadata and decompression-amplification controls. Much larger hostile-input surface than this first slice. | W3C PNG Third Edition describes PNG as a patent-free replacement for GIF. Still requires provenance and dependency review for any implementation; no external decoder code is to be copied or linked. | Excellent public test material and reference tools; broad bit depths, indexed/truecolour/greyscale, alpha, interlace and colour metadata substantially enlarge conformance scope. | Strong later candidate after a bounded inflater and resource ledger are independently assured. |
| JPEG | Entropy decoding, quantisation, IDCT, subsampling, restart markers and metadata; more complex arithmetic and error recovery. | Patent/provenance review is codec/profile-specific; do not infer clearance from common availability. | Large mature corpora exist, but lossy output requires tolerance rules and colour/subsampling semantics. | Defer. |
| GIF | Palette and LZW decode, extensions, transparency and animation/frame disposal. | Requires independent review of current implementation provenance and applicable rights; no third-party implementation is proposed. | Mature corpus, but animation disposal and palette corner cases expand the first milestone. | Defer. |
| TIFF / WebP / AVIF / JPEG XL | Multiple variants, compression methods, metadata and colour semantics; several imply substantial codec machinery. | Requires format- and implementation-specific review. | High-quality corpora exist, but the profile space is too broad for the first decoder. | Defer. |

## 3. BMP provenance and legal status

Primary format references:
- Microsoft Learn, Bitmap Storage: https://learn.microsoft.com/en-us/windows/win32/gdi/bitmap-storage
- Microsoft Open Specifications, BitmapInfoHeader Object: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-wmf/567172fa-b8a2-4d79-86a2-5e21d6659ef3
- Library of Congress, BMP format description: https://www.loc.gov/preservation/digital/formats/fdd/fdd000189.shtml
- MDN image type comparison and its BMP licensing note: https://developer.mozilla.org/en-US/docs/Web/Media/Formats/Image_types
- W3C PNG Third Edition (comparison): https://www.w3.org/TR/png-3/

The BMP format is proprietary in origin and Microsoft supplies the most authoritative structural documentation. The Library of Congress assessment says “no concerns” in its licensing/patent field, while MDN records that Microsoft holds patents against BMP and has published a non-assertion promise subject to conditions; MDN explicitly distinguishes that promise from a licence. This discrepancy is treated conservatively: Capstan has not received legal clearance. The implementation is first-party, authored in Capstan, with no copied or linked decoder code. A formal legal review of the exact BI_RGB profile, Open Specification Promise applicability and relevant territories remains mandatory before release distribution.

The PNG comparison is clearer at the format level: W3C calls PNG a patent-free replacement for GIF. That does not make an arbitrary PNG decoder implementation, dependency or build chain automatically cleared. The first implementation remains a from-scratch Capstan project.

## 4. Selected BMP profile: normative semantics before expansion

The initial decoder is intentionally restricted to:
- 14-byte BITMAPFILEHEADER followed by exactly one 40-byte BITMAPINFOHEADER;
- BI_RGB compression only;
- 24-bit BGR or 32-bit BGRx input;
- positive signed width and nonzero signed height; positive height is bottom-up, negative height is top-down;
- canonical pixel offset 54, one plane, zero reserved fields, no palette declarations or metadata gap;
- maximum side 8,192 pixels, maximum 2,097,152 pixels, maximum input 16 MiB;
- exact file-size and image-size consistency, with zero image-size permitted for BI_RGB.

For width W and bits-per-pixel B, the input row stride is DWORD aligned:

    row_stride = ((W * B + 31) // 32) * 4

All multiplications/additions must be checked before allocation or slicing. The decoder must reject if the calculated stride, total pixel extent or file extent exceeds the validated input/budget bounds. Rows are emitted in top-to-bottom order regardless of input orientation. The output is row-major RGBA8. BGR input channels are reordered to RGB. For 32-bit BI_RGB, the fourth BGRx byte is reserved/ignored; output alpha is always 255. No palette, bitfield mask, RLE, V4/V5 header, embedded profile, gamma, ICC, orientation metadata or colour transform is inferred. The output is untagged sample data; it must not be advertised as colour-managed sRGB.

Unsupported inputs fail closed; no best-effort fallback or guessed interpretation is permitted.

## 5. Security and release gates

The selection is based on a smaller parser/decompressor surface, not a claim that BMP is inherently safe. Before release:
1. Complete legal review of BMP patent/OSP and format-documentation provenance.
2. Add a redistributable, independently generated BMP corpus with positive and negative fixtures covering every accepted field, arithmetic boundary, row orientation, row padding, truncation, trailing data, oversized dimensions and malformed reserved/header fields.
3. Differential-check output pixels against at least one independent implementation, used only as a test oracle.
4. Run coverage-guided and mutation fuzzing with strict CPU, memory and input bounds; retain all failures as regression fixtures.
5. Bind every parser allocation to the shared resource ledger and enforce opaque source/frame ownership and failure atomicity.
6. Execute exact-head Capstan tests on supported CI platforms; record sanitizer and fuzz evidence separately.
7. Keep the decoder profile and compatibility registry entry direction-specific; do not infer support for other BMP DIB headers or compressed variants.

No parser is claimed vulnerability-free. This audit chooses the smallest first step and preserves the remaining evidence gates.
