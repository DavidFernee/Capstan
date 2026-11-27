# G0 literal dependency inventory

Pinned commit 7be0a4a6ee02b9eb76bb06a5505cb6d9b277e6b6. Roots: seven explicitly supplied compiler modules from tests/run.sh; ccam_lowering, ccam_native_x64, ccam_direct_elf_tests, ccam_aggregate_machine. Recursively inspected line-start literal imports in bounded batches. All 23 retrieved; all detected edges resolved. Compiler files have implicit global symbol dependencies not represented by imports. This is not full production closure: native research modules beyond these roots, C runtime/headers, seed, generated artifacts, host tools and implicit symbols remain open. No build executed.

| Path | Git blob | Literal imports (relative) |
|---|---|---|
| compiler/ast.cap | 596dac3f21d25b404ae2c3e900b09da611488542 | None detected |
| compiler/lexer.cap | 6bc9bf8c12b4b9bcf8928b45d302f8e8453a02eb | None detected |
| compiler/parser.cap | b656da773f2aa118b0fd2eeeb537a8a4614cad1e | None detected |
| compiler/checker.cap | 3a7b109196e350397238b9e6aa723345566e5365 | None detected |
| compiler/ranges.cap | 91431cbf826b5953481178f67ecfe942f08094f4 | None detected |
| compiler/codegen.cap | a43b6163a11f3d71f0e74b1758e4cf49e24d9c89 | None detected |
| compiler/main.cap | ac1b4d3b4985ddc32b19914dd353b127d5fddc68 | None detected |
| verification/ccam_lowering.cap | db91956debb38de7acb2766ebf25e7f589fcd7e0 | ccam_calls.cap |
| verification/ccam_native_x64.cap | e3eee998b9c82c9c28810bf9e672d8589f880c1f | ccam_lowering.cap |
| verification/ccam_direct_elf_tests.cap | 7f7d91a0c903e2af726fcfe98e657c16db409a00 | ccam_direct_elf.cap |
| verification/ccam_aggregate_machine.cap | c359b6efad1a0b7fb702139875b9093d2a13a26f | ccam_heap.cap |
| verification/ccam_calls.cap | 0f6d64132415186398f09f43f305b743f8d3a2df | ccam_core.cap, ccam_memory_unwind_model.cap |
| verification/ccam_core.cap | 5ce0daf5cdfebd886aaaf8a097ec53a48775e6c8 | None detected |
| verification/ccam_memory_unwind_model.cap | 64a90828ad271f4446c637117bfd350462db528f | ccam_memory_store_model.cap |
| verification/ccam_direct_elf.cap | b6b2b94875525b9502087b345cd6f167e149e39a | ccam_calls.cap, native_elf64.cap, native_link_model.cap, native_alu_encoding.cap |
| verification/ccam_heap.cap | d72d00ba2ffdffc74f79d5a4b381c2f1187c6c77 | None detected |
| verification/ccam_memory_store_model.cap | a219c0b9e07508d06335a81db77d27b5570781db | ccam_core.cap, ccam_memory_reservation.cap |
| verification/native_elf64.cap | 7788480d1bd314036be5ef570c41ef9d0afa4ba0 | native_binary_fields.cap |
| verification/native_link_model.cap | f7b8dcab473cc5961661754e3916928dfab48a41 | native_rel32.cap |
| verification/native_alu_encoding.cap | 72a95f16ec6d121c19c17a45f13dbf874493fb77 | native_rel32.cap |
| verification/ccam_memory_reservation.cap | e7937f6cad073c12d878fc05a6b468dd59a1c19e | ccam_core.cap |
| verification/native_binary_fields.cap | 41d9a085e39dfbebd15bd8c16809b6b587af66fc | None detected |
| verification/native_rel32.cap | a261d36ac481db9983eda5624a7a3613d7f69f73 | None detected |

G0 HOLD. Extend to remaining build roots and actual compiler invocation manifest.

## Build entry points at the integrated G0 revision

Inspected `02328b31a555f282878574b2f65ee68dc2751a2a`, the pinned #583
revision used for the separately operated Linux/GCC reproduction.

| Entry point | Explicit inputs and generated stages |
|---|---|
| `make bootstrap` | `bootstrap/capstan0.py` translates the seven compiler sources from `Makefile`'s `SRC` into `stage1.py`. The same ordered inputs produce `stage2.c` and `stage3.c`. The recipe compares those outputs byte for byte. |
| `make fmt` | The bootstrapped compiler translates `tools/fmt.cap` into `fmt.c`. GCC produces `capstanfmt`. |
| `make lsp` | The bootstrapped compiler translates the first six compiler sources in `SRC`, followed by `tools/lsp.cap`, into `lsp.c`. GCC produces `capstan-lsp`. |
| `bin/capstan native` | The bootstrapped compiler receives `compiler/{ast,lexer,parser,checker}.cap`, `verification/{ccam_core,ccam_calls,ccam_lowering,ccam_native_x64,ccam_direct_elf}.cap`, then `tools/native_driver.cap`. GCC builds the driver. Direct mode writes ELF from the driver. Assembly mode additionally uses `as` and `ld`, then checks the image with `readelf` and `nm`. |

Ran `gcc -MM -Iruntime` on the reproduced `stage2.c`, `stage3.c`, `fmt.c`
and `lsp.c`, and on a freshly emitted `native-driver.c` generated from
the ordered inputs above. All five reported the same two repository headers,
`runtime/capstan_rt.h` and its included `runtime/capstan_gc.h`. The pinned
Makefile declared only the first as a prerequisite. A simulated change to
the collector header left the stage 2 build out of date without scheduling
its recipe. The follow-up Makefile change tracks both headers for the four
persistent executables.

The dependency scan excludes host and system headers. This inventory covers
the listed entry points on the pinned Linux/GCC baseline. It does not extend
to a production C-free seed, future native profiles or every repository test.
