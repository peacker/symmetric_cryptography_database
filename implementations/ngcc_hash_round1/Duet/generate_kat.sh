#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bits_list=(512 768 1024)
cc="${CC:-cc}"
out=""
run_kat=1
extra_flags=()

usage() {
  cat <<'USAGE'
Usage: generate_kat.sh [--bits 512|768|1024] [--cc CC] [-o OUTPUT]
                       [--build-only] [-- EXTRA_CFLAGS...]

Without --bits, builds and runs KAT generators for Duet-512, Duet-768,
and Duet-1024 in sequence. Generated files are written to Duet-*/output/.
Use --bits to run a single algorithm instance.
USAGE
}

while (($#)); do
  case "$1" in
    --bits)
      bits_list=("$2")
      shift 2
      ;;
    --cc)
      cc="$2"
      shift 2
      ;;
    -o|--out)
      out="$2"
      shift 2
      ;;
    --build-only|--no-run)
      run_kat=0
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      extra_flags+=("$@")
      break
      ;;
    *)
      extra_flags+=("$1")
      shift
      ;;
  esac
done

if [[ -n "$out" && "${#bits_list[@]}" -ne 1 ]]; then
  printf 'ERROR: -o/--out can only be used together with --bits.\n' >&2
  exit 1
fi

run_one() {
  local bits="$1"
  local pkg="$SCRIPT_DIR/Duet-$bits"
  local main_src="$pkg/CryptHash_Duet-${bits}.c"
  local exe="$out"

  case "$bits" in
    512|768|1024) ;;
    *)
      printf 'Unsupported --bits value: %s\n' "$bits" >&2
      exit 1
      ;;
  esac

  if [[ -z "$exe" ]]; then
    exe="/tmp/kat_duet_${bits}_reference"
  fi

  printf '\n== Duet-%s reference KAT ==\n' "$bits"
  "$cc" -std=c99 -Wpedantic -Wall -Wextra -O2 \
    ${extra_flags[@]+"${extra_flags[@]}"} -I "$pkg" \
    "$main_src" "$pkg/drng.c" "$pkg/KAT_CryptHash.c" -o "$exe"

  printf 'Built KAT generator: %s\n' "$exe"

  if [[ "$run_kat" -eq 1 ]]; then
    (cd "$pkg" && "$exe")
    printf 'Generated KAT files under: %s/output\n' "$pkg"
  fi
}

for bits in "${bits_list[@]}"; do
  run_one "$bits"
done

printf '\nReference implementation KAT task finished.\n'
