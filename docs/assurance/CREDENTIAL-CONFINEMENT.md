# Credential confinement and CWE-916 — proposed normative contract

Status: candidate; not implemented or proved. Tracks #232. The supported credential profile mediates credential acquisition and verifier storage. Arbitrary public bytes cannot be classified by human intent.

## Typing and effects

Introduce opaque Password, PasswordHash and IntegrityData types. Password is introduced only by approved bounded credential ingress; PasswordHash only by the approved KDF or validated verifier decoder; IntegrityData only from noncredential provenance. Generic input cannot become IntegrityData through a generic trust operation. Credential ingress must be distinct from ordinary input; the profile must prevent alternate unmediated credential storage and cryptographic sinks.

Password has no public representation, string conversion, generic trust, serialization, reflection, raw byte access or equality. Moves, borrows, aggregates, generic instantiation and function calls retain the credential label. Derived values cannot erase the label; secret-dependent control flow must not produce public fast-hash operands. Reject unknown operations by default. PasswordHash may be persisted only using the designated verifier codec and storage API.

Primitive signatures (abstract, not proposed concrete syntax):
- password_hash(Password) -> Result<PasswordHash, CredentialError>
- password_verify(Password, PasswordHash) -> Result<bool, CredentialError>
- integrity_hash(IntegrityData) -> Digest
- integrity_verify(IntegrityData, Digest) -> bool

The verifier result is a narrowly authorized disclosure for authentication, not a general declassification mechanism. The approved password KDF policy must enforce unique random salts, reviewed minimum cost, bounded maximum resource consumption and upgrade semantics; malformed or unsupported parameters fail before allocation. No caller-selected weaker KDF is permitted.

## Proof obligations

Define a typing judgment with provenance labels and an operational semantics with credential-ingress, KDF, verifier-decode, integrity-hash and storage events. Prove preservation of typing and credential provenance for every transition, including aliases, generic substitution, field projection and calls. Prove that the integrity-hash event can occur only with IntegrityData whose provenance excludes credential ingress, except explicitly modeled authorized disclosures that themselves cannot become integrity operands. Prove that every credential persistence event contains only an approved PasswordHash. Establish checker soundness, lowering simulation and runtime primitive correspondence separately. Model resource exhaustion and invalid verifier encodings as explicit failures.

A proof of a reference model alone does not establish production enforcement. Maintain the existing assurance status until exact-revision implementation-linked evidence and independent review are available.

## Adversarial acceptance matrix

Reject direct fast hashing, renamed variables, aliases, nested aggregates, generic wrappers, function returns, method transformations, casts, generic trust, serialization, implicit-flow laundering and alternative storage routes. Reject malformed verifier encodings, weak cost settings, unsupported algorithms and excessive resource requests. Positive controls include valid password hashing and verification, wrong-password rejection, approved rehash upgrade and noncredential artifact integrity hashing. Test each on the production path and native path when supported. Keep #232 open until these obligations are met. #511 is incremental only.
