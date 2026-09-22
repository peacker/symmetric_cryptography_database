QuantaSylva Hash (QSH) -- Reference Implementation: instance QSH-768
================================================================

Variant parameters
  word width w        : 64 bits
  ChaCha-Bahru rounds : 18 full R-rounds + 1 final column-only layer
  digest length       : 768 bits
  state h = 4096, message block m = h/2, chunk = 16 blocks, tree mode

Files
  CryptHash_AlgorithmInstance.h   Programming interface (official NGCC API).
                                  Sets ALGORITHM_INSTANCE / DIGEST_BIT_LENGTH.
  CryptHash_AlgorithmInstance.c   QSH reference implementation of CryptHash().
                                  Pure ISO C99, no platform intrinsics.
  drng.c / drng.h                 Official ICCS DRNG.
  KAT_CryptHash.c                 Official KAT generator.
  CMakeLists.txt / build.sh       Automated build (C99, -O2).
  README.txt                      This file.

Build & generate test vectors
  sh build.sh        (or: cmake -B build && cmake --build build)
  ./katgen           -> writes ./output/KAT_2_12_QSH-768.txt, KAT_2_23, KAT_2_33, KAT_Loop

Interface
  int CryptHash(int digest_len_bits, const unsigned char *msg,
                unsigned long long msg_len_bits, unsigned char *digest);
  Conventions: message bits MSB-first within bytes; words and the 128-bit
  length little-endian; digest serialized little-endian.
