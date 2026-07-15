#!/usr/bin/env python3
"""Test: every family in families.yaml has a corresponding local file in references/.

Some families were never matched to a downloaded PDF (paywalled papers, dead
links, competition submissions we never fetched). Those are tracked in
KNOWN_MISSING below so CI stays green while the gap remains visible and
machine-checked in both directions:
  - a family NOT in KNOWN_MISSING must resolve to a local file (catches
    regressions and newly-added families that forgot to ship a reference PDF).
  - a family listed in KNOWN_MISSING must still actually be unresolved (keeps
    the exception list pruned as PDFs get added).

Regenerate the current unresolved set with: python scripts/reference_pdfs.py
"""
from __future__ import annotations

from reference_pdfs import build_family_pdf_map

KNOWN_MISSING = {
    "abacus", "aes", "aes_cbc", "aes_ctr", "aes_gcm", "aria", "arirang", "aurora", "blender",
    "blue_midnight_wish", "boole", "catfish", "cheetah", "chi_hash", "clefia",
    "cmea", "crunch", "crypton", "cubehash", "dch", "deal", "dynamic_sha",
    "dynamic_sha2", "echo_hash", "ecoh", "edon_r", "enrupt", "essence",
    "fantomas_robin", "fsb", "fugue", "hamsi", "hmac_sha256", "hpc",
    "khichidi_1",
    "labyrinth", "lane", "lea_iso", "lesamnta", "luffa", "lux_hash",
    "m3lcrypt", "mcrypton", "mcssha3", "md6", "meshhash", "mibs", "mmb",
    "msx", "multi2", "nasha", "newdes", "oryx", "panama", "pbkdf2", "pea", "picaro",
    "pufferfish", "rc4plus", "sandstorm", "sarmal", "sgail", "shabal",
    "shamata", "shavite3", "simd_hash", "siphash", "spectral_hash",
    "streamhash", "swifftx", "tangle_hash", "tib3", "twister_hash",
    "ulbc", "vmpc", "vortex_hash", "wake", "wamm", "waterfall_hash",
    "xchacha", "xoodoo", "zuc",
}


def main() -> None:
    fam_map = build_family_pdf_map()
    unresolved = {fid for fid, paths in fam_map.items() if not paths}

    errors: list[str] = []

    unexpected = unresolved - KNOWN_MISSING
    for fid in sorted(unexpected):
        errors.append(f"family '{fid}' has no local reference file in references/"
                       " and is not in KNOWN_MISSING")

    stale = KNOWN_MISSING - unresolved
    for fid in sorted(stale):
        errors.append(f"family '{fid}' is listed in KNOWN_MISSING but now resolves"
                       " to a local file — remove it from the exception list")

    unknown_ids = KNOWN_MISSING - set(fam_map)
    for fid in sorted(unknown_ids):
        errors.append(f"KNOWN_MISSING references '{fid}', which is not a family id")

    if errors:
        print(f"REFERENCE PDF COVERAGE ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        raise SystemExit(1)

    print(f"Reference PDF coverage OK — checked {len(fam_map)} families, "
          f"{len(KNOWN_MISSING)} tracked as known-missing.")


if __name__ == "__main__":
    main()
