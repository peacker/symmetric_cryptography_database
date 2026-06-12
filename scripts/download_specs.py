#!/usr/bin/env python3
"""
download_specs.py

Downloads spec PDFs from:
  1. stamparm/cryptospecs GitHub repo (symmetrical + hash)
  2. NIST Lightweight Cryptography Round 1 spec-doc folder

Saves PDFs to references/ with year-prefixed filenames.
Prints a summary of successes and failures.
"""

import os
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

REFS_DIR = Path(__file__).parent.parent / "references"
BASE_NIST = "https://csrc.nist.gov/CSRC/media/Projects/Lightweight-Cryptography/documents/round-1/spec-doc"
BASE_CRYPTO = "https://raw.githubusercontent.com/stamparm/cryptospecs/master"

# ─────────────────────────────────────────────────────────────────────────────
# CRYPTOSPECS: symmetrical
# Format: (remote_filename, local_filename_without_extension, year)
# Skip files we already have in references/ (checked by local_filename prefix).
# ─────────────────────────────────────────────────────────────────────────────
CRYPTO_SYMM = [
    # (remote_path_under_symmetrical/specs, local_stem, year)
    ("achterbahn.pdf", "achterbahn",   2005),
    ("blowfish.pdf",   "blowfish",     1994),
    ("camellia.pdf",   "camellia",     2001),
    ("cast-128.pdf",   "cast-128",     1996),
    ("cast-256.pdf",   "cast-256",     1998),
    ("decim.pdf",      "decim",        2005),
    ("dfc.pdf",        "dfc",          1998),
    ("e2.pdf",         "e2",           1998),
    ("fealnx.pdf",     "fealnx",       1997),
    ("ffcsr.pdf",      "ffcsr",        2005),
    ("frog.pdf",       "frog",         1998),
    ("grain.pdf",      "grain",        2005),
    ("hc256.pdf",      "hc256",        2004),
    ("idea.pdf",       "idea",         1991),
    ("loki97.pdf",     "loki97",       1998),
    ("lucifer.pdf",    "lucifer",      1973),
    ("macguffin.pdf",  "macguffin",    1994),
    ("magenta.pdf",    "magenta",      1998),
    ("mars.pdf",       "mars",         1999),
    ("mickey.pdf",     "mickey",       2005),
    ("mir1.pdf",       "mir1",         2002),
    ("rabbit.pdf",     "rabbit",       2003),
    ("rc4drop.pdf",    "rc4drop",      2007),
    ("rc5.pdf",        "rc5",          1994),
    ("rc6.pdf",        "rc6",          1998),
    ("rijndael.pdf",   "rijndael",     1998),
    ("safer+.pdf",     "safer-plus",   1998),
    ("safer-K128.pdf", "safer-k128",   1994),
    ("safer-K64.pdf",  "safer-k64",    1993),
    ("sapphire.pdf",   "sapphire",     1995),
    ("seal.pdf",       "seal",         1993),
    ("seed.pdf",       "seed",         1998),
    ("sfinks.pdf",     "sfinks",       2005),
    ("tea.pdf",        "tea",          1994),
    ("threeway.pdf",   "threeway",     1991),
    ("twofish.pdf",    "twofish",      1998),
    ("yamb.pdf",       "yamb",         2005),
]

# ─────────────────────────────────────────────────────────────────────────────
# CRYPTOSPECS: hash
# ─────────────────────────────────────────────────────────────────────────────
CRYPTO_HASH = [
    ("fnv1.pdf",       "fnv1",         1991),
    ("haval.pdf",      "haval",        1992),
    ("md2.pdf",        "md2",          1992),
    ("md4.pdf",        "md4",          1990),
    ("md5.pdf",        "md5",          1992),
    ("ripemd.pdf",     "ripemd",       1995),
    ("sha.pdf",        "sha1",         2002),
    ("tiger.pdf",      "tiger",        1995),
    ("whirlpool.pdf",  "whirlpool",    2003),
]

# ─────────────────────────────────────────────────────────────────────────────
# NIST LWC Round 1 spec-doc filenames (56 candidates; TGIF and TRIAD already
# downloaded).  Format: (spec_doc_filename, local_stem, year)
# URL will be: BASE_NIST/{spec_doc_filename}
# ─────────────────────────────────────────────────────────────────────────────
NIST_LWC = [
    ("ace-spec.pdf",                    "ace",              2019),
    ("ascon-spec.pdf",                  "ascon_lwc",        2019),
    ("Bleep64-spec.pdf",                "bleep64",          2019),
    ("CiliPadi-spec.pdf",               "cilipadi",         2019),
    ("CLAE-spec.pdf",                   "clae",             2019),
    ("CLX-spec.pdf",                    "clx",              2019),
    ("COMET-spec.pdf",                  "comet",            2019),
    ("DryGASCON-spec.pdf",              "drygascon",        2019),
    ("Elephant-spec.pdf",               "elephant",         2019),
    ("ESTATE-spec.pdf",                 "estate",           2019),
    ("FlexAEAD-spec.pdf",               "flexaead",         2019),
    ("ForkAE-spec.pdf",                 "forkae",           2019),
    ("Fountain-spec.pdf",               "fountain",         2019),
    ("GAGE_InGAGE-spec.pdf",            "gage_ingaege",     2019),
    ("GIFT-COFB-spec.pdf",              "gift_cofb",        2019),
    ("Gimli-spec.pdf",                  "gimli",            2019),
    ("Grain128AEAD-spec.pdf",           "grain128aead",     2019),
    ("HERN_HERON-spec.pdf",             "hern_heron",       2019),
    ("HYENA-spec.pdf",                  "hyena",            2019),
    ("ISAP-spec.pdf",                   "isap",             2019),
    ("KNOT-spec.pdf",                   "knot",             2019),
    ("LAEM-spec.pdf",                   "laem",             2019),
    ("Lilliput-AE-spec.pdf",            "lilliput_ae",      2019),
    ("Limdolen-spec.pdf",               "limdolen",         2019),
    ("LOTUS-LOCUS-spec.pdf",            "lotus_locus",      2019),
    ("mixFeed-spec.pdf",                "mixfeed",          2019),
    ("ORANGE-spec.pdf",                 "orange",           2019),
    ("Oribatida-spec.pdf",              "oribatida",        2019),
    ("PHOTON-Beetle-spec.pdf",          "photon_beetle",    2019),
    ("Pyjamask-spec.pdf",               "pyjamask",         2019),
    ("Qameleon-spec.pdf",               "qameleon",         2019),
    ("Quartet-spec.pdf",                "quartet",          2019),
    ("REMUS-spec.pdf",                  "remus",            2019),
    ("Romulus-spec.pdf",                "romulus",          2019),
    ("SAEAES-spec.pdf",                 "saeaes",           2019),
    ("Saturnin-spec.pdf",               "saturnin",         2019),
    ("Shamash-Shamashash-spec.pdf",     "shamash",          2019),
    ("SIMPLE-spec.pdf",                 "simple",           2019),
    ("SIV-Rijndael256-spec.pdf",        "siv_rijndael256",  2019),
    ("SIV-TEM-PHOTON-spec.pdf",         "siv_tem_photon",   2019),
    ("SKINNY-AEAD-spec.pdf",            "skinny_aead",      2019),
    ("SNEIK-spec.pdf",                  "sneik",            2019),
    ("SPARKLE-spec.pdf",                "sparkle",          2019),
    ("SPIX-spec.pdf",                   "spix",             2019),
    ("SpoC-spec.pdf",                   "spoc",             2019),
    ("Spook-spec.pdf",                  "spook",            2019),
    ("Subterranean-v2-spec.pdf",        "subterranean_v2",  2019),
    ("SUNDAE-GIFT-spec.pdf",            "sundae_gift",      2019),
    ("Sycon-spec.pdf",                  "sycon",            2019),
    ("TinyJAMBU-spec.pdf",              "tinyjambu",        2019),
    ("TRIFLE-spec.pdf",                 "trifle",           2019),
    ("WAGE-spec.pdf",                   "wage",             2019),
    ("Xoodyak-spec.pdf",                "xoodyak",          2019),
    ("Yarara-Coral-spec.pdf",           "yarara_coral",     2019),
]


def existing_stems(refs_dir: Path) -> set:
    stems = set()
    for f in refs_dir.iterdir():
        if f.is_file():
            # strip year prefix "YYYY-"
            name = f.stem
            if len(name) > 5 and name[4] == "-":
                name = name[5:]
            stems.add(name.lower())
    return stems


def download(url: str, dest: Path, label: str) -> bool:
    if dest.exists():
        print(f"  [skip] already exists: {dest.name}")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        # Verify it's a PDF (or at least has content)
        if len(data) < 100:
            print(f"  [fail] too small ({len(data)}B): {label}")
            return False
        dest.write_bytes(data)
        print(f"  [ok]   {dest.name}  ({len(data)//1024}kB)")
        return True
    except urllib.error.HTTPError as e:
        print(f"  [http] {e.code}: {label}  <- {url}")
        return False
    except Exception as e:
        print(f"  [err] {label}: {e}")
        return False


def try_nist_variants(stem: str, primary: str, year: int, refs_dir: Path) -> tuple[bool, str]:
    """Try primary filename, then common case variations."""
    candidates = [primary]
    # also try lowercase and uppercase
    candidates += [primary.lower(), primary.upper()]
    for fn in dict.fromkeys(candidates):  # dedup preserving order
        url = f"{BASE_NIST}/{fn}"
        dest = refs_dir / f"{year}-{stem}.pdf"
        if download(url, dest, f"NIST:{stem}"):
            return True, fn
    return False, primary


def main():
    REFS_DIR.mkdir(exist_ok=True)
    successes, failures = [], []

    # ── Cryptospecs symmetrical ──────────────────────────────────────────────
    print("\n=== cryptospecs/symmetrical ===")
    for remote, stem, year in CRYPTO_SYMM:
        url = f"{BASE_CRYPTO}/symmetrical/specs/{remote}"
        dest = REFS_DIR / f"{year}-{stem}.pdf"
        ok = download(url, dest, f"sym:{stem}")
        (successes if ok else failures).append(f"sym:{stem}")
        time.sleep(0.1)

    # ── Cryptospecs hash ─────────────────────────────────────────────────────
    print("\n=== cryptospecs/hash ===")
    for remote, stem, year in CRYPTO_HASH:
        url = f"{BASE_CRYPTO}/hash/specs/{remote}"
        dest = REFS_DIR / f"{year}-{stem}.pdf"
        ok = download(url, dest, f"hash:{stem}")
        (successes if ok else failures).append(f"hash:{stem}")
        time.sleep(0.1)

    # ── NIST LWC Round 1 ─────────────────────────────────────────────────────
    print("\n=== NIST LWC Round 1 ===")
    for spec_fn, stem, year in NIST_LWC:
        dest = REFS_DIR / f"{year}-{stem}.pdf"
        if dest.exists():
            print(f"  [skip] already exists: {dest.name}")
            successes.append(f"nist:{stem}")
            continue
        ok, used = try_nist_variants(stem, spec_fn, year, REFS_DIR)
        (successes if ok else failures).append(f"nist:{stem}")
        time.sleep(0.2)

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Downloaded / already present : {len(successes)}")
    print(f"Failed                        : {len(failures)}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(f"  {f}")


if __name__ == "__main__":
    main()
