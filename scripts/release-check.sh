#!/usr/bin/env bash
# Pre-release consistency checks. Usage: scripts/release-check.sh v0.4.0
# Fails unless the tag, the compiler's VERSION and the changelog all agree,
# and the changelog entry is no longer marked unreleased.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tag="${1:?usage: release-check.sh vX.Y.Z}"
ver="${tag#v}"
[[ "$ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "tag '$tag' is not vX.Y.Z"; exit 1; }
src_ver="$(sed -n 's/^const string VERSION = "\(.*\)";/\1/p' "$ROOT/compiler/main.cap")"
[[ "$src_ver" == "$ver" ]] || { echo "compiler VERSION is $src_ver, tag is $ver"; exit 1; }
grep -q "^## $ver\$" "$ROOT/CHANGELOG.md" || { echo "CHANGELOG.md has no released '## $ver' entry (remove '(unreleased)' when releasing)"; exit 1; }
if [[ -x "$ROOT/build/capstanc" ]]; then
  [[ "$("$ROOT/build/capstanc" version)" == "Capstan $ver" ]] || { echo "built compiler reports a different version"; exit 1; }
fi
echo "release $tag: version and changelog consistent"
