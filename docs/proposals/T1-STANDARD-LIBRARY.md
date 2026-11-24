# Proposal: how the standard library is written in Capstan (T1)

*Status: proposal for the owner's decision. Nothing here is implemented.*

T3 has started: SHA-256, HMAC and PBKDF2 now exist in Capstan (`lib/crypto.cap`) and agree with
the C runtime. They cannot replace the C yet, because Capstan has no way for a program, or for
a builtin such as `hash()`, to use library code. This note proposes that mechanism and lists the
decisions it needs.

## What it must achieve

- Builtins such as `hash()`, `hash_password()`, `escape_html()` and `int_to_str()` become
  ordinary Capstan functions, so the C runtime shrinks to memory, I/O and the system-call layer
  (section 6: "no unsafe component").
- Library code obeys every rule user code obeys. Where a function must do something the rules
  forbid in general (a digest of untrusted input is safe to print), it says so with an audited
  `trust()`, listed by every build like any other.
- Builds stay reproducible: the compiler must still reproduce itself byte for byte, and the
  library a program was built with must be pinned and recorded in the SBOM.
- No new way for code to be injected: a program cannot be made to load a different library by
  its environment.

## Proposed design

1. **Location.** The library ships with the compiler as `lib/std/*.cap` (`std/crypto.cap`,
   `std/text.cap`, ...). The compiler finds it relative to its own binary
   (`bin/../lib/std`). A `--stdlib DIR` flag overrides that, for testing; an environment
   variable does not, so the environment cannot swap in other code.
2. **Explicit imports.** `import std "crypto";` brings in `std/crypto.cap`. The existing path
   rules for `import` (relative, no `..`) are unchanged; `std` is the only other root.
3. **Builtins become library functions.** The compiler keeps the builtin names (`hash`,
   `hash_password`, ...) but resolves each to a library function, implicitly importing the
   module that defines it. Programs do not change. During the transition, the suite compares
   each Capstan implementation with the C one it replaces (as `tests/crypto/` does now); the C
   is deleted only after one release with both in agreement.
4. **Only what is used.** Unused library functions generate no code, so a program carries only
   what it calls. This also keeps compile times flat as the library grows.
5. **Visibility first.** Library internals (`sha256_block`, the PBKDF2 scratch states) must not
   be callable or shadowed by programs. This needs v0.5's `public`/`private` for module
   members, so the proposal is to implement visibility first, then T1.
6. **Audited declassification.** A function like `hash(Tainted) → string` necessarily turns
   untrusted bytes into trusted text (a hex digest). With the laundering rules of #27, the
   library has to say so: one `trust()` per such function, with its justification ("a
   SHA-256 digest is hexadecimal and cannot inject"). The build's AUDIT list then shows exactly
   which library functions declassify, and tests check that each one's output alphabet is what
   its justification claims.
7. **Stage 0.** The Python stage 0 reads the same library files (it already translates any
   Capstan), so the bootstrap and the differential fuzzer keep working unchanged.
8. **Supply chain.** The release archive and SBOM already include `lib/`; the library's hash
   becomes part of the reproducibility report.

## Decisions for the owner

1. `import std "crypto";` (a distinct root, proposed) or `import "std/crypto.cap";` (a reserved
   path prefix)?
2. Keep builtin names working through implicit imports (proposed), or require an explicit
   `import std` for library functions and keep only a small core of true builtins?
3. Visibility before T1 (proposed), or T1 first with a naming convention (`_internal`) until
   v0.5?
4. Is one audited `trust()` per declassifying library function acceptable under "no unsafe
   component", given it is visible in every build? The alternative is a separate,
   compiler-checked `declassify` construct limited to the standard library.

## Order of work if accepted

1. `public`/`private` for module members (v0.5).
2. `std` imports, the library path and its tests; move `lib/crypto.cap` to `lib/std/crypto.cap`.
3. Route `hash()`/`hash_verify()` to the library; run both implementations side by side for a
   release; then `hash_password()`/`verify_password()`/`needs_rehash()`.
4. T4: `int_to_str` and number parsing in Capstan (the C version no longer uses `snprintf`, #33).
5. Delete the C implementations replaced, and record the reduction in the trusted base.
