Eijen CryptHash API package for this algorithm instance.

Files:
- CryptHash_AlgorithmInstance.h: required ICCS CryptHash API and instance macros.
- CryptHash_AlgorithmInstance.c: adapter from CryptHash bit-length API to Eijen.
- eijen.h, eijen_internal.h, eijen_ref.c/eijen_avx2.c: Eijen implementation source.
- KAT_CryptHash.c, drng.c, drng.h: unmodified ICCS test-vector generator support files.
- CMakeLists.txt: automated build script.

Build and run:
  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
  cmake --build build -j
  ./build/kat
