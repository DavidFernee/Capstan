# Anchor A1 process-adapter contract harness

Run independently of the compiler and without launching a child process:

```sh
python3 -I tests/anchor/process_adapter_contract.py
```

The harness is deliberately test-only. It defines a deterministic reference model
and a fake OS boundary so that process lifecycle, output budgets, cancellation,
deadlines, restart backoff, JSON-RPC framing/correlation and stale-diagnostic rules
can be exercised before the native process API exists.

**What passing means:** the reference model and its contract tests are internally
consistent for the listed cases.

**What passing does not mean:** it does not test a production process adapter, a
real kernel process group/job object, real descriptor inheritance, actual OS I/O,
a native Anchor LSP connection, or any security property of an unimplemented
backend. The fake backend never calls `subprocess`, `fork`, `exec`, or shell APIs.

When a production Capstan-native adapter is available, retain these vectors and
run the same semantic cases against an adapter conformance bridge. Do not replace
the reference model with the implementation under test or let the mock become
the only evidence.

The existing compiler LSP parser/server has its own end-to-end protocol and fuzz
tests under `tests/lsp/`; this harness covers Anchor's adapter/supervision contract,
not a second implementation of the compiler's LSP server.
