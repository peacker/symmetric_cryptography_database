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
    "primitive_families": "primitive_families.yaml",
    "mode_families": "mode_families.yaml",
    "components": "components.yaml",
    "primitive_constructions": "primitive_constructions.yaml",
    "mode_constructions": "mode_constructions.yaml",
    "rounds": "rounds.yaml",
    "primitive_types": "primitive_types.yaml",
    "mode_types": "mode_types.yaml",
    "references": "references.yaml",
    "processes": "processes.yaml",
}


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_data(names: list[str] | None = None) -> dict[str, dict]:
    """Load a subset (or all) of the standard data/*.yaml documents.

    Returns a dict keyed by the short names in DATA_FILES, e.g. "primitive_families" -> parsed doc.
    """
    keys = names if names is not None else list(DATA_FILES.keys())
    return {name: load_yaml(DATA_DIR / DATA_FILES[name]) for name in keys}


def all_families(data: dict[str, dict]) -> list[dict]:
    """Concatenate primitive_families and mode_families, each tagged with its tier.

    Family ids are unique across both tiers, so influence edges, process
    participation, and coverage checks can treat this as one flat namespace.
    """
    out = []
    for fam in data["primitive_families"].get("primitive_families", []):
        tagged = dict(fam)
        tagged["_tier"] = "primitive"
        out.append(tagged)
    for fam in data["mode_families"].get("mode_families", []):
        tagged = dict(fam)
        tagged["_tier"] = "mode"
        out.append(tagged)
    return out


def all_instances(families: list[dict]) -> list[dict]:
    """Flatten every family's nested instances into a flat list, injecting
    family_id/_tier back in so downstream code can treat it like the old
    flat primitives.yaml rows."""
    out = []
    for fam in families:
        for inst in fam.get("instances", []):
            flat = dict(inst)
            flat["family_id"] = fam["id"]
            flat["_tier"] = fam.get("_tier")
            out.append(flat)
    return out


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
