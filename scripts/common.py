#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
BUILD_DIR = ROOT / "build"
SCHEMA_DIR = ROOT / "schema"
DB_PATH = BUILD_DIR / "symmetric_primitives.db"

DATA_FILES = {
    "families": "families.yaml",
    "primitives": "primitives.yaml",
    "components": "components.yaml",
    "constructions": "constructions.yaml",
    "rounds": "rounds.yaml",
    "primitive_types": "primitive_types.yaml",
    "references": "references.yaml",
    "processes": "processes.yaml",
    "modes": "modes.yaml",
}


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_data(names: list[str] | None = None) -> dict[str, dict]:
    """Load a subset (or all) of the standard data/*.yaml documents.

    Returns a dict keyed by the short names in DATA_FILES, e.g. "families" -> parsed doc.
    """
    keys = names if names is not None else list(DATA_FILES.keys())
    return {name: load_yaml(DATA_DIR / DATA_FILES[name]) for name in keys}


def family_year(family: dict, references_by_id: dict[str, dict]) -> int | None:
    """Earliest integer year among a family's references, or None if unknown.

    This is the same "family year" shown in the genealogy visualization
    (see build_db.py), kept here so other scripts agree with what's displayed.
    """
    candidates = [
        references_by_id[ref_id]["year"]
        for ref_id in family.get("reference_ids", [])
        if ref_id in references_by_id and isinstance(references_by_id[ref_id].get("year"), int)
    ]
    return min(candidates) if candidates else None
