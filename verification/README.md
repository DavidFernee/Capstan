# Verification prototypes

## CCAM reference machine

Run the C-independent conformance tests with:

```sh
python3 -m unittest discover -s verification -v
```

The reference machine is a deliberately small executable specification for the
Capstan Core Abstract Machine (CCAM) v0.1. It is not the production runtime,
does not yet implement the full Capstan language, and has not itself been
formally verified. See [the machine specification](../docs/architecture/CCAM.md).

The test suite is intended to run before the existing C bootstrap in CI. It
must remain runnable on a machine with Python 3 but no C compiler.

## Scope of the first slice

Implemented: signed-64 checked arithmetic, booleans, typed registers, control
flow, direct calls/returns, explicit traps, and deterministic step/call-depth
limits.

Not implemented yet: parser/source lowering, heap objects, strings, collections,
GC, taint, secrets, policies/grants, IO, concurrency, or native code generation.
These features require explicit semantics and independent conformance tests
before they are added to the machine.
