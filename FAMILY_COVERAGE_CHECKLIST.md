# Symmetric Primitive Family Coverage Checklist

This is a planning list of known symmetric primitive/cipher families.

- `[x]` means the family is already present in the database.
- `[ ]` means it is not in the database yet.

## Alphabetical List

| status | scheme | underlying primitive name | type | spec_year | spec_url | spec_section_or_page | pdf_available_in_repo |
|---|---|---|---|---|---|---|---|
| [x] | ACE | ACE permutation | permutation | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ace-spec.pdf | Full | yes |
| [x] | ACHTERBAHN | ACHTERBAHN | stream_cipher | 2005 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/achterbahn.pdf | Full | yes |
| [x] | AES | AES | block_cipher | 2001 | https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.197-upd1.pdf | Full | no |
| [x] | Akelarre | Akelarre | block_cipher | 1996 | https://sacworkshop.org/proc/SAC_96_002.pdf | PDF Page 3-16 | yes |
| [x] | ANT | ANT | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000338 | Full | yes |
| [x] | Anubis | Anubis | block_cipher | 2000 | https://garykessler.net/library/crypto/Anubis.pdf | Full | yes |
| [x] | ARADI | ARADI | block_cipher | 2024 | https://eprint.iacr.org/2024/1240 | TODO | yes |
| [x] | ARIA | ARIA | block_cipher | 2010 | https://www.rfc-editor.org/rfc/rfc5794 | TODO | no |
| [x] | ASCON | ASCON permutation | permutation | 2016 | https://ascon.isec.tugraz.at/files/asconv12.pdf | Full | yes |
| [x] | Ballet | Ballet | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000335 | Full | yes |
| [x] | BEAR/LION | BEAR/LION | construction | 1996 | https://www.cl.cam.ac.uk/archive/rja14/Papers/bear-lion.pdf | Full | yes |
| [ ] | BelT | BelT | block_cipher | TODO | TODO | TODO | no |
| [x] | BipBip | BipBip | tweakable_block_cipher | 2023 | https://tches.iacr.org/index.php/TCHES/article/view/9955/9458 | TODO | no |
| [ ] | Bleep64 | Bleep64 | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Bleep64-spec.pdf | Full | yes |
| [x] | Blink | Blink | block_cipher | 2025 | https://eprint.iacr.org/2025/1314 | TODO | yes |
| [x] | Blowfish | Blowfish | block_cipher | 1994 | https://www.schneier.com/academic/blowfish/ | TODO | yes |
| [x] | BMGL | BMGL | prng | 2000 | https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.37.8270&rep=rep1&type=pdf | Full | yes |
| [x] | Camellia | Camellia | block_cipher | 2004 | https://www.rfc-editor.org/rfc/rfc3713 | TODO | no |
| [x] | CAST-128 | CAST-128 | block_cipher | 1997 | https://www.rfc-editor.org/rfc/rfc2144 | TODO | no |
| [x] | CAST-256 | CAST-256 | block_cipher | 1999 | https://www.rfc-editor.org/rfc/rfc2612 | TODO | no |
| [x] | ChaCha | ChaCha | stream_cipher | 2008 | https://cr.yp.to/chacha.html | TODO | no |
| [x] | Chaskey | Chaskey | mac | 2014 | https://eprint.iacr.org/2014/386 | Full | yes |
| [x] | ChiLow | ChiLow | tweakable_block_cipher | 2025 | https://eprint.iacr.org/2025/308 | TODO | yes |
| [ ] | CiliPadi | CiliPadi | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/CiliPadi-spec.pdf | Full | yes |
| [ ] | CIPHERUNICORN-A | CIPHERUNICORN-A | block_cipher | TODO | TODO | TODO | no |
| [ ] | CIPHERUNICORN-E | CIPHERUNICORN-E | block_cipher | TODO | TODO | TODO | no |
| [ ] | CLAE | CLAE | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/CLAE-spec.pdf | Full | yes |
| [x] | CLEFIA | CLEFIA | block_cipher | 2011 | https://www.rfc-editor.org/rfc/rfc6114 | TODO | no |
| [x] | CLX | CLX | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/CLX-spec.pdf | Full | yes |
| [ ] | CMEA | CMEA | stream_cipher | TODO | TODO | TODO | no |
| [ ] | COMET | COMET | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/COMET-spec.pdf | Full | yes |
| [x] | CRISP | CRISP | 1996 | block_cipher | https://sacworkshop.org/proc/SAC_96_002.pdf | PDF Page 17-31 | yes |
| [x] | CRYPTON | CRYPTON | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | no |
| [ ] | CryptMT3 | CryptMT3 | stream_cipher | 2004 | https://link.springer.com/chapter/10.1007/978-3-540-68351-3_2 | Full | yes |
| [x] | CS-Cipher | CS-Cipher | block_cipher | TODO | TODO | TODO | yes |
| [x] | DEAL | DEAL | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | no |
| [x] | DECIM | DECIM | stream_cipher | 2005 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/decim.pdf | Full | yes |
| [ ] | Deoxys | Deoxys | tweakable_block_cipher | TODO | TODO | TODO | no |
| [x] | DES | DES | block_cipher | 1977 | https://csrc.nist.gov/pubs/fips/46/final | TODO | no |
| [x] | DESX | DESX | block_cipher | 1996 | https://doi.org/10.1007/3-540-68697-5_9 | Full | yes |
| [x] | DFC | DFC | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | yes |
| [ ] | Dragon | Dragon | stream_cipher | 2004 | https://link.springer.com/chapter/10.1007/978-3-540-68351-3_3 | Full | yes |
| [x] | DryGASCON | GASCON permutation | permutation | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | E2 | E2 | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | yes |
| [x] | Elephant | Elephant | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [ ] | Enocoro-128v2 | Enocoro-128v2 | stream_cipher | TODO | TODO | TODO | no |
| [ ] | ESTATE | ESTATE | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ESTATE-spec.pdf | Full | yes |
| [x] | F-FCSR | F-FCSR | stream_cipher | 2005 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/ffcsr.pdf | Full | yes |
| [ ] | Fantomas / Robin | Fantomas / Robin | block_cipher | TODO | TODO | TODO | no |
| [x] | FBC | FBC | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000340 | Full | yes |
| [x] | FEAL | FEAL | block_cipher | 1987 | https://info.isl.ntt.co.jp/crypt/eng/archive/index.html | Full | yes |
| [x] | FEAL-NX | FEAL-NX | block_cipher | 1997 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/fealnx.pdf | Full | yes |
| [x] | FESH | FESH | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000336 | Full | yes |
| [ ] | FlexAEAD | FlexAEAD | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/FlexAEAD-spec.pdf | Full | yes |
| [x] | FNV-1 | FNV-1 | hash | 1991 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/hash/specs/fnv1.pdf | Full | yes |
| [ ] | ForkAE | ForkAE | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ForkAE-spec.pdf | Full | yes |
| [ ] | Fountain | Fountain | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Fountain-spec.pdf | Full | yes |
| [x] | FROG | FROG | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | yes |
| [ ] | GAGE and InGAGE | GAGE and InGAGE | permutation | TODO | TODO | TODO | no |
| [x] | GIFT | GIFT | block_cipher | 2017 | https://iacr.org/archive/ches2017/105290001/105290001.pdf | TODO | no |
| [ ] | GIFT-COFB | GIFT | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/GIFT-COFB-spec.pdf | Full | yes |
| [x] | Gimli | Gimli | permutation | 2017 | https://gimli.cr.yp.to/ | TODO | yes |
| [x] | GOST 28147-89 (Magma) | Magma | block_cipher | 1989 | https://datatracker.ietf.org/doc/html/rfc5830 | Full | yes |
| [x] | Grain | Grain | stream_cipher | 2005 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/grain.pdf | Full | yes |
| [x] | Grain-128 | Grain-128 | stream_cipher | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | no |
| [ ] | Grain-128AEAD | Grain-128 | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | no |
| [ ] | Grand Cru | Grand Cru | block_cipher | TODO | TODO | TODO | no |
| [x] | HAVAL | HAVAL | hash | 1992 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/hash/specs/haval.pdf | Full | yes |
| [ ] | HC-128 | HC-128 | stream_cipher | 2004 | https://link.springer.com/chapter/10.1007/978-3-540-68351-3_4 | Full | yes |
| [x] | HC-256 | HC-256 | stream_cipher | 2004 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/hc256.pdf | Full | yes |
| [ ] | HERN & HERON | HERN & HERON | block_cipher | TODO | TODO | TODO | no |
| [ ] | HIGHT | HIGHT | block_cipher | TODO | TODO | TODO | no |
| [x] | HPC | HPC | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | no |
| [ ] | HyENA | HyENA | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/HYENA-spec.pdf | Full | yes |
| [x] | ICE | ICE | block_cipher | 1997 | https://doi.org/10.1007/BFb0052346 | Full | yes |
| [x] | IDEA | IDEA | block_cipher | 1991 | https://doi.org/10.1007/3-540-46877-3_35 | TODO | yes |
| [x] | ISAAC | ISAAC | prng | 1997 | https://link.springer.com/chapter/10.1007/3-540-60865-6_41 | Full | yes |
| [x] | ISAP | ISAP | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [ ] | LEX | LEX | stream_cipher | 2004 | https://link.springer.com/chapter/10.1007/978-3-540-68351-3_4 | Full | yes |
| [x] | KASUMI | KASUMI | block_cipher | 2001 | https://www.3gpp.org/ftp/Specs/archive/35_series/35.202/ | TODO | no |
| [x] | KATAN | KATAN | block_cipher | 2009 | https://www.iacr.org/archive/ches2009/57470001/57470001.pdf | TODO | yes |
| [ ] | KCipher-2 | KCipher-2 | stream_cipher | TODO | TODO | TODO | no |
| [x] | Khazad | Khazad | block_cipher | TODO | TODO | TODO | yes |
| [ ] | KLEIN | KLEIN | block_cipher | TODO | TODO | TODO | no |
| [x] | KNOT | KNOT | permutation | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | KTANTAN | KTANTAN | block_cipher | 2009 | https://www.iacr.org/archive/ches2009/57470001/57470001.pdf | TODO | no |
| [ ] | Kuznyechik | Kuznyechik | block_cipher | TODO | TODO | TODO | no |
| [ ] | LAEM | LAEM | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LAEM-spec.pdf | Full | yes |
| [ ] | LEA | LEA | block_cipher | TODO | TODO | TODO | no |
| [ ] | LEA-128 | LEA | block_cipher | TODO | TODO | TODO | no |
| [x] | LED | LED | block_cipher | 2011 | https://www.iacr.org/archive/ches2011/69170327/69170327.pdf | TODO | yes |
| [x] | LEVIATHAN | LEVIATHAN | stream_cipher | TODO | TODO | TODO | yes |
| [x] | LILI-128 | LILI-128 | stream_cipher | TODO | TODO | TODO | yes |
| [ ] | Lilliput-AE | Lilliput-AE | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Lilliput-AE-spec.pdf | Full | yes |
| [ ] | Limdolen | Limdolen | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Limdolen-spec.pdf | Full | yes |
| [ ] | LOCUS | LOCUS | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LOTUS-AEAD-and-LOCUS-AEAD-spec.pdf | Full | yes |
| [ ] | LOKI | LOKI | block_cipher | TODO | TODO | TODO | no |
| [x] | LOKI97 | LOKI97 | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | yes |
| [ ] | LOTUS | LOTUS | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LOTUS-AEAD-and-LOCUS-AEAD-spec.pdf | Full | yes |
| [ ] | LOTUS-AEAD and LOCUS-AEAD | LOTUS/LOCUS | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/LOTUS-AEAD-and-LOCUS-AEAD-spec.pdf | Full | yes |
| [x] | Lucifer | Lucifer | block_cipher | 1973 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/lucifer.pdf | Full | yes |
| [x] | MacGuffin | MacGuffin | block_cipher | 1994 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/macguffin.pdf | Full | yes |
| [x] | MAGENTA | MAGENTA | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | yes |
| [ ] | MANTIS | MANTIS | tweakable_block_cipher | TODO | TODO | TODO | no |
| [x] | MARS | MARS | block_cipher | 1999 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | yes |
| [ ] | MCRYPTON | MCRYPTON | block_cipher | TODO | TODO | TODO | no |
| [x] | MD2 | MD2 | hash | 1992 | https://www.rfc-editor.org/rfc/rfc1319 | Full | yes |
| [x] | MD4 | MD4 | hash | 1990 | https://www.rfc-editor.org/rfc/rfc1320 | Full | yes |
| [x] | MD5 | MD5 | hash | 1992 | https://www.rfc-editor.org/rfc/rfc1321 | Full | yes |
| [ ] | MIBS | MIBS | block_cipher | TODO | TODO | TODO | no |
| [x] | MICKEY | MICKEY | stream_cipher | 2005 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/mickey.pdf | Full | yes |
| [ ] | MIDORI | MIDORI | block_cipher | TODO | TODO | TODO | no |
| [x] | MIR-1 | MIR-1 | stream_cipher | 2002 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/mir1.pdf | Full | yes |
| [x] | MISTY1 | MISTY1 | block_cipher | TODO | TODO | TODO | yes |
| [ ] | mixFeed | mixFeed | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/mixFeed-spec.pdf | Full | yes |
| [ ] | MMB | MMB | block_cipher | TODO | TODO | TODO | no |
| [x] | MSX | MSX | block_cipher | 2026 | https://cic.iacr.org/p/2/4/32 | TODO | no |
| [ ] | MUGI | MUGI | stream_cipher | TODO | TODO | TODO | no |
| [ ] | MULTI-S01 | MULTI-S01 | stream_cipher | TODO | TODO | TODO | no |
| [ ] | MULTI2 | MULTI2 | block_cipher | TODO | TODO | TODO | no |
| [x] | NBC | NBC | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000339 | Full | yes |
| [ ] | NewDES | NewDES | block_cipher | 1985 | https://en.wikipedia.org/wiki/NewDES | TODO | no |
| [x] | Nimbus | Nimbus | block_cipher | TODO | TODO | TODO | yes |
| [ ] | NLSv2 | NLSv2 | stream_cipher | 2004 | https://link.springer.com/chapter/10.1007/978-3-540-68351-3_6 | Full | yes |
| [x] | NOEKEON | NOEKEON | block_cipher | TODO | TODO | TODO | yes |
| [x] | NUSH | NUSH | stream_cipher | TODO | TODO | TODO | yes |
| [ ] | ORANGE | ORANGE | permutation | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ORANGE-spec.pdf | Full | yes |
| [ ] | Oribatida | Oribatida | permutation | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Oribatida-spec.pdf | Full | yes |
| [ ] | ORYX | ORYX | stream_cipher | TODO | TODO | TODO | no |
| [ ] | PEA | PEA | block_cipher | TODO | TODO | TODO | no |
| [x] | PHOTON | PHOTON | permutation | 2021 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | no |
| [ ] | PHOTON-Beetle | PHOTON | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/PHOTON-Beetle-spec.pdf | Full | yes |
| [ ] | PICARO | PICARO | block_cipher | TODO | TODO | TODO | no |
| [x] | PRESENT | PRESENT | block_cipher | 2007 | https://iacr.org/archive/ches2007/47270450/47270450.pdf | TODO | yes |
| [ ] | PRIDE | PRIDE | block_cipher | TODO | TODO | TODO | no |
| [x] | PRINCE | PRINCE | block_cipher | 2012 | https://www.iacr.org/archive/asiacrypt2012/76580403/76580403.pdf | TODO | no |
| [ ] | PRINCEv2 | PRINCEv2 | block_cipher | TODO | TODO | TODO | no |
| [x] | Pyjamask | Pyjamask | block_cipher | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | Q | Q | block_cipher | 2000 | https://web.archive.org/web/20070205001927/http://www.cosic.esat.kuleuven.ac.be/nessie/ | Full | yes |
| [x] | Qameleon | Qameleon | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | QARMA | QARMA | tweakable_block_cipher | 2016 | https://eprint.iacr.org/2016/444 | TODO | yes |
| [x] | QARMAv2 | QARMAv2 | tweakable_block_cipher | 2023 | https://eprint.iacr.org/2023/929 | TODO | yes |
| [ ] | Quartet | Quartet | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Quartet-spec.pdf | Full | yes |
| [x] | Rabbit | Rabbit | stream_cipher | 2003 | https://link.springer.com/chapter/10.1007/978-3-540-68351-3_7 | Full | yes |
| [x] | Raindrop | Raindrop | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000342 | Full | yes |
| [x] | RC2 | RC2 | block_cipher | 1998 | https://datatracker.ietf.org/doc/html/rfc2268 | Full | yes |
| [x] | RC4 | RC4 | stream_cipher | 1987 | https://en.wikipedia.org/wiki/RC4 | TODO | no |
| [x] | RC4+ | RC4+ | stream_cipher | 1987 | https://en.wikipedia.org/wiki/RC4 | TODO | no |
| [ ] | RC4-drop | RC4-drop | stream_cipher | 2007 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/rc4drop.pdf | Full | yes |
| [x] | RC4A | RC4A | stream_cipher | 2007 | https://eprint.iacr.org/2007/070 | Full | yes |
| [x] | RC5 | RC5 | block_cipher | 1996 | https://www.rfc-editor.org/rfc/rfc2040 | TODO | no |
| [x] | RC6 | RC6 | block_cipher | 1998 | https://www.cerias.purdue.edu/apps/reports_and_papers/view/2029 | TODO | yes |
| [x] | REMUS | REMUS | aead | 2019 | https://eprint.iacr.org/2019/992 | Full | yes |
| [x] | Rijndael | Rijndael | block_cipher | 1998 | https://csrc.nist.gov/projects/aes | TODO | yes |
| [x] | RIPEMD | RIPEMD | hash | 1995 | https://homes.esat.kuleuven.be/~bosselae/ripemd160.html | Full | yes |
| [x] | Romulus | Romulus | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [ ] | SAEAES | SAEAES | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SAEAES-spec.pdf | Full | yes |
| [x] | SAFER | SAFER | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | no |
| [x] | SAFER+ | SAFER+ | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | no |
| [x] | SAFER++ | SAFER++ | block_cipher | 1998 | https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines/aes-development | TODO | no |
| [x] | Salsa20 | Salsa20 | stream_cipher | 2004 | https://cr.yp.to/snuffle.html | Full | no |
| [x] | Sapphire | Sapphire | stream_cipher | 1995 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/sapphire.pdf | Full | yes |
| [x] | Saturnin | Saturnin | block_cipher | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | SC2000 | SC2000 | block_cipher | TODO | TODO | TODO | yes |
| [x] | SCARF | SCARF | tweakable_block_cipher | 2023 | https://www.usenix.org/system/files/usenixsecurity23-canale.pdf | TODO | yes |
| [x] | SEAL | SEAL | stream_cipher | 1993 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/seal.pdf | Full | yes |
| [x] | SEED | SEED | block_cipher | 2005 | https://www.rfc-editor.org/rfc/rfc4269 | TODO | no |
| [x] | Serpent | Serpent | block_cipher | 1998 | https://www.cl.cam.ac.uk/archive/rja14/Papers/serpent.pdf | TODO | yes |
| [x] | SFINKS | SFINKS | stream_cipher | 2005 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/sfinks.pdf | Full | yes |
| [x] | SHA-1 / SHA-2 | SHA-1 / SHA-2 | hash | 2002 | https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf | Full | yes |
| [x] | SHACAL | SHACAL | block_cipher | 2000 | https://en.wikipedia.org/wiki/SHACAL | Full | yes |
| [x] | SHACAL2 | SHACAL2 | block_cipher | 2001 | https://en.wikipedia.org/wiki/SHACAL | Full | yes |
| [x] | Shamash & Shamashash | Shamash & Shamashash | aead+hash | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/ShamashAndShamashash-spec.pdf | Full | yes |
| [x] | SHARK | SHARK | block_cipher | 1996 | https://doi.org/10.1007/3-540-68697-5_11 | Full | yes |
| [x] | SIMON | SIMON | block_cipher | 2013 | https://eprint.iacr.org/2013/404 | TODO | no |
| [x] | SIMPLE | SIMPLE | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [ ] | SIV-Rijndael256 | Rijndael | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SIV-Rijndael256-spec.pdf | Full | yes |
| [ ] | SIV-TEM-PHOTON | PHOTON | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SIV-TEM-PHOTON-spec.pdf | Full | yes |
| [x] | SKINNY | SKINNY | tweakable_block_cipher | 2016 | https://doi.org/10.1007/978-3-662-53008-5_5 | TODO | no |
| [ ] | SKINNY-AEAD/SKINNY-HASH | SKINNY | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SKINNY-spec.pdf | Full | yes |
| [x] | SKIPJACK | SKIPJACK | block_cipher | 1998 | https://nvlpubs.nist.gov/nistpubs/Legacy/FIPS/fipspub185.pdf | Full | yes |
| [x] | SM4 | SM4 | block_cipher | 2021 | https://www.rfc-editor.org/rfc/rfc8998 | TODO | yes |
| [x] | SMBA | SMBA | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000341 | Full | yes |
| [x] | SNEIK | SNEIK | permutation | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | SNOW | SNOW | stream_cipher | 2001 | https://web.archive.org/web/20201017161826/http://www.madchat.fr/crypto/hash-lib-algo/snow/snow10.pdf | Full | yes |
| [x] | SNOW 2.0 | SNOW 2.0 | stream_cipher | 2002 | https://link.springer.com/chapter/10.1007/3-540-36563-X_24 | Full | yes |
| [x] | SNOW 3G | SNOW 3G | stream_cipher | 2006 | https://web.archive.org/web/20200822072535/https://www.gsma.com/aboutus/wp-content/uploads/2014/12/snow3gspec.pdf | Full | yes |
| [x] | SOBER-t16 | SOBER-t16 | stream_cipher | 2000 | https://web.archive.org/web/20110812013604/https://www.cosic.esat.kuleuven.be/nessie/workshop/submissions/sober-t16.zip | Full | yes |
| [x] | SOBER-t32 | SOBER-t32 | stream_cipher | 2000 | https://web.archive.org/web/20110812013604/https://www.cosic.esat.kuleuven.be/nessie/workshop/submissions/sober-t32.zip | Full | yes |
| [x] | SOSEMANUK1 | SOSEMANUK1 | stream_cipher | 2005 | https://web.archive.org/web/20120414020956/http://www.ecrypt.eu.org/stream/sosemanukpf.html | Full | yes |
| [x] | SPARKLE | SPARKLE | permutation | 2020 | https://sparkle-lwc.github.io/ | TODO | yes |
| [x] | SPECK | SPECK | block_cipher | 2013 | https://eprint.iacr.org/2013/404 | Full | yes |
| [x] | SPECKEY | SPECKEY | block_cipher | 2016 | https://eprint.iacr.org/2016/984 | Full | yes |
| [x] | SPEEDY | SPEEDY | block_cipher | 2021 | https://doi.org/10.46586/tches.v2021.i4.510-545 | Full | yes |
| [x] | SPIX | SPIX | permutation | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | SpoC | SpoC | permutation | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | Spook | Spook | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | SPRING | SPRING | prng | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000343 | Full | yes |
| [x] | Spritz | Spritz | stream_cipher | 2014 | https://people.csail.mit.edu/rivest/pubs/RS14.pdf | Full | yes |
| [x] | SQUARE | SQUARE | block_cipher | 1997 | https://link.springer.com/chapter/10.1007/BFb0052343 | Full | yes |
| [x] | Subterranean | Subterranean permutation | permutation | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/subterranean-spec.pdf | Full | yes |
| [ ] | Subterranean 2.0 | Subterranean 2.0 | permutation | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/subterranean-spec.pdf | Full | yes |
| [ ] | SUNDAE-GIFT | GIFT | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/SUNDAE-GIFT-spec.pdf | Full | yes |
| [x] | Sycon | Sycon | permutation | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | TANGRAM | TANGRAM | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000337 | Full | yes |
| [x] | TEA | TEA | block_cipher | 1994 | https://doi.org/10.1007/3-540-60590-8_29 | TODO | yes |
| [x] | Thank Goodness It's Friday (TGIF) | Thank Goodness It's Friday (TGIF) | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/TGIF-spec.pdf | Full | yes |
| [ ] | Three-key Triple DES | DES | block_cipher | TODO | TODO | TODO | no |
| [x] | Threefish | Threefish | block_cipher | 2010 | https://www.schneier.com/wp-content/uploads/2015/01/skein.pdf | Full | yes |
| [x] | Tiger | Tiger | hash | 1995 | https://www.cl.cam.ac.uk/~rja14/Papers/tiger.pdf | Full | yes |
| [x] | TinyJambu | TinyJambu | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | TREYFER | TREYFER | block_cipher | 2008 | https://users.encs.concordia.ca/~youssef/Publications/Papers/A%20Related-Key%20Attack%20on%20TREYFER.pdf | Full | yes |
| [x] | Triad | Triad | stream_cipher | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/TRIAD-spec.pdf | Full | yes |
| [x] | TRIFLE | TRIFLE | aead | 2019 | https://csrc.nist.gov/projects/lightweight-cryptography | TODO | yes |
| [x] | Trivium | Trivium | stream_cipher | 2006 | https://web.archive.org/web/20180828163734/http://www.ecrypt.eu.org/stream/p3ciphers/trivium/trivium_p3.pdf | Full | yes |
| [x] | TWINE | TWINE | block_cipher | 2012 | https://doi.org/10.1007/978-3-642-34047-5_13 | TODO | no |
| [ ] | Two-key Triple DES | DES | block_cipher | TODO | TODO | TODO | no |
| [x] | Twofish | Twofish | block_cipher | 1998 | https://www.schneier.com/academic/twofish/ | TODO | yes |
| [x] | uBlock | uBlock | block_cipher | 2019 | http://www.jcr.cacrnet.org.cn/EN/10.13868/j.cnki.jcr.000334 | Full | yes |
| [ ] | UEA2 / ZUC | ZUC | stream_cipher | TODO | TODO | TODO | no |
| [x] | uLBC | uLBC | block_cipher | 2025 | https://cic.iacr.org/p/1/4/25 | TODO | no |
| [ ] | VMPC | VMPC | stream_cipher | TODO | TODO | TODO | no |
| [ ] | WAGE | WAGE | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/WAGE-spec.pdf | Full | yes |
| [ ] | WAKE | WAKE | stream_cipher | TODO | TODO | TODO | no |
| [x] | Whirlpool | Whirlpool | hash | 2003 | https://www.larc.usp.br/~pbarreto/whirlpool.zip | Full | yes |
| [x] | XChaCha | ChaCha | stream_cipher | TODO | TODO | TODO | no |
| [ ] | XEX-based families (XTS lineage) | AES | mode | TODO | TODO | TODO | no |
| [x] | Xoodoo | Xoodoo | permutation | 2018 | https://keccak.team/xoodoo.html | TODO | no |
| [ ] | Xoodyak | Xoodoo | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Xoodyak-spec.pdf | Full | yes |
| [x] | XTEA | XTEA | block_cipher | 1997 | https://www.cix.co.uk/~klockstone/xtea.pdf | TODO | yes |
| [x] | XXTEA | XXTEA | block_cipher | 1998 | https://www.cix.co.uk/~klockstone/xxtea.pdf | Full | yes |
| [x] | XXTEA / Corrected Block TEA | XXTEA | block_cipher | 1998 | https://www.cix.co.uk/~klockstone/xxtea.pdf | Full | yes |
| [x] | YAMB | YAMB | stream_cipher | 2005 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/yamb.pdf | Full | yes |
| [ ] | Yarara and Coral | Yarara and Coral | aead | 2019 | https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc/Yarara_and_Coral-spec.pdf | Full | yes |
| [x] | 3-Way | 3-Way | block_cipher | 1991 | https://raw.githubusercontent.com/stamparm/cryptospecs/master/symmetrical/specs/threeway.pdf | Full | yes |

## Modes of Operation Coverage Checklist

This section tracks modes of operation built on symmetric primitives.

| status | mode | mode_type | spec_year | spec_url | underlying_primitives | pdf_available_in_repo |
|---|---|---|---|---|---|---|
| [x] | BMGL | PRNG | 2000 | https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.37.8270&rep=rep1&type=pdf | Rijndael | yes |
| [x] | CBC (Cipher Block Chaining) | ENC | 1976 | NIST SP 800-38A | AES/Rijndael | no |
| [x] | ChaCha20-Poly1305 | AEAD | 2008 | RFC 7539 | ChaCha20, Poly1305 | no |
| [x] | CTR (Counter Mode) | ENC | 2001 | NIST SP 800-38A | AES/Rijndael | no |
| [x] | GCM (Galois/Counter Mode) | AEAD | 2005 | NIST SP 800-38D | AES/Rijndael | no |
| [x] | HMAC-SHA256 | MAC | 1997 | RFC 2104 | SHA-256 | no |
| [x] | PBKDF2 | PBKDF | 2000 | RFC 2898 | HMAC-SHA256 | no |

## Notes

- This list is intentionally broad and includes both classic and modern families.
- Some entries are umbrella labels (for planning) and may be split into separate canonical families during ingestion.
- Keep this file sorted alphabetically when adding/removing entries.
