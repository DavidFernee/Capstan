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

## Supported versions

Until v1.0, security fixes are made in the latest release only.
