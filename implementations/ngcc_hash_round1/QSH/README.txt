QuantaSylva Hash (QSH) -- Reference Implementation
==================================================

Directory layout (one folder per algorithm instance):
  QSH-512/    QSH-512  (w=32, 512-bit digest)
  QSH-768/    QSH-768  (w=64, 768-bit digest)
  QSH-1024/   QSH-1024 (w=64, 1024-bit digest)

Each folder is self-contained and builds an executable "katgen" that
generates the known-answer test (KAT) vector files using the official,
unmodified ICCS toolchain (drng.c, KAT_CryptHash.c). The QSH algorithm
itself is implemented in CryptHash_AlgorithmInstance.c (pure ISO C99).

See each folder's README.txt for details.
