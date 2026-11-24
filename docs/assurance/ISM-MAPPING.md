# Secure development evidence: ISM and SSDF

This maps Capstan's toolchain, process and tests to:

- the Australian Government **Information Security Manual (ISM), September 2026 edition**, chapter
  "Guidelines for software development" ([ASD](https://www.cyber.gov.au/ism/guidelines-for-software-development));
- **NIST SP 800-218, Secure Software Development Framework (SSDF) Version 1.1**, February 2022
  ([NIST](https://csrc.nist.gov/pubs/sp/800/218/final)). SSDF Version 1.2 (SP 800-218 Rev. 1) was
  released as an initial public draft on 17 December 2025 and is not yet final; this mapping uses 1.1.

It describes the integrated repository state reviewed on 2026-11-24. Control wording below is
summarised; the ISM and the SSDF hold the exact text. The C-free/CCAM architecture is not yet the
integrated execution path, and selected Lean model proofs do not establish implementation or
compiler correctness. Workflow configuration is distinguished from a successful published release.

**Statuses.** **Met**: the repository demonstrates it, and the evidence is named. **Partial**: part
of the control is demonstrated; the rest is stated. **Not yet**: not demonstrated in the repository,
with the roadmap item where there is one. Settings held outside the repository (for example GitHub
branch protection or secret scanning) may exist, but are not counted, because the repository does not
show them. **N/A**: the control concerns a kind of system Capstan is not (for example a web
application or an AI service).

Capstan is both a **toolchain** (compiler, runtime, formatter, build and release process) and a
**language** that other developers use. The tables assess the toolchain. Where a control concerns
applications, the "Capstan programs" note says what the language enforces for software written in it.

## ISM, Guidelines for software development (September 2026)

### Development environments and authoritative source

| Control | Summary | Status | Evidence or plan |
|---|---|---|---|
| ISM-0400 | Development, testing, staging and production environments are separated | Partial | Tests run on fresh GitHub-hosted runners (`.github/workflows/ci.yml`); releases are built in a separate workflow (`release.yml`). Capstan has no production environment of its own |
| ISM-1419 | Software is developed and modified only in development environments | N/A | No production environment |
| ISM-1420 | Production data is not used in other environments unless equally secured | N/A | No production data. Tests use synthetic inputs and published vectors |
| ISM-2023, ISM-2024 | An authoritative source is established, maintained and used for all development | Met | The Git repository; releases are archived from the tagged commit (`release.yml`, `git archive`) |
| ISM-1422, ISM-1816 | Unauthorised access to, and modification of, the authoritative source is prevented | Not yet | Not demonstrated in the repository. Signed releases are planned ([DESIGN-MAP.md](../DESIGN-MAP.md), section 8, Supply chain) |
| ISM-2025 | An issue tracker links development tasks to security issues, requests and fixes | Not yet | Fixes are recorded in [CHANGELOG.md](../../CHANGELOG.md), not linked to tracked issues. No roadmap item |

### Policy, requirements, roles and skills

| Control | Summary | Status | Evidence or plan |
|---|---|---|---|
| ISM-2120 | A secure software development policy is developed, implemented and maintained | Partial | Design principles and standing security commitments ([DESIGN-MAP.md](../DESIGN-MAP.md), sections 2 and 8), release gate ([TESTING.md](../TESTING.md)). Not yet a single policy document |
| ISM-2033 | Software security requirements are documented and maintained | Met | [CWE-COVERAGE.md](../CWE-COVERAGE.md), [CWE-ATLAS.md](../CWE-ATLAS.md), conformance areas in [SPEC.md](../SPEC.md) enforced by `tests/spec_coverage.py` |
| ISM-2034 | Security design decisions are documented and reviewed | Partial | Documented in [DESIGN-MAP.md](../DESIGN-MAP.md). Independent review not yet: external audit before v1.0 (section 8) |
| ISM-2035, ISM-2036 | Security roles, responsibilities and knowledge are identified and documented | Not yet | No roadmap item |
| ISM-2121, ISM-2037, ISM-2038 | Developers have, or are trained to, the necessary security skills; a skills register is kept | Not yet | No roadmap item |

### Design and secure programming

| Control | Summary | Status | Evidence or plan |
|---|---|---|---|
| ISM-0401 | Secure by Design principles and practices are followed throughout the lifecycle | Partial | Vulnerability classes are removed from the language rather than tested for (DESIGN-MAP principle 1); see [MEMORY-SAFETY.md](MEMORY-SAFETY.md). Gaps: items marked Not yet in this document |
| ISM-1238, ISM-2039 | Threat modelling supports the lifecycle and the threat model is reviewed throughout it | Met | [THREAT-MODEL.md](THREAT-MODEL.md), maintained with each release; the CWE atlas re-checks every verdict on each test run (`tests/cwe/atlas.py`) |
| ISM-2040 | Secure programming practices for the language are used | Met | The compiler and formatter are written in Capstan and must pass `--strict --release` (`tests/run.sh`, bootstrap). Capstan programs: the compiler enforces the practices |
| ISM-2041 | Memory-safe languages are used, or less preferably memory-safe practices | Partial | Compiler, formatter and every Capstan program: memory-safe language. Runtime remains C and is tested under ASan/UBSan; see [MEMORY-SAFETY.md](MEMORY-SAFETY.md) and the qualified [runtime memory/lifetime model](RUNTIME-MEMORY-MODEL.md). C-free runtime migration is not integrated |
| ISM-2042 | Secure by Default; security features are built in at no extra cost | Met | Every check is on by default and cannot be switched off; `--strict` and `--release` only add checks; `--keep-checks` only adds run-time checks. Apache 2.0 licence |
| ISM-1780 | SecDevOps practices are used | Met | The full suite runs on every push and pull request, nightly with long fuzzing, and before every release, on three platforms (`.github/workflows/`, [TESTING.md](../TESTING.md)) |
| ISM-2043 | Software is structured for readability and maintainability | Met | One file per compiler stage (`compiler/`); every source file is formatted by `capstan fmt`, enforced by the suite (fmt section) |
| ISM-2044 | No default credentials | Met | The toolchain has no credentials. Capstan programs: credential literals are rejected (`tests/reject/hardcoded_password.cap`, `credential_literal.cap`); secrets come from `secret_env()` |
| ISM-2045 | Backwards compatibility does not weaken security | Partial | Hashes carry their algorithm tag and `needs_rehash()` flags old ones, so defaults can be raised without breaking stored values ([CWE-COVERAGE.md](../CWE-COVERAGE.md), CWE-327). No stability policy yet (v1.0) |
| ISM-2046 to ISM-2050 | User impersonation, authentication-factor reset, privilege changes, re-authentication, signature validation | N/A | The toolchain has no users or accounts. Capstan programs: authorisation is through policies and grants (CWE-862, CWE-613, CWE-639); an authentication framework is planned for v0.9 |
| ISM-2051, ISM-2052 | Software logs security events, and logs protect sensitive data | N/A | The compiler is not a service. Capstan programs: `Secret` values cannot be logged (`tests/reject/secret_logged.cap`) and untrusted text is escaped before logging (`log_injection.cap`) |
| ISM-1798 | A hardening or loosening guide is provided | Not yet | `--strict`, `--release` and `--keep-checks` are described in [README.md](../../README.md) and [CWE-COVERAGE.md](../CWE-COVERAGE.md), but there is no hardening guide. No roadmap item |
| ISM-2053 | End-of-life procedures are produced | N/A | No accounts or data held |

### Software artefacts, build and release

| Control | Summary | Status | Evidence or plan |
|---|---|---|---|
| ISM-1796 | Executables are digitally signed | N/A at present | The repository's release workflow publishes source artefacts; it does not establish distribution of executable binaries. If executable artefacts are added, their signing must be verified as a separate release gate |
| ISM-1797 | Installers, patches and updates are signed or provided with cryptographic checksums | Partial | `release.yml` defines SHA-256 checksums and keyless Sigstore signing/verification for release files. This is workflow-source evidence; a successful published release and end-user verification record must still be checked for each release |
| ISM-2026 | Artefacts are scanned for malicious content before import into the authoritative source | Not yet | No scanning is shown. Capstan imports no third-party code into the repository |
| ISM-2027 | Artefacts are verified by signature or secure hash before import | Not yet | GitHub Actions and the C compilers are taken from the platform without verification in the repository |
| ISM-2028, ISM-2102 | Artefacts are tested for known weaknesses (SAST, DAST or SCA) before import and periodically | Partial | All in-repository code is checked on every change and nightly: the compiler checks its own source (`--strict --release`), the runtime runs under sanitisers, and fuzzing runs nightly. No software composition analysis of the toolchain (GCC, Clang, Python, libc) |
| ISM-2029 | Third-party components come only from trustworthy sources | Partial | There are no third-party libraries. External tools are the platform's C compiler, Python 3 and libc, and GitHub's own `actions/*` workflows |
| ISM-2154 | Dependencies are pinned to approved versions | Partial | GitHub Actions are pinned to full commit SHAs in the current workflows. Toolchain versions (including C compiler/Python) and external build inputs still require a separate approved-version and update policy |
| ISM-2030 | Commit scanning blocks credentials, keys and secrets | Not yet | No commit scanning is configured in the repository. Capstan source: the compiler rejects credential literals in known formats (`tests/unit/lint_table.py`) but this does not scan other files |
| ISM-2031 | Compilers and build tools with security features are used, with those features enabled | Partial | The Capstan compiler's checks are always on. The C compilation of generated code (`bin/capstan`: `-O2 -std=gnu11 -w`) does not enable stack protectors, control-flow integrity, PIE or `_FORTIFY_SOURCE`. Planned: DESIGN-MAP section 6, Defence in depth |
| ISM-2155 | Reproducible build practices, so releases can be verified independently | Partial | The compiler reproduces its own C byte for byte, with both GCC and Clang and from stage 0 (`Makefile`, `tests/run.sh`, bootstrap). Byte-identical native binaries and release archives are not yet demonstrated |
| ISM-2032 | All automated tests pass without warnings or errors before artefacts are built | Met | `release.yml`: the publish job depends on `tests/run.sh --full` passing on every platform; the compiler's generated C must build with `-Werror` (bootstrap section) |
| ISM-2054, ISM-2055 | SBOMs and build provenance of imported components are used | Not yet | No third-party components are imported; the toolchain's own SBOMs are not checked |
| ISM-1730 | An SBOM is produced and made available | Partial | `release.yml` defines CycloneDX 1.6 and SPDX 2.3 SBOM generation and validation for release artefacts. This establishes workflow configuration, not that a particular release has successfully published and retained those SBOMs |
| ISM-2082, ISM-2083 | Cryptographic bills of materials are used and produced | Not yet | The algorithms are SHA-256, HMAC-SHA256 and PBKDF2-SHA256 (`runtime/capstan_rt.h`), but no CBOM is published. Alignment with ASD-approved algorithms is planned (DESIGN-MAP section 9) |
| ISM-2056 | Build provenance is produced and made available | Partial | `release.yml` defines GitHub artifact attestations/SLSA provenance and verification. This is not an independent rebuild and does not establish SLSA Build Level 3; verify the published attestation for each release |

### APIs, input handling and databases

These controls concern applications. The toolchain has no network API or database.

| Control | Summary | Status | Capstan programs |
|---|---|---|---|
| ISM-1817, ISM-1818, ISM-2013, ISM-2014, ISM-1910, ISM-2015 | API clients are authenticated and authorised; API calls are logged | N/A | No networking yet (v0.6) |
| ISM-1240, ISM-2016 | All input from networks is validated and sanitised | N/A | All input is `Tainted` and reaches sinks only through a validator, an escaper or an audited `trust()` (`tests/reject/tainted_as_trusted.cap`). The compiler applies this to its own source files |
| ISM-2057 | Input validation rules are documented and tested with positive and negative tests | Met | Each validator and escaper is tested against its specification (`tests/unit/test_runtime.c`, [TESTING.md](../TESTING.md), unit) |
| ISM-2058 | Inputs are validated before deserialisation | N/A | No object deserialisation exists (CWE-502) |
| ISM-2059 | File uploads are restricted and scanned | N/A | Typed upload handling planned with the web framework (v0.9) |
| ISM-1275, ISM-1276 | Queries are filtered, and parameterised queries are used | N/A | Query text must be a literal with bound parameters (`tests/reject/sql_injection.cap`, `sql_injection_variable.cap`). `sql_query()` is a demonstration sink today |
| ISM-1278, ISM-1536 | Database errors reveal little; queries and errors are logged centrally | N/A | No database driver yet (v0.6) |

### Review and testing

| Control | Summary | Status | Evidence or plan |
|---|---|---|---|
| ISM-2061, ISM-2060 | Peer review of critical and security-related components; reviews verify secure practices | Not yet | Changes arrive by pull request, but required review is not shown. External audit before v1.0 (DESIGN-MAP section 8) |
| ISM-2062 | Unit and integration tests cover positive and negative cases | Met | Negative: 68 rejected programs (`tests/reject/`), safe-stop tests (`tests/runtime/`), the CWE atlas. Positive: conformance programs with exact expected output (`tests/accept/`), examples |
| ISM-0402 | Comprehensive SAST, DAST and SCA before release and periodically | Partial | Static: the compiler checks its own source with `--strict --release`. Dynamic: ASan and UBSan, differential and mutation fuzzing, nightly long campaigns, coverage floors and compiler mutation testing ([TESTING.md](../TESTING.md)). No SCA of the external toolchain |
| ISM-2122 | Suitable AI models augment security testing | Not yet | Capstan Review, advisory (DESIGN-MAP section 5, Phase C) |

### Vulnerability disclosure and response

| Control | Summary | Status | Evidence or plan |
|---|---|---|---|
| ISM-1616, ISM-1755, ISM-1756 | Vulnerability disclosure program, policy and procedures | Met | [SECURITY.md](../../SECURITY.md): scope, private reporting, acknowledgement in 5 working days, assessment in 14 days |
| ISM-1717 | security.txt for internet-facing websites | N/A | Capstan has no website |
| ISM-1908 | Vulnerabilities are disclosed responsibly with CWE and CPE information | Partial | SECURITY.md commits to an advisory for every confirmed issue, and every safety diagnostic carries a CWE number. No advisory has been issued yet, and CPE identifiers are not mentioned |
| ISM-1754 | Vulnerabilities are resolved in a timely manner | Partial | Timelines in SECURITY.md; not yet exercised |
| ISM-1909 | Root cause analysis; vulnerability classes are remediated | Met | Classes, not instances, are removed: every atlas gap is a test with an owner milestone (DESIGN-MAP section 8). Bugs found by coverage and mutation testing became tests ([TESTING.md](../TESTING.md); [CHANGELOG.md](../../CHANGELOG.md), "Fixed") |
| ISM-1911 | Security-relevant usage, errors and crashes are logged centrally | N/A | The compiler is a local tool. Capstan programs name the CWE on every safe stop (exit code 101) |

### Other sections of the chapter

The **artificial intelligence application development** (ISM-2084 to ISM-2094, ISM-2103, ISM-2123,
ISM-2156 to ISM-2159, ISM-1924), **mobile application development** (ISM-1922) and **web application
development** (ISM-1239, ISM-0971, ISM-1849, ISM-1850, ISM-2063 to ISM-2067, ISM-1424, ISM-1552,
ISM-1851, ISM-1241) controls are N/A to the toolchain. For Capstan programs, ISM-1241 (output
encoding) is supported by the `Html` type and `escape_html()` (`tests/reject/xss.cap`,
`tainted_into_html.cap`); a web framework is planned for v0.9. When Capstan Review is built, the AI
controls will apply to it.

## NIST SP 800-218, SSDF Version 1.1

### Prepare the Organization (PO)

| Task | Summary | Status | Evidence or plan |
|---|---|---|---|
| PO.1.1 | Security requirements for development infrastructure and processes | Partial | DESIGN-MAP sections 8 and 10; release gate in [TESTING.md](../TESTING.md). Not one document |
| PO.1.2 | Security requirements for the software | Met | [CWE-COVERAGE.md](../CWE-COVERAGE.md), [CWE-ATLAS.md](../CWE-ATLAS.md), [SPEC.md](../SPEC.md) conformance areas |
| PO.1.3 | Requirements communicated to third-party suppliers | N/A | No commercial suppliers |
| PO.2.1, PO.2.2 | Roles and responsibilities; role-based training | Not yet | No roadmap item |
| PO.2.3 | Management commitment to secure development | Partial | Standing commitments in DESIGN-MAP section 8 |
| PO.3.1 | Specify the toolchain | Met | [README.md](../../README.md) (requirements), `Makefile`, CI matrix in `.github/workflows/ci.yml` |
| PO.3.2 | Operate the toolchain securely | Partial | Hosted runners per job and Actions pinned by commit SHA (`.github/workflows/`). Toolchain versions, runner trust and external rebuild remain residual dependencies |
| PO.3.3 | Tools produce evidence of secure practices | Met | Test reports from every platform attached to each release (`release.yml`); coverage report ([COVERAGE.md](../COVERAGE.md)) |
| PO.4.1 | Define and track criteria for security checks | Met | No release unless `tests/run.sh --full` passes on every platform; coverage floors (`tests/coverage_floors.txt`); quality bar (DESIGN-MAP section 10) |
| PO.4.2 | Gather and protect the supporting information | Partial | Reports and fuzz failures kept as CI artefacts and release assets; not signed |
| PO.5.1, PO.5.2 | Separate and protect development environments; harden endpoints | Not yet | Not demonstrated beyond ephemeral CI runners |

### Protect the Software (PS)

| Task | Summary | Status | Evidence or plan |
|---|---|---|---|
| PS.1.1 | Store code with least-privilege access and tamper protection | Not yet | Not demonstrated in the repository |
| PS.2.1 | Make release integrity information available | Partial | `release.yml` defines SHA-256 checksums, keyless Sigstore signatures and verification for release files; confirm the successful release run and published assets for each tag |
| PS.3.1 | Archive and protect each release | Partial | Source archive, test reports and checksums on each GitHub release; tags in Git |
| PS.3.2 | Collect and share provenance data, such as an SBOM | Partial | `release.yml` defines CycloneDX and SPDX SBOMs plus GitHub artifact attestations. It does not establish a complete SBOM of every external toolchain dependency or an independent reproducible build |

### Produce Well-Secured Software (PW)

| Task | Summary | Status | Evidence or plan |
|---|---|---|---|
| PW.1.1 | Risk modelling such as threat modelling | Met | [THREAT-MODEL.md](THREAT-MODEL.md); CWE atlas; K0 study ([K0-KERNEL-CVES.md](../K0-KERNEL-CVES.md)) |
| PW.1.2 | Track security requirements, risks and design decisions | Met | DESIGN-MAP (roadmap, section 11 known risks); atlas gaps with owner milestones |
| PW.1.3 | Use standardised security features | Partial | Crypto follows FIPS 180-2, RFC 4231 and RFC 7914 and is tested against their vectors; it is self-implemented, not a validated module (FIPS 140-3 option planned, DESIGN-MAP section 9) |
| PW.2.1 | Qualified review of the design | Not yet | External audit before v1.0 (DESIGN-MAP section 8) |
| PW.4.1, PW.4.4 | Acquire, and verify over time, well-secured third-party components | Partial | No third-party libraries. Monitoring advisories for the C compilers and libc is planned (DESIGN-MAP section 8, Dependency watch) |
| PW.4.2 | Create and maintain well-secured in-house components | Met | Runtime unit tests against published vectors and specifications, sanitisers, collector stress ([TESTING.md](../TESTING.md)) |
| PW.5.1 | Secure coding practices for the language | Met | Compiler and formatter in Capstan, passing `--strict --release`; formatting enforced |
| PW.6.1 | Compiler and build tools with security-improving features | Partial | Capstan's checks always on; C exploit mitigations not explicitly enabled (DESIGN-MAP section 6) |
| PW.6.2 | Approved tool configurations | Partial | Flags fixed in `Makefile`, `bin/capstan` and `tests/run.sh`; generated C must build with `-Wall -Wextra -Werror`; hardening flags not yet included |
| PW.7.1, PW.7.2 | Code review or analysis, with findings recorded and triaged | Partial | Automated analysis on every change (self-check, coverage, mutation testing, survivors recorded in [TESTING.md](../TESTING.md)). Human review not shown |
| PW.8.1, PW.8.2 | Test executable code, with results recorded | Met | `tests/run.sh` sections ([TESTING.md](../TESTING.md)); fuzz failures saved with seeds for reproduction |
| PW.9.1, PW.9.2 | Secure defaults, documented | Met | All checks on by default; heap limit on by default (`runtime/capstan_gc.h`); options documented in [README.md](../../README.md) and [CWE-COVERAGE.md](../CWE-COVERAGE.md) |

### Respond to Vulnerabilities (RV)

| Task | Summary | Status | Evidence or plan |
|---|---|---|---|
| RV.1.1 | Gather and investigate vulnerability reports | Met | [SECURITY.md](../../SECURITY.md) |
| RV.1.2 | Review and test code to find undetected vulnerabilities | Met | Nightly long fuzzing; CWE atlas on every run; coverage and mutation testing |
| RV.1.3 | Disclosure and remediation policy | Met | [SECURITY.md](../../SECURITY.md) |
| RV.2.1, RV.2.2 | Analyse, prioritise and remediate each vulnerability | Partial | Process in SECURITY.md; not yet exercised by a reported vulnerability |
| RV.3.1, RV.3.2 | Find root causes and patterns | Met | Weaknesses handled as CWE classes; the K0 study classifies a year of kernel CVEs by root cause |
| RV.3.3 | Look for and fix similar vulnerabilities | Met | Every atlas verdict re-checked on every run; laundering variants tested together (`tests/reject/launder_*.cap`) |
| RV.3.4 | Improve the SDLC to prevent recurrence | Met | A regression test for every fix (SECURITY.md, DESIGN-MAP section 8); fuzz failures become permanent tests ([TESTING.md](../TESTING.md)) |

## Summary of what is not yet done

The largest gaps are evidence of successful published release assets/attestations for each tag,
complete external-toolchain dependency and cryptographic BOM coverage, independent rebuilds,
C exploit mitigations for generated programs, enforced peer review, independent audit, and
documented roles and skills. The workflows now define checksums, keyless signatures, CycloneDX/SPDX
SBOMs and GitHub provenance; those controls must not be described as absent, but workflow source
alone is not proof that a particular release completed or that an external reproducible build exists.
