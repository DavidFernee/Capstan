# Shanty WAV/PCM fixture corpus and runtime capability audit

**Status:** synthetic corpus v1.0.0; independent oracle validation only. This does not claim that the Capstan decoder has executed these fixtures.

## Runtime capability audit

The current parser in lib/halyard/shanty.cap is Capstan-authored and uses the shared Halyard byte-source abstraction. It reads bounded in-memory byte sources, uses integer byte extraction and checked field validation, and returns typed result structs. The profile is RIFF/WAVE PCM format tag 1, 1–8 channels, 1–384000 Hz, 8/16/24/32-bit integer PCM, exact block alignment and byte-rate consistency, one fmt chunk before one data chunk, up to 1024 chunks and 8 MiB input. It skips unknown chunks and RIFF odd-byte padding. Decoding produces interleaved integer samples in their original bit-depth domain; 8-bit PCM is unsigned and centred by subtracting 128.

The parser can be tested through Capstan's colocated test declarations. It does not currently provide file I/O, streaming, device playback/capture, compressed codecs, WAVE extensible, floating-point PCM, RF64, zero-copy sample views or recoverable allocator failure. The source and budget structs remain public/mutable and sequential; the legacy unbudgeted entry points remain callable. These limitations mean the prototype is not yet a hostile-input security boundary or release-ready.

## Corpus

tests/media/fixtures/wav-pcm-corpus.json contains ten original synthetic fixtures. The hex payloads are authored for this repository from the documented profile; no third-party audio is redistributed. Fixture bytes and expected vectors are dedicated to CC0-1.0. Each valid fixture records metadata and exact decoded sample values; negative fixtures record the expected rejection class.

Coverage includes:
- 8-bit mono unsigned boundary values;
- 16-bit stereo signed boundaries and two frames;
- 24-bit stereo signed minimum/maximum;
- 32-bit mono signed minimum/maximum;
- three-channel 16-bit PCM with an odd-length unknown JUNK chunk before fmt and an unknown LIST chunk after data, exercising chunk ordering and pad-byte handling;
- malformed block alignment, truncated data, missing odd-chunk pad byte, data-before-fmt and data length not divisible by block alignment.

The independent oracle in tests/media/validate_wav_corpus.py uses only Python's standard library. It parses RIFF chunk boundaries and independently decodes PCM values, then compares complete results against the recorded vectors. It is test-only and is not a build, runtime or media implementation dependency.

Run:
    python3 -I tests/media/validate_wav_corpus.py tests/media/fixtures/wav-pcm-corpus.json
    python3 -I tests/media/test_wav_corpus.py

## Evidence boundary and remaining work

This corpus validates its own bytes and expected vectors against an independent reference decoder. It is not yet an executable differential input to shanty_wave_parse or shanty_wave_decode_samples; the current Capstan tests remain colocated in lib/halyard/shanty.cap. A follow-up should make the same canonical fixtures drive the Capstan evaluator without maintaining a second set of expected values. No fuzz campaign, exact-head Capstan corpus execution, timing, throughput or peak-memory measurement is claimed.


## Exact Capstan/runtime capability evidence

The current Halyard byte-source implementation in lib/halyard/core.cap provides:
- halyard_source_from_list(input, max_bytes): validates the maximum and every byte (0..255), then copies the caller's list into a defensive snapshot. Its comment explicitly says this is not an ambient file/network source.
- halyard_source_length() and halyard_source_remaining(): bounded metadata queries over the in-memory snapshot.
- halyard_read_exact(source, count): uses the subtraction-form check count <= length - position; on failure the cursor is unchanged.
- halyard_skip() and typed read-result structs for bounded parser movement.
- halyard_consumption_budget_create(input_limit, output_limit, decoded_limit, work_limit): a four-dimensional monotonic consumption budget used by the budgeted Shanty entry points.

The Shanty parser uses Capstan structs, optional values, List<int>, bounded loops, integer bitwise operations and typed result structs. The colocated tests use Capstan test declarations and construct deterministic in-memory fixtures. The source is deliberately independent of ambient filesystem, network and device authority.

The gaps are equally concrete: no file-backed or streaming byte source, asynchronous/short-read transport contract, seek contract, recoverable allocation-result API, mandatory opaque ownership, concurrent ledger semantics or cancellation-aware source lifetime is present in this vertical slice. The public source/budget fields and legacy unbudgeted entry points remain callable. These are runtime/ownership gaps, not a lack of integer byte parsing capability.
