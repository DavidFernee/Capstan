# Security policy

Capstan is a language designed to prevent security vulnerabilities, so a flaw in its
guarantees is a security issue in its own right. Reports are very welcome.

## What to report

- A program that Capstan accepts but that contains a weakness Capstan claims to prevent
  (see [docs/CWE-COVERAGE.md](docs/CWE-COVERAGE.md) and [docs/CWE-ATLAS.md](docs/CWE-ATLAS.md))
- Memory corruption, undefined behaviour or a crash in the compiler, runtime or generated code
- A way to bypass taint tracking, grants, policies, secret handling or other checks
- Problems in the cryptographic code
- Weaknesses in the build, bootstrap or release process

Known, documented gaps listed in the atlas are not new vulnerabilities, but a practical
exploit of one is still worth reporting.

Confirmed findings are credited in the hall of fame of the Capstan Challenge
([docs/CHALLENGE.md](docs/CHALLENGE.md)), a planned yearly prize for breaking Capstan's guarantees.
The challenge is a draft and offers no prize until it is announced with its funding.

## How to report

Please use GitHub's private vulnerability reporting for this repository
(Security → Report a vulnerability). Do not open a public issue for an undisclosed vulnerability.

Include a minimal Capstan program or steps that show the problem, and the version
(`capstanc version`) and platform.

## What happens next

- Acknowledgement within 5 working days
- An assessment and an expected timeline within 14 days
- A fix, a regression test that would have caught it, a security advisory, and credit
  for the reporter unless they prefer otherwise

## Verifying a release

Every release carries SBOMs (CycloneDX and SPDX), SLSA build provenance, a keyless Sigstore
signature for every file, and reports showing the compiler reproduced itself byte for byte on
every platform. `scripts/verify-release.sh vX.Y.Z` checks all of them; see
[docs/TESTING.md](docs/TESTING.md#verifying-a-release). A release that fails verification should
be reported as above.

## Supported versions

Until v1.0, security fixes are made in the latest release only.
