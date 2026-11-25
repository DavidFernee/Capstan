# Capstan Media security assurance and vulnerability accounting

> **Status:** mandatory security programme and release policy, 2026-11-25.
> This document specifies required controls and evidence. It does not assert that the
> current prototype or architecture is vulnerability-free.

## 1. Security objective

For every released Shanty, Deadeye and Media Core configuration:

- Every publicly known, applicable vulnerability in first-party code, dependencies,
  platform adapters, codecs, parsers, demuxers, protocol handlers, metadata handlers,
  build tools and shipped transitive components is inventoried and dispositioned.
- No known applicable vulnerability may be silently accepted or left without an owner,
  mitigation, evidence and review date.
- Every known vulnerability with a reproducible trigger is represented by a regression
  test, exploitability test or a documented reason why reproduction is not technically
  possible in the supported configuration.
- Untrusted media processing is isolated and resource-bounded so that a defect in a
  codec does not automatically grant host-level authority.
- Release is blocked by unresolved critical/high-risk applicable findings, failed
  security regressions, unknown dependency provenance, or missing security evidence.

This is an operational assurance target, not a mathematical assertion that no unknown
vulnerability exists. "Not reproducible" is not equivalent to "not vulnerable"; an
environment-specific failed exploit attempt is not a sufficient disposition.

## 2. Vulnerability accounting system

Maintain a machine-readable vulnerability ledger for all shipped and build-time
components. Each record must contain:

- stable advisory/CVE/GHSA/vendor identifier(s), aliases and source URLs;
- affected component, source revision, version range and build configuration;
- affected code path, feature flags, platform and reachable input surface;
- root-cause class and security impact;
- exploit preconditions and public proof-of-concept / regression corpus references;
- applicability analysis for every supported Capstan configuration;
- status: applicable, not applicable with evidence, fixed, mitigated, accepted exception
  (release-blocking unless formally approved), or under investigation;
- fix commit, first fixed version and regression test identifier;
- owner, reviewer, discovery date, last recheck and next review date;
- residual risk and compensating controls.

The ledger must include vulnerabilities without CVE identifiers, vendor advisories,
security mailing-list reports, bug-bounty disclosures, OSS-Fuzz findings, static-analysis
findings and internally discovered defects. Deduplicate aliases without losing provenance.

Automated feeds are necessary but insufficient. At minimum, reconcile NVD/CVE, GitHub
Advisories, OSV, CISA KEV, vendor/project advisories, distro security trackers, release
notes, security mailing lists and fuzzing issue trackers. Record feed timestamps and
query coverage. Reconcile the SBOM against each feed on every build and release.

## 3. Required vulnerability classes

The threat catalogue is intentionally broader than known CVEs. Each class needs
preventive design rules, static/dynamic detection, targeted fuzzing and regression tests.

### Memory safety and lifetime
- heap/stack/global out-of-bounds read/write; off-by-one and underflow;
- use-after-free, double-free, invalid-free, stale references and aliasing;
- uninitialised or partially initialised data, information disclosure;
- invalid pointer arithmetic, alignment faults, type confusion and object-size errors;
- race conditions, data races, TOCTOU and unsafe cross-thread buffer ownership.

### Arithmetic and representation
- integer overflow/underflow, signedness and truncation;
- multiplication/addition overflow in dimensions, strides, plane sizes, sample counts,
  channel counts, block sizes, offsets and allocation sizes;
- divide/modulo by zero, invalid shifts, endian confusion and sign-extension;
- timestamp/timebase overflow, wraparound, precision loss and inconsistent rounding;
- parser differential and ambiguous/non-canonical representation.

### Parser, demuxer and bitstream logic
- truncated, overlong, malformed, nested, recursive and contradictory structures;
- invalid chunk/atom/box sizes, offsets, lengths, counts, indexes and table references;
- malformed variable-length integers, Huffman/code tables, entropy coding and bit readers;
- invalid codec parameter sets, sequence headers, slice/tile/partition maps and references;
- malformed metadata, EXIF, ICC, XMP, ID3, subtitles, captions, chapters and attachments;
- state-machine confusion across seek, flush, reset, discontinuity and format changes;
- parser differentials between sniffers, demuxers, decoders and downstream consumers.

### Resource exhaustion and algorithmic complexity
- decompression bombs and extreme dimensions/resolutions;
- excessive frame/sample/packet/track/chunk counts and metadata sizes;
- unbounded allocation, retention, queues, recursion, threads and reassembly;
- quadratic/exponential parsing, pathological codebooks and adversarial complexity;
- CPU/GPU exhaustion, watchdog bypass, hangs, deadlocks and cancellation failure;
- decompression ratio abuse, sparse/large files and integer-amplified allocations.

### Injection, authority and data leakage
- path traversal, local-file inclusion, SSRF and unsafe external manifest/playlist references;
- credential leakage on redirects, proxy confusion and unsafe URL scheme handling;
- command, script, macro, template, XML/entity and dynamic-library loading injection;
- unsafe project/session file deserialization and arbitrary plugin/element instantiation;
- metadata, thumbnails, logs, crash dumps or decoded pixels leaking memory/secrets;
- malicious subtitle, font, attachment, artwork or embedded document handling.

### Cryptography, protocol and supply chain
- weak or incorrect cryptographic use, nonce reuse, downgrade and authentication errors;
- TLS/certificate validation defects, redirect policy errors and insecure transport;
- parser/decoder dependency vulnerabilities and compromised build artifacts;
- malicious codec plugins, dependency confusion, typosquatting and unpinned sources;
- compromised toolchains, reproducibility gaps, provenance and signing failures.

### Platform and hardware boundaries
- GPU shader/compiler/driver attack surfaces and untrusted command buffers;
- DMA/shared-memory lifetime, mapping and bounds errors;
- hardware decoder firmware/driver exposure and unsafe fallback paths;
- device hotplug, malformed device responses, callback races and privilege escalation;
- sandbox escape, IPC confusion, confused deputy and worker protocol flaws.

## 4. Mandatory architecture controls

1. Memory-safe implementation for new parsers and security-critical glue wherever possible.
2. Checked arithmetic at every trust boundary; no implicit integer narrowing.
3. Bounded input, output, aggregate memory, dimensions, decoded work, queues, threads,
   recursion and deadlines. Budget is charged before work/allocation.
4. Parse into validated typed representations; never pass raw untrusted offsets or
   dimensions directly into allocation, pointer arithmetic, GPU or renderer APIs.
5. Capability-minimal codec workers with no ambient filesystem/network/device/secret access.
6. Independent validation of worker outputs and strict IPC framing.
7. No implicit plugin loading, URL fetching, path opening, script execution or attachment
   interpretation from media content.
8. Deterministic codec selection from an explicit allowlist; no automatic "try every
   decoder" fallback on hostile inputs.
9. Separate control plane from real-time audio callback; callback performs no blocking
   I/O, unbounded allocation, contended locking or arbitrary plugin callback.
10. Software reference path and output validation for hardware-accelerated processing.
11. Dependency pinning, SBOM, source provenance, signed artifacts and reproducible builds.
12. Fail closed on malformed data, budget exhaustion, unknown mandatory features and
    worker faults; no partially trusted output is published.

## 5. Reproduction and regression protocol

For every applicable public or internal vulnerability:

1. Obtain the authoritative advisory, affected source revision and patch.
2. Reconstruct the vulnerable precondition and identify the precise input boundary.
3. Create or obtain a legally usable minimal reproducer; preserve provenance and hash.
4. Run only in a disposable, network-isolated, resource-limited test environment.
5. Demonstrate the vulnerable behavior on a known-affected reference build where safe
   and feasible; record exact environment and output.
6. Run the same input against the proposed Capstan implementation and every shipped
   backend/configuration.
7. Require safe rejection or correct decoding, bounded resource use, no memory-safety
   violation, no authority escape and no output corruption.
8. Retain the input as a regression corpus item; add minimized variants and mutations.
9. If reproduction is impossible, record why, the missing preconditions, independent
   evidence and reviewer approval. Do not mark "fixed" based only on non-reproduction.
10. Verify the fix with sanitizers, fuzz regression, differential tests and source review.

Exploit reproducer artifacts must be handled as hazardous inputs. Never run them on a
developer workstation or privileged CI runner.

## 6. Testing and analysis requirements

- Continuous coverage-guided fuzzing for every parser, demuxer, bitstream parser, decoder,
  encoder, metadata reader, manifest parser, subtitle parser and worker IPC boundary.
- Structure-aware fuzzing seeded from specifications and real-world corpora.
- Mutation, truncation, boundary-value, differential and metamorphic testing.
- ASan, UBSan, MSan and TSan where supported; platform-specific equivalents otherwise.
- Static analysis, taint/dataflow review, integer/bounds check analysis and dependency scans.
- Property-based tests for arithmetic, ownership, state machines and resource ledgers.
- Fault injection for allocation failure, short reads, cancellation, worker death, timeout,
  device loss, clock discontinuity and malformed IPC.
- Long-running fuzz campaigns with coverage tracking, corpus minimisation and regression
  retention. A green short fuzz run is not proof of safety.
- Independent penetration review before broad release; red-team media corpus for each
  supported format family.

## 7. Release gates

A release is blocked if any of these hold:

- an applicable critical/high severity vulnerability is open;
- a known vulnerability lacks an evidence-backed disposition;
- a known reproducer triggers unsafe behavior in any supported release configuration;
- any parser/decoder can exceed its declared resource budget;
- a codec executes outside its declared isolation/capability policy;
- SBOM, provenance, dependency revision or licence/patent review is incomplete;
- security regression tests fail or required fuzz jobs are stale;
- a new codec/format lacks a threat review, adversarial corpus and ownership assignment;
- an exception lacks written rationale, named approver, compensating controls and expiry.

Severity is not the sole criterion: a low-scored issue that crosses a trust boundary or
breaks a declared invariant can still block release.

## 8. Operational vulnerability response

- Continuous advisory and dependency monitoring; urgent triage for actively exploited
  vulnerabilities and CISA KEV entries.
- Defined response SLAs by severity and exploitability, with emergency release capability.
- Rebuild and retest all affected supported configurations after a fix.
- Publish security advisories and machine-readable affected/fixed version data.
- Preserve evidence, hashes, provenance and regression artifacts.
- Reassess historical releases and provide upgrade/mitigation guidance.
- Re-open prior dispositions when reachability, configuration or threat intelligence changes.

## 9. Initial audit workstreams

- Inventory every current Capstan media-related dependency, tool and transitive component.
- Build a format-to-parser/decoder attack-surface map for each proposed supported format.
- Import and deduplicate advisories from GStreamer, FFmpeg, image/audio codec projects,
  protocol implementations, operating-system vendors and vulnerability databases.
- Build a root-cause taxonomy and regression corpus, not merely a CVE spreadsheet.
- Audit Shroud's PNG code and every current binary input/output path.
- Define worker isolation per supported OS; identify where no robust sandbox exists.
- Establish CI jobs for SBOM/advisory reconciliation, fuzzing, sanitizers and reproducibility.

## 10. Evidence and claim discipline

Use precise statuses: inventoried, applicability-assessed, reproducer-retained, fixed,
mitigated, regression-passing, fuzzed (with campaign duration/corpus/coverage), reviewed,
model-checked, formally verified (with exact property), and implementation-refined.

Never claim "all vulnerabilities eliminated", "unhackable", or "no vulnerabilities exist"
from a clean scanner, no known CVEs, a passing test suite, a fuzzing campaign or a formal
model alone. The defensible release statement is that all known applicable findings in
the declared scope have evidence-backed dispositions, required regressions pass, and
residual risks and scope are published.
