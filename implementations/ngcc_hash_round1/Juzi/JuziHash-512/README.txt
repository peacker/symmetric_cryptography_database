JuziHash-512 reference ISO C implementation, GCC/Linux version

This folder contains the ICCS CryptHash API implementation and KAT generator for
JuziHash-512.  Windows batch files have been removed; use the Makefile or the shell
script on Linux.

Files:

  CryptHash_AlgorithmInstance.c    JuziHash implementation and CryptHash() entry point.
  CryptHash_AlgorithmInstance.h    ICCS-compatible header.
  KAT_CryptHash.c                  ICCS KAT generator.
  drng.c, drng.h                   ICCS DRNG support files.
  Makefile                         GCC build rules.
  run_kat_gcc.sh                   Build and run the KAT generator.
  README.txt                       This file.

Build:

  make

Run KAT generation:

  make kat

Clean generated files:

  make clean

Compiler flags:

  gcc -std=c99 -O2 -Wall -Wextra

No platform-specific instruction is required.

The public ICCS entry point is:

  int CryptHash(int digest_len_bits, const unsigned char *msg,
                unsigned long long msg_len_bits, unsigned char *digest);

For this instance, digest_len_bits must be 512.
