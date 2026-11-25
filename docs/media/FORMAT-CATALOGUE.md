# Shanty and Deadeye compatibility catalogue

> **Status: Target catalogue (2026-11-25).** No row in this document implies an
> implementation or a licence/patent clearance. Decode and encode are separate
> capabilities. Each eventual entry must record exact profiles, versions, platforms,
> test corpus and assurance evidence.

## Shanty — audio

| Family | Formats / codecs | Intended use | Initial status |
|---|---|---|---|
| PCM containers | WAV/RIFF, RF64, WAVE64, AIFF, AU, CAF | Uncompressed and archival audio | Target |
| Lossless | FLAC, ALAC, WavPack, Monkey's Audio | Archival, production | Target |
| Lossy | MP3, AAC, Vorbis, Opus | Consumer and streaming | Target |
| Broadcast/pro | BWF, ADM metadata, AC-3, E-AC-3, DTS | Broadcast and delivery | Target |
| High-resolution | DSD/DSF/DFF, DXD | Specialist audio | Target |
| Event/music | MIDI 1.0, MIDI 2.0, MOD, XM, IT, S3M | Synthesis and tracker music | Target |
| Spatial | Ambisonics, channel-based immersive audio, object metadata | Spatial production | Target |
| Streaming | HLS audio, DASH audio, Icecast/Shoutcast-compatible streams | Live and on-demand | Target |

## Deadeye — video and images

| Family | Formats / codecs | Intended use | Initial status |
|---|---|---|---|
| Containers | MP4/ISO BMFF, QuickTime MOV, Matroska, WebM, AVI, MPEG-TS | Packaging and tracks | Target |
| Modern video | AV1, AVC/H.264, HEVC/H.265, VVC/H.266 | General and high-efficiency video | Target |
| Open/legacy video | VP8, VP9, Theora, MPEG-1/2, Cinepak, Indeo, RealVideo | Compatibility and archival | Target |
| Production | ProRes, DNxHD, DNxHR, JPEG 2000 | Editing and mastering | Target |
| Still images | PNG, JPEG, GIF, TIFF, BMP, WebP, AVIF, JPEG XL | Image ingest | Target |
| High-dynamic-range | OpenEXR, Radiance HDR, DPX | VFX, cinema and scientific imagery | Target |
| Animation | GIF, APNG, animated WebP/AVIF | Animated images | Target |
| Streaming | HLS, MPEG-DASH, fragmented MP4, low-latency profiles | Live and on-demand | Target |
| Ancillary | WebVTT, SRT, TTML, CEA-608/708, chapters, timecode | Captions and production metadata | Target |

## Cross-cutting requirements

- Explicit sample formats, channel layouts, planar/interleaved layouts and sample rates.
- Explicit pixel formats, chroma subsampling, bit depth, alpha, colour primaries,
  transfer characteristics, matrix coefficients and range.
- Variable frame rate, rational timestamps, timecode, discontinuities and seek semantics.
- Multitrack audio/video, metadata, captions, chapters and attachments.
- HDR and wide-gamut handling without silent tone mapping.
- High frame rates, large dimensions, stereo/360-degree and image sequences.
- Software reference implementations and optional hardware acceleration.
- Container support never implies support for every possible codec/profile carried by it.

## Registry record required for every compatibility claim

`id`, `version`, `container`, `codec`, `profile`, `level`, `operation`
(decode/encode/demux/mux), `bit_depth`, `chroma`, `channel_layout`,
`platforms`, `implementation`, `source_revision`, `licence_review`,
`patent_review`, `corpus_revision`, `test_status`, `fuzz_status`,
`assurance_level`, `known_limitations`.

A codec with decode-only support must not be described as encode-capable. A container
with one tested codec must not be described as universal container support.
