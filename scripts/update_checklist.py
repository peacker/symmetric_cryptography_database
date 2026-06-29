#!/usr/bin/env python3
"""
update_checklist.py

Rewrites FAMILY_COVERAGE_CHECKLIST.md to:
  1. Add a `type` column (block_cipher, stream_cipher, aead, hash, permutation,
     tweakable_block_cipher, mac, prng, construction, mode, etc.)
  2. Add all new entries discovered from:
     - stamparm/cryptospecs (symmetrical + hash)
     - NIST LWC Round 1 candidates
  3. Sort alphabetically by scheme name.
  4. Update pdf_available_in_repo for newly downloaded PDFs.
"""

import os
import re
from pathlib import Path

REPO = Path(__file__).parent.parent
CHECKLIST = REPO / "FAMILY_COVERAGE_CHECKLIST.md"
REFS = REPO / "references"

# ─────────────────────────────────────────────────────────────────────────────
# TYPE MAP: scheme name (lower) -> primary type
# ─────────────────────────────────────────────────────────────────────────────
TYPE_MAP = {
    "ace":                          "permutation",
    "achterbahn":                   "stream_cipher",
    "aes":                          "block_cipher",
    "akelarre":                     "block_cipher",
    "ant":                          "block_cipher",
    "anubis":                       "block_cipher",
    "aradi":                        "block_cipher",
    "aria":                         "block_cipher",
    "ascon":                        "permutation",
    "ballet":                       "block_cipher",
    "bear/lion":                    "construction",
    "belt":                         "block_cipher",
    "bipbip":                       "tweakable_block_cipher",
    "bleep64":                      "aead",
    "blink":                        "block_cipher",
    "blowfish":                     "block_cipher",
    "bmgl":                         "prng",
    "camellia":                     "block_cipher",
    "cast-128":                     "block_cipher",
    "cast-256":                     "block_cipher",
    "chacha":                       "stream_cipher",
    "chaskey":                      "mac",
    "chilow":                       "tweakable_block_cipher",
    "cilipadi":                     "aead",
    "cipherunicorn-a":              "block_cipher",
    "cipherunicorn-e":              "block_cipher",
    "clae":                         "aead",
    "clefia":                       "block_cipher",
    "clx":                          "stream_cipher",
    "cmea":                         "stream_cipher",
    "comet":                        "aead",
    "crisp":                        "block_cipher",
    "crypton":                      "block_cipher",
    "cs-cipher":                    "block_cipher",
    "deal":                         "block_cipher",
    "decim":                        "stream_cipher",
    "deoxys":                       "tweakable_block_cipher",
    "des":                          "block_cipher",
    "desx":                         "block_cipher",
    "dfc":                          "block_cipher",
    "drygascon":                    "permutation",
    "e2":                           "block_cipher",
    "elephant":                     "aead",
    "enocoro-128v2":                "stream_cipher",
    "estate":                       "aead",
    "f-fcsr":                       "stream_cipher",
    "fantomas / robin":             "block_cipher",
    "feal":                         "block_cipher",
    "feal-nx":                      "block_cipher",
    "fbc":                          "block_cipher",
    "fesh":                         "block_cipher",
    "flexaead":                     "aead",
    "forkae":                       "aead",
    "fountain":                     "aead",
    "frog":                         "block_cipher",
    "gage and ingage":              "permutation",
    "gift":                         "block_cipher",
    "gift-cofb":                    "aead",
    "gimli":                        "permutation",
    "gost 28147-89 (magma)":        "block_cipher",
    "grain":                        "stream_cipher",
    "grain-128":                    "stream_cipher",
    "grain-128aead":                "aead",
    "grand cru":                    "block_cipher",
    "hc-256":                       "stream_cipher",
    "hern & heron":                 "block_cipher",
    "hight":                        "block_cipher",
    "hpc":                          "block_cipher",
    "hyena":                        "aead",
    "ice":                          "block_cipher",
    "idea":                         "block_cipher",
    "isaac":                        "prng",
    "isap":                         "aead",
    "kasumi":                       "block_cipher",
    "katan":                        "block_cipher",
    "kcipher-2":                    "stream_cipher",
    "khazad":                       "block_cipher",
    "klein":                        "block_cipher",
    "knot":                         "permutation",
    "ktantan":                      "block_cipher",
    "kuznyechik":                   "block_cipher",
    "laem":                         "aead",
    "lea":                          "block_cipher",
    "lea-128":                      "block_cipher",
    "led":                          "block_cipher",
    "leviathan":                    "stream_cipher",
    "lili-128":                     "stream_cipher",
    "lilliput-ae":                  "aead",
    "limdolen":                     "aead",
    "locus":                        "aead",
    "loki":                         "block_cipher",
    "loki97":                       "block_cipher",
    "lotus":                        "aead",
    "lotus-aead and locus-aead":    "aead",
    "lucifer":                      "block_cipher",
    "macguffin":                    "block_cipher",
    "magenta":                      "block_cipher",
    "mantis":                       "tweakable_block_cipher",
    "mars":                         "block_cipher",
    "mcrypton":                     "block_cipher",
    "mibs":                         "block_cipher",
    "mickey":                       "stream_cipher",
    "midori":                       "block_cipher",
    "mir-1":                        "block_cipher",
    "misty1":                       "block_cipher",
    "mixfeed":                      "aead",
    "mmb":                          "block_cipher",
    "msx":                          "block_cipher",
    "mugi":                         "stream_cipher",
    "multi-s01":                    "stream_cipher",
    "multi2":                       "block_cipher",
    "nbc":                          "block_cipher",
    "newdes":                       "block_cipher",
    "nimbus":                       "block_cipher",
    "noekeon":                      "block_cipher",
    "nush":                         "stream_cipher",
    "orange":                       "permutation",
    "oribatida":                    "permutation",
    "oryx":                         "stream_cipher",
    "pea":                          "block_cipher",
    "photon":                       "permutation",
    "photon-beetle":                "aead",
    "picaro":                       "block_cipher",
    "present":                      "block_cipher",
    "pride":                        "block_cipher",
    "prince":                       "block_cipher",
    "princev2":                     "block_cipher",
    "pyjamask":                     "block_cipher",
    "q":                            "block_cipher",
    "qameleon":                     "aead",
    "qarma":                        "tweakable_block_cipher",
    "qarmav2":                      "tweakable_block_cipher",
    "quartet":                      "aead",
    "raindrop":                     "block_cipher",
    "rabbit":                       "stream_cipher",
    "rc2":                          "block_cipher",
    "rc4":                          "stream_cipher",
    "rc4+":                         "stream_cipher",
    "rc4a":                         "stream_cipher",
    "rc4-drop":                     "stream_cipher",
    "rc5":                          "block_cipher",
    "rc6":                          "block_cipher",
    "remus":                        "aead",
    "rijndael":                     "block_cipher",
    "romulus":                      "aead",
    "saeaes":                       "aead",
    "safer":                        "block_cipher",
    "safer+":                       "block_cipher",
    "safer++":                      "block_cipher",
    "safer-k64":                    "block_cipher",
    "safer-k128":                   "block_cipher",
    "salsa20":                      "stream_cipher",
    "sapphire":                     "stream_cipher",
    "saturnin":                     "block_cipher",
    "sc2000":                       "block_cipher",
    "scarf":                        "tweakable_block_cipher",
    "seal":                         "stream_cipher",
    "seed":                         "block_cipher",
    "serpent":                      "block_cipher",
    "sfinks":                       "stream_cipher",
    "shacal":                       "block_cipher",
    "shacal2":                      "block_cipher",
    "shamash & shamashash":         "hash",
    "shark":                        "block_cipher",
    "simon":                        "block_cipher",
    "simple":                       "aead",
    "siv-rijndael256":              "aead",
    "siv-tem-photon":               "aead",
    "skinny":                       "tweakable_block_cipher",
    "skinny-aead/skinny-hash":      "aead",
    "skipjack":                     "block_cipher",
    "sm4":                          "block_cipher",
    "smba":                         "block_cipher",
    "sneik":                        "permutation",
    "snow":                         "stream_cipher",
    "snow 2.0":                     "stream_cipher",
    "snow 3g":                      "stream_cipher",
    "sober-t16":                    "stream_cipher",
    "sober-t32":                    "stream_cipher",
    "sosemanuk1":                   "stream_cipher",
    "sparkle":                      "permutation",
    "speck":                        "block_cipher",
    "speckey":                      "block_cipher",
    "speedy":                       "block_cipher",
    "spix":                         "permutation",
    "spoc":                         "permutation",
    "spook":                        "aead",
    "spring":                       "prng",
    "spritz":                       "stream_cipher",
    "square":                       "block_cipher",
    "subterranean 2.0":             "permutation",
    "sundae-gift":                  "aead",
    "sycon":                        "permutation",
    "tea":                          "block_cipher",
    "tangram":                      "block_cipher",
    "thank goodness it's friday (tgif)": "aead",
    "three-key triple des":         "block_cipher",
    "threeway":                     "block_cipher",
    "threefish":                    "block_cipher",
    "tinyjambu":                    "aead",
    "treyfer":                      "block_cipher",
    "triad":                        "stream_cipher",
    "trifle":                       "aead",
    "trivium":                      "stream_cipher",
    "twine":                        "block_cipher",
    "two-key triple des":           "block_cipher",
    "twofish":                      "block_cipher",
    "ublock":                       "block_cipher",
    "uea2 / zuc":                   "stream_cipher",
    "ulbc":                         "block_cipher",
    "vmpc":                         "stream_cipher",
    "wage":                         "aead",
    "wake":                         "stream_cipher",
    "xchacha":                      "stream_cipher",
    "xex-based families (xts lineage)": "mode",
    "xoodoo":                       "permutation",
    "xoodyak":                      "aead",
    "xtea":                         "block_cipher",
    "xxtea":                        "block_cipher",
    "xxtea / corrected block tea":  "block_cipher",
    "yamb":                         "stream_cipher",
    "yarará and coral":             "aead",
    "yarara and coral":             "aead",
    "3-way":                        "block_cipher",
    # Hash functions
    "fnv-1":                        "hash",
    "haval":                        "hash",
    "md2":                          "hash",
    "md4":                          "hash",
    "md5":                          "hash",
    "ripemd":                       "hash",
    "sha-1 / sha-2":                "hash",
    "tiger":                        "hash",
    "whirlpool":                    "hash",
}

# ─────────────────────────────────────────────────────────────────────────────
# NEW ENTRIES to add (not currently in checklist)
# Format: (status, scheme, primitive, type, year, url, section, pdf_stem)
#   pdf_stem: stem of file in references/ (without YYYY- prefix), or "" if none
# ─────────────────────────────────────────────────────────────────────────────
NEW_ENTRIES = [
    # ── From cryptospecs/symmetrical ────────────────────────────────────────
    ("[ ]", "ACHTERBAHN",               "ACHTERBAHN",           "stream_cipher",        "2005", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/achterbahn.pdf", "Full", "2005-achterbahn"),
    ("[ ]", "Blowfish",                 "Blowfish",             "block_cipher",         "1994", "https://www.schneier.com/academic/blowfish/", "TODO", "1994-blowfish"),
    ("[ ]", "Camellia",                 "Camellia",             "block_cipher",         "2001", "https://info.isl.ntt.co.jp/crypt/camellia/", "TODO", "2001-camellia"),
    ("[ ]", "CAST-128",                 "CAST-128",             "block_cipher",         "1996", "https://www.rfc-editor.org/rfc/rfc2144", "TODO", "1996-cast-128"),
    ("[ ]", "CAST-256",                 "CAST-256",             "block_cipher",         "1998", "https://www.rfc-editor.org/rfc/rfc2612", "TODO", "1998-cast-256"),
    ("[ ]", "DECIM",                    "DECIM",                "stream_cipher",        "2005", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/decim.pdf", "Full", "2005-decim"),
    ("[ ]", "FEAL-NX",                  "FEAL-NX",              "block_cipher",         "1997", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/fealnx.pdf", "Full", "1997-fealnx"),
    ("[ ]", "F-FCSR",                   "F-FCSR",               "stream_cipher",        "2005", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/ffcsr.pdf", "Full", "2005-ffcsr"),
    ("[ ]", "Grain",                    "Grain",                "stream_cipher",        "2005", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/grain.pdf", "Full", "2005-grain"),
    ("[ ]", "HC-256",                   "HC-256",               "stream_cipher",        "2004", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/hc256.pdf", "Full", "2004-hc256"),
    ("[ ]", "Lucifer",                  "Lucifer",              "block_cipher",         "1973", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/lucifer.pdf", "Full", "1973-lucifer"),
    ("[ ]", "MacGuffin",                "MacGuffin",            "block_cipher",         "1994", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/macguffin.pdf", "Full", "1994-macguffin"),
    ("[ ]", "MICKEY",                   "MICKEY",               "stream_cipher",        "2005", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/mickey.pdf", "Full", "2005-mickey"),
    ("[ ]", "MIR-1",                    "MIR-1",                "block_cipher",         "2002", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/mir1.pdf", "Full", "2002-mir1"),
    ("[ ]", "NewDES",                   "NewDES",               "block_cipher",         "1985", "https://en.wikipedia.org/wiki/NewDES", "TODO", ""),
    ("[ ]", "Rabbit",                   "Rabbit",               "stream_cipher",        "2003", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/rabbit.pdf", "Full", "2003-rabbit"),
    ("[ ]", "RC4-drop",                 "RC4-drop",             "stream_cipher",        "2007", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/rc4drop.pdf", "Full", "2007-rc4drop"),
    ("[ ]", "Sapphire",                 "Sapphire",             "stream_cipher",        "1995", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/sapphire.pdf", "Full", "1995-sapphire"),
    ("[ ]", "SEAL",                     "SEAL",                 "stream_cipher",        "1993", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/seal.pdf", "Full", "1993-seal"),
    ("[ ]", "SFINKS",                   "SFINKS",               "stream_cipher",        "2005", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/sfinks.pdf", "Full", "2005-sfinks"),
    ("[ ]", "3-Way",                    "3-Way",                "block_cipher",         "1991", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/threeway.pdf", "Full", "1991-threeway"),
    ("[ ]", "YAMB",                     "YAMB",                 "stream_cipher",        "2005", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/yamb.pdf", "Full", "2005-yamb"),
    # ── From cryptospecs/hash ───────────────────────────────────────────────
    ("[ ]", "FNV-1",                    "FNV-1",                "hash",                 "1991", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/hash/specs/fnv1.pdf", "Full", "1991-fnv1"),
    ("[ ]", "HAVAL",                    "HAVAL",                "hash",                 "1992", "https://raw.githubusercontent.com/stamparm/cryptospecs/master/hash/specs/haval.pdf", "Full", "1992-haval"),
    ("[ ]", "MD2",                      "MD2",                  "hash",                 "1992", "https://www.rfc-editor.org/rfc/rfc1319", "TODO", "1992-md2"),
    ("[ ]", "MD4",                      "MD4",                  "hash",                 "1990", "https://www.rfc-editor.org/rfc/rfc1320", "TODO", "1990-md4"),
    ("[ ]", "MD5",                      "MD5",                  "hash",                 "1992", "https://www.rfc-editor.org/rfc/rfc1321", "TODO", "1992-md5"),
    ("[ ]", "RIPEMD",                   "RIPEMD",               "hash",                 "1995", "https://homes.esat.kuleuven.be/~bosselae/ripemd160.html", "TODO", "1995-ripemd"),
    ("[ ]", "SHA-1 / SHA-2",            "SHA-1 / SHA-2",        "hash",                 "2002", "https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf", "TODO", "2002-sha1"),
    ("[ ]", "Tiger",                    "Tiger",                "hash",                 "1995", "https://www.cl.cam.ac.uk/~rja14/Papers/tiger.pdf", "TODO", "1995-tiger"),
    ("[ ]", "Whirlpool",                "Whirlpool",            "hash",                 "2003", "https://www.larc.usp.br/~pbarreto/whirlpool.zip", "TODO", "2003-whirlpool"),
    # ── NIST LWC Round 1 candidates not yet in checklist ────────────────────
    ("[ ]", "GIFT-COFB",                "GIFT",                 "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/GIFT-COFB-spec.pdf", "Full", "2019-gift_cofb"),
    ("[ ]", "Grain-128AEAD",            "Grain-128",            "aead",                 "2019", "https://csrc.nist.gov/projects/lightweight-cryptography", "TODO", ""),
    ("[ ]", "HERN & HERON",             "HERN & HERON",         "block_cipher",         "2019", "https://csrc.nist.gov/projects/lightweight-cryptography", "TODO", ""),
    ("[ ]", "PHOTON-Beetle",            "PHOTON",               "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/PHOTON-Beetle-spec.pdf", "Full", "2019-photon_beetle"),
    ("[ ]", "SIV-Rijndael256",          "Rijndael",             "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SIV-Rijndael256-spec.pdf", "Full", "2019-siv_rijndael256"),
    ("[ ]", "SIV-TEM-PHOTON",           "PHOTON",               "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SIV-TEM-PHOTON-spec.pdf", "Full", "2019-siv_tem_photon"),
    ("[ ]", "SKINNY-AEAD/SKINNY-HASH",  "SKINNY",               "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SKINNY-spec.pdf", "Full", "2019-skinny_aead"),
    ("[ ]", "SUNDAE-GIFT",              "GIFT",                 "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SUNDAE-GIFT-spec.pdf", "Full", "2019-sundae_gift"),
    ("[ ]", "Xoodyak",                  "Xoodoo",               "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Xoodyak-spec.pdf", "Full", "2019-xoodyak"),
    # Yarará and Coral is already in checklist as "Yarara and Coral"; NIST_LWC_UPDATES handles the spec backfill.
    ("[ ]", "Subterranean 2.0",         "Subterranean 2.0",     "permutation",          "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/subterranean-spec.pdf", "Full", "2019-subterranean_v2"),
    ("[ ]", "Shamash & Shamashash",     "Shamash & Shamashash", "hash",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ShamashAndShamashash-spec.pdf", "Full", "2019-shamash"),
    ("[ ]", "LOTUS-AEAD and LOCUS-AEAD", "LOTUS/LOCUS",        "aead",                 "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LOTUS-AEAD-and-LOCUS-AEAD-spec.pdf", "Full", "2019-lotus_locus"),
    ("[ ]", "GAGE and InGAGE",          "GAGE permutation",     "permutation",          "2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/GAGEandInGAGE-spec.pdf", "Full", "2019-gage_ingaege"),
]

# ─────────────────────────────────────────────────────────────────────────────
# TYPE overrides for existing entries where the scheme name may differ
# ─────────────────────────────────────────────────────────────────────────────
SCHEME_TYPE_OVERRIDE = {
    "ACE":                              "permutation",
    "ACHTERBAHN":                       "stream_cipher",
    "AES":                              "block_cipher",
    "Akelarre":                         "block_cipher",
    "ANT":                              "block_cipher",
    "Anubis":                           "block_cipher",
    "ARADI":                            "block_cipher",
    "ARIA":                             "block_cipher",
    "ASCON":                            "permutation",
    "Ballet":                           "block_cipher",
    "BEAR/LION":                        "construction",
    "BelT":                             "block_cipher",
    "BipBip":                           "tweakable_block_cipher",
    "Bleep64":                          "aead",
    "Blink":                            "block_cipher",
    "Blowfish":                         "block_cipher",
    "BMGL":                             "prng",
    "Camellia":                         "block_cipher",
    "CAST-128":                         "block_cipher",
    "CAST-256":                         "block_cipher",
    "ChaCha":                           "stream_cipher",
    "Chaskey":                          "mac",
    "ChiLow":                           "tweakable_block_cipher",
    "CiliPadi":                         "aead",
    "CIPHERUNICORN-A":                  "block_cipher",
    "CIPHERUNICORN-E":                  "block_cipher",
    "CLAE":                             "aead",
    "CLEFIA":                           "block_cipher",
    "CLX":                              "stream_cipher",
    "CMEA":                             "stream_cipher",
    "COMET":                            "aead",
    "CRISP":                            "block_cipher",
    "CRYPTON":                          "block_cipher",
    "CS-Cipher":                        "block_cipher",
    "DEAL":                             "block_cipher",
    "DECIM":                            "stream_cipher",
    "Deoxys":                           "tweakable_block_cipher",
    "DES":                              "block_cipher",
    "DESX":                             "block_cipher",
    "DFC":                              "block_cipher",
    "DryGASCON":                        "permutation",
    "E2":                               "block_cipher",
    "Elephant":                         "aead",
    "Enocoro-128v2":                    "stream_cipher",
    "ESTATE":                           "aead",
    "F-FCSR":                           "stream_cipher",
    "Fantomas / Robin":                 "block_cipher",
    "FEAL":                             "block_cipher",
    "FEAL-NX":                          "block_cipher",
    "FBC":                              "block_cipher",
    "FESH":                             "block_cipher",
    "FlexAEAD":                         "aead",
    "ForkAE":                           "aead",
    "Fountain":                         "aead",
    "FROG":                             "block_cipher",
    "GAGE and InGAGE":                  "permutation",
    "GIFT":                             "block_cipher",
    "GIFT-COFB":                        "aead",
    "Gimli":                            "permutation",
    "GOST 28147-89 (Magma)":            "block_cipher",
    "Grain":                            "stream_cipher",
    "Grain-128":                        "stream_cipher",
    "Grain-128AEAD":                    "aead",
    "Grand Cru":                        "block_cipher",
    "HC-256":                           "stream_cipher",
    "HERN & HERON":                     "block_cipher",
    "HIGHT":                            "block_cipher",
    "HPC":                              "block_cipher",
    "HyENA":                            "aead",
    "ICE":                              "block_cipher",
    "IDEA":                             "block_cipher",
    "ISAAC":                            "prng",
    "ISAP":                             "aead",
    "KASUMI":                           "block_cipher",
    "KATAN":                            "block_cipher",
    "KCipher-2":                        "stream_cipher",
    "Khazad":                           "block_cipher",
    "KLEIN":                            "block_cipher",
    "KNOT":                             "permutation",
    "KTANTAN":                          "block_cipher",
    "Kuznyechik":                       "block_cipher",
    "LAEM":                             "aead",
    "LEA":                              "block_cipher",
    "LEA-128":                          "block_cipher",
    "LED":                              "block_cipher",
    "LEVIATHAN":                        "stream_cipher",
    "LILI-128":                         "stream_cipher",
    "Lilliput-AE":                      "aead",
    "Limdolen":                         "aead",
    "LOCUS":                            "aead",
    "LOKI":                             "block_cipher",
    "LOKI97":                           "block_cipher",
    "LOTUS":                            "aead",
    "LOTUS-AEAD and LOCUS-AEAD":        "aead",
    "Lucifer":                          "block_cipher",
    "MacGuffin":                        "block_cipher",
    "MAGENTA":                          "block_cipher",
    "MANTIS":                           "tweakable_block_cipher",
    "MARS":                             "block_cipher",
    "MCRYPTON":                         "block_cipher",
    "MIBS":                             "block_cipher",
    "MICKEY":                           "stream_cipher",
    "MIDORI":                           "block_cipher",
    "MIR-1":                            "block_cipher",
    "MISTY1":                           "block_cipher",
    "mixFeed":                          "aead",
    "MMB":                              "block_cipher",
    "MSX":                              "block_cipher",
    "MUGI":                             "stream_cipher",
    "MULTI-S01":                        "stream_cipher",
    "MULTI2":                           "block_cipher",
    "NBC":                              "block_cipher",
    "NewDES":                           "block_cipher",
    "Nimbus":                           "block_cipher",
    "NOEKEON":                          "block_cipher",
    "NUSH":                             "stream_cipher",
    "ORANGE":                           "permutation",
    "Oribatida":                        "permutation",
    "ORYX":                             "stream_cipher",
    "PEA":                              "block_cipher",
    "PHOTON":                           "permutation",
    "PHOTON-Beetle":                    "aead",
    "PICARO":                           "block_cipher",
    "PRESENT":                          "block_cipher",
    "PRIDE":                            "block_cipher",
    "PRINCE":                           "block_cipher",
    "PRINCEv2":                         "block_cipher",
    "Pyjamask":                         "block_cipher",
    "Q":                                "block_cipher",
    "Qameleon":                         "aead",
    "QARMA":                            "tweakable_block_cipher",
    "QARMAv2":                          "tweakable_block_cipher",
    "Quartet":                          "aead",
    "Raindrop":                         "block_cipher",
    "Rabbit":                           "stream_cipher",
    "RC2":                              "block_cipher",
    "RC4":                              "stream_cipher",
    "RC4+":                             "stream_cipher",
    "RC4A":                             "stream_cipher",
    "RC4-drop":                         "stream_cipher",
    "RC5":                              "block_cipher",
    "RC6":                              "block_cipher",
    "REMUS":                            "aead",
    "Rijndael":                         "block_cipher",
    "Romulus":                          "aead",
    "SAEAES":                           "aead",
    "SAFER":                            "block_cipher",
    "SAFER+":                           "block_cipher",
    "SAFER++":                          "block_cipher",
    "SALSA":                            "stream_cipher",
    "Sapphire":                         "stream_cipher",
    "Saturnin":                         "block_cipher",
    "SC2000":                           "block_cipher",
    "SCARF":                            "tweakable_block_cipher",
    "SEAL":                             "stream_cipher",
    "SEED":                             "block_cipher",
    "Serpent":                          "block_cipher",
    "SFINKS":                           "stream_cipher",
    "SHACAL":                           "block_cipher",
    "SHACAL2":                          "block_cipher",
    "Shamash & Shamashash":             "hash",
    "SHARK":                            "block_cipher",
    "SIMON":                            "block_cipher",
    "SIMPLE":                           "aead",
    "SIV-Rijndael256":                  "aead",
    "SIV-TEM-PHOTON":                   "aead",
    "SKINNY":                           "tweakable_block_cipher",
    "SKINNY-AEAD/SKINNY-HASH":          "aead",
    "SKIPJACK":                         "block_cipher",
    "SM4":                              "block_cipher",
    "SMBA":                             "block_cipher",
    "SNEIK":                            "permutation",
    "SNOW":                             "stream_cipher",
    "SNOW 2.0":                         "stream_cipher",
    "SNOW 3G":                          "stream_cipher",
    "SOBER-t16":                        "stream_cipher",
    "SOBER-t32":                        "stream_cipher",
    "SOSEMANUK1":                       "stream_cipher",
    "SPARKLE":                          "permutation",
    "SPECK":                            "block_cipher",
    "SPECKEY":                          "block_cipher",
    "SPEEDY":                           "block_cipher",
    "SPIX":                             "permutation",
    "SpoC":                             "permutation",
    "Spook":                            "aead",
    "SPRING":                           "prng",
    "Spritz":                           "stream_cipher",
    "SQUARE":                           "block_cipher",
    "Subterranean 2.0":                 "permutation",
    "SUNDAE-GIFT":                      "aead",
    "Sycon":                            "permutation",
    "TEA":                              "block_cipher",
    "TANGRAM":                          "block_cipher",
    "Thank Goodness It's Friday (TGIF)": "aead",
    "Three-key Triple DES":             "block_cipher",
    "3-Way":                            "block_cipher",
    "Threefish":                        "block_cipher",
    "TinyJambu":                        "aead",
    "TREYFER":                          "block_cipher",
    "Triad":                            "stream_cipher",
    "TRIFLE":                           "aead",
    "Trivium":                          "stream_cipher",
    "TWINE":                            "block_cipher",
    "Two-key Triple DES":               "block_cipher",
    "Twofish":                          "block_cipher",
    "uBlock":                           "block_cipher",
    "UEA2 / ZUC":                       "stream_cipher",
    "uLBC":                             "block_cipher",
    "VMPC":                             "stream_cipher",
    "WAGE":                             "aead",
    "WAKE":                             "stream_cipher",
    "XChaCha":                          "stream_cipher",
    "XEX-based families (XTS lineage)": "mode",
    "Xoodoo":                           "permutation",
    "Xoodyak":                          "aead",
    "XTEA":                             "block_cipher",
    "XXTEA":                            "block_cipher",
    "XXTEA / Corrected Block TEA":      "block_cipher",
    "YAMB":                             "stream_cipher",
    "Yarará and Coral":                 "aead",
    "Yarara and Coral":             "aead",
    "Yarará and Coral":             "aead",
    "FNV-1":                            "hash",
    "HAVAL":                            "hash",
    "MD2":                              "hash",
    "MD4":                              "hash",
    "MD5":                              "hash",
    "RIPEMD":                           "hash",
    "SHA-1 / SHA-2":                    "hash",
    "Tiger":                            "hash",
    "Whirlpool":                        "hash",
}


# ─────────────────────────────────────────────────────────────────────────────
# NIST LWC spec updates for entries already in the checklist as [ ] / TODO
# Maps scheme name -> (year, url, section, pdf_stem)
# ─────────────────────────────────────────────────────────────────────────────
NIST_LWC_UPDATES = {
    "ACE":              ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ace-spec.pdf",                  "Full", "2019-ace"),
    "Bleep64":          ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Bleep64-spec.pdf",              "Full", "2019-bleep64"),
    "CiliPadi":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/CiliPadi-spec.pdf",             "Full", "2019-cilipadi"),
    "CLAE":             ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/CLAE-spec.pdf",                 "Full", "2019-clae"),
    "CLX":              ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/CLX-spec.pdf",                  "Full", "2019-clx"),
    "COMET":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/COMET-spec.pdf",                "Full", "2019-comet"),
    "DryGASCON":        ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/DryGASCON-spec.pdf",            "Full", "2019-drygascon"),
    "Elephant":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Elephant-spec.pdf",             "Full", "2019-elephant"),
    "ESTATE":           ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ESTATE-spec.pdf",               "Full", "2019-estate"),
    "FlexAEAD":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/FlexAEAD-spec.pdf",             "Full", "2019-flexaead"),
    "ForkAE":           ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ForkAE-spec.pdf",               "Full", "2019-forkae"),
    "Fountain":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Fountain-spec.pdf",             "Full", "2019-fountain"),
    "Gimli":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Gimli-spec.pdf",                "Full", "2019-gimli"),
    "HyENA":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/HYENA-spec.pdf",                "Full", "2019-hyena"),
    "ISAP":             ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ISAP-spec.pdf",                 "Full", "2019-isap"),
    "KNOT":             ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/KNOT-spec.pdf",                 "Full", "2019-knot"),
    "LAEM":             ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LAEM-spec.pdf",                 "Full", "2019-laem"),
    "Lilliput-AE":      ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Lilliput-AE-spec.pdf",          "Full", "2019-lilliput_ae"),
    "Limdolen":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Limdolen-spec.pdf",             "Full", "2019-limdolen"),
    "LOCUS":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LOTUS-AEAD-and-LOCUS-AEAD-spec.pdf", "Full", "2019-lotus_locus"),
    "LOTUS":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LOTUS-AEAD-and-LOCUS-AEAD-spec.pdf", "Full", "2019-lotus_locus"),
    "mixFeed":          ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/mixFeed-spec.pdf",              "Full", "2019-mixfeed"),
    "ORANGE":           ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ORANGE-spec.pdf",               "Full", "2019-orange"),
    "Oribatida":        ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Oribatida-spec.pdf",            "Full", "2019-oribatida"),
    "PHOTON":           ("2021", "https://csrc.nist.gov/projects/lightweight-cryptography",                                                                       "TODO", ""),
    "Pyjamask":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Pyjamask-spec.pdf",             "Full", "2019-pyjamask"),
    "Qameleon":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Qameleon-spec.pdf",             "Full", "2019-qameleon"),
    "Quartet":          ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Quartet-spec.pdf",              "Full", "2019-quartet"),
    "REMUS":            ("2019", "https://eprint.iacr.org/2019/992",                                                                                               "Full", ""),
    "Romulus":          ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Romulus-spec.pdf",              "Full", "2019-romulus"),
    "SAEAES":           ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SAEAES-spec.pdf",               "Full", "2019-saeaes"),
    "Saturnin":         ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Saturnin-spec.pdf",             "Full", "2019-saturnin"),
    "SIMPLE":           ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SIMPLE-spec.pdf",               "Full", "2019-simple"),
    "SNEIK":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SNEIK-spec.pdf",                "Full", "2019-sneik"),
    "SPARKLE":          ("2020", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SPARKLE-spec.pdf",              "Full", "2019-sparkle"),
    "SPIX":             ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SPIX-spec.pdf",                 "Full", "2019-spix"),
    "SpoC":             ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SpoC-spec.pdf",                 "Full", "2019-spoc"),
    "Spook":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Spook-spec.pdf",                "Full", "2019-spook"),
    "Sycon":            ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Sycon-spec.pdf",                "Full", "2019-sycon"),
    "TinyJambu":        ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/TinyJAMBU-spec.pdf",            "Full", "2019-tinyjambu"),
    "TRIFLE":           ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/TRIFLE-spec.pdf",               "Full", "2019-trifle"),
    "WAGE":             ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/WAGE-spec.pdf",                 "Full", "2019-wage"),
    "Xoodoo":           ("2018", "https://keccak.team/xoodoo.html",                                                                                               "TODO", ""),
    "Grain-128":        ("2019", "https://csrc.nist.gov/projects/lightweight-cryptography",                                                                       "TODO", ""),
    "Shamash & Shamashash": ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ShamashAndShamashash-spec.pdf", "Full", "2019-shamash"),
    "Subterranean 2.0": ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/subterranean-spec.pdf",          "Full", "2019-subterranean_v2"),
    "Yarara and Coral": ("2019", "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Yarara_and_Coral-spec.pdf",       "Full", "2019-yarara_coral"),
}


def pdf_exists(stem: str) -> bool:
    if not stem:
        return False
    return any(f.stem == stem for f in REFS.iterdir() if f.is_file())


def parse_existing_entries(lines: list[str]) -> list[dict]:
    """Parse existing table rows from the Alphabetical List section.
    Handles both old format (7 cols: status|scheme|primitive|year|url|section|pdf)
    and new format (8 cols: status|scheme|primitive|type|year|url|section|pdf).
    """
    entries = []
    in_table = False
    for line in lines:
        line = line.rstrip()
        if line.startswith("## Alphabetical List"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            in_table = False
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p != ""]  # strip empty first/last
        if len(parts) < 2 or parts[0] in ("status", "---"):
            continue
        if len(parts) >= 8:
            # New format: status | scheme | primitive | type | year | url | section | pdf
            entries.append({
                "status":    parts[0],
                "scheme":    parts[1],
                "primitive": parts[2],
                # skip parts[3] = existing type; we'll recalculate
                "year":      parts[4],
                "url":       parts[5],
                "section":   parts[6],
                "pdf":       parts[7],
            })
        elif len(parts) == 7:
            # Old format: status | scheme | primitive | year | url | section | pdf
            entries.append({
                "status":    parts[0],
                "scheme":    parts[1],
                "primitive": parts[2],
                "year":      parts[3],
                "url":       parts[4],
                "section":   parts[5],
                "pdf":       parts[6],
            })
        elif len(parts) == 5:
            # malformed row (e.g., CRISP with missing columns)
            entries.append({
                "status":    parts[0],
                "scheme":    parts[1],
                "primitive": parts[2],
                "year":      parts[3],
                "url":       parts[4],
                "section":   "TODO",
                "pdf":       "no",
            })
    return entries


def normalize_scheme(name: str) -> str:
    """Lowercase + strip for comparison."""
    return name.lower().strip()


def get_type(scheme: str) -> str:
    t = SCHEME_TYPE_OVERRIDE.get(scheme)
    if t:
        return t
    return TYPE_MAP.get(normalize_scheme(scheme), "block_cipher")


def build_entry_row(status, scheme, primitive, typ, year, url, section, pdf_flag) -> str:
    return f"| {status} | {scheme} | {primitive} | {typ} | {year} | {url} | {section} | {pdf_flag} |"


def main():
    text = CHECKLIST.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find section boundaries
    alph_start = next(i for i, l in enumerate(lines) if l.startswith("## Alphabetical List"))
    # Find the Modes section or end of file
    modes_start = next(
        (i for i in range(alph_start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines)
    )

    header_lines = lines[:alph_start + 1]
    footer_lines = lines[modes_start:]

    # Parse existing entries
    existing = parse_existing_entries(lines)
    existing_schemes = {normalize_scheme(e["scheme"]) for e in existing}

    # Determine which new entries to add
    new_to_add = []
    for ne in NEW_ENTRIES:
        status, scheme, primitive, typ, year, url, section, pdf_stem = ne
        if normalize_scheme(scheme) not in existing_schemes:
            new_to_add.append({
                "status":    status,
                "scheme":    scheme,
                "primitive": primitive,
                "year":      year,
                "url":       url,
                "section":   section,
                "pdf":       "yes" if pdf_exists(pdf_stem) else "no",
            })

    # Combine all entries
    all_entries = existing + new_to_add

    # Sort alphabetically by scheme
    def sort_key(e):
        s = e["scheme"].lower().strip()
        # Put numbers at end
        return (s[0].isdigit(), s)

    all_entries.sort(key=sort_key)

    # Build new table
    table_lines = [
        "",
        "| status | scheme | underlying primitive name | type | spec_year | spec_url | spec_section_or_page | pdf_available_in_repo |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for e in all_entries:
        scheme = e["scheme"]
        status = e["status"]
        primitive = e["primitive"]
        typ = get_type(scheme)
        year = e["year"]
        url = e["url"]
        section = e["section"]
        pdf_flag = e["pdf"]

        # Apply NIST LWC updates for entries with TODO fields
        if scheme in NIST_LWC_UPDATES and (year == "TODO" or url == "TODO"):
            nist_year, nist_url, nist_section, nist_stem = NIST_LWC_UPDATES[scheme]
            year = nist_year
            url = nist_url
            section = nist_section
            if pdf_exists(nist_stem):
                pdf_flag = "yes"
        elif scheme in NIST_LWC_UPDATES:
            # Already has real fields but may need pdf update
            _, _, _, nist_stem = NIST_LWC_UPDATES[scheme]
            if pdf_exists(nist_stem):
                pdf_flag = "yes"

        # Also try by constructing a stem from the year + scheme name
        if pdf_flag == "no" and year != "TODO":
            stem_guess = str(year) + "-" + normalize_scheme(scheme).replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace("'", "").replace(".", "").replace("&", "")
            if pdf_exists(stem_guess):
                pdf_flag = "yes"

        row = build_entry_row(status, scheme, primitive, typ, year, url, section, pdf_flag)
        table_lines.append(row)

    # Reassemble the file
    new_lines = (
        header_lines
        + table_lines
        + [""]
        + footer_lines
    )
    CHECKLIST.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"Updated checklist: {len(all_entries)} total entries ({len(new_to_add)} new added)")


if __name__ == "__main__":
    main()
