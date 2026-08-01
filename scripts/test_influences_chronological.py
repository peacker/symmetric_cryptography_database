#!/usr/bin/env python3
"""Test: an influence's source family is never dated later than the family
it influenced.

Family year is the earliest reference year (see common.family_year, same
value shown in the genealogy visualization). If either family's year is
unknown, the edge is skipped rather than failed — there's nothing to check.
Equal years are allowed (contemporaneous designs, e.g. joint standardization).
"""
from __future__ import annotations

from common import all_families, family_year, load_all_data

# (target_family_id, source_family_id) pairs that are chronologically "late"
# by our year<-earliest-reference proxy but are not data bugs — each is a
# real, checked historical nuance rather than a backwards/misattributed edge.
# Keep this pruned: if a future reference fix makes an entry here resolve
# correctly, remove it (mirrors the KNOWN_MISSING pattern in
# test_reference_pdf_coverage.py).
KNOWN_EXCEPTIONS = {
    # SHARK (1996) credits "the CAST design procedure" for its subkey
    # generation. That general technique was presented at SAC 1994/1995,
    # predating SHARK, but our only cast128 reference is the CAST-128-specific
    # RFC 2144 (1997); no precisely-citable earlier paper was found to add.
    ("shark", "cast128"),
    # SEAL's family year (1993) reflects SEAL 1.0; SHA-1 (1995) was adopted
    # specifically in the later SEAL 2.0/3.0 revisions, not the original.
    # SEAL isn't split into versioned families the way e.g. Subterranean is.
    ("seal", "sha1_sha2"),
    # TwoCats (PHC 2014) credits Catena; Catena's own PHC-2014 round-1
    # submission predates TwoCats, but our only catena reference is its
    # later v5 (2015) spec — the original submission PDF wasn't locatable.
    ("twocats", "catena"),
    # The hmac_sha256 family's year (1997) is RFC 2104, which introduced HMAC
    # generically; this family bundles that generic construction with its
    # specific SHA-256 instantiation, which necessarily postdates SHA-256
    # (2001). The dependency is real (HMAC-SHA256 wraps SHA-256), just dated
    # by the generic-construction paper rather than a SHA-256-specific one.
    ("hmac_sha256", "sha2_hash"),
    # Rubato (EUROCRYPT 2022) explicitly reuses Pasta's Feistel S-box ("we use
    # building blocks from HERA and Pasta"). Pasta's own eprint (2021/731) was
    # public in June 2021, well before Rubato -- but our dobraunig_et_al_2023_pasta
    # reference is dated 2023 to match its final TCHES publication year (the
    # same final-venue-year convention used elsewhere in this database), which
    # makes the year-proxy check see it as later than Rubato.
    ("rubato", "pasta_pi"),
}


def main() -> None:
    data = load_all_data(["primitive_families", "mode_families", "references"])
    families = all_families(data)
    references_by_id = {r["id"]: r for r in data["references"]["references"]}

    families_by_id = {f["id"]: f for f in families}
    years = {fid: family_year(f, references_by_id) for fid, f in families_by_id.items()}

    errors: list[str] = []
    seen_exceptions: set[tuple[str, str]] = set()
    checked = 0
    for f in families:
        fid = f["id"]
        target_year = years.get(fid)
        for inf in f.get("influences", []):
            src = inf["source_family_id"]
            source_year = years.get(src)
            if target_year is None or source_year is None:
                continue
            checked += 1
            if source_year > target_year:
                if (fid, src) in KNOWN_EXCEPTIONS:
                    seen_exceptions.add((fid, src))
                    continue
                errors.append(
                    f"'{fid}' (year {target_year}) is listed as influenced by '{src}' "
                    f"(year {source_year}), which is later — likely the edge is on the "
                    f"wrong family or points the wrong direction"
                )

    stale = KNOWN_EXCEPTIONS - seen_exceptions
    for fid, src in sorted(stale):
        errors.append(
            f"KNOWN_EXCEPTIONS lists ('{fid}', '{src}') but that edge no longer "
            f"violates chronology — remove it from the exception list"
        )

    if errors:
        print(f"INFLUENCES CHRONOLOGY ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        raise SystemExit(1)

    print(f"Influences chronology OK — checked {checked} dated edges, "
          f"{len(KNOWN_EXCEPTIONS)} tracked as known exceptions.")


if __name__ == "__main__":
    main()
