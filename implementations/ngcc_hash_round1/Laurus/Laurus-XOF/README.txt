The following is a reference implementation code automated build script, which can generate algorithm test vectors.

1->In the Linux system, enter gcc CryptHash_AlgorithmInstance.c drng.c KAT_CryptHash.c laurus_xof.c -o main -O2.
2->Enter ./main to execute the main file.