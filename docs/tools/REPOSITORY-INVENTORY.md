# Capstan repository inventory tool

`tools/inventory.cap` is a Capstan implementation of a source-file and physical-line inventory reporter.

## Build

From the repository root:

```sh
mkdir -p build
bin/capstan build -o build/inventory.c tools/inventory.cap
${CC:-cc} -std=gnu11 -O2 -Iruntime build/inventory.c -o build/capstan-inventory
```

The current compiler wrapper emits C and therefore still requires the existing C toolchain. This tool is Capstan source, but it does not pretend the bootstrap/compiler pipeline is already C-free.

## Run against tracked files

```sh
tracked=()
while IFS= read -r -d '' path; do tracked[${#tracked[@]}]="$path"; done < <(git ls-files -z)
build/capstan-inventory --output build/inventory.csv -- "${tracked[@]}"
```

For a small explicit selection:

```sh
build/capstan-inventory --output build/inventory.csv compiler/main.cap tools/inventory.cap tests/run.sh
```

Without `--output`, the CSV report is written to standard output. The process exits 0 when every file is readable, 1 if one or more files could not be inventoried, and 2 for invalid command-line use or report-write failure.

## Report semantics

The CSV contains a per-file section followed by per-language totals and repository totals. Per-file rows include a `classification` column:

- `lines` counts physical lines: LF bytes plus one when a non-empty file lacks a final LF. CRLF counts as one line break; an empty file has zero lines.
- `bytes` counts file bytes, not Unicode characters.
- A file containing a NUL byte is reported as `Binary (NUL)`, with zero physical source lines. This is a conservative binary-content heuristic, not complete binary-format detection: binary files without NUL bytes can still be counted as text.
- Purpose classification uses exact path segments: `generated` becomes `Generated`; `vendor`, `vendors`, `third_party`, `third-party` and `node_modules` become `Vendored`; `tests`, `test`, `testdata` and `fixtures` become `Test`; `docs` and `documentation` become `Documentation`; other paths are `Repository`. This is a path convention heuristic, not provenance verification.\n- Language classification is extension-based and intentionally conservative. Unknown extensions are reported as `other`; this is a review queue, not a claim that all files are programming languages.
- `escape_csv` is used for every path/classification/language cell. It quotes cells, doubles embedded quotes and neutralises spreadsheet formula prefixes.
- Files larger than 16 MiB, unreadable files and non-regular files are reported as unreadable and cause exit status 1. They are not silently counted as zero-line files.

The tool reports physical lines for files without NUL bytes, not language-aware code/comment/blank SLOC. Its NUL-byte check is deliberately described as a heuristic and must not be used as a security or content-validation boundary. It includes whatever paths the caller supplies; the purpose classification is descriptive and does not exclude any category from totals.

## Important completeness boundary

Capstan currently has path-based bounded file reads but no directory enumeration or Git-tree API. Consequently this program accepts an explicit file list and does not recursively walk the repository itself. A complete inventory depends on obtaining the complete tracked path list from Git (or a future Capstan directory/tree API). A partial list must never be described as a complete repository count.

The current implementation also reads paths using the existing ambient `read_file` API. That API is not a directory capability and does not establish race-resistant repository-root confinement. Do not run it over untrusted worktrees or claim that it provides a sandbox. The longer-term Capstan-only migration must replace this with capability-scoped filesystem access before the inventory tool is treated as a security boundary.
