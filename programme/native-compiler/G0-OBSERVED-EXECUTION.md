# G0 observed execution evidence

PR #573 head 0c9038868711651c1746dce784ea2f8246950ef3; logs identify synthetic merge 8458eb6 into 7be0a4a6ee02b9eb76bb06a5505cb6d9b277e6b6. Not final consolidated main 9be453f954bb78a83abee5f48993773ef08f1ffe.

CI run 45964503460: Ubuntu Clang job 140389847167 562/0; Ubuntu GCC 140389847233 562/0; macOS Clang 140389847221 542/0; supply-chain 140389846803 success. Ubuntu image ubuntu-26.04 version 20261116.202.1; macos-26-arm64 version 20261117.0516.1. Bootstrap fixpoint and stage3.c checksum recording reported; actual digest and compiler/Python versions not recovered. Artifact listing empty.

Formal run 45964503488: language job 140389847204 Lean 4.19.0 commit 6caaee842e94; injection checker source bridge PASS. Allocator job 140389846680 Lean 4.36.0 commit 611c117bfaf7b7ae1cfcf246ce6fba31e8f509e9; additional checks reported 60118 and 60261 declarations with no errors, skipping exported but unpermitted sorryAx. Counts overlap or include dependencies and are not requirements coverage; no claim of concrete compiler refinement. CodeQL run 45964503411 success.

All seven evidence PRs merged; comparison to original audited baseline shows seven added programme documents only. Consolidated exact commit workflow and combined-status queries returned no results. Independent reproduction and acceptance outstanding. G0 HOLD.
