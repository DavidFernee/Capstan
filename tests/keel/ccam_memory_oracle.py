#!/usr/bin/env python3
"""Differential oracle for CCAM v0.2 byte storage.

Python integers and int.to_bytes are independent of the Capstan implementation.
The generated Capstan program stores deterministic signed-64 vectors, prints
physical abstract bytes and reloads them; both streams are compared exactly.
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPSTANC, CC, *CFLAGS = sys.argv[1:]
rng = random.Random(20261125)
values = [
    -(1 << 63), -(1 << 63) + 1, -0x0102030405060708,
    -65536, -257, -256, -255, -1, 0, 1, 255, 256, 257,
    65535, 0x0102030405060708, (1 << 63) - 2, (1 << 63) - 1,
]
values.extend(rng.randint(-(1 << 63), (1 << 63) - 1) for _ in range(192))
count = len(values)
source = [
    'int main() {',
    '    CCAMMemManager manager = ccam_mem_manager(1, 4096);',
    f'    CCAMMemCreateResult created = ccam_mem_create(manager, 17, {count * 8}, -1);',
    '    if (!created.ok) { return 1; }',
    f'    CCAMMemResult reserved = ccam_mem_reserve(created.manager, created.identity, 17, {count}, 8, 8);',
    '    if (!reserved.ok) { return 1; }',
    '    manager = reserved.manager;',
]
for i, value in enumerate(values):
    literal = "CCAM_I64_MIN" if value == -(1 << 63) else str(value)
    source.extend([
        f'    CCAMMemResult store_{i} = ccam_mem_store_i64(manager, reserved.view, 17, {i}, {literal});',
        f'    if (!store_{i}.ok) {{ return 1; }}',
        f'    manager = store_{i}.manager;',
    ])
source.extend([
    '    string bytes_line = "";',
    f'    for (int i = 0; i < {count * 8}; i += 1) {{',
    '        if (i > 0) { bytes_line = bytes_line + ","; }',
    '        bytes_line = bytes_line + int_to_str(manager.regions[0].bytes[i]);',
    '    }',
    '    println(bytes_line);',
    '    string values_line = "";',
    f'    for (int i = 0; i < {count}; i += 1) {{',
    '        CCAMMemResult loaded = ccam_mem_load_i64(manager, reserved.view, 17, i);',
    '        if (!loaded.ok) { return 1; }',
    '        if (i > 0) { values_line = values_line + ","; }',
    '        values_line = values_line + int_to_str(loaded.int_value);',
    '    }',
    '    println(values_line);',
    '    return 0;',
    '}',
])
program = "\n".join(source) + "\n"
expected_bytes = b"".join(value.to_bytes(8, "little", signed=True) for value in values)
expected = [
    ",".join(str(byte) for byte in expected_bytes),
    ",".join(str(value) for value in values),
]
with tempfile.TemporaryDirectory(prefix="capstan-ccam-memory-oracle-") as tmp:
    # The imported CCAM core is also a standalone verification program. Rename
    # its entry point in this isolated oracle copy so the generated oracle main
    # is the sole executable entry point; repository sources remain untouched.
    source_paths = {
        "ccam_core.cap": "verification/ccam_core.cap",
        "ccam_memory_reservation.cap": "verification/ccam_memory_reservation.cap",
        "ccam_memory_store_model.cap": "verification/ccam_memory_store_model.cap",
    }
    for name, relative in source_paths.items():
        with open(os.path.join(ROOT, relative), "r", encoding="utf-8") as source_file:
            content = source_file.read()
        if name == "ccam_core.cap":
            if content.count("int main() {") != 1:
                sys.exit("CCAM core oracle entry-point shape changed")
            content = content.replace(
                "int main() {", "int ccam_core_self_test_main() {", 1
            )
        with open(os.path.join(tmp, name), "w", encoding="utf-8") as target_file:
            target_file.write(content)
    model = os.path.join(tmp, "ccam_memory_store_model.cap")
    main = os.path.join(tmp, "memory_oracle.cap")
    cfile = os.path.join(tmp, "memory_oracle.c")
    exe = os.path.join(tmp, "memory_oracle")
    with open(main, "w", encoding="utf-8") as f:
        f.write(program)
    build = subprocess.run(
        [CAPSTANC, "build", "--strict", "-o", cfile, model, main],
        cwd=ROOT, capture_output=True, text=True)
    if build.returncode:
        sys.exit("CCAM memory oracle program did not compile:\n" +
                 build.stdout + build.stderr)
    compiled = subprocess.run(
        [CC, *CFLAGS, cfile, "-o", exe],
        cwd=ROOT, capture_output=True, text=True)
    if compiled.returncode:
        sys.exit("CCAM memory oracle C did not compile:\n" +
                 compiled.stdout + compiled.stderr)
    run = subprocess.run([exe], cwd=ROOT, capture_output=True, text=True)
    if run.returncode:
        sys.exit(f"CCAM memory oracle exited {run.returncode}:\n" +
                 run.stdout + run.stderr)
    actual = run.stdout.splitlines()
    if actual != expected:
        for i, (got, want) in enumerate(zip(actual, expected)):
            if got != want:
                sys.exit(f"CCAM byte-store oracle stream {i}: mismatch at " +
                         f"expected length {len(want)}, actual length {len(got)}")
        sys.exit(f"CCAM byte-store oracle output length: expected {len(expected)}, got {len(actual)}")
print(f"CCAM byte-store differential oracle: {count} signed-i64 values and {count * 8} little-endian bytes agree")
