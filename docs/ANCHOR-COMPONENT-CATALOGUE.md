# Anchor security-reviewed component catalogue

**Status:** proposed contract for the Anchor v0.6+ roadmap.  
**Normative language:** MUST, MUST NOT, SHOULD and MAY describe requirements of a future implementation, not features available in the current repository.

## 1. Goals and non-goals

The catalogue makes reviewed implementations easier to adopt than bespoke security code. It is a curated distribution channel for reusable Capstan components, not an unrestricted plugin marketplace.

It MUST identify every release and its complete dependency closure immutably; make security claims explicit, scoped, attributable and independently verifiable; distinguish package integrity, publisher identity, test results, review, formal properties and deployment security; expose capabilities, sensitive-data flows, configuration assumptions and operational responsibilities; support reproducible offline verification; and reuse Capstan's existing SBOM and release-provenance infrastructure.

It MUST NOT label a component simply “secure” or “verified” without a named property, scope, subject, verifier and evidence; treat a signature, tests, audit or absence of advisories as proof of benign code; install, execute or upgrade packages merely because a workspace opens; silently change a locked dependency graph; or allow transitive dependencies to acquire capabilities implicitly.

## 1A. Existing repository baseline

The repository already has meaningful release-level supply-chain controls:
- scripts/sbom.py emits deterministic CycloneDX 1.6 and SPDX 2.3 SBOMs for a Capstan
  source archive, including per-file hashes and declared build/runtime requirements;
- scripts/sbom-validate.py validates those SBOMs against the official schemas;
- .github/workflows/release.yml builds on Linux (GCC and Clang) and macOS (Clang),
  produces reproducibility reports, generates SBOMs, and signs release assets;
- GitHub artifact attestations provide build provenance, and release assets carry
  keyless Sigstore bundles;
- scripts/verify-release.sh checks checksums, signatures, provenance, SBOM consistency
  and reproducibility, with an optional local rebuild.

These are concrete release controls and should be reused. Their scope must not be
overstated: the current SBOM describes the Capstan source archive, build tools and
runtime dependency; it does not yet describe a third-party Capstan package graph because
a package manager/catalogue is not implemented. The release verifier checks a tagged
Capstan release, not arbitrary component descriptors, transitive package locks,
component-level assurance statements, catalogue trust snapshots or advisory freshness.

The verifier's --skip-signatures and --skip-attestations options are diagnostic escape
hatches: using them omits identity/provenance checks. A successful run with either option
must not be presented as authenticated release verification. Likewise, local verification
of cached files does not establish current revocation status. The catalogue verifier
will need explicit trust-snapshot and offline-freshness semantics described below.

## 2. Core records and identity

The design separates five record types. They may be encoded together, but their semantics and identities MUST remain distinct.

### 2.1 Component descriptor

A publisher-maintained, declarative descriptor explains the component. It MUST be bounded data, not executable configuration.

Required fields:
- globally unique package coordinate and descriptor schema version;
- name, purpose, maintainer and source repository;
- supported Capstan/compiler compatibility range and public API identity;
- release version, immutable source revision and cryptographic artifact/source digest;
- direct dependency constraints and resolved dependency identities for the release;
- supported platforms/targets, if relevant;
- requested capabilities and the reason each is required;
- data classification and trust/taint behaviour at public boundaries;
- secret inputs, outputs, copies and documented lifecycle limitations;
- protocols, algorithms and formats implemented;
- configuration schema, safe defaults, insecure/legacy modes and migration behaviour;
- resource limits, expected cost and failure modes;
- threat model, assumptions, known limitations and operational duties;
- links to SBOM, build provenance, release signature, assurance statements and advisories.

A descriptor MUST NOT override Anchor's trust policy or grant itself capabilities. Declared capabilities are requests to be reviewed, not permissions.

### 2.2 Immutable package subject

A release subject is identified by a cryptographic digest over exact artifact bytes (or a precisely specified canonical source archive). A version string, Git tag, branch or repository URL is not an immutable identity.

The release record MUST bind package coordinate/version, artifact digest and algorithm, source repository and immutable revision, complete resolved dependency closure with each digest, build toolchain and parameters for binary artifacts, SBOM identity, provenance identity, and signature identity with its signing-time trust context.

A mutable tag may be a human-friendly alias but MUST resolve to the same immutable digest recorded in the lockfile. Reusing a version for different bytes is a release-integrity failure.

### 2.3 Project lock record

The lock record pins exact package coordinates, versions, digests and the complete transitive dependency closure. It also records descriptor and assurance-bundle digests, target/toolchain constraints, requested capabilities and their transitive origins, selected configuration profile identity (not secret values), and the catalogue/trust snapshot used for verification.

A lock record MUST NOT contain passwords, private keys, access tokens or other secret values. It may identify a separately managed secret reference.

Resolution MUST fail closed on digest mismatch, missing locked artifacts, ambiguous identity, dependency substitution or undeclared capability increase. Opening a project may inspect existing lock data and cached metadata; it MUST NOT fetch packages, execute package code or rewrite the lockfile automatically.

### 2.4 Assurance statement

An assurance statement is a structured claim about a precisely identified subject. It MUST identify:
- stable claim identifier and schema version;
- exact subject digest and dependency closure;
- property claimed and its boundary (for example, rejection of malformed encodings under stated limits, not “the parser is secure”);
- assumptions, exclusions, supported targets and configuration conditions;
- method: review, test, fuzzing, static/dynamic analysis, conformance, reproducible-build check or formal verification;
- tool names, exact versions, configuration and relevant test corpus/revision;
- result, author/reviewer identity and date;
- evidence artifact digests and verifier instructions;
- validity/review policy and any superseding, withdrawn or disputed statement.

A claim MUST NOT be inherited by a new source digest or dependency closure merely because the package version or public API is unchanged. Evidence can be reused only when its stated subject and assumptions still match.

### 2.5 Evidence artifact and trust snapshot

Evidence artifacts are immutable, content-addressed objects: reports, test logs, fuzz summaries, SBOMs, build provenance, audit records, proof objects, reproducibility results and advisory snapshots.

A trust snapshot records catalogue roots, accepted signer identities, key validity/revocation information, advisory database versions and verification policy. Verification results MUST refer to the snapshot, not merely say “signature valid”.

## 3. Assurance dimensions and UI status

Assurance is a vector of independent dimensions, not a single score or ordered badge.

| Dimension | Establishes | Does not establish |
|---|---|---|
| Identity/integrity | Artifact digest matches locked subject | Code is safe |
| Publisher signature | An accepted key signed the subject/statement | Publisher or code is trustworthy |
| Build provenance | Attested source and build process match policy | Builder or source was uncompromised |
| Tests/conformance | Named cases passed on named targets | Absence of untested defects |
| Fuzzing | A stated campaign exercised inputs and found reported failures | Exhaustive correctness |
| Independent review | A named reviewer examined a stated scope | Every path or deployment was reviewed |
| Formal property | A stated property was proved under stated assumptions | General security of the component |
| Advisory status | Known advisories in a particular snapshot | Absence of undisclosed or unpublished issues |
| Capability review | Declared authority/data flows were reviewed | Host enforcement where no mechanism exists |
| Configuration conformance | Settings satisfy a reviewed profile | Safe deployment beyond that profile |

The UI MUST display subject digest, evidence date, verifier result and scope with each claim. It SHOULD link each summary to its source report and verification procedure.

Use explicit per-dimension states such as not-provided, not-checked, verified, failed, stale, revoked, disputed and not-applicable. Do not collapse them into a single colour or score. Not-checked is not verified; unavailable evidence is not a pass; verifier failure is not itself a vulnerability finding; withdrawn claims remain visible in history; and “no known advisory” is qualified by snapshot and timestamp.

A package may be signature-verified and still be unreviewed, vulnerable or configuration-incompatible. Preserve this distinction in catalogue lists, editor hints, build reports and release gates.

## 4. Signatures, provenance and interoperability

Capstan's existing release engineering emits CycloneDX and SPDX SBOMs, GitHub artifact attestations, keyless Sigstore signatures, reproducibility reports and a release verification script. The catalogue SHOULD reuse those artifacts and verification paths where their subject and trust semantics fit. It MUST NOT create a competing SBOM or bespoke signature format.

Use established interoperable signature/attestation envelopes and verification implementations. Bind signatures to immutable digests and typed predicates. Verify signer identity, issuer, repository/workflow constraints and trust roots, not merely cryptographic validity. Pin verifier/tool versions and record the trust policy. Reject ambiguous or unsupported algorithms and malformed metadata. Keep signing keys and trust-root administration outside the component package.

The precise manifest encoding and attestation predicate schema require a separate interoperability decision with the supply-chain/release owner. This proposal specifies semantics before committing to serialization or inventing a schema. Consume CycloneDX, SPDX, SLSA/in-toto and Sigstore artifacts directly where possible.

## 5. Verification procedure

Verification MUST be deterministic for a fixed package, trust snapshot, verifier version and policy.

1. **Parse safely:** enforce byte, nesting, collection, string and decompression limits; reject duplicate/ambiguous fields, invalid encodings and unsupported schema versions. Metadata parsing never executes code.
2. **Resolve identity:** compare package coordinate, version, artifact digest, source revision and every dependency digest with the lock record.
3. **Verify signatures:** validate signatures against the selected trust snapshot, including signer identity and policy constraints.
4. **Verify provenance:** validate attested source, builder, workflow, parameters and subject digest against release policy.
5. **Verify SBOM closure:** compare SBOM with the locked dependency closure; report missing, extra, unknown or mismatched components.
6. **Verify assurance statements:** validate signatures, subject binding, evidence digests, verifier identity and scope; infer no unstated claims.
7. **Check advisories:** evaluate the locked graph against the exact local advisory snapshot, retaining affected-version ranges and reachability evidence where available.
8. **Evaluate capabilities/configuration:** compare requested and transitive capabilities and selected configuration with project policy.
9. **Emit report:** produce machine-readable and human-readable results tied to package graph, toolchain, trust snapshot and policy.

A verification report is itself an evidence artifact. It MUST be reproducible from the same inputs or record nondeterministic/environmental inputs.

## 6. Offline and revocation semantics

Offline mode is first-class for air-gapped and restricted environments. It verifies only locally available material: package bytes, descriptors, signatures, attestations, SBOMs, assurance evidence, trust roots and advisory snapshots.

The result MUST state which artifacts were available and verified, which trust/advisory snapshots were used, each snapshot's latest known update time, whether freshness requirements were met, and which checks could not be performed offline.

A cached signature can be verified offline, but revocation cannot be known beyond the latest imported trust/revocation snapshot. Anchor MUST NOT display “currently trusted” when it can establish only “valid under snapshot X, last refreshed at time Y”. Policy may reject snapshots older than a configured maximum age. If freshness cannot be established, status is stale or unknown, never current by implication.

Importing a newer trust or advisory snapshot is explicit and requires its own signature/provenance verification. Snapshot rollback MUST be detected with monotonic sequence/epoch metadata or an equivalent anti-rollback mechanism. Recovery for legitimate key rotation and disaster recovery must be specified.

## 7. Capability and data-flow policy

Capabilities are security authority, not descriptive tags. A component MUST declare every directly requested capability and its reason. The resolver computes the transitive union and shows which dependency introduces each capability.

The UI/verifier distinguishes declared capability (publisher assertion), reviewed capability (assurance claim), granted capability (project/host policy decision), and exercised capability (observed runtime event, if trustworthy instrumentation exists). These are different facts. A declaration does not grant authority, and IDE review does not enforce authority. If the runtime/host cannot enforce a requested capability, Anchor must say so and must not imply sandboxing.

Sensitive-data metadata describes entry/exit points and transformations: untrusted input, validated data, secrets, credentials, keys, personal data and externally observable outputs. Publisher declarations of taint/secret guarantees are not authoritative; those require compiler/runtime semantics or independent evidence. Unknown flows remain unknown.

## 8. Automatic remediation and lockfile changes

The design map's supply-chain policy proposes automatic remediation subject to signature, capability, cooling-off, project-test and compatibility gates. The catalogue must implement those gates rather than bypass them.

Automatic remediation is distinct from silent mutation:
- every graph change MUST produce a reviewable diff, reason, advisory link and old/new SBOM and lock identities;
- no capability increase, source-repository change, signer-policy change or trust-root change may be applied automatically;
- security-sensitive changes MUST pass applicable cooling-off and test gates, except where the documented known-exploited-vulnerability policy explicitly permits a waiver;
- every change MUST be recorded in a durable remediation log and be reversible;
- project/organisation policy and selected review mode determine whether a change is applied automatically or awaits approval;
- opening a workspace MUST NOT itself download, execute or mutate dependencies.

Anchor shows resulting state and provenance; it never makes a lockfile change invisible or describes an unreviewed update as verified.

## 9. Authentication component review profile

Authentication packages should be narrow protocol implementations/adapters with clear boundaries, not opaque all-in-one login components. Review profiles include, as applicable:

- **WebAuthn/passkeys:** unpredictable single-use challenges; origin, RP-ID and ceremony binding; signature/credential validation; lifecycle; user-verification policy; backup/synchronisation semantics; replay and downgrade tests.
- **OIDC relying party:** issuer/audience/nonce/state validation; PKCE and redirect URI policy; token signature/algorithm policy; key rotation; discovery/JWKS trust; mix-up, replay and confused-deputy tests.
- **MFA orchestration:** enrolment and factor binding; step-up policy; recovery and factor replacement; rate limits; replay; downgrade and weaker fallback channels.
- **Password verification:** established hashing scheme; bounded parameters/input sizes; canonical record parsing; constant-time comparison claims supported by evidence; migration/rehash policy; secret lifecycle.
- **Sessions:** unpredictable opaque identifiers; rotation, expiry and revocation; fixation and CSRF controls; cookie policy; concurrent-session and logout semantics.
- **Authorisation:** deny-by-default semantics; explicit subject/resource/action inputs; tenant boundaries; policy-change behaviour; privilege-escalation and confused-deputy tests; auditable decisions without secret leakage.

All profiles include abuse cases, resource-exhaustion limits, error behaviour, logging/redaction rules, deployment assumptions and recovery procedures. The integrating application remains responsible for identity proofing, account recovery, tenant isolation, authorization policy, monitoring, incident response and secure deployment unless reviewed evidence explicitly covers them.

The current Capstan crypto-library review identified unbounded work/input and secret-lifecycle concerns. No authentication component may claim assurance by depending on those APIs until the relevant findings are resolved and the exact dependency subject passes required review and tests.

## 10. Catalogue governance and release lifecycle

The catalogue operator defines admission criteria, reviewer independence, conflict-of-interest disclosure, key management, emergency withdrawal, incident response, vulnerability disclosure and supported-version policy.

A release lifecycle is explicit: submission and source ownership verification; automated static/build/conformance/resource-budget checks; independent security review against the component profile; reproducible release and SBOM/provenance generation; signed publication with immutable subject identity; advisory monitoring and periodic re-review; withdrawal/replacement/end-of-support with affected-version guidance.

A publisher cannot approve its own independent-review claim. A reviewer cannot silently edit the subject reviewed. Emergency withdrawal preserves signed historical records while preventing new installations under current policy. Existing locked projects receive actionable warnings and migration guidance, not silent dependency substitution.

## 11. Initial acceptance gates

Before Anchor presents a component as catalogue-verified, the implementation must have:
- versioned, strictly parsed descriptor schema with size/depth limits and negative tests;
- immutable package/dependency identities with lockfile round-trip tests;
- signature/provenance verification using established formats and pinned verifiers;
- trust-snapshot freshness and anti-rollback tests, including offline/revoked-key cases;
- SBOM-to-lock graph consistency checks;
- assurance-statement subject binding and tamper tests;
- capability-closure and undeclared-capability negative tests;
- advisory snapshot, affected-range and stale-data tests;
- machine-readable report with deterministic input identities;
- UI tests proving unknown, stale, failed and revoked states cannot render as verified;
- independent review of the verifier and adversarial malformed-metadata testing.

Until these gates exist, Anchor may display catalogue metadata as unverified information, but MUST NOT produce a verified status.
