# G0 integrated baseline reproduction (Linux/GCC)

Build operator: Codex. Execution date: 27 November 2026 UTC. This record supplies
execution evidence for G0-06 and G0-07 in the
[consolidated acceptance register](G0-CONSOLIDATED-ACCEPTANCE.md).

## Source and environment

| Item | Recorded value |
|---|---|
| Integrated revision (PR #583) | `02328b31a555f282878574b2f65ee68dc2751a2a` |
| CI checkout (PR #583 synthetic merge) | `d8dbb7c41236b77e35ea3868c4c50a8d78404775` |
| Root tree at both commits | `a6d553ef83f09c87801c2de65e21c733b91ae9a5` |
| First parent at both commits | `c6cfc03ce0aa7217813cae728058f5abfcd65283` |
| Second parent at both commits | `b2d0a29512214823ee5ea03697acddf8cbf66f66` |
| SHA-256 of `git ls-tree -r HEAD` output | `dc3d843f799de7b50a95aabd69868e625bbbdc37d4ac91c213c117442e9932df` |
| Local OS and kernel | Debian 13, Linux 6.18.57, x86-64 |
| Local tools | GCC 14.2.0 (Debian 14.2.0-19), GNU assembler and linker 2.44, Python 3.12.14, GNU Make 4.4.1, Git 2.56.1 |

I fetched both commit objects and compared their root trees and ordered parents
using Git. I ran the following sequence in a new detached worktree at the
integrated revision. The initial porcelain status was empty.

```sh
git worktree add --detach ../g0-reproduction 02328b31a555f282878574b2f65ee68dc2751a2a
cd ../g0-reproduction
set -e
export CC=gcc
git rev-parse HEAD 'HEAD^{tree}'
test -z "$(git status --porcelain)"
git ls-tree -r HEAD > ../g0-tree.txt
sha256sum ../g0-tree.txt
make
cmp build/stage2.c build/stage3.c
sha256sum build/stage1.py build/stage2.c build/stage3.c build/capstanc2 \
  build/capstanc build/capstanfmt build/capstan-lsp
bash tests/run.sh
```

## Bootstrap and artifact comparison

`make` completed successfully and `cmp` confirmed the stage 2 and stage 3 C
outputs were identical. The [original GCC job](https://github.com/DavidFernee/Capstan/actions/runs/45974821039/job/140423820894)
and [GCC rerun](https://github.com/DavidFernee/Capstan/actions/runs/45974821039/job/140440008520)
recorded the same hashes as each other. Both ran on Ubuntu 26.04 with GCC 15.2.0
and Python 3.14.4. The three generated sources matched the local files byte for
byte. The executable hashes differed across the two toolchains.

| File | Local SHA-256 | GitHub GCC SHA-256 |
|---|---|---|
| `build/stage1.py` | `cec8006bef45d81616c7397d20fd799b8ccf2cf5a8fb62cc720ce7bfd92e8ce7` | `cec8006bef45d81616c7397d20fd799b8ccf2cf5a8fb62cc720ce7bfd92e8ce7` |
| `build/stage2.c` | `ad9b87ea02f3060c71d3719aa4d826d366cda9eb57138448bf9dfa3578691c4b` | `ad9b87ea02f3060c71d3719aa4d826d366cda9eb57138448bf9dfa3578691c4b` |
| `build/stage3.c` | `ad9b87ea02f3060c71d3719aa4d826d366cda9eb57138448bf9dfa3578691c4b` | `ad9b87ea02f3060c71d3719aa4d826d366cda9eb57138448bf9dfa3578691c4b` |
| `build/capstanc2` | `cb9c4160b86268d58c47839ded3731085f97cd11cac9abda1612bef4451083c1` | `9ed3c1a522065a7d12c1d92fad0691ba25158188f2c8f53ad5714bc4981d33c1` |
| `build/capstanc` | `193f13b06fa994c1a8f5dbee31980b5766d4cf2b838252fbc7fb027218b989fc` | `6bc229a36bc4de16f0e1420d9b7b3f147c658755a5a7df58b2efee48658ded54` |
| `build/capstanfmt` | `b5378fc7e7ab24b2458cf8c75c1f4c46abc6eca64801b0a17a513a19144483cf` | `c599fc61a5373d41469c61bbf74666265b4e4526f21121872bd4ba2e1404dc07` |
| `build/capstan-lsp` | `5d87af628f34cba4260eab20c26f5cbc74adc99f1ad6fcc55ce6526ce1d3a8c4` | `8342b412c8194c486eeb978299bb7293481a64dd0dc0286c54ce9fd9d1a159cb` |

## Local tool executable identities

These hashes identify the resolved executables. The OS and kernel above identify
the environment for the build and tests.

| Executable | SHA-256 |
|---|---|
| GCC driver | `a23ecab8ff08f09ad8c80602c2c5df7f49e09c25905cb8975902e101bf72635f` |
| GCC `cc1` | `02675980109a4a5496cddf67d5286de57942759edc830deaa525e36f9a2a0291` |
| GNU assembler | `07dd8551ea0aa065975e4dddb8e1bb7dc308d12d54eca22c3858db79467c7cb9` |
| GNU linker | `d2766988b6a1b1d1518cdc09242e726d1f24e151e16410ada3092b11ffd9081b` |
| Python | `fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7` |
| GNU Make | `8a229baf64671988cfb5af43ba3070c6ce7214cf32bcf96155115559d1466fa7` |
| Git | `1a408c65693b5bc310aa0b250bebb77c7693c1636e7ed8d68083dcccf884b446` |

## Test result and scope

`bash tests/run.sh` exited zero with **561 passed, 0 failed**. Both GitHub GCC
jobs reported **562 passed, 0 failed**. Clang was absent locally, so the suite's
optional Clang bootstrap fixpoint check did not run and the portability check
covered GCC at `-O0`, `-O2` and `-O3`. The CI portability check exercised both
GCC and Clang. Both environments reported 14,110 Shroud behaviour checks
passed.

The suite rewrote two tracked files in the detached worktree.
`tests/spec_coverage.py` regenerated `docs/CONFORMANCE.md` from 44 areas and
249 tagged tests to 45 areas and 292 tagged tests. The Shroud harness ran with
`--update-golden` and rewrote two accessibility JSON hashes in
`tests/shroud/golden.txt`. Both regenerated results agree with the original
and rerun CI logs. The Shroud PNG hashes matched the committed values. The
successful suite permits these regenerations, so its exit status does not
establish that the committed generated references are current.

This was a separately operated reproduction of the integrated Linux/GCC
baseline. macOS, Clang, Lean, and CodeQL were outside the local run. Programme
ownership acknowledgements, the independent review of all eight criteria,
and the programme authority's decision remain with the acceptance process.
