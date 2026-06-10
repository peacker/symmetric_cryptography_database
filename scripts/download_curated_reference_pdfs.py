#!/usr/bin/env python3

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "references"


def slugify(name: str) -> str:
    s = name.lower().strip()
    s = s.replace("++", "pp")
    s = s.replace("+", "plus")
    s = s.replace("/", " ")
    s = s.replace("&", " and ")
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unknown"


def normalize_url(url: str) -> str | None:
    u = (url or "").strip()
    if not u:
        return None
    low = u.lower()
    if low.endswith(".pdf"):
        return u
    # Common pattern for IACR ePrint references where .pdf can be appended.
    if "eprint.iacr.org" in low and re.search(r"/\d{4}/\d+/?$", low):
        return u.rstrip("/") + ".pdf"
    return None


def is_pdf_blob(blob: bytes, content_type: str) -> bool:
    if blob.startswith(b"%PDF"):
        return True
    return "pdf" in (content_type or "").lower()


def download(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read(), response.headers.get("Content-Type", "")


def next_name(base: Path, stem: str) -> Path:
    p = base / f"{stem}.pdf"
    if not p.exists():
        return p
    i = 2
    while True:
        q = base / f"{stem}-{i}.pdf"
        if not q.exists():
            return q
        i += 1


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    refs_doc = yaml.safe_load((DATA_DIR / "references.yaml").read_text(encoding="utf-8"))
    fam_doc = yaml.safe_load((DATA_DIR / "families.yaml").read_text(encoding="utf-8"))

    refs = {r["id"]: r for r in refs_doc.get("references", [])}
    jobs: list[tuple[str, str, int, str]] = []

    for family in fam_doc.get("families", []):
        family_name = family.get("name", "")
        family_slug = slugify(family_name)
        for ref_id in family.get("reference_ids", []):
            ref = refs.get(ref_id)
            if not ref:
                continue
            url = normalize_url(ref.get("url", ""))
            if not url:
                continue
            year = int(ref.get("year", 2000))
            jobs.append((family_slug, ref_id, year, url))

    seen_key: set[tuple[str, str]] = set()
    success = 0
    fail = 0

    for family_slug, ref_id, year, url in jobs:
        key = (family_slug, url)
        if key in seen_key:
            continue
        seen_key.add(key)

        try:
            blob, content_type = download(url)
        except Exception as exc:
            print(f"FAIL {family_slug} {ref_id}: {url} ({exc})")
            fail += 1
            continue

        if not is_pdf_blob(blob, content_type):
            print(f"SKIP non-pdf {family_slug} {ref_id}: {url}")
            fail += 1
            continue

        stem = f"{year}-{family_slug}"
        out = next_name(OUT_DIR, stem)
        out.write_bytes(blob)
        print(f"OK {out.name} <- {url}")
        success += 1

    print(f"Done: success={success}, fail={fail}, total_jobs={len(jobs)}")


if __name__ == "__main__":
    main()
