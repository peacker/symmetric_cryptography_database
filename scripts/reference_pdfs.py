#!/usr/bin/env python3
"""Resolve data/references.yaml entries and families.yaml families to local files
under references/.

Two ways a reference resolves to a local file:
  1. An explicit "Local copy: references/<file>." note in references.yaml.
  2. A filename in references/ that starts with the reference's year and whose
     slug shares enough tokens with the reference title / family name.

Used by scripts/test_reference_coverage.py and by the influence-mining workflow
to find which local file(s) to read for a given family.
"""
from __future__ import annotations

import re
from pathlib import Path

from common import ROOT, all_families, load_all_data

REFERENCES_DIR = ROOT / "references"

LOCAL_COPY_RE = re.compile(r"(references/[^\s.,;'\"]+\.[A-Za-z0-9]+)")

STOPWORDS = {
    "the", "a", "an", "of", "and", "for", "on", "in", "to", "new", "algorithm",
    "algorithms", "cipher", "ciphers", "block", "stream", "hash", "function",
    "functions", "family", "specification", "specifications", "spec", "design",
    "report", "reports", "status", "paper", "v1", "v2", "v3", "et", "al",
    "competition", "candidate", "candidates", "cryptographic", "cryptography",
    "classification", "proposal", "submission", "documentation", "supporting",
    "round", "first", "second", "third", "part", "posts", "entries", "nist",
    "primitive", "primitives", "analysis", "attack", "attacks", "security",
    "efficient", "software", "hardware", "fast", "oriented", "version",
}


def slug_tokens(text: str) -> set[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return {t for t in text.split() if t and t not in STOPWORDS}


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def strip_year_prefix(compact_stem: str) -> str:
    return re.sub(r"^(19|20)\d{2}", "", compact_stem)


def strip_version_suffix(compact_stem: str) -> str:
    return re.sub(r"v\d+(?:\d)*$", "", compact_stem)


def raw_tokens(stem: str) -> set[str]:
    """Split a filename stem on non-alnum, dropping a leading 4-digit year.
    Used to recognize names listed as their own word in multi-cipher
    filenames (e.g. "...-[kalyna,mukhomor,ade,labirinth,rsb].pdf"), which a
    single compacted blob would otherwise merge into one unrecognizable run.
    """
    parts = re.split(r"[^a-z0-9]+", stem.lower())
    parts = [p for p in parts if p]
    if parts and re.fullmatch(r"(19|20)\d{2}", parts[0]):
        parts = parts[1:]
    return set(parts)


def local_files() -> list[Path]:
    return sorted(p for p in REFERENCES_DIR.iterdir() if p.is_file() and p.suffix.lower() in {".pdf", ".txt"})


def explicit_local_copies(references: list[dict]) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {}
    for ref in references:
        notes = ref.get("notes") or ""
        matches = LOCAL_COPY_RE.findall(notes)
        paths = []
        for m in matches:
            p = ROOT / m
            if p.exists():
                paths.append(p)
        if paths:
            result[ref["id"]] = paths
    return result


def fuzzy_match(ref: dict, family_names: list[str], files: list[Path]) -> list[Path]:
    # Pass 1: compact substring match against family id/name (e.g. "hc_256" /
    # "HC-256" both reduce to "hc256", matching filename stem "2004-hc256").
    id_compacts = {compact(n) for n in family_names if compact(n)}
    direct: list[Path] = []
    for f in files:
        stem_compact = strip_year_prefix(compact(f.stem))
        if not stem_compact:
            continue
        tokens = raw_tokens(f.stem)
        for c in id_compacts:
            # A name listed as its own word works regardless of length (handles
            # both short ids and multi-cipher filenames like
            # "...-[kalyna,mukhomor,ade,labirinth,rsb].pdf" where each bracketed
            # name is comma-separated, i.e. its own token).
            if c in tokens:
                direct.append(f)
                break
            # Short ids (e.g. "q", "rig", "chi") additionally require an exact
            # *whole-stem* match to avoid false substring hits ("rig" inside
            # "original", "chi" inside "kuznyechik") that a prefix check alone
            # wouldn't catch.
            if len(c) <= 3:
                if stem_compact == c or strip_version_suffix(stem_compact) == c:
                    direct.append(f)
                    break
                continue
            # Longer ids: filenames follow a "{year}-{primary_name}[-suffix]"
            # convention, so the cipher name always starts right after the year
            # prefix — require a prefix match rather than "appears anywhere",
            # otherwise names that happen to be English-word fragments of
            # another word give false positives (e.g. "tangle" inside
            # "rectangle").
            if stem_compact.startswith(c):
                direct.append(f)
                break
    if direct:
        return direct

    # Pass 2: title-token overlap, generous year window, since references.yaml
    # "year" is the publication year of a specific document (e.g. an RFC or
    # later analysis) which can postdate the original design PDF on disk.
    year = ref.get("year")
    title_tokens = {t for t in slug_tokens(ref.get("title", "")) if len(t) >= 4}
    if not title_tokens:
        return []

    candidates = []
    for f in files:
        m = re.match(r"(\d{4})-", f.name)
        if m and year:
            file_year = int(m.group(1))
            if abs(file_year - year) > 4:
                continue
        stem_compact = strip_year_prefix(compact(f.stem))
        matched = [t for t in title_tokens if t in stem_compact]
        overlap = len(matched)
        if overlap >= 2 or (overlap == 1 and len(matched[0]) >= 7):
            candidates.append((overlap, f))
    candidates.sort(key=lambda t: -t[0])
    return [f for score, f in candidates if score == candidates[0][0]] if candidates else []


def build_family_pdf_map() -> dict[str, list[Path]]:
    """Return family_id -> sorted list of resolved local file Paths (may be empty)."""
    data = load_all_data(["primitive_families", "mode_families", "references"])
    families = all_families(data)
    references = {r["id"]: r for r in data["references"]["references"]}
    files = local_files()

    explicit = explicit_local_copies(list(references.values()))

    result: dict[str, list[Path]] = {}
    for family in families:
        fid = family["id"]
        family_names = [family["name"], fid.replace("_", " ")]
        resolved: dict[str, Path] = {}
        for ref_id in family.get("reference_ids", []):
            ref = references.get(ref_id)
            if ref is None:
                continue
            paths = explicit.get(ref_id)
            if not paths:
                paths = fuzzy_match(ref, family_names, files)
            for p in paths:
                resolved[str(p)] = p
        result[fid] = sorted(resolved.values(), key=lambda p: p.name)
    return result


def main() -> None:
    fam_map = build_family_pdf_map()
    missing = {fid: paths for fid, paths in fam_map.items() if not paths}
    print(f"Families: {len(fam_map)}, unresolved: {len(missing)}")
    for fid in sorted(missing):
        print(f"  NO LOCAL FILE: {fid}")


if __name__ == "__main__":
    main()
