# SHA-256 scalar temporary wipe boundary

**Status:** source-level and optimized-execution regression coverage. This is not a claim of complete physical erasure.

## Scope

The SHA-256 compression function previously wiped the 64-word message schedule and eight working variables but left four additional message-derived scalar objects without explicit wipe boundaries:

- `s0` and `s1` in each of the 48 message-schedule expansion iterations;
- `t1` and `t2` in each of the 64 compression rounds.

The current change wipes each scalar immediately after its final algorithmic use. The result is still fed into the same schedule/working-state expression before the wipe. No digest, HMAC or PBKDF2 algorithm inputs or outputs are changed.

## Test observation

With `CAP_SHA256_SCALAR_WIPE_TEST_HOOK`, the unit-test translation unit observes each scalar object through a `volatile unsigned char` pointer immediately after `cap_wipe`. The observer checks every byte is zero. A direct one-block compression test asserts exactly 224 observations: two schedule temporaries for each of 48 expansion words (96), plus two round temporaries for each of 64 rounds (128).

The normal SHA-256 known-answer tests, million-byte streaming vector, HMAC-SHA256 vectors and PBKDF2-SHA256 vectors remain in the same runtime unit suite. `tests/run.sh` compiles and executes that unit test at `-O0`, `-O2` and `-O3`. The repository CI matrix supplies GCC on Ubuntu, Clang on Ubuntu and Clang on macOS. These optimized executions inspect the actual post-wipe object bytes through volatile reads; they are not a disassembly proof of all compiler-generated copies.

## C abstract-machine boundary

`cap_wipe` writes zero bytes through a `volatile unsigned char *`. The volatile accesses are observable side effects and the compiler must preserve those accesses in the generated program. The test-only observer then reads the selected objects through volatile accesses and checks the values at that boundary.

This establishes only that the selected C objects are zero at the observation boundary in the tested compiler/build configurations. It does **not** establish erasure of:
- copies held only in general-purpose or vector registers;
- compiler-generated spills or temporaries not represented by the selected objects;
- prior copies, inlined expression values or caller-owned inputs;
- caches, speculative state, swap, hibernation images, crash dumps or physical memory remanence;
- other concurrent copies or copies made by a different implementation.

No source-level wipe can establish those broader properties by itself. Do not describe this change as complete physical erasure, constant-time execution, or cryptographic-module validation.
