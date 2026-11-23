#!/usr/bin/env bash
# Verify a downloaded Capstan release. See docs/TESTING.md, "Verifying a release".
#
#   scripts/verify-release.sh [options] vX.Y.Z [DIR]
#
# DIR holds the release's assets; without it they are downloaded with `gh release download`.
# Checks, in order (any failure stops with exit status 1):
#   1. SHA256SUMS: every listed file is present and matches; no unlisted file is present
#      (other than signature bundles and the provenance bundle).
#   2. Signatures: every listed file and SHA256SUMS has a Sigstore bundle (FILE.sigstore.json)
#      that cosign verifies as signed by this repository's release workflow, for this tag,
#      through GitHub's OIDC issuer.
#   3. Provenance: `gh attestation verify` finds SLSA build provenance for every listed file,
#      made by the release workflow from this tag on a GitHub-hosted runner, both in the
#      repository's attestation store and in the attached capstan-X.Y.Z.intoto.jsonl.
#   4. SBOM: the CycloneDX and SPDX SBOMs describe exactly the files in the source archive.
#   5. Reproducibility: every platform's report says the compiler reproduced itself, and all
#      report the same build/stage2.c and build/stage3.c checksums.
#   6. With --rebuild: the source archive is unpacked and bootstrapped here (needs a C compiler,
#      make and Python 3), and must produce those same checksums.
#
# Options:
#   --rebuild            also do check 6
#   --skip-signatures    leave out check 2 (for testing without network access)
#   --skip-attestations  leave out check 3 (likewise)
#   --repo OWNER/REPO    the repository the release must come from (default DavidFernee/Capstan)
#
# Run it from a clone of the repository you have reviewed, not from the archive being verified.
# Needs: bash, python3, sha256sum or shasum; cosign (v3 or later) for check 2; gh for check 3
# (`gh auth login` first) and for downloading.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="DavidFernee/Capstan"
ISSUER="https://token.actions.githubusercontent.com"
rebuild=0; sigs=1; atts=1; args=()
while (($#)); do
  case "$1" in
    --rebuild) rebuild=1 ;;
    --skip-signatures) sigs=0 ;;
    --skip-attestations) atts=0 ;;
    --repo) REPO="${2:?--repo needs OWNER/REPO}"; shift ;;
    -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    -*) echo "verify-release: unknown option $1" >&2; exit 2 ;;
    *) args+=("$1") ;;
  esac
  shift
done
tag="${args[0]:-}"; dir="${args[1]:-}"
[[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "usage: verify-release.sh [options] vX.Y.Z [DIR]" >&2; exit 2; }
[[ "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo "verify-release: bad --repo '$REPO'" >&2; exit 2; }
ver="${tag#v}"
WORKFLOW="$REPO/.github/workflows/release.yml"
IDENTITY="https://github.com/$WORKFLOW@refs/tags/$tag"

die() { echo "verify-release: FAILED: $*" >&2; exit 1; }
step() { echo "== $*"; }
sha256() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }
need() { command -v "$1" >/dev/null || die "$1 is needed for $2 (or pass $3 to leave this check out)"; }
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

if [[ -z "$dir" ]]; then
  command -v gh >/dev/null || die "gh is needed to download the release; or download it yourself and pass DIR"
  dir="$tmp/release"; mkdir "$dir"
  step "downloading $REPO $tag"
  gh release download "$tag" --repo "$REPO" --dir "$dir"
fi
[[ -d "$dir" ]] || die "$dir is not a directory"
cd "$dir"

step "checksums"
[[ -f SHA256SUMS ]] || die "SHA256SUMS is missing"
listed=()
while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^([0-9a-f]{64})\ [\ *]([A-Za-z0-9][A-Za-z0-9._-]*)$ ]] || die "malformed SHA256SUMS line: $line"
  want="${BASH_REMATCH[1]}"; f="${BASH_REMATCH[2]}"
  [[ -f "$f" && ! -L "$f" ]] || die "$f is listed in SHA256SUMS but missing"
  [[ "$(sha256 "$f")" == "$want" ]] || die "$f does not match its checksum"
  listed+=("$f")
done < SHA256SUMS
((${#listed[@]})) || die "SHA256SUMS is empty"
for f in * .[!.]*; do
  [[ -e "$f" ]] || continue
  case "$f" in SHA256SUMS|*.sigstore.json|"capstan-$ver.intoto.jsonl") continue ;; esac
  printf '%s\n' "${listed[@]}" | grep -qxF -- "$f" || die "$f is not listed in SHA256SUMS"
done
for f in "capstan-$ver.tar.gz" "capstan-$ver.cdx.json" "capstan-$ver.spdx.json"; do
  printf '%s\n' "${listed[@]}" | grep -qxF -- "$f" || die "$f is not in the release"
done
ls reproducibility-*.txt >/dev/null 2>&1 || die "no reproducibility report in the release"
echo "  ${#listed[@]} files match SHA256SUMS"

if ((sigs)); then
  step "signatures (cosign, keyless: $IDENTITY)"
  need cosign "checking signatures" --skip-signatures
  for f in SHA256SUMS "${listed[@]}"; do
    [[ -f "$f.sigstore.json" ]] || die "$f has no signature bundle ($f.sigstore.json)"
    cosign verify-blob --bundle "$f.sigstore.json" --certificate-identity "$IDENTITY" \
      --certificate-oidc-issuer "$ISSUER" "$f" >/dev/null 2>"$tmp/cosign" \
      || { cat "$tmp/cosign" >&2; die "signature of $f does not verify"; }
    echo "  signed: $f"
  done
else
  echo "== signatures: SKIPPED (--skip-signatures)"
fi

if ((atts)); then
  step "build provenance (gh attestation verify: $WORKFLOW, refs/tags/$tag)"
  need gh "checking provenance" --skip-attestations
  opts=(--repo "$REPO" --signer-workflow "$WORKFLOW" --source-ref "refs/tags/$tag" --deny-self-hosted-runners)
  for f in "${listed[@]}"; do
    gh attestation verify "$f" "${opts[@]}" >"$tmp/att" 2>&1 || { cat "$tmp/att" >&2; die "no valid provenance for $f in $REPO's attestations"; }
    if [[ -f "capstan-$ver.intoto.jsonl" ]]; then
      gh attestation verify "$f" --bundle "capstan-$ver.intoto.jsonl" "${opts[@]}" >"$tmp/att" 2>&1 \
        || { cat "$tmp/att" >&2; die "capstan-$ver.intoto.jsonl does not hold valid provenance for $f"; }
    fi
    echo "  provenance: $f"
  done
else
  echo "== build provenance: SKIPPED (--skip-attestations)"
fi

step "SBOM"
out="$(python3 -I "$ROOT/scripts/sbom.py" check --archive "capstan-$ver.tar.gz" \
  --cyclonedx "capstan-$ver.cdx.json" --spdx "capstan-$ver.spdx.json" 2>&1)" || die "SBOM: $out"
echo "  $out"

step "reproducibility"
field() { sed -n "s|^$2: ||p" "$1" | head -1; }
s2=""; s3=""
for r in reproducibility-*.txt; do
  [[ "$(field "$r" fixpoint)" == reached ]] || die "$r: the compiler did not reproduce itself"
  [[ "$(field "$r" compiler)" == "Capstan $ver" ]] || die "$r: built compiler is '$(field "$r" compiler)', not Capstan $ver"
  a="$(field "$r" "sha256 build/stage2.c")"; b="$(field "$r" "sha256 build/stage3.c")"
  [[ "$a" =~ ^[0-9a-f]{64}$ && "$a" == "$b" ]] || die "$r: stage2.c and stage3.c checksums differ or are missing"
  [[ -z "$s3" || "$b" == "$s3" ]] || die "$r reports stage3.c $b, another platform reported $s3"
  s2="$a"; s3="$b"
  echo "  $r: fixpoint reached ($(field "$r" platform); $(field "$r" cc))"
done
echo "  every platform: build/stage2.c = build/stage3.c = sha256 $s3"

if ((rebuild)); then
  step "rebuild from capstan-$ver.tar.gz"
  for t in make python3 "${CC:-cc}"; do command -v "$t" >/dev/null || die "--rebuild needs $t"; done
  mkdir "$tmp/src"
  python3 -I -c 'import sys, tarfile; tarfile.open(sys.argv[1]).extractall(sys.argv[2], filter="data")' \
    "capstan-$ver.tar.gz" "$tmp/src" 2>/dev/null \
    || tar -xzf "capstan-$ver.tar.gz" -C "$tmp/src"
  [[ -f "$tmp/src/capstan-$ver/Makefile" ]] || die "archive does not unpack to capstan-$ver/"
  make -s -C "$tmp/src/capstan-$ver" bootstrap >"$tmp/build.log" 2>&1 || { tail -20 "$tmp/build.log" >&2; die "bootstrap of the source archive failed"; }
  got2="$(sha256 "$tmp/src/capstan-$ver/build/stage2.c")"; got3="$(sha256 "$tmp/src/capstan-$ver/build/stage3.c")"
  [[ "$got2" == "$s2" && "$got3" == "$s3" ]] || die "rebuilt stage2.c/stage3.c ($got2 / $got3) differ from the published $s3"
  echo "  rebuilt here: fixpoint reached, stage3.c sha256 $got3 matches every platform"
fi

echo "verify-release: $REPO $tag verified ($( ((sigs)) && echo signatures || echo 'signatures skipped'), $( ((atts)) && echo provenance || echo 'provenance skipped')$( ((rebuild)) && echo ', rebuilt' ))"
