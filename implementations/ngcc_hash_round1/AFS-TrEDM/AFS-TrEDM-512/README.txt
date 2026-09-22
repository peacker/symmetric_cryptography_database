AFS-TrEDM-S6 reference implementation for AFS-TrEDM-512
====================================================

This directory contains the ISO C99 reference implementation for the S6
variant of AFS-TrEDM-512.  The implementation keeps the AFS-TrEDM aligned TrEDM
sponge mode, AFS64_t5_k2 S-box, padding/framing rules, MSB-first bit handling
and public SplitMix64 RC32(round,lane) schedule, but replaces the pre-S6
row-wise linear layer with the lane-friendly AFS-LMDS-1600-S6 linear
diffusion layer.

Instance profile
----------------

Digest length: 512 bits
Default split: g = 6 rounds, h = 6 rounds
Effective permutation: AFS-p-S6[1600,12]

The S6 profile follows the current AFS-LMDS-1600-S6 design report:
512 uses 6+6 rounds, 768 uses 10+10 rounds, and 1024 uses 12+12 rounds.
This means that only the 1024-bit instance remains a 24-round permutation in
the original sense.  Stage112 L64x25 KAT is invalid for S6. S6 has new
IV/domain strings, linear layer, and round profiles.

Files
-----

CryptHash_AlgorithmInstance.h
    ICCS API_CryptHash interface header.  The macros ALGORITHM_INSTANCE and
    DIGEST_BIT_LENGTH are set for this instance.

CryptHash_AlgorithmInstance.c
    CryptHash() wrapper that validates the fixed digest length and calls the
    AFS-TrEDM core.

afs_sbox64.c / afs_sbox64.h
    Reference implementation of the selected AFS-64 S-box instance:
    A8 = 11000011, K8 = [17, 24, 1, 1, 16, 31, 24, 0].

afs_lmds1600_s6.c / afs_lmds1600_s6.h
    Reference implementation of AFS-LMDS-1600-S6:
        L_r = tau[d_r]^-1 o L_P o tau[d_r],
        d_r = [INF,0,1,2,3,4][r mod 6],
        L_P = mu o pi_AFS o rho_AFS o M_col.
    This is a lane-major 25 x 64-bit linear layer built from a bitsliced GF(32)
    Cauchy MDS, AFS lane rotation, a 1+24 long-cycle lane permutation,
    per-lane invertible diffusion, and six projective directions.
    The GF(32) MDS multiplication is implemented with generic xtime/multiply
    code for readability and auditability.

afs_p1600.c / afs_p1600.h
    AFS-p-S6[1600,12] reference permutation.  The public RC32(round,lane)
    constants are still generated directly from the documented SplitMix64
    schedule at use time.

afs_tredm.c / afs_tredm.h
    Aligned TrEDM sponge mode and padding/framing logic.  The hard-coded IV
    was re-derived with the domain string:
        AFS-TrEDM-v2|d=512|r=1024|c=576|b=1600|nr=12|sbox=AFS64_t5_k2|linear=AFS-LMDS-1600-S6

KAT_CryptHash.c, drng.c, drng.h
    ICCS KAT generator and deterministic random generator files.

quick_test.c
    Small smoke-test program.  It is not part of the ICCS API.

hash_cli.c
    Command-line helper for hashing byte-aligned messages.

benchmark.c
    Reproducible performance benchmark driver.

Build and smoke test
--------------------

    make clean
    make
    make run-quick
    make profile-info

Short KAT generation
--------------------

    make kat-2-12

Full KAT generation
-------------------

    make kat
    ./kat

The full KAT run includes the 2^33-bit message test and requires substantial
time and memory, as noted in the ICCS API template.

Benchmark
---------

    make benchmark
    ./benchmark --quick
    ./benchmark --full

Round-constant note
-------------------

The public SplitMix64 RC32(round,lane) design is retained.  It injects a
deterministic public 32-bit constant into every AFS64_t5_k2 call.  The constants
used by each instance are generated directly by the submitted permutation
source.
