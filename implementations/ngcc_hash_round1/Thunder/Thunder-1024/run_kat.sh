#!/bin/bash

set -e

rm -f kat

gcc -std=c99 -O2 \
    KAT_CryptHash.c \
    CryptHash_AlgorithmInstance.c \
    drng.c \
    -o kat

echo "==== Running KAT (generate test vectors) ===="

./kat

echo "==== Done ===="