# Schooner threat model

**Status:** initial proposal; review required
**Date:** 2026-11-26
**Related:** [Schooner architecture](ARCHITECTURE.md)

## Assets

Kernel integrity; process and service memory; capability authority; user and service data; secrets and cryptographic keys; persistent data; device and DMA memory; boot/update keys and measurements; resource availability; audit/evidence records.

## Adversaries

- Unprivileged local process attempting privilege escalation, data theft, denial of service or cross-process access.
- Malicious or compromised user-space service, driver, parser or application.
- Malformed or adversarial IPC, filesystem, network, media and device input.
- Compromised or buggy device/firmware and malicious DMA-capable peripherals.
- Concurrent processes racing capability use/revocation, process teardown, mapping changes or service restart.
- Supply-chain compromise of source dependencies, compiler, assembler, linker, image builder or update channel.
- Physical attacker where the platform's hardware protection and secure-boot assumptions make that threat in scope.

## Trust boundaries

1. Capstan source and type/effect checking to CCAM lowering.
2. CCAM validation/evaluation to native code generation.
3. Native code to ISA/ABI and platform adapters.
4. User mode to kernel mode.
5. Process/service to process/service IPC.
6. Kernel to device, firmware and DMA.
7. Storage/network/media untrusted bytes to parsers.
8. Build/release/update infrastructure to installed boot image.

Each boundary needs an explicit data/authority contract, validation, resource budget, failure behaviour and evidence.

## Security goals

- No unprivileged path to kernel memory or another process's private memory.
- No authority amplification through delegation, stale handles, object reuse or confused deputies.
- No memory reclamation while any CPU/device actor can still access the region.
- No resource budget duplication or unbounded kernel work from untrusted requests.
- No parser-controlled allocation or iteration outside declared limits.
- No service failure that silently leaks capabilities or reserved resources past teardown.
- No claim of confidentiality against hardware/firmware side channels without an explicit mitigation and hardware threat model.
- No claim that language safety alone proves kernel, runtime, compiler, firmware or hardware correctness.

## Explicit exclusions and assumptions

The first emulator milestone does not establish resistance to physical attacks, malicious firmware, microarchitectural side channels, faulty hardware, all DMA behaviours or arbitrary hypervisor compromise. These must be recorded as assumptions or later work, not silently treated as prevented.

The design does not promise that every application is free of logic flaws, that arbitrary concurrent programs terminate, or that all denial of service is preventable. It aims to bound kernel-controlled work and isolate faults under declared assumptions.

## Required evidence

For every goal, identify: formal property; implementation mechanism; attacker-controlled inputs; negative/adversarial tests; fault-injection cases; hardware assumptions; residual risks; exact commit and platform. Unknown evidence remains unknown. No vulnerability class is declared impossible merely because the language lacks a corresponding surface syntax.
