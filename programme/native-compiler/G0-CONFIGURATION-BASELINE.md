# G0-06 configuration baseline candidate

Inspected commit 7be0a4a6ee02b9eb76bb06a5505cb6d9b277e6b6. This is a static manifest, not an observed clean build. The final integrated candidate must be repinned after audit PRs merge.

| Input | Git blob |
|---|---|
| Makefile | effba39be3f91c98c6c6c2b99c22b5e78dd10ab5 |
| bootstrap/capstan0.py | f374716051640c4e2776089156fb4eff18a87c4b |
| runtime/capstan_rt.h | 27cc7cfc6827f5745150f4bf2d5c38dd65978a06 |
| runtime/capstan_gc.h | dee014e7a47c82d9a3ad9e163ade35f03b4e0ca1 |
| bin/capstan | cfff60dad16c533e6fdfc1996a7a7d84cf2fcb06 |
| tests/run.sh | d361d71290db59c55f575d2d00545ebc999bd792 |
| .github/workflows/ci.yml | 39e08c63a2bb863ff5aeb0367bb7975253c47e38 |
| verification/lean/lean-toolchain | 7aca1d8a939cc24c413eddd793671cdce7070b74 |
| formal/lean-toolchain | 00f848359b1cdaf7c12cd6b7acc5b4364752e154 |

Compiler source roots: ast, lexer, parser, checker, ranges, codegen, main under compiler/*.cap; see #572 for exact blobs and scoped literal dependencies. Runtime includes capstan_gc.h and system C/POSIX headers. Seed uses Python standard library os, sys, stat, codecs, re, hashlib (observed import lines, not transitive closure).

Declared proof tools: Lean 4.19.0 language; Lean 4.36.0 allocator. CI declares ubuntu-latest GCC and Clang, macos-latest Clang; labels are mutable. Checkout action pinned 3d3c42e5aac5ba805825da76410c181273ba90b1, upload-artifact cf430e030ddbb5b0abf93d22962f4752f3646cd9. Formal workflow filename not resolved in this pass; no inferred pin.

## Reproduction protocol (to execute independently)

Start from a fresh detached checkout of the final approved commit, verify clean status and record tree identity, submodule state and complete file manifest. Use isolated disposable workspace. Record uname, OS release, CPU architecture, runner image version, locale/timezone, Python, make, CC, assembler/linker, libc/SDK and Lean/Lake versions, resolved executable paths and hashes, environment overrides and effective flags. For each CI matrix entry run make clean, make bootstrap and make test; retain logs and exit status. Compare build/stage2.c and build/stage3.c and record SHA-256 of generated Python, generated C and native compiler binaries. Reproduce on independent clean checkout and distinguish same-environment reproducibility from cross-target equivalence. Record exact formal and CodeQL workflow identifiers and outcomes separately.

Makefile defaults: -O2 -std=gnu11 -Wall -Wno-unused-function -Wno-unused-variable -Wno-unused-but-set-variable -Wno-parentheses-equality; hardening -fstack-protector-strong -fPIE, Linux additionally -pie -D_FORTIFY_SOURCE=2. Python stage0 translates to stage1.py, stage1 emits stage2.c, native stage2 emits stage3.c, cmp checks C fixpoint. This is the transitional C-dependent compiler, not native C-free S3.

## Unobserved evidence

Actual tool versions, runner image digests, tree hash, complete transitive host/runtime/seed closure, generated artifact hashes, clean build/test logs and independent reproduction are all OPEN. No execution performed. G0-06 candidate only; G0 HOLD.
