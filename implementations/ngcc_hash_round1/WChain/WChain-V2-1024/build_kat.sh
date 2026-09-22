#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR"

CC=${CC:-gcc}
"$CC" ${CFLAGS:--O2 -std=c99 -Wall -Wextra -Wpedantic} \
  -DWCHAIN_NO_MAIN -DWCHAIN_DISABLE_SIMD \
  -I. \
  KAT_CryptHash.c drng.c CryptHash_AlgorithmInstance.c wchain_c.c \
  -o kat_WChain-V2-1024_ref
