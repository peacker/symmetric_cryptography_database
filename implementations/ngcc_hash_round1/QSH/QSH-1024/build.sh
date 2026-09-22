#!/bin/sh
# Reference build (ISO C99). Produces ./katgen, which writes the KAT files
# (KAT_2_12/2_23/2_33/Loop) for QSH-1024 into ./output/.
set -e
gcc -std=c99 -Wpedantic -Wall -Wextra -O2 \
    drng.c KAT_CryptHash.c CryptHash_AlgorithmInstance.c -o katgen
echo "built ./katgen  -- run it to generate ./output/KAT_*_QSH-1024.txt"
