#!/usr/bin/env python3
"""Resolve data/*_families.yaml families to local files under references/.

references/ filenames follow one fixed, deterministic format:

    [YYYY][name1,name2,...][doctype][notes].ext

  - YYYY: the document's own year.
  - names: one or more identifiers, joined by "," when a single document
    covers more than one entry (e.g. a combined paper, a multi-cipher
    competition submission, or a primitive shared across tiers). Each name
    is ideally this database's own family id, so a family resolves to its
    backing document(s) by *exact* match -- no fuzzy/substring guessing.
    When a document doesn't belong to any single family (a general survey,
    a construction-level paper, RFC text not tied to one family, ...) the
    names field instead holds a short descriptive slug.
    "," was picked over "+" specifically because some family *names* (not
    ids) legitimately contain a literal "+" (e.g. SAFER+, RC4+) -- a "+"
    separator would be ambiguous for anyone reading/writing the names field
    from a cipher's display name rather than its id. No existing family id
    or name contains a comma, colon, or square bracket, so those remain
    safe as the separator and the field delimiters respectively.
  - doctype: optional (e.g. "rfc", "fips", "patent", "nist_sp", "spec",
    "presentation") -- empty ("[]") when it's just an ordinary paper.
  - notes: optional free-text disambiguation (a version tag, which of two
    same-year papers on the same design this is, a patent number, ...).
    Free text here is not split on any separator, so it may contain "+"
    (used historically as a hyphen stand-in) -- just avoid literal "[" or
    "]", which would break the filename's own field delimiters.

This replaces an earlier "YYYY-name[-suffix].ext" convention that relied on
fuzzy filename matching (prefix/substring heuristics) to guess which family
a file belonged to -- which was a real source of bugs (e.g. "loki" silently
resolving to "loki97.pdf", a later and unrelated cipher, because the old
matcher only checked whether one compacted string was a prefix of another).
Every filename here is instead parsed structurally, so resolution is exact.

Used by scripts/test_reference_pdf_coverage.py and by scripts/build_static_site.py
(to build the family_id -> local PDF map baked into the site for the
"Open PDF" viewer), and by the influence-mining workflow to find which local
file(s) to read for a given family.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import ROOT, all_families, load_all_data

REFERENCES_DIR = ROOT / "references"

FILENAME_RE = re.compile(r"^\[(\d{4})\]\[([^\]]*)\]\[([^\]]*)\]\[([^\]]*)\]$")


def parse_filename(path: Path) -> dict | None:
    """Parse a references/ filename into its year/names/doctype/notes fields,
    or None if it doesn't match the [YYYY][names][doctype][notes] format
    (e.g. a file dropped in ahead of being renamed/triaged)."""
    m = FILENAME_RE.match(path.stem)
    if not m:
        return None
    year, names, doctype, notes = m.groups()
    return {
        "year": int(year),
        "names": [n for n in names.split(",") if n],
        "doctype": doctype,
        "notes": notes,
        "path": path,
    }


def local_files() -> list[Path]:
    return sorted(p for p in REFERENCES_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".txt"})


def unparsed_files() -> list[Path]:
    """Files in references/ that don't match the naming convention at all --
    surfaced separately from "no family matched" so a typo'd/legacy filename
    doesn't silently look the same as a file that's correctly named but
    genuinely not tied to any family (a survey paper, say)."""
    return [f for f in local_files() if parse_filename(f) is None]


def build_family_pdf_map() -> dict[str, list[Path]]:
    """Return family_id -> sorted list of resolved local file Paths (may be
    empty) for *every* family in primitive_families.yaml/mode_families.yaml
    -- not just the ones some file's names field happens to mention, so an
    unresolved family shows up as an empty list rather than a missing key.

    A file resolves to every family id listed in its own names field,
    exactly -- e.g. "[1990][md4,md4_hash][][].pdf" resolves for both the
    md4 and md4_hash families.
    """
    by_name: dict[str, list[Path]] = {}
    for f in local_files():
        parsed = parse_filename(f)
        if not parsed:
            continue
        for name in parsed["names"]:
            by_name.setdefault(name, []).append(f)

    data = load_all_data(["primitive_families", "mode_families"])
    family_ids = [f["id"] for f in all_families(data)]
    return {
        fid: sorted(by_name.get(fid, []), key=lambda p: p.name)
        for fid in family_ids
    }


def main() -> None:
    fam_map = build_family_pdf_map()
    missing = {fid: paths for fid, paths in fam_map.items() if not paths}
    unparsed = unparsed_files()
    print(f"Families: {len(fam_map)}, unresolved: {len(missing)}, unparsed filenames: {len(unparsed)}")
    for fid in sorted(missing):
        print(f"  NO LOCAL FILE: {fid}")
    for f in unparsed:
        print(f"  UNPARSED FILENAME: {f.name}")


if __name__ == "__main__":
    main()
