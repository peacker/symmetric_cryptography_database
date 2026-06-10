#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REFS_YAML = ROOT / "data" / "references.yaml"
OUT_DIR_DEFAULT = ROOT / "references"


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


def fetch_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def fetch_bytes(url: str, timeout: int = 60) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read()
        ctype = response.headers.get("Content-Type", "")
        return data, ctype


def wiki_search_titles(query: str, limit: int = 5) -> list[str]:
    encoded = urllib.parse.quote(query)
    url = (
        "https://en.wikipedia.org/w/api.php?action=query&list=search&"
        f"srsearch={encoded}&srlimit={limit}&format=json"
    )
    try:
        data = fetch_json(url)
    except Exception:
        return []
    return [entry.get("title", "") for entry in data.get("query", {}).get("search", []) if entry.get("title")]


def wiki_page_extlinks(title: str) -> list[str]:
    links: list[str] = []
    cont: str | None = None

    while True:
        base = (
            "https://en.wikipedia.org/w/api.php?action=query&prop=extlinks&ellimit=max&"
            f"titles={urllib.parse.quote(title)}&format=json"
        )
        if cont:
            base += f"&eloffset={urllib.parse.quote(cont)}"
        try:
            data = fetch_json(base)
        except Exception:
            return links

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            for item in page.get("extlinks", []):
                star = item.get("*")
                if star:
                    links.append(star)

        cont_data = data.get("continue")
        if not cont_data or "eloffset" not in cont_data:
            break
        cont = str(cont_data["eloffset"])

    return links


def candidate_pdf_urls(family_name: str) -> list[str]:
    queries = [
        f"{family_name} cipher",
        f"{family_name} cryptography",
        f"{family_name} block cipher",
    ]
    seen_titles: set[str] = set()
    urls: list[str] = []

    for q in queries:
        for title in wiki_search_titles(q, limit=5):
            if title in seen_titles:
                continue
            seen_titles.add(title)
            for link in wiki_page_extlinks(title):
                low = link.lower()
                if low.endswith(".pdf"):
                    urls.append(link)
                elif "eprint.iacr.org" in low and re.search(r"/\d{4}/\d+/?$", low):
                    urls.append(link.rstrip("/") + ".pdf")
                elif "rfc-editor.org/rfc/" in low and low.endswith(".html"):
                    # RFC HTML pages are not PDF specs, skip.
                    continue

    # Prioritize well-known canonical sources.
    def rank(url: str) -> int:
        low = url.lower()
        score = 0
        if "eprint.iacr.org" in low:
            score += 3
        if "nist.gov" in low or "csrc.nist.gov" in low:
            score += 3
        if "rfc-editor.org" in low:
            score += 2
        if "iso.org" in low:
            score += 1
        return -score

    dedup: list[str] = []
    seen_url: set[str] = set()
    for u in sorted(urls, key=rank):
        if u not in seen_url:
            seen_url.add(u)
            dedup.append(u)
    return dedup


def infer_year(url: str, fallback_year: int = 2000) -> int:
    years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", url)]
    if years:
        return min(y for y in years if 1900 <= y <= 2100)
    return fallback_year


def is_pdf_blob(blob: bytes, content_type: str) -> bool:
    if blob.startswith(b"%PDF"):
        return True
    return "pdf" in content_type.lower()


def load_placeholder_families(limit: int | None = None) -> list[str]:
    doc = yaml.safe_load(REFS_YAML.read_text(encoding="utf-8"))
    refs = doc.get("references", [])
    names = [
        r.get("title", "").strip()
        for r in refs
        if r.get("notes") == "Placeholder reference for checklist coverage ingestion."
    ]
    names = [n for n in names if n]
    if limit is not None:
        return names[:limit]
    return names


def next_available_path(base_dir: Path, stem: str) -> Path:
    path = base_dir / f"{stem}.pdf"
    if not path.exists():
        return path
    i = 2
    while True:
        alt = base_dir / f"{stem}-{i}.pdf"
        if not alt.exists():
            return alt
        i += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Download cipher spec PDFs into references/")
    parser.add_argument("--out-dir", default=str(OUT_DIR_DEFAULT), help="Output directory for PDFs")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of families to process")
    parser.add_argument("--sleep", type=float, default=0.2, help="Sleep seconds between network requests")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    families = load_placeholder_families(limit=args.limit)
    print(f"Processing {len(families)} families...")

    downloaded = 0
    misses: list[str] = []

    for idx, family in enumerate(families, start=1):
        slug = slugify(family)
        print(f"[{idx}/{len(families)}] {family}")
        urls = candidate_pdf_urls(family)
        ok = False

        for url in urls[:20]:
            try:
                blob, content_type = fetch_bytes(url, timeout=45)
            except Exception:
                time.sleep(args.sleep)
                continue

            if not is_pdf_blob(blob, content_type):
                time.sleep(args.sleep)
                continue

            year = infer_year(url, fallback_year=2000)
            stem = f"{year}-{slug}"
            path = next_available_path(out_dir, stem)
            path.write_bytes(blob)
            print(f"  saved: {path.name} <- {url}")
            downloaded += 1
            ok = True
            break

        if not ok:
            misses.append(family)

        time.sleep(args.sleep)

    print("\nDone")
    print(f"Downloaded: {downloaded}")
    print(f"Misses: {len(misses)}")
    if misses:
        print("Missing families:")
        for m in misses:
            print(f"- {m}")


if __name__ == "__main__":
    main()
