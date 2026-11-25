# Shanty RIFF/WAVE PCM vertical slice

**Implementation:** `lib/halyard/shanty.cap`  
**Dependency:** `lib/halyard/core.cap`  
**Status:** first Capstan-native offline parser/decoder prototype; not release-ready.

## Supported input profile

The first Shanty slice recognises RIFF/WAVE and accepts only integer PCM format tag 1:

- 1–8 channels;
- sample rates from 1 through 384,000 Hz;
- 8-, 16-, 24- and 32-bit samples;
- exact block alignment and byte-rate consistency;
- one `fmt ` chunk before one `data` chunk;
- unknown chunks skipped with RIFF odd-length padding;
- no more than 1,024 chunks;
- input bounded to 8 MiB.

The parser rejects a malformed RIFF/WAVE signature, inconsistent RIFF length, truncated chunk headers or payloads, duplicate format/data chunks, data before format, unsupported format tags/bit depths, invalid channel/rate values, invalid block alignment, and trailing bytes outside the declared RIFF form.

Eight-bit WAVE PCM is unsigned and is centred by subtracting 128. Sixteen-, twenty-four- and thirty-two-bit PCM are decoded as signed little-endian two's-complement values. Samples remain in their original integer bit-depth domain and are interleaved by frame/channel. No floating-point conversion, normalisation, resampling, mixing, clipping or dithering is performed.

## Explicit non-goals

This slice does not implement:
- compressed audio codecs or WAVE extensible (`WAVE_FORMAT_EXTENSIBLE`);
- floating-point PCM;
- multiple data chunks, RF64, BW64 or files larger than the declared bound;
- device playback/capture, real-time callbacks, mixing, resampling or DSP;
- streaming decode or zero-copy sample views;
- aggregate-ledger reservations for the copied PCM payload and decoded sample list.

The parser materialises the data chunk, and the decoder materialises an integer sample list. Their peak allocations are therefore larger than the input payload. The 8 MiB input cap is a prototype guard, not a process-memory guarantee. These allocations must be integrated with Halyard's cumulative work budgets and live-resource leases before hostile-input release.

## Capstan implementation and tests

All parser, decoder, helper and regression logic is authored in Capstan in `lib/halyard/shanty.cap`. The module imports the sibling `core.cap`; it does not use parent-directory imports, foreign-language shims, third-party codec code or generated-C media implementation.

Nine colocated Capstan test declarations cover:
- metadata parsing for a stereo 48 kHz/16-bit WAVE file;
- exact signed 16-bit interleaved decoding;
- malformed RIFF signatures and declared sizes;
- unsupported format tags and invalid block alignment;
- unsigned 8-bit centring;
- signed 24- and 32-bit boundary samples;
- unknown-chunk skipping and odd-byte padding;
- rejection of forged PCM byte arrays and inconsistent byte rates;
- rejection of a source mutated after construction.

Run the colocated test declarations using Capstan's test mode for this module. The
current repository bootstrap/toolchain is still part of the execution TCB; the Shanty
implementation and test source itself is Capstan. Exact-head execution is still required;
no test-pass or conformance claim is made until observed.

## Release blockers

- Opaque/non-forgeable Core and Shanty state.
- Aggregate output, retained-memory, allocation and decoded-sample accounting.
- Cumulative work budget that cannot be refunded by releasing sample buffers.
- A streaming parser/decoder design with explicit ownership and cancellation.
- Adversarial RIFF corpus, fuzzing, property tests, malformed-chunk coverage and independent review.
- Exact-head CI and measured peak memory, allocation count, throughput and latency.
